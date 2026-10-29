"""Esquemas de contenido de api/openapi.yaml (B-04): cursos, módulos y lecciones.

Los textos llegan en el idioma pedido (`?lang=`); si falta la traducción, en
español y con `fallback = true`.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


class ModuloDetalle(ModuloResumen):
    curso_id: int
    curso: str
    fallback: bool
    lecciones: list[LeccionResumen]


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
    modulos: list[ModuloResumen]


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
    fallback: bool
    duracion_min: int
    componentes: list[Componente]
    videos: list[VideoLeccion]
    practicas: list[Practica]
    quiz_id: int | None
    anterior: LeccionRef | None
    siguiente: LeccionRef | None
    progreso: ProgresoLeccion
