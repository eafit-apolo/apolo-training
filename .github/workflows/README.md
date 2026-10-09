# .github/workflows

Flujos de GitHub Actions (CI y publicación de imágenes).

## `calidad.yml`

Corre en cada PR. Sus dos jobs son checks obligatorios de `main`.

- **pre-commit:** los hooks de `.pre-commit-config.yaml` sobre todo el repo,
  con `SKIP=gitleaks`. Si un hook cambiaría algo, el job falla y muestra el
  diff. Para arreglarlo, corre `pre-commit run --all-files` en local, haz
  commit y vuelve a subir.
- **gitleaks:** gitleaks con `.gitleaks.toml` sobre los commits del PR, no
  solo sobre el estado final. El binario se baja del release oficial y se
  verifica su checksum.

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

## Reglas para los workflows nuevos

- Un check obligatorio de `main` no lleva filtros de rutas: si no corre, el PR
  queda bloqueado.
- Cada workflow declara sus permisos mínimos con `permissions:`.
- Las herramientas van con versión fija.
- El dueño de las imágenes va en la variable `IMAGE_PREFIX`, nunca escrito
  fijo.
