import { NgOptimizedImage } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { SelectorIdioma } from './selector-idioma';

interface Enlace {
  readonly ruta: string;
  readonly clave: string;
}

/**
 * Marco común: barra con el símbolo de Apolo, menú y selector de idioma.
 * Las pantallas de cuenta (ingresar, cambiar la clave) lo usan sin menú
 * (`data: { sinMenu: true }` en la ruta).
 */
@Component({
  selector: 'at-shell',
  imports: [
    NgOptimizedImage,
    MatButtonModule,
    MatToolbarModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslocoPipe,
    SelectorIdioma,
  ],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Shell {
  /**
   * Llega desde `data` de la ruta (withComponentInputBinding). Si la ruta no lo
   * trae, el router lo deja en `undefined`, por eso el valor «normal» es el falso.
   */
  readonly sinMenu = input<boolean | undefined>(false);

  // Panel y Administración se mostrarán según el rol cuando exista la sesión.
  protected readonly enlaces: readonly Enlace[] = [
    { ruta: '/cursos', clave: 'nav.cursos' },
    { ruta: '/mi-progreso', clave: 'nav.miProgreso' },
    { ruta: '/panel', clave: 'nav.panel' },
    { ruta: '/admin', clave: 'nav.admin' },
  ];
}
