"""Subida y entrega de videos y subtítulos (B-05).

El curso de prueba (tests/ayuda_contenido.py) trae el video m00-bienvenida
(módulo 0, abierto) y los tres de la VPN (m01-vpn-*, en el módulo 1, que está
bloqueado para un estudiante nuevo). Carla es instructora y Ana, estudiante.
"""

import os
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import Auditoria, Video
from app.routers.panel import partes
from app.services import medios
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import armar_contenido
from tests.ayuda_medios import VTT_EN, VTT_ES, generar_video
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

CLAVE = "m00-bienvenida"
LECCION = "/api/cursos/induccion/lecciones/m00/bienvenida"
# m00/m00-bienvenida-20261105T140312-a1b2.mp4 (y .es.vtt o .en.vtt)
NOMBRE = re.compile(r"^m00/m00-bienvenida-\d{8}T\d{6}-[0-9a-f]{4}\.mp4$")
NOMBRE_VTT = re.compile(r"^m00/m00-bienvenida-\d{8}T\d{6}-[0-9a-f]{4}\.es\.vtt$")


@pytest.fixture(scope="module")
def mp4(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    carpeta = tmp_path_factory.mktemp("videos")
    return generar_video(carpeta / "bueno.mp4").read_bytes()


@pytest.fixture(scope="module")
def mpeg4(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    carpeta = tmp_path_factory.mktemp("videos")
    return generar_video(carpeta / "mpeg4.mp4", video="mpeg4").read_bytes()


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> None:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))


@pytest.fixture
async def carla(
    crear_cliente, app_bd: FastAPI, sesion_bd: AsyncSession, contenido: None
) -> AsyncClient:
    await crear_usuario(sesion_bd, "carla", rol="instructor")
    cliente = crear_cliente(app_bd)
    assert (await ingresar(cliente, "carla")).status_code == 200
    return cliente


@pytest.fixture
async def ana(
    crear_cliente, app_bd: FastAPI, sesion_bd: AsyncSession, contenido: None
) -> AsyncClient:
    await crear_usuario(sesion_bd, "ana")
    cliente = crear_cliente(app_bd)
    assert (await ingresar(cliente, "ana")).status_code == 200
    return cliente


@pytest.fixture
def media(app_bd: FastAPI) -> Path:
    return app_bd.state.settings.media_dir


@pytest.fixture
def entrega_api(app_bd: FastAPI) -> None:
    """Como en desarrollo: la API manda el archivo (sin nginx delante)."""
    app_bd.state.settings.media_entrega = "api"


async def subir(
    cliente: AsyncClient,
    datos: bytes | AsyncIterator[bytes],
    clave: str = CLAVE,
    tipo: str = "video/mp4",
) -> Response:
    return await cliente.put(
        f"/api/panel/videos/{clave}",
        content=datos,
        headers={**con_csrf(cliente), "Content-Type": tipo},
    )


async def subir_vtt(
    cliente: AsyncClient, idioma: str, texto: str | bytes, clave: str = CLAVE
) -> Response:
    return await cliente.put(
        f"/api/panel/videos/{clave}/subtitulos/{idioma}",
        content=texto.encode() if isinstance(texto, str) else texto,
        headers={**con_csrf(cliente), "Content-Type": "text/vtt"},
    )


async def fila(bd: AsyncSession, clave: str = CLAVE) -> Video:
    return await bd.scalar(
        select(Video).where(Video.clave == clave),
        execution_options={"populate_existing": True},
    )


def archivos(media: Path) -> list[str]:
    """Todo lo que hay en media/, también lo que quedó a medio subir."""
    return sorted(str(p.relative_to(media)) for p in media.rglob("*") if p.is_file())


# --- Subida ------------------------------------------------------------------


