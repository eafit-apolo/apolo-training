"""Ayudas para las pruebas de sesión (B-03)."""

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora, hash_clave
from app.models import Usuario

CLAVE = "clave-de-prueba-1"


async def crear_usuario(
    bd: AsyncSession,
    username: str = "tester",
    *,
    clave: str = CLAVE,
    rol: str = "estudiante",
    debe_cambiar_clave: bool = False,
    activo: bool = True,
) -> Usuario:
    usuario = Usuario(
        username=username,
        nombre=f"Prueba {username}",
        cluster="apolo2",
        rol=rol,
        idioma="es",
        clave_hash=await hash_clave(clave),
        debe_cambiar_clave=debe_cambiar_clave,
        activo=activo,
        baja_en=None if activo else ahora(),
    )
    bd.add(usuario)
    await bd.flush()
    return usuario


async def ingresar(
    cliente: AsyncClient, username: str = "tester", clave: str = CLAVE
) -> Response:
    return await cliente.post(
        "/api/auth/login", json={"username": username, "clave": clave}
    )


def con_csrf(cliente: AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": cliente.cookies["csrf"]}


def cookies_puestas(respuesta: Response) -> dict[str, str]:
    """Nombre → cabecera Set-Cookie completa (en minúsculas)."""
    return {
        linea.split("=", 1)[0]: linea.lower()
        for linea in respuesta.headers.get_list("set-cookie")
    }
