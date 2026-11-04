import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  inject,
  input,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { ClusterElegido } from './cluster-elegido';
import { Codigo } from './codigo';
import type { Bloque, Panel } from './markdown';

let siguienteId = 0;

/**
 * Pinta los bloques de `analizarMarkdown()`. El HTML entra por `innerHTML`,
 * así que Angular lo sanitiza (segunda capa, después de markdown.ts). Las
 * listas con código, las citas y las pestañas se pintan con este mismo
 * componente, por dentro.
 *
 * Pestañas según el patrón de WAI-ARIA: Tab entra a la pestaña elegida y las
 * flechas, Inicio y Fin cambian de pestaña.
 */
@Component({
  selector: 'at-bloques',
  imports: [TranslocoPipe, Codigo],
  template: `
    @for (b of bloques(); track $index; let grupo = $index) {
      @switch (b.tipo) {
        @case ('html') {
          <div class="at-md-html" [innerHTML]="b.html"></div>
        }
        @case ('codigo') {
          <at-codigo [bloque]="b" />
        }
        @case ('lista') {
          @if (b.ordenada) {
            <ol [attr.start]="b.inicio === 1 ? null : b.inicio">
              @for (item of b.items; track $index) {
                <li><at-bloques [bloques]="item" /></li>
              }
            </ol>
          } @else {
            <ul>
              @for (item of b.items; track $index) {
                <li><at-bloques [bloques]="item" /></li>
              }
            </ul>
          }
        }
        @case ('cita') {
          <blockquote><at-bloques [bloques]="b.bloques" /></blockquote>
        }
        @case ('pestanas') {
          <div class="at-pestanas">
            @if (b.paneles.length > 1) {
              <div role="tablist" [attr.aria-label]="'leccion.pestanas' | transloco">
                @for (p of b.paneles; track p.cluster) {
                  <button
                    type="button"
                    role="tab"
                    [id]="idDe(grupo, p, 'pestana')"
                    [attr.aria-controls]="idDe(grupo, p, 'panel')"
                    [attr.aria-selected]="p.cluster === cluster.actual()"
                    [tabIndex]="p.cluster === cluster.actual() ? 0 : -1"
                    (click)="cluster.elegir(p.cluster)"
                    (keydown)="teclas($event, b.paneles)"
                  >
                    {{ 'cluster.' + p.cluster | transloco }}
                    @if (p.cluster === cluster.propio()) {
                      <span class="tuyo">{{ 'leccion.tuCluster' | transloco }}</span>
                    }
                  </button>
                }
              </div>
              @for (p of b.paneles; track p.cluster) {
                <div
                  role="tabpanel"
                  class="at-pestanas-panel"
                  [id]="idDe(grupo, p, 'panel')"
                  [attr.aria-labelledby]="idDe(grupo, p, 'pestana')"
                  [hidden]="p.cluster !== cluster.actual()"
                >
                  <at-bloques [bloques]="p.bloques" />
                </div>
              }
            } @else {
              @let p = b.paneles[0];
              <p class="at-pestanas-solo">{{ 'cluster.' + p.cluster | transloco }}</p>
              <div class="at-pestanas-panel"><at-bloques [bloques]="p.bloques" /></div>
            }
          </div>
        }
      }
    }
  `,
  styles: `
    at-bloques {
      display: block;
    }

    at-bloques .at-md-html > :first-child {
      margin-top: 0;
    }

    at-bloques :is(p, li) {
      line-height: 1.6;
    }

    at-bloques h3 {
      margin: 28px 0 8px;
    }

    at-bloques :is(ul, ol) {
      margin: 8px 0 16px;
      padding-left: 28px;
    }

    at-bloques li + li {
      margin-top: 6px;
    }

    at-bloques :not(pre) > code {
      padding: 0.1em 0.35em;
      border-radius: 4px;
      background: var(--mat-sys-surface-container-high);
      font:
        0.9em ui-monospace,
        SFMono-Regular,
        Menlo,
        Consolas,
        monospace;
    }

    at-bloques blockquote {
      margin: 16px 0;
      padding: 4px 16px;
      border-left: 4px solid var(--mat-sys-outline-variant);
    }

    .at-md-tabla {
      margin: 16px 0;
      overflow-x: auto;
    }

    .at-md-tabla table {
      border-collapse: collapse;
    }

    .at-md-tabla :is(th, td) {
      padding: 8px 12px;
      border: 1px solid var(--mat-sys-outline-variant);
      text-align: left;
      vertical-align: top;
    }

    .at-md-tabla th {
      background: var(--mat-sys-surface-container);
    }

    .at-pestanas {
      margin: 16px 0;
    }

    .at-pestanas [role='tablist'] {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }

    .at-pestanas [role='tab'] {
      padding: 10px 16px 8px;
      border: 0;
      border-bottom: 3px solid transparent;
      background: none;
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-title-small);
      cursor: pointer;
    }

    .at-pestanas [role='tab'][aria-selected='true'] {
      border-bottom-color: var(--mat-sys-primary);
      color: var(--mat-sys-primary);
    }

    .at-pestanas [role='tab']:focus-visible {
      outline: 3px solid var(--mat-sys-primary);
      outline-offset: -3px;
    }

    .at-pestanas .tuyo {
      font: var(--mat-sys-body-small);
    }

    .at-pestanas-solo {
      margin: 0;
      font: var(--mat-sys-title-small);
      color: var(--mat-sys-primary);
    }

    .at-pestanas-panel {
      padding: 16px 0 0;
    }

    .at-pestanas-panel[hidden] {
      display: none;
    }
  `,
  // El HTML de las lecciones entra por innerHTML (sin los atributos de la
  // encapsulación): los estilos van con el prefijo at-bloques.
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Bloques {
  readonly bloques = input.required<readonly Bloque[]>();

  protected readonly cluster = inject(ClusterElegido);
  private readonly id = `at-md-${siguienteId++}`;

  protected idDe(grupo: number, panel: Panel, parte: 'pestana' | 'panel'): string {
    return `${this.id}-${grupo}-${parte}-${panel.cluster}`;
  }

  protected teclas(evento: KeyboardEvent, paneles: readonly Panel[]): void {
    const actual = paneles.findIndex((p) => p.cluster === this.cluster.actual());
    const destino = {
      ArrowRight: (actual + 1) % paneles.length,
      ArrowLeft: (actual - 1 + paneles.length) % paneles.length,
      Home: 0,
      End: paneles.length - 1,
    }[evento.key];
    if (destino === undefined) {
      return;
    }
    evento.preventDefault();
    this.cluster.elegir(paneles[destino].cluster);
    const pestanas = (evento.currentTarget as HTMLElement).parentElement?.children;
    (pestanas?.[destino] as HTMLElement | undefined)?.focus();
  }
}
