"""El gateway contra un servidor SSH de verdad, dentro de la misma prueba.

El servidor (asyncssh) hace lo que hace sshd con PAM en la VM de práctica:
pregunta «Password:» por keyboard-interactive y, con la clave correcta, abre
un shell de mentira en una PTY. Así se prueban conectar_ssh y _Cliente
reales, incluida la verificación de la llave del servidor, sin la VM ni la
VPN.
"""

import asyncio
import threading

import asyncssh
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import CABECERAS, CLAVE, CONECTADO, ORIGEN, RUTA, validar_falso


class _ServidorConClave(asyncssh.SSHServer):
    def begin_auth(self, username: str) -> bool:
        return True  # siempre pide autenticación

    def kbdint_auth_supported(self) -> bool:
        return True

    def get_kbdint_challenge(self, username, lang, submethods):
        # nombre, instrucciones, idioma y una pregunta sin eco
        return "", "", "", [("Password: ", False)]

    def validate_kbdint_response(self, username, responses):
        return username == "ana" and responses == [CLAVE]


async def _shell(proceso: asyncssh.SSHServerProcess) -> None:
    """Un shell mínimo: saluda, informa el tamaño de la PTY y repite líneas."""
    columnas, filas, *_ = proceso.term_size
    usuario = proceso.get_extra_info("username")
    proceso.stdout.write(f"hola {usuario} {proceso.term_type} {columnas}x{filas}\r\n")
    async for linea in proceso.stdin:
        if linea.strip() == "exit":
            break
        proceso.stdout.write(f"eco: {linea.strip()}\r\n")
    proceso.exit(0)


@pytest.fixture
def servidor_ssh(tmp_path):
    """El servidor corre en su propio hilo, con su propio event loop.

    El TestClient es síncrono: mientras una prueba espera en receive_bytes(),
    bloquea el hilo que la corre. Si el servidor viviera en ese mismo hilo, no
    podría responder y todo terminaría por timeout.
    """
    loop = asyncio.new_event_loop()
    hilo = threading.Thread(target=loop.run_forever, daemon=True)
    hilo.start()

    def en_el_hilo(corrutina):
        return asyncio.run_coroutine_threadsafe(corrutina, loop).result(timeout=10)

    llave = asyncssh.generate_private_key("ssh-ed25519")

    async def iniciar() -> asyncssh.SSHAcceptor:
        return await asyncssh.create_server(
            _ServidorConClave,
            "127.0.0.1",
            0,  # un puerto libre cualquiera
            server_host_keys=[llave],
            process_factory=_shell,
        )

    servidor = en_el_hilo(iniciar())
    puerto = servidor.sockets[0].getsockname()[1]
    # El mismo formato que tendrá known_hosts en la 117: «[host]:puerto llave».
    known_hosts = tmp_path / "known_hosts"
    publica = llave.export_public_key().decode().strip()
    known_hosts.write_text(f"[127.0.0.1]:{puerto} {publica}\n")
    yield puerto, known_hosts

    loop.call_soon_threadsafe(servidor.close)
    en_el_hilo(servidor.wait_closed())
    loop.call_soon_threadsafe(loop.stop)
    hilo.join()
    loop.close()


def _cliente(puerto: int, known_hosts) -> TestClient:
    settings = Settings(
        origen=ORIGEN,
        ssh_host="127.0.0.1",
        ssh_puerto=puerto,
        known_hosts=str(known_hosts),
    )
    return TestClient(create_app(settings, validar=validar_falso))


def _leer_hasta(ws, fin: bytes) -> bytes:
    """Lee la salida hasta ver `fin` (puede llegar en varios marcos)."""
    salida = b""
    while fin not in salida:
        salida += ws.receive_bytes()
    return salida


def test_sesion_completa(servidor_ssh):
    puerto, known_hosts = servidor_ssh
    with _cliente(puerto, known_hosts).websocket_connect(RUTA, headers=CABECERAS) as ws:
        # xterm avisa su tamaño antes de que exista la PTY.
        ws.send_json({"tipo": "tamano", "columnas": 120, "filas": 32})
        assert ws.receive_bytes() == b"Password: "
        ws.send_json({"tipo": "entrada", "datos": f"{CLAVE}\r"})
        assert ws.receive_bytes() == b"\r\n"
        assert ws.receive_json() == CONECTADO
        # La PTY se abrió como xterm-256color con el tamaño de la ventana.
        assert b"hola ana xterm-256color 120x32" in _leer_hasta(ws, b"\r\n")
        ws.send_json({"tipo": "entrada", "datos": "ls\r"})
        assert b"eco: ls" in _leer_hasta(ws, b"eco: ls")
        ws.send_json({"tipo": "entrada", "datos": "exit\r"})
        _leer_hasta(ws, b"exit")
        assert ws.receive_json() == {"tipo": "estado", "estado": "cerrado"}


def test_clave_errada_vuelve_a_preguntar(servidor_ssh):
    puerto, known_hosts = servidor_ssh
    with _cliente(puerto, known_hosts).websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_bytes() == b"Password: "
        ws.send_json({"tipo": "entrada", "datos": "otra\r"})
        assert ws.receive_bytes() == b"\r\n"
        # El servidor vuelve a preguntar (en la VM, hasta MaxAuthTries de sshd).
        assert ws.receive_bytes() == b"Password: "
        ws.send_json({"tipo": "entrada", "datos": f"{CLAVE}\r"})
        assert ws.receive_bytes() == b"\r\n"
        assert ws.receive_json() == CONECTADO


def test_llave_del_servidor_distinta(servidor_ssh, tmp_path):
    puerto, _ = servidor_ssh
    # known_hosts con otra llave: como si un impostor ocupara el lugar de la VM.
    otra = asyncssh.generate_private_key("ssh-ed25519").export_public_key().decode()
    known_hosts = tmp_path / "otro_known_hosts"
    known_hosts.write_text(f"[127.0.0.1]:{puerto} {otra.strip()}\n")
    with _cliente(puerto, known_hosts).websocket_connect(RUTA, headers=CABECERAS) as ws:
        # Cierra sin llegar a pedir la contraseña.
        assert ws.receive_json() == {
            "tipo": "estado",
            "estado": "cerrado",
            "motivo": "error",
        }
