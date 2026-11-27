import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { TranslocoPipe } from '@jsverse/transloco';
import { Comando } from '../../shared/comando';
import type { ClaveTemporalApi } from './datos';

/**
 * La clave temporal tras «Reiniciar clave de la plataforma» (B-08): se ve una
 * sola vez (la base solo guarda su hash). Recuerda que la de la VM no cambia.
 */
@Component({
  selector: 'at-clave-temporal',
  imports: [MatDialogModule, MatButtonModule, TranslocoPipe, Comando],
  template: `
    <h2 mat-dialog-title>
      {{ 'admin.clave.titulo' | transloco: { username: datos.username } }}
    </h2>
    <mat-dialog-content>
      <at-comando
        class="at-clave"
        [texto]="datos.clave_temporal"
        [etiqueta]="'admin.clave.etiqueta' | transloco"
      />
      <p>{{ 'admin.clave.unaVez' | transloco: { username: datos.username } }}</p>
      <p>{{ 'admin.clave.vm' | transloco }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-flat-button type="button" mat-dialog-close>
        {{ 'admin.clave.listo' | transloco }}
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .at-clave {
      margin: 0 0 16px;
      font-size: 1.15rem;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClaveTemporalDialogo {
  protected readonly datos = inject<ClaveTemporalApi>(MAT_DIALOG_DATA);
}
