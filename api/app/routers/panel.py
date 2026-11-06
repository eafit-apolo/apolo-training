"""Rutas del panel de instructor (instructor y admin): por ahora los videos
(B-05): listarVideos, subirVideo y subirSubtitulos del contrato.

La subida manda el archivo como cuerpo del PUT, no como formulario
(`curl -T video.mp4`, o el archivo tal cual desde la F-08), así se escribe una
sola vez mientras llega. Ver api/README.md.
"""

from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Path, Request
from starlette.requests import ClientDisconnect

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.core.errores import ErrorApi
from app.models.valores import PATRON_CLAVE_VIDEO
from app.schemas.contenido import Idioma
from app.schemas.medios import VideoAdmin
from app.services import medios
from app.services.auditoria import ip_de

router = APIRouter(prefix="/panel", tags=["panel"])

PANEL = con_roles("instructor", "admin")
ClaveVideo = Annotated[str, Path(pattern=PATRON_CLAVE_VIDEO)]


def _con_cuerpo(tipo: str, esquema: dict[str, Any]) -> dict[str, Any]:
    """PANEL más el cuerpo en el OpenAPI: la ruta lo lee como flujo y FastAPI
    no lo declararía solo."""
    extra = {
        **PANEL["openapi_extra"],
        "requestBody": {"required": True, "content": {tipo: {"schema": esquema}}},
    }
    return {**PANEL, "openapi_extra": extra}


async def partes(request: Request) -> AsyncIterator[bytes]:
    """El cuerpo según llega. Si quien sube cierra la pestaña o se cae la red,
    un 400 (que nadie va a leer) en vez de un «error no controlado» en el log."""
    try:
        async for parte in request.stream():
            yield parte
    except ClientDisconnect as exc:
        raise ErrorApi(
            400, "peticion_invalida", "La subida se cortó antes de terminar"
        ) from exc


def _subida(request: Request) -> medios.Subida:
    return medios.Subida(
        partes=partes(request),
        tipo=request.headers.get("content-type"),
        largo=request.headers.get("content-length"),
    )


@router.get(
    "/videos",
    operation_id="listarVideos",
    summary="Videos del curso con el estado de archivo y subtítulos",
    **PANEL,
)
async def listar_videos(usuario: UsuarioDep, bd: SesionDep) -> list[VideoAdmin]:
    return await medios.listar_videos(bd, usuario.idioma)


@router.put(
    "/videos/{clave}",
    operation_id="subirVideo",
    summary="Subir o reemplazar el MP4 de un video",
    **_con_cuerpo("video/mp4", {"type": "string", "format": "binary"}),
)
async def subir_video(
    clave: ClaveVideo, request: Request, usuario: UsuarioDep, bd: SesionDep
) -> VideoAdmin:
    return await medios.subir_video(
        bd, request.app.state.settings, clave, _subida(request), usuario, ip_de(request)
    )


@router.put(
    "/videos/{clave}/subtitulos/{idioma}",
    operation_id="subirSubtitulos",
    summary="Subir o reemplazar el VTT de un idioma",
    **_con_cuerpo("text/vtt", {"type": "string"}),
)
async def subir_subtitulos(
    clave: ClaveVideo,
    idioma: Idioma,
    request: Request,
    usuario: UsuarioDep,
    bd: SesionDep,
) -> VideoAdmin:
    return await medios.subir_subtitulos(
        bd,
        request.app.state.settings,
        clave,
        idioma,
        _subida(request),
        usuario,
        ip_de(request),
    )
