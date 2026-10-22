import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../shared/icono';

export interface Enlace {
  readonly ruta: string;
  readonly clave: string;
}

/** Botón ☰ con el menú principal, para tableta y celular (shell.scss lo muestra). */
@Component({
  selector: 'at-menu-movil',
  imports: [MatButtonModule, MatMenuModule, RouterLink, RouterLinkActive, TranslocoPipe, Icono],
  template: `
    <button
      type="button"
      mat-icon-button
      [matMenuTriggerFor]="menu"
      [attr.aria-label]="'shell.menu' | transloco"
    >
      <at-icono nombre="menu" />
    </button>
    <mat-menu #menu="matMenu" xPosition="before">
      @for (enlace of enlaces(); track enlace.ruta) {
        <a
          mat-menu-item
          [routerLink]="enlace.ruta"
          routerLinkActive="activo"
          ariaCurrentWhenActive="page"
        >
          {{ enlace.clave | transloco }}
        </a>
      }
    </mat-menu>
  `,
  styles: `
    :host {
      display: none;
    }

    @media (max-width: 839.98px) {
      :host {
        display: inline-flex;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MenuMovil {
  readonly enlaces = input.required<readonly Enlace[]>();
}
