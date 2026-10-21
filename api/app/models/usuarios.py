"""Personas y sesiones."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.valores import CLUSTERS, IDIOMAS, PATRON_USERNAME, ROLES, uno_de


class Usuario(Base):
    """Una fila por persona. Una baja no borra la fila: pone activo = false."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(f"username ~ '{PATRON_USERNAME}'", name="username"),
        CheckConstraint(uno_de("cluster", CLUSTERS), name="cluster"),
        CheckConstraint(uno_de("rol", ROLES), name="rol"),
        CheckConstraint(uno_de("idioma", IDIOMAS), name="idioma"),
        CheckConstraint("intentos_fallidos >= 0", name="intentos_fallidos"),
        # Activo y sin fecha de baja, o dado de baja con su fecha.
        CheckConstraint("activo = (baja_en IS NULL)", name="baja"),
        Index("ix_usuarios_cluster_activo", "cluster", "activo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # El mismo usuario de su clúster y de la VM de práctica: no se cambia.
    username: Mapped[str] = mapped_column(Text, unique=True)
    nombre: Mapped[str] = mapped_column(Text)
    correo: Mapped[str | None] = mapped_column(Text)
    cluster: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(Text, server_default="estudiante")
    idioma: Mapped[str] = mapped_column(Text, server_default="es")
    # argon2id. Nunca se guarda la contraseña.
    clave_hash: Mapped[str] = mapped_column(Text)
    debe_cambiar_clave: Mapped[bool] = mapped_column(server_default=true())
    intentos_fallidos: Mapped[int] = mapped_column(server_default=text("0"))
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo: Mapped[bool] = mapped_column(server_default=true())
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    baja_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_ingreso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Sesion(Base):
    """Un refresh token emitido. Solo se guarda su hash."""

    __tablename__ = "sesiones"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # sha256 del refresh token.
    refresh_hash: Mapped[str] = mapped_column(Text, unique=True)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_uso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
