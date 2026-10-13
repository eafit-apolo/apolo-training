"""Modelos SQLAlchemy (B-02 en adelante).

Cada modelo nuevo se importa aquí: Alembic carga este paquete para conocer
todas las tablas al generar migraciones.
"""

from app.models.base import Base

__all__ = ["Base"]
