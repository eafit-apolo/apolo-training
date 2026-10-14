import type { Routes } from '@angular/router';
import { pendiente } from '../../shared/pendiente';

// Pantalla 06 (solo admin).
export default [
  { path: '', pathMatch: 'full', redirectTo: 'usuarios' },
  pendiente('usuarios', 'paginas.usuarios'),
  pendiente('qos', 'paginas.qos'),
] satisfies Routes;
