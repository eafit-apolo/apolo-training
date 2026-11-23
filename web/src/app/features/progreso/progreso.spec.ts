import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import {
  graduacionDeEjemplo,
  labsDeEjemplo,
  modulosDeEjemplo,
  progresoDeEjemplo,
} from '../../../testing/progreso';
import {
  ANA,
  CARLA,
  borrarCookies,
  botonCon,
  entrarComo,
  errorApi,
  escribir,
  ponerCsrf,
} from '../../../testing/sesion';
import { contenidoDePrueba } from '../../../testing/contenido';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { IdiomaService } from '../../core/i18n/idioma';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { Usuario } from '../../core/sesion/sesion';
import type { MiProgresoApi } from './datos';
import {
  cifrasDe,
  faltasDeGraduacion,
  haceCuanto,
  leccionesDePracticas,
  numeroDeLeccion,
  sincronizacionAtrasada,
} from './datos';

const MIN = 60_000;

describe('Mi progreso: cálculos', () => {
  it('cada práctica va con la primera lección que la nombra y su número', () => {
    const modulos = modulosDeEjemplo();
    const mapa = leccionesDePracticas(modulos);
    expect([...mapa.keys()]).toEqual(['conexion', 'terminal']);
    expect(mapa.get('conexion')).toEqual({
      modulo: 'm01',
      moduloNumero: 1,
      slug: 'ssh',
      titulo: 'Conectarse por SSH',
      numero: '1.1',
      bloqueada: false,
    });
    expect(mapa.get('terminal')?.bloqueada).toBe(true);

    // Si dos lecciones nombran la misma práctica, manda la primera.
    const repetida = modulosDeEjemplo();
    const otra = { ...repetida[2].lecciones[0], practicas: ['conexion' as const] };
    repetida[2] = { ...repetida[2], lecciones: [otra] };
    expect(leccionesDePracticas(repetida).get('conexion')?.modulo).toBe('m01');
  });

  it('numera la lección por su posición en el módulo', () => {
    const modulos = modulosDeEjemplo();
    const dos = { ...modulos[1], lecciones: [modulos[1].lecciones[0], modulos[2].lecciones[0]] };
    expect(numeroDeLeccion([dos], 'm01', 'terminal')).toBe('1.2');
    expect(numeroDeLeccion(modulos, 'm01', 'no-existe')).toBeNull();
    expect(numeroDeLeccion(modulos, 'm09', 'ssh')).toBeNull();
  });

  it('cuenta módulos completos, prácticas aprobadas y el estado de la graduación', () => {
    expect(cifrasDe(progresoDeEjemplo())).toEqual({
      avance: 33,
      modulosCompletos: 1,
      modulos: 3,
      practicasAprobadas: 1,
      practicas: 7,
      graduacion: 'sin_enviar',
    });
    const rechazada = progresoDeEjemplo({
      graduacion: graduacionDeEjemplo({ estado: 'rechazada' }),
    });
    expect(cifrasDe(rechazada).graduacion).toBe('rechazada');
  });

  it('la sincronización se atrasa a los 15 minutos, o cuando lo dice la API', () => {
    const ahora = Date.parse('2026-11-23T15:00:00Z');
    const hace = (m: number) => new Date(ahora - m * MIN).toISOString();
    expect(sincronizacionAtrasada(hace(15), false, ahora)).toBe(false);
    expect(sincronizacionAtrasada(hace(16), false, ahora)).toBe(true);
    expect(sincronizacionAtrasada(hace(1), true, ahora)).toBe(true);
    // Sin ningún reporte no hay atraso (la V-05 todavía no manda).
    expect(sincronizacionAtrasada(null, false, ahora)).toBe(false);
  });

  it('dice hace cuánto en minutos, horas o días, nunca en el futuro', () => {
    const ahora = Date.parse('2026-11-23T15:00:00Z');
    const hace = (m: number) => new Date(ahora - m * MIN).toISOString();
    expect(haceCuanto(hace(3), ahora)).toEqual({ valor: -3, unidad: 'minute' });
    expect(haceCuanto(hace(59), ahora)).toEqual({ valor: -59, unidad: 'minute' });
    expect(haceCuanto(hace(61), ahora)).toEqual({ valor: -1, unidad: 'hour' });
    expect(haceCuanto(hace(26 * 60), ahora)).toEqual({ valor: -1, unidad: 'day' });
    expect(haceCuanto(hace(-2), ahora).valor).toBe(-0);
  });

  it('revisa el JobID y la salida como la API', () => {
    expect(faltasDeGraduacion('', '')).toEqual(['jobid', 'salida']);
    expect(faltasDeGraduacion('  ', ' \n')).toEqual(['jobid', 'salida']);
    expect(faltasDeGraduacion('12a', 'ok')).toEqual(['jobidInvalido']);
    expect(faltasDeGraduacion('12_', 'ok')).toEqual(['jobidInvalido']);
    expect(faltasDeGraduacion(' 1234 ', 'ok')).toEqual([]);
    expect(faltasDeGraduacion('1234_5', 'ok')).toEqual([]);
    expect(faltasDeGraduacion('1', 'x'.repeat(4000))).toEqual([]);
    expect(faltasDeGraduacion('1', 'x'.repeat(4001))).toEqual(['salidaLarga']);
    // Caracteres, no unidades UTF-16 (como Python).
    expect(faltasDeGraduacion('1', '😀'.repeat(4000))).toEqual([]);
  });
});

