import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  resource,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Idioma } from '../../../core/i18n/idioma';
import { IdiomaService } from '../../../core/i18n/idioma';
import { codigoDeError } from '../../../core/sesion/errores';
import { Icono } from '../../../shared/icono';
import type { Miga } from '../../../shared/migas';
import { Migas } from '../../../shared/migas';
import { PaginaPendiente } from '../../../shared/pagina-pendiente';
import type { LeccionApi, LeccionRefApi, ProgresoLeccionApi } from '../datos/api';
import { ContenidoApi } from '../datos/api';
import { CatalogoService } from '../datos/catalogo';
import { Bloqueado } from '../modulo/bloqueado';
import { Bloques } from './bloques';
import { ClusterElegido } from './cluster-elegido';
import { Codigo } from './codigo';
import { analizarMarkdown, bloqueDeCodigo } from './markdown';
import { Videos } from './videos';

interface Pedido {
  readonly curso: string;
  readonly modulo: string;
  readonly leccion: string;
  readonly idioma: Idioma;
}

const mismoPedido = (a: Pedido | undefined, b: Pedido | undefined) =>
  a === b ||
  (!!a &&
    !!b &&
    a.curso === b.curso &&
    a.modulo === b.modulo &&
    a.leccion === b.leccion &&
    a.idioma === b.idioma);

/**
 * Pantalla 03: la lección (F-04). El marco (migas, título, estado) sale del
 * catálogo; el cuerpo, de `GET /api/cursos/{curso}/lecciones/{modulo}/{leccion}`:
 * video, texto con pestañas Apolo II / Apolo III y botones de copiar, la
 * práctica, el quiz, «Marcar como completada» y anterior / siguiente.
 */
