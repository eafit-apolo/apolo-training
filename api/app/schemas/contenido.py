"""Esquemas de contenido de api/openapi.yaml (B-04): cursos, módulos y lecciones.

Los textos llegan en el idioma pedido (`?lang=`); si falta la traducción, en
español y con `fallback = true`.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.valores import PRACTICAS

Idioma = Literal["es", "en"]
# El módulo n+1 se abre al completar el n: a lo sumo uno está «en_curso».
EstadoModulo = Literal["completo", "en_curso", "bloqueado"]
Componente = Literal["video", "lectura", "practica", "quiz"]
# Las siete del verificador (las mismas de valores.PRACTICAS).
Practica = Literal[PRACTICAS]
SistemaVideo = Literal["todos", "windows", "macos", "linux"]


class ModuloRef(BaseModel):
    id: int
    slug: str
    numero: int
    titulo: str


class LeccionRef(BaseModel):
    id: int
    slug: str
    # El slug del módulo (m05): con él y slug se arma la ruta de la web.
    modulo: str
    modulo_numero: int
    titulo: str


class LeccionResumen(BaseModel):
    id: int
    slug: str
    orden: int
    titulo: str
    duracion_min: int
    completada: bool
    componentes: list[Componente]


class ModuloResumen(BaseModel):
    id: int
    slug: str
    numero: int
    titulo: str
    resumen: str
    duracion_min: int
    estado: EstadoModulo
    bloqueado_por: ModuloRef | None
    lecciones_total: int
    lecciones_completas: int
    # Para la tarjeta del módulo: lecciones con video, prácticas y preguntas.
    videos: int
    practicas: int
    preguntas: int
    componentes: list[Componente]


class ModuloConLecciones(ModuloResumen):
    lecciones: list[LeccionResumen]


class ModuloDetalle(ModuloConLecciones):
    curso_id: int
    curso: str
    fallback: bool


class CursoResumen(BaseModel):
    id: int
    slug: str
    titulo: str
    descripcion: str | None
    duracion_min: int
    videos: int
    avance_pct: int
    modulos_total: int
    modulos_completos: int
    lecciones_total: int
    lecciones_completas: int
    # La siguiente lección por hacer (la primera si no ha empezado); null si terminó.
    continuar: LeccionRef | None
    fallback: bool


class CursoDetalle(CursoResumen):
    # Con las lecciones de cada módulo: la web arma todo el curso (catálogo,
    # grilla, barra lateral) con una sola petición.
    modulos: list[ModuloConLecciones]


class Subtitulo(BaseModel):
    idioma: Idioma
    url: str


class VideoRef(BaseModel):
    id: int
    clave: str
    # false mientras no se haya subido el MP4 («Video pendiente», B-05).
    disponible: bool
    duracion_seg: int | None
    url: str | None
    subtitulos: list[Subtitulo]


class VideoLeccion(BaseModel):
    # «todos», o el sistema operativo en la lección de VPN.
    sistema: SistemaVideo
    video: VideoRef


class ProgresoLeccion(BaseModel):
    leccion_id: int
    video_posicion_seg: int
    video_max_seg: int
    video_completo: bool
    quiz_aprobado: bool
    completada: bool
    completada_en: datetime | None


class LeccionProgreso(BaseModel):
    id: int
    slug: str
    titulo: str
    completada: bool
    video_completo: bool
    tiene_quiz: bool
    quiz_aprobado: bool
    # El mejor puntaje (0 a 100) de sus intentos; null sin quiz o sin intentos.
    quiz_mejor_puntaje: float | None


class ModuloProgreso(BaseModel):
    id: int
    slug: str
    numero: int
    titulo: str
    estado: EstadoModulo
    lecciones_total: int
    lecciones_completas: int
    lecciones: list[LeccionProgreso]


class MiProgreso(BaseModel):
    """Mi progreso (B-06): el curso de inducción por módulo y por lección.

    Laboratorios, sincronización, graduación y siguiente paso llegan con la
    B-07.
    """

    model_config = ConfigDict(title="MiProgreso")

    # El slug del curso; null si todavía no hay un curso publicado.
    curso: str | None
    avance_pct: int
    lecciones_total: int
    lecciones_completas: int
    modulos: list[ModuloProgreso]
    fallback: bool


# Los ids son bigint y los segundos, integer de PostgreSQL: un número fuera de
# rango es un 422, no un error de la base.
IdBigint = Annotated[int, Field(ge=1, le=2**63 - 1)]


class ProgresoVideoEntrada(BaseModel):
    """El reporte del reproductor cada 15 s (F-05)."""

    model_config = ConfigDict(title="ProgresoVideoEntrada")

    leccion_id: IdBigint
    # El video que se está viendo: en la lección de VPN hay uno por sistema, y
    # el 90 % se mide con su duración.
    video_id: IdBigint
    segundo: Annotated[int, Field(ge=0, le=2**31 - 1)]


class Leccion(BaseModel):
    model_config = ConfigDict(title="Leccion")

    id: int
    slug: str
    curso: str
    modulo: ModuloRef
    orden: int
    titulo: str
    # Markdown; la web lo sanitiza antes de mostrarlo (F-04).
    contenido: str
    # El título y el texto de la lección vinieron en español (F-04): los del
    # módulo y de las lecciones vecinas no cuentan.
    fallback: bool
    duracion_min: int
    componentes: list[Componente]
    videos: list[VideoLeccion]
    practicas: list[Practica]
    quiz_id: int | None
    anterior: LeccionRef | None
    siguiente: LeccionRef | None
    progreso: ProgresoLeccion
