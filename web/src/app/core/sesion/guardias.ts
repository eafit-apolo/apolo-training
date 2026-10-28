import { inject } from '@angular/core';
import type { CanActivateChildFn, CanActivateFn, CanMatchFn, ResolveFn } from '@angular/router';
import { Router } from '@angular/router';
import { rutaInterna } from './rutas';
import type { Rol } from './sesion';
import { SesionService } from './sesion';

/** `?volver=` para las URL de ingreso, salvo cuando es la página de inicio. */
function conVolver(volver: string | null) {
  return volver && volver !== '/cursos' ? { queryParams: { volver } } : {};
}

/**
 * Pantallas con menú (todo menos /ingresar y /cambiar-clave): sin sesión, a
 * /ingresar recordando a dónde iba; con la clave temporal, a /cambiar-clave.
 * Va en `canActivateChild` para revisarse en cada navegación, no solo al
 * entrar al shell.
 */
export const conSesion: CanActivateChildFn = (_ruta, estado) => {
  const usuario = inject(SesionService).usuario();
  const router = inject(Router);
  if (!usuario) {
    return router.createUrlTree(['/ingresar'], conVolver(rutaInterna(estado.url)));
  }
  if (usuario.debe_cambiar_clave) {
    return router.createUrlTree(['/cambiar-clave'], conVolver(rutaInterna(estado.url)));
  }
  return true;
};

/**
 * Secciones de un rol (Panel, Administración). Quien no lo tiene va a /cursos
 * sin descargar el código de esa sección (`canMatch`). Sin sesión deja pasar:
 * `conSesion` lo lleva a /ingresar con la ruta completa en `?volver=`.
 */
export function conRol(...roles: readonly Rol[]): CanMatchFn {
  return () => {
    const rol = inject(SesionService).rol();
    const router = inject(Router);
    return rol === null || roles.includes(rol) ? true : router.createUrlTree(['/cursos']);
  };
}

/** /ingresar: quien ya tiene sesión sigue a donde iba (o a cambiar la clave). */
export const sinSesion: CanActivateFn = (ruta) => {
  const usuario = inject(SesionService).usuario();
  const router = inject(Router);
  if (!usuario) {
    return true;
  }
  const volver = rutaInterna(ruta.queryParamMap.get('volver'));
  if (usuario.debe_cambiar_clave) {
    return router.createUrlTree(['/cambiar-clave'], conVolver(volver));
  }
  return router.parseUrl(volver ?? '/cursos');
};

/** /cambiar-clave: hace falta sesión; sirve para el cambio obligatorio y el voluntario. */
export const paraCambiarClave: CanActivateFn = () => {
  const usuario = inject(SesionService).usuario();
  return usuario ? true : inject(Router).createUrlTree(['/ingresar']);
};

/** «Crea tu contraseña» en el primer ingreso; «Cambiar contraseña» si es voluntario. */
export const tituloCambiarClave: ResolveFn<string> = () =>
  inject(SesionService).usuario()?.debe_cambiar_clave === false
    ? 'paginas.cambiarClaveVoluntario'
    : 'paginas.cambiarClave';
