#!/usr/bin/env python3
"""Gera o dossiê HTML da varredura /paspalho e guarda o histórico.

Uso:
  uv run -q python render_report.py achados.json

achados.json:
{
  "alvo": {"nome": "Fulano de Tal", "handle": "fulano"},
  "periodo": "últimos 90 dias",
  "fontes": [{"fonte": "Instagram @fulano (12 posts)", "lidos": 812, "status": "ok", "obs": ""}],
  "padrao": ["(opcional, modo suspeito) 1 linha por padrão: contra quem, tema, frequência, rede"],
  "achados": [{
     "nivel": "grave" | "paspalho" | "critica",
     "platform": "instagram", "author": "fulano", "text": "...", "url": "...",
     "date": "2026-10-28 21:13", "likes": 4, "post_url": "...", "post_caption": "...",
     "motivo": "por que caiu nesse nível (1 frase)"
  }]
}

Salva em ~/Downloads/Paspalho/<handle>/<data>.json + .html (ou na pasta da
variável PASPALHO_DIR) e marca como
NOVO o achado cuja url não aparece em nenhuma varredura anterior da pasta.
Imprime o caminho do HTML.
"""
import html, json, os, re, sys
from datetime import datetime
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(os.environ.get("PASPALHO_DIR") or Path.home() / "Downloads" / "Paspalho")
NIVEIS = {
    "grave": ("🚨", "Ofensa grave", "xingamento, ameaça, misoginia, acusação de crime — candidato a medida jurídica"),
    "paspalho": ("🤡", "Paspalho detectado", "deboche, rebaixamento, ataque à pessoa em vez da ideia"),
    "critica": ("🧐", "Crítica dura, mas legítima", "discorda do conteúdo sem atacar a pessoa — não é paspalhada, fica só pra contexto"),
}
E = html.escape


def L(u):
    """Link só se for http(s): texto coletado nas redes não vira javascript: no laudo."""
    u = str(u or "")
    return E(u) if re.match(r"https?://", u, re.I) else "#"

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def quando(d):
    """'2026-01-15 21:30' -> 'quinta, 15/01/2026 às 21:30' (horário de Brasília). Outro formato volta como veio."""
    try:
        dt = datetime.strptime(str(d)[:16], "%Y-%m-%d %H:%M")
        return f"{DIAS[dt.weekday()]}, {dt.strftime('%d/%m/%Y')} às {dt.strftime('%H:%M')}"
    except Exception:
        return str(d or "")


def main():
    src = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    handle = re.sub(r"[^\w.-]", "_", str(src["alvo"]["handle"]).lstrip("@")).strip(".") or "sem-handle"  # vira nome de pasta
    pasta = BASE / handle
    pasta.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now().strftime("%Y-%m-%d")

    vistos = set()
    for old in pasta.glob("*.json"):
        if old.stem == hoje:
            continue
        try:
            vistos |= {a["url"] for a in json.loads(old.read_text(encoding="utf-8")).get("achados", [])}
        except Exception:
            pass
    for a in src["achados"]:
        a["novo"] = a["url"] not in vistos
    (pasta / f"{hoje}.json").write_text(json.dumps(src, ensure_ascii=False, indent=2), encoding="utf-8")

    cont = {k: sum(1 for a in src["achados"] if a["nivel"] == k) for k in NIVEIS}
    novos = sum(1 for a in src["achados"] if a["novo"] and a["nivel"] != "critica")
    lidos = sum(f.get("lidos") or 0 for f in src["fontes"])

    def card(a):
        badge = '<span class="novo">NOVO</span>' if a["novo"] else ""
        ctx = f'<div class="ctx">no post: <a href="{L(a.get("post_url"))}">{E((a.get("post_caption") or "")[:110])}</a></div>' if a.get("post_url") else ""
        return f"""
        <article class="card {E(a['nivel'])}">
          <header><b>{E(a['platform'])}</b> · <span class="autor">@{E(str(a.get('author','?')).lstrip('@'))}</span>
            · {E(quando(a.get('date')))} · ♥ {a.get('likes') or 0} {badge}</header>
          <blockquote>{E(a['text'])}</blockquote>
          <p class="motivo">{E(a.get('motivo',''))}</p>
          {ctx}
          <a class="link" href="{L(a['url'])}">abrir comentário ↗</a>
        </article>"""

    secoes = ""
    for k, (emo, titulo, desc) in NIVEIS.items():
        itens = sorted([a for a in src["achados"] if a["nivel"] == k], key=lambda a: (not a["novo"], -(a.get("likes") or 0)))
        if not itens:
            continue
        secoes += f'<section><h2>{emo} {titulo} <small>{len(itens)}</small></h2><p class="desc">{desc}</p>{"".join(card(a) for a in itens)}</section>'
    if not secoes:
        secoes = '<section class="limpo"><h2>✨ Nenhum paspalho no radar</h2><p>Varredura limpa nas fontes abaixo.</p></section>'

    padrao = ""
    if src.get("padrao"):
        padrao = '<section><h2>🧭 Padrão</h2><ul class="padrao">' + "".join(f"<li>{E(x)}</li>" for x in src["padrao"]) + "</ul></section>"

    fontes = "".join(
        f"<tr><td>{E(f['fonte'])}</td><td>{f.get('lidos') if f.get('lidos') is not None else '—'}</td>"
        f"<td class='st-{E(f.get('status','ok'))}'>{E(f.get('status','ok'))}</td><td>{E(f.get('obs',''))}</td></tr>"
        for f in src["fontes"])

    doc = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Paspalhômetro · @{E(handle)} · {hoje}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#fbf7f0;--ink:#1d1a16;--muted:#6f675c;--line:#e6ddcf;--grave:#c0392b;--pasp:#e67e22;--crit:#7f8c8d}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 ui-sans-serif,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:880px;margin:0 auto;padding:48px 24px 80px}}
