"""Rutas de contenido (B-04): listarCursos, obtenerCurso, obtenerModulo y
obtenerLeccion del contrato.

Van por slug, igual que las rutas de la web (/cursos/induccion/m05/trabajos);
las respuestas traen también el `id` numérico, que usan las rutas de escritura
(progreso, quiz). Sin `?lang=`, el idioma del perfil.
"""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.schemas.contenido import (
    CursoDetalle,
    CursoResumen,
    Idioma,
    Leccion,
    ModuloDetalle,
)
from app.services import contenido

router = APIRouter(prefix="/cursos", tags=["contenido"])

TODOS = con_roles(*ROLES)
LangDep = Annotated[
    Idioma | None,
    Query(
        description="Idioma del contenido; sin él, el del perfil. Si falta la traducción, en español con fallback = true."
    ),
]


@router.get(
    "",
    operation_id="listarCursos",
    summary="Catálogo de cursos publicados con el avance del usuario",
    **TODOS,
)
async def listar_cursos(
    usuario: UsuarioDep, bd: SesionDep, lang: LangDep = None
) -> list[CursoResumen]:
    return await contenido.listar_cursos(bd, usuario, lang or usuario.idioma)


@router.get(
    "/{curso}",
    operation_id="obtenerCurso",
    summary="Curso con sus módulos, el estado de cada uno y la lección para continuar",
    **TODOS,
)
async def obtener_curso(
    curso: str, usuario: UsuarioDep, bd: SesionDep, lang: LangDep = None
) -> CursoDetalle:
    return await contenido.obtener_curso(bd, curso, usuario, lang or usuario.idioma)


@router.get(
    "/{curso}/modulos/{modulo}",
    operation_id="obtenerModulo",
    summary="Módulo con sus lecciones",
    **TODOS,
)
async def obtener_modulo(
    curso: str, modulo: str, usuario: UsuarioDep, bd: SesionDep, lang: LangDep = None
) -> ModuloDetalle:
    return await contenido.obtener_modulo(
        bd, curso, modulo, usuario, lang or usuario.idioma
    )


@router.get(
    "/{curso}/lecciones/{modulo}/{leccion}",
    operation_id="obtenerLeccion",
    summary="Lección completa con su progreso",
    **TODOS,
)
async def obtener_leccion(
    curso: str,
    modulo: str,
    leccion: str,
    usuario: UsuarioDep,
    bd: SesionDep,
    lang: LangDep = None,
) -> Leccion:
    return await contenido.obtener_leccion(
        bd, curso, modulo, leccion, usuario, lang or usuario.idioma
    )
