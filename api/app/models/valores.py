"""Valores permitidos de las columnas de estado.

Se guardan como texto con un CHECK, no como ENUM de PostgreSQL: agregar un
valor a un ENUM complica las migraciones. Si cambia una lista, la migración
nueva tiene que borrar y volver a crear el CHECK de esa columna.
"""

CLUSTERS = ("apolo2", "apolo3")
ROLES = ("estudiante", "instructor", "admin")
IDIOMAS = ("es", "en")

# Las prácticas que revisa el verificador (apolo-training verificar <práctica>),
# con los mismos nombres del front matter de las lecciones (C-01).
PRACTICAS = (
    "conexion",
    "terminal",
    "archivos",
    "modulos",
    "memoria",
    "nucleos",
    "paralelo",
)
ESTADOS_PRACTICA = ("intentado", "aprobado")

# Sistema operativo de un video: «todos», o uno por sistema en la lección de VPN.
SISTEMAS_VIDEO = ("todos", "windows", "macos", "linux")

ESTADOS_GRADUACION = ("enviada", "aprobada", "rechazada")

PATRON_USERNAME = "^[a-z_][a-z0-9_-]{0,31}$"
PATRON_CLAVE_VIDEO = "^m[0-9]{2}-[a-z0-9-]+$"
PATRON_CLAVE_PREGUNTA = "^m[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*$"
PATRON_JOBID = "^[0-9]+(_[0-9]+)?$"


def uno_de(columna: str, valores: tuple[str, ...]) -> str:
    """Condición de un CHECK: la columna toma uno de los valores."""
    lista = ", ".join(f"'{valor}'" for valor in valores)
    return f"{columna} IN ({lista})"


def todos_en(columna: str, valores: tuple[str, ...]) -> str:
    """Condición de un CHECK: cada elemento del arreglo es uno de los valores."""
    lista = ", ".join(f"'{valor}'" for valor in valores)
    return f"{columna} <@ ARRAY[{lista}]::text[]"
