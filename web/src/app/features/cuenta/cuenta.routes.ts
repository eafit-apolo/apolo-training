import type { Routes } from '@angular/router';
import { pendiente } from '../../shared/pendiente';

// Pantalla 01. Va fuera del menú (app.routes.ts), así que estas rutas se
// importan directo; sus componentes igual se cargan aparte.
export const cuentaRoutes: Routes = [
  pendiente('ingresar', 'paginas.ingresar'),
  pendiente('cambiar-clave', 'paginas.cambiarClave'),
];
