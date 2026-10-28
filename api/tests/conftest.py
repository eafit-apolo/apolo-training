"""Fixtures comunes.

Las pruebas que tocan PostgreSQL usan API_DATABASE_URL (en CI la pone el job
`api`; en local, el servicio `pruebas` de deploy/compose.dev.yaml). Si falta,
esas pruebas fallan con un mensaje claro en vez de saltarse: así nadie cree
que pasaron.
"""

import os
from collections.abc import AsyncIterator, Callable

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import crear_engine, obtener_sesion
from app.main import create_app

# Puerto 1 en localhost: nadie escucha ahí, así que la conexión falla al momento.
URL_SIN_BASE = "postgresql+asyncpg://nadie@localhost:1/nada"
# Solo para las pruebas (32 caracteres o más, como exige Settings).
SECRETO_PRUEBAS = "pruebas-" * 4


@pytest.fixture
def settings_con_base() -> Settings:
    if not os.environ.get("API_DATABASE_URL"):
        pytest.fail(
            "Falta API_DATABASE_URL. Corre las pruebas con "
            "`docker compose -f deploy/compose.dev.yaml run --rm pruebas` "
            "desde la raíz del repo (ver deploy/README.md)."
        )
    return Settings(version="pruebas", secreto=SECRETO_PRUEBAS)


@pytest.fixture
def settings_sin_base() -> Settings:
    return Settings(
        database_url=URL_SIN_BASE,
        db_timeout=2,
        version="pruebas",
        secreto=SECRETO_PRUEBAS,
    )


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
        # https: httpx no manda las cookies Secure (at, rt, csrf) por http.
        cliente = AsyncClient(transport=transporte, base_url="https://prueba")
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


@pytest.fixture
async def sesion_bd(settings_con_base: Settings) -> AsyncIterator[AsyncSession]:
    """Sesión dentro de una transacción que se deshace al final de la prueba.

    Lo que la prueba escriba (incluso con commit) no queda en la base: el
    commit de la sesión solo cierra un savepoint dentro de esa transacción.
    """
    engine = crear_engine(settings_con_base)
    async with engine.connect() as conexion:
        transaccion = await conexion.begin()
        sesion = AsyncSession(
            bind=conexion,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield sesion
        finally:
            await sesion.close()
            await transaccion.rollback()
    await engine.dispose()


@pytest.fixture
def app_bd(settings_con_base: Settings, sesion_bd: AsyncSession) -> FastAPI:
    """App cuyas rutas usan la sesión de `sesion_bd`: lo que escriban se deshace
    al final de la prueba, y la prueba ve lo mismo que la app."""
    app = create_app(settings_con_base)

    async def _misma_sesion() -> AsyncIterator[AsyncSession]:
        yield sesion_bd

    app.dependency_overrides[obtener_sesion] = _misma_sesion
    return app


@pytest.fixture
def cliente_bd(crear_cliente, app_bd: FastAPI) -> AsyncClient:
    return crear_cliente(app_bd)
