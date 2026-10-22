import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import type { Miga } from '../../../shared/migas';
import { Migas } from '../../../shared/migas';
import { PaginaPendiente } from '../../../shared/pagina-pendiente';
import { plural } from '../../../shared/plural';
import { rutaLeccion } from '../datos/armar';
import { CatalogoService } from '../datos/catalogo';
import { Bloqueado } from './bloqueado';

/** Página de un módulo: resumen, avance y sus lecciones. */
@Component({
  selector: 'at-modulo',
  imports: [
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
    Migas,
    PaginaPendiente,
    Bloqueado,
  ],
  templateUrl: './modulo.html',
  styleUrl: './modulo.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modulo {
  /** `:curso` y `:modulo` de la ruta. */
  readonly curso = input<string>();
  readonly modulo = input<string>();

  private readonly catalogo = inject(CatalogoService);
  protected readonly datosCurso = computed(() => this.catalogo.curso(this.curso()));
  protected readonly datos = computed(() => this.catalogo.modulo(this.datosCurso(), this.modulo()));
  protected readonly plural = plural;

  protected readonly migas = computed<readonly Miga[]>(() => {
    const curso = this.datosCurso();
    const modulo = this.datos();
    return [
      { clave: 'nav.cursos', ruta: ['/cursos'] },
      { texto: curso?.titulo, ruta: ['/cursos', curso?.id ?? ''] },
      { texto: `${modulo?.numero} · ${modulo?.titulo}` },
    ];
  });

  /** Primera lección sin completar; si todas lo están, la primera (para repasar). */
  protected readonly siguiente = computed(() => {
    const curso = this.datosCurso();
    const modulo = this.datos();
    if (!curso || !modulo || modulo.estado === 'bloqueado') {
      return null;
    }
    const leccion = modulo.lecciones.find((l) => !l.completa) ?? modulo.lecciones[0];
    return leccion ? rutaLeccion(curso.id, leccion) : null;
  });
}
