"""Configuración desde el entorno."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_exige_el_driver_async() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg"):
        Settings(database_url="postgresql://nadie@localhost/nada")


def test_la_clave_no_sale_en_repr() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://nadie:clave-secreta@localhost/nada"
    )

    assert "clave-secreta" not in repr(settings)


def test_lee_variables_con_prefijo_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_DATABASE_URL", "postgresql+asyncpg://nadie@localhost/nada")
    monkeypatch.setenv("API_VERSION", "1.2.3")

    assert Settings().version == "1.2.3"


@pytest.mark.parametrize(("docs", "esperado"), [(False, 404), (True, 200)])
async def test_docs_solo_si_se_activan(
    crear_cliente, settings_sin_base: Settings, docs: bool, esperado: int
) -> None:
    app = create_app(settings_sin_base.model_copy(update={"docs": docs}))
    cliente = crear_cliente(app)

    respuesta = await cliente.get("/api/openapi.json")

    assert respuesta.status_code == esperado
