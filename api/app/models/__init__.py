"""Modelos SQLAlchemy (B-02 en adelante).

Cada modelo nuevo se importa aquí: Alembic carga este paquete para conocer
todas las tablas al generar migraciones. El diagrama y las reglas están en
docs/diseno/modelo-datos.md; si cambia un modelo, se cambia también ese archivo.
"""

from app.models.auditoria import Auditoria
from app.models.base import Base
from app.models.contenido import (
    Curso,
    Leccion,
    LeccionVideo,
    Modulo,
    Opcion,
    Pregunta,
    Quiz,
    Video,
)
from app.models.progreso import (
    Graduacion,
    Intento,
    Practica,
    ProgresoLeccion,
    Sincronizacion,
)
from app.models.usuarios import Sesion, Usuario

__all__ = [
    "Auditoria",
    "Base",
    "Curso",
    "Graduacion",
    "Intento",
    "Leccion",
    "LeccionVideo",
    "Modulo",
    "Opcion",
    "Practica",
    "Pregunta",
    "ProgresoLeccion",
    "Quiz",
    "Sesion",
    "Sincronizacion",
    "Usuario",
    "Video",
]
