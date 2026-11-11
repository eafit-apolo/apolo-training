"""Rutas de los quizzes (B-06): obtenerQuiz y enviarIntento del contrato.

El id del quiz viene en la lección (`quiz_id`). Sin `?lang=`, el idioma del
perfil.
"""

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.routers.contenido import LangDep
from app.schemas.quizzes import IntentoEntrada, IntentoResultado, Quiz
from app.services import quizzes

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

# Los ids son bigint: uno fuera de rango es un 422, no un error de PostgreSQL.
QuizId = Annotated[int, Path(ge=1, le=2**63 - 1)]


@router.get(
    "/{quiz_id}",
    operation_id="obtenerQuiz",
    summary="Preguntas del quiz, sin las respuestas correctas",
    **con_roles(*ROLES),
)
async def obtener_quiz(
    quiz_id: QuizId, usuario: UsuarioDep, bd: SesionDep, lang: LangDep = None
) -> Quiz:
    return await quizzes.obtener_quiz(bd, quiz_id, usuario, lang or usuario.idioma)


@router.post(
    "/{quiz_id}/intentos",
    operation_id="enviarIntento",
    summary="Enviar respuestas y calificar en el servidor",
    status_code=status.HTTP_201_CREATED,
    **con_roles(*ROLES),
)
async def enviar_intento(
    quiz_id: QuizId,
    entrada: IntentoEntrada,
    usuario: UsuarioDep,
    bd: SesionDep,
    lang: LangDep = None,
) -> IntentoResultado:
    return await quizzes.enviar_intento(
        bd, quiz_id, entrada, usuario, lang or usuario.idioma
    )
