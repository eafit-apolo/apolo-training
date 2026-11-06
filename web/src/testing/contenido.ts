import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Provider } from '@angular/core';
import type { Rol } from '../app/core/sesion/sesion';
import { SesionService } from '../app/core/sesion/sesion';
import type {
  CursoDetalleApi,
  CursoResumenApi,
  LeccionApi,
  LeccionRefApi,
  ModuloApi,
  ModuloRefApi,
  Practica,
  ProgresoLeccionApi,
  ProgresoVideoEntradaApi,
  VideoLeccionApi,
} from '../app/features/cursos/datos/api';
import { ContenidoApi } from '../app/features/cursos/datos/api';
import { MUESTRA_EN, MUESTRA_ES } from './leccion-muestra';

// Los datos de ejemplo de la F-02, ahora solo para las pruebas: con ellos se
// arma lo que respondería la API de contenido (B-04) a cada usuario de ejemplo.

interface ContenidoLeccion {
  readonly slug: string;
  readonly titulo: string;
  readonly duracion: number;
  readonly video: boolean;
  readonly practicas: number;
  readonly preguntas: number;
}

interface ContenidoModulo {
  readonly numero: number;
  readonly titulo: string;
  readonly resumen: string;
  readonly lecciones: readonly ContenidoLeccion[];
}

interface ContenidoCurso {
  readonly id: string;
  readonly titulo: string;
  readonly descripcion: string;
  readonly modulos: readonly ContenidoModulo[];
}

/**
 * 9 módulos, 82 min, 24 preguntas y 7 prácticas, como content/mapa.md. Las
 * lecciones, sus títulos y sus minutos son de ejemplo.
 */
