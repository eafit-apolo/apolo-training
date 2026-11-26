"""Aprobados pendientes de QOS, «QOS aplicada» y el CSV de la medición (B-08).

El curso de prueba (tests/ayuda_contenido.py) tiene cuatro lecciones:
m00/bienvenida, m01/vpn, m01/ssh y m02/lectura.
"""

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Auditoria,
    Graduacion,
    Leccion,
    Practica,
    ProgresoLeccion,
    Usuario,
)
from app.models.valores import PRACTICAS
from app.services import progreso
from app.services.aprobados import COLUMNAS_CSV
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import armar_contenido
from tests.ayuda_progreso import completar, graduacion, practica
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

PENDIENTES = "/api/admin/aprobados-pendientes"
CSV = "/api/panel/export/progreso.csv"
LECCIONES = ("bienvenida", "vpn", "ssh", "lectura")


def dia(n: int) -> datetime:
    return datetime(2026, 11, n, 15, tzinfo=UTC)


DIA_10, DIA_11, DIA_12 = dia(10), dia(11), dia(12)


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def diego(cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido) -> Usuario:
    admin = await crear_usuario(sesion_bd, "diego", rol="admin")
    assert (await ingresar(cliente_bd, "diego")).status_code == 200
    return admin


async def aprobado(
    bd: AsyncSession,
    username: str,
    *,
    leccion: datetime = DIA_10,
    practicas: datetime = DIA_11,
    revision: datetime = DIA_12,
    **usuario,
) -> Usuario:
    """Un usuario con todo: lecciones, las siete prácticas y la graduación
    aprobada, con las fechas dadas."""
    persona = await crear_usuario(bd, username, **usuario)
    await completar(bd, persona, *LECCIONES)
    await bd.execute(
        update(ProgresoLeccion)
        .where(ProgresoLeccion.usuario_id == persona.id)
        .values(completada_en=leccion)
    )
    for nombre in PRACTICAS:
        await practica(bd, persona, nombre, sincronizado_en=practicas)
    await graduacion(bd, persona, "aprobada", revisada_en=revision)
    return persona


async def pendientes(cliente: AsyncClient) -> list[dict]:
    respuesta = await cliente.get(PENDIENTES)
    assert respuesta.status_code == 200
    return respuesta.json()


async def marcar(cliente: AsyncClient, username: str, csrf: bool = True):
    return await cliente.post(
        f"{PENDIENTES}/{username}/qos-aplicada",
        headers=con_csrf(cliente) if csrf else {},
    )


async def auditoria(bd: AsyncSession, accion: str) -> list[Auditoria]:
    return list(
        await bd.scalars(
            select(Auditoria).where(Auditoria.accion == accion).order_by(Auditoria.id)
        )
    )


# --- Aprobados pendientes --------------------------------------------------------------


async def test_los_aprobados_sin_qos_de_los_mas_viejos_a_los_nuevos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    # aprobado_en es la última de las tres fechas.
    await aprobado(sesion_bd, "ana", revision=dia(20))
    await aprobado(sesion_bd, "bruno", leccion=dia(15), revision=dia(14))
    await aprobado(sesion_bd, "carla", practicas=dia(18))

    assert await pendientes(cliente_bd) == [
        {
            "username": "bruno",
            "nombre": "Prueba bruno",
            "cluster": "apolo2",
            "aprobado_en": "2026-11-15T15:00:00Z",
        },
        {
            "username": "carla",
            "nombre": "Prueba carla",
            "cluster": "apolo2",
            "aprobado_en": "2026-11-18T15:00:00Z",
        },
        {
            "username": "ana",
            "nombre": "Prueba ana",
            "cluster": "apolo2",
            "aprobado_en": "2026-11-20T15:00:00Z",
        },
    ]


