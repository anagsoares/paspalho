#!/bin/sh
# Instala (ou atualiza) a skill /paspalho do Claude Code.
#
# Uso, no Terminal do Mac:
#   curl -fsSL https://raw.githubusercontent.com/anagsoares/paspalho/main/instalar.sh | sh
#
# O que ele faz:
#   0. mostra o aviso legal e só continua com "sim" (ou PASPALHO_ACEITO=sim);
#   1. confere se é Mac e se tem o Google Chrome;
#   2. instala o uv (programa que roda os scripts), se faltar, depois de perguntar;
#   3. baixa a skill em ~/.claude/skills/paspalho (ou atualiza, se já estiver lá).
# Não pede senha, não mexe no seu Chrome de sempre e não instala nada fora da sua pasta.
set -e

REPO="${PASPALHO_REPO:-https://github.com/anagsoares/paspalho}"  # variável só pra teste
DESTINO="$HOME/.claude/skills/paspalho"

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
aviso(){ printf '  \033[33m!\033[0m %s\n' "$1"; }
erro() { printf '  \033[31m✗\033[0m %s\n' "$1"; exit 1; }

# Quando roda por "curl | sh", o teclado não está no stdin: pergunta direto no terminal.
perguntar() {
  printf '%s [S/n] ' "$1"
  if [ -r /dev/tty ]; then read -r r </dev/tty; else r=s; fi
  case "$r" in [nN]*) return 1 ;; *) return 0 ;; esac
}

echo ""
echo "🤡 Instalando o Paspalhômetro (skill /paspalho do Claude Code)"
echo ""

# 0. Aviso legal: só segue com "sim" explícito
cat <<'AVISO'
  ┌─ AVISO LEGAL ───────────────────────────────────────────────────────────┐
  │ • A ferramenta roda no seu computador. A autora não recebe nem vê nada.  │
  │ • Você é a única pessoa responsável por quem investiga, pelos dados que  │
  │   coleta e pelo que faz com o laudo. A autora não se responsabiliza     │
  │   pelo mau uso.                                                         │
  │ • Proibido usar pra perseguir, expor, humilhar, discriminar ou montar   │
  │   dossiê sobre alguém.                                                  │
  │ • Ler redes de forma automatizada pode violar os termos de uso delas.   │
  │ • O laudo é feito por IA, pode errar e não é prova nem parecer jurídico.│
  └─────────────────────────────────────────────────────────────────────────┘
  Texto completo: https://github.com/anagsoares/paspalho/blob/main/AVISO-LEGAL.md
AVISO
echo ""
if [ "$PASPALHO_ACEITO" = "sim" ]; then
  ok "Aviso legal aceito"
else
  printf '  Você leu e concorda com o aviso legal? Digite sim para continuar: '
  r=""
  if [ -r /dev/tty ]; then read -r r </dev/tty 2>/dev/null || r=""; fi
  case "$r" in
    [sS][iI][mM]) ok "Aviso legal aceito" ;;
    *) echo ""; erro "Instalação cancelada: é preciso concordar com o aviso legal." ;;
  esac
fi
echo ""

# 1. Mac + Chrome
[ "$(uname)" = "Darwin" ] || erro "Por enquanto a skill só funciona no Mac."
ok "Mac"
if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
  ok "Google Chrome"
else
  erro "Não achei o Google Chrome em Aplicativos. Instale em https://www.google.com/chrome/ e rode de novo."
fi

# 2. Claude Code (só avisa: a pessoa pode usar pela extensão do VS Code ou pelo app)
if command -v claude >/dev/null 2>&1; then
  ok "Claude Code"
else
  aviso "Não achei o comando 'claude' no Terminal. Se você usa o Claude Code pelo app ou pelo VS Code, tudo bem."
fi

# 3. uv
export PATH="$HOME/.local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
  ok "uv"
else
  echo ""
  echo "  Falta o uv, um programa pequeno que roda os scripts da skill (https://docs.astral.sh/uv/)."
  if perguntar "  Posso instalar o uv agora?"; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
    command -v uv >/dev/null 2>&1 || erro "O uv não instalou. Tente de novo ou peça ajuda ao Claude Code: 'instala o uv pra mim'."
    ok "uv instalado"
  else
    aviso "Sem o uv, Instagram, Threads, X e YouTube ficam de fora. Rode este instalador de novo quando quiser."
  fi
fi

# 4. A skill
# Git de verdade? (no Mac novo, /usr/bin/git é só um atalho que abre um pop-up da Apple)
tem_git() {
  command -v git >/dev/null 2>&1 || return 1
  [ "$(command -v git)" != "/usr/bin/git" ] || xcode-select -p >/dev/null 2>&1
}
baixar_pacote() {
  mkdir -p "$DESTINO"
  curl -fsSL "$REPO/archive/refs/heads/main.tar.gz" | tar -xz -C "$DESTINO" --strip-components 1 \
    || { rm -rf "$DESTINO"; erro "Não consegui baixar a skill. Confira a internet e rode de novo."; }
  date > "$DESTINO/.instalado-sem-git"
}

mkdir -p "$HOME/.claude/skills"
if [ -L "$DESTINO" ]; then
  ok "A skill já está instalada como atalho para $(readlink "$DESTINO"). Não mexi."
elif [ -d "$DESTINO/.git" ]; then
  git -C "$DESTINO" pull --ff-only -q || erro "Não consegui atualizar. Confira a internet e rode de novo."
  ok "Skill atualizada para a versão mais nova"
elif [ -f "$DESTINO/.instalado-sem-git" ]; then
  rm -rf "$DESTINO"; baixar_pacote
  ok "Skill atualizada para a versão mais nova"
elif [ -e "$DESTINO" ]; then
  erro "Já existe uma pasta $DESTINO que não veio deste instalador. Renomeie ou apague e rode de novo."
elif tem_git; then
  git clone -q --depth 1 "$REPO" "$DESTINO" || erro "Não consegui baixar a skill. Confira a internet e rode de novo."
  ok "Skill instalada em $DESTINO"
else
  baixar_pacote
  ok "Skill instalada em $DESTINO"
fi

echo ""
echo "Pronto! Agora:"
echo "  1. Feche e abra o Claude Code de novo."
echo "  2. Digite /paspalho"
echo "  3. Na primeira vez, um Chrome separado abre pedindo os logins das redes."
echo "     Use contas criadas só pra investigação (o README explica por quê)."
echo ""
