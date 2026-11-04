import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  computed,
  inject,
  input,
  linkedSignal,
} from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../../core/i18n/idioma';
import { Icono } from '../../../shared/icono';
import type { SistemaVideo, VideoLeccionApi } from '../datos/api';

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
 * haya subido el MP4 (B-05), «Video en preparación». El reproductor completo
 * (subtítulos, velocidad, reanudar y avance) es de la F-05.
 */
@Component({
  selector: 'at-videos',
  imports: [TranslocoPipe, Icono],
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
    @if (actual(); as v) {
      @if (v.video.disponible && v.video.url) {
        <video controls preload="metadata" [src]="v.video.url">
          @for (s of v.video.subtitulos; track s.idioma) {
            <track
              kind="subtitles"
              [src]="s.url"
              [attr.srclang]="s.idioma"
              [label]="'idioma.' + s.idioma | transloco"
              [default]="s.idioma === 'en' && idioma.actual() === 'en'"
            />
          }
        </video>
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

    video {
      display: block;
      width: 100%;
      aspect-ratio: 16 / 9;
      border-radius: 12px;
      background: #000;
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

  protected readonly idioma = inject(IdiomaService);
  protected readonly propio = sistemaDe(inject(DOCUMENT).defaultView?.navigator);

  /** El del navegador si la lección lo tiene; si no, el primero. */
  protected readonly elegido = linkedSignal<SistemaVideo | undefined>(() => {
    const lista = this.videos();
    return (lista.find((v) => v.sistema === this.propio) ?? lista[0])?.sistema;
  });
  protected readonly actual = computed(() =>
    this.videos().find((v) => v.sistema === this.elegido()),
  );
}
