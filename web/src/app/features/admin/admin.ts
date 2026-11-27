import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  computed,
  inject,
} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Pestana } from '../../shared/pestanas';
import { Pestanas } from '../../shared/pestanas';
import { AdminEstado } from './estado';

/**
 * Pantalla 06 (F-08): la administración, aparte del panel de instructor y solo
 * para admins (la API lo refuerza: `/api/admin` da 403 a un instructor). Dos
 * pestañas: usuarios (con la página de cada uno) y aprobados pendientes de QOS.
 */
@Component({
  selector: 'at-admin',
  imports: [RouterOutlet, TranslocoPipe, Pestanas],
  providers: [AdminEstado],
  template: `
    <div class="at-contenedor at-admin">
      <div class="cabecera">
        <h1>{{ 'nav.admin' | transloco }}</h1>
      </div>
      <p class="explicacion">{{ 'admin.explicacion' | transloco }}</p>
      <at-pestanas [pestanas]="pestanas()" etiqueta="admin.pestanas" />
      <router-outlet />
    </div>
  `,
  styleUrl: './admin.scss',
  // Sin encapsulación: los estilos comunes llegan a las pestañas (todo va bajo .at-admin).
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Administracion {
  private readonly estado = inject(AdminEstado);

  protected readonly pestanas = computed<readonly Pestana[]>(() => [
    { ruta: '/admin/usuarios', clave: 'paginas.usuarios' },
    {
      ruta: '/admin/qos',
      clave: 'paginas.qos',
      cuenta: this.estado.pendientes()?.length ?? null,
      cuentaClave: 'admin.qos.esperando',
    },
  ]);

  constructor() {
    void this.estado.cargarPendientes();
  }
}
