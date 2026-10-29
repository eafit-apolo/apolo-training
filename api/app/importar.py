"""Importador de contenido (B-04): carga content/ del repo en la base.

    python -m app.importar              # valida y carga (usa API_DATABASE_URL)
    python -m app.importar --revisar    # solo valida; no necesita la base (CI)
    python -m app.importar --dir RUTA   # otra carpeta content/

Por defecto lee la carpeta content/ que está dos niveles arriba de app/: la
raíz del repo, o /content en los servicios migrar y pruebas de
deploy/compose.dev.yaml, que la montan en solo lectura. Si algo no cumple los
esquemas o las reglas de content/README.md, no carga nada y dice cada error con
su archivo. Se puede correr las veces que sea: lo que no cambió no se toca.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.services.contenido_lector import (
    CursoLeido,
    ErrorContenido,
    leer_contenido,
    revisar_plantillas,
)

log = logging.getLogger("app.importar")

CONTENIDO = Path(__file__).resolve().parents[2] / "content"


async def _cargar(curso: CursoLeido) -> str:
    # Solo aquí hace falta la base (y la configuración): --revisar no la usa.
    from app.core.config import Settings
    from app.core.db import crear_engine, crear_sessionmaker
    from app.services.contenido_carga import cargar_contenido

    engine = crear_engine(Settings())
    try:
        async with crear_sessionmaker(engine)() as sesion:
            resumen = await cargar_contenido(sesion, curso)
            await sesion.commit()
    finally:
        await engine.dispose()
    return resumen.texto()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.importar",
        description="Valida content/ y lo carga en la base de la API.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=CONTENIDO,
        help=f"carpeta content/ (por defecto {CONTENIDO})",
    )
    parser.add_argument(
        "--revisar", action="store_true", help="solo valida, sin tocar la base"
    )
    args = parser.parse_args(argv)

    try:
        curso = leer_contenido(args.dir)
        errores = revisar_plantillas(args.dir)
        if errores:
            raise ErrorContenido(errores)
    except ErrorContenido as exc:
        for error in exc.errores:
            log.error("%s", error)
        log.error("Contenido con %d errores: no se cargó nada.", len(exc.errores))
        return 1

    log.info(
        "Contenido válido: curso %s, %d módulos, %d lecciones y %d preguntas.",
        curso.slug,
        len(curso.modulos),
        curso.lecciones,
        curso.preguntas,
    )
    if args.revisar:
        return 0
    try:
        resumen = asyncio.run(_cargar(curso))
    except ErrorContenido as exc:
        for error in exc.errores:
            log.error("%s", error)
        log.error("No se cargó nada.")
        return 1
    log.info("Importado: %s.", resumen)
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    sys.exit(main())
