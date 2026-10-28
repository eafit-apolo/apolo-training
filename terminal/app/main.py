"""Punto de entrada: create_app() arma el gateway de terminal.

uvicorn la llama como fábrica (`app.main:create_app --factory`) y con un solo
proceso: el registro de sesiones vive en memoria (ver sesion.Registro).
"""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import partial

import httpx
from fastapi import FastAPI, WebSocket, status

from app import mensajes
from app.api import SesionInvalida, validar_sesion
from app.config import Settings
from app.mensajes import Motivo
from app.sesion import Conectar, Registro, Sesion
from app.ssh import conectar_ssh

log = logging.getLogger("terminal")

# Recibe la cookie `at` (o None) y devuelve el username, o lanza SesionInvalida.
Validar = Callable[[str | None], Awaitable[str]]


def create_app(
    settings: Settings | None = None,
    validar: Validar | None = None,
    conectar: Conectar | None = None,
) -> FastAPI:
    """`validar` y `conectar` se reemplazan en las pruebas (sin API ni SSH)."""
    # Las pruebas pasan su propia configuración; en producción sale del entorno.
    settings = settings or Settings()
    # Sin esto, uvicorn solo muestra sus propios logs y no los de "terminal".
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    # Un solo cliente para toda la vida de la app: reutiliza las conexiones a la API.
    cliente_api = httpx.AsyncClient(base_url=settings.api_url, timeout=5)
    validar = validar or partial(validar_sesion, cliente_api)
    conectar = conectar or partial(conectar_ssh, settings)
    registro = Registro()

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        yield
        await cliente_api.aclose()

    app = FastAPI(
        title="apolo-training terminal",
        lifespan=ciclo_de_vida,
        # Sin documentación automática: este servicio no tiene API pública.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    # Para el healthcheck de Docker.
    @app.get("/health")
    async def salud() -> dict[str, str]:
        return {"estado": "ok"}

    @app.websocket("/ws/terminal")
    async def terminal(ws: WebSocket) -> None:
        # 1. Antes de aceptar. Se rechaza si:
        #    - el Origin no es el de la plataforma: otra página intentando abrir
        #      la terminal con las cookies del usuario;
        #    - la URL trae parámetros: alguien intentando elegir host o usuario.
        #    Cerrar antes de accept() hace que el navegador reciba un 403.
        if ws.headers.get("origin") != settings.origen or ws.query_params:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await ws.accept()

        # 2. ¿De quién es la sesión? Se lo pregunta a la API con su cookie.
        #    Ya se aceptó, para poder decirle a la app el motivo del cierre.
        try:
            username = await validar(ws.cookies.get("at"))
        except SesionInvalida:
            await _cerrar(ws, "sesion_invalida")
            return
        except httpx.HTTPError as exc:
            log.warning("la API no respondió: %s", exc)
            await _cerrar(ws, "error")
            return

        # 3. Una sesión por usuario: si ya tenía una, esta la reemplaza.
        sesion = Sesion(ws, username, settings, conectar)
        registro.abrir(sesion)
        log.info("inicio usuario=%s", username)
        motivo: Motivo | None = None
        try:
            # 4. SSH, puente y tiempos, hasta que algo la cierre.
            motivo = await sesion.correr()
        finally:
            registro.cerrar(sesion)
            # Solo quién, cuánto y por qué: nunca lo que se escribió.
            duracion = round(time.monotonic() - sesion.inicio)
            log.info(
                "fin usuario=%s motivo=%s duracion=%ss", username, motivo, duracion
            )
        if sesion.navegador_conectado:
            await _cerrar(ws, motivo)

    return app


async def _cerrar(ws: WebSocket, motivo: Motivo | None) -> None:
    """Le dice a la app por qué se cierra y cierra el WebSocket."""
    await ws.send_json(mensajes.estado("cerrado", motivo))
    await ws.close()
