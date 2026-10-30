import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router, TitleStrategy, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { TranslocoService } from '@jsverse/transloco';
import { problemasDeAccesibilidad } from '../testing/axe';
import { ANA, BRUNO, CARLA, DIEGO, entrarComo } from '../testing/sesion';
import { ContenidoApiDePrueba, contenidoDePrueba } from '../testing/contenido';
import { traduccionesDePrueba } from '../testing/transloco';
import { opcionesRouter } from './app.config';
import { routes } from './app.routes';
import { TituloTraducido } from './core/i18n/titulo';

describe('Rutas de la app (docs/diseno/pantallas.md)', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
        { provide: TitleStrategy, useClass: TituloTraducido },
      ],
    });
    // Ana va en el módulo 5 (datos de ejemplo de la F-02).
    entrarComo(ANA);
  });

  async function abrir(url: string) {
    const harness = await RouterTestingHarness.create(url);
    const raiz = harness.routeNativeElement as HTMLElement;
    return {
      raiz,
      url: TestBed.inject(Router).url,
      h1: raiz.querySelector('h1')?.textContent?.trim(),
      conMenu: raiz.querySelector('nav') !== null,
    };
  }

  it('la raíz lleva al catálogo', async () => {
    const pagina = await abrir('/');
    expect(pagina.url).toBe('/cursos');
    expect(pagina.h1).toBe('Hola, Ana');
  });

  // Diego es admin y terminó el curso: puede abrir todas las pantallas.
  it.each([
    ['/cursos', 'Hola, Diego'],
    ['/cursos/induccion', 'Curso de inducción a Apolo'],
    ['/cursos/induccion/m05', 'Módulo 5 · Trabajos con Slurm'],
    ['/cursos/induccion/m05/trabajos', '5.1 · Tu primer trabajo con Slurm'],
    ['/cursos/otro', 'Página no encontrada'],
    ['/cursos/induccion/m99', 'Página no encontrada'],
    ['/cursos/induccion/m05/no-existe', 'Página no encontrada'],
    ['/mi-progreso', 'Mi progreso'],
    ['/panel', 'Panel del curso'],
    ['/panel/graduaciones', 'Graduaciones'],
    ['/panel/videos', 'Videos'],
    ['/admin/usuarios', 'Usuarios'],
    ['/admin/qos', 'Aprobados pendientes de QOS'],
    ['/no-existe', 'Página no encontrada'],
  ])('%s → «%s», con menú', async (url, h1) => {
    entrarComo(DIEGO);
    const pagina = await abrir(url);
    expect(pagina.url).toBe(url);
    expect(pagina.h1).toBe(h1);
    expect(pagina.conMenu).toBe(true);
  });

  it.each([
    ['/ingresar', null, 'Ingresa al curso de inducción'],
    ['/cambiar-clave', BRUNO, 'Crea tu contraseña'],
    ['/cambiar-clave', ANA, 'Cambiar contraseña'],
  ] as const)('%s (%o) → «%s», sin menú', async (url, usuario, h1) => {
    entrarComo(usuario);
    const pagina = await abrir(url);
    expect(pagina.url).toBe(url);
    expect(pagina.h1).toBe(h1);
    expect(pagina.conMenu).toBe(false);
  });

  it('/admin lleva a usuarios', async () => {
    entrarComo(DIEGO);
    expect((await abrir('/admin')).url).toBe('/admin/usuarios');
  });

  it('el título de la pestaña se traduce y cambia con el idioma', async () => {
    await abrir('/mi-progreso');
    const titulo = TestBed.inject(Title);
    expect(titulo.getTitle()).toBe('Mi progreso · Curso de inducción Apolo');

    TestBed.inject(TranslocoService).setActiveLang('en');
    await TestBed.inject(Router).navigateByUrl('/mi-progreso');

    expect(titulo.getTitle()).toBe('My progress · Apolo induction course');
  });

  it('el título de la pestaña de una lección es su nombre, sin traducir', async () => {
    await abrir('/cursos/induccion/m05/trabajos');
    const titulo = TestBed.inject(Title);
    expect(titulo.getTitle()).toBe('5.1 · Tu primer trabajo con Slurm · Curso de inducción Apolo');

    TestBed.inject(TranslocoService).setActiveLang('en');
    await TestBed.inject(Router).navigateByUrl('/cursos/induccion/m05');

    expect(titulo.getTitle()).toBe('5 · Trabajos con Slurm · Apolo induction course');
  });

  it('las migas llevan de la lección al módulo, al curso y a Cursos', async () => {
    const { raiz } = await abrir('/cursos/induccion/m05/trabajos');
    const migas = raiz.querySelector('at-migas nav');
    expect(migas?.getAttribute('aria-label')).toBe('Ruta de navegación');
    const enlaces = Array.from(migas?.querySelectorAll('a') ?? []).map((a) =>
      a.getAttribute('href'),
    );
    expect(enlaces).toEqual(['/cursos', '/cursos/induccion', '/cursos/induccion/m05']);
    expect(migas?.querySelector('[aria-current="page"]')?.textContent?.trim()).toBe(
      'Tu primer trabajo con Slurm',
    );
  });

  it('un módulo bloqueado se ve pero dice qué terminar y a dónde ir', async () => {
    const { raiz, h1 } = await abrir('/cursos/induccion/m06');
    expect(h1).toBe('Módulo 6 · Núcleos y paralelismo');
    expect(raiz.textContent).toContain('Este módulo se abre cuando termines el módulo 5.');
    const ir = raiz.querySelector<HTMLAnchorElement>('at-bloqueado a');
    expect(ir?.getAttribute('href')).toBe('/cursos/induccion/m05');
    expect(raiz.querySelector('.lecciones')).toBeNull();
  });

  it('una instructora abre un módulo bloqueado, con un aviso', async () => {
    entrarComo(CARLA);
    const { raiz, h1 } = await abrir('/cursos/induccion/m08');
    expect(h1).toBe('Módulo 8 · Cierre y quiz final');
    expect(raiz.querySelector('at-bloqueado')).toBeNull();
    expect(raiz.querySelector('.aviso-rol')?.textContent).toContain(
      'bloqueado para los estudiantes',
    );
    expect(raiz.querySelector('.lecciones a')).not.toBeNull();
  });

  it('el contenido se pide una vez por usuario, no en cada pantalla', async () => {
    const api = TestBed.inject(ContenidoApiDePrueba);
    await abrir('/cursos/induccion/m05');
    await TestBed.inject(Router).navigateByUrl('/cursos/induccion/m05/trabajos');
    await TestBed.inject(Router).navigateByUrl('/cursos/induccion');
    expect(api.pedidos).toEqual(['cursos/induccion?lang=es']);
  });

  it('si la API de contenido falla, la pantalla lo dice', async () => {
    const api = TestBed.inject(ContenidoApiDePrueba);
    vi.spyOn(api, 'curso').mockRejectedValue(new Error('sin red'));
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { h1 } = await abrir('/cursos/induccion');
    expect(h1).toBe('No pudimos cargar el curso');
  });

  it('una lección de un módulo bloqueado tampoco se abre', async () => {
    const { raiz } = await abrir('/cursos/induccion/m07/graduacion');
    expect(raiz.querySelector('at-bloqueado')).not.toBeNull();
    expect(raiz.querySelector('.cuerpo')).toBeNull();
  });

  it('el avance es el del usuario de la sesión: Bruno no ha empezado', async () => {
    entrarComo({ ...BRUNO, idioma: 'es', debe_cambiar_clave: false });
    const { raiz, h1 } = await abrir('/cursos');
    expect(h1).toBe('Hola, Bruno');
    expect(raiz.querySelector('.seguir a')?.textContent).toContain('Empezar');
    expect(raiz.querySelector('.seguir a')?.getAttribute('href')).toBe(
      '/cursos/induccion/m00/bienvenida',
    );
  });

  it('con el curso terminado, «Continuar» lleva a Mi progreso', async () => {
    entrarComo(DIEGO);
    const { raiz } = await abrir('/cursos');
    expect(raiz.querySelector('.seguir a')?.getAttribute('href')).toBe('/mi-progreso');
  });

  it.each([
    '/cursos',
    '/cursos/induccion',
    '/cursos/induccion/m05',
    '/cursos/induccion/m05/trabajos',
    '/cursos/induccion/m06',
    '/ingresar',
    '/cambiar-clave',
  ])('%s no tiene problemas de accesibilidad (axe)', async (url) => {
    if (url === '/ingresar') {
      entrarComo(null);
    }
    const { raiz } = await abrir(url);
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });
});
