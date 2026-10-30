import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';
import type { Idioma } from '../../../core/i18n/idioma';
import { IdiomaService } from '../../../core/i18n/idioma';
import { SesionService } from '../../../core/sesion/sesion';
import type { CursoDetalleApi } from './api';
import { ContenidoApi } from './api';
import { armarCurso } from './armar';
import type { Curso, Leccion, Modulo } from './curso';

/**
 * Cursos con el avance del usuario, desde la API de contenido (B-04).
 *
 * Las rutas de los cursos esperan a `cargarCatalogo()` o `cargarCurso()`
 * (guardias de `cargar.ts`), así que las pantallas leen de forma síncrona con
 * `cursos()`, `curso()`, `modulo()` y `leccion()`. Lo cargado vale para un
 * usuario y un idioma: con otro usuario se pide de nuevo, y al cambiar el
 * idioma se vuelve a pedir lo que está en pantalla, sin vaciarla mientras llega.
 */
@Injectable({ providedIn: 'root' })
export class CatalogoService {
  private readonly api = inject(ContenidoApi);
  private readonly sesion = inject(SesionService);
  private readonly idioma = inject(IdiomaService);

  private readonly detalles = signal<ReadonlyMap<string, CursoDetalleApi>>(new Map());
  /** Slugs del catálogo, en orden; `null` si no se ha pedido. */
  private readonly lista = signal<readonly string[] | null>(null);
  private usuarioCargado: string | null = null;
  private idiomaCargado: Idioma | null = null;

  /** La última carga falló (sin conexión o un error de la API). */
  readonly error = signal(false);

  /** Instructores y admins abren los módulos bloqueados (decisión del 29-oct). */
  private readonly puedeVerBloqueados = computed(() => {
    const rol = this.sesion.rol();
    return rol === 'instructor' || rol === 'admin';
  });

  private readonly armados = computed(() => {
    const ver = this.puedeVerBloqueados();
    return new Map([...this.detalles()].map(([slug, api]) => [slug, armarCurso(api, ver)]));
  });

  readonly cursos = computed<readonly Curso[]>(() =>
    (this.lista() ?? []).flatMap((slug) => this.armados().get(slug) ?? []),
  );

  constructor() {
    effect(() => {
      const idioma = this.idioma.actual();
      untracked(() => {
        if (this.idiomaCargado !== null && idioma !== this.idiomaCargado) {
          void this.recargar();
        }
      });
    });
  }

  /** El catálogo y el detalle de cada curso (la portada muestra «Continuar»). */
  async cargarCatalogo(): Promise<void> {
    this.sincronizar();
    if (this.lista() === null) {
      await this.pedir(true, []);
    }
  }

  async cargarCurso(slug: string | null): Promise<void> {
    this.sincronizar();
    if (slug && !this.detalles().has(slug)) {
      await this.pedir(false, [slug]);
    }
  }

  /** Vuelve a pedir lo cargado (otro idioma; luego, tras completar una lección). */
  async recargar(): Promise<void> {
    await this.pedir(this.lista() !== null, [...this.detalles().keys()]);
  }

  curso(id: string | undefined): Curso | undefined {
    return id ? this.armados().get(id) : undefined;
  }

  modulo(curso: Curso | undefined, id: string | undefined): Modulo | undefined {
    return curso?.modulos.find((m) => m.id === id);
  }

  leccion(modulo: Modulo | undefined, slug: string | undefined): Leccion | undefined {
    return modulo?.lecciones.find((l) => l.slug === slug);
  }

  /** Lo guardado es de otro usuario: se descarta. */
  private sincronizar(): void {
    const usuario = this.sesion.usuario()?.username ?? null;
    if (usuario !== this.usuarioCargado) {
      this.detalles.set(new Map());
      this.lista.set(null);
      this.usuarioCargado = usuario;
      this.idiomaCargado = null;
    }
  }

  private async pedir(conCatalogo: boolean, slugs: readonly string[]): Promise<void> {
    const idioma = this.idioma.actual();
    try {
      const lista = conCatalogo ? (await this.api.cursos(idioma)).map((c) => c.slug) : null;
      const todos = [...new Set([...(lista ?? []), ...slugs])];
      const detalles = await Promise.all(todos.map((slug) => this.api.curso(slug, idioma)));
      if (idioma !== this.idioma.actual()) {
        return; // Cambió el idioma mientras llegaba: ya hay otra carga en camino.
      }
      this.detalles.update((actuales) => {
        const nuevos = new Map(actuales);
        todos.forEach((slug, i) => {
          const detalle = detalles[i];
          if (detalle) {
            nuevos.set(slug, detalle);
          } else {
            nuevos.delete(slug);
          }
        });
        return nuevos;
      });
      if (lista) {
        this.lista.set(lista);
      }
      this.idiomaCargado = idioma;
      this.error.set(false);
    } catch (error) {
      console.error('No se pudo cargar el contenido', error);
      this.error.set(true);
    }
  }
}
