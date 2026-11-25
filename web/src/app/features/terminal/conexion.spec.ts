import { WebSocketDePrueba } from '../../../testing/terminal';
import { ConexionTerminal, TROZO, trozos, urlTerminal } from './conexion';

describe('Conexión con el gateway de terminal (T-06)', () => {
  let ws: WebSocketDePrueba;
  let recibido: string;

  function conectar(): ConexionTerminal {
    recibido = '';
    return new ConexionTerminal(
      (url) => {
        ws = new WebSocketDePrueba(url);
        return ws as unknown as WebSocket;
      },
      'wss://training.apolo.eafit.edu.co/ws/terminal',
      (datos) => (recibido += new TextDecoder().decode(datos)),
    );
  }

  it('la URL es la del mismo origen, wss en https y ws en local', () => {
    expect(urlTerminal({ protocol: 'https:', host: 'training.apolo.eafit.edu.co' })).toBe(
      'wss://training.apolo.eafit.edu.co/ws/terminal',
    );
    expect(urlTerminal({ protocol: 'http:', host: 'localhost:4200' })).toBe(
      'ws://localhost:4200/ws/terminal',
    );
  });

  it('pide los marcos binarios como ArrayBuffer y empieza conectando', () => {
    const conexion = conectar();
    expect(ws.binaryType).toBe('arraybuffer');
    expect(conexion.estado()).toEqual({ fase: 'conectando' });
  });

  it('el tamaño que llega antes de abrir se manda al abrir, y solo si cambia', () => {
    const conexion = conectar();
    conexion.cambiarTamano(120, 32);
    expect(ws.enviados).toEqual([]);

    ws.abrir();
    conexion.cambiarTamano(120, 32);
    conexion.cambiarTamano(100, 30);
    expect(ws.mensajes()).toEqual([
      { tipo: 'tamano', columnas: 120, filas: 32 },
      { tipo: 'tamano', columnas: 100, filas: 30 },
    ]);
  });

  it('lo que se teclea va como entrada; antes de abrir no se manda nada', () => {
    const conexion = conectar();
    conexion.enviar('ls');
    ws.abrir();
    conexion.enviar('ls -l\r');
    expect(ws.mensajes()).toEqual([{ tipo: 'entrada', datos: 'ls -l\r' }]);
  });

  it('un texto pegado muy largo va en trozos que el gateway acepta', () => {
    const conexion = conectar();
    ws.abrir();
    conexion.enviar('a'.repeat(TROZO * 2 + 5));
    const tamanos = ws.mensajes().map((m) => (m as { datos: string }).datos.length);
    expect(tamanos).toEqual([TROZO, TROZO, 5]);
  });

  it('los trozos no parten un emoji', () => {
    const partes = trozos('ab😀cd', 3);
    expect(partes).toEqual(['ab', '😀c', 'd']);
    expect(partes.join('')).toBe('ab😀cd');
  });

  it('la salida binaria llega tal cual a la pantalla', () => {
    conectar();
    ws.abrir();
    ws.salida('Password: ');
    ws.salida('[prueba-v03@apolo-training ~ (apolo2)]$ ');
    expect(recibido).toBe('Password: [prueba-v03@apolo-training ~ (apolo2)]$ ');
  });

  it('con «conectado» queda conectada', () => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('conectado');
    expect(conexion.estado()).toEqual({ fase: 'conectada' });
  });

  it.each([
    'inactividad',
    'tiempo_maximo',
    'otra_sesion',
    'ssh_rechazado',
    'sesion_invalida',
    'error',
  ])('«cerrado» con motivo %s la cierra con ese motivo', (motivo) => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('cerrado', motivo);
    // El gateway cierra el WebSocket después: el motivo no cambia.
    ws.cerrarDesdeElServidor();
    expect(conexion.estado()).toEqual({ fase: 'cerrada', motivo });
  });

  it('«cerrado» sin motivo es que el usuario salió del shell (exit)', () => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('conectado');
    ws.estado('cerrado');
    expect(conexion.estado()).toEqual({ fase: 'cerrada', motivo: 'salida' });
  });

  it('un motivo que no conoce se trata como error', () => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('cerrado', 'otro');
    expect(conexion.estado()).toEqual({ fase: 'cerrada', motivo: 'error' });
  });

  it('si el WebSocket se cierra sin avisar (o el gateway lo rechaza), se perdió la conexión', () => {
    const conexion = conectar();
    ws.cerrarDesdeElServidor();
    expect(conexion.estado()).toEqual({ fase: 'cerrada', motivo: 'conexion' });
  });

  it('ignora los marcos de texto que no son un estado', () => {
    const conexion = conectar();
    ws.abrir();
    ws.texto('no es JSON');
    ws.texto('{"tipo":"otro"}');
    expect(conexion.estado()).toEqual({ fase: 'conectando' });
    expect(recibido).toBe('');
  });

  it('cerrada ya no manda lo que se teclea', () => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('cerrado', 'inactividad');
    conexion.enviar('ls\r');
    expect(ws.enviados).toEqual([]);
  });

  it('si la cierra la app, cierra el WebSocket sin cambiar de estado', () => {
    const conexion = conectar();
    ws.abrir();
    ws.estado('conectado');
    conexion.cerrar();
    expect(ws.cerradoPorLaApp).toBe(true);
    ws.cerrarDesdeElServidor();
    expect(conexion.estado()).toEqual({ fase: 'conectada' });
  });
});
