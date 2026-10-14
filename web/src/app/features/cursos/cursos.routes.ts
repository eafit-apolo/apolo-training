import type { Routes } from '@angular/router';
import { pendiente } from '../../shared/pendiente';

// Pantallas 02 (catálogo) y 03 (lección).
export default [
  pendiente('', 'paginas.catalogo'),
  pendiente(':curso/:modulo/:leccion', 'paginas.leccion'),
] satisfies Routes;
