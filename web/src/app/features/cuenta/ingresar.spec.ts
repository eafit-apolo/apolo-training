import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { TranslocoService } from '@jsverse/transloco';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { ANA, BRUNO, botonCon, borrarCookies, errorApi, escribir } from '../../../testing/sesion';
import { contenidoDePrueba } from '../../../testing/contenido';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { interceptorSesion } from '../../core/sesion/interceptor';
import { desbloqueo, regionDe } from './hora';

describe('Ingresar (pantalla 01)', () => {
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
  });

  afterEach(() => {
    api.verify();
    vi.useRealTimers();
  });

  async function abrir(url = '/ingresar') {
    const harness = await RouterTestingHarness.create(url);
    const raiz = harness.routeNativeElement as HTMLElement;
    // Deja terminar los `await` que siguen a una respuesta y luego pinta.
    const listo = async () => {
      await new Promise((r) => setTimeout(r));
      await harness.fixture.whenStable();
    };
    return { harness, raiz, listo };
  }

  async function ingresar(raiz: HTMLElement, listo: () => Promise<unknown>, usuario = 'ana') {
    escribir(raiz, 'input[name=username]', usuario);
    escribir(raiz, 'input[name=clave]', 'apolo-training-dev');
    botonCon(raiz, 'Ingresar').click();
    await listo();
    return api.expectOne({ method: 'POST', url: '/api/auth/login' });
  }

  const alerta = (raiz: HTMLElement) =>
    raiz.querySelector('[role=alert]')?.textContent?.replace(/\s+/g, ' ').trim();

  it('entra con el usuario en minúsculas y sin espacios, y va a Cursos', async () => {
    const { raiz, listo } = await abrir();
    const login = await ingresar(raiz, listo, '  Ana ');
    expect(login.request.body).toEqual({ username: 'ana', clave: 'apolo-training-dev' });
    login.flush({ usuario: ANA });

    await vi.waitFor(() => expect(TestBed.inject(Router).url).toBe('/cursos'));
  });

  it('vuelve a la página de ?volver=', async () => {
    const { raiz, listo } = await abrir('/ingresar?volver=%2Fmi-progreso');
    (await ingresar(raiz, listo)).flush({ usuario: ANA });
    await vi.waitFor(() => expect(TestBed.inject(Router).url).toBe('/mi-progreso'));
  });

  it('con la clave temporal va a cambiarla, recordando a dónde iba', async () => {
    const { raiz, listo } = await abrir('/ingresar?volver=%2Fmi-progreso');
    (await ingresar(raiz, listo, 'bruno')).flush({ usuario: BRUNO });
    await vi.waitFor(() =>
      expect(TestBed.inject(Router).url).toBe('/cambiar-clave?volver=%2Fmi-progreso'),
    );
    // El idioma del perfil de Bruno manda.
    expect(TestBed.inject(TranslocoService).getActiveLang()).toBe('en');
  });

  it('sin usuario ni clave marca los campos y no llama a la API', async () => {
    const { raiz, listo } = await abrir();
    botonCon(raiz, 'Ingresar').click();
    await listo();

    expect(raiz.textContent).toContain('Escribe tu usuario.');
    expect(raiz.textContent).toContain('Escribe tu contraseña.');
    expect(raiz.querySelectorAll('mat-form-field.mat-form-field-invalid')).toHaveLength(2);
    // El mensaje queda enlazado al campo para el lector de pantalla.
    const campo = raiz.querySelector('input[name=username]');
    const error = raiz.querySelector('mat-error');
    expect(campo?.getAttribute('aria-describedby')).toContain(error?.id);
    api.expectNone('/api/auth/login');
  });

  it('clave errada: mensaje en el idioma de la interfaz y la clave se borra', async () => {
    const { raiz, listo } = await abrir();
    (await ingresar(raiz, listo)).flush(errorApi('clave_incorrecta'), {
      status: 401,
      statusText: 'Unauthorized',
    });
    await listo();

    expect(alerta(raiz)).toBe('Usuario o contraseña incorrectos.');
    expect(raiz.querySelector<HTMLInputElement>('input[name=clave]')?.value).toBe('');
    expect(document.activeElement?.getAttribute('name')).toBe('clave');
    // Sin «Te quedan N intentos»: el aviso fijo (decisión del 28-oct).
    expect(raiz.textContent).toContain('Tras 5 intentos fallidos la cuenta se bloquea 15 minutos.');
    expect(raiz.textContent).not.toMatch(/te quedan/i);
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('cuenta bloqueada: la hora con la zona y los minutos que faltan', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-10-28T19:30:00Z'));
    const hasta = '2026-10-28T19:44:10+00:00';
    const { raiz, listo } = await abrir();
    (await ingresar(raiz, listo)).flush(errorApi('cuenta_bloqueada', { bloqueado_hasta: hasta }), {
      status: 403,
      statusText: 'Forbidden',
    });
    await listo();

    const { hora } = desbloqueo(new Date(hasta), new Date(), regionDe('es', navigator.languages));
    expect(alerta(raiz)).toBe(
      `Tu cuenta quedó bloqueada por varios intentos fallidos. Podrás intentarlo otra vez a las ${hora}, en 15 minutos.`,
    );
  });

  it.each([
    [{ status: 403, codigo: 'cuenta_inactiva' }, 'escribe a apolo@eafit.edu.co'],
    [{ status: 422, codigo: 'datos_invalidos' }, 'Usuario o contraseña incorrectos.'],
    [{ status: 429, codigo: 'demasiadas_peticiones' }, 'Espera un minuto'],
    [{ status: 500, codigo: 'error_interno' }, 'Algo falló de nuestro lado'],
  ])('%o → «%s»', async ({ status, codigo }, texto) => {
    const { raiz, listo } = await abrir();
    (await ingresar(raiz, listo)).flush(errorApi(codigo), { status, statusText: '' });
    await listo();
    expect(alerta(raiz)).toContain(texto);
  });

  it('sin conexión lo dice, con la VPN como una de las causas', async () => {
    const { raiz, listo } = await abrir();
    (await ingresar(raiz, listo)).error(new ProgressEvent('error'));
    await listo();
    expect(alerta(raiz)).toContain('Revisa tu conexión (fuera de EAFIT, la VPN)');
  });

  it('con ?motivo=vencida avisa que la sesión terminó, hasta el primer intento', async () => {
    const { raiz, listo } = await abrir('/ingresar?motivo=vencida&volver=%2Fcursos');
    expect(raiz.querySelector('[role=status]')?.textContent).toContain('Tu sesión terminó.');

    (await ingresar(raiz, listo)).flush(errorApi('clave_incorrecta'), {
      status: 401,
      statusText: '',
    });
    await listo();
    expect(raiz.querySelector('[role=status]')).toBeNull();
  });

  it('«Mostrar la contraseña» cambia el tipo del campo', async () => {
    const { raiz, listo } = await abrir();
    const campo = raiz.querySelector<HTMLInputElement>('input[name=clave]');
    const boton = raiz.querySelector<HTMLButtonElement>(
      'button[aria-label="Mostrar la contraseña"]',
    );
    expect(campo?.type).toBe('password');

    boton?.click();
    await listo();

    expect(campo?.type).toBe('text');
    expect(boton?.getAttribute('aria-pressed')).toBe('true');
  });
});

