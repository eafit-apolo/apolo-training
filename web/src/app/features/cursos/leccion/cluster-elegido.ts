import { Injectable, computed, inject, signal } from '@angular/core';
import type { Cluster } from '../../../core/sesion/sesion';
import { SesionService } from '../../../core/sesion/sesion';

/**
 * Qué pestaña Apolo II / Apolo III se ve. Todas las de una lección cambian
 * juntas; al abrir otra lección vuelve a la del perfil (`reiniciar()`). Sin
 * perfil (no debería pasar: todo usuario tiene clúster), Apolo II.
 */
@Injectable({ providedIn: 'root' })
export class ClusterElegido {
  private readonly sesion = inject(SesionService);
  private readonly elegido = signal<Cluster | null>(null);

  /** El clúster del usuario: su pestaña dice «(tu clúster)». */
  readonly propio = computed<Cluster | null>(() => this.sesion.usuario()?.cluster ?? null);
  readonly actual = computed<Cluster>(() => this.elegido() ?? this.propio() ?? 'apolo2');

  elegir(cluster: Cluster): void {
    this.elegido.set(cluster);
  }

  reiniciar(): void {
    this.elegido.set(null);
  }
}
