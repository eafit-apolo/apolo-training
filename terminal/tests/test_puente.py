"""Paso 5: el puente con la PTY (entrada, salida y tamaño)."""

from tests.conftest import CABECERAS, CONECTADO, RUTA, cerrado


def entrada(datos: str) -> dict:
    return {"tipo": "entrada", "datos": datos}


def test_entrada_y_salida(cliente):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        ws.send_json(entrada("ls -l\r"))
        # La salida llega en marcos binarios, tal cual la dio el shell.
        assert ws.receive_bytes() == b"ls -l\r"


def test_la_entrada_va_tal_cual(cliente):
    # Con la PTY abierta no hay editor de línea: Retroceso, flechas o Ctrl+C
    # llegan intactos a la VM, que es la que los interpreta.
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        ws.send_json(entrada("ab\x7f\x1b[A\x03"))
        assert ws.receive_bytes() == b"ab\x7f\x1b[A\x03"


def test_tamano_antes_y_despues_de_conectar(cliente, ssh):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        ws.send_json({"tipo": "tamano", "columnas": 120, "filas": 32})
        ws.send_json(entrada("x"))
        ws.receive_bytes()
    conexion = ssh.conexiones[0]
    # La PTY se abre con 80x24 si xterm no avisó antes, y luego cambia.
    assert conexion.term_size == (80, 24)
    assert conexion.proceso.tamanos == [(120, 32)]


def test_tamano_invalido_se_ignora(cliente, ssh):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        ws.send_json({"tipo": "tamano", "columnas": 0, "filas": 99999})
        ws.send_json(entrada("x"))
        ws.receive_bytes()
    assert ssh.conexiones[0].proceso.tamanos == []


def test_exit_cierra_sin_motivo(cliente):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        ws.send_json(entrada("exit\r"))
        assert ws.receive_json() == cerrado()
