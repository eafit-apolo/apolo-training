"""Línea de comandos: idioma, ayuda, progreso y errores de uso."""

import re
import string

import pytest

import apolo_training as at


def campos(plantilla):
    return sorted(c[1] for c in string.Formatter().parse(plantilla) if c[1])


def test_los_dos_idiomas_tienen_los_mismos_mensajes():
    assert sorted(at.MENSAJES["es"]) == sorted(at.MENSAJES["en"])
    for clave, plantilla in at.MENSAJES["es"].items():
        assert campos(plantilla) == campos(at.MENSAJES["en"][clave]), clave


def test_espanol_por_defecto(correr):
    r = correr("verificar", "memoria")
    assert r.salida.startswith("[PENDIENTE] Primero envía")


@pytest.mark.parametrize(
    "args",
    [
        ["--lang", "en", "verificar", "memoria"],
        ["verificar", "memoria", "--lang", "en"],
        ["verificar", "--lang=en", "memoria"],
        ["verificar", "memoria", "--lang", "EN"],
    ],
)
def test_ingles_con_lang(correr, args):
    r = correr(*args)
    assert r.salida.startswith("[PENDING] First submit")


def test_ingles_con_la_variable(correr):
    r = correr("verificar", "memoria", APOLO_TRAINING_LANG="en")
    assert r.salida.startswith("[PENDING]")


def test_lang_manda_sobre_la_variable(correr):
    r = correr("verificar", "memoria", "--lang", "es", APOLO_TRAINING_LANG="en")
    assert r.salida.startswith("[PENDIENTE]")


def test_variable_mal_escrita_vuelve_al_espanol(correr):
    r = correr("verificar", "memoria", APOLO_TRAINING_LANG="fr")
    assert r.codigo == 1
    assert r.salida.startswith("[PENDIENTE]")


@pytest.mark.parametrize("args", [["--lang", "fr", "progreso"], ["progreso", "--lang"]])
def test_lang_invalido(correr, args):
    r = correr(*args)
    assert r.codigo == 2
    assert "Usa es o en" in r.error


@pytest.mark.parametrize("idioma, texto", [("es", "--lang en"), ("en", "--lang en")])
def test_la_ayuda_explica_como_cambiar_el_idioma(correr, idioma, texto):
    r = correr("ayuda", "--lang", idioma)
    assert r.codigo == 0
    assert texto in r.salida
    assert "APOLO_TRAINING_LANG=en" in r.salida
    for practica in at.PRACTICAS:
        assert practica in r.salida


def test_sin_argumentos_muestra_la_ayuda(correr):
    r = correr()
    assert r.codigo == 2
    assert "Uso:" in r.salida


def test_progreso_lista_las_siete_practicas(correr):
    r = correr("progreso", escenario="todo_hecho", SSH_CONNECTION="x 1 y 22")
    assert r.codigo == 0
    filas = dict(re.split(r"\s+", linea, maxsplit=1) for linea in r.salida.splitlines())
    assert list(filas) == list(at.PRACTICAS)
    assert filas["memoria"] == "aprobado"
    assert filas["conexion"] == "aprobado"
    assert filas["terminal"] == "pendiente"


def test_progreso_en_ingles(correr):
    r = correr("progreso", "--lang", "en")
    assert "pending" in r.salida
    assert "pendiente" not in r.salida


@pytest.mark.parametrize(
    "args, mensaje",
    [
        (["verificar"], "Indica qué práctica"),
        (["verificar", "ondemand"], "No conozco la práctica «ondemand»"),
        (["verificar", "ondemand", "123"], "No conozco la práctica"),
        (["instalar"], "No conozco «instalar»"),
        (["progreso", "extra"], "No conozco"),
    ],
)
def test_errores_de_uso(correr, args, mensaje):
    r = correr(*args)
    assert r.codigo == 2
    assert mensaje in r.error


def test_ondemand_ya_no_existe():
    assert "ondemand" not in at.VERIFICADORES
    assert "ondemand" not in at.PRACTICAS
    assert set(at.VERIFICADORES) == set(at.PRACTICAS)
