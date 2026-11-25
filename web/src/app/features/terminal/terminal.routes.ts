import type { Routes } from '@angular/router';

// La terminal real en su propia pestaña (T-06), desde «Abrir en otra pestaña».
export default [
  {
    path: '',
    title: 'paginas.terminal',
    loadComponent: () => import('./pagina-terminal').then((m) => m.PaginaTerminal),
  },
] satisfies Routes;
