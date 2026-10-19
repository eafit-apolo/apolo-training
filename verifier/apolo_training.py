#!/usr/bin/env python3
"""apolo-training: verifica las prácticas del curso de inducción de Apolo.

Funciona con Python 3.6 o superior y solo usa la biblioteca estándar.
Lee el historial de Slurm (sacct) del propio usuario y los archivos de su
carpeta ~/apolo-training; no necesita permisos especiales.

Cada práctica es una función que recibe un Contexto (usuario, HOME, material)
y devuelve (aprobada, clave_del_mensaje, parámetros). Así la puede reusar el
reporte de la plataforma sin depender del idioma ni de la salida en pantalla.
"""

import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys

VENTANA = "now-30days"
IDIOMAS = ("es", "en")
VARIABLE_IDIOMA = "APOLO_TRAINING_LANG"
VARIABLE_BASE = "APOLO_TRAINING"
VARIABLE_CLUSTER = "APOLO_TRAINING_CLUSTER"
CLUSTERS = ("apolo2", "apolo3")
CARPETA = "apolo-training"
NO_COPIAR = ("README.md",)  # documentación del repositorio, no del curso
PATRON_CLAVE = re.compile(r"TRN-[A-Z0-9]{4}-[A-Z0-9]{4}")
PATRON_CODIGO = re.compile(r"ARC-[0-9A-F]{6}")
PATRON_JOBID = re.compile(r"^[0-9]+(_[0-9]+)?$")

PRACTICAS = (
    "conexion",
    "terminal",
    "archivos",
    "modulos",
    "memoria",
    "nucleos",
    "paralelo",
)

