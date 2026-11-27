import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { aprobadoDeEjemplo, listaDeEjemplo } from '../../../testing/admin';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { contenidoDePrueba } from '../../../testing/contenido';
import { sinAnimaciones } from '../../../testing/panel';
import {
  DIEGO,
  borrarCookies,
  botonCon,
  entrarComo,
  errorApi,
  ponerCsrf,
} from '../../../testing/sesion';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { opcionesRouter } from '../../app.config';
import { routes } from '../../app.routes';
import { interceptorSesion } from '../../core/sesion/interceptor';
import type { AprobadoPendienteApi } from './datos';
import { comandoQos, comillas, faltasAlta, ordenAlta } from './datos';

const ALTA = {
  usuario: 'ana',
  nombre: 'Ana Pérez',
  correo: 'ana@eafit.edu.co',
  cluster: 'apolo2',
  idioma: 'es',
} as const;

describe('Administración: cálculos', () => {
  it('revisa los datos de la alta con las reglas de apolo-training-admin', () => {
    expect(faltasAlta(ALTA)).toEqual([]);
    expect(faltasAlta({ ...ALTA, usuario: '', nombre: ' ', correo: '' })).toEqual([
      'usuario',
      'nombre',
      'correo',
    ]);
    expect(faltasAlta({ ...ALTA, usuario: 'Ana' })).toEqual(['usuarioInvalido']);
    expect(faltasAlta({ ...ALTA, usuario: 'a'.repeat(33) })).toEqual(['usuarioInvalido']);
    expect(faltasAlta({ ...ALTA, usuario: '_ana-2' })).toEqual([]);
    // El nombre va al GECOS de /etc/passwd: sin : ni , y hasta 120.
    expect(faltasAlta({ ...ALTA, nombre: 'Pérez, Ana' })).toEqual(['nombreInvalido']);
    expect(faltasAlta({ ...ALTA, nombre: 'Ana: admin' })).toEqual(['nombreInvalido']);
    expect(faltasAlta({ ...ALTA, nombre: 'á'.repeat(120) })).toEqual([]);
    expect(faltasAlta({ ...ALTA, nombre: 'á'.repeat(121) })).toEqual(['nombreInvalido']);
    expect(faltasAlta({ ...ALTA, correo: 'ana@eafit' })).toEqual(['correoInvalido']);
  });

  it('pone comillas solo cuando hacen falta, y escapa la comilla simple', () => {
    expect(comillas('ana@eafit.edu.co')).toBe('ana@eafit.edu.co');
    expect(comillas('Ana Pérez')).toBe("'Ana Pérez'");
    expect(comillas("Ana O'Neil")).toBe("'Ana O'\\''Neil'");
    expect(comillas('$(rm -rf ~)')).toBe("'$(rm -rf ~)'");
  });

  it('arma la orden de alta (y --idioma solo en inglés)', () => {
    expect(ordenAlta(ALTA)).toBe(
      "sudo apolo-training-admin alta ana --cluster apolo2 --nombre 'Ana Pérez' --correo ana@eafit.edu.co",
    );
    expect(ordenAlta({ ...ALTA, cluster: 'apolo3', idioma: 'en', nombre: '  Bo  ' })).toBe(
      'sudo apolo-training-admin alta ana --cluster apolo3 --nombre Bo --correo ana@eafit.edu.co --idioma en',
    );
  });

  it('el comando de la QOS lleva el marcador de la V-08', () => {
    expect(comandoQos('carla')).toBe('sacctmgr modify user carla set qos=<qos-normal>');
  });
});

