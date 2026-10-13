"""Motor y sesiones async de SQLAlchemy.

El motor se crea con la app (create_app) y se guarda en app.state; no abre
conexiones hasta la primera consulta, así que crear la app no exige que
PostgreSQL esté arriba.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def crear_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"timeout": settings.db_timeout},
    )


def crear_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def obtener_engine(request: Request) -> AsyncEngine:
    return request.app.state.engine


async def obtener_sesion(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as sesion:
        yield sesion


EngineDep = Annotated[AsyncEngine, Depends(obtener_engine)]
SesionDep = Annotated[AsyncSession, Depends(obtener_sesion)]
