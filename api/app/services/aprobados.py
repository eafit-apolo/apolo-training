"""Quienes aprobaron el curso y esperan su QOS normal, y el CSV de la medición
(B-08).

- **Aprobados pendientes:** estudiantes activos que cumplen las tres
  condiciones de docs/diseno/modelo-datos.md (todas las lecciones, las siete
  prácticas y la graduación aprobada) y todavía no tienen `qos_aplicada_en`.
  `aprobado_en` es cuándo se cumplió la última; van los más viejos primero.
  La plataforma no toca el clúster real: un admin aplica la QOS allá (V-08) y
  marca aquí «QOS aplicada». Marcar a alguien que no está en esa lista es un
  409 (`no_aprobado`, o `qos_ya_aplicada` si ya se marcó).
- **CSV** (instructor y admin): una fila por estudiante, también los dados de
  baja (cuentan como abandono, decisión del 26-nov), con la columna `activo`.
  Instructores y admins no entran: distorsionarían la medición. Coma, UTF-8 y
  fechas ISO 8601 en UTC. Ningún campo puede empezar por `=`, `+`, `-` ni `@`
  (username, clúster y estados tienen patrón fijo), así que no hay fórmulas que
  una hoja de cálculo pueda ejecutar.
"""

import csv
import io
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.core.seguridad import ahora
from app.models import Graduacion, Usuario
from app.schemas.admin import AprobadoPendiente
from app.services import auditoria
from app.services.resumen import resumenes

COLUMNAS_CSV = (
    "username",
    "cluster",
    "activo",
    "creado_en",
    "ultimo_ingreso",
    "avance_pct",
    "modulos_completos",
    "labs_aprobados",
    "graduacion_estado",
    "qos_aplicada_en",
)


async def pendientes(bd: AsyncSession) -> list[AprobadoPendiente]:
    # Primero los que pueden estar (graduación aprobada sin QOS); el resto de
    # la regla la revisa el resumen.
    candidatos = list(
        await bd.scalars(
            select(Usuario)
            .join(Graduacion, Graduacion.usuario_id == Usuario.id)
            .where(
                Usuario.rol == "estudiante",
                Usuario.activo.is_(True),
                Graduacion.estado == "aprobada",
                Graduacion.qos_aplicada_en.is_(None),
            )
            .execution_options(populate_existing=True)
        )
    )
    datos = await resumenes(bd, [u.id for u in candidatos])
    lista = [
        AprobadoPendiente(
            username=u.username,
            nombre=u.nombre,
            cluster=datos[u.id].graduacion.cluster,
            aprobado_en=datos[u.id].aprobado_en,
        )
        for u in candidatos
        if datos[u.id].aprobado
    ]
    return sorted(lista, key=lambda a: (a.aprobado_en, a.username))


async def marcar_qos(
    bd: AsyncSession, username: str, admin: Usuario, ip: str | None
) -> None:
    usuario = await bd.scalar(
        select(Usuario)
        .where(Usuario.username == username)
        .execution_options(populate_existing=True)
    )
    if usuario is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese usuario")
    # FOR UPDATE: dos admins que marcan a la vez no la marcan dos veces.
    graduacion = await bd.scalar(
        select(Graduacion)
        .where(Graduacion.usuario_id == usuario.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if graduacion is not None and graduacion.qos_aplicada_en is not None:
        raise ErrorApi(409, "qos_ya_aplicada", "Ya se había marcado la QOS")
    resumen = (await resumenes(bd, [usuario.id]))[usuario.id]
    if (
        graduacion is None
        or usuario.rol != "estudiante"
        or not usuario.activo
        or not resumen.aprobado
    ):
        raise ErrorApi(409, "no_aprobado", "El usuario todavía no aprobó el curso")
    graduacion.qos_aplicada_en = ahora()
    graduacion.qos_aplicada_por = admin.id
    auditoria.registrar(
        bd,
        "qos_aplicada",
        actor_id=admin.id,
        objetivo=username,
        detalle={"cluster": graduacion.cluster},
        ip=ip,
    )
    await bd.commit()


def _fecha(valor: datetime | None) -> str:
    return valor.astimezone(UTC).isoformat(timespec="seconds") if valor else ""


async def exportar_csv(
    bd: AsyncSession, cluster: str | None, quien: Usuario, ip: str | None
) -> str:
    consulta = select(Usuario).where(Usuario.rol == "estudiante")
    if cluster:
        consulta = consulta.where(Usuario.cluster == cluster)
    usuarios = list(
        await bd.scalars(
            consulta.order_by(Usuario.username).execution_options(
                populate_existing=True
            )
        )
    )
    datos = await resumenes(bd, [u.id for u in usuarios])

    salida = io.StringIO()
    escritor = csv.writer(salida)  # coma y fin de línea \r\n (RFC 4180)
    escritor.writerow(COLUMNAS_CSV)
    for u in usuarios:
        r = datos[u.id]
        escritor.writerow(
            (
                u.username,
                u.cluster,
                "true" if u.activo else "false",
                _fecha(u.creado_en),
                _fecha(u.ultimo_ingreso),
                r.avance_pct,
                r.modulos_completos,
                r.labs_aprobados,
                r.graduacion_estado or "",
                _fecha(r.graduacion.qos_aplicada_en if r.graduacion else None),
            )
        )
    # Sale de la plataforma con datos de personas: queda quién lo bajó.
    auditoria.registrar(
        bd,
        "export_progreso",
        actor_id=quien.id,
        detalle={"cluster": cluster, "filas": len(usuarios)},
        ip=ip,
    )
    await bd.commit()
    return salida.getvalue()
