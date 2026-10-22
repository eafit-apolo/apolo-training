/**
 * Tipos del catálogo tal como los usan las pantallas. El contenido sale de
 * `content/` (C-01) y el avance, del usuario. Mientras no exista la API de
 * contenido (B-04) se arman en el navegador con `armarCurso()`; con la B-04
 * los traerá la API y estos tipos se alinean con `api/openapi.yaml`.
 */

/** Una lección como está en `content/es/mNN/<slug>.md`. */
export interface ContenidoLeccion {
  readonly slug: string;
  readonly titulo: string;
  /** Minutos. */
  readonly duracion: number;
  readonly video: boolean;
  /** Prácticas verificadas con `apolo-training verificar` (la graduación cuenta como una). */
  readonly practicas: number;
  readonly preguntas: number;
}

/** Un módulo como está en `content/es/mNN/_modulo.md`, con sus lecciones en orden. */
export interface ContenidoModulo {
  readonly numero: number;
  readonly titulo: string;
  readonly resumen: string;
  readonly lecciones: readonly ContenidoLeccion[];
}

export interface ContenidoCurso {
  readonly id: string;
  readonly titulo: string;
  readonly descripcion: string;
  readonly modulos: readonly ContenidoModulo[];
}

/**
 * El módulo n+1 se abre al completar el n (B-04), así que hay a lo sumo un
 * módulo «en curso»: el primero sin terminar.
 */
export type EstadoModulo = 'completo' | 'en-curso' | 'bloqueado';

export interface Leccion {
  /** `mNN/slug`: el id del contenido, que también es su ruta. */
  readonly id: string;
  readonly modulo: string;
  readonly slug: string;
  /** «5.1»: número del módulo y posición de la lección. */
  readonly numero: string;
  readonly titulo: string;
  readonly duracion: number;
  readonly completa: boolean;
}

export interface Modulo {
  /** `mNN`. */
  readonly id: string;
  readonly numero: number;
  readonly titulo: string;
  readonly resumen: string;
  readonly duracion: number;
  readonly videos: number;
  readonly practicas: number;
  readonly preguntas: number;
  readonly estado: EstadoModulo;
  readonly lecciones: readonly Leccion[];
  /** Lecciones completas. */
  readonly hechas: number;
}

export interface Curso {
  readonly id: string;
  readonly titulo: string;
  readonly descripcion: string;
  readonly duracion: number;
  readonly videos: number;
  readonly modulos: readonly Modulo[];
  readonly modulosCompletos: number;
  /** Porcentaje de lecciones completas, de 0 a 100. */
  readonly avance: number;
  /** Primera lección sin completar del módulo en curso; `null` si terminó el curso. */
  readonly continuar: Leccion | null;
  readonly empezado: boolean;
}
