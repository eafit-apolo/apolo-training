"""Cambiar el rol de un usuario desde la consola de la plataforma (B-08).

Sirve para el **primer admin**: sin un admin no hay quién cambie roles desde
/api/admin. El usuario tiene que existir (lo crea `apolo-training-admin alta`
en la VM de práctica). En la 117:

    docker compose exec api python -m app.rol USUARIO admin

Sigue la regla de la ruta de admin: nunca deja la plataforma sin admin activo
(`ultimo_admin`). Queda en la auditoría como `cambio_rol` con
`actor_servicio = consola`. Para todo lo demás, la pantalla de Administración.
"""

import argparse
import asyncio
import logging
import re
import sys

from app.core.errores import ErrorApi
from app.models.valores import PATRON_USERNAME, ROLES

log = logging.getLogger("app.rol")


async def _cambiar(username: str, rol: str) -> tuple[str, str]:
    from app.core.config import Settings
    from app.core.db import crear_engine, crear_sessionmaker
    from app.services.usuarios import SERVICIO_CONSOLA, cambiar_rol

    engine = crear_engine(Settings())
    try:
        async with crear_sessionmaker(engine)() as sesion:
            return await cambiar_rol(
                sesion, username, rol, actor_servicio=SERVICIO_CONSOLA
            )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.rol",
        description="Cambia el rol de un usuario de la plataforma (el primer admin).",
    )
    parser.add_argument("usuario", help="el username, que ya debe existir")
    parser.add_argument("rol", choices=ROLES)
    args = parser.parse_args(argv)
    if not re.fullmatch(PATRON_USERNAME, args.usuario):
        log.error("%r no es un username válido.", args.usuario)
        return 2
    try:
        antes, ahora = asyncio.run(_cambiar(args.usuario, args.rol))
    except ErrorApi as exc:
        log.error("%s: %s", args.usuario, exc.detail)
        return 1
    if antes == ahora:
        log.info("%s ya era %s: no cambió nada.", args.usuario, ahora)
    else:
        log.info("%s: %s → %s.", args.usuario, antes, ahora)
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    sys.exit(main())
