import { DOCUMENT } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  signal,
  untracked,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../core/i18n/idioma';
import type { Cluster } from '../../core/sesion/sesion';
import { SesionService } from '../../core/sesion/sesion';
import { Icono } from '../../shared/icono';
import type { Pestana } from '../../shared/pestanas';
import { Pestanas } from '../../shared/pestanas';
import { urlCsv } from './datos';
import { PanelEstado } from './estado';

/**
 * Pantalla 05 (F-08): la cabecera del panel de instructor, con las pestañas
 * (Resumen, Graduaciones y Videos, cada una su ruta) y «Exportar CSV», que
 * baja el progreso de los estudiantes para la medición (B-08).
 *
 * Carga el resumen al entrar y al cambiar el idioma (los títulos de los
 * módulos vienen traducidos); lo comparten la cuenta de «Graduaciones» y la
 * pestaña «Resumen».
 */
@Component({
  selector: 'at-panel',
  imports: [MatButtonModule, RouterOutlet, TranslocoPipe, Icono, Pestanas],
  providers: [PanelEstado],
  templateUrl: './panel.html',
  styleUrl: './panel.scss',
  // Sin encapsulación: los estilos comunes llegan a las pestañas (todo va bajo .at-panel).
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Panel {
  private readonly estado = inject(PanelEstado);
  private readonly idioma = inject(IdiomaService).actual;
  private readonly sesion = inject(SesionService);
  private readonly documento = inject(DOCUMENT);

  protected readonly cluster = signal<Cluster | null>(null);
  protected readonly falloCsv = signal(false);

  protected readonly pestanas = computed<readonly Pestana[]>(() => [
    { ruta: '/panel', clave: 'panel.resumen.titulo', exacta: true },
    {
      ruta: '/panel/graduaciones',
      clave: 'paginas.graduaciones',
      cuenta: this.estado.resumen()?.graduaciones_por_revisar ?? null,
      cuentaClave: 'panel.porRevisar',
    },
    { ruta: '/panel/videos', clave: 'paginas.videos' },
  ]);

  constructor() {
    effect(() => {
      const idioma = this.idioma();
      untracked(() => void this.estado.cargar(idioma));
    });
  }

  protected elegirCluster(valor: string): void {
    this.cluster.set(valor === 'apolo2' || valor === 'apolo3' ? valor : null);
  }

  /**
   * Baja el CSV con un enlace temporal (la cookie de sesión va sola). Antes
   * comprueba la sesión: con `at` vencido, la descarga sería un 401 en JSON.
   */
  protected async exportar(): Promise<void> {
    this.falloCsv.set(false);
    try {
      await this.sesion.comprobar();
    } catch {
      this.falloCsv.set(true);
      return;
    }
    const enlace = this.documento.createElement('a');
    enlace.href = urlCsv(this.cluster());
    enlace.download = '';
    enlace.click();
  }
}
