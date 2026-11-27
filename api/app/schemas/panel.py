"""Esquema del resumen del panel de instructor (F-08): `ResumenPanel` de
api/openapi.yaml, con `AvanceModulo` para «dónde se atascan»."""

from datetime import datetime

from pydantic import BaseModel


class AvanceModulo(BaseModel):
    numero: int
    titulo: str
    # Estudiantes activos que completaron el módulo.
    completos: int


class ResumenPanel(BaseModel):
    estudiantes_activos: int
    sin_empezar: int
    en_curso: int
    aprobados: int
    graduaciones_por_revisar: int
    aprobados_pendientes_qos: int
    # La misma de Mi progreso: el último reporte de la VM, o None si nunca hubo.
    ultima_sincronizacion: datetime | None
    avance_por_modulo: list[AvanceModulo]
