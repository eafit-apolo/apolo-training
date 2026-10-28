import type { HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { DOCUMENT, Injectable, inject } from '@angular/core';
import type { Observable } from 'rxjs';
import { catchError, finalize, shareReplay, switchMap, throwError } from 'rxjs';
import { CABECERA_CSRF, COOKIE_CSRF, leerCookie } from './cookies';
import { codigoDeError } from './errores';
import { API, SesionService } from './sesion';

const METODOS_SEGUROS = new Set(['GET', 'HEAD', 'OPTIONS']);

/** Un 401 de estas no se arregla renovando: es la respuesta misma de la sesión. */
const SIN_RENOVAR = new Set([`${API}/auth/login`, `${API}/auth/refresh`, `${API}/auth/logout`]);

/**
 * Renovación compartida: si varias peticiones dan 401 a la vez (por ejemplo,
 * al volver a una pestaña después de 15 min), todas esperan el mismo
 * `POST /api/auth/refresh`. Un 204 sin cookies nuevas (otra pestaña acababa de
 * renovar) también sirve: el navegador ya tiene las vigentes.
 */
@Injectable({ providedIn: 'root' })
export class Renovacion {
  private readonly http = inject(HttpClient);
  private enCurso: Observable<unknown> | null = null;

  renovar(): Observable<unknown> {
    this.enCurso ??= this.http.post(`${API}/auth/refresh`, null).pipe(
      finalize(() => {
        this.enCurso = null;
      }),
      shareReplay(1),
    );
    return this.enCurso;
  }
}

/** `X-CSRF-Token` con el valor de la cookie `csrf`, en todo lo que no sea GET. */
function conCsrf<T>(peticion: HttpRequest<T>, documento: Document): HttpRequest<T> {
  if (METODOS_SEGUROS.has(peticion.method)) {
    return peticion;
  }
  const csrf = leerCookie(documento, COOKIE_CSRF);
  return csrf === null ? peticion : peticion.clone({ setHeaders: { [CABECERA_CSRF]: csrf } });
}

/**
 * Interceptor de la sesión, solo para `/api/…`:
 *
 * 1. Pone `X-CSRF-Token` (la API lo exige en todo lo que no sea GET).
 * 2. Ante un 401, renueva una vez y repite la petición con el CSRF nuevo. Si
 *    la renovación falla, la sesión terminó: `SesionService.vencida()` lleva a
 *    /ingresar y la petición devuelve el 401 original.
 * 3. Ante un 403 `debe_cambiar_clave`, lleva a /cambiar-clave.
 */
export const interceptorSesion: HttpInterceptorFn = (peticion, siguiente) => {
  if (!peticion.url.startsWith(`${API}/`)) {
    return siguiente(peticion);
  }
  const documento = inject(DOCUMENT);
  const renovacion = inject(Renovacion);
  const sesion = inject(SesionService);

  return siguiente(conCsrf(peticion, documento)).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse)) {
        return throwError(() => error);
      }
      if (error.status === 401 && !SIN_RENOVAR.has(peticion.url)) {
        return renovacion.renovar().pipe(
          catchError(() => {
            sesion.vencida();
            return throwError(() => error);
          }),
          switchMap(() => siguiente(conCsrf(peticion, documento))),
        );
      }
      if (error.status === 403 && codigoDeError(error) === 'debe_cambiar_clave') {
        sesion.exigirCambio();
      }
      return throwError(() => error);
    }),
  );
};
