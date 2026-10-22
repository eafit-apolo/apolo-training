import { Injectable, computed, signal } from '@angular/core';

export type Cluster = 'apolo2' | 'apolo3';
export type Rol = 'estudiante' | 'instructor' | 'admin';

export interface Usuario {
  readonly username: string;
  readonly nombre: string;
  readonly cluster: Cluster;
  readonly rol: Rol;
}

/**
 * Los mismos usuarios de ejemplo de la API (`api/app/datos_ejemplo.py`), sin
 * `elena`, que está dada de baja. Sirven para probar la navegación por rol y
 * por avance mientras no hay sesión.
 */
export const USUARIOS_EJEMPLO: readonly Usuario[] = [
  { username: 'ana', nombre: 'Ana', cluster: 'apolo2', rol: 'estudiante' },
  { username: 'bruno', nombre: 'Bruno', cluster: 'apolo3', rol: 'estudiante' },
  { username: 'carla', nombre: 'Carla', cluster: 'apolo2', rol: 'instructor' },
  { username: 'diego', nombre: 'Diego', cluster: 'apolo3', rol: 'admin' },
];

/**
 * Usuario actual. Mientras no exista la sesión (B-03 y F-03) es uno de los
 * usuarios de ejemplo y se cambia con «Probar como» en el menú de usuario; la
 * F-03 lo llenará con `GET /api/me` y quitará `probarComo()`.
 */
@Injectable({ providedIn: 'root' })
export class SesionService {
  private readonly actual = signal<Usuario | null>(USUARIOS_EJEMPLO[0]);

  readonly usuario = this.actual.asReadonly();
  readonly rol = computed(() => this.actual()?.rol ?? null);

  probarComo(username: string): void {
    const usuario = USUARIOS_EJEMPLO.find((u) => u.username === username);
    if (usuario) {
      this.actual.set(usuario);
    }
  }
}
