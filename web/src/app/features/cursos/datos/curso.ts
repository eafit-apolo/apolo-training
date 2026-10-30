/**
 * Tipos del catálogo tal como los usan las pantallas. Salen de la API de
 * contenido (B-04, `GET /api/cursos/{curso}`) con `armarCurso()`.
 */

/**
 * El módulo n+1 se abre al completar el n, así que hay a lo sumo un módulo
 * «en curso»: el primero sin terminar.
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
  /**
   * Si se puede entrar: no está bloqueado, o el usuario es instructor o
   * admin, que abren los bloqueados para revisar el contenido.
   */
  readonly abierto: boolean;
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
  /** La siguiente lección por hacer (la primera si no ha empezado); `null` si terminó. */
  readonly continuar: Leccion | null;
  readonly empezado: boolean;
}
