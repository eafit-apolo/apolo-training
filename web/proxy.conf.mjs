// ng serve envía /api a la API, así la web y la API comparten origen como en
// producción (las cookies de la sesión lo necesitan) y no hace falta CORS.
// Con `npm start` en tu equipo va a localhost:8000; en deploy/compose.dev.yaml,
// API_URL apunta al servicio `api`.
export default {
  '/api': {
    target: process.env.API_URL ?? 'http://localhost:8000',
  },
};