MENSAJES = {
    "es": {
        "ayuda": (
            "apolo-training: verifica las prácticas del curso de inducción de Apolo.\n"
            "\n"
            "Uso:\n"
            "  apolo-training preparar             copia el material del curso"
            " a ~/apolo-training\n"
            "  apolo-training verificar PRÁCTICA   revisa una práctica\n"
            "  apolo-training progreso             muestra qué prácticas llevas"
            " aprobadas\n"
            "  apolo-training eficiencia JOBID     cuánto de lo reservado usó"
            " un trabajo\n"
            "  apolo-training ayuda                muestra esta ayuda\n"
            "\n"
            "Prácticas: {practicas}\n"
            "\n"
            "Idioma: español por defecto. Para inglés, agrega --lang en a"
            " cualquier comando,\n"
            "o déjalo fijo con: export APOLO_TRAINING_LANG=en"
        ),
        "aprobado": "[APROBADO]",
        "pendiente": "[PENDIENTE]",
        "progreso_aprobado": "aprobado",
        "progreso_pendiente": "pendiente",
        # Errores de uso
        "comando_desconocido": (
            "No conozco «{comando}». Mira la ayuda con: apolo-training ayuda"
        ),
        "falta_practica": (
            "Indica qué práctica verificar: apolo-training verificar PRÁCTICA\n"
            "Prácticas: {practicas}"
        ),
        "practica_desconocida": (
            "No conozco la práctica «{practica}». Las prácticas son: {practicas}"
        ),
        "idioma_desconocido": "Idioma no soportado: «{valor}». Usa es o en.",
        "jobid_invalido": (
            "Indica el número del trabajo, por ejemplo: apolo-training eficiencia 1234"
        ),
        "sacct_no_existe": (
            "No encuentro el comando sacct. Usa apolo-training en la máquina de"
            " práctica o en un clúster con Slurm."
        ),
        "sacct_fallo": (
            "sacct terminó con un error (código {codigo}). Intenta de nuevo en un"
            " minuto; si sigue fallando, avísale al equipo de Apolo."
        ),
        "material_no_existe": (
            "No encuentro el material del curso en {ruta}."
            " ¿Cargaste el módulo? module load apolo-training"
        ),
        "material_incompleto": (
            "El material del curso en {ruta} está incompleto."
            " Avísale al equipo de Apolo."
        ),
        # preparar
        "preparar_ok": "Listo: el material del curso quedó en {destino}",
        "preparar_restaurado": (
            "Restauré {n} archivo(s) que faltaban en {destino}; no toqué los demás."
        ),
        "preparar_existe": "Ya tenías el material en {destino}; no toqué tus archivos.",
        "preparar_ida": "Generé {ida} con tu código para la práctica de archivos.",
        # conexion
        "conexion_ok": "Estás conectado por SSH a la máquina de práctica.",
        "conexion_no": (
            "No veo una sesión SSH. Conéctate con ssh (o desde la terminal de la"
            " plataforma) y vuelve a correr este comando."
        ),
        # terminal y archivos
        "sin_carpeta": (
            "No encuentro {carpeta}. Primero corre: apolo-training preparar"
        ),
        "terminal_sin_respuesta": (
            "Aún no veo {respuesta}. Busca la clave dentro de {datos}"
            " y guárdala en ese archivo."
        ),
        "terminal_no": (
            "{respuesta} no tiene la clave correcta. Sigue buscando en {datos};"
            " grep -r te puede ayudar."
        ),
        "terminal_ok": "Encontraste la clave y la guardaste bien.",
        "archivos_sin_ida": "No encuentro {ida}. Corre: apolo-training preparar",
        "archivos_sin_vuelta": (
            "Descarga {ida} a tu computador, cámbiale el nombre a vuelta.txt"
            " y súbelo a {carpeta}"
        ),
        "archivos_no": (
            "{vuelta} no tiene el código de tu ida.txt. Sube el mismo archivo"
            " que descargaste, solo con el nombre cambiado."
        ),
        "archivos_ok": (
            "Descargaste y subiste el archivo: ya sabes mover archivos entre tu"
            " computador y el clúster."
        ),
        # Slurm
        "sin_datos": (
            "Este clúster no está guardando el uso real de CPU, así que no puedo"
            " medir la eficiencia. Avísale al equipo de Apolo."
        ),
        "sin_datos_apolo3": (
            "No hay datos del uso real de CPU de tu trabajo. Si estás en Apolo III,"
            " es normal: hoy no lo registra, así que este laboratorio se hace en la"
            " VM de práctica. Si estás en la VM, avísale al equipo de Apolo."
        ),
        "modulos_ok": "Tu programa encontró numpy: cargaste bien el módulo.",
        "modulos_no": (
            "No veo un trabajo 'curso-modulos' completado."
            " ¿Descomentaste la línea module load?"
        ),
        "memoria_ok": "Viste a Slurm detener tu trabajo por memoria y lo corregiste.",
        "memoria_fallo": (
            "Ya lo viste fallar por memoria; ahora sube --mem y vuelve a enviarlo."
        ),
        "memoria_sin_limite": (
            "Tu trabajo terminó sin que Slurm lo detuviera. Si lo enviaste con"
            " --mem=1G, este clúster no está limitando la memoria: avísale al"
            " equipo de Apolo."
        ),
        "memoria_sin_limite_apolo3": (
            "Tu trabajo terminó sin que Slurm lo detuviera. Si estás en Apolo III,"
            " es normal: hoy no limita la memoria, así que este laboratorio se hace"
            " en la VM de práctica. Si estás en la VM, envíalo primero con"
            " --mem=1G y deja que falle."
        ),
        "memoria_no": "Primero envía 'curso-memoria' con --mem=1G y deja que falle.",
        "nucleos_ok": (
            "Comprobaste que reservar más núcleos no acelera un programa de un"
            " solo proceso."
        ),
        "nucleos_no": (
            "Envía 'curso-nucleos' reservando 4 núcleos o más con un solo proceso,"
            " y revisa su eficiencia con 'apolo-training eficiencia JOBID'."
        ),
        "paralelo_ok": (
            "Tu trabajo en paralelo aprovechó el {mejor:.0%} de los núcleos reservados."
        ),
        "paralelo_no": (
            "Aún no veo un 'curso-paralelo' que use bien sus núcleos"
            " (mejor: {mejor:.0%})."
        ),
        # eficiencia
        "efi_no_encontrado": (
            "No encuentro el trabajo {jobid} entre tus trabajos de los últimos 30 días."
        ),
        "efi_trabajo": "Trabajo {jobid} ({nombre}): {estado}",
        "efi_reserva": "Núcleos reservados: {cpus} | Duración: {duracion}",
        "efi_espera": "Espera a que termine para ver su eficiencia.",
        "efi_corto": (
            "El trabajo no llegó a correr o duró menos de 2 segundos: es muy poco"
            " para medir su eficiencia."
        ),
        "efi_sin_datos_apolo3": (
            "No hay datos del uso real de CPU ni de memoria de este trabajo. Si"
            " estás en Apolo III, es normal: hoy no los registra, así que no puedo"
            " medir su eficiencia. Si estás en la VM, avísale al equipo de Apolo."
        ),
        "efi_nucleos": (
            "Eficiencia de núcleos: {eficiencia:.0%}"
            " (usó el equivalente a {usados:.1f} de {cpus} núcleos)"
        ),
        "efi_memoria": "Memoria máxima usada: {memoria:.0f} MB (pedida: {pedida})",
    },
    "en": {
        "ayuda": (
            "apolo-training: checks the practice tasks of the Apolo induction"
            " course.\n"
            "\n"
            "Usage:\n"
            "  apolo-training preparar             copies the course material"
            " to ~/apolo-training\n"
            "  apolo-training verificar PRACTICE   checks one practice task\n"
            "  apolo-training progreso             shows which practice tasks"
            " you have passed\n"
            "  apolo-training eficiencia JOBID     how much of its reservation"
            " a job used\n"
            "  apolo-training ayuda                shows this help\n"
            "\n"
            "Practice tasks: {practicas}\n"
            "\n"
            "Language: Spanish by default. For English, add --lang en to any"
            " command,\n"
            "or make it permanent with: export APOLO_TRAINING_LANG=en"
        ),
        "aprobado": "[PASSED]",
        "pendiente": "[PENDING]",
        "progreso_aprobado": "passed",
        "progreso_pendiente": "pending",
        "comando_desconocido": (
            "Unknown command «{comando}». See the help with: apolo-training ayuda"
        ),
        "falta_practica": (
            "Say which practice task to check: apolo-training verificar PRACTICE\n"
            "Practice tasks: {practicas}"
        ),
        "practica_desconocida": (
            "Unknown practice task «{practica}». The practice tasks are: {practicas}"
        ),
        "idioma_desconocido": "Unsupported language: «{valor}». Use es or en.",
        "jobid_invalido": (
            "Give the job number, for example: apolo-training eficiencia 1234"
        ),
        "sacct_no_existe": (
            "The sacct command was not found. Use apolo-training on the practice"
            " machine or on a cluster with Slurm."
        ),
        "sacct_fallo": (
            "sacct ended with an error (code {codigo}). Try again in a minute;"
            " if it keeps failing, tell the Apolo team."
        ),
        "material_no_existe": (
            "The course material was not found in {ruta}."
            " Did you load the module? module load apolo-training"
        ),
        "material_incompleto": (
            "The course material in {ruta} is incomplete. Tell the Apolo team."
        ),
        "preparar_ok": "Done: the course material is in {destino}",
        "preparar_restaurado": (
            "Restored {n} missing file(s) in {destino}; your other files were"
            " not touched."
        ),
        "preparar_existe": (
            "You already had the material in {destino}; your files were not touched."
        ),
        "preparar_ida": "Created {ida} with your code for the file transfer task.",
        "conexion_ok": "You are connected to the practice machine over SSH.",
        "conexion_no": (
            "No SSH session found. Connect with ssh (or from the platform's"
            " terminal) and run this command again."
        ),
        "sin_carpeta": "{carpeta} was not found. First run: apolo-training preparar",
        "terminal_sin_respuesta": (
            "{respuesta} does not exist yet. Look for the course code inside"
            " {datos} and save it in that file."
        ),
        "terminal_no": (
            "{respuesta} does not have the right code. Keep looking in {datos};"
            " grep -r can help."
        ),
        "terminal_ok": "You found the code and saved it correctly.",
        "archivos_sin_ida": "{ida} was not found. Run: apolo-training preparar",
        "archivos_sin_vuelta": (
            "Download {ida} to your computer, rename it to vuelta.txt"
            " and upload it to {carpeta}"
        ),
        "archivos_no": (
            "{vuelta} does not have the code from your ida.txt. Upload the same"
            " file you downloaded, only renamed."
        ),
        "archivos_ok": (
            "You downloaded and uploaded the file: you can now move files between"
            " your computer and the cluster."
        ),
        "sin_datos": (
            "This cluster is not recording real CPU usage, so efficiency cannot"
            " be measured. Tell the Apolo team."
        ),
        "sin_datos_apolo3": (
            "There is no data on your job's real CPU usage. If you are on Apolo III,"
            " this is expected: it does not record it yet, so this lab is done on"
            " the practice machine. If you are on the practice machine, tell the"
            " Apolo team."
        ),
        "modulos_ok": "Your program found numpy: you loaded the module correctly.",
        "modulos_no": (
            "No completed 'curso-modulos' job found."
            " Did you uncomment the module load line?"
        ),
        "memoria_ok": "You saw Slurm stop your job for memory and you fixed it.",
        "memoria_fallo": (
            "You saw it fail for memory; now raise --mem and submit it again."
        ),
        "memoria_sin_limite": (
            "Your job finished without Slurm stopping it. If you submitted it"
            " with --mem=1G, this cluster is not limiting memory: tell the"
            " Apolo team."
        ),
        "memoria_sin_limite_apolo3": (
            "Your job finished without Slurm stopping it. If you are on Apolo III,"
            " this is expected: it does not limit memory yet, so this lab is done on"
            " the practice machine. If you are on the practice machine, first submit"
            " it with --mem=1G and let it fail."
        ),
        "memoria_no": "First submit 'curso-memoria' with --mem=1G and let it fail.",
        "nucleos_ok": (
            "You checked that reserving more cores does not speed up a"
            " single-process program."
        ),
        "nucleos_no": (
            "Submit 'curso-nucleos' reserving 4 or more cores with a single"
            " process, and check its efficiency with"
            " 'apolo-training eficiencia JOBID'."
        ),
        "paralelo_ok": ("Your parallel job used {mejor:.0%} of the cores it reserved."),
        "paralelo_no": (
            "No 'curso-paralelo' job that uses its cores well yet (best: {mejor:.0%})."
        ),
        "efi_no_encontrado": (
            "Job {jobid} was not found among your jobs of the last 30 days."
        ),
        "efi_trabajo": "Job {jobid} ({nombre}): {estado}",
        "efi_reserva": "Reserved cores: {cpus} | Duration: {duracion}",
        "efi_espera": "Wait for it to finish to see its efficiency.",
        "efi_corto": (
            "The job did not run or lasted less than 2 seconds: too short to"
            " measure its efficiency."
        ),
        "efi_sin_datos_apolo3": (
            "There is no data on this job's real CPU or memory usage. If you are on"
            " Apolo III, this is expected: it does not record them yet, so its"
            " efficiency cannot be measured. If you are on the practice machine,"
            " tell the Apolo team."
        ),
        "efi_nucleos": (
            "Core efficiency: {eficiencia:.0%}"
            " (it used the equivalent of {usados:.1f} of {cpus} cores)"
        ),
        "efi_memoria": "Peak memory used: {memoria:.0f} MB (requested: {pedida})",
    },
}


