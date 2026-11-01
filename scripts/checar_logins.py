#!/usr/bin/env python3
"""Diz em quais redes o Chrome da investigação (porta 9333) está logado.
Olha só o NOME dos cookies de sessão, nunca o valor.

Uso:
  uv run -q --with websocket-client python checar_logins.py
"""
import json, os, sys, urllib.request

import websocket

REDES = {
    "Instagram": ("instagram.com", "sessionid"),
    "Threads": ("threads.com", "sessionid"),
    "X": ("x.com", "auth_token"),
    "LinkedIn": ("linkedin.com", "li_at"),
}


def main():
    try:
        porta = os.environ.get("PASPALHO_PORTA") or "9333"
        ver = json.load(urllib.request.urlopen(f"http://localhost:{porta}/json/version", timeout=3))
    except Exception:
        sys.exit("O Chrome da investigação não está aberto. Rode: sh scripts/abrir_chrome.sh")
    ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=20, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": "Storage.getCookies"}))
    cookies = json.loads(ws.recv())["result"]["cookies"]
    ws.close()
    faltam = []
    for rede, (dom, nome) in REDES.items():
        ok = any(c["name"] == nome and dom in c["domain"] for c in cookies)
        print(f"{'✓' if ok else '✗'} {rede}")
        if not ok:
            faltam.append(rede)
    if faltam:
        print("Falta logar em: " + ", ".join(faltam) + ". Rode `sh scripts/abrir_chrome.sh --logins` e entre nessas contas.")


if __name__ == "__main__":
    main()
