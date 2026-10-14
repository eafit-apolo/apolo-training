import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';

/**
 * Pantalla provisional de la F-01: ocupa cada ruta hasta que llegue la
 * pantalla real. Las claves llegan desde `data` de la ruta.
 */
@Component({
  selector: 'at-pagina-pendiente',
  imports: [TranslocoPipe],
  template: `
    <h1>{{ titulo() | transloco }}</h1>
    <p>{{ mensaje() | transloco }}</p>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaginaPendiente {
  readonly titulo = input.required<string>();
  readonly mensaje = input('pendiente.mensaje');
}
