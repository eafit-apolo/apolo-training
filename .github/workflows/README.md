# .github/workflows

Flujos de GitHub Actions (CI y publicación de imágenes).

## `calidad.yml`

Corre en cada PR. Sus jobs son checks obligatorios de `main` (los dos del
verificador se agregan después de su primer merge).

- **pre-commit:** los hooks de `.pre-commit-config.yaml` sobre todo el repo,
  con `SKIP=gitleaks`. Si un hook cambiaría algo, el job falla y muestra el
  diff. Para arreglarlo, corre `pre-commit run --all-files` en local, haz
  commit y vuelve a subir.
- **gitleaks:** gitleaks con `.gitleaks.toml` sobre los commits del PR, no
  solo sobre el estado final. El binario se baja del release oficial y se
  verifica su checksum.
- **verificador (3.12)** y **verificador (3.6):** las pruebas de `verifier/`
  con pytest. El de 3.6 corre en el contenedor `python:3.6-slim-bullseye`,
  porque `setup-python` ya no ofrece esa versión en `ubuntu-24.04`. Tardan
  menos de un minuto, así que corren en todos los PR, sin filtros de rutas.

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

### Versiones

La versión de gitleaks (`GITLEAKS_VERSION`) tiene que ser la misma de
`.pre-commit-config.yaml`. Al subirla, se cambia en los dos lugares.

Las versiones de pytest están en `verifier/requirements-dev.txt`: 7.0.1 es la
última que funciona con Python 3.6.

## Reglas para los workflows nuevos

- Un check obligatorio de `main` no lleva filtros de rutas: si no corre, el PR
  queda bloqueado.
- Cada workflow declara sus permisos mínimos con `permissions:`.
- Las herramientas van con versión fija.
- El dueño de las imágenes va en la variable `IMAGE_PREFIX`, nunca escrito
  fijo.