describe('Administración (pantalla 06): nuevo usuario y QOS', () => {
  let api: HttpTestingController;

  beforeEach(() => {
    borrarCookies();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(withInterceptors([interceptorSesion])),
        provideHttpClientTesting(),
        provideRouter(routes, ...opcionesRouter),
        contenidoDePrueba(),
        sinAnimaciones(),
      ],
    });
    api = TestBed.inject(HttpTestingController);
    ponerCsrf('csrf-1');
  });

  afterEach(() => {
    api.verify();
    borrarCookies();
    document.querySelectorAll('.cdk-overlay-container').forEach((c) => (c.innerHTML = ''));
  });

  const pendientes = () => new Promise((r) => setTimeout(r));
  const texto = (el: Element | null | undefined) => el?.textContent?.replace(/\s+/g, ' ').trim();

  async function abrir(ruta: string, aprobados: AprobadoPendienteApi[] = [aprobadoDeEjemplo()]) {
    entrarComo(DIEGO);
    const harness = await RouterTestingHarness.create(ruta);
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    api.expectOne('/api/admin/aprobados-pendientes').flush(aprobados);
    if (ruta === '/admin' || ruta.startsWith('/admin/usuarios')) {
      api.expectOne((r) => r.url === '/api/admin/usuarios').flush(listaDeEjemplo());
    }
    await listo();
    return { raiz, listo };
  }

  function escribir(dialogo: Element, indice: number, valor: string) {
    const campo = dialogo.querySelectorAll<HTMLInputElement>('input:not([type=radio])')[indice];
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
  }

  it('/admin lleva a usuarios; las pestañas cuentan los aprobados pendientes', async () => {
    const { raiz } = await abrir('/admin');
    expect(texto(raiz.querySelector('h1'))).toBe('Administración');
    expect(
      Array.from(raiz.querySelectorAll('at-pestanas a')).map((a) => [
        texto(a),
        a.getAttribute('aria-current'),
      ]),
    ).toEqual([
      ['Usuarios', 'page'],
      ['Aprobados pendientes de QOS 11 esperando', null],
    ]);
    // Visible: el número; el lector de pantalla lee «1 esperando».
    expect(texto(raiz.querySelector('at-pestanas .cuenta'))).toBe('1');
    expect(texto(raiz.querySelector('at-pestanas .at-oculto'))).toBe('1 esperando');
  });

  it('«Nuevo usuario» arma la orden con comillas solo cuando todo está bien', async () => {
    const { raiz, listo } = await abrir('/admin/usuarios');
    botonCon(raiz, 'Nuevo usuario').click();
    await listo();
    const dialogo = document.querySelector('mat-dialog-container')!;
    expect(texto(dialogo.querySelector('h2'))).toBe('Nuevo usuario');
    expect(dialogo.querySelector('at-comando')).toBeNull();
    expect(texto(dialogo)).toContain('Completa los datos para ver la orden.');

    escribir(dialogo, 0, 'Ana');
    await listo();
    expect(dialogo.querySelectorAll('input')[0].getAttribute('aria-invalid')).toBe('true');
    escribir(dialogo, 0, 'ana');
    escribir(dialogo, 1, "Ana O'Neil Pérez");
    escribir(dialogo, 2, 'ana@eafit.edu.co');
    await listo();
    expect(texto(dialogo.querySelector('at-comando code'))).toBe(
      "sudo apolo-training-admin alta ana --cluster apolo2 --nombre 'Ana O'\\''Neil Pérez' --correo ana@eafit.edu.co",
    );
    const radios = dialogo.querySelectorAll<HTMLInputElement>('input[type=radio]');
    radios[1].click(); // Apolo III
    radios[3].click(); // inglés
    await listo();
    expect(texto(dialogo.querySelector('at-comando code'))).toBe(
      "sudo apolo-training-admin alta ana --cluster apolo3 --nombre 'Ana O'\\''Neil Pérez' --correo ana@eafit.edu.co --idioma en",
    );
    // Una coma en el nombre: sin orden (la 116 la rechazaría).
    escribir(dialogo, 1, 'Pérez, Ana');
    await listo();
    expect(dialogo.querySelector('at-comando')).toBeNull();
    expect(await problemasDeAccesibilidad(dialogo)).toEqual([]);
  });

  it('QOS: el comando para el clúster real, y «QOS aplicada» con confirmación', async () => {
    const { raiz, listo } = await abrir('/admin/qos');
    const tarjeta = raiz.querySelector('.aprobado')!;
    expect(texto(tarjeta.querySelector('h2'))).toBe('carla · Carla Ejemplo');
    expect(texto(tarjeta)).toContain('Corre esto en Apolo II como administrador:');
    expect(texto(tarjeta.querySelector('at-comando code'))).toBe(
      'sacctmgr modify user carla set qos=<qos-normal>',
    );
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);

    botonCon(raiz, 'Marcar QOS aplicada').click();
    await listo();
    const dialogo = document.querySelector('mat-dialog-container')!;
    expect(texto(dialogo.querySelector('h2'))).toBe('¿Ya aplicaste la QOS de carla?');
    expect(texto(dialogo)).toContain('ya corrió en Apolo II');
    (dialogo.querySelectorAll('button')[1] as HTMLButtonElement).click();
    await listo();
    const pedido = api.expectOne('/api/admin/aprobados-pendientes/carla/qos-aplicada');
    expect(pedido.request.method).toBe('POST');
    expect(pedido.request.headers.get('X-CSRF-Token')).toBe('csrf-1');
    pedido.flush(null, { status: 204, statusText: 'No Content' });
    await listo();
    api.expectOne('/api/admin/aprobados-pendientes').flush([]);
    await listo();
    expect(texto(raiz.querySelector('[role=status]'))).toContain(
      'QOS de carla marcada como aplicada.',
    );
    expect(texto(raiz.querySelector('.vacio'))).toBe('Nadie espera su QOS.');
    expect(raiz.querySelector('at-pestanas .cuenta')).toBeNull();
  });

  it('QOS: si ya estaba marcada (409), lo dice y recarga', async () => {
    const { raiz, listo } = await abrir('/admin/qos');
    botonCon(raiz, 'Marcar QOS aplicada').click();
    await listo();
    (document.querySelectorAll('mat-dialog-container button')[1] as HTMLButtonElement).click();
    await listo();
    api
      .expectOne('/api/admin/aprobados-pendientes/carla/qos-aplicada')
      .flush(errorApi('qos_ya_aplicada'), { status: 409, statusText: 'Conflict' });
    await listo();
    api.expectOne('/api/admin/aprobados-pendientes').flush([]);
    await listo();
    expect(texto(raiz.querySelector('[role=alert]'))).toBe(
      'Esa QOS ya estaba marcada. La lista está actualizada.',
    );
  });

  it('QOS: «Cancelar» no marca nada', async () => {
    const { raiz, listo } = await abrir('/admin/qos');
    botonCon(raiz, 'Marcar QOS aplicada').click();
    await listo();
    (document.querySelectorAll('mat-dialog-container button')[0] as HTMLButtonElement).click();
    await listo();
    expect(raiz.querySelector('.aprobado')).not.toBeNull();
  });
});