async def test_subir_un_video_lo_guarda_y_aparece_en_la_leccion(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, media: Path, mp4
) -> None:
    respuesta = await subir(carla, mp4)

    assert respuesta.status_code == 200, respuesta.text
    video = respuesta.json()
    assert video["clave"] == CLAVE
    assert video["disponible"] is True
    assert video["duracion_seg"] == 2
    assert video["tamano_bytes"] == len(mp4)
    assert video["subido_por"] == "carla"
    assert [x["slug"] for x in video["lecciones"]] == ["bienvenida"]
    guardado = await fila(sesion_bd)
    assert NOMBRE.match(guardado.archivo)
    assert archivos(media) == [guardado.archivo]
    assert (media / guardado.archivo).read_bytes() == mp4
    assert (media / guardado.archivo).stat().st_mode & 0o777 == 0o644
    # DoD 1: aparece en la lección, con la URL que valida la sesión.
    leccion = (await ana.get(LECCION)).json()
    assert leccion["videos"][0]["video"]["disponible"] is True
    assert leccion["videos"][0]["video"]["url"] == f"/api/media/{guardado.id}"


async def test_nginx_puede_leer_lo_subido_aunque_el_umask_sea_estricto(
    carla: AsyncClient, sesion_bd: AsyncSession, media: Path, mp4
) -> None:
    """nginx corre con otro usuario (W-05): el video y su carpeta, legibles."""
    anterior = os.umask(0o077)
    try:
        assert (await subir(carla, mp4)).status_code == 200
        assert (await subir_vtt(carla, "es", VTT_ES)).status_code == 200
    finally:
        os.umask(anterior)

    video = await fila(sesion_bd)
    for relativo in (video.archivo, video.vtt_es):
        assert (media / relativo).stat().st_mode & 0o777 == 0o644
        assert (media / relativo).parent.stat().st_mode & 0o005 == 0o005


async def test_la_subida_queda_en_la_auditoria(
    carla: AsyncClient, sesion_bd: AsyncSession, mp4
) -> None:
    await subir(carla, mp4)
    await subir_vtt(carla, "en", VTT_EN)

    todas = await sesion_bd.scalars(select(Auditoria).order_by(Auditoria.id))
    filas = todas.all()[-2:]

    assert [(f.accion, f.objetivo) for f in filas] == [
        ("video_subido", CLAVE),
        ("subtitulos_subidos", CLAVE),
    ]
    assert filas[0].detalle == {"tamano_bytes": len(mp4), "duracion_seg": 2}
    assert filas[1].detalle == {"idioma": "en"}


async def test_reemplazar_borra_el_archivo_anterior(
    carla: AsyncClient, sesion_bd: AsyncSession, media: Path, mp4
) -> None:
    await subir(carla, mp4)
    primero = (await fila(sesion_bd)).archivo

    respuesta = await subir(carla, mp4)

    assert respuesta.status_code == 200
    segundo = (await fila(sesion_bd)).archivo
    assert segundo != primero
    assert archivos(media) == [segundo]


async def test_borra_lo_que_quedo_de_una_subida_vieja(
    carla: AsyncClient, media: Path, mp4
) -> None:
    """Un worker que se reinició a mitad de una subida deja su .part."""
    subiendo = media / ".subiendo"
    subiendo.mkdir(parents=True)
    vieja, en_curso = subiendo / "vieja.part", subiendo / "en-curso.part"
    vieja.write_bytes(b"x")
    en_curso.write_bytes(b"x")
    hace_dos_dias = time.time() - 2 * 24 * 3600
    os.utime(vieja, (hace_dos_dias, hace_dos_dias))

    assert (await subir(carla, mp4)).status_code == 200

    assert not vieja.exists()
    assert en_curso.exists()


async def test_por_partes_sin_content_length(
    carla: AsyncClient, sesion_bd: AsyncSession, mp4
) -> None:
    """Como llega un archivo grande: en trozos, sin saber el total de antemano."""

    async def partes() -> AsyncIterator[bytes]:
        for i in range(0, len(mp4), 1000):
            yield mp4[i : i + 1000]

    respuesta = await subir(carla, partes())

    assert respuesta.status_code == 200, respuesta.text
    assert (await fila(sesion_bd)).tamano_bytes == len(mp4)


