import type { Routes } from '@angular/router';
import { GraduacionesPanel } from './graduaciones';
import { Panel } from './panel';
import { ResumenPanel } from './resumen';
import { VideosPanel } from './videos';

// Pantalla 05 (instructor y admin; la guardia está en app.routes.ts). Las tres
// pestañas son rutas hijas de `at-panel`, que tiene la cabecera y el CSV.
export default [
  {
    path: '',
    component: Panel,
    children: [
      { path: '', title: 'paginas.panel', component: ResumenPanel },
      { path: 'graduaciones', title: 'paginas.graduaciones', component: GraduacionesPanel },
      { path: 'videos', title: 'paginas.videos', component: VideosPanel },
    ],
  },
] satisfies Routes;
