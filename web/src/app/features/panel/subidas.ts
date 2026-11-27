import { DOCUMENT } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, InjectionToken, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { CABECERA_CSRF, COOKIE_CSRF, leerCookie } from '../../core/sesion/cookies';
import { API } from '../../core/sesion/sesion';
import type { Destino, VideoAdminApi } from './datos';

/**
 * Crea el `XMLHttpRequest` de cada subida; las pruebas lo reemplazan por uno
 * de mentira (como `CREAR_WEBSOCKET` en la terminal).
 *
 * Las subidas van por XHR y no por HttpClient: la app usa `withFetch()` (lo
 * necesita el `keepalive` del reproductor, F-05) y con fetch el navegador no
 * informa cuánto se ha subido (Angular lanza el error 2824 si se le pide). El
 * `HttpXhrBackend` de Angular sí lo informa, pero suma 3 kB al bundle inicial;
 * este XHR vive solo en el chunk del panel.
 */
export const CREAR_XHR = new InjectionToken<() => XMLHttpRequest>('CREAR_XHR', {
  providedIn: 'root',
  factory: () => () => new XMLHttpRequest(),
});

export type EventoSubida =
  | { readonly tipo: 'progreso'; readonly cargado: number; readonly total: number }
  | { readonly tipo: 'listo'; readonly video: VideoAdminApi };

/** `XMLHttpRequest.DONE`, sin depender del global (las pruebas usan uno de mentira). */
const TERMINADO = 4;

/**
 * `PUT /api/panel/videos/{clave}` y `.../subtitulos/{idioma}` (B-05): el
 * archivo como cuerpo del PUT, sin formulario, con el progreso de la subida.
 *
 * No pasa por el interceptor de sesión: el CSRF se pone aquí, y la pantalla
 * comprueba la sesión antes de empezar (reenviar 2 GB por una renovación sería
 * peor). Los errores llegan como `HttpErrorResponse`, igual que los de
 * HttpClient (`codigoDeError`, `estadoDeError`). Cancelar = dejar de escuchar
 * el Observable: el XHR se aborta.
 */
@Injectable({ providedIn: 'root' })
export class SubidasApi {
  private readonly crear = inject(CREAR_XHR);
  private readonly documento = inject(DOCUMENT);

  subir(clave: string, destino: Destino, archivo: File): Observable<EventoSubida> {
    const base = `${API}/panel/videos/${encodeURIComponent(clave)}`;
    const url = destino === 'video' ? base : `${base}/subtitulos/${destino}`;
    return new Observable<EventoSubida>((suscriptor) => {
      const xhr = this.crear();
      xhr.open('PUT', url);
      xhr.setRequestHeader('Content-Type', destino === 'video' ? 'video/mp4' : 'text/vtt');
      const csrf = leerCookie(this.documento, COOKIE_CSRF);
      if (csrf !== null) {
        xhr.setRequestHeader(CABECERA_CSRF, csrf);
      }
      xhr.upload.onprogress = (evento) => {
        suscriptor.next({
          tipo: 'progreso',
          cargado: evento.loaded,
          total: evento.lengthComputable ? evento.total : archivo.size,
        });
      };
      xhr.onload = () => {
        const cuerpo = leerJson(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          suscriptor.next({ tipo: 'listo', video: cuerpo as VideoAdminApi });
          suscriptor.complete();
        } else {
          suscriptor.error(
            new HttpErrorResponse({
              status: xhr.status,
              statusText: xhr.statusText,
              error: cuerpo,
              url,
            }),
          );
        }
      };
      // Sin respuesta (red caída, VPN apagada): status 0, como HttpClient.
      xhr.onerror = () => suscriptor.error(new HttpErrorResponse({ status: 0, url }));
      xhr.send(archivo);
      return () => {
        if (xhr.readyState !== TERMINADO) {
          xhr.abort();
        }
      };
    });
  }
}

function leerJson(texto: string): unknown {
  try {
    return texto ? JSON.parse(texto) : null;
  } catch {
    return texto;
  }
}
