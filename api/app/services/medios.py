"""Videos y subtítulos (B-05): subida desde el panel y entrega solo con sesión.

**Subida.** El PUT trae el archivo como cuerpo (no multipart): se escribe una
sola vez, mientras llega, en `media/.subiendo/` (el mismo volumen que el
destino, así moverlo no copia nada) y se corta al pasar el límite. Después se
lee el formato, se mueve a `media/m05/m05-trabajos-20261105T140312-a1b2.mp4`
y se actualiza la fila. Cada subida lleva un nombre nuevo para no pisar el
archivo que alguien puede estar viendo; el anterior se borra al confirmar.

**Entrega.** Con `API_MEDIA_ENTREGA=nginx` (la 117) la API responde vacío con
`X-Accel-Redirect: /media-interno/<archivo>` y nginx manda el archivo, con
Range, desde una `location` interna (W-05). Con `api` (desarrollo) lo manda la
API misma con `FileResponse`, que también entiende Range.

Cualquier sesión puede pedir un video, también de un módulo bloqueado: el
bloqueo es para ir en orden, no para esconder (decisión del 5-nov).
"""

import contextlib
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import anyio
from fastapi import Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.errores import ErrorApi
from app.core.seguridad import ahora
from app.models import Leccion, LeccionVideo, Modulo, Usuario, Video
from app.schemas.contenido import Idioma, LeccionRef
from app.schemas.medios import SubtitulosVideo, VideoAdmin
from app.services import auditoria
from app.services.contenido import Textos
from app.services.video_formato import FormatoInvalido, leer_formato

logger = logging.getLogger(__name__)

# 2 GiB, lo mismo que `client_max_body_size 2G` de nginx.
LIMITE_VIDEO = 2 * 1024**3
LIMITE_VTT = 1024**2
# La `location` interna de nginx (W-05); flujo 6 de docs/diseno/flujos.md.
PREFIJO_INTERNO = "/media-interno/"
SUBIENDO = ".subiendo"
# Para que el navegador revalide (ETag) y no muestre un video ya reemplazado.
CACHE = "private, no-cache"
TIPO_VIDEO = "video/mp4"
TIPO_VTT = "text/vtt; charset=utf-8"
# Escribir de a 1 MiB: menos saltos al hilo de archivos que con cada trozo.
BLOQUE = 1024**2
# Segundos tras los que un .part de .subiendo/ se da por abandonado.
PARTE_VIEJA = 24 * 3600


@dataclass(frozen=True)
class Subida:
    """El cuerpo de un PUT tal como llega, con sus cabeceras."""

    partes: AsyncIterator[bytes]
    tipo: str | None
    largo: str | None


# --- Panel -----------------------------------------------------------------


async def _admin(
    bd: AsyncSession, videos: list[Video], idioma: Idioma
) -> list[VideoAdmin]:
    ids = [video.id for video in videos]
    subidores = {v.subido_por for v in videos if v.subido_por}
    usuarios: dict[int, str] = dict(
        (
            await bd.execute(
                select(Usuario.id, Usuario.username).where(Usuario.id.in_(subidores))
            )
        ).all()
    )
    t = Textos(idioma)
    lecciones: dict[int, list[LeccionRef]] = defaultdict(list)
    for video_id, leccion, modulo in await bd.execute(
        select(LeccionVideo.video_id, Leccion, Modulo)
        .join(Leccion, Leccion.id == LeccionVideo.leccion_id)
        .join(Modulo, Modulo.id == Leccion.modulo_id)
        .where(LeccionVideo.video_id.in_(ids), Leccion.publicada.is_(True))
        .order_by(Modulo.numero, Leccion.orden)
    ):
        lecciones[video_id].append(
            LeccionRef(
                id=leccion.id,
                slug=leccion.slug,
                modulo=modulo.slug,
                modulo_numero=modulo.numero,
                titulo=t(leccion.titulo_es, leccion.titulo_en),
            )
        )
    return [
        VideoAdmin(
            id=video.id,
            clave=video.clave,
            disponible=video.archivo is not None,
            duracion_seg=video.duracion_seg,
            tamano_bytes=video.tamano_bytes,
            subtitulos=SubtitulosVideo(
                es=video.vtt_es is not None, en=video.vtt_en is not None
            ),
            lecciones=lecciones[video.id],
            subido_por=usuarios.get(video.subido_por) if video.subido_por else None,
            subido_en=video.subido_en,
        )
        for video in videos
    ]


async def listar_videos(bd: AsyncSession, idioma: Idioma) -> list[VideoAdmin]:
    """Todos los videos que creó el importador, por clave, con o sin archivo."""
    videos = list(await bd.scalars(select(Video).order_by(Video.clave)))
    return await _admin(bd, videos, idioma)


