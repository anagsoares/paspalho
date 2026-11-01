# paspalho — notas pra quem mexe no código

Skill do Claude Code (`SKILL.md` é a entrada). Instalada em `~/.claude/skills/paspalho/`.

## Se a pessoa pediu ajuda pra instalar

Quem usa este repositório costuma **não ser programador**. Conduza pela mão, um passo por vez,
sem jargão, e faça você o que der (rodar comando, conferir resultado):

1. Confira: Mac ou Windows, e Google Chrome instalado. Sem Chrome, mande baixar em
   google.com/chrome e espere.
2. **Antes de instalar, mostre à pessoa o resumo do `AVISO-LEGAL.md`** (responsabilidade dela,
   usos proibidos, termos das redes, laudo de IA não é prova) e pergunte se ela concorda. Só
   com "sim" dela, rode o instalador com `PASPALHO_ACEITO=sim` na frente do `sh`
   (sem teclado, o instalador cancela sozinho). Nunca preencha o aceite por conta própria.
3. Rode o instalador. **Mac:** `curl -fsSL https://raw.githubusercontent.com/anagsoares/paspalho/main/instalar.sh | PASPALHO_ACEITO=sim sh`.
   **Windows** (PowerShell): `$env:PASPALHO_ACEITO="sim"; irm https://raw.githubusercontent.com/anagsoares/paspalho/main/instalar.ps1 | iex`.
   Ele instala o `uv` se faltar (pergunta antes) e clona em `~/.claude/skills/paspalho`.
   Se você não tem terminal interativo, instale o uv antes (Mac: `curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows: `irm https://astral.sh/uv/install.ps1 | iex`),
   porque sem teclado a pergunta do uv assume "sim".
4. Peça pra pessoa fechar e abrir o Claude Code, e digitar `/paspalho`.
5. Na primeira vez abre o Chrome da investigação com 4 logins. **Recomende contas criadas só
   pra isso** (ler rede automatizado fere os termos de uso). Login é ela quem faz, nunca você.
6. Atualizar = rodar o instalador de novo. Desinstalar = apagar as pastas `~/.claude/skills/paspalho` e `~/.claude/paspalho`
   (no Windows, `%USERPROFILE%\.claude\...`).

## Regras do repositório (é público)

- **Nunca** colocar no repositório texto, @, nome, URL ou data de caso investigado de verdade:
  nem no exemplo da página, nem nos critérios, nem no léxico, nem em mensagem de commit.
  Exemplo é sempre inventado, com `@perfil_a`, `Fulano de Tal` etc. Laudos ficam em
  `~/Downloads/Paspalho/` e pedidos em `~/.claude/paspalho/`, ambos fora do repo.
- Nada de credencial, caminho `/Users/<nome>`, e-mail pessoal ou ID de artefato.
- O servidor local (`paspalhometro_server.py`) só aceita pedido da própria página: confere
  `Host` e `Origin`, exige `Content-Type: application/json` e repassa só os campos do
  formulário (`alvo`, `vitima`, `processos`, `completa`). Não afrouxar: o pedido vira trabalho
  pro Claude Code, e outro site aberto no navegador conseguiria mandar instruções.
- `AVISO-LEGAL.md` é a proteção jurídica da autora: README, instalador (aceite com "sim",
  padrão = cancelar) e rodapé da página apontam pra ele. Não remover esses pontos.
- Link no laudo só sai se for `http(s)://` (`link()` na página, `L()` no `render_report.py`).

## Peças

- `scripts/abrir_chrome.py` (acha o Chrome no Mac e no Windows), `scripts/checar_logins.py`: Chrome da investigação (perfil em `~/.claude/paspalho/chrome`, porta 9333).
- Coletores (todos gravam o mesmo JSONL): `ig_comments.py`, `ig_following.py`, `threads_replies.py`, `x_search.py`, `yt_comments.py` (usa `yt-dlp`; sem ele instalado, roda via `uvx yt-dlp`).
- `instalar.sh` (Mac) e `instalar.ps1` (Windows, ainda não testado em máquina real): instaladores de quem baixa (confere Mac/Chrome, instala uv, clona ou atualiza). Não mexe se `~/.claude/skills/paspalho` for symlink. `PASPALHO_REPO=file:///caminho` testa sem GitHub.
- Paspalhômetro local: `paspalhometro_server.py` serve `pagina/index.html`; `esperar_pedido.py` pega o pedido; `progresso.py` escreve o andamento que a página lê.
- Laudo: `render_report.py` (HTML simples + JSON em `~/Downloads/Paspalho/`). O laudo visual é a própria página do Paspalhômetro lendo o JSON.
- `pagina/index.html` **só funciona servida pelo `paspalhometro_server.py`**. Não publicar como artefato do
  claude.ai: o modo artefato (busca pelo Firecrawl) foi removido em 2026-11-01 porque não funciona direito.

## Testar do zero

Numa máquina que já tem Chrome de debug na 9333: abra o Claude Code com
`PASPALHO_PORTA=9334 claude` e rode `/paspalho`. Sobe um Chrome novo, com perfil limpo em
`~/.claude/paspalho/chrome`, pedindo os 4 logins, igual a quem acabou de instalar.

## Armadilhas conhecidas

- **Instagram:** `fetch('/api/v1/...')` dentro da aba dá 429/404 mesmo logado. Funciona capturar o que a página carrega: 1ª página de comentários vem embutida no HTML (`script[type="application/json"]`); as seguintes vêm por GraphQL ao rolar, com gatilho no spinner `[aria-label="Loading..."]` + mouse wheel.
- **Aba em segundo plano** precisa de `Emulation.setFocusEmulationEnabled`, senão não carrega mais itens. Janela minimizada pausa a rolagem infinita.
- **Página de perfil do Instagram também carrega o feed de quem está logado:** filtrar posts pelo dono do perfil (já feito em `user_posts`).
- **Threads tira da página os itens antigos ao rolar:** capturar o JSON (`thread_items`), nunca o texto da página.
- **CDP via websocket** precisa de `suppress_origin=True` (senão 403).
- **Chrome headless com cookies copiados** é barrado pelo controle de permissões do Claude Code como burla anti-robô. Não usar.
- **Matar processo:** sempre pelo PID da porta. `pkill -f chrome` casa com o próprio Claude Code (flag `--no-chrome`).
- **X:** a busca (`from:`) esconde contas que a conta logada bloqueou. Perfil bloqueado ainda abre em `x.com/<handle>/with_replies` clicando em "Ver os posts".
- **Vigia de pedidos:** `esperar_pedido.py` grava `~/.claude/paspalho/vigia` a cada 2 s; o servidor usa isso pra dizer na página se o pedido está na fila sem ninguém ouvindo, ou se foi pego e não começou.
- **Windows:** todo script lê, grava e imprime em UTF-8 explícito (senão acento e emoji quebram no
  Windows); rodar sempre com `uv run -q python` (`python3` não existe lá). `.gitattributes` força
  LF, senão o Git do Windows converte as quebras de linha. `progresso.py` tenta de novo se o arquivo
  estiver em uso (no Windows, trocar arquivo aberto pelo servidor dá erro por um instante).
  Desligar o servidor = `paspalhometro_server.py --parar` (PID gravado), nada de `lsof`/`pkill`.
