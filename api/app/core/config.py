"""Configuración de la API: variables de entorno (prefijo API_) y, en la 117,
los secretos de Compose (W-05)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secretos de Compose en la 117 (W-05): un archivo por variable, con su nombre
# en minúsculas (/run/secrets/api_database_url, /run/secrets/api_secreto).
CARPETA_SECRETOS = Path("/run/secrets")


def carpeta_secretos(ruta: Path) -> Path | None:
    """La carpeta de secretos solo si existe.

    En desarrollo y en la CI no existe, y pydantic-settings avisaría en cada
    Settings(); con filterwarnings = error (pytest.ini) se caerían las pruebas.
    """
    return ruta if ruta.is_dir() else None


class Settings(BaseSettings):
    # Una variable de entorno gana sobre el archivo del mismo nombre, así que en
    # desarrollo (compose.dev.yaml) no cambia nada.
    model_config = SettingsConfigDict(
        env_prefix="API_",
        extra="ignore",
        secrets_dir=carpeta_secretos(CARPETA_SECRETOS),
    )

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
    # Videos y subtítulos subidos desde el panel (B-05). En la 117, un volumen
    # que la API escribe y nginx lee (W-06).
    media_dir: Path = Path("/srv/apolo-training/media")
    # Cómo se entregan: `nginx` (la 117) responde con X-Accel-Redirect y nginx
    # manda el archivo; `api` lo manda la API misma, con Range (desarrollo, donde
    # no hay nginx delante).
    media_entrega: Literal["nginx", "api"] = "nginx"

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
