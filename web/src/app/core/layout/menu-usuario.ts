import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { Router, RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../shared/icono';
import { SesionService, USUARIOS_EJEMPLO } from '../sesion/sesion';

/**
 * Menú de usuario del encabezado: nombre y perfil del clúster, Mi progreso,
 * cambiar la contraseña y cerrar la sesión. «Probar como» cambia el usuario de
 * ejemplo mientras no hay sesión (se quita en la F-03).
 */
@Component({
  selector: 'at-menu-usuario',
  imports: [MatButtonModule, MatMenuModule, RouterLink, TranslocoPipe, Icono],
  template: `
    @if (sesion.usuario(); as usuario) {
      <button type="button" mat-button class="disparador" [matMenuTriggerFor]="menu">
        <span class="avatar" aria-hidden="true">{{ usuario.nombre.charAt(0) }}</span>
        <span class="nombre"
          >{{ usuario.nombre }} · {{ 'cluster.' + usuario.cluster | transloco }}</span
        >
        <at-icono nombre="desplegar" />
      </button>

      <mat-menu #menu="matMenu" xPosition="before">
        <a mat-menu-item routerLink="/mi-progreso">{{ 'nav.miProgreso' | transloco }}</a>
        <a mat-menu-item routerLink="/cambiar-clave">
          <at-icono nombre="clave" />
          {{ 'usuario.cambiarClave' | transloco }}
        </a>
        <button mat-menu-item type="button" (click)="salir()">
          <at-icono nombre="salir" />
          {{ 'usuario.salir' | transloco }}
        </button>
        <div role="separator" class="separador"></div>
        <div role="group" [attr.aria-label]="'usuario.probarComo' | transloco">
          <p class="grupo" aria-hidden="true">{{ 'usuario.probarComo' | transloco }}</p>
          @for (ejemplo of ejemplos; track ejemplo.username) {
            <button
              mat-menu-item
              type="button"
              role="menuitemradio"
              [attr.aria-checked]="ejemplo.username === usuario.username"
              (click)="sesion.probarComo(ejemplo.username)"
            >
              <at-icono
                [nombre]="ejemplo.username === usuario.username ? 'completo' : 'pendiente'"
              />
              {{ ejemplo.nombre }} · {{ 'rol.' + ejemplo.rol | transloco }} ·
              {{ 'cluster.' + ejemplo.cluster | transloco }}
            </button>
          }
        </div>
      </mat-menu>
    }
  `,
  styles: `
    .disparador at-icono {
      margin: 0 0 0 4px;
    }

    .avatar {
      display: inline-grid;
      place-items: center;
      width: 32px;
      height: 32px;
      margin-right: 8px;
      border-radius: 50%;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
      font-weight: 600;
    }

    @media (max-width: 839.98px) {
      .nombre {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        clip-path: inset(50%);
        white-space: nowrap;
      }

      .avatar {
        margin-right: 0;
      }
    }

    .separador {
      margin: 8px 0;
      border-top: 1px solid var(--mat-sys-outline-variant);
    }

    .grupo {
      margin: 0;
      padding: 4px 16px;
      color: var(--mat-sys-on-surface-variant);
      font: var(--mat-sys-label-medium);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MenuUsuario {
  protected readonly sesion = inject(SesionService);
  private readonly router = inject(Router);
  protected readonly ejemplos = USUARIOS_EJEMPLO;

  /** Sin sesión todavía: solo lleva a la pantalla de ingreso (la F-03 la cierra de verdad). */
  protected salir(): void {
    void this.router.navigateByUrl('/ingresar');
  }
}
