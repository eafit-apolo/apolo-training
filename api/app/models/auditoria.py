"""Auditoría: solo se agregan filas."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Auditoria(Base):
    """Nunca guarda contraseñas, tokens ni lo que se escribe en una terminal."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # null si fue un servicio, o un ingreso fallido con un usuario que no existe.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # vm-practica; null si fue una persona.
    actor_servicio: Mapped[str | None] = mapped_column(Text)
    # login_ok, login_fallido, alta, baja, graduacion_revisada…
    accion: Mapped[str] = mapped_column(Text)
    # username u objeto afectado.
    objetivo: Mapped[str | None] = mapped_column(Text)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
