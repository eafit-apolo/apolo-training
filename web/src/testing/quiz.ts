import { HttpErrorResponse } from '@angular/common/http';
import type {
  IntentoEntradaApi,
  PreguntaQuizApi,
  QuizApi,
  ResultadoPreguntaApi,
} from '../app/features/cursos/datos/api';

// Los quizzes de ejemplo de la F-06 y la calificación de la B-06
// (api/app/services/quizzes.py), para que las pruebas de la web usen la misma
// regla que la API: una pregunta cuenta si marcó exactamente las correctas, sin
// puntos parciales, y aprueba con `aciertos >= umbral × total`.

export const UMBRAL = 0.8;

const TEXTOS = {
  es: {
    pregunta: (n: number) => `Pregunta ${n}: ¿qué hace \`squeue\`?`,
    opcion: (n: number, p: number) => `Opción ${n} de la pregunta ${p}`,
    opcionCodigo: (p: number) => `Usar \`sbatch\` en la pregunta ${p}`,
    explicacion: (n: number) => `Explicación de la pregunta ${n}, con \`sacct\`.`,
  },
  en: {
    pregunta: (n: number) => `Question ${n}: what does \`squeue\` do?`,
    opcion: (n: number, p: number) => `Option ${n} of question ${p}`,
    opcionCodigo: (p: number) => `Use \`sbatch\` in question ${p}`,
    explicacion: (n: number) => `Explanation of question ${n}, with \`sacct\`.`,
  },
} as const;

/** Lo que la API sabe y no manda: las opciones correctas y la explicación de cada pregunta. */
export interface QuizCompleto {
  readonly quiz: QuizApi;
  readonly correctas: ReadonlyMap<number, ReadonlySet<number>>;
  readonly explicaciones: ReadonlyMap<number, string>;
}

export interface OpcionesQuiz {
  readonly clave: string;
  readonly quizId: number;
  readonly leccionId: number;
  readonly preguntas: number;
  readonly idioma: string;
  readonly mejor: number | null;
  /** El inglés no existe: el quiz sale en español con `fallback`. */
  readonly sinIngles?: boolean;
  /** Los mismos ids en cada llamada (los de la lección de ejemplo). */
  readonly idDe: (clave: string) => number;
}

/**
 * `n` preguntas: las pares son de una respuesta (3 opciones, la correcta es la
 * 2) y las impares de varias (4 opciones, las correctas son la 1 y la 3). El
 * enunciado y la segunda opción llevan código en línea, como los reales.
 */
export function armarQuiz(o: OpcionesQuiz): QuizCompleto {
  const fallback = o.idioma === 'en' && !!o.sinIngles;
  const textos = o.idioma === 'en' && !fallback ? TEXTOS.en : TEXTOS.es;
  const correctas = new Map<number, ReadonlySet<number>>();
  const explicaciones = new Map<number, string>();
  const preguntas: PreguntaQuizApi[] = Array.from({ length: o.preguntas }, (_, i) => {
    const multiple = i % 2 === 1;
    const id = o.idDe(`pregunta:${o.clave}:${i}`);
    const opciones = Array.from({ length: multiple ? 4 : 3 }, (_, j) => ({
      id: o.idDe(`opcion:${o.clave}:${i}:${j}`),
      orden: j + 1,
      texto: j === 1 ? textos.opcionCodigo(i + 1) : textos.opcion(j + 1, i + 1),
    }));
    correctas.set(id, new Set((multiple ? [0, 2] : [1]).map((j) => opciones[j].id)));
    explicaciones.set(id, textos.explicacion(i + 1));
    return { id, orden: i + 1, enunciado: textos.pregunta(i + 1), multiple, opciones };
  });
  return {
    quiz: {
      id: o.quizId,
      leccion_id: o.leccionId,
      umbral: UMBRAL,
      es_final: false,
      fallback,
      mejor_puntaje: o.mejor,
      preguntas,
    },
    correctas,
    explicaciones,
  };
}

function invalido(detalle: string): HttpErrorResponse {
  return new HttpErrorResponse({
    status: 422,
    error: { detail: detalle, codigo: 'respuestas_invalidas' },
  });
}

export interface Calificacion {
  readonly puntaje: number;
  readonly aprobado: boolean;
  readonly preguntas: ResultadoPreguntaApi[];
}

/** Califica como la API: 422 `respuestas_invalidas` si las respuestas no encajan con el quiz. */
export function calificar(completo: QuizCompleto, entrada: IntentoEntradaApi): Calificacion {
  const { quiz, correctas, explicaciones } = completo;
  const porPregunta = new Map<number, readonly number[]>();
  for (const r of entrada.respuestas) {
    if (porPregunta.has(r.pregunta_id)) {
      throw invalido('una pregunta respondida dos veces');
    }
    porPregunta.set(r.pregunta_id, r.opciones);
  }
  if (porPregunta.size !== quiz.preguntas.length) {
    throw invalido('hay que responder todas las preguntas');
  }
  const preguntas: ResultadoPreguntaApi[] = quiz.preguntas.map((p) => {
    const marcadas = porPregunta.get(p.id);
    const ids = new Set(p.opciones.map((o) => o.id));
    if (!marcadas?.length || marcadas.some((id) => !ids.has(id))) {
      throw invalido('opciones que no son de la pregunta');
    }
    if (!p.multiple && marcadas.length !== 1) {
      throw invalido('una pregunta de una respuesta lleva exactamente una opción');
    }
    const esperadas = correctas.get(p.id) as ReadonlySet<number>;
    const elegidas = new Set(marcadas);
    const correcta =
      elegidas.size === esperadas.size && [...elegidas].every((id) => esperadas.has(id));
    return { pregunta_id: p.id, correcta, explicacion: explicaciones.get(p.id) as string };
  });
  const aciertos = preguntas.filter((p) => p.correcta).length;
  const total = quiz.preguntas.length;
  return {
    puntaje: Math.round((10000 * aciertos) / total) / 100,
    // Con enteros, como la API: 7 de 8 sí aprueba y 6 de 8 no.
    aprobado: aciertos * 100 >= Math.round(UMBRAL * 100) * total,
    preguntas,
  };
}
