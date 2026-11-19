#!/usr/bin/env python3
"""apolo-training-admin: altas y bajas del curso en la VM de práctica y la plataforma.

Corre como root en la VM de práctica (116), con el Python 3.9 de Rocky 9, y solo
usa la biblioteca estándar. Se instala como /usr/sbin/apolo-training-admin.

  alta USUARIO --cluster apolo2|apolo3 --nombre "..." --correo ...
      Cuenta Unix con el grupo del clúster y una clave temporal vencida
      (chage -d 0), asociación de Slurm en curso-<cluster>, perfil, material
      del curso y usuario en la plataforma con la misma clave temporal. Si un
      paso falla, deshace los anteriores: no quedan cuentas a medias.

  baja USUARIO
      Vence la cuenta Unix, corta sus procesos y trabajos, quita la asociación
      de Slurm, desactiva al usuario en la plataforma y deja la marca para
      archivar el home a los 30 días. Se puede repetir: completa lo que falte.

  archivar
      Empaqueta y borra el home de las bajas con 30 días o más. Lo corre el
      timer diario apolo-training-admin-archivar.timer.

La configuración está en /etc/apolo-training/admin.conf (ver admin.conf.example)
y el token de servicio en /etc/apolo-training/token (root, 600).
"""

import argparse
import configparser
import datetime
import functools
import grp
import json
import os
import pwd
import re
import secrets
import shlex
import shutil
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = "/etc/apolo-training/admin.conf"
CLUSTERS = ("apolo2", "apolo3")
IDIOMAS = ("es", "en")
PATRON_USUARIO = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")  # el Username de la API
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIAS_ARCHIVO = 30
LARGO_CLAVE = 14
# Sin los caracteres que se confunden al dictar o copiar la clave: 0 O 1 l I
ALFABETO_CLAVE = "".join(
    c for c in string.ascii_letters + string.digits if c not in "0O1lI"
)
# Hosts a los que se permite hablar por http (sin TLS): solo pruebas locales
HOSTS_LOCALES = ("localhost", "127.0.0.1", "::1")
# sacctmgr no deja quitar una asociación con trabajos vivos; scancel tarda un
# poco en terminarlos, así que se reintenta.
INTENTOS_SACCTMGR = 10
ESPERA_SACCTMGR = 2

PREDETERMINADOS = {
    "url": "",  # https://<plataforma>/api, obligatorio para alta y baja
    "token": "/etc/apolo-training/token",
    "timeout": "15",
    "verificador": "/opt/ohpc/pub/apps/apolo-training/1.0",
    "perfiles": "/etc/apolo-training/usuarios",
    "bajas": "/var/lib/apolo-training/bajas",
    "archivo": "/var/lib/apolo-training/archivo",
}


class Error(Exception):
    """Error que se le muestra al administrador, sin traza."""


class ErrorAPI(Error):
    """La plataforma respondió con error o no respondió."""

    def __init__(self, estado, codigo, detalle):
        self.estado = estado  # código HTTP, o None si no hubo respuesta
        self.codigo = codigo
        texto = f"HTTP {estado}" if estado else "sin respuesta"
        super().__init__(f"plataforma: {texto} ({codigo}): {detalle}")


# --- salida ---------------------------------------------------------------


def paso(texto):
    print(f"· {texto}", flush=True)


def aviso(texto):
    print(f"  aviso: {texto}", file=sys.stderr, flush=True)


# --- configuración y validaciones -----------------------------------------


def leer_config(ruta):
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(ruta, encoding="utf-8"):
        raise Error(f"no se pudo leer la configuración {ruta}")
    conf = dict(PREDETERMINADOS)
    if parser.has_section("admin"):
        conf.update(parser["admin"])
    return conf


def validar_url(conf):
    """La URL base de la API: https, o http solo hacia la propia máquina."""
    url = conf["url"].rstrip("/")
    partes = urllib.parse.urlsplit(url)
    if not url:
        raise Error("falta url en la configuración")
    if partes.scheme == "https" or (
        partes.scheme == "http" and partes.hostname in HOSTS_LOCALES
    ):
        return url
    raise Error(f"url debe ser https://…: {url}")


