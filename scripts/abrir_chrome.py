#!/usr/bin/env python3
"""Abre o "Chrome da investigação": um Chrome separado do seu, com perfil próprio,
que a skill controla pela porta 9333. Na primeira vez, abre as telas de login de
Instagram, Threads, X e LinkedIn. Os logins ficam salvos nesse perfil.
Funciona no Mac e no Windows.

Uso:
  uv run -q python abrir_chrome.py            # abre (ou confirma que já está aberto)
  uv run -q python abrir_chrome.py --logins   # abre as telas de login de novo

Dica: use contas criadas só pra isso (veja o README).
"""
import os, platform, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

PORTA = os.environ.get("PASPALHO_PORTA") or "9333"
PERFIL = Path.home() / ".claude" / "paspalho" / "chrome"
LOGINS = ["https://www.instagram.com/accounts/login/", "https://www.threads.com/login",
          "https://x.com/i/flow/login", "https://www.linkedin.com/login"]


def achar_chrome():
    sistema = platform.system()
    if sistema == "Darwin":
        candidatos = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                      str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome")]
    elif sistema == "Windows":
        candidatos = [str(Path(os.environ[v]) / "Google/Chrome/Application/chrome.exe")
                      for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA") if os.environ.get(v)]
    else:
        candidatos = [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium")]
    return next((c for c in candidatos if c and Path(c).is_file()), None)


def no_ar(timeout=2):
    try:
        urllib.request.urlopen(f"http://localhost:{PORTA}/json/version", timeout=timeout)
        return True
    except Exception:
        return False


def main():
    logins = "--logins" in sys.argv
    if no_ar():
        print(f"Chrome da investigação já está aberto (porta {PORTA}).")
        if logins:
            for u in LOGINS:
                urllib.request.urlopen(urllib.request.Request(f"http://localhost:{PORTA}/json/new?{u}", method="PUT"), timeout=5)
            print("Abri as telas de login.")
        return

    chrome = achar_chrome()
    if not chrome:
        sys.exit("Não achei o Google Chrome. Instale em https://www.google.com/chrome/ e rode de novo.")

    PERFIL.mkdir(parents=True, exist_ok=True)
    primeira = not any(PERFIL.iterdir())
    cmd = [chrome, f"--remote-debugging-port={PORTA}", f"--user-data-dir={PERFIL}",
           "--no-first-run", "--no-default-browser-check"]
    # sempre com uma janela: sem nenhuma, o Chrome não responde a alguns comandos e a rolagem não carrega
    cmd += LOGINS if (primeira or logins) else ["about:blank"]

    # solto do terminal: o Chrome continua aberto quando o comando termina
    extra = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
             if platform.system() == "Windows" else {"start_new_session": True})
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **extra)
    if primeira or logins:
        print("Abri o Chrome da investigação com as telas de login de Instagram, Threads, X e LinkedIn.")
    else:
        print(f"Abri o Chrome da investigação (porta {PORTA}).")

    for _ in range(15):
        if no_ar(1):
            return
        time.sleep(1)
    sys.exit(f"O Chrome abriu mas a porta {PORTA} não respondeu. Feche esse Chrome e rode de novo.")


if __name__ == "__main__":
    main()
