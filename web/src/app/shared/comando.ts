import { Clipboard } from '@angular/cdk/clipboard';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  input,
  signal,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from './icono';

/** Cuánto se ve «Copiado» antes de volver a «Copiar». */
const AVISO_MS = 2000;

/**
 * Un comando para copiar y correr en otra máquina (F-08): la orden de
 * `apolo-training-admin`, el `sacctmgr` de la QOS o el `sacct` para confirmar
 * una graduación. Texto plano, sin resaltado, con «Copiar» (el portapapeles
 * de CDK, que también funciona por http) y el aviso en una región `aria-live`.
 */
@Component({
  selector: 'at-comando',
  imports: [TranslocoPipe, Icono],
  template: `
    <div class="cabecera">
      <span>{{ etiqueta() ?? ('comando.etiqueta' | transloco) }}</span>
      <button type="button" class="copiar" (click)="copiar()">
        <at-icono [nombre]="estado() === 'copiado' ? 'hecho' : 'copiar'" />
        {{
          (estado() === 'copiado'
            ? 'comando.copiado'
            : estado() === 'fallo'
              ? 'comando.noCopiado'
              : 'comando.copiar'
          ) | transloco
        }}
      </button>
    </div>
    <pre tabindex="0"><code>{{ texto() }}</code></pre>
    <span class="at-oculto" aria-live="polite">{{
      estado() === 'copiado' ? ('comando.avisoCopiado' | transloco) : ''
    }}</span>
  `,
  styles: `
    :host {
      display: block;
      overflow: hidden;
      border-radius: 8px;
      background: #1e1f2a;
      color: #e8e8f0;
    }

    .cabecera {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 36px;
      padding: 0 4px 0 16px;
      background: #2a2b38;
      color: #c8c8d8;
      font: var(--mat-sys-label-medium);
    }

    .copiar {
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

    .copiar:hover {
      background: #3a3b4a;
    }

    .copiar:focus-visible,
    pre:focus-visible {
      outline: 3px solid #8fb4ff;
      outline-offset: -3px;
    }

    pre {
      margin: 0;
      padding: 12px 16px 14px;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font:
        0.9rem/1.5 ui-monospace,
        SFMono-Regular,
        Menlo,
        Consolas,
        'Liberation Mono',
        monospace;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Comando {
  private readonly portapapeles = inject(Clipboard);

  readonly texto = input.required<string>();
  /** Lo que va arriba a la izquierda; por defecto, «Comando». */
  readonly etiqueta = input<string | null>(null);

  protected readonly estado = signal<'listo' | 'copiado' | 'fallo'>('listo');
  private temporizador: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.temporizador));
  }

  protected copiar(): void {
    const ok = this.portapapeles.copy(this.texto());
    this.estado.set(ok ? 'copiado' : 'fallo');
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.estado.set('listo'), AVISO_MS);
  }
}
