"""Rutas de administración (solo admin, B-08): listarUsuarios, obtenerUsuario,
cambiarRol, reiniciarClave, listarAprobadosPendientes y marcarQosAplicada del
contrato. Un instructor recibe 403 en todas (tests/test_roles.py).

Aquí no se crean ni se dan de baja cuentas: eso lo hace `apolo-training-admin`
en la VM de práctica (rutas internas), para que la cuenta exista en los dos
lados o en ninguno.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from app.core.auth import UsuarioDep, con_roles
from app.core.db import SesionDep
from app.models.valores import PATRON_USERNAME
from app.schemas.admin import (
    AprobadoPendiente,
    ClaveTemporal,
    EstadoCuenta,
    ListaUsuarios,
    UsuarioAdmin,
    UsuarioCambio,
    UsuarioDetalleAdmin,
)
from app.schemas.labs import SinNulos
from app.schemas.usuario import Cluster, Rol
from app.services import aprobados, usuarios
from app.services.auditoria import ip_de

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN = con_roles("admin")
Username = Annotated[str, Path(pattern=PATRON_USERNAME)]


@router.get(
    "/usuarios",
    operation_id="listarUsuarios",
    summary="Usuarios con su avance, con búsqueda y filtros",
    **ADMIN,
)
async def listar_usuarios(
    bd: SesionDep,
    q: Annotated[str | None, Query(max_length=100), SinNulos] = None,
    cluster: Cluster | None = None,
    rol: Rol | None = None,
    estado: EstadoCuenta | None = None,
    pagina: Annotated[int, Query(ge=1, le=100_000)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ListaUsuarios:
    return await usuarios.listar(
        bd,
        q=q,
        cluster=cluster,
        rol=rol,
        estado=estado,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get(
    "/usuarios/{username}",
    operation_id="obtenerUsuario",
    summary="Detalle de un usuario con su progreso",
    **ADMIN,
)
async def obtener_usuario(
    username: Username, admin: UsuarioDep, bd: SesionDep
) -> UsuarioDetalleAdmin:
    return await usuarios.detalle(bd, username, admin.idioma)


@router.patch(
    "/usuarios/{username}",
    operation_id="cambiarRol",
    summary="Cambiar el rol de un usuario",
    **ADMIN,
)
async def cambiar_rol(
    username: Username,
    cambio: UsuarioCambio,
    admin: UsuarioDep,
    bd: SesionDep,
    request: Request,
) -> UsuarioAdmin:
    return await usuarios.cambiar_rol_admin(
        bd, username, cambio.rol, admin, ip_de(request)
    )


@router.post(
    "/usuarios/{username}/reiniciar-clave",
    operation_id="reiniciarClave",
    summary="Generar una clave temporal de la plataforma",
    **ADMIN,
)
async def reiniciar_clave(
    username: Username,
    admin: UsuarioDep,
    bd: SesionDep,
    request: Request,
    response: Response,
) -> ClaveTemporal:
    # La clave va en la respuesta: que ningún caché la guarde.
    response.headers["Cache-Control"] = "no-store"
    return await usuarios.reiniciar_clave(bd, username, admin, ip_de(request))


@router.get(
    "/aprobados-pendientes",
    operation_id="listarAprobadosPendientes",
    summary="Quienes aprobaron el curso y esperan su QOS normal",
    **ADMIN,
)
async def listar_aprobados_pendientes(bd: SesionDep) -> list[AprobadoPendiente]:
    return await aprobados.pendientes(bd)


@router.post(
    "/aprobados-pendientes/{username}/qos-aplicada",
    operation_id="marcarQosAplicada",
    summary="Registrar que ya se aplicó la QOS normal en el clúster real",
    status_code=204,
    **ADMIN,
)
async def marcar_qos_aplicada(
    username: Username, admin: UsuarioDep, bd: SesionDep, request: Request
) -> None:
    await aprobados.marcar_qos(bd, username, admin, ip_de(request))
