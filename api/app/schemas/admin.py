"""Esquemas de administración de api/openapi.yaml (B-08): `UsuarioAdmin`,
`UsuarioDetalleAdmin`, `ListaUsuarios`, `UsuarioCambio`, `ClaveTemporal` y
`AprobadoPendiente`."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.labs import EstadoGraduacion, MiProgreso
from app.schemas.usuario import Cluster, Rol, UsuarioSalida

# Uno solo por usuario; gana el primero que se cumple, en este orden.
EstadoCuenta = Literal["baja", "bloqueado", "debe_cambiar_clave", "activo"]


class UsuarioAdmin(UsuarioSalida):
    model_config = ConfigDict(title="UsuarioAdmin")

    estado: EstadoCuenta
    bloqueado_hasta: datetime | None
    creado_en: datetime
    ultimo_ingreso: datetime | None
    baja_en: datetime | None
    avance_pct: int
    labs_aprobados: int
    graduacion_estado: EstadoGraduacion | None


class UsuarioDetalleAdmin(UsuarioAdmin):
    model_config = ConfigDict(title="UsuarioDetalleAdmin")

    # Mi progreso de ese usuario, en el idioma de quien lo mira.
    progreso: MiProgreso


class ListaUsuarios(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    items: list[UsuarioAdmin]


class UsuarioCambio(BaseModel):
    rol: Rol


class ClaveTemporal(BaseModel):
    username: str
    # Se muestra una sola vez; la base solo guarda su hash.
    clave_temporal: str


class AprobadoPendiente(BaseModel):
    username: str
    nombre: str
    cluster: Cluster
    # Cuándo se cumplió la última de las tres condiciones.
    aprobado_en: datetime
