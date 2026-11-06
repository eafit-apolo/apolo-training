import { HttpErrorResponse } from '@angular/common/http';
import type { ComponentFixture } from '@angular/core/testing';
import { TestBed } from '@angular/core/testing';
import { problemasDeAccesibilidad } from '../../../../testing/axe';
import { traduccionesDePrueba } from '../../../../testing/transloco';
import type { Simulacion, VideoSimulado } from '../../../../testing/video';
import { cargarVideo, pausarVideo, simularVideos } from '../../../../testing/video';
import { IdiomaService } from '../../../core/i18n/idioma';
import { SesionService } from '../../../core/sesion/sesion';
import type { ProgresoLeccionApi, ProgresoVideoEntradaApi, VideoRefApi } from '../datos/api';
import { ContenidoApi } from '../datos/api';
import { CatalogoService } from '../datos/catalogo';
import { leerGuardadas } from './preferencias-video';
import { CADA_MS, PAUSA_LARGA_MS, Reproductor, inicioDe, tiempo } from './reproductor';

const VIDEO: VideoRefApi = {
  id: 7,
  clave: 'm05-trabajos',
  disponible: true,
  duracion_seg: 300,
  url: '/api/media/7',
  subtitulos: [
    { idioma: 'es', url: '/api/media/7/subtitulos/es' },
    { idioma: 'en', url: '/api/media/7/subtitulos/en' },
  ],
};

function progreso(cambios: Partial<ProgresoLeccionApi> = {}): ProgresoLeccionApi {
  return {
    leccion_id: 41,
    video_posicion_seg: 0,
    video_max_seg: 0,
    video_completo: false,
    quiz_aprobado: false,
    completada: false,
    completada_en: null,
    ...cambios,
  };
}

describe('inicioDe y tiempo', () => {
  it.each([
    [120, 300, 120],
    [5, 300, 5],
    [4, 300, 0],
    [269, 300, 269],
    [270, 300, 0],
    [300, 300, 0],
    [50, 0, 0],
  ])('posición %i de %i s → empieza en %i', (posicion, duracion, inicio) => {
    expect(inicioDe(posicion, duracion)).toBe(inicio);
  });

  it.each([
    [0, '0:00'],
    [9, '0:09'],
    [222, '3:42'],
    [3723, '1:02:03'],
  ])('%i s se muestra como %s', (segundos, texto) => {
    expect(tiempo(segundos)).toBe(texto);
  });
});

describe('leerGuardadas', () => {
  it('sin nada guardado: normal, subtítulos en inglés solo con la interfaz en inglés', () => {
    expect(leerGuardadas(null)).toEqual({ velocidad: 1, subtitulos: { es: 'no', en: 'en' } });
  });

  it('lo que no sirve vuelve al valor por defecto', () => {
    expect(leerGuardadas('{"velocidad":3,"subtitulos":{"es":"fr","en":"es"}}')).toEqual({
      velocidad: 1,
      subtitulos: { es: 'no', en: 'es' },
    });
    expect(leerGuardadas('no es json')).toEqual(leerGuardadas(null));
  });
});

