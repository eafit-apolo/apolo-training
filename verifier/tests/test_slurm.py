"""Prácticas que leen sacct: modulos, memoria, nucleos, paralelo y eficiencia."""

import pytest

import apolo_training as at

# (escenario, práctica) -> (aprobada, clave del mensaje)
ESPERADO = {
    ("todo_hecho", "modulos"): (True, "modulos_ok"),
    ("todo_hecho", "memoria"): (True, "memoria_ok"),
    ("todo_hecho", "nucleos"): (True, "nucleos_ok"),
    ("todo_hecho", "paralelo"): (True, "paralelo_ok"),
    ("solo_fallo_memoria", "modulos"): (False, "modulos_no"),
    ("solo_fallo_memoria", "memoria"): (False, "memoria_fallo"),
    ("solo_fallo_memoria", "nucleos"): (False, "nucleos_no"),
    ("solo_fallo_memoria", "paralelo"): (False, "paralelo_no"),
    ("nada_hecho", "modulos"): (False, "modulos_no"),
    ("nada_hecho", "memoria"): (False, "memoria_no"),
    ("nada_hecho", "nucleos"): (False, "nucleos_no"),
    ("nada_hecho", "paralelo"): (False, "paralelo_no"),
    # Apolo III: sin límite de memoria y sin registro del uso de CPU
    ("como_apolo3", "modulos"): (True, "modulos_ok"),
    ("como_apolo3", "memoria"): (False, "memoria_sin_limite"),
    ("como_apolo3", "nucleos"): (False, "sin_datos"),
    ("como_apolo3", "paralelo"): (False, "sin_datos"),
}


@pytest.mark.parametrize("caso", sorted(ESPERADO), ids="-".join)
def test_practicas_slurm(contexto, caso):
    nombre_escenario, practica = caso
    ok, clave, _ = at.VERIFICADORES[practica](contexto(nombre_escenario))
    assert (ok, clave) == ESPERADO[caso]


def test_paralelo_informa_la_eficiencia(contexto):
    ok, _, params = at.practica_paralelo(contexto("todo_hecho"))
    assert ok
    assert params["mejor"] == pytest.approx(75 / (20 * 4))


def test_sacct_pide_solo_los_trabajos_del_usuario(contexto, llamadas_sacct):
    at.practica_memoria(contexto("todo_hecho"))
    (args,) = llamadas_sacct()
    assert args[args.index("-u") + 1] == "prueba"
    assert args[args.index("-S") + 1] == "now-30days"
    assert "--name=curso-memoria" in args


def test_verificar_por_comando(correr):
    r = correr("verificar", "memoria", escenario="todo_hecho")
    assert r.codigo == 0
    assert r.salida.startswith("[APROBADO] ")

    r = correr("verificar", "memoria", escenario="solo_fallo_memoria")
    assert r.codigo == 1
    assert r.salida.startswith("[PENDIENTE] ")


def test_eficiencia_de_un_trabajo(correr):
    r = correr("eficiencia", "104", escenario="todo_hecho")
    assert r.codigo == 0
    assert "Trabajo 104 (curso-nucleos): COMPLETED" in r.salida
    assert "Eficiencia de núcleos: 25%" in r.salida
    assert "1.0 de 4 núcleos" in r.salida
    assert "Memoria máxima usada: 210 MB" in r.salida


def test_eficiencia_de_un_trabajo_en_curso(correr):
    r = correr("eficiencia", "106", escenario="todo_hecho")
    assert r.codigo == 0
    assert "Espera a que termine" in r.salida


def test_eficiencia_sin_registro_de_uso(correr):
    r = correr("eficiencia", "104", escenario="como_apolo3")
    assert r.codigo == 0
    assert "no está guardando el uso real de CPU" in r.salida


def test_eficiencia_de_un_trabajo_que_no_existe(correr):
    r = correr("eficiencia", "999", escenario="todo_hecho")
    assert r.codigo == 1
    assert "No encuentro el trabajo 999" in r.salida


@pytest.mark.parametrize("jobid", ["abc", "12.batch", "-5"])
def test_eficiencia_con_jobid_invalido(correr, jobid):
    r = correr("eficiencia", jobid)
    assert r.codigo == 2
    assert "número del trabajo" in r.error


def test_sin_sacct(correr):
    r = correr("verificar", "modulos", PATH="/ruta/que/no/existe")
    assert r.codigo == 2
    assert "No encuentro el comando sacct" in r.error


def test_sacct_con_error(correr):
    r = correr("verificar", "modulos", SACCT_CODIGO="1")
    assert r.codigo == 2
    assert "código 1" in r.error


@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("", 0.0),
        ("Unknown", 0.0),
        ("00:04.120", 4.12),
        ("01:00.000", 60.0),
        ("02:03:04", 7384.0),
        ("1-00:00:01", 86401.0),
    ],
)
def test_segundos(valor, esperado):
    assert at.segundos(valor) == pytest.approx(esperado)
