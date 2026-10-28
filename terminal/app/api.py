"""Quién abre la terminal: se le pregunta a la API con la cookie del usuario.

El gateway no conoce la llave de los JWT: reenvía la cookie `at` a
GET /api/me, y la API dice si la sesión sirve y de quién es.
"""

import re

import httpx

# Nombres de usuario Unix válidos. La API ya los valida al crear la cuenta;
# esto es una segunda barrera antes de usarlo como usuario SSH (paso 4).
USERNAME_VALIDO = re.compile(r"[a-z_][a-z0-9_-]{0,31}")


class SesionInvalida(Exception):
    """Sin cookie, sesión vencida o cerrada, cuenta de baja o clave temporal."""


async def validar_sesion(cliente: httpx.AsyncClient, cookie_at: str | None) -> str:
    """Devuelve el username si la sesión puede abrir la terminal.

    Lanza SesionInvalida si no puede, y httpx.HTTPError si la API falla.
    """
    if not cookie_at:
        raise SesionInvalida
    # Solo la cookie de acceso: la de refresh y la de CSRF no hacen falta.
    respuesta = await cliente.get("/api/me", headers={"Cookie": f"at={cookie_at}"})
    if respuesta.status_code in (401, 403):
        raise SesionInvalida
    respuesta.raise_for_status()

    perfil = respuesta.json()
    # /api/me también responde a quien debe cambiar la clave temporal; la app lo
    # lleva a /cambiar-clave, así que aquí no se le abre la terminal.
    if not perfil["activo"] or perfil["debe_cambiar_clave"]:
        raise SesionInvalida
    username = perfil["username"]
    if not USERNAME_VALIDO.fullmatch(username):
        raise SesionInvalida
    return username
