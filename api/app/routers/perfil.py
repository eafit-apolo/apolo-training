"""GET y PATCH /api/me: operaciones obtenerPerfil y actualizarPerfil."""

from fastapi import APIRouter

from app.core.auth import SesionActualDep, con_roles
from app.core.db import SesionDep
from app.models.valores import ROLES
from app.schemas.usuario import PerfilCambio, UsuarioSalida

router = APIRouter(tags=["perfil"])

# Las dos admiten a quien todavía debe cambiar la clave: la app necesita el
# perfil para llevarlo a /cambiar-clave, y ahí también se cambia el idioma.
SIN_CAMBIO_PENDIENTE = con_roles(*ROLES, cambio_pendiente=True)


@router.get(
    "/me",
    operation_id="obtenerPerfil",
    summary="Perfil del usuario con sesión",
    **SIN_CAMBIO_PENDIENTE,
)
async def obtener_perfil(actual: SesionActualDep) -> UsuarioSalida:
    return UsuarioSalida.model_validate(actual.usuario)


@router.patch(
    "/me",
    operation_id="actualizarPerfil",
    summary="Cambiar el idioma preferido",
    **SIN_CAMBIO_PENDIENTE,
)
async def actualizar_perfil(
    datos: PerfilCambio, actual: SesionActualDep, bd: SesionDep
) -> UsuarioSalida:
    actual.usuario.idioma = datos.idioma
    await bd.commit()
    return UsuarioSalida.model_validate(actual.usuario)
