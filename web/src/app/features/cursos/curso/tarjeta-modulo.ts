import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { plural } from '../../../shared/plural';
import type { Modulo } from '../datos/curso';
import { EstadoModulo } from './estado-modulo';

/**
 * Tarjeta de un módulo en la grilla del curso. Un módulo bloqueado se ve
 * (título, duración, qué trae) pero no es un enlace.
 */
@Component({
  selector: 'at-tarjeta-modulo',
  imports: [MatProgressBarModule, RouterLink, TranslocoPipe, EstadoModulo],
  template: `
    @let m = modulo();
    <div class="cabecera">
      <span class="numero" aria-hidden="true">{{ m.numero }}</span>
      <at-estado-modulo [estado]="m.estado" [compacto]="m.estado === 'bloqueado'" />
    </div>
    <h3>
      @if (m.estado === 'bloqueado') {
        <span class="at-oculto">{{ 'cursos.moduloCorto' | transloco: { n: m.numero } }}</span>
        {{ m.titulo }}
      } @else {
        <a class="enlace" [routerLink]="['/cursos', curso(), m.id]">
          <span class="at-oculto">{{ 'cursos.moduloCorto' | transloco: { n: m.numero } }}</span>
          {{ m.titulo }}
        </a>
      }
    </h3>
    <p class="minutos">{{ 'cursos.minutos' | transloco: { n: m.duracion } }}</p>
    <ul class="at-etiquetas">
      @if (m.videos) {
        <li>{{ plural('cursos.videos', m.videos) | transloco: { n: m.videos } }}</li>
      }
      @if (m.practicas) {
        <li>{{ plural('cursos.practicas', m.practicas) | transloco: { n: m.practicas } }}</li>
      }
      @if (m.preguntas) {
        <li>{{ plural('cursos.preguntas', m.preguntas) | transloco: { n: m.preguntas } }}</li>
      }
    </ul>
    @if (m.estado === 'bloqueado') {
      <p class="bloqueado">{{ 'estado.abreAl' | transloco: { n: m.numero - 1 } }}</p>
    } @else {
      <mat-progress-bar
        mode="determinate"
        [value]="(100 * m.hechas) / m.lecciones.length"
        [attr.aria-label]="
          plural('modulo.avanceEtiqueta', m.lecciones.length)
            | transloco: { n: m.numero, hechas: m.hechas, total: m.lecciones.length }
        "
      />
    }
  `,
  styleUrl: './tarjeta-modulo.scss',
  host: {
    '[class.bloqueado]': "modulo().estado === 'bloqueado'",
    '[class.en-curso]': "modulo().estado === 'en-curso'",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TarjetaModulo {
  readonly curso = input.required<string>();
  readonly modulo = input.required<Modulo>();
  protected readonly plural = plural;
}
