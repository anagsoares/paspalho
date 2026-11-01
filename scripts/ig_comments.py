#!/usr/bin/env python3
"""Coleta comentários públicos de posts do Instagram pelo Chrome da investigação
(o "Chrome da investigação", porta 9333, aberto por scripts/abrir_chrome.sh) já logado.

Como funciona: abre uma aba em segundo plano, navega até o perfil e até cada
post como uma pessoa faria, e captura as respostas GraphQL que o próprio
Instagram carrega (Network.getResponseBody). Chamar /api/v1/... direto via
fetch dá 429/404 desde 2026-10 — por isso a captura passiva.

Uso:
  uv run -q --with websocket-client python ig_comments.py --user fulano --posts 12 --out c.jsonl
  uv run -q --with websocket-client python ig_comments.py --post https://www.instagram.com/p/XXXX/ --out c.jsonl

Saída: JSONL, um comentário por linha:
  {platform, post_url, post_date, post_caption, comment_id, parent_id, author,
   text, likes, date, url}
Comentários triviais (só emoji/pontuação, só @menção, <=3 letras) são
descartados — nunca são paspalhada e só incham a triagem.
"""
import argparse, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

import websocket

BRT = timezone(timedelta(hours=-3))
# Porta do Chrome da investigação. Mude com PASPALHO_PORTA (ex.: pra testar do zero com
# um Chrome novo sem mexer num Chrome de debug que já usa a 9333).
PORTA = int(os.environ.get("PASPALHO_PORTA") or 9333)
SCROLL_JS = r"""
(() => {
  // abre respostas escondidas ("View replies (3)", "View all 5 replies", "Ver respostas")
  let clicked = 0;
  document.querySelectorAll('span,button,div[role=button]').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t.length < 40 && /^(Ver|View)\b.*(respostas|replies)/i.test(t) && clicked < 15) { el.click(); clicked++; }
  });
  // o spinner "Loading..." no fim da lista é o gatilho da próxima página
  const l = document.querySelector('[aria-label="Loading..."],[aria-label="Carregando..."]');
  if (l) l.scrollIntoView({block: 'end'});
  document.querySelectorAll('*').forEach(el => {
    if (el.tagName !== 'HTML' && el.scrollHeight > el.clientHeight + 50 && /(auto|scroll)/.test(getComputedStyle(el).overflowY)) {
      el.scrollTop = el.scrollHeight; el.dispatchEvent(new Event('scroll'));
    }
  });
  return !!l;
})()
"""


def ts(epoch):
    return datetime.fromtimestamp(int(epoch), BRT).strftime("%Y-%m-%d %H:%M")


def trivial(text):
    t = re.sub(r"@[\w.]+", "", text or "")
    return len(re.findall(r"[^\W\d_]", t)) <= 3


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


