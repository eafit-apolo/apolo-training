"""Contenido del curso: lo carga el importador (B-04) desde content/ del repo.

El importador busca por slug o clave, así que importar dos veces no duplica
filas. Los `orden` únicos son diferibles: se revisan al final de la
transacción, para que el importador pueda reordenar sin chocar a mitad de camino.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.valores import (
    PATRON_CLAVE_PREGUNTA,
    PATRON_CLAVE_VIDEO,
    PRACTICAS,
    SISTEMAS_VIDEO,
    todos_en,
    uno_de,
)


class Curso(Base):
    __tablename__ = "cursos"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    titulo_es: Mapped[str] = mapped_column(Text)
    titulo_en: Mapped[str | None] = mapped_column(Text)
    descripcion_es: Mapped[str | None] = mapped_column(Text)
    descripcion_en: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(server_default=text("1"))
    publicado: Mapped[bool] = mapped_column(server_default=false())


class Modulo(Base):
    """content/<idioma>/mNN/_modulo.md. El siguiente se abre cuando el anterior
    está completo (prerrequisito_id)."""

    __tablename__ = "modulos"
    __table_args__ = (
        UniqueConstraint("curso_id", "slug", name="uq_modulos_curso_id_slug"),
        UniqueConstraint("curso_id", "numero", name="uq_modulos_curso_id_numero"),
        CheckConstraint("numero BETWEEN 0 AND 99", name="numero"),
        CheckConstraint("duracion_min >= 1", name="duracion_min"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    curso_id: Mapped[int] = mapped_column(ForeignKey("cursos.id"))
    # El id del front matter: m05.
    slug: Mapped[str] = mapped_column(Text)
    numero: Mapped[int]
    titulo_es: Mapped[str] = mapped_column(Text)
    titulo_en: Mapped[str | None] = mapped_column(Text)
    resumen_es: Mapped[str] = mapped_column(Text)
    resumen_en: Mapped[str | None] = mapped_column(Text)
    duracion_min: Mapped[int]
    prerrequisito_id: Mapped[int | None] = mapped_column(
        ForeignKey("modulos.id", ondelete="SET NULL")
    )


class Leccion(Base):
    """content/<idioma>/mNN/<slug>.md. No tiene un tipo: trae lo que diga su
    front matter (videos, prácticas y quiz) y se completa cuando se cumple todo."""

    __tablename__ = "lecciones"
    __table_args__ = (
        UniqueConstraint("modulo_id", "slug", name="uq_lecciones_modulo_id_slug"),
        UniqueConstraint(
            "modulo_id",
            "orden",
            name="uq_lecciones_modulo_id_orden",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("orden >= 1", name="orden"),
        CheckConstraint("duracion_min >= 1", name="duracion_min"),
        CheckConstraint(todos_en("practicas", PRACTICAS), name="practicas"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id"))
    slug: Mapped[str] = mapped_column(Text)
    orden: Mapped[int]
    titulo_es: Mapped[str] = mapped_column(Text)
    titulo_en: Mapped[str | None] = mapped_column(Text)
    # Markdown; si falta el inglés, la API devuelve el español (fallback).
    contenido_es: Mapped[str] = mapped_column(Text)
    contenido_en: Mapped[str | None] = mapped_column(Text)
    duracion_min: Mapped[int]
    # Prácticas de la VM de esta lección (lista, como en el front matter).
    practicas: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]")
    )
    # false si la lección salió del repo: se conserva el progreso de los usuarios.
    publicada: Mapped[bool] = mapped_column(server_default=true())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Video(Base):
    """Un video, identificado por su clave (m05-trabajos). El importador crea la
    fila sin archivo; el instructor sube el MP4 y los VTT desde el panel."""

    __tablename__ = "videos"
    __table_args__ = (CheckConstraint(f"clave ~ '{PATRON_CLAVE_VIDEO}'", name="clave"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    clave: Mapped[str] = mapped_column(Text, unique=True)
    # Relativo a /srv/apolo-training/media; null mientras no se haya subido.
    archivo: Mapped[str | None] = mapped_column(Text)
    duracion_seg: Mapped[int | None]
    tamano_bytes: Mapped[int | None] = mapped_column(BigInteger)
    vtt_es: Mapped[str | None] = mapped_column(Text)
    vtt_en: Mapped[str | None] = mapped_column(Text)
    subido_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    subido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeccionVideo(Base):
    """Qué video se muestra en una lección. Casi siempre uno, con sistema
    «todos»; en la lección de VPN, uno por sistema operativo."""

    __tablename__ = "lecciones_videos"
    __table_args__ = (
        CheckConstraint(uno_de("sistema", SISTEMAS_VIDEO), name="sistema"),
    )

    leccion_id: Mapped[int] = mapped_column(
        ForeignKey("lecciones.id", ondelete="CASCADE"), primary_key=True
    )
    sistema: Mapped[str] = mapped_column(Text, primary_key=True, server_default="todos")
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)


class Quiz(Base):
    """El quiz de una lección. Se identifica por su lección."""

    __tablename__ = "quizzes"
    __table_args__ = (CheckConstraint("umbral > 0 AND umbral <= 1", name="umbral"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    leccion_id: Mapped[int] = mapped_column(
        ForeignKey("lecciones.id", ondelete="CASCADE"), unique=True
    )
    umbral: Mapped[Decimal] = mapped_column(Numeric(3, 2), server_default=text("0.80"))
    es_final: Mapped[bool] = mapped_column(server_default=false())


class Pregunta(Base):
    __tablename__ = "preguntas"
    __table_args__ = (
        UniqueConstraint(
            "quiz_id",
            "orden",
            name="uq_preguntas_quiz_id_orden",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(f"clave ~ '{PATRON_CLAVE_PREGUNTA}'", name="clave"),
        CheckConstraint("orden >= 1", name="orden"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    # Estable aunque cambie el texto: así se conservan los intentos anteriores.
    clave: Mapped[str] = mapped_column(Text, unique=True)
    orden: Mapped[int]
    enunciado_es: Mapped[str] = mapped_column(Text)
    enunciado_en: Mapped[str | None] = mapped_column(Text)
    explicacion_es: Mapped[str] = mapped_column(Text)
    explicacion_en: Mapped[str | None] = mapped_column(Text)
    # Más de una opción correcta.
    multiple: Mapped[bool] = mapped_column(server_default=false())


class Opcion(Base):
    __tablename__ = "opciones"
    __table_args__ = (
        UniqueConstraint(
            "pregunta_id",
            "orden",
            name="uq_opciones_pregunta_id_orden",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("orden >= 1", name="orden"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    pregunta_id: Mapped[int] = mapped_column(
        ForeignKey("preguntas.id", ondelete="CASCADE")
    )
    orden: Mapped[int]
    texto_es: Mapped[str] = mapped_column(Text)
    texto_en: Mapped[str | None] = mapped_column(Text)
    # Nunca sale al navegador, ni al calificar (B-06).
    correcta: Mapped[bool] = mapped_column(server_default=false())
