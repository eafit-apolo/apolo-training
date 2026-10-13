"""Formato de error del contrato: {"detail": "...", "codigo": "..."}."""

import pytest
from fastapi import FastAPI, Query
from httpx import AsyncClient

from app.core.config import Settings
from app.core.errores import ErrorApi
from app.main import create_app


@pytest.fixture
def app_de_prueba(settings_sin_base: Settings) -> FastAPI:
    """App real con rutas extra solo para provocar cada tipo de error."""
    app = create_app(settings_sin_base)

    @app.get("/api/_prueba/error-api")
    async def error_api() -> None:
        raise ErrorApi(403, "sin_permiso", "Solo para admins")

    @app.get("/api/_prueba/validacion")
    async def validacion(pagina: int = Query(ge=1)) -> dict[str, int]:
        return {"pagina": pagina}

    @app.get("/api/_prueba/falla")
    async def falla() -> None:
        raise RuntimeError("algo se rompió")

    return app


@pytest.fixture
def cliente_errores(crear_cliente, app_de_prueba: FastAPI) -> AsyncClient:
    return crear_cliente(app_de_prueba)


async def test_error_api_lleva_su_codigo(cliente_errores: AsyncClient) -> None:
    respuesta = await cliente_errores.get("/api/_prueba/error-api")

    assert respuesta.status_code == 403
    assert respuesta.json() == {"detail": "Solo para admins", "codigo": "sin_permiso"}


async def test_ruta_inexistente_es_no_encontrado(cliente_errores: AsyncClient) -> None:
    respuesta = await cliente_errores.get("/api/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"
    assert "detail" in respuesta.json()


async def test_metodo_no_permitido(cliente_errores: AsyncClient) -> None:
    respuesta = await cliente_errores.post("/api/health")

    assert respuesta.status_code == 405
    assert respuesta.json()["codigo"] == "metodo_no_permitido"


async def test_validacion_dice_que_campo_fallo(cliente_errores: AsyncClient) -> None:
    respuesta = await cliente_errores.get(
        "/api/_prueba/validacion", params={"pagina": 0}
    )

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "datos_invalidos"
    assert cuerpo["errores"] == [{"campo": "pagina", "codigo": "greater_than_equal"}]


async def test_error_inesperado_no_filtra_detalles(
    cliente_errores: AsyncClient,
) -> None:
    respuesta = await cliente_errores.get("/api/_prueba/falla")

    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno", "codigo": "error_interno"}
    assert "algo se rompió" not in respuesta.text