class ErrorUso(Exception):
    """Error que se le muestra al usuario con un mensaje traducido."""

    def __init__(self, clave, **params):
        super().__init__(clave)
        self.clave = clave
        self.params = params


def texto(idioma, clave, **params):
    return MENSAJES[idioma][clave].format(**params)


def ruta_base(entorno):
    """Carpeta de instalación: $APOLO_TRAINING o, si no está, la del script."""
    base = entorno.get(VARIABLE_BASE)
    if base:
        return base
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class Contexto:
    """De quién se verifican las prácticas y dónde está el material.

    cluster es el perfil del usuario (apolo2 o apolo3, o None si no se sabe).
    Solo elige el texto de algunos mensajes; nunca cambia si una práctica se
    aprueba. Por defecto sale de APOLO_TRAINING_CLUSTER; quien verifica como
    root a otro usuario (el reporte de la V-05) debe pasarlo explícito.
    """

    def __init__(self, usuario=None, home=None, base=None, entorno=None, cluster=None):
        self.entorno = os.environ if entorno is None else entorno
        self.usuario = usuario or getpass.getuser()
        self.home = home or os.path.expanduser("~")
        self.base = base or ruta_base(self.entorno)
        if cluster is None:
            cluster = self.entorno.get(VARIABLE_CLUSTER, "")
        cluster = cluster.strip().lower()
        self.cluster = cluster if cluster in CLUSTERS else None

    @property
    def apolo3(self):
        return self.cluster == "apolo3"

    @property
    def material(self):
        return os.path.join(self.base, "labs")

    @property
    def carpeta(self):
        return os.path.join(self.home, CARPETA)

    def corta(self, ruta):
        """Muestra la ruta con ~ en lugar del HOME completo."""
        if ruta == self.home or ruta.startswith(self.home + os.sep):
            return "~" + ruta[len(self.home) :]
        return ruta

    def sacct(self, *args):
        cmd = ["sacct", "-n", "-P", "-u", self.usuario, "-S", VENTANA] + list(args)
        try:
            proceso = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=dict(self.entorno),
                check=False,
            )
        except OSError:
            raise ErrorUso("sacct_no_existe")
        if proceso.returncode != 0:
            raise ErrorUso("sacct_fallo", codigo=proceso.returncode)
        return [linea.split("|") for linea in proceso.stdout.splitlines() if linea]