def leer_token(conf):
    """Token de servicio; se exige que solo root lo pueda leer."""
    ruta = conf["token"]
    try:
        info = os.stat(ruta)
    except FileNotFoundError:
        raise Error(f"falta el token de servicio {ruta}") from None
    if info.st_mode & 0o077:
        raise Error(f"{ruta} debe ser solo de root: chmod 600 {ruta}")
    with open(ruta, encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise Error(f"{ruta} está vacío")
    return token


def validar_usuario(usuario):
    if not PATRON_USUARIO.match(usuario):
        raise Error(
            f"usuario inválido: {usuario!r} (minúsculas, números, _ y -; máximo 32)"
        )
    return usuario


def validar_nombre(nombre):
    nombre = nombre.strip()
    # Va también al campo GECOS de /etc/passwd, que separa con : y ,
    if not nombre or len(nombre) > 120 or any(c in nombre for c in ":,\n"):
        raise Error("nombre inválido: de 1 a 120 caracteres, sin : , ni saltos")
    return nombre


def validar_correo(correo):
    correo = correo.strip()
    if len(correo) > 254 or not PATRON_CORREO.match(correo):
        raise Error(f"correo inválido: {correo!r}")
    return correo


# --- sistema (se reemplazan en las pruebas) --------------------------------


def es_root():
    return os.geteuid() == 0


def existe_en_vm(usuario):
    try:
        pwd.getpwnam(usuario)
    except KeyError:
        return False
    return True


def home_de(usuario):
    try:
        return pwd.getpwnam(usuario).pw_dir
    except KeyError:
        return None


def es_del_curso(usuario):
    """True si está en el grupo apolo2 o apolo3 (protege a los administradores)."""
    for cluster in CLUSTERS:
        try:
            if usuario in grp.getgrnam(cluster).gr_mem:
                return True
        except KeyError:
            continue
    return False


def correr(cmd, entrada=None, aceptar=(0,), **kwargs):
    """Corre un comando sin shell y devuelve el CompletedProcess.

    Si el código de salida no está en aceptar, lanza Error con la salida del
    comando. La entrada (stdin) nunca se imprime: ahí va la clave temporal.
    """
    print(f"    $ {shlex.join(cmd)}", flush=True)
    # Se busca con el PATH de este proceso aunque el comando lleve otro env.
    ejecutable = shutil.which(cmd[0]) or cmd[0]
    proceso = subprocess.run(
        [ejecutable, *cmd[1:]],
        input=entrada,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        **kwargs,
    )
    if proceso.returncode not in aceptar:
        salida = proceso.stdout.strip()
        mensaje = f"{cmd[0]} terminó con código {proceso.returncode}"
        raise Error(f"{mensaje}: {salida}" if salida else mensaje)
    return proceso


def clave_temporal():
    """Clave aleatoria con al menos una minúscula, una mayúscula y un número."""
    while True:
        clave = "".join(secrets.choice(ALFABETO_CLAVE) for _ in range(LARGO_CLAVE))
        if (
            any(c.islower() for c in clave)
            and any(c.isupper() for c in clave)
            and any(c.isdigit() for c in clave)
        ):
            return clave


def hoy():
    return datetime.datetime.now(datetime.timezone.utc).date()


# --- plataforma -------------------------------------------------------------


def llamar_api(conf, token, metodo, ruta, cuerpo):
    """Llama una ruta /internal/* y devuelve el JSON de la respuesta."""
    url = validar_url(conf) + ruta
    # S310: el esquema ya lo limitó validar_url a https (o http local)
    pedido = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(cuerpo).encode("utf-8"),
        method=metodo,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(  # noqa: S310
            pedido, timeout=float(conf["timeout"])
        ) as respuesta:
            datos = respuesta.read()
    except urllib.error.HTTPError as e:
        codigo, detalle = "desconocido", e.reason
        try:
            error = json.loads(e.read().decode("utf-8"))
            codigo = error.get("codigo", codigo)
            detalle = error.get("detail", detalle)
        except (ValueError, AttributeError):
            pass
        raise ErrorAPI(e.code, codigo, detalle) from None
    except (urllib.error.URLError, OSError) as e:
        raise ErrorAPI(None, "sin_conexion", getattr(e, "reason", e)) from None
    return json.loads(datos.decode("utf-8")) if datos else None


# --- alta -------------------------------------------------------------------


def escribir_perfil(conf, usuario, cluster):
    """El archivo que lee /etc/profile.d/apolo-training.sh (P-03)."""
    carpeta = conf["perfiles"]
    os.makedirs(carpeta, mode=0o755, exist_ok=True)
    ruta = os.path.join(carpeta, usuario)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(cluster + "\n")
    os.chmod(ruta, 0o644)  # lo lee la shell del usuario; solo root lo cambia
    return ruta


def revertir(deshacer):
    """Corre las acciones de deshacer en orden inverso; devuelve las que fallaron."""
    fallos = []
    if deshacer:
        paso("revirtiendo lo hecho en la VM")
    for descripcion, accion in reversed(deshacer):
        try:
            accion()
        except Exception as e:
            fallos.append(f"{descripcion}: {e}")
    return fallos


def alta(args, conf):
    usuario = validar_usuario(args.usuario)
    nombre = validar_nombre(args.nombre)
    correo = validar_correo(args.correo)
    cluster = args.cluster

    # Todo lo que puede fallar sin tocar nada se revisa antes de empezar.
    if existe_en_vm(usuario):
        raise Error(
            f"{usuario} ya existe en la VM (para reactivarlo, ver el runbook de altas y bajas)"
        )
    validar_url(conf)
    token = leer_token(conf)
    verificador = os.path.join(conf["verificador"], "bin", "apolo-training")
    if not os.access(verificador, os.X_OK):
        raise Error(f"no se encuentra el verificador {verificador}")

    clave = clave_temporal()
    deshacer = []  # (descripción, acción) de cada paso que ya se hizo
    print(f"Alta de {usuario} ({cluster})")
    try:
        paso("cuenta Unix con clave temporal")
        correr(["useradd", "-m", "-G", cluster, "-c", nombre, usuario])
        deshacer.append(
            (
                "borrar la cuenta Unix",
                functools.partial(correr, ["userdel", "-r", usuario]),
            )
        )
        correr(["chpasswd"], entrada=f"{usuario}:{clave}\n")
        correr(["chage", "-d", "0", usuario])  # la pide cambiar al primer ingreso

        paso(f"asociación de Slurm en curso-{cluster}")
        correr(["sacctmgr", "-i", "add", "user", usuario, f"Account=curso-{cluster}"])
        deshacer.append(
            (
                "quitar la asociación de Slurm",
                functools.partial(
                    correr, ["sacctmgr", "-i", "delete", "user", usuario]
                ),
            )
        )

        paso("perfil")
        perfil = escribir_perfil(conf, usuario, cluster)
        deshacer.append(("borrar el perfil", functools.partial(os.remove, perfil)))

        paso("material del curso (apolo-training preparar)")
        correr(
            ["runuser", "-u", usuario, "--", verificador, "preparar"],
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "APOLO_TRAINING": conf["verificador"],
                "APOLO_TRAINING_CLUSTER": cluster,
            },
            cwd="/",
        )
        # El home y el material se van con userdel -r.

        paso("usuario en la plataforma")
        cuerpo = {
            "username": usuario,
            "nombre": nombre,
            "correo": correo,
            "cluster": cluster,
            "clave_temporal": clave,
        }
        if args.idioma:
            cuerpo["idioma"] = args.idioma
        llamar_api(conf, token, "POST", "/internal/usuarios", cuerpo)
    except BaseException as e:  # también Ctrl+C: nada de cuentas a medias
        fallos = revertir(deshacer)
        if fallos:
            raise Error(
                f"la alta falló ({e}) y la reversión quedó incompleta; revisar a mano:\n  "
                + "\n  ".join(fallos)
            ) from e
        if isinstance(e, Exception):
            raise Error(f"la alta falló y se revirtió: {e}") from e
        raise

    print(f"\nListo: {usuario} ({cluster}) en la VM y en la plataforma.")
    print(f"Clave temporal: {clave}")
    print("Sirve para SSH y para la plataforma; se cambia en el primer ingreso.")


