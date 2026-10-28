"""Las contraseñas nunca aparecen en registros (DoD 3 de la B-03).

Recorre login correcto y errado, bloqueo, cambio de clave y un usuario mal
escrito con todo el registro en DEBUG, y busca las claves en lo registrado, en
la auditoría y en las respuestas. (A PostgreSQL nunca llega la clave, solo el
hash: el SQL no podría mostrarla.)
"""

import logging

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Auditoria
from tests.ayuda_sesion import CLAVE, con_csrf, crear_usuario, ingresar

ERRADA = "Errada-Que-No-Debe-Salir"
NUEVA = "Nueva-Que-No-Debe-Salir"
EN_EL_CAMPO_DE_USUARIO = "MiClave Secreta!"


async def test_ninguna_clave_queda_registrada(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await crear_usuario(sesion_bd)
    respuestas = []

    for _ in range(5):
        respuestas.append(await ingresar(cliente_bd, clave=ERRADA))
    usuario = await crear_usuario(sesion_bd, username="otro")
    respuestas.append(await ingresar(cliente_bd, username="otro"))
    respuestas.append(
        await cliente_bd.post(
            "/api/auth/cambiar-clave",
            json={"clave_actual": CLAVE, "clave_nueva": NUEVA},
            headers=con_csrf(cliente_bd),
        )
    )
    respuestas.append(
        await cliente_bd.post(
            "/api/auth/cambiar-clave",
            json={"clave_actual": ERRADA, "clave_nueva": "corta"},
            headers=con_csrf(cliente_bd),
        )
    )
    # Alguien escribe la clave en el campo del usuario.
    respuestas.append(
        await cliente_bd.post(
            "/api/auth/login",
            json={"username": EN_EL_CAMPO_DE_USUARIO, "clave": CLAVE},
        )
    )
    respuestas.append(await ingresar(cliente_bd, username="nadie", clave=ERRADA))

    auditoria = [
        f"{fila.accion} {fila.objetivo} {fila.detalle}"
        for fila in await sesion_bd.scalars(select(Auditoria))
    ]
    assert len(auditoria) >= 8
    # El registro sí capturó las peticiones: la prueba miró algo.
    assert "/api/auth/login" in caplog.text
    assert usuario.clave_hash.startswith("$argon2id$")
    for clave in (CLAVE, ERRADA, NUEVA, "corta", EN_EL_CAMPO_DE_USUARIO):
        assert clave not in caplog.text, clave
        assert all(clave not in linea for linea in auditoria), clave
        assert all(clave not in r.text for r in respuestas), clave
