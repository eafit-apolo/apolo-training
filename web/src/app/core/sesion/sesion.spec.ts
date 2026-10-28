import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import {
  ANA,
  BRUNO,
  borrarCookies,
  entrarComo,
  errorApi,
  ponerCsrf,
} from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { IdiomaService } from '../i18n/idioma';
import { interceptorSesion } from './interceptor';
import { SesionService } from './sesion';

describe('SesionService', () => {
  let sesion: SesionService;
  let api: HttpTestingController;

  beforeEach(() => {
    borrarCookies();
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(withInterceptors([interceptorSesion])),
        provideHttpClientTesting(),
        provideRouter([{ path: '**', children: [] }]),
      ],
    });
    sesion = TestBed.inject(SesionService);
    api = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
  });

  /** Deja correr las promesas pendientes (el `await` que sigue a cada respuesta). */
  const pendientes = () => new Promise((r) => setTimeout(r));

  describe('iniciar()', () => {
    it('sin la cookie csrf no hay sesión y no llama a la API', async () => {
      await sesion.iniciar();
      expect(sesion.usuario()).toBeNull();
      api.expectNone('/api/me');
    });

    it('con sesión carga el perfil y su idioma manda', async () => {
      ponerCsrf('a');
      const listo = sesion.iniciar();
      api.expectOne('/api/me').flush(BRUNO);
      await listo;

      expect(sesion.usuario()).toEqual(BRUNO);
      expect(sesion.rol()).toBe('estudiante');
      expect(TestBed.inject(IdiomaService).actual()).toBe('en');
    });

    it('si la sesión venció y no se puede renovar, arranca sin sesión', async () => {
      ponerCsrf('a');
      const listo = sesion.iniciar();
      api.expectOne('/api/me').flush(errorApi('sin_sesion'), { status: 401, statusText: '' });
      await pendientes();
      api
        .expectOne('/api/auth/refresh')
        .flush(errorApi('token_vencido'), { status: 401, statusText: '' });
      await listo;

      expect(sesion.usuario()).toBeNull();
    });
  });

  it('ingresar() manda usuario y clave y guarda el perfil', async () => {
    const listo = sesion.ingresar('ana', 'apolo-training-dev');
    const login = api.expectOne({ method: 'POST', url: '/api/auth/login' });
    expect(login.request.body).toEqual({ username: 'ana', clave: 'apolo-training-dev' });
    login.flush({ usuario: ANA });

    expect(await listo).toEqual(ANA);
    expect(sesion.usuario()).toEqual(ANA);
  });

  it('cambiarClave() manda las dos claves y vuelve a pedir el perfil', async () => {
    entrarComo(BRUNO);
    ponerCsrf('a');
    const listo = sesion.cambiarClave('temporal-1', 'nueva-clave-1');

    const cambio = api.expectOne('/api/auth/cambiar-clave');
    expect(cambio.request.body).toEqual({
      clave_actual: 'temporal-1',
      clave_nueva: 'nueva-clave-1',
    });
    expect(cambio.request.headers.get('X-CSRF-Token')).toBe('a');
    cambio.flush(null, { status: 204, statusText: 'No Content' });
    await pendientes();
    api.expectOne('/api/me').flush({ ...BRUNO, debe_cambiar_clave: false });
    await listo;

    expect(sesion.usuario()?.debe_cambiar_clave).toBe(false);
  });

  it('salir() cierra la sesión y lleva a /ingresar aunque la API falle', async () => {
    entrarComo(ANA);
    vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    const listo = sesion.salir();
    api
      .expectOne({ method: 'POST', url: '/api/auth/logout' })
      .flush(errorApi('error_interno'), { status: 500, statusText: '' });
    await listo;

    expect(sesion.usuario()).toBeNull();
    expect(TestBed.inject(Router).url).toBe('/ingresar');
  });

  describe('cambiarIdioma()', () => {
    it('sin sesión solo cambia la interfaz', async () => {
      await sesion.cambiarIdioma('en');
      expect(TestBed.inject(IdiomaService).actual()).toBe('en');
      api.expectNone('/api/me');
    });

    it('con sesión lo guarda en el perfil', async () => {
      entrarComo(ANA);
      const listo = sesion.cambiarIdioma('en');
      await pendientes();
      const patch = api.expectOne({ method: 'PATCH', url: '/api/me' });
      expect(patch.request.body).toEqual({ idioma: 'en' });
      patch.flush({ ...ANA, idioma: 'en' });
      await listo;

      expect(sesion.usuario()?.idioma).toBe('en');
    });

    it('si el PATCH falla, la interfaz queda en el idioma elegido', async () => {
      entrarComo(ANA);
      vi.spyOn(console, 'warn').mockImplementation(() => undefined);
      const listo = sesion.cambiarIdioma('en');
      await pendientes();
      api
        .expectOne({ method: 'PATCH', url: '/api/me' })
        .flush(errorApi('error_interno'), { status: 500, statusText: '' });
      await listo;

      expect(TestBed.inject(IdiomaService).actual()).toBe('en');
      expect(sesion.usuario()?.idioma).toBe('es');
    });
  });
});
