"""Mensajes del WebSocket (docs/diseno/flujos.md, «3. Terminal real»).

Del navegador llegan marcos de texto con JSON: `entrada` (lo que el usuario
teclea) y `tamano` (filas y columnas de xterm). Hacia el navegador van marcos
binarios con la salida de la terminal, tal cual, y marcos de texto con el
`estado`.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

# Motivos de cierre que la app traduce.
Motivo = Literal[
    "inactividad",
    "tiempo_maximo",
    "otra_sesion",
    "ssh_rechazado",
    "sesion_invalida",
    "error",
]


class Entrada(BaseModel):
    tipo: Literal["entrada"]
    # Lo que se teclea o se pega; el límite evita mensajes gigantes.
    datos: str = Field(max_length=64 * 1024)


class Tamano(BaseModel):
    tipo: Literal["tamano"]
    columnas: int = Field(ge=1, le=1000)
    filas: int = Field(ge=1, le=1000)


# El campo `tipo` decide con qué modelo se valida el resto.
_mensaje = TypeAdapter(Annotated[Entrada | Tamano, Field(discriminator="tipo")])


def leer(texto: str) -> Entrada | Tamano | None:
    """El mensaje del navegador, o None si no es uno de los dos tipos válidos.

    Cualquier otro mensaje (por ejemplo, uno que intente elegir host) se ignora.
    """
    try:
        return _mensaje.validate_json(texto)
    except ValidationError:
        return None


def estado(
    valor: Literal["conectado", "cerrado"], motivo: Motivo | None = None
) -> dict[str, Any]:
    mensaje: dict[str, Any] = {"tipo": "estado", "estado": valor}
    if motivo is not None:
        mensaje["motivo"] = motivo
    return mensaje
