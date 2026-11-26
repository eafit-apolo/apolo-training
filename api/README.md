# api

API de la plataforma: FastAPI, SQLAlchemy 2 (async con asyncpg), Alembic y
pydantic-settings, con pruebas en pytest. El contrato acordado está en
[`openapi.yaml`](openapi.yaml) (A-11); cuando una ruta nueva se aparte de él,
se corrige el contrato en el mismo PR.

## Estructura

| Ruta                   | Qué va ahí                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| `app/main.py`          | `create_app()`: arma la app, el motor de la base y los errores                                         |
| `app/core/`            | Configuración (`config.py`), base de datos (`db.py`) y errores                                         |
| `app/routers/`         | Rutas HTTP, un módulo por grupo del contrato                                                           |
| `app/services/`        | Lógica de negocio; no sabe de cookies ni de `Request` (errores con `ErrorApi`)                         |
| `app/models/`          | Modelos SQLAlchemy; cada modelo nuevo se importa en `__init__`; valores de los `CHECK` en `valores.py` |
| `app/datos_ejemplo.py` | Usuarios de ejemplo del entorno de desarrollo                                                          |
| `app/importar.py`      | Importador de `content/` (B-04): `python -m app.importar`                                              |
| `app/rol.py`           | Cambiar un rol desde la consola (el primer admin, B-08): `python -m app.rol USUARIO admin`             |
| `app/schemas/`         | Esquemas pydantic de entrada y salida                                                                  |
| `migrations/`          | Migraciones de Alembic                                                                                 |
| `tests/`               | Pruebas (pytest + httpx, contra PostgreSQL real)                                                       |

## Variables de entorno

Todas llevan el prefijo `API_`. No hay archivo `.env`: se leen del entorno.

En la 117 (W-05), `API_DATABASE_URL`, `API_SECRETO` y `API_TOKEN_SERVICIO`
llegan como secretos de Compose: los archivos `/run/secrets/api_database_url`,
`/run/secrets/api_secreto` y `/run/secrets/api_token_servicio` (este último,
de la V-04). La API los lee solo si `/run/secrets` existe, y una
variable de entorno con el mismo nombre gana sobre el archivo.

| Variable              | Obligatoria                       | Qué es                                                                             |
| --------------------- | --------------------------------- | ---------------------------------------------------------------------------------- |
| `API_DATABASE_URL`    | sí                                | `postgresql+asyncpg://usuario:clave@host:puerto/base`                              |
| `API_DB_TIMEOUT`      | no (3)                            | Segundos que `/api/health` espera a PostgreSQL                                     |
| `API_VERSION`         | no (`dev`)                        | Versión que informa `/api/health`; la imagen la recibe del build                   |
| `API_DOCS`            | no (`false`)                      | Publica `/api/docs` y `/api/openapi.json` (solo desarrollo)                        |
| `API_DATOS_EJEMPLO`   | no (`false`)                      | Deja correr `python -m app.datos_ejemplo` (solo desarrollo)                        |
| `API_SECRETO`         | sí, para la API                   | 32 caracteres o más; firma la sesión. Cambiarlo cierra todas                       |
| `API_COOKIES_SEGURAS` | no (`true`)                       | Cookies con `Secure`; `false` solo para probar por http desde otro equipo          |
| `API_MEDIA_DIR`       | no (`/srv/apolo-training/media`)  | Carpeta de los videos y subtítulos subidos (B-05)                                  |
| `API_MEDIA_ENTREGA`   | no (`nginx`)                      | `nginx` (`X-Accel-Redirect`, la 117) o `api` (la API manda el archivo; desarrollo) |
| `API_TOKEN_SERVICIO`  | no (sin él, `/internal/*` da 401) | 32 caracteres o más; el token de la VM de práctica para `/api/internal/*` (B-07)   |

En la imagen además: `WEB_CONCURRENCY` (workers de gunicorn, 2 por defecto) y
`GUNICORN_CMD_ARGS` para opciones extra.

## Correrla en tu equipo

Lo más simple es el entorno de desarrollo de `deploy/compose.dev.yaml`, que
levanta la base, aplica las migraciones y corre la API con recarga automática
(ver [deploy/README.md](../deploy/README.md)). Desde la raíz del repo:

```bash
docker compose -f deploy/compose.dev.yaml up --build
```

