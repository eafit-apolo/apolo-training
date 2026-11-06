/**
 * Un `<video>` de mentira para las pruebas del reproductor (F-05): jsdom no
 * reproduce nada, así que aquí `currentTime`, `duration`, `paused`,
 * `textTracks`, `play()` y `load()` se manejan a mano. Las pistas salen de los
 * `<track>` del elemento, una por `srclang`, como en un navegador.
 *
 * `simularVideos()` en el `beforeEach` y `restaurar()` en el `afterEach`.
 */

export interface PistaSimulada {
  readonly language: string;
  mode: TextTrackMode;
}

export interface VideoSimulado {
  tiempo: number;
  duracion: number;
  pausado: boolean;
  /** Cuántas veces se llamó a `load()`. */
  cargas: number;
  readonly pistas: PistaSimulada[];
}

const PROPIEDADES = ['currentTime', 'duration', 'paused', 'textTracks', 'play', 'load'] as const;

export interface Simulacion {
  /** El estado de un `<video>` (se crea al primer uso). */
  de(video: HTMLMediaElement): VideoSimulado;
  restaurar(): void;
}

export function simularVideos(): Simulacion {
  const prototipo = HTMLMediaElement.prototype;
  const originales = PROPIEDADES.map(
    (nombre) => [nombre, Object.getOwnPropertyDescriptor(prototipo, nombre)] as const,
  );
  const estados = new WeakMap<HTMLMediaElement, VideoSimulado>();
  const listas = new WeakMap<HTMLMediaElement, EventTarget & Record<number, PistaSimulada>>();

  const de = (video: HTMLMediaElement): VideoSimulado => {
    let estado = estados.get(video);
    if (!estado) {
      estado = { tiempo: 0, duracion: 300, pausado: true, cargas: 0, pistas: [] };
      estados.set(video, estado);
    }
    return estado;
  };

  /** La lista de pistas al día con los `<track>`, conservando el modo de cada una. */
  const pistasDe = (video: HTMLMediaElement) => {
    const estado = de(video);
    for (const track of Array.from(video.querySelectorAll('track'))) {
      const idioma = track.getAttribute('srclang') ?? '';
      if (!estado.pistas.some((p) => p.language === idioma)) {
        estado.pistas.push({ language: idioma, mode: 'disabled' });
      }
    }
    let lista = listas.get(video);
    if (!lista) {
      lista = new EventTarget() as EventTarget & Record<number, PistaSimulada>;
      listas.set(video, lista);
    }
    estado.pistas.forEach((pista, i) => (lista[i] = pista));
    Object.defineProperty(lista, 'length', { value: estado.pistas.length, configurable: true });
    return lista;
  };

  Object.defineProperties(prototipo, {
    currentTime: {
      configurable: true,
      get(this: HTMLMediaElement) {
        return de(this).tiempo;
      },
      set(this: HTMLMediaElement, valor: number) {
        de(this).tiempo = valor;
      },
    },
    duration: {
      configurable: true,
      get(this: HTMLMediaElement) {
        return de(this).duracion;
      },
    },
    paused: {
      configurable: true,
      get(this: HTMLMediaElement) {
        return de(this).pausado;
      },
    },
    textTracks: {
      configurable: true,
      get(this: HTMLMediaElement) {
        return pistasDe(this);
      },
    },
    play: {
      configurable: true,
      writable: true,
      value(this: HTMLMediaElement) {
        de(this).pausado = false;
        this.dispatchEvent(new Event('play'));
        return Promise.resolve();
      },
    },
    load: {
      configurable: true,
      writable: true,
      value(this: HTMLMediaElement) {
        de(this).cargas++;
      },
    },
  });

  return {
    de,
    restaurar: () => {
      for (const [nombre, descriptor] of originales) {
        if (descriptor) {
          Object.defineProperty(prototipo, nombre, descriptor);
        }
      }
    },
  };
}

/** Lo que hace el navegador al tener la duración: `loadedmetadata`. */
export function cargarVideo(video: HTMLMediaElement): void {
  video.dispatchEvent(new Event('loadedmetadata'));
  video.dispatchEvent(new Event('canplay'));
}

/** El usuario pausa: `paused` y luego el evento. */
export function pausarVideo(simulado: VideoSimulado, video: HTMLMediaElement): void {
  simulado.pausado = true;
  video.dispatchEvent(new Event('pause'));
}
