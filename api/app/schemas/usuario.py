"""Esquemas `Usuario`, `PerfilCambio`, `AltaUsuario` y `EstadoUsuario` de
api/openapi.yaml."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.core.seguridad import CLAVE_MAXIMA, CLAVE_MINIMA
from app.models.valores import PATRON_USERNAME
from app.schemas.labs import Cluster, SinNulos

# Como valida el correo apolo-training-admin en la 116 (V-04): sin
# email-validator, que sería una dependencia más para una sola regla.
PATRON_CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

Rol = Literal["estudiante", "instructor", "admin"]
Idioma = Literal["es", "en"]


class UsuarioSalida(BaseModel):
    """Esquema `Usuario`: el perfil, sin nada de la clave ni de la sesión."""

    model_config = ConfigDict(from_attributes=True, title="Usuario")

    username: str
    nombre: str
    correo: str | None = None
    cluster: Cluster
    rol: Rol
    idioma: Idioma
    debe_cambiar_clave: bool
    activo: bool


class PerfilCambio(BaseModel):
    idioma: Idioma


class AltaUsuario(BaseModel):
    """Lo que manda `apolo-training-admin alta` desde la 116 (V-04).

    Sin `rol`: la 116 solo crea estudiantes; el rol lo cambia un admin en la
    plataforma (o `python -m app.rol` para el primero). Un campo de más es un
    422, así la 116 revierte la alta en vez de crear algo distinto de lo que
    pidió.
    """

    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(pattern=PATRON_USERNAME)]
    nombre: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
        SinNulos,
    ]
    correo: Annotated[str, Field(pattern=PATRON_CORREO, max_length=254)]
    cluster: Cluster
    idioma: Idioma = "es"
    # La misma de la VM; la API solo guarda su hash.
    clave_temporal: Annotated[
        SecretStr, Field(min_length=CLAVE_MINIMA, max_length=CLAVE_MAXIMA)
    ]


class EstadoUsuario(BaseModel):
    """`false` = baja (`apolo-training-admin baja`); `true` = reactivar."""

    activo: bool
