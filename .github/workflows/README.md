# .github/workflows

Flujos de GitHub Actions (CI y publicación de imágenes).

## `calidad.yml`

Corre en cada PR. Todos sus jobs son checks obligatorios de `main`; un job
nuevo se vuelve obligatorio después de su primer merge (ver
[Cómo agregar un check obligatorio](#cómo-agregar-un-check-obligatorio)).

- **pre-commit:** los hooks de `.pre-commit-config.yaml` sobre todo el repo,
  con `SKIP=gitleaks`. Si un hook cambiaría algo, el job falla y muestra el
  diff. Para arreglarlo, corre `pre-commit run --all-files` en local, haz
  commit y vuelve a subir. También es el que corre ruff sobre `api/` (con
  `api/ruff.toml`) y `verifier/` (con `verifier/ruff.toml`), y prettier sobre
  `web/` (con `web/.prettierrc.json`).
- **gitleaks:** gitleaks con `.gitleaks.toml` sobre los commits del PR, no
  solo sobre el estado final. El binario se baja del release oficial y se
  verifica su checksum.
- **verificador (3.12)** y **verificador (3.6):** las pruebas de `verifier/`
  con pytest. El de 3.6 corre en el contenedor `python:3.6-slim-bullseye`,
  porque `setup-python` ya no ofrece esa versión en `ubuntu-24.04`. Tardan
  menos de un minuto, así que corren en todos los PR, sin filtros de rutas.
- **api:** levanta un PostgreSQL 16 de servicio y, desde `api/`, aplica las
  migraciones (`alembic upgrade head`), comprueba que los modelos y las
  migraciones coinciden (`alembic check`) y corre pytest. También corre en
  todos los PR, sin filtros de rutas. La clave de esa base es de prueba y
  la base desaparece al terminar el job.
- **web:** desde `web/`, con Node 24: `npm ci`, ESLint (`ng lint`), las pruebas
  con Vitest (`ng test --watch=false`) y el build de producción. `ng build` no
  falla por una advertencia (presupuesto, CSS, imports), así que el paso busca
  `WARNING` en la salida y falla si la encuentra. Tarda menos de un minuto.

Si se lanza a mano desde la pestaña Actions (_Run workflow_), gitleaks revisa
todo el historial del repo.

### Por qué gitleaks va en un job aparte

El hook de gitleaks revisa solo lo que está en _staged_. En CI no hay nada en
_staged_, así que dentro de `pre-commit run --all-files` pasaría sin revisar
nada.

### Si gitleaks encuentra algo en un PR

Un commit nuevo que borre el dato no basta: el dato sigue en el commit
anterior y el job sigue fallando. Hay que sacarlo del historial de la rama
(`git rebase -i` o `git reset`) y subirla con `git push --force-with-lease`. Si
era un secreto real, además hay que rotarlo.

### Por qué los checks obligatorios no llevan filtros de rutas

Con un filtro (`paths: [api/**]`), el job solo corre si el PR toca esa
carpeta. Si el check es obligatorio y el PR no la toca, GitHub lo deja en
«Expected — Waiting for status to be reported» para siempre: el job nunca se
lanza, nunca informa y el PR no se puede fusionar. Pasa, por ejemplo, con un PR
que solo cambia un `.md` de `docs/`.

Todos los jobs de `calidad.yml` tardan alrededor de un minuto, así que es más
simple correrlos siempre que mantener excepciones.

### Cómo agregar un check obligatorio

1. Se crea el job en un PR y se fusiona. Antes del merge no conviene hacerlo
   obligatorio: los PR abiertos sobre el `main` viejo no tienen ese job y
   quedarían bloqueados.
2. En _Settings → Branches_, en la regla de `main`, se agrega el check con su
   `name:` (por ejemplo `web`). Solo aparece en la lista si corrió en la última
   semana.
3. Se hace en la web, no con un `PUT` a la API de protección de ramas: ese
   `PUT` reescribe toda la protección y es fácil borrar otra regla sin querer.
4. Se comprueba la lista:

   ```bash
   gh api repos/<dueño>/apolo-training/branches/main/protection/required_status_checks \
     --jq '.checks[].context'
   ```

«Require branches to be up to date» queda apagado (`strict: false`): con dos
personas fusionando, obligaría a actualizar cada PR después de cada merge.

### Si falla `alembic check` en el job api

Un modelo cambió y falta su migración. Genérala en local con
`alembic revision --autogenerate -m "..."` (ver `api/README.md`), revísala a
mano y súbela en el mismo PR.

### Versiones

La versión de gitleaks (`GITLEAKS_VERSION`) tiene que ser la misma de
`.pre-commit-config.yaml`. Al subirla, se cambia en los dos lugares.

Las versiones de pytest están en `verifier/requirements-dev.txt`: 7.0.1 es la
última que funciona con Python 3.6. Las de la API están en
`api/requirements.txt` y `api/requirements-dev.txt`; ruff no va ahí, porque lo
fija `.pre-commit-config.yaml`.

Las de la web están fijadas exactas en `web/package.json` y
`web/package-lock.json`. prettier va con la misma versión que en
`.pre-commit-config.yaml`; al subirla, se cambia en los dos lugares. El job usa
Node 24, que cumple el rango de `engines` de `web/package.json`.

## `imagenes.yml`

Construye las imágenes de `api/` y `web/` con sus `Dockerfile` (cada carpeta
es su propio contexto) y las publica en GHCR. Tiene dos jobs con la misma
matriz (`api` y `web`):

- **construir (api)** y **construir (web)**, en cada PR que toque `api/`,
  `web/` o este workflow: construyen la imagen para comprobar que el
  `Dockerfile` sigue funcionando y la descartan. No publican nada y solo tienen
  permiso de lectura.
- **publicar (api)** y **publicar (web)**, al fusionar en `main` (si el merge
  toca `api/`, `web/` o este workflow) o al subir un tag `vX.Y.Z`: construyen
  la imagen y la suben a GHCR. Es el único job con `packages: write`, así que
  un PR nunca recibe permiso para escribir en GHCR.

Las dos imágenes se llaman `${IMAGE_PREFIX}/apolo-training-api` y
`${IMAGE_PREFIX}/apolo-training-web`. Siempre se construyen las dos juntas,
para que la API y la web de un mismo merge tengan la misma etiqueta.

### Por qué este workflow sí lleva filtros de rutas

No es un check obligatorio de `main`, así que si no corre no bloquea nada. Un
PR que solo cambia documentación o contenido no necesita reconstruir las
imágenes. Por la misma razón, si `construir` falla, el PR no queda bloqueado:
hay que revisarlo antes de aprobar.

GitHub no aplica los filtros de rutas a los tags: un tag `vX.Y.Z` siempre
construye y publica las dos imágenes.

### Etiquetas

| Evento         | Etiquetas en GHCR                       | `VERSION`     |
| -------------- | --------------------------------------- | ------------- |
| merge a `main` | `sha-abc1234`, `main`                   | `sha-abc1234` |
| tag `v0.3.1`   | `0.3.1`, `0.3`, `sha-abc1234`, `latest` | `0.3.1`       |
| PR             | ninguna (no se publica)                 | `pr-<número>` |

- `sha-abc1234` son los 7 primeros caracteres del commit. Es la etiqueta que
  se despliega: no cambia nunca.
- `main` apunta a lo último que se fusionó, y `latest`, al último tag. Las dos
  se mueven, así que el despliegue nunca las usa.
- `VERSION` llega a los dos `Dockerfile` como _build-arg_: en la API es
  `API_VERSION` (la versión que devuelve `GET /api/health`) y en las dos queda
  en la etiqueta OCI `org.opencontainers.image.version`.
- `metadata-action` agrega también `org.opencontainers.image.source`, que
  enlaza el paquete de GHCR con este repo.

### `IMAGE_PREFIX`

Es una variable del repo (no un secreto): _Settings → Secrets and variables →
Actions → Variables_. Vale `ghcr.io/<dueño del repo en minúsculas>`. Docker no
acepta mayúsculas en el nombre de una imagen, y `GITHUB_TOKEN` solo puede
publicar en el espacio del dueño del repo. El job `publicar` lo comprueba antes
de construir y falla con un mensaje claro si la variable falta o no coincide.

```bash
gh variable set IMAGE_PREFIX --body "ghcr.io/<dueño>" -R <dueño>/apolo-training
gh variable list -R <dueño>/apolo-training
```

### Visibilidad de los paquetes

Un paquete nuevo en GHCR nace privado y hereda el acceso del repo enlazado.
Cuando el repo se haga público, los paquetes siguen privados hasta que alguien
cambie su visibilidad en _Package settings_; un paquete público no se puede
volver privado. Mientras sean privados, la máquina que haga `docker pull`
necesita un token con `read:packages`.

### Al transferir el repo (A-16)

Los paquetes de GHCR no se mueven con el repo: quedan en la cuenta del dueño
anterior.

1. Cambiar `IMAGE_PREFIX` al dueño nuevo (por ejemplo `ghcr.io/eafit-apolo`).
2. Lanzar el workflow a mano sobre `main` (_Actions → Imágenes → Run
   workflow_) para publicar las dos imágenes en el espacio nuevo.
3. Cambiar `IMAGE_PREFIX` donde se use al desplegar (Ansible).
4. Borrar los paquetes viejos de la cuenta anterior.

### Caché

Cada imagen usa la caché de GitHub Actions con su propio `scope` (`api` o
`web`), para que una no pise a la otra. Los PR pueden leer la caché de `main`,
así que un `Dockerfile` sin cambios se construye en segundos.

## Reglas para los workflows nuevos

- Un check obligatorio de `main` no lleva filtros de rutas: si no corre, el PR
  queda bloqueado.
- Cada workflow declara sus permisos mínimos con `permissions:`. Un permiso
  de escritura (como `packages: write`) va solo en el job que lo necesita, y
  ese job no corre en los PR.
- Las herramientas van con versión fija.
- El dueño de las imágenes va en la variable `IMAGE_PREFIX`, nunca escrito
  fijo.
