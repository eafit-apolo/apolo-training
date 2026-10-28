"""Fixtures comunes: el gateway con una API y un SSH falsos.

Las pruebas no necesitan la API, la VM de práctica ni la VPN: create_app()
recibe un `validar` que conoce una sola cookie (la de ana) y un `conectar`
que imita a sshd.
"""

import asyncio

import asyncssh
import pytest
from fastapi.testclient import TestClient

from app.api import SesionInvalida
from app.config import Settings
from app.main import create_app

ORIGEN = "https://training.apolo.eafit.edu.co"
RUTA = "/ws/terminal"
# Lo que manda el navegador de ana desde la plataforma.
CABECERAS = {"origin": ORIGEN, "cookie": "at=token-de-ana"}
# La contraseña de ana en la VM falsa.
CLAVE = "clave-de-prueba-1"
CONECTADO = {"tipo": "estado", "estado": "conectado"}


def cerrado(motivo: str | None = None) -> dict:
    mensaje = {"tipo": "estado", "estado": "cerrado"}
    if motivo:
        mensaje["motivo"] = motivo
    return mensaje


async def validar_falso(cookie_at: str | None) -> str:
    if cookie_at != "token-de-ana":
        raise SesionInvalida
    return "ana"


class ProcesoFalso:
    """Un shell en una PTY que devuelve lo que recibe (eco)."""

    def __init__(self) -> None:
        self._cola: asyncio.Queue[bytes] = asyncio.Queue()
        self.stdin = self
        self.stdout = self
        self.tamanos: list[tuple[int, int]] = []

    def write(self, datos: bytes) -> None:
        # "exit\r" cierra el shell: la salida termina (b"").
        self._cola.put_nowait(b"" if datos == b"exit\r" else datos)

    async def read(self, _n: int) -> bytes:
        return await self._cola.get()

    def change_terminal_size(self, columnas: int, filas: int) -> None:
        self.tamanos.append((columnas, filas))


class ConexionFalsa:
    """Una conexión SSH ya autenticada como `username`."""

    def __init__(self, username: str) -> None:
        self.username = username
        self.proceso = ProcesoFalso()
        self.term_size: tuple[int, int] | None = None

    async def __aenter__(self) -> "ConexionFalsa":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def create_process(self, *, term_type, term_size, encoding) -> ProcesoFalso:
        self.term_size = term_size
        return self.proceso


class SSHFalso:
    """Imita a sshd: registra con qué usuario se conectó cada sesión.

    Con `pedir_clave`, pregunta «Password:» como PAM y solo acepta CLAVE.
    """

    def __init__(self, pedir_clave: bool = False) -> None:
        self.pedir_clave = pedir_clave
        self.usuarios: list[str] = []
        self.conexiones: list[ConexionFalsa] = []

    async def __call__(self, username: str, terminal) -> ConexionFalsa:
        self.usuarios.append(username)
        if self.pedir_clave and await terminal.pedir("Password: ", False) != CLAVE:
            raise asyncssh.PermissionDenied("clave errada")
        conexion = ConexionFalsa(username)
        self.conexiones.append(conexion)
        return conexion


@pytest.fixture
def ssh() -> SSHFalso:
    return SSHFalso()


@pytest.fixture
def crear_cliente(ssh: SSHFalso):
    """Fábrica: cada prueba puede cambiar el validador, el SSH o los tiempos
    (por ejemplo, crear_cliente(inactividad=0.2))."""

    def _crear(validar=validar_falso, conectar=ssh, **opciones) -> TestClient:
        settings = Settings(origen=ORIGEN, **opciones)
        return TestClient(create_app(settings, validar=validar, conectar=conectar))

    return _crear


@pytest.fixture
def cliente(crear_cliente) -> TestClient:
    return crear_cliente()
