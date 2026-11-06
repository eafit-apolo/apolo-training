import { HttpErrorResponse } from '@angular/common/http';
import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  DestroyRef,
  afterNextRender,
  afterRenderEffect,
  computed,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../../core/i18n/idioma';
import { SesionService } from '../../../core/sesion/sesion';
import { Icono } from '../../../shared/icono';
import type { ProgresoLeccionApi, VideoRefApi } from '../datos/api';
import { ContenidoApi } from '../datos/api';
import { CatalogoService } from '../datos/catalogo';
import type { Subtitulos } from './preferencias-video';
import { PreferenciasVideo, VELOCIDADES } from './preferencias-video';

/** Cada cuánto se reporta el segundo mientras el video corre (F-05). */
export const CADA_MS = 15_000;

/**
 * Sin hablar con la API durante este tiempo, la cookie `at` (15 min) pudo
 * vencer: al dar play se comprueba la sesión antes de que el video la necesite.
 */
export const PAUSA_LARGA_MS = 10 * 60_000;

/** Desde dónde empezar: el segundo guardado, salvo al principio (< 5 s) o ya visto (≥ 90 %). */
export function inicioDe(posicion: number, duracion: number): number {
  return posicion >= 5 && duracion > 0 && posicion < duracion * 0.9 ? posicion : 0;
}