# --- Utilidades de sacct --------------------------------------------------


def segundos(t):
    """Convierte '[D-][HH:]MM:SS[.mmm]' (formato de sacct) a segundos."""
    if not t or t in ("INVALID", "Unknown"):
        return 0.0
    dias = 0
    if "-" in t:
        d, t = t.split("-", 1)
        dias = int(d)
    partes = [float(p) for p in t.split(":")]
    while len(partes) < 3:
        partes.insert(0, 0.0)
    h, m, s = partes
    return dias * 86400 + h * 3600 + m * 60 + s


def megas(v):
    """Memoria de sacct pedida con --units=M, p. ej. '210.50M' -> 210.5."""
    v = v.strip().rstrip("KMGTPnc")
    return float(v) if v else 0.0


def trabajos(ctx, nombre):
    """Trabajos con ese nombre, agrupando cada trabajo con sus pasos."""
    res = {}
    for jobid, estado, cpus, elapsed, totalcpu in ctx.sacct(
        "--name=" + nombre, "-o", "JobID,State,AllocCPUS,Elapsed,TotalCPU"
    ):
        t = res.setdefault(
            jobid.split(".")[0],
            {
                "estado": "",
                "estados": [],
                "cpus": 0,
                "elapsed": 0.0,
                "cpu_pasos": 0.0,
                "cpu_trabajo": 0.0,
            },
        )
        est = estado.split()[0] if estado else ""
        t["estados"].append(est)
        if "." in jobid:
            t["cpu_pasos"] += segundos(totalcpu)
        else:
            t["estado"] = est
            t["cpus"] = int(cpus or 0)
            t["elapsed"] = segundos(elapsed)
            t["cpu_trabajo"] = segundos(totalcpu)
    return list(res.values())


