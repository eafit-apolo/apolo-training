import { Directive, effect, inject, input } from '@angular/core';
import { MatInput } from '@angular/material/input';

/**
 * `[atErrorSi]="condicion()"` en un `matInput`: lo marca con error (borde rojo,
 * `aria-invalid`, `mat-error` visible) según una signal, sin `@angular/forms`.
 * Sin un `NgControl`, `matInput` nunca recalcula su estado de error; aquí se
 * le da el criterio y se le pide recalcular cuando la condición cambia.
 *
 * Las pantallas de cuenta no usan formularios reactivos para que
 * `@angular/forms` no entre al bundle inicial (F-03).
 */
@Directive({ selector: '[atErrorSi]' })
export class ErrorSi {
  readonly atErrorSi = input.required<boolean>();

  constructor() {
    const campo = inject(MatInput);
    campo.errorStateMatcher = { isErrorState: () => this.atErrorSi() };
    effect(() => {
      this.atErrorSi();
      campo.updateErrorState();
    });
  }
}

/** Valor de un `<input>` desde su evento `input`. */
export function valorDe(evento: Event): string {
  return (evento.target as HTMLInputElement).value;
}
