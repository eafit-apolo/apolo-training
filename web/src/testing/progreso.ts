import type {
  GraduacionApi,
  LabEstadoApi,
  LeccionProgresoApi,
  MiProgresoApi,
  ModuloProgresoApi,
} from '../app/features/progreso/datos';
import { PRACTICAS } from '../app/features/progreso/datos';

// Mi progreso de ejemplo (F-07), con la forma de `GET /api/me/progreso` de la
// B-07: tres módulos como el contenido real (m00 completo, m01 en curso con
// la práctica `conexion`, m02 bloqueado con `terminal`) y las siete prácticas.

let siguienteId = 1;

function leccion(slug: string, titulo: string, mas: Partial<LeccionProgresoApi> = {}) {
  return {
    id: siguienteId++,
    slug,
    titulo,
    completada: false,
    video_completo: false,
    tiene_quiz: false,
    quiz_aprobado: false,
    quiz_mejor_puntaje: null,
    practicas: [],
    ...mas,
  } satisfies LeccionProgresoApi;
}

export function modulosDeEjemplo(): ModuloProgresoApi[] {
  siguienteId = 1;
  return [
    {
      id: 100,
      slug: 'm00',
      numero: 0,
      titulo: 'Bienvenida',
      estado: 'completo',
      lecciones_total: 1,
      lecciones_completas: 1,
      lecciones: [
        leccion('bienvenida', 'Bienvenida al curso', {
          completada: true,
          video_completo: true,
          tiene_quiz: true,
          quiz_aprobado: true,
          quiz_mejor_puntaje: 100,
        }),
      ],
    },
    {
      id: 101,
      slug: 'm01',
      numero: 1,
      titulo: 'Conexión',
      estado: 'en_curso',
      lecciones_total: 1,
      lecciones_completas: 0,
      lecciones: [
        leccion('ssh', 'Conectarse por SSH', {
          tiene_quiz: true,
          quiz_mejor_puntaje: 50,
          practicas: ['conexion'],
        }),
      ],
    },
    {
      id: 102,
      slug: 'm02',
      numero: 2,
      titulo: 'Terminal y Linux',
      estado: 'bloqueado',
      lecciones_total: 1,
      lecciones_completas: 0,
      lecciones: [leccion('terminal', 'Comandos básicos de Linux', { practicas: ['terminal'] })],
    },
  ];
}

export function labsDeEjemplo(cambios: Partial<Record<string, Partial<LabEstadoApi>>> = {}) {
  return PRACTICAS.map((lab): LabEstadoApi => ({
    lab,
    estado: 'sin_intentar',
    jobid: null,
    fecha: null,
    detalle: null,
    ...cambios[lab],
  }));
}

export function graduacionDeEjemplo(mas: Partial<GraduacionApi> = {}): GraduacionApi {
  return {
    cluster: 'apolo2',
    jobid: '4321',
    salida_verificador: '[APROBADO] graduacion: curso-graduacion COMPLETED en learning',
    estado: 'enviada',
    enviada_en: '2026-11-23T15:00:00Z',
    revisada_en: null,
    comentario: null,
    qos_aplicada_en: null,
    ...mas,
  };
}

/** Mi progreso de `ana` a mitad del curso; `mas` reemplaza campos enteros. */
export function progresoDeEjemplo(mas: Partial<MiProgresoApi> = {}): MiProgresoApi {
  const modulos = modulosDeEjemplo();
  return {
    curso: 'induccion',
    avance_pct: 33,
    lecciones_total: 3,
    lecciones_completas: 1,
    modulos,
    fallback: false,
    labs: labsDeEjemplo({
      conexion: { estado: 'aprobado', fecha: '2026-11-23T14:50:00Z' },
      memoria: {
        estado: 'intentado',
        jobid: '1042',
        fecha: '2026-11-23T14:55:00Z',
        detalle: 'OUT_OF_MEMORY con --mem=1G',
      },
    }),
    ultima_sincronizacion: new Date(Date.now() - 3 * 60_000).toISOString(),
    sincronizacion_atrasada: false,
    graduacion: null,
    aprobado: false,
    siguiente_paso: {
      tipo: 'leccion',
      leccion: {
        id: modulos[1].lecciones[0].id,
        slug: 'ssh',
        modulo: 'm01',
        modulo_numero: 1,
        titulo: 'Conectarse por SSH',
      },
      lab: null,
    },
    ...mas,
  };
}
