"""Rutas de progreso: completarLeccion (F-04) y reportarVideo (F-05) del contrato.

Los quizzes llegan con la B-06.
"""

from typing import Annotated

from fastapi import APIRouter, Path

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.schemas.contenido import ProgresoLeccion, ProgresoVideoEntrada
from app.services import progreso

router = APIRouter(tags=["progreso"])

# Los ids son bigint: uno fuera de rango es un 422, no un error de PostgreSQL.
LeccionId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.post(
    "/lecciones/{leccion_id}/completar",
    operation_id="completarLeccion",
    summary="Marcar como completada una lección",
    **con_roles(*ROLES),
)
async def completar_leccion(
    leccion_id: LeccionId, usuario: UsuarioDep, bd: SesionDep
) -> ProgresoLeccion:
    return await progreso.completar_leccion(bd, leccion_id, usuario)


@router.post(
    "/progreso/video",
    operation_id="reportarVideo",
    summary="Reportar el segundo actual del video (cada 15 s)",
    **con_roles(*ROLES),
)
async def reportar_video(
    entrada: ProgresoVideoEntrada, usuario: UsuarioDep, bd: SesionDep
) -> ProgresoLeccion:
    return await progreso.reportar_video(bd, entrada, usuario)
