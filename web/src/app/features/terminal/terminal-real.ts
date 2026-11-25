import type { ElementRef } from '@angular/core';
import {
  ChangeDetectionStrategy,
  Component,
  DOCUMENT,
  DestroyRef,
  Injector,
  afterNextRender,
  computed,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import type { Cluster } from '../../core/sesion/sesion';
import { SesionService } from '../../core/sesion/sesion';
import type { NombreIcono } from '../../shared/icono';
import { Icono } from '../../shared/icono';
import type { MotivoCierre } from './conexion';
import { CREAR_WEBSOCKET, ConexionTerminal, urlTerminal } from './conexion';
import type { PantallaTerminal } from './pantalla';
import { FABRICA_PANTALLA } from './pantalla';

type Fase = 'inactiva' | 'conectando' | 'conectada' | 'cerrada';

/** Además de los motivos de la conexión: no se pudo descargar xterm.js. */
type Motivo = MotivoCierre | 'carga';

/** El login real de cada clúster (docs/perfiles.md), para el aviso. */
const LOGIN: Record<Cluster, string> = {
  apolo2: 'apolo.eafit.edu.co',
  apolo3: 'apolo-3.eafit.edu.co',
};

const ICONO: Record<Fase, NombreIcono> = {
  inactiva: 'pendiente',
  conectando: 'en-curso',
  conectada: 'completo',
  cerrada: 'error',
};

/**
 * La terminal real hacia la VM de práctica (T-06), con el gateway de la T-05.
 * No se conecta sola: cada conexión pide la contraseña de la VM y el gateway
 * deja una sola sesión por usuario (abrir otra cierra esta con `otra_sesion`).
 * Al cerrarse muestra el motivo y «Reconectar». Salir de la página cierra el
 * WebSocket, y el gateway cierra la sesión SSH.
 */
@Component({
  selector: 'at-terminal-real',
  imports: [MatButtonModule, RouterLink, TranslocoPipe, Icono],
  templateUrl: './terminal-real.html',
  styleUrl: './terminal-real.scss',
  host: { '[class.completa]': 'completa()' },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TerminalReal {
  /** En /terminal: se conecta al entrar, ocupa la pantalla y no ofrece otra pestaña. */
  readonly completa = input(false);

  private readonly sesion = inject(SesionService);
  private readonly crearWebSocket = inject(CREAR_WEBSOCKET);
  private readonly fabrica = inject(FABRICA_PANTALLA);
  private readonly documento = inject(DOCUMENT);
  private readonly injector = inject(Injector);
  private readonly elemento = viewChild.required<ElementRef<HTMLElement>>('pantalla');

  private readonly preparando = signal(false);
  private readonly conexion = signal<ConexionTerminal | null>(null);
  /** Un fallo antes de abrir el WebSocket. */
  private readonly fallo = signal<Motivo | null>(null);
  /** La pantalla se muestra desde la primera vez que se abre. */
  protected readonly visible = signal(false);

  protected readonly fase = computed<Fase>(() => {
    if (this.preparando()) {
      return 'conectando';
    }
    const conexion = this.conexion();
    if (conexion) {
      return conexion.estado().fase;
    }
    return this.fallo() ? 'cerrada' : 'inactiva';
  });

  protected readonly motivo = computed<Motivo | null>(() => {
    const estado = this.conexion()?.estado();
    return estado?.fase === 'cerrada' ? estado.motivo : this.fallo();
  });

  protected readonly icono = computed(() => ICONO[this.fase()]);
  protected readonly cluster = computed(() => this.sesion.usuario()?.cluster ?? null);
  protected readonly login = computed(() => {
    const cluster = this.cluster();
    return cluster ? LOGIN[cluster] : null;
  });

  private pantalla: PantallaTerminal | null = null;
  private observador: ResizeObserver | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.soltar());
    afterNextRender(() => {
      if (this.completa()) {
        void this.abrir();
      }
    });
  }

  /** «Abrir terminal» y «Reconectar». */
  protected async abrir(): Promise<void> {
    if (this.preparando()) {
      return;
    }
    this.conexion()?.cerrar();
    this.conexion.set(null);
    this.fallo.set(null);
    this.preparando.set(true);
    try {
      // Si `at` venció, el interceptor la renueva. Si la sesión terminó o hay
      // que cambiar la clave, el interceptor lleva a la pantalla que toca.
      await this.sesion.comprobar();
    } catch {
      this.fracasar('conexion');
      return;
    }
    try {
      await this.prepararPantalla();
    } catch {
      this.fracasar('carga');
      return;
    }
    const conexion = new ConexionTerminal(
      this.crearWebSocket,
      urlTerminal(this.documento.location),
      (datos) => this.pantalla?.escribir(datos),
    );
    this.conexion.set(conexion);
    this.preparando.set(false);
    this.ajustar();
    this.pantalla?.enfocar();
  }

  /** La primera vez crea xterm (ya visible, para que pueda medirse); después, la limpia. */
  private async prepararPantalla(): Promise<void> {
    if (this.pantalla) {
      this.pantalla.limpiar();
      return;
    }
    this.visible.set(true);
    await new Promise<void>((listo) => afterNextRender(() => listo(), { injector: this.injector }));
    const elemento = this.elemento().nativeElement;
    this.pantalla = await this.fabrica(elemento, (datos) => this.conexion()?.enviar(datos));
    // Cambiar el tamaño de la ventana (o de la columna) ajusta filas y columnas.
    if (typeof ResizeObserver !== 'undefined') {
      this.observador = new ResizeObserver(() => this.ajustar());
      this.observador.observe(elemento);
    }
  }

  private ajustar(): void {
    const tamano = this.pantalla?.ajustar();
    if (tamano) {
      this.conexion()?.cambiarTamano(tamano.columnas, tamano.filas);
    }
  }

  private fracasar(motivo: Motivo): void {
    this.preparando.set(false);
    this.fallo.set(motivo);
  }

  private soltar(): void {
    this.conexion()?.cerrar();
    this.observador?.disconnect();
    this.pantalla?.destruir();
    this.pantalla = null;
  }
}
