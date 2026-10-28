import type { Routes } from '@angular/router';
import { paraCambiarClave, sinSesion, tituloCambiarClave } from '../../core/sesion/guardias';

// Pantalla 01. Va fuera del menú (app.routes.ts), así que estas rutas se
// importan directo; sus componentes igual se cargan aparte.
export const cuentaRoutes: Routes = [
  {
    path: 'ingresar',
    title: 'paginas.ingresar',
    canActivate: [sinSesion],
    loadComponent: () => import('./ingresar').then((m) => m.Ingresar),
  },
  {
    path: 'cambiar-clave',
    title: tituloCambiarClave,
    canActivate: [paraCambiarClave],
    loadComponent: () => import('./cambiar-clave').then((m) => m.CambiarClave),
  },
];
