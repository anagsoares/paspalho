# Instala (ou atualiza) a skill /paspalho do Claude Code no Windows.
#
# Uso, no PowerShell:
#   irm https://raw.githubusercontent.com/anagsoares/paspalho/main/instalar.ps1 | iex
#
# O que ele faz:
#   0. mostra o aviso legal e só continua com "sim" (ou $env:PASPALHO_ACEITO = "sim");
#   1. confere se tem o Google Chrome;
#   2. instala o uv (programa que roda os scripts), se faltar, depois de perguntar;
#   3. baixa a skill em %USERPROFILE%\.claude\skills\paspalho (ou atualiza, se já estiver lá).
# Não pede senha de administrador, não mexe no seu Chrome de sempre e não instala nada fora da sua pasta.

$ErrorActionPreference = "Stop"
$Repo = if ($env:PASPALHO_REPO) { $env:PASPALHO_REPO } else { "https://github.com/anagsoares/paspalho" }  # variável só pra teste
$Destino = Join-Path $HOME ".claude\skills\paspalho"

function Ok($t)    { Write-Host "  [ok] $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Erro($t)  { Write-Host "  [x]  $t" -ForegroundColor Red; throw "instalação interrompida" }

function Instalar {
  Write-Host ""
  Write-Host "Instalando o Paspalhômetro (skill /paspalho do Claude Code)"
  Write-Host ""

  # 0. Aviso legal: só segue com "sim" explícito
  Write-Host "  AVISO LEGAL" -ForegroundColor Cyan
  Write-Host "  - A ferramenta roda no seu computador. A autora não recebe nem vê nada."
  Write-Host "  - Você é a única pessoa responsável por quem investiga, pelos dados que coleta"
  Write-Host "    e pelo que faz com o laudo. A autora não se responsabiliza pelo mau uso."
  Write-Host "  - Proibido usar pra perseguir, expor, humilhar, discriminar ou montar dossiê sobre alguém."
  Write-Host "  - Ler redes de forma automatizada pode violar os termos de uso delas."
  Write-Host "  - O laudo é feito por IA, pode errar e não é prova nem parecer jurídico."
  Write-Host "  Texto completo: https://github.com/anagsoares/paspalho/blob/main/AVISO-LEGAL.md"
  Write-Host ""
  if ($env:PASPALHO_ACEITO -eq "sim") {
    Ok "Aviso legal aceito"
  } else {
    $r = ""
    try { $r = Read-Host "  Você leu e concorda com o aviso legal? Digite sim para continuar" } catch { $r = "" }
    if ($r -match '^\s*sim\s*$') { Ok "Aviso legal aceito" }
    else { Erro "Instalação cancelada: é preciso concordar com o aviso legal." }
  }
  Write-Host ""

  # 1. Chrome
  $chromes = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
               "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
               "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
  if ($chromes | Where-Object { $_ -and (Test-Path $_) }) { Ok "Google Chrome" }
  else { Erro "Não achei o Google Chrome. Instale em https://www.google.com/chrome/ e rode de novo." }

  # 2. Claude Code (só avisa: a pessoa pode usar pelo app ou pelo VS Code)
  if (Get-Command claude -ErrorAction SilentlyContinue) { Ok "Claude Code" }
  else { Aviso "Não achei o comando 'claude'. Se você usa o Claude Code pelo app ou pelo VS Code, tudo bem." }

  # 3. uv
  $env:Path = "$HOME\.local\bin;$env:Path"
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    Ok "uv"
  } else {
    Write-Host ""
    Write-Host "  Falta o uv, um programa pequeno que roda os scripts da skill (https://docs.astral.sh/uv/)."
    $r = "s"
    try { $r = Read-Host "  Posso instalar o uv agora? [S/n]" } catch { $r = "s" }
    if ($r -notmatch '^[nN]') {
      powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
      $env:Path = "$HOME\.local\bin;$env:Path"
      if (Get-Command uv -ErrorAction SilentlyContinue) { Ok "uv instalado" }
      else { Erro "O uv não instalou. Tente de novo ou peça ajuda ao Claude Code: 'instala o uv pra mim'." }
    } else {
      Aviso "Sem o uv, a skill não roda. Rode este instalador de novo quando quiser."
    }
  }

  # 4. A skill
  New-Item -ItemType Directory -Force -Path (Join-Path $HOME ".claude\skills") | Out-Null
  $item = Get-Item $Destino -ErrorAction SilentlyContinue
  $temGit = [bool](Get-Command git -ErrorAction SilentlyContinue)
  if ($item -and $item.LinkType) {
    Ok "A skill já está instalada como atalho para $($item.Target). Não mexi."
  } elseif ($item -and (Test-Path (Join-Path $Destino ".git"))) {
    git -C $Destino pull --ff-only -q
    if ($LASTEXITCODE -ne 0) { Erro "Não consegui atualizar. Confira a internet e rode de novo." }
    Ok "Skill atualizada para a versão mais nova"
  } elseif ($item -and (Test-Path (Join-Path $Destino ".instalado-sem-git"))) {
    Remove-Item -Recurse -Force $Destino
    Baixar-Pacote
    Ok "Skill atualizada para a versão mais nova"
  } elseif ($item) {
    Erro "Já existe uma pasta $Destino que não veio deste instalador. Renomeie ou apague e rode de novo."
  } elseif ($temGit) {
    git clone -q --depth 1 $Repo $Destino
    if ($LASTEXITCODE -ne 0) { Erro "Não consegui baixar a skill. Confira a internet e rode de novo." }
    Ok "Skill instalada em $Destino"
  } else {
    Baixar-Pacote
    Ok "Skill instalada em $Destino"
  }

  Write-Host ""
  Write-Host "Pronto! Agora:"
  Write-Host "  1. Feche e abra o Claude Code de novo."
  Write-Host "  2. Digite /paspalho"
  Write-Host "  3. Na primeira vez, um Chrome separado abre pedindo os logins das redes."
  Write-Host "     Use contas criadas só pra investigação (o README explica por quê)."
  Write-Host ""
}

function Baixar-Pacote {
  # Sem git: baixa o .zip da versão atual
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("paspalho-" + [guid]::NewGuid())
  try {
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp "paspalho.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "$Repo/archive/refs/heads/main.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $pasta = Get-ChildItem $tmp -Directory | Select-Object -First 1
    Move-Item $pasta.FullName $Destino
    Set-Content -Path (Join-Path $Destino ".instalado-sem-git") -Value (Get-Date)
  } catch {
    Erro "Não consegui baixar a skill. Confira a internet e rode de novo."
  } finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
  }
}

# Dentro de uma função: com "irm | iex", um erro não fecha a janela do PowerShell da pessoa
try { Instalar } catch { if ($_.Exception.Message -ne "instalação interrompida") { Write-Host "  [x]  $($_.Exception.Message)" -ForegroundColor Red } }
