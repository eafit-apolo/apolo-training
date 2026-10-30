import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import { plural } from '../../../shared/plural';
import type { Curso } from '../datos/curso';
import { EstadoModulo } from '../curso/estado-modulo';

/**
 * Barra lateral del aula: avance del curso, todos los módulos con su estado y
 * su avance, y las lecciones del módulo abierto. Los bloqueados no son
 * enlaces (salvo para instructores y admins). La página actual lleva `aria-current="page"`.
 */
@Component({
  selector: 'at-barra-lateral',
  imports: [MatProgressBarModule, RouterLink, RouterLinkActive, TranslocoPipe, Icono, EstadoModulo],
  templateUrl: './barra-lateral.html',
  styleUrl: './barra-lateral.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BarraLateral {
  readonly curso = input.required<Curso>();
  /** Id del módulo abierto (`m05`): se despliegan sus lecciones. */
  readonly abierto = input<string>();
  /** Se eligió un enlace (en celular, el aula cierra el panel). */
  readonly navego = output();
  protected readonly plural = plural;
}
