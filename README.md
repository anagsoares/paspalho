# 🤡 Paspalhômetro

Uma skill pro **Claude Code** que investiga comentários agressivos nas redes sociais e monta um laudo visual, com termômetro de paspalhice.

Ela responde duas perguntas:

- **"Esse perfil é agressivo?"** Você coloca o nome e/ou as redes de alguém, e ela levanta o que essa pessoa escreve por aí. Onde encontra agressividade, aprofunda: naquela rede, naquela conta, naquele tema.
- **"Essa pessoa fala mal de mim?"** Ela procura quem ofende, debocha ou rebaixa você no Instagram, Threads, X, LinkedIn, YouTube e na web.

No fim aparece o laudo: quantos comentários são graves e quantos são deboche, um termômetro que vai de "Gente boa" a "PASPALHO-MOR", uma tabela com o dia da semana e a hora de cada comentário (com os xingamentos em negrito), o padrão da pessoa, quem ela mais ataca e considerações.

> **Não é programador(a)? Não tem problema.** Você não precisa entender nada de código. Abra o Claude Code e diga:
>
> *"Quero instalar a skill Paspalhômetro deste link: https://github.com/anagsoares/paspalho. Me guia passo a passo, eu não sou programador(a)."*
>
> O Claude Code lê as instruções deste repositório e faz com você.

---

## ⚠️ Leia antes de usar

**Use contas criadas só pra isso.** Pra ler o Instagram, o Threads, o X e o LinkedIn, a skill navega com uma conta logada, como uma pessoa faria, só que de forma automática. Isso vai contra os termos de uso dessas redes, e quem usa muito pode ter a conta limitada ou bloqueada. Por isso:

- crie contas novas, só pra investigação, em cada rede;
- não use a sua conta pessoal nem a da sua empresa;
- não rode dezenas de investigações seguidas.

**O que a skill faz e o que ela não faz:**

- Lê só o que é público, que qualquer pessoa logada veria.
- O laudo mostra o que a pessoa escreveu, onde e contra quem. Não busca endereço, família, telefone nem vida pessoal, e não tenta descobrir quem está por trás de perfis anônimos.
- Processos judiciais aparecem só como resultado de busca pelo nome, com aviso: nome igual não quer dizer que é a mesma pessoa.
- Ela não responde, não denuncia e não bloqueia ninguém. A decisão do que fazer é sua.
- O laudo não é parecer jurídico. Se algum comentário for virar caso, guarde a prova logo (print com o link e a data aparecendo, ou ata notarial), porque comentário pode ser apagado.

---

## Como funciona

```
 Você preenche o            O Claude Code             Um Chrome separado,         O laudo aparece
 Paspalhômetro       ──▶    recebe o pedido     ──▶   logado nas contas de   ──▶  na mesma página
 (no seu navegador)         e planeja a busca         investigação, lê as         e fica salvo em
                                                       redes                       Downloads/Paspalho
```

1. **O formulário.** Quando você digita `/paspalho`, o Claude Code abre o Paspalhômetro no seu navegador. É uma página que roda só no seu computador (endereço `localhost`).
2. **O pedido.** Quando você clica em **Investigar paspalho**, o pedido volta pro Claude Code, que decide onde procurar.
3. **A coleta.** O Claude Code usa um **Chrome separado**, só da investigação, com perfil próprio. Ele abre as páginas das redes em segundo plano e copia os comentários públicos. Você vê na página, ao vivo, onde ele está procurando.
4. **A triagem.** O Claude lê cada comentário e separa em três tipos:
   - 🚨 **grave:** xingamento, ameaça, acusação de crime sem prova, misoginia, ofensa racial;
   - 🤡 **paspalho:** deboche, rebaixamento, ataque à pessoa em vez da ideia;
   - 🧐 **crítica:** discorda com argumento. Não conta como paspalhada.
5. **O aprofundamento.** Se aparece agressividade numa rede, numa conta ou num tema, ele cava mais ali (até 3 rodadas).
6. **O laudo.** O termômetro soma os achados (grave vale 2, paspalhada vale 1, o que tem mais de 5 anos vale metade) e dá o nível:

   | Nível | Quer dizer |
   |---|---|
   | Gente boa | Nenhum padrão de agressividade no que foi lido |
   | Resmungão | Escorrega às vezes, sem padrão de ataque |
   | Paspalho | Rebaixa os outros com frequência |
   | Paspalhão | Agressividade é parte do jeito de conversar |
   | PASPALHO-MOR | Ataca pessoas de forma recorrente e grave |

   Todo comentário do laudo tem o link pra você conferir o original. A skill nunca inventa nem reescreve comentário.

---

## O que você precisa