async def test_quien_no_cumple_todo_no_esta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await aprobado(sesion_bd, "ok")
    # Falta una práctica.
    sin_practica = await aprobado(sesion_bd, "sin-practica")
    await sesion_bd.execute(
        update(Practica)
        .where(Practica.usuario_id == sin_practica.id, Practica.practica == "paralelo")
        .values(estado="intentado")
    )
    # Falta una lección.
    sin_leccion = await aprobado(sesion_bd, "sin-leccion")
    lectura = await sesion_bd.scalar(
        select(Leccion.id).where(Leccion.slug == "lectura")
    )
    await sesion_bd.execute(
        update(ProgresoLeccion)
        .where(
            ProgresoLeccion.usuario_id == sin_leccion.id,
            ProgresoLeccion.leccion_id == lectura,
        )
        .values(completada_en=None)
    )
    # Graduación todavía sin revisar.
    enviada = await aprobado(sesion_bd, "enviada")
    await sesion_bd.execute(
        update(Graduacion)
        .where(Graduacion.usuario_id == enviada.id)
        .values(estado="enviada")
    )
    # Ya con la QOS.
    con_qos = await aprobado(sesion_bd, "con-qos")
    await sesion_bd.execute(
        update(Graduacion)
        .where(Graduacion.usuario_id == con_qos.id)
        .values(qos_aplicada_en=dia(25))
    )
    # Instructores y bajas no esperan QOS.
    await aprobado(sesion_bd, "instructora", rol="instructor")
    await aprobado(sesion_bd, "de-baja", activo=False)

    assert [a["username"] for a in await pendientes(cliente_bd)] == ["ok"]


async def test_sin_aprobados_la_lista_esta_vacia(
    cliente_bd: AsyncClient, diego: Usuario
) -> None:
    assert await pendientes(cliente_bd) == []


# --- QOS aplicada ---------------------------------------------------------------------------


async def test_marcar_la_qos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    ana = await aprobado(sesion_bd, "ana")
    antes = await progreso.mi_progreso(sesion_bd, ana, "es")
    assert antes.siguiente_paso.tipo == "esperar_qos"

    respuesta = await marcar(cliente_bd, "ana")

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    fila = await sesion_bd.get(Graduacion, ana.id, populate_existing=True)
    assert fila.qos_aplicada_en is not None
    assert fila.qos_aplicada_por == diego.id
    assert await pendientes(cliente_bd) == []
    despues = await progreso.mi_progreso(sesion_bd, ana, "es")
    assert despues.siguiente_paso.tipo == "terminado"
    (registro,) = await auditoria(sesion_bd, "qos_aplicada")
    assert (registro.actor_id, registro.objetivo, registro.detalle) == (
        diego.id,
        "ana",
        {"cluster": "apolo2"},
    )


async def test_marcar_dos_veces_da_409(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await aprobado(sesion_bd, "ana")
    await marcar(cliente_bd, "ana")

    respuesta = await marcar(cliente_bd, "ana")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "qos_ya_aplicada"
    assert len(await auditoria(sesion_bd, "qos_aplicada")) == 1


@pytest.mark.parametrize(
    "caso", ["sin_graduacion", "enviada", "falta_leccion", "instructor"]
)
async def test_marcar_a_quien_no_aprobo_da_409(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario, caso: str
) -> None:
    if caso == "sin_graduacion":
        await crear_usuario(sesion_bd, "ana")
    elif caso == "enviada":
        ana = await aprobado(sesion_bd, "ana")
        await sesion_bd.execute(
            update(Graduacion)
            .where(Graduacion.usuario_id == ana.id)
            .values(estado="enviada")
        )
    elif caso == "falta_leccion":
        ana = await crear_usuario(sesion_bd, "ana")
        await completar(sesion_bd, ana, "bienvenida")
        for nombre in PRACTICAS:
            await practica(sesion_bd, ana, nombre)
        await graduacion(sesion_bd, ana, "aprobada")
    else:
        await aprobado(sesion_bd, "ana", rol="instructor")

    respuesta = await marcar(cliente_bd, "ana")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "no_aprobado"
    assert await auditoria(sesion_bd, "qos_aplicada") == []


async def test_marcar_a_alguien_que_no_existe_da_404(
    cliente_bd: AsyncClient, diego: Usuario
) -> None:
    respuesta = await marcar(cliente_bd, "nadie")

    assert respuesta.status_code == 404


async def test_marcar_pide_el_token_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await aprobado(sesion_bd, "ana")

    respuesta = await marcar(cliente_bd, "ana", csrf=False)

    assert respuesta.status_code == 403
    assert [a["username"] for a in await pendientes(cliente_bd)] == ["ana"]


# --- CSV -------------------------------------------------------------------------------------


def leer_csv(texto: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(texto)))


