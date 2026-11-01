#!/usr/bin/env python3
"""Manda o andamento da investigação pro Paspalhômetro local (a página lê a cada 2 s).

Uso (o <id> vem do pedido):
  uv run -q python progresso.py <id> etapa "Lendo respostas no Threads"          # nova etapa, girando
  uv run -q python progresso.py <id> ok "405 respostas lidas"                     # fecha a última etapa com ✓
  uv run -q python progresso.py <id> erro "Instagram pediu login"                 # fecha com !
  uv run -q python progresso.py <id> pulo "TikTok: sem pista de onde procurar"    # fecha com –
  uv run -q python progresso.py <id> linhas parcial.json                          # adiciona linhas à tabela (lista no formato `achados`)
  uv run -q python progresso.py <id> fim achados.json                             # laudo final (o mesmo JSON do render_report.py)

Grava em ~/.claude/paspalho/andamento/<id>.json de forma atômica.
"""
import json, os, sys, tempfile, time
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

DADOS = Path.home() / ".claude" / "paspalho" / "andamento"


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    pid, acao, arg = sys.argv[1], sys.argv[2], sys.argv[3]
    DADOS.mkdir(parents=True, exist_ok=True)
    if (DADOS.parent / "cancelados" / pid).exists():
        sys.exit(f"PEDIDO {pid} CANCELADO: a pessoa clicou em 'Parar pesquisa'. Pare esta investigação e espere o próximo pedido.")
    f = DADOS / f"{pid}.json"
    st = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"etapas": [], "linhas": [], "fim": False}
    estados = {"ok": "ok", "erro": "err", "pulo": "skip"}
    if acao == "etapa":
        for e in st["etapas"]:
            if e["estado"] == "run":
                e["estado"] = "ok"
        st["etapas"].append({"txt": arg, "estado": "run", "det": ""})
    elif acao in estados:
        alvo = next((e for e in reversed(st["etapas"]) if e["estado"] == "run"), None)
        if alvo is None:
            st["etapas"].append({"txt": arg, "estado": estados[acao], "det": ""})
        else:
            alvo["estado"], alvo["det"] = estados[acao], arg
    elif acao == "linhas":
        novas = json.loads(Path(arg).read_text(encoding="utf-8"))
        vistos = {l.get("url") or l.get("text") for l in st["linhas"]}
        st["linhas"] += [l for l in novas if (l.get("url") or l.get("text")) not in vistos]
    elif acao == "fim":
        for e in st["etapas"]:
            if e["estado"] == "run":
                e["estado"] = "ok"
        st["resultado"] = json.loads(Path(arg).read_text(encoding="utf-8"))
        st["fim"] = True
    else:
        sys.exit(f"ação desconhecida: {acao}")
    fd, tmp = tempfile.mkstemp(dir=DADOS)
    with os.fdopen(fd, "w", encoding="utf-8") as h:
        json.dump(st, h, ensure_ascii=False)
    for tentativa in range(20):  # no Windows, o arquivo pode estar aberto pelo servidor por um instante
        try:
            os.replace(tmp, f)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        os.unlink(tmp)
        sys.exit("não consegui gravar o andamento (arquivo em uso); rode de novo")


if __name__ == "__main__":
    main()
