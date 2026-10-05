# Cómo contribuir

## Flujo de una tarea

1. Parte de la rama principal al día: `git switch main && git pull`.
2. Crea una rama con el prefijo que corresponda y el código de la tarea del plan:
   - `feat/` funcionalidad nueva, por ejemplo `feat/b-03-login`.
   - `fix/` corrección de un error.
   - `chore/` mantenimiento, configuración o infraestructura.
   - `docs/` documentación.
3. Haz commits pequeños. El mensaje empieza con el código de la tarea:
   `B-03: agrega el endpoint de login`.
4. Sube la rama y abre un PR. La plantilla pide el código de la tarea y la
   Definition of Done; borra los bloques que no apliquen.
5. El otro revisa y aprueba. Nadie fusiona su propio PR: quien aprueba fusiona
   con squash y la rama se borra sola.
6. Marca la tarea como hecha en el plan.

La rama principal está protegida: no se hace push directo y se necesita una
aprobación, también para los administradores.

## Antes del primer commit

```bash
pip install --user pre-commit   # o: pipx install pre-commit
pre-commit install
```

Los hooks corren en cada commit: `check-yaml`, `end-of-file-fixer`,
`trailing-whitespace`, `ruff`, `prettier` y `gitleaks`. Para correrlos sobre todo
el repo: `pre-commit run --all-files`.

## Lo que nunca entra al repo

- IPs, nombres de host internos o el mapa de red (`docs/red.md` vive en Affine).
- Contraseñas, llaves, tokens, certificados o archivos `.env`.
- Nombres de usuario, datos de personas ni salidas de comandos que los contengan.
- Videos y volcados de base de datos.

Si un archivo necesita una IP o un secreto, la variable va en Ansible Vault o en
GitHub Secrets y el repo solo la referencia por nombre. Si `gitleaks` bloquea un
commit, quita el dato; no desactives el hook.

## Etiquetas

`infra`, `api`, `web`, `terminal`, `contenido`, `video`, `docs`.
