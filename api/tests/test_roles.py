"""Roles de cada ruta (DoD 2 de la B-03).

Cada ruta declara `x-roles` con publica(), con_refresh() o con_roles() de
app/core/auth.py. Estas pruebas recorren TODAS las rutas de la app, así que
cubren solas las que lleguen después (panel en la B-05, admin en la B-08):

- toda ruta declara roles, y son los mismos de api/openapi.yaml;
- sin sesión, toda ruta protegida responde 401;
- un estudiante recibe 403 en toda ruta cuyos roles no lo incluyen;
- quien debe cambiar la clave recibe 403 en todo menos /auth/*, GET y PATCH /me.

Las dos rutas de prueba de abajo demuestran el mecanismo con un rol de cada
lado; las de panel existen desde la B-05 y las de admin desde la B-08 (DoD 3
de la B-08: un instructor recibe 403 en todo /api/admin).

Las rutas internas (`x-roles: [servicio]`, B-07) no tienen sesión: sin token
responden 401 como las demás, pero una sesión no les sirve de nada (ni 403 ni
`debe_cambiar_clave`); sus pruebas están en test_labs.py.

Las rutas se leen del OpenAPI que genera la app, no de `app.routes`: desde
FastAPI 0.143, `app.routes` trae un `_IncludedRouter` por router, no sus rutas
(visto el 20-nov: hasta entonces estas pruebas solo veían las dos de prueba).
"""

import re
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
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


def operaciones(app: FastAPI) -> dict[tuple[str, str], dict]:
    """(MÉTODO, ruta) → operación del OpenAPI generado (con `x-roles`)."""
    app.openapi_schema = None  # que incluya las rutas agregadas después
    return {
        (metodo.upper(), ruta): op
        for ruta, ops in app.openapi()["paths"].items()
        for metodo, op in ops.items()
        if metodo in METODOS
    }


def roles(op: dict) -> list[str] | None:
    return op.get("x-roles")


def protegidas(app: FastAPI) -> dict[tuple[str, str], dict]:
    return {
        clave: op
        for clave, op in operaciones(app).items()
        if roles(op) != ["publico"] and clave not in CON_REFRESH
    }


def de_sesion(app: FastAPI) -> dict[tuple[str, str], dict]:
    """Las protegidas que se usan con sesión (no las internas)."""
    return {
        clave: op for clave, op in protegidas(app).items() if roles(op) != ["servicio"]
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


def test_se_ven_todas_las_rutas(app_real: FastAPI) -> None:
    # Que nunca más queden vacías (ver el docstring).
    claves = operaciones(app_real)

    assert ("GET", "/api/me/progreso") in claves
    assert ("POST", "/api/internal/labs") in claves
    assert ("PATCH", "/api/admin/usuarios/{username}") in claves
    assert len(claves) >= 34


def test_toda_ruta_declara_roles(app_real: FastAPI) -> None:
    sin_roles = [clave for clave, op in operaciones(app_real).items() if not roles(op)]

    assert sin_roles == []


def test_rutas_iguales_al_contrato(app_real: FastAPI) -> None:
    contrato = yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))
    esperadas = {
        (metodo.upper(), PREFIJO + ruta): op
        for ruta, ops in contrato["paths"].items()
        for metodo, op in ops.items()
        if metodo in METODOS
    }

    for clave, op in operaciones(app_real).items():
        assert clave in esperadas, f"{clave} no está en api/openapi.yaml"
        assert op["operationId"] == esperadas[clave]["operationId"], clave
        assert set(roles(op)) == set(esperadas[clave]["x-roles"]), clave


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
        clave: op
        for clave, op in de_sesion(app_con_pruebas).items()
        if "estudiante" not in roles(op)
    }

    assert len(restringidas) >= 2
    for metodo, ruta in restringidas:
        respuesta = await pedir(cliente, metodo, ruta, csrf=True)
        assert respuesta.status_code == 403, (metodo, ruta)
        assert respuesta.json()["codigo"] == "sin_permiso", (metodo, ruta)


async def test_instructor_recibe_403_en_todo_admin(
    crear_cliente, app_real: FastAPI, app_bd: FastAPI, sesion_bd: AsyncSession
) -> None:
    """DoD 3 de la B-08: las rutas reales de /api/admin, no las de prueba."""
    cliente = crear_cliente(app_bd)
    await crear_usuario(sesion_bd, rol="instructor")
    await ingresar(cliente)
    de_admin = [
        clave for clave in de_sesion(app_real) if clave[1].startswith("/api/admin/")
    ]

    assert len(de_admin) == 6
    for metodo, ruta in de_admin:
        assert roles(operaciones(app_real)[metodo, ruta]) == ["admin"], ruta
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
        for clave in de_sesion(app_con_pruebas)
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
