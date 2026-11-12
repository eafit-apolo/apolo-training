# deploy

Aquí van los archivos para levantar la plataforma con Docker Compose:

- `compose.dev.yaml`: el entorno de desarrollo en tu equipo.
- `compose.yaml`: la plataforma en la 117 (proxy, web, API, terminal y base).
- `nginx.conf`: el proxy de la 117 (TLS, cabeceras de seguridad y el reparto
  de rutas).

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
| `migrar`  | `alembic upgrade head`, los usuarios de ejemplo y `content/` (B-04), y termina; la API arranca solo si salió bien                 |
| `api`     | uvicorn con `--reload` (etapa `dev` de `api/Dockerfile`), `API_DOCS=true`; los videos subidos en el volumen `media` (B-05)        |
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
existen. Para volver a los datos de ejemplo desde cero, `down -v` y `up`.

### Contenido

`migrar` también importa `content/` con `python -m app.importar` (B-04), así
que el entorno arranca con el curso del repo (hoy, el módulo 0 con su lección,
su video y su quiz). Después de editar el contenido, vuelve a importarlo sin
bajar nada:

```bash
docker compose -f deploy/compose.dev.yaml run --rm migrar
```

Si un archivo no cumple los esquemas, `migrar` sale con error y dice cuál
(`docker compose -f deploy/compose.dev.yaml logs migrar`). Para solo validar:
`docker compose -f deploy/compose.dev.yaml run --rm --no-deps migrar python -m app.importar --revisar`.
Los videos quedan «pendientes» hasta que se suban (ver «Videos»).

Desde la B-03 se puede entrar con ellos (`POST /api/auth/login`). Si cambias la
clave de `bruno` o bloqueas a alguien con 5 intentos fallidos, `down -v` y `up`
lo dejan como al principio. Las sesiones las firma `API_SECRETO`, que en este
compose tiene un valor fijo de desarrollo.

Las cookies de la sesión llevan `Secure`: Chrome y Firefox las aceptan en
`http://localhost`, pero Safari (y cualquier navegador que entre por la IP del
equipo, como el celular) las descarta. Para esa prueba, levanta el entorno con
`API_COOKIES_SEGURAS=false` en la misma terminal y vuelve a levantarlo sin la
variable al terminar.

### Videos

