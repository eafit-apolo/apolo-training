import type { Routes } from '@angular/router';
import { pendiente } from '../../shared/pendiente';

// Pantalla 05 (instructor y admin).
export default [
  pendiente('', 'paginas.panel'),
  pendiente('graduaciones', 'paginas.graduaciones'),
  pendiente('videos', 'paginas.videos'),
] satisfies Routes;
