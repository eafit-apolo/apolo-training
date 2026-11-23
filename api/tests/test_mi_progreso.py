"""Mi progreso, la parte de la B-07: prácticas, sincronización, graduación,
`aprobado` y `siguiente_paso` (GET /api/me/progreso). La parte de la B-06
(avance por módulo y por lección) está en test_quizzes.py.

El curso de prueba (tests/ayuda_contenido.py): m00/bienvenida; m01/vpn y
m01/ssh (con la práctica `conexion`); m02/lectura. Las otras seis prácticas no
las nombra ninguna lección.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora
from app.models import (
    Curso,
    Graduacion,
    Leccion,
    Practica,
    ProgresoLeccion,
    Sincronizacion,
    Usuario,
)
from app.models.valores import PRACTICAS
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import armar_contenido
from tests.ayuda_sesion import crear_usuario, ingresar

MI = "/api/me/progreso"


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def ana(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path
) -> Usuario:
    usuario = await crear_usuario(sesion_bd, "ana")
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    return usuario


async def completar(bd: AsyncSession, usuario: Usuario, *slugs: str) -> None:
    for slug in slugs:
        leccion_id = await bd.scalar(select(Leccion.id).where(Leccion.slug == slug))
        bd.add(
            ProgresoLeccion(
                usuario_id=usuario.id, leccion_id=leccion_id, completada_en=ahora()
            )
        )
    await bd.flush()


async def practica(
    bd: AsyncSession, usuario: Usuario, nombre: str, estado: str = "aprobado", **mas
) -> None:
    bd.add(
        Practica(
            usuario_id=usuario.id,
            practica=nombre,
            estado=estado,
            fecha=datetime(2026, 11, 23, 15, tzinfo=UTC),
            **mas,
        )
    )
    await bd.flush()


async def graduacion(bd: AsyncSession, usuario: Usuario, estado: str, **mas) -> None:
    bd.add(
        Graduacion(
            usuario_id=usuario.id,
            cluster="apolo2",
            jobid="98765",
            salida_verificador="[APROBADO] graduacion",
            estado=estado,
            **mas,
        )
    )
    await bd.flush()


async def todo_menos_la_graduacion(bd: AsyncSession, usuario: Usuario) -> None:
    await completar(bd, usuario, "bienvenida", "vpn", "ssh", "lectura")
    for nombre in PRACTICAS:
        await practica(bd, usuario, nombre)


async def mi(cliente: AsyncClient) -> dict:
    respuesta = await cliente.get(MI)
    assert respuesta.status_code == 200
    return respuesta.json()


def paso(progreso: dict) -> tuple:
    siguiente = progreso["siguiente_paso"]
    leccion = siguiente["leccion"]
    return (
        siguiente["tipo"],
        f"{leccion['modulo']}/{leccion['slug']}" if leccion else None,
        siguiente["lab"],
    )


async def test_al_empezar(cliente_bd: AsyncClient, ana: Usuario) -> None:
    progreso = await mi(cliente_bd)

    assert progreso["labs"] == [
        {
            "lab": nombre,
            "estado": "sin_intentar",
            "jobid": None,
            "fecha": None,
            "detalle": None,
        }
        for nombre in PRACTICAS
    ]
    assert progreso["ultima_sincronizacion"] is None
    assert progreso["sincronizacion_atrasada"] is False
    assert progreso["graduacion"] is None
    assert progreso["aprobado"] is False
    assert progreso["siguiente_paso"] == {
        "tipo": "leccion",
        "leccion": {
            "id": progreso["modulos"][0]["lecciones"][0]["id"],
            "slug": "bienvenida",
            "modulo": "m00",
            "modulo_numero": 0,
            "titulo": "Bienvenida",
        },
        "lab": None,
    }


async def test_muestra_cada_practica_como_la_sincronizo_la_vm(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await practica(sesion_bd, ana, "memoria", jobid="1042", detalle="Con --mem=4G")
    await practica(sesion_bd, ana, "nucleos", "intentado", jobid="1050")

    labs = {lab["lab"]: lab for lab in (await mi(cliente_bd))["labs"]}

    assert list(labs) == list(PRACTICAS)
    assert labs["memoria"] == {
        "lab": "memoria",
        "estado": "aprobado",
        "jobid": "1042",
        "fecha": "2026-11-23T15:00:00Z",
        "detalle": "Con --mem=4G",
    }
    assert (labs["nucleos"]["estado"], labs["nucleos"]["jobid"]) == (
        "intentado",
        "1050",
    )
    assert labs["paralelo"]["estado"] == "sin_intentar"


async def test_las_practicas_son_de_cada_usuario(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    bruno = await crear_usuario(sesion_bd, "bruno")
    await practica(sesion_bd, bruno, "memoria")
    await graduacion(sesion_bd, bruno, "enviada")

    progreso = await mi(cliente_bd)

    assert {lab["estado"] for lab in progreso["labs"]} == {"sin_intentar"}
    assert progreso["graduacion"] is None


async def test_ultima_sincronizacion_y_atraso(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    vieja = ahora() - timedelta(minutes=16)
    sesion_bd.add(Sincronizacion(registros=0, aceptados=0, recibida_en=vieja))
    await sesion_bd.flush()
    atrasada = await mi(cliente_bd)
    reciente = ahora() - timedelta(minutes=14)
    sesion_bd.add(Sincronizacion(registros=3, aceptados=3, recibida_en=reciente))
    await sesion_bd.flush()
    al_dia = await mi(cliente_bd)

    assert datetime.fromisoformat(atrasada["ultima_sincronizacion"]) == vieja
    assert atrasada["sincronizacion_atrasada"] is True
    assert datetime.fromisoformat(al_dia["ultima_sincronizacion"]) == reciente
    assert al_dia["sincronizacion_atrasada"] is False


async def test_muestra_la_graduacion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await graduacion(sesion_bd, ana, "rechazada", comentario="Falta --mem=1G")

    progreso = await mi(cliente_bd)

    assert progreso["graduacion"]["estado"] == "rechazada"
    assert progreso["graduacion"]["comentario"] == "Falta --mem=1G"
    assert progreso["graduacion"]["salida_verificador"] == "[APROBADO] graduacion"


# --- Siguiente paso, en el orden del curso ----------------------------------------


async def test_la_practica_de_un_modulo_va_antes_que_el_siguiente_modulo(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await completar(sesion_bd, ana, "bienvenida", "vpn")
    assert paso(await mi(cliente_bd)) == ("leccion", "m01/ssh", None)

    await completar(sesion_bd, ana, "ssh")
    # m01 completo y m02 abierto, pero falta la práctica de m01.
    assert paso(await mi(cliente_bd)) == ("laboratorio", None, "conexion")

    await practica(sesion_bd, ana, "conexion", "intentado")
    assert paso(await mi(cliente_bd)) == ("laboratorio", None, "conexion")

    await sesion_bd.execute(update(Practica).values(estado="aprobado"))
    assert paso(await mi(cliente_bd)) == ("leccion", "m02/lectura", None)


async def test_despues_las_practicas_que_ninguna_leccion_nombra(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await completar(sesion_bd, ana, "bienvenida", "vpn", "ssh", "lectura")
    await practica(sesion_bd, ana, "conexion")
    await practica(sesion_bd, ana, "terminal")

    assert paso(await mi(cliente_bd)) == ("laboratorio", None, "archivos")


async def test_sin_curso_publicado_siguen_las_practicas(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await sesion_bd.execute(update(Curso).values(publicado=False))
    for nombre in PRACTICAS:
        await practica(sesion_bd, ana, nombre)
    await graduacion(sesion_bd, ana, "aprobada", qos_aplicada_en=ahora())

    progreso = await mi(cliente_bd)

    # Sin lecciones no hay curso que aprobar.
    assert progreso["aprobado"] is False
    assert paso(progreso) == ("terminado", None, None)


@pytest.mark.parametrize(
    ("estado", "qos", "esperado", "aprobado"),
    [
        (None, False, "graduacion", False),
        ("enviada", False, "esperar_revision", False),
        ("rechazada", False, "graduacion", False),
        ("aprobada", False, "esperar_qos", True),
        ("aprobada", True, "terminado", True),
    ],
)
async def test_al_final_la_graduacion_y_la_qos(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    ana: Usuario,
    estado: str | None,
    qos: bool,
    esperado: str,
    aprobado: bool,
) -> None:
    await todo_menos_la_graduacion(sesion_bd, ana)
    if estado:
        await graduacion(
            sesion_bd, ana, estado, qos_aplicada_en=ahora() if qos else None
        )

    progreso = await mi(cliente_bd)

    assert paso(progreso) == (esperado, None, None)
    assert progreso["aprobado"] is aprobado


async def test_no_aprueba_si_falta_una_practica(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await completar(sesion_bd, ana, "bienvenida", "vpn", "ssh", "lectura")
    for nombre in PRACTICAS[:-1]:
        await practica(sesion_bd, ana, nombre)
    await practica(sesion_bd, ana, PRACTICAS[-1], "intentado")
    await graduacion(sesion_bd, ana, "aprobada")

    progreso = await mi(cliente_bd)

    assert progreso["aprobado"] is False
    assert paso(progreso) == ("laboratorio", None, "paralelo")


async def test_no_aprueba_si_falta_una_leccion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await todo_menos_la_graduacion(sesion_bd, ana)
    await graduacion(sesion_bd, ana, "aprobada")
    await sesion_bd.execute(
        update(ProgresoLeccion)
        .where(
            ProgresoLeccion.leccion_id
            == select(Leccion.id).where(Leccion.slug == "lectura").scalar_subquery()
        )
        .values(completada_en=None)
    )

    progreso = await mi(cliente_bd)

    assert progreso["aprobado"] is False
    assert paso(progreso) == ("leccion", "m02/lectura", None)