def uso_cpu(t):
    return t["cpu_pasos"] or t["cpu_trabajo"]


def eficiencia(t):
    """Fracción de los núcleos reservados que el trabajo usó de verdad."""
    reservado = t["elapsed"] * t["cpus"]
    return uso_cpu(t) / reservado if reservado else 0.0


def sin_datos(t):
    """Terminó bien, corrió unos segundos y no registró CPU: el clúster no mide
    el uso (hoy pasa en Apolo III, P-05)."""
    return t["estado"] == "COMPLETED" and t["elapsed"] >= 2 and uso_cpu(t) == 0


# --- Prácticas -----------------------------------------------------------


def practica_conexion(ctx):
    """Cualquier sesión SSH en la máquina de práctica aprueba.

    La terminal de la plataforma también entra por SSH, así que no se distingue.
    """
    if ctx.entorno.get("SSH_CONNECTION") or ctx.entorno.get("SSH_CLIENT"):
        return True, "conexion_ok", {}
    return False, "conexion_no", {}


def clave_original(ctx):
    """La clave escondida en el material original (la única que coincide)."""
    datos = os.path.join(ctx.material, "terminal", "datos")
    encontradas = set()
    for raiz, _, archivos in os.walk(datos):
        for nombre in archivos:
            with open(os.path.join(raiz, nombre), encoding="utf-8") as f:
                encontradas.update(PATRON_CLAVE.findall(f.read()))
    if len(encontradas) != 1:
        raise ErrorUso("material_incompleto", ruta=ctx.material)
    return encontradas.pop()


