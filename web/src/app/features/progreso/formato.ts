import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { IdiomaService } from '../../core/i18n/idioma';
import { regionDe } from '../cuenta/hora';
import { haceCuanto } from './datos';

/**
 * Fechas de Mi progreso en la hora local y el formato regional del idioma de
 * la interfaz (el del navegador si es del mismo idioma: `es-CO`, `en-US`…).
 */
@Injectable({ providedIn: 'root' })
export class FormatoFecha {
  private readonly idioma = inject(IdiomaService).actual;
  private readonly documento = inject(DOCUMENT);

  /** Día y hora, cortos: «23 nov, 10:05 a. m.». */
  fecha(iso: string): string {
    return this.formato(iso, {
      day: 'numeric',
      month: 'short',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  /** Solo la hora si es del mismo día que `ahora`; si no, también el día. */
  hora(iso: string, ahora: number): string {
    const hoy = new Date(iso).toDateString() === new Date(ahora).toDateString();
    return hoy ? this.formato(iso, { hour: 'numeric', minute: '2-digit' }) : this.fecha(iso);
  }

  /** «hace 3 minutos», «hace 2 horas», «3 minutes ago»… */
  hace(iso: string, ahora: number): string {
    const { valor, unidad } = haceCuanto(iso, ahora);
    try {
      return new Intl.RelativeTimeFormat(this.region(), { numeric: 'auto' }).format(valor, unidad);
    } catch {
      return new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(valor, unidad);
    }
  }

  private formato(iso: string, opciones: Intl.DateTimeFormatOptions): string {
    try {
      return new Intl.DateTimeFormat(this.region(), opciones).format(new Date(iso));
    } catch {
      // Una región que Intl no conoce: el formato por defecto del navegador.
      return new Intl.DateTimeFormat(undefined, opciones).format(new Date(iso));
    }
  }

  private region(): string {
    return regionDe(this.idioma(), this.documento.defaultView?.navigator.languages ?? []);
  }
}
