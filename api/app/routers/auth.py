"""Rutas /api/auth/*: operaciones iniciarSesion, renovarSesion, cerrarSesion y
cambiarClave del contrato."""

from fastapi import APIRouter, Request, Response, status

from app.core.auth import SesionActualDep, con_refresh, con_roles, publica
from app.core.db import SesionDep
from app.core.seguridad import (
    CABECERA_CSRF,
    COOKIE_ACCESO,
    COOKIE_CSRF,
    COOKIE_REFRESH,
    borrar_cookies,
    poner_cookies,
)
from app.models.valores import ROLES
from app.schemas.auth import CambioClave, LoginEntrada, LoginSalida
from app.schemas.usuario import UsuarioSalida
from app.services import auth
from app.services.auditoria import ip_de

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    operation_id="iniciarSesion",
    summary="Iniciar sesión con usuario y contraseña",
    **publica(),
)
async def iniciar_sesion(
    datos: LoginEntrada, request: Request, response: Response, bd: SesionDep
) -> LoginSalida:
    settings = request.app.state.settings
    usuario, tokens = await auth.iniciar_sesion(
        bd, settings, datos.username, datos.clave.get_secret_value(), ip_de(request)
    )
    poner_cookies(
        response,
        settings,
        acceso=tokens.acceso,
        refresh=tokens.refresh,
        csrf=tokens.csrf,
    )
    return LoginSalida(usuario=UsuarioSalida.model_validate(usuario))


@router.post(
    "/refresh",
    operation_id="renovarSesion",
    summary="Renovar el token de acceso con la cookie de refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    **con_refresh(),
)
async def renovar_sesion(request: Request, response: Response, bd: SesionDep) -> None:
    settings = request.app.state.settings
    tokens = await auth.renovar_sesion(
        bd,
        settings,
        request.cookies.get(COOKIE_REFRESH),
        request.headers.get(CABECERA_CSRF),
        request.cookies.get(COOKIE_CSRF),
        ip_de(request),
    )
    if tokens is not None:
        poner_cookies(
            response,
            settings,
            acceso=tokens.acceso,
            refresh=tokens.refresh,
            csrf=tokens.csrf,
        )


@router.post(
    "/logout",
    operation_id="cerrarSesion",
    summary="Cerrar sesión",
    status_code=status.HTTP_204_NO_CONTENT,
    **con_refresh(),
)
async def cerrar_sesion(request: Request, response: Response, bd: SesionDep) -> None:
    settings = request.app.state.settings
    await auth.cerrar_sesion(
        bd,
        settings,
        request.cookies.get(COOKIE_REFRESH),
        request.cookies.get(COOKIE_ACCESO),
        request.headers.get(CABECERA_CSRF),
        request.cookies.get(COOKIE_CSRF),
    )
    borrar_cookies(response, settings)


@router.post(
    "/cambiar-clave",
    operation_id="cambiarClave",
    summary="Cambiar la contraseña de la plataforma",
    status_code=status.HTTP_204_NO_CONTENT,
    **con_roles(*ROLES, cambio_pendiente=True),
)
async def cambiar_clave(
    datos: CambioClave, actual: SesionActualDep, request: Request, bd: SesionDep
) -> None:
    await auth.cambiar_clave(
        bd,
        actual.usuario,
        actual.sesion_id,
        datos.clave_actual.get_secret_value(),
        datos.clave_nueva.get_secret_value(),
        ip_de(request),
    )
