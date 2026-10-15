# api

API de la plataforma: FastAPI, SQLAlchemy 2 (async con asyncpg), Alembic y
pydantic-settings, con pruebas en pytest. El contrato acordado está en
[`openapi.yaml`](openapi.yaml) (A-11); cuando una ruta nueva se aparte de él,
se corrige el contrato en el mismo PR.

## Estructura

| Ruta            | Qué va ahí                                                     |
| --------------- | -------------------------------------------------------------- |
| `app/main.py`   | `create_app()`: arma la app, el motor de la base y los errores |
| `app/core/`     | Configuración (`config.py`), base de datos (`db.py`) y errores |
| `app/routers/`  | Rutas HTTP, un módulo por grupo del contrato                   |
| `app/services/` | Lógica de negocio; no sabe de HTTP                             |
| `app/models/`   | Modelos SQLAlchemy; cada modelo nuevo se importa en `__init__` |
| `app/schemas/`  | Esquemas pydantic de entrada y salida                          |
| `migrations/`   | Migraciones de Alembic                                         |
| `tests/`        | Pruebas (pytest + httpx, contra PostgreSQL real)               |

## Variables de entorno

Todas llevan el prefijo `API_`. No hay archivo `.env`: se leen del entorno.

| Variable           | Obligatoria  | Qué es                                                           |
| ------------------ | ------------ | ---------------------------------------------------------------- |
| `API_DATABASE_URL` | sí           | `postgresql+asyncpg://usuario:clave@host:puerto/base`            |
| `API_DB_TIMEOUT`   | no (3)       | Segundos que `/api/health` espera a PostgreSQL                   |
| `API_VERSION`      | no (`dev`)   | Versión que informa `/api/health`; la imagen la recibe del build |
| `API_DOCS`         | no (`false`) | Publica `/api/docs` y `/api/openapi.json` (solo desarrollo)      |

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

alembic upgrade head
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
`pre-commit`.

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
  y revisarla a mano antes del commit. Los nombres de índices y restricciones salen de
  `app/models/base.py`.
- **Sin `print()`** (ruff `T20`): se usa `logging`, y nunca se registra la URL
  de la base ni claves.
