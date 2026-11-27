import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  Injector,
  ViewEncapsulation,
  afterNextRender,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../core/i18n/idioma';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { Comando } from '../../shared/comando';
import { Icono } from '../../shared/icono';
import type { EstadoGraduacion } from '../progreso/datos';
import { PRACTICAS } from '../progreso/datos';
import { FormatoFecha } from '../progreso/formato';
import type { Decision, GraduacionAdminApi } from './datos';
import { PanelApi, comandoConfirmar } from './datos';
import { PanelEstado } from './estado';

export type FiltroGraduaciones = EstadoGraduacion | 'todas';

/** Un texto para la región `aria-live` o un aviso: clave de traducción y parámetros. */
interface Texto {
  readonly clave: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * Pestaña «Graduaciones» del panel (F-08): las enviadas desde Mi progreso, por
 * estado (por revisar, aprobadas, rechazadas o todas), de la más vieja a la
 * más nueva. Al elegir una se ve la salida del verificador, cuántas prácticas
 * tiene aprobadas y el `sacct` para confirmarla en su clúster; si está por
 * revisar, se aprueba o se rechaza (rechazar exige comentario, como la API).
 */
@Component({
  selector: 'at-panel-graduaciones',
  imports: [MatButtonModule, MatProgressBarModule, TranslocoPipe, Comando, Icono],
  templateUrl: './graduaciones.html',
  styleUrl: './graduaciones.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GraduacionesPanel {
  private readonly api = inject(PanelApi);
  private readonly panel = inject(PanelEstado);
  private readonly idioma = inject(IdiomaService).actual;
  private readonly formato = inject(FormatoFecha);
  private readonly injector = inject(Injector);

  protected readonly totalPracticas = PRACTICAS.length;
  protected readonly filtro = signal<FiltroGraduaciones>('enviada');
  protected readonly lista = signal<readonly GraduacionAdminApi[] | null>(null);
  protected readonly fallo = signal(false);
  protected readonly elegida = signal<string | null>(null);
  protected readonly comentario = signal('');
  protected readonly faltaComentario = signal(false);
  protected readonly enviando = signal<Decision | null>(null);
  /** Un error al revisar (dentro del detalle). */
  protected readonly errorRevision = signal<string | null>(null);
  /** Un aviso sobre la lista (por ejemplo, alguien más ya la revisó). */
  protected readonly aviso = signal<string | null>(null);
  protected readonly anuncio = signal<Texto | null>(null);

  protected readonly graduacion = computed(
    () => this.lista()?.find((g) => g.username === this.elegida()) ?? null,
  );

  private readonly titulo = viewChild<ElementRef<HTMLElement>>('detalleTitulo');
  private readonly campoComentario = viewChild<ElementRef<HTMLTextAreaElement>>('campoComentario');
  private pedido = 0;

  constructor() {
    effect(() => {
      const filtro = this.filtro();
      untracked(() => void this.cargar(filtro));
    });
  }

  protected elegirFiltro(valor: string): void {
    const filtros: readonly FiltroGraduaciones[] = ['enviada', 'aprobada', 'rechazada', 'todas'];
    const filtro = filtros.find((f) => f === valor) ?? 'enviada';
    this.aviso.set(null);
    this.elegida.set(null);
    this.filtro.set(filtro);
  }

  /** Abre el detalle y lleva el foco a su título. */
  protected elegir(graduacion: GraduacionAdminApi): void {
    this.elegida.set(graduacion.username);
    this.comentario.set('');
    this.faltaComentario.set(false);
    this.errorRevision.set(null);
    afterNextRender(() => this.titulo()?.nativeElement.focus(), { injector: this.injector });
  }

  protected cerrar(): void {
    this.elegida.set(null);
  }

  protected escribir(valor: string): void {
    this.comentario.set(valor);
    if (valor.trim() !== '') {
      this.faltaComentario.set(false);
    }
  }

  protected comando(graduacion: GraduacionAdminApi): string {
    return comandoConfirmar(graduacion);
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  protected async revisar(decision: Decision): Promise<void> {
    const graduacion = this.graduacion();
    if (!graduacion || this.enviando()) {
      return;
    }
    if (decision === 'rechazar' && this.comentario().trim() === '') {
      this.faltaComentario.set(true);
      this.campoComentario()?.nativeElement.focus();
      return;
    }
    this.enviando.set(decision);
    this.errorRevision.set(null);
    this.anuncio.set(null);
    try {
      await this.api.revisar(graduacion.username, decision, this.comentario());
      this.elegida.set(null);
      this.anuncio.set({
        clave:
          decision === 'aprobar'
            ? 'panel.graduaciones.avisos.aprobada'
            : 'panel.graduaciones.avisos.rechazada',
        parametros: { username: graduacion.username },
      });
      await this.cargar(this.filtro());
      void this.panel.cargar(this.idioma());
    } catch (error) {
      const codigo = codigoDeError(error);
      if (codigo === 'sin_graduacion_pendiente' || codigo === 'no_encontrado') {
        // Otra persona la revisó, o el usuario la reenvió: se recarga.
        this.elegida.set(null);
        this.aviso.set('panel.graduaciones.avisos.yaRevisada');
        await this.cargar(this.filtro());
        void this.panel.cargar(this.idioma());
      } else if (codigo === 'comentario_obligatorio') {
        this.faltaComentario.set(true);
        this.campoComentario()?.nativeElement.focus();
      } else {
        this.errorRevision.set(
          estadoDeError(error) === 0 ? 'errores.sin_conexion' : 'errores.inesperado',
        );
      }
    } finally {
      this.enviando.set(null);
    }
  }

  protected reintentar(): void {
    void this.cargar(this.filtro());
  }

  private async cargar(filtro: FiltroGraduaciones): Promise<void> {
    const pedido = ++this.pedido;
    try {
      const lista = await this.api.graduaciones(filtro === 'todas' ? null : filtro);
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
