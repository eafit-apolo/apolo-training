"""Esquemas de los quizzes de api/openapi.yaml (B-06): Quiz, IntentoEntrada e
IntentoResultado.

La opción correcta no aparece en ninguno: ni al pedir el quiz ni al calificar.
"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.contenido import IdBigint, ProgresoLeccion


class OpcionQuiz(BaseModel):
    model_config = ConfigDict(title="OpcionQuiz")

    id: int
    orden: int
    texto: str


class PreguntaQuiz(BaseModel):
    model_config = ConfigDict(title="Pregunta")

    id: int
    orden: int
    # Markdown corto.
    enunciado: str
    # true si se pueden marcar varias opciones.
    multiple: bool
    opciones: list[OpcionQuiz]


class Quiz(BaseModel):
    model_config = ConfigDict(title="Quiz")

    id: int
    leccion_id: int
    # Parte de las preguntas que hay que acertar para aprobar (0.8 = 80 %).
    umbral: float
    es_final: bool
    fallback: bool
    # El mejor puntaje (0 a 100) del usuario; null si no lo ha intentado.
    mejor_puntaje: float | None
    preguntas: list[PreguntaQuiz]


class RespuestaPregunta(BaseModel):
    model_config = ConfigDict(title="RespuestaPregunta")

    pregunta_id: IdBigint
    # Las opciones marcadas: exactamente una si la pregunta no es múltiple.
    opciones: Annotated[list[IdBigint], Field(min_length=1, max_length=20)]


class IntentoEntrada(BaseModel):
    model_config = ConfigDict(title="IntentoEntrada")

    # Una por pregunta del quiz, todas.
    respuestas: Annotated[list[RespuestaPregunta], Field(min_length=1, max_length=50)]


class ResultadoPregunta(BaseModel):
    model_config = ConfigDict(title="ResultadoPregunta")

    pregunta_id: int
    correcta: bool
    explicacion: str


class IntentoResultado(BaseModel):
    model_config = ConfigDict(title="IntentoResultado")

    id: int
    # Porcentaje de preguntas acertadas, de 0 a 100.
    puntaje: float
    aprobado: bool
    # Como en Quiz: 0.8 = 80 %.
    umbral: float
    mejor_puntaje: float
    preguntas: list[ResultadoPregunta]
    progreso: ProgresoLeccion
