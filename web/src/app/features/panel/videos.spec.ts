import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { contenidoDePrueba } from '../../../testing/contenido';
import type { XhrDePrueba } from '../../../testing/panel';
import {
  resumenDeEjemplo,
  simularSubidas,
  sinAnimaciones,
  videoDeEjemplo,
} from '../../../testing/panel';
import { CARLA, borrarCookies, entrarComo, errorApi, ponerCsrf } from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { VideoAdminApi } from './datos';

const MB = 1024 ** 2;

function archivo(nombre: string, bytes: number, tipo = ''): File {
  const f = new File(['x'], nombre, { type: tipo });
  Object.defineProperty(f, 'size', { value: bytes });
  return f;
}

describe('Panel: videos', () => {
  let api: HttpTestingController;
  let xhrs: XhrDePrueba[];

  beforeEach(() => {
    borrarCookies();
    const subidas = simularSubidas();
    xhrs = subidas.xhrs;
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(withInterceptors([interceptorSesion])),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
        sinAnimaciones(),
        subidas.proveedor,
      ],
    });
    api = TestBed.inject(HttpTestingController);
    ponerCsrf('csrf-1');
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
    document.querySelectorAll('.cdk-overlay-container').forEach((c) => (c.innerHTML = ''));
  });

  const pendientes = () => new Promise((r) => setTimeout(r));
  const SUBIDO = videoDeEjemplo({
    id: 2,
    clave: 'm05-trabajos',
    disponible: true,
    duracion_seg: 245,
    tamano_bytes: 200 * MB,
    subtitulos: { es: true, en: false },
    lecciones: [
      { id: 50, slug: 'trabajos', modulo: 'm05', modulo_numero: 5, titulo: 'Trabajos con Slurm' },
    ],
    subido_por: 'carla',
    subido_en: '2026-11-26T15:00:00Z',
  });

  async function abrir(lista: VideoAdminApi[] = [videoDeEjemplo(), SUBIDO]) {
    entrarComo(CARLA);
    const harness = await RouterTestingHarness.create('/panel/videos');
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    api.expectOne('/api/panel/resumen?lang=es').flush(resumenDeEjemplo());
    api.expectOne('/api/panel/videos?lang=es').flush(lista);
    await listo();
    return { raiz, listo };
  }

  const texto = (el: Element | null | undefined) => el?.textContent?.replace(/\s+/g, ' ').trim();
  const fila = (raiz: HTMLElement, clave: string) =>
    Array.from(raiz.querySelectorAll('tbody tr')).find((tr) =>
      tr.querySelector('th')?.textContent?.includes(clave),
    )!;
  const boton = (raiz: HTMLElement, etiqueta: string) => {
    const encontrado = raiz.querySelector<HTMLButtonElement>(`button[aria-label="${etiqueta}"]`);
    if (!encontrado) {
      throw new Error(`No hay botón «${etiqueta}»`);
    }
    return encontrado;
  };

  /** Lo que hace la persona: el botón, y en el selector de archivos, el archivo. */
  async function elegir(
    raiz: HTMLElement,
    etiqueta: string,
    elegido: File,
    listo: () => Promise<void>,
  ) {
    const selector = raiz.querySelector<HTMLInputElement>('input[type=file]')!;
    const clic = vi.spyOn(selector, 'click').mockImplementation(() => undefined);
    boton(raiz, etiqueta).click();
    expect(clic).toHaveBeenCalled();
    Object.defineProperty(selector, 'files', { value: [elegido], configurable: true });
    selector.dispatchEvent(new Event('change'));
    await listo();
    clic.mockRestore();
  }

  /** Responde el `GET /api/me` con que se comprueba la sesión antes de subir. */
  async function sesionAlDia(listo: () => Promise<void>) {
    api.expectOne('/api/me').flush(CARLA);
    await listo();
  }

  it('lista los videos con su estado, la lección enlazada y las acciones', async () => {
    const { raiz } = await abrir();
    const pendiente = fila(raiz, 'm00-bienvenida');
    expect(texto(pendiente.querySelector('td:nth-of-type(2)'))).toBe('Pendiente');
    expect(pendiente.querySelector('a')?.getAttribute('href')).toBe(
      '/cursos/induccion/m00/bienvenida',
    );
    const subido = fila(raiz, 'm05-trabajos');
    expect(Array.from(subido.querySelectorAll('td')).map((td) => texto(td))).toEqual([
      '5 · Trabajos con Slurm',
      'Subido',
      '4:05',
      'Subido',
      'Sin subir',
      'Reemplazar MP4 Reemplazar VTT ES Subir VTT EN',
    ]);
    expect(boton(raiz, 'Subir el MP4 de m00-bienvenida').textContent).toContain('Subir MP4');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('DoD 1: sube el MP4 y sus dos VTT, con el progreso, y la fila queda al día', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);

    await elegir(
      raiz,
      'Subir el MP4 de m00-bienvenida',
      archivo('bienvenida.mp4', 200 * MB, 'video/mp4'),
      listo,
    );
    await sesionAlDia(listo);
    expect(xhrs).toHaveLength(1);
    const mp4 = xhrs[0];
    expect(mp4.metodo).toBe('PUT');
    expect(mp4.url).toBe('/api/panel/videos/m00-bienvenida');
    expect(mp4.cabeceras).toEqual({ 'Content-Type': 'video/mp4', 'X-CSRF-Token': 'csrf-1' });
    expect(texto(raiz.querySelector('[aria-live]'))).toBe(
      'Empezó la subida de bienvenida.mp4 a m00-bienvenida.',
    );
    mp4.progreso(124 * MB, 200 * MB);
    await listo();
    const subida = raiz.querySelector('.subida')!;
    expect(texto(subida.querySelector('.subida-titulo'))).toBe(
      'Subiendo bienvenida.mp4 a m00-bienvenida',
    );
    expect(texto(subida)).toContain('124 MB de 200 MB · 62 %');
    expect(subida.querySelector('mat-progress-bar')?.getAttribute('aria-valuenow')).toBe('62');
    // Mientras sube, no se puede empezar otra.
    boton(raiz, 'Subir los subtítulos ES de m00-bienvenida').click();
    await listo();
    expect(texto(raiz.querySelector('[role=alert]'))).toContain('Espera a que termine la subida');
    expect(xhrs).toHaveLength(1);

    let actual = videoDeEjemplo({ disponible: true, duracion_seg: 120, tamano_bytes: 200 * MB });
    mp4.responder(200, actual);
    await listo();
    expect(raiz.querySelector('.subida')).toBeNull();
    expect(texto(raiz.querySelector('[aria-live]'))).toBe(
      'Listo: bienvenida.mp4 quedó en m00-bienvenida.',
    );
    expect(texto(fila(raiz, 'm00-bienvenida').querySelector('td:nth-of-type(3)'))).toBe('2:00');

    for (const idioma of ['es', 'en'] as const) {
      const etiqueta = `Subir los subtítulos ${idioma.toUpperCase()} de m00-bienvenida`;
      await elegir(raiz, etiqueta, archivo(`${idioma}.vtt`, 2000), listo);
      await sesionAlDia(listo);
      const vtt = xhrs.at(-1)!;
      expect(vtt.url).toBe(`/api/panel/videos/m00-bienvenida/subtitulos/${idioma}`);
      expect(vtt.cabeceras['Content-Type']).toBe('text/vtt');
      actual = { ...actual, subtitulos: { ...actual.subtitulos, [idioma]: true } };
      vtt.responder(200, actual);
      await listo();
    }
    expect(
      Array.from(fila(raiz, 'm00-bienvenida').querySelectorAll('td')).map((td) => texto(td)),
    ).toEqual([
      '0 · Bienvenida al curso',
      'Subido',
      '2:00',
      'Subido',
      'Subido',
      'Reemplazar MP4 Reemplazar VTT ES Reemplazar VTT EN',
    ]);
  });

  it('el navegador revisa la extensión y el tamaño antes de subir', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(
      raiz,
      'Subir el MP4 de m00-bienvenida',
      archivo('clase.mov', 5 * MB, 'video/quicktime'),
      listo,
    );
    expect(texto(raiz.querySelector('[role=alert]'))).toBe(
      'clase.mov no es un MP4: el video tiene que ser un archivo .mp4.',
    );
    await elegir(
      raiz,
      'Subir los subtítulos EN de m00-bienvenida',
      archivo('en.vtt', 2 * MB),
      listo,
    );
    expect(texto(raiz.querySelector('[role=alert]'))).toBe('en.vtt pasa del máximo (1 MB).');
    expect(xhrs).toHaveLength(0);
  });

  it('antes de reemplazar un archivo subido pregunta; «Cancelar» no sube nada', async () => {
    const { raiz, listo } = await abrir();
    await elegir(raiz, 'Reemplazar el MP4 de m05-trabajos', archivo('nuevo.mp4', 10 * MB), listo);
    const dialogo = document.querySelector('mat-dialog-container')!;
    expect(texto(dialogo.querySelector('h2'))).toBe('¿Reemplazar el video de m05-trabajos?');
    // El foco en «Cancelar» se comprueba en Chrome: jsdom no sabe qué se ve.
    (dialogo.querySelectorAll('button')[0] as HTMLButtonElement).click();
    await listo();
    expect(xhrs).toHaveLength(0);

    await elegir(
      raiz,
      'Reemplazar los subtítulos ES de m05-trabajos',
      archivo('es.vtt', 1000),
      listo,
    );
    const otro = document.querySelector('mat-dialog-container')!;
    expect(texto(otro.querySelector('h2'))).toBe('¿Reemplazar los subtítulos ES de m05-trabajos?');
    (otro.querySelectorAll('button')[1] as HTMLButtonElement).click();
    await listo();
    await sesionAlDia(listo);
    expect(xhrs).toHaveLength(1);
    expect(xhrs[0].url).toBe('/api/panel/videos/m05-trabajos/subtitulos/es');
    xhrs[0].responder(200, SUBIDO);
    await listo();
  });

  it('«Cancelar» aborta la subida', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(raiz, 'Subir el MP4 de m00-bienvenida', archivo('a.mp4', 50 * MB), listo);
    await sesionAlDia(listo);
    xhrs[0].progreso(10 * MB, 50 * MB);
    await listo();
    (raiz.querySelector('.subida button') as HTMLButtonElement).click();
    await listo();
    expect(xhrs[0].abortado).toBe(true);
    expect(raiz.querySelector('.subida')).toBeNull();
    expect(texto(raiz.querySelector('[aria-live]'))).toBe('Se canceló la subida.');
  });

  it('un video que la API no acepta muestra por qué', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(raiz, 'Subir el MP4 de m00-bienvenida', archivo('a.mp4', 5 * MB), listo);
    await sesionAlDia(listo);
    xhrs[0].responder(415, {
      ...errorApi('video_formato_invalido'),
      detail: 'El video es mpeg4; tiene que ser H.264',
    });
    await listo();
    expect(texto(raiz.querySelector('[role=alert]'))).toBe(
      'La plataforma no aceptó el video: tiene que ser MP4 con H.264 (8 bits, 4:2:0) y audio AAC, o sin audio. Detalle: El video es mpeg4; tiene que ser H.264',
    );
    expect(raiz.querySelector('.subida')).toBeNull();
  });

  it('si la sesión vence justo al empezar (401), la renueva y lo intenta una vez más', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(raiz, 'Subir los subtítulos ES de m00-bienvenida', archivo('es.vtt', 1000), listo);
    await sesionAlDia(listo);
    xhrs[0].responder(401, errorApi('no_autenticado'));
    await listo();
    await sesionAlDia(listo);
    expect(xhrs).toHaveLength(2);
    xhrs[1].responder(401, errorApi('no_autenticado'));
    await listo();
    // La segunda vez ya no reintenta.
    expect(xhrs).toHaveLength(2);
    expect(texto(raiz.querySelector('[role=alert]'))).toContain('Algo falló de nuestro lado');
  });

  it('sin red durante la subida, lo dice', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(raiz, 'Subir el MP4 de m00-bienvenida', archivo('a.mp4', 5 * MB), listo);
    await sesionAlDia(listo);
    xhrs[0].sinRed();
    await listo();
    expect(texto(raiz.querySelector('[role=alert]'))).toContain(
      'No pudimos comunicarnos con la plataforma',
    );
  });

  it('salir del panel a mitad de una subida la aborta', async () => {
    const { raiz, listo } = await abrir([videoDeEjemplo()]);
    await elegir(raiz, 'Subir el MP4 de m00-bienvenida', archivo('a.mp4', 5 * MB), listo);
    await sesionAlDia(listo);
    expect(raiz.querySelector('.subida')).not.toBeNull();
    TestBed.resetTestingModule();
    expect(xhrs[0].abortado).toBe(true);
  });
});
