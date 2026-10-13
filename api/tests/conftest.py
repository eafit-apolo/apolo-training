"""Fixtures comunes.

Las pruebas que tocan PostgreSQL usan API_DATABASE_URL (en CI la pone el job
`api`; en local, `api/compose.yaml`). Si falta, esas pruebas fallan con un
mensaje claro en vez de saltarse: así nadie cree que pasaron.
"""

import os
from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

# Puerto 1 en localhost: nadie escucha ahí, así que la conexión falla al momento.
URL_SIN_BASE = "postgresql+asyncpg://nadie@localhost:1/nada"


@pytest.fixture
def settings_con_base() -> Settings:
    if not os.environ.get("API_DATABASE_URL"):
        pytest.fail(
            "Falta API_DATABASE_URL. Levanta la base con "
            "`docker compose up -d db` en api/ (ver api/README.md)."
        )
    return Settings(version="pruebas")


@pytest.fixture
def settings_sin_base() -> Settings:
    return Settings(database_url=URL_SIN_BASE, db_timeout=2, version="pruebas")


@pytest.fixture
async def crear_cliente() -> AsyncIterator[Callable[[FastAPI], AsyncClient]]:
    """Fábrica de clientes httpx contra una app, sin levantar un servidor."""
    apps: list[FastAPI] = []
    clientes: list[AsyncClient] = []

    def _crear(app: FastAPI) -> AsyncClient:
        apps.append(app)
        # raise_app_exceptions=False: que un 500 llegue como respuesta, igual
        # que lo vería el navegador, en vez de relanzar la excepción en la prueba.
        transporte = ASGITransport(app=app, raise_app_exceptions=False)
        cliente = AsyncClient(transport=transporte, base_url="http://prueba")
        clientes.append(cliente)
        return cliente

    yield _crear
    for cliente in clientes:
        await cliente.aclose()
    for app in apps:
        await app.state.engine.dispose()


@pytest.fixture
def cliente(crear_cliente, settings_con_base: Settings) -> AsyncClient:
    return crear_cliente(create_app(settings_con_base))


@pytest.fixture
def cliente_sin_base(crear_cliente, settings_sin_base: Settings) -> AsyncClient:
    return crear_cliente(create_app(settings_sin_base))
