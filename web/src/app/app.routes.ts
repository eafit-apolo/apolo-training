import type { Routes } from '@angular/router';
import { Shell } from './core/layout/shell';
import { conRol, conSesion } from './core/sesion/guardias';
import { cuentaRoutes } from './features/cuenta/cuenta.routes';
import { pendiente } from './shared/pendiente';

// Rutas de docs/diseno/pantallas.md. Cada sección se carga aparte (lazy).
export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'cursos' },
  // Pantalla 01, sin menú. Si la URL no es de cuenta, el router sigue con la
  // siguiente ruta vacía.
  { path: '', component: Shell, data: { sinMenu: true }, children: cuentaRoutes },
  {
    path: '',
    component: Shell,
    // Todo lo que tiene menú pide sesión (F-03); Panel y Administración, además, su rol.
    canActivateChild: [conSesion],
    children: [
      { path: 'cursos', loadChildren: () => import('./features/cursos/cursos.routes') },
      { path: 'mi-progreso', loadChildren: () => import('./features/progreso/progreso.routes') },
      {
        path: 'panel',
        canMatch: [conRol('instructor', 'admin')],
        loadChildren: () => import('./features/panel/panel.routes'),
      },
      {
        path: 'admin',
        canMatch: [conRol('admin')],
        loadChildren: () => import('./features/admin/admin.routes'),
      },
      pendiente('**', 'paginas.noEncontrada', 'noEncontrada.mensaje'),
    ],
  },
];
