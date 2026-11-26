"""Ayudas para poner avance a mano en las pruebas (B-07 y B-08): lecciones
completas, prácticas y graduación, sin pasar por la API."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora
from app.models import Graduacion, Leccion, Practica, ProgresoLeccion, Usuario


async def completar(bd: AsyncSession, usuario: Usuario, *slugs: str) -> None:
    for slug in slugs:
        leccion_id = await bd.scalar(select(Leccion.id).where(Leccion.slug == slug))
        bd.add(
            ProgresoLeccion(
                usuario_id=usuario.id, leccion_id=leccion_id, completada_en=ahora()
            )
        )
    await bd.flush()


async def practica(
    bd: AsyncSession, usuario: Usuario, nombre: str, estado: str = "aprobado", **mas
) -> None:
    bd.add(
        Practica(
            usuario_id=usuario.id,
            practica=nombre,
            estado=estado,
            fecha=datetime(2026, 11, 23, 15, tzinfo=UTC),
            **mas,
        )
    )
    await bd.flush()


async def graduacion(bd: AsyncSession, usuario: Usuario, estado: str, **mas) -> None:
    bd.add(
        Graduacion(
            usuario_id=usuario.id,
            cluster="apolo2",
            jobid="98765",
            salida_verificador="[APROBADO] graduacion",
            estado=estado,
            **mas,
        )
    )
    await bd.flush()
