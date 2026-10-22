import { Injectable, computed, inject } from '@angular/core';
import { SesionService } from '../../../core/sesion/sesion';
import { armarCurso } from './armar';
import type { Curso, Leccion, Modulo } from './curso';
import { CURSOS_EJEMPLO, PROGRESO_EJEMPLO } from './datos-ejemplo';

/**
 * Cursos con el avance del usuario actual. Hoy salen de los datos de ejemplo;
 * con la B-04 vendrán de `GET /api/cursos` y `GET /api/modulos/{id}`, sin
 * cambiar lo que reciben las pantallas.
 */
@Injectable({ providedIn: 'root' })
export class CatalogoService {
  private readonly sesion = inject(SesionService);

  readonly cursos = computed<readonly Curso[]>(() => {
    const usuario = this.sesion.usuario();
    const completas = new Set(usuario ? (PROGRESO_EJEMPLO[usuario.username] ?? []) : []);
    return CURSOS_EJEMPLO.map((c) => armarCurso(c, completas));
  });

  curso(id: string | undefined): Curso | undefined {
    return this.cursos().find((c) => c.id === id);
  }

  modulo(curso: Curso | undefined, id: string | undefined): Modulo | undefined {
    return curso?.modulos.find((m) => m.id === id);
  }

  leccion(modulo: Modulo | undefined, slug: string | undefined): Leccion | undefined {
    return modulo?.lecciones.find((l) => l.slug === slug);
  }
}
