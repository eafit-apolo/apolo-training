import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import type { Provider } from '@angular/core';
import type { Rol } from '../app/core/sesion/sesion';
import { SesionService } from '../app/core/sesion/sesion';
import type {
  CursoDetalleApi,
  CursoResumenApi,
  IntentoEntradaApi,
  IntentoResultadoApi,
  LeccionApi,
  LeccionRefApi,
  ModuloApi,
  ModuloRefApi,
  Practica,
  ProgresoLeccionApi,
  ProgresoVideoEntradaApi,
  QuizApi,
  VideoLeccionApi,
} from '../app/features/cursos/datos/api';
import { ContenidoApi } from '../app/features/cursos/datos/api';
import { MUESTRA_EN, MUESTRA_ES } from './leccion-muestra';
import type { QuizCompleto } from './quiz';
import { armarQuiz, calificar } from './quiz';

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
  /** Lecciones que, para la prueba, no tienen quiz (por defecto lo tienen las del mapa). */
  readonly sinQuiz?: ReadonlySet<string>;
  /** Lecciones con el quiz aprobado y con el 90 % del video visto en esta sesión. */
  readonly aprobados?: ReadonlySet<string>;
  readonly vistos?: ReadonlySet<string>;
}

/** Cuántas preguntas tiene el quiz de una lección de ejemplo (`m05/trabajos`); 0 si no tiene. */
export function preguntasDeEjemplo(clave: string): number {
  for (const m of CURSOS_EJEMPLO[0].modulos) {
    const hallada = m.lecciones.find((l) => `${idModulo(m.numero)}/${l.slug}` === clave);
    if (hallada) {
      return hallada.preguntas;
    }
  }
  return 0;
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
  const conQuiz = l.componentes.includes('quiz') && !opciones.sinQuiz?.has(clave);
  const componentes = conQuiz ? l.componentes : l.componentes.filter((c) => c !== 'quiz');
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
    componentes,
    videos,
    practicas: PRACTICAS_EJEMPLO[clave] ?? [],
    quiz_id: conQuiz ? idDe(`quiz:${clave}`) : null,
    anterior: ref(posicion - 1),
    siguiente: ref(posicion + 1),
    progreso: progresoDe(l.id, l.completada, {
      // Una lección con quiz que ya estaba completa tiene el quiz aprobado.
      quizAprobado: conQuiz && (l.completada || !!opciones.aprobados?.has(clave)),
      videoCompleto: !!opciones.vistos?.has(clave),
    }),
  };
}

function progresoDe(
  leccionId: number,
  completada: boolean,
  extra: { quizAprobado?: boolean; videoCompleto?: boolean } = {},
): ProgresoLeccionApi {
  return {
    leccion_id: leccionId,
    video_posicion_seg: 0,
    video_max_seg: 0,
    video_completo: extra.videoCompleto ?? false,
    quiz_aprobado: extra.quizAprobado ?? false,
    completada,
    completada_en: completada ? '2026-11-04T15:00:00Z' : null,
  };
}

/** `m05/trabajos` de una lección por su id numérico. */
function claveDe(id: number): string | undefined {
  return [...IDS].find(([clave, valor]) => valor === id && /^m\d\d\/[^:]+$/.test(clave))?.[0];
}

/** `m05/trabajos` de un quiz por su id numérico. */
function claveDeQuiz(id: number): string | undefined {
  return [...IDS]
    .find(([clave, valor]) => valor === id && clave.startsWith('quiz:'))?.[0]
    ?.slice(5);
}

