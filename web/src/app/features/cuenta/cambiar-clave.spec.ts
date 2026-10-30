import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import {
  ANA,
  BRUNO,
  botonCon,
  borrarCookies,
  entrarComo,
  errorApi,
  escribir,
  ponerCsrf,
} from '../../../testing/sesion';
import { contenidoDePrueba } from '../../../testing/contenido';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { Usuario } from '../../core/sesion/sesion';
import type { Regla } from './cambiar-clave';
import { reglasDeClave } from './cambiar-clave';

describe('reglasDeClave', () => {
  const ok = (actual: string, nueva: string, repetir: string, usuario = 'ana') =>
    Object.fromEntries(
      reglasDeClave(actual, nueva, repetir, usuario).map((r) => [r.clave, r.ok]),
    ) as Partial<Record<Regla['clave'], boolean>>;

  it('marca cada regla por separado', () => {
    expect(ok('temporal', '', '')).toEqual({
      largo: false,
      distintaActual: false,
      distintaUsuario: false,
      coinciden: false,
    });
    expect(ok('temporal', 'corta', 'corta')).toEqual({
      largo: false,
      distintaActual: true,
      distintaUsuario: true,
      coinciden: true,
    });
    expect(ok('temporal', 'temporal', 'temporal').distintaActual).toBe(false);
    expect(ok('temporal', 'una-clave-larga', 'otra')).toMatchObject({
      largo: true,
      coinciden: false,
    });
  });

  it('el usuario no sirve como clave, tampoco en mayúsculas (como la API)', () => {
    expect(ok('x', 'Bruno123', 'Bruno123', 'bruno123').distintaUsuario).toBe(false);
  });

  it('cuenta caracteres, no unidades UTF-16 (como Python)', () => {
    expect(ok('x', '😀😀😀😀', '😀😀😀😀').largo).toBe(false);
    expect(ok('x', '😀😀😀😀😀😀😀😀', '😀😀😀😀😀😀😀😀').largo).toBe(true);
  });

  it('el máximo de 128 solo aparece cuando se pasa', () => {
    expect(reglasDeClave('x', 'a'.repeat(128), '', 'ana').map((r) => r.clave)).not.toContain(
      'maximo',
    );
    expect(reglasDeClave('x', 'a'.repeat(129), '', 'ana').at(-1)).toEqual({
      clave: 'maximo',
      ok: false,
    });
  });
});

