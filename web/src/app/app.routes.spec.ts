import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router, TitleStrategy, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { TranslocoService } from '@jsverse/transloco';
import { problemasDeAccesibilidad } from '../testing/axe';
import { traduccionesDePrueba } from '../testing/transloco';
import { opcionesRouter } from './app.config';
import { routes } from './app.routes';
import { TituloTraducido } from './core/i18n/titulo';
import { SesionService } from './core/sesion/sesion';

describe('Rutas de la app (docs/diseno/pantallas.md)', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideRouter(routes, ...opcionesRouter),
        { provide: TitleStrategy, useClass: TituloTraducido },
      ],
    });
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

  it.each([
    ['/cursos', 'Hola, Ana', true],
    ['/cursos/induccion', 'Curso de inducción a Apolo', true],
    ['/cursos/induccion/m05', 'Módulo 5 · Trabajos con Slurm', true],
    ['/cursos/induccion/m05/trabajos', '5.1 · Tu primer trabajo con Slurm', true],
    ['/cursos/otro', 'Página no encontrada', true],
    ['/cursos/induccion/m99', 'Página no encontrada', true],
    ['/cursos/induccion/m05/no-existe', 'Página no encontrada', true],
    ['/mi-progreso', 'Mi progreso', true],
    ['/panel', 'Panel del curso', true],
    ['/panel/graduaciones', 'Graduaciones', true],
    ['/panel/videos', 'Videos', true],
    ['/admin/usuarios', 'Usuarios', true],
    ['/admin/qos', 'Aprobados pendientes de QOS', true],
    ['/ingresar', 'Ingresar', false],
    ['/cambiar-clave', 'Crea tu contraseña', false],
    ['/no-existe', 'Página no encontrada', true],
  ])('%s → «%s» (menú: %s)', async (url, h1, conMenu) => {
    const pagina = await abrir(url);
    expect(pagina.url).toBe(url);
    expect(pagina.h1).toBe(h1);
    expect(pagina.conMenu).toBe(conMenu);
  });

  it('/admin lleva a usuarios', async () => {
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

  it('una lección de un módulo bloqueado tampoco se abre', async () => {
    const { raiz } = await abrir('/cursos/induccion/m07/graduacion');
    expect(raiz.querySelector('at-bloqueado')).not.toBeNull();
    expect(raiz.querySelector('.cuerpo')).toBeNull();
  });

  it('«Probar como» cambia el avance: Bruno no ha empezado', async () => {
    TestBed.inject(SesionService).probarComo('bruno');
    const { raiz, h1 } = await abrir('/cursos');
    expect(h1).toBe('Hola, Bruno');
    expect(raiz.querySelector('.seguir a')?.textContent).toContain('Empezar');
    expect(raiz.querySelector('.seguir a')?.getAttribute('href')).toBe(
      '/cursos/induccion/m00/bienvenida',
    );
  });

  it('con el curso terminado, «Continuar» lleva a Mi progreso', async () => {
    TestBed.inject(SesionService).probarComo('diego');
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
  ])('%s no tiene problemas de accesibilidad (axe)', async (url) => {
    const { raiz } = await abrir(url);
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });
});
