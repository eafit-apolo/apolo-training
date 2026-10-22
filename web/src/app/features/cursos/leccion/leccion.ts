import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { TranslocoPipe } from '@jsverse/transloco';
import { Icono } from '../../../shared/icono';
import type { Miga } from '../../../shared/migas';
import { Migas } from '../../../shared/migas';
import { PaginaPendiente } from '../../../shared/pagina-pendiente';
import { CatalogoService } from '../datos/catalogo';
import { Bloqueado } from '../modulo/bloqueado';

/**
 * Pantalla 03, solo el marco: migas, título y estado. El cuerpo (video,
 * resumen con pestañas, práctica, quiz, anterior y siguiente) es de la F-04.
 */
@Component({
  selector: 'at-leccion',
  imports: [TranslocoPipe, Icono, Migas, PaginaPendiente, Bloqueado],
  template: `
    @if (datos(); as l) {
      <at-migas [migas]="migas()" />
      <h1>{{ l.numero }} · {{ l.titulo }}</h1>
      @let m = datosModulo();
      @if (m && m.estado === 'bloqueado') {
        <at-bloqueado [curso]="datosCurso()" [modulo]="m" />
      } @else {
        <p class="meta">
          <at-icono nombre="duracion" />
          {{ 'cursos.minutos' | transloco: { n: l.duracion } }} ·
          <at-icono [nombre]="l.completa ? 'completo' : 'pendiente'" [class.hecha]="l.completa" />
          {{ (l.completa ? 'estado.leccionCompleta' : 'estado.leccionPendiente') | transloco }}
        </p>
        <div class="cuerpo">
          <p>{{ 'leccion.pendiente' | transloco }}</p>
        </div>
      }
    } @else {
      <at-pagina-pendiente titulo="paginas.noEncontrada" mensaje="noEncontrada.mensaje" />
    }
  `,
  styles: `
    .meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px;
      margin: 0 0 24px;
      color: var(--mat-sys-on-surface-variant);
      --at-icono: 20px;
    }

    .hecha {
      color: var(--at-verde);
    }

    .cuerpo {
      display: grid;
      place-items: center;
      min-height: 240px;
      padding: 24px;
      border: 2px dashed var(--mat-sys-outline-variant);
      border-radius: 12px;
      color: var(--mat-sys-on-surface-variant);
      text-align: center;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Leccion {
  /** `:curso`, `:modulo` y `:leccion` de la ruta (llegan por paramsInheritanceStrategy). */
  readonly curso = input<string>();
  readonly modulo = input<string>();
  readonly leccion = input<string>();

  private readonly catalogo = inject(CatalogoService);
  protected readonly datosCurso = computed(() => this.catalogo.curso(this.curso()));
  protected readonly datosModulo = computed(() =>
    this.catalogo.modulo(this.datosCurso(), this.modulo()),
  );
  protected readonly datos = computed(() =>
    this.catalogo.leccion(this.datosModulo(), this.leccion()),
  );

  protected readonly migas = computed<readonly Miga[]>(() => {
    const curso = this.datosCurso();
    const modulo = this.datosModulo();
    return [
      { clave: 'nav.cursos', ruta: ['/cursos'] },
      { texto: curso?.titulo, ruta: ['/cursos', curso?.id ?? ''] },
      {
        texto: `${modulo?.numero} · ${modulo?.titulo}`,
        ruta: ['/cursos', curso?.id ?? '', modulo?.id ?? ''],
      },
      { texto: this.datos()?.titulo },
    ];
  });
}
