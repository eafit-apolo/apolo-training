import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { cursoDe, resumenDe } from '../../../../testing/contenido';
import { ANA, CARLA, DIEGO, entrarComo } from '../../../../testing/sesion';
import { traduccionesDePrueba } from '../../../../testing/transloco';
import { IdiomaService } from '../../../core/i18n/idioma';
import { interceptorSesion } from '../../../core/sesion/interceptor';
import { CatalogoService } from './catalogo';

describe('CatalogoService (API de contenido)', () => {
  let catalogo: CatalogoService;
  let api: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(withInterceptors([interceptorSesion])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    catalogo = TestBed.inject(CatalogoService);
    api = TestBed.inject(HttpTestingController);
    entrarComo(ANA);
  });

  afterEach(() => api.verify());

  const pendientes = () => new Promise((r) => setTimeout(r));
  const CURSO = '/api/cursos/induccion';

  async function responderCurso(lang = 'es', cuerpo: object = cursoDe('ana')) {
    await pendientes();
    api.expectOne(`${CURSO}?lang=${lang}`).flush(cuerpo);
  }

  it('pide el curso una vez, en el idioma de la interfaz, y lo arma', async () => {
    const carga = catalogo.cargarCurso('induccion');
    await responderCurso();
    await carga;

    const curso = catalogo.curso('induccion');
    expect(curso?.continuar?.id).toBe('m05/trabajos');
    expect(catalogo.modulo(curso, 'm06')?.estado).toBe('bloqueado');
    expect(catalogo.modulo(curso, 'm06')?.abierto).toBe(false);

    await catalogo.cargarCurso('induccion');
    api.expectNone(`${CURSO}?lang=es`);
  });

  it('el catálogo pide la lista y el detalle de cada curso', async () => {
    const carga = catalogo.cargarCatalogo();
    await pendientes();
    api.expectOne('/api/cursos?lang=es').flush([resumenDe(cursoDe('ana'))]);
    await responderCurso();
    await carga;

    expect(catalogo.cursos().map((c) => c.id)).toEqual(['induccion']);
    expect(catalogo.error()).toBe(false);
  });

  it('un curso que no existe queda sin datos, sin marcar error', async () => {
    const carga = catalogo.cargarCurso('otro');
    await pendientes();
    api
      .expectOne('/api/cursos/otro?lang=es')
      .flush({ detail: 'x', codigo: 'no_encontrado' }, { status: 404, statusText: 'Not Found' });
    await carga;

    expect(catalogo.curso('otro')).toBeUndefined();
    expect(catalogo.error()).toBe(false);
  });

  it('si la API falla, lo marca para que la pantalla lo diga', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const carga = catalogo.cargarCurso('induccion');
    await pendientes();
    api.expectOne(`${CURSO}?lang=es`).flush(null, { status: 500, statusText: 'Error' });
    await carga;

    expect(catalogo.error()).toBe(true);
    expect(catalogo.curso('induccion')).toBeUndefined();
  });

  it('con otro usuario descarta lo cargado y lo vuelve a pedir', async () => {
    const primera = catalogo.cargarCurso('induccion');
    await responderCurso();
    await primera;

    entrarComo(DIEGO);
    const segunda = catalogo.cargarCurso('induccion');
    expect(catalogo.curso('induccion')).toBeUndefined();
    await responderCurso('es', cursoDe('diego'));
    await segunda;

    expect(catalogo.curso('induccion')?.continuar).toBeNull();
  });

  it('al cambiar el idioma vuelve a pedir lo que está en pantalla, sin vaciarlo', async () => {
    const carga = catalogo.cargarCurso('induccion');
    await responderCurso();
    await carga;

    await TestBed.inject(IdiomaService).cambiar('en');
    TestBed.tick();
    expect(catalogo.curso('induccion')).toBeDefined();
    const ingles = { ...cursoDe('ana'), titulo: 'Apolo induction course' };
    await responderCurso('en', ingles);
    await pendientes();

    expect(catalogo.curso('induccion')?.titulo).toBe('Apolo induction course');
  });

  it('instructores y admins abren los módulos bloqueados', async () => {
    entrarComo(CARLA);
    const carga = catalogo.cargarCurso('induccion');
    await responderCurso('es', cursoDe('carla'));
    await carga;

    const m08 = catalogo.modulo(catalogo.curso('induccion'), 'm08');
    expect(m08?.estado).toBe('bloqueado');
    expect(m08?.abierto).toBe(true);
  });
});
