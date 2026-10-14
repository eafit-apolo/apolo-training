import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router, TitleStrategy, provideRouter, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { TranslocoService } from '@jsverse/transloco';
import { traduccionesDePrueba } from '../testing/transloco';
import { routes } from './app.routes';
import { TituloTraducido } from './core/i18n/titulo';

describe('Rutas de la app (docs/diseno/pantallas.md)', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideRouter(routes, withComponentInputBinding()),
        { provide: TitleStrategy, useClass: TituloTraducido },
      ],
    });
  });

  async function abrir(url: string) {
    const harness = await RouterTestingHarness.create(url);
    const raiz = harness.routeNativeElement as HTMLElement;
    return {
      url: TestBed.inject(Router).url,
      h1: raiz.querySelector('h1')?.textContent?.trim(),
      conMenu: raiz.querySelector('nav') !== null,
    };
  }

  it('la raíz lleva al catálogo', async () => {
    const pagina = await abrir('/');
    expect(pagina.url).toBe('/cursos');
    expect(pagina.h1).toBe('Cursos');
  });

  it.each([
    ['/cursos', 'Cursos', true],
    ['/cursos/induccion/m05/l1', 'Lección', true],
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
});
