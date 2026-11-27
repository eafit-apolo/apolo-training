import { Injectable, inject, signal } from '@angular/core';
import type { Idioma } from '../../core/i18n/idioma';
import type { ResumenPanelApi } from './datos';
import { PanelApi } from './datos';

/**
 * El resumen del panel, compartido por la cabecera (la cuenta de «Graduaciones»)
 * y la pestaña «Resumen». Lo provee `at-panel`: nace y muere con el panel, así
 * que cada visita empieza con datos nuevos.
 */
@Injectable()
export class PanelEstado {
  private readonly api = inject(PanelApi);

  readonly resumen = signal<ResumenPanelApi | null>(null);
  readonly fallo = signal(false);
  /** Para descartar la respuesta de un pedido viejo (otro idioma, doble recarga). */
  private pedido = 0;

  async cargar(idioma: Idioma): Promise<boolean> {
    const pedido = ++this.pedido;
    try {
      const resumen = await this.api.resumen(idioma);
      if (pedido !== this.pedido) {
        return false;
      }
      this.resumen.set(resumen);
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
