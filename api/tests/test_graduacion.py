"""Graduación (B-07, DoD 3): el usuario la envía (POST /api/me/graduacion) y
un instructor la lista y la revisa (GET /api/panel/graduaciones y POST
/api/panel/graduaciones/{username}/revision). Los roles de cada ruta los
revisa test_roles.py.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Auditoria, Graduacion, Practica, Usuario
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

ENVIAR = "/api/me/graduacion"
LISTA = "/api/panel/graduaciones"
SALIDA = "[APROBADO] graduacion: curso-graduacion terminó (COMPLETED) en learning"


def revision(username: str) -> str:
    return f"{LISTA}/{username}/revision"


@pytest.fixture
async def ana(cliente_bd: AsyncClient, sesion_bd: AsyncSession) -> Usuario:
    usuario = await crear_usuario(sesion_bd, "ana")
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    return usuario


@pytest.fixture
async def carla(crear_cliente, app_bd, sesion_bd: AsyncSession) -> AsyncClient:
    """Cliente con la sesión de una instructora."""
    await crear_usuario(sesion_bd, "carla", rol="instructor")
    cliente = crear_cliente(app_bd)
    assert (await ingresar(cliente, "carla")).status_code == 200
    return cliente


async def enviar(cliente: AsyncClient, jobid: str = "98765", salida: str = SALIDA):
    return await cliente.post(
        ENVIAR, json={"jobid": jobid, "salida": salida}, headers=con_csrf(cliente)
    )


async def revisar(cliente: AsyncClient, username: str, decision: str, **mas):
    return await cliente.post(
        revision(username),
        json={"decision": decision, **mas},
        headers=con_csrf(cliente),
    )


async def fila(bd: AsyncSession, usuario: Usuario) -> Graduacion | None:
    return await bd.get(Graduacion, usuario.id, populate_existing=True)


async def auditoria(bd: AsyncSession, accion: str) -> list[Auditoria]:
    return list(await bd.scalars(select(Auditoria).where(Auditoria.accion == accion)))


# --- Enviar -------------------------------------------------------------------


async def test_enviar_la_graduacion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    respuesta = await enviar(cliente_bd)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert {k: v for k, v in cuerpo.items() if k != "enviada_en"} == {
        "cluster": "apolo2",
        "jobid": "98765",
        "salida_verificador": SALIDA,
        "estado": "enviada",
        "revisada_en": None,
        "comentario": None,
        "qos_aplicada_en": None,
    }
    assert datetime.fromisoformat(cuerpo["enviada_en"]).tzinfo is not None
    guardada = await fila(sesion_bd, ana)
    assert (guardada.estado, guardada.jobid) == ("enviada", "98765")
    (registro,) = await auditoria(sesion_bd, "graduacion_enviada")
    assert (registro.actor_id, registro.objetivo, registro.detalle) == (
        ana.id,
        "ana",
        {"jobid": "98765"},
    )


async def test_el_cluster_es_el_del_perfil(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await sesion_bd.execute(
        update(Usuario).where(Usuario.id == ana.id).values(cluster="apolo3")
    )

    respuesta = await enviar(cliente_bd, jobid="1234_5")

    assert (respuesta.json()["cluster"], respuesta.json()["jobid"]) == (
        "apolo3",
        "1234_5",
    )


async def test_un_reenvio_reemplaza_la_anterior(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd, jobid="1")

    respuesta = await enviar(cliente_bd, jobid="2", salida="otra salida")

    assert respuesta.status_code == 200
    guardada = await fila(sesion_bd, ana)
    assert (guardada.jobid, guardada.salida_verificador, guardada.estado) == (
        "2",
        "otra salida",
        "enviada",
    )
    assert len(list(await sesion_bd.scalars(select(Graduacion)))) == 1


async def test_reenviar_despues_de_un_rechazo_borra_la_revision(
    cliente_bd: AsyncClient, carla: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd, jobid="1")
    await revisar(carla, "ana", "rechazar", comentario="Falta --mem=1G")
    vieja = datetime(2026, 11, 1, tzinfo=UTC)
    await sesion_bd.execute(update(Graduacion).values(enviada_en=vieja))

    respuesta = await enviar(cliente_bd, jobid="2")

    cuerpo = respuesta.json()
    assert (cuerpo["estado"], cuerpo["revisada_en"], cuerpo["comentario"]) == (
        "enviada",
        None,
        None,
    )
    guardada = await fila(sesion_bd, ana)
    assert guardada.revisada_por is None
    assert guardada.enviada_en > vieja


async def test_una_aprobada_no_se_reemplaza(
    cliente_bd: AsyncClient, carla: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd, jobid="1")
    await revisar(carla, "ana", "aprobar")

    respuesta = await enviar(cliente_bd, jobid="2")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "graduacion_aprobada"
    guardada = await fila(sesion_bd, ana)
    assert (guardada.jobid, guardada.estado) == ("1", "aprobada")
    assert len(await auditoria(sesion_bd, "graduacion_enviada")) == 1


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"jobid": "abc", "salida": SALIDA},
        {"jobid": "", "salida": SALIDA},
        {"jobid": "98765", "salida": ""},
        {"jobid": "98765", "salida": "x" * 4001},
        {"jobid": "98765", "salida": "con\x00nulo"},
        {"jobid": "98765"},
    ],
)
async def test_una_entrada_mal_armada_da_422(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario, cuerpo: dict
) -> None:
    respuesta = await cliente_bd.post(ENVIAR, json=cuerpo, headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 422
    assert await fila(sesion_bd, ana) is None


async def test_la_salida_puede_tener_4000_caracteres(
    cliente_bd: AsyncClient, ana: Usuario
) -> None:
    assert (await enviar(cliente_bd, salida="x" * 4000)).status_code == 200


async def test_enviar_pide_el_token_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    respuesta = await cliente_bd.post(ENVIAR, json={"jobid": "1", "salida": SALIDA})

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"
    assert await fila(sesion_bd, ana) is None


async def test_la_salida_no_va_a_la_auditoria(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd, salida="SALIDA-QUE-NO-DEBE-SALIR")

    filas = await auditoria(sesion_bd, "graduacion_enviada")
    assert "SALIDA-QUE-NO-DEBE-SALIR" not in str([f.detalle for f in filas])


# --- Revisar ------------------------------------------------------------------


async def test_aprobar(
    cliente_bd: AsyncClient, carla: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd)

    respuesta = await revisar(carla, "ana", "aprobar")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert (cuerpo["username"], cuerpo["nombre"], cuerpo["estado"]) == (
        "ana",
        "Prueba ana",
        "aprobada",
    )
    assert (cuerpo["revisada_por"], cuerpo["comentario"]) == ("carla", None)
    assert cuerpo["revisada_en"] is not None
    carla_id = await sesion_bd.scalar(
        select(Usuario.id).where(Usuario.username == "carla")
    )
    guardada = await fila(sesion_bd, ana)
    assert (guardada.estado, guardada.revisada_por) == ("aprobada", carla_id)
    (registro,) = await auditoria(sesion_bd, "graduacion_revisada")
    assert (registro.actor_id, registro.objetivo, registro.detalle) == (
        carla_id,
        "ana",
        {"decision": "aprobar"},
    )
    progreso = (await cliente_bd.get("/api/me/progreso")).json()
    assert progreso["graduacion"]["estado"] == "aprobada"


async def test_rechazar_con_comentario(
    cliente_bd: AsyncClient, carla: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    await enviar(cliente_bd)

    respuesta = await revisar(
        carla, "ana", "rechazar", comentario="  Pon --mem=1G en el script  "
    )

    assert respuesta.status_code == 200
    assert (respuesta.json()["estado"], respuesta.json()["comentario"]) == (
        "rechazada",
        "Pon --mem=1G en el script",
    )
    progreso = (await cliente_bd.get("/api/me/progreso")).json()
    assert progreso["graduacion"]["comentario"] == "Pon --mem=1G en el script"


@pytest.mark.parametrize("comentario", [None, "", "   "])
async def test_rechazar_exige_comentario(
    cliente_bd: AsyncClient,
    carla: AsyncClient,
    sesion_bd: AsyncSession,
    ana: Usuario,
    comentario: str | None,
) -> None:
    await enviar(cliente_bd)
    mas = {} if comentario is None else {"comentario": comentario}

    respuesta = await revisar(carla, "ana", "rechazar", **mas)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "comentario_obligatorio"
    assert (await fila(sesion_bd, ana)).estado == "enviada"


async def test_aprobar_con_comentario_lo_guarda(
    cliente_bd: AsyncClient, carla: AsyncClient, ana: Usuario
) -> None:
    await enviar(cliente_bd)

    respuesta = await revisar(carla, "ana", "aprobar", comentario="Bien hecho")

    assert respuesta.json()["comentario"] == "Bien hecho"


async def test_solo_se_revisa_una_enviada(
    cliente_bd: AsyncClient, carla: AsyncClient, sesion_bd: AsyncSession, ana: Usuario
) -> None:
    sin_enviar = await revisar(carla, "ana", "aprobar")
    await enviar(cliente_bd)
    await revisar(carla, "ana", "rechazar", comentario="No")
    ya_revisada = await revisar(carla, "ana", "aprobar")

    for respuesta in (sin_enviar, ya_revisada):
        assert respuesta.status_code == 409
        assert respuesta.json()["codigo"] == "sin_graduacion_pendiente"
    assert (await fila(sesion_bd, ana)).estado == "rechazada"
    assert len(await auditoria(sesion_bd, "graduacion_revisada")) == 1


async def test_revisar_un_usuario_que_no_existe(carla: AsyncClient) -> None:
    respuesta = await revisar(carla, "nadie", "aprobar")

    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [{"decision": "quizas"}, {}, {"decision": "rechazar", "comentario": "x" * 1001}],
)
async def test_una_revision_mal_armada_da_422(
    cliente_bd: AsyncClient, carla: AsyncClient, ana: Usuario, cuerpo: dict
) -> None:
    await enviar(cliente_bd)

    respuesta = await carla.post(revision("ana"), json=cuerpo, headers=con_csrf(carla))

    assert respuesta.status_code == 422


# --- Listar -------------------------------------------------------------------


async def test_listar_las_mas_viejas_primero_y_por_estado(
    carla: AsyncClient, sesion_bd: AsyncSession
) -> None:
    hoy = datetime(2026, 11, 23, 15, tzinfo=UTC)
    for n, (username, estado) in enumerate(
        [("bruno", "enviada"), ("ana", "enviada"), ("elena", "aprobada")]
    ):
        usuario = await crear_usuario(sesion_bd, username)
        sesion_bd.add(
            Graduacion(
                usuario_id=usuario.id,
                cluster="apolo2",
                jobid=str(n + 1),
                salida_verificador=SALIDA,
                estado=estado,
                enviada_en=hoy - timedelta(days=n),
            )
        )
        if username == "ana":
            for practica in ("conexion", "memoria"):
                sesion_bd.add(
                    Practica(
                        usuario_id=usuario.id,
                        practica=practica,
                        estado="aprobado",
                        fecha=hoy,
                    )
                )
            sesion_bd.add(
                Practica(
                    usuario_id=usuario.id,
                    practica="nucleos",
                    estado="intentado",
                    fecha=hoy,
                )
            )
    await sesion_bd.flush()

    todas = (await carla.get(LISTA)).json()
    enviadas = (await carla.get(LISTA, params={"estado": "enviada"})).json()
    invalido = await carla.get(LISTA, params={"estado": "perdida"})

    assert [g["username"] for g in todas] == ["elena", "ana", "bruno"]
    assert [g["username"] for g in enviadas] == ["ana", "bruno"]
    ana = enviadas[0]
    assert (ana["labs_aprobados"], ana["revisada_por"], ana["nombre"]) == (
        2,
        None,
        "Prueba ana",
    )
    assert enviadas[1]["labs_aprobados"] == 0
    assert invalido.status_code == 422


async def test_listar_sin_graduaciones(carla: AsyncClient) -> None:
    respuesta = await carla.get(LISTA)

    assert (respuesta.status_code, respuesta.json()) == (200, [])
