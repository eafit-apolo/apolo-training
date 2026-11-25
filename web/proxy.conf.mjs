// ng serve envía /api a la API, así la web y la API comparten origen como en
// producción (las cookies de la sesión lo necesitan) y no hace falta CORS.
// Con `npm start` en tu equipo va a localhost:8000; en deploy/compose.dev.yaml,
// API_URL apunta al servicio `api`. /ws (la terminal real, T-06) va al gateway:
// localhost:8002 es el `terminal-imagen` de compose.dev.yaml publicado en tu
// equipo, y TERMINAL_URL apunta a él dentro de Compose.
export default {
  '/api': {
    target: process.env.API_URL ?? 'http://localhost:8000',
  },
  '/ws': {
    target: process.env.TERMINAL_URL ?? 'http://localhost:8002',
    ws: true,
  },
};