# --- baja -------------------------------------------------------------------


def quitar_asociacion(usuario):
    for _ in range(INTENTOS_SACCTMGR):
        proceso = correr(["sacctmgr", "-i", "delete", "user", usuario], aceptar=(0, 1))
        salida = proceso.stdout
        if "Nothing deleted" in salida:
            aviso("no tenía asociación en Slurm")
            return
        if proceso.returncode == 0:
            return
        if "active" not in salida.lower():  # «Job(s) active, cancel job(s)…»
            raise Error(f"sacctmgr: {salida.strip()}")
        time.sleep(ESPERA_SACCTMGR)
    raise Error("sacctmgr: el usuario sigue con trabajos activos; reintentar la baja")


def marcar_baja(conf, usuario):
    """Deja la fecha de la baja para el archivado; si ya existe, la conserva."""
    carpeta = conf["bajas"]
    os.makedirs(carpeta, mode=0o700, exist_ok=True)
    ruta = os.path.join(carpeta, usuario)
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    fecha = hoy().isoformat()
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(fecha + "\n")
    return fecha


def baja(args, conf):
    usuario = validar_usuario(args.usuario)
    validar_url(conf)
    token = leer_token(conf)

    print(f"Baja de {usuario}")
    en_vm = existe_en_vm(usuario)
    if en_vm:
        if not es_del_curso(usuario):
            raise Error(f"{usuario} no está en apolo2 ni apolo3: no es del curso")
        paso("cuenta Unix vencida y bloqueada")
        # -e 1 vence la cuenta: PAM rechaza todo ingreso, también con llave SSH.
        # -L solo bloquea la clave; se deja por si alguien quita el vencimiento.
        correr(["usermod", "-L", "-e", "1", usuario])
        correr(["pkill", "-KILL", "-u", usuario], aceptar=(0, 1))  # 1: sin procesos

        paso("trabajos y asociación de Slurm")
        correr(["scancel", "-u", usuario])
        quitar_asociacion(usuario)

        fecha = marcar_baja(conf, usuario)
        paso(f"home marcado para archivar ({fecha} + {DIAS_ARCHIVO} días)")
    else:
        aviso("no existe en la VM; solo se desactiva en la plataforma")

    paso("usuario desactivado en la plataforma")
    try:
        llamar_api(
            conf, token, "PATCH", f"/internal/usuarios/{usuario}", {"activo": False}
        )
    except ErrorAPI as e:
        if e.estado != 404:
            raise Error(
                f"{e}\nLa VM ya quedó de baja; repetir la baja para completar."
            ) from None
        if not en_vm:
            raise Error(
                f"{usuario} no existe ni en la VM ni en la plataforma"
            ) from None
        aviso("no existía en la plataforma")

    print(f"\nListo: {usuario} ya no puede entrar por SSH ni a la plataforma.")


