#!/usr/bin/env python3
"""Lista quem um perfil do Instagram SEGUE — base do modo autor: como o Instagram
não lista comentários por pessoa, os perfis que o suspeito segue são onde ele
mais provavelmente comenta. Filtra pelo nicho e devolve os @ pra varrer com
`ig_comments.py --user A --user B ... --author <suspeito>`.

Uso:
  uv run -q --with websocket-client python ig_following.py --user fulano --out seguindo.json [--max 5000]

Saída: JSON [{username, full_name, is_verified}] na ordem do Instagram
(mais recentes primeiro). Usa o Chrome da investigação (9333), aba em segundo plano.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ig_comments as m  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--max", type=int, default=5000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    u = a.user.lstrip("@")

    br = m.Browser()
    found = {}

    def grab(bodies):
        for b in bodies:
            for d in m.walk(b):
                if d.get("username") and "full_name" in d and d["username"].lower() != u.lower():
                    found.setdefault(d["username"], {"username": d["username"], "full_name": d.get("full_name") or "",
                                                     "is_verified": bool(d.get("is_verified"))})
    try:
        br.goto(f"https://www.instagram.com/{u}/", 7)
        m.check_login(br)
        grab(br.goto(f"https://www.instagram.com/{u}/following/", 8))
        stale = 0
        while len(found) < a.max:
            before = len(found)
            br.js(m.SCROLL_JS)
            br.wheel()
            grab(br.drain(2.5))
            stale = stale + 1 if len(found) == before else 0
            if stale >= 4:
                break
            if len(found) // 200 != before // 200:
                print(f"... {len(found)}", file=sys.stderr)
    finally:
        br.close()
    json.dump(list(found.values()), open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"OK: {len(found)} perfis seguidos por @{u} → {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
