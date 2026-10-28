"""POST /api/auth/cambiar-clave y el cambio obligatorio del primer ingreso."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import UsuarioDep, con_roles
from app.models import Auditoria, Sesion
from app.models.valores import ROLES
from tests.ayuda_sesion import CLAVE, con_csrf, crear_usuario, ingresar

NUEVA = "otra-clave-buena"


@pytest.fixture
def app_con_ruta(app_bd: FastAPI) -> FastAPI:
    """Una ruta cualquiera que exige haber cambiado la clave."""

    @app_bd.get("/api/_prueba/normal", **con_roles(*ROLES))
    async def normal(usuario: UsuarioDep) -> dict[str, str]:
        return {"username": usuario.username}

    return app_bd


async def cambiar(cliente: AsyncClient, actual: str, nueva: str):
    return await cliente.post(
        "/api/auth/cambiar-clave",
        json={"clave_actual": actual, "clave_nueva": nueva},
        headers=con_csrf(cliente),
    )


async def test_primer_ingreso_solo_deja_cambiar_la_clave(
    crear_cliente, app_con_ruta: FastAPI, sesion_bd: AsyncSession
) -> None:
    cliente = crear_cliente(app_con_ruta)
    await crear_usuario(sesion_bd, debe_cambiar_clave=True)
    login = await ingresar(cliente)
    assert login.json()["usuario"]["debe_cambiar_clave"] is True

    otra = await cliente.get("/api/_prueba/normal")
    perfil = await cliente.get("/api/me")
    idioma = await cliente.patch(
        "/api/me", json={"idioma": "en"}, headers=con_csrf(cliente)
    )

    assert otra.status_code == 403
    assert otra.json()["codigo"] == "debe_cambiar_clave"
    assert perfil.status_code == 200
    assert idioma.status_code == 200

    assert (await cambiar(cliente, CLAVE, NUEVA)).status_code == 204
    assert (await cliente.get("/api/me")).json()["debe_cambiar_clave"] is False
    assert (await cliente.get("/api/_prueba/normal")).status_code == 200


async def test_cambio_cierra_las_demas_sesiones(
    crear_cliente, app_bd: FastAPI, cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    otro_equipo = crear_cliente(app_bd)
    await ingresar(otro_equipo)
    await ingresar(cliente_bd)

    respuesta = await cambiar(cliente_bd, CLAVE, NUEVA)

    assert respuesta.status_code == 204
    assert (await cliente_bd.get("/api/me")).status_code == 200
    assert (await otro_equipo.get("/api/me")).status_code == 401
    abiertas = await sesion_bd.scalar(
        select(func.count())
        .select_from(Sesion)
        .where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None))
    )
    assert abiertas == 1
    assert await sesion_bd.scalar(
        select(Auditoria.id).where(Auditoria.accion == "cambio_clave")
    )
    # La nueva entra y la vieja ya no.
    assert (await ingresar(otro_equipo, clave=NUEVA)).status_code == 200
    assert (await ingresar(otro_equipo, clave=CLAVE)).status_code == 401


@pytest.mark.parametrize(
    ("actual", "nueva", "codigo"),
    [
        ("no-es-la-actual", NUEVA, "clave_incorrecta"),
        (CLAVE, "1234567", "clave_debil"),
        (CLAVE, "TESTER", "clave_debil"),
        (CLAVE, CLAVE, "clave_repetida"),
    ],
)
async def test_cambio_rechazado(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    actual: str,
    nueva: str,
    codigo: str,
) -> None:
    await crear_usuario(sesion_bd, username="tester")
    await ingresar(cliente_bd)

    respuesta = await cambiar(cliente_bd, actual, nueva)

    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == codigo


async def test_ocho_caracteres_bastan(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    assert (await cambiar(cliente_bd, CLAVE, "12345678")).status_code == 204


async def test_mas_de_128_caracteres_es_invalida(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    respuesta = await cambiar(cliente_bd, CLAVE, "x" * 129)

    assert respuesta.status_code == 422


async def test_cambio_sin_sesion_o_sin_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    sin_sesion = await cliente_bd.post(
        "/api/auth/cambiar-clave", json={"clave_actual": CLAVE, "clave_nueva": NUEVA}
    )
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    sin_csrf = await cliente_bd.post(
        "/api/auth/cambiar-clave", json={"clave_actual": CLAVE, "clave_nueva": NUEVA}
    )

    assert sin_sesion.status_code == 401
    assert sin_csrf.status_code == 403
    assert sin_csrf.json()["codigo"] == "csrf_invalido"
