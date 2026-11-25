import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import type { ComponentFixture } from '@angular/core/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslocoService } from '@jsverse/transloco';
import type { MockInstance } from 'vitest';
import { problemasDeAccesibilidad } from '../../../testing/axe';
import { ANA, CARLA, botonCon, entrarComo } from '../../../testing/sesion';
import type { SimulacionTerminal } from '../../../testing/terminal';
import { simularTerminal } from '../../../testing/terminal';
import { traduccionesDePrueba } from '../../../testing/transloco';
import { SesionService } from '../../core/sesion/sesion';
import { TerminalReal } from './terminal-real';

/** Guarda el callback del ResizeObserver para simular un cambio de tamaño. */
class ObservadorDePrueba {
  static ultimo: ObservadorDePrueba | null = null;
  observados: Element[] = [];
  desconectado = false;

  constructor(readonly avisar: () => void) {
    ObservadorDePrueba.ultimo = this;
  }

  observe(elemento: Element): void {
    this.observados.push(elemento);
  }

  disconnect(): void {
    this.desconectado = true;
  }
}

describe('Terminal real (T-06)', () => {
  let sim: SimulacionTerminal;
  let fixture: ComponentFixture<TerminalReal>;
  let comprobar: MockInstance<SesionService['comprobar']>;

  beforeEach(() => {
    ObservadorDePrueba.ultimo = null;
    vi.stubGlobal('ResizeObserver', ObservadorDePrueba);
    sim = simularTerminal();
    TestBed.configureTestingModule({
      imports: [traduccionesDePrueba()],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        ...sim.providers,
      ],
    });
    entrarComo(ANA);
    comprobar = vi.spyOn(TestBed.inject(SesionService), 'comprobar').mockResolvedValue(undefined);
  });

  afterEach(() => vi.unstubAllGlobals());

  async function listo(): Promise<HTMLElement> {
    for (let i = 0; i < 3; i++) {
      await new Promise((r) => setTimeout(r));
      await fixture.whenStable();
    }
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  async function montar(completa = false): Promise<HTMLElement> {
    fixture = TestBed.createComponent(TerminalReal);
    fixture.componentRef.setInput('completa', completa);
    return listo();
  }

  /** Monta, pulsa «Abrir terminal» y deja el WebSocket abierto. */
  async function conectar(): Promise<HTMLElement> {
    const raiz = await montar();
    botonCon(raiz, 'Abrir terminal').click();
    await listo();
    sim.sockets[0].abrir();
    return listo();
  }

  const estado = (raiz: HTMLElement) =>
    raiz.querySelector('[role="status"]')?.textContent?.replace(/\s+/g, ' ').trim();
  const pantalla = (raiz: HTMLElement) => raiz.querySelector<HTMLElement>('.pantalla');

  it('empieza sin conectar, con «Abrir terminal», el enlace a otra pestaña y el aviso', async () => {
    const raiz = await montar();

    expect(estado(raiz)).toBe('Sin conectar');
    expect(botonCon(raiz, 'Abrir terminal')).toBeTruthy();
    const enlace = botonCon(raiz, 'Abrir en otra pestaña') as HTMLAnchorElement;
    expect(enlace.getAttribute('href')).toBe('/terminal');
    expect(enlace.target).toBe('_blank');
    expect(enlace.rel).toBe('noopener');
    expect(raiz.querySelector('.aviso')?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'Esta es la VM de práctica del curso, no Apolo II: tu clúster real es apolo.eafit.edu.co. ' +
        'Te pide la contraseña de la VM de práctica y se cierra tras 15 minutos sin escribir o a las 2 horas.',
    );
    // No se conecta sola ni descarga xterm.
    expect(pantalla(raiz)?.hidden).toBe(true);
    expect(sim.sockets).toHaveLength(0);
    expect(sim.pantallas).toHaveLength(0);
    expect(comprobar).not.toHaveBeenCalled();
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('a un usuario de Apolo III le dice su clúster real', async () => {
    entrarComo(CARLA);
    const raiz = await montar();
    expect(raiz.querySelector('.aviso')?.textContent).toContain(
      'no Apolo III: tu clúster real es apolo-3.eafit.edu.co.',
    );
  });

  it('«Abrir terminal» renueva la sesión, crea la pantalla y abre el WebSocket del mismo origen', async () => {
    comprobar.mockImplementation(async () => {
      // Primero la sesión: el gateway valida la cookie al conectar.
      expect(sim.sockets).toHaveLength(0);
    });
    const raiz = await montar();
    botonCon(raiz, 'Abrir terminal').click();
    await listo();

    expect(comprobar).toHaveBeenCalledTimes(1);
    expect(sim.sockets).toHaveLength(1);
    expect(sim.sockets[0].url).toBe(`ws://${location.host}/ws/terminal`);
    expect(estado(raiz)).toBe('Conectando a la VM de práctica…');
    expect(pantalla(raiz)?.hidden).toBe(false);
    expect(sim.pantallas[0].elemento).toBe(pantalla(raiz));
    expect(sim.pantallas[0].enfocada).toBe(1);
    expect(() => botonCon(raiz, 'Abrir terminal')).toThrow();

    // Al abrir, el tamaño de la pantalla.
    sim.sockets[0].abrir();
    expect(sim.sockets[0].mensajes()).toEqual([{ tipo: 'tamano', columnas: 100, filas: 30 }]);
  });

  it('dos clics seguidos abren una sola conexión', async () => {
    const raiz = await montar();
    const boton = botonCon(raiz, 'Abrir terminal');
    boton.click();
    boton.click();
    await listo();
    expect(sim.sockets).toHaveLength(1);
  });

  it('DoD 1: la VM pide la clave en la terminal, se conecta y lo que se teclea llega', async () => {
    const raiz = await conectar();
    const ws = sim.sockets[0];
    const xterm = sim.pantallas[0];

    ws.salida('apolo-training: VM de práctica del curso de inducción de Apolo.\r\nPassword: ');
    xterm.teclear('clave\r');
    ws.estado('conectado');
    ws.salida('[prueba-v03@apolo-training ~ (apolo2)]$ ');
    xterm.teclear('apolo-training verificar modulos\r');
    await listo();

    expect(estado(raiz)).toBe('Conectada a la VM de práctica · perfil Apolo II');
    expect(xterm.escrito).toContain('Password: ');
    expect(xterm.escrito).toContain('(apolo2)]$ ');
    expect(ws.mensajes().slice(1)).toEqual([
      { tipo: 'entrada', datos: 'clave\r' },
      { tipo: 'entrada', datos: 'apolo-training verificar modulos\r' },
    ]);
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('DoD 2: al cambiar el tamaño, ajusta la pantalla y le avisa al gateway', async () => {
    await conectar();
    const observador = ObservadorDePrueba.ultimo;
    expect(observador?.observados).toEqual([sim.pantallas[0].elemento]);

    sim.pantallas[0].tamano = { columnas: 80, filas: 24 };
    observador?.avisar();
    observador?.avisar();

    expect(sim.sockets[0].mensajes()).toEqual([
      { tipo: 'tamano', columnas: 100, filas: 30 },
      { tipo: 'tamano', columnas: 80, filas: 24 },
    ]);
  });

  it('DoD 3: al salir de la página cierra el WebSocket (y el gateway, la sesión SSH)', async () => {
    await conectar();
    sim.sockets[0].estado('conectado');
    fixture.destroy();
    expect(sim.sockets[0].cerradoPorLaApp).toBe(true);
    expect(sim.pantallas[0].destruida).toBe(true);
    expect(ObservadorDePrueba.ultimo?.desconectado).toBe(true);
  });

  it.each([
    ['inactividad', 'Se cerró después de 15 minutos sin escribir.'],
    ['tiempo_maximo', 'Se cerró porque llevaba 2 horas abierta.'],
    ['otra_sesion', 'Se cerró porque abriste la terminal en otra pestaña o ventana.'],
    ['ssh_rechazado', 'La VM de práctica no aceptó la contraseña.'],
    [
      'sesion_invalida',
      'Tu sesión en la plataforma terminó o te falta cambiar la contraseña. Reconecta para revisarlo.',
    ],
    ['error', 'No se pudo conectar con la VM de práctica. Intenta de nuevo en un momento.'],
    [undefined, 'Saliste de la sesión (exit).'],
  ])('cerrada con motivo %s: «%s» y «Reconectar»', async (motivo, mensaje) => {
    const raiz = await conectar();
    sim.sockets[0].estado('cerrado', motivo);
    sim.sockets[0].cerrarDesdeElServidor();
    await listo();

    expect(estado(raiz)).toBe(mensaje);
    expect(botonCon(raiz, 'Reconectar')).toBeTruthy();
    // La pantalla se queda con lo último que se vio.
    expect(pantalla(raiz)?.hidden).toBe(false);
  });

  it('si el WebSocket se cierra sin avisar, dice que se perdió la conexión', async () => {
    const raiz = await conectar();
    sim.sockets[0].cerrarDesdeElServidor();
    await listo();
    expect(estado(raiz)).toBe('Se perdió la conexión con la terminal.');
    expect(await problemasDeAccesibilidad(raiz)).toEqual([]);
  });

  it('«Reconectar» abre otra conexión en la misma pantalla, ya limpia', async () => {
    const raiz = await conectar();
    sim.sockets[0].salida('lo de antes');
    sim.sockets[0].estado('cerrado', 'inactividad');
    await listo();

    botonCon(raiz, 'Reconectar').click();
    await listo();

    expect(comprobar).toHaveBeenCalledTimes(2);
    expect(sim.sockets).toHaveLength(2);
    expect(sim.sockets[0].cerradoPorLaApp).toBe(true);
    expect(sim.pantallas).toHaveLength(1);
    expect(sim.pantallas[0].limpiezas).toBe(1);
    expect(sim.pantallas[0].escrito).toBe('');
    expect(estado(raiz)).toBe('Conectando a la VM de práctica…');
  });

  it('si no se puede comprobar la sesión, no abre el WebSocket', async () => {
    comprobar.mockRejectedValue(new Error('sin red'));
    const raiz = await montar();
    botonCon(raiz, 'Abrir terminal').click();
    await listo();

    expect(sim.sockets).toHaveLength(0);
    expect(estado(raiz)).toBe('Se perdió la conexión con la terminal.');
    expect(botonCon(raiz, 'Reconectar')).toBeTruthy();
  });

  it('si xterm no se puede cargar, lo dice', async () => {
    sim.fallarCarga = true;
    const raiz = await montar();
    botonCon(raiz, 'Abrir terminal').click();
    await listo();

    expect(sim.sockets).toHaveLength(0);
    expect(estado(raiz)).toBe('No se pudo cargar la terminal. Recarga la página.');
  });

  it('en /terminal (pantalla completa) se conecta al entrar y no ofrece otra pestaña', async () => {
    const raiz = await montar(true);
    expect(comprobar).toHaveBeenCalledTimes(1);
    expect(sim.sockets).toHaveLength(1);
    expect(fixture.nativeElement.classList).toContain('completa');
    expect(() => botonCon(raiz, 'Abrir en otra pestaña')).toThrow();
  });

  it('en inglés', async () => {
    TestBed.inject(TranslocoService).setActiveLang('en');
    const raiz = await montar();
    expect(estado(raiz)).toBe('Not connected');
    expect(botonCon(raiz, 'Open terminal')).toBeTruthy();
    expect(botonCon(raiz, 'Open in a new tab')).toBeTruthy();
    expect(raiz.querySelector('.aviso')?.textContent).toContain(
      'This is the course practice VM, not Apolo II: your real cluster is apolo.eafit.edu.co.',
    );
  });
});
