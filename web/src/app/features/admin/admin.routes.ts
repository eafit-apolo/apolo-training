import type { ResolveFn, Routes } from '@angular/router';
import { tituloLiteral } from '../../core/i18n/titulo';
import { Administracion } from './admin';
import { QosAdmin } from './qos';
import { UsuarioAdmin } from './usuario';
import { UsuariosAdmin } from './usuarios';

/** Título de la pestaña del navegador: el username. */
const tituloUsuario: ResolveFn<string> = (ruta) =>
  tituloLiteral(ruta.paramMap.get('usuario') ?? '');

// Pantalla 06 (solo admin; la guardia está en app.routes.ts). Las pestañas son
// rutas hijas de `at-admin`; la página de un usuario cuelga de «Usuarios».
export default [
  {
    path: '',
    component: Administracion,
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'usuarios' },
      { path: 'usuarios', title: 'paginas.usuarios', component: UsuariosAdmin },
      { path: 'usuarios/:usuario', title: tituloUsuario, component: UsuarioAdmin },
      { path: 'qos', title: 'paginas.qos', component: QosAdmin },
    ],
  },
] satisfies Routes;
