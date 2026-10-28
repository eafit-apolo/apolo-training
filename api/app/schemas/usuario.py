"""Esquemas `Usuario` y `PerfilCambio` de api/openapi.yaml."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class UsuarioSalida(BaseModel):
    """Esquema `Usuario`: el perfil, sin nada de la clave ni de la sesión."""

    model_config = ConfigDict(from_attributes=True, title="Usuario")

    username: str
    nombre: str
    correo: str | None = None
    cluster: Literal["apolo2", "apolo3"]
    rol: Literal["estudiante", "instructor", "admin"]
    idioma: Literal["es", "en"]
    debe_cambiar_clave: bool
    activo: bool


class PerfilCambio(BaseModel):
    idioma: Literal["es", "en"]
