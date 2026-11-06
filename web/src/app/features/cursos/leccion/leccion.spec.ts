import { Clipboard } from '@angular/cdk/clipboard';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { problemasDeAccesibilidad } from '../../../../testing/axe';
import { ContenidoApiDePrueba, contenidoDePrueba } from '../../../../testing/contenido';
import { MUESTRA_ES, MUESTRA_PELIGROSA } from '../../../../testing/leccion-muestra';
import { ANA, CARLA, botonCon, entrarComo } from '../../../../testing/sesion';
import { traduccionesDePrueba } from '../../../../testing/transloco';
import type { Simulacion } from '../../../../testing/video';
import { cargarVideo, pausarVideo, simularVideos } from '../../../../testing/video';
import { opcionesRouter } from '../../../app.config';
import { routes } from '../../../app.routes';
import { IdiomaService } from '../../../core/i18n/idioma';
import { CatalogoService } from '../datos/catalogo';
import { Bloques } from './bloques';

const TRABAJOS = '/cursos/induccion/m05/trabajos';
/** Ana con perfil de Apolo III (mismo avance: va en el módulo 5). */
const ANA_APOLO3 = { ...ANA, cluster: 'apolo3' as const };

describe('Lección (F-04)', () => {
  let api: ContenidoApiDePrueba;
  let harness: RouterTestingHarness;

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
    api = TestBed.inject(ContenidoApiDePrueba);
    entrarComo(ANA);
  });

  async function listo(): Promise<HTMLElement> {
    for (let i = 0; i < 3; i++) {
      await new Promise((r) => setTimeout(r));
      await harness.fixture.whenStable();
    }
    harness.detectChanges();
    return harness.routeNativeElement as HTMLElement;
  }

  async function abrir(url: string): Promise<HTMLElement> {
    harness = await RouterTestingHarness.create(url);
    return listo();
  }

  async function ir(url: string): Promise<HTMLElement> {
    await TestBed.inject(Router).navigateByUrl(url);
    return listo();
  }

  const texto = (raiz: Element, selector: string) =>
    Array.from(raiz.querySelectorAll(selector)).map((e) =>
      e.textContent?.replace(/\s+/g, ' ').trim(),
    );

  describe('DoD 1: la lección de muestra se ve completa', () => {
    it('en español', async () => {
      const raiz = await abrir(TRABAJOS);

      expect(texto(raiz, '.texto-leccion h2')).toEqual([
        'Objetivos',
        'Resumen',
        'Práctica',
        'Si algo falla',
      ]);
      expect(raiz.textContent).toContain('Video en preparación');
      // Script, comandos, salida y tres pasos con código; más el de la práctica.
      expect(raiz.querySelectorAll('.texto-leccion at-codigo')).toHaveLength(6);
      expect(raiz.querySelectorAll('.texto-leccion .at-codigo-copiar')).toHaveLength(5);
      expect(raiz.querySelector('.texto-leccion ol at-codigo')).not.toBeNull();
      expect(raiz.querySelector('.texto-leccion .at-md-tabla table')).not.toBeNull();
      expect(raiz.querySelectorAll('[role="tab"]')).toHaveLength(2);
      expect(texto(raiz, '.tarjeta h2')).toEqual(['Verifica tu práctica', 'Quiz']);
      expect(raiz.querySelector('.tarjeta at-codigo')?.textContent).toContain(
        'apolo-training verificar memoria',
      );
      expect(raiz.querySelector('.texto-leccion')?.hasAttribute('lang')).toBe(false);
      expect(api.lecciones).toEqual(['m05/trabajos?lang=es']);
    });

    it('y en inglés, sin aviso de traducción', async () => {
      await abrir(TRABAJOS);
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await listo();

      expect(texto(raiz, '.texto-leccion h2')).toEqual([
        'Objectives',
        'Summary',
        'Practice',
        'If something goes wrong',
      ]);
      expect(raiz.textContent).toContain('Video coming soon');
      expect(texto(raiz, '.tarjeta h2')).toEqual(['Check your practice', 'Quiz']);
      expect(texto(raiz, '[role="tab"]')).toEqual(['Apolo II (your cluster)', 'Apolo III']);
      expect(raiz.textContent).not.toContain('shown in Spanish');
      expect(api.lecciones).toEqual(['m05/trabajos?lang=es', 'm05/trabajos?lang=en']);
    });

    it('una lección sin inglés sale en español, con aviso y lang="es"', async () => {
      await TestBed.inject(IdiomaService).cambiar('en');
      const raiz = await abrir('/cursos/induccion/m04/modulos');

      expect(raiz.querySelector('.aviso')?.textContent).toContain(
        "This lesson isn't available in English yet",
      );
      expect(raiz.querySelector('.texto-leccion')?.getAttribute('lang')).toBe('es');
      expect(texto(raiz, '.texto-leccion h2')).toEqual(['Objetivos']);
    });
  });

  describe('DoD 2: pestañas Apolo II / Apolo III', () => {
    const pestanas = (raiz: Element) =>
      Array.from(raiz.querySelectorAll<HTMLElement>('[role="tab"]'));
    const visibles = (raiz: Element) =>
      Array.from(raiz.querySelectorAll<HTMLElement>('[role="tabpanel"]:not([hidden])')).map((p) =>
        p.textContent?.trim().slice(0, 25),
      );

    it('un usuario apolo3 ve abierta la de Apolo III', async () => {
      entrarComo(ANA_APOLO3);
      const raiz = await abrir(TRABAJOS);

      const [dos, tres] = pestanas(raiz);
      expect(tres.textContent?.trim()).toBe('Apolo III (tu clúster)');
      expect(tres.getAttribute('aria-selected')).toBe('true');
      expect(tres.tabIndex).toBe(0);
      expect(dos.getAttribute('aria-selected')).toBe('false');
      expect(dos.tabIndex).toBe(-1);
      expect(visibles(raiz)).toEqual(['No hay partición por defe']);
    });

    it('un usuario apolo2 ve abierta la de Apolo II', async () => {
      const raiz = await abrir(TRABAJOS);

      expect(pestanas(raiz)[0].getAttribute('aria-selected')).toBe('true');
      expect(visibles(raiz)).toEqual(['La partición por defecto ']);
    });

    it('las flechas cambian de pestaña y todas las de la lección cambian juntas', async () => {
      api.textos.set('m05/trabajos', {
        es: `${MUESTRA_ES}\n\n::: apolo2\n\nOtra de dos.\n\n:::\n\n::: apolo3\n\nOtra de tres.\n\n:::\n`,
      });
      const raiz = await abrir(TRABAJOS);
      const [dos] = pestanas(raiz);

      dos.focus();
      dos.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
      await listo();

      const tres = pestanas(raiz)[1];
      expect(document.activeElement).toBe(tres);
      expect(tres.getAttribute('aria-selected')).toBe('true');
      expect(visibles(raiz)).toEqual(['No hay partición por defe', 'Otra de tres.']);

      tres.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true }));
      await listo();
      expect(visibles(raiz)).toEqual(['La partición por defecto ', 'Otra de dos.']);
    });

    it('otra lección vuelve a abrir la pestaña del perfil', async () => {
      api.textos.set('m04/modulos', {
        es: '::: apolo2\n\nDos.\n\n:::\n\n::: apolo3\n\nTres.\n\n:::\n',
      });
      const raiz = await abrir(TRABAJOS);
      pestanas(raiz)[1].click();
      await listo();
      expect(visibles(raiz)).toEqual(['No hay partición por defe']);

      await ir('/cursos/induccion/m04/modulos');

      expect(visibles(raiz)).toEqual(['Dos.']);
    });
  });

  describe('DoD 3: ningún HTML del Markdown se ejecuta', () => {
    afterEach(() => {
      delete (window as { __atacado?: boolean }).__atacado;
    });

    it('el HTML de la lección se ve como texto y los enlaces javascript: no son enlaces', async () => {
      api.textos.set('m05/trabajos', { es: MUESTRA_PELIGROSA });
      const raiz = await abrir(TRABAJOS);
      const contenido = raiz.querySelector('.texto-leccion') as HTMLElement;

      expect((window as { __atacado?: boolean }).__atacado).toBeUndefined();
      expect(contenido.querySelector('script, img, div[onclick]')).toBeNull();
      expect(contenido.textContent).toContain('<script>window.__atacado = true</script>');
      expect(contenido.textContent).toContain('<div onclick=');
      const enlaces = Array.from(contenido.querySelectorAll('a'));
      expect(enlaces.map((a) => a.getAttribute('href'))).toEqual([
        'https://apolo-docs.readthedocs.io',
      ]);
      expect(enlaces[0].getAttribute('rel')).toBe('noopener noreferrer');
      const conEventos = Array.from(contenido.querySelectorAll('*')).filter((e) =>
        e.getAttributeNames().some((n) => n.startsWith('on')),
      );
      expect(conEventos).toEqual([]);
    });

    it('si algo se colara, Angular lo sanitiza al pintarlo (segunda capa)', () => {
      const aviso = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
      const fixture = TestBed.createComponent(Bloques);
      fixture.componentRef.setInput('bloques', [
        {
          tipo: 'html',
          html:
            '<img src="x" onerror="window.__atacado = true">' +
            '<script>window.__atacado = true</script>' +
            '<a href="javascript:window.__atacado = true">clic</a>',
        },
      ]);
      fixture.detectChanges();
      const raiz = fixture.nativeElement as HTMLElement;

      expect(raiz.querySelector('script')).toBeNull();
      expect(raiz.querySelector('img')?.hasAttribute('onerror')).toBe(false);
      expect(raiz.querySelector('a')?.getAttribute('href')).toMatch(/^unsafe:javascript:/);
      expect(aviso).toHaveBeenCalled();
    });
  });

  describe('bloques de código', () => {
    it('«Copiar» copia el comando tal cual y lo confirma', async () => {
      const copiar = vi.spyOn(TestBed.inject(Clipboard), 'copy').mockReturnValue(true);
      const raiz = await abrir(TRABAJOS);
      const boton = raiz.querySelectorAll<HTMLButtonElement>('.at-codigo-copiar')[1];

      boton.click();
      await listo();

      expect(copiar).toHaveBeenCalledWith('sbatch <script>.sh\nsqueue -u $USER\nsacct -j <JobID>');
      expect(boton.textContent?.trim()).toBe('Copiado');
      expect(boton.closest('at-codigo')?.querySelector('[aria-live]')?.textContent).toBe(
        'Copiado al portapapeles',
      );
    });

    it('la salida dice «salida» y no tiene botón', async () => {
      const raiz = await abrir(TRABAJOS);
      const salida = Array.from(raiz.querySelectorAll('at-codigo')).find((c) =>
        c.textContent?.includes('NODELIST(REASON)'),
      );

      expect(salida?.querySelector('.at-codigo-cabecera')?.textContent?.trim()).toBe('salida');
      expect(salida?.querySelector('button')).toBeNull();
    });
  });

  describe('video', () => {
    it('la lección de VPN abre el video del sistema del navegador', async () => {
      vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
        'Mozilla/5.0 (X11; Linux x86_64) Chrome/140',
      );
      const raiz = await abrir('/cursos/induccion/m01/vpn');

      const botones = Array.from(raiz.querySelectorAll('at-videos button'));
      expect(botones.map((b) => b.textContent?.replace(/\s+/g, ' ').trim())).toEqual([
        'Windows',
        'macOS',
        'Linux (tu sistema)',
      ]);
      expect(botones[2].getAttribute('aria-pressed')).toBe('true');
    });

    it('un video subido se reproduce, con sus subtítulos', async () => {
      api.conVideo.add('m05/trabajos');
      const raiz = await abrir(TRABAJOS);

      const video = raiz.querySelector('video');
      expect(video?.getAttribute('src')).toMatch(/^\/api\/media\/\d+$/);
      expect(video?.hasAttribute('playsinline')).toBe(true);
      expect(video?.querySelectorAll('track')).toHaveLength(2);
      expect(raiz.querySelector('at-reproductor .controles')?.textContent).toContain('Velocidad');
    });

    describe('con el reproductor (F-05)', () => {
      let simulacion: Simulacion;

      beforeEach(() => {
        simulacion = simularVideos();
        api.conVideo.add('m05/trabajos');
      });

      afterEach(() => simulacion.restaurar());

      it('al ver el 90 % la lección queda completa, sin sacar el foco del video', async () => {
        const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
        const raiz = await abrir(TRABAJOS);
        const video = raiz.querySelector('video') as HTMLVideoElement;
        const estado = simulacion.de(video);
        cargarVideo(video);
        // jsdom no deja enfocar un <video>: el foco va en un control del reproductor.
        const velocidad = raiz.querySelector('at-reproductor select') as HTMLSelectElement;
        velocidad.focus();

        estado.tiempo = 280;
        pausarVideo(estado, video);
        const final = await listo();

        expect(api.reportes.map((r) => r.entrada.segundo)).toEqual([280]);
        expect(recargar).toHaveBeenCalled();
        expect(final.querySelector('.completar .hecha')?.textContent?.trim()).toBe(
          'Completaste esta lección',
        );
        expect(final.querySelector('.anuncio')?.textContent?.trim()).toBe(
          'Viste el video: completaste esta lección.',
        );
        expect(document.activeElement).toBe(velocidad);
        expect(final.querySelector('.meta')?.textContent).toContain('Completa');
        // El mismo video: la respuesta no lo vuelve a armar.
        expect(final.querySelector('video')).toBe(video);
      });

      it('al cambiar el idioma los subtítulos cambian sin recargar el video (DoD 2)', async () => {
        const raiz = await abrir(TRABAJOS);
        const video = raiz.querySelector('video') as HTMLVideoElement;
        const estado = simulacion.de(video);
        cargarVideo(video);
        expect(estado.pistas.map((p) => p.mode)).toEqual(['disabled', 'disabled']);

        await TestBed.inject(IdiomaService).cambiar('en');
        const final = await listo();

        expect(final.querySelector('video')).toBe(video);
        expect(estado.cargas).toBe(0);
        expect(estado.pistas.find((p) => p.language === 'en')?.mode).toBe('showing');
        expect(final.querySelector('at-reproductor label')?.textContent).toContain('Speed');
      });

      it('en la VPN, cambiar de sistema arma otro reproductor y el anterior reporta dónde iba', async () => {
        vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(
          'Mozilla/5.0 (X11; Linux x86_64) Chrome/140',
        );
        api.conVideo.add('m01/vpn');
        const raiz = await abrir('/cursos/induccion/m01/vpn');
        const linux = raiz.querySelector('video') as HTMLVideoElement;
        cargarVideo(linux);
        simulacion.de(linux).tiempo = 50;

        (raiz.querySelectorAll('at-videos .sistemas button')[0] as HTMLButtonElement).click();
        const final = await listo();

        const windows = final.querySelector('video');
        expect(windows).not.toBe(linux);
        expect(windows?.getAttribute('src')).not.toBe(linux.getAttribute('src'));
        expect(api.reportes).toHaveLength(1);
        expect(api.reportes[0].entrada.segundo).toBe(50);
        expect(`/api/media/${api.reportes[0].entrada.video_id}`).toBe(linux.getAttribute('src'));
      });

      it('una instructora en un módulo bloqueado ve el video, pero no reporta', async () => {
        // Una instructora sin avance: el módulo 5 está bloqueado para ella.
        entrarComo({ ...CARLA, username: 'bruno' });
        const raiz = await abrir(TRABAJOS);
        expect(raiz.querySelector('.aviso')?.textContent).toContain(
          'bloqueado para los estudiantes',
        );
        const video = raiz.querySelector('video') as HTMLVideoElement;
        const estado = simulacion.de(video);
        cargarVideo(video);

        estado.tiempo = 280;
        pausarVideo(estado, video);
        await listo();

        expect(api.reportes).toEqual([]);
      });
    });
  });

  describe('completar y avanzar', () => {
    it('la siguiente lección de un módulo bloqueado no es un enlace', async () => {
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('.vecina:not(.siguiente)')?.getAttribute('href')).toBe(
        '/cursos/induccion/m04/modulos',
      );
      const siguiente = raiz.querySelector('.siguiente');
      expect(siguiente?.tagName).toBe('P');
      expect(siguiente?.textContent).toContain('6.1 · Núcleos y paralelismo');
      expect(siguiente?.textContent).toContain('Bloqueado: termina el módulo 5');
    });

    it('«Marcar como completada» guarda, pone al día el avance y abre el módulo siguiente', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      const raiz = await abrir(TRABAJOS);

      botonCon(raiz, 'Marcar como completada').click();
      const final = await listo();

      expect(api.completadas).toHaveLength(1);
      expect(recargar).toHaveBeenCalled();
      const hecha = final.querySelector<HTMLElement>('.completar .hecha');
      expect(hecha?.textContent?.trim()).toBe('Completaste esta lección');
      expect(document.activeElement).toBe(hecha);
      expect(final.querySelector('.meta')?.textContent).toContain('Completa');
      expect(final.querySelector('a.siguiente')?.getAttribute('href')).toBe(
        '/cursos/induccion/m06/paralelismo',
      );
      expect(final.querySelector('.completar button')).toBeNull();
    });

    it('si la API no deja completarla, dice por qué', async () => {
      vi.spyOn(api, 'completar').mockRejectedValue(
        new HttpErrorResponse({ status: 409, error: { codigo: 'requisitos_pendientes' } }),
      );
      const raiz = await abrir(TRABAJOS);

      botonCon(raiz, 'Marcar como completada').click();
      await listo();

      expect(raiz.querySelector('.completar [role="alert"]')?.textContent).toBe(
        'Termina el video para completar esta lección.',
      );
    });

    it('con un video subido no hay botón: se completa al verlo', async () => {
      api.conVideo.add('m05/trabajos');
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('.completar button')).toBeNull();
      expect(raiz.querySelector('.completar')?.textContent?.trim()).toBe(
        'Esta lección se completa al ver el 90 % del video.',
      );
    });

    it('una lección ya completa lo dice, sin botón', async () => {
      const raiz = await abrir('/cursos/induccion/m04/modulos');

      expect(raiz.querySelector('.completar')?.textContent?.trim()).toBe(
        'Completaste esta lección',
      );
    });

    it('una instructora en un módulo bloqueado lee la lección, pero no la completa', async () => {
      entrarComo(CARLA);
      const raiz = await abrir('/cursos/induccion/m08/cierre');

      expect(raiz.querySelector('.aviso')?.textContent).toContain('bloqueado para los estudiantes');
      expect(raiz.querySelector('.texto-leccion h2')?.textContent).toBe('Objetivos');
      expect(raiz.querySelector('.completar')?.textContent?.trim()).toBe('');
    });
  });

  describe('errores', () => {
    it('si la API dice que el módulo está bloqueado, lo muestra y pone al día el catálogo', async () => {
      const recargar = vi.spyOn(TestBed.inject(CatalogoService), 'recargar');
      vi.spyOn(api, 'leccion').mockRejectedValue(
        new HttpErrorResponse({ status: 403, error: { codigo: 'modulo_bloqueado' } }),
      );
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('at-bloqueado')).not.toBeNull();
      expect(recargar).toHaveBeenCalled();
    });

    it('si la lección no carga, lo dice y deja reintentar', async () => {
      const leccion = api.leccion.bind(api);
      vi.spyOn(api, 'leccion')
        .mockRejectedValueOnce(new HttpErrorResponse({ status: 0 }))
        .mockImplementation(leccion);
      const raiz = await abrir(TRABAJOS);

      expect(raiz.querySelector('[role="alert"]')?.textContent).toContain(
        'No pudimos cargar la lección',
      );
      botonCon(raiz, 'Reintentar').click();
      await listo();

      expect(raiz.querySelector('[role="alert"]')).toBeNull();
      expect(raiz.querySelector('.texto-leccion h2')?.textContent).toBe('Objetivos');
    });

    it('una lección que la API ya no tiene dice que no existe', async () => {
      vi.spyOn(api, 'leccion').mockResolvedValue(null);
      const raiz = await abrir(TRABAJOS);

      expect(raiz.textContent).toContain('Esta dirección no existe.');
    });
  });

  it.each([
    ['la lección de muestra, Apolo III', TRABAJOS, ANA_APOLO3],
    ['la lección de VPN', '/cursos/induccion/m01/vpn', ANA],
    ['una lección completa', '/cursos/induccion/m04/modulos', ANA],
  ])('%s no tiene problemas de accesibilidad (axe)', async (_, url, usuario) => {
    entrarComo(usuario);
    const raiz = await abrir(url);

    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });
});
