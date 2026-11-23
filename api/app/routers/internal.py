"""Rutas internas de la VM de práctica (token de servicio, sin sesión):
sincronizarLabs (B-07) del contrato. Las de altas y bajas (`/internal/usuarios`)
llegan con la B-08 y usan la misma dependencia.

La IP de la 116 la filtra el nginx de la 117; la API revisa el token.
"""

from fastapi import APIRouter

from app.core.auth import con_servicio
from app.core.db import SesionDep
from app.schemas.labs import ReporteLabs, ResultadoSincronizacion
from app.services import labs

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/labs",
    operation_id="sincronizarLabs",
    summary="Recibir el reporte de prácticas de la VM de práctica",
    **con_servicio(),
)
async def sincronizar_labs(
    reporte: ReporteLabs, bd: SesionDep
) -> ResultadoSincronizacion:
    return await labs.sincronizar(bd, reporte)
