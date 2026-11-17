import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Injector,
  ViewEncapsulation,
  afterNextRender,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output,
  resource,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../../core/i18n/idioma';
import { codigoDeError } from '../../../core/sesion/errores';
import { Icono } from '../../../shared/icono';
import type { IntentoResultadoApi, PreguntaQuizApi, QuizApi } from '../datos/api';
import { ContenidoApi } from '../datos/api';
import { Bloques } from './bloques';
import { analizarEnLinea, analizarMarkdown } from './markdown';

let siguienteId = 0;

const porOrden = (a: { readonly orden: number }, b: { readonly orden: number }) =>
  a.orden - b.orden;

/** Las opciones marcadas de cada pregunta, por id de pregunta. */
type Marcadas = Readonly<Record<number, readonly number[]>>;

/**
 * El quiz de una lección (F-06): `GET /api/quizzes/{id}` para las preguntas y
 * `POST …/intentos` para calificar. La API califica y nunca dice cuál era la
 * opción correcta: aquí solo se muestra si cada pregunta salió bien y su
 * explicación, para que reintentar sirva.
 *
 * Una pregunta de una respuesta es un grupo de botones de radio y una de varias
 * son casillas. Sin `@angular/forms` (el inicial sube de 424 a 499 kB si forms
 * queda compartido): signals y los inputs nativos.
 */
