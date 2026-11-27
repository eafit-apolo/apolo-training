import { Injectable, inject, signal } from '@angular/core';
import type { AprobadoPendienteApi } from './datos';
import { AdminApi } from './datos';

/**
 * Los aprobados pendientes de QOS, compartidos por la cabecera (la cuenta de
 * la pestaña) y la pestaña misma. Lo provee `at-admin`: nace y muere con la
 * administración.
 */
@Injectable()
export class AdminEstado {
  private readonly api = inject(AdminApi);

  readonly pendientes = signal<readonly AprobadoPendienteApi[] | null>(null);
  readonly fallo = signal(false);
  private pedido = 0;

  async cargarPendientes(): Promise<boolean> {
    const pedido = ++this.pedido;
    try {
      const lista = await this.api.pendientes();
      if (pedido !== this.pedido) {
        return false;
      }
      this.pendientes.set(lista);
      this.fallo.set(false);
      return true;
    } catch {
      if (pedido === this.pedido) {
        this.fallo.set(true);
      }
      return false;
    }
  }
}
