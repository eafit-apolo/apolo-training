# apolo-training

Curso de inducción asincrónico del Centro de Computación Científica Apolo
(Universidad EAFIT) para usuarios nuevos de Apolo II y Apolo III: plataforma
web, terminales de práctica y verificador de laboratorios.

## Estructura

| Carpeta              | Qué contiene                                          |
| -------------------- | ----------------------------------------------------- |
| `web/`               | App Angular 22, Transloco ES/EN, xterm.js             |
| `api/`               | FastAPI, SQLAlchemy 2, Alembic, pytest                |
| `terminal/`          | Gateway WebSocket ↔ SSH (asyncssh)                    |
| `content/`           | Lecciones y quizzes en Markdown (es/ y en/), esquemas |
| `labs/`              | Laboratorios de práctica                              |
| `verifier/`          | Verificador `apolo-training` (CLI) y pruebas          |
| `admin/`             | `apolo-training-admin` y timer de sincronización      |
| `modulefiles/`       | Modulefile de Lmod                                    |
| `deploy/`            | Compose de desarrollo y de la 117, `nginx.conf`       |
| `ansible/`           | Roles de la VM de práctica y de la plataforma         |
| `docs/`              | Documentación pública del proyecto                    |
| `.github/workflows/` | CI y publicación de imágenes                          |

## Desarrollo local

Con Docker, desde la raíz del repo:

```bash
docker compose -f deploy/compose.dev.yaml up --build
```

Levanta PostgreSQL, la API con recarga automática y la web en
<http://localhost:4200>. Pruebas, migraciones, puertos y problemas comunes en
[deploy/README.md](deploy/README.md).

## Cómo trabajamos

Ver [CONTRIBUTING.md](CONTRIBUTING.md): ramas `docs/`, `fix/`, `chore/` y
`feat/`, un PR por tarea del plan y revisión del otro antes de fusionar.

## Repositorio listo para ser público

Este repositorio se va a transferir a la organización eafit-apolo y a hacerse
público. Por eso nunca entran aquí:

- IPs, nombres de host internos ni el mapa de red del centro.
- Contraseñas, llaves, tokens ni archivos `.env`.
- Datos de usuarios, videos ni volcados de base de datos.

Los secretos van en GitHub Secrets, en Ansible Vault o fuera del repo.
`gitleaks` corre en cada commit y bloquea los patrones más comunes.
