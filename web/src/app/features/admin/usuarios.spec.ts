import { provideHttpClient, withInterceptors } from '@angular/common/http';
import type { TestRequest } from '@angular/common/http/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import {
  aprobadoDeEjemplo,
  detalleDeEjemplo,
  listaDeEjemplo,
  usuarioAdminDeEjemplo,
} from '../../../testing/admin';
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
import type { ListaUsuariosApi } from './datos';

describe('Administración: usuarios', () => {
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
  const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms));
  /** El texto visible, con un espacio entre elementos (como lo lee un lector de pantalla). */
  const texto = (el: Element | null | undefined) => {
    if (!el) {
      return undefined;
    }
    const partes: string[] = [];
    const recorrido = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (recorrido.nextNode()) {
      partes.push(recorrido.currentNode.textContent ?? '');
    }
    return partes.join(' ').replace(/\s+/g, ' ').trim();
  };

  async function abrir(
    ruta = '/admin/usuarios',
    lista: ListaUsuariosApi | null = listaDeEjemplo(),
  ) {
    entrarComo(DIEGO);
    const harness = await RouterTestingHarness.create(ruta);
    const raiz = harness.routeNativeElement as HTMLElement;
    const listo = async () => {
      await pendientes();
      await harness.fixture.whenStable();
    };
    api.expectOne('/api/admin/aprobados-pendientes').flush([aprobadoDeEjemplo()]);
    if (lista) {
      pedidoLista().flush(lista);
    }
    await listo();
    return { raiz, listo, harness };
  }

  function pedidoLista(): TestRequest {
    return api.expectOne((r) => r.url === '/api/admin/usuarios');
  }

  const parametros = (pedido: TestRequest) =>
    Object.fromEntries(pedido.request.params.keys().map((k) => [k, pedido.request.params.get(k)]));

  /** Abre el menú «⋯» de una fila y elige una acción. */
  async function accion(
    raiz: HTMLElement,
    username: string,
    nombre: string,
    listo: () => Promise<void>,
  ) {
    raiz.querySelector<HTMLButtonElement>(`button[aria-label="Acciones de ${username}"]`)!.click();
    await listo();
    const item = Array.from(
      document.querySelectorAll<HTMLElement>('.mat-mdc-menu-panel [mat-menu-item]'),
    ).find((b) => b.textContent?.trim() === nombre);
    if (!item) {
      throw new Error(`No hay «${nombre}» en el menú`);
    }
    item.click();
    await listo();
  }

  const dialogo = () => document.querySelector('mat-dialog-container:last-of-type')!;
  const botonDelDialogo = (nombre: string) =>
    Array.from(dialogo().querySelectorAll<HTMLButtonElement>('button')).find(
      (b) => b.textContent?.trim() === nombre,
    )!;

  it('la lista: estado de cada cuenta, avance de los estudiantes y 50 por página', async () => {
    const { raiz, listo } = await abrir('/admin/usuarios', null);
    const pedido = pedidoLista();
    expect(parametros(pedido)).toEqual({ pagina: '1', por_pagina: '50' });
    pedido.flush(listaDeEjemplo());
    await listo();
    const filas = Array.from(raiz.querySelectorAll('tbody tr'));
    expect(filas).toHaveLength(6);
    const estados = filas.map((f) => texto(f.querySelector('.chip')));
    expect(estados[0]).toBe('Activo');
    expect(estados[2]).toMatch(/^Bloqueado hasta /);
    expect(estados.slice(3, 5)).toEqual(['Debe cambiar la clave', 'Dado de baja']);
    expect(texto(filas[0].querySelector('.avance'))).toBe('52 %');
    // Un instructor no tiene avance del curso.
    expect(filas[1].querySelector('.avance')).toBeNull();
    expect(filas[0].querySelector('a')?.getAttribute('href')).toBe('/admin/usuarios/ana');
    expect(texto(raiz.querySelector('.paginas span'))).toBe('1–6 de 6');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('los filtros y la búsqueda (tras una pausa) piden de nuevo desde la página 1', async () => {
    const { raiz, listo } = await abrir(
      '/admin/usuarios',
      listaDeEjemplo(undefined, { total: 120 }),
    );
    botonCon(raiz, 'Siguiente').click();
    await listo();
    let pedido = pedidoLista();
    expect(parametros(pedido)['pagina']).toBe('2');
    pedido.flush(listaDeEjemplo(undefined, { total: 120, pagina: 2 }));
    await listo();

    const [cluster, rol, estado] = Array.from(
      raiz.querySelectorAll<HTMLSelectElement>('.barra-usuarios select'),
    );
    cluster.value = 'apolo3';
    cluster.dispatchEvent(new Event('change'));
    await listo();
    pedido = pedidoLista();
    expect(parametros(pedido)).toEqual({ pagina: '1', por_pagina: '50', cluster: 'apolo3' });
    pedido.flush(listaDeEjemplo());
    rol.value = 'estudiante';
    rol.dispatchEvent(new Event('change'));
    await listo();
    pedidoLista().flush(listaDeEjemplo());
    estado.value = 'bloqueado';
    estado.dispatchEvent(new Event('change'));
    await listo();
    pedido = pedidoLista();
    expect(parametros(pedido)).toMatchObject({ rol: 'estudiante', estado: 'bloqueado' });
    pedido.flush(listaDeEjemplo([]));
    await listo();
    expect(texto(raiz.querySelector('.vacio'))).toBe(
      'Ningún usuario coincide con la búsqueda o los filtros.',
    );

    const busqueda = raiz.querySelector<HTMLInputElement>('input[type=search]')!;
    busqueda.value = 'di';
    busqueda.dispatchEvent(new Event('input'));
    busqueda.value = 'diego';
    busqueda.dispatchEvent(new Event('input'));
    await listo();
    api.expectNone((r) => r.url === '/api/admin/usuarios');
    await esperar(350);
    await listo();
    pedido = pedidoLista();
    expect(parametros(pedido)['q']).toBe('diego');
    pedido.flush(listaDeEjemplo([usuarioAdminDeEjemplo({ username: 'diego' })]));
    await listo();
  });

  it('reiniciar la clave: pregunta, muestra la clave una vez y recarga', async () => {
    const { raiz, listo } = await abrir();
    await accion(raiz, 'ana', 'Reiniciar clave de la plataforma', listo);
    expect(texto(dialogo().querySelector('h2'))).toBe('¿Reiniciar la clave de ana?');
    botonDelDialogo('Reiniciar la clave').click();
    await listo();
    const pedido = api.expectOne('/api/admin/usuarios/ana/reiniciar-clave');
    expect(pedido.request.method).toBe('POST');
    pedido.flush({ username: 'ana', clave_temporal: 'Kq7vRt2pLm9xWa' });
    await listo();
    expect(texto(dialogo().querySelector('h2'))).toBe('Clave temporal de ana');
    expect(texto(dialogo().querySelector('at-comando code'))).toBe('Kq7vRt2pLm9xWa');
    expect(texto(dialogo())).toContain('la de la VM de práctica se cambia allá');
    botonDelDialogo('Ya la copié').click();
    await listo();
    pedidoLista().flush(listaDeEjemplo());
    await listo();
    expect(texto(raiz.querySelector('[role=status]'))).toContain('Clave de ana reiniciada.');
  });

  it('a una cuenta dada de baja no se le reinicia la clave', async () => {
    const { raiz, listo } = await abrir();
    raiz.querySelector<HTMLButtonElement>('button[aria-label="Acciones de gabriela"]')!.click();
    await listo();
    const item = Array.from(
      document.querySelectorAll<HTMLButtonElement>('.mat-mdc-menu-panel button'),
    ).find((b) => b.textContent?.trim() === 'Reiniciar clave de la plataforma')!;
    expect(item.disabled).toBe(true);
  });

  it('si la API dice que la cuenta está de baja (409), lo explica', async () => {
    const { raiz, listo } = await abrir();
    await accion(raiz, 'ana', 'Reiniciar clave de la plataforma', listo);
    botonDelDialogo('Reiniciar la clave').click();
    await listo();
    api
      .expectOne('/api/admin/usuarios/ana/reiniciar-clave')
      .flush(errorApi('usuario_inactivo'), { status: 409, statusText: 'Conflict' });
    await listo();
    expect(texto(raiz.querySelector('[role=alert]'))).toBe(
      'Esa cuenta está dada de baja: no se le puede reiniciar la clave.',
    );
  });

  it('cambiar el rol: elige, guarda y recarga; el último admin se explica en el diálogo', async () => {
    const { raiz, listo } = await abrir();
    await accion(raiz, 'ana', 'Cambiar rol…', listo);
    expect(texto(dialogo().querySelector('h2'))).toBe('Cambiar el rol de ana');
    const radios = dialogo().querySelectorAll<HTMLInputElement>('input[type=radio]');
    expect(Array.from(radios).map((r) => r.checked)).toEqual([true, false, false]);
    radios[1].click();
    await listo();
    botonDelDialogo('Guardar').click();
    await listo();
    let pedido = api.expectOne('/api/admin/usuarios/ana');
    expect(pedido.request.method).toBe('PATCH');
    expect(pedido.request.body).toEqual({ rol: 'instructor' });
    pedido.flush(usuarioAdminDeEjemplo({ rol: 'instructor' }));
    await listo();
    pedidoLista().flush(listaDeEjemplo());
    await listo();
    expect(texto(raiz.querySelector('[role=status]'))).toContain('ana ahora es Instructor.');

    await accion(raiz, 'elena', 'Cambiar rol…', listo);
    dialogo().querySelectorAll<HTMLInputElement>('input[type=radio]')[0].click();
    await listo();
    botonDelDialogo('Guardar').click();
    await listo();
    pedido = api.expectOne('/api/admin/usuarios/elena');
    pedido.flush(errorApi('ultimo_admin'), { status: 409, statusText: 'Conflict' });
    await listo();
    expect(texto(dialogo().querySelector('[role=alert]'))).toContain('es el último admin activo');
    botonDelDialogo('Cancelar').click();
    await listo();
    expect(document.querySelector('mat-dialog-container')).toBeNull();
  });

  it('si un admin se quita a sí mismo el rol, se relee su perfil y sale de la administración', async () => {
    const yo = usuarioAdminDeEjemplo({ username: 'diego', nombre: 'Diego', rol: 'admin' });
    const { raiz, listo } = await abrir('/admin/usuarios', listaDeEjemplo([yo]));
    await accion(raiz, 'diego', 'Cambiar rol…', listo);
    dialogo().querySelectorAll<HTMLInputElement>('input[type=radio]')[1].click();
    await listo();
    expect(texto(dialogo())).toContain('Es tu propio rol');
    botonDelDialogo('Guardar').click();
    await listo();
    api.expectOne('/api/admin/usuarios/diego').flush({ ...yo, rol: 'instructor' });
    await listo();
    api.expectOne('/api/me').flush({ ...DIEGO, rol: 'instructor' });
    await listo();
    expect(TestBed.inject(Router).url).toBe('/cursos');
  });

  it('la página de un usuario: su cuenta, sus acciones y su progreso en modo lectura', async () => {
    const { raiz, listo } = await abrir('/admin/usuarios/ana', null);
    const pedido = api.expectOne((r) => r.url === '/api/admin/usuarios/ana');
    expect(pedido.request.params.get('lang')).toBe('es');
    pedido.flush(detalleDeEjemplo());
    await listo();
    expect(texto(raiz.querySelector('.cuenta h2'))).toBe('ana · Ana Ejemplo');
    expect(texto(raiz.querySelector('.cuenta .chip'))).toBe('Activo');
    expect(texto(raiz.querySelector('.datos dd'))).toBe('ana@example.com');
    expect(Array.from(raiz.querySelectorAll('.cifras li')).map((li) => texto(li))).toEqual([
      'Avance 33 %',
      'Módulos 1 de 3',
      'Prácticas 1 de 7',
      'Graduación Sin enviar',
    ]);
    expect(raiz.querySelectorAll('at-modulos-progreso details.modulo')).toHaveLength(3);
    // Un admin ve las lecciones de los módulos bloqueados como enlaces.
    expect(raiz.querySelector('.modulo-bloqueado .lecciones a')).not.toBeNull();
    const practicas = Array.from(raiz.querySelectorAll('section tbody tr'));
    expect(practicas).toHaveLength(7);
    expect(texto(practicas[4])).toMatch(/^Memoria Intentada 1042 .* OUT_OF_MEMORY con --mem=1G$/);
    // Sin el formulario de la graduación: es de solo lectura.
    expect(raiz.querySelector('textarea')).toBeNull();
    expect(botonCon(raiz, 'Reiniciar clave de la plataforma')).toBeTruthy();
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('la página de alguien que no existe lo dice', async () => {
    const { raiz, listo } = await abrir('/admin/usuarios/nadie', null);
    api
      .expectOne((r) => r.url === '/api/admin/usuarios/nadie')
      .flush(errorApi('no_encontrado'), { status: 404, statusText: 'Not Found' });
    await listo();
    expect(texto(raiz.querySelector('[role=alert] h2'))).toBe('No existe ese usuario');
  });
});
