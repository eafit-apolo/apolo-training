"""Filas de auditoría. Nunca contraseñas, tokens ni lo que escribe el usuario
en un campo que no se pudo validar."""

import ipaddress
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Auditoria


def ip_de(request: Request) -> str | None:
    """IP de quien llama, si es una IP válida.

    Detrás del nginx de borde será la de nginx hasta que se configuren las
    cabeceras del proxy (W-06).
    """
    if request.client is None:
        return None
    try:
        return str(ipaddress.ip_address(request.client.host))
    except ValueError:
        return None


def registrar(
    bd: AsyncSession,
    accion: str,
    *,
    actor_id: int | None = None,
    objetivo: str | None = None,
    detalle: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Agrega la fila a la transacción en curso; la confirma quien llama."""
    bd.add(
        Auditoria(
            actor_id=actor_id,
            accion=accion,
            objetivo=objetivo,
            detalle=detalle,
            ip=ip,
        )
    )
