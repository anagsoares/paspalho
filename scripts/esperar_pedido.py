#!/usr/bin/env python3
"""Espera a pessoa clicar "Investigar paspalho" no Paspalhômetro local.

Rode em background (run_in_background): termina quando chega um pedido e imprime o JSON dele.
O pedido é movido pra pedidos/lidos/ pra não ser pego duas vezes.
Enquanto espera, atualiza ~/.claude/paspalho/vigia a cada 2 s: é o "sinal de vida" que a
página usa pra saber se o Claude Code está ouvindo. Religue este script a cada pedido.

Uso:
  uv run -q python esperar_pedido.py
"""
import os, sys, time
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

B = Path.home() / ".claude" / "paspalho"
D = B / "pedidos"
LIDOS = D / "lidos"


def main():
    LIDOS.mkdir(parents=True, exist_ok=True)
    vigia = B / "vigia"
    while True:
        vigia.write_text(str(int(time.time())), encoding="utf-8")
        fila = sorted(D.glob("*.json"), key=lambda f: f.stat().st_mtime)
        if fila:
            f = fila[0]  # o mais antigo primeiro
            try:
                texto = f.read_text(encoding="utf-8")
                destino = LIDOS / f.name
                os.replace(f, destino)
            except OSError:  # ainda sendo gravado ou cancelado agora: tenta de novo
                time.sleep(0.5)
                continue
            os.utime(destino)  # a hora em que foi pego (a página usa)
            print(texto, flush=True)
            vigia.unlink(missing_ok=True)
            return
        time.sleep(2)


if __name__ == "__main__":
    main()
