"""Esquemas de videos de api/openapi.yaml (B-05): `VideoAdmin` del panel."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.contenido import LeccionRef


class SubtitulosVideo(BaseModel):
    es: bool
    en: bool


class VideoAdmin(BaseModel):
    """Un video con su archivo y sus subtítulos, como lo ve el panel."""

    model_config = ConfigDict(title="VideoAdmin")

    id: int
    clave: str
    # false mientras no se haya subido el MP4.
    disponible: bool
    duracion_seg: int | None
    tamano_bytes: int | None
    subtitulos: SubtitulosVideo
    # Lecciones publicadas que lo muestran (en la de VPN, cada sistema tiene el suyo).
    lecciones: list[LeccionRef]
    subido_por: str | None
    subido_en: datetime | None
