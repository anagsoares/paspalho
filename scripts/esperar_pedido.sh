#!/bin/sh
# Espera a pessoa clicar "Investigar paspalho" no Paspalhômetro local.
# Rode em background (run_in_background): termina quando chega um pedido e imprime o JSON dele.
# O pedido é movido pra pedidos/lidos/ pra não ser pego duas vezes.
# Enquanto espera, atualiza ~/.claude/paspalho/vigia a cada 2 s: é o "sinal de vida" que a
# página usa pra saber se o Claude Code está ouvindo. Religue este script a cada pedido.
B="$HOME/.claude/paspalho"
D="$B/pedidos"
mkdir -p "$D/lidos"
while :; do
  date +%s > "$B/vigia"
  f=$(ls -t "$D"/*.json 2>/dev/null | tail -1)
  if [ -n "$f" ]; then
    cat "$f"; echo
    mv "$f" "$D/lidos/"
    touch "$D/lidos/$(basename "$f")"
    rm -f "$B/vigia"
    exit 0
  fi
  sleep 2
done
