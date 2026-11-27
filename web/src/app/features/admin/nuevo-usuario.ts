import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Idioma } from '../../core/i18n/idioma';
import type { Cluster } from '../../core/sesion/sesion';
import { Comando } from '../../shared/comando';
import type { DatosAlta } from './datos';
import { CLUSTERES, CORREO_MAXIMO, NOMBRE_MAXIMO, faltasAlta, ordenAlta } from './datos';

/**
 * «Nuevo usuario» (pantalla 06, decisión del 27-nov): la web no crea cuentas.
 * Un formulario corto arma la orden exacta de `apolo-training-admin alta`, con
 * las comillas bien puestas, para correrla en la VM de práctica: así la cuenta
 * existe en la VM y en la plataforma, o en ninguna.
 */
@Component({
  selector: 'at-nuevo-usuario',
  imports: [MatDialogModule, MatButtonModule, TranslocoPipe, Comando],
  template: `
    <h2 mat-dialog-title>{{ 'admin.nuevo.titulo' | transloco }}</h2>
    <mat-dialog-content>
      <p>{{ 'admin.nuevo.explicacion' | transloco }}</p>
      <div class="at-alta">
        <label class="at-alta-campo">
          {{ 'admin.nuevo.usuario' | transloco }}
          <input
            #usuario
            type="text"
            autocomplete="off"
            spellcheck="false"
            autocapitalize="none"
            maxlength="32"
            [value]="datos().usuario"
            [attr.aria-invalid]="error('usuarioInvalido') || null"
            aria-describedby="alta-usuario-ayuda"
            (input)="cambiar('usuario', usuario.value)"
          />
          <span
            id="alta-usuario-ayuda"
            class="at-alta-ayuda"
            [class.at-alta-mal]="error('usuarioInvalido')"
          >
            {{ 'admin.nuevo.usuarioAyuda' | transloco }}
          </span>
        </label>
        <label class="at-alta-campo">
          {{ 'admin.nuevo.nombre' | transloco }}
          <input
            #nombre
            type="text"
            autocomplete="off"
            [attr.maxlength]="nombreMaximo"
            [value]="datos().nombre"
            [attr.aria-invalid]="error('nombreInvalido') || null"
            aria-describedby="alta-nombre-ayuda"
            (input)="cambiar('nombre', nombre.value)"
          />
          <span
            id="alta-nombre-ayuda"
            class="at-alta-ayuda"
            [class.at-alta-mal]="error('nombreInvalido')"
          >
            {{ 'admin.nuevo.nombreAyuda' | transloco }}
          </span>
        </label>
        <label class="at-alta-campo">
          {{ 'admin.nuevo.correo' | transloco }}
          <input
            #correo
            type="email"
            autocomplete="off"
            spellcheck="false"
            [attr.maxlength]="correoMaximo"
            [value]="datos().correo"
            [attr.aria-invalid]="correoMal() || null"
            [attr.aria-describedby]="correoMal() ? 'alta-correo-error' : null"
            (input)="cambiar('correo', correo.value)"
            (blur)="correoTocado.set(true)"
          />
          @if (correoMal()) {
            <span id="alta-correo-error" class="at-alta-ayuda at-alta-mal">
              {{ 'admin.nuevo.correoInvalido' | transloco }}
            </span>
          }
        </label>
        <fieldset class="at-alta-opciones">
          <legend>{{ 'admin.nuevo.cluster' | transloco }}</legend>
          @for (c of clusteres; track c) {
            <label>
              <input
                type="radio"
                name="alta-cluster"
                [value]="c"
                [checked]="c === datos().cluster"
                (change)="cambiar('cluster', c)"
              />
              {{ 'cluster.' + c | transloco }}
            </label>
          }
        </fieldset>
        <fieldset class="at-alta-opciones">
          <legend>{{ 'admin.nuevo.idioma' | transloco }}</legend>
          @for (i of idiomas; track i) {
            <label>
              <input
                type="radio"
                name="alta-idioma"
                [value]="i"
                [checked]="i === datos().idioma"
                (change)="cambiar('idioma', i)"
              />
              {{ 'idioma.' + i | transloco }}
            </label>
          }
        </fieldset>
      </div>

      <h3 class="at-alta-orden">{{ 'admin.nuevo.orden' | transloco }}</h3>
      @if (orden(); as texto) {
        <at-comando [texto]="texto" />
        <p class="at-alta-ayuda">{{ 'admin.nuevo.despues' | transloco }}</p>
      } @else {
        <p class="at-alta-ayuda" aria-live="polite">{{ 'admin.nuevo.completa' | transloco }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>
        {{ 'admin.nuevo.cerrar' | transloco }}
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .at-alta {
      display: grid;
      gap: 12px;
    }

    .at-alta-campo {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font: var(--mat-sys-label-large);

      input {
        min-height: 44px;
        padding: 8px 12px;
        border: 1px solid var(--mat-sys-outline);
        border-radius: 4px;
        background: var(--mat-sys-surface);
        color: var(--mat-sys-on-surface);
        font: var(--mat-sys-body-large);
      }

      input:focus-visible {
        outline: 3px solid var(--mat-sys-primary);
        outline-offset: 1px;
      }

      input[aria-invalid='true'] {
        border: 2px solid var(--mat-sys-error);
      }
    }

    .at-alta-ayuda {
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-body-medium);
    }

    .at-alta-mal {
      color: var(--mat-sys-error);
    }

    .at-alta-opciones {
      display: flex;
      flex-wrap: wrap;
      gap: 4px 16px;
      margin: 0;
      padding: 0;
      border: 0;

      legend {
        margin-bottom: 4px;
        font: var(--mat-sys-label-large);
      }

      label {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        min-height: 44px;
      }

      input {
        width: 20px;
        height: 20px;
        margin: 0;
        accent-color: var(--mat-sys-primary);
      }
    }

    .at-alta-orden {
      margin: 20px 0 8px;
      font: var(--mat-sys-title-medium);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NuevoUsuarioDialogo {
  protected readonly clusteres = CLUSTERES;
  protected readonly idiomas: readonly Idioma[] = ['es', 'en'];
  protected readonly nombreMaximo = NOMBRE_MAXIMO;
  protected readonly correoMaximo = CORREO_MAXIMO;

  protected readonly datos = signal<DatosAlta>({
    usuario: '',
    nombre: '',
    correo: '',
    cluster: 'apolo2',
    idioma: 'es',
  });
  private readonly faltas = computed(() => faltasAlta(this.datos()));
  /** La orden, solo cuando todo está bien (así no se copia una a medias). */
  protected readonly orden = computed(() =>
    this.faltas().length ? null : ordenAlta(this.datos()),
  );

  protected cambiar(campo: keyof DatosAlta, valor: string): void {
    this.datos.update((d) => ({ ...d, [campo]: valor as Cluster & Idioma }));
  }

  /** El correo se marca al salir del campo: mientras se escribe casi siempre está a medias. */
  protected readonly correoTocado = signal(false);
  protected readonly correoMal = computed(
    () => this.correoTocado() && this.faltas().includes('correoInvalido'),
  );

  /** Un error de formato (no «falta»): se marca mientras se escribe. */
  protected error(falta: 'usuarioInvalido' | 'nombreInvalido'): boolean {
    return this.faltas().includes(falta);
  }
}
