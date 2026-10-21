"""Usuarios de ejemplo para el entorno de desarrollo (B-02).

Los carga el servicio `migrar` de deploy/compose.dev.yaml después de
`alembic upgrade head`:

    python -m app.datos_ejemplo

Solo corre con API_DATOS_EJEMPLO=true, que pone únicamente el compose de
desarrollo: en la VM de la plataforma no carga nada. Se puede correr las veces
que sea: crea los usuarios que falten y no toca los que ya existen.
"""

import asyncio
import logging
import sys
from typing import Any

from argon2 import PasswordHasher
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import crear_engine, crear_sessionmaker
from app.models import Usuario

log = logging.getLogger("app.datos_ejemplo")

# La clave de todos los usuarios de ejemplo. Solo existe en tu base local.
CLAVE_EJEMPLO = "apolo-training-dev"

# Cada rol, cada clúster y los casos que la B-03 necesita probar.
USUARIOS: tuple[dict[str, Any], ...] = (
    {
        "username": "ana",
        "nombre": "Ana (estudiante de Apolo II)",
        "cluster": "apolo2",
        "rol": "estudiante",
        "idioma": "es",
        "debe_cambiar_clave": False,
    },
    {
        "username": "bruno",
        "nombre": "Bruno (estudiante de Apolo III, debe cambiar la clave)",
        "cluster": "apolo3",
        "rol": "estudiante",
        "idioma": "en",
        "debe_cambiar_clave": True,
    },
    {
        "username": "carla",
        "nombre": "Carla (instructora)",
        "cluster": "apolo3",
        "rol": "instructor",
        "idioma": "es",
        "debe_cambiar_clave": False,
    },
    {
        "username": "diego",
        "nombre": "Diego (administrador)",
        "cluster": "apolo2",
        "rol": "admin",
        "idioma": "es",
        "debe_cambiar_clave": False,
    },
    {
        "username": "elena",
        "nombre": "Elena (dada de baja)",
        "cluster": "apolo3",
        "rol": "estudiante",
        "idioma": "es",
        "debe_cambiar_clave": False,
        "activo": False,
    },
)


async def cargar(sesion: AsyncSession) -> int:
    """Crea los usuarios de ejemplo que falten. Devuelve cuántos creó.

    No confirma la transacción: eso lo hace quien llama.
    """
    nombres = [datos["username"] for datos in USUARIOS]
    existentes = set(
        await sesion.scalars(
            select(Usuario.username).where(Usuario.username.in_(nombres))
        )
    )
    hasher = PasswordHasher()
    creados = 0
    for datos in USUARIOS:
        if datos["username"] in existentes:
            continue
        activo = datos.get("activo", True)
        consulta = (
            insert(Usuario)
            .values(
                **datos,
                correo=f"{datos['username']}@example.com",
                clave_hash=hasher.hash(CLAVE_EJEMPLO),
                baja_en=None if activo else func.now(),
            )
            .on_conflict_do_nothing(index_elements=["username"])
            .returning(Usuario.id)
        )
        if (await sesion.execute(consulta)).first() is not None:
            creados += 1
    return creados


async def _cargar_y_confirmar(settings: Settings) -> int:
    engine = crear_engine(settings)
    try:
        async with crear_sessionmaker(engine)() as sesion:
            creados = await cargar(sesion)
            await sesion.commit()
    finally:
        await engine.dispose()
    return creados


def main(settings: Settings | None = None) -> int:
    settings = settings or Settings()
    if not settings.datos_ejemplo:
        log.error(
            "No cargo datos de ejemplo: falta API_DATOS_EJEMPLO=true. "
            "Solo se usa en el entorno de desarrollo."
        )
        return 1
    creados = asyncio.run(_cargar_y_confirmar(settings))
    log.info(
        "Usuarios de ejemplo: %d nuevos de %d (clave: %s).",
        creados,
        len(USUARIOS),
        CLAVE_EJEMPLO,
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    sys.exit(main())
