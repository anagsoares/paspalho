#!/usr/bin/env python3
"""Busca posts e respostas no X (Twitter).

Caminho 1 (padrão): o Chrome da investigação logado no X (porta 9333). Abre a busca
do X numa aba em segundo plano, rola e captura os posts que a página carrega.
Caminho 2 (plano B): se o X não estiver logado e a skill /last30days estiver
instalada com credencial do X, usa o motor dela.
Sem nenhum dos dois: avisa e sai. Registre a fonte como `pulado`.

Uso:
  uv run -q --with websocket-client python x_search.py --q 'from:fulano' --q 'to:fulano' --q '"Nome Sobrenome" contexto' --out x.jsonl [--scrolls 8]

Cada --q é uma busca do X (aceita operadores: aspas, OR, -palavra, from:, to:, since:AAAA-MM-DD).
`from:` traz o que a pessoa escreveu; `to:` traz quem responde a ela.
Saída no mesmo JSONL dos outros coletores (datas em horário de Brasília).
"""
import argparse, json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

BRT = timezone(timedelta(hours=-3))
sys.path.insert(0, str(Path(__file__).parent))


def data_x(s):
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y").astimezone(BRT).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


def trivial(text):
    return len(re.findall(r"[^\W\d_]", re.sub(r"@\w+", "", text or ""))) <= 3


def x_logado():
    try:
        import websocket  # noqa: F401
    except ImportError:
        print("aviso: rode com `uv run -q --with websocket-client python x_search.py ...`; "
              "sem essa biblioteca não dá pra usar o Chrome logado e cai no plano B.", file=sys.stderr)
        return False
    try:
        import websocket, urllib.request
        import os
        ver = json.load(urllib.request.urlopen(f"http://localhost:{os.environ.get('PASPALHO_PORTA') or 9333}/json/version", timeout=3))
        ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=20, suppress_origin=True)
        ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
        cs = json.loads(ws.recv())["result"]["cookies"]
        ws.close()
        return any(c["name"] == "auth_token" and "x.com" in c["domain"] for c in cs)
    except Exception:
        return False


def tweets_from(bodies):
    """Acha posts no JSON que o X carrega: objetos com legacy.full_text + id."""
    import ig_comments as m
    out = {}
    for b in bodies:
        for d in m.walk(b):
            leg = d.get("legacy")
            if not (isinstance(leg, dict) and "full_text" in leg and leg.get("id_str")):
                continue
            u = ((d.get("core") or {}).get("user_results") or {}).get("result") or {}
            handle = (u.get("core") or {}).get("screen_name") or (u.get("legacy") or {}).get("screen_name") or "?"
            note = (((d.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
            out[leg["id_str"]] = {
                "id": leg["id_str"], "author": handle, "text": note or leg["full_text"],
                "date": data_x(leg.get("created_at", "")), "likes": leg.get("favorite_count", 0),
                "parent": leg.get("in_reply_to_status_id_str"), "to": leg.get("in_reply_to_screen_name"),
            }
    return out


def via_chrome(queries, scrolls):
    import ig_comments as m
    br = m.Browser()
    res = {}
    try:
        for q in queries:
            bodies = br.goto(f"https://x.com/search?q={quote(q)}&src=typed_query&f=live", 8)
            antes = -1
            for _ in range(scrolls):
                br.js("window.scrollTo(0, document.body.scrollHeight)")
                br.wheel()
                bodies += br.drain(2.5)
                n = len(tweets_from(bodies))
                if n == antes:
                    break
                antes = n
            achados = tweets_from(bodies)
            print(f"{q} — {len(achados)} posts", file=sys.stderr)
            for t in achados.values():
                t["busca"] = q
            res.update(achados)
    finally:
        br.close()
    return list(res.values())


def via_last30days(queries, count):
    l30 = Path.home() / ".claude/skills/last30days/scripts"
    if not l30.exists():
        return None
    sys.path.insert(0, str(l30))
    try:
        from lib import env, bird_x
    except Exception:
        return None
    cfg = env.get_config()
    if not (cfg.get("AUTH_TOKEN") and cfg.get("CT0")):
        return None
    bird_x.set_credentials(cfg["AUTH_TOKEN"], cfg["CT0"])
    out = []
    for q in queries:
        items = (bird_x._run_bird_search(q, count, 60) or {}).get("items") or []
        print(f"{q} — {len(items)} posts (via /last30days)", file=sys.stderr)
        for t in items:
            a = t.get("author") or {}
            out.append({"id": str(t.get("id")), "author": a.get("username") or "?", "text": t.get("text") or "",
                        "date": data_x(t.get("createdAt", "")), "likes": t.get("likeCount") or 0,
                        "parent": t.get("inReplyToStatusId"), "to": None, "busca": q})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", action="append", required=True)
    ap.add_argument("--scrolls", type=int, default=8)
    ap.add_argument("--count", type=int, default=40, help="só pro plano B (/last30days)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if x_logado():
        posts = via_chrome(a.q, a.scrolls)
    else:
        posts = via_last30days(a.q, a.count)
        if posts is None:
            sys.exit("X pulado: o Chrome da investigação não está logado no X (rode `uv run -q python scripts/abrir_chrome.py --logins`).")

    vistos, kept = set(), 0
    with open(a.out, "w", encoding="utf-8") as f:
        for t in posts:
            if t["id"] in vistos or trivial(t["text"]):
                continue
            vistos.add(t["id"])
            kept += 1
            url = f"https://x.com/{t['author']}/status/{t['id']}"
            f.write(json.dumps({
                "platform": "x", "post_url": url, "post_date": None,
                "post_caption": f"busca: {t['busca']}" + (f" · respondendo @{t['to']}" if t.get("to") else ""),
                "comment_id": t["id"], "parent_id": t.get("parent"), "author": t["author"],
                "text": t["text"], "likes": t["likes"], "date": t["date"], "url": url,
            }, ensure_ascii=False) + "\n")
    print(f"OK: {kept} posts únicos → {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
