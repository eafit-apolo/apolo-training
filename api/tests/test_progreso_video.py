"""Avance del video (F-05): POST /api/progreso/video.

El curso de prueba (tests/ayuda_contenido.py), con la bienvenida sin su quiz
(`SIN_QUIZ`): m00/bienvenida (un video), m01/vpn (un video por sistema),
m01/ssh y m02/lectura (sin video). El video junto con el quiz está en
test_quizzes.py.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Leccion, ProgresoLeccion, Usuario, Video
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from app.services.progreso import segundos_para_ver
from tests.ayuda_contenido import SIN_QUIZ, armar_contenido
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

CURSO = "/api/cursos/induccion"
RUTA = "/api/progreso/video"


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content", SIN_QUIZ)
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def estudiante(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path
) -> Usuario:
    usuario = await crear_usuario(sesion_bd, "ana")
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    return usuario


async def id_de(bd: AsyncSession, slug: str) -> int:
    return await bd.scalar(select(Leccion.id).where(Leccion.slug == slug))


async def subir(bd: AsyncSession, clave: str, duracion: int = 100) -> int:
    """Hace como si el MP4 ya estuviera subido y devuelve el id del video."""
    return await bd.scalar(
        update(Video)
        .where(Video.clave == clave)
        .values(archivo=f"{clave}.mp4", duracion_seg=duracion)
        .returning(Video.id)
    )


async def reportar(
    cliente: AsyncClient, leccion_id: int, video_id: int, segundo: int
) -> Response:
    return await cliente.post(
        RUTA,
        json={"leccion_id": leccion_id, "video_id": video_id, "segundo": segundo},
        headers=con_csrf(cliente),
    )


async def fila(bd: AsyncSession, usuario: Usuario, leccion_id: int) -> ProgresoLeccion:
    return await bd.scalar(
        select(ProgresoLeccion)
        .where(
            ProgresoLeccion.usuario_id == usuario.id,
            ProgresoLeccion.leccion_id == leccion_id,
        )
        .execution_options(populate_existing=True)
    )


def estados(curso: dict) -> dict[str, str]:
    return {m["slug"]: m["estado"] for m in curso["modulos"]}


@pytest.mark.parametrize(
    ("duracion", "umbral"), [(100, 90), (101, 91), (5, 5), (1, 1), (299, 270)]
)
def test_el_umbral_es_el_90_por_ciento_redondeado_hacia_arriba(
    duracion: int, umbral: int
) -> None:
    assert segundos_para_ver(duracion) == umbral


async def test_el_primer_reporte_guarda_la_posicion_y_la_leccion_la_trae(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")

    respuesta = await reportar(cliente_bd, leccion, video, 42)

    assert respuesta.status_code == 200
    progreso = respuesta.json()
    assert progreso["leccion_id"] == leccion
    assert (progreso["video_posicion_seg"], progreso["video_max_seg"]) == (42, 42)
    assert progreso["video_completo"] is False
    assert progreso["completada"] is False
    assert progreso["completada_en"] is None
    cuerpo = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()
    assert cuerpo["progreso"]["video_posicion_seg"] == 42


async def test_al_retroceder_se_reanuda_ahi_pero_el_maximo_se_queda(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")

    await reportar(cliente_bd, leccion, video, 60)
    progreso = (await reportar(cliente_bd, leccion, video, 15)).json()

    assert (progreso["video_posicion_seg"], progreso["video_max_seg"]) == (15, 60)
    filas = await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion))
    assert filas == 1


async def test_al_90_por_ciento_el_video_queda_visto_y_la_leccion_completa(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")

    casi = (await reportar(cliente_bd, leccion, video, 89)).json()
    assert casi["video_completo"] is False
    assert casi["completada"] is False

    visto = (await reportar(cliente_bd, leccion, video, 90)).json()

    assert visto["video_completo"] is True
    assert visto["completada"] is True
    assert visto["completada_en"] is not None
    # El quiz todavía no bloquea (B-06): m00 queda completo y se abre m01.
    curso = (await cliente_bd.get(CURSO)).json()
    assert estados(curso) == {"m00": "completo", "m01": "en_curso", "m02": "bloqueado"}


async def test_saltar_al_90_por_ciento_en_el_primer_reporte_tambien_cuenta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")

    progreso = (await reportar(cliente_bd, leccion, video, 90)).json()

    assert progreso["video_completo"] is True
    assert progreso["completada"] is True


async def test_si_suben_un_video_mas_largo_lo_visto_sigue_visto(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")
    await reportar(cliente_bd, leccion, video, 95)
    # El instructor lo reemplaza por uno de 200 s: 95 ya no es el 90 %.
    await subir(sesion_bd, "m00-bienvenida", duracion=200)

    progreso = (await reportar(cliente_bd, leccion, video, 10)).json()

    assert progreso["video_max_seg"] == 95
    assert progreso["video_completo"] is True
    assert progreso["completada"] is True


async def test_visto_y_completa_no_vuelven_atras(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    # Dentro de la transacción de la prueba now() no cambia: la fecha se pone
    # a mano, en el pasado, para ver que no se pisa.
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")
    antes = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id,
            leccion_id=leccion,
            video_posicion_seg=95,
            video_max_seg=95,
            video_completo=True,
            completada_en=antes,
        )
    )
    await sesion_bd.flush()

    progreso = (await reportar(cliente_bd, leccion, video, 3)).json()

    assert progreso["video_posicion_seg"] == 3
    assert progreso["video_max_seg"] == 95
    assert progreso["video_completo"] is True
    assert datetime.fromisoformat(progreso["completada_en"]) == antes


async def test_una_leccion_marcada_a_mano_conserva_su_fecha(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    # Se completó a mano antes de que subieran el video (F-04); el primer
    # reporte crea el avance del video sin tocar la fecha.
    leccion = await id_de(sesion_bd, "bienvenida")
    antes = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id, leccion_id=leccion, completada_en=antes
        )
    )
    await sesion_bd.flush()
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)

    progreso = (await reportar(cliente_bd, leccion, video, 20)).json()

    assert progreso["completada"] is True
    assert progreso["video_completo"] is False
    assert datetime.fromisoformat(progreso["completada_en"]) == antes


async def test_un_segundo_mayor_que_la_duracion_se_recorta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")

    progreso = (await reportar(cliente_bd, leccion, video, 5000)).json()

    assert (progreso["video_posicion_seg"], progreso["video_max_seg"]) == (100, 100)
    assert progreso["video_completo"] is True


async def test_con_el_video_visto_completar_ya_no_da_409(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")
    completar = f"/api/lecciones/{leccion}/completar"
    antes = await cliente_bd.post(completar, headers=con_csrf(cliente_bd))
    assert antes.status_code == 409

    await reportar(cliente_bd, leccion, video, 90)
    despues = await cliente_bd.post(completar, headers=con_csrf(cliente_bd))

    assert despues.status_code == 200
    assert despues.json()["completada"] is True


async def test_en_la_vpn_el_90_por_ciento_es_del_video_que_se_ve(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    estudiante: Usuario,
) -> None:
    # m01 se abre con m00 completo.
    bienvenida = await id_de(sesion_bd, "bienvenida")
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id, leccion_id=bienvenida, completada_en=func.now()
        )
    )
    await sesion_bd.flush()
    windows = await subir(sesion_bd, "m01-vpn-windows", duracion=200)
    linux = await subir(sesion_bd, "m01-vpn-linux", duracion=100)
    vpn = await id_de(sesion_bd, "vpn")

    en_windows = (await reportar(cliente_bd, vpn, windows, 90)).json()
    assert en_windows["video_completo"] is False

    en_linux = (await reportar(cliente_bd, vpn, linux, 90)).json()
    assert en_linux["video_completo"] is True
    assert en_linux["completada"] is True


async def test_un_video_sin_subir_da_404(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    leccion = await id_de(sesion_bd, "bienvenida")
    sin_subir = await sesion_bd.scalar(
        select(Video.id).where(Video.clave == "m00-bienvenida")
    )

    respuesta = await reportar(cliente_bd, leccion, sin_subir, 10)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"
    assert (
        await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion)) == 0
    )


async def test_un_video_de_otra_leccion_o_que_no_existe_da_404(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await subir(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")
    de_otra = await subir(sesion_bd, "m01-vpn-linux")

    for video in (de_otra, 999999999):
        respuesta = await reportar(cliente_bd, leccion, video, 10)
        assert respuesta.status_code == 404, video
    assert (
        await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion)) == 0
    )


async def test_una_leccion_que_no_existe_o_no_esta_publicada_da_404(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida")
    assert (await reportar(cliente_bd, 999999999, video, 10)).status_code == 404

    await sesion_bd.execute(
        update(Leccion).where(Leccion.slug == "bienvenida").values(publicada=False)
    )
    leccion = await id_de(sesion_bd, "bienvenida")
    assert (await reportar(cliente_bd, leccion, video, 10)).status_code == 404


@pytest.mark.parametrize("rol", ["estudiante", "instructor", "admin"])
async def test_en_un_modulo_bloqueado_no_se_guarda_con_ningun_rol(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path, rol: str
) -> None:
    await crear_usuario(sesion_bd, "carla", rol=rol)
    await ingresar(cliente_bd, "carla")
    video = await subir(sesion_bd, "m01-vpn-linux")

    respuesta = await reportar(cliente_bd, await id_de(sesion_bd, "vpn"), video, 10)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "modulo_bloqueado"
    assert respuesta.json()["bloqueado_por"]["slug"] == "m00"
    assert (
        await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion)) == 0
    )


async def test_el_avance_es_de_cada_usuario(
    cliente_bd: AsyncClient,
    crear_cliente,
    app_bd,
    sesion_bd: AsyncSession,
    estudiante: Usuario,
) -> None:
    bruno = await crear_usuario(sesion_bd, "bruno")
    otro = crear_cliente(app_bd)
    await ingresar(otro, "bruno")
    video = await subir(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")

    await reportar(cliente_bd, leccion, video, 50)
    await reportar(otro, leccion, video, 20)

    assert (await fila(sesion_bd, estudiante, leccion)).video_posicion_seg == 50
    assert (await fila(sesion_bd, bruno, leccion)).video_posicion_seg == 20


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"leccion_id": 1, "video_id": 1, "segundo": -1},
        {"leccion_id": 1, "video_id": 1, "segundo": 2**31},
        {"leccion_id": 0, "video_id": 1, "segundo": 10},
        {"leccion_id": 1, "video_id": 2**63, "segundo": 10},
        {"leccion_id": 1, "segundo": 10},
        {"leccion_id": 1, "video_id": 1, "segundo": "diez"},
    ],
)
async def test_un_cuerpo_invalido_da_422(
    cliente_bd: AsyncClient, estudiante: Usuario, cuerpo: dict
) -> None:
    respuesta = await cliente_bd.post(RUTA, json=cuerpo, headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"


async def test_sin_el_token_csrf_da_403(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")

    respuesta = await cliente_bd.post(
        RUTA, json={"leccion_id": leccion, "video_id": video, "segundo": 10}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"
