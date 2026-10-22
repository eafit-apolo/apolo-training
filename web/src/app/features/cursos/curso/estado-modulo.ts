import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import type { NombreIcono } from '../../../shared/icono';
import { Icono } from '../../../shared/icono';
import type { EstadoModulo as Estado } from '../datos/curso';

const ICONOS: Record<Estado, NombreIcono> = {
  completo: 'completo',
  'en-curso': 'en-curso',
  bloqueado: 'bloqueado',
};

/**
 * Estado de un módulo con ícono y texto (no solo color, WCAG 1.4.1). Con
 * `compacto` el texto es corto y queda solo para el lector de pantalla.
 */
@Component({
  selector: 'at-estado-modulo',
  imports: [TranslocoPipe, Icono],
  template: `
    <at-icono [nombre]="icono()" />
    <span [class.at-oculto]="compacto()">
      @if (estado() === 'bloqueado' && !compacto()) {
        {{ 'estado.bloqueadoHasta' | transloco: { n: anterior() } }}
      } @else {
        {{ 'estado.' + estado() | transloco }}
      }
    </span>
  `,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font: var(--mat-sys-label-medium);
      color: var(--mat-sys-on-surface-variant);
    }

    :host(.completo) at-icono {
      color: var(--at-verde);
    }

    :host(.en-curso) at-icono {
      color: var(--mat-sys-primary);
    }
  `,
  host: { '[class]': 'estado()' },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EstadoModulo {
  readonly estado = input.required<Estado>();
  /** Número del módulo que hay que terminar para abrir este. */
  readonly anterior = input(0);
  readonly compacto = input(false);
  protected readonly icono = computed(() => ICONOS[this.estado()]);
}
