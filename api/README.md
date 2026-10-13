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
| `compose.yaml`  | PostgreSQL y la API para desarrollar en tu equipo              |

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

Necesitas Python 3.12 y Docker. Todo se corre desde `api/`:

```bash
cd api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

docker compose up -d db
export API_DATABASE_URL=postgresql+asyncpg://apolo:apolo@localhost:5432/apolo_training

alembic upgrade head
API_DOCS=true uvicorn --factory app.main:create_app --reload
```

La API queda en <http://localhost:8000/api/health> y la documentación en
<http://localhost:8000/api/docs>. Si el puerto 5432 ya está ocupado, levanta la
base con `API_DB_PUERTO=5433 docker compose up -d db` y cambia el puerto en la URL.

Para probar la imagen como en producción (base + API):

```bash
docker compose up -d --build
curl -s localhost:8000/api/health   # {"estado":"ok","base_datos":"ok","version":"local"}
docker compose down
```

## Pruebas y calidad

```bash
python -m pytest               # necesita API_DATABASE_URL y la base arriba
alembic check                  # los modelos y las migraciones coinciden
pre-commit run --all-files     # ruff (con api/ruff.toml), prettier y demás
```

En CI, el job `api` de `.github/workflows/calidad.yml` levanta PostgreSQL 16,
aplica las migraciones, corre `alembic check` y pytest. ruff lo corre el job
`pre-commit`.

## Convenciones

- **Errores:** siempre `{"detail": "...", "codigo": "..."}`. Para un error
  esperado se lanza `ErrorApi(status, "codigo_estable", "detalle")`; la app
  traduce el `codigo`.
- **Dependencias con `Annotated`:** `sesion: SesionDep`, no
  `sesion = Depends(...)` (ruff lo exige con `FAST002`).
- **Migraciones:** `alembic revision --autogenerate -m "..."` y revisarla a
  mano antes del commit. Los nombres de índices y restricciones salen de
  `app/models/base.py`.
- **Sin `print()`** (ruff `T20`): se usa `logging`, y nunca se registra la URL
  de la base ni claves.