async def _video_por_clave(bd: AsyncSession, clave: str) -> Video:
    video = await bd.scalar(select(Video).where(Video.clave == clave))
    if video is None:
        raise ErrorApi(
            404,
            "no_encontrado",
            "No hay un video con esa clave: sale del front matter de una lección",
        )
    return video


def _revisar_cabeceras(
    tipo: str | None, largo: str | None, limite: int, codigo: str
) -> None:
    """Antes de leer nada: ni un formulario ni algo que ya se sabe que no cabe."""
    if tipo and tipo.lower().startswith("multipart/"):
        raise ErrorApi(
            415,
            codigo,
            "Manda el archivo como cuerpo del PUT (curl -T archivo), no como formulario",
        )
    if largo and largo.isdigit() and int(largo) > limite:
        raise _muy_grande(limite)


def _muy_grande(limite: int) -> ErrorApi:
    return ErrorApi(
        413,
        "archivo_muy_grande",
        f"El archivo pasa de {limite // 1024**2} MB",
    )


async def _recibir(cuerpo: AsyncIterator[bytes], destino: Path, limite: int) -> int:
    """Escribe el cuerpo en `destino` mientras llega; 413 al pasar el límite."""
    total = 0
    pendiente = bytearray()
    async with await anyio.open_file(destino, "wb") as archivo:
        async for parte in cuerpo:
            total += len(parte)
            if total > limite:
                raise _muy_grande(limite)
            pendiente += parte
            if len(pendiente) >= BLOQUE:
                await archivo.write(bytes(pendiente))
                pendiente.clear()
        if pendiente:
            await archivo.write(bytes(pendiente))
    return total


def _carpeta_temporal(settings: Settings) -> Path:
    """`media/.subiendo/`, sin los restos de subidas que no terminaron.

    Un `.part` de más de un día quedó de un worker que se reinició a mitad de
    una subida; se borra al empezar otra. Uno en curso se escribe a cada
    momento, así que nunca es viejo.
    """
    carpeta = settings.media_dir / SUBIENDO
    carpeta.mkdir(parents=True, exist_ok=True)
    limite = time.time() - PARTE_VIEJA
    for parte in carpeta.glob("*.part"):
        # Otra subida puede estar borrándolo en el mismo momento.
        with contextlib.suppress(OSError):
            if parte.stat().st_mtime < limite:
                parte.unlink()
    return carpeta


def _nombre_nuevo(clave: str, extension: str) -> str:
    """m05-trabajos → m05/m05-trabajos-20261105T140312-a1b2.mp4"""
    modulo = clave.split("-", 1)[0]
    marca = ahora().strftime("%Y%m%dT%H%M%S")
    return f"{modulo}/{clave}-{marca}-{secrets.token_hex(2)}.{extension}"


def _mover(settings: Settings, temporal: Path, relativo: str) -> Path:
    # nginx corre con otro usuario: tiene que poder entrar a la carpeta del
    # módulo y leer el archivo, sea cual sea el umask del proceso.
    final = settings.media_dir / relativo
    if not final.parent.is_dir():
        final.parent.mkdir(parents=True, exist_ok=True)
        final.parent.chmod(0o755)
    os.replace(temporal, final)
    final.chmod(0o644)
    return final


def _borrar(settings: Settings, relativo: str | None) -> None:
    if relativo is None:
        return
    try:
        (settings.media_dir / relativo).unlink(missing_ok=True)
    except OSError:
        logger.warning("No se pudo borrar el archivo anterior %s", relativo)


async def _guardar(
    bd: AsyncSession,
    settings: Settings,
    video_id: int,
    temporal: Path,
    relativo: str,
    campos: dict[str, object],
    columna: str,
    accion: str,
    usuario: Usuario,
    detalle: dict[str, object],
    ip: str | None,
) -> Video:
    """Mueve el archivo a su lugar, actualiza la fila y borra el anterior.

    `FOR UPDATE`: si dos personas suben el mismo video a la vez, la segunda
    espera, ve el archivo de la primera como «anterior» y lo borra; ninguno
    queda huérfano.
    """
    final = _mover(settings, temporal, relativo)
    try:
        video = await bd.scalar(
            select(Video).where(Video.id == video_id).with_for_update(),
            # Relee la fila aunque ya esté en la sesión: el «anterior» tiene
            # que ser el de la base, no el que se leyó antes de recibir.
            execution_options={"populate_existing": True},
        )
        anterior = getattr(video, columna)
        setattr(video, columna, relativo)
        for nombre, valor in campos.items():
            setattr(video, nombre, valor)
        auditoria.registrar(
            bd,
            accion,
            actor_id=usuario.id,
            objetivo=video.clave,
            detalle=detalle,
            ip=ip,
        )
        await bd.commit()
    except BaseException:
        final.unlink(missing_ok=True)
        raise
    _borrar(settings, anterior)
    return video