# --- archivar ---------------------------------------------------------------


def sigue_de_baja(usuario):
    """True si la cuenta sigue vencida o bloqueada (nadie la reactivó)."""
    proceso = correr(["getent", "shadow", usuario], aceptar=(0, 2))
    if proceso.returncode == 2:  # ya no existe
        return True
    campos = proceso.stdout.strip().split(":")
    clave, vence = campos[1], campos[7]
    return clave.startswith("!") or vence == "1"


def archivar_uno(conf, usuario, fecha):
    home = home_de(usuario)
    if home and not sigue_de_baja(usuario):
        raise Error(f"{usuario}: la cuenta ya no está de baja; no se archiva")
    if home and os.path.isdir(home):
        if os.path.dirname(home.rstrip("/")) in ("", "/"):
            raise Error(f"{usuario}: home sospechoso {home}; no se archiva")
        os.makedirs(conf["archivo"], mode=0o700, exist_ok=True)
        destino = os.path.join(conf["archivo"], f"{usuario}-{fecha}.tar.gz")
        correr(
            [
                "tar",
                "--numeric-owner",
                "-czf",
                destino,
                "-C",
                os.path.dirname(home),
                os.path.basename(home),
            ]
        )
        os.chmod(destino, 0o600)
        shutil.rmtree(home)
        paso(f"{usuario}: home archivado en {destino}")
    else:
        paso(f"{usuario}: no tenía home")
    perfil = os.path.join(conf["perfiles"], usuario)
    if os.path.exists(perfil):
        os.remove(perfil)
    os.remove(os.path.join(conf["bajas"], usuario))


def archivar(args, conf):
    carpeta = conf["bajas"]
    if not os.path.isdir(carpeta):
        return
    errores = []
    for usuario in sorted(os.listdir(carpeta)):
        if not PATRON_USUARIO.match(usuario):
            continue
        with open(os.path.join(carpeta, usuario), encoding="utf-8") as f:
            texto = f.read().strip()
        try:
            fecha = datetime.date.fromisoformat(texto)
        except ValueError:
            errores.append(f"{usuario}: fecha inválida {texto!r}")
            continue
        if (hoy() - fecha).days < DIAS_ARCHIVO:
            continue
        try:
            archivar_uno(conf, usuario, fecha.isoformat())
        except Error as e:
            errores.append(str(e))
    if errores:
        raise Error("no se pudo archivar:\n  " + "\n  ".join(errores))


# --- línea de comandos ------------------------------------------------------


def crear_parser():
    parser = argparse.ArgumentParser(
        prog="apolo-training-admin",
        description="Altas y bajas del curso en la VM de práctica y la plataforma.",
    )
    parser.add_argument(
        "--config", default=CONFIG, help=f"archivo de configuración ({CONFIG})"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("alta", help="crear el usuario en la VM y en la plataforma")
    p.add_argument("usuario", help="el mismo usuario de su clúster")
    p.add_argument("--cluster", choices=CLUSTERS, required=True)
    p.add_argument("--nombre", required=True, help="nombre completo, entre comillas")
    p.add_argument("--correo", required=True)
    p.add_argument("--idioma", choices=IDIOMAS, help="idioma de la plataforma (es)")
    p.set_defaults(funcion=alta)

    p = sub.add_parser("baja", help="impedir el ingreso por SSH y a la plataforma")
    p.add_argument("usuario")
    p.set_defaults(funcion=baja)

    p = sub.add_parser(
        "archivar",
        help=f"archivar el home de las bajas de hace {DIAS_ARCHIVO} días o más",
    )
    p.set_defaults(funcion=archivar)
    return parser


def main(argv=None):
    args = crear_parser().parse_args(argv)
    try:
        if not es_root():
            raise Error("hay que correrlo como root")
        conf = leer_config(args.config)
        args.funcion(args, conf)
    except Error as e:
        print(f"apolo-training-admin: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
