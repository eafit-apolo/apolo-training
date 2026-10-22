import type { ContenidoCurso } from './curso';

/**
 * Datos de ejemplo hasta la API de contenido (B-04), que los reemplaza.
 *
 * Siguen el mapa del curso (content/mapa.md, cambio del 15-oct): 9 módulos,
 * 82 min, 24 preguntas, 7 prácticas y la graduación. Las lecciones, sus
 * títulos y sus minutos son de ejemplo.
 */
export const CURSOS_EJEMPLO: readonly ContenidoCurso[] = [
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