def practica_terminal(ctx):
    carpeta = os.path.join(ctx.carpeta, "terminal")
    if not os.path.isdir(carpeta):
        return False, "sin_carpeta", {"carpeta": ctx.corta(ctx.carpeta)}
    respuesta = os.path.join(carpeta, "respuesta.txt")
    params = {
        "respuesta": ctx.corta(respuesta),
        "datos": ctx.corta(os.path.join(carpeta, "datos")),
    }
    if not os.path.isfile(respuesta):
        return False, "terminal_sin_respuesta", params
    with open(respuesta, encoding="utf-8", errors="replace") as f:
        contenido = f.read().upper()
    if clave_original(ctx) in contenido:
        return True, "terminal_ok", {}
    return False, "terminal_no", params


def practica_archivos(ctx):
    carpeta = os.path.join(ctx.carpeta, "archivos")
    ida = os.path.join(carpeta, "ida.txt")
    vuelta = os.path.join(carpeta, "vuelta.txt")
    params = {
        "ida": ctx.corta(ida),
        "vuelta": ctx.corta(vuelta),
        "carpeta": ctx.corta(carpeta) + "/",
    }
    if not os.path.isfile(ida):
        return False, "archivos_sin_ida", params
    with open(ida, encoding="utf-8", errors="replace") as f:
        codigo = PATRON_CODIGO.search(f.read())
    if not codigo:
        return False, "archivos_sin_ida", params
    if not os.path.isfile(vuelta):
        return False, "archivos_sin_vuelta", params
    with open(vuelta, encoding="utf-8", errors="replace") as f:
        if codigo.group(0) in f.read().upper():
            return True, "archivos_ok", {}
    return False, "archivos_no", params


def practica_modulos(ctx):
    if any(t["estado"] == "COMPLETED" for t in trabajos(ctx, "curso-modulos")):
        return True, "modulos_ok", {}
    return False, "modulos_no", {}


def practica_memoria(ctx):
    ts = trabajos(ctx, "curso-memoria")
    fallo = any("OUT_OF_MEMORY" in t["estados"] for t in ts)
    arreglo = any(t["estado"] == "COMPLETED" for t in ts)
    if fallo and arreglo:
        return True, "memoria_ok", {}
    if fallo:
        return False, "memoria_fallo", {}
    if arreglo:
        # En Apolo III es lo esperado (no limita la memoria); en la VM o en
        # Apolo II, o el usuario se saltó el --mem=1G o algo se rompió.
        if ctx.apolo3:
            return False, "memoria_sin_limite_apolo3", {}
        return False, "memoria_sin_limite", {}
    return False, "memoria_no", {}


def clave_sin_datos(ctx):
    """En Apolo III es lo esperado; en la VM o en Apolo II, algo se rompió."""
    return "sin_datos_apolo3" if ctx.apolo3 else "sin_datos"


def practica_nucleos(ctx):
    ts = [
        t
        for t in trabajos(ctx, "curso-nucleos")
        if t["estado"] == "COMPLETED" and t["cpus"] >= 4
    ]
    if any(uso_cpu(t) > 0 and eficiencia(t) < 0.5 for t in ts):
        return True, "nucleos_ok", {}
    if any(sin_datos(t) for t in ts):
        return False, clave_sin_datos(ctx), {}
    return False, "nucleos_no", {}


