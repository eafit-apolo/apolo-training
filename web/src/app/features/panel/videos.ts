import { DOCUMENT } from '@angular/common';
import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Subscription } from 'rxjs';
import type { Idioma } from '../../core/i18n/idioma';
import { IdiomaService } from '../../core/i18n/idioma';
import { campoDeError, codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { SesionService } from '../../core/sesion/sesion';
import { confirmar } from '../../shared/confirmar';
import { Icono } from '../../shared/icono';
import { CatalogoService } from '../cursos/datos/catalogo';
import type { Destino, VideoAdminApi } from './datos';
import { LIMITE_VIDEO, LIMITE_VTT, PanelApi, duracion, revisarArchivo, tamano } from './datos';
import { SubidasApi } from './subidas';

/** La subida en curso (una a la vez en toda la pantalla). */
interface Subida {
  readonly clave: string;
  readonly destino: Destino;
  readonly archivo: string;
  readonly cargado: number;
  readonly total: number;
}

/** Un texto para la región `aria-live` o un aviso: clave de traducción y parámetros. */
interface Texto {
  readonly clave: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * Pestaña «Videos» del panel (F-08): los videos que creó el importador (la
 * clave sale del front matter de cada lección: aquí solo se suben archivos),
 * con su MP4, su duración y sus subtítulos en español e inglés.
 *
 * Decisiones del 27-nov: una subida a la vez, con «Cancelar»; antes de
 * reemplazar un archivo ya subido se pregunta; el navegador revisa la
 * extensión y el tamaño antes de enviar (el formato real lo revisa la API) y
 * la sesión se comprueba antes de empezar, para no reenviar 2 GB por una
 * renovación.
 */
@Component({
  selector: 'at-panel-videos',
  imports: [MatButtonModule, MatProgressBarModule, RouterLink, TranslocoPipe, Icono],
  templateUrl: './videos.html',
  styleUrl: './videos.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideosPanel {
  private readonly api = inject(PanelApi);
  private readonly subidas = inject(SubidasApi);
  private readonly sesion = inject(SesionService);
  private readonly dialogo = inject(MatDialog);
  private readonly catalogo = inject(CatalogoService);
  private readonly documento = inject(DOCUMENT);
  protected readonly idioma = inject(IdiomaService).actual;

  protected readonly idiomas: readonly Idioma[] = ['es', 'en'];
  protected readonly lista = signal<readonly VideoAdminApi[] | null>(null);
  protected readonly fallo = signal(false);
  protected readonly subida = signal<Subida | null>(null);
  protected readonly error = signal<Texto | null>(null);
  protected readonly anuncio = signal<Texto | null>(null);

  /** El curso, para enlazar cada video con su lección (el catálogo lo sabe). */
  protected readonly curso = computed(() => this.catalogo.cursos()[0]?.id ?? null);
  protected readonly porcentaje = computed(() => {
    const s = this.subida();
    return s && s.total ? Math.round((100 * s.cargado) / s.total) : 0;
  });

  private readonly selector = viewChild.required<ElementRef<HTMLInputElement>>('selector');
  /** El botón que abrió el selector de archivos. */
  private elegido: { readonly video: VideoAdminApi; readonly destino: Destino } | null = null;
  private suscripcion: Subscription | null = null;
  /** Sube con cada subida o cancelación: una respuesta de una subida vieja se ignora. */
  private intento = 0;
  private pedido = 0;

  constructor() {
    effect(() => {
      const idioma = this.idioma();
      untracked(() => void this.cargar(idioma));
    });
    // Solo para los enlaces a las lecciones; si falla, van sin enlace.
    this.catalogo.cargarCatalogo().catch(() => undefined);

    // Cerrar la pestaña a mitad de una subida la pierde: el navegador pregunta.
    const alSalir = (evento: BeforeUnloadEvent) => {
      if (this.subida()) {
        evento.preventDefault();
      }
    };
    const ventana = this.documento.defaultView;
    ventana?.addEventListener('beforeunload', alSalir);
    inject(DestroyRef).onDestroy(() => {
      ventana?.removeEventListener('beforeunload', alSalir);
      this.suscripcion?.unsubscribe();
    });
  }

  /** «Subir» o «Reemplazar»: abre el selector de archivos del sistema. */
  protected elegirArchivo(video: VideoAdminApi, destino: Destino): void {
    if (this.subida()) {
      this.error.set({ clave: 'panel.videos.ocupado' });
      return;
    }
    this.error.set(null);
    this.elegido = { video, destino };
    const campo = this.selector().nativeElement;
    campo.accept = destino === 'video' ? '.mp4,video/mp4' : '.vtt,text/vtt';
    campo.value = '';
    campo.click();
  }

  protected async alElegir(campo: HTMLInputElement): Promise<void> {
    const archivo = campo.files?.[0];
    const elegido = this.elegido;
    this.elegido = null;
    if (!archivo || !elegido) {
      return;
    }
    const { video, destino } = elegido;
    const falta = revisarArchivo(destino, archivo);
    if (falta) {
      this.error.set({
        clave: `panel.videos.faltas.${falta}`,
        parametros: { archivo: archivo.name, maximo: this.maximo(destino) },
      });
      return;
    }
    const existe = destino === 'video' ? video.disponible : video.subtitulos[destino];
    if (
      existe &&
      !(await confirmar(this.dialogo, {
        titulo:
          destino === 'video'
            ? 'panel.videos.reemplazar.tituloVideo'
            : 'panel.videos.reemplazar.tituloVtt',
        mensaje: 'panel.videos.reemplazar.mensaje',
        confirmar: 'panel.videos.reemplazar.confirmar',
        parametros: { clave: video.clave, idioma: destino.toUpperCase() },
      }))
    ) {
      return;
    }
    await this.empezar(video.clave, destino, archivo, true);
  }

  protected cancelar(): void {
    this.intento++;
    this.suscripcion?.unsubscribe();
    this.suscripcion = null;
    this.subida.set(null);
    this.anuncio.set({ clave: 'panel.videos.cancelada' });
  }

  protected reintentar(): void {
    void this.cargar(this.idioma());
  }

  protected duracion(segundos: number): string {
    return duracion(segundos);
  }

  /** «124 MB», «1,5 GB»… en el idioma de la interfaz. */
  protected tamano(bytes: number): string {
    const { valor, unidad } = tamano(bytes);
    return new Intl.NumberFormat(this.idioma(), {
      style: 'unit',
      unit: unidad,
      unitDisplay: 'short',
      maximumFractionDigits: 1,
    }).format(valor);
  }

  private maximo(destino: Destino): string {
    return this.tamano(destino === 'video' ? LIMITE_VIDEO : LIMITE_VTT);
  }

  private async empezar(
    clave: string,
    destino: Destino,
    archivo: File,
    puedeReintentar: boolean,
  ): Promise<void> {
    const intento = ++this.intento;
    this.error.set(null);
    this.subida.set({ clave, destino, archivo: archivo.name, cargado: 0, total: archivo.size });
    this.anuncio.set({
      clave: 'panel.videos.empieza',
      parametros: { archivo: archivo.name, clave },
    });
    try {
      // Si `at` venció, el interceptor lo renueva aquí y no a mitad de la subida.
      await this.sesion.comprobar();
    } catch (error) {
      if (intento === this.intento) {
        this.subida.set(null);
        this.error.set(this.errorDe(error));
      }
      return;
    }
    if (intento !== this.intento) {
      return; // Se canceló mientras se comprobaba la sesión.
    }
    this.suscripcion = this.subidas.subir(clave, destino, archivo).subscribe({
      next: (evento) => {
        if (intento !== this.intento) {
          return;
        }
        if (evento.tipo === 'progreso') {
          this.subida.update((s) => s && { ...s, cargado: evento.cargado, total: evento.total });
          return;
        }
        this.suscripcion = null;
        this.lista.update((lista) =>
          lista ? lista.map((v) => (v.id === evento.video.id ? evento.video : v)) : lista,
        );
        this.subida.set(null);
        this.anuncio.set({
          clave: 'panel.videos.listo',
          parametros: { archivo: archivo.name, clave },
        });
      },
      error: (error: unknown) => {
        if (intento !== this.intento) {
          return;
        }
        this.suscripcion = null;
        if (estadoDeError(error) === 401 && puedeReintentar) {
          // La sesión venció justo al empezar: se renueva y se intenta una vez más.
          void this.empezar(clave, destino, archivo, false);
          return;
        }
        this.subida.set(null);
        this.error.set(this.errorDe(error));
      },
    });
  }

  private errorDe(error: unknown): Texto {
    const detalle = campoDeError(error, 'detail');
    switch (codigoDeError(error)) {
      case 'video_formato_invalido':
        return { clave: 'panel.videos.errores.formato', parametros: { detalle } };
      case 'vtt_invalido':
        return { clave: 'panel.videos.errores.vtt', parametros: { detalle } };
      case 'archivo_muy_grande':
        return { clave: 'panel.videos.errores.muyGrande' };
      case 'no_encontrado':
        return { clave: 'panel.videos.errores.noExiste' };
    }
    return { clave: estadoDeError(error) === 0 ? 'errores.sin_conexion' : 'errores.inesperado' };
  }

  private async cargar(idioma: Idioma): Promise<void> {
    const pedido = ++this.pedido;
    try {
      const lista = await this.api.videos(idioma);
      if (pedido === this.pedido) {
        this.lista.set(lista);
        this.fallo.set(false);
      }
    } catch {
      if (pedido === this.pedido) {
        this.fallo.set(true);
      }
    }
  }
}