/** 222 → «3:42»; 3723 → «1:02:03». */
export function tiempo(segundos: number): string {
  const total = Math.max(0, Math.floor(segundos));
  const [h, m, s] = [Math.floor(total / 3600), Math.floor((total % 3600) / 60), total % 60];
  const dos = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${dos(m)}:${dos(s)}` : `${m}:${dos(s)}`;
}

function pistas(video: HTMLVideoElement): TextTrack[] {
  return Array.from((video.textTracks ?? []) as ArrayLike<TextTrack>);
}

/** Deja visible solo la pista elegida (o ninguna). */
function mostrar(video: HTMLVideoElement, elegidos: Subtitulos): void {
  for (const pista of pistas(video)) {
    const modo: TextTrackMode = pista.language === elegidos ? 'showing' : 'disabled';
    if (pista.mode !== modo) {
      pista.mode = modo;
    }
  }
}

/**
 * Lo que eligió el usuario en el menú del navegador: la única pista visible, o
 * ninguna. Con más de una visible no eligió él: Chrome a veces prende otra por
 * su cuenta al cargar (pasó al recargar con los de inglés puestos), y eso no
 * es una elección (`null`).
 */
function elegidaEnElNavegador(video: HTMLVideoElement): Subtitulos | null {
  const visibles = pistas(video).filter((p) => p.mode === 'showing');
  if (visibles.length > 1) {
    return null;
  }
  const idioma = visibles[0]?.language;
  return idioma === 'es' || idioma === 'en' ? idioma : 'no';
}

/**
 * El reproductor de un video (F-05). Usa los controles del navegador (teclado,
 * lectores de pantalla, pantalla completa y celulares funcionan solos) y suma
 * debajo la velocidad y los subtítulos, que no todos los navegadores traen.
 *
 * - Subtítulos: por defecto en inglés con la interfaz en inglés y apagados en
 *   español; la elección se recuerda por idioma (`PreferenciasVideo`) y
 *   cambia en vivo con el selector ES/EN.
 * - Retoma en el segundo guardado (salvo al principio o si ya lo vio).
 * - Reporta el segundo a `POST /api/progreso/video` cada 15 s mientras corre,
 *   al pausar, al saltar en pausa, al terminar, al ocultar la pestaña y al
 *   salir de la lección. Al pasar el 90 % la API completa la lección: el
 *   catálogo se recarga (barra lateral y módulo siguiente).
 * - El `<video>` pide el archivo sin el interceptor: tras una pausa larga su
 *   petición da 401 y el elemento falla. Entonces se comprueba la sesión (el
 *   interceptor la renueva), se vuelve a cargar y sigue en el mismo segundo.
 */
@Component({
  selector: 'at-reproductor',
  imports: [TranslocoPipe, Icono],
  template: `
    <div class="marco">
      <video
        #elementoVideo
        controls
        playsinline
        preload="metadata"
        [src]="video().url"
        (loadedmetadata)="alCargar()"
        (canplay)="alPoder()"
        (play)="alReproducir()"
        (pause)="alPausar()"
        (ended)="alTerminar()"
        (seeked)="alSaltar()"
        (ratechange)="alCambiarVelocidad()"
        (error)="alFallar()"
      >
        @for (s of video().subtitulos; track s.idioma) {
          <track
            kind="subtitles"
            [src]="s.url"
            [attr.srclang]="s.idioma"
            [label]="'idioma.' + s.idioma | transloco"
          />
        }
      </video>
      @if (fallo()) {
        <div class="fallo" role="alert">
          <p class="titulo">{{ 'leccion.video.error.titulo' | transloco }}</p>
          <p>{{ 'leccion.video.error.mensaje' | transloco }}</p>
          <button type="button" (click)="reintentar()">
            <at-icono nombre="reintentar" />
            {{ 'leccion.error.reintentar' | transloco }}
          </button>
        </div>
      }
    </div>
    <div class="controles">
      <label>
        <span>{{ 'leccion.video.velocidad' | transloco }}</span>
        <select #velocidad (change)="elegirVelocidad(+velocidad.value)">
          @for (o of velocidades(); track o.valor) {
            <option [value]="o.valor" [selected]="o.valor === velocidadActual()">
              {{ o.texto ?? ('leccion.video.normal' | transloco) }}
            </option>
          }
        </select>
      </label>
      @if (video().subtitulos.length) {
        <label>
          <span>{{ 'leccion.video.subtitulos' | transloco }}</span>
          <select #pista (change)="elegirSubtitulos(pista.value)">
            <option value="no" [selected]="subtitulos() === 'no'">
              {{ 'leccion.video.sinSubtitulos' | transloco }}
            </option>
            @for (s of video().subtitulos; track s.idioma) {
              <option [value]="s.idioma" [selected]="subtitulos() === s.idioma">
                {{ 'idioma.' + s.idioma | transloco }}
              </option>
            }
          </select>
        </label>
      }
      @if (retomado(); as segundo) {
        <p class="retomado">
          {{ 'leccion.video.retomado' | transloco: { tiempo: tiempo(segundo) } }}
          <button type="button" class="enlace" (click)="desdeElInicio()">
            {{ 'leccion.video.desdeInicio' | transloco }}
          </button>
        </p>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }

    .marco {
      position: relative;
    }

    video {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      border-radius: 12px;
      background: #000;
    }

    .fallo {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 16px;
      border-radius: 12px;
      background: rgb(0 0 0 / 85%);
      color: #fff;
      text-align: center;
    }

    .fallo p {
      margin: 0;
    }

    .fallo .titulo {
      font: var(--mat-sys-title-medium);
    }

    .fallo button {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      padding: 8px 16px;
      border: 1px solid #fff;
      border-radius: 20px;
      background: transparent;
      color: #fff;
      font: var(--mat-sys-label-large);
      cursor: pointer;
      --at-icono: 20px;
    }

    .controles {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 20px;
      margin-top: 10px;
    }

    label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font: var(--mat-sys-label-large);
    }

    select {
      min-height: 40px;
      padding: 0 10px;
      border: 1px solid var(--mat-sys-outline);
      border-radius: 8px;
      background: var(--mat-sys-surface);
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-body-medium);
    }

    .retomado {
      margin: 0;
      font: var(--mat-sys-body-medium);
      color: var(--mat-sys-on-surface-variant);
    }

    .enlace {
      padding: 0;
      border: 0;
      background: none;
      color: var(--mat-sys-primary);
      font: inherit;
      text-decoration: underline;
      cursor: pointer;
    }

    select:focus-visible,
    button:focus-visible {
      outline: 3px solid var(--mat-sys-primary);
      outline-offset: 2px;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Reproductor {
  readonly video = input.required<VideoRefApi>();
  readonly leccionId = input.required<number>();
  /** El progreso de la lección al abrirla: de ahí salen el segundo para retomar y si ya estaba completa. */
  readonly progreso = input.required<ProgresoLeccionApi>();
  /** `false` para los otros videos de la lección de VPN: solo retoma el que se abrió primero. */
  readonly retomar = input(true);
  /** `false` en un módulo bloqueado (un instructor que lo lee): no se reporta nada. */
  readonly guardar = input(true);
  /** Cada respuesta de la API, para que la lección muestre su progreso. */
  readonly reportado = output<ProgresoLeccionApi>();

  private readonly api = inject(ContenidoApi);
  private readonly sesion = inject(SesionService);
  private readonly catalogo = inject(CatalogoService);
  private readonly idioma = inject(IdiomaService);
  private readonly preferencias = inject(PreferenciasVideo);
  private readonly documento = inject(DOCUMENT);
  private readonly destruir = inject(DestroyRef);
  private readonly referencia = viewChild.required<ElementRef<HTMLVideoElement>>('elementoVideo');

  protected readonly tiempo = tiempo;
  protected readonly fallo = signal(false);
  /** El segundo en que retomó, para «Seguiste donde ibas». */
  protected readonly retomado = signal<number | null>(null);
  protected readonly velocidadActual = signal(this.preferencias.velocidad());
  protected readonly velocidades = computed(() => {
    const formato = new Intl.NumberFormat(this.idioma.actual());
    const actual = this.velocidadActual();
    const lista = VELOCIDADES.includes(actual) ? VELOCIDADES : [...VELOCIDADES, actual];
    return [...lista]
      .sort((a, b) => a - b)
      .map((valor) => ({ valor, texto: valor === 1 ? null : `${formato.format(valor)}x` }));
  });
  /** La pista elegida para el idioma de la interfaz, si el video la tiene. */
  protected readonly subtitulos = computed<Subtitulos>(() => {
    const elegidos = this.preferencias.subtitulos(this.idioma.actual());
    return this.video().subtitulos.some((s) => s.idioma === elegidos) ? elegidos : 'no';
  });

  /** El elemento, guardado para leerlo también al destruir el componente. */
  private elemento: HTMLVideoElement | null = null;
  private porRetomar = true;
  private temporizador: ReturnType<typeof setInterval> | undefined;
  private reproduciendo = false;
  /** Lo último que tiene la API, para no repetir el mismo segundo. */
  private ultimoReportado: number | null = null;
  private ultimaPosicion = 0;
  private enviando = false;
  private pendiente = false;
  /** Un 403 o 404 de la API: no vale la pena seguir reportando. */
  private detenido = false;
  private destruido = false;
  private completada: boolean | null = null;
  private ultimoContacto = Date.now();
  /** Entre un fallo del video y la siguiente carga que sí sirve. */
  private recuperando = false;
  private retomarEn: { readonly segundo: number; readonly seguir: boolean } | null = null;

  constructor() {
    afterNextRender(() => {
      const elemento = this.referencia().nativeElement;
      this.elemento = elemento;
      // El usuario eligió una pista en el menú del navegador: se recuerda. Si
      // el navegador prendió otra por su cuenta, se vuelve a la elegida.
      const lista = elemento.textTracks as TextTrackList | undefined;
      const alCambiarPistas = () => {
        const ahora = elegidaEnElNavegador(elemento);
        if (ahora === null) {
          mostrar(elemento, this.subtitulos());
        } else if (ahora !== this.subtitulos()) {
          this.preferencias.guardarSubtitulos(this.idioma.actual(), ahora);
        }
      };
      lista?.addEventListener?.('change', alCambiarPistas);
      this.destruir.onDestroy(() => lista?.removeEventListener?.('change', alCambiarPistas));
    });
    afterRenderEffect(() => {
      const elegidos = this.subtitulos();
      mostrar(this.referencia().nativeElement, elegidos);
    });

    const alOcultar = () => {
      if (this.documento.visibilityState === 'hidden') {
        void this.reportar({ alSalir: true });
      }
    };
    const alSalirDeLaPagina = () => void this.reportar({ alSalir: true });
    const ventana = this.documento.defaultView;
    this.documento.addEventListener('visibilitychange', alOcultar);
    ventana?.addEventListener('pagehide', alSalirDeLaPagina);
    this.destruir.onDestroy(() => {
      this.documento.removeEventListener('visibilitychange', alOcultar);
      ventana?.removeEventListener('pagehide', alSalirDeLaPagina);
      this.destruido = true;
      this.parar();
      // Al ir a otra lección: lo último antes de que el video desaparezca.
      void this.reportar();
    });
  }

  protected alCargar(): void {
    const elemento = this.elemento ?? this.referencia().nativeElement;
    const velocidad = this.preferencias.velocidad();
    elemento.defaultPlaybackRate = velocidad;
    elemento.playbackRate = velocidad;
    mostrar(elemento, this.subtitulos());
    this.ultimoReportado ??= this.progreso().video_posicion_seg;

    if (this.retomarEn) {
      // Volvió a cargar tras un fallo: al mismo segundo, y sigue si iba corriendo.
      const { segundo, seguir } = this.retomarEn;
      this.retomarEn = null;
      // Chrome deja pintado el subtítulo de antes del fallo: apagar y prender
      // la pista lo borra.
      mostrar(elemento, 'no');
      mostrar(elemento, this.subtitulos());
      elemento.currentTime = segundo;
      if (seguir) {
        void elemento.play()?.catch(() => undefined);
      }
      return;
    }
    if (this.porRetomar) {
      this.porRetomar = false;
      const duracion = Number.isFinite(elemento.duration)
        ? elemento.duration
        : (this.video().duracion_seg ?? 0);
      const inicio = this.retomar() ? inicioDe(this.progreso().video_posicion_seg, duracion) : 0;
      if (inicio > 0) {
        elemento.currentTime = inicio;
        this.retomado.set(inicio);
      }
    }
  }

  /** Llegaron datos: la carga que siguió a un fallo sí sirvió. */
  protected alPoder(): void {
    this.recuperando = false;
  }

  protected alReproducir(): void {
    this.reproduciendo = true;
    if (Date.now() - this.ultimoContacto > PAUSA_LARGA_MS) {
      void this.comprobarSesion();
    }
    this.parar();
    this.temporizador = setInterval(() => void this.reportar(), CADA_MS);
  }

  protected alPausar(): void {
    this.reproduciendo = false;
    this.parar();
    void this.reportar();
  }

  protected alTerminar(): void {
    this.reproduciendo = false;
    this.parar();
    const duracion = this.elemento?.duration;
    void this.reportar({
      segundo: duracion && Number.isFinite(duracion) ? Math.ceil(duracion) : undefined,
    });
  }

  /** Saltar con el video en pausa también cuenta: si cierra ahí, retoma ahí. */
  protected alSaltar(): void {
    if (this.elemento?.paused) {
      void this.reportar();
    }
  }

  protected alCambiarVelocidad(): void {
    const velocidad = this.elemento?.playbackRate;
    if (velocidad !== undefined) {
      this.velocidadActual.set(velocidad);
      this.preferencias.guardarVelocidad(velocidad);
    }
  }

  protected elegirVelocidad(velocidad: number): void {
    const elemento = this.elemento;
    if (elemento && Number.isFinite(velocidad)) {
      elemento.defaultPlaybackRate = velocidad;
      elemento.playbackRate = velocidad;
    }
  }

  protected elegirSubtitulos(valor: string): void {
    if (valor === 'no' || valor === 'es' || valor === 'en') {
      this.preferencias.guardarSubtitulos(this.idioma.actual(), valor);
    }
  }

  protected desdeElInicio(): void {
    if (this.elemento) {
      this.elemento.currentTime = 0;
    }
    this.retomado.set(null);
  }

  protected alFallar(): void {
    if (this.recuperando) {
      // Falló otra vez justo después de recuperar: que el usuario lo intente.
      this.recuperando = false;
      this.fallo.set(true);
      return;
    }
    void this.recuperar();
  }

  protected reintentar(): void {
    this.fallo.set(false);
    void this.recuperar();
  }

  private async recuperar(): Promise<void> {
    const elemento = this.elemento;
    if (!elemento) {
      return;
    }
    this.recuperando = true;
    this.retomarEn ??= {
      segundo: elemento.currentTime || this.ultimaPosicion,
      seguir: this.reproduciendo,
    };
    this.reproduciendo = false;
    this.parar();
    try {
      // Si `at` venció, el interceptor la renueva; si la sesión terminó, lleva a /ingresar.
      await this.sesion.comprobar();
      this.ultimoContacto = Date.now();
    } catch {
      this.recuperando = false;
      this.fallo.set(true);
      return;
    }
    elemento.load();
  }

  private async comprobarSesion(): Promise<void> {
    try {
      await this.sesion.comprobar();
      this.ultimoContacto = Date.now();
    } catch {
      // Si el video llega a fallar, recuperar() lo intenta otra vez.
    }
  }

  private parar(): void {
    clearInterval(this.temporizador);
    this.temporizador = undefined;
  }

  private async reportar(opciones: { segundo?: number; alSalir?: boolean } = {}): Promise<void> {
    const elemento = this.elemento;
    if (!elemento || !this.guardar() || this.detenido) {
      return;
    }
    const actual = Number.isFinite(elemento.currentTime) ? elemento.currentTime : 0;
    this.ultimaPosicion = actual;
    const segundo = Math.max(0, opciones.segundo ?? Math.round(actual));
    if (segundo === this.ultimoReportado) {
      return;
    }
    if (this.enviando && !opciones.alSalir) {
      // Al terminar el que va en camino se manda el segundo de ese momento.
      this.pendiente = true;
      return;
    }
    this.enviando = true;
    try {
      const progreso = await this.api.reportarVideo(
        { leccion_id: this.leccionId(), video_id: this.video().id, segundo },
        opciones.alSalir,
      );
      this.ultimoReportado = segundo;
      this.ultimoContacto = Date.now();
      // «Seguiste donde ibas» ya cumplió: sigue viendo (o pausó) desde ahí.
      this.retomado.set(null);
      const antes = this.completada ?? this.progreso().completada;
      this.completada = progreso.completada;
      if (!this.destruido) {
        this.reportado.emit(progreso);
      }
      if (progreso.completada && !antes) {
        // El avance, la barra lateral y el desbloqueo del módulo siguiente.
        void this.catalogo.recargar();
      }
    } catch (error) {
      if (error instanceof HttpErrorResponse && (error.status === 403 || error.status === 404)) {
        this.detenido = true;
        this.parar();
      }
      // Sin conexión: va con el siguiente reporte.
    } finally {
      this.enviando = false;
      if (this.pendiente) {
        this.pendiente = false;
        void this.reportar();
      }
    }
  }
}
