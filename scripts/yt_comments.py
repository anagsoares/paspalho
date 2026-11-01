#!/usr/bin/env python3
"""Coleta comentários públicos do YouTube via yt-dlp (grátis, sem login).

Uso:
  python3 yt_comments.py --video URL [--video URL ...] --out c.jsonl
  python3 yt_comments.py --channel https://www.youtube.com/@canal --videos 8 --out c.jsonl
  python3 yt_comments.py --search "Nome Sobrenome contexto" --videos 8 --out c.jsonl

--search acha vídeos DE OUTRAS PESSOAS falando da pessoa — é onde mora o
paspalho que fala "dela" e não "com ela".

Saída no mesmo formato JSONL do ig_comments.py.
"""
import argparse, json, re, shutil, subprocess, sys
from datetime import datetime, timezone, timedelta

BRT = timezone(timedelta(hours=-3))


def trivial(text):
    t = re.sub(r"@[\w.-]+", "", text or "")
    return len(re.findall(r"[^\W\d_]", t)) <= 3


def ytdlp(args):
    # sem yt-dlp instalado, roda pelo uv (baixa na hora, não precisa instalar nada)
    cmd = ["yt-dlp"] if shutil.which("yt-dlp") else ["uvx", "yt-dlp"]
    r = subprocess.run([*cmd, "--no-warnings", "--ignore-errors", *args], capture_output=True, text=True)
    return r.stdout


def list_videos(src, n):
    out = ytdlp(["--flat-playlist", "--playlist-end", str(n), "--print", "%(webpage_url)s\t%(title)s", src])
    return [l.split("\t")[0] for l in out.splitlines() if l.startswith("http")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", action="append", default=[])
    ap.add_argument("--channel")
    ap.add_argument("--search")
    ap.add_argument("--videos", type=int, default=8)
    ap.add_argument("--max-comments", type=int, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    urls = list(a.video)
    if a.channel:
        urls += list_videos(a.channel.rstrip("/") + "/videos", a.videos)
    if a.search:
        urls += list_videos(f"ytsearch{a.videos}:{a.search}", a.videos)
    urls = list(dict.fromkeys(urls))
    if not urls:
        sys.exit("nenhum vídeo encontrado")

    total = kept = 0
    with open(a.out, "w") as f:
        for url in urls:
            raw = ytdlp(["-J", "--skip-download", "--write-comments",
                         "--extractor-args", f"youtube:max_comments={a.max_comments},all,all,all;comment_sort=top", url])
            try:
                info = json.loads(raw)
            except json.JSONDecodeError:
                print(f"aviso: falhou {url}", file=sys.stderr)
                continue
            cs = info.get("comments") or []
            print(f"{url} — {info.get('channel')} · {info.get('title','')[:60]} — {len(cs)} comentários", file=sys.stderr)
            for c in cs:
                total += 1
                if trivial(c.get("text")):
                    continue
                kept += 1
                parent = c.get("parent")
                f.write(json.dumps({
                    "platform": "youtube",
                    "post_url": info.get("webpage_url", url),
                    "post_date": info.get("upload_date"),
                    "post_caption": f"[{info.get('channel')}] {info.get('title','')}"[:200],
                    "comment_id": c.get("id"),
                    "parent_id": None if parent in (None, "root") else parent,
                    "author": c.get("author"),
                    "text": c.get("text"),
                    "likes": c.get("like_count", 0),
                    "date": datetime.fromtimestamp(c["timestamp"], BRT).strftime("%Y-%m-%d %H:%M") if c.get("timestamp") else None,
                    "url": f"{info.get('webpage_url', url)}&lc={c.get('id')}",
                }, ensure_ascii=False) + "\n")
    print(f"OK: {len(urls)} vídeos, {total} comentários, {kept} não-triviais → {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
