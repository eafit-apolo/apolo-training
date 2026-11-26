"""Rutas internas de la VM de práctica (token de servicio, sin sesión):
sincronizarLabs (B-07), altaUsuario y cambiarEstadoUsuario (B-08) del
contrato. Las llaman el timer de la V-05 y `apolo-training-admin` (V-04).

La IP de la 116 la filtra el nginx de la 117; la API revisa el token.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Request

from app.core.auth import con_servicio
from app.core.db import SesionDep
from app.models.valores import PATRON_USERNAME
from app.schemas.labs import ReporteLabs, ResultadoSincronizacion
from app.schemas.usuario import AltaUsuario, EstadoUsuario, UsuarioSalida
from app.services import labs, usuarios
from app.services.auditoria import ip_de

router = APIRouter(prefix="/internal", tags=["internal"])

Username = Annotated[str, Path(pattern=PATRON_USERNAME)]


@router.post(
    "/labs",
    operation_id="sincronizarLabs",
    summary="Recibir el reporte de prácticas de la VM de práctica",
    **con_servicio(),
)
async def sincronizar_labs(
    reporte: ReporteLabs, bd: SesionDep
) -> ResultadoSincronizacion:
    return await labs.sincronizar(bd, reporte)


@router.post(
    "/usuarios",
    operation_id="altaUsuario",
    summary="Crear el usuario en la plataforma (apolo-training-admin alta)",
    status_code=201,
    **con_servicio(),
)
async def alta_usuario(
    entrada: AltaUsuario, bd: SesionDep, request: Request
) -> UsuarioSalida:
    return UsuarioSalida.model_validate(
        await usuarios.alta(bd, entrada, ip_de(request))
    )


@router.patch(
    "/usuarios/{username}",
    operation_id="cambiarEstadoUsuario",
    summary="Dar de baja o reactivar (apolo-training-admin baja)",
    **con_servicio(),
)
async def cambiar_estado_usuario(
    username: Username, entrada: EstadoUsuario, bd: SesionDep, request: Request
) -> UsuarioSalida:
    return UsuarioSalida.model_validate(
        await usuarios.cambiar_estado(bd, username, entrada.activo, ip_de(request))
    )
