import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { filter, map } from 'rxjs';
import { Icono } from '../../shared/icono';
import { rutaInterna } from '../sesion/rutas';
import { SesionService } from '../sesion/sesion';

/**
 * Menú de usuario del encabezado: nombre y perfil del clúster, Mi progreso,
 * cambiar la contraseña (voluntario; decisión del 28-oct) y cerrar la sesión.
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
        <a mat-menu-item routerLink="/cambiar-clave" [queryParams]="{ volver: volver() }">
          <at-icono nombre="clave" />
          {{ 'usuario.cambiarClave' | transloco }}
        </a>
        <button mat-menu-item type="button" (click)="salir()">
          <at-icono nombre="salir" />
          {{ 'usuario.salir' | transloco }}
        </button>
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
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MenuUsuario {
  protected readonly sesion = inject(SesionService);
  private readonly router = inject(Router);

  /** Página actual, para que «Cancelar» en /cambiar-clave vuelva a ella. */
  protected readonly volver = toSignal(
    this.router.events.pipe(
      filter((e) => e instanceof NavigationEnd),
      map((e) => rutaInterna(e.urlAfterRedirects)),
    ),
    { initialValue: rutaInterna(this.router.url) },
  );

  protected salir(): void {
    void this.sesion.salir();
  }
}
