"""Configuración del gateway, leída de variables de entorno (prefijo TERMINAL_)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TERMINAL_", extra="ignore")

    # Único origen desde el que se puede abrir la terminal: la plataforma.
    origen: str = "https://training.apolo.eafit.edu.co"
    # La API por la red interna del compose; solo se usa GET /api/me.
    api_url: str = "http://api:8000"
    # Único destino SSH. Sale de aquí, nunca del navegador.
    ssh_host: str = "apolo-training.apolo.eafit.edu.co"
    ssh_puerto: int = 22
    # Llave pública de la VM de práctica. Sin ella no se conecta: un servidor
    # falso en el camino recibiría las contraseñas de los usuarios.
    known_hosts: str = "/run/terminal/known_hosts"
    # Segundos sin que el usuario escriba, y duración máxima de una sesión.
    inactividad: float = Field(default=15 * 60, gt=0)
    maximo: float = Field(default=2 * 60 * 60, gt=0)
