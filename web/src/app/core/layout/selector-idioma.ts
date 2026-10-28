import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import type { MatButtonToggleChange } from '@angular/material/button-toggle';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Idioma } from '../i18n/idioma';
import { IDIOMAS, IdiomaService, esIdioma } from '../i18n/idioma';
import { SesionService } from '../sesion/sesion';

/** Cada idioma se nombra en su propia lengua, sin importar el idioma activo. */
const NOMBRES: Record<Idioma, string> = { es: 'Español', en: 'English' };

@Component({
  selector: 'at-selector-idioma',
  imports: [MatButtonToggleModule, TranslocoPipe],
  template: `
    <mat-button-toggle-group
      hideSingleSelectionIndicator
      [value]="idioma.actual()"
      (change)="elegir($event)"
      [attr.aria-label]="'idioma.etiqueta' | transloco"
    >
      @for (codigo of idiomas; track codigo) {
        <mat-button-toggle [value]="codigo" [attr.lang]="codigo" [aria-label]="nombres[codigo]">
          {{ codigo.toUpperCase() }}
        </mat-button-toggle>
      }
    </mat-button-toggle-group>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SelectorIdioma {
  protected readonly idioma = inject(IdiomaService);
  private readonly sesion = inject(SesionService);
  protected readonly idiomas = IDIOMAS;
  protected readonly nombres = NOMBRES;

  protected elegir(evento: MatButtonToggleChange): void {
    if (esIdioma(evento.value)) {
      // Con sesión también se guarda en el perfil (PATCH /api/me).
      void this.sesion.cambiarIdioma(evento.value);
    }
  }
}
