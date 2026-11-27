import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { contenidoDePrueba } from '../../../testing/contenido';
import { resumenDeEjemplo, sinAnimaciones } from '../../../testing/panel';
import {
  ANA,
  CARLA,
  DIEGO,
  borrarCookies,
  botonCon,
  entrarComo,
  ponerCsrf,
} from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { IdiomaService } from '../../core/i18n/idioma';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { Usuario } from '../../core/sesion/sesion';
import type { ResumenPanelApi } from './datos';
import { comandoConfirmar, duracion, mayorSalto, revisarArchivo, tamano, urlCsv } from './datos';

const MB = 1024 ** 2;

function archivo(nombre: string, bytes: number, tipo = ''): File {
  const f = new File([''], nombre, { type: tipo });
  Object.defineProperty(f, 'size', { value: bytes });
  return f;
}

describe('Panel: cálculos', () => {
  it('arma la URL del CSV de todos o de un clúster', () => {
    expect(urlCsv(null)).toBe('/api/panel/export/progreso.csv');
    expect(urlCsv('apolo3')).toBe('/api/panel/export/progreso.csv?cluster=apolo3');
  });

  it('el sacct para confirmar busca el JobID de ese usuario con -D', () => {
    expect(comandoConfirmar({ jobid: '55120', username: 'ana' })).toBe(
      'sacct -D -j 55120 -u ana -o JobID,JobName,Partition,State,Elapsed',
    );
  });

  it('el mayor salto es la mayor caída frente al módulo anterior (al primero llegan todos)', () => {
    const modulos = [
      { numero: 0, titulo: 'Bienvenida', completos: 8 },
      { numero: 1, titulo: 'Conexión', completos: 7 },
      { numero: 5, titulo: 'Trabajos', completos: 3 },
      { numero: 6, titulo: 'Núcleos', completos: 2 },
    ];
    expect(mayorSalto(modulos, 8)).toEqual({
      numero: 5,
      titulo: 'Trabajos',
      antes: 7,
      despues: 3,
    });
    // Nadie empezó: la caída está en el primero.
    expect(
      mayorSalto(
        modulos.map((m) => ({ ...m, completos: 0 })),
        4,
      )?.numero,
    ).toBe(0);
    // Con un empate, el primero.
    expect(
      mayorSalto(
        [
          { numero: 0, titulo: 'A', completos: 2 },
          { numero: 1, titulo: 'B', completos: 0 },
        ],
        4,
      )?.numero,
    ).toBe(0);
    // Nadie se queda, o no hay estudiantes: sin mensaje.
    expect(
      mayorSalto(
        modulos.map((m) => ({ ...m, completos: 8 })),
        8,
      ),
    ).toBeNull();
    expect(mayorSalto([], 0)).toBeNull();
  });

  it('escribe la duración como m:ss o h:mm:ss', () => {
    expect(duracion(245)).toBe('4:05');
    expect(duracion(59.6)).toBe('1:00');
    expect(duracion(3750)).toBe('1:02:30');
    expect(duracion(0)).toBe('0:00');
  });

  it('revisa la extensión y el tamaño antes de subir', () => {
    expect(revisarArchivo('video', archivo('m05.mp4', 200 * MB))).toBeNull();
    expect(revisarArchivo('video', archivo('sin-extension', 5 * MB, 'video/mp4'))).toBeNull();
    expect(revisarArchivo('video', archivo('m05.MOV', 5 * MB, 'video/quicktime'))).toBe('noMp4');
    expect(revisarArchivo('video', archivo('m05.mp4', 2 * 1024 * MB + 1))).toBe('muyGrande');
    expect(revisarArchivo('video', archivo('m05.mp4', 2 * 1024 * MB))).toBeNull();
    expect(revisarArchivo('es', archivo('es.vtt', 2000))).toBeNull();
    expect(revisarArchivo('en', archivo('en.srt', 2000))).toBe('noVtt');
    expect(revisarArchivo('es', archivo('es.vtt', MB + 1))).toBe('muyGrande');
    expect(revisarArchivo('es', archivo('es.vtt', 0))).toBe('vacio');
  });

  it('elige la unidad del tamaño', () => {
    expect(tamano(512)).toEqual({ valor: 512, unidad: 'byte' });
    expect(tamano(144 * 1024)).toEqual({ valor: 144, unidad: 'kilobyte' });
    expect(tamano(124.4 * MB)).toEqual({ valor: 124, unidad: 'megabyte' });
    expect(tamano(1.55 * 1024 * MB)).toEqual({ valor: 1.6, unidad: 'gigabyte' });
  });
});

