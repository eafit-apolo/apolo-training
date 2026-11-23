import { ChangeDetectionStrategy, Component, ViewEncapsulation, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../shared/icono';
import type { EstadoModuloApi } from '../cursos/datos/api';
import type { ModuloProgresoApi } from './datos';

/**
 * Los módulos de Mi progreso (F-07): una fila por módulo (lecciones completas
 * y estado) que se despliega con sus lecciones: completa, video visto, mejor
 * puntaje del quiz y las prácticas que explica (decisión del 23-nov).
 */
@Component({
  selector: 'at-modulos-progreso',
  imports: [RouterLink, TranslocoPipe, Icono],
  templateUrl: './modulos.html',
  styleUrl: './modulos.scss',
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModulosProgreso {
  readonly modulos = input.required<readonly ModuloProgresoApi[]>();
  /** Slug del curso, para los enlaces a las lecciones. */
  readonly curso = input.required<string | null>();
  /** Instructores y admins abren los módulos bloqueados (B-04). */
  readonly abreBloqueados = input(false);

  /** Si la lección se muestra como enlace: un estudiante no abre un módulo bloqueado. */
  protected abre(estado: EstadoModuloApi): boolean {
    return estado !== 'bloqueado' || this.abreBloqueados();
  }
}