.kicker{{font:600 12px/1 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
h1{{font:800 44px/1.05 Georgia,serif;margin:10px 0 6px;letter-spacing:-.02em}} h1 span{{color:var(--pasp)}}
.sub{{color:var(--muted);margin:0 0 28px}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 36px}}
.kpi{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px}} .kpi b{{display:block;font:800 32px/1 Georgia,serif}} .kpi span{{font-size:13px;color:var(--muted)}}
.kpi.g b{{color:var(--grave)}} .kpi.p b{{color:var(--pasp)}}
h2{{font:700 24px/1.2 Georgia,serif;margin:40px 0 4px}} h2 small{{font:600 14px ui-monospace,monospace;color:var(--muted);margin-left:6px}}
.desc{{color:var(--muted);margin:0 0 14px;font-size:14px}}
.card{{background:#fff;border:1px solid var(--line);border-left:5px solid var(--crit);border-radius:12px;padding:16px 18px;margin:0 0 12px}}
.card.grave{{border-left-color:var(--grave)}} .card.paspalho{{border-left-color:var(--pasp)}}
.card header{{font-size:13px;color:var(--muted)}} .autor{{color:var(--ink);font-weight:600}}
blockquote{{margin:10px 0;font:17px/1.5 Georgia,serif;white-space:pre-wrap}}
.motivo{{margin:0 0 6px;font-size:14px}} .ctx{{font-size:13px;color:var(--muted)}} .ctx a{{color:inherit}}
.link{{font-size:13px;font-weight:600;color:var(--ink)}}
.novo{{background:var(--grave);color:#fff;font:700 10px/1 ui-monospace,monospace;padding:3px 6px;border-radius:4px;margin-left:6px}}
table{{width:100%;border-collapse:collapse;font-size:14px;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
td,th{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line)}} th{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
.st-falhou,.st-bloqueado{{color:var(--grave);font-weight:600}} .st-parcial{{color:var(--pasp);font-weight:600}}
.padrao{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 18px 14px 34px;margin:8px 0 0}} .padrao li{{margin:4px 0}}
.nota{{margin-top:36px;font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:16px}}
@media(max-width:640px){{.kpis{{grid-template-columns:repeat(2,1fr)}} h1{{font-size:34px}}}}
</style></head><body><main>
<div class="kicker">Paspalhômetro · varredura de {hoje}</div>
<h1>{E(src['alvo']['nome'])} <span>@{E(handle)}</span></h1>
<p class="sub">{E(src.get('periodo',''))} · {lidos} comentários/posts lidos</p>
<div class="kpis">
 <div class="kpi g"><b>{cont['grave']}</b><span>ofensas graves</span></div>
 <div class="kpi p"><b>{cont['paspalho']}</b><span>paspalhos</span></div>
 <div class="kpi"><b>{cont['critica']}</b><span>críticas legítimas</span></div>
 <div class="kpi"><b>{novos}</b><span>novos desde a última</span></div>
</div>
{padrao}
{secoes}
<h2>🔎 Onde procurei</h2>
<table><tr><th>Fonte</th><th>Lidos</th><th>Status</th><th>Obs.</th></tr>{fontes}</table>
<p class="nota">Só conteúdo público. Comentário pode ser apagado a qualquer momento — se algum for virar caso jurídico,
preservar já (print com URL e data visíveis, ou ata notarial/Verifact). Autor = o @ exibido na plataforma; nenhuma tentativa de identificar quem está por trás.</p>
</main></body></html>"""
    out = pasta / f"{hoje}.html"
    out.write_text(doc, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
