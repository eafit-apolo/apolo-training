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


def test_create_app_exige_el_secreto(settings_sin_base: Settings) -> None:
    with pytest.raises(RuntimeError, match="API_SECRETO"):
        create_app(settings_sin_base.model_copy(update={"secreto": None}))


def test_secreto_de_32_caracteres_o_mas() -> None:
    with pytest.raises(ValidationError, match="32 caracteres"):
        Settings(
            database_url="postgresql+asyncpg://nadie@localhost/nada", secreto="corto"
        )


def test_el_secreto_no_sale_en_repr(settings_sin_base: Settings) -> None:
    assert settings_sin_base.secreto.get_secret_value() not in repr(settings_sin_base)


@pytest.mark.parametrize(("docs", "esperado"), [(False, 404), (True, 200)])
async def test_docs_solo_si_se_activan(
    crear_cliente, settings_sin_base: Settings, docs: bool, esperado: int
) -> None:
    app = create_app(settings_sin_base.model_copy(update={"docs": docs}))
    cliente = crear_cliente(app)

    respuesta = await cliente.get("/api/openapi.json")

    assert respuesta.status_code == esperado


def test_medios_por_defecto_los_de_la_117(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_MEDIA_DIR", raising=False)
    monkeypatch.delenv("API_MEDIA_ENTREGA", raising=False)
    settings = Settings(database_url="postgresql+asyncpg://nadie@localhost/nada")

    assert str(settings.media_dir) == "/srv/apolo-training/media"
    assert settings.media_entrega == "nginx"


def test_entrega_de_medios_solo_nginx_o_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_DATABASE_URL", "postgresql+asyncpg://nadie@localhost/nada")
    monkeypatch.setenv("API_MEDIA_ENTREGA", "apache")

    with pytest.raises(ValidationError, match="media_entrega"):
        Settings()
