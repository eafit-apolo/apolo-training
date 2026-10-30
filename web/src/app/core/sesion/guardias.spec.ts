import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ANA, BRUNO, CARLA, DIEGO, entrarComo } from '../../../testing/sesion';
import { contenidoDePrueba } from '../../../testing/contenido';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { rutaInterna } from './rutas';
import type { Usuario } from './sesion';

// DoD 2 y 3 de la F-03: un estudiante no abre /admin, y pruebas de las guardias.
describe('Guardias de ruta', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
      ],
    });
  });

  /** Abre `url` con `usuario` en la sesión y devuelve a dónde terminó el router. */
  async function abrirComo(usuario: Usuario | null, url: string): Promise<string> {
    entrarComo(usuario);
    await RouterTestingHarness.create(url);
    return TestBed.inject(Router).url;
  }

  describe('sin sesión', () => {
    it.each([
      ['/cursos', '/ingresar'],
      ['/', '/ingresar'],
      ['/mi-progreso', '/ingresar?volver=%2Fmi-progreso'],
      ['/cursos/induccion/m05/trabajos', '/ingresar?volver=%2Fcursos%2Finduccion%2Fm05%2Ftrabajos'],
      ['/admin', '/ingresar?volver=%2Fadmin%2Fusuarios'],
      ['/panel', '/ingresar?volver=%2Fpanel'],
      ['/no-existe', '/ingresar?volver=%2Fno-existe'],
      ['/cambiar-clave', '/ingresar'],
      ['/ingresar', '/ingresar'],
    ])('%s → %s', async (url, destino) => {
      expect(await abrirComo(null, url)).toBe(destino);
    });
  });

  describe('por rol (Panel y Administración)', () => {
    it.each([
      ['ana', '/admin', '/cursos', ANA],
      ['ana', '/admin/usuarios', '/cursos', ANA],
      ['ana', '/admin/qos', '/cursos', ANA],
      ['ana', '/panel', '/cursos', ANA],
      ['ana', '/panel/graduaciones', '/cursos', ANA],
      ['carla', '/admin', '/cursos', CARLA],
      ['carla', '/panel', '/panel', CARLA],
      ['carla', '/panel/videos', '/panel/videos', CARLA],
      ['diego', '/admin', '/admin/usuarios', DIEGO],
      ['diego', '/admin/qos', '/admin/qos', DIEGO],
      ['diego', '/panel', '/panel', DIEGO],
    ] as const)('%s abre %s → %s', async (_nombre, url, destino, usuario) => {
      expect(await abrirComo(usuario, url)).toBe(destino);
    });

    it('un estudiante no ve la pantalla de Administración', async () => {
      entrarComo(ANA);
      const harness = await RouterTestingHarness.create('/admin/usuarios');
      const raiz = harness.routeNativeElement as HTMLElement;
      expect(raiz.querySelector('h1')?.textContent?.trim()).toBe('Hola, Ana');
      expect(raiz.querySelector('nav')?.textContent).not.toContain('Administración');
    });
  });

  describe('con la clave temporal', () => {
    it.each([
      ['/cursos', '/cambiar-clave'],
      ['/mi-progreso', '/cambiar-clave?volver=%2Fmi-progreso'],
      ['/ingresar', '/cambiar-clave'],
      ['/ingresar?volver=%2Fmi-progreso', '/cambiar-clave?volver=%2Fmi-progreso'],
      ['/cambiar-clave', '/cambiar-clave'],
    ])('%s → %s', async (url, destino) => {
      expect(await abrirComo(BRUNO, url)).toBe(destino);
    });
  });

  describe('/ingresar con sesión', () => {
    it.each([
      ['/ingresar', '/cursos'],
      ['/ingresar?volver=%2Fmi-progreso', '/mi-progreso'],
      ['/ingresar?volver=%2F%2Fotro.sitio', '/cursos'],
      ['/ingresar?volver=https%3A%2F%2Fotro.sitio', '/cursos'],
    ])('%s → %s', async (url, destino) => {
      expect(await abrirComo(ANA, url)).toBe(destino);
    });
  });

  it('/cambiar-clave con sesión normal es el cambio voluntario', async () => {
    expect(await abrirComo(ANA, '/cambiar-clave')).toBe('/cambiar-clave');
  });
});

describe('rutaInterna', () => {
  it.each([
    ['/mi-progreso', '/mi-progreso'],
    ['/cursos/induccion/m05?x=1#arriba', '/cursos/induccion/m05?x=1#arriba'],
    ['//otro.sitio/ruta', null],
    ['/\\otro.sitio', null],
    ['https://otro.sitio', null],
    ['javascript:alert(1)', null],
    ['mi-progreso', null],
    ['/ingresar', null],
    ['/ingresar?volver=%2Fcursos', null],
    ['/cambiar-clave', null],
    ['/ingresarx', '/ingresarx'],
    ['', null],
    [undefined, null],
    [42, null],
  ])('%o → %o', (valor, esperado) => {
    expect(rutaInterna(valor)).toBe(esperado);
  });
});
