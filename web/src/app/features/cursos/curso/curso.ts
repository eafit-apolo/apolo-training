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
import { EstadoModulo } from './estado-modulo';
import { TarjetaModulo } from './tarjeta-modulo';

/** Pantalla 02 (abajo): el curso, su avance y la grilla de módulos. */
@Component({
  selector: 'at-curso',
  imports: [
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
    Migas,
    PaginaPendiente,
    EstadoModulo,
    TarjetaModulo,
  ],
  templateUrl: './curso.html',
  styleUrl: './curso.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Curso {
  /** `:curso` de la ruta. */
  readonly curso = input<string>();

  private readonly catalogo = inject(CatalogoService);
  protected readonly datos = computed(() => this.catalogo.curso(this.curso()));
  protected readonly fallo = this.catalogo.error;
  protected readonly plural = plural;

  protected readonly migas = computed<readonly Miga[]>(() => [
    { clave: 'nav.cursos', ruta: ['/cursos'] },
    { texto: this.datos()?.titulo },
  ]);

  protected readonly rutaContinuar = computed(() => {
    const curso = this.datos();
    return curso?.continuar ? rutaLeccion(curso.id, curso.continuar) : null;
  });
}
