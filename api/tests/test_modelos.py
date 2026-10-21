"""Modelo de datos (B-02): tablas, índices y restricciones en PostgreSQL.

Corren después de `alembic upgrade head`, así que prueban la base que deja la
migración, no solo los modelos.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Base,
    Curso,
    Graduacion,
    Leccion,
    LeccionVideo,
    Modulo,
    Practica,
    Usuario,
    Video,
)

TABLAS = {
    "auditoria",
    "cursos",
    "graduaciones",
    "intentos",
    "lecciones",
    "lecciones_videos",
    "modulos",
    "opciones",
    "practicas",
    "preguntas",
    "progreso_lecciones",
    "quizzes",
    "sesiones",
    "sincronizaciones",
    "usuarios",
    "videos",
}


def nuevo_usuario(**cambios) -> Usuario:
    datos = {
        "username": "prueba",
        "nombre": "Prueba",
        "cluster": "apolo2",
        "clave_hash": "no-es-un-hash",
    }
    return Usuario(**(datos | cambios))


async def nueva_leccion(sesion: AsyncSession, **cambios) -> Leccion:
    curso = Curso(slug="prueba", titulo_es="Curso de prueba")
    sesion.add(curso)
    await sesion.flush()
    modulo = Modulo(
        curso_id=curso.id,
        slug="m05",
        numero=5,
        titulo_es="Trabajos",
        resumen_es="Resumen",
        duracion_min=13,
    )
    sesion.add(modulo)
    await sesion.flush()
    datos = {
        "modulo_id": modulo.id,
        "slug": "trabajos",
        "orden": 1,
        "titulo_es": "Trabajos con Slurm",
        "contenido_es": "## Objetivos",
        "duracion_min": 13,
    }
    leccion = Leccion(**(datos | cambios))
    sesion.add(leccion)
    await sesion.flush()
    return leccion


async def falla(sesion: AsyncSession, restriccion: str) -> None:
    """El flush pendiente debe chocar con esa restricción."""
    with pytest.raises(IntegrityError, match=restriccion):
        await sesion.flush()
    await sesion.rollback()


# --- Tablas e índices -------------------------------------------------------


async def test_la_migracion_crea_todas_las_tablas(sesion_bd: AsyncSession) -> None:
    tablas = await sesion_bd.run_sync(
        lambda s: set(inspect(s.connection()).get_table_names())
    )

    assert tablas - {"alembic_version"} == TABLAS
    assert set(Base.metadata.tables) == TABLAS


async def test_indices_de_las_tablas_de_progreso(sesion_bd: AsyncSession) -> None:
    def leer(s):
        insp = inspect(s.connection())
        return {
            tabla: (
                insp.get_pk_constraint(tabla)["constrained_columns"],
                [i["column_names"] for i in insp.get_indexes(tabla)],
            )
            for tabla in ("progreso_lecciones", "practicas", "intentos")
        }

    datos = await sesion_bd.run_sync(leer)

    # La PK empieza por usuario_id, así que también sirve de índice para él.
    assert datos["progreso_lecciones"][0] == ["usuario_id", "leccion_id"]
    assert ["leccion_id"] in datos["progreso_lecciones"][1]
    assert datos["practicas"][0] == ["usuario_id", "practica"]
    assert ["usuario_id", "quiz_id"] in datos["intentos"][1]


# --- usuarios ---------------------------------------------------------------


async def test_usuario_con_valores_por_defecto(sesion_bd: AsyncSession) -> None:
    usuario = nuevo_usuario()
    sesion_bd.add(usuario)
    await sesion_bd.flush()
    await sesion_bd.refresh(usuario)

    assert usuario.id is not None
    assert (usuario.rol, usuario.idioma) == ("estudiante", "es")
    assert usuario.debe_cambiar_clave is True
    assert usuario.activo is True
    assert usuario.intentos_fallidos == 0
    assert usuario.creado_en is not None


@pytest.mark.parametrize(
    ("cambio", "restriccion"),
    [
        ({"cluster": "apolo4"}, "ck_usuarios_cluster"),
        ({"rol": "root"}, "ck_usuarios_rol"),
        ({"idioma": "fr"}, "ck_usuarios_idioma"),
        ({"username": "Ana Pérez"}, "ck_usuarios_username"),
        ({"activo": False}, "ck_usuarios_baja"),
        ({"baja_en": datetime(2026, 10, 1, tzinfo=UTC)}, "ck_usuarios_baja"),
    ],
)
async def test_usuario_rechaza_valores_invalidos(
    sesion_bd: AsyncSession, cambio: dict, restriccion: str
) -> None:
    sesion_bd.add(nuevo_usuario(**cambio))
    await falla(sesion_bd, restriccion)


async def test_username_unico(sesion_bd: AsyncSession) -> None:
    sesion_bd.add(nuevo_usuario())
    await sesion_bd.flush()
    sesion_bd.add(nuevo_usuario(cluster="apolo3"))
    await falla(sesion_bd, "uq_usuarios_username")


# --- Contenido --------------------------------------------------------------


async def test_leccion_con_varias_practicas(sesion_bd: AsyncSession) -> None:
    leccion = await nueva_leccion(sesion_bd, practicas=["nucleos", "paralelo"])
    await sesion_bd.refresh(leccion)

    assert leccion.practicas == ["nucleos", "paralelo"]


async def test_leccion_sin_practicas_queda_con_lista_vacia(
    sesion_bd: AsyncSession,
) -> None:
    leccion = await nueva_leccion(sesion_bd)
    await sesion_bd.refresh(leccion)

    assert leccion.practicas == []


async def test_leccion_rechaza_una_practica_que_no_existe(
    sesion_bd: AsyncSession,
) -> None:
    with pytest.raises(IntegrityError, match="ck_lecciones_practicas"):
        await nueva_leccion(sesion_bd, practicas=["memoria", "ondemand"])


async def test_orden_de_lecciones_se_puede_intercambiar(
    sesion_bd: AsyncSession,
) -> None:
    primera = await nueva_leccion(sesion_bd)
    segunda = Leccion(
        modulo_id=primera.modulo_id,
        slug="estados",
        orden=2,
        titulo_es="Estados",
        contenido_es="## Objetivos",
        duracion_min=3,
    )
    sesion_bd.add(segunda)
    await sesion_bd.flush()

    # El único de (modulo_id, orden) es diferible: el cruce se revisa al final.
    primera.orden, segunda.orden = 2, 1
    await sesion_bd.flush()
    await sesion_bd.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


async def test_orden_de_lecciones_repetido_falla_al_confirmar(
    sesion_bd: AsyncSession,
) -> None:
    primera = await nueva_leccion(sesion_bd)
    sesion_bd.add(
        Leccion(
            modulo_id=primera.modulo_id,
            slug="estados",
            orden=1,
            titulo_es="Estados",
            contenido_es="## Objetivos",
            duracion_min=3,
        )
    )
    await sesion_bd.flush()

    with pytest.raises(IntegrityError, match="uq_lecciones_modulo_id_orden"):
        await sesion_bd.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


async def test_leccion_de_vpn_con_un_video_por_sistema(sesion_bd: AsyncSession) -> None:
    leccion = await nueva_leccion(sesion_bd, slug="vpn")
    for sistema in ("windows", "macos", "linux"):
        video = Video(clave=f"m01-vpn-{sistema}")
        sesion_bd.add(video)
        await sesion_bd.flush()
        sesion_bd.add(
            LeccionVideo(leccion_id=leccion.id, sistema=sistema, video_id=video.id)
        )
    await sesion_bd.flush()

    sesion_bd.add(
        LeccionVideo(leccion_id=leccion.id, sistema="windows", video_id=video.id)
    )
    await falla(sesion_bd, "pk_lecciones_videos")


async def test_leccion_video_rechaza_un_sistema_desconocido(
    sesion_bd: AsyncSession,
) -> None:
    leccion = await nueva_leccion(sesion_bd)
    video = Video(clave="m05-trabajos")
    sesion_bd.add(video)
    await sesion_bd.flush()

    sesion_bd.add(
        LeccionVideo(leccion_id=leccion.id, sistema="android", video_id=video.id)
    )
    await falla(sesion_bd, "ck_lecciones_videos_sistema")


async def test_video_rechaza_una_clave_mal_formada(sesion_bd: AsyncSession) -> None:
    sesion_bd.add(Video(clave="trabajos.mp4"))
    await falla(sesion_bd, "ck_videos_clave")


# --- Progreso ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("cambio", "restriccion"),
    [
        ({"practica": "ondemand"}, "ck_practicas_practica"),
        ({"estado": "pendiente"}, "ck_practicas_estado"),
    ],
)
async def test_practica_rechaza_valores_invalidos(
    sesion_bd: AsyncSession, cambio: dict, restriccion: str
) -> None:
    usuario = nuevo_usuario()
    sesion_bd.add(usuario)
    await sesion_bd.flush()
    datos = {
        "usuario_id": usuario.id,
        "practica": "memoria",
        "estado": "aprobado",
        "jobid": "1042",
        "fecha": datetime(2026, 10, 21, tzinfo=UTC),
    }
    sesion_bd.add(Practica(**(datos | cambio)))
    await falla(sesion_bd, restriccion)


async def test_practica_sin_trabajo_de_slurm(sesion_bd: AsyncSession) -> None:
    usuario = nuevo_usuario()
    sesion_bd.add(usuario)
    await sesion_bd.flush()

    sesion_bd.add(
        Practica(
            usuario_id=usuario.id,
            practica="conexion",
            estado="aprobado",
            fecha=datetime(2026, 10, 21, tzinfo=UTC),
        )
    )
    await sesion_bd.flush()


@pytest.mark.parametrize(
    ("cambio", "restriccion"),
    [
        ({"jobid": "abc"}, "ck_graduaciones_jobid"),
        ({"estado": "pendiente"}, "ck_graduaciones_estado"),
        ({"cluster": "cronos"}, "ck_graduaciones_cluster"),
    ],
)
async def test_graduacion_rechaza_valores_invalidos(
    sesion_bd: AsyncSession, cambio: dict, restriccion: str
) -> None:
    usuario = nuevo_usuario()
    sesion_bd.add(usuario)
    await sesion_bd.flush()
    datos = {
        "usuario_id": usuario.id,
        "cluster": "apolo3",
        "jobid": "98765",
        "salida_verificador": "[APROBADO] …",
    }
    sesion_bd.add(Graduacion(**(datos | cambio)))
    await falla(sesion_bd, restriccion)
