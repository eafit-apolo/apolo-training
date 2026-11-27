import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import type { MatDialog } from '@angular/material/dialog';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { TranslocoPipe } from '@jsverse/transloco';
import { firstValueFrom } from 'rxjs';

/** Claves de traducción (y sus parámetros) del diálogo. */
export interface DatosConfirmar {
  readonly titulo: string;
  readonly mensaje: string;
  /** El texto del botón que confirma («Reemplazar», «Reiniciar la clave»…). */
  readonly confirmar: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * Pregunta antes de una acción que no se deshace (F-08): reemplazar un video,
 * reiniciar una clave, marcar la QOS. El foco empieza en «Cancelar», así un
 * Enter de más no confirma; Esc también cancela.
 */
@Component({
  selector: 'at-confirmar',
  imports: [MatDialogModule, MatButtonModule, TranslocoPipe],
  template: `
    <h2 mat-dialog-title>{{ datos.titulo | transloco: datos.parametros }}</h2>
    <mat-dialog-content>
      <p>{{ datos.mensaje | transloco: datos.parametros }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" [mat-dialog-close]="false">
        {{ 'confirmar.cancelar' | transloco }}
      </button>
      <button mat-flat-button type="button" [mat-dialog-close]="true">
        {{ datos.confirmar | transloco: datos.parametros }}
      </button>
    </mat-dialog-actions>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Confirmar {
  protected readonly datos = inject<DatosConfirmar>(MAT_DIALOG_DATA);
}

/** Abre el diálogo y devuelve `true` solo si la persona confirmó. */
export async function confirmar(dialogo: MatDialog, datos: DatosConfirmar): Promise<boolean> {
  const ref = dialogo.open<Confirmar, DatosConfirmar, boolean>(Confirmar, {
    data: datos,
    width: '28rem',
    maxWidth: 'calc(100vw - 32px)',
  });
  return (await firstValueFrom(ref.afterClosed())) === true;
}
