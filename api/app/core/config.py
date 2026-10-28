"""Configuración de la API, leída solo de variables de entorno (prefijo API_)."""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")

    # postgresql+asyncpg://usuario:clave@host:puerto/base
    # Es SecretStr para que la clave no salga en logs ni en repr().
    database_url: SecretStr
    # Segundos que espera /api/health a PostgreSQL antes de responder 503.
    db_timeout: float = Field(default=3.0, gt=0)
    # Versión que informa /api/health; la imagen la recibe del build (ARG VERSION).
    version: str = "dev"
    # /api/docs y /api/openapi.json solo si se activan (desarrollo).
    docs: bool = False
    # Solo desarrollo: permite que `python -m app.datos_ejemplo` cargue los
    # usuarios de ejemplo. Lo pone el servicio migrar de deploy/compose.dev.yaml.
    datos_ejemplo: bool = False
    # Firma el token de acceso (JWT HS256) y genera el token CSRF de cada sesión
    # (B-03). Obligatoria para la API, no para las migraciones ni los datos de
    # ejemplo: por eso no tiene valor por defecto y la exige create_app().
    # Cambiarla cierra todas las sesiones.
    secreto: SecretStr | None = None
    # Cookies con Secure. Solo se apaga para probar desde otro equipo por http
    # (Safari descarta las cookies Secure fuera de https y de localhost).
    cookies_seguras: bool = True

    @field_validator("secreto")
    @classmethod
    def _secreto_largo(cls, valor: SecretStr | None) -> SecretStr | None:
        if valor is not None and len(valor.get_secret_value()) < 32:
            raise ValueError("debe tener 32 caracteres o más")
        return valor

    @field_validator("database_url")
    @classmethod
    def _driver_async(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("debe empezar por postgresql+asyncpg://")
        return valor


@lru_cache
def obtener_settings() -> Settings:
    return Settings()