function bloqueado(status: number, error: object): HttpErrorResponse {
  return new HttpErrorResponse({ status, error });
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
  /** Lecciones que, para la prueba, no tienen quiz (por defecto las del mapa sí lo tienen). */
  readonly sinQuiz = new Set<string>();
  /** Quizzes (`m05/trabajos`) sin inglés: salen en español con `fallback`. */
  readonly quizSinIngles = new Set<string>();
  /** Los quizzes que se pidieron (`m05/trabajos?lang=es`). */
  readonly quizzes: string[] = [];
  /** Los intentos que se mandaron a calificar, en orden. */
  readonly intentos: { clave: string; entrada: IntentoEntradaApi }[] = [];
  /** Lo que se completó durante la prueba, además de PROGRESO_EJEMPLO. */
  private readonly hechas = new Set<string>();
  private readonly aprobados = new Set<string>();
  private readonly vistos = new Set<string>();
  private readonly mejores = new Map<string, number>();
  private contadorIntentos = 0;

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
      sinQuiz: this.sinQuiz,
      aprobados: this.aprobados,
      vistos: this.vistos,
    });
  }

  /**
   * Como la API (B-04, F-04 y B-06): un video subido sin ver o un quiz sin
   * aprobar da 409.
   */
  async completar(leccionId: number): Promise<ProgresoLeccionApi> {
    this.completadas.push(leccionId);
    const clave = claveDe(leccionId);
    if (!clave) {
      throw bloqueado(404, { codigo: 'no_encontrado' });
    }
    if (!this.cumplida(clave)) {
      throw bloqueado(409, { detail: 'falta el video o el quiz', codigo: 'requisitos_pendientes' });
    }
    this.hechas.add(clave);
    return this.progreso(leccionId, clave);
  }

  /** Los reportes del reproductor (F-05), en orden. */
  readonly reportes: { entrada: ProgresoVideoEntradaApi; alSalir: boolean }[] = [];

  /**
   * Como la API (F-05 y B-06): al 90 % de los 300 s del video queda visto, y la
   * lección se completa si no falta el quiz.
   */
  async reportarVideo(
    entrada: ProgresoVideoEntradaApi,
    alSalir = false,
  ): Promise<ProgresoLeccionApi> {
    this.reportes.push({ entrada, alSalir });
    const clave = claveDe(entrada.leccion_id);
    if (!clave || !this.conVideo.has(clave)) {
      throw bloqueado(404, { codigo: 'no_encontrado' });
    }
    const segundo = Math.min(entrada.segundo, 300);
    if (segundo >= 270) {
      this.vistos.add(clave);
    }
    if (this.cumplida(clave)) {
      this.hechas.add(clave);
    }
    return {
      ...this.progreso(entrada.leccion_id, clave),
      video_posicion_seg: segundo,
      video_max_seg: segundo,
    };
  }

  /**
   * Como la API (B-06): las preguntas sin la correcta. Un estudiante en un
   * módulo bloqueado recibe 403; instructores y admins lo leen.
   */
  async quiz(quizId: number, idioma: string): Promise<QuizApi> {
    this.quizzes.push(`${claveDeQuiz(quizId)}?lang=${idioma}`);
    const completo = this.quizCompleto(quizId, idioma);
    const rol = this.sesion.usuario()?.rol ?? 'estudiante';
    if (this.moduloBloqueado(completo.clave) && rol === 'estudiante') {
      throw bloqueado(403, { detail: 'bloqueado', codigo: 'modulo_bloqueado' });
    }
    return completo.quiz.quiz;
  }

  /**
   * Como la API (B-06): califica sin puntos parciales, guarda el mejor puntaje
   * y deja la lección completa si ya se cumplió lo demás. Enviar exige el
   * módulo abierto, también para instructores y admins.
   */
  async enviarIntento(
    quizId: number,
    entrada: IntentoEntradaApi,
    idioma: string,
  ): Promise<IntentoResultadoApi> {
    const completo = this.quizCompleto(quizId, idioma);
    this.intentos.push({ clave: completo.clave, entrada });
    if (this.moduloBloqueado(completo.clave)) {
      throw bloqueado(403, { detail: 'bloqueado', codigo: 'modulo_bloqueado' });
    }
    const { clave } = completo;
    const nota = calificar(completo.quiz, entrada);
    const mejor = Math.max(nota.puntaje, this.mejores.get(clave) ?? 0);
    this.mejores.set(clave, mejor);
    if (nota.aprobado) {
      this.aprobados.add(clave);
    }
    if (this.cumplida(clave)) {
      this.hechas.add(clave);
    }
    return {
      id: ++this.contadorIntentos,
      puntaje: nota.puntaje,
      aprobado: nota.aprobado,
      umbral: completo.quiz.quiz.umbral,
      mejor_puntaje: mejor,
      preguntas: nota.preguntas,
      progreso: this.progreso(completo.quiz.quiz.leccion_id, clave),
    };
  }

  /** Lo que la API ve de un quiz y no manda: sirve para que las pruebas elijan bien. */
  correctasDe(quizId: number): QuizCompleto['correctas'] {
    return this.quizCompleto(quizId, 'es').quiz.correctas;
  }

  private quizCompleto(quizId: number, idioma: string): { clave: string; quiz: QuizCompleto } {
    const clave = claveDeQuiz(quizId);
    if (!clave || this.sinQuiz.has(clave)) {
      throw bloqueado(404, { codigo: 'no_encontrado' });
    }
    return {
      clave,
      quiz: armarQuiz({
        clave,
        quizId,
        leccionId: idDe(clave),
        preguntas: preguntasDeEjemplo(clave),
        idioma,
        mejor: this.mejores.get(clave) ?? null,
        sinIngles: this.quizSinIngles.has(clave),
        idDe,
      }),
    };
  }

  private moduloBloqueado(clave: string): boolean {
    const modulo = this.armar().modulos.find((m) => m.slug === clave.split('/')[0]);
    return modulo?.estado === 'bloqueado';
  }

  /** La regla de la API: video subido visto y quiz aprobado, si los tiene. */
  private cumplida(clave: string): boolean {
    const quiz = preguntasDeEjemplo(clave) > 0 && !this.sinQuiz.has(clave);
    return (
      (!this.conVideo.has(clave) || this.vistos.has(clave)) && (!quiz || this.aprobados.has(clave))
    );
  }

  private progreso(leccionId: number, clave: string): ProgresoLeccionApi {
    return progresoDe(leccionId, this.completas().includes(clave), {
      quizAprobado: this.aprobados.has(clave),
      videoCompleto: this.vistos.has(clave),
    });
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
