import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from './icono';

/** Una miga: `clave` se traduce; `texto` (contenido del curso) va tal cual. */
export interface Miga {
  readonly clave?: string;
  readonly texto?: string;
  readonly ruta?: readonly string[];
}

/**
 * Migas de pan. La última es la página actual y no es un enlace. En celular
 * solo se ve el enlace a la página de arriba («‹ Módulo 5»).
 */
@Component({
  selector: 'at-migas',
  imports: [RouterLink, TranslocoPipe, Icono],
  template: `
    <nav [attr.aria-label]="'migas.etiqueta' | transloco">
      <ol>
        @for (miga of migas(); track $index; let ultima = $last) {
          <li [class.padre]="$index === padre()">
            @if (ultima || !miga.ruta) {
              <span aria-current="page">{{
                miga.clave ? (miga.clave | transloco) : miga.texto
              }}</span>
            } @else {
              <a [routerLink]="miga.ruta">
                <at-icono class="atras" nombre="atras" />
                {{ miga.clave ? (miga.clave | transloco) : miga.texto }}
              </a>
              <at-icono class="separador" nombre="siguiente" />
            }
          </li>
        }
      </ol>
    </nav>
  `,
  styles: `
    :host {
      display: block;
      margin-bottom: 8px;
      font: var(--mat-sys-body-medium);
      --at-icono: 18px;
    }

    ol {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    li {
      display: flex;
      align-items: center;
      gap: 4px;
      color: var(--mat-sys-on-surface-variant);
    }

    a {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      min-height: 24px;
      color: var(--mat-sys-primary);
    }

    .atras {
      display: none;
    }

    @media (max-width: 599.98px) {
      li:not(.padre) {
        display: none;
      }

      .separador {
        display: none;
      }

      .atras {
        display: inline-flex;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Migas {
  readonly migas = input.required<readonly Miga[]>();
  protected readonly padre = computed(() => this.migas().length - 2);
}
