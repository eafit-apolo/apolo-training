"""V-09: lo que la A-02 encontró en el historial de Slurm (sacct).

1. En Apolo II el contador de JobID se reinició: dos trabajos distintos pueden
   tener el mismo número.
2. Hay trabajos fantasma (runaway): sacct los da como RUNNING para siempre,
   aunque Slurm ya no los tiene. Como no tienen hora de fin, salen en cualquier
   ventana de fechas y chocan con los números nuevos.
3. Apolo III no registra TotalCPU ni MaxRSS. Lo cubren test_apolo3.py y
   test_slurm.py; aquí, que la búsqueda por JobID tampoco se confunda.

El escenario contador_reiniciado es un usuario de Apolo II con trabajos nuevos
que comparten número con fantasmas de antes del reinicio.
"""

import os
import subprocess
import sys

import pytest

import apolo_training as at
from conftest import PRUEBAS, REPO, escenario

ESCENARIO = "contador_reiniciado"
CAMPOS_GRADUACION = ("JobID", "JobName", "State", "Partition")


def crear_contexto(entorno, home, nombre=ESCENARIO, **kwargs):
    env = dict(entorno, SACCT_ESCENARIO=escenario(nombre))
    return at.Contexto(usuario="prueba", home=home, base=REPO, entorno=env, **kwargs)


# --- Números repetidos ------------------------------------------------------


def test_agrupar_no_mezcla_trabajos_con_el_mismo_numero():
    filas = [
        ["7", "nuevo"],
        ["7.batch", "paso del nuevo"],
        ["7", "fantasma"],
        ["7.batch", "paso del fantasma"],
        ["8.batch", "paso sin trabajo"],
    ]
    assert at.agrupar(filas) == [
        (["7", "nuevo"], [["7.batch", "paso del nuevo"]]),
        (["7", "fantasma"], [["7.batch", "paso del fantasma"]]),
    ]


def test_paralelo_hecho_no_lo_tapa_un_fantasma_con_su_numero(contexto):
    # Antes se juntaban por número: el fantasma (RUNNING, 8 núcleos, 245 días)
    # pisaba al trabajo bien hecho y la práctica quedaba pendiente.
    ok, clave, params = at.practica_paralelo(contexto(ESCENARIO))
    assert (ok, clave) == (True, "paralelo_ok")
    assert params["mejor"] == pytest.approx(70 / (20 * 4))


def test_memoria_con_un_fantasma_del_mismo_numero(contexto):
    assert at.practica_memoria(contexto(ESCENARIO)) == (True, "memoria_ok", {})


def test_buscar_trabajo_elige_el_mas_reciente(contexto):
    # Es lo que usará la graduación (V-07): el JOBID 52105 existe dos veces.
    trabajo, pasos = at.buscar_trabajo(contexto(ESCENARIO), "52105", CAMPOS_GRADUACION)
    assert trabajo["State"] == "COMPLETED"
    assert trabajo["Partition"] == "longjobs"
    assert trabajo["Submit"] == "2026-11-05T09:30:12"
    assert trabajo["fantasma"] is False
    assert [p["JobID"] for p in pasos] == ["52105.batch", "52105.extern"]


def test_buscar_trabajo_pide_todos_los_registros_del_usuario(contexto, llamadas_sacct):
    at.buscar_trabajo(contexto(ESCENARIO), "52105", CAMPOS_GRADUACION)
    (args,) = llamadas_sacct()
    assert args[args.index("-j") + 1] == "52105"
    assert "-D" in args
    assert args[args.index("-u") + 1] == "prueba"
    assert args[args.index("-o") + 1] == "JobID,JobName,State,Partition,Submit"


def test_buscar_trabajo_que_no_existe(contexto):
    assert at.buscar_trabajo(contexto(ESCENARIO), "999", CAMPOS_GRADUACION) is None


def test_buscar_trabajo_con_campos_vacios_de_apolo3(contexto):
    trabajo, pasos = at.buscar_trabajo(
        contexto("como_apolo3"), "104", at.CAMPOS_EFICIENCIA
    )
    assert trabajo["TotalCPU"] == ""
    assert all(p["MaxRSS"] == "" for p in pasos)


def test_buscar_trabajo_de_un_arreglo_pide_la_tarea(contexto):
    # sacct -j 52110 también trae las tareas 52110_1 y 52110_2: se busca la
    # que se pidió, como antes de la V-09.
    ctx = contexto(ESCENARIO)
    assert at.buscar_trabajo(ctx, "52110", CAMPOS_GRADUACION) is None
    trabajo, pasos = at.buscar_trabajo(ctx, "52110_2", CAMPOS_GRADUACION)
    assert trabajo["JobID"] == "52110_2"
    assert [p["JobID"] for p in pasos] == ["52110_2.batch"]


def test_eficiencia_de_un_numero_repetido(correr):
    r = correr("eficiencia", "52101", escenario=ESCENARIO)
    assert r.codigo == 0
    assert "Trabajo 52101 (curso-memoria): OUT_OF_MEMORY" in r.salida
    assert "Memoria máxima usada: 1024 MB" in r.salida

    r = correr("eficiencia", "52105", escenario=ESCENARIO)
    assert "Eficiencia de núcleos: 88%" in r.salida
    assert "Memoria máxima usada: 60 MB" in r.salida


