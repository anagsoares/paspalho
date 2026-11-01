#!/usr/bin/env python3
"""Todas as respostas que um @ deu no Threads (aba Respostas do perfil), com o
post a que respondeu. Precisa do Threads logado no Chrome da investigação (9333) —
deslogado só mostra ~5. O Threads tira da página as respostas antigas conforme
rola, então NÃO dá pra ler o texto da página no fim: aqui se captura o JSON que
o site carrega a cada rolagem.

Uso:
  uv run -q --with websocket-client python threads_replies.py <handle> <saida.json> [max_rolagens=150] [replies|threads]
  (replies = respostas dele em posts alheios; threads = posts dele mesmo)

Saída: JSON [{author, text, date, likes, url, parent_author, parent_text, parent_url}]
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ig_comments as m

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")
who = sys.argv[1].lstrip("@").lower()
out = sys.argv[2]
maxs = int(sys.argv[3]) if len(sys.argv) > 3 else 150
tab = sys.argv[4] if len(sys.argv) > 4 else "replies"
url = f"https://www.threads.com/@{who}" + ("/replies" if tab == "replies" else "")
br = m.Browser()
items = {}
def grab(bodies):
    for b in bodies:
        for d in m.walk(b):
            if isinstance(d.get("thread_items"), list):
                posts = [ti.get("post") for ti in d["thread_items"] if isinstance(ti, dict) and ti.get("post")]
                for i, p in enumerate(posts):
                    u = (p.get("user") or {}).get("username", "")
                    if u.lower() == who and p.get("code"):
                        parent = posts[i-1] if i else None
                        items[p["code"]] = {
                            "author": u, "text": (p.get("caption") or {}).get("text") or "",
                            "date": m.ts(p["taken_at"]) if p.get("taken_at") else None,
                            "likes": p.get("like_count", 0),
                            "url": f"https://www.threads.com/@{u}/post/{p['code']}",
                            "parent_author": (parent.get("user") or {}).get("username") if parent else None,
                            "parent_text": ((parent.get("caption") or {}).get("text") or "")[:300] if parent else None,
                            "parent_url": f"https://www.threads.com/@{(parent.get('user') or {}).get('username')}/post/{parent.get('code')}" if parent else None,
                        }
try:
    grab(br.goto(url, 8) + br.embedded())
    stale = 0
    for i in range(maxs):
        before = len(items)
        br.js("window.scrollTo(0, document.body.scrollHeight)"); br.wheel()
        grab(br.drain(3))
        stale = stale + 1 if len(items) == before else 0
        if stale >= 4: break
    json.dump(sorted(items.values(), key=lambda x: x["date"] or "", reverse=True), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    v = sorted(items.values(), key=lambda x: x["date"] or "")
    print("rolagens", i+1, "| respostas dele:", len(items), "| de", v[0]["date"] if v else "-", "até", v[-1]["date"] if v else "-")
finally:
    br.close()
