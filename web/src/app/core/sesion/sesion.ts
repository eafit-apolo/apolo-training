import { HttpClient } from '@angular/common/http';
import { DOCUMENT, Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import type { Idioma } from '../i18n/idioma';
import { IdiomaService } from '../i18n/idioma';
import { COOKIE_CSRF, leerCookie } from './cookies';
import { rutaInterna } from './rutas';

export type Cluster = 'apolo2' | 'apolo3';
export type Rol = 'estudiante' | 'instructor' | 'admin';

/** Esquema `Usuario` de api/openapi.yaml: el perfil de `GET /api/me`. */
export interface Usuario {
  readonly username: string;
  readonly nombre: string;
  readonly correo?: string | null;
  readonly cluster: Cluster;
  readonly rol: Rol;
  readonly idioma: Idioma;
  readonly debe_cambiar_clave: boolean;
  readonly activo: boolean;
}

interface LoginSalida {
  readonly usuario: Usuario;
}

/** Prefijo de la API: mismo origen (nginx en la 117, proxy de `ng serve` en local). */
export const API = '/api';

/**
 * La sesión del usuario (B-03). Las cookies las maneja el navegador: `at` y
 * `rt` son `HttpOnly` y la app nunca las ve; solo lee `csrf` (interceptor.ts).
 * Aquí queda el perfil de `GET /api/me`, del que salen el nombre, el rol (menú
 * y guardias), el clúster y el idioma.
 */
@Injectable({ providedIn: 'root' })
export class SesionService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly documento = inject(DOCUMENT);
  private readonly idioma = inject(IdiomaService);
  private readonly actual = signal<Usuario | null>(null);

  readonly usuario = this.actual.asReadonly();
  readonly rol = computed(() => this.actual()?.rol ?? null);

  /**
   * Al arrancar la app: si hay sesión, carga el perfil y su idioma. Sin la
   * cookie `csrf` (dura lo mismo que `rt`) no hay sesión que renovar, así que
   * no llama a la API. Si `at` venció, el interceptor renueva y repite.
   */
  async iniciar(): Promise<void> {
    if (leerCookie(this.documento, COOKIE_CSRF) === null) {
      return;
    }
    try {
      await this.entrar(await firstValueFrom(this.http.get<Usuario>(`${API}/me`)));
    } catch {
      this.actual.set(null);
    }
  }

  /** `POST /api/auth/login`. Los errores (`clave_incorrecta`…) los muestra la pantalla. */
  async ingresar(username: string, clave: string): Promise<Usuario> {
    const { usuario } = await firstValueFrom(
      this.http.post<LoginSalida>(`${API}/auth/login`, { username, clave }),
    );
    await this.entrar(usuario);
    return usuario;
  }

  /** `POST /api/auth/cambiar-clave` y el perfil otra vez (ya sin `debe_cambiar_clave`). */
  async cambiarClave(claveActual: string, claveNueva: string): Promise<Usuario> {
    await firstValueFrom(
      this.http.post<null>(`${API}/auth/cambiar-clave`, {
        clave_actual: claveActual,
        clave_nueva: claveNueva,
      }),
    );
    const usuario = await firstValueFrom(this.http.get<Usuario>(`${API}/me`));
    this.actual.set(usuario);
    return usuario;
  }

  /** `POST /api/auth/logout` (204 aunque ya no haya sesión) y a /ingresar, falle o no. */
  async salir(): Promise<void> {
    try {
      await firstValueFrom(this.http.post<null>(`${API}/auth/logout`, null));
    } catch (error) {
      console.warn('No se pudo cerrar la sesión en la API', error);
    }
    this.actual.set(null);
    await this.router.navigateByUrl('/ingresar');
  }

  /**
   * Cambia la interfaz al instante y, con sesión, lo guarda en el perfil
   * (`PATCH /api/me`, que también funciona con `debe_cambiar_clave`). Si el
   * PATCH falla, la interfaz queda en el idioma elegido igual.
   */
  async cambiarIdioma(idioma: Idioma): Promise<void> {
    await this.idioma.cambiar(idioma);
    const usuario = this.actual();
    if (!usuario || usuario.idioma === idioma) {
      return;
    }
    this.actual.set({ ...usuario, idioma });
    try {
      await firstValueFrom(this.http.patch<Usuario>(`${API}/me`, { idioma }));
    } catch (error) {
      const ahora = this.actual();
      if (ahora?.idioma === idioma) {
        this.actual.set({ ...ahora, idioma: usuario.idioma });
      }
      console.warn('No se pudo guardar el idioma en el perfil', error);
    }
  }

  /**
   * El interceptor no pudo renovar la sesión: se olvida el perfil y se va a
   * /ingresar con «Tu sesión terminó» y la página para volver. Al arrancar la
   * app (antes de la primera navegación) solo se olvida: las guardias llevan a
   * /ingresar.
   */
  vencida(): void {
    this.actual.set(null);
    const url = this.router.url;
    if (!this.router.navigated || url.startsWith('/ingresar')) {
      return;
    }
    const volver = rutaInterna(url);
    void this.router.navigate(['/ingresar'], {
      queryParams: volver ? { motivo: 'vencida', volver } : { motivo: 'vencida' },
    });
  }

  /** La API respondió 403 `debe_cambiar_clave` (le reiniciaron la clave): a /cambiar-clave. */
  exigirCambio(): void {
    const usuario = this.actual();
    if (usuario && !usuario.debe_cambiar_clave) {
      this.actual.set({ ...usuario, debe_cambiar_clave: true });
    }
    if (this.router.navigated && !this.router.url.startsWith('/cambiar-clave')) {
      void this.router.navigateByUrl('/cambiar-clave');
    }
  }

  /** Con sesión manda el idioma del perfil (decisión del 28-oct). */
  private async entrar(usuario: Usuario): Promise<void> {
    this.actual.set(usuario);
    await this.idioma.cambiar(usuario.idioma);
  }
}
