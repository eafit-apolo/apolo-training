import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';

/**
 * Pantalla provisional de la F-01: ocupa cada ruta hasta que llegue la
 * pantalla real. Las claves llegan desde `data` de la ruta. También es la
 * página «no encontrada» de las pantallas del curso.
 */
@Component({
  selector: 'at-pagina-pendiente',
  imports: [TranslocoPipe],
  template: `
    <div class="at-contenedor">
      <h1>{{ titulo() | transloco }}</h1>
      <p>{{ mensaje() | transloco }}</p>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaginaPendiente {
  readonly titulo = input.required<string>();
  readonly mensaje = input('pendiente.mensaje');
}
