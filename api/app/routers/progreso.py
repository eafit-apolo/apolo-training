"""Rutas de progreso: completarLeccion (F-04), reportarVideo (F-05) y
obtenerMiProgreso (B-06) del contrato. Los quizzes están en `quizzes.py`.
"""

from typing import Annotated

from fastapi import APIRouter, Path

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.routers.contenido import LangDep
from app.schemas.contenido import MiProgreso, ProgresoLeccion, ProgresoVideoEntrada
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


@router.get(
    "/me/progreso",
    operation_id="obtenerMiProgreso",
    summary="Avance del usuario por módulo y por lección (pantalla Mi progreso)",
    **con_roles(*ROLES),
)
async def obtener_mi_progreso(
    usuario: UsuarioDep, bd: SesionDep, lang: LangDep = None
) -> MiProgreso:
    return await progreso.mi_progreso(bd, usuario, lang or usuario.idioma)
