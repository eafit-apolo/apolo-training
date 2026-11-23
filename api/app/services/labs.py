"""Sincronización de las prácticas desde la VM de práctica (B-07).

La VM (V-05) manda cada 5 minutos el reporte **completo**: el mejor estado de
cada práctica de cada usuario. Reglas:

- upsert por usuario y práctica: enviar el mismo reporte dos veces no cambia
  nada (DoD 2), y si un envío se pierde, el siguiente lo corrige;
- un `aprobado` nunca retrocede ni se reescribe (se queda el primer JobID que
  la aprobó); un `intentado` sobre un aprobado vuelve en `ignorados` con
  `no_retrocede`;
- un usuario que la plataforma no conoce, o dado de baja, vuelve en
  `ignorados` sin romper el resto del envío;
- el mismo usuario y práctica dos veces en un envío es un error del reporte
  (422 `registro_repetido`): no se guarda nada;
- cada envío queda en `sincronizaciones`, aunque no traiga cambios: de ahí sale
  la «última sincronización» de Mi progreso.
"""

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import Practica, Sincronizacion, Usuario
from app.schemas.labs import (
    Ignorado,
    RegistroLab,
    ReporteLabs,
    ResultadoSincronizacion,
)

# asyncpg admite hasta 32 767 parámetros por sentencia: 6 por fila.
POR_LOTE = 1000


def _sin_repetidos(registros: list[RegistroLab]) -> None:
    vistos: set[tuple[str, str]] = set()
    for registro in registros:
        clave = (registro.usuario, registro.lab)
        if clave in vistos:
            raise ErrorApi(
                422,
                "registro_repetido",
                f"El reporte trae dos veces {registro.usuario}/{registro.lab}",
            )
        vistos.add(clave)


async def _aprobadas(
    bd: AsyncSession, validos: list[tuple[int, RegistroLab]]
) -> set[tuple[int, str]]:
    """(usuario_id, práctica) de las que ya están aprobadas en la base."""
    if not validos:
        return set()
    return set(
        (
            await bd.execute(
                select(Practica.usuario_id, Practica.practica).where(
                    Practica.estado == "aprobado",
                    tuple_(Practica.usuario_id, Practica.practica).in_(
                        [(usuario_id, r.lab) for usuario_id, r in validos]
                    ),
                )
            )
        ).all()
    )


async def sincronizar(
    bd: AsyncSession, reporte: ReporteLabs
) -> ResultadoSincronizacion:
    registros = reporte.registros
    _sin_repetidos(registros)

    usuarios = {
        username: (usuario_id, activo)
        for username, usuario_id, activo in await bd.execute(
            select(Usuario.username, Usuario.id, Usuario.activo).where(
                Usuario.username.in_(sorted({r.usuario for r in registros}))
            )
        )
    }
    ignorados: list[Ignorado] = []
    validos: list[tuple[int, RegistroLab]] = []
    for registro in registros:
        usuario = usuarios.get(registro.usuario)
        if usuario is None or not usuario[1]:
            motivo = "usuario_desconocido" if usuario is None else "usuario_inactivo"
            ignorados.append(
                Ignorado(usuario=registro.usuario, lab=registro.lab, motivo=motivo)
            )
        else:
            validos.append((usuario[0], registro))

    aprobadas = await _aprobadas(bd, validos)

    filas = []
    for usuario_id, registro in validos:
        if (usuario_id, registro.lab) in aprobadas:
            if registro.estado == "intentado":
                ignorados.append(
                    Ignorado(
                        usuario=registro.usuario,
                        lab=registro.lab,
                        motivo="no_retrocede",
                    )
                )
            # Un aprobado sobre otro aprobado no cambia nada.
            continue
        filas.append(
            {
                "usuario_id": usuario_id,
                "practica": registro.lab,
                "estado": registro.estado,
                "jobid": registro.jobid,
                "detalle": registro.detalle,
                "fecha": registro.fecha,
            }
        )

    for inicio in range(0, len(filas), POR_LOTE):
        sentencia = insert(Practica).values(filas[inicio : inicio + POR_LOTE])
        nuevo = sentencia.excluded
        await bd.execute(
            sentencia.on_conflict_do_update(
                index_elements=[Practica.usuario_id, Practica.practica],
                set_={
                    "estado": nuevo.estado,
                    "jobid": nuevo.jobid,
                    "detalle": nuevo.detalle,
                    "fecha": nuevo.fecha,
                    "sincronizado_en": nuevo.sincronizado_en,
                },
                # Un aprobado no se toca (también si otro envío lo aprobó
                # entre la consulta de arriba y esta), y una fila igual
                # tampoco: así su `sincronizado_en` dice cuándo cambió.
                where=(Practica.estado != "aprobado")
                & tuple_(
                    Practica.estado, Practica.jobid, Practica.detalle, Practica.fecha
                ).is_distinct_from(
                    tuple_(nuevo.estado, nuevo.jobid, nuevo.detalle, nuevo.fecha)
                ),
            )
        )

    aceptados = len(registros) - len(ignorados)
    bd.add(Sincronizacion(registros=len(registros), aceptados=aceptados))
    await bd.commit()
    return ResultadoSincronizacion(aceptados=aceptados, ignorados=ignorados)
