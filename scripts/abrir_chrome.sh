#!/bin/sh
# Abre o "Chrome da investigação": um Chrome separado do seu, com perfil próprio,
# que a skill controla pela porta 9333. Na primeira vez, abre as telas de login de
# Instagram, Threads, X e LinkedIn. Os logins ficam salvos nesse perfil.
#
# Dica: use contas criadas só pra isso (veja o README).
PORTA="${PASPALHO_PORTA:-9333}"
PERFIL="$HOME/.claude/paspalho/chrome"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LOGINS="https://www.instagram.com/accounts/login/ https://www.threads.com/login https://x.com/i/flow/login https://www.linkedin.com/login"

if curl -s -m 2 "http://localhost:$PORTA/json/version" >/dev/null 2>&1; then
  echo "Chrome da investigação já está aberto (porta $PORTA)."
  if [ "$1" = "--logins" ]; then
    for u in $LOGINS; do curl -s -X PUT "http://localhost:$PORTA/json/new?$u" >/dev/null; done
    echo "Abri as telas de login."
  fi
  exit 0
fi

if [ ! -x "$CHROME" ]; then
  echo "Não achei o Google Chrome em /Applications. Instale o Chrome e rode de novo."
  exit 1
fi

mkdir -p "$PERFIL"
PRIMEIRA=0
[ -z "$(ls -A "$PERFIL" 2>/dev/null)" ] && PRIMEIRA=1

if [ "$PRIMEIRA" = 1 ] || [ "$1" = "--logins" ]; then
  # shellcheck disable=SC2086
  nohup "$CHROME" --remote-debugging-port=$PORTA --user-data-dir="$PERFIL" --no-first-run --no-default-browser-check $LOGINS >/dev/null 2>&1 &
  echo "Abri o Chrome da investigação com as telas de login de Instagram, Threads, X e LinkedIn."
else
  nohup "$CHROME" --remote-debugging-port=$PORTA --user-data-dir="$PERFIL" --no-first-run --no-default-browser-check --no-startup-window >/dev/null 2>&1 &
  echo "Abri o Chrome da investigação (porta $PORTA)."
fi

for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -s -m 1 "http://localhost:$PORTA/json/version" >/dev/null 2>&1 && exit 0
  sleep 1
done
echo "O Chrome abriu mas a porta $PORTA não respondeu. Feche esse Chrome e rode de novo."
exit 1