class Browser:
    def __init__(self, port=None):
        port = port or PORTA
        try:
            ver = json.load(urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=5))
        except Exception:
            sys.exit(f"O Chrome da investigação não está aberto (porta {port}). Rode: sh scripts/abrir_chrome.sh")
        self.ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self.n, self.pending = 0, []
        self.open_tab()

    def open_tab(self):
        # aba em segundo plano numa janela que já existe — não abre janela nova nem rouba foco.
        # (janela minimizada não serve: o Chrome pausa a rolagem infinita)
        self.target = self.call("Target.createTarget", {"url": "about:blank", "background": True})["targetId"]
        self.s = self.call("Target.attachToTarget", {"targetId": self.target, "flatten": True})["sessionId"]
        self.call("Network.enable", {}, self.s)
        self.call("Page.enable", {}, self.s)
        # aba em segundo plano não dispara lazy-load; fingir foco resolve
        self.call("Emulation.setFocusEmulationEnabled", {"enabled": True}, self.s)

    def call(self, method, params=None, sess=None):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if sess:
            msg["sessionId"] = sess
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.n:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error']}")
                return r["result"]
            self.pending.append(r)

    def drain(self, sec):
        """Espera `sec` segundos coletando eventos; devolve os JSONs GraphQL que chegaram."""
        end = time.time() + sec
        self.ws.settimeout(1)
        while time.time() < end:
            try:
                self.pending.append(json.loads(self.ws.recv()))
            except Exception:
                pass
        self.ws.settimeout(60)
        ids, bodies = [], []
        for e in self.pending:
            if e.get("method") == "Network.responseReceived":
                u = e["params"]["response"]["url"]
                if "/graphql" in u or "/api/v1/media/" in u or "/api/v1/friendships/" in u:
                    ids.append(e["params"]["requestId"])
            elif e.get("method") == "Network.loadingFinished" and e["params"]["requestId"] in ids:
                pass
        self.pending = []
        for rid in ids:
            try:
                b = self.call("Network.getResponseBody", {"requestId": rid}, self.s).get("body", "")
                for line in b.splitlines():  # alguns GraphQL vêm em várias linhas JSON
                    line = line.strip()
                    if line.startswith("{"):
                        bodies.append(json.loads(line))
            except Exception:
                continue
        return bodies

    def goto(self, url, wait=8):
        try:
            self.call("Page.navigate", {"url": url}, self.s)
        except RuntimeError as e:
            # a aba some se alguém fechar abas/janela do Chrome da investigação no meio — reabre e segue
            if "Session with given id not found" not in str(e) and "No target" not in str(e):
                raise
            print("aviso: aba de coleta foi fechada — reabrindo", file=sys.stderr)
            self.open_tab()
            self.call("Page.navigate", {"url": url}, self.s)
        return self.drain(wait)

    def embedded(self):
        """JSON que o Instagram já manda renderizado no HTML (a 1ª página de
        comentários de um post vem aqui, não em chamada GraphQL)."""
        texts = self.js("""[...document.querySelectorAll('script[type="application/json"]')]
            .map(s => s.textContent).filter(t => t.includes('comment_like_count') || t.includes('taken_at'))""") or []
        out = []
        for t in texts:
            try:
                out.append(json.loads(t))
            except json.JSONDecodeError:
                pass
        return out

    def wheel(self):
        self.call("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": 950, "y": 400, "deltaX": 0, "deltaY": 2000}, self.s)

    def js(self, expr):
        return self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True}, self.s)["result"].get("value")

    def close(self):
        try:
            self.call("Target.closeTarget", {"targetId": self.target})
        except Exception:
            pass


def posts_from(bodies):
    out = {}
    for b in bodies:
        for d in walk(b):
            if "code" in d and "taken_at" in d and "pk" in d and d.get("taken_at"):
                out[d["code"]] = d
    return out


def comments_from(bodies):
    out = {}
    for b in bodies:
        for d in walk(b):
            u = d.get("user")
            if "text" in d and "created_at" in d and "pk" in d and isinstance(u, dict) and u.get("username"):
                out[str(d["pk"])] = d
    return out


def check_login(br):
    href = br.js("location.href") or ""
    if "/accounts/login" in href or br.js("document.documentElement.className.includes('not-logged-in')"):
        sys.exit("Instagram deslogado no Chrome da investigação — rode `sh scripts/abrir_chrome.sh --logins` e entre no Instagram.")