def practica_paralelo(ctx):
    ts = [
        t
        for t in trabajos(ctx, "curso-paralelo")
        if t["estado"] == "COMPLETED" and t["cpus"] >= 4
    ]
    mejor = max((eficiencia(t) for t in ts), default=0.0)
    if mejor >= 0.5:
        return True, "paralelo_ok", {"mejor": mejor}
    if ts and all(sin_datos(t) for t in ts):
        return False, clave_sin_datos(ctx), {}
    return False, "paralelo_no", {"mejor": mejor}


VERIFICADORES = {
    "conexion": practica_conexion,
    "terminal": practica_terminal,
    "archivos": practica_archivos,
    "modulos": practica_modulos,
    "memoria": practica_memoria,
    "nucleos": practica_nucleos,
    "paralelo": practica_paralelo,
}


# --- preparar ------------------------------------------------------------


def copiar_faltantes(origen, destino):
    """Copia el material sin sobrescribir lo que el usuario ya tiene."""
    copiados = 0
    for raiz, _, archivos in os.walk(origen):
        relativa = os.path.relpath(raiz, origen)
        carpeta = os.path.normpath(os.path.join(destino, relativa))
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta)
        for nombre in archivos:
            if relativa == "." and nombre in NO_COPIAR:
                continue
            final = os.path.join(carpeta, nombre)
            if os.path.lexists(final):
                continue
            # copyfile no copia permisos: los archivos quedan editables para el
            # usuario aunque el material instalado sea de solo lectura.
            shutil.copyfile(os.path.join(raiz, nombre), final)
            if nombre.endswith(".sh"):
                os.chmod(final, 0o755)
            copiados += 1
    return copiados


def preparar(ctx):
    """Deja el material en ~/apolo-training y genera ida.txt. Devuelve mensajes."""
    if not os.path.isdir(ctx.material):
        raise ErrorUso("material_no_existe", ruta=ctx.material)
    existia = os.path.isdir(ctx.carpeta)
    copiados = copiar_faltantes(ctx.material, ctx.carpeta)
    destino = ctx.corta(ctx.carpeta)
    if not existia:
        mensajes = [("preparar_ok", {"destino": destino})]
    elif copiados:
        mensajes = [("preparar_restaurado", {"n": copiados, "destino": destino})]
    else:
        mensajes = [("preparar_existe", {"destino": destino})]

    ida = os.path.join(ctx.carpeta, "archivos", "ida.txt")
    if not os.path.exists(ida):
        if not os.path.isdir(os.path.dirname(ida)):
            os.makedirs(os.path.dirname(ida))
        codigo = "ARC-" + secrets.token_hex(3).upper()
        with open(ida, "w", encoding="utf-8") as f:
            f.write(
                "Apolo training: práctica de archivos / file transfer practice\n"
                f"código / code: {codigo}\n"
            )
        mensajes.append(("preparar_ida", {"ida": ctx.corta(ida)}))
    return mensajes


# --- eficiencia ----------------------------------------------------------


