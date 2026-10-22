import { NgOptimizedImage } from '@angular/common';
import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  viewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { filter } from 'rxjs';
import type { Rol } from '../sesion/sesion';
import { SesionService } from '../sesion/sesion';
import type { Enlace as EnlaceMenu } from './menu-movil';
import { MenuMovil } from './menu-movil';
import { MenuUsuario } from './menu-usuario';
import { SelectorIdioma } from './selector-idioma';

interface Enlace extends EnlaceMenu {
  /** Sin `roles`, lo ven todos. */
  readonly roles?: readonly Rol[];
}

const ENLACES: readonly Enlace[] = [
  { ruta: '/cursos', clave: 'nav.cursos' },
  { ruta: '/mi-progreso', clave: 'nav.miProgreso' },
  { ruta: '/panel', clave: 'nav.panel', roles: ['instructor', 'admin'] },
  { ruta: '/admin', clave: 'nav.admin', roles: ['admin'] },
];

/**
 * Marco común: encabezado con el símbolo de Apolo, menú, selector de idioma y
 * menú de usuario. En celular el menú pasa a un botón ☰. Las pantallas de
 * cuenta (ingresar, cambiar la clave) lo usan sin menú
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
    MenuMovil,
    MenuUsuario,
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

  private readonly sesion = inject(SesionService);
  private readonly contenido = viewChild.required<ElementRef<HTMLElement>>('contenido');

  /**
   * Panel y Administración solo para su rol. Es solo lo que se muestra: las
   * guardias de ruta son de la F-03 y la API lo refuerza.
   */
  protected readonly enlaces = computed(() => {
    const rol = this.sesion.rol();
    return ENLACES.filter((e) => !e.roles || (rol !== null && e.roles.includes(rol)));
  });

  constructor() {
    // Al cambiar de página (no en la primera carga), el foco pasa al contenido
    // para que el lector de pantalla empiece por la página nueva.
    inject(Router)
      .events.pipe(
        filter((e) => e instanceof NavigationEnd && e.id > 1),
        takeUntilDestroyed(),
      )
      .subscribe(() => this.contenido().nativeElement.focus({ preventScroll: true }));
  }
}