describe('Reproductor (F-05)', () => {
  let simulacion: Simulacion;
  let fixture: ComponentFixture<Reproductor>;
  let video: HTMLVideoElement;
  let estado: VideoSimulado;
  let reportes: { entrada: ProgresoVideoEntradaApi; alSalir: boolean }[];
  let respuesta: (entrada: ProgresoVideoEntradaApi) => Promise<ProgresoLeccionApi>;
  const recargar = vi.fn(async () => undefined);
  const comprobar = vi.fn(async () => undefined);

  beforeEach(() => {
    localStorage.clear();
    simulacion = simularVideos();
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
    reportes = [];
    respuesta = async (entrada) =>
      progreso({ video_posicion_seg: entrada.segundo, video_max_seg: entrada.segundo });
    recargar.mockClear();
    comprobar.mockReset().mockResolvedValue(undefined);
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        {
          provide: ContenidoApi,
          useValue: {
            reportarVideo: (entrada: ProgresoVideoEntradaApi, alSalir = false) => {
              reportes.push({ entrada, alSalir });
              return respuesta(entrada);
            },
          },
        },
        { provide: CatalogoService, useValue: { recargar } },
        { provide: SesionService, useValue: { comprobar } },
      ],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    simulacion.restaurar();
  });

  async function crear(
    entradas: { video?: VideoRefApi; progreso?: ProgresoLeccionApi; retomar?: boolean } = {},
    guardar = true,
  ): Promise<HTMLElement> {
    fixture = TestBed.createComponent(Reproductor);
    fixture.componentRef.setInput('video', entradas.video ?? VIDEO);
    fixture.componentRef.setInput('leccionId', 41);
    fixture.componentRef.setInput('progreso', entradas.progreso ?? progreso());
    fixture.componentRef.setInput('retomar', entradas.retomar ?? true);
    fixture.componentRef.setInput('guardar', guardar);
    await estable();
    video = fixture.nativeElement.querySelector('video');
    estado = simulacion.de(video);
    return fixture.nativeElement;
  }

  /** Deja correr las promesas (la API de mentira) y pinta. */
  async function estable(): Promise<void> {
    // jsdom manda `ratechange` en una tarea aparte, como el navegador.
    await new Promise((r) => setTimeout(r));
    for (let i = 0; i < 3; i++) {
      await Promise.resolve();
      await fixture.whenStable();
    }
  }

  async function reproducirHasta(segundo: number): Promise<void> {
    await video.play();
    estado.tiempo = segundo;
    vi.advanceTimersByTime(CADA_MS);
    await estable();
  }

  const segundos = () => reportes.map((r) => r.entrada.segundo);
  const pista = (idioma: string) => estado.pistas.find((p) => p.language === idioma)?.mode;
  const opciones = (raiz: HTMLElement, i: number) =>
    Array.from(raiz.querySelectorAll('select')[i].options).map((o) => o.textContent?.trim());

  describe('subtítulos (DoD 2)', () => {
    it('en español vienen apagados; en inglés, en inglés; y cambian con el idioma', async () => {
      const raiz = await crear();
      cargarVideo(video);

      expect(video.querySelectorAll('track')).toHaveLength(2);
      expect([pista('es'), pista('en')]).toEqual(['disabled', 'disabled']);
      expect(raiz.querySelectorAll('select')[1].value).toBe('no');

      await TestBed.inject(IdiomaService).cambiar('en');
      await estable();
      expect([pista('es'), pista('en')]).toEqual(['disabled', 'showing']);
      expect(raiz.querySelectorAll('select')[1].value).toBe('en');

      await TestBed.inject(IdiomaService).cambiar('es');
      await estable();
      expect(pista('en')).toBe('disabled');
    });

    it('se pueden apagar, y la elección se recuerda para ese idioma', async () => {
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await crear();
      const selector = raiz.querySelectorAll('select')[1];

      selector.value = 'no';
      selector.dispatchEvent(new Event('change'));
      await estable();

      expect(pista('en')).toBe('disabled');
      expect(JSON.parse(localStorage.getItem('apolo-training.video') ?? '{}').subtitulos).toEqual({
        es: 'no',
        en: 'no',
      });
      fixture.destroy();
      await crear();
      expect(pista('en')).toBe('disabled');
    });

    it('en español se pueden prender los de español', async () => {
      const raiz = await crear();
      const selector = raiz.querySelectorAll('select')[1];

      selector.value = 'es';
      selector.dispatchEvent(new Event('change'));
      await estable();

      expect([pista('es'), pista('en')]).toEqual(['showing', 'disabled']);
    });

    it('si los elige en el menú del navegador, también se recuerda', async () => {
      await crear();
      estado.pistas[0].mode = 'showing';
      video.textTracks.dispatchEvent(new Event('change'));
      await estable();

      expect(fixture.nativeElement.querySelectorAll('select')[1].value).toBe('es');
      expect(JSON.parse(localStorage.getItem('apolo-training.video') ?? '{}').subtitulos.es).toBe(
        'es',
      );
    });

    it('si el navegador prende otra pista por su cuenta, se vuelve a la elegida sin guardar nada', async () => {
      await TestBed.inject(IdiomaService).cambiar('en');
      await crear();
      expect(pista('en')).toBe('showing');

      // Lo que hizo Chrome al recargar: prendió la de español además de la de inglés.
      estado.pistas[0].mode = 'showing';
      video.textTracks.dispatchEvent(new Event('change'));
      await estable();

      expect([pista('es'), pista('en')]).toEqual(['disabled', 'showing']);
      expect(localStorage.getItem('apolo-training.video')).toBeNull();
    });

    it('sin la pista en inglés, en inglés quedan apagados y solo se ofrece el español', async () => {
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await crear({ video: { ...VIDEO, subtitulos: [VIDEO.subtitulos[0]] } });

      expect(pista('es')).toBe('disabled');
      expect(opciones(raiz, 1)).toEqual(['Off', 'Spanish']);
      // Que este video no la tenga no cambia lo que eligió para los demás.
      video.textTracks.dispatchEvent(new Event('change'));
      await estable();
      expect(localStorage.getItem('apolo-training.video')).toBeNull();
    });

    it('un video sin subtítulos no tiene selector', async () => {
      const raiz = await crear({ video: { ...VIDEO, subtitulos: [] } });

      expect(raiz.querySelectorAll('select')).toHaveLength(1);
      expect(video.querySelector('track')).toBeNull();
    });
  });

  describe('velocidad', () => {
    it('de 0.75x a 2x; la elegida se aplica y se recuerda', async () => {
      const raiz = await crear();
      cargarVideo(video);
      expect(opciones(raiz, 0)).toEqual(['0,75x', 'Normal', '1,25x', '1,5x', '1,75x', '2x']);
      expect(raiz.querySelectorAll('select')[0].value).toBe('1');

      const selector = raiz.querySelectorAll('select')[0];
      selector.value = '1.5';
      selector.dispatchEvent(new Event('change'));
      await estable();

      expect(video.playbackRate).toBe(1.5);
      fixture.destroy();
      await crear();
      cargarVideo(video);
      expect(video.playbackRate).toBe(1.5);
      expect(fixture.nativeElement.querySelectorAll('select')[0].value).toBe('1.5');
    });

    it('una velocidad del menú del navegador fuera de la lista se muestra, pero no se guarda', async () => {
      const raiz = await crear();
      video.playbackRate = 0.5;
      await estable();

      expect(opciones(raiz, 0)[0]).toBe('0,5x');
      expect(raiz.querySelectorAll('select')[0].value).toBe('0.5');
      expect(localStorage.getItem('apolo-training.video')).toBeNull();
    });
  });

  describe('retomar (DoD 3)', () => {
    it('empieza en el segundo guardado y lo dice', async () => {
      const raiz = await crear({ progreso: progreso({ video_posicion_seg: 120 }) });
      cargarVideo(video);
      await estable();

      expect(estado.tiempo).toBe(120);
      expect(raiz.querySelector('.retomado')?.textContent).toContain('Seguiste donde ibas (2:00).');

      (raiz.querySelector('.retomado button') as HTMLButtonElement).click();
      await estable();
      expect(estado.tiempo).toBe(0);
      expect(raiz.querySelector('.retomado')).toBeNull();
    });

    it('el aviso se va cuando ya guardó otro segundo', async () => {
      const raiz = await crear({ progreso: progreso({ video_posicion_seg: 120 }) });
      cargarVideo(video);
      await estable();
      expect(raiz.querySelector('.retomado')).not.toBeNull();

      await reproducirHasta(135);

      expect(segundos()).toEqual([135]);
      expect(raiz.querySelector('.retomado')).toBeNull();
    });

    it.each([
      ['casi al principio', 3, true],
      ['si ya lo vio', 280, true],
      ['en el video de otro sistema', 120, false],
    ])('no retoma %s', async (_, posicion, retomar) => {
      const raiz = await crear({ progreso: progreso({ video_posicion_seg: posicion }), retomar });
      cargarVideo(video);
      await estable();

      expect(estado.tiempo).toBe(0);
      expect(raiz.querySelector('.retomado')).toBeNull();
    });

    it('retoma una sola vez: una carga nueva del mismo video no vuelve atrás', async () => {
      await crear({ progreso: progreso({ video_posicion_seg: 120 }) });
      cargarVideo(video);
      estado.tiempo = 150;
      cargarVideo(video);

      expect(estado.tiempo).toBe(150);
    });
  });

  describe('reporte', () => {
    it('cada 15 s mientras corre, sin repetir el mismo segundo, y al pausar', async () => {
      await crear();
      cargarVideo(video);

      await reproducirHasta(14.6);
      await reproducirHasta(14.6);
      estado.tiempo = 29.2;
      vi.advanceTimersByTime(CADA_MS);
      await estable();
      estado.tiempo = 33;
      pausarVideo(estado, video);
      await estable();
      vi.advanceTimersByTime(CADA_MS * 3);
      await estable();

      expect(segundos()).toEqual([15, 29, 33]);
      expect(reportes[0].entrada).toEqual({ leccion_id: 41, video_id: 7, segundo: 15 });
      expect(reportes.every((r) => !r.alSalir)).toBe(true);
    });

    it('al saltar con el video en pausa también reporta', async () => {
      await crear();
      cargarVideo(video);
      estado.tiempo = 200;
      video.dispatchEvent(new Event('seeked'));
      await estable();

      expect(segundos()).toEqual([200]);
    });

    it('al terminar manda la duración completa', async () => {
      await crear();
      cargarVideo(video);
      estado.duracion = 299.4;
      estado.tiempo = 299.4;
      video.dispatchEvent(new Event('ended'));
      await estable();

      expect(segundos()).toEqual([300]);
    });

    it('al ocultar la pestaña manda el último con keepalive', async () => {
      await crear();
      cargarVideo(video);
      estado.tiempo = 42;
      vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden');
      document.dispatchEvent(new Event('visibilitychange'));
      await estable();

      expect(reportes).toEqual([
        { entrada: { leccion_id: 41, video_id: 7, segundo: 42 }, alSalir: true },
      ]);
    });

    it('al salir de la lección manda dónde iba', async () => {
      await crear();
      cargarVideo(video);
      estado.tiempo = 61;
      fixture.destroy();
      await Promise.resolve();

      expect(segundos()).toEqual([61]);
    });

    it('en un módulo bloqueado (un instructor que lo lee) no reporta nada', async () => {
      await crear({}, false);
      cargarVideo(video);
      await reproducirHasta(30);
      pausarVideo(estado, video);
      fixture.destroy();

      expect(reportes).toEqual([]);
    });

    it('un 403 o un 404 detiene los reportes', async () => {
      respuesta = async () => {
        throw new HttpErrorResponse({ status: 403, error: { codigo: 'modulo_bloqueado' } });
      };
      await crear();
      cargarVideo(video);
      await reproducirHasta(15);
      await reproducirHasta(30);

      expect(segundos()).toEqual([15]);
    });

    it('sin conexión lo intenta en el siguiente', async () => {
      respuesta = async () => {
        throw new HttpErrorResponse({ status: 0 });
      };
      await crear();
      cargarVideo(video);
      await reproducirHasta(15);
      await reproducirHasta(30);

      expect(segundos()).toEqual([15, 30]);
    });

    it('al llegar al 90 % la API completa la lección: avisa una vez y recarga el catálogo', async () => {
      respuesta = async (entrada) =>
        progreso({
          video_posicion_seg: entrada.segundo,
          video_completo: entrada.segundo >= 270,
          completada: entrada.segundo >= 270,
        });
      await crear();
      const emitidos: ProgresoLeccionApi[] = [];
      fixture.componentInstance.reportado.subscribe((p) => emitidos.push(p));
      cargarVideo(video);

      await reproducirHasta(260);
      expect(recargar).not.toHaveBeenCalled();
      await reproducirHasta(275);
      await reproducirHasta(290);

      expect(emitidos.map((p) => p.completada)).toEqual([false, true, true]);
      expect(recargar).toHaveBeenCalledTimes(1);
    });
  });

  describe('sesión vencida y errores', () => {
    it('si el video falla, comprueba la sesión, lo vuelve a cargar y sigue donde iba', async () => {
      const raiz = await crear();
      cargarVideo(video);
      await video.play();
      estado.tiempo = 95;
      video.dispatchEvent(new Event('error'));
      await estable();

      expect(comprobar).toHaveBeenCalledTimes(1);
      expect(estado.cargas).toBe(1);
      estado.tiempo = 0;
      estado.pausado = true;
      cargarVideo(video);
      await estable();

      expect(estado.tiempo).toBe(95);
      expect(estado.pausado).toBe(false);
      expect(raiz.querySelector('.fallo')).toBeNull();
    });

    it('si vuelve a fallar enseguida, lo dice y deja reintentar', async () => {
      const raiz = await crear();
      cargarVideo(video);
      estado.tiempo = 40;
      video.dispatchEvent(new Event('error'));
      await estable();
      estado.tiempo = 0;
      video.dispatchEvent(new Event('error'));
      await estable();

      expect(raiz.querySelector('.fallo')?.textContent).toContain('No pudimos cargar el video');
      expect(estado.cargas).toBe(1);

      (raiz.querySelector('.fallo button') as HTMLButtonElement).click();
      await estable();
      expect(raiz.querySelector('.fallo')).toBeNull();
      expect(estado.cargas).toBe(2);
      cargarVideo(video);
      expect(estado.tiempo).toBe(40);
    });

    it('si no se puede comprobar la sesión, lo dice', async () => {
      comprobar.mockRejectedValue(new HttpErrorResponse({ status: 0 }));
      const raiz = await crear();
      cargarVideo(video);
      video.dispatchEvent(new Event('error'));
      await estable();

      expect(raiz.querySelector('.fallo')?.getAttribute('role')).toBe('alert');
      expect(estado.cargas).toBe(0);
    });

    it('al dar play tras una pausa larga comprueba la sesión antes de que el video la necesite', async () => {
      await crear();
      cargarVideo(video);
      await video.play();
      expect(comprobar).not.toHaveBeenCalled();
      pausarVideo(estado, video);

      vi.advanceTimersByTime(PAUSA_LARGA_MS + 1000);
      await video.play();
      await estable();

      expect(comprobar).toHaveBeenCalledTimes(1);
    });
  });

  it('sin problemas de accesibilidad (también con el aviso de retomar y el de fallo)', async () => {
    const raiz = await crear({ progreso: progreso({ video_posicion_seg: 120 }) });
    cargarVideo(video);
    comprobar.mockRejectedValue(new HttpErrorResponse({ status: 0 }));
    video.dispatchEvent(new Event('error'));
    await estable();

    expect(raiz.querySelector('.retomado')).not.toBeNull();
    expect(raiz.querySelector('.fallo')).not.toBeNull();
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });
});