def test_sacct_con_fechas_comparables(monkeypatch, home):
    # Submit se compara como texto: el formato no puede depender del usuario.
    recibido = {}

    def falso_run(cmd, **kwargs):
        recibido.update(kwargs["env"])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(at.subprocess, "run", falso_run)
    ctx = at.Contexto(
        usuario="prueba",
        home=home,
        base=REPO,
        entorno={"SLURM_TIME_FORMAT": "relative"},
    )
    ctx.sacct("-o", "JobID")
    assert recibido["SLURM_TIME_FORMAT"] == "standard"


# --- Fantasmas ----------------------------------------------------------------


def test_un_fantasma_no_cuenta_como_trabajo(contexto):
    ctx = contexto(ESCENARIO)
    assert at.trabajos(ctx, "curso-modulos") == []
    assert [t["estado"] for t in at.trabajos(ctx, "curso-memoria")] == [
        "OUT_OF_MEMORY",
        "COMPLETED",
    ]
    assert at.practica_modulos(ctx) == (False, "modulos_no", {})


def test_un_trabajo_que_slurm_si_tiene_no_es_fantasma(contexto):
    # 106 está corriendo de verdad: squeue lo da.
    estados = [
        t["estado"] for t in at.trabajos(contexto("todo_hecho"), "curso-paralelo")
    ]
    assert "RUNNING" in estados


def test_solo_un_running_puede_ser_fantasma(contexto):
    # squeue ya olvidó los trabajos terminados: eso no los vuelve fantasmas.
    # El 106 (RUNNING) sí, porque squeue tampoco lo tiene.
    ctx = contexto("todo_hecho", SQUEUE_VIVOS="")
    assert [t["estado"] for t in at.trabajos(ctx, "curso-paralelo")] == ["COMPLETED"]
    assert at.practica_paralelo(ctx)[0] is True


def test_si_squeue_falla_no_se_esconde_nada(contexto):
    ctx = contexto(ESCENARIO, SQUEUE_CODIGO="1")
    assert ctx.vivos() is None
    assert [t["estado"] for t in at.trabajos(ctx, "curso-modulos")] == ["RUNNING"]


def test_sin_squeue_no_se_esconde_nada(tmp_path, entorno, home):
    solo_sacct = tmp_path / "solo-sacct"
    solo_sacct.mkdir()
    os.symlink(os.path.join(PRUEBAS, "bin", "sacct"), str(solo_sacct / "sacct"))
    # El sacct simulado necesita python3; squeue no está en ninguna de las dos.
    ruta = str(solo_sacct) + os.pathsep + os.path.dirname(sys.executable)
    ctx = crear_contexto(dict(entorno, PATH=ruta), home)
    assert ctx.vivos() is None
    assert len(at.trabajos(ctx, "curso-modulos")) == 1


def test_squeue_se_consulta_una_vez_y_solo_si_hace_falta(contexto, llamadas_squeue):
    # Sin trabajos RUNNING no hace falta preguntarle a squeue.
    at.practica_modulos(contexto("todo_hecho"))
    assert llamadas_squeue() == []

    ctx = contexto(ESCENARIO)
    for practica in ("modulos", "memoria", "paralelo"):
        at.VERIFICADORES[practica](ctx)
    (args,) = llamadas_squeue()
    assert args[args.index("-u") + 1] == "prueba"
    assert args[args.index("-t") + 1] == "all"
    assert args[args.index("-o") + 1] == "%i"
    assert "-r" in args
    assert "-h" in args


def test_vivos_desde_afuera_para_el_reporte(entorno, home, llamadas_squeue):
    # La V-05 revisa a todos los usuarios como root: pasa el resultado de una
    # sola llamada a squeue y no se pregunta otra vez por cada usuario.
    ctx = crear_contexto(entorno, home, vivos=[])
    assert at.trabajos(ctx, "curso-modulos") == []
    assert at.practica_paralelo(ctx)[0] is True

    ctx = crear_contexto(entorno, home, vivos=["52100"])
    assert [t["estado"] for t in at.trabajos(ctx, "curso-modulos")] == ["RUNNING"]
    assert llamadas_squeue() == []


@pytest.mark.parametrize("idioma", ["es", "en"])
def test_eficiencia_de_un_fantasma(correr, idioma):
    r = correr("eficiencia", "52100", "--lang", idioma, escenario=ESCENARIO)
    assert r.codigo == 0
    assert at.texto(idioma, "efi_fantasma") in r.salida
    assert at.texto(idioma, "efi_espera") not in r.salida


def test_buscar_trabajo_marca_el_fantasma(contexto):
    trabajo, _ = at.buscar_trabajo(contexto(ESCENARIO), "52100", CAMPOS_GRADUACION)
    assert trabajo["State"] == "RUNNING"
    assert trabajo["fantasma"] is True
