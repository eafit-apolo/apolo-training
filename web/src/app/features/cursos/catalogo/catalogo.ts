import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { SesionService } from '../../../core/sesion/sesion';
import { Icono } from '../../../shared/icono';
import { plural } from '../../../shared/plural';
import { rutaLeccion } from '../datos/armar';
import { CatalogoService } from '../datos/catalogo';

/** Pantalla 02 (arriba): saludo, perfil, «Continuar» y la lista de cursos. */
@Component({
  selector: 'at-catalogo',
  imports: [
    NgOptimizedImage,
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
  ],
  templateUrl: './catalogo.html',
  styleUrl: './catalogo.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Catalogo {
  protected readonly usuario = inject(SesionService).usuario;
  protected readonly cursos = inject(CatalogoService).cursos;
  protected readonly plural = plural;

  /** El curso para «Continuar»: el primero sin terminar, o el primero si todos terminaron. */
  protected readonly actual = computed(() => {
    const cursos = this.cursos();
    return cursos.find((c) => c.continuar) ?? cursos[0];
  });

  protected readonly moduloContinuar = computed(() => {
    const curso = this.actual();
    return curso?.modulos.find((m) => m.id === curso.continuar?.modulo);
  });

  protected readonly rutaContinuar = computed(() => {
    const curso = this.actual();
    return curso?.continuar ? rutaLeccion(curso.id, curso.continuar) : null;
  });
}
