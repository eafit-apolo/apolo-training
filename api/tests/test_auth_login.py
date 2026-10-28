"""POST /api/auth/login: clave correcta, errada, bloqueo y cuentas de baja."""

from datetime import timedelta

import pytest
from argon2 import PasswordHasher
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora
from app.models import Auditoria, Sesion, Usuario
from tests.ayuda_sesion import CLAVE, cookies_puestas, crear_usuario, ingresar


async def acciones(bd: AsyncSession) -> list[tuple[str, str | None]]:
    filas = await bd.execute(
        select(Auditoria.accion, Auditoria.objetivo).order_by(Auditoria.id)
    )
    return [tuple(fila) for fila in filas]


async def test_login_correcto(cliente_bd: AsyncClient, sesion_bd: AsyncSession) -> None:
    usuario = await crear_usuario(sesion_bd)

    respuesta = await ingresar(cliente_bd)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "usuario": {
            "username": "tester",
            "nombre": "Prueba tester",
            "correo": None,
            "cluster": "apolo2",
            "rol": "estudiante",
            "idioma": "es",
            "debe_cambiar_clave": False,
            "activo": True,
        }
    }
    await sesion_bd.refresh(usuario)
    assert usuario.ultimo_ingreso is not None
    assert await sesion_bd.scalar(
        select(Sesion.id).where(Sesion.usuario_id == usuario.id)
    )
    assert ("login_ok", "tester") in await acciones(sesion_bd)


async def test_cookies_de_la_sesion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd)

    cookies = cookies_puestas(await ingresar(cliente_bd))

    assert set(cookies) == {"at", "rt", "csrf"}
    for linea in cookies.values():
        assert "secure" in linea
        assert "samesite=strict" in linea
    assert "httponly" in cookies["at"]
    assert "httponly" in cookies["rt"]
    assert "httponly" not in cookies["csrf"]
    assert "path=/;" in cookies["at"]
    assert "path=/api/auth" in cookies["rt"]
    assert "max-age=900" in cookies["at"]
    assert "max-age=604800" in cookies["rt"]


async def test_clave_errada(cliente_bd: AsyncClient, sesion_bd: AsyncSession) -> None:
    usuario = await crear_usuario(sesion_bd)

    respuesta = await ingresar(cliente_bd, clave="otra-clave-cualquiera")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "clave_incorrecta"
    assert "set-cookie" not in respuesta.headers
    await sesion_bd.refresh(usuario)
    assert usuario.intentos_fallidos == 1
    assert ("login_fallido", "tester") in await acciones(sesion_bd)


async def test_usuario_inexistente_responde_igual_y_no_guarda_lo_escrito(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    respuesta = await ingresar(cliente_bd, username="nadie")

    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "clave_incorrecta"
    fila = await sesion_bd.scalar(select(Auditoria).order_by(Auditoria.id.desc()))
    assert fila.accion == "login_fallido"
    assert fila.objetivo is None
    assert fila.actor_id is None
    assert fila.detalle == {"motivo": "usuario_inexistente"}


async def test_bloqueo_tras_cinco_fallos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)

    for _ in range(4):
        assert (await ingresar(cliente_bd, clave="errada-errada")).status_code == 401
    quinto = await ingresar(cliente_bd, clave="errada-errada")

    assert quinto.status_code == 403
    assert quinto.json()["codigo"] == "cuenta_bloqueada"
    await sesion_bd.refresh(usuario)
    assert usuario.intentos_fallidos == 0
    assert usuario.bloqueado_hasta is not None
    falta = usuario.bloqueado_hasta - ahora()
    assert timedelta(minutes=14) < falta <= timedelta(minutes=15)
    assert quinto.json()["bloqueado_hasta"] == usuario.bloqueado_hasta.isoformat()
    assert ("cuenta_bloqueada", "tester") in await acciones(sesion_bd)

    # Bloqueada, ni la clave correcta entra (y no se revisa).
    con_la_buena = await ingresar(cliente_bd)
    assert con_la_buena.status_code == 403
    assert con_la_buena.json()["codigo"] == "cuenta_bloqueada"


async def test_pasado_el_bloqueo_vuelve_a_entrar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    usuario.bloqueado_hasta = ahora() - timedelta(seconds=1)
    await sesion_bd.flush()

    respuesta = await ingresar(cliente_bd)

    assert respuesta.status_code == 200
    await sesion_bd.refresh(usuario)
    assert usuario.bloqueado_hasta is None


async def test_entrar_bien_reinicia_los_fallos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    for _ in range(3):
        await ingresar(cliente_bd, clave="errada-errada")

    assert (await ingresar(cliente_bd)).status_code == 200
    await sesion_bd.refresh(usuario)
    assert usuario.intentos_fallidos == 0


async def test_cuenta_de_baja_solo_se_dice_con_la_clave_correcta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, activo=False)

    errada = await ingresar(cliente_bd, clave="errada-errada")
    correcta = await ingresar(cliente_bd)

    assert errada.status_code == 401
    assert errada.json()["codigo"] == "clave_incorrecta"
    assert correcta.status_code == 403
    assert correcta.json()["codigo"] == "cuenta_inactiva"
    assert "set-cookie" not in correcta.headers


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"username": "Con Mayúsculas", "clave": CLAVE},
        {"username": "tester", "clave": ""},
        {"username": "tester", "clave": "x" * 129},
        {"username": "tester"},
    ],
)
async def test_datos_invalidos(cliente_bd: AsyncClient, cuerpo: dict) -> None:
    respuesta = await cliente_bd.post("/api/auth/login", json=cuerpo)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"


async def test_rehace_un_hash_con_parametros_viejos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    usuario = await crear_usuario(sesion_bd)
    usuario.clave_hash = PasswordHasher(time_cost=1, memory_cost=8192).hash(CLAVE)
    await sesion_bd.flush()
    viejo = usuario.clave_hash

    assert (await ingresar(cliente_bd)).status_code == 200
    await sesion_bd.refresh(usuario)
    assert usuario.clave_hash != viejo
    assert PasswordHasher().verify(usuario.clave_hash, CLAVE)


async def test_el_rol_sale_de_la_base(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, rol="instructor")

    respuesta = await ingresar(cliente_bd)

    assert respuesta.json()["usuario"]["rol"] == "instructor"
    assert (
        await sesion_bd.scalar(select(Usuario.rol).where(Usuario.username == "tester"))
        == "instructor"
    )
