import type { CursoDetalleApi, EstadoModuloApi, ModuloApi } from './api';
import type { Curso, EstadoModulo, Leccion, Modulo } from './curso';

const ESTADOS: Record<EstadoModuloApi, EstadoModulo> = {
  completo: 'completo',
  en_curso: 'en-curso',
  bloqueado: 'bloqueado',
};

function armarModulo(api: ModuloApi, puedeVerBloqueados: boolean): Modulo {
  const lecciones: Leccion[] = api.lecciones.map((l, i) => ({
    id: `${api.slug}/${l.slug}`,
    modulo: api.slug,
    slug: l.slug,
    numero: `${api.numero}.${i + 1}`,
    titulo: l.titulo,
    duracion: l.duracion_min,
    completa: l.completada,
  }));
  const estado = ESTADOS[api.estado];
  return {
    id: api.slug,
    numero: api.numero,
    titulo: api.titulo,
    resumen: api.resumen,
    duracion: api.duracion_min,
    videos: api.videos,
    practicas: api.practicas,
    preguntas: api.preguntas,
    estado,
    abierto: estado !== 'bloqueado' || puedeVerBloqueados,
    lecciones,
    hechas: api.lecciones_completas,
  };
}

/**
 * Pasa el curso de la API (B-04) a los tipos de las pantallas. Los estados y
 * el avance los calcula la API con la regla de desbloqueo; aquí solo se
 * numeran las lecciones («5.1») y se marca qué módulos se pueden abrir.
 */
export function armarCurso(api: CursoDetalleApi, puedeVerBloqueados = false): Curso {
  const modulos = api.modulos.map((m) => armarModulo(m, puedeVerBloqueados));
  const continuar = api.continuar;
  return {
    id: api.slug,
    titulo: api.titulo,
    descripcion: api.descripcion ?? '',
    duracion: api.duracion_min,
    videos: api.videos,
    modulos,
    modulosCompletos: api.modulos_completos,
    avance: api.avance_pct,
    continuar: continuar
      ? (modulos
          .find((m) => m.id === continuar.modulo)
          ?.lecciones.find((l) => l.slug === continuar.slug) ?? null)
      : null,
    empezado: api.lecciones_completas > 0,
  };
}

/** Ruta de la app de un módulo o de una lección. */
export function rutaModulo(curso: string, modulo: string): string[] {
  return ['/cursos', curso, modulo];
}

export function rutaLeccion(curso: string, leccion: Leccion): string[] {
  return ['/cursos', curso, leccion.modulo, leccion.slug];
}
