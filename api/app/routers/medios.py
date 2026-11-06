"""Rutas de medios (B-05): obtenerVideo y obtenerSubtitulos del contrato.

Validan la sesión como el resto de la API y entregan el archivo por nginx
(X-Accel-Redirect) o, en desarrollo, desde la API; ver app/services/medios.py.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Response

from app.core.auth import con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.schemas.contenido import Idioma
from app.services import medios

router = APIRouter(prefix="/media", tags=["medios"])

# Los ids son bigint: uno fuera de rango es un 422, no un error de PostgreSQL.
VideoId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.get(
    "/{video_id}",
    operation_id="obtenerVideo",
    summary="Video MP4 (solo con sesión)",
    response_class=Response,
    **con_roles(*ROLES),
)
async def obtener_video(video_id: VideoId, request: Request, bd: SesionDep) -> Response:
    return await medios.entregar_video(bd, request.app.state.settings, video_id)


@router.get(
    "/{video_id}/subtitulos/{idioma}",
    operation_id="obtenerSubtitulos",
    summary="Subtítulos WebVTT del video",
    response_class=Response,
    **con_roles(*ROLES),
)
async def obtener_subtitulos(
    video_id: VideoId, idioma: Idioma, request: Request, bd: SesionDep
) -> Response:
    return await medios.entregar_subtitulos(
        bd, request.app.state.settings, video_id, idioma
    )
