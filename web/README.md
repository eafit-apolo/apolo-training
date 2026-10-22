# web

Frontend del curso de inducción: Angular 22 (componentes standalone, signals y
sin zone.js), Angular Material con la paleta de Apolo y Transloco para los
textos en español e inglés. Las pantallas y sus rutas salen de
[`docs/diseno/pantallas.md`](../docs/diseno/pantallas.md).

## Requisitos

- Node `^22.22.3`, `^24.15.0` o `>=26` (el CI y la imagen usan Node 24). La
  versión menor importa: con Node 22.22.0, el CLI de Angular no arranca.
- Docker, para el entorno completo (web, API y base) y para probar la imagen.

Lo más simple es el entorno de desarrollo de `deploy/compose.dev.yaml`, que
corre `ng serve` junto a la API y la base, sin instalar Node en tu equipo (ver
[deploy/README.md](../deploy/README.md)). Desde la raíz del repo:
`docker compose -f deploy/compose.dev.yaml up --build`.

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

`ng serve` envía `/api` a la API (`proxy.conf.mjs`), así la web y la API
comparten origen como en producción. Con `npm start` en tu equipo apunta a
`http://localhost:8000`; para otra dirección, `API_URL=http://localhost:8001 npm start`.

## Estructura

```text
src/
├── index.html, main.ts
├── styles.scss            # tema de Material, foco visible y estilos comunes (at-contenedor, at-oculto)
├── styles/_theme-colors.scss  # paleta generada desde #001B89 (no editar a mano)
├── testing/               # textos reales y axe para las pruebas (no entra al build)
└── app/
    ├── app.ts, app.config.ts, app.routes.ts
    ├── core/
    │   ├── i18n/          # idioma inicial, cargador y títulos traducidos
    │   ├── layout/        # shell: encabezado, menú (☰ en celular), idioma y menú de usuario
    │   └── sesion/        # usuario actual (hoy uno de ejemplo; GET /api/me en la F-03)
    ├── shared/            # ícono, migas de pan, plural y la pantalla provisional
    └── features/          # una carpeta por sección, cargada aparte (lazy)
        ├── cuenta/        # 01 ingresar y cambiar la clave (sin menú)
        ├── cursos/        # 02 catálogo y curso; 03 módulo y lección, con la barra lateral
        │   └── datos/     # tipos, CatalogoService, armarCurso() y los datos de ejemplo
        ├── progreso/      # 04 mi progreso
        ├── panel/         # 05 panel de instructor
        └── admin/         # 06 administración de usuarios
```

Las pantallas que todavía no existen son una página provisional
(`shared/pendiente.ts`). La pantalla real reemplaza su `pendiente(...)` en el
archivo de rutas de la sección.

## Navegación del curso (F-02)

```text
/cursos                           catálogo: saludo, «Continuar» y los cursos
/cursos/:curso                    el curso y la grilla de módulos
/cursos/:curso/:modulo            el módulo y sus lecciones      ┐ con la barra
/cursos/:curso/:modulo/:leccion   la lección (su cuerpo es de la F-04) ┘ lateral
```

`:modulo` y `:leccion` son el id del contenido (`m05/trabajos`, ver
`content/README.md`). El módulo n+1 se abre al completar el n: los bloqueados
se ven, pero no son enlaces, y abrirlos por dirección muestra qué terminar.
Las pantallas del aula reciben los parámetros de sus rutas padre
(`paramsInheritanceStrategy: 'always'` en `app.config.ts`).

**Datos de ejemplo.** Mientras no exista la API de contenido (B-04), los
cursos salen de `features/cursos/datos/datos-ejemplo.ts` y el avance de cada
usuario de ejemplo (los mismos de `api/app/datos_ejemplo.py`) se calcula con
`armarCurso()`. En el menú de usuario, «Probar como» cambia de usuario: Ana va
en el módulo 5, Bruno no ha empezado, Carla (instructora) va a mitad del 7 y
Diego (admin) terminó. Panel y Administración solo se muestran a su rol; las
guardias de ruta y la sesión real son de la F-03, que también quita «Probar
como».

**Adaptable.** Celular hasta 599 px (desde 360), tableta hasta 1023 y
escritorio desde 1024. Por debajo de 840 px el menú pasa al botón ☰; por
debajo de 1024 la barra lateral es un panel «Módulos» que atrapa el foco, se
cierra con Esc y devuelve el foco al botón. En celular las migas se reducen al
enlace de la página de arriba.

**Íconos.** Material Symbols como trazos SVG dentro de `shared/icono.ts` (sin
fuente ni descargas, porque la plataforma solo se abre por VPN). Para agregar
uno, copia el `d` del SVG del paquete `@material-symbols/svg-400`.

**Accesibilidad (WCAG 2.2 AA).** Foco visible en todos los controles
(`mat.strong-focus-indicators` y `:focus-visible`), estados con ícono y texto,
`aria-current="page"` en la página actual y foco al contenido al cambiar de
página. Las pruebas pasan axe por cada pantalla (`src/testing/axe.ts`); el
contraste no se puede medir en jsdom y se revisa en el navegador.

## Idiomas

Los textos de la interfaz están en `public/i18n/es.json` y `en.json`. Una
prueba exige que los dos tengan las mismas claves y ningún texto vacío, así que
toda clave nueva va en ambos.

El idioma inicial es el que el usuario eligió antes en ese navegador; si no, el
del navegador, y si no, español. Cambiarlo con el selector ES/EN cambia los
textos y el título de la pestaña sin recargar. Cuando exista la sesión, el del
perfil (`GET /api/me`) mandará sobre los demás.

## Imagen

El `Dockerfile` tiene una etapa `dev` (la de `deploy/compose.dev.yaml`, con
`ng serve`) y la imagen que se publica: compila con `node:24-alpine` y sirve el
resultado con `nginxinc/nginx-unprivileged` (sin root, puerto 8080).
`nginx.conf` solo sirve la app; TLS, cabeceras de seguridad y `/api` van en el
nginx de borde de `deploy/`.

Para probar la imagen publicada en local, desde la raíz del repo:

```bash
docker compose -f deploy/compose.dev.yaml up -d --build web-imagen   # http://127.0.0.1:8080
docker compose -f deploy/compose.dev.yaml ps                          # health: starting y luego healthy
docker compose -f deploy/compose.dev.yaml --profile imagenes down
```

## Convenciones

- Prefijo `at` (apolo-training) en selectores: `<at-shell>`, `[atAlgo]`.
- Componentes `OnPush`, `inject()` en vez de constructor y `input()` /
  `output()` con signals; ESLint lo exige.
- Formato con prettier (`.prettierrc.json`, solo afecta a `web/`).
