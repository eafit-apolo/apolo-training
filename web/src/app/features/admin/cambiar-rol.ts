import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { TranslocoPipe } from '@jsverse/transloco';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import type { Rol } from '../../core/sesion/sesion';
import type { UsuarioAdminApi } from './datos';
import { AdminApi, ROLES } from './datos';

export interface DatosCambiarRol {
  readonly username: string;
  readonly nombre: string;
  readonly rol: Rol;
  /** El admin cambia su propio rol: pierde la administración si deja de ser admin. */
  readonly propio: boolean;
}

/**
 * «Cambiar rol» (B-08): radios nativos (sin `@angular/forms`) y
 * `PATCH /api/admin/usuarios/{username}`. Se cierra con el usuario actualizado;
 * un 409 `ultimo_admin` se explica aquí mismo.
 */
@Component({
  selector: 'at-cambiar-rol',
  imports: [MatDialogModule, MatButtonModule, TranslocoPipe],
  template: `
    <h2 mat-dialog-title>
      {{ 'admin.rol.titulo' | transloco: { username: datos.username } }}
    </h2>
    <mat-dialog-content>
      <fieldset class="at-roles">
        <legend>{{ 'admin.rol.leyenda' | transloco: { nombre: datos.nombre } }}</legend>
        @for (r of roles; track r) {
          <label>
            <input
              type="radio"
              name="rol"
              [value]="r"
              [checked]="r === elegido()"
              (change)="elegir(r)"
            />
            <span>
              <strong>{{ 'admin.roles.' + r | transloco }}</strong>
              <span class="at-rol-texto">{{ 'admin.rol.que.' + r | transloco }}</span>
            </span>
          </label>
        }
      </fieldset>
      @if (datos.propio && elegido() !== 'admin') {
        <p class="at-rol-aviso">{{ 'admin.rol.propio' | transloco }}</p>
      }
      @if (error(); as clave) {
        <p class="at-rol-error" role="alert">{{ clave | transloco }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>
        {{ 'confirmar.cancelar' | transloco }}
      </button>
      <button
        mat-flat-button
        type="button"
        [attr.aria-disabled]="guardando() || null"
        (click)="guardar()"
      >
        {{ (guardando() ? 'admin.rol.guardando' : 'admin.rol.guardar') | transloco }}
      </button>
    </mat-dialog-actions>
  `,
  styles: `
    .at-roles {
      display: grid;
      gap: 8px;
      margin: 0;
      padding: 0;
      border: 0;

      legend {
        margin-bottom: 8px;
      }

      label {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        min-height: 44px;
        padding: 8px;
        border-radius: 8px;
        cursor: pointer;
      }

      label:hover {
        background: var(--mat-sys-surface-container);
      }

      input {
        width: 20px;
        height: 20px;
        margin: 2px 0 0;
        accent-color: var(--mat-sys-primary);
      }
    }

    .at-rol-texto {
      display: block;
      color: var(--mat-sys-on-surface-variant);
    }

    .at-rol-aviso,
    .at-rol-error {
      padding: 8px 12px;
      border-left: 4px solid var(--mat-sys-tertiary);
      background: var(--mat-sys-surface-container);
    }

    .at-rol-error {
      border-left-color: var(--mat-sys-error);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CambiarRolDialogo {
  protected readonly datos = inject<DatosCambiarRol>(MAT_DIALOG_DATA);
  private readonly ref = inject<MatDialogRef<CambiarRolDialogo, UsuarioAdminApi>>(MatDialogRef);
  private readonly api = inject(AdminApi);

  protected readonly roles = ROLES;
  protected readonly elegido = signal<Rol>(this.datos.rol);
  protected readonly guardando = signal(false);
  protected readonly error = signal<string | null>(null);

  protected elegir(rol: Rol): void {
    this.elegido.set(rol);
    this.error.set(null);
  }

  protected async guardar(): Promise<void> {
    if (this.guardando()) {
      return;
    }
    if (this.elegido() === this.datos.rol) {
      this.ref.close();
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    try {
      this.ref.close(await this.api.cambiarRol(this.datos.username, this.elegido()));
    } catch (error) {
      const codigo = codigoDeError(error);
      this.error.set(
        codigo === 'ultimo_admin'
          ? 'admin.rol.ultimoAdmin'
          : codigo === 'no_encontrado'
            ? 'admin.noExiste'
            : estadoDeError(error) === 0
              ? 'errores.sin_conexion'
              : 'errores.inesperado',
      );
    } finally {
      this.guardando.set(false);
    }
  }
}
