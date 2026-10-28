"""Quién hace la petición y qué puede hacer (B-03).

Cada ruta declara sus roles con uno de estos ayudantes, que además ponen
`x-roles` en el OpenAPI generado (debe coincidir con api/openapi.yaml; lo
revisa tests/test_roles.py):

    @router.get("/health", **publica())
    @router.post("/auth/refresh", **con_refresh())          # usa la cookie rt
    @router.get("/me", **con_roles(*ROLES, cambio_pendiente=True))
    @router.get("/panel/resumen", **con_roles("instructor", "admin"))

Dentro de la función, `UsuarioDep` (o `SesionActualDep`) da el usuario: FastAPI
resuelve la dependencia una sola vez por petición, así que no repite la
consulta. Todo lo que no sea GET exige además el token CSRF.
"""

from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, Request
from sqlalchemy import select

from app.core.db import SesionDep
from app.core.errores import ErrorApi
from app.core.seguridad import (
    CABECERA_CSRF,
    COOKIE_ACCESO,
    COOKIE_CSRF,
    METODOS_SEGUROS,
    ahora,
    csrf_valido,
    leer_token_acceso,
)
from app.models import Sesion, Usuario
from app.models.valores import ROLES


@dataclass(frozen=True)
class SesionActual:
    usuario: Usuario
    sesion_id: int


def verificar_csrf(request: Request, sesion_id: int) -> None:
    settings = request.app.state.settings
    if not csrf_valido(
        settings,
        sesion_id,
        request.headers.get(CABECERA_CSRF),
        request.cookies.get(COOKIE_CSRF),
    ):
        raise ErrorApi(403, "csrf_invalido", "Falta el token CSRF o no coincide")


async def obtener_sesion_actual(request: Request, bd: SesionDep) -> SesionActual:
    """Valida la cookie at contra la base: sesión viva y usuario activo.

    Admite `debe_cambiar_clave`; para todo lo demás está `obtener_usuario`.
    """
    token = request.cookies.get(COOKIE_ACCESO)
    if not token:
        raise ErrorApi(401, "sin_sesion", "Falta la cookie de sesión")
    try:
        usuario_id, sesion_id = leer_token_acceso(request.app.state.settings, token)
    except jwt.ExpiredSignatureError as exc:
        raise ErrorApi(401, "token_vencido", "El token de acceso venció") from exc
    except jwt.InvalidTokenError as exc:
        raise ErrorApi(401, "token_invalido", "Token de acceso inválido") from exc

    fila = (
        await bd.execute(
            select(Usuario, Sesion)
            .join(Sesion, Sesion.usuario_id == Usuario.id)
            .where(Sesion.id == sesion_id, Usuario.id == usuario_id)
        )
    ).first()
    if fila is None:
        raise ErrorApi(401, "sin_sesion", "La sesión no existe")
    usuario, sesion = fila
    if sesion.revocada_en is not None or sesion.expira_en <= ahora():
        raise ErrorApi(401, "sin_sesion", "La sesión se cerró o venció")
    if not usuario.activo:
        raise ErrorApi(401, "sin_sesion", "La cuenta está dada de baja")

    if request.method not in METODOS_SEGUROS:
        verificar_csrf(request, sesion_id)
    return SesionActual(usuario=usuario, sesion_id=sesion_id)


SesionActualDep = Annotated[SesionActual, Depends(obtener_sesion_actual)]


async def obtener_usuario(actual: SesionActualDep) -> Usuario:
    """El usuario con sesión, si ya cambió la clave temporal."""
    if actual.usuario.debe_cambiar_clave:
        raise ErrorApi(
            403, "debe_cambiar_clave", "Primero hay que cambiar la contraseña"
        )
    return actual.usuario


UsuarioDep = Annotated[Usuario, Depends(obtener_usuario)]


def _exigir_rol(*roles: str):
    async def exigir(usuario: UsuarioDep) -> None:
        if usuario.rol not in roles:
            raise ErrorApi(403, "sin_permiso", "Tu rol no permite esta acción")

    return exigir


def publica() -> dict[str, Any]:
    """Ruta sin sesión (x-roles: [publico])."""
    return {"openapi_extra": {"x-roles": ["publico"]}}


def con_refresh() -> dict[str, Any]:
    """Rutas de sesión que se autentican con la cookie rt, no con at."""
    return {"openapi_extra": {"x-roles": list(ROLES)}}


def con_roles(*roles: str, cambio_pendiente: bool = False) -> dict[str, Any]:
    """Exige sesión y uno de los roles.

    `cambio_pendiente=True` deja pasar a quien todavía debe cambiar la clave
    (solo /auth/cambiar-clave, GET /me y PATCH /me).
    """
    desconocidos = set(roles) - set(ROLES)
    if not roles or desconocidos:
        raise ValueError(f"Roles inválidos: {sorted(desconocidos) or 'ninguno'}")
    if cambio_pendiente:
        if set(roles) != set(ROLES):
            raise ValueError("cambio_pendiente solo tiene sentido con todos los roles")
        dependencia = Depends(obtener_sesion_actual)
    else:
        dependencia = Depends(_exigir_rol(*roles))
    return {"dependencies": [dependencia], "openapi_extra": {"x-roles": list(roles)}}
