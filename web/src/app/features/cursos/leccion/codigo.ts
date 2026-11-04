import { Clipboard } from '@angular/cdk/clipboard';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ViewEncapsulation,
  inject,
  input,
  signal,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import type { BloqueCodigo } from './markdown';

/** Cuánto se ve «Copiado» antes de volver a «Copiar». */
const AVISO_MS = 2000;

/**
 * Un bloque de código con el lenguaje arriba («bash», o «salida» en las
 * salidas) y el botón «Copiar». Copia con el portapapeles de CDK, que también
 * funciona por http (por ejemplo, al probar desde un celular por IP).
 */
@Component({
  selector: 'at-codigo',
  imports: [TranslocoPipe, Icono],
  template: `
    @let b = bloque();
    <div class="at-codigo-cabecera">
      <span>{{ b.lenguaje === 'text' ? ('leccion.salida' | transloco) : b.lenguaje }}</span>
      @if (b.copiable) {
        <button type="button" class="at-codigo-copiar" (click)="copiar()">
          <at-icono [nombre]="estado() === 'copiado' ? 'hecho' : 'copiar'" />
          {{
            (estado() === 'copiado'
              ? 'leccion.copiado'
              : estado() === 'fallo'
                ? 'leccion.noCopiado'
                : 'leccion.copiar'
            ) | transloco
          }}
        </button>
      }
    </div>
    <pre tabindex="0"><code [innerHTML]="b.html"></code></pre>
    <span class="at-oculto" aria-live="polite">{{
      estado() === 'copiado' ? ('leccion.avisoCopiado' | transloco) : ''
    }}</span>
  `,
  styles: `
    at-codigo {
      display: block;
      margin: 12px 0 16px;
      overflow: hidden;
      border-radius: 8px;
      background: #1e1f2a;
      color: #e8e8f0;
    }

    .at-codigo-cabecera {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 36px;
      padding: 0 4px 0 16px;
      background: #2a2b38;
      color: #c8c8d8;
      font: var(--mat-sys-label-medium);
    }

    .at-codigo-copiar {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 32px;
      padding: 0 12px;
      border: 0;
      border-radius: 6px;
      background: transparent;
      color: #e8e8f0;
      font: var(--mat-sys-label-large);
      cursor: pointer;
      --at-icono: 18px;
    }

    .at-codigo-copiar:hover {
      background: #3a3b4a;
    }

    .at-codigo-copiar:focus-visible {
      outline: 3px solid #8fb4ff;
      outline-offset: -3px;
    }

    at-codigo pre {
      margin: 0;
      padding: 12px 16px 14px;
      overflow-x: auto;
      font:
        0.9rem/1.5 ui-monospace,
        SFMono-Regular,
        Menlo,
        Consolas,
        'Liberation Mono',
        monospace;
    }

    at-codigo pre:focus-visible {
      outline: 3px solid #8fb4ff;
      outline-offset: -3px;
    }

    // Resaltado de bash, AA sobre el fondo oscuro.
    at-codigo .hljs-comment {
      color: #a0a4b8;
    }

    at-codigo .hljs-meta {
      color: #c4a7ff;
    }

    at-codigo .hljs-built_in,
    at-codigo .hljs-keyword {
      color: #8fb4ff;
    }

    at-codigo .hljs-string {
      color: #a6e3a1;
    }

    at-codigo .hljs-variable,
    at-codigo .hljs-subst,
    at-codigo .hljs-number,
    at-codigo .hljs-literal {
      color: #ffcb8b;
    }
  `,
  // El HTML resaltado entra por innerHTML y no lleva los atributos de la
  // encapsulación: los estilos van con el prefijo at-codigo.
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Codigo {
  readonly bloque = input.required<BloqueCodigo>();

  private readonly portapapeles = inject(Clipboard);
  protected readonly estado = signal<'listo' | 'copiado' | 'fallo'>('listo');
  private temporizador: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.temporizador));
  }

  protected copiar(): void {
    const copiado = this.portapapeles.copy(this.bloque().codigo);
    this.estado.set(copiado ? 'copiado' : 'fallo');
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.estado.set('listo'), AVISO_MS);
  }
}