const CURSOS_EJEMPLO: readonly ContenidoCurso[] = [
  {
    id: 'induccion',
    titulo: 'Curso de inducción a Apolo',
    descripcion:
      'Conéctate, mueve tus archivos, carga software y envía trabajos a Slurm, practicando en una máquina real.',
    modulos: [
      {
        numero: 0,
        titulo: 'Bienvenida',
        resumen:
          'Qué es Apolo, en qué se diferencian Apolo II y Apolo III, por qué el nodo de login no es para calcular y cómo funciona el curso.',
        lecciones: [
          {
            slug: 'bienvenida',
            titulo: 'Bienvenida a Apolo',
            duracion: 5,
            video: true,
            practicas: 0,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 1,
        titulo: 'Conexión',
        resumen:
          'La VPN de EAFIT en tu sistema operativo y la conexión por SSH al login de tu clúster.',
        lecciones: [
          {
            slug: 'vpn',
            titulo: 'La VPN de EAFIT',
            duracion: 6,
            video: true,
            practicas: 0,
            preguntas: 1,
          },
          {
            slug: 'ssh',
            titulo: 'Entrar por SSH',
            duracion: 6,
            video: true,
            practicas: 1,
            preguntas: 1,
          },
        ],
      },
      {
        numero: 2,
        titulo: 'Terminal y Linux',
        resumen:
          'Moverte por tus carpetas, ver y buscar archivos con grep y guardar la salida de un comando.',
        lecciones: [
          {
            slug: 'terminal',
            titulo: 'La terminal de Linux',
            duracion: 11,
            video: true,
            practicas: 1,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 3,
        titulo: 'Archivos y transferencia',
        resumen: 'Tu home y su cuota, y cómo subir y bajar archivos con scp o con FileZilla.',
        lecciones: [
          {
            slug: 'archivos',
            titulo: 'Tus archivos en el clúster',
            duracion: 10,
            video: true,
            practicas: 1,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 4,
        titulo: 'Software con módulos',
        resumen: 'Buscar y cargar software con module avail, spider y load.',
        lecciones: [
          {
            slug: 'modulos',
            titulo: 'Software con módulos',
            duracion: 8,
            video: true,
            practicas: 1,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 5,
        titulo: 'Trabajos con Slurm',
        resumen:
          'Escribir un script de Slurm, enviarlo a una partición y seguirlo con squeue y sacct.',
        lecciones: [
          {
            slug: 'trabajos',
            titulo: 'Tu primer trabajo con Slurm',
            duracion: 12,
            video: true,
            practicas: 1,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 6,
        titulo: 'Núcleos y paralelismo',
        resumen: 'Núcleos reservados frente a núcleos usados, y cómo medir la eficiencia.',
        lecciones: [
          {
            slug: 'paralelismo',
            titulo: 'Núcleos y paralelismo',
            duracion: 10,
            video: true,
            practicas: 2,
            preguntas: 2,
          },
        ],
      },
      {
        numero: 7,
        titulo: 'VS Code y graduación',
        resumen:
          'Editar con VS Code por Remote-SSH sin calcular en el login, y tu trabajo de graduación en el clúster real.',
        lecciones: [
          {
            slug: 'vscode',
            titulo: 'VS Code con Remote-SSH',
            duracion: 5,
            video: true,
            practicas: 0,
            preguntas: 2,
          },
          {
            slug: 'graduacion',
            titulo: 'Tu graduación',
            duracion: 4,
            video: false,
            practicas: 1,
            preguntas: 0,
          },
        ],
      },
      {
        numero: 8,
        titulo: 'Cierre y quiz final',
        resumen: 'Cómo pedir ayuda (siempre con el JobID), qué sigue y el quiz final.',
        lecciones: [
          {
            slug: 'cierre',
            titulo: 'Cierre y quiz final',
            duracion: 5,
            video: false,
            practicas: 0,
            preguntas: 8,
          },
        ],
      },
    ],
  },
];

const HASTA_EL_MODULO_4 = [
  'm00/bienvenida',
  'm01/vpn',
  'm01/ssh',
  'm02/terminal',
  'm03/archivos',
  'm04/modulos',
];
const HASTA_EL_MODULO_6 = [...HASTA_EL_MODULO_4, 'm05/trabajos', 'm06/paralelismo'];

/**
 * Lecciones completas de cada usuario de ejemplo: Ana va en el módulo 5 (como
 * en docs/diseno/pantallas.md), Bruno no ha empezado, Carla va a la mitad del
 * módulo 7 y Diego terminó.
 */
export const PROGRESO_EJEMPLO: Readonly<Record<string, readonly string[]>> = {
  ana: HASTA_EL_MODULO_4,
  bruno: [],
  carla: [...HASTA_EL_MODULO_6, 'm07/vscode'],
  diego: [...HASTA_EL_MODULO_6, 'm07/vscode', 'm07/graduacion', 'm08/cierre'],
};

function idModulo(numero: number): string {
  return `m${String(numero).padStart(2, '0')}`;
}

function suma<T>(lista: readonly T[], valor: (item: T) => number): number {
  return lista.reduce((total, item) => total + valor(item), 0);
}

let siguienteId = 1;
const IDS = new Map<string, number>();
function idDe(clave: string): number {
  if (!IDS.has(clave)) {
    IDS.set(clave, siguienteId++);
  }
  return IDS.get(clave) as number;
}

/**
 * El curso de ejemplo como lo devuelve `GET /api/cursos/induccion`, con la
 * misma regla de la API: el módulo n+1 se abre al completar el n, y una
 * lección marcada en un módulo bloqueado no cuenta.
 */
export function cursoDeEjemplo(
  completas: readonly string[],
  contenido: ContenidoCurso = CURSOS_EJEMPLO[0],
): CursoDetalleApi {
  const hechas = new Set(completas);
  const modulos: ModuloApi[] = [];
  let anterior: ModuloApi | null = null;
  for (const m of contenido.modulos) {
    const slug = idModulo(m.numero);
    const abierto = anterior === null || anterior.estado === 'completo';
    const lecciones = m.lecciones.map((l, i) => ({
      id: idDe(`${slug}/${l.slug}`),
      slug: l.slug,
      orden: i + 1,
      titulo: l.titulo,
      duracion_min: l.duracion,
      completada: abierto && hechas.has(`${slug}/${l.slug}`),
      componentes: [
        ...(l.video ? (['video'] as const) : []),
        'lectura' as const,
        ...(l.practicas ? (['practica'] as const) : []),
        ...(l.preguntas ? (['quiz'] as const) : []),
      ],
    }));
    const completasModulo = lecciones.filter((l) => l.completada).length;
    const refAnterior: ModuloRefApi | null = anterior
      ? { id: anterior.id, slug: anterior.slug, numero: anterior.numero, titulo: anterior.titulo }
      : null;
    const modulo: ModuloApi = {
      id: idDe(slug),
      slug,
      numero: m.numero,
      titulo: m.titulo,
      resumen: m.resumen,
      duracion_min: suma(m.lecciones, (l) => l.duracion),
      estado: !abierto
        ? 'bloqueado'
        : completasModulo === lecciones.length
          ? 'completo'
          : 'en_curso',
      bloqueado_por: abierto ? null : refAnterior,
      lecciones_total: lecciones.length,
      lecciones_completas: completasModulo,
      videos: m.lecciones.filter((l) => l.video).length,
      practicas: suma(m.lecciones, (l) => l.practicas),
      preguntas: suma(m.lecciones, (l) => l.preguntas),
      componentes: ['lectura'],
      lecciones,
    };
    modulos.push(modulo);
    anterior = modulo;
  }
  const total = suma(modulos, (m) => m.lecciones_total);
  const completasCurso = suma(modulos, (m) => m.lecciones_completas);
  const enCurso = modulos.find((m) => m.estado === 'en_curso');
  const siguiente = enCurso?.lecciones.find((l) => !l.completada);
  const continuar: LeccionRefApi | null =
    enCurso && siguiente
      ? {
          id: siguiente.id,
          slug: siguiente.slug,
          modulo: enCurso.slug,
          modulo_numero: enCurso.numero,
          titulo: siguiente.titulo,
        }
      : null;
  return {
    id: 1,
    slug: contenido.id,
    titulo: contenido.titulo,
    descripcion: contenido.descripcion,
    duracion_min: suma(modulos, (m) => m.duracion_min),
    videos: suma(modulos, (m) => m.videos),
    avance_pct: total ? Math.round((100 * completasCurso) / total) : 0,
    modulos_total: modulos.length,
    modulos_completos: modulos.filter((m) => m.estado === 'completo').length,
    lecciones_total: total,
    lecciones_completas: completasCurso,
    continuar,
    fallback: false,
    modulos,
  };
}

/** El curso de ejemplo para un usuario de ejemplo (`ana`, `bruno`, `carla`, `diego`). */
export function cursoDe(username: string): CursoDetalleApi {
  return cursoDeEjemplo(PROGRESO_EJEMPLO[username] ?? []);
}

/** El resumen del catálogo (`GET /api/cursos`): el detalle sin los módulos. */
export function resumenDe(curso: CursoDetalleApi): CursoResumenApi {
  const resumen: { modulos?: unknown } = { ...curso };
  delete resumen.modulos;
  return resumen as CursoResumenApi;
}

/** Las prácticas de cada lección de ejemplo (content/mapa.md). */
const PRACTICAS_EJEMPLO: Readonly<Record<string, readonly Practica[]>> = {
  'm01/ssh': ['conexion'],
  'm02/terminal': ['terminal'],
  'm03/archivos': ['archivos'],
  'm04/modulos': ['modulos'],
  'm05/trabajos': ['memoria'],
  'm06/paralelismo': ['nucleos', 'paralelo'],
};

/** El texto de una lección en español y, si está traducida, en inglés. */
export interface TextoLeccion {
  readonly es: string;
  readonly en?: string;
}

/** `m05/trabajos` trae la lección de muestra de la F-04; las demás, un texto corto. */
export function textosDeEjemplo(): Map<string, TextoLeccion> {
  return new Map([['m05/trabajos', { es: MUESTRA_ES, en: MUESTRA_EN }]]);
}

export interface OpcionesLeccion {
  readonly rol?: Rol;
  readonly textos?: ReadonlyMap<string, TextoLeccion>;
  /** Lecciones (`m05/trabajos`) con el video ya subido. */
  readonly conVideo?: ReadonlySet<string>;
}

/**
 * Una lección como la devuelve `GET /api/cursos/induccion/lecciones/{m}/{l}`,
 * con la misma regla de la API: un estudiante en un módulo bloqueado recibe
 * 403 `modulo_bloqueado`; instructores y admins entran.
 */
export function leccionDeEjemplo(
  completas: readonly string[],
  modulo: string,
  slug: string,
  idioma: string,
  opciones: OpcionesLeccion = {},
): LeccionApi | null {
  const curso = cursoDeEjemplo(completas);
  const todas = curso.modulos.flatMap((m) => m.lecciones.map((l) => ({ m, l })));
  const posicion = todas.findIndex(({ m, l }) => m.slug === modulo && l.slug === slug);
  if (posicion < 0) {
    return null;
  }
  const { m, l } = todas[posicion];
  if (m.estado === 'bloqueado' && (opciones.rol ?? 'estudiante') === 'estudiante') {
    throw new HttpErrorResponse({
      status: 403,
      error: { detail: 'bloqueado', codigo: 'modulo_bloqueado', bloqueado_por: m.bloqueado_por },
    });
  }
  const clave = `${modulo}/${slug}`;
  const ref = (i: number): LeccionRefApi | null => {
    const vecina = todas[i];
    return vecina
      ? {
          id: vecina.l.id,
          slug: vecina.l.slug,
          modulo: vecina.m.slug,
          modulo_numero: vecina.m.numero,
          titulo: vecina.l.titulo,
        }
      : null;
  };
  const texto = (opciones.textos ?? textosDeEjemplo()).get(clave) ?? {
    es: `## Objetivos\n\nTexto de ${l.titulo}.\n`,
  };
  const traducida = idioma === 'en' && texto.en !== undefined;
  const disponible = opciones.conVideo?.has(clave) ?? false;
  // Como la API: los sistemas en orden alfabético.
  const sistemas =
    clave === 'm01/vpn' ? (['linux', 'macos', 'windows'] as const) : (['todos'] as const);
  const videos: VideoLeccionApi[] = l.componentes.includes('video')
    ? sistemas.map((sistema) => {
        const id = idDe(`video:${clave}:${sistema}`);
        return {
          sistema,
          video: {
            id,
            clave: `${modulo}-${slug}${sistema === 'todos' ? '' : `-${sistema}`}`,
            disponible,
            duracion_seg: disponible ? 300 : null,
            url: disponible ? `/api/media/${id}` : null,
            subtitulos: disponible
              ? (['es', 'en'] as const).map((i) => ({
                  idioma: i,
                  url: `/api/media/${id}/subtitulos/${i}`,
                }))
              : [],
          },
        };
      })
    : [];
  return {
    id: l.id,
    slug,
    curso: curso.slug,
    modulo: { id: m.id, slug: m.slug, numero: m.numero, titulo: m.titulo },
    orden: l.orden,
    titulo: l.titulo,
    contenido: traducida ? (texto.en as string) : texto.es,
    fallback: idioma === 'en' && !traducida,
    duracion_min: l.duracion_min,
    componentes: l.componentes,
    videos,
    practicas: PRACTICAS_EJEMPLO[clave] ?? [],
    quiz_id: l.componentes.includes('quiz') ? idDe(`quiz:${clave}`) : null,
    anterior: ref(posicion - 1),
    siguiente: ref(posicion + 1),
    progreso: progresoDe(l.id, l.completada),
  };
}

function progresoDe(leccionId: number, completada: boolean): ProgresoLeccionApi {
  return {
    leccion_id: leccionId,
    video_posicion_seg: 0,
    video_max_seg: 0,
    video_completo: false,
    quiz_aprobado: false,
    completada,
    completada_en: completada ? '2026-11-04T15:00:00Z' : null,
  };
}

/** `m05/trabajos` de una lección por su id numérico. */
function claveDe(id: number): string | undefined {
  return [...IDS].find(([clave, valor]) => valor === id && clave.includes('/'))?.[0];
}

/** ContenidoApi con los datos de ejemplo, para el usuario de la sesión. */
@Injectable()
export class ContenidoApiDePrueba {
  private readonly sesion = inject(SesionService);
  /** Lo que se pidió del curso, para comprobar que no se repite. */
  readonly pedidos: string[] = [];
  /** Las lecciones que se pidieron (`m05/trabajos?lang=es`). */
  readonly lecciones: string[] = [];
  /** Los ids que se mandaron a completar. */
  readonly completadas: number[] = [];
  /** Texto de cada lección; las pruebas pueden cambiarlo. */
  readonly textos = textosDeEjemplo();
  /** Lecciones con el video ya subido. */
  readonly conVideo = new Set<string>();
  /** Lo que se completó durante la prueba, además de PROGRESO_EJEMPLO. */
  private readonly hechas = new Set<string>();

  async cursos(idioma: string): Promise<CursoResumenApi[]> {
    this.pedidos.push(`cursos?lang=${idioma}`);
    return [resumenDe(this.armar())];
  }

  async curso(slug: string, idioma: string): Promise<CursoDetalleApi | null> {
    this.pedidos.push(`cursos/${slug}?lang=${idioma}`);
    return slug === 'induccion' ? this.armar() : null;
  }

  async leccion(
    curso: string,
    modulo: string,
    slug: string,
    idioma: string,
  ): Promise<LeccionApi | null> {
    this.lecciones.push(`${modulo}/${slug}?lang=${idioma}`);
    if (curso !== 'induccion') {
      return null;
    }
    return leccionDeEjemplo(this.completas(), modulo, slug, idioma, {
      rol: this.sesion.usuario()?.rol,
      textos: this.textos,
      conVideo: this.conVideo,
    });
  }

  /** Como la API (B-04 y F-04): un video subido sin ver da 409. */
  async completar(leccionId: number): Promise<ProgresoLeccionApi> {
    this.completadas.push(leccionId);
    const clave = claveDe(leccionId);
    if (!clave) {
      throw new HttpErrorResponse({ status: 404, error: { codigo: 'no_encontrado' } });
    }
    if (this.conVideo.has(clave)) {
      throw new HttpErrorResponse({
        status: 409,
        error: { detail: 'falta el video', codigo: 'requisitos_pendientes' },
      });
    }
    this.hechas.add(clave);
    return progresoDe(leccionId, true);
  }

  /** Los reportes del reproductor (F-05), en orden. */
  readonly reportes: { entrada: ProgresoVideoEntradaApi; alSalir: boolean }[] = [];

  /** Como la API (F-05): al 90 % de los 300 s del video la lección queda completa. */
  async reportarVideo(
    entrada: ProgresoVideoEntradaApi,
    alSalir = false,
  ): Promise<ProgresoLeccionApi> {
    this.reportes.push({ entrada, alSalir });
    const clave = claveDe(entrada.leccion_id);
    if (!clave || !this.conVideo.has(clave)) {
      throw new HttpErrorResponse({ status: 404, error: { codigo: 'no_encontrado' } });
    }
    const segundo = Math.min(entrada.segundo, 300);
    const visto = segundo >= 270;
    if (visto) {
      this.hechas.add(clave);
    }
    return {
      ...progresoDe(entrada.leccion_id, this.completas().includes(clave)),
      video_posicion_seg: segundo,
      video_max_seg: segundo,
      video_completo: visto,
    };
  }

  private completas(): string[] {
    return [...(PROGRESO_EJEMPLO[this.sesion.usuario()?.username ?? ''] ?? []), ...this.hechas];
  }

  private armar(): CursoDetalleApi {
    return cursoDeEjemplo(this.completas());
  }
}

/** Reemplaza la API de contenido por los datos de ejemplo (pruebas de rutas y pantallas). */
export function contenidoDePrueba(): Provider[] {
  return [ContenidoApiDePrueba, { provide: ContenidoApi, useExisting: ContenidoApiDePrueba }];
}