describe('Cambiar la clave (pantalla 01)', () => {
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
  });

  async function abrir(usuario: Usuario, url = '/cambiar-clave') {
    entrarComo(usuario);
    const harness = await RouterTestingHarness.create(url);
    const raiz = harness.routeNativeElement as HTMLElement;
    // Deja terminar los `await` que siguen a una respuesta y luego pinta.
    const listo = async () => {
      await new Promise((r) => setTimeout(r));
      await harness.fixture.whenStable();
    };
    return { raiz, listo };
  }

  async function llenar(raiz: HTMLElement, listo: () => Promise<unknown>, nueva: string) {
    escribir(raiz, 'input[name=actual]', 'temporal-123');
    escribir(raiz, 'input[name=nueva]', nueva);
    escribir(raiz, 'input[name=repetir]', nueva);
    await listo();
  }

  const reglasOk = (raiz: HTMLElement) =>
    Array.from(raiz.querySelectorAll('.reglas li.ok')).map((li) =>
      li.textContent?.replace(/\s+/g, ' ').trim(),
    );
  const alerta = (raiz: HTMLElement) => raiz.querySelector('[role=alert]')?.textContent?.trim();
  const pendientes = () => new Promise((r) => setTimeout(r));

  describe('primer ingreso (obligatorio)', () => {
    // Bruno tiene el perfil en inglés, pero aquí la interfaz sigue en español.
    const bruno = { ...BRUNO, idioma: 'es' } as const;

    it('pide la temporal, avisa de las dos contraseñas y solo deja cerrar sesión', async () => {
      const { raiz } = await abrir(bruno);
      expect(raiz.querySelector('h1')?.textContent?.trim()).toBe('Crea tu contraseña');
      expect(raiz.textContent).toContain('Contraseña temporal');
      expect(raiz.textContent).toContain(
        'La de la VM de práctica la cambias en tu primera conexión SSH',
      );
      expect(raiz.textContent).toContain('Distinta de la temporal');
      expect(raiz.textContent).toContain('Hasta que la cambies no puedes abrir el curso.');
      expect(botonCon(raiz, 'Cerrar sesión')).toBeTruthy();
      expect(() => botonCon(raiz, 'Cancelar')).toThrow();
      expect(raiz.querySelector('nav')).toBeNull();
      expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
    });

    it('marca las reglas mientras se escribe', async () => {
      const { raiz, listo } = await abrir(bruno);
      expect(reglasOk(raiz)).toEqual([]);

      escribir(raiz, 'input[name=actual]', 'temporal-123');
      escribir(raiz, 'input[name=nueva]', 'corta');
      await listo();
      expect(reglasOk(raiz)).toEqual([
        'Cumple: Distinta de la temporal',
        'Cumple: Distinta de tu usuario',
      ]);

      escribir(raiz, 'input[name=nueva]', 'una-clave-buena');
      escribir(raiz, 'input[name=repetir]', 'una-clave-buena');
      await listo();
      expect(reglasOk(raiz)).toHaveLength(4);
    });

    it('si falta una regla no llama a la API', async () => {
      const { raiz, listo } = await abrir(bruno);
      await llenar(raiz, listo, 'corta');
      botonCon(raiz, 'Guardar y continuar').click();
      await listo();

      expect(alerta(raiz)).toBe('Revisa los requisitos de la nueva contraseña.');
      api.expectNone('/api/auth/cambiar-clave');
    });

    it('guarda, recarga el perfil y sigue a donde iba', async () => {
      const { raiz, listo } = await abrir(bruno, '/cambiar-clave?volver=%2Fmi-progreso');
      await llenar(raiz, listo, 'una-clave-buena');
      botonCon(raiz, 'Guardar y continuar').click();
      await listo();

      const cambio = api.expectOne('/api/auth/cambiar-clave');
      expect(cambio.request.body).toEqual({
        clave_actual: 'temporal-123',
        clave_nueva: 'una-clave-buena',
      });
      expect(cambio.request.headers.get('X-CSRF-Token')).toBe('csrf-1');
      cambio.flush(null, { status: 204, statusText: 'No Content' });
      await pendientes();
      api.expectOne('/api/me').flush({ ...bruno, debe_cambiar_clave: false });

      await vi.waitFor(() => expect(TestBed.inject(Router).url).toBe('/mi-progreso'));
    });

    it.each([
      ['clave_incorrecta', 'La contraseña temporal no es correcta.'],
      ['clave_repetida', 'La nueva contraseña debe ser distinta de la actual.'],
      ['clave_debil', 'La nueva contraseña debe tener 8 caracteres o más'],
    ])('la API responde %s → «%s»', async (codigo, texto) => {
      const { raiz, listo } = await abrir(bruno);
      await llenar(raiz, listo, 'una-clave-buena');
      botonCon(raiz, 'Guardar y continuar').click();
      await listo();
      api
        .expectOne('/api/auth/cambiar-clave')
        .flush(errorApi(codigo), { status: 400, statusText: 'Bad Request' });
      await listo();

      expect(alerta(raiz)).toContain(texto);
      expect(TestBed.inject(Router).url).toBe('/cambiar-clave');

      // Al corregir, el error de la API se quita.
      escribir(raiz, 'input[name=nueva]', 'otra-clave-buena');
      await listo();
      expect(alerta(raiz)).toBeUndefined();
    });
  });

  describe('desde el menú (voluntario)', () => {
    it('pide la actual y deja cancelar, volviendo a la página de antes', async () => {
      const { raiz } = await abrir(ANA, '/cambiar-clave?volver=%2Fcursos%2Finduccion');
      expect(raiz.querySelector('h1')?.textContent?.trim()).toBe('Cambiar contraseña');
      expect(raiz.textContent).toContain('Contraseña actual');
      expect(raiz.textContent).toContain('Distinta de la actual');
      expect(raiz.textContent).toContain('se cierran tus sesiones en otros equipos');
      expect(botonCon(raiz, 'Cancelar').getAttribute('href')).toBe('/cursos/induccion');
      expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
    });

    it('al guardar avisa que cerró las otras sesiones', async () => {
      const { raiz, listo } = await abrir(ANA);
      await llenar(raiz, listo, 'una-clave-buena');
      botonCon(raiz, 'Guardar').click();
      await listo();
      api.expectOne('/api/auth/cambiar-clave').flush(null, { status: 204, statusText: '' });
      await pendientes();
      api.expectOne('/api/me').flush(ANA);

      await vi.waitFor(() => expect(TestBed.inject(Router).url).toBe('/cursos'));
      expect(document.body.textContent).toContain('Cerramos tus sesiones en otros equipos.');
    });

    it('una clave actual errada se borra y se pide de nuevo', async () => {
      const { raiz, listo } = await abrir(ANA);
      await llenar(raiz, listo, 'una-clave-buena');
      botonCon(raiz, 'Guardar').click();
      await listo();
      api
        .expectOne('/api/auth/cambiar-clave')
        .flush(errorApi('clave_incorrecta'), { status: 400, statusText: '' });
      await listo();

      expect(alerta(raiz)).toBe('La contraseña actual no es correcta.');
      expect(raiz.querySelector<HTMLInputElement>('input[name=actual]')?.value).toBe('');
      expect(document.activeElement?.getAttribute('name')).toBe('actual');
    });
  });
});
