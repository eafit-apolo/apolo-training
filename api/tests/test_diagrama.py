"""El diagrama de docs/diseno/modelo-datos.md coincide con los modelos (B-02).

Compara tablas y columnas del bloque Mermaid con Base.metadata. Si cambias un
modelo, cambia también el diagrama en el mismo PR.

Busca el archivo dos carpetas arriba de tests/: la raíz del repo, o / en el
servicio `pruebas` de deploy/compose.dev.yaml, que monta docs/ en /docs.
"""

import re
from pathlib import Path

import pytest

from app.models import Base

DIAGRAMA = Path(__file__).resolve().parents[2] / "docs" / "diseno" / "modelo-datos.md"
TABLA = re.compile(r"^  (\w+) \{$")
COLUMNA = re.compile(r"^    \w+(?:\[\])? (\w+)")


def columnas_del_diagrama(texto: str) -> dict[str, set[str]]:
    bloque = texto.split("```mermaid", 1)[1].split("```", 1)[0]
    tablas: dict[str, set[str]] = {}
    actual = None
    for linea in bloque.splitlines():
        if inicio := TABLA.match(linea):
            actual = tablas.setdefault(inicio.group(1), set())
        elif linea.strip() == "}":
            actual = None
        elif actual is not None and (columna := COLUMNA.match(linea)):
            actual.add(columna.group(1))
    return tablas


def test_diagrama_igual_a_los_modelos() -> None:
    if not DIAGRAMA.is_file():
        pytest.fail(
            f"No encuentro {DIAGRAMA}: corre las pruebas desde el repo completo"
        )

    diagrama = columnas_del_diagrama(DIAGRAMA.read_text(encoding="utf-8"))
    modelos = {
        nombre: {columna.name for columna in tabla.columns}
        for nombre, tabla in Base.metadata.tables.items()
    }

    assert diagrama == modelos
