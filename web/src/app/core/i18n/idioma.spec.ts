import { DOCUMENT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { TranslocoService } from '@jsverse/transloco';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { IdiomaService, idiomaDelNavegador } from './idioma';

const CLAVE = 'apolo-training.idioma';

describe('idiomaDelNavegador', () => {
  it.each([
    [['en-US', 'es'], 'en'],
    [['es-CO', 'en'], 'es'],
    [['fr-FR', 'en-GB'], 'en'],
    [['fr-FR'], 'es'],
    [[], 'es'],
  ])('%j → %s', (preferidos, esperado) => {
    expect(idiomaDelNavegador(preferidos)).toBe(esperado);
  });
});

describe('IdiomaService', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [traduccionesDePrueba()] });
  });

  afterEach(() => vi.restoreAllMocks());

  function navegadorEn(...idiomas: string[]) {
    vi.spyOn(navigator, 'languages', 'get').mockReturnValue(idiomas);
  }

  it('usa la elección guardada en este navegador antes que la del navegador', async () => {
    navegadorEn('es-CO');
    localStorage.setItem(CLAVE, 'en');
    const servicio = TestBed.inject(IdiomaService);

    await servicio.iniciar();

    expect(servicio.actual()).toBe('en');
    expect(TestBed.inject(TranslocoService).getActiveLang()).toBe('en');
    expect(TestBed.inject(DOCUMENT).documentElement.lang).toBe('en');
  });

  it('sin elección guardada toma la del navegador', async () => {
    navegadorEn('en-US');
    const servicio = TestBed.inject(IdiomaService);

    await servicio.iniciar();

    expect(servicio.actual()).toBe('en');
  });

  it('ignora un valor guardado que no es un idioma de la app', async () => {
    navegadorEn('fr-FR');
    localStorage.setItem(CLAVE, 'fr');
    const servicio = TestBed.inject(IdiomaService);

    await servicio.iniciar();

    expect(servicio.actual()).toBe('es');
  });

  it('cambiar() aplica el idioma y lo recuerda', async () => {
    navegadorEn('es-CO');
    const servicio = TestBed.inject(IdiomaService);
    await servicio.iniciar();

    await servicio.cambiar('en');

    expect(servicio.actual()).toBe('en');
    expect(localStorage.getItem(CLAVE)).toBe('en');
    expect(TestBed.inject(DOCUMENT).documentElement.lang).toBe('en');
  });

  it('sigue funcionando si localStorage lanza (modo privado)', async () => {
    navegadorEn('en');
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('bloqueado');
    });
    const servicio = TestBed.inject(IdiomaService);

    await servicio.iniciar();
    await servicio.cambiar('es');

    expect(servicio.actual()).toBe('es');
  });
});
