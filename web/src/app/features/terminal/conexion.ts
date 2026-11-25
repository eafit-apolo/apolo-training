import type { Signal } from '@angular/core';
import { InjectionToken, signal } from '@angular/core';

/** Motivos de cierre del gateway (docs/diseno/flujos.md, «3. Terminal real»). */
export type MotivoGateway =
  'inactividad' | 'tiempo_maximo' | 'otra_sesion' | 'ssh_rechazado' | 'sesion_invalida' | 'error';

/**
 * Además de los del gateway: `salida` (el usuario salió del shell: llega
 * `cerrado` sin motivo) y `conexion` (el WebSocket se cerró sin avisar: red,
 * gateway caído o un `Origin` rechazado).
 */
export type MotivoCierre = MotivoGateway | 'salida' | 'conexion';

export type EstadoConexion =
  /** El WebSocket se está abriendo o la VM pide la contraseña. */
  | { readonly fase: 'conectando' }
  /** La autenticación pasó y la PTY está abierta. */
  | { readonly fase: 'conectada' }
  | { readonly fase: 'cerrada'; readonly motivo: MotivoCierre };

const MOTIVOS: readonly string[] = [
  'inactividad',
  'tiempo_maximo',
  'otra_sesion',
  'ssh_rechazado',
  'sesion_invalida',
  'error',
] satisfies readonly MotivoGateway[];

/** Crea el WebSocket; las pruebas lo reemplazan por uno de mentira. */
export const CREAR_WEBSOCKET = new InjectionToken<(url: string) => WebSocket>('CREAR_WEBSOCKET', {
  providedIn: 'root',
  factory: () => (url) => new WebSocket(url),
});

/** `wss://<host>/ws/terminal` (o `ws://` en local): el mismo origen de la app. */
export function urlTerminal(ubicacion: Pick<Location, 'protocol' | 'host'>): string {
  return `${ubicacion.protocol === 'https:' ? 'wss' : 'ws'}://${ubicacion.host}/ws/terminal`;
}

/**
 * Lo que se pega de una vez puede ser largo y el gateway acepta hasta 64 KiB
 * por mensaje: se manda en trozos.
 */
export const TROZO = 16 * 1024;

/** Corta `texto` en trozos de hasta `maximo` sin partir un emoji (par sustituto). */
export function trozos(texto: string, maximo = TROZO): string[] {
  const partes: string[] = [];
  let inicio = 0;
  while (inicio < texto.length) {
    let fin = Math.min(inicio + maximo, texto.length);
    const anterior = texto.charCodeAt(fin - 1);
    if (fin < texto.length && anterior >= 0xd800 && anterior <= 0xdbff) {
      fin--;
    }
    partes.push(texto.slice(inicio, fin));
    inicio = fin;
  }
  return partes;
}

/**
 * Una conexión con el gateway de terminal (T-05). Del navegador salen
 * `entrada` y `tamano` como JSON; del gateway llegan bytes (la salida de la
 * terminal, tal cual) y `estado` como JSON. Una conexión cerrada no se reabre:
 * para reconectar se crea otra.
 */
export class ConexionTerminal {
  private readonly actual = signal<EstadoConexion>({ fase: 'conectando' });
  readonly estado: Signal<EstadoConexion> = this.actual.asReadonly();

  private readonly ws: WebSocket;
  private tamano: { readonly columnas: number; readonly filas: number } | null = null;
  private tamanoEnviado = '';

  constructor(
    crear: (url: string) => WebSocket,
    url: string,
    private readonly alRecibir: (datos: Uint8Array) => void,
  ) {
    this.ws = crear(url);
    this.ws.binaryType = 'arraybuffer';
    // El tamaño puede llegar antes de que abra: se manda al abrir.
    this.ws.onopen = () => this.mandarTamano();
    this.ws.onmessage = (evento: MessageEvent) => this.recibir(evento.data);
    // A un error siempre le sigue `close`.
    this.ws.onclose = () => this.terminar('conexion');
  }

  /** Lo que el usuario teclea o pega. */
  enviar(datos: string): void {
    if (!this.abierta()) {
      return;
    }
    for (const parte of trozos(datos)) {
      this.mandar({ tipo: 'entrada', datos: parte });
    }
  }

  /** Filas y columnas de la pantalla; solo se manda si cambiaron. */
  cambiarTamano(columnas: number, filas: number): void {
    this.tamano = { columnas, filas };
    this.mandarTamano();
  }

  /** La cierra la app (reconectar, salir de la página): sin avisos ni estado nuevo. */
  cerrar(): void {
    this.ws.onopen = null;
    this.ws.onmessage = null;
    this.ws.onclose = null;
    this.ws.close();
  }

  private abierta(): boolean {
    return this.ws.readyState === WebSocket.OPEN && this.actual().fase !== 'cerrada';
  }

  private mandarTamano(): void {
    if (!this.tamano || !this.abierta()) {
      return;
    }
    const { columnas, filas } = this.tamano;
    const clave = `${columnas}x${filas}`;
    if (clave === this.tamanoEnviado) {
      return;
    }
    this.tamanoEnviado = clave;
    this.mandar({ tipo: 'tamano', columnas, filas });
  }

  private mandar(mensaje: object): void {
    this.ws.send(JSON.stringify(mensaje));
  }

  private recibir(datos: unknown): void {
    if (typeof datos !== 'string') {
      // Marco binario: la salida de la terminal.
      this.alRecibir(new Uint8Array(datos as ArrayBuffer));
      return;
    }
    let mensaje: { tipo?: unknown; estado?: unknown; motivo?: unknown };
    try {
      mensaje = JSON.parse(datos);
    } catch {
      return;
    }
    if (mensaje?.tipo !== 'estado') {
      return;
    }
    if (mensaje.estado === 'conectado' && this.actual().fase === 'conectando') {
      this.actual.set({ fase: 'conectada' });
    } else if (mensaje.estado === 'cerrado') {
      const motivo = mensaje.motivo;
      if (motivo === undefined || motivo === null) {
        this.terminar('salida');
      } else {
        this.terminar(MOTIVOS.includes(motivo as string) ? (motivo as MotivoGateway) : 'error');
      }
    }
  }

  /** El primer motivo gana: tras `cerrado`, el gateway cierra el WebSocket. */
  private terminar(motivo: MotivoCierre): void {
    if (this.actual().fase !== 'cerrada') {
      this.actual.set({ fase: 'cerrada', motivo });
    }
  }
}
