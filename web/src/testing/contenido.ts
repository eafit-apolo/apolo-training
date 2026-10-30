import { Injectable, inject } from '@angular/core';
import type { Provider } from '@angular/core';
import { SesionService } from '../app/core/sesion/sesion';
import type {
  CursoDetalleApi,
  CursoResumenApi,
  LeccionRefApi,
  ModuloApi,
  ModuloRefApi,
} from '../app/features/cursos/datos/api';
import { ContenidoApi } from '../app/features/cursos/datos/api';

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

/** ContenidoApi con los datos de ejemplo, para el usuario de la sesión. */
@Injectable()
export class ContenidoApiDePrueba {
  private readonly sesion = inject(SesionService);
  /** Lo que se pidió, para comprobar que no se repite. */
  readonly pedidos: string[] = [];

  async cursos(idioma: string): Promise<CursoResumenApi[]> {
    this.pedidos.push(`cursos?lang=${idioma}`);
    return [resumenDe(this.armar())];
  }

  async curso(slug: string, idioma: string): Promise<CursoDetalleApi | null> {
    this.pedidos.push(`cursos/${slug}?lang=${idioma}`);
    return slug === 'induccion' ? this.armar() : null;
  }

  private armar(): CursoDetalleApi {
    return cursoDe(this.sesion.usuario()?.username ?? '');
  }
}

/** Reemplaza la API de contenido por los datos de ejemplo (pruebas de rutas y pantallas). */
export function contenidoDePrueba(): Provider[] {
  return [ContenidoApiDePrueba, { provide: ContenidoApi, useExisting: ContenidoApiDePrueba }];
}
