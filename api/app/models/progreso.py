"""Progreso de cada usuario: quices, lecciones, prácticas y graduación."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.valores import (
    CLUSTERS,
    ESTADOS_GRADUACION,
    ESTADOS_PRACTICA,
    PATRON_JOBID,
    PRACTICAS,
    uno_de,
)


class Intento(Base):
    """Cada envío de un quiz. Intentos ilimitados; cuenta el mejor."""

    __tablename__ = "intentos"
    __table_args__ = (
        CheckConstraint("puntaje BETWEEN 0 AND 100", name="puntaje"),
        Index("ix_intentos_usuario_id_quiz_id", "usuario_id", "quiz_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"))
    puntaje: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    aprobado: Mapped[bool]
    # {"<pregunta_id>": [<opcion_id>, ...]}
    respuestas: Mapped[dict[str, Any]] = mapped_column(JSONB)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProgresoLeccion(Base):
    """Una fila por usuario y lección, creada en el primer reporte."""

    __tablename__ = "progreso_lecciones"
    __table_args__ = (
        CheckConstraint("video_posicion_seg >= 0", name="video_posicion_seg"),
        CheckConstraint("video_max_seg >= 0", name="video_max_seg"),
    )

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    leccion_id: Mapped[int] = mapped_column(
        ForeignKey("lecciones.id"), primary_key=True, index=True
    )
    # Dónde se reanuda y lo más lejos que llegó.
    video_posicion_seg: Mapped[int] = mapped_column(server_default=text("0"))
    video_max_seg: Mapped[int] = mapped_column(server_default=text("0"))
    video_completo: Mapped[bool] = mapped_column(server_default=false())
    quiz_aprobado: Mapped[bool] = mapped_column(server_default=false())
    # Se llena una sola vez.
    completada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Practica(Base):
    """El último estado de cada práctica por usuario, como lo envía la VM de
    práctica (V-05). Un aprobado nunca se reemplaza por un intentado."""

    __tablename__ = "practicas"
    __table_args__ = (
        CheckConstraint(uno_de("practica", PRACTICAS), name="practica"),
        CheckConstraint(uno_de("estado", ESTADOS_PRACTICA), name="estado"),
    )

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    practica: Mapped[str] = mapped_column(Text, primary_key=True)
    estado: Mapped[str] = mapped_column(Text)
    # Solo las de Slurm tienen trabajo; conexion, terminal y archivos no.
    jobid: Mapped[str | None] = mapped_column(Text)
    # Mensaje del verificador.
    detalle: Mapped[str | None] = mapped_column(Text)
    # Fin del trabajo en Slurm, o cuándo se verificó si no hay trabajo.
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sincronizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Sincronizacion(Base):
    """Cada envío de la VM, aunque no traiga cambios: de aquí sale la «última
    sincronización» de Mi progreso."""

    __tablename__ = "sincronizaciones"
    __table_args__ = (
        CheckConstraint("aceptados BETWEEN 0 AND registros", name="aceptados"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    recibida_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    registros: Mapped[int]
    aceptados: Mapped[int]
    origen: Mapped[str] = mapped_column(Text, server_default="vm-practica")


class Graduacion(Base):
    """Una por usuario: el trabajo por lotes de su clúster real (V-07) y la
    salida de apolo-training verificar graduacion. La revisa un instructor."""

    __tablename__ = "graduaciones"
    __table_args__ = (
        CheckConstraint(uno_de("cluster", CLUSTERS), name="cluster"),
        CheckConstraint(f"jobid ~ '{PATRON_JOBID}'", name="jobid"),
        CheckConstraint(uno_de("estado", ESTADOS_GRADUACION), name="estado"),
    )

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    cluster: Mapped[str] = mapped_column(Text)
    jobid: Mapped[str] = mapped_column(Text)
    salida_verificador: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text, server_default="enviada", index=True)
    enviada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revisada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    revisada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comentario: Mapped[str | None] = mapped_column(Text)
    qos_aplicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qos_aplicada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
