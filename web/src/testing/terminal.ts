import type { Provider } from '@angular/core';
import { CREAR_WEBSOCKET } from '../app/features/terminal/conexion';
import type { PantallaTerminal } from '../app/features/terminal/pantalla';
import { FABRICA_PANTALLA } from '../app/features/terminal/pantalla';

/**
 * Un WebSocket de mentira hacia el gateway de terminal (T-05): guarda lo que
 * manda la app y simula lo que haría el gateway.
 */
export class WebSocketDePrueba {
  readyState: number = WebSocket.CONNECTING;
  binaryType = 'blob';
  cerradoPorLaApp = false;
  readonly enviados: string[] = [];
  onopen: ((evento: Event) => void) | null = null;
  onmessage: ((evento: MessageEvent) => void) | null = null;
  onclose: ((evento: CloseEvent) => void) | null = null;

  constructor(readonly url: string) {}

  send(datos: string): void {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('send() con el WebSocket sin abrir');
    }
    this.enviados.push(datos);
  }

  close(): void {
    this.cerradoPorLaApp = true;
    this.readyState = WebSocket.CLOSED;
  }

  /** Lo que mandó la app, ya como objetos. */
  mensajes(): unknown[] {
    return this.enviados.map((m) => JSON.parse(m));
  }

  // Lo que hace el gateway.

  abrir(): void {
    this.readyState = WebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  /** Salida de la terminal: un marco binario. */
  salida(texto: string): void {
    const bytes = new TextEncoder().encode(texto);
    this.onmessage?.(new MessageEvent('message', { data: bytes.buffer }));
  }

  /** Un marco de texto con `estado`. */
  estado(estado: 'conectado' | 'cerrado', motivo?: string): void {
    const mensaje =
      motivo === undefined ? { tipo: 'estado', estado } : { tipo: 'estado', estado, motivo };
    this.texto(JSON.stringify(mensaje));
  }

  texto(datos: string): void {
    this.onmessage?.(new MessageEvent('message', { data: datos }));
  }

  /** El gateway (o la red) cierra el WebSocket. */
  cerrarDesdeElServidor(): void {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: 1006 }));
  }
}

/** La pantalla de xterm.js, de mentira: guarda lo escrito y deja simular teclas y tamaños. */
export class PantallaDePrueba implements PantallaTerminal {
  escrito = '';
  limpiezas = 0;
  enfocada = 0;
  destruida = false;
  tamano: { columnas: number; filas: number } | null = { columnas: 100, filas: 30 };

  constructor(
    readonly elemento: HTMLElement,
    private readonly alTeclear: (datos: string) => void,
  ) {}

  /** Lo que haría xterm al teclear o pegar. */
  teclear(datos: string): void {
    this.alTeclear(datos);
  }

  escribir(datos: Uint8Array | string): void {
    this.escrito += typeof datos === 'string' ? datos : new TextDecoder().decode(datos);
  }

  ajustar() {
    return this.tamano;
  }

  limpiar(): void {
    this.escrito = '';
    this.limpiezas++;
  }

  enfocar(): void {
    this.enfocada++;
  }

  destruir(): void {
    this.destruida = true;
  }
}

export interface SimulacionTerminal {
  /** Los WebSocket que abrió la app, en orden. */
  readonly sockets: WebSocketDePrueba[];
  /** Las pantallas que creó (una por componente). */
  readonly pantallas: PantallaDePrueba[];
  readonly providers: Provider[];
  /** Si es `true`, la pantalla no se puede crear (como si xterm no descargara). */
  fallarCarga: boolean;
}

/** WebSocket y pantalla de mentira para la terminal real (sin red ni xterm.js). */
export function simularTerminal(): SimulacionTerminal {
  const simulacion: SimulacionTerminal = {
    sockets: [],
    pantallas: [],
    fallarCarga: false,
    providers: [],
  };
  (simulacion.providers as Provider[]).push(
    {
      provide: CREAR_WEBSOCKET,
      useValue: (url: string) => {
        const ws = new WebSocketDePrueba(url);
        simulacion.sockets.push(ws);
        return ws as unknown as WebSocket;
      },
    },
    {
      provide: FABRICA_PANTALLA,
      useValue: async (elemento: HTMLElement, alTeclear: (datos: string) => void) => {
        if (simulacion.fallarCarga) {
          throw new Error('no cargó xterm');
        }
        const pantalla = new PantallaDePrueba(elemento, alTeclear);
        simulacion.pantallas.push(pantalla);
        return pantalla;
      },
    },
  );
  return simulacion;
}
