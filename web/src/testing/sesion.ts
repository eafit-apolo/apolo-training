import type { WritableSignal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import type { Usuario } from '../app/core/sesion/sesion';
import { SesionService } from '../app/core/sesion/sesion';

// Los usuarios de ejemplo de la API (api/app/datos_ejemplo.py), con el nombre
// corto. Bruno debe cambiar la clave y tiene el perfil en inglés, como allá.
export const ANA: Usuario = {
  username: 'ana',
  nombre: 'Ana',
  cluster: 'apolo2',
  rol: 'estudiante',
  idioma: 'es',
  debe_cambiar_clave: false,
  activo: true,
};
export const BRUNO: Usuario = {
  username: 'bruno',
  nombre: 'Bruno',
  cluster: 'apolo3',
  rol: 'estudiante',
  idioma: 'en',
  debe_cambiar_clave: true,
  activo: true,
};
export const CARLA: Usuario = {
  username: 'carla',
  nombre: 'Carla',
  cluster: 'apolo3',
  rol: 'instructor',
  idioma: 'es',
  debe_cambiar_clave: false,
  activo: true,
};
export const DIEGO: Usuario = {
  username: 'diego',
  nombre: 'Diego',
  cluster: 'apolo2',
  rol: 'admin',
  idioma: 'es',
  debe_cambiar_clave: false,
  activo: true,
};

/**
 * Deja a `usuario` como sesión actual sin pasar por la API ni cambiar el
 * idioma (reemplaza a «Probar como» de la F-02 en las pruebas).
 */
export function entrarComo(usuario: Usuario | null): void {
  const sesion = TestBed.inject(SesionService) as unknown as {
    actual: WritableSignal<Usuario | null>;
  };
  sesion.actual.set(usuario);
}

/** Pone la cookie `csrf` (legible en jsdom, como en el navegador). */
export function ponerCsrf(valor: string): void {
  document.cookie = `csrf=${valor}; path=/`;
}

export function borrarCookies(): void {
  for (const parte of document.cookie.split(';')) {
    const nombre = parte.split('=')[0].trim();
    if (nombre) {
      document.cookie = `${nombre}=; max-age=0; path=/`;
    }
  }
}

/** Escribe en un `<input>` como lo haría la persona (evento `input`). */
export function escribir(raiz: HTMLElement, selector: string, valor: string): void {
  const campo = raiz.querySelector<HTMLInputElement>(selector);
  if (!campo) {
    throw new Error(`No hay campo «${selector}»`);
  }
  campo.value = valor;
  campo.dispatchEvent(new Event('input'));
}

/** El botón (o enlace con aspecto de botón) cuyo texto es `texto`. */
export function botonCon(raiz: HTMLElement, texto: string): HTMLElement {
  const encontrado = Array.from(raiz.querySelectorAll<HTMLElement>('button, a')).find(
    (b) => b.textContent?.trim() === texto,
  );
  if (!encontrado) {
    throw new Error(`No hay botón «${texto}»`);
  }
  return encontrado;
}

/** Cuerpo de error de la API: `{"detail", "codigo"}` y campos extra. */
export function errorApi(codigo: string, extra: Record<string, unknown> = {}) {
  return { detail: codigo, codigo, ...extra };
}
