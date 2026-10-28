import type { Idioma } from '../../core/i18n/idioma';

/** Correo de soporte del wireframe 01 (A-11): «¿Olvidaste tu contraseña?» y cuenta dada de baja. */
export const CORREO_SOPORTE = 'apolo@eafit.edu.co';

/**
 * Formato regional para el idioma de la interfaz: el del navegador si es del
 * mismo idioma (`es-CO` → 3:42 p. m., `es-ES` → 15:42), y si no, el idioma
 * solo.
 */
export function regionDe(idioma: Idioma, preferidos: readonly string[]): string {
  return preferidos.find((p) => p.toLowerCase().split('-')[0] === idioma) ?? idioma;
}

export interface Desbloqueo {
  /**
   * Hora local con la diferencia con UTC («3:42 p. m. GMT-5»), para quien esté
   * en otro país: «GMT-5» se entiende en cualquier parte; «COT» no.
   */
  readonly hora: string;
  /** Minutos que faltan, redondeados hacia arriba (al menos 1). */
  readonly minutos: number;
}

/** Cuándo se puede volver a intentar, a partir de `bloqueado_hasta` de la API. */
export function desbloqueo(hasta: Date, ahora: Date, region: string): Desbloqueo {
  const opciones: Intl.DateTimeFormatOptions = {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'shortOffset',
  };
  let hora: string;
  try {
    hora = new Intl.DateTimeFormat(region, opciones).format(hasta);
  } catch {
    // Una región que Intl no conoce: el formato por defecto del navegador.
    hora = new Intl.DateTimeFormat(undefined, opciones).format(hasta);
  }
  const minutos = Math.max(1, Math.ceil((hasta.getTime() - ahora.getTime()) / 60_000));
  return { hora, minutos };
}
