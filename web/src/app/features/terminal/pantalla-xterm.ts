import { FitAddon } from '@xterm/addon-fit';
import { Terminal } from '@xterm/xterm';
import type { PantallaTerminal } from './pantalla';

/**
 * La pantalla con xterm.js 6. Este archivo solo se carga con import dinámico
 * (pantalla.ts), así xterm queda en su propio paquete. Los estilos de xterm
 * están en `styles` de angular.json.
 */
export function crearPantallaXterm(
  elemento: HTMLElement,
  alTeclear: (datos: string) => void,
): PantallaTerminal {
  const terminal = new Terminal({
    cursorBlink: true,
    // Las de los bloques de código (codigo.ts): sin fuentes descargadas.
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace",
    fontSize: 14,
    scrollback: 5000,
    theme: { background: '#1e1f2a', foreground: '#e8e8f0', cursor: '#8fb4ff' },
  });
  const ajuste = new FitAddon();
  terminal.loadAddon(ajuste);
  terminal.open(elemento);
  const tecleo = terminal.onData(alTeclear);
  return {
    escribir: (datos) => terminal.write(datos),
    ajustar: () => {
      // Sin tamaño (pestaña oculta, elemento sin medidas) no hay propuesta.
      if (!ajuste.proposeDimensions()) {
        return null;
      }
      ajuste.fit();
      return { columnas: terminal.cols, filas: terminal.rows };
    },
    limpiar: () => terminal.reset(),
    enfocar: () => terminal.focus(),
    destruir: () => {
      tecleo.dispose();
      terminal.dispose();
    },
  };
}