describe('Hora del desbloqueo', () => {
  it('usa la región del navegador si es del mismo idioma', () => {
    expect(regionDe('es', ['es-CO', 'en'])).toBe('es-CO');
    expect(regionDe('en', ['es-CO', 'en-GB'])).toBe('en-GB');
    expect(regionDe('en', ['es-CO'])).toBe('en');
  });

  it('dice la diferencia con UTC y redondea los minutos hacia arriba (al menos 1)', () => {
    const ahora = new Date('2026-10-28T19:30:00Z');
    const { hora, minutos } = desbloqueo(new Date('2026-10-28T19:44:10Z'), ahora, 'es-CO');
    expect(minutos).toBe(15);
    expect(hora).toMatch(/\d{1,2}:44/);
    expect(hora).toMatch(/GMT/);
    expect(hora).not.toMatch(/COT/);

    expect(desbloqueo(new Date('2026-10-28T19:30:05Z'), ahora, 'en').minutos).toBe(1);
    expect(desbloqueo(new Date('2026-10-28T19:29:00Z'), ahora, 'en').minutos).toBe(1);
  });

  it('una región rara no rompe la pantalla', () => {
    const { hora } = desbloqueo(new Date(), new Date(), 'no-es-una-region-valida-xx');
    expect(hora).toMatch(/\d/);
  });
});