def reporte_eficiencia(ctx, idioma, jobid):
    """Resumen al estilo de seff: cuánto de lo reservado usó el trabajo."""
    filas = ctx.sacct(
        "-j",
        jobid,
        "--units=M",
        "-o",
        "JobID,JobName,State,AllocCPUS,Elapsed,TotalCPU,MaxRSS,ReqMem",
    )
    trabajo = [f for f in filas if f[0] == jobid]
    if not trabajo:
        print(texto(idioma, "efi_no_encontrado", jobid=jobid))
        return 1
    _, nombre, estado, cpus, elapsed, totalcpu, _, reqmem = trabajo[0]
    pasos = [f for f in filas if f[0].startswith(jobid + ".")]
    t = {
        "estado": estado.split()[0] if estado else "",
        "cpus": int(cpus or 0),
        "elapsed": segundos(elapsed),
        "cpu_pasos": sum(segundos(f[5]) for f in pasos),
        "cpu_trabajo": segundos(totalcpu),
    }
    memoria = max([megas(f[6]) for f in pasos] or [0.0])

    print(texto(idioma, "efi_trabajo", jobid=jobid, nombre=nombre, estado=estado))
    print(texto(idioma, "efi_reserva", cpus=t["cpus"], duracion=elapsed))
    if t["estado"] in ("RUNNING", "PENDING"):
        print(texto(idioma, "efi_espera"))
    elif t["elapsed"] < 2:
        print(texto(idioma, "efi_corto"))
    elif uso_cpu(t) == 0 and memoria == 0:
        # Sin CPU ni MaxRSS en ningún paso, termine como termine: el clúster no
        # registra el uso. Un trabajo de Apolo II que casi no usó CPU sí trae MaxRSS.
        clave = "efi_sin_datos_apolo3" if ctx.apolo3 else "sin_datos"
        print(texto(idioma, clave))
    else:
        usados = uso_cpu(t) / t["elapsed"] if t["elapsed"] else 0.0
        print(
            texto(
                idioma,
                "efi_nucleos",
                eficiencia=eficiencia(t),
                usados=usados,
                cpus=t["cpus"],
            )
        )
        print(texto(idioma, "efi_memoria", memoria=memoria, pedida=reqmem))
    return 0


# --- Línea de comandos ---------------------------------------------------


def separar_idioma(args, entorno):
    """Saca --lang de cualquier posición. Prioridad: --lang, variable, español."""
    idioma = None
    resto = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--lang":
            if i + 1 >= len(args):
                raise ErrorUso("idioma_desconocido", valor="")
            idioma = args[i + 1]
            i += 2
            continue
        if a.startswith("--lang="):
            idioma = a.split("=", 1)[1]
        else:
            resto.append(a)
        i += 1
    if idioma is None:
        idioma = entorno.get(VARIABLE_IDIOMA, "").strip().lower() or "es"
        if idioma not in IDIOMAS:
            idioma = "es"  # una variable mal escrita no debe romper el comando
    idioma = idioma.strip().lower()
    if idioma not in IDIOMAS:
        raise ErrorUso("idioma_desconocido", valor=idioma)
    return idioma, resto


def ejecutar(args, idioma, ctx):
    lista = ", ".join(PRACTICAS)
    if not args or args[0] in ("ayuda", "help", "-h", "--help"):
        print(texto(idioma, "ayuda", practicas=lista))
        return 0 if args else 2
    comando, resto = args[0], args[1:]

    if comando == "verificar":
        if not resto:
            raise ErrorUso("falta_practica", practicas=lista)
        if resto[0] not in VERIFICADORES or len(resto) > 1:
            raise ErrorUso(
                "practica_desconocida", practica=" ".join(resto), practicas=lista
            )
        ok, clave, params = VERIFICADORES[resto[0]](ctx)
        etiqueta = texto(idioma, "aprobado" if ok else "pendiente")
        print(etiqueta + " " + texto(idioma, clave, **params))
        return 0 if ok else 1

    if comando == "progreso" and not resto:
        for nombre in PRACTICAS:
            ok = VERIFICADORES[nombre](ctx)[0]
            estado = "progreso_aprobado" if ok else "progreso_pendiente"
            print(f"{nombre:<10} {texto(idioma, estado)}")
        return 0

    if comando == "eficiencia":
        if len(resto) != 1 or not PATRON_JOBID.match(resto[0]):
            raise ErrorUso("jobid_invalido")
        return reporte_eficiencia(ctx, idioma, resto[0])

    if comando == "preparar" and not resto:
        for clave, params in preparar(ctx):
            print(texto(idioma, clave, **params))
        return 0

    raise ErrorUso("comando_desconocido", comando=" ".join(args))


def main(args=None, entorno=None):
    args = sys.argv[1:] if args is None else args
    entorno = os.environ if entorno is None else entorno
    idioma = "es"
    try:
        idioma, resto = separar_idioma(args, entorno)
        return ejecutar(resto, idioma, Contexto(entorno=entorno))
    except ErrorUso as e:
        print(texto(idioma, e.clave, **e.params), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
