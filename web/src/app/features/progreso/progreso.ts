import { DOCUMENT } from '@angular/common';
import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ViewEncapsulation,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { IdiomaService } from '../../core/i18n/idioma';
import { SesionService } from '../../core/sesion/sesion';
import { Icono } from '../../shared/icono';
import type { Practica } from '../cursos/datos/api';
import type { LabEstadoApi, LeccionDePractica, MiProgresoApi } from './datos';
import {
  ProgresoApi,
  cifrasDe,
  leccionesDePracticas,
  numeroDeLeccion,
  sincronizacionAtrasada,
} from './datos';
import { FormatoFecha } from './formato';
import { GraduacionPanel } from './graduacion';
import { ModulosProgreso } from './modulos';

/** Cada cuánto se recalculan «hace N min» y el aviso de atraso. */
const TIC_MS = 60_000;

/**
 * Pantalla 04 (F-07): qué le falta al usuario para terminar el curso. Todo sale
 * de `GET /api/me/progreso`: cifras, siguiente paso, módulos con sus
 * lecciones, las siete prácticas de la VM con la última sincronización y la
 * graduación.
 *
 * Se recarga al cambiar el idioma (los títulos vienen traducidos), al volver
 * a la pestaña, con «Actualizar» y después de enviar la graduación (decisión
 * del 23-nov). «Hace N min» y el aviso de los 15 minutos se recalculan cada
 * minuto sin pedir nada a la API.
 */
