#!/usr/bin/env python3
"""Paspalhômetro local: o formulário roda no navegador da pessoa e o trabalho volta
pro Claude Code.

Fluxo:
  1. Claude Code sobe este servidor (em background) e abre http://localhost:<porta>/
  2. A pessoa preenche e clica "Investigar paspalho" → POST /api/pedido grava
     <dados>/pedidos/<id>.json
  3. Claude Code, que está esperando esse arquivo (esperar_pedido.py), roda a skill e
     escreve o andamento com progresso.py → <dados>/andamento/<id>.json
  4. A página consulta GET /api/status?id=<id> a cada 2 s, mostra as etapas, monta a
     tabela com as linhas parciais e, no fim, o laudo completo.

Uso:
  uv run -q python paspalhometro_server.py [--porta 8766]
  uv run -q python paspalhometro_server.py --parar

Só escuta em 127.0.0.1. Sem dependências fora da biblioteca padrão.

Segurança: o pedido vira trabalho pro Claude Code, então só aceita o que vem da própria
página. Outro site aberto no navegador não consegue mandar pedido (Origin e Host são
conferidos, POST exige JSON) e o pedido só leva os campos do formulário, com tamanho limitado.
"""
import argparse, json, os, secrets, signal, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

for s in (sys.stdout, sys.stderr):
    s.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
PAGINA = AQUI.parent / "pagina" / "index.html"
DADOS = Path.home() / ".claude" / "paspalho"
CAMPOS_TEXTO = {"alvo": 1000, "vitima": 1000}  # campo: tamanho máximo
CAMPOS_SIM_NAO = ("processos", "completa")


def aguardando(pid):
    """O que dizer enquanto o Claude Code ainda não mandou nenhuma etapa."""
    agora = time.time()
    na_fila = DADOS / "pedidos" / f"{pid}.json"
    lido = DADOS / "pedidos" / "lidos" / f"{pid}.json"
    vigia = DADOS / "vigia"
    try:
        ouvindo = vigia.exists() and agora - int(vigia.read_text(encoding="utf-8").strip() or 0) < 10
    except ValueError:
        ouvindo = False
    if na_fila.exists():
        if ouvindo:
            return [{"txt": "Pedido enviado. O Claude Code vai pegar em instantes…", "estado": "run", "det": ""}]
        return [{"txt": "Pedido na fila, mas o Claude Code não está esperando pedidos", "estado": "err",
                 "det": "volte na conversa do Claude Code e diga: pega o pedido do paspalhômetro"}]
    if lido.exists():
        if agora - lido.stat().st_mtime < 60:
            return [{"txt": "O Claude Code pegou o pedido e está começando…", "estado": "run", "det": ""}]
        return [{"txt": "O Claude Code pegou o pedido mas ainda não começou", "estado": "err",
                 "det": "a conversa pode ter sido interrompida: volte no Claude Code e diga: roda o pedido do paspalhômetro"}]
    return []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _local(self):
        """Host e Origin têm que ser este servidor (barra outro site e DNS rebinding)."""
        porta = self.server.server_address[1]
        validos = {f"localhost:{porta}", f"127.0.0.1:{porta}"}
        if self.headers.get("Host", "") not in validos:
            return False
        origem = self.headers.get("Origin")
        return origem is None or origem in {f"http://{v}" for v in validos}

    def do_GET(self):
        if not self._local():
            return self._send(403, {"erro": "acesso só pela página do Paspalhômetro"})
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/ultimo":  # último laudo terminado, pra página reabrir com ele
            fins = sorted((DADOS / "andamento").glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            for f in fins:
                try:
                    st = json.loads(f.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if st.get("fim") and st.get("resultado"):
                    return self._send(200, {"id": f.stem, "resultado": st["resultado"]})
            return self._send(200, {})
        if u.path == "/api/status":
            pid = (parse_qs(u.query).get("id") or [""])[0]
            if not pid.isalnum():
                return self._send(400, {"erro": "id inválido"})
            f = DADOS / "andamento" / f"{pid}.json"
            if not f.exists():
                return self._send(200, {"etapas": aguardando(pid), "linhas": [], "fim": False})
            try:
                return self._send(200, json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:  # arquivo no meio da escrita
                return self._send(200, {"etapas": [], "linhas": [], "fim": False, "parcial": True})
        return self._send(404, {"erro": "não encontrado"})

    def do_POST(self):
        # POST de outro site sempre traz Origin: sem Origin igual ao nosso, não entra
        if not self._local() or not self.headers.get("Origin"):
            return self._send(403, {"erro": "acesso só pela página do Paspalhômetro"})
        caminho = urlparse(self.path).path
        if caminho == "/api/cancelar":  # botão "Parar pesquisa"
            pid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            if not pid.isalnum():
                return self._send(400, {"erro": "id inválido"})
            (DADOS / "cancelados").mkdir(parents=True, exist_ok=True)
            (DADOS / "cancelados" / pid).write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
            na_fila = DADOS / "pedidos" / f"{pid}.json"
            if na_fila.exists():  # ainda não pego: sai da fila
                na_fila.unlink()
            return self._send(200, {"ok": True})
        if caminho != "/api/pedido":
            return self._send(404, {"erro": "não encontrado"})
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self._send(415, {"erro": "o pedido tem que ser JSON"})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            bruto = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"erro": "JSON inválido"})
        if not isinstance(bruto, dict):
            return self._send(400, {"erro": "JSON inválido"})
        # só os campos do formulário seguem pro Claude Code
        pedido = {k: str(bruto.get(k) or "").strip()[:lim] for k, lim in CAMPOS_TEXTO.items()}
        pedido.update({k: bruto.get(k) is True for k in CAMPOS_SIM_NAO})
        if not pedido["alvo"]:
            return self._send(400, {"erro": "Preencha quem você quer investigar."})
        pid = secrets.token_hex(4)
        pedido.update({"id": pid, "recebido_em": time.strftime("%Y-%m-%d %H:%M:%S")})
        (DADOS / "pedidos").mkdir(parents=True, exist_ok=True)
        (DADOS / "pedidos" / f"{pid}.json").write_text(json.dumps(pedido, ensure_ascii=False, indent=1), encoding="utf-8")
        return self._send(200, {"id": pid})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8766)
    ap.add_argument("--parar", action="store_true", help="desliga o servidor que está no ar")
    a = ap.parse_args()
    pidf = DADOS / "servidor.pid"
    if a.parar:  # pelo PID que o próprio servidor gravou: igual no Mac e no Windows
        try:
            os.kill(int(pidf.read_text(encoding="utf-8")), signal.SIGTERM)
            print("Paspalhômetro desligado.")
        except (OSError, ValueError):
            print("O Paspalhômetro não estava no ar.")
        pidf.unlink(missing_ok=True)
        return
    for d in ("pedidos", "andamento"):
        (DADOS / d).mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.porta), H)
    pidf.write_text(str(os.getpid()), encoding="utf-8")
    print(f"Paspalhômetro em http://localhost:{a.porta}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