describe('Mi progreso (pantalla 04)', () => {
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
      ],
    });
    api = TestBed.inject(HttpTestingController);
    ponerCsrf('csrf-1');
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
    vi.useRealTimers();
  });

  const pendientes = () => new Promise((r) => setTimeout(r));

  async function abrir(datos: MiProgresoApi | null = progresoDeEjemplo(), usuario: Usuario = ANA) {
    entrarComo(usuario);
    const harness = await RouterTestingHarness.create('/mi-progreso');
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    if (datos) {
      responder(datos);
      await listo();
    }
    return { raiz, listo, harness };
  }

  function responder(datos: MiProgresoApi, idioma = 'es') {
    const pedido = api.expectOne((r) => r.url === '/api/me/progreso');
    expect(pedido.request.method).toBe('GET');
    expect(pedido.request.params.get('lang')).toBe(idioma);
    pedido.flush(datos);
  }

  /** El texto visible, con un espacio entre elementos (como lo lee un lector de pantalla). */
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
  const cifras = (raiz: HTMLElement) =>
    Array.from(raiz.querySelectorAll('.cifras li')).map((li) => texto(li));
  const practicas = (raiz: HTMLElement) =>
    Array.from(raiz.querySelectorAll('.practica')).map((li) => texto(li));
  const anuncio = (raiz: HTMLElement) => texto(raiz.querySelector('[aria-live]'));
  const alerta = (raiz: HTMLElement) => texto(raiz.querySelector('[role=alert]'));

  it('muestra las cifras, el siguiente paso, los módulos y las siete prácticas', async () => {
    const { raiz } = await abrir();
    expect(texto(raiz.querySelector('h1'))).toBe('Mi progreso');
    expect(texto(raiz.querySelector('.perfil'))).toBe(
      'Curso de inducción a Apolo · tu perfil: Apolo II',
    );
    expect(cifras(raiz)).toEqual([
      'Avance 33 %',
      'Módulos 1 de 3',
      'Prácticas 1 de 7',
      'Graduación Sin enviar',
    ]);
    expect(texto(raiz.querySelector('.paso-principal'))).toBe(
      'Sigue con la lección 1.1 · Conectarse por SSH',
    );
    expect(botonCon(raiz, 'Ir a la lección').getAttribute('href')).toBe(
      '/cursos/induccion/m01/ssh',
    );
    expect(raiz.querySelectorAll('.modulo')).toHaveLength(3);
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('DoD 1: las siete prácticas con su estado, JobID, fecha, detalle y su lección', async () => {
    const { raiz } = await abrir();
    const lista = practicas(raiz);
    expect(lista).toHaveLength(7);
    expect(lista[0]).toMatch(/^Conexión Aprobada .*Lección 1\.1 · Conectarse por SSH$/);
    expect(lista[1]).toBe('Terminal Sin intentar Lección 2.1 · Comandos básicos de Linux');
    expect(lista[4]).toMatch(/^Memoria Intentada JobID 1042 .* OUT_OF_MEMORY con --mem=1G$/);
    expect(lista.slice(2).map((p) => p?.split(' ').slice(0, 3).join(' '))).toEqual([
      'Archivos Sin intentar',
      'Módulos Sin intentar',
      'Memoria Intentada JobID',
      'Núcleos Sin intentar',
      'Paralelo Sin intentar',
    ]);
    // La lección de la práctica de un módulo abierto es un enlace; la de uno
    // bloqueado, no (un estudiante no la puede abrir).
    const enlaces = Array.from(raiz.querySelectorAll('.practica-leccion a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(enlaces).toEqual(['/cursos/induccion/m01/ssh']);
  });

  it('una instructora abre también las lecciones de los módulos bloqueados', async () => {
    const { raiz } = await abrir(progresoDeEjemplo(), CARLA);
    const enlaces = Array.from(raiz.querySelectorAll('.practica-leccion a')).map((a) =>
      a.getAttribute('href'),
    );
    expect(enlaces).toEqual(['/cursos/induccion/m01/ssh', '/cursos/induccion/m02/terminal']);
    expect(raiz.querySelector('.modulo-bloqueado .lecciones a')?.getAttribute('href')).toBe(
      '/cursos/induccion/m02/terminal',
    );
  });

  it('cada módulo se despliega con sus lecciones, el video y el mejor puntaje', async () => {
    const { raiz } = await abrir();
    const modulos = Array.from(raiz.querySelectorAll<HTMLDetailsElement>('details.modulo'));
    expect(modulos.map((m) => texto(m.querySelector('summary')))).toEqual([
      '0 · Bienvenida Lecciones: 1 de 1 Completo',
      '1 · Conexión Lecciones: 0 de 1 En curso',
      '2 · Terminal y Linux Lecciones: 0 de 1 Bloqueado',
    ]);
    expect(modulos.every((m) => !m.open)).toBe(true);
    expect(texto(modulos[0].querySelector('.lecciones li'))).toBe(
      '0.1 · Bienvenida al curso Completa Video visto Quiz aprobado · 100 %',
    );
    expect(texto(modulos[1].querySelector('.lecciones li'))).toBe(
      '1.1 · Conectarse por SSH Pendiente Quiz sin aprobar · mejor 50 % Práctica: Conexión',
    );
    // Un estudiante no tiene enlace a una lección de un módulo bloqueado.
    expect(modulos[2].querySelector('.lecciones a')).toBeNull();
    expect(texto(modulos[2].querySelector('.lecciones li'))).toBe(
      '2.1 · Comandos básicos de Linux Pendiente Práctica: Terminal',
    );
  });

  describe('sincronización', () => {
    it('dice la hora de la última y hace cuánto', async () => {
      const { raiz } = await abrir();
      expect(texto(raiz.querySelector('.sincronizacion'))).toMatch(
        /^Última sincronización: .+ \(hace 3 minutos\)$/,
      );
      expect(raiz.querySelector('.aviso-atraso')).toBeNull();
    });

    it('DoD 2: con más de 15 minutos avisa que el retraso no es del usuario', async () => {
      const datos = progresoDeEjemplo({
        ultima_sincronizacion: new Date(Date.now() - 20 * MIN).toISOString(),
        sincronizacion_atrasada: true,
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.aviso-atraso'))).toMatch(
        /^La VM de práctica no envía resultados desde .+: tus prácticas pueden tardar en aparecer aquí\. No es un error tuyo y no tienes que repetirlas\.$/,
      );
      expect(texto(raiz.querySelector('.sincronizacion'))).toContain('(hace 20 minutos)');
      expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
    });

    it('con la página abierta, el aviso aparece solo cuando el reporte envejece', async () => {
      vi.useFakeTimers({ toFake: ['setInterval', 'Date'] });
      vi.setSystemTime(Date.parse('2026-11-23T15:00:00Z'));
      const datos = progresoDeEjemplo({
        ultima_sincronizacion: '2026-11-23T14:50:00Z',
        sincronizacion_atrasada: false,
      });
      const { raiz, listo } = await abrir(datos);
      expect(raiz.querySelector('.aviso-atraso')).toBeNull();
      expect(texto(raiz.querySelector('.sincronizacion'))).toContain('(hace 10 minutos)');

      vi.advanceTimersByTime(6 * MIN);
      await listo();
      expect(texto(raiz.querySelector('.sincronizacion'))).toContain('(hace 16 minutos)');
      expect(raiz.querySelector('.aviso-atraso')).not.toBeNull();
    });

    it('si la VM nunca reportó, lo dice sin alarmar', async () => {
      const datos = progresoDeEjemplo({
        ultima_sincronizacion: null,
        sincronizacion_atrasada: false,
        labs: labsDeEjemplo(),
      });
      const { raiz } = await abrir(datos);
      expect(raiz.querySelector('.sincronizacion')).toBeNull();
      expect(raiz.querySelector('.aviso-atraso')).toBeNull();
      expect(raiz.textContent).toContain('La VM de práctica todavía no ha enviado resultados.');
      expect(practicas(raiz).every((p) => p?.includes('Sin intentar'))).toBe(true);
    });
  });

  describe('siguiente paso', () => {
    it('una práctica: lleva a la lección que la explica', async () => {
      const datos = progresoDeEjemplo({
        siguiente_paso: { tipo: 'laboratorio', leccion: null, lab: 'conexion' },
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.paso-texto'))).toBe(
        'Siguiente paso Haz la práctica «Conexión» en la VM de práctica Los pasos están en la lección 1.1 · Conectarse por SSH.',
      );
      expect(botonCon(raiz, 'Ir a la lección').getAttribute('href')).toBe(
        '/cursos/induccion/m01/ssh',
      );
    });

    it('una práctica que ninguna lección nombra: el comando para verificarla', async () => {
      const datos = progresoDeEjemplo({
        siguiente_paso: { tipo: 'laboratorio', leccion: null, lab: 'paralelo' },
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.paso-texto'))).toBe(
        'Siguiente paso Haz la práctica «Paralelo» en la VM de práctica Cuando la hagas, verifícala en la VM con apolo-training verificar paralelo',
      );
      expect(() => botonCon(raiz, 'Ir a la lección')).toThrow();
    });

    it('la graduación: el botón lleva el foco a esa sección', async () => {
      const datos = progresoDeEjemplo({
        siguiente_paso: { tipo: 'graduacion', leccion: null, lab: null },
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.paso-texto'))).toBe(
        'Siguiente paso Envía tu graduación Corre el trabajo de graduación en Apolo II y pega aquí el resultado.',
      );
      botonCon(raiz, 'Ir a la graduación').click();
      expect(document.activeElement).toBe(raiz.querySelector('#graduacion-titulo'));
    });

    it.each([
      [
        'graduacion',
        graduacionDeEjemplo({ estado: 'rechazada', comentario: 'Falta la salida' }),
        'Envía tu graduación Tu graduación fue rechazada: lee el comentario del instructor y vuelve a enviarla.',
      ],
      [
        'esperar_revision',
        graduacionDeEjemplo(),
        'Tu graduación está en revisión Un instructor la revisará. Mientras tanto puedes repasar cualquier lección.',
      ],
      [
        'esperar_qos',
        graduacionDeEjemplo({ estado: 'aprobada' }),
        '¡Aprobaste el curso! Falta que un administrador active tu cuenta normal (la QOS) en Apolo II.',
      ],
      [
        'terminado',
        graduacionDeEjemplo({ estado: 'aprobada', qos_aplicada_en: '2026-11-24T15:00:00Z' }),
        '¡Terminaste el curso! Tu cuenta de Apolo II ya tiene la QOS normal: puedes enviar trabajos sin los límites del curso.',
      ],
    ] as const)('%s', async (tipo, graduacion, esperado) => {
      const datos = progresoDeEjemplo({
        graduacion,
        siguiente_paso: { tipo, leccion: null, lab: null },
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.paso-texto'))).toBe(`Siguiente paso ${esperado}`);
    });

    it('sin curso publicado lo dice', async () => {
      const datos = progresoDeEjemplo({
        curso: null,
        avance_pct: 0,
        lecciones_total: 0,
        lecciones_completas: 0,
        modulos: [],
        siguiente_paso: { tipo: 'terminado', leccion: null, lab: null },
      });
      const { raiz } = await abrir(datos);
      expect(texto(raiz.querySelector('.paso-texto'))).toBe(
        'Siguiente paso Todavía no hay un curso publicado.',
      );
      expect(raiz.querySelector('.modulo')).toBeNull();
      expect(practicas(raiz)).toHaveLength(7);
    });
  });

  describe('graduación', () => {
    const enviar = (raiz: HTMLElement) =>
      raiz.querySelector<HTMLButtonElement>('at-graduacion button[type=submit]')!.click();

    it('sin enviar: los pasos de su clúster y el formulario', async () => {
      const { raiz } = await abrir();
      const pasos = Array.from(raiz.querySelectorAll('.pasos li')).map((li) => texto(li));
      expect(pasos[0]).toBe(
        'Conéctate por SSH a Apolo II, tu clúster real (no a la VM de práctica).',
      );
      expect(pasos[2]).toBe('Envía el trabajo de graduación: sbatch -p learning graduacion.sh');
      expect(raiz.querySelector('input[name=jobid]')).not.toBeNull();
      expect(raiz.querySelector('textarea[name=salida]')).not.toBeNull();
      expect(raiz.querySelector('details.enviado')).toBeNull();
    });

    it('en Apolo III la partición es bigmem', async () => {
      const { raiz } = await abrir(progresoDeEjemplo(), CARLA);
      expect(texto(raiz.querySelectorAll('.pasos li')[2])).toBe(
        'Envía el trabajo de graduación: sbatch -p bigmem graduacion.sh',
      );
    });

    it('sin datos no llama a la API y lleva el foco al primer campo', async () => {
      const { raiz, listo } = await abrir();
      enviar(raiz);
      await listo();
      expect(raiz.textContent).toContain('Escribe el JobID.');
      expect(raiz.textContent).toContain('Pega la salida del verificador.');
      expect(document.activeElement).toBe(raiz.querySelector('input[name=jobid]'));
      api.expectNone('/api/me/graduacion');

      escribir(raiz, 'input[name=jobid]', '12a');
      escribir(raiz, 'textarea[name=salida]', 'salida');
      await listo();
      enviar(raiz);
      await listo();
      expect(raiz.textContent).toContain('El JobID son solo números');
      api.expectNone('/api/me/graduacion');
    });

    it('la envía con CSRF, recarga Mi progreso y lo anuncia', async () => {
      const { raiz, listo } = await abrir();
      escribir(raiz, 'input[name=jobid]', ' 4321 ');
      escribir(raiz, 'textarea[name=salida]', '[APROBADO] graduacion');
      await listo();
      expect(texto(raiz.querySelector('at-graduacion .mat-mdc-form-field-hint-end'))).toBe(
        '21 / 4000',
      );
      enviar(raiz);

      const pedido = api.expectOne('/api/me/graduacion');
      expect(pedido.request.method).toBe('POST');
      expect(pedido.request.body).toEqual({ jobid: '4321', salida: '[APROBADO] graduacion' });
      expect(pedido.request.headers.get('X-CSRF-Token')).toBe('csrf-1');
      pedido.flush(graduacionDeEjemplo(), { status: 201, statusText: 'Created' });
      await listo();

      responder(
        progresoDeEjemplo({
          graduacion: graduacionDeEjemplo(),
          siguiente_paso: { tipo: 'esperar_revision', leccion: null, lab: null },
        }),
      );
      await listo();
      expect(anuncio(raiz)).toBe('Enviamos tu graduación. Un instructor la revisará.');
      expect(raiz.querySelector('input[name=jobid]')).toBeNull();
      expect(cifras(raiz)[3]).toBe('Graduación En revisión');
    });

    it('enviada: se ve lo enviado y «Corregir envío» abre el formulario con esos datos', async () => {
      const { raiz, listo } = await abrir(progresoDeEjemplo({ graduacion: graduacionDeEjemplo() }));
      const panel = raiz.querySelector('at-graduacion')!;
      expect(texto(panel.querySelector('.graduacion-estado'))).toBe('En revisión');
      expect(texto(panel)).toContain('con el JobID 4321. Un instructor la revisará.');
      expect(texto(panel.querySelector('details.enviado pre'))).toContain('[APROBADO] graduacion');
      expect(panel.querySelector('form')).toBeNull();

      botonCon(raiz, 'Corregir envío').click();
      await listo();
      expect(raiz.querySelector<HTMLInputElement>('input[name=jobid]')?.value).toBe('4321');
      expect(raiz.querySelector<HTMLTextAreaElement>('textarea[name=salida]')?.value).toContain(
        'COMPLETED en learning',
      );
      expect(document.activeElement).toBe(raiz.querySelector('input[name=jobid]'));
      expect(botonCon(raiz, 'Enviar de nuevo')).toBeTruthy();

      botonCon(raiz, 'Cancelar').click();
      await listo();
      expect(raiz.querySelector('at-graduacion form')).toBeNull();
    });

    it('rechazada: el comentario del instructor y el formulario abierto, vacío', async () => {
      const { raiz } = await abrir(
        progresoDeEjemplo({
          graduacion: graduacionDeEjemplo({
            estado: 'rechazada',
            revisada_en: '2026-11-23T16:00:00Z',
            comentario: 'El trabajo terminó en FAILED.\nVuelve a correrlo.',
          }),
        }),
      );
      const panel = raiz.querySelector('at-graduacion')!;
      expect(texto(panel.querySelector('.graduacion-estado'))).toBe('Rechazada');
      expect(texto(panel.querySelector('.comentario-rechazo'))).toBe(
        'Comentario del instructor El trabajo terminó en FAILED. Vuelve a correrlo.',
      );
      expect(raiz.querySelector<HTMLInputElement>('input[name=jobid]')?.value).toBe('');
      expect(() => botonCon(raiz, 'Cancelar')).toThrow();
      expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
    });

    it.each([
      [null, 'Falta que un administrador active tu cuenta normal (la QOS) en Apolo II.'],
      ['2026-11-24T15:00:00Z', 'tu cuenta normal (la QOS) en Apolo II está activa.'],
    ])('aprobada (QOS %s): sin formulario ni «Corregir envío»', async (qos, esperado) => {
      const { raiz } = await abrir(
        progresoDeEjemplo({
          graduacion: graduacionDeEjemplo({ estado: 'aprobada', qos_aplicada_en: qos }),
        }),
      );
      const panel = raiz.querySelector('at-graduacion')!;
      expect(texto(panel.querySelector('.graduacion-estado'))).toBe('Aprobada');
      expect(texto(panel)).toContain(esperado);
      expect(panel.querySelector('form')).toBeNull();
      expect(() => botonCon(raiz, 'Corregir envío')).toThrow();
    });

    it.each([
      [422, errorApi('datos_invalidos'), 'La plataforma no aceptó el JobID o la salida.'],
      [500, errorApi('error_interno'), 'si sigue fallando, escribe a apolo@eafit.edu.co.'],
      [0, null, 'Revisa tu conexión (fuera de EAFIT, la VPN)'],
    ])(
      'si la API responde %s, lo dice con el foco en el error',
      async (estado, cuerpo, esperado) => {
        const { raiz, listo } = await abrir();
        escribir(raiz, 'input[name=jobid]', '4321');
        escribir(raiz, 'textarea[name=salida]', 'salida');
        await listo();
        enviar(raiz);
        const pedido = api.expectOne('/api/me/graduacion');
        if (estado === 0) {
          pedido.error(new ProgressEvent('error'));
        } else {
          pedido.flush(cuerpo, { status: estado, statusText: 'Error' });
        }
        await listo();
        expect(alerta(raiz)).toContain(esperado);
        expect(document.activeElement).toBe(raiz.querySelector('at-graduacion [role=alert]'));
        // Lo escrito se conserva para intentarlo de nuevo.
        expect(raiz.querySelector<HTMLInputElement>('input[name=jobid]')?.value).toBe('4321');
      },
    );

    it('409 graduacion_aprobada: recarga y muestra la graduación aprobada', async () => {
      const { raiz, listo } = await abrir(progresoDeEjemplo({ graduacion: graduacionDeEjemplo() }));
      botonCon(raiz, 'Corregir envío').click();
      await listo();
      enviar(raiz);
      api
        .expectOne('/api/me/graduacion')
        .flush(errorApi('graduacion_aprobada'), { status: 409, statusText: 'Conflict' });
      await listo();
      responder(progresoDeEjemplo({ graduacion: graduacionDeEjemplo({ estado: 'aprobada' }) }));
      await listo();
      expect(anuncio(raiz)).toBe('Tu graduación ya estaba aprobada.');
      expect(texto(raiz.querySelector('.graduacion-estado'))).toBe('Aprobada');
      expect(raiz.querySelector('at-graduacion form')).toBeNull();
    });
  });

  describe('recargas', () => {
    it('«Actualizar» vuelve a pedir y lo anuncia', async () => {
      const { raiz, listo } = await abrir();
      botonCon(raiz, 'Actualizar').click();
      await listo();
      expect(botonCon(raiz, 'Actualizando…').getAttribute('aria-disabled')).toBe('true');
      responder(progresoDeEjemplo({ avance_pct: 50 }));
      await listo();
      expect(cifras(raiz)[0]).toBe('Avance 50 %');
      expect(anuncio(raiz)).toBe('Tu progreso está al día.');
    });

    it('al volver a la pestaña vuelve a pedir', async () => {
      const { raiz, listo } = await abrir();
      document.dispatchEvent(new Event('visibilitychange'));
      responder(progresoDeEjemplo({ avance_pct: 67 }));
      await listo();
      expect(cifras(raiz)[0]).toBe('Avance 67 %');
    });

    it('al cambiar el idioma pide en inglés y descarta la respuesta vieja', async () => {
      const { raiz, listo } = await abrir();
      botonCon(raiz, 'Actualizar').click();
      await listo();
      await TestBed.inject(IdiomaService).cambiar('en');
      await listo();
      const [viejo, nuevo] = api.match((r) => r.url === '/api/me/progreso');
      expect(nuevo.request.params.get('lang')).toBe('en');
      nuevo.flush(progresoDeEjemplo({ avance_pct: 40 }));
      viejo.flush(progresoDeEjemplo({ avance_pct: 10 }));
      await listo();
      expect(cifras(raiz)[0]).toBe('Progress 40%');
      expect(texto(raiz.querySelector('h1'))).toBe('My progress');
    });

    it('si falla la primera carga, error con «Reintentar»', async () => {
      const { raiz, listo } = await abrir(null);
      api
        .expectOne('/api/me/progreso?lang=es')
        .flush(errorApi('error_interno'), { status: 500, statusText: 'Error' });
      await listo();
      expect(texto(raiz.querySelector('.error-carga h2'))).toBe('No pudimos cargar tu progreso');
      botonCon(raiz, 'Reintentar').click();
      responder(progresoDeEjemplo());
      await listo();
      expect(raiz.querySelector('.error-carga')).toBeNull();
      expect(cifras(raiz)).toHaveLength(4);
    });

    it('si falla una recarga, conserva lo que había y avisa', async () => {
      const { raiz, listo } = await abrir();
      botonCon(raiz, 'Actualizar').click();
      api
        .expectOne('/api/me/progreso?lang=es')
        .flush(errorApi('error_interno'), { status: 500, statusText: 'Error' });
      await listo();
      expect(alerta(raiz)).toContain('No pudimos actualizar tu progreso');
      expect(cifras(raiz)[0]).toBe('Avance 33 %');
      expect(anuncio(raiz)).toBe('');

      // La siguiente recarga que funciona quita el aviso.
      botonCon(raiz, 'Actualizar').click();
      responder(progresoDeEjemplo());
      await listo();
      expect(alerta(raiz)).toBeUndefined();
      expect(anuncio(raiz)).toBe('Tu progreso está al día.');
    });

    it('si falta traducir parte del curso, lo avisa', async () => {
      const { raiz } = await abrir(progresoDeEjemplo({ fallback: true }));
      expect(raiz.textContent).toContain('Parte del curso todavía no está traducida');
    });
  });
});
