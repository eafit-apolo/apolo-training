"""Modelo de datos inicial (B-02): todas las tablas de la plataforma.

Diagrama y reglas en docs/diseno/modelo-datos.md. Revisada a mano: los CHECK
de estados, los `orden` únicos diferibles y los índices de las tablas de
progreso (usuario_id y leccion_id) son los del diseño.

Revision ID: dd3ec210722f
Revises:
Create Date: 2026-10-21 14:20:00.326110+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "dd3ec210722f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cursos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("titulo_es", sa.Text(), nullable=False),
        sa.Column("titulo_en", sa.Text(), nullable=True),
        sa.Column("descripcion_es", sa.Text(), nullable=True),
        sa.Column("descripcion_en", sa.Text(), nullable=True),
        sa.Column("orden", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "publicado", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cursos")),
        sa.UniqueConstraint("slug", name=op.f("uq_cursos_slug")),
    )
    op.create_table(
        "sincronizaciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "recibida_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("registros", sa.Integer(), nullable=False),
        sa.Column("aceptados", sa.Integer(), nullable=False),
        sa.Column("origen", sa.Text(), server_default="vm-practica", nullable=False),
        sa.CheckConstraint(
            "aceptados BETWEEN 0 AND registros",
            name=op.f("ck_sincronizaciones_aceptados"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sincronizaciones")),
    )
    op.create_index(
        op.f("ix_sincronizaciones_recibida_en"),
        "sincronizaciones",
        ["recibida_en"],
        unique=False,
    )
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("correo", sa.Text(), nullable=True),
        sa.Column("cluster", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), server_default="estudiante", nullable=False),
        sa.Column("idioma", sa.Text(), server_default="es", nullable=False),
        sa.Column("clave_hash", sa.Text(), nullable=False),
        sa.Column(
            "debe_cambiar_clave",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "intentos_fallidos",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "activo", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("baja_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_ingreso", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "cluster IN ('apolo2', 'apolo3')", name=op.f("ck_usuarios_cluster")
        ),
        sa.CheckConstraint("idioma IN ('es', 'en')", name=op.f("ck_usuarios_idioma")),
        sa.CheckConstraint(
            "rol IN ('estudiante', 'instructor', 'admin')", name=op.f("ck_usuarios_rol")
        ),
        sa.CheckConstraint(
            "username ~ '^[a-z_][a-z0-9_-]{0,31}$'", name=op.f("ck_usuarios_username")
        ),
        sa.CheckConstraint("activo = (baja_en IS NULL)", name=op.f("ck_usuarios_baja")),
        sa.CheckConstraint(
            "intentos_fallidos >= 0", name=op.f("ck_usuarios_intentos_fallidos")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuarios")),
        sa.UniqueConstraint("username", name=op.f("uq_usuarios_username")),
    )
    op.create_index(
        "ix_usuarios_cluster_activo", "usuarios", ["cluster", "activo"], unique=False
    )
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_servicio", sa.Text(), nullable=True),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("objetivo", sa.Text(), nullable=True),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["usuarios.id"], name=op.f("fk_auditoria_actor_id_usuarios")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria")),
    )
    op.create_index(
        op.f("ix_auditoria_actor_id"), "auditoria", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_auditoria_creado_en"), "auditoria", ["creado_en"], unique=False
    )
    op.create_table(
        "graduaciones",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("cluster", sa.Text(), nullable=False),
        sa.Column("jobid", sa.Text(), nullable=False),
        sa.Column("salida_verificador", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), server_default="enviada", nullable=False),
        sa.Column(
            "enviada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revisada_por", sa.BigInteger(), nullable=True),
        sa.Column("revisada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("qos_aplicada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qos_aplicada_por", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "cluster IN ('apolo2', 'apolo3')", name=op.f("ck_graduaciones_cluster")
        ),
        sa.CheckConstraint(
            "estado IN ('enviada', 'aprobada', 'rechazada')",
            name=op.f("ck_graduaciones_estado"),
        ),
        sa.CheckConstraint(
            "jobid ~ '^[0-9]+(_[0-9]+)?$'", name=op.f("ck_graduaciones_jobid")
        ),
        sa.ForeignKeyConstraint(
            ["qos_aplicada_por"],
            ["usuarios.id"],
            name=op.f("fk_graduaciones_qos_aplicada_por_usuarios"),
        ),
        sa.ForeignKeyConstraint(
            ["revisada_por"],
            ["usuarios.id"],
            name=op.f("fk_graduaciones_revisada_por_usuarios"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_graduaciones_usuario_id_usuarios"),
        ),
        sa.PrimaryKeyConstraint("usuario_id", name=op.f("pk_graduaciones")),
    )
    op.create_index(
        op.f("ix_graduaciones_estado"), "graduaciones", ["estado"], unique=False
    )
    op.create_table(
        "modulos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("curso_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("titulo_es", sa.Text(), nullable=False),
        sa.Column("titulo_en", sa.Text(), nullable=True),
        sa.Column("resumen_es", sa.Text(), nullable=False),
        sa.Column("resumen_en", sa.Text(), nullable=True),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("prerrequisito_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("duracion_min >= 1", name=op.f("ck_modulos_duracion_min")),
        sa.CheckConstraint("numero BETWEEN 0 AND 99", name=op.f("ck_modulos_numero")),
        sa.ForeignKeyConstraint(
            ["curso_id"], ["cursos.id"], name=op.f("fk_modulos_curso_id_cursos")
        ),
        sa.ForeignKeyConstraint(
            ["prerrequisito_id"],
            ["modulos.id"],
            name=op.f("fk_modulos_prerrequisito_id_modulos"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modulos")),
        sa.UniqueConstraint("curso_id", "numero", name="uq_modulos_curso_id_numero"),
        sa.UniqueConstraint("curso_id", "slug", name="uq_modulos_curso_id_slug"),
    )
    op.create_table(
        "practicas",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("practica", sa.Text(), nullable=False),
        sa.Column("estado", sa.Text(), nullable=False),
        sa.Column("jobid", sa.Text(), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "sincronizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado IN ('intentado', 'aprobado')", name=op.f("ck_practicas_estado")
        ),
        sa.CheckConstraint(
            "practica IN ('conexion', 'terminal', 'archivos', 'modulos', 'memoria', 'nucleos', 'paralelo')",
            name=op.f("ck_practicas_practica"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_practicas_usuario_id_usuarios"),
        ),
        sa.PrimaryKeyConstraint("usuario_id", "practica", name=op.f("pk_practicas")),
    )
    op.create_table(
        "sesiones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_hash", sa.Text(), nullable=False),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultimo_uso_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_sesiones_usuario_id_usuarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesiones")),
        sa.UniqueConstraint("refresh_hash", name=op.f("uq_sesiones_refresh_hash")),
    )
    op.create_index(
        op.f("ix_sesiones_usuario_id"), "sesiones", ["usuario_id"], unique=False
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("archivo", sa.Text(), nullable=True),
        sa.Column("duracion_seg", sa.Integer(), nullable=True),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=True),
        sa.Column("vtt_es", sa.Text(), nullable=True),
        sa.Column("vtt_en", sa.Text(), nullable=True),
        sa.Column("subido_por", sa.BigInteger(), nullable=True),
        sa.Column("subido_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "clave ~ '^m[0-9]{2}-[a-z0-9-]+$'", name=op.f("ck_videos_clave")
        ),
        sa.ForeignKeyConstraint(
            ["subido_por"], ["usuarios.id"], name=op.f("fk_videos_subido_por_usuarios")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos")),
        sa.UniqueConstraint("clave", name=op.f("uq_videos_clave")),
    )
    op.create_table(
        "lecciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("modulo_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("titulo_es", sa.Text(), nullable=False),
        sa.Column("titulo_en", sa.Text(), nullable=True),
        sa.Column("contenido_es", sa.Text(), nullable=False),
        sa.Column("contenido_en", sa.Text(), nullable=True),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column(
            "practicas",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "publicada", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "practicas <@ ARRAY['conexion', 'terminal', 'archivos', 'modulos', 'memoria', 'nucleos', 'paralelo']::text[]",
            name=op.f("ck_lecciones_practicas"),
        ),
        sa.CheckConstraint("duracion_min >= 1", name=op.f("ck_lecciones_duracion_min")),
        sa.CheckConstraint("orden >= 1", name=op.f("ck_lecciones_orden")),
        sa.ForeignKeyConstraint(
            ["modulo_id"], ["modulos.id"], name=op.f("fk_lecciones_modulo_id_modulos")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lecciones")),
        sa.UniqueConstraint(
            "modulo_id",
            "orden",
            deferrable=True,
            initially="DEFERRED",
            name="uq_lecciones_modulo_id_orden",
        ),
        sa.UniqueConstraint("modulo_id", "slug", name="uq_lecciones_modulo_id_slug"),
    )
    op.create_table(
        "lecciones_videos",
        sa.Column("leccion_id", sa.BigInteger(), nullable=False),
        sa.Column("sistema", sa.Text(), server_default="todos", nullable=False),
        sa.Column("video_id", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "sistema IN ('todos', 'windows', 'macos', 'linux')",
            name=op.f("ck_lecciones_videos_sistema"),
        ),
        sa.ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            name=op.f("fk_lecciones_videos_leccion_id_lecciones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name=op.f("fk_lecciones_videos_video_id_videos"),
        ),
        sa.PrimaryKeyConstraint(
            "leccion_id", "sistema", name=op.f("pk_lecciones_videos")
        ),
    )
    op.create_index(
        op.f("ix_lecciones_videos_video_id"),
        "lecciones_videos",
        ["video_id"],
        unique=False,
    )
    op.create_table(
        "progreso_lecciones",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("leccion_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "video_posicion_seg",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "video_max_seg", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "video_completo",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "quiz_aprobado",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("completada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "video_max_seg >= 0", name=op.f("ck_progreso_lecciones_video_max_seg")
        ),
        sa.CheckConstraint(
            "video_posicion_seg >= 0",
            name=op.f("ck_progreso_lecciones_video_posicion_seg"),
        ),
        sa.ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            name=op.f("fk_progreso_lecciones_leccion_id_lecciones"),
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_progreso_lecciones_usuario_id_usuarios"),
        ),
        sa.PrimaryKeyConstraint(
            "usuario_id", "leccion_id", name=op.f("pk_progreso_lecciones")
        ),
    )
    op.create_index(
        op.f("ix_progreso_lecciones_leccion_id"),
        "progreso_lecciones",
        ["leccion_id"],
        unique=False,
    )
    op.create_table(
        "quizzes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("leccion_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "umbral",
            sa.Numeric(precision=3, scale=2),
            server_default=sa.text("0.80"),
            nullable=False,
        ),
        sa.Column(
            "es_final", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint(
            "umbral > 0 AND umbral <= 1", name=op.f("ck_quizzes_umbral")
        ),
        sa.ForeignKeyConstraint(
            ["leccion_id"],
            ["lecciones.id"],
            name=op.f("fk_quizzes_leccion_id_lecciones"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quizzes")),
        sa.UniqueConstraint("leccion_id", name=op.f("uq_quizzes_leccion_id")),
    )
    op.create_table(
        "intentos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), nullable=False),
        sa.Column("puntaje", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("aprobado", sa.Boolean(), nullable=False),
        sa.Column(
            "respuestas", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "puntaje BETWEEN 0 AND 100", name=op.f("ck_intentos_puntaje")
        ),
        sa.ForeignKeyConstraint(
            ["quiz_id"], ["quizzes.id"], name=op.f("fk_intentos_quiz_id_quizzes")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuarios.id"],
            name=op.f("fk_intentos_usuario_id_usuarios"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intentos")),
    )
    op.create_index(
        "ix_intentos_usuario_id_quiz_id",
        "intentos",
        ["usuario_id", "quiz_id"],
        unique=False,
    )
    op.create_table(
        "preguntas",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("quiz_id", sa.BigInteger(), nullable=False),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("enunciado_es", sa.Text(), nullable=False),
        sa.Column("enunciado_en", sa.Text(), nullable=True),
        sa.Column("explicacion_es", sa.Text(), nullable=False),
        sa.Column("explicacion_en", sa.Text(), nullable=True),
        sa.Column(
            "multiple", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint(
            "clave ~ '^m[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*$'",
            name=op.f("ck_preguntas_clave"),
        ),
        sa.CheckConstraint("orden >= 1", name=op.f("ck_preguntas_orden")),
        sa.ForeignKeyConstraint(
            ["quiz_id"],
            ["quizzes.id"],
            name=op.f("fk_preguntas_quiz_id_quizzes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_preguntas")),
        sa.UniqueConstraint("clave", name=op.f("uq_preguntas_clave")),
        sa.UniqueConstraint(
            "quiz_id",
            "orden",
            deferrable=True,
            initially="DEFERRED",
            name="uq_preguntas_quiz_id_orden",
        ),
    )
    op.create_table(
        "opciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("pregunta_id", sa.BigInteger(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("texto_es", sa.Text(), nullable=False),
        sa.Column("texto_en", sa.Text(), nullable=True),
        sa.Column(
            "correcta", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint("orden >= 1", name=op.f("ck_opciones_orden")),
        sa.ForeignKeyConstraint(
            ["pregunta_id"],
            ["preguntas.id"],
            name=op.f("fk_opciones_pregunta_id_preguntas"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opciones")),
        sa.UniqueConstraint(
            "pregunta_id",
            "orden",
            deferrable=True,
            initially="DEFERRED",
            name="uq_opciones_pregunta_id_orden",
        ),
    )


def downgrade() -> None:
    op.drop_table("opciones")
    op.drop_table("preguntas")
    op.drop_index("ix_intentos_usuario_id_quiz_id", table_name="intentos")
    op.drop_table("intentos")
    op.drop_table("quizzes")
    op.drop_index(
        op.f("ix_progreso_lecciones_leccion_id"), table_name="progreso_lecciones"
    )
    op.drop_table("progreso_lecciones")
    op.drop_index(op.f("ix_lecciones_videos_video_id"), table_name="lecciones_videos")
    op.drop_table("lecciones_videos")
    op.drop_table("lecciones")
    op.drop_table("videos")
    op.drop_index(op.f("ix_sesiones_usuario_id"), table_name="sesiones")
    op.drop_table("sesiones")
    op.drop_table("practicas")
    op.drop_table("modulos")
    op.drop_index(op.f("ix_graduaciones_estado"), table_name="graduaciones")
    op.drop_table("graduaciones")
    op.drop_index(op.f("ix_auditoria_creado_en"), table_name="auditoria")
    op.drop_index(op.f("ix_auditoria_actor_id"), table_name="auditoria")
    op.drop_table("auditoria")
    op.drop_index("ix_usuarios_cluster_activo", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_index(
        op.f("ix_sincronizaciones_recibida_en"), table_name="sincronizaciones"
    )
    op.drop_table("sincronizaciones")
    op.drop_table("cursos")
