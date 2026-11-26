"""Sincronización de prácticas (B-07): POST /api/internal/labs.

La llama la VM de práctica con el token de servicio (V-05). DoD 1: sin token o
con uno malo, 401 (la IP la filtra el nginx de la 117). DoD 2: el mismo
reporte dos veces no duplica ni cambia nada. DoD 3: pruebas del upsert.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.seguridad import ahora
from app.main import create_app
from app.models import Practica, Sincronizacion, Usuario
from app.services import labs
from tests.ayuda_servicio import TOKEN
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

URL = "/api/internal/labs"
FECHA = "2026-11-23T09:58:12-05:00"


def registro(usuario: str = "ana", lab: str = "memoria", **campos) -> dict:
    return {
        "usuario": usuario,
        "lab": lab,
        "estado": "intentado",
        "jobid": "1042",
        "fecha": FECHA,
        **campos,
    }


def reporte(*registros: dict) -> dict:
    return {"generado_en": "2026-11-23T10:05:00-05:00", "registros": list(registros)}


async def enviar(cliente: AsyncClient, cuerpo: dict, token: str | None = TOKEN):
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    return await cliente.post(URL, json=cuerpo, headers=cabeceras)


async def practicas(bd: AsyncSession) -> dict[tuple[str, str], Practica]:
    filas = await bd.execute(
        select(Usuario.username, Practica)
        .join(Usuario, Usuario.id == Practica.usuario_id)
        .execution_options(populate_existing=True)
    )
    return {(username, p.practica): p for username, p in filas}


async def sincronizaciones(bd: AsyncSession) -> list[tuple[int, int]]:
    return list(
        (
            await bd.execute(
                select(Sincronizacion.registros, Sincronizacion.aceptados).order_by(
                    Sincronizacion.id
                )
            )
        ).all()
    )


@pytest.fixture
async def ana(sesion_bd: AsyncSession) -> Usuario:
    return await crear_usuario(sesion_bd, "ana")


# --- Token (DoD 1) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "cabecera",
    [
        None,
        f"Bearer {'x' * 64}",
        f"Bearer {TOKEN[:-1]}",
        f"Bearer {TOKEN}extra",
        f"Basic {TOKEN}",
        "Bearer",
        "Bearer ",
        TOKEN,
    ],
)
async def test_sin_token_o_con_uno_malo_responde_401(
    vm: AsyncClient, sesion_bd: AsyncSession, cabecera: str | None
) -> None:
    cabeceras = {"Authorization": cabecera} if cabecera is not None else {}

    respuesta = await vm.post(URL, json=reporte(), headers=cabeceras)

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_servicio_invalido"
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert await sincronizaciones(sesion_bd) == []


async def test_sin_token_configurado_en_la_api_nadie_entra(
    cliente_bd: AsyncClient,
) -> None:
    # cliente_bd usa la configuración de pruebas, que no tiene token.
    respuesta = await enviar(cliente_bd, reporte())

    assert respuesta.status_code == 401


async def test_el_token_se_revisa_antes_que_el_cuerpo(vm: AsyncClient) -> None:
    sin_token = await enviar(vm, {"cualquier": "cosa"}, token=None)
    con_token = await enviar(vm, {"cualquier": "cosa"})

    assert sin_token.status_code == 401
    assert con_token.status_code == 422


async def test_una_sesion_de_usuario_no_sirve(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "diego", rol="admin")
    assert (await ingresar(vm, "diego")).status_code == 200

    respuesta = await vm.post(URL, json=reporte(), headers=con_csrf(vm))

    assert respuesta.status_code == 401


def test_el_token_corto_no_arranca() -> None:
    with pytest.raises(ValueError, match="32 caracteres"):
        Settings(token_servicio="corto")


# --- Upsert (DoD 2 y 3) ----------------------------------------------------------


async def test_un_reporte_vacio_queda_registrado(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    respuesta = await enviar(vm, reporte())

    assert respuesta.status_code == 200
    assert respuesta.json() == {"aceptados": 0, "ignorados": []}
    assert await sincronizaciones(sesion_bd) == [(0, 0)]


async def test_guarda_cada_practica_del_usuario(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    respuesta = await enviar(
        vm,
        reporte(
            registro(estado="aprobado", detalle="Terminó con --mem=4G"),
            registro(lab="conexion", estado="aprobado", jobid=None),
            registro(lab="nucleos", jobid="1050"),
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"aceptados": 3, "ignorados": []}
    filas = await practicas(sesion_bd)
    assert set(filas) == {("ana", "memoria"), ("ana", "conexion"), ("ana", "nucleos")}
    memoria = filas["ana", "memoria"]
    assert (memoria.estado, memoria.jobid, memoria.detalle) == (
        "aprobado",
        "1042",
        "Terminó con --mem=4G",
    )
    assert memoria.fecha == datetime(2026, 11, 23, 14, 58, 12, tzinfo=UTC)
    assert filas["ana", "conexion"].jobid is None
    assert filas["ana", "nucleos"].estado == "intentado"
    assert await sincronizaciones(sesion_bd) == [(3, 3)]


async def test_el_mismo_reporte_dos_veces_no_cambia_nada(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    cuerpo = reporte(registro(), registro(lab="paralelo", estado="aprobado"))
    await enviar(vm, cuerpo)
    # En una transacción now() no avanza: se pone una fecha vieja a mano para
    # ver que el segundo envío no reescribe las filas.
    vieja = ahora() - timedelta(days=1)
    await sesion_bd.execute(update(Practica).values(sincronizado_en=vieja))
    antes = {
        clave: (p.estado, p.jobid, p.detalle, p.fecha)
        for clave, p in (await practicas(sesion_bd)).items()
    }

    respuesta = await enviar(vm, cuerpo)

    assert respuesta.json() == {"aceptados": 2, "ignorados": []}
    despues = await practicas(sesion_bd)
    assert len(despues) == 2
    assert {
        clave: (p.estado, p.jobid, p.detalle, p.fecha) for clave, p in despues.items()
    } == antes
    assert {p.sincronizado_en for p in despues.values()} == {vieja}
    assert await sincronizaciones(sesion_bd) == [(2, 2), (2, 2)]


async def test_un_intentado_se_actualiza_con_el_ultimo_intento(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(vm, reporte(registro(jobid="1042", detalle="OUT_OF_MEMORY")))
    vieja = ahora() - timedelta(days=1)
    await sesion_bd.execute(update(Practica).values(sincronizado_en=vieja))

    await enviar(vm, reporte(registro(jobid="1043", detalle=None)))

    memoria = (await practicas(sesion_bd))["ana", "memoria"]
    assert (memoria.estado, memoria.jobid, memoria.detalle) == (
        "intentado",
        "1043",
        None,
    )
    assert memoria.sincronizado_en > vieja


async def test_un_intentado_pasa_a_aprobado(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(vm, reporte(registro()))

    await enviar(vm, reporte(registro(estado="aprobado", jobid="1044")))

    memoria = (await practicas(sesion_bd))["ana", "memoria"]
    assert (memoria.estado, memoria.jobid) == ("aprobado", "1044")


async def test_un_aprobado_no_retrocede(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(vm, reporte(registro(estado="aprobado")))

    respuesta = await enviar(vm, reporte(registro(jobid="1099", detalle="otra vez")))

    assert respuesta.json() == {
        "aceptados": 0,
        "ignorados": [{"usuario": "ana", "lab": "memoria", "motivo": "no_retrocede"}],
    }
    memoria = (await practicas(sesion_bd))["ana", "memoria"]
    assert (memoria.estado, memoria.jobid, memoria.detalle) == (
        "aprobado",
        "1042",
        None,
    )
    assert await sincronizaciones(sesion_bd) == [(1, 1), (1, 0)]


async def test_un_aprobado_conserva_el_primer_trabajo_que_lo_aprobo(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(vm, reporte(registro(estado="aprobado", jobid="1042")))

    respuesta = await enviar(vm, reporte(registro(estado="aprobado", jobid="2001")))

    assert respuesta.json() == {"aceptados": 1, "ignorados": []}
    assert (await practicas(sesion_bd))["ana", "memoria"].jobid == "1042"


async def test_un_aprobado_no_retrocede_aunque_llegue_entre_consultas(
    vm: AsyncClient,
    sesion_bd: AsyncSession,
    ana: Usuario,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Otro envío lo aprobó después de que este revisó cuáles estaban
    # aprobados: lo frena el WHERE del upsert.
    await enviar(vm, reporte(registro(estado="aprobado")))

    async def ninguna(*_):
        return set()

    monkeypatch.setattr(labs, "_aprobadas", ninguna)
    await enviar(vm, reporte(registro(jobid="1099")))

    memoria = (await practicas(sesion_bd))["ana", "memoria"]
    assert (memoria.estado, memoria.jobid) == ("aprobado", "1042")


async def test_usuarios_desconocidos_o_de_baja_no_rompen_el_envio(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await crear_usuario(sesion_bd, "elena", activo=False)

    respuesta = await enviar(
        vm,
        reporte(
            registro("nadie"),
            registro("elena", "modulos"),
            registro("ana", "modulos", estado="aprobado"),
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "aceptados": 1,
        "ignorados": [
            {"usuario": "nadie", "lab": "memoria", "motivo": "usuario_desconocido"},
            {"usuario": "elena", "lab": "modulos", "motivo": "usuario_inactivo"},
        ],
    }
    assert set(await practicas(sesion_bd)) == {("ana", "modulos")}
    assert await sincronizaciones(sesion_bd) == [(3, 1)]


async def test_cada_usuario_tiene_sus_practicas(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await crear_usuario(sesion_bd, "bruno")

    await enviar(
        vm, reporte(registro("ana", estado="aprobado"), registro("bruno", jobid="7"))
    )

    filas = await practicas(sesion_bd)
    assert filas["ana", "memoria"].estado == "aprobado"
    assert (filas["bruno", "memoria"].estado, filas["bruno", "memoria"].jobid) == (
        "intentado",
        "7",
    )


async def test_un_registro_repetido_rechaza_el_envio(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    respuesta = await enviar(
        vm, reporte(registro(), registro(lab="nucleos"), registro(estado="aprobado"))
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "registro_repetido"
    assert "ana/memoria" in respuesta.json()["detail"]
    assert await practicas(sesion_bd) == {}
    assert await sincronizaciones(sesion_bd) == []


@pytest.mark.parametrize(
    "campos",
    [
        {"lab": "ondemand"},
        {"estado": "sin_intentar"},
        {"usuario": "Ana Mayúscula"},
        {"jobid": "abc"},
        {"fecha": "2026-11-23T09:58:12"},  # sin zona horaria
        {"detalle": "x" * 201},
        {"detalle": "con\x00nulo"},
    ],
)
async def test_un_registro_mal_armado_da_422(
    vm: AsyncClient, sesion_bd: AsyncSession, ana: Usuario, campos: dict
) -> None:
    respuesta = await enviar(vm, reporte(registro(**campos)))

    assert respuesta.status_code == 422
    assert await sincronizaciones(sesion_bd) == []


async def test_acepta_hasta_5000_registros(vm: AsyncClient) -> None:
    respuesta = await enviar(vm, reporte(*[registro()] * 5001))

    assert respuesta.status_code == 422


async def test_un_reporte_grande_se_guarda_por_lotes(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    # 150 usuarios por 7 prácticas = 1050 filas: más de un lote de 1000.
    sesion_bd.add_all(
        Usuario(username=f"u{n:03d}", nombre="x", cluster="apolo2", clave_hash="x")
        for n in range(150)
    )
    await sesion_bd.flush()
    practicas7 = ("conexion", "terminal", "archivos", "modulos", "memoria")
    practicas7 += ("nucleos", "paralelo")
    registros = [
        registro(f"u{n:03d}", lab, jobid=None) for n in range(150) for lab in practicas7
    ]

    respuesta = await enviar(vm, reporte(*registros))

    assert respuesta.json() == {"aceptados": 1050, "ignorados": []}
    total = await sesion_bd.scalar(select(func.count()).select_from(Practica))
    assert total == 1050


async def test_el_token_no_queda_en_la_app(settings_con_token: Settings) -> None:
    app: FastAPI = create_app(settings_con_token)

    assert TOKEN not in repr(app.state.settings)
