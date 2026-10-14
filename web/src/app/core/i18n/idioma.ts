import { DOCUMENT, Injectable, inject, signal } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';
import { firstValueFrom } from 'rxjs';

export const IDIOMAS = ['es', 'en'] as const;
export type Idioma = (typeof IDIOMAS)[number];
export const IDIOMA_POR_DEFECTO: Idioma = 'es';

const CLAVE_ALMACEN = 'apolo-training.idioma';

export function esIdioma(valor: unknown): valor is Idioma {
  return IDIOMAS.includes(valor as Idioma);
}

/** El primero de los idiomas del navegador que la app tiene; si ninguno, español. */
export function idiomaDelNavegador(preferidos: readonly string[]): Idioma {
  for (const preferido of preferidos) {
    const base = preferido.toLowerCase().split('-')[0];
    if (esIdioma(base)) {
      return base;
    }
  }
  return IDIOMA_POR_DEFECTO;
}

/**
 * Idioma de la interfaz.
 *
 * Al arrancar: el que el usuario eligió antes en este navegador, si no el del
 * navegador y si no español. Cuando exista la sesión, el del perfil
 * (`GET /api/me`) mandará sobre estos y `cambiar()` también lo guardará con
 * `PATCH /api/me`.
 */
@Injectable({ providedIn: 'root' })
export class IdiomaService {
  private readonly transloco = inject(TranslocoService);
  private readonly documento = inject(DOCUMENT);
  private readonly idioma = signal<Idioma>(IDIOMA_POR_DEFECTO);

  readonly actual = this.idioma.asReadonly();

  /** Elige el idioma inicial y espera sus textos, para no mostrar claves al arrancar. */
  iniciar(): Promise<void> {
    return this.aplicar(this.guardado() ?? this.delNavegador());
  }

  /** Cambia los textos sin recargar la página y recuerda la elección. */
  cambiar(idioma: Idioma): Promise<void> {
    this.guardar(idioma);
    return this.aplicar(idioma);
  }

  private async aplicar(idioma: Idioma): Promise<void> {
    this.idioma.set(idioma);
    this.documento.documentElement.lang = idioma;
    this.transloco.setActiveLang(idioma);
    try {
      await firstValueFrom(this.transloco.load(idioma));
    } catch (error) {
      // Sin los textos la app igual arranca; Transloco usa el idioma de respaldo.
      console.error(`No se pudieron cargar los textos en «${idioma}»`, error);
    }
  }

  private delNavegador(): Idioma {
    return idiomaDelNavegador(this.documento.defaultView?.navigator.languages ?? []);
  }

  // localStorage puede faltar o lanzar (modo privado, cookies bloqueadas):
  // en ese caso la elección solo dura hasta recargar.
  private guardado(): Idioma | null {
    try {
      const valor = this.documento.defaultView?.localStorage.getItem(CLAVE_ALMACEN);
      return esIdioma(valor) ? valor : null;
    } catch {
      return null;
    }
  }

  private guardar(idioma: Idioma): void {
    try {
      this.documento.defaultView?.localStorage.setItem(CLAVE_ALMACEN, idioma);
    } catch {
      // Ver guardado().
    }
  }
}
