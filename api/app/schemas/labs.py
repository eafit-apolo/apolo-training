"""Esquemas de las prácticas y la graduación de api/openapi.yaml (B-07).

En la API una práctica se llama `lab` (ruta /internal/labs, campo `lab`,
`LabId`), como en el contrato desde la A-11; en la base, `practicas`. Son las
siete del verificador, también las que no tienen trabajo de Slurm (`conexion`,
`terminal` y `archivos`), por eso `jobid` es opcional.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

from app.models.valores import PATRON_JOBID, PATRON_USERNAME
from app.schemas.contenido import AvanceCurso, LeccionRef, Practica

LabId = Practica
Cluster = Literal["apolo2", "apolo3"]
EstadoGraduacion = Literal["enviada", "aprobada", "rechazada"]


def _sin_nulos(texto: str) -> str:
    # PostgreSQL no guarda el carácter nulo en un text: sería un 500.
    if "\x00" in texto:
        raise ValueError("no puede tener el carácter nulo")
    return texto


Username = Annotated[str, Field(pattern=PATRON_USERNAME)]
JobId = Annotated[str, Field(pattern=PATRON_JOBID)]
# Textos libres: con largo máximo y sin el carácter nulo.
SinNulos = AfterValidator(_sin_nulos)
Detalle = Annotated[str, Field(max_length=200), SinNulos]
Salida = Annotated[str, Field(min_length=1, max_length=4000), SinNulos]
Comentario = Annotated[str, Field(max_length=1000), SinNulos]


# --- Sincronización (POST /api/internal/labs) ---------------------------------


class RegistroLab(BaseModel):
    """El mejor estado de una práctica de un usuario, según la VM (V-05)."""

    usuario: Username
    lab: LabId
    estado: Literal["intentado", "aprobado"]
    # Solo las de Slurm tienen trabajo.
    jobid: JobId | None = None
    # Fin del trabajo, o cuándo se verificó si no hay trabajo. Con zona horaria.
    fecha: AwareDatetime
    detalle: Detalle | None = None


class ReporteLabs(BaseModel):
    """Reporte completo (no incremental) que la VM manda cada 5 minutos."""

    generado_en: AwareDatetime
    registros: Annotated[list[RegistroLab], Field(max_length=5000)]


class Ignorado(BaseModel):
    usuario: str
    lab: str
    motivo: Literal["usuario_desconocido", "usuario_inactivo", "no_retrocede"]


class ResultadoSincronizacion(BaseModel):
    aceptados: int
    ignorados: list[Ignorado]


# --- Mi progreso ----------------------------------------------------------------


class LabEstadoUsuario(BaseModel):
    lab: LabId
    estado: Literal["sin_intentar", "intentado", "aprobado"]
    jobid: str | None
    fecha: datetime | None
    detalle: str | None


class SiguientePaso(BaseModel):
    tipo: Literal[
        "leccion",
        "laboratorio",
        "graduacion",
        "esperar_revision",
        "esperar_qos",
        "terminado",
    ]
    # `leccion` solo con tipo leccion y `lab` solo con tipo laboratorio.
    leccion: LeccionRef | None
    lab: LabId | None


# --- Graduación ---------------------------------------------------------------


class Graduacion(BaseModel):
    cluster: Cluster
    jobid: str
    salida_verificador: str
    estado: EstadoGraduacion
    enviada_en: datetime
    revisada_en: datetime | None
    # El del instructor; al rechazar, el usuario lo ve en Mi progreso.
    comentario: str | None
    qos_aplicada_en: datetime | None


class GraduacionEntrada(BaseModel):
    """El JobID del trabajo de graduación y la salida de
    `apolo-training verificar graduacion JOBID`, pegada tal cual."""

    jobid: JobId
    salida: Salida


class GraduacionAdmin(Graduacion):
    username: str
    nombre: str
    revisada_por: str | None
    labs_aprobados: int


class RevisionGraduacion(BaseModel):
    decision: Literal["aprobar", "rechazar"]
    # Obligatorio al rechazar.
    comentario: Comentario | None = None


class MiProgreso(AvanceCurso):
    """Mi progreso (B-06 y B-07): el avance del curso, las siete prácticas, la
    última sincronización de la VM, la graduación y el siguiente paso."""

    model_config = ConfigDict(title="MiProgreso")

    # Siempre las siete, aunque no se hayan intentado, en el orden del curso.
    labs: list[LabEstadoUsuario]
    # La última vez que la VM mandó su reporte (para todos los usuarios).
    ultima_sincronizacion: datetime | None
    # Más de 15 minutos sin reporte. false si nunca hubo uno.
    sincronizacion_atrasada: bool
    graduacion: Graduacion | None
    # Lecciones completas, las siete prácticas aprobadas y la graduación aprobada.
    aprobado: bool
    siguiente_paso: SiguientePaso
