import type { Routes } from '@angular/router';

// Pantalla 04 (F-07).
export default [
  {
    path: '',
    title: 'paginas.miProgreso',
    loadComponent: () => import('./progreso').then((m) => m.MiProgreso),
  },
] satisfies Routes;
