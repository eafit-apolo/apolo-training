import type { ElementRef, WritableSignal } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  Injector,
  afterNextRender,
  computed,
  inject,
  input,
  linkedSignal,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { TranslocoPipe } from '@jsverse/transloco';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import type { Cluster } from '../../core/sesion/sesion';
import { ErrorSi, valorDe } from '../../shared/error-si';
import { Icono } from '../../shared/icono';
import { CORREO_SOPORTE } from '../cuenta/hora';
import type { FaltaGraduacion, GraduacionApi } from './datos';
import { ProgresoApi, SALIDA_MAXIMA, faltasDeGraduacion } from './datos';
import { FormatoFecha } from './formato';

/** La partición de la graduación en cada clúster real (P-01). */
export const PARTICION_GRADUACION: Readonly<Record<Cluster, string>> = {
  apolo2: 'learning',
  apolo3: 'bigmem',
};

type ErrorEnvio = 'aprobada' | 'invalida' | 'conexion' | 'otro';

/**
 * La graduación en Mi progreso (F-07): los pasos cortos para el clúster del
 * perfil, el formulario (JobID y la salida del verificador) y el estado.
 *
 * Sin graduación o rechazada, el formulario está abierto. Enviada, se ve lo
 * enviado y «Corregir envío» lo abre con esos datos (la API deja reenviarla
 * mientras no esté aprobada; decisión del 23-nov). Aprobada, solo el estado y
 * la QOS. Sin `@angular/forms`, como las pantallas de cuenta (F-03).
 */
@Component({
  selector: 'at-graduacion',
  imports: [MatButtonModule, MatFormFieldModule, MatInputModule, TranslocoPipe, Icono, ErrorSi],
  templateUrl: './graduacion.html',
  styleUrl: './graduacion.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GraduacionPanel {
  readonly graduacion = input.required<GraduacionApi | null>();
  readonly cluster = input.required<Cluster>();
  /**
   * Mi progreso debe recargar: `true` si la API la aceptó; `false` si ya
   * estaba aprobada (otra pestaña, o la aprobaron mientras se corregía).
   */
  readonly enviada = output<boolean>();

  private readonly api = inject(ProgresoApi);
  private readonly injector = inject(Injector);
  protected readonly formato = inject(FormatoFecha);
  protected readonly correo = CORREO_SOPORTE;
  protected readonly maximo = SALIDA_MAXIMA;

  /** El formulario se abre solo sin graduación o con una rechazada. */
  protected readonly editando = linkedSignal(() => {
    const g = this.graduacion();
    return g === null || g.estado === 'rechazada';
  });
  protected readonly jobid = signal('');
  protected readonly salida = signal('');
  protected readonly intentado = signal(false);
  protected readonly enviando = signal(false);
  protected readonly error = signal<ErrorEnvio | null>(null);

  protected readonly particion = computed(() => PARTICION_GRADUACION[this.cluster()]);
  protected readonly faltas = computed(() => faltasDeGraduacion(this.jobid(), this.salida()));
  protected readonly largo = computed(() => [...this.salida()].length);

  private readonly campoJobid = viewChild<ElementRef<HTMLInputElement>>('campoJobid');
  private readonly campoSalida = viewChild<ElementRef<HTMLTextAreaElement>>('campoSalida');
  private readonly campoError = viewChild<ElementRef<HTMLElement>>('errorEnvio');

  protected falta(...claves: FaltaGraduacion[]): boolean {
    return this.intentado() && this.faltas().some((f) => claves.includes(f));
  }

  protected escribir(campo: WritableSignal<string>, evento: Event): void {
    campo.set(valorDe(evento));
    this.error.set(null);
  }

  /** «Corregir envío»: el formulario con lo que ya se envió. */
  protected corregir(): void {
    const g = this.graduacion();
    this.jobid.set(g?.jobid ?? '');
    this.salida.set(g?.salida_verificador ?? '');
    this.intentado.set(false);
    this.error.set(null);
    this.editando.set(true);
    afterNextRender(() => this.campoJobid()?.nativeElement.focus(), { injector: this.injector });
  }

  protected cancelar(): void {
    this.editando.set(false);
    this.error.set(null);
  }

  protected async enviar(evento: Event): Promise<void> {
    evento.preventDefault();
    if (this.enviando()) {
      return;
    }
    this.intentado.set(true);
    this.error.set(null);
    const faltas = this.faltas();
    if (faltas.length) {
      // El foco va al primer campo con problema.
      const campo = faltas[0].startsWith('jobid') ? this.campoJobid() : this.campoSalida();
      campo?.nativeElement.focus();
      return;
    }
    this.enviando.set(true);
    try {
      await this.api.enviarGraduacion({ jobid: this.jobid().trim(), salida: this.salida() });
      this.jobid.set('');
      this.salida.set('');
      this.intentado.set(false);
      this.enviada.emit(true);
    } catch (error) {
      const codigo = codigoDeError(error);
      if (codigo === 'graduacion_aprobada') {
        this.error.set('aprobada');
        this.enviada.emit(false);
      } else if (estadoDeError(error) === 422) {
        this.error.set('invalida');
      } else if (estadoDeError(error) === 0) {
        this.error.set('conexion');
      } else {
        this.error.set('otro');
      }
      afterNextRender(() => this.campoError()?.nativeElement.focus(), { injector: this.injector });
    } finally {
      this.enviando.set(false);
    }
  }
}
