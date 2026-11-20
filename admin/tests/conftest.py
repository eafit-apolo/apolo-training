"""Dobles para probar apolo-training-admin sin root, sin Slurm y sin la API.

- Los comandos del sistema son tests/bin/falso, enlazado con cada nombre en un
  PATH temporal: registran cada llamada y responden lo que pida la prueba.
- La plataforma es un servidor HTTP local (127.0.0.1) que guarda los pedidos y
  responde, en orden, lo que la prueba le encole (201 si no hay nada).
- Lo que consulta /etc/passwd y /etc/group se reemplaza con monkeypatch.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

PRUEBAS = os.path.dirname(os.path.abspath(__file__))
ADMIN = os.path.dirname(PRUEBAS)
FALSO = os.path.join(PRUEBAS, "bin", "falso")
COMANDOS = (
    "useradd",
    "userdel",
    "usermod",
    "chpasswd",
    "chage",
    "sacctmgr",
    "scancel",
    "pkill",
    "runuser",
    "getent",
)
TOKEN = "token-de-prueba"

sys.path.insert(0, ADMIN)

import apolo_training_admin as admin  # noqa: E402


class Comandos:
    def __init__(self, log):
        self.log = log

    def llamadas(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(linea) for linea in f]

    def nombres(self):
        """Comando y subcomando, p. ej. 'sacctmgr add' o 'useradd'."""
        resultado = []
        for llamada in self.llamadas():
            cmd = llamada["cmd"]
            if cmd[0] == "sacctmgr":
                resultado.append(f"sacctmgr {cmd[2]}")
            else:
                resultado.append(cmd[0])
        return resultado


@pytest.fixture
def comandos(tmp_path, monkeypatch):
    carpeta = tmp_path / "bin"
    carpeta.mkdir()
    for nombre in COMANDOS:
        os.symlink(FALSO, carpeta / nombre)
    monkeypatch.setenv("PATH", f"{carpeta}{os.pathsep}{os.environ['PATH']}")
    log = tmp_path / "comandos.log"
    monkeypatch.setenv("FALSO_LOG", str(log))
    return Comandos(str(log))


class Plataforma:
    def __init__(self):
        self.pedidos = []
        self.respuestas = []

    def responder(self, estado, cuerpo=None):
        self.respuestas.append((estado, cuerpo))


def _manejador(plataforma):
    class Manejador(BaseHTTPRequestHandler):
        def _atender(self):
            largo = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(largo) or b"null")
            plataforma.pedidos.append(
                {
                    "metodo": self.command,
                    "ruta": self.path,
                    "auth": self.headers.get("Authorization"),
                    "cuerpo": cuerpo,
                }
            )
            estado, respuesta = (
                plataforma.respuestas.pop(0) if plataforma.respuestas else (201, {})
            )
            datos = json.dumps(respuesta).encode()
            self.send_response(estado)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        do_POST = _atender
        do_PATCH = _atender

        def log_message(self, *args):
            pass

    return Manejador


@pytest.fixture
def plataforma():
    p = Plataforma()
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), _manejador(p))
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    p.url = f"http://127.0.0.1:{servidor.server_address[1]}/api"
    yield p
    servidor.shutdown()
    servidor.server_close()


class Rutas:
    pass


@pytest.fixture
def conf(tmp_path, plataforma):
    r = Rutas()
    r.token = tmp_path / "token"
    r.token.write_text(TOKEN + "\n")
    r.token.chmod(0o600)

    r.verificador = tmp_path / "verificador"
    (r.verificador / "bin").mkdir(parents=True)
    os.symlink(FALSO, r.verificador / "bin" / "apolo-training")

    r.perfiles = tmp_path / "perfiles"
    r.bajas = tmp_path / "bajas"
    r.archivo = tmp_path / "archivo"
    r.url = plataforma.url

    r.archivo_conf = tmp_path / "admin.conf"
    r.escribir = lambda **cambios: r.archivo_conf.write_text(
        "[admin]\n"
        + "".join(
            f"{clave} = {valor}\n"
            for clave, valor in {
                "url": r.url,
                "token": r.token,
                "timeout": "2",
                "verificador": r.verificador,
                "perfiles": r.perfiles,
                "bajas": r.bajas,
                "archivo": r.archivo,
                **cambios,
            }.items()
        )
    )
    r.escribir()
    return r


class VM:
    """Usuarios que «existen» en la VM y cuáles son del curso."""

    def __init__(self):
        self.usuarios = set()
        self.del_curso = set()
        self.homes = {}


@pytest.fixture
def vm(monkeypatch):
    v = VM()
    monkeypatch.setattr(admin, "es_root", lambda: True)
    monkeypatch.setattr(admin, "existe_en_vm", lambda u: u in v.usuarios)
    monkeypatch.setattr(admin, "es_del_curso", lambda u: u in v.del_curso)
    monkeypatch.setattr(admin, "home_de", lambda u: v.homes.get(u))
    monkeypatch.setattr(admin, "ESPERA_SACCTMGR", 0)
    return v


class Resultado:
    def __init__(self, codigo, salida, error):
        self.codigo = codigo
        self.salida = salida
        self.error = error


@pytest.fixture
def correr(conf, vm, comandos, capsys):
    """Corre apolo-training-admin con la configuración de prueba."""

    def ejecutar(*args):
        codigo = admin.main(["--config", str(conf.archivo_conf), *args])
        capturado = capsys.readouterr()
        return Resultado(codigo, capturado.out, capturado.err)

    return ejecutar