Mientras no esté la pantalla del panel (F-08), un video se sube con curl como
`carla` (instructora); los pasos están en
[api/README.md](../api/README.md#videos-y-subtítulos-b-05). Los archivos quedan
en el volumen `media`: `down` los conserva y `down -v` los borra junto con la
base.

Aquí no hay nginx delante, así que la API manda el video ella misma, con Range
(`API_MEDIA_ENTREGA=api` en este compose). En la 117 lo manda nginx
(`X-Accel-Redirect`, W-05). Para probar ese camino en tu equipo hace falta un
nginx delante de la API con la `location /media-interno/` y levantar la API con
`API_MEDIA_ENTREGA=nginx docker compose -f deploy/compose.dev.yaml up -d api`
en la misma terminal.

Un video subido deja su lección sin «Marcar como completada»: se completa al
ver el 90 % en el reproductor (F-05). Con un video de prueba, adelántalo casi
hasta el final y pausa.

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
  imagen se reconstruye sola. `pruebas` va aparte (es «a pedido»), así que la
  primera vez después del cambio córrelo también con `--build`; si no, usa la
  imagen vieja y falla al importar el paquete nuevo:

  ```bash
  docker compose -f deploy/compose.dev.yaml run --rm --build pruebas
  ```

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
que no está en este entorno. `api-imagen` tiene su propio volumen de videos
(`media-imagen`): subir uno a `localhost:8001` comprueba que el usuario de la
imagen (uid 10001) puede escribir ahí. Puertos: `API_IMAGEN_PUERTO` (8001),
`WEB_IMAGEN_PUERTO` (8080) y `TERMINAL_IMAGEN_PUERTO` (8002).

`terminal-imagen` abre SSH de verdad hacia la VM de práctica, así que necesita
la VPN y la llave revisada de la VM; los pasos están en
[`terminal/README.md`](../terminal/README.md).

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
  hasta que las migraciones y la importación del contenido pasen; un error del
  importador dice el archivo de `content/` y el campo.
- **El video no carga y `/api/media/…` responde 200 vacío**: la API está con
  `API_MEDIA_ENTREGA=nginx` sin un nginx delante. Vuelve a levantarla sin esa
  variable.
- **La base de pruebas no existe**: el script que la crea
  (`dev/initdb/10-base-pruebas.sh`) solo corre con el volumen vacío. Si tu
  volumen es anterior, bórralo con `down -v`.

## La plataforma en la 117

`compose.yaml` y `nginx.conf` viven en `/srv/apolo-training` y se corre desde
ahí. Ansible (grupo `web` de `ansible/site.yml`) deja listo el host: Docker y
DOCKER-USER, las carpetas de datos con su dueño y su etiqueta SELinux, los
secretos de Compose desde el Vault, la llave de la VM de práctica y el
certificado TLS (ver `ansible/README.md`).

| Servicio   | Qué es                                                          | Puertos                                                      |
| ---------- | --------------------------------------------------------------- | ------------------------------------------------------------ |
| `proxy`    | nginx: TLS, cabeceras de seguridad, gzip y reparto de rutas     | 80 (solo el reto de Let's Encrypt) y 443 (solo desde la VPN) |
| `web`      | La app de Angular, servida por nginx sin root                   | 8080, solo en la red `interna`                               |
| `api`      | FastAPI con gunicorn, usuario `api` (uid 10001)                 | 8000, solo en `interna`                                      |
| `terminal` | Gateway WebSocket ↔ SSH a la VM de práctica                     | 8001, solo en `interna`; sale al 22 de la 116 por `salida`   |
| `db`       | PostgreSQL 16.15, base y usuario `training`, datos en `pgdata/` | 5432, solo en `interna`                                      |

| Ruta en el proxy    | Va a             | Detalle                                                         |
| ------------------- | ---------------- | --------------------------------------------------------------- |
| `/`                 | `web:8080`       | La web entrega `index.html` para las rutas de Angular           |
| `/api/`             | `api:8000`       | Con la ruta completa y `X-Forwarded-For`/`-Proto`               |
| `/api/panel/videos` | `api:8000`       | Subida de videos de hasta 2 GB, sin buffer en el proxy          |
| `/ws/terminal`      | `terminal:8001`  | WebSocket (Upgrade, HTTP/1.1), timeouts de 2 h                  |
| `/media-interno/`   | `media/` (disco) | `internal`: solo con el `X-Accel-Redirect` de la API, con Range |

- **Solo el proxy publica puertos.** El 443 lo limita a la VPN el firewall
  perimetral (y DOCKER-USER); el 80 queda abierto a Internet para Let's
  Encrypt y responde 404 a todo lo demás.
- **Imágenes** de `ghcr.io/eafit-apolo` con la etiqueta `TAG` (`main` por
  defecto); `IMAGE_PREFIX` y `TAG` se pueden fijar en el `.env` de
  `/srv/apolo-training`.
- **Secretos fuera del repo**, como secrets de Compose en `secrets/`:
  `db_password` (root, 600), `api_database_url` y `api_secreto` (uid 10001,
  400; la API los lee de `/run/secrets`). Los escribe Ansible desde el Vault.
  `db_password` solo se usa al crear la base, con `pgdata/` vacío: cambiarla
  después no cambia la clave (hace falta `ALTER USER training PASSWORD …`).
- **Upstreams con `resolve`.** nginx arranca aunque `api`, `web` o `terminal`
  no estén (responde 502 en sus rutas) y sigue su IP si se recrean.
- **CSP Ya es obligatoria**
  Angular (`inlineCritical: false`); después pasa a `Content-Security-Policy`.
- **Arranca sola** tras reiniciar la VM: `restart: unless-stopped`. Si alguien
  detiene un servicio con `docker compose stop`, no vuelve hasta un `up`.

### Levantarla la primera vez

Como administrador de la 117 (en el grupo `docker`), desde una copia del repo:

```bash
# 1. El host: secretos, known_hosts y un certificado provisional (desde ansible/).
ansible-playbook site.yml --limit web
# 2. La plataforma, con la base primero y las migraciones antes de la API.
sudo install -m 0644 deploy/compose.yaml /srv/apolo-training/compose.yaml
sudo install -m 0644 deploy/nginx.conf /srv/apolo-training/nginx.conf
cd /srv/apolo-training
docker compose pull
docker compose up -d --wait db
docker compose run --rm api alembic upgrade head
docker compose run --rm -v "$PWD/content:/content:ro,z" api python -m app.importar   # content/ copiado del repo
docker compose up -d --wait
# 3. Otra vez Ansible (desde ansible/): con el proxy arriba, emite el certificado real.
ansible-playbook site.yml --limit web
```

### Cambiar `nginx.conf`

El proxy monta el archivo, no la carpeta: si se reemplaza (`install`, `git`,
Ansible), el contenedor sigue viendo el viejo. Por eso es `restart` y no
`nginx -s reload`, y antes se prueba en un contenedor aparte:

```bash
sudo install -m 0644 deploy/nginx.conf /srv/apolo-training/nginx.conf
cd /srv/apolo-training
docker compose run --rm proxy nginx -t   # prueba sin tocar el proxy que corre
docker compose restart proxy
```

### Verificar

```bash
cd /srv/apolo-training
docker compose ps        # todos Up; solo proxy con «->» en PORTS
sudo ss -tlnp            # solo 22, 80 y 443
# Desde la VPN:
curl -I https://training.apolo.eafit.edu.co/              # 200 y las cabeceras de seguridad
curl -i https://training.apolo.eafit.edu.co/api/health    # 200, base_datos: ok
npx wscat -c wss://training.apolo.eafit.edu.co/ws/terminal -o https://training.apolo.eafit.edu.co
                         # Connected y {"motivo":"sesion_invalida"}
# Desde fuera de la VPN: el 443 no responde y el 80 da 404.
```

Para probar este compose en tu equipo sin tocar `/srv`, apunta
`APOLO_TRAINING_RAIZ` a una carpeta con las de la 117 (`pgdata/`, `media/`,
`acme/`, `tls/`, `terminal/known_hosts` y los tres archivos de `secrets/`):
`APOLO_TRAINING_RAIZ=/tmp/raiz docker compose -f deploy/compose.yaml up -d`.
`pgdata/` queda con dueño 999; bórrala desde un contenedor
(`docker run --rm -v /tmp/raiz:/r alpine rm -rf /r/pgdata`).
