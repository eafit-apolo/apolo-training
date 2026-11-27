import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ViewEncapsulation,
  computed,
  inject,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../core/i18n/idioma';
import { SesionService } from '../../core/sesion/sesion';
import { Icono } from '../../shared/icono';
import { FormatoFecha } from '../progreso/formato';
import { mayorSalto } from './datos';
import { PanelEstado } from './estado';

/** Cada cuánto se recalcula «hace N min» de la sincronización. */
const TIC_MS = 60_000;

/**
 * Pestaña «Resumen» del panel (F-08): las cifras de los estudiantes activos,
 * cuántos completaron cada módulo («dónde se atascan», el insumo de la
 * medición del piloto) y lo que espera una acción: graduaciones por revisar y
 * aprobados sin QOS. Los datos los carga `at-panel` (`PanelEstado`).
 */
@Component({
  selector: 'at-panel-resumen',
  imports: [MatButtonModule, MatProgressBarModule, RouterLink, TranslocoPipe, Icono],
  templateUrl: './resumen.html',
  styleUrl: './resumen.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResumenPanel {
  protected readonly estado = inject(PanelEstado);
  private readonly idioma = inject(IdiomaService).actual;
  private readonly formato = inject(FormatoFecha);
  private readonly sesion = inject(SesionService);

  /** Los aprobados sin QOS se atienden en Administración (solo admin). */
  protected readonly esAdmin = computed(() => this.sesion.rol() === 'admin');
  protected readonly cargando = signal(false);
  protected readonly anuncio = signal('');
  protected readonly ahora = signal(Date.now());

  protected readonly salto = computed(() => {
    const r = this.estado.resumen();
    return r ? mayorSalto(r.avance_por_modulo, r.estudiantes_activos) : null;
  });

  constructor() {
    const reloj = setInterval(() => this.ahora.set(Date.now()), TIC_MS);
    inject(DestroyRef).onDestroy(() => clearInterval(reloj));
  }

  /** El ancho de la barra: la parte de los activos que completó el módulo. */
  protected ancho(completos: number): number {
    const activos = this.estado.resumen()?.estudiantes_activos ?? 0;
    return activos ? Math.round((100 * completos) / activos) : 0;
  }

  protected hace(iso: string): string {
    return this.formato.hace(iso, this.ahora());
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  /** «Actualizar»: vuelve a pedir y lo anuncia sin mover el foco. */
  protected async actualizar(): Promise<void> {
    this.anuncio.set('');
    this.cargando.set(true);
    const ok = await this.estado.cargar(this.idioma());
    this.cargando.set(false);
    this.ahora.set(Date.now());
    if (ok) {
      this.anuncio.set('panel.actualizado');
    }
  }
}
