"""P-05: mensajes de Apolo III y eficiencia sin registro de uso.

Apolo III hoy no limita la memoria ni registra TotalCPU ni MaxRSS (A-03). El
perfil del usuario (APOLO_TRAINING_CLUSTER) solo elige el texto del mensaje;
nunca cambia si una práctica se aprueba.
"""

import importlib.util
import os

import pytest

RUTA = os.path.join(os.path.dirname(__file__), os.pardir, "apolo_training.py")


@pytest.fixture(scope="module")
def at():
    spec = importlib.util.spec_from_file_location("apolo_training_p05", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


# Filas de sacct -P como las de las prácticas: JobID|State|AllocCPUS|Elapsed|TotalCPU
SIN_REGISTRO = {
    "curso-memoria": [
        ["101", "COMPLETED", "1", "00:00:20", "00:00:00"],
        ["101.batch", "COMPLETED", "1", "00:00:20", "00:00:00"],
    ],
    "curso-nucleos": [
        ["102", "COMPLETED", "4", "00:00:40", "00:00:00"],
        ["102.batch", "COMPLETED", "4", "00:00:40", "00:00:00"],
    ],
    "curso-paralelo": [
        ["103", "COMPLETED", "4", "00:00:12", "00:00:00"],
        ["103.batch", "COMPLETED", "4", "00:00:12", "00:00:00"],
    ],
}

# Filas de eficiencia: JobID|JobName|State|AllocCPUS|Elapsed|TotalCPU|MaxRSS|ReqMem
EFICIENCIA = {
    # Apolo III: FAILED tras 5 minutos, sin TotalCPU ni MaxRSS
    "201": [
        ["201", "mi-trabajo", "FAILED", "2", "00:05:00", "00:00:00", "", "1024M"],
        ["201.batch", "batch", "FAILED", "2", "00:05:00", "00:00:00", "", ""],
    ],
    # Apolo III: TIMEOUT, el caso más común
    "202": [
        ["202", "mi-trabajo", "TIMEOUT", "4", "02:00:00", "00:00:00", "", "4096M"],
        ["202.batch", "batch", "CANCELLED", "4", "02:00:00", "00:00:00", "", ""],
    ],
    # Apolo II: casi sin CPU (un sleep), pero con MaxRSS: sí hay registro
    "203": [
        ["203", "espera", "COMPLETED", "1", "00:01:00", "00:00:00", "", "1024M"],
        ["203.batch", "batch", "COMPLETED", "1", "00:01:00", "00:00:00", "2.10M", ""],
    ],
    # Cancelado antes de correr
    "204": [
        [
            "204",
            "mi-trabajo",
            "CANCELLED by 1000",
            "2",
            "00:00:00",
            "00:00:00",
            "",
            "1024M",
        ],
    ],
    # Apolo II: FAILED con datos reales
    "205": [
        ["205", "mi-trabajo", "FAILED", "2", "00:00:30", "00:00:30", "", "1024M"],
        ["205.batch", "batch", "FAILED", "2", "00:00:30", "00:00:30", "210.50M", ""],
    ],
}


def contexto(at, tmp_path, cluster_env=None, cluster=None, filas=None):
    entorno = {}
    if cluster_env is not None:
        entorno["APOLO_TRAINING_CLUSTER"] = cluster_env
    ctx = at.Contexto(
        usuario="ana",
        home=str(tmp_path),
        base=str(tmp_path),
        entorno=entorno,
        cluster=cluster,
    )

    def sacct(*args):
        nombre = [a.split("=", 1)[1] for a in args if a.startswith("--name=")]
        if nombre:
            return [list(f) for f in (filas or SIN_REGISTRO).get(nombre[0], [])]
        jobid = args[args.index("-j") + 1]
        return [list(f) for f in EFICIENCIA.get(jobid, [])]

    ctx.sacct = sacct
    return ctx


# --- El perfil en el Contexto ---------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("apolo3", "apolo3"),
        (" APOLO3\n", "apolo3"),
        ("apolo2", "apolo2"),
        ("", None),
        ("apolo4", None),
    ],
)
def test_cluster_desde_la_variable(at, tmp_path, valor, esperado):
    assert contexto(at, tmp_path, cluster_env=valor).cluster == esperado


def test_cluster_sin_variable(at, tmp_path):
    assert contexto(at, tmp_path).cluster is None


def test_cluster_explicito_manda_sobre_la_variable(at, tmp_path):
    # La V-05 verifica como root: pasa el perfil leído de /etc/apolo-training/usuarios/
    ctx = contexto(at, tmp_path, cluster_env="apolo2", cluster="apolo3")
    assert ctx.cluster == "apolo3"


