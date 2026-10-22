import type { Routes } from '@angular/router';
import { tituloCurso, tituloLeccion, tituloModulo } from './datos/titulos';

// Pantallas 02 (catálogo y curso) y 03 (módulo y lección, dentro del aula con
// la barra lateral). `:modulo` y `:leccion` son el id del contenido
// (`m05/trabajos`, C-01).
export default [
  {
    path: '',
    title: 'paginas.catalogo',
    loadComponent: () => import('./catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: ':curso',
    title: tituloCurso,
    loadComponent: () => import('./curso/curso').then((m) => m.Curso),
  },
  {
    path: ':curso/:modulo',
    loadComponent: () => import('./aula/aula').then((m) => m.Aula),
    children: [
      {
        path: '',
        title: tituloModulo,
        loadComponent: () => import('./modulo/modulo').then((m) => m.Modulo),
      },
      {
        path: ':leccion',
        title: tituloLeccion,
        loadComponent: () => import('./leccion/leccion').then((m) => m.Leccion),
      },
    ],
  },
] satisfies Routes;