async def subir_video(
    bd: AsyncSession,
    settings: Settings,
    clave: str,
    subida: Subida,
    usuario: Usuario,
    ip: str | None,
) -> VideoAdmin:
    video = await _video_por_clave(bd, clave)
    video_id = video.id
    _revisar_cabeceras(
        subida.tipo, subida.largo, LIMITE_VIDEO, "video_formato_invalido"
    )
    # Cierra la transacción de la sesión (y suelta la conexión) antes de
    # recibir un archivo que puede tardar minutos. commit y no rollback: en las
    # pruebas la sesión es un savepoint y un rollback borraría sus datos.
    await bd.commit()

    temporal = _carpeta_temporal(settings) / f"{uuid.uuid4().hex}.part"
    try:
        tamano = await _recibir(subida.partes, temporal, LIMITE_VIDEO)
        if tamano == 0:
            raise ErrorApi(415, "video_formato_invalido", "No llegó ningún archivo")
        try:
            formato = await run_in_threadpool(leer_formato, temporal)
        except FormatoInvalido as exc:
            raise ErrorApi(415, "video_formato_invalido", str(exc)) from exc
        guardado = await _guardar(
            bd,
            settings,
            video_id,
            temporal,
            _nombre_nuevo(clave, "mp4"),
            {
                "duracion_seg": formato.duracion_seg,
                "tamano_bytes": tamano,
                "subido_por": usuario.id,
                "subido_en": ahora(),
            },
            columna="archivo",
            accion="video_subido",
            usuario=usuario,
            detalle={"tamano_bytes": tamano, "duracion_seg": formato.duracion_seg},
            ip=ip,
        )
    finally:
        temporal.unlink(missing_ok=True)
    return (await _admin(bd, [guardado], usuario.idioma))[0]


def _validar_vtt(datos: bytes) -> None:
    try:
        texto = datos.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ErrorApi(
            415, "vtt_invalido", "Los subtítulos tienen que estar en UTF-8"
        ) from exc
    primera = texto.split("\n", 1)[0].rstrip("\r")
    if primera != "WEBVTT" and not primera.startswith(("WEBVTT ", "WEBVTT\t")):
        raise ErrorApi(415, "vtt_invalido", "Un WebVTT empieza por la línea WEBVTT")


async def subir_subtitulos(
    bd: AsyncSession,
    settings: Settings,
    clave: str,
    idioma: Idioma,
    subida: Subida,
    usuario: Usuario,
    ip: str | None,
) -> VideoAdmin:
    """Los subtítulos se pueden subir antes que el video; se muestran cuando
    el video esté."""
    video = await _video_por_clave(bd, clave)
    _revisar_cabeceras(subida.tipo, subida.largo, LIMITE_VTT, "vtt_invalido")
    temporal = _carpeta_temporal(settings) / f"{uuid.uuid4().hex}.part"
    try:
        await _recibir(subida.partes, temporal, LIMITE_VTT)
        _validar_vtt(await anyio.Path(temporal).read_bytes())
        guardado = await _guardar(
            bd,
            settings,
            video.id,
            temporal,
            _nombre_nuevo(clave, f"{idioma}.vtt"),
            {},
            columna=f"vtt_{idioma}",
            accion="subtitulos_subidos",
            usuario=usuario,
            detalle={"idioma": idioma},
            ip=ip,
        )
    finally:
        temporal.unlink(missing_ok=True)
    return (await _admin(bd, [guardado], usuario.idioma))[0]


# --- Entrega -----------------------------------------------------------------


def _entregar(settings: Settings, relativo: str | None, tipo: str) -> Response:
    if relativo is None:
        raise ErrorApi(404, "no_encontrado", "Todavía no se ha subido")
    raiz = settings.media_dir.resolve()
    ruta = (raiz / relativo).resolve()
    # La ruta sale de la base, pero nunca se sirve algo fuera de media/.
    if not ruta.is_relative_to(raiz) or not ruta.is_file():
        logger.warning("Falta el archivo %s en %s", relativo, raiz)
        raise ErrorApi(404, "no_encontrado", "No se encontró el archivo")
    cabeceras = {"Cache-Control": CACHE}
    if settings.media_entrega == "api":
        return FileResponse(ruta, media_type=tipo, headers=cabeceras)
    cabeceras["X-Accel-Redirect"] = PREFIJO_INTERNO + quote(relativo)
    return Response(media_type=tipo, headers=cabeceras)


async def _video_por_id(bd: AsyncSession, video_id: int) -> Video:
    video = await bd.get(Video, video_id)
    if video is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese video")
    return video


async def entregar_video(
    bd: AsyncSession, settings: Settings, video_id: int
) -> Response:
    video = await _video_por_id(bd, video_id)
    return _entregar(settings, video.archivo, TIPO_VIDEO)


async def entregar_subtitulos(
    bd: AsyncSession, settings: Settings, video_id: int, idioma: Idioma
) -> Response:
    video = await _video_por_id(bd, video_id)
    return _entregar(settings, getattr(video, f"vtt_{idioma}"), TIPO_VTT)
