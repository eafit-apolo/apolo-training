import type { Route } from '@angular/router';

/**
 * Ruta provisional: título traducido en la pestaña y PaginaPendiente, cargada
 * aparte. Cuando llegue la pantalla real, se reemplaza por su `loadComponent`.
 */
export function pendiente(path: string, clave: string, mensaje?: string): Route {
  return {
    path,
    title: clave,
    data: mensaje ? { titulo: clave, mensaje } : { titulo: clave },
    loadComponent: () => import('./pagina-pendiente').then((m) => m.PaginaPendiente),
  };
}
