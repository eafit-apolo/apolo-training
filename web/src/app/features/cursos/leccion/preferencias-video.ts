import { DOCUMENT, Injectable, computed, inject, signal } from '@angular/core';
import type { Idioma } from '../../../core/i18n/idioma';

/** Las velocidades del selector (F-05: de 0.75x a 2x). */
export const VELOCIDADES: readonly number[] = [0.75, 1, 1.25, 1.5, 1.75, 2];

/** `no` (desactivados) o el idioma de la pista. */
export type Subtitulos = 'no' | Idioma;

interface Guardadas {
  readonly velocidad: number;
  /** La elección para cada idioma de la interfaz. */
  readonly subtitulos: Readonly<Record<Idioma, Subtitulos>>;
}

/**
 * Por defecto: velocidad normal; con la interfaz en inglés, subtítulos en
 * inglés, y en español sin subtítulos (el video se habla en español).
 */
const POR_DEFECTO: Guardadas = { velocidad: 1, subtitulos: { es: 'no', en: 'en' } };

const CLAVE_ALMACEN = 'apolo-training.video';

const esSubtitulos = (valor: unknown): valor is Subtitulos =>
  valor === 'no' || valor === 'es' || valor === 'en';

/** Lo guardado, si sirve; lo que no, vuelve al valor por defecto. */
export function leerGuardadas(texto: string | null | undefined): Guardadas {
  let datos: unknown;
  try {
    datos = texto ? JSON.parse(texto) : null;
  } catch {
    datos = null;
  }
  const d = (datos ?? {}) as { velocidad?: unknown; subtitulos?: { es?: unknown; en?: unknown } };
  const { es, en } = d.subtitulos ?? {};
  return {
    velocidad:
      typeof d.velocidad === 'number' && VELOCIDADES.includes(d.velocidad)
        ? d.velocidad
        : POR_DEFECTO.velocidad,
    subtitulos: {
      es: esSubtitulos(es) ? es : POR_DEFECTO.subtitulos.es,
      en: esSubtitulos(en) ? en : POR_DEFECTO.subtitulos.en,
    },
  };
}

/**
 * La velocidad y los subtítulos que eligió el usuario, en este navegador
 * (decisión del 6-nov). Los subtítulos se recuerdan por idioma de la
 * interfaz: al pasar la interfaz a inglés salen los que eligió para inglés.
 */
@Injectable({ providedIn: 'root' })
export class PreferenciasVideo {
  private readonly documento = inject(DOCUMENT);
  private readonly datos = signal<Guardadas>(leerGuardadas(this.leer()));

  readonly velocidad = computed(() => this.datos().velocidad);

  subtitulos(idioma: Idioma): Subtitulos {
    return this.datos().subtitulos[idioma];
  }

  /** Solo las del selector; otra (el menú del navegador ofrece 0.5x) no se guarda. */
  guardarVelocidad(velocidad: number): void {
    if (VELOCIDADES.includes(velocidad)) {
      this.cambiar({ ...this.datos(), velocidad });
    }
  }

  guardarSubtitulos(idioma: Idioma, subtitulos: Subtitulos): void {
    const actual = this.datos();
    this.cambiar({ ...actual, subtitulos: { ...actual.subtitulos, [idioma]: subtitulos } });
  }

  private cambiar(datos: Guardadas): void {
    this.datos.set(datos);
    try {
      this.documento.defaultView?.localStorage.setItem(CLAVE_ALMACEN, JSON.stringify(datos));
    } catch {
      // Sin localStorage (modo privado, cookies bloqueadas) dura hasta recargar.
    }
  }

  private leer(): string | null {
    try {
      return this.documento.defaultView?.localStorage.getItem(CLAVE_ALMACEN) ?? null;
    } catch {
      return null;
    }
  }
}
