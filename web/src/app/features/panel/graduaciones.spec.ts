import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { contenidoDePrueba } from '../../../testing/contenido';
import { graduacionAdminDeEjemplo, resumenDeEjemplo, sinAnimaciones } from '../../../testing/panel';
import {
  CARLA,
  borrarCookies,
  botonCon,
  entrarComo,
  errorApi,
  ponerCsrf,
} from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { GraduacionAdminApi } from './datos';

describe('Panel: graduaciones', () => {
  let api: HttpTestingController;

  beforeEach(() => {
    borrarCookies();
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
  const ANA = graduacionAdminDeEjemplo();
  const BETO = graduacionAdminDeEjemplo({
    username: 'beto',
    nombre: 'Beto Ejemplo',
    cluster: 'apolo3',
    jobid: '98811',
    labs_aprobados: 3,
    salida_verificador: '[APROBADO] graduacion · Apolo III',
  });

  async function abrir(lista: GraduacionAdminApi[] = [ANA, BETO]) {
    entrarComo(CARLA);
    const harness = await RouterTestingHarness.create('/panel/graduaciones');
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    api.expectOne('/api/panel/resumen?lang=es').flush(resumenDeEjemplo());
    responderLista(lista, 'enviada');
    await listo();
    return { raiz, listo };
  }

  function responderLista(lista: GraduacionAdminApi[], estado: string | null) {
    const pedido = api.expectOne((r) => r.url === '/api/panel/graduaciones');
    expect(pedido.request.params.get('estado')).toBe(estado);
    pedido.flush(lista);
  }

  const texto = (el: Element | null | undefined) => el?.textContent?.replace(/\s+/g, ' ').trim();
  const filas = (raiz: HTMLElement) =>
    Array.from(raiz.querySelectorAll('tbody tr')).map((tr) =>
      Array.from(tr.querySelectorAll('td')).map((td) => texto(td)),
    );
  const comentario = (raiz: HTMLElement) =>
    raiz.querySelector<HTMLTextAreaElement>('.detalle textarea')!;

  function escribir(raiz: HTMLElement, valor: string) {
    const campo = comentario(raiz);
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  }

  it('lista las graduaciones por revisar, de la más vieja a la más nueva', async () => {
    const { raiz } = await abrir();
    const [ana, beto] = filas(raiz);
    expect(ana.slice(0, 4)).toEqual(['ana', 'Ana Ejemplo', 'Apolo II', '55120']);
    expect(ana.slice(5)).toEqual(['7 de 7', 'En revisión', 'Revisar']);
    expect(beto[5]).toBe('3 de 7');
    expect(raiz.querySelector('tbody tr:nth-child(2) .chip-atencion')).not.toBeNull();
    expect(raiz.querySelector('tbody button')?.getAttribute('aria-label')).toBe(
      'Revisar la graduación de ana',
    );
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('el filtro pide por estado, y «Todas» sin estado', async () => {
    const { raiz, listo } = await abrir();
    const filtro = raiz.querySelector<HTMLSelectElement>('.filtros select')!;
    filtro.value = 'rechazada';
    filtro.dispatchEvent(new Event('change'));
    await listo();
    responderLista([], 'rechazada');
    await listo();
    expect(texto(raiz.querySelector('.vacio'))).toBe('No hay graduaciones con ese estado.');
    filtro.value = 'todas';
    filtro.dispatchEvent(new Event('change'));
    await listo();
    responderLista([ANA], null);
    await listo();
    expect(filas(raiz)).toHaveLength(1);
  });

  it('sin graduaciones por revisar lo dice', async () => {
    const { raiz } = await abrir([]);
    expect(texto(raiz.querySelector('.vacio'))).toBe('No hay graduaciones por revisar.');
  });

  it('al elegir una: salida, prácticas que faltan, el sacct para confirmarla y el foco en el título', async () => {
    const { raiz, listo } = await abrir();
    raiz.querySelectorAll<HTMLButtonElement>('tbody button')[1].click();
    await listo();
    const detalle = raiz.querySelector('.detalle')!;
    expect(texto(detalle.querySelector('h2'))).toBe('Graduación de beto · Beto Ejemplo');
    expect(document.activeElement).toBe(detalle.querySelector('h2'));
    expect(texto(detalle.querySelector('pre.salida'))).toBe('[APROBADO] graduacion · Apolo III');
    expect(texto(detalle.querySelector('.aviso'))).toContain('Tiene 3 de 7 prácticas aprobadas');
    expect(texto(detalle.querySelector('at-comando code'))).toBe(
      'sacct -D -j 98811 -u beto -o JobID,JobName,Partition,State,Elapsed',
    );
    expect(texto(detalle)).toContain('Para confirmarla, corre esto en el login de Apolo III:');
    expect(raiz.querySelector('tbody tr.elegida td')?.textContent).toContain('beto');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('rechazar sin comentario no llama a la API: lo pide y lleva el foco al campo', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Revisar').click();
    await listo();
    escribir(raiz, '   ');
    botonCon(raiz, 'Rechazar').click();
    await listo();
    expect(texto(raiz.querySelector('#comentario-error'))).toBe(
      'Para rechazarla, escribe qué le falta.',
    );
    expect(comentario(raiz).getAttribute('aria-invalid')).toBe('true');
    expect(comentario(raiz).getAttribute('aria-describedby')).toBe('comentario-error');
    expect(document.activeElement).toBe(comentario(raiz));
    // Al escribir, el error se va.
    escribir(raiz, 'Falta la práctica de paralelo');
    await listo();
    expect(raiz.querySelector('#comentario-error')).toBeNull();
  });

  it('aprobar: manda la decisión, recarga la lista y la cuenta, y lo anuncia', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Revisar').click();
    await listo();
    botonCon(raiz, 'Aprobar').click();
    await listo();
    const pedido = api.expectOne('/api/panel/graduaciones/ana/revision');
    expect(pedido.request.method).toBe('POST');
    expect(pedido.request.headers.get('X-CSRF-Token')).toBe('csrf-1');
    expect(pedido.request.body).toEqual({ decision: 'aprobar', comentario: null });
    pedido.flush({ ...ANA, estado: 'aprobada' });
    await listo();
    responderLista([BETO], 'enviada');
    await listo();
    api
      .expectOne('/api/panel/resumen?lang=es')
      .flush(resumenDeEjemplo({ graduaciones_por_revisar: 1 }));
    await listo();
    expect(raiz.querySelector('.detalle')).toBeNull();
    expect(filas(raiz).map((f) => f[0])).toEqual(['beto']);
    expect(texto(raiz.querySelector('[aria-live]'))).toBe('Aprobaste la graduación de ana.');
  });

  it('rechazar con comentario lo manda recortado', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Revisar').click();
    await listo();
    escribir(raiz, '  Corre la graduación en learning, no en longjobs  ');
    botonCon(raiz, 'Rechazar').click();
    await listo();
    const pedido = api.expectOne('/api/panel/graduaciones/ana/revision');
    expect(pedido.request.body).toEqual({
      decision: 'rechazar',
      comentario: 'Corre la graduación en learning, no en longjobs',
    });
    pedido.flush({ ...ANA, estado: 'rechazada' });
    await listo();
    responderLista([BETO], 'enviada');
    await listo();
    api.expectOne('/api/panel/resumen?lang=es').flush(resumenDeEjemplo());
    await listo();
    expect(texto(raiz.querySelector('[aria-live]'))).toContain('Rechazaste la graduación de ana.');
  });

  it('si otra persona ya la revisó (409), avisa y recarga', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Revisar').click();
    await listo();
    botonCon(raiz, 'Aprobar').click();
    await listo();
    api
      .expectOne('/api/panel/graduaciones/ana/revision')
      .flush(errorApi('sin_graduacion_pendiente'), { status: 409, statusText: 'Conflict' });
    await listo();
    responderLista([BETO], 'enviada');
    await listo();
    api.expectOne('/api/panel/resumen?lang=es').flush(resumenDeEjemplo());
    await listo();
    expect(texto(raiz.querySelector('[role=status]'))).toContain(
      'Esa graduación ya no está por revisar',
    );
    expect(raiz.querySelector('.detalle')).toBeNull();
  });

  it('sin conexión: el error queda en el detalle y conserva el comentario', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Revisar').click();
    await listo();
    escribir(raiz, 'Revisa la partición');
    botonCon(raiz, 'Rechazar').click();
    await listo();
    api.expectOne('/api/panel/graduaciones/ana/revision').error(new ProgressEvent('error'));
    await listo();
    expect(texto(raiz.querySelector('.detalle [role=alert]'))).toContain(
      'No pudimos comunicarnos con la plataforma',
    );
    expect(comentario(raiz).value).toBe('Revisa la partición');
  });

  it('una ya revisada se ve sin botones, con quién la revisó y el comentario', async () => {
    const { raiz, listo } = await abrir([
      graduacionAdminDeEjemplo({
        estado: 'rechazada',
        revisada_por: 'carla',
        revisada_en: '2026-11-26T16:00:00Z',
        comentario: 'Falta paralelo',
      }),
    ]);
    botonCon(raiz, 'Ver').click();
    await listo();
    const detalle = raiz.querySelector('.detalle')!;
    expect(detalle.querySelector('textarea')).toBeNull();
    expect(texto(detalle)).toMatch(/Revisada por carla el .*\./);
    expect(texto(detalle.querySelector('.comentario'))).toBe('Comentario Falta paralelo');
  });
});
