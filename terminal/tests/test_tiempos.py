"""Paso 6: cierre por inactividad o tiempo máximo, y una sesión por usuario."""

import time

from tests.conftest import CABECERAS, CONECTADO, RUTA, cerrado


def test_cierre_por_inactividad(crear_cliente):
    cliente = crear_cliente(inactividad=0.3)
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        assert ws.receive_json() == cerrado("inactividad")


def test_escribir_reinicia_la_inactividad(crear_cliente):
    cliente = crear_cliente(inactividad=0.5)
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        inicio = time.monotonic()
        # Escribe cada 0.2 s durante 0.8 s: más que la inactividad permitida.
        for _ in range(4):
            time.sleep(0.2)
            ws.send_json({"tipo": "entrada", "datos": "x"})
            assert ws.receive_bytes() == b"x"
        assert time.monotonic() - inicio > 0.5
        assert ws.receive_json() == cerrado("inactividad")


def test_cierre_por_tiempo_maximo(crear_cliente):
    cliente = crear_cliente(maximo=0.3)
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
        assert ws.receive_json() == cerrado("tiempo_maximo")


def test_segunda_sesion_cierra_la_primera(cliente):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as primera:
        assert primera.receive_json() == CONECTADO
        with cliente.websocket_connect(RUTA, headers=CABECERAS) as segunda:
            assert segunda.receive_json() == CONECTADO
            assert primera.receive_json() == cerrado("otra_sesion")
            # La segunda sigue funcionando.
            segunda.send_json({"tipo": "entrada", "datos": "hola"})
            assert segunda.receive_bytes() == b"hola"


def test_tras_reemplazo_una_tercera_tambien_cierra_la_segunda(cliente):
    # Si la primera, al terminar, borrara del registro a la segunda, la tercera
    # no la encontraría y quedarían dos abiertas.
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as primera:
        primera.receive_json()
        with cliente.websocket_connect(RUTA, headers=CABECERAS) as segunda:
            segunda.receive_json()
            assert primera.receive_json() == cerrado("otra_sesion")
            with cliente.websocket_connect(RUTA, headers=CABECERAS) as tercera:
                assert tercera.receive_json() == CONECTADO
                assert segunda.receive_json() == cerrado("otra_sesion")