@pytest.fixture
async def carla(crear_cliente, app_bd, sesion_bd: AsyncSession) -> AsyncClient:
    """Una instructora con sesión: el CSV es del panel."""
    await crear_usuario(sesion_bd, "carla", rol="instructor")
    cliente = crear_cliente(app_bd)
    assert (await ingresar(cliente, "carla")).status_code == 200
    return cliente


async def test_el_csv_de_la_medicion(
    carla: AsyncClient, sesion_bd: AsyncSession, contenido
) -> None:
    ana = await aprobado(sesion_bd, "ana")
    await sesion_bd.execute(
        update(Graduacion)
        .where(Graduacion.usuario_id == ana.id)
        .values(qos_aplicada_en=dia(25))
    )
    bruno = await crear_usuario(sesion_bd, "bruno", activo=False)
    bruno.cluster = "apolo3"
    await completar(sesion_bd, bruno, "bienvenida")
    await practica(sesion_bd, bruno, "conexion")
    await graduacion(sesion_bd, bruno, "rechazada")
    await crear_usuario(sesion_bd, "elena")
    await crear_usuario(sesion_bd, "diego", rol="admin")
    await sesion_bd.flush()

    respuesta = await carla.get(CSV)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "text/csv; charset=utf-8"
    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["content-disposition"].startswith(
        'attachment; filename="progreso-todos-'
    )
    texto = respuesta.text
    assert texto.splitlines()[0] == ",".join(COLUMNAS_CSV)
    assert "\r\n" in texto
    filas = leer_csv(texto)
    # Solo estudiantes, también los de baja; ni carla ni diego.
    assert [f["username"] for f in filas] == ["ana", "bruno", "elena"]
    assert {k: filas[0][k] for k in COLUMNAS_CSV if k not in ("creado_en",)} == {
        "username": "ana",
        "cluster": "apolo2",
        "activo": "true",
        "ultimo_ingreso": "",
        "avance_pct": "100",
        "modulos_completos": "3",
        "labs_aprobados": "7",
        "graduacion_estado": "aprobada",
        "qos_aplicada_en": "2026-11-25T15:00:00+00:00",
    }
    assert (
        datetime.fromisoformat(filas[0]["creado_en"]).utcoffset().total_seconds() == 0
    )
    assert {
        k: filas[1][k] for k in ("cluster", "activo", "avance_pct", "labs_aprobados")
    } == {
        "cluster": "apolo3",
        "activo": "false",
        "avance_pct": "25",
        "labs_aprobados": "1",
    }
    assert (filas[1]["graduacion_estado"], filas[2]["graduacion_estado"]) == (
        "rechazada",
        "",
    )


async def test_el_csv_por_cluster(carla: AsyncClient, sesion_bd: AsyncSession) -> None:
    await crear_usuario(sesion_bd, "ana")
    bruno = await crear_usuario(sesion_bd, "bruno")
    bruno.cluster = "apolo3"
    await sesion_bd.flush()

    respuesta = await carla.get(CSV, params={"cluster": "apolo3"})

    assert [f["username"] for f in leer_csv(respuesta.text)] == ["bruno"]
    assert 'filename="progreso-apolo3-' in respuesta.headers["content-disposition"]
    assert (await carla.get(CSV, params={"cluster": "cronos"})).status_code == 422


async def test_bajar_el_csv_queda_en_la_auditoria(
    carla: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "ana")

    await carla.get(CSV, params={"cluster": "apolo2"})

    (registro,) = await auditoria(sesion_bd, "export_progreso")
    autora = await sesion_bd.scalar(
        select(Usuario.id).where(Usuario.username == "carla")
    )
    assert (registro.actor_id, registro.detalle) == (
        autora,
        {"cluster": "apolo2", "filas": 1},
    )


async def test_el_csv_sin_estudiantes_trae_solo_el_encabezado(
    carla: AsyncClient,
) -> None:
    respuesta = await carla.get(CSV)

    assert respuesta.text == ",".join(COLUMNAS_CSV) + "\r\n"


async def test_un_estudiante_no_baja_el_csv(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "ana")
    await ingresar(cliente_bd, "ana")

    respuesta = await cliente_bd.get(CSV)

    assert respuesta.status_code == 403
    assert await auditoria(sesion_bd, "export_progreso") == []
