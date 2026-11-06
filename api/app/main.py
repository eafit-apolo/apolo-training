"""Punto de entrada: create_app() arma la aplicación.

gunicorn la llama como fábrica ("app.main:create_app()"), así cada worker
lee la configuración del entorno y crea su propio motor de base de datos.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, obtener_settings
from app.core.db import crear_engine, crear_sessionmaker
from app.core.errores import registrar_manejadores
from app.routers import auth, contenido, medios, panel, perfil, progreso, salud

PREFIJO = "/api"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or obtener_settings()
    if settings.secreto is None:
        # Sin secreto no hay sesiones: mejor no arrancar que fallar en el login.
        raise RuntimeError("Falta API_SECRETO (32 caracteres o más); ver api/README.md")
    engine = crear_engine(settings)

    @asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="apolo-training API",
        version=settings.version,
        lifespan=ciclo_de_vida,
        openapi_url=f"{PREFIJO}/openapi.json" if settings.docs else None,
        docs_url=f"{PREFIJO}/docs" if settings.docs else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = crear_sessionmaker(engine)

    registrar_manejadores(app)
    app.include_router(salud.router, prefix=PREFIJO)
    app.include_router(auth.router, prefix=PREFIJO)
    app.include_router(perfil.router, prefix=PREFIJO)
    app.include_router(contenido.router, prefix=PREFIJO)
    app.include_router(progreso.router, prefix=PREFIJO)
    app.include_router(medios.router, prefix=PREFIJO)
    app.include_router(panel.router, prefix=PREFIJO)
    return app