- Um **Mac** com o **Google Chrome** instalado.
- O **Claude Code** instalado e funcionando ([como instalar](https://docs.claude.com/pt/docs/claude-code/overview)). Pode ser pelo Terminal, pelo app ou pela extensão do VS Code.

O instalador cuida do resto.

## Como instalar

**Passo 1.** Abra o **Terminal** do Mac (aperte `⌘ + espaço`, digite *Terminal* e dê Enter).

**Passo 2.** Copie a linha abaixo, cole no Terminal e aperte Enter:

```
curl -fsSL https://raw.githubusercontent.com/anagsoares/paspalho/main/instalar.sh | sh
```

O instalador:
- confere se você tem Mac e Chrome;
- instala o **uv** (um programa pequeno que roda os scripts da skill), se faltar. Ele pergunta antes;
- coloca a skill na pasta do Claude Code (`~/.claude/skills/paspalho`).

Ele não pede senha e não mexe no seu Chrome de sempre.

**Passo 3.** Feche e abra o Claude Code de novo. Pronto.

<details>
<summary>Prefere instalar pelo git, sem o instalador?</summary>

```
git clone https://github.com/anagsoares/paspalho ~/.claude/skills/paspalho
```

E instale o uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
</details>

## Primeira vez: logar as contas de investigação

Na primeira vez que você usar, a skill abre um **Chrome separado**, só pra investigação. Ele tem um perfil próprio e não mexe no seu Chrome de sempre.

Nesse Chrome abrem quatro telas de login: **Instagram, Threads, X e LinkedIn**. Entre com as contas de investigação que você criou. Os logins ficam salvos nesse Chrome, então você só faz isso uma vez. Quem digita a senha é sempre você: o Claude nunca vê nem digita senha.

Se pular alguma rede, tudo bem: ela só fica de fora do laudo.

## Como usar

No Claude Code, digite:

```
/paspalho
```

O **Paspalhômetro** abre no seu navegador. Na primeira vez ele mostra um laudo de exemplo, com perfis inventados, só pra você ver como fica. Preencha:

1. **Quem você quer investigar?** O nome completo e/ou os links e @ das redes da pessoa, separados por vírgula ou ponto e vírgula. Exemplo: `Fulano de Tal; @fulano; linkedin.com/in/fulano`
2. **Quer saber se essa pessoa já xingou você?** Se quiser, coloque as suas redes. Em branco, a busca é geral.
3. Marque se quer **buscar processos judiciais públicos** e se quer a **investigação completa** (mais buscas, demora mais).

Clique em **Investigar paspalho**. Embaixo do botão aparece onde o Claude está procurando, e a tabela vai se montando enquanto ele acha. No fim, o laudo completo aparece na mesma página. Mudou de ideia? Clique em **Parar pesquisa**.

Também dá pra pedir direto no chat, sem o formulário:

> /paspalho investiga o @fulano

## Onde fica o laudo

Na sua pasta **Downloads**, dentro de `Paspalho/<nome do perfil>/`. Cada investigação gera um arquivo `.html`, que abre no navegador, e um `.json` com os dados. Quando você investiga o mesmo perfil de novo, os comentários que não estavam no laudo anterior aparecem marcados como **NOVO**.

## Privacidade e segurança

- **Tudo fica no seu Mac.** Os laudos, os pedidos e o Chrome da investigação ficam no seu computador. Nada vai pra um servidor da skill (ela não tem servidor). Os textos coletados passam pelo Claude, como qualquer conversa sua no Claude Code.
- **O Paspalhômetro só aceita pedido dele mesmo.** A página roda em `localhost` e recusa pedido vindo de qualquer outro site aberto no seu navegador.
- **O Chrome da investigação guarda os logins** das contas de investigação, na pasta `~/.claude/paspalho/chrome`. Quem usa o seu Mac consegue entrar nessas contas. Mais um motivo pra não usar sua conta pessoal.
- **O código é aberto.** Dá pra ler tudo o que a skill faz neste repositório.

## Atualizar e desinstalar

**Atualizar:** rode de novo a linha de instalação. Ela baixa a versão mais nova.

**Desinstalar:** cole no Terminal:

```
rm -rf ~/.claude/skills/paspalho ~/.claude/paspalho
```

Isso apaga a skill, o histórico de pedidos e o Chrome da investigação (com os logins). Os laudos em `Downloads/Paspalho` continuam lá até você apagar.

## Perguntas comuns

**Meu Chrome normal não abre enquanto a investigação roda.**
Clicar no ícone do Chrome traz o Chrome da investigação pra frente. Pra abrir o seu, cole no Terminal: `open -na "Google Chrome"`.

**Apareceu "precisa login" numa rede.**
Peça pro Claude Code: *"abre as telas de login do paspalho"*. Entre na rede que faltou, naquele Chrome separado.

**A página diz que o pedido está na fila, mas nada acontece.**
Volte na conversa do Claude Code e diga: *"pega o pedido do paspalhômetro"*.

**O laudo diz que não achou nada. Quer dizer que a pessoa é tranquila?**
Quer dizer que não achou nada no que conseguiu ler. O laudo sempre mostra quanto foi lido em cada rede. O Instagram, por exemplo, não lista os comentários que uma pessoa fez: a skill procura nos perfis onde ela provavelmente comenta.

**A pessoa me bloqueou (ou eu bloqueei ela). E agora?**
Bloqueio esconde o perfil nos dois sentidos. É mais um motivo pra usar uma conta de investigação, que não tem bloqueio com ninguém.

**Funciona no Windows?**
Por enquanto, só no Mac.

---

Feito por [Ana G. Soares](https://instagram.com/ana.gsoares) · [UNIAGIL](https://uniagil.com) · Licença [MIT](LICENSE)
