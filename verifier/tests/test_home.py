"""preparar y las prácticas que miran el HOME: conexion, terminal y archivos."""

import os
import re

import apolo_training as at
from conftest import REPO


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def escribir(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)


# --- preparar ------------------------------------------------------------


def test_preparar_copia_el_material(correr, home):
    r = correr("preparar")
    assert r.codigo == 0
    assert "~/apolo-training" in r.salida
    carpeta = os.path.join(home, "apolo-training")
    assert os.path.isfile(os.path.join(carpeta, "pi.py"))
    assert os.access(os.path.join(carpeta, "curso.sh"), os.X_OK)
    assert os.path.isdir(os.path.join(carpeta, "terminal", "datos"))
    assert not os.path.exists(os.path.join(carpeta, "README.md"))


def test_preparar_genera_un_codigo_por_usuario(correr, home):
    correr("preparar")
    ida = leer(os.path.join(home, "apolo-training", "archivos", "ida.txt"))
    assert re.search(r"ARC-[0-9A-F]{6}", ida)


def test_preparar_no_toca_lo_que_ya_existe(correr, home):
    correr("preparar")
    carpeta = os.path.join(home, "apolo-training")
    ida = os.path.join(carpeta, "archivos", "ida.txt")
    antes = leer(ida)
    escribir(os.path.join(carpeta, "curso.sh"), "# editado por el usuario\n")
    os.remove(os.path.join(carpeta, "pi.py"))

    r = correr("preparar")
    assert r.codigo == 0
    assert "Restauré 1 archivo(s)" in r.salida
    assert leer(ida) == antes
    assert leer(os.path.join(carpeta, "curso.sh")) == "# editado por el usuario\n"
    assert os.path.isfile(os.path.join(carpeta, "pi.py"))

    r = correr("preparar")
    assert "no toqué tus archivos" in r.salida


def test_preparar_sin_material(correr, tmp_path):
    r = correr("preparar", APOLO_TRAINING=str(tmp_path / "no-existe"))
    assert r.codigo == 2
    assert "module load apolo-training" in r.error


def test_material_tiene_una_sola_clave(contexto):
    clave = at.clave_original(contexto())
    assert re.match(r"^TRN-[A-Z0-9]{4}-[A-Z0-9]{4}$", clave)


# --- conexion ------------------------------------------------------------


def test_conexion_con_ssh(contexto):
    ctx = contexto(SSH_CONNECTION="cliente 50000 servidor 22")
    assert at.practica_conexion(ctx) == (True, "conexion_ok", {})


def test_conexion_sin_ssh(contexto):
    assert at.practica_conexion(contexto())[0] is False


# --- terminal ------------------------------------------------------------


def test_terminal_sin_preparar(correr):
    r = correr("verificar", "terminal")
    assert r.codigo == 1
    assert "apolo-training preparar" in r.salida


def test_terminal_paso_a_paso(correr, home, contexto):
    correr("preparar")
    respuesta = os.path.join(home, "apolo-training", "terminal", "respuesta.txt")

    r = correr("verificar", "terminal")
    assert r.codigo == 1
    assert "~/apolo-training/terminal/respuesta.txt" in r.salida

    escribir(respuesta, "TRN-AAAA-BBBB\n")
    r = correr("verificar", "terminal")
    assert r.codigo == 1
    assert "grep -r" in r.salida

    # Sirve en minúsculas y con la línea completa que encontró grep
    clave = at.clave_original(contexto())
    escribir(respuesta, "aviso: la clave del curso es " + clave.lower() + "\n")
    r = correr("verificar", "terminal")
    assert r.codigo == 0
    assert r.salida.startswith("[APROBADO]")


def test_terminal_compara_con_el_material_original(correr, home):
    """Cambiar la clave en la copia del usuario no sirve para aprobar."""
    correr("preparar")
    carpeta = os.path.join(home, "apolo-training", "terminal")
    escribir(os.path.join(carpeta, "datos", "notas.txt"), "TRN-AAAA-BBBB\n")
    escribir(os.path.join(carpeta, "respuesta.txt"), "TRN-AAAA-BBBB\n")
    assert correr("verificar", "terminal").codigo == 1


# --- archivos ------------------------------------------------------------


def test_archivos_paso_a_paso(correr, home):
    r = correr("verificar", "archivos")
    assert r.codigo == 1
    assert "apolo-training preparar" in r.salida

    correr("preparar")
    carpeta = os.path.join(home, "apolo-training", "archivos")
    r = correr("verificar", "archivos")
    assert r.codigo == 1
    assert "vuelta.txt" in r.salida

    escribir(os.path.join(carpeta, "vuelta.txt"), "código / code: ARC-000000\n")
    r = correr("verificar", "archivos")
    assert r.codigo == 1
    assert "no tiene el código" in r.salida

    # Lo que haría el usuario: descargar ida.txt y subirlo con otro nombre
    escribir(
        os.path.join(carpeta, "vuelta.txt"), leer(os.path.join(carpeta, "ida.txt"))
    )
    r = correr("verificar", "archivos")
    assert r.codigo == 0
    assert r.salida.startswith("[APROBADO]")


def test_material_del_repo_no_trae_ida():
    assert not os.path.exists(os.path.join(REPO, "labs", "archivos", "ida.txt"))
