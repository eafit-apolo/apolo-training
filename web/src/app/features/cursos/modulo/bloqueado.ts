import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import type { Curso, Modulo } from '../datos/curso';

/**
 * Lo que se ve al abrir por dirección un módulo o una lección bloqueados
 * (la API responderá 403 `modulo_bloqueado`): por qué y a dónde ir.
 */
@Component({
  selector: 'at-bloqueado',
  imports: [MatButtonModule, RouterLink, TranslocoPipe, Icono],
  template: `
    <div class="aviso" role="status">
      <at-icono nombre="bloqueado" />
      <p>{{ 'estado.bloqueadoPagina' | transloco: { n: modulo().numero - 1 } }}</p>
    </div>
    @if (enCurso(); as m) {
      <a mat-flat-button [routerLink]="['/cursos', curso()?.id, m.id]">
        {{ 'estado.irAlModulo' | transloco: { n: m.numero, titulo: m.titulo } }}
      </a>
    }
  `,
  styles: `
    .aviso {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 16px 0 24px;
      padding: 16px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container-high);
    }

    p {
      margin: 0;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Bloqueado {
  readonly curso = input<Curso>();
  readonly modulo = input.required<Modulo>();
  protected readonly enCurso = computed(() =>
    this.curso()?.modulos.find((m) => m.estado === 'en-curso'),
  );
}