# --- Prácticas: el perfil cambia el texto, no el resultado ---------------


@pytest.mark.parametrize(
    ("practica", "generico"),
    [
        ("memoria", "memoria_sin_limite"),
        ("nucleos", "sin_datos"),
        ("paralelo", "sin_datos"),
    ],
)
@pytest.mark.parametrize("cluster", ["apolo2", None])
def test_sin_apolo3_queda_el_mensaje_de_siempre(
    at, tmp_path, practica, generico, cluster
):
    ok, clave, _ = at.VERIFICADORES[practica](contexto(at, tmp_path, cluster=cluster))
    assert (ok, clave) == (False, generico)


@pytest.mark.parametrize(
    ("practica", "clave_apolo3"),
    [
        ("memoria", "memoria_sin_limite_apolo3"),
        ("nucleos", "sin_datos_apolo3"),
        ("paralelo", "sin_datos_apolo3"),
    ],
)
def test_apolo3_explica_la_diferencia(at, tmp_path, practica, clave_apolo3):
    ok, clave, _ = at.VERIFICADORES[practica](contexto(at, tmp_path, cluster="apolo3"))
    assert (ok, clave) == (False, clave_apolo3)


def test_apolo3_no_cambia_una_practica_aprobada(at, tmp_path):
    filas = {
        "curso-memoria": [
            ["111", "OUT_OF_MEMORY", "1", "00:00:05", "00:00:04"],
            ["111.batch", "OUT_OF_MEMORY", "1", "00:00:05", "00:00:04"],
            ["112", "COMPLETED", "1", "00:00:20", "00:00:19"],
            ["112.batch", "COMPLETED", "1", "00:00:20", "00:00:19"],
        ]
    }
    ctx = contexto(at, tmp_path, cluster="apolo3", filas=filas)
    assert at.VERIFICADORES["memoria"](ctx) == (True, "memoria_ok", {})


@pytest.mark.parametrize("idioma", ["es", "en"])
@pytest.mark.parametrize(
    "clave", ["memoria_sin_limite_apolo3", "sin_datos_apolo3", "efi_sin_datos_apolo3"]
)
def test_textos_de_apolo3_cubren_los_dos_lugares(at, idioma, clave):
    # Un usuario apolo3 también usa la VM: el texto no puede darle la razón
    # a Apolo III si está en la VM.
    texto = at.texto(idioma, clave)
    assert "Apolo III" in texto
    assert ("VM" if idioma == "es" else "practice machine") in texto


# --- eficiencia -----------------------------------------------------------


def salida_eficiencia(at, tmp_path, capsys, jobid, cluster=None, idioma="es"):
    ctx = contexto(at, tmp_path, cluster=cluster)
    assert at.reporte_eficiencia(ctx, idioma, jobid) == 0
    return capsys.readouterr().out


@pytest.mark.parametrize("jobid", ["201", "202"])
@pytest.mark.parametrize("idioma", ["es", "en"])
def test_eficiencia_apolo3_sin_registro_aunque_no_termine_bien(
    at, tmp_path, capsys, jobid, idioma
):
    salida = salida_eficiencia(
        at, tmp_path, capsys, jobid, cluster="apolo3", idioma=idioma
    )
    assert at.texto(idioma, "efi_sin_datos_apolo3") in salida
    assert "0%" not in salida
    assert "0 MB" not in salida


def test_eficiencia_sin_registro_sin_perfil(at, tmp_path, capsys):
    salida = salida_eficiencia(at, tmp_path, capsys, "201")
    assert at.texto("es", "sin_datos") in salida


def test_eficiencia_poco_cpu_con_maxrss_si_se_mide(at, tmp_path, capsys):
    salida = salida_eficiencia(at, tmp_path, capsys, "203", cluster="apolo2")
    assert "Eficiencia de núcleos: 0%" in salida
    assert at.texto("es", "sin_datos") not in salida


def test_eficiencia_fallido_con_datos_se_mide(at, tmp_path, capsys):
    salida = salida_eficiencia(at, tmp_path, capsys, "205", cluster="apolo2")
    assert "Eficiencia de núcleos: 50%" in salida
    assert "Memoria máxima usada: 210 MB" in salida


@pytest.mark.parametrize("cluster", ["apolo2", "apolo3", None])
def test_eficiencia_trabajo_que_no_corrio(at, tmp_path, capsys, cluster):
    salida = salida_eficiencia(at, tmp_path, capsys, "204", cluster=cluster)
    assert at.texto("es", "efi_corto") in salida
    assert "0%" not in salida