def user_posts(br, user, n):
    """Posts recentes de um perfil (só os do dono — a página também carrega o feed de quem está logado)."""
    bodies = br.goto(f"https://www.instagram.com/{user}/", 9)
    check_login(br)
    bodies += br.embedded()
    alvo = user.lower()
    own = lambda ps: {k: v for k, v in ps.items()
                      if ((v.get("user") or v.get("owner") or {}).get("username") or "").lower() == alvo}
    posts = own(posts_from(bodies))
    tries = 0
    while posts and len(posts) < n and tries < 8:
        br.js("window.scrollTo(0, document.body.scrollHeight)")
        posts.update(own(posts_from(br.drain(3))))
        tries += 1
    return sorted(posts.values(), key=lambda p: -int(p["taken_at"]))[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", action="append", default=[], help="@ do perfil (sem @); pode repetir")
    ap.add_argument("--post", action="append", default=[], help="URL de post/reel (pode repetir)")
    ap.add_argument("--posts", type=int, default=12, help="quantos posts recentes de cada perfil")
    ap.add_argument("--since", help="AAAA-MM-DD: ignora posts mais antigos")
    ap.add_argument("--author", help="modo autor: só grava comentários feitos por este @")
    ap.add_argument("--scrolls", type=int, default=25, help="teto de rolagens por post (~15 comentários cada; para sozinho quando acaba)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not a.user and not a.post:
        sys.exit("passe --user ou --post")
    author = a.author.lstrip("@").lower() if a.author else None
    since = datetime.strptime(a.since, "%Y-%m-%d").replace(tzinfo=BRT).timestamp() if a.since else 0

    br = Browser()
    try:
        targets = []  # (code, meta|None)
        for u in a.user:
            u = u.lstrip("@")
            ps = [p for p in user_posts(br, u, a.posts) if int(p["taken_at"]) >= since]
            if not ps:
                msg = (f"Nenhum post de @{u} visível pra conta logada — perfil privado, sem posts recentes, "
                       "ou BLOQUEIO entre a conta logada e ele (bloqueio esconde o perfil nos dois sentidos).")
                if len(a.user) == 1 and not a.post:
                    sys.exit(msg + " Pra ver, precisa logar outra conta no Chrome da investigação.")
                print("aviso: " + msg, file=sys.stderr)
            targets += [(p["code"], p) for p in ps]
        for url in a.post:
            m = re.search(r"/(?:p|reel|reels|tv)/([\w-]+)", url)
            if m:
                targets.append((m.group(1), None))
            else:
                print(f"aviso: URL inválida {url}", file=sys.stderr)

        total = kept = 0
        with open(a.out, "w") as f:
            for code, meta in targets:
                post_url = f"https://www.instagram.com/p/{code}/"
                if meta and not meta.get("comment_count"):
                    continue  # post sem comentário: nem abre
                bodies = br.goto(post_url, 7)
                check_login(br)
                bodies += br.embedded()
                seen, stale = len(comments_from(bodies)), 0
                for _ in range(a.scrolls):
                    has_more = br.js(SCROLL_JS)
                    br.wheel()
                    bodies += br.drain(3)
                    now = len(comments_from(bodies))
                    stale = stale + 1 if now == seen else 0
                    seen = now
                    if stale >= 2 or (not has_more and stale >= 1):
                        break
                if meta is None:
                    meta = posts_from(bodies).get(code, {})
                owner = ((meta.get("user") or meta.get("owner") or {}).get("username")) or ""
                cap = (f"[@{owner}] " if owner else "") + ((meta.get("caption") or {}).get("text") or "")[:200]
                pdate = ts(meta["taken_at"]) if meta.get("taken_at") else None
                cs = comments_from(bodies)
                hits = 0
                for c in cs.values():
                    total += 1
                    if author and c["user"]["username"].lower() != author:
                        continue
                    if not author and trivial(c.get("text")):
                        continue
                    kept += 1; hits += 1
                    parent = c.get("parent_comment_id") or c.get("replied_to_comment_id")
                    f.write(json.dumps({
                        "platform": "instagram",
                        "post_url": post_url,
                        "post_date": pdate,
                        "post_caption": cap,
                        "comment_id": str(c["pk"]),
                        "parent_id": str(parent) if parent else None,
                        "author": c["user"]["username"],
                        "text": c.get("text"),
                        "likes": c.get("comment_like_count", 0),
                        "date": ts(c["created_at"]),
                        "url": f"{post_url}c/{c['pk']}/",
                    }, ensure_ascii=False) + "\n")
                    f.flush()
                tag = f", {hits} de @{author}" if author else ""
                print(f"{post_url} @{owner} ({pdate}) — {meta.get('comment_count', '?')} no post, {len(cs)} capturados{tag}", file=sys.stderr)
        print(f"OK: {len(targets)} posts, {total} comentários lidos, {kept} gravados → {a.out}", file=sys.stderr)
    finally:
        br.close()


if __name__ == "__main__":
    main()
