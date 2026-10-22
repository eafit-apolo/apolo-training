import type {
  ContenidoCurso,
  ContenidoModulo,
  Curso,
  EstadoModulo,
  Leccion,
  Modulo,
} from './curso';

/** `m05` para el módulo 5, como las carpetas de `content/es/`. */
export function idModulo(numero: number): string {
  return `m${String(numero).padStart(2, '0')}`;
}

function suma<T>(lista: readonly T[], valor: (item: T) => number): number {
  return lista.reduce((total, item) => total + valor(item), 0);
}

function armarModulo(
  contenido: ContenidoModulo,
  completas: ReadonlySet<string>,
  anteriorCompleto: boolean,
): Modulo {
  const id = idModulo(contenido.numero);
  const lecciones: Leccion[] = contenido.lecciones.map((l, i) => ({
    id: `${id}/${l.slug}`,
    modulo: id,
    slug: l.slug,
    numero: `${contenido.numero}.${i + 1}`,
    titulo: l.titulo,
    duracion: l.duracion,
    completa: anteriorCompleto && completas.has(`${id}/${l.slug}`),
  }));
  const hechas = lecciones.filter((l) => l.completa).length;
  let estado: EstadoModulo = 'en-curso';
  if (!anteriorCompleto) {
    estado = 'bloqueado';
  } else if (hechas === lecciones.length) {
    estado = 'completo';
  }
  return {
    id,
    numero: contenido.numero,
    titulo: contenido.titulo,
    resumen: contenido.resumen,
    duracion: suma(contenido.lecciones, (l) => l.duracion),
    videos: contenido.lecciones.filter((l) => l.video).length,
    practicas: suma(contenido.lecciones, (l) => l.practicas),
    preguntas: suma(contenido.lecciones, (l) => l.preguntas),
    estado,
    lecciones,
    hechas,
  };
}

/**
 * Arma el curso con el estado de cada módulo a partir de las lecciones
 * completas (`mNN/slug`). Es la regla de la B-04: el módulo n+1 se abre al
 * completar el n. Una lección marcada en un módulo bloqueado no cuenta.
 */
export function armarCurso(contenido: ContenidoCurso, completas: ReadonlySet<string>): Curso {
  const modulos: Modulo[] = [];
  let anteriorCompleto = true;
  for (const m of contenido.modulos) {
    const modulo = armarModulo(m, completas, anteriorCompleto);
    modulos.push(modulo);
    anteriorCompleto = modulo.estado === 'completo';
  }
  const lecciones = modulos.flatMap((m) => m.lecciones);
  const hechas = lecciones.filter((l) => l.completa).length;
  const enCurso = modulos.find((m) => m.estado === 'en-curso');
  return {
    id: contenido.id,
    titulo: contenido.titulo,
    descripcion: contenido.descripcion,
    duracion: suma(modulos, (m) => m.duracion),
    videos: suma(modulos, (m) => m.videos),
    modulos,
    modulosCompletos: modulos.filter((m) => m.estado === 'completo').length,
    avance: lecciones.length ? Math.round((100 * hechas) / lecciones.length) : 0,
    continuar: enCurso?.lecciones.find((l) => !l.completa) ?? null,
    empezado: hechas > 0,
  };
}

/** Ruta de la app de un módulo o de una lección. */
export function rutaModulo(curso: string, modulo: string): string[] {
  return ['/cursos', curso, modulo];
}

export function rutaLeccion(curso: string, leccion: Leccion): string[] {
  return ['/cursos', curso, leccion.modulo, leccion.slug];
}
