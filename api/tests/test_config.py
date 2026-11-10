"""Configuración desde el entorno y desde los secretos de Compose."""

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import CARPETA_SECRETOS, Settings, carpeta_secretos
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


# --- Secretos de Compose (W-05) ------------------------------------------------

URL_SECRETA = "postgresql+asyncpg://api:clave-de-la-117@db/apolo_training"
SECRETO_EN_ARCHIVO = "secreto-de-la-117-" * 3


@pytest.fixture
def secretos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Una carpeta como /run/secrets de la 117, sin las variables en el entorno."""
    monkeypatch.delenv("API_DATABASE_URL", raising=False)
    monkeypatch.delenv("API_SECRETO", raising=False)
    # Como los deja Compose: un archivo por secreto, con salto de línea al final.
    (tmp_path / "api_database_url").write_text(URL_SECRETA + "\n")
    (tmp_path / "api_secreto").write_text(SECRETO_EN_ARCHIVO + "\n")
    return tmp_path


def test_lee_los_secretos_de_compose(secretos: Path) -> None:
    settings = Settings(_secrets_dir=secretos)

    assert settings.database_url.get_secret_value() == URL_SECRETA
    assert settings.secreto.get_secret_value() == SECRETO_EN_ARCHIVO


def test_la_variable_de_entorno_gana_sobre_el_secreto(
    secretos: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("API_DATABASE_URL", "postgresql+asyncpg://dev@localhost/dev")

    settings = Settings(_secrets_dir=secretos)

    assert (
        settings.database_url.get_secret_value()
        == "postgresql+asyncpg://dev@localhost/dev"
    )
    assert settings.secreto.get_secret_value() == SECRETO_EN_ARCHIVO


def test_un_secreto_en_archivo_tambien_se_valida(secretos: Path) -> None:
    (secretos / "api_secreto").write_text("corto\n")

    with pytest.raises(ValidationError, match="32 caracteres"):
        Settings(_secrets_dir=secretos)


def test_carpeta_de_secretos_solo_si_existe(tmp_path: Path) -> None:
    assert carpeta_secretos(tmp_path) == tmp_path
    assert carpeta_secretos(tmp_path / "no-existe") is None


def test_en_la_117_busca_en_run_secrets() -> None:
    # La condición se evalúa al importar el módulo. Para verla como en la 117,
    # se importa en otro proceso haciendo creer que /run/secrets existe.
    codigo = (
        "from pathlib import Path\n"
        "original = Path.is_dir\n"
        "Path.is_dir = lambda p: str(p) == '/run/secrets' or original(p)\n"
        "from app.core.config import Settings\n"
        "print(Settings.model_config['secrets_dir'])\n"
    )
    proceso = subprocess.run(  # noqa: S603 (el intérprete de las pruebas, sin shell)
        [sys.executable, "-c", codigo],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert Path("/run/secrets") == CARPETA_SECRETOS
    assert proceso.stdout.strip() == "/run/secrets"
