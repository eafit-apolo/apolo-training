from typing import Literal

from pydantic import BaseModel


class Salud(BaseModel):
    """Esquema `Salud` de api/openapi.yaml."""

    estado: Literal["ok", "degradado"]
    base_datos: Literal["ok", "sin_conexion"]
    version: str | None = None
