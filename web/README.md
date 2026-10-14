# web

Frontend del curso de inducción: Angular 22 (componentes standalone, signals y
sin zone.js), Angular Material con la paleta de Apolo y Transloco para los
textos en español e inglés. Las pantallas y sus rutas salen de
[`docs/diseno/pantallas.md`](../docs/diseno/pantallas.md).

## Requisitos

- Node `^22.22.3`, `^24.15.0` o `>=26` (el CI y la imagen usan Node 24). La
  versión menor importa: con Node 22.22.0, el CLI de Angular no arranca.
- Docker, solo para probar la imagen.

## Comandos

Todos dentro de `web/`:

```bash
npm ci            # instala lo del package-lock.json (no uses npm install para esto)
npm start         # servidor de desarrollo en http://localhost:4200
npm run lint      # ESLint (TypeScript y plantillas)
npm test          # Vitest; en una sola pasada: npm test -- --watch=false
npm run build     # build de producción en dist/web/browser
npm run format    # prettier sobre web/ (el pre-commit hace lo mismo)
```

`.npmrc` fija versiones exactas al instalar algo nuevo (`save-exact`) y exige
la versión de Node de `engines` (`engine-strict`).

## Estructura

```text
src/
├── index.html, main.ts
├── styles.scss            # tema de Material
├── styles/_theme-colors.scss  # paleta generada desde #001B89 (no editar a mano)
├── testing/transloco.ts   # textos reales para las pruebas (no entra al build)
└── app/
    ├── app.ts, app.config.ts, app.routes.ts
    ├── core/
    │   ├── i18n/          # idioma inicial, cargador y títulos traducidos
    │   └── layout/        # shell: barra, menú y selector de idioma
    ├── shared/            # pantalla provisional de la F-01
    └── features/          # una carpeta por sección, cargada aparte (lazy)
        ├── cuenta/        # 01 ingresar y cambiar la clave (sin menú)
        ├── cursos/        # 02 catálogo y 03 lección
        ├── progreso/      # 04 mi progreso
        ├── panel/         # 05 panel de instructor
        └── admin/         # 06 administración de usuarios
```

Cada pantalla es por ahora una página provisional (`shared/pendiente.ts`). La
pantalla real reemplaza su `pendiente(...)` en el archivo de rutas de la
sección.

## Idiomas

Los textos de la interfaz están en `public/i18n/es.json` y `en.json`. Una
prueba exige que los dos tengan las mismas claves y ningún texto vacío, así que
toda clave nueva va en ambos.

El idioma inicial es el que el usuario eligió antes en ese navegador; si no, el
del navegador, y si no, español. Cambiarlo con el selector ES/EN cambia los
textos y el título de la pestaña sin recargar. Cuando exista la sesión, el del
perfil (`GET /api/me`) mandará sobre los demás.

## Imagen

```bash
docker compose up -d --build     # http://127.0.0.1:8080 (otro puerto: WEB_PUERTO=8081)
docker compose ps                # health: starting y luego healthy
docker compose down
```

El `Dockerfile` compila con `node:24-alpine` y sirve el resultado con
`nginxinc/nginx-unprivileged` (sin root, puerto 8080). `nginx.conf` solo sirve
la app; TLS, cabeceras de seguridad y `/api` van en el nginx de borde de
`deploy/`. `compose.yaml` es solo para probar la imagen: la Q-02 lo lleva a
`deploy/compose.dev.yaml`.

## Convenciones

- Prefijo `at` (apolo-training) en selectores: `<at-shell>`, `[atAlgo]`.
- Componentes `OnPush`, `inject()` en vez de constructor y `input()` /
  `output()` con signals; ESLint lo exige.
- Formato con prettier (`.prettierrc.json`, solo afecta a `web/`).
