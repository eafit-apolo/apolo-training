"""Cookie at, CSRF, renovación (refresh), cierre de sesión y GET/PATCH /api/me."""

from datetime import timedelta

import jwt
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora, token_csrf
from app.models import Auditoria, Sesion, Usuario
from tests.ayuda_sesion import con_csrf, cookies_puestas, crear_usuario, ingresar
from tests.conftest import SECRETO_PRUEBAS


async def sesiones_abiertas(bd: AsyncSession, usuario: Usuario) -> int:
    return await bd.scalar(
        select(func.count())
        .select_from(Sesion)
        .where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None))
    )


# --- Cookie at ----------------------------------------------------------------


async def test_me_sin_sesion(cliente_bd: AsyncClient) -> None:
    respuesta = await cliente_bd.get("/api/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "sin_sesion"


async def test_me_con_token_invalido(cliente_bd: AsyncClient) -> None:
    cliente_bd.cookies.set("at", "no-es-un-jwt")

    respuesta = await cliente_bd.get("/api/me")

    assert respuesta.json()["codigo"] == "token_invalido"


async def test_me_con_token_de_otro_secreto(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    falso = jwt.encode(
        {"sub": str(usuario.id), "sid": 1, "exp": ahora() + timedelta(minutes=5)},
        "otro-secreto-de-32-caracteres-xx",
        algorithm="HS256",
    )
    cliente_bd.cookies.set("at", falso)

    respuesta = await cliente_bd.get("/api/me")

    assert respuesta.json()["codigo"] == "token_invalido"


async def test_me_con_token_vencido(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    vencido = jwt.encode(
        {"sub": str(usuario.id), "sid": 1, "exp": ahora() - timedelta(seconds=1)},
        SECRETO_PRUEBAS,
        algorithm="HS256",
    )
    cliente_bd.cookies.set("at", vencido)

    respuesta = await cliente_bd.get("/api/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_vencido"


async def test_me_con_sesion(cliente_bd: AsyncClient, sesion_bd: AsyncSession) -> None:
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    respuesta = await cliente_bd.get("/api/me")

    assert respuesta.status_code == 200
    assert respuesta.json()["username"] == "tester"


async def test_baja_y_cambio_de_rol_tienen_efecto_al_instante(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    usuario.rol = "admin"
    await sesion_bd.flush()
    assert (await cliente_bd.get("/api/me")).json()["rol"] == "admin"

    usuario.activo = False
    usuario.baja_en = ahora()
    await sesion_bd.flush()
    respuesta = await cliente_bd.get("/api/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "sin_sesion"


# --- CSRF ---------------------------------------------------------------------


async def test_patch_me_exige_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    sin = await cliente_bd.patch("/api/me", json={"idioma": "en"})
    distinto = await cliente_bd.patch(
        "/api/me", json={"idioma": "en"}, headers={"X-CSRF-Token": "x" * 64}
    )
    bien = await cliente_bd.patch(
        "/api/me", json={"idioma": "en"}, headers=con_csrf(cliente_bd)
    )

    assert sin.status_code == distinto.status_code == 403
    assert sin.json()["codigo"] == distinto.json()["codigo"] == "csrf_invalido"
    assert bien.status_code == 200
    assert bien.json()["idioma"] == "en"


async def test_csrf_plantado_por_otro_sitio_no_sirve(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    """Cookie y cabecera iguales, pero no son las de esta sesión."""
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    plantado = "a" * 64
    cliente_bd.cookies.set("csrf", plantado)

    respuesta = await cliente_bd.patch(
        "/api/me", json={"idioma": "en"}, headers={"X-CSRF-Token": plantado}
    )

    assert respuesta.status_code == 403


async def test_csrf_de_otra_sesion_no_sirve(
    app_bd: FastAPI, cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    de_otra = token_csrf(app_bd.state.settings, 999_999)
    cliente_bd.cookies.set("csrf", de_otra)

    respuesta = await cliente_bd.patch(
        "/api/me", json={"idioma": "en"}, headers={"X-CSRF-Token": de_otra}
    )

    assert respuesta.status_code == 403


# --- Refresh ------------------------------------------------------------------


async def test_refresh_rota_las_cookies(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    viejas = dict(cliente_bd.cookies)

    respuesta = await cliente_bd.post("/api/auth/refresh", headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 204
    assert set(cookies_puestas(respuesta)) == {"at", "rt", "csrf"}
    for nombre in ("at", "rt", "csrf"):
        assert cliente_bd.cookies[nombre] != viejas[nombre]
    assert await sesiones_abiertas(sesion_bd, usuario) == 1
    assert (await cliente_bd.get("/api/me")).status_code == 200

    # El at viejo era de la sesión que se rotó: ya no sirve.
    cliente_bd.cookies.set("at", viejas["at"])
    assert (await cliente_bd.get("/api/me")).status_code == 401


async def test_refresh_desliza_los_siete_dias(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    primera = await sesion_bd.scalar(
        select(Sesion).where(Sesion.usuario_id == usuario.id)
    )
    primera.expira_en = ahora() + timedelta(hours=1)
    await sesion_bd.flush()

    await cliente_bd.post("/api/auth/refresh", headers=con_csrf(cliente_bd))

    nueva = await sesion_bd.scalar(
        select(Sesion).where(
            Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None)
        )
    )
    assert nueva.expira_en - ahora() > timedelta(days=6, hours=23)


async def test_refresh_sin_cookie_o_sin_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    sin_cookie = await cliente_bd.post("/api/auth/refresh")
    await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    sin_csrf = await cliente_bd.post("/api/auth/refresh")

    assert sin_cookie.status_code == 401
    assert sin_cookie.json()["codigo"] == "sin_sesion"
    assert sin_csrf.status_code == 403
    assert sin_csrf.json()["codigo"] == "csrf_invalido"


async def test_refresh_vencido(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    sesion = await sesion_bd.scalar(
        select(Sesion).where(Sesion.usuario_id == usuario.id)
    )
    sesion.expira_en = ahora() - timedelta(seconds=1)
    await sesion_bd.flush()

    respuesta = await cliente_bd.post("/api/auth/refresh", headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_vencido"


async def test_dos_pestanas_que_renuevan_a_la_vez(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    viejas = dict(cliente_bd.cookies)
    await cliente_bd.post("/api/auth/refresh", headers=con_csrf(cliente_bd))
    nuevas = dict(cliente_bd.cookies)

    # La otra pestaña manda el rt viejo enseguida: no cambia nada.
    cliente_bd.cookies.set("rt", viejas["rt"], path="/api/auth")
    cliente_bd.cookies.set("csrf", viejas["csrf"])
    respuesta = await cliente_bd.post(
        "/api/auth/refresh", headers={"X-CSRF-Token": viejas["csrf"]}
    )

    assert respuesta.status_code == 204
    assert "set-cookie" not in respuesta.headers
    assert await sesiones_abiertas(sesion_bd, usuario) == 1
    assert nuevas["rt"] != viejas["rt"]


async def test_reuso_de_un_refresh_viejo_cierra_todo(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    viejas = dict(cliente_bd.cookies)
    await cliente_bd.post("/api/auth/refresh", headers=con_csrf(cliente_bd))
    rotada = await sesion_bd.scalar(
        select(Sesion).where(
            Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_not(None)
        )
    )
    rotada.revocada_en = ahora() - timedelta(minutes=1)
    await sesion_bd.flush()

    cliente_bd.cookies.set("rt", viejas["rt"], path="/api/auth")
    cliente_bd.cookies.set("csrf", viejas["csrf"])
    respuesta = await cliente_bd.post(
        "/api/auth/refresh", headers={"X-CSRF-Token": viejas["csrf"]}
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "token_invalido"
    assert await sesiones_abiertas(sesion_bd, usuario) == 0
    assert await sesion_bd.scalar(
        select(Auditoria.id).where(Auditoria.accion == "reuso_refresh")
    )


# --- Logout -------------------------------------------------------------------


async def test_logout_cierra_y_borra_las_cookies(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    at = cliente_bd.cookies["at"]

    respuesta = await cliente_bd.post("/api/auth/logout", headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 204
    borradas = cookies_puestas(respuesta)
    assert set(borradas) == {"at", "rt", "csrf"}
    assert all("max-age=0" in linea for linea in borradas.values())
    assert await sesiones_abiertas(sesion_bd, usuario) == 0
    cliente_bd.cookies.set("at", at)
    assert (await cliente_bd.get("/api/me")).status_code == 401


async def test_logout_con_at_vencido_usa_rt(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)
    cliente_bd.cookies.delete("at")

    respuesta = await cliente_bd.post("/api/auth/logout", headers=con_csrf(cliente_bd))

    assert respuesta.status_code == 204
    assert await sesiones_abiertas(sesion_bd, usuario) == 0


async def test_logout_sin_sesion_responde_204(cliente_bd: AsyncClient) -> None:
    respuesta = await cliente_bd.post("/api/auth/logout")

    assert respuesta.status_code == 204


async def test_logout_sin_csrf_no_cierra(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    await ingresar(cliente_bd)

    respuesta = await cliente_bd.post("/api/auth/logout")

    assert respuesta.status_code == 403
    assert await sesiones_abiertas(sesion_bd, usuario) == 1
