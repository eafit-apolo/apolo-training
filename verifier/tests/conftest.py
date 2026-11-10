import json
import os
import subprocess
import sys

import pytest

PRUEBAS = os.path.dirname(os.path.abspath(__file__))
VERIFIER = os.path.dirname(PRUEBAS)
REPO = os.path.dirname(VERIFIER)
SCRIPT = os.path.join(VERIFIER, "apolo_training.py")
ESCENARIOS = os.path.join(PRUEBAS, "escenarios")

sys.path.insert(0, VERIFIER)

import apolo_training

# Variables del sistema que no deben influir en las pruebas
QUITAR = ("SSH_CONNECTION", "SSH_CLIENT", "APOLO_TRAINING_LANG", "APOLO_TRAINING")


@pytest.fixture
def home(tmp_path):
    carpeta = tmp_path / "home"
    carpeta.mkdir()
    return str(carpeta)


@pytest.fixture
def entorno(tmp_path, home):
    """Entorno de un usuario de prueba: HOME temporal y sacct y squeue simulados."""
    env = {k: v for k, v in os.environ.items() if k not in QUITAR}
    env.update(
        {
            "HOME": home,
            "PATH": os.path.join(PRUEBAS, "bin") + os.pathsep + env.get("PATH", ""),
            "APOLO_TRAINING": REPO,
            "SACCT_ESCENARIO": os.path.join(ESCENARIOS, "nada_hecho.json"),
            "SACCT_LOG": str(tmp_path / "sacct.log"),
            "SQUEUE_LOG": str(tmp_path / "squeue.log"),
        }
    )
    return env


def escenario(nombre):
    return os.path.join(ESCENARIOS, nombre + ".json")


@pytest.fixture
def contexto(entorno, home):
    """Contexto para llamar las prácticas como funciones."""

    def crear(nombre_escenario="nada_hecho", **extra):
        env = dict(entorno, SACCT_ESCENARIO=escenario(nombre_escenario), **extra)
        return apolo_training.Contexto(
            usuario="prueba", home=home, base=REPO, entorno=env
        )

    return crear


class Resultado:
    def __init__(self, proceso):
        self.codigo = proceso.returncode
        self.salida = proceso.stdout
        self.error = proceso.stderr


@pytest.fixture
def correr(entorno):
    """Corre el comando como lo haría el usuario y devuelve código y salida."""

    def ejecutar(*args, **kwargs):
        env = dict(entorno)
        if "escenario" in kwargs:
            env["SACCT_ESCENARIO"] = escenario(kwargs.pop("escenario"))
        env.update(kwargs)
        proceso = subprocess.run(
            [sys.executable, SCRIPT] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env,
            check=False,
        )
        return Resultado(proceso)

    return ejecutar


def leer_llamadas(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta) as f:
        return [json.loads(linea) for linea in f]


@pytest.fixture
def llamadas_sacct(entorno):
    """Las llamadas que recibió el sacct simulado, como listas de argumentos."""
    return lambda: leer_llamadas(entorno["SACCT_LOG"])


@pytest.fixture
def llamadas_squeue(entorno):
    """Las llamadas que recibió el squeue simulado, como listas de argumentos."""
    return lambda: leer_llamadas(entorno["SQUEUE_LOG"])
