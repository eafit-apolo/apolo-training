"""«Marcar como completada» (F-04): POST /api/lecciones/{id}/completar.

El curso de prueba (tests/ayuda_contenido.py): m00/bienvenida (video sin subir
y quiz), m01/vpn (un video por sistema) y m01/ssh (práctica y quiz), y
m02/lectura (solo texto).
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
from tests.ayuda_contenido import armar_contenido
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

CURSO = "/api/cursos/induccion"


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
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


async def completar(cliente: AsyncClient, bd: AsyncSession, slug: str) -> Response:
    leccion = await id_de(bd, slug)
    return await cliente.post(
        f"/api/lecciones/{leccion}/completar", headers=con_csrf(cliente)
    )


async def subir_video(bd: AsyncSession, clave: str) -> None:
    await bd.execute(
        update(Video).where(Video.clave == clave).values(archivo=f"{clave}-es.mp4")
    )


def estados(curso: dict) -> dict[str, str]:
    return {m["slug"]: m["estado"] for m in curso["modulos"]}


async def test_completar_guarda_y_abre_el_modulo_siguiente(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    respuesta = await completar(cliente_bd, sesion_bd, "bienvenida")

    assert respuesta.status_code == 200
    progreso = respuesta.json()
    assert progreso["leccion_id"] == await id_de(sesion_bd, "bienvenida")
    assert progreso["completada"] is True
    assert progreso["completada_en"] is not None
    curso = (await cliente_bd.get(CURSO)).json()
    assert estados(curso) == {"m00": "completo", "m01": "en_curso", "m02": "bloqueado"}
    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()
    assert leccion["progreso"]["completada"] is True


async def test_completar_dos_veces_no_cambia_la_fecha(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    # Dentro de la transacción de la prueba now() no cambia: la primera fecha
    # se pone a mano, en el pasado, para ver que no se pisa.
    antes = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id,
            leccion_id=await id_de(sesion_bd, "bienvenida"),
            completada_en=antes,
        )
    )
    await sesion_bd.flush()

    respuesta = await completar(cliente_bd, sesion_bd, "bienvenida")
    otra_vez = await completar(cliente_bd, sesion_bd, "bienvenida")

    assert respuesta.status_code == otra_vez.status_code == 200
    assert datetime.fromisoformat(otra_vez.json()["completada_en"]) == antes
    filas = await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion))
    assert filas == 1


async def test_conserva_el_avance_del_video_que_ya_habia(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id,
            leccion_id=await id_de(sesion_bd, "bienvenida"),
            video_posicion_seg=30,
            video_max_seg=45,
        )
    )
    await sesion_bd.flush()

    progreso = (await completar(cliente_bd, sesion_bd, "bienvenida")).json()

    assert progreso["completada"] is True
    assert (progreso["video_posicion_seg"], progreso["video_max_seg"]) == (30, 45)


async def test_un_video_subido_sin_ver_da_409(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await subir_video(sesion_bd, "m00-bienvenida")

    respuesta = await completar(cliente_bd, sesion_bd, "bienvenida")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "requisitos_pendientes"
    assert (
        await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion)) == 0
    )


async def test_con_el_video_visto_si_se_completa(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await subir_video(sesion_bd, "m00-bienvenida")
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id,
            leccion_id=await id_de(sesion_bd, "bienvenida"),
            video_completo=True,
        )
    )
    await sesion_bd.flush()

    respuesta = await completar(cliente_bd, sesion_bd, "bienvenida")

    assert respuesta.status_code == 200
    assert respuesta.json()["video_completo"] is True


async def test_una_leccion_ya_completa_sigue_completa_si_luego_suben_el_video(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    primera = (await completar(cliente_bd, sesion_bd, "bienvenida")).json()
    await subir_video(sesion_bd, "m00-bienvenida")

    segunda = await completar(cliente_bd, sesion_bd, "bienvenida")

    assert segunda.status_code == 200
    assert segunda.json()["completada_en"] == primera["completada_en"]


async def test_el_quiz_y_las_practicas_todavia_no_bloquean(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    for slug in ("bienvenida", "vpn", "ssh"):
        respuesta = await completar(cliente_bd, sesion_bd, slug)
        assert respuesta.status_code == 200, slug

    curso = (await cliente_bd.get(CURSO)).json()
    assert estados(curso)["m02"] == "en_curso"


async def test_el_avance_es_de_cada_usuario(
    cliente_bd: AsyncClient,
    crear_cliente,
    app_bd,
    sesion_bd: AsyncSession,
    estudiante: Usuario,
) -> None:
    await crear_usuario(sesion_bd, "bruno")
    otro = crear_cliente(app_bd)
    await ingresar(otro, "bruno")

    await completar(cliente_bd, sesion_bd, "bienvenida")

    assert estados((await cliente_bd.get(CURSO)).json())["m00"] == "completo"
    assert estados((await otro.get(CURSO)).json())["m00"] == "en_curso"


@pytest.mark.parametrize("rol", ["estudiante", "instructor", "admin"])
async def test_un_modulo_bloqueado_no_se_completa_con_ningun_rol(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path, rol: str
) -> None:
    await crear_usuario(sesion_bd, "carla", rol=rol)
    await ingresar(cliente_bd, "carla")

    respuesta = await completar(cliente_bd, sesion_bd, "lectura")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "modulo_bloqueado"
    assert respuesta.json()["bloqueado_por"]["slug"] == "m01"
    assert (
        await sesion_bd.scalar(select(func.count()).select_from(ProgresoLeccion)) == 0
    )


async def test_lo_que_no_existe_o_no_esta_publicado_da_404(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    respuesta = await cliente_bd.post(
        "/api/lecciones/999999999/completar", headers=con_csrf(cliente_bd)
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"

    await sesion_bd.execute(
        update(Leccion).where(Leccion.slug == "bienvenida").values(publicada=False)
    )
    assert (await completar(cliente_bd, sesion_bd, "bienvenida")).status_code == 404


@pytest.mark.parametrize("leccion", ["0", str(2**63), "abc"])
async def test_un_id_invalido_da_422(
    cliente_bd: AsyncClient, estudiante: Usuario, leccion: str
) -> None:
    respuesta = await cliente_bd.post(
        f"/api/lecciones/{leccion}/completar", headers=con_csrf(cliente_bd)
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"


async def test_sin_el_token_csrf_da_403(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    leccion = await id_de(sesion_bd, "bienvenida")

    respuesta = await cliente_bd.post(f"/api/lecciones/{leccion}/completar")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"
