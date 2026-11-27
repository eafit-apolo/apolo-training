"""Resumen del panel de instructor (F-08): `GET /api/panel/resumen`.

El curso de prueba (tests/ayuda_contenido.py) tiene tres módulos: m00
(bienvenida), m01 (vpn y ssh) y m02 (lectura).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora
from app.models import Curso, Graduacion, Sincronizacion, Usuario
from app.models.valores import PRACTICAS
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import MODULO, armar_contenido
from tests.ayuda_progreso import completar, graduacion, practica
from tests.ayuda_sesion import crear_usuario, ingresar

RESUMEN = "/api/panel/resumen"
LECCIONES = ("bienvenida", "vpn", "ssh", "lectura")
# m00 y m01 traducidos; m02 sin traducir.
EN = {
    "en/m00/_modulo.md": MODULO.format(id="m00", titulo="Welcome", duracion=3),
    "en/m01/_modulo.md": MODULO.format(id="m01", titulo="Connecting", duracion=9),
}


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def carla(cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido) -> Usuario:
    instructora = await crear_usuario(sesion_bd, "carla", rol="instructor")
    assert (await ingresar(cliente_bd, "carla")).status_code == 200
    return instructora


async def resumen(cliente: AsyncClient) -> dict:
    respuesta = await cliente.get(RESUMEN)
    assert respuesta.status_code == 200
    return respuesta.json()


async def con_todo(
    bd: AsyncSession, username: str, *, revision: str = "aprobada", **usuario
) -> Usuario:
    """Las cuatro lecciones, las siete prácticas y la graduación."""
    persona = await crear_usuario(bd, username, **usuario)
    await completar(bd, persona, *LECCIONES)
    for nombre in PRACTICAS:
        await practica(bd, persona, nombre)
    await graduacion(bd, persona, revision)
    return persona


def por_modulo(datos: dict) -> list[tuple[int, int]]:
    return [(m["numero"], m["completos"]) for m in datos["avance_por_modulo"]]


async def test_sin_estudiantes_todo_en_cero(
    cliente_bd: AsyncClient, carla: Usuario
) -> None:
    assert await resumen(cliente_bd) == {
        "estudiantes_activos": 0,
        "sin_empezar": 0,
        "en_curso": 0,
        "aprobados": 0,
        "graduaciones_por_revisar": 0,
        "aprobados_pendientes_qos": 0,
        "ultima_sincronizacion": None,
        "avance_por_modulo": [
            {"numero": 0, "titulo": "Bienvenida", "completos": 0},
            {"numero": 1, "titulo": "Conexión", "completos": 0},
            {"numero": 2, "titulo": "Lectura", "completos": 0},
        ],
    }


async def test_las_cifras_de_los_estudiantes_activos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    await crear_usuario(sesion_bd, "ana")  # sin empezar
    bruno = await crear_usuario(sesion_bd, "bruno")  # m00
    await completar(sesion_bd, bruno, "bienvenida")
    dora = await crear_usuario(sesion_bd, "dora")  # m00 y m01, y dos prácticas
    await completar(sesion_bd, dora, "bienvenida", "vpn", "ssh")
    await practica(sesion_bd, dora, "conexion")
    await practica(sesion_bd, dora, "memoria", estado="intentado")
    await con_todo(sesion_bd, "eva")  # aprobada, sin QOS
    fabio = await con_todo(sesion_bd, "fabio")  # aprobado, con QOS
    await sesion_bd.execute(
        update(Graduacion)
        .where(Graduacion.usuario_id == fabio.id)
        .values(qos_aplicada_en=ahora())
    )
    await con_todo(sesion_bd, "gema", revision="enviada")  # todo, sin revisar

    datos = await resumen(cliente_bd)

    assert datos["estudiantes_activos"] == 6
    assert datos["sin_empezar"] == 1
    assert datos["en_curso"] == 3
    assert datos["aprobados"] == 2
    assert datos["graduaciones_por_revisar"] == 1
    assert datos["aprobados_pendientes_qos"] == 1
    assert por_modulo(datos) == [(0, 5), (1, 4), (2, 3)]


async def test_aprobado_es_todo_no_solo_la_graduacion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    # Graduación aprobada, pero la práctica paralelo quedó en intentado.
    ana = await crear_usuario(sesion_bd, "ana")
    await completar(sesion_bd, ana, *LECCIONES)
    for nombre in PRACTICAS:
        estado = "intentado" if nombre == "paralelo" else "aprobado"
        await practica(sesion_bd, ana, nombre, estado=estado)
    await graduacion(sesion_bd, ana, "aprobada")

    datos = await resumen(cliente_bd)

    assert (datos["aprobados"], datos["en_curso"]) == (0, 1)
    assert datos["aprobados_pendientes_qos"] == 0


async def test_instructores_admins_y_bajas_no_cuentan(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    await completar(sesion_bd, carla, *LECCIONES)
    await con_todo(sesion_bd, "diego", rol="admin")
    await con_todo(sesion_bd, "elena", activo=False)
    await crear_usuario(sesion_bd, "ana")

    datos = await resumen(cliente_bd)

    assert datos["estudiantes_activos"] == 1
    assert datos["sin_empezar"] == 1
    assert datos["aprobados"] == 0
    assert datos["aprobados_pendientes_qos"] == 0
    assert por_modulo(datos) == [(0, 0), (1, 0), (2, 0)]


async def test_las_graduaciones_por_revisar_son_las_enviadas(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    for username, estado in (
        ("ana", "enviada"),
        ("bruno", "enviada"),
        ("dora", "rechazada"),
        ("eva", "aprobada"),
    ):
        await graduacion(sesion_bd, await crear_usuario(sesion_bd, username), estado)

    datos = await resumen(cliente_bd)
    lista = await cliente_bd.get(
        "/api/panel/graduaciones", params={"estado": "enviada"}
    )

    assert datos["graduaciones_por_revisar"] == 2 == len(lista.json())


async def test_una_leccion_de_un_modulo_bloqueado_no_cuenta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    # Hizo m01 sin terminar m00: como en Mi progreso, no cuenta.
    ana = await crear_usuario(sesion_bd, "ana")
    await completar(sesion_bd, ana, "vpn", "ssh")

    datos = await resumen(cliente_bd)

    assert datos["sin_empezar"] == 1
    assert datos["en_curso"] == 0
    assert por_modulo(datos) == [(0, 0), (1, 0), (2, 0)]


async def test_una_practica_aprobada_ya_es_empezar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    await practica(sesion_bd, ana, "conexion")
    bruno = await crear_usuario(sesion_bd, "bruno")
    await practica(sesion_bd, bruno, "conexion", estado="intentado")

    datos = await resumen(cliente_bd)

    assert (datos["sin_empezar"], datos["en_curso"]) == (1, 1)


async def test_la_ultima_sincronizacion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    vieja = datetime(2026, 11, 26, 15, tzinfo=UTC)
    for recibida in (vieja, vieja + timedelta(minutes=5)):
        sesion_bd.add(Sincronizacion(registros=1, aceptados=1, recibida_en=recibida))
    await sesion_bd.flush()

    datos = await resumen(cliente_bd)

    assert datetime.fromisoformat(datos["ultima_sincronizacion"]) == vieja + timedelta(
        minutes=5
    )


async def test_los_titulos_en_el_idioma_del_perfil(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, tmp_path: Path, carla: Usuario
) -> None:
    raiz = armar_contenido(tmp_path / "content", EN)
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    carla.idioma = "en"
    await sesion_bd.flush()

    datos = await resumen(cliente_bd)

    # m02 no tiene traducción: queda en español.
    assert [m["titulo"] for m in datos["avance_por_modulo"]] == [
        "Welcome",
        "Connecting",
        "Lectura",
    ]


async def test_los_titulos_en_el_idioma_pedido(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, tmp_path: Path, carla: Usuario
) -> None:
    raiz = armar_contenido(tmp_path / "content", EN)
    await cargar_contenido(sesion_bd, leer_contenido(raiz))

    en = await cliente_bd.get(RESUMEN, params={"lang": "en"})

    # carla tiene el perfil en español; manda ?lang=.
    assert [m["titulo"] for m in en.json()["avance_por_modulo"]][:2] == [
        "Welcome",
        "Connecting",
    ]


async def test_sin_curso_publicado_no_hay_modulos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, carla: Usuario
) -> None:
    await sesion_bd.execute(update(Curso).values(publicado=False))
    await crear_usuario(sesion_bd, "ana")

    datos = await resumen(cliente_bd)

    assert datos["avance_por_modulo"] == []
    assert (datos["estudiantes_activos"], datos["sin_empezar"]) == (1, 1)


async def test_un_admin_tambien_lo_ve(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido
) -> None:
    await crear_usuario(sesion_bd, "diego", rol="admin")
    assert (await ingresar(cliente_bd, "diego")).status_code == 200

    assert (await cliente_bd.get(RESUMEN)).status_code == 200


async def test_un_estudiante_no(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido
) -> None:
    await crear_usuario(sesion_bd, "ana")
    assert (await ingresar(cliente_bd, "ana")).status_code == 200

    respuesta = await cliente_bd.get(RESUMEN)

    assert respuesta.status_code == 403