async def test_formato_invalido_415_sin_tocar_nada(
    carla: AsyncClient, sesion_bd: AsyncSession, media: Path, mpeg4
) -> None:
    respuesta = await subir(carla, mpeg4)

    assert respuesta.status_code == 415
    assert respuesta.json()["codigo"] == "video_formato_invalido"
    assert "tiene que ser H.264" in respuesta.json()["detail"]
    assert (await fila(sesion_bd)).archivo is None
    assert archivos(media) == []


async def test_cuerpo_vacio_415(carla: AsyncClient) -> None:
    respuesta = await subir(carla, b"")

    assert respuesta.status_code == 415
    assert respuesta.json()["detail"] == "No llegó ningún archivo"


async def test_como_formulario_415_con_la_pista(carla: AsyncClient, mp4) -> None:
    respuesta = await carla.put(
        f"/api/panel/videos/{CLAVE}",
        files={"archivo": ("video.mp4", mp4, "video/mp4")},
        headers=con_csrf(carla),
    )

    assert respuesta.status_code == 415
    assert "curl -T" in respuesta.json()["detail"]


async def test_mas_grande_que_el_limite_413(
    carla: AsyncClient,
    sesion_bd: AsyncSession,
    media: Path,
    mp4,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(medios, "LIMITE_VIDEO", len(mp4) - 1)

    async def partes() -> AsyncIterator[bytes]:
        yield mp4

    # Con Content-Length se corta antes de leer; sin él, al pasar el límite.
    for datos in (mp4, partes()):
        respuesta = await subir(carla, datos)
        assert respuesta.status_code == 413
        assert respuesta.json()["codigo"] == "archivo_muy_grande"
    assert (await fila(sesion_bd)).archivo is None
    assert archivos(media) == []


async def test_subida_cortada_400_sin_dejar_nada(
    carla: AsyncClient, media: Path, mp4, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quien sube cierra la pestaña a mitad de camino."""

    async def se_corta(request: Request) -> AsyncIterator[bytes]:
        yield mp4[:1000]
        raise ErrorApi(400, "peticion_invalida", "La subida se cortó")

    monkeypatch.setattr("app.routers.panel.partes", se_corta)

    respuesta = await subir(carla, mp4)

    assert respuesta.status_code == 400
    assert archivos(media) == []


async def test_un_corte_de_la_conexion_es_un_400() -> None:
    mensajes = iter(
        [
            {"type": "http.request", "body": b"abc", "more_body": True},
            {"type": "http.disconnect"},
        ]
    )

    async def recibir() -> dict:
        return next(mensajes)

    request = Request({"type": "http", "method": "PUT", "headers": []}, recibir)
    recibido: list[bytes] = []

    async def leer() -> None:
        async for parte in partes(request):
            recibido.append(parte)

    with pytest.raises(ErrorApi) as error:
        await leer()

    assert recibido == [b"abc"]
    assert error.value.status_code == 400


async def test_clave_que_no_existe_404(carla: AsyncClient, mp4) -> None:
    respuesta = await subir(carla, mp4, clave="m09-no-existe")

    assert respuesta.status_code == 404
    assert "front matter" in respuesta.json()["detail"]


async def test_clave_mal_escrita_422(carla: AsyncClient, mp4) -> None:
    respuesta = await subir(carla, mp4, clave="Bienvenida")

    assert respuesta.status_code == 422


async def test_un_estudiante_no_sube(ana: AsyncClient, mp4) -> None:
    respuesta = await subir(ana, mp4)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "sin_permiso"


async def test_subir_exige_csrf(carla: AsyncClient, mp4) -> None:
    respuesta = await carla.put(
        f"/api/panel/videos/{CLAVE}", content=mp4, headers={"Content-Type": "video/mp4"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"


# --- Subtítulos --------------------------------------------------------------


async def test_subtitulos_antes_que_el_video(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, media: Path, mp4
) -> None:
    respuesta = await subir_vtt(carla, "es", VTT_ES)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["subtitulos"] == {"es": True, "en": False}
    assert respuesta.json()["disponible"] is False
    guardado = await fila(sesion_bd)
    assert NOMBRE_VTT.match(guardado.vtt_es)
    # Sin video, la lección todavía no los muestra.
    leccion = (await ana.get(LECCION)).json()
    assert leccion["videos"][0]["video"]["subtitulos"] == []

    await subir(carla, mp4)
    leccion = (await ana.get(LECCION)).json()
    assert leccion["videos"][0]["video"]["subtitulos"] == [
        {"idioma": "es", "url": f"/api/media/{guardado.id}/subtitulos/es"}
    ]


async def test_reemplazar_subtitulos_borra_los_anteriores(
    carla: AsyncClient, sesion_bd: AsyncSession, media: Path
) -> None:
    await subir_vtt(carla, "en", VTT_EN)
    await subir_vtt(carla, "en", VTT_EN)

    assert archivos(media) == [(await fila(sesion_bd)).vtt_en]


@pytest.mark.parametrize(
    ("texto", "detalle"),
    [
        ("1\n00:00.000 --> 00:01.000\nSin cabecera\n", "empieza por la línea WEBVTT"),
        ("WEBVTTX\n", "empieza por la línea WEBVTT"),
        ("WEBVTT\n\nCanción".encode("latin-1"), "UTF-8"),
    ],
)
async def test_subtitulos_invalidos_415(
    carla: AsyncClient, media: Path, texto: str | bytes, detalle: str
) -> None:
    respuesta = await subir_vtt(carla, "es", texto)

    assert respuesta.status_code == 415
    assert respuesta.json()["codigo"] == "vtt_invalido"
    assert detalle in respuesta.json()["detail"]
    assert archivos(media) == []


async def test_subtitulos_de_mas_de_1_mb_413(carla: AsyncClient) -> None:
    respuesta = await subir_vtt(carla, "es", "WEBVTT\n\n" + "x" * 1024**2)

    assert respuesta.status_code == 413


async def test_idioma_que_no_existe_422(carla: AsyncClient) -> None:
    respuesta = await subir_vtt(carla, "fr", VTT_ES)

    assert respuesta.status_code == 422


# --- Panel -------------------------------------------------------------------


async def test_listar_videos_con_su_estado(
    carla: AsyncClient, mp4, sesion_bd: AsyncSession
) -> None:
    await subir(carla, mp4)

    respuesta = await carla.get("/api/panel/videos")

    assert respuesta.status_code == 200
    videos = {v["clave"]: v for v in respuesta.json()}
    assert list(videos) == sorted(videos)
    assert set(videos) == {
        "m00-bienvenida",
        "m01-vpn-linux",
        "m01-vpn-macos",
        "m01-vpn-windows",
    }
    assert videos["m00-bienvenida"]["disponible"] is True
    assert videos["m00-bienvenida"]["subido_en"] is not None
    pendiente = videos["m01-vpn-linux"]
    assert pendiente["disponible"] is False
    assert pendiente["subido_por"] is None
    assert pendiente["subtitulos"] == {"es": False, "en": False}
    assert pendiente["lecciones"] == [
        {
            "id": pendiente["lecciones"][0]["id"],
            "slug": "vpn",
            "modulo": "m01",
            "modulo_numero": 1,
            "titulo": "La VPN",
        }
    ]


async def test_un_estudiante_no_ve_el_panel(ana: AsyncClient) -> None:
    assert (await ana.get("/api/panel/videos")).status_code == 403


# --- Entrega -----------------------------------------------------------------


async def test_con_nginx_responde_x_accel_redirect(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, mp4
) -> None:
    await subir(carla, mp4)
    await subir_vtt(carla, "es", VTT_ES)
    video = await fila(sesion_bd)

    respuesta = await ana.get(f"/api/media/{video.id}")
    subtitulos = await ana.get(f"/api/media/{video.id}/subtitulos/es")

    assert respuesta.status_code == 200
    assert respuesta.headers["x-accel-redirect"] == f"/media-interno/{video.archivo}"
    assert respuesta.headers["content-type"] == "video/mp4"
    assert respuesta.headers["cache-control"] == "private, no-cache"
    assert respuesta.content == b""
    assert subtitulos.headers["x-accel-redirect"] == f"/media-interno/{video.vtt_es}"
    assert subtitulos.headers["content-type"] == "text/vtt; charset=utf-8"


@pytest.mark.usefixtures("entrega_api")
async def test_en_desarrollo_la_api_manda_el_archivo_con_range(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, mp4
) -> None:
    await subir(carla, mp4)
    await subir_vtt(carla, "en", VTT_EN)
    video = await fila(sesion_bd)

    completo = await ana.get(f"/api/media/{video.id}")
    # DoD 3: adelantar el video es pedir un trozo con Range.
    trozo = await ana.get(f"/api/media/{video.id}", headers={"Range": "bytes=100-199"})
    subtitulos = await ana.get(f"/api/media/{video.id}/subtitulos/en")

    assert completo.status_code == 200
    assert completo.content == mp4
    assert "x-accel-redirect" not in completo.headers
    assert trozo.status_code == 206
    assert trozo.headers["content-range"] == f"bytes 100-199/{len(mp4)}"
    assert trozo.content == mp4[100:200]
    assert subtitulos.status_code == 200
    assert subtitulos.text == VTT_EN
    assert subtitulos.headers["content-type"] == "text/vtt; charset=utf-8"


async def test_sin_sesion_401(
    carla: AsyncClient, crear_cliente, app_bd: FastAPI, sesion_bd: AsyncSession, mp4
) -> None:
    """DoD 2."""
    await subir(carla, mp4)
    video = await fila(sesion_bd)
    anonimo = crear_cliente(app_bd)

    for url in (f"/api/media/{video.id}", f"/api/media/{video.id}/subtitulos/es"):
        respuesta = await anonimo.get(url)
        assert respuesta.status_code == 401
        assert "x-accel-redirect" not in respuesta.headers


async def test_un_modulo_bloqueado_no_esconde_el_video(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, mp4
) -> None:
    """Decisión del 5-nov: el bloqueo es para ir en orden, no para esconder."""
    await subir(carla, mp4, clave="m01-vpn-linux")
    video = await fila(sesion_bd, "m01-vpn-linux")

    assert (await ana.get("/api/cursos/induccion/lecciones/m01/vpn")).status_code == 403
    assert (await ana.get(f"/api/media/{video.id}")).status_code == 200


async def test_sin_subir_404(ana: AsyncClient, sesion_bd: AsyncSession) -> None:
    video = await fila(sesion_bd)

    for url in (
        f"/api/media/{video.id}",
        f"/api/media/{video.id}/subtitulos/es",
        "/api/media/999999999",
    ):
        respuesta = await ana.get(url)
        assert respuesta.status_code == 404, url
        assert respuesta.json()["codigo"] == "no_encontrado"


async def test_si_falta_el_archivo_404_y_no_x_accel(
    carla: AsyncClient, ana: AsyncClient, sesion_bd: AsyncSession, media: Path, mp4
) -> None:
    await subir(carla, mp4)
    video = await fila(sesion_bd)
    (media / video.archivo).unlink()

    respuesta = await ana.get(f"/api/media/{video.id}")

    assert respuesta.status_code == 404
    assert "x-accel-redirect" not in respuesta.headers


async def test_nunca_sale_de_la_carpeta_de_medios(
    ana: AsyncClient, sesion_bd: AsyncSession, tmp_path: Path
) -> None:
    """Aunque la base dijera otra cosa, solo se sirve lo que está en media/."""
    (tmp_path / "secreto.txt").write_text("no")
    video = await fila(sesion_bd)
    video.archivo = "../secreto.txt"
    await sesion_bd.flush()

    assert (await ana.get(f"/api/media/{video.id}")).status_code == 404


async def test_id_fuera_de_rango_422(ana: AsyncClient) -> None:
    assert (await ana.get(f"/api/media/{2**63}")).status_code == 422
