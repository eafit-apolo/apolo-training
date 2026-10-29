"""Un content/ de prueba en una carpeta temporal, con los esquemas reales (B-04).

El curso de ejemplo tiene tres módulos: m00 (una lección con video y quiz),
m01 (VPN con un video por sistema, y SSH con una práctica) y m02 (solo texto).
"""

import shutil
from pathlib import Path

import pytest

# La raíz del repo, o / en el servicio `pruebas` de deploy/compose.dev.yaml,
# que monta content/ en /content.
CONTENIDO_REAL = Path(__file__).resolve().parents[2] / "content"

CURSO = """---
id: induccion
titulo: Curso de prueba
descripcion: Un curso para las pruebas.
---
"""

MODULO = """---
id: {id}
titulo: {titulo}
resumen: Resumen de {titulo}.
duracion: {duracion}
---
"""

BIENVENIDA = """---
id: m00/bienvenida
titulo: Bienvenida
orden: 1
duracion: 3
video: m00-bienvenida
quiz:
  - clave: m00-login
    enunciado: ¿Qué se hace en el login?
    opciones:
      - texto: Enviar trabajos.
        correcta: true
      - texto: Correr simulaciones.
    explicacion: El login es para preparar y enviar.
---

## Objetivos

Texto de la bienvenida.
"""

VPN = """---
id: m01/vpn
titulo: La VPN
orden: 1
duracion: 4
video:
  windows: m01-vpn-windows
  macos: m01-vpn-macos
  linux: m01-vpn-linux
---

## Objetivos

Conéctate a la VPN.
"""

SSH = """---
id: m01/ssh
titulo: Entrar por SSH
orden: 2
duracion: 5
practicas: [conexion]
quiz:
  - clave: m01-ssh
    enunciado: ¿Con qué te conectas?
    opciones:
      - texto: Con SSH.
        correcta: true
      - texto: Con FTP.
      - texto: Con la terminal de la plataforma.
        correcta: true
    explicacion: SSH o la terminal real.
---

## Objetivos

Entra por SSH.
"""

LECTURA = """---
id: m02/lectura
titulo: Una lectura
orden: 1
duracion: 2
---

## Objetivos

Solo texto.
"""

ARCHIVOS: dict[str, str] = {
    "es/_curso.md": CURSO,
    "es/m00/_modulo.md": MODULO.format(id="m00", titulo="Bienvenida", duracion=3),
    "es/m00/bienvenida.md": BIENVENIDA,
    "es/m01/_modulo.md": MODULO.format(id="m01", titulo="Conexión", duracion=9),
    "es/m01/vpn.md": VPN,
    "es/m01/ssh.md": SSH,
    "es/m02/_modulo.md": MODULO.format(id="m02", titulo="Lectura", duracion=2),
    "es/m02/lectura.md": LECTURA,
}


def contenido_real() -> Path:
    if not (CONTENIDO_REAL / "schema").is_dir():
        pytest.fail(
            f"No encuentro {CONTENIDO_REAL}: corre las pruebas desde el repo completo"
        )
    return CONTENIDO_REAL


def armar_contenido(raiz: Path, archivos: dict[str, str | None] | None = None) -> Path:
    """content/ con el curso de ejemplo, los esquemas y las plantillas reales.

    `archivos` agrega o reemplaza archivos (ruta relativa → texto); con None,
    el archivo se quita.
    """
    real = contenido_real()
    if raiz.exists():
        shutil.rmtree(raiz)
    shutil.copytree(real / "schema", raiz / "schema")
    (raiz / "es").mkdir()
    for plantilla in ("_plantilla.md", "_plantilla-modulo.md"):
        shutil.copy(real / "es" / plantilla, raiz / "es" / plantilla)
    todos: dict[str, str | None] = {**ARCHIVOS, **(archivos or {})}
    for ruta, texto in todos.items():
        if texto is None:
            continue
        archivo = raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(texto, encoding="utf-8")
    return raiz
