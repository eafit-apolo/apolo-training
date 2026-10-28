import type { HttpErrorResponse } from '@angular/common/http';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import type { TestRequest } from '@angular/common/http/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { ANA, borrarCookies, entrarComo, errorApi, ponerCsrf } from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { interceptorSesion } from './interceptor';
import { SesionService } from './sesion';

// DoD 3 de la F-03: pruebas del interceptor.
describe('interceptorSesion', () => {
  let http: HttpClient;
  let api: HttpTestingController;
  let router: Router;

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
    http = TestBed.inject(HttpClient);
    api = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
  });

  const NO_AUTENTICADO = { status: 401, statusText: 'Unauthorized' };
  const SIN_CONTENIDO = { status: 204, statusText: 'No Content' };

  function csrfDe(peticion: TestRequest): string | null {
    return peticion.request.headers.get('X-CSRF-Token');
  }

  it('manda X-CSRF-Token con la cookie csrf en todo lo que no sea GET', () => {
    ponerCsrf('token-1');

    http.post('/api/me/graduacion', {}).subscribe();
    http.patch('/api/me', { idioma: 'en' }).subscribe();
    http.get('/api/me').subscribe();

    expect(csrfDe(api.expectOne({ method: 'POST', url: '/api/me/graduacion' }))).toBe('token-1');
    expect(csrfDe(api.expectOne({ method: 'PATCH', url: '/api/me' }))).toBe('token-1');
    expect(csrfDe(api.expectOne({ method: 'GET', url: '/api/me' }))).toBeNull();
  });

  it('no toca las peticiones que no son de la API (textos de i18n)', () => {
    ponerCsrf('token-1');
    http.post('i18n/es.json', {}).subscribe();
    expect(csrfDe(api.expectOne('i18n/es.json'))).toBeNull();
  });

  it('sin cookie csrf no inventa la cabecera (el login)', () => {
    http.post('/api/auth/login', {}).subscribe();
    expect(api.expectOne('/api/auth/login').request.headers.has('X-CSRF-Token')).toBe(false);
  });

  it('ante dos 401 a la vez renueva una sola vez y repite las dos con el CSRF nuevo', () => {
    ponerCsrf('viejo');
    const respuestas: unknown[] = [];
    http.get('/api/me').subscribe((r) => respuestas.push(r));
    http.post('/api/me/graduacion', { jobid: '1' }).subscribe((r) => respuestas.push(r));

    api.expectOne('/api/me').flush(errorApi('token_vencido'), NO_AUTENTICADO);
    api.expectOne('/api/me/graduacion').flush(errorApi('token_vencido'), NO_AUTENTICADO);

    // Una sola renovación, con el CSRF que había (la API lo exige también aquí).
    const renovacion = api.expectOne('/api/auth/refresh');
    expect(csrfDe(renovacion)).toBe('viejo');
    ponerCsrf('nuevo');
    renovacion.flush(null, SIN_CONTENIDO);

    api.expectOne({ method: 'GET', url: '/api/me' }).flush(ANA);
    const repetida = api.expectOne({ method: 'POST', url: '/api/me/graduacion' });
    expect(csrfDe(repetida)).toBe('nuevo');
    expect(repetida.request.body).toEqual({ jobid: '1' });
    repetida.flush({ estado: 'enviada' });

    expect(respuestas).toEqual([ANA, { estado: 'enviada' }]);
  });

  it('un 204 sin cookies nuevas (otra pestaña ya renovó) también sirve', () => {
    ponerCsrf('vigente');
    let perfil: unknown;
    http.get('/api/me').subscribe((r) => (perfil = r));

    api.expectOne('/api/me').flush(errorApi('token_vencido'), NO_AUTENTICADO);
    api.expectOne('/api/auth/refresh').flush(null, SIN_CONTENIDO);
    api.expectOne('/api/me').flush(ANA);

    expect(perfil).toEqual(ANA);
  });

  it('una renovación más tarde es otra renovación', () => {
    ponerCsrf('a');
    http.get('/api/me').subscribe();
    api.expectOne('/api/me').flush(errorApi('token_vencido'), NO_AUTENTICADO);
    api.expectOne('/api/auth/refresh').flush(null, SIN_CONTENIDO);
    api.expectOne('/api/me').flush(ANA);

    http.get('/api/me').subscribe();
    api.expectOne('/api/me').flush(errorApi('token_vencido'), NO_AUTENTICADO);
    api.expectOne('/api/auth/refresh').flush(null, SIN_CONTENIDO);
    api.expectOne('/api/me').flush(ANA);
  });

  it('si la renovación falla, la sesión termina: a /ingresar con el motivo y la página', async () => {
    ponerCsrf('a');
    await router.navigateByUrl('/cursos/induccion/m05');
    entrarComo(ANA);
    let error: HttpErrorResponse | undefined;
    http.get('/api/me/progreso').subscribe({ error: (e: HttpErrorResponse) => (error = e) });

    api.expectOne('/api/me/progreso').flush(errorApi('token_vencido'), NO_AUTENTICADO);
    api.expectOne('/api/auth/refresh').flush(errorApi('token_invalido'), NO_AUTENTICADO);

    expect(error?.status).toBe(401);
    expect(TestBed.inject(SesionService).usuario()).toBeNull();
    await vi.waitFor(() =>
      expect(router.url).toBe('/ingresar?motivo=vencida&volver=%2Fcursos%2Finduccion%2Fm05'),
    );
  });

  it.each(['/api/auth/login', '/api/auth/refresh', '/api/auth/logout'])(
    'un 401 de %s no intenta renovar',
    (url) => {
      let estado: number | undefined;
      http.post(url, {}).subscribe({ error: (e: HttpErrorResponse) => (estado = e.status) });
      api.expectOne(url).flush(errorApi('clave_incorrecta'), NO_AUTENTICADO);
      expect(estado).toBe(401);
      api.expectNone('/api/auth/refresh');
    },
  );

  it('un 403 debe_cambiar_clave lleva a /cambiar-clave', async () => {
    await router.navigateByUrl('/mi-progreso');
    entrarComo(ANA);
    http.get('/api/me/progreso').subscribe({ error: () => undefined });

    api
      .expectOne('/api/me/progreso')
      .flush(errorApi('debe_cambiar_clave'), { status: 403, statusText: 'Forbidden' });

    await vi.waitFor(() => expect(router.url).toBe('/cambiar-clave'));
    expect(TestBed.inject(SesionService).usuario()?.debe_cambiar_clave).toBe(true);
  });

  it('otros 403 (sin_permiso) solo llegan a quien hizo la petición', async () => {
    await router.navigateByUrl('/cursos');
    let codigo: unknown;
    http.get('/api/panel/resumen').subscribe({
      error: (e: HttpErrorResponse) => (codigo = (e.error as { codigo: string }).codigo),
    });
    api
      .expectOne('/api/panel/resumen')
      .flush(errorApi('sin_permiso'), { status: 403, statusText: 'Forbidden' });
    expect(codigo).toBe('sin_permiso');
    expect(router.url).toBe('/cursos');
  });
});
