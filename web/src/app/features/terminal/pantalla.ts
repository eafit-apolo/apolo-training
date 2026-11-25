import { InjectionToken } from '@angular/core';

/** Lo que la terminal real necesita de xterm.js; las pruebas usan una de mentira. */
export interface PantallaTerminal {
  /** La salida de la VM (bytes tal cual) o un texto. */
  escribir(datos: Uint8Array | string): void;
  /** Ajusta filas y columnas al tamaño del elemento y las devuelve (null si no se ve). */
  ajustar(): { readonly columnas: number; readonly filas: number } | null;
  /** Borra la pantalla, para reconectar. */
  limpiar(): void;
  enfocar(): void;
  destruir(): void;
}

/** Crea la pantalla dentro de `elemento`; `alTeclear` recibe lo que se escribe o se pega. */
export type FabricaPantalla = (
  elemento: HTMLElement,
  alTeclear: (datos: string) => void,
) => Promise<PantallaTerminal>;

/**
 * xterm.js pesa unos 350 kB: se descarga solo la primera vez que alguien abre
 * la terminal (import dinámico), no con el resto de la app.
 */
export const FABRICA_PANTALLA = new InjectionToken<FabricaPantalla>('FABRICA_PANTALLA', {
  providedIn: 'root',
  factory: () => (elemento, alTeclear) =>
    import('./pantalla-xterm').then((m) => m.crearPantallaXterm(elemento, alTeclear)),
});
