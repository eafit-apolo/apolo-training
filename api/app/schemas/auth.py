"""Esquemas `LoginEntrada`, `LoginSalida` y `CambioClave` de api/openapi.yaml.

Las claves son SecretStr: no salen en repr() ni en un log por accidente.
"""

from pydantic import BaseModel, Field, SecretStr

from app.core.seguridad import CLAVE_MAXIMA
from app.models.valores import PATRON_USERNAME
from app.schemas.usuario import UsuarioSalida


class LoginEntrada(BaseModel):
    username: str = Field(pattern=PATRON_USERNAME)
    clave: SecretStr = Field(min_length=1, max_length=CLAVE_MAXIMA)


class LoginSalida(BaseModel):
    usuario: UsuarioSalida


class CambioClave(BaseModel):
    clave_actual: SecretStr = Field(min_length=1, max_length=CLAVE_MAXIMA)
    # El mínimo lo revisa el servicio para responder 400 clave_debil (no 422).
    clave_nueva: SecretStr = Field(max_length=CLAVE_MAXIMA)
