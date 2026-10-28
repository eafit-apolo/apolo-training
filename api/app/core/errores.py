"""Errores con el formato del contrato (A-11): {"detail": "...", "codigo": "..."}.

La app traduce `codigo` con Transloco; `detail` es solo para quien depura.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Código estable para los errores HTTP que no lanza la API a propósito
# (ruta inexistente, método no permitido...).
CODIGOS_HTTP = {
    400: "peticion_invalida",
    401: "sin_sesion",
    403: "sin_permiso",
    404: "no_encontrado",
    405: "metodo_no_permitido",
    429: "demasiadas_peticiones",
}


class ErrorApi(Exception):
    """Error que la API lanza a propósito, con su código estable.

    `extra` agrega campos al cuerpo, como `bloqueado_hasta` en `cuenta_bloqueada`.
    """

    def __init__(
        self,
        status_code: int,
        codigo: str,
        detail: str,
        headers: dict[str, str] | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.codigo = codigo
        self.detail = detail
        self.headers = headers
        self.extra = extra or {}


def _respuesta(
    status_code: int,
    detail: str,
    codigo: str,
    headers: dict[str, str] | None = None,
    **extra: object,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "codigo": codigo, **extra},
        headers=headers,
    )


async def _error_api(_: Request, exc: ErrorApi) -> JSONResponse:
    return _respuesta(exc.status_code, exc.detail, exc.codigo, exc.headers, **exc.extra)


async def _error_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    codigo = CODIGOS_HTTP.get(exc.status_code, "error_http")
    return _respuesta(exc.status_code, str(exc.detail), codigo, exc.headers)


async def _error_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    errores = [
        {
            # ("body", "username") -> "username"; ("query", "lang") -> "lang"
            "campo": ".".join(str(parte) for parte in error["loc"][1:])
            or str(error["loc"][0]),
            "codigo": error["type"],
        }
        for error in exc.errors()
    ]
    return _respuesta(422, "Datos inválidos", "datos_invalidos", errores=errores)


async def _error_interno(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado", exc_info=exc)
    return _respuesta(500, "Error interno", "error_interno")


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ErrorApi, _error_api)
    app.add_exception_handler(StarletteHTTPException, _error_http)
    app.add_exception_handler(RequestValidationError, _error_validacion)
    app.add_exception_handler(Exception, _error_interno)
