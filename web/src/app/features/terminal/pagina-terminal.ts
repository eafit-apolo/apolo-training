import { ChangeDetectionStrategy, Component } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { TerminalReal } from './terminal-real';

/**
 * /terminal: la terminal real a pantalla completa, para quien la abre en otra
 * pestaña desde una lección. Aquí sí se conecta al entrar: abrir la pestaña
 * ya es pedir la terminal.
 */
@Component({
  selector: 'at-pagina-terminal',
  imports: [TranslocoPipe, TerminalReal],
  template: `
    <div class="at-contenedor">
      <h1>{{ 'paginas.terminal' | transloco }}</h1>
      <at-terminal-real [completa]="true" />
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaginaTerminal {}
