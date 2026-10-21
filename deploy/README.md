# deploy

Aquí van los archivos para levantar la plataforma con Docker Compose:

- `compose.dev.yaml`: el entorno de desarrollo en tu equipo (esta guía).
- `compose.yaml` y `nginx.conf`: la plataforma en la 117 (llegan con la W-06).

Cada servicio trae su `Dockerfile` en su propia carpeta (`api/Dockerfile`,
`web/Dockerfile`…), y el dueño de las imágenes publicadas va en la variable
`IMAGE_PREFIX`.

## Desarrollo local

`compose.dev.yaml` levanta PostgreSQL 16, la API con recarga automática y la
web con `ng serve`. El código se monta desde `api/` y `web/`: al guardar un
archivo, la API se reinicia sola y el navegador se actualiza. No hace falta la
117 ni instalar Python o Node en tu equipo.

### Requisitos

- Linux con Docker Engine, el servicio de Docker activo, el plugin
  `docker compose` (v2 o más nuevo) y tu usuario en el grupo `docker` (en Arch,
  ver «Docker en Arch Linux»).
- Si tu uid no es 1000 (`id -u`), exporta antes `UID_LOCAL` y `GID_LOCAL`
  (puedes dejarlo en tu `~/.bashrc`):

  ```bash
  export UID_LOCAL=$(id -u) GID_LOCAL=$(id -g)
  ```

  Los contenedores corren con tu usuario, así que lo que se crea dentro
  (migraciones, cachés de Angular y pytest) queda a tu nombre y no de root.

### Docker en Arch Linux

En Arch, instalar Docker no lo deja listo: el servicio no arranca solo y tu
usuario todavía no puede usarlo. Se hace una sola vez:

```bash
sudo pacman -S --needed docker docker-compose docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Después **cierra la sesión y vuelve a entrar** (o, solo en esa terminal,
`newgrp docker`) y comprueba:

```bash
id -nG | grep -w docker              # debe aparecer docker
docker info --format '{{.ServerVersion}}'
docker compose version
```

Por qué cada paso:

- `docker-compose` trae el plugin `docker compose` y `docker-buildx` el
  constructor que usa `--build`.
- `systemctl enable --now` arranca el servicio ahora y en cada encendido. Sin
  él, el socket `/var/run/docker.sock` no existe.
- El socket es de root y del grupo `docker` (`srw-rw----`), por eso hace falta
  el grupo. Los grupos se leen al iniciar sesión: hasta que vuelvas a entrar,
  la terminal sigue sin el grupo nuevo.
- Estar en el grupo `docker` equivale a ser root en tu equipo; está bien en tu
  PC de desarrollo, no en un servidor compartido.
- No uses `sudo docker compose` en lugar del grupo: `sudo` no pasa tus
  variables (`UID_LOCAL`, los puertos) y lo que Docker cree en el repo puede
  quedar de root.

### Levantarlo

Desde la raíz del repo:

```bash
docker compose -f deploy/compose.dev.yaml up --build
```

La primera vez tarda unos minutos (descarga imágenes e instala dependencias);
después, segundos. Los registros salen en la terminal y `Ctrl+C` lo detiene.
Para dejarlo en segundo plano, agrega `-d` y mira los registros con
`docker compose -f deploy/compose.dev.yaml logs -f api web`.

| Qué                     | Dónde                              |
| ----------------------- | ---------------------------------- |
| Web (`ng serve`)        | <http://localhost:4200>            |
| API a través de la web  | <http://localhost:4200/api/health> |
| API directa             | <http://localhost:8000/api/health> |
| Documentación de la API | <http://localhost:8000/api/docs>   |
| PostgreSQL              | `localhost:5433`, usuario `apolo`  |

Todo escucha solo en 127.0.0.1. Si un puerto está ocupado, cámbialo con
`WEB_PUERTO`, `API_PUERTO` o `API_DB_PUERTO`, por ejemplo
`API_DB_PUERTO=5434 docker compose -f deploy/compose.dev.yaml up --build`.
La base usa el 5433 y no el 5432 para no chocar con otro PostgreSQL que tengas
en tu equipo; dentro de Docker, la API la sigue encontrando en `db:5432`.

### Servicios

| Servicio  | Qué hace                                                                                                                          |
| --------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `db`      | PostgreSQL 16 con `apolo_training` y `apolo_training_test` (volumen `db`)                                                         |
| `migrar`  | `alembic upgrade head`, carga los usuarios de ejemplo y termina; la API arranca solo si salió bien                                |
| `api`     | uvicorn con `--reload` (etapa `dev` de `api/Dockerfile`), `API_DOCS=true`                                                         |
| `web`     | `ng serve` (etapa `dev` de `web/Dockerfile`); envía `/api` al servicio API                                                        |
| `pruebas` | Lo mismo que el job `api` del CI (migraciones de ida y vuelta, `alembic check` y pytest), contra `apolo_training_test` (a pedido) |

La web y la API comparten origen gracias al proxy de `ng serve`
(`web/proxy.conf.mjs`), igual que en producción detrás del nginx de borde: las
cookies de la sesión lo necesitan y así no hace falta CORS.

### Usuarios de ejemplo

`migrar` carga estos usuarios con `python -m app.datos_ejemplo` (B-02). Todos
tienen la clave `apolo-training-dev`, que solo existe en tu base local: el
script no corre sin `API_DATOS_EJEMPLO=true`, que solo pone este compose.

| Usuario | Rol        | Clúster   | Para probar                        |
| ------- | ---------- | --------- | ---------------------------------- |
| `ana`   | estudiante | Apolo II  | Un estudiante normal, en español   |
| `bruno` | estudiante | Apolo III | El cambio de clave obligatorio, EN |
| `carla` | instructor | Apolo III | El panel de instructor             |
| `diego` | admin      | Apolo II  | La administración                  |
| `elena` | estudiante | Apolo III | Una cuenta dada de baja            |

Se puede correr las veces que sea: crea los que falten y no toca los que ya
existen. Para volver a los datos de ejemplo desde cero, `down -v` y `up`. El
módulo de ejemplo con lección, video y quiz llega con el importador (B-04).

### Tareas de cada día

Todos desde la raíz del repo. Para escribir menos, puedes crear un alias:
`alias dc='docker compose -f deploy/compose.dev.yaml'`.

```bash
# Pruebas de la API (migraciones, alembic check y pytest, como en el CI)
docker compose -f deploy/compose.dev.yaml run --rm pruebas
# Solo algunas pruebas
docker compose -f deploy/compose.dev.yaml run --rm pruebas python -m pytest -k salud

