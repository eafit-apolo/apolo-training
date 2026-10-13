"""GET /api/health según el esquema `Salud` del contrato."""

from httpx import AsyncClient


async def test_salud_con_base(cliente: AsyncClient) -> None:
    respuesta = await cliente.get("/api/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "estado": "ok",
        "base_datos": "ok",
        "version": "pruebas",
    }


async def test_salud_sin_base_responde_503(cliente_sin_base: AsyncClient) -> None:
    respuesta = await cliente_sin_base.get("/api/health")

    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "estado": "degradado",
        "base_datos": "sin_conexion",
        "version": "pruebas",
    }


async def test_salud_no_expone_la_url_en_el_log(
    cliente_sin_base: AsyncClient, caplog
) -> None:
    await cliente_sin_base.get("/api/health")

    assert "PostgreSQL no responde" in caplog.text
    assert "postgresql+asyncpg" not in caplog.text
    assert "nadie" not in caplog.text