describe('Panel de instructor (pantalla 05)', () => {
  let api: HttpTestingController;

  beforeEach(() => {
    borrarCookies();
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(withInterceptors([interceptorSesion])),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
        sinAnimaciones(),
      ],
    });
    api = TestBed.inject(HttpTestingController);
    ponerCsrf('csrf-1');
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
  });

  const pendientes = () => new Promise((r) => setTimeout(r));

  async function abrir(
    resumen: ResumenPanelApi | null = resumenDeEjemplo(),
    usuario: Usuario = CARLA,
    ruta = '/panel',
  ) {
    entrarComo(usuario);
    const harness = await RouterTestingHarness.create(ruta);
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    if (resumen) {
      responderResumen(resumen);
      await listo();
    }
    return { raiz, listo, harness };
  }

  function responderResumen(resumen: ResumenPanelApi, idioma = 'es') {
    const pedido = api.expectOne((r) => r.url === '/api/panel/resumen');
    expect(pedido.request.params.get('lang')).toBe(idioma);
    pedido.flush(resumen);
  }

  const texto = (el: Element | null | undefined) => {
    if (!el) {
      return undefined;
    }
    const partes: string[] = [];
    const recorrido = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (recorrido.nextNode()) {
      partes.push(recorrido.currentNode.textContent ?? '');
    }
    return partes.join(' ').replace(/\s+/g, ' ').trim();
  };
  const pestanas = (raiz: HTMLElement) =>
    Array.from(raiz.querySelectorAll('at-pestanas a')).map((a) => ({
      texto: texto(a),
      actual: a.getAttribute('aria-current'),
    }));

  it('el resumen: cifras, módulos con el mayor salto y lo que está por hacer', async () => {
    const { raiz } = await abrir();
    expect(texto(raiz.querySelector('h1'))).toBe('Panel del curso');
    expect(Array.from(raiz.querySelectorAll('.cifras li')).map((li) => texto(li))).toEqual([
      'Activos 8',
      'Sin empezar 1',
      'En curso 6',
      'Aprobados 1',
      expect.stringMatching(/^Sincronización hace 2 minutos$/),
    ]);
    expect(Array.from(raiz.querySelectorAll('.barras li')).map((li) => texto(li))).toEqual([
      '0 · Bienvenida 7 7 de 8 estudiantes activos',
      '1 · Conexión 6 6 de 8 estudiantes activos',
      '2 · Terminal y Linux 3 3 de 8 estudiantes activos',
    ]);
    expect(texto(raiz.querySelector('.salto'))).toBe(
      'Dónde se atascan: el mayor salto está en el módulo 2 · Terminal y Linux (de 6 a 3).',
    );
    const barras = Array.from(raiz.querySelectorAll<HTMLElement>('.barra-relleno'));
    expect(barras.map((b) => b.style.width)).toEqual(['88%', '75%', '38%']);
    expect(botonCon(raiz, 'Revisar').getAttribute('href')).toBe('/panel/graduaciones');
    // Una instructora no ve el enlace a Administración: la QOS la aplica un admin.
    expect(raiz.querySelector('a[href="/admin/qos"]')).toBeNull();
    expect(texto(raiz.querySelector('.por-hacer-nota'))).toBe(
      'La QOS la aplica un admin en el clúster real.',
    );
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('las pestañas marcan la actual y cuentan las graduaciones por revisar', async () => {
    const { raiz } = await abrir();
    expect(pestanas(raiz)).toEqual([
      { texto: 'Resumen', actual: 'page' },
      { texto: 'Graduaciones 2 2 por revisar', actual: null },
      { texto: 'Videos', actual: null },
    ]);
  });

  it('un admin ve el acceso a los aprobados pendientes de QOS', async () => {
    const { raiz } = await abrir(resumenDeEjemplo(), DIEGO);
    expect(botonCon(raiz, 'Ir a Administración').getAttribute('href')).toBe('/admin/qos');
  });

  it('sin estudiantes lo dice, y sin curso publicado no hay barras', async () => {
    const vacio = resumenDeEjemplo({
      estudiantes_activos: 0,
      sin_empezar: 0,
      en_curso: 0,
      aprobados: 0,
      graduaciones_por_revisar: 0,
      aprobados_pendientes_qos: 0,
      ultima_sincronizacion: null,
      avance_por_modulo: [{ numero: 0, titulo: 'Bienvenida', completos: 0 }],
    });
    const { raiz } = await abrir(vacio);
    expect(texto(raiz.querySelector('.cifras li:last-child'))).toBe('Sincronización Nunca');
    expect(raiz.textContent).toContain('Todavía no hay estudiantes activos');
    expect(raiz.querySelector('.salto')).toBeNull();
    expect(Array.from(raiz.querySelectorAll('at-pestanas .cuenta'))).toHaveLength(0);
    expect(() => botonCon(raiz, 'Revisar')).toThrow();
  });

  it('al cambiar el idioma vuelve a pedir el resumen en ese idioma', async () => {
    const { listo } = await abrir();
    await TestBed.inject(IdiomaService).cambiar('en');
    await listo();
    responderResumen(resumenDeEjemplo(), 'en');
    await listo();
  });

  it('«Actualizar» vuelve a pedir y lo anuncia', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Actualizar').click();
    await listo();
    responderResumen(resumenDeEjemplo({ aprobados: 2 }));
    await listo();
    expect(texto(raiz.querySelector('.cifras li:nth-child(4)'))).toBe('Aprobados 2');
    expect(texto(raiz.querySelector('[aria-live]'))).toBe('Panel actualizado.');
  });

  it('si la API falla, lo dice y se puede reintentar', async () => {
    const { raiz, listo } = await abrir(null);
    api.expectOne('/api/panel/resumen?lang=es').flush(null, { status: 500, statusText: 'Error' });
    await listo();
    expect(texto(raiz.querySelector('[role=alert] h2'))).toBe('No pudimos cargar el panel');
    botonCon(raiz, 'Reintentar').click();
    await listo();
    responderResumen(resumenDeEjemplo());
    await listo();
    expect(raiz.querySelectorAll('.cifras li')).toHaveLength(5);
  });

  it('«Exportar CSV» comprueba la sesión y baja el CSV del clúster elegido', async () => {
    const { raiz, listo } = await abrir();
    const clics: string[] = [];
    const espia = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clics.push(this.getAttribute('href') ?? '');
    });
    const select = raiz.querySelector<HTMLSelectElement>('.exportar select')!;
    select.value = 'apolo3';
    select.dispatchEvent(new Event('change'));
    botonCon(raiz, 'Exportar CSV').click();
    await listo();
    api.expectOne('/api/me').flush(CARLA);
    await listo();
    expect(clics).toEqual(['/api/panel/export/progreso.csv?cluster=apolo3']);

    // Sin conexión: no baja nada y lo dice.
    botonCon(raiz, 'Exportar CSV').click();
    await listo();
    api.expectOne('/api/me').error(new ProgressEvent('error'));
    await listo();
    expect(clics).toHaveLength(1);
    expect(texto(raiz.querySelector('.cabecera ~ [role=alert]'))).toContain(
      'No pudimos preparar el CSV',
    );
    espia.mockRestore();
  });

  it('DoD 2: un estudiante no entra al panel ni a la administración', async () => {
    entrarComo(ANA);
    const harness = await RouterTestingHarness.create('/panel');
    expect(TestBed.inject(Router).url).toBe('/cursos');
    await harness.navigateByUrl('/admin');
    expect(TestBed.inject(Router).url).toBe('/cursos');
    expect(harness.routeNativeElement?.querySelector('at-panel')).toBeFalsy();
  });

  it('DoD 2: una instructora entra al panel, pero no a la administración', async () => {
    const { harness } = await abrir();
    expect(harness.routeNativeElement?.querySelector('h1')?.textContent).toContain('Panel');
    await harness.navigateByUrl('/admin/usuarios');
    expect(TestBed.inject(Router).url).toBe('/cursos');
  });
});