@Component({
  selector: 'at-quiz',
  imports: [MatButtonModule, MatProgressBarModule, TranslocoPipe, Icono, Bloques],
  templateUrl: './quiz.html',
  styleUrl: './quiz.scss',
  // Las opciones y las explicaciones entran por innerHTML (sin los atributos de
  // la encapsulación): los estilos van con el prefijo at-quiz.
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Quiz {
  readonly quizId = input.required<number>();
  /** `false` para un instructor o admin que lee un módulo bloqueado: lee, no envía. */
  readonly puedeEnviar = input(true);
  /** La lección ya tiene el quiz aprobado (`progreso.quiz_aprobado`). */
  readonly aprobado = input(false);
  /** Aprobar no la completa todavía: falta el 90 % del video. */
  readonly faltaVideo = input(false);
  /** La lección ya quedó completa. */
  readonly leccionCompleta = input(false);

  /** Lo que respondió la API al calificar: el avance de la lección viene dentro. */
  readonly calificado = output<IntentoResultadoApi>();
  /** La API dijo 403 `modulo_bloqueado`: el catálogo estaba viejo. */
  readonly bloqueado = output<void>();

  private readonly api = inject(ContenidoApi);
  private readonly idioma = inject(IdiomaService);
  private readonly injector = inject(Injector);
  private readonly anfitrion = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly uid = `at-quiz-${siguienteId++}`;

  protected readonly respuesta = resource({
    params: () => ({ id: this.quizId(), idioma: this.idioma.actual() }),
    loader: ({ params }) => this.api.quiz(params.id, params.idioma),
  });

  /**
   * El quiz en pantalla. Al cambiar el idioma se ve el anterior hasta que llegue
   * el nuevo (las opciones marcadas siguen valiendo: los ids son los mismos en
   * español y en inglés); al cambiar de quiz, no.
   */
  protected readonly quiz = linkedSignal<QuizApi | undefined, QuizApi | undefined>({
    source: () => (this.respuesta.hasValue() ? this.respuesta.value() : undefined),
    computation: (nuevo, previo) => {
      if (nuevo !== undefined) {
        return nuevo;
      }
      return previo?.value?.id === this.quizId() ? previo.value : undefined;
    },
  });

  /** Preguntas y opciones en su orden, con el Markdown ya convertido. */
  protected readonly preguntas = computed(() =>
    [...(this.quiz()?.preguntas ?? [])].sort(porOrden).map((p) => ({
      ...p,
      bloques: analizarMarkdown(p.enunciado),
      opciones: [...p.opciones]
        .sort(porOrden)
        .map((o) => ({ ...o, html: analizarEnLinea(o.texto) })),
    })),
  );

  protected readonly marcadas = linkedSignal<number, Marcadas>({
    source: this.quizId,
    computation: () => ({}),
  });
  protected readonly resultado = linkedSignal<number, IntentoResultadoApi | null>({
    source: this.quizId,
    computation: () => null,
  });
  protected readonly enviando = signal(false);
  /** Preguntas sin contestar tras un intento de envío. */
  protected readonly sinResponder = signal<ReadonlySet<number>>(new Set());
  /** Clave del mensaje de error al enviar. */
  protected readonly error = signal<string | null>(null);
  private readonly resumen = viewChild<ElementRef<HTMLElement>>('resumen');

  /** Lo que la API dijo de cada pregunta, con la explicación lista para pintar. */
  protected readonly veredictos = computed(
    () =>
      new Map(
        (this.resultado()?.preguntas ?? []).map((r) => [
          r.pregunta_id,
          { correcta: r.correcta, explicacion: analizarEnLinea(r.explicacion) },
        ]),
      ),
  );
  protected readonly aciertos = computed(
    () => this.resultado()?.preguntas.filter((p) => p.correcta).length ?? 0,
  );
  /** El mejor puntaje, ya con el intento de ahora. */
  protected readonly mejor = computed(
    () => this.resultado()?.mejor_puntaje ?? this.quiz()?.mejor_puntaje ?? null,
  );
  protected readonly umbralPct = computed(() => Math.round((this.quiz()?.umbral ?? 0.8) * 100));
  /** Con el resultado a la vista, o sin permiso, o enviando, no se cambian las respuestas. */
  protected readonly cerrado = computed(
    () => !this.puedeEnviar() || this.resultado() !== null || this.enviando(),
  );

  protected idDe(pregunta: PreguntaQuizApi, parte?: string): string {
    return `${this.uid}-${pregunta.id}${parte ? `-${parte}` : ''}`;
  }

  /** Un número para la pantalla: sin decimales sobrantes y con la coma del idioma. */
  protected numero(valor: number): string {
    return new Intl.NumberFormat(this.idioma.actual(), { maximumFractionDigits: 1 }).format(valor);
  }

  protected esta(pregunta: number, opcion: number): boolean {
    return this.marcadas()[pregunta]?.includes(opcion) ?? false;
  }

  /** Lo que describe a una pregunta para el lector de pantalla: la pista, lo que falta y el veredicto. */
  protected descripcion(pregunta: PreguntaQuizApi): string {
    const ids = [this.idDe(pregunta, 'pista')];
    if (this.sinResponder().has(pregunta.id)) {
      ids.push(this.idDe(pregunta, 'falta'));
    }
    if (this.veredictos().has(pregunta.id)) {
      ids.push(this.idDe(pregunta, 'veredicto'));
    }
    return ids.join(' ');
  }

  protected elegir(pregunta: PreguntaQuizApi, opcion: number, evento: Event): void {
    const marcada = (evento.target as HTMLInputElement).checked;
    const actuales = this.marcadas()[pregunta.id] ?? [];
    const nuevas = pregunta.multiple
      ? marcada
        ? [...actuales.filter((id) => id !== opcion), opcion]
        : actuales.filter((id) => id !== opcion)
      : [opcion];
    this.marcadas.update((m) => ({ ...m, [pregunta.id]: nuevas }));
    if (this.sinResponder().has(pregunta.id)) {
      this.sinResponder.update((s) => new Set([...s].filter((id) => id !== pregunta.id)));
    }
    this.error.set(null);
  }

  constructor() {
    // El catálogo creía abierto un módulo que la API dice bloqueado.
    effect(() => {
      if (codigoDeError(this.respuesta.error()) === 'modulo_bloqueado') {
        untracked(() => this.bloqueado.emit());
      }
    });
  }

  protected async enviar(): Promise<void> {
    const quiz = this.quiz();
    if (!quiz || this.enviando() || !this.puedeEnviar()) {
      return;
    }
    const sin = this.preguntas().filter((p) => !this.marcadas()[p.id]?.length);
    if (sin.length) {
      // Con `aria-disabled` el botón sí recibe el clic: se dice qué falta y se
      // lleva el foco a la primera pregunta sin contestar.
      this.sinResponder.set(new Set(sin.map((p) => p.id)));
      this.error.set(null);
      this.enfocarPregunta(sin[0].id);
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    try {
      const resultado = await this.api.enviarIntento(
        quiz.id,
        {
          respuestas: this.preguntas().map((p) => ({
            pregunta_id: p.id,
            opciones: this.marcadas()[p.id],
          })),
        },
        this.idioma.actual(),
      );
      this.resultado.set(resultado);
      this.calificado.emit(resultado);
      // El resumen queda arriba, con el foco: el lector de pantalla lo lee y las
      // explicaciones de cada pregunta siguen debajo.
      afterNextRender(() => this.resumen()?.nativeElement.focus(), { injector: this.injector });
    } catch (error) {
      const codigo = codigoDeError(error);
      if (codigo === 'modulo_bloqueado') {
        this.bloqueado.emit();
      }
      this.error.set(
        codigo === 'modulo_bloqueado' ? 'leccion.quiz.bloqueado' : 'leccion.quiz.errorEnviar',
      );
    } finally {
      this.enviando.set(false);
    }
  }

  /** Vuelve a abrir las preguntas con lo que ya estaba marcado. */
  protected reintentar(): void {
    this.resultado.set(null);
    this.error.set(null);
    this.enfocarPregunta(this.preguntas()[0]?.id);
  }

  private enfocarPregunta(id: number | undefined): void {
    if (id === undefined) {
      return;
    }
    afterNextRender(
      () =>
        this.anfitrion.nativeElement
          .querySelector<HTMLElement>(`[data-pregunta="${id}"] input:not([disabled])`)
          ?.focus(),
      { injector: this.injector },
    );
  }
}
