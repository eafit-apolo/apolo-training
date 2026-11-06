"""Roles de cada ruta (DoD 2 de la B-03).

Cada ruta declara `x-roles` con publica(), con_refresh() o con_roles() de
app/core/auth.py. Estas pruebas recorren TODAS las rutas de la app, así que
cubren solas las que lleguen después (panel en la B-05, admin en la B-08):

- toda ruta declara roles, y son los mismos de api/openapi.yaml;
- sin sesión, toda ruta protegida responde 401;
- un estudiante recibe 403 en toda ruta cuyos roles no lo incluyen;
- quien debe cambiar la clave recibe 403 en todo menos /auth/*, GET y PATCH /me.

Mientras no haya rutas de admin (B-08), las dos rutas de prueba de abajo
demuestran que el mecanismo funciona; las de panel existen desde la B-05.
"""

import re
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import con_roles
from app.core.config import Settings
from app.main import PREFIJO, create_app
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

CONTRATO = Path(__file__).resolve().parents[1] / "openapi.yaml"
METODOS = {"get", "post", "put", "patch", "delete"}
# Se autentican con la cookie rt, no con at (ver con_refresh()).
CON_REFRESH = {("POST", "/api/auth/refresh"), ("POST", "/api/auth/logout")}
# Las únicas que admiten a quien todavía debe cambiar la clave.
CON_CAMBIO_PENDIENTE = {
    ("POST", "/api/auth/cambiar-clave"),
    ("GET", "/api/me"),
    ("PATCH", "/api/me"),
}


def operaciones(app: FastAPI) -> dict[tuple[str, str], APIRoute]:
    return {
        (metodo, ruta.path): ruta
        for ruta in app.routes
        if isinstance(ruta, APIRoute)
        for metodo in ruta.methods
    }


def roles(ruta: APIRoute) -> list[str] | None:
    return (ruta.openapi_extra or {}).get("x-roles")


def protegidas(app: FastAPI) -> dict[tuple[str, str], APIRoute]:
    return {
        clave: ruta
        for clave, ruta in operaciones(app).items()
        if roles(ruta) != ["publico"] and clave not in CON_REFRESH
    }


def url(ruta: str) -> str:
    """/api/x/{id} → /api/x/1: basta para llegar a la ruta."""
    return re.sub(r"\{[^}]+\}", "1", ruta)


async def pedir(cliente: AsyncClient, metodo: str, ruta: str, csrf: bool):
    cabeceras = con_csrf(cliente) if csrf and metodo != "GET" else {}
    return await cliente.request(metodo, url(ruta), json={}, headers=cabeceras)


@pytest.fixture
def app_real(settings_sin_base: Settings) -> FastAPI:
    return create_app(settings_sin_base)


@pytest.fixture
def app_con_pruebas(app_bd: FastAPI) -> FastAPI:
    """La app con dos rutas de prueba restringidas (no están en el contrato)."""

    @app_bd.get(f"{PREFIJO}/_prueba/panel", **con_roles("instructor", "admin"))
    async def panel() -> dict[str, bool]:
        return {"ok": True}

    @app_bd.delete(f"{PREFIJO}/_prueba/admin/{{username}}", **con_roles("admin"))
    async def admin(username: str) -> dict[str, str]:
        return {"username": username}

    return app_bd


def test_toda_ruta_declara_roles(app_real: FastAPI) -> None:
    sin_roles = [
        clave for clave, ruta in operaciones(app_real).items() if not roles(ruta)
    ]

    assert sin_roles == []


def test_rutas_iguales_al_contrato(app_real: FastAPI) -> None:
    contrato = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    esperadas = {
        (metodo.upper(), PREFIJO + ruta): op
        for ruta, ops in contrato["paths"].items()
        for metodo, op in ops.items()
        if metodo in METODOS
    }

    for clave, ruta in operaciones(app_real).items():
        assert clave in esperadas, f"{clave} no está en api/openapi.yaml"
        assert ruta.operation_id == esperadas[clave]["operationId"], clave
        assert set(roles(ruta)) == set(esperadas[clave]["x-roles"]), clave


async def test_sin_sesion_toda_ruta_protegida_responde_401(
    crear_cliente, app_real: FastAPI
) -> None:
    cliente = crear_cliente(app_real)
    for (metodo, ruta), _ in protegidas(app_real).items():
        respuesta = await pedir(cliente, metodo, ruta, csrf=False)
        assert respuesta.status_code == 401, (metodo, ruta)


async def test_estudiante_recibe_403_donde_no_le_toca(
    crear_cliente, app_con_pruebas: FastAPI, sesion_bd: AsyncSession
) -> None:
    cliente = crear_cliente(app_con_pruebas)
    await crear_usuario(sesion_bd, rol="estudiante")
    await ingresar(cliente)
    restringidas = {
        clave: ruta
        for clave, ruta in protegidas(app_con_pruebas).items()
        if "estudiante" not in roles(ruta)
    }

    assert len(restringidas) >= 2
    for metodo, ruta in restringidas:
        respuesta = await pedir(cliente, metodo, ruta, csrf=True)
        assert respuesta.status_code == 403, (metodo, ruta)
        assert respuesta.json()["codigo"] == "sin_permiso", (metodo, ruta)


@pytest.mark.parametrize(
    ("rol", "panel", "admin"),
    [("instructor", 200, 403), ("admin", 200, 200)],
)
async def test_cada_rol_entra_a_lo_suyo(
    crear_cliente,
    app_con_pruebas: FastAPI,
    sesion_bd: AsyncSession,
    rol: str,
    panel: int,
    admin: int,
) -> None:
    cliente = crear_cliente(app_con_pruebas)
    await crear_usuario(sesion_bd, rol=rol)
    await ingresar(cliente)

    assert (await cliente.get("/api/_prueba/panel")).status_code == panel
    respuesta = await cliente.delete(
        "/api/_prueba/admin/ana", headers=con_csrf(cliente)
    )
    assert respuesta.status_code == admin


async def test_con_cambio_pendiente_solo_auth_y_me(
    crear_cliente, app_con_pruebas: FastAPI, sesion_bd: AsyncSession
) -> None:
    cliente = crear_cliente(app_con_pruebas)
    await crear_usuario(sesion_bd, rol="admin", debe_cambiar_clave=True)
    await ingresar(cliente)
    bloqueadas = {
        clave
        for clave in protegidas(app_con_pruebas)
        if clave not in CON_CAMBIO_PENDIENTE
    }

    assert bloqueadas
    for metodo, ruta in bloqueadas:
        respuesta = await pedir(cliente, metodo, ruta, csrf=True)
        assert respuesta.status_code == 403, (metodo, ruta)
        assert respuesta.json()["codigo"] == "debe_cambiar_clave", (metodo, ruta)


def test_con_roles_rechaza_roles_inventados() -> None:
    with pytest.raises(ValueError, match="superusuario"):
        con_roles("superusuario")
