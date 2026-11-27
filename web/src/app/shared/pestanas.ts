import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';

/** Una pestaña: una ruta con su título (clave de traducción). */
export interface Pestana {
  readonly ruta: string;
  readonly clave: string;
  /** Activa solo en esa ruta exacta (la de «Resumen», que es la raíz). */
  readonly exacta?: boolean;
  /** Un número al lado («Graduaciones 2»); 0 o `null` no se muestra. */
  readonly cuenta?: number | null;
  /** Lo que lee el lector de pantalla con la cuenta («2 por revisar»). */
  readonly cuentaClave?: string;
}

/**
 * Pestañas del panel y de la administración (F-08): enlaces a rutas hijas,
 * con `aria-current="page"` en la activa. Son navegación, no un `tablist`:
 * cada una es una página con su dirección.
 */
@Component({
  selector: 'at-pestanas',
  imports: [RouterLink, RouterLinkActive, TranslocoPipe],
  template: `
    <nav [attr.aria-label]="etiqueta() | transloco">
      <ul>
        @for (p of pestanas(); track p.ruta) {
          <li>
            <a
              [routerLink]="p.ruta"
              routerLinkActive="activa"
              [routerLinkActiveOptions]="{ exact: p.exacta ?? false }"
              ariaCurrentWhenActive="page"
            >
              {{ p.clave | transloco }}
              @if (p.cuenta) {
                <span class="cuenta" aria-hidden="true">{{ p.cuenta }}</span>
                @if (p.cuentaClave) {
                  <span class="at-oculto">{{ p.cuentaClave | transloco: { n: p.cuenta } }}</span>
                }
              }
            </a>
          </li>
        }
      </ul>
    </nav>
  `,
  styles: `
    :host {
      display: block;
      margin: 0 0 24px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }

    ul {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    a {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 44px;
      padding: 0 16px;
      border-bottom: 3px solid transparent;
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-title-small);
      text-decoration: none;
    }

    a:hover {
      color: var(--mat-sys-on-surface);
      background: var(--mat-sys-surface-container);
    }

    a:focus-visible {
      outline: 3px solid var(--mat-sys-primary);
      outline-offset: -3px;
    }

    a.activa {
      border-bottom-color: var(--mat-sys-primary);
      color: var(--mat-sys-primary);
    }

    .cuenta {
      min-width: 22px;
      padding: 0 6px;
      border-radius: 999px;
      background: var(--mat-sys-tertiary-container);
      color: var(--mat-sys-on-tertiary-container);
      font: var(--mat-sys-label-medium);
      text-align: center;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Pestanas {
  readonly pestanas = input.required<readonly Pestana[]>();
  /** Clave de traducción del nombre de la navegación. */
  readonly etiqueta = input.required<string>();
}
