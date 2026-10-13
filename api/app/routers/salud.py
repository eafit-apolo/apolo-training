"""GET /api/health: operación `salud` del contrato."""

import asyncio
import logging

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import EngineDep
from app.schemas.salud import Salud

logger = logging.getLogger(__name__)

router = APIRouter(tags=["salud"])


@router.get(
    "/health",
    operation_id="salud",
    summary="Estado de la API y de la conexión a PostgreSQL",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": Salud,
            "description": "La API responde pero la base de datos no",
        }
    },
)
async def salud(request: Request, response: Response, engine: EngineDep) -> Salud:
    settings = request.app.state.settings
    try:
        async with asyncio.timeout(settings.db_timeout):
            async with engine.connect() as conexion:
                await conexion.execute(text("SELECT 1"))
    except (OSError, TimeoutError, SQLAlchemyError) as exc:
        # Sin la URL ni la clave: solo el tipo de error.
        logger.warning("PostgreSQL no responde: %s", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Salud(
            estado="degradado", base_datos="sin_conexion", version=settings.version
        )
    return Salud(estado="ok", base_datos="ok", version=settings.version)
