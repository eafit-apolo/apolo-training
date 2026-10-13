# verifier

Verificador `apolo-training`: revisa las siete prácticas del curso de
inducción en la máquina de práctica. Es un solo archivo,
`apolo_training.py`, que funciona con Python 3.6 o superior y usa solo la
biblioteca estándar.

## Uso

```bash
module load apolo-training
apolo-training preparar             # copia el material a ~/apolo-training
apolo-training verificar memoria    # revisa una práctica
apolo-training progreso             # las siete prácticas y su estado
apolo-training eficiencia 1234      # cuánto de lo reservado usó un trabajo
apolo-training ayuda
```

`verificar` termina con código 0 si la práctica está aprobada, 1 si está
pendiente y 2 si hubo un error de uso (práctica que no existe, sacct que no
responde, material que falta).

### Idioma

Español por defecto. Inglés con `--lang en` en cualquier posición del
comando, o con `export APOLO_TRAINING_LANG=en`. `--lang` manda sobre la
variable. No se usa `LANG`: Rocky trae `en_US.UTF-8` y cada cliente SSH envía
el suyo. Los nombres de los comandos y de las prácticas no se traducen.

## Cómo se verifica cada práctica

| Práctica   | Aprueba cuando…                                                                                            |
| ---------- | ---------------------------------------------------------------------------------------------------------- |
| `conexion` | el comando corre dentro de una sesión SSH (la terminal de la plataforma también entra por SSH).            |
| `terminal` | `~/apolo-training/terminal/respuesta.txt` contiene la clave escondida en el material original.             |
| `archivos` | `~/apolo-training/archivos/vuelta.txt` contiene el código de `ida.txt`, que `preparar` genera por usuario. |
| `modulos`  | hay un trabajo `curso-modulos` en estado `COMPLETED`.                                                      |
| `memoria`  | hay un `curso-memoria` en `OUT_OF_MEMORY` y otro en `COMPLETED`.                                           |
| `nucleos`  | un `curso-nucleos` con 4 núcleos o más usó menos del 50 % de lo reservado.                                 |
| `paralelo` | un `curso-paralelo` con 4 núcleos o más usó el 50 % o más de lo reservado.                                 |

Las prácticas de Slurm leen `sacct` del propio usuario en los últimos 30 días.
Si el clúster no registra el uso de CPU (como Apolo III), lo dicen en vez de
dar un resultado falso.

`archivos` se puede aprobar con un `cp ida.txt vuelta.txt` en el servidor; se
aceptó así. Queda como opción futura revisar el registro de SFTP de `sshd`.

## Instalación

La hace el despliegue (V-06). En la carpeta de instalación
(`<ruta>/apolo-training/1.0`) quedan:

- `bin/apolo-training`: copia de `apolo_training.py` con permisos 755.
- `labs/`: copia de la carpeta `labs/` del repo.

El modulefile (`modulefiles/apolo-training/1.0.lua`) agrega `bin/` al `PATH`
y define `APOLO_TRAINING` con esa carpeta. Sin la variable, el verificador
busca `labs/` junto a su propia carpeta, así que en el repo funciona con
`python3 verifier/apolo_training.py`.

## Pruebas

```bash
python3 -m venv .venv
.venv/bin/pip install -r verifier/requirements-dev.txt
.venv/bin/python -m pytest verifier
```

- `tests/bin/sacct` es un sacct simulado que responde con los trabajos de
  `tests/escenarios/` (todo hecho, solo el fallo de memoria, nada hecho y un
  clúster como Apolo III).
- Cada prueba usa un `HOME` temporal, así que no toca tu carpeta.
- En CI corren con Python 3.12 y 3.6 (`.github/workflows/calidad.yml`).

## Para reusarlo desde el reporte de la plataforma

Cada práctica es una función que recibe un `Contexto` y devuelve
`(aprobada, clave_del_mensaje, parámetros)`, sin imprimir nada:

```python
import apolo_training as at

ctx = at.Contexto(usuario="ana", home="/home/ana")
aprobada, clave, params = at.VERIFICADORES["memoria"](ctx)
```

`conexion` depende del entorno de la sesión, así que desde otro proceso
(por ejemplo, como root) no sirve tal cual.

## Compatibilidad con Python 3.6

No uses `text=`, `capture_output=`, `dataclasses`, el operador `:=` ni nada
posterior a 3.6. `verifier/ruff.toml` apaga las reglas de ruff que propondrían
esos cambios, y el job `verificador (3.6)` lo comprueba en cada PR.
