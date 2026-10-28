"""validar_sesion contra una API falsa (httpx.MockTransport, sin red)."""

import httpx
import pytest

from app.api import SesionInvalida, validar_sesion

# Lo que responde GET /api/me (esquema Usuario de api/openapi.yaml).
PERFIL = {
    "username": "ana",
    "nombre": "Ana",
    "cluster": "apolo2",
    "rol": "estudiante",
    "idioma": "es",
    "debe_cambiar_clave": False,
    "activo": True,
}


def api_falsa(estado: int, perfil: dict | None = None) -> httpx.AsyncClient:
    """Un cliente httpx cuya «API» responde siempre lo mismo a GET /api/me."""

    def responder(peticion: httpx.Request) -> httpx.Response:
        assert peticion.url.path == "/api/me"
        # Solo se reenvía la cookie de acceso.
        assert peticion.headers["cookie"] == "at=token"
        return httpx.Response(estado, json=perfil or {})

    return httpx.AsyncClient(
        base_url="http://api", transport=httpx.MockTransport(responder)
    )


async def test_sesion_valida():
    async with api_falsa(200, PERFIL) as cliente:
        assert await validar_sesion(cliente, "token") == "ana"


async def test_sin_cookie_ni_pregunta():
    async with api_falsa(200, PERFIL) as cliente:
        with pytest.raises(SesionInvalida):
            await validar_sesion(cliente, None)


@pytest.mark.parametrize(
    ("estado", "perfil"),
    [
        (401, None),  # sin sesión o vencida
        (200, {**PERFIL, "activo": False}),  # dada de baja
        (200, {**PERFIL, "debe_cambiar_clave": True}),  # clave temporal
        (200, {**PERFIL, "username": "../root"}),  # no es un usuario Unix
    ],
)
async def test_sesion_invalida(estado, perfil):
    async with api_falsa(estado, perfil) as cliente:
        with pytest.raises(SesionInvalida):
            await validar_sesion(cliente, "token")


async def test_api_con_error_no_es_sesion_invalida():
    # Un 500 es un problema de la plataforma, no del usuario: motivo «error».
    async with api_falsa(500) as cliente:
        with pytest.raises(httpx.HTTPStatusError):
            await validar_sesion(cliente, "token")