La API queda en <http://localhost:8000/api/health> y la documentación en
<http://localhost:8000/api/docs>.

### Sin Docker para la API

Si prefieres correr la API con tu propio Python (para el depurador del editor,
por ejemplo), levanta solo la base con Docker. Necesitas Python 3.12; si tu
sistema no lo trae (Arch, por ejemplo, va en una versión más nueva), crea el
entorno con [uv](https://docs.astral.sh/uv/), que baja un 3.12 a tu carpeta de
usuario sin tocar el del sistema. Un entorno de uv no trae `pip`, así que se
instala con `uv pip`:

```bash
docker compose -f deploy/compose.dev.yaml up -d db   # desde la raíz del repo

cd api
uv venv -p 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
export API_DATABASE_URL=postgresql+asyncpg://apolo:apolo@localhost:5433/apolo_training
export API_SECRETO=desarrollo-desarrollo-desarrollo-desarrollo   # solo local

alembic upgrade head
API_DATOS_EJEMPLO=true python -m app.datos_ejemplo   # usuarios de ejemplo (opcional)
python -m app.importar                               # el contenido de content/ (B-04)
API_DOCS=true uvicorn --factory app.main:create_app --reload
```

La base queda en el puerto 5433 de tu equipo. Si está ocupado, levántala con
`API_DB_PUERTO=5434` y cambia el puerto en la URL.

Si ya tienes Python 3.12, sirve igual `python3.12 -m venv .venv` y
`pip install -r requirements-dev.txt`. En Arch, `pip install` fuera de un
entorno virtual falla a propósito (PEP 668): si ves ese error, el entorno no
quedó activado.

La imagen de producción (gunicorn sin root) se prueba con el perfil `imagenes`
de `deploy/compose.dev.yaml` (ver [deploy/README.md](../deploy/README.md)).

## Importar el contenido (B-04)

El curso vive en `content/` (formato en [content/README.md](../content/README.md)).
El importador lo valida con los esquemas de `content/schema/` y las reglas del
README, y lo carga en la base:

```bash
python -m app.importar              # valida y carga (usa API_DATABASE_URL)
python -m app.importar --revisar    # solo valida; no necesita la base (el job content del CI)
python -m app.importar --dir RUTA   # otra carpeta content/
```

- Por defecto lee `content/` dos niveles arriba de `app/`: la raíz del repo, o
  `/content` en los servicios `migrar` y `pruebas` del compose de desarrollo,
  que la montan en solo lectura. La imagen que se publica lleva el `content/`
  de su misma versión en `/content` (contexto de build aparte, ver
  `Dockerfile`), y el despliegue de la 117 lo importa sin montar nada. `migrar` lo corre después de las migraciones;
  para volver a importar tras editar el contenido,
  `docker compose -f deploy/compose.dev.yaml run --rm migrar`.
- Si un archivo no cumple, no carga nada y dice cada error con su archivo y su
  campo. Todo va en una transacción.
- Se puede correr las veces que sea: busca por slug o clave y lo que no cambió
  no se toca («Importado: sin cambios»).
- Nunca borra progreso. Una lección que sale del repo queda con
  `publicada = false`; una pregunta que sale se borra con sus opciones (los
  intentos guardan sus respuestas); un quiz que sale se borra solo si nadie lo
  ha intentado, y si no, el importador falla y lo dice.
- Los videos se crean sin archivo, con su clave: el instructor los sube desde
  el panel (B-05).

Las rutas de lectura (`/api/cursos/...`) van por slug y calculan el estado de
cada módulo con la regla de desbloqueo: el n+1 se abre al completar el n
(`app/services/contenido.py`). Instructores y admins pueden abrir lecciones de
módulos bloqueados.

`POST /api/lecciones/{id}/completar` es «Marcar como completada» (F-04,
`app/services/progreso.py`), para las lecciones sin quiz ni video subido: 409
`requisitos_pendientes` si la lección tiene quiz o un video ya subido sin ver
(mientras no esté completa), y 403 `modulo_bloqueado` si su módulo está
bloqueado, también para instructores y admins.

`POST /api/progreso/video` es el reporte del reproductor (F-05, mismo
archivo), con `leccion_id`, `video_id` y `segundo`: cada 15 s mientras el
video corre, al pausar, al terminar y al salir de la lección. Guarda dónde se
reanuda (`video_posicion_seg`, el último segundo) y lo más lejos que llegó
(`video_max_seg`); al pasar el 90 % de la duración de ese video, el video
queda visto y la lección completa si no tiene quiz o si ya lo aprobó. Todo en
una sola sentencia (`INSERT … ON CONFLICT`), así dos pestañas a la vez no se
pisan. Con el módulo bloqueado, 403 para todos los roles, igual que completar.

## Quizzes y Mi progreso (B-06)

`GET /api/quizzes/{quiz_id}` da las preguntas del quiz de una lección (el id
viene en la lección como `quiz_id`) **sin la opción correcta**, con el mejor
puntaje del usuario. Se lee como la lección: un estudiante recibe 403
`modulo_bloqueado` si el módulo está bloqueado; instructores y admins pueden
leerlo.

`POST /api/quizzes/{quiz_id}/intentos` califica en el servidor
(`app/services/quizzes.py`):

- Hay que responder todas las preguntas, una vez cada una, con opciones de esa
  pregunta (exactamente una si no es múltiple); si no, 422
  `respuestas_invalidas`.
- Una pregunta cuenta si se marcaron exactamente sus opciones correctas, sin
  puntos parciales. El puntaje es el porcentaje de preguntas acertadas y
  aprueba si acierta al menos el `umbral` del quiz (0.80): en un quiz de 2
  preguntas hay que acertar las dos; en el final, 7 de 8.
- La respuesta dice, por pregunta, si acertó y la explicación, **nunca cuál
  opción era la correcta**, para que reintentar sirva. Intentos ilimitados;
  cuenta el mejor.
- Aprobar marca `quiz_aprobado` y completa la lección si su video subido ya
  está visto o si no tiene video subido; si falta el video, la completa el
  reporte que pase el 90 %. Nada de eso vuelve atrás. Exige el módulo abierto
  a todos los roles, como completar.

`GET /api/me/progreso` da el avance del curso de inducción por módulo y por
lección: completada, video visto, quiz aprobado, mejor puntaje y, desde la
F-07, las prácticas que explica (`practicas`, para que la web enlace cada
práctica con su lección). Desde la B-07 trae también las prácticas, la
sincronización, la graduación, `aprobado` y el siguiente paso (ver abajo).

## Prácticas, graduación y siguiente paso (B-07)

**Sincronización.** `POST /api/internal/labs` lo llama la VM de práctica cada
5 minutos (V-05) con `Authorization: Bearer <token>`. La API compara el token
con `API_TOKEN_SERVICIO` (`secrets.compare_digest`) y responde 401
`token_servicio_invalido` si falta, no es `Bearer` o no coincide; una sesión
de usuario no sirve. La IP de la 116 la filtra el nginx de la 117, no la API.
El reporte es completo (`app/services/labs.py`):

- upsert por usuario y práctica: el mismo reporte dos veces no cambia nada;
- un `aprobado` no retrocede ni cambia de JobID; un `intentado` sobre un
  aprobado vuelve en `ignorados` con `no_retrocede`;
- un usuario desconocido o dado de baja vuelve en `ignorados` (el resto se
  guarda); el mismo usuario y práctica dos veces → 422 `registro_repetido`;
- cada envío deja una fila en `sincronizaciones`.

**Graduación** (`app/services/graduaciones.py`). `POST /api/me/graduacion`
guarda el JobID y la salida del verificador con el clúster del perfil. Se puede
enviar en cualquier momento y reenviar mientras no esté aprobada (vuelve a
`enviada` y borra la revisión); aprobada → 409 `graduacion_aprobada`.
`GET /api/panel/graduaciones?estado=` las lista, las más viejas primero, con
las prácticas aprobadas de cada uno. `POST
/api/panel/graduaciones/{username}/revision` aprueba o rechaza una `enviada`
(si no, 409 `sin_graduacion_pendiente`); rechazar exige comentario (422
`comentario_obligatorio`). Se auditan `graduacion_enviada` y
`graduacion_revisada` (sin la salida).

**Mi progreso.** `labs` trae siempre las siete prácticas;
`sincronizacion_atrasada` es `true` con más de 15 minutos sin reporte (`false`
si nunca hubo uno); `aprobado` = lecciones completas + siete prácticas
aprobadas + graduación aprobada. `siguiente_paso` sigue el orden del curso:
módulo por módulo sus lecciones y luego sus prácticas; después las prácticas
que ninguna lección nombra, la graduación, `esperar_revision`, `esperar_qos` y
`terminado`.

Probar la sincronización en desarrollo (el token es el valor fijo de
`API_TOKEN_SERVICIO` en `deploy/compose.dev.yaml`):

```bash
TOKEN=$(awk '/API_TOKEN_SERVICIO:/ {print $2}' deploy/compose.dev.yaml)
curl -s -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"generado_en": "2026-11-23T10:05:00-05:00", "registros": [
        {"usuario": "ana", "lab": "memoria", "estado": "aprobado",
         "jobid": "1042", "fecha": "2026-11-23T09:58:12-05:00"}]}' \
  http://localhost:8000/api/internal/labs
```

## Cuentas, administración y medición (B-08)

**Altas y bajas solo desde la VM de práctica.** `apolo-training-admin` (V-04)
llama, con el mismo token de servicio de la B-07, a:

- `POST /api/internal/usuarios` (alta): crea un **estudiante** con la clave
  temporal de la VM (solo el hash) y `debe_cambiar_clave`. Si el username ya
  existe, aunque esté de baja, 409 `usuario_existe` y la 116 revierte su alta.
  Un campo de más (por ejemplo `rol`) es un 422.
- `PATCH /api/internal/usuarios/{username}` con `{"activo": false}` (baja): no
  vuelve a entrar y se cierran todas sus sesiones; con `true` se reactiva. Se
  puede repetir sin cambiar nada; 404 si no existe (la baja lo tolera).

Lógica en `app/services/usuarios.py`; se auditan `alta`, `baja` y
`reactivacion` con `actor_servicio = vm-practica`.

**Administración (solo admin, `/api/admin`).** La lista (`?q=`, `cluster`,
`rol`, `estado`, `pagina`, `por_pagina`) con un `estado` por cuenta (`baja`,
`bloqueado`, `debe_cambiar_clave` o `activo`, el primero que se cumpla), el
detalle con el Mi progreso del usuario, el cambio de rol (409 `ultimo_admin`
si quitaría al último admin activo) y el reinicio de la clave de la plataforma
(no la de la VM): una clave temporal de 14 caracteres que se ve una sola vez
(`Cache-Control: no-store`), `debe_cambiar_clave`, la cuenta desbloqueada y
sus sesiones cerradas (409 `usuario_inactivo` con una baja). Los aprobados
pendientes de QOS y «QOS aplicada» están en `app/services/aprobados.py`. Se
auditan `cambio_rol`, `reinicio_clave` y `qos_aplicada` (nunca la clave).

**El primer admin.** Sin admin no hay quién cambie roles desde la web: tras
la alta desde la 116, en la plataforma:

```bash
docker compose exec api python -m app.rol USUARIO admin
```

Sigue la misma regla (`ultimo_admin`) y queda en la auditoría con
`actor_servicio = consola`. En desarrollo, `diego` ya es admin.

**CSV de la medición.** `GET /api/panel/export/progreso.csv[?cluster=]`
(instructor y admin): una fila por estudiante, también las bajas (columna
`activo`); coma, UTF-8 y fechas ISO 8601 en UTC. Se audita `export_progreso`.

**El avance de muchos a la vez** (`app/services/resumen.py`): la lista, los
aprobados y el CSV leen la estructura del curso una vez y lo de todos en
cuatro consultas, con la misma regla de Mi progreso (una lección de un módulo
bloqueado no cuenta); `tests/test_admin_usuarios.py` lo compara con Mi
progreso. Si cambia la regla del avance o de `aprobado` en
`app/services/progreso.py`, hay que cambiarla también ahí.

Probar el alta en desarrollo:

```bash
TOKEN=$(awk '/API_TOKEN_SERVICIO:/ {print $2}' deploy/compose.dev.yaml)
curl -s -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"username": "fabio", "nombre": "Fabio Prueba", "correo": "fabio@example.com",
       "cluster": "apolo2", "clave_temporal": "Kx7pQm2vRt9wNa"}' \
  http://localhost:8000/api/internal/usuarios
```

## Videos y subtítulos (B-05)

Un instructor o admin sube el MP4 y los VTT de cada video por su clave, la del
front matter de la lección (`m05-trabajos`); el importador ya creó la fila.
Rutas en `app/routers/panel.py` y `app/routers/medios.py`; lógica en
`app/services/medios.py` y `app/services/video_formato.py`.

- **El archivo va como cuerpo del PUT**, no como formulario: la API lo escribe
  mientras llega en `media/.subiendo/` (el mismo volumen, así moverlo no copia
  nada) y corta al pasar 2 GiB (413 `archivo_muy_grande`). Un formulario
  multipart da 415 con la pista. Lo que quede ahí de una subida que no terminó
  (un worker que se reinició) se borra al día siguiente, con la próxima subida.
- **Formato:** [PyAV](https://pypi.org/project/av/) (el paquete `av`, que trae
  FFmpeg adentro) lee el contenedor, los códecs y la duración. Se acepta lo que
  reproduce cualquier navegador: MP4 con H.264 de 8 bits 4:2:0, perfil
  Baseline, Main o High, y audio AAC o sin audio; si no, 415
  `video_formato_invalido` y `detail` dice qué trae el archivo. Los VTT: hasta
  1 MiB, en UTF-8 y empezando por `WEBVTT` (415 `vtt_invalido`).
- Cada subida lleva un nombre nuevo en la carpeta del módulo
  (`m05/m05-trabajos-20261105T140312-a1b2.mp4`) y el archivo anterior se borra
  al guardar: quien esté viendo el video viejo no recibe pedazos del nuevo.
  Queda en la auditoría (`video_subido`, `subtitulos_subidos`).
- **Entrega:** `GET /api/media/{id}` y `/api/media/{id}/subtitulos/{idioma}`
  validan la sesión, como el resto de la API, y con `API_MEDIA_ENTREGA=nginx`
  responden vacías con `X-Accel-Redirect: /media-interno/<archivo>`: nginx
  manda el archivo con Range desde una `location` interna (W-05). Con `api`
  (el compose de desarrollo) lo manda la API misma con `FileResponse`, que
  también entiende Range. Cualquier sesión puede pedir un video, aunque su
  lección esté en un módulo bloqueado.
- Con un video subido, su lección ya no se marca a mano: se completa al verlo
  (F-05, ver abajo).

Mientras no exista la pantalla del panel (F-08), se sube con curl. Como todo
PUT, necesita la sesión y la cabecera CSRF (con el compose de desarrollo, en
`http://localhost:8000`):

```bash
J=$(mktemp)
curl -s -c "$J" -H 'Content-Type: application/json' \
  -d '{"username":"carla","clave":"apolo-training-dev"}' \
  http://localhost:8000/api/auth/login >/dev/null
CSRF=$(awk '$6=="csrf"{print $7}' "$J")

curl -s -b "$J" http://localhost:8000/api/panel/videos   # las claves que hay
curl -s -b "$J" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: video/mp4' \
  -T video.mp4 http://localhost:8000/api/panel/videos/m00-bienvenida
curl -s -b "$J" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: text/vtt' \
  -T es.vtt http://localhost:8000/api/panel/videos/m00-bienvenida/subtitulos/es
```

## Pruebas y calidad

Con Docker, desde la raíz del repo (lo mismo que el job `api` del CI, contra
una base aparte):

```bash
docker compose -f deploy/compose.dev.yaml run --rm pruebas
```

Con tu propio Python, desde `api/` y con la base arriba:

```bash
python -m pytest               # necesita API_DATABASE_URL
alembic check                  # los modelos y las migraciones coinciden
pre-commit run --all-files     # ruff (con api/ruff.toml), prettier y demás
```

En CI, el job `api` de `.github/workflows/calidad.yml` levanta PostgreSQL 16,
aplica las migraciones, corre `alembic check` y pytest. ruff lo corre el job
`pre-commit`, y el job `content` valida `content/` con
`python -m app.importar --revisar`. Las pruebas del importador también leen el
`content/` real (por eso el servicio `pruebas` lo monta). Las de videos (B-05)
generan MP4 de pocos KB con PyAV (`tests/ayuda_medios.py`), así que no hay
videos en el repo, y guardan lo subido en una carpeta temporal.

## Reglas de ruff

`api/ruff.toml` lista las reglas con `select` en vez de usar las de por
defecto, por dos razones:

- ruff 0.16 activa por defecto muchas más reglas que antes, así que sin
  `select` cada actualización de ruff podría cambiar qué se revisa.
- Una configuración anidada (`api/ruff.toml`) no hereda la de la raíz, y el
  repo no tiene una en la raíz. Lo que no esté aquí no se revisa en `api/`.

| Código  | Qué revisa                                                            |
| ------- | --------------------------------------------------------------------- |
| `E`/`W` | Estilo de pycodestyle (`E501`, el largo de línea, se deja al formato) |
| `F`     | Errores de Pyflakes: nombres sin definir, imports sin usar            |
| `I`     | Orden de los imports (`app` cuenta como código propio)                |
| `UP`    | Sintaxis moderna para Python 3.12                                     |
| `B`     | Errores probables (bugbear)                                           |
| `ASYNC` | Llamadas que bloquean dentro de código async                          |
| `FAST`  | Buenas prácticas de FastAPI (por ejemplo, `Annotated`)                |
| `S`     | Seguridad (bandit)                                                    |
| `DTZ`   | Fechas sin zona horaria                                               |
| `C4`    | Comprensiones innecesarias                                            |
| `SIM`   | Código que se puede simplificar                                       |
| `PT`    | Estilo de pytest                                                      |
| `T20`   | `print()` olvidados                                                   |
| `RUF`   | Reglas propias de ruff                                                |

En `tests/` se permiten `S101` (`assert`), `S105` y `S106` (claves de prueba
escritas en el código). Para agregar una regla, se suma su código a `select` en
el mismo PR que arregla lo que encuentre.

## Convenciones

- **Errores:** siempre `{"detail": "...", "codigo": "..."}`. Para un error
  esperado se lanza `ErrorApi(status, "codigo_estable", "detalle")`; la app
  traduce el `codigo`.
- **Dependencias con `Annotated`:** `sesion: SesionDep`, no
  `sesion = Depends(...)` (ruff lo exige con `FAST002`). `EngineDep` y
  `SesionDep` están en `app/core/db.py`:

  ```python
  from app.core.db import SesionDep


  @router.get("/cursos")
  async def listar_cursos(sesion: SesionDep) -> list[Curso]: ...
  ```

  Así la firma dice qué recibe la ruta y la dependencia se escribe una sola vez.

- **Migraciones:** `alembic revision --autogenerate -m "..."` (con Docker:
  `docker compose -f deploy/compose.dev.yaml run --rm api alembic revision --autogenerate -m "..."`)
  y revisarla a mano antes del commit: autogenerate no detecta cambios en los
  `CHECK`, así que esos se escriben a mano. Los nombres de índices y
  restricciones salen de `app/models/base.py`. Toda migración debe poder
  deshacerse: el CI corre `upgrade head`, `downgrade base` y `upgrade head`.
  El modelo y su diagrama están en `docs/diseno/modelo-datos.md`.
- **Sin `print()`** (ruff `T20`): se usa `logging`, y nunca se registra la URL
  de la base ni claves. Las claves que llegan en el cuerpo son `SecretStr`.
- **Roles de cada ruta (B-03):** toda ruta declara quién la usa con un ayudante
  de `app/core/auth.py`, que además pone `x-roles` en el OpenAPI. Tiene que
  coincidir con `x-roles` de `openapi.yaml`: lo revisa `tests/test_roles.py`,
  que también prueba que un estudiante recibe 403 en toda ruta que no lo
  incluye.

  ```python
  from app.core.auth import UsuarioDep, con_roles


  @router.get("/panel/resumen", **con_roles("instructor", "admin"))
  async def resumen(usuario: UsuarioDep, sesion: SesionDep) -> Resumen: ...
  ```

  `publica()` es para rutas sin sesión y `con_refresh()` para las que usan la
  cookie `rt`. Con `con_roles(...)`, todo lo que no sea GET exige además el
  token CSRF, sin código extra en la ruta.

- **Sesión (B-03):** cookies `at` (JWT de 15 min con el id del usuario y de su
  sesión), `rt` (7 días desde el último uso, solo su sha256 en `sesiones`) y
  `csrf` (HMAC del id de la sesión). El rol y el estado se leen de la base en
  cada petición: una baja, un cambio de rol o un logout valen al instante.
  Constantes (duraciones, bloqueo, largo de la clave) en `app/core/seguridad.py`.
