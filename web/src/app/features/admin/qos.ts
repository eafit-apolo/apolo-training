import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe, TranslocoService } from '@jsverse/transloco';
import { codigoDeError, estadoDeError } from '../../core/sesion/errores';
import { Comando } from '../../shared/comando';
import { confirmar } from '../../shared/confirmar';
import { Icono } from '../../shared/icono';
import { FormatoFecha } from '../progreso/formato';
import type { AprobadoPendienteApi } from './datos';
import { AdminApi, comandoQos } from './datos';
import { AdminEstado } from './estado';

/** Un aviso: clave de traducción y parámetros. */
interface Texto {
  readonly clave: string;
  readonly parametros?: Record<string, unknown>;
}

/**
 * Pestaña «Aprobados pendientes de QOS» (F-08): quienes terminaron todo
 * (lecciones, las siete prácticas y la graduación aprobada), de los más viejos
 * a los más nuevos. La plataforma no toca el clúster real: muestra el comando,
 * el admin lo corre allá y marca aquí «QOS aplicada» (V-08 define el nombre de
 * la QOS; mientras tanto, `QOS_NORMAL` es un marcador).
 */
@Component({
  selector: 'at-admin-qos',
  imports: [MatButtonModule, MatProgressBarModule, RouterLink, TranslocoPipe, Comando, Icono],
  template: `
    <p class="explicacion">{{ 'admin.qos.explicacion' | transloco }}</p>
    @if (aviso(); as a) {
      <p class="aviso" role="status">
        <at-icono nombre="info" />
        {{ a.clave | transloco: a.parametros }}
      </p>
    }
    @if (error(); as clave) {
      <p class="aviso aviso-error" role="alert">
        <at-icono nombre="error" />
        {{ clave | transloco }}
      </p>
    }

    @if (estado.pendientes(); as lista) {
      @if (estado.fallo()) {
        <p class="aviso aviso-error" role="alert">
          <at-icono nombre="error" />
          {{ 'panel.noActualizado' | transloco }}
        </p>
      }
      @if (!lista.length) {
        <p class="vacio">{{ 'admin.qos.vacia' | transloco }}</p>
      } @else {
        <ul class="aprobados">
          @for (a of lista; track a.username) {
            <li class="tarjeta aprobado">
              <div class="aprobado-cabecera">
                <h2>
                  <a class="enlace" [routerLink]="['/admin/usuarios', a.username]">{{
                    a.username
                  }}</a>
                  · {{ a.nombre }}
                </h2>
                <span>
                  {{
                    'admin.qos.datos'
                      | transloco
                        : {
                            cluster: ('cluster.' + a.cluster | transloco),
                            fecha: fecha(a.aprobado_en),
                          }
                  }}
                </span>
              </div>
              <p>
                {{
                  'admin.qos.correEn' | transloco: { cluster: ('cluster.' + a.cluster | transloco) }
                }}
              </p>
              <at-comando [texto]="comando(a)" />
              <div class="acciones">
                <button
                  mat-flat-button
                  type="button"
                  class="marcar"
                  [attr.aria-disabled]="marcando() === a.username || null"
                  [attr.aria-label]="'admin.qos.marcarA' | transloco: { username: a.username }"
                  (click)="marcar(a)"
                >
                  <at-icono nombre="hecho" />
                  {{ 'admin.qos.marcar' | transloco }}
                </button>
              </div>
            </li>
          }
        </ul>
      }
    } @else if (estado.fallo()) {
      <section class="error-carga" role="alert">
        <h2>{{ 'admin.errorCarga' | transloco }}</h2>
        <p>{{ 'errorCarga.mensaje' | transloco }}</p>
        <button mat-flat-button type="button" (click)="reintentar()">
          <at-icono nombre="reintentar" />
          {{ 'panel.reintentar' | transloco }}
        </button>
      </section>
    } @else {
      <mat-progress-bar mode="indeterminate" [attr.aria-label]="'admin.cargando' | transloco" />
    }
  `,
  styles: `
    .aprobados {
      display: grid;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .aprobado-cabecera {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 4px 16px;
      margin-bottom: 8px;

      h2 {
        margin: 0;
        font: var(--mat-sys-title-medium);
      }
    }

    .aprobado .acciones {
      justify-content: flex-end;
      margin-top: 12px;
    }

    .marcar.mat-mdc-unelevated-button:not(:disabled) {
      background: var(--at-verde);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QosAdmin {
  protected readonly estado = inject(AdminEstado);
  private readonly api = inject(AdminApi);
  private readonly dialogo = inject(MatDialog);
  private readonly formato = inject(FormatoFecha);
  private readonly transloco = inject(TranslocoService);

  protected readonly marcando = signal<string | null>(null);
  protected readonly aviso = signal<Texto | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    // Al volver a la pestaña, la lista otra vez (la cabecera la cargó al entrar).
    if (this.estado.pendientes() !== null) {
      void this.estado.cargarPendientes();
    }
  }

  protected comando(aprobado: AprobadoPendienteApi): string {
    return comandoQos(aprobado.username);
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  protected reintentar(): void {
    void this.estado.cargarPendientes();
  }

  protected async marcar(aprobado: AprobadoPendienteApi): Promise<void> {
    if (this.marcando()) {
      return;
    }
    this.aviso.set(null);
    this.error.set(null);
    const cluster = this.transloco.translate(`cluster.${aprobado.cluster}`);
    const seguro = await confirmar(this.dialogo, {
      titulo: 'admin.qos.preguntaTitulo',
      mensaje: 'admin.qos.pregunta',
      confirmar: 'admin.qos.confirmar',
      parametros: { username: aprobado.username, cluster },
    });
    if (!seguro) {
      return;
    }
    this.marcando.set(aprobado.username);
    try {
      await this.api.marcarQos(aprobado.username);
      this.aviso.set({ clave: 'admin.qos.hecha', parametros: { username: aprobado.username } });
    } catch (error) {
      const codigo = codigoDeError(error);
      this.error.set(
        codigo === 'qos_ya_aplicada'
          ? 'admin.qos.yaAplicada'
          : codigo === 'no_aprobado' || codigo === 'no_encontrado'
            ? 'admin.qos.noAprobado'
            : estadoDeError(error) === 0
              ? 'errores.sin_conexion'
              : 'errores.inesperado',
      );
    } finally {
      this.marcando.set(null);
      await this.estado.cargarPendientes();
    }
  }
}
