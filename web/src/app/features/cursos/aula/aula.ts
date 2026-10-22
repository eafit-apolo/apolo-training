import { BreakpointObserver } from '@angular/cdk/layout';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import type { MatSidenav } from '@angular/material/sidenav';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { map } from 'rxjs';
import { Icono } from '../../../shared/icono';
import { PaginaPendiente } from '../../../shared/pagina-pendiente';
import { CatalogoService } from '../datos/catalogo';
import { BarraLateral } from './barra-lateral';

const ESCRITORIO = '(min-width: 1024px)';
const TABLETA = '(min-width: 600px)';
/** Alto del encabezado (shell.scss): mat-toolbar de 64 px (56 en celular) + 3 px de borde. */
const ALTO_ENCABEZADO = { tableta: 67, celular: 59 };

/**
 * Marco de las pantallas de módulo y lección: barra lateral fija en
 * escritorio y, en tableta y celular, un panel «Módulos» que se abre con un
 * botón (atrapa el foco, se cierra con Esc y devuelve el foco al botón).
 */
@Component({
  selector: 'at-aula',
  imports: [
    MatButtonModule,
    MatSidenavModule,
    RouterOutlet,
    TranslocoPipe,
    Icono,
    PaginaPendiente,
    BarraLateral,
  ],
  template: `
    @if (datos(); as curso) {
      <mat-sidenav-container class="aula">
        <mat-sidenav
          #lateral
          class="lateral"
          [mode]="escritorio() ? 'side' : 'over'"
          [opened]="escritorio()"
          [fixedInViewport]="true"
          [fixedTopGap]="altoEncabezado()"
        >
          @if (!escritorio()) {
            <div class="cerrar">
              <button
                type="button"
                mat-icon-button
                [attr.aria-label]="'aula.cerrar' | transloco"
                (click)="lateral.close()"
              >
                <at-icono nombre="cerrar" />
              </button>
            </div>
          }
          <at-barra-lateral [curso]="curso" [abierto]="modulo()" (navego)="cerrarEnCelular()" />
        </mat-sidenav>

        <mat-sidenav-content class="contenido">
          @if (!escritorio()) {
            <button type="button" mat-stroked-button class="abrir" (click)="lateral.open()">
              <at-icono nombre="modulos" />
              {{ 'aula.abrir' | transloco: { n: curso.avance } }}
            </button>
          }
          <router-outlet />
        </mat-sidenav-content>
      </mat-sidenav-container>
    } @else {
      <at-pagina-pendiente titulo="paginas.noEncontrada" mensaje="noEncontrada.mensaje" />
    }
  `,
  styles: `
    .aula {
      min-height: calc(100dvh - 67px);
      background: transparent;
    }

    .lateral {
      width: 300px;
      max-width: 85vw;
      border-right: 1px solid var(--mat-sys-outline-variant);
      border-radius: 0;
      background: var(--mat-sys-surface-container-low);
    }

    .cerrar {
      display: flex;
      justify-content: flex-end;
      padding: 8px 8px 0;
    }

    .contenido {
      box-sizing: border-box;
      max-width: 960px;
      padding: 24px 32px 48px;
    }

    .abrir {
      margin-bottom: 16px;
    }

    @media (max-width: 599.98px) {
      .contenido {
        padding: 16px 16px 48px;
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Aula {
  /** `:curso` y `:modulo` de la ruta. */
  readonly curso = input<string>();
  readonly modulo = input<string>();

  private readonly catalogo = inject(CatalogoService);
  private readonly lateral = viewChild<MatSidenav>('lateral');
  protected readonly datos = computed(() => this.catalogo.curso(this.curso()));

  private readonly pantalla = inject(BreakpointObserver);
  protected readonly escritorio = this.coincide(ESCRITORIO);
  private readonly tableta = this.coincide(TABLETA);
  protected readonly altoEncabezado = computed(() =>
    this.tableta() ? ALTO_ENCABEZADO.tableta : ALTO_ENCABEZADO.celular,
  );

  protected cerrarEnCelular(): void {
    if (!this.escritorio()) {
      void this.lateral()?.close();
    }
  }

  private coincide(consulta: string) {
    return toSignal(this.pantalla.observe(consulta).pipe(map((r) => r.matches)), {
      initialValue: this.pantalla.isMatched(consulta),
    });
  }
}