@Component({
  selector: 'at-mi-progreso',
  imports: [
    MatButtonModule,
    MatProgressBarModule,
    RouterLink,
    TranslocoPipe,
    Icono,
    GraduacionPanel,
    ModulosProgreso,
  ],
  templateUrl: './progreso.html',
  styleUrl: './progreso.scss',
  // Sin encapsulación para que los estilos lleguen a `at-graduacion`; todo va
  // bajo `.at-progreso`.
  encapsulation: ViewEncapsulation.None,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MiProgreso {
  private readonly api = inject(ProgresoApi);
  private readonly sesion = inject(SesionService);
  private readonly idioma = inject(IdiomaService).actual;
  private readonly documento = inject(DOCUMENT);
  private readonly formato = inject(FormatoFecha);

  protected readonly usuario = this.sesion.usuario;
  protected readonly datos = signal<MiProgresoApi | null>(null);
  protected readonly cargando = signal(false);
  /** Falló la carga: sin datos, pantalla de error; con datos, un aviso. */
  protected readonly fallo = signal(false);
  /** Texto de la región `aria-live` (actualizado, enviada…). */
  protected readonly anuncio = signal('');
  protected readonly ahora = signal(Date.now());

  private readonly titulo = viewChild<ElementRef<HTMLElement>>('graduacionTitulo');
  /** Para descartar la respuesta de un pedido viejo (otro idioma, doble clic). */
  private pedido = 0;

  protected readonly cifras = computed(() => {
    const datos = this.datos();
    return datos ? cifrasDe(datos) : null;
  });

  protected readonly lecciones = computed(() => leccionesDePracticas(this.datos()?.modulos ?? []));

  protected readonly atrasada = computed(() => {
    const datos = this.datos();
    return datos
      ? sincronizacionAtrasada(
          datos.ultima_sincronizacion,
          datos.sincronizacion_atrasada,
          this.ahora(),
        )
      : false;
  });

  /** Instructores y admins abren los módulos bloqueados (B-04). */
  protected readonly abreBloqueados = computed(() => {
    const rol = this.sesion.rol();
    return rol === 'instructor' || rol === 'admin';
  });

  protected readonly paso = computed(() => {
    const datos = this.datos();
    if (!datos) {
      return null;
    }
    const paso = datos.siguiente_paso;
    if (paso.tipo === 'leccion' && paso.leccion && datos.curso) {
      const l = paso.leccion;
      return {
        tipo: paso.tipo,
        numero: numeroDeLeccion(datos.modulos, l.modulo, l.slug),
        titulo: l.titulo,
        ruta: ['/cursos', datos.curso, l.modulo, l.slug],
        lab: null,
      };
    }
    if (paso.tipo === 'laboratorio' && paso.lab) {
      const donde = this.lecciones().get(paso.lab);
      return {
        tipo: paso.tipo,
        numero: donde?.numero ?? null,
        titulo: donde?.titulo ?? null,
        ruta: donde ? this.rutaDe(donde) : null,
        lab: paso.lab,
      };
    }
    return { tipo: paso.tipo, numero: null, titulo: null, ruta: null, lab: null };
  });

  constructor() {
    // Carga al entrar y cada vez que cambia el idioma.
    effect(() => {
      const idioma = this.idioma();
      untracked(() => void this.cargar(idioma));
    });

    const reloj = setInterval(() => this.ahora.set(Date.now()), TIC_MS);
    const alVolver = () => {
      if (this.documento.visibilityState === 'visible') {
        this.ahora.set(Date.now());
        void this.cargar(this.idioma());
      }
    };
    this.documento.addEventListener('visibilitychange', alVolver);
    inject(DestroyRef).onDestroy(() => {
      clearInterval(reloj);
      this.documento.removeEventListener('visibilitychange', alVolver);
    });
  }

  /** «Actualizar»: vuelve a pedir y lo anuncia sin mover el foco. */
  protected async actualizar(): Promise<void> {
    this.anuncio.set('');
    if (await this.cargar(this.idioma())) {
      this.anuncio.set('progreso.actualizado');
    }
  }

  /**
   * Tras enviar la graduación: recarga (cambia el siguiente paso) y, si la API
   * la aceptó, lo anuncia. Si ya estaba aprobada, la recarga lo muestra.
   */
  protected async alEnviarGraduacion(aceptada: boolean): Promise<void> {
    this.anuncio.set('');
    await this.cargar(this.idioma());
    this.anuncio.set(
      aceptada ? 'progreso.graduacion.enviadaAviso' : 'progreso.graduacion.yaAprobada',
    );
  }

  /** «Envía tu graduación» del siguiente paso: lleva el foco a esa sección. */
  protected irAGraduacion(): void {
    const titulo = this.titulo()?.nativeElement;
    titulo?.scrollIntoView?.({ block: 'start' });
    titulo?.focus();
  }

  /** Ruta de la lección de una práctica, si el usuario la puede abrir. */
  protected rutaDe(donde: LeccionDePractica): string[] | null {
    const curso = this.datos()?.curso;
    if (!curso || (donde.bloqueada && !this.abreBloqueados())) {
      return null;
    }
    return ['/cursos', curso, donde.modulo, donde.slug];
  }

  protected leccionDe(lab: LabEstadoApi): LeccionDePractica | undefined {
    return this.lecciones().get(lab.lab);
  }

  protected fecha(iso: string): string {
    return this.formato.fecha(iso);
  }

  protected hora(iso: string): string {
    return this.formato.hora(iso, this.ahora());
  }

  protected hace(iso: string): string {
    return this.formato.hace(iso, this.ahora());
  }

  protected nombreLab(lab: Practica): string {
    return `progreso.practicas.nombres.${lab}`;
  }

  /** Pide Mi progreso; `true` si llegó (y es la respuesta del último pedido). */
  private async cargar(idioma: Parameters<ProgresoApi['progreso']>[0]): Promise<boolean> {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    try {
      const datos = await this.api.progreso(idioma);
      if (pedido !== this.pedido) {
        return false;
      }
      this.datos.set(datos);
      this.fallo.set(false);
      this.ahora.set(Date.now());
      return true;
    } catch {
      if (pedido === this.pedido) {
        this.fallo.set(true);
      }
      return false;
    } finally {
      if (pedido === this.pedido) {
        this.cargando.set(false);
      }
    }
  }

  protected reintentar(): void {
    void this.cargar(this.idioma());
  }
}