# Nueva migración (B-02 en adelante): queda en api/migrations/versions/
docker compose -f deploy/compose.dev.yaml run --rm api alembic revision --autogenerate -m "describe el cambio"

# Consola de PostgreSQL
docker compose -f deploy/compose.dev.yaml exec db psql -U apolo apolo_training

# Detener (los datos de la base se conservan)
docker compose -f deploy/compose.dev.yaml down
# Detener y borrar la base para empezar de cero
docker compose -f deploy/compose.dev.yaml down -v
```

Las pruebas usan su propia base para no tocar tus datos de desarrollo.

### Cuando cambian las dependencias

- `api/requirements*.txt`: con `--build` (ya va en el comando de siempre) la
  imagen se reconstruye sola.
- `web/package-lock.json`: el contenedor `web` se detiene con un aviso. Hay
  que renovar el `node_modules` del contenedor con `-V`:

  ```bash
  docker compose -f deploy/compose.dev.yaml up --build -V
  ```

`-V` no toca la base: está en un volumen con nombre, y solo `down -v` la borra.

### Probar las imágenes de producción

El CI construye las imágenes en cada PR pero no las corre. Antes de un PR que
cambie un `Dockerfile` o `web/nginx.conf`, se pueden probar en local con el
perfil `imagenes` (gunicorn sin root y nginx, como en la 117):

```bash
docker compose -f deploy/compose.dev.yaml up -d --build api-imagen web-imagen
docker compose -f deploy/compose.dev.yaml ps    # health: starting y luego healthy
curl -s localhost:8001/api/health               # {"estado":"ok",...,"version":"local"}
curl -sI localhost:8080/cursos | head -1        # 200
docker compose -f deploy/compose.dev.yaml --profile imagenes down
```

`web-imagen` solo sirve la app: `/api` lo reparte el nginx de borde de la 117,
que no está en este entorno. Puertos: `API_IMAGEN_PUERTO` (8001) y
`WEB_IMAGEN_PUERTO` (8080).

### Si algo falla

- **`Cannot connect to the Docker daemon` o `no such file or directory` en
  `/var/run/docker.sock`**: el servicio de Docker no está corriendo. Arráncalo
  con `sudo systemctl enable --now docker` (ver «Docker en Arch Linux»).
- **`permission denied while trying to connect to the Docker daemon socket`**:
  tu usuario no está en el grupo `docker`, o lo está pero la sesión es anterior.
  Revisa con `id -nG`; si no aparece `docker`, agrégalo y vuelve a entrar a la
  sesión (o `newgrp docker`).
- **`port is already allocated` o `address already in use`**: otro programa
  usa ese puerto. Cambia la variable del puerto (ver arriba) o detén lo que lo
  ocupa. Después, levanta el entorno con `--force-recreate`: un contenedor que
  falló al publicar su puerto puede quedar `Up` pero sin red (en `ps` no muestra
  puertos y nadie le llega).

  ```bash
  docker compose -f deploy/compose.dev.yaml up --build -d --force-recreate
  ```

- **`Permission denied` en `web/node_modules`** al correr `npm ci` en tu
  equipo: si la carpeta no existía, Docker la creó vacía y de root para montar
  la del contenedor. Bórrala con `sudo rmdir web/node_modules` y vuelve a
  correr `npm ci`.
- **`migrar` sale con error**: mira el motivo con
  `docker compose -f deploy/compose.dev.yaml logs migrar`. La API no arranca
  hasta que las migraciones pasen.
- **La base de pruebas no existe**: el script que la crea
  (`dev/initdb/10-base-pruebas.sh`) solo corre con el volumen vacío. Si tu
  volumen es anterior, bórralo con `down -v`.