@Component({
  selector: 'at-leccion',
  imports: [
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
    Migas,
    PaginaPendiente,
    Bloqueado,
    Bloques,
    Codigo,
    Videos,
  ],
  templateUrl: './leccion.html',
  styleUrl: './leccion.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Leccion {
  /** `:curso`, `:modulo` y `:leccion` de la ruta (llegan por paramsInheritanceStrategy). */
  readonly curso = input<string>();
  readonly modulo = input<string>();
  readonly leccion = input<string>();

  private readonly catalogo = inject(CatalogoService);
  private readonly api = inject(ContenidoApi);
  private readonly idioma = inject(IdiomaService);
  private readonly cluster = inject(ClusterElegido);
  private readonly injector = inject(Injector);

  protected readonly datosCurso = computed(() => this.catalogo.curso(this.curso()));
  protected readonly datosModulo = computed(() =>
    this.catalogo.modulo(this.datosCurso(), this.modulo()),
  );
  protected readonly datos = computed(() =>
    this.catalogo.leccion(this.datosModulo(), this.leccion()),
  );

  protected readonly migas = computed<readonly Miga[]>(() => {
    const curso = this.datosCurso();
    const modulo = this.datosModulo();
    return [
      { clave: 'nav.cursos', ruta: ['/cursos'] },
      { texto: curso?.titulo, ruta: ['/cursos', curso?.id ?? ''] },
      {
        texto: `${modulo?.numero} · ${modulo?.titulo}`,
        ruta: ['/cursos', curso?.id ?? '', modulo?.id ?? ''],
      },
      { texto: this.datos()?.titulo },
    ];
  });

  /** Lo que se pide a la API: nada si la lección no existe o su módulo no se abre. */
  private readonly pedido = computed<Pedido | undefined>(
    () => {
      const [curso, modulo, leccion] = [this.curso(), this.modulo(), this.leccion()];
      if (!curso || !modulo || !leccion || !this.datos() || !this.datosModulo()?.abierto) {
        return undefined;
      }
      return { curso, modulo, leccion, idioma: this.idioma.actual() };
    },
    // Recargar el catálogo (al completar) arma objetos nuevos: no vuelve a pedir.
    { equal: mismoPedido },
  );

  protected readonly respuesta = resource({
    params: () => this.pedido(),
    loader: ({ params }) =>
      this.api.leccion(params.curso, params.modulo, params.leccion, params.idioma),
  });

  /**
   * La lección en pantalla: `null` si la API dice que no existe y `undefined`
   * mientras llega. Al cambiar el idioma se ve la anterior hasta que llegue la
   * nueva; al cambiar de lección, no.
   */
  protected readonly cuerpo = linkedSignal<
    { valor: LeccionApi | null | undefined; pedido: Pedido | undefined },
    LeccionApi | null | undefined
  >({
    source: () => ({
      valor: this.respuesta.hasValue() ? this.respuesta.value() : undefined,
      pedido: this.pedido(),
    }),
    computation: ({ valor, pedido }, previo) => {
      if (valor !== undefined) {
        return valor;
      }
      const anterior = previo?.value;
      return anterior && anterior.modulo.slug === pedido?.modulo && anterior.slug === pedido.leccion
        ? anterior
        : undefined;
    },
  });

  /** La API dice que el módulo está bloqueado (el catálogo estaba viejo). */
  protected readonly bloqueadoEnApi = computed(
    () => codigoDeError(this.respuesta.error()) === 'modulo_bloqueado',
  );

  protected readonly bloques = computed(() => {
    const cuerpo = this.cuerpo();
    return cuerpo ? analizarMarkdown(cuerpo.contenido) : [];
  });

  /** El comando que cierra cada práctica, con su botón de copiar. */
  protected readonly practicas = computed(() =>
    (this.cuerpo()?.practicas ?? []).map((p) =>
      bloqueDeCodigo('bash', `apolo-training verificar ${p}`),
    ),
  );

  protected readonly anterior = computed(() => this.vecina(this.cuerpo()?.anterior));
  protected readonly siguiente = computed(() => this.vecina(this.cuerpo()?.siguiente));

  /**
   * Se marca a mano si no tiene un video ya subido (decisión del 4-nov); con
   * video, se completa al ver el 90 % (F-05). El quiz todavía no la bloquea.
   */
  protected readonly puedeMarcar = computed(() => {
    const cuerpo = this.cuerpo();
    return !!cuerpo && !cuerpo.videos.some((v) => v.video.disponible);
  });
  protected readonly guardando = signal(false);
  /** Clave del mensaje de error al completar. */
  protected readonly errorCompletar = signal<string | null>(null);
  /** Clave del aviso para lectores de pantalla cuando el video completa la lección. */
  protected readonly anuncio = signal<string | null>(null);
  private readonly avisoHecha = viewChild<ElementRef<HTMLElement>>('hecha');

  constructor() {
    // Cada lección abre la pestaña del clúster del usuario, y no arrastra el
    // error de completar de la anterior.
    effect(() => {
      this.modulo();
      this.leccion();
      untracked(() => {
        this.cluster.reiniciar();
        this.errorCompletar.set(null);
        this.anuncio.set(null);
      });
    });
    // El catálogo creía abierto un módulo que la API dice bloqueado: se pone al día.
    effect(() => {
      if (this.bloqueadoEnApi()) {
        untracked(() => void this.catalogo.recargar());
      }
    });
  }

  protected async completar(): Promise<void> {
    const cuerpo = this.cuerpo();
    if (!cuerpo || this.guardando()) {
      return;
    }
    this.guardando.set(true);
    this.errorCompletar.set(null);
    try {
      const progreso = await this.api.completar(cuerpo.id);
      this.respuesta.value.update((l) => (l?.id === progreso.leccion_id ? { ...l, progreso } : l));
      // El botón desaparece: el foco pasa al aviso «Completaste esta lección».
      afterNextRender(() => this.avisoHecha()?.nativeElement.focus(), {
        injector: this.injector,
      });
      // El avance, la barra lateral y el desbloqueo del módulo siguiente.
      await this.catalogo.recargar();
    } catch (error) {
      const codigo = codigoDeError(error);
      if (codigo === 'modulo_bloqueado') {
        void this.catalogo.recargar();
      }
      this.errorCompletar.set(
        codigo === 'requisitos_pendientes'
          ? 'leccion.completar.requisitos'
          : 'leccion.completar.error',
      );
    } finally {
      this.guardando.set(false);
    }
  }

  /**
   * Lo que respondió la API al reporte del video. El reproductor ya recarga
   * el catálogo cuando la lección se completa; aquí, el estado de la pantalla.
   */
  protected alReportarVideo(progreso: ProgresoLeccionApi): void {
    const antes = this.cuerpo();
    if (antes?.id !== progreso.leccion_id) {
      return;
    }
    this.respuesta.value.update((l) => (l?.id === progreso.leccion_id ? { ...l, progreso } : l));
    if (progreso.completada && !antes.progreso.completada) {
      this.anuncio.set('leccion.completar.alVer');
    }
  }

  private vecina(ref: LeccionRefApi | null | undefined) {
    if (!ref) {
      return null;
    }
    const curso = this.datosCurso();
    const modulo = this.catalogo.modulo(curso, ref.modulo);
    const leccion = this.catalogo.leccion(modulo, ref.slug);
    return {
      ruta: ['/cursos', curso?.id ?? '', ref.modulo, ref.slug],
      numero: leccion?.numero ?? String(ref.modulo_numero),
      titulo: leccion?.titulo ?? ref.titulo,
      abierta: modulo?.abierto ?? false,
      /** El módulo que hay que terminar para abrirla. */
      falta: ref.modulo_numero - 1,
    };
  }
}
