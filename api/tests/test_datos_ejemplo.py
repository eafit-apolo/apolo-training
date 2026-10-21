"""Usuarios de ejemplo del entorno de desarrollo (B-02)."""

import logging

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import datos_ejemplo
from app.core.config import Settings
from app.models import Usuario
from app.models.valores import CLUSTERS, ROLES


async def usuarios_de_ejemplo(sesion: AsyncSession) -> list[Usuario]:
    nombres = [datos["username"] for datos in datos_ejemplo.USUARIOS]
    return list(
        await sesion.scalars(select(Usuario).where(Usuario.username.in_(nombres)))
    )


async def test_carga_cada_rol_y_cada_cluster(sesion_bd: AsyncSession) -> None:
    creados = await datos_ejemplo.cargar(sesion_bd)
    usuarios = await usuarios_de_ejemplo(sesion_bd)

    assert creados == len(datos_ejemplo.USUARIOS) == len(usuarios)
    assert {u.rol for u in usuarios} == set(ROLES)
    assert {u.cluster for u in usuarios} == set(CLUSTERS)
    assert any(u.debe_cambiar_clave for u in usuarios)
    inactivos = [u for u in usuarios if not u.activo]
    assert len(inactivos) == 1
    assert inactivos[0].baja_en is not None


async def test_la_clave_queda_con_argon2id(sesion_bd: AsyncSession) -> None:
    await datos_ejemplo.cargar(sesion_bd)
    usuarios = await usuarios_de_ejemplo(sesion_bd)

    hasher = PasswordHasher()
    for usuario in usuarios:
        assert usuario.clave_hash.startswith("$argon2id$")
        assert hasher.verify(usuario.clave_hash, datos_ejemplo.CLAVE_EJEMPLO)


async def test_cargar_dos_veces_no_duplica(sesion_bd: AsyncSession) -> None:
    await datos_ejemplo.cargar(sesion_bd)

    assert await datos_ejemplo.cargar(sesion_bd) == 0
    assert len(await usuarios_de_ejemplo(sesion_bd)) == len(datos_ejemplo.USUARIOS)


def test_no_corre_sin_la_variable(
    settings_sin_base: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    # settings_sin_base no tiene base: si intentara conectarse, fallaría distinto.
    with caplog.at_level(logging.ERROR):
        assert datos_ejemplo.main(settings_sin_base) == 1

    assert "API_DATOS_EJEMPLO=true" in caplog.text
