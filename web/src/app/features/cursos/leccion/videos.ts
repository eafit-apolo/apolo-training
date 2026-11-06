import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  computed,
  inject,
  input,
  linkedSignal,
  output,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import type { ProgresoLeccionApi, SistemaVideo, VideoLeccionApi } from '../datos/api';
import { Reproductor } from './reproductor';

type Sistema = Exclude<SistemaVideo, 'todos'>;

/** La API los manda en orden alfabético; se muestran en este. */
const ORDEN: readonly SistemaVideo[] = ['todos', 'windows', 'macos', 'linux'];

/** El sistema operativo del navegador, para abrir su video en la lección de VPN. */
export function sistemaDe(navegador: Navigator | undefined): Sistema | null {
  const datos = navegador as (Navigator & { userAgentData?: { platform?: string } }) | undefined;
  const texto = `${datos?.userAgentData?.platform ?? ''} ${datos?.userAgent ?? ''}`.toLowerCase();
  if (/windows|win32|win64/.test(texto)) {
    return 'windows';
  }
  if (/mac|iphone|ipad/.test(texto)) {
    return 'macos';
  }
  if (/linux|x11|cros/.test(texto)) {
    return 'linux';
  }
  return null;
}

/**
 * El espacio del video, arriba de la lección. Casi siempre es uno; en la de
 * VPN hay uno por sistema operativo y se abre el del navegador. Mientras no se
 * haya subido el MP4 (B-05), «Video en preparación»; si ya está, el
 * reproductor (F-05).
 */
@Component({
  selector: 'at-videos',
  imports: [TranslocoPipe, Icono, Reproductor],
  template: `
    @let lista = videos();
    @if (lista.length > 1) {
      <div class="sistemas" role="group" [attr.aria-label]="'leccion.video.sistemas' | transloco">
        @for (v of lista; track v.sistema) {
          <button
            type="button"
            [attr.aria-pressed]="v.sistema === elegido()"
            (click)="elegido.set(v.sistema)"
          >
            {{ 'leccion.video.' + v.sistema | transloco }}
            @if (v.sistema === propio) {
              <span class="tuyo">{{ 'leccion.video.tuSistema' | transloco }}</span>
            }
          </button>
        }
      </div>
    }
    <!-- Un reproductor por video: al cambiar de sistema se arma otro y el anterior
         reporta dónde iba. -->
    @for (v of mostrado(); track v.video.id) {
      @if (v.video.disponible && v.video.url) {
        <at-reproductor
          [video]="v.video"
          [leccionId]="leccionId()"
          [progreso]="progreso()"
          [retomar]="v.sistema === inicial()"
          [guardar]="guardar()"
          (reportado)="reportado.emit($event)"
        />
      } @else {
        <div class="pendiente">
          <at-icono nombre="video" />
          <div>
            <p class="titulo">{{ 'leccion.video.pendiente' | transloco }}</p>
            <p>{{ 'leccion.video.pendienteTexto' | transloco }}</p>
          </div>
        </div>
      }
    }
  `,
  styles: `
    :host {
      display: block;
      margin: 0 0 24px;
    }

    .sistemas {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }

    .sistemas button {
      padding: 6px 14px;
      border: 1px solid var(--mat-sys-outline);
      border-radius: 8px;
      background: transparent;
      color: var(--mat-sys-on-surface);
      font: var(--mat-sys-label-large);
      cursor: pointer;
    }

    .sistemas button[aria-pressed='true'] {
      border-color: var(--mat-sys-primary);
      background: var(--mat-sys-secondary-container);
      color: var(--mat-sys-on-secondary-container);
    }

    .sistemas button:focus-visible {
      outline: 3px solid var(--mat-sys-primary);
      outline-offset: 2px;
    }

    .tuyo {
      font: var(--mat-sys-body-small);
    }

    .pendiente {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container);
      --at-icono: 40px;
    }

    .pendiente at-icono {
      color: var(--mat-sys-primary);
    }

    p {
      margin: 0;
    }

    .titulo {
      font: var(--mat-sys-title-medium);
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Videos {
  readonly videos = input.required<readonly VideoLeccionApi[], readonly VideoLeccionApi[]>({
    transform: (lista) =>
      [...lista].sort((a, b) => ORDEN.indexOf(a.sistema) - ORDEN.indexOf(b.sistema)),
  });

  readonly leccionId = input.required<number>();
  readonly progreso = input.required<ProgresoLeccionApi>();
  /** `false` en un módulo bloqueado que un instructor está leyendo. */
  readonly guardar = input(true);
  readonly reportado = output<ProgresoLeccionApi>();

  protected readonly propio = sistemaDe(inject(DOCUMENT).defaultView?.navigator);

  /** El del navegador si la lección lo tiene; si no, el primero. */
  protected readonly inicial = computed(() => {
    const lista = this.videos();
    return (lista.find((v) => v.sistema === this.propio) ?? lista[0])?.sistema;
  });

  /**
   * El elegido. Si la lista vuelve a llegar (al cambiar el idioma, o tras un
   * reporte) y todavía tiene el que eligió el usuario, se queda ese.
   */
  protected readonly elegido = linkedSignal<readonly VideoLeccionApi[], SistemaVideo | undefined>({
    source: this.videos,
    computation: (lista, previo) =>
      previo && lista.some((v) => v.sistema === previo.value) ? previo.value : this.inicial(),
  });
  protected readonly mostrado = computed(() =>
    this.videos().filter((v) => v.sistema === this.elegido()),
  );
}
