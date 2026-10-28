"""Paso 7: se registran el inicio y el fin de cada sesión, nunca el contenido."""

import logging

from tests.conftest import CABECERAS, CONECTADO, RUTA


def test_inicio_y_fin_sin_contenido(cliente, caplog):
    secreto = "cat notas-privadas.txt"
    with (
        caplog.at_level(logging.DEBUG),
        cliente.websocket_connect(RUTA, headers=CABECERAS) as ws,
    ):
        assert ws.receive_json() == CONECTADO
        ws.send_json({"tipo": "entrada", "datos": f"{secreto}\r"})
        ws.receive_bytes()
        ws.send_json({"tipo": "entrada", "datos": "exit\r"})
        ws.receive_json()

    mensajes = [r.getMessage() for r in caplog.records if r.name == "terminal"]
    assert mensajes[0] == "inicio usuario=ana"
    assert mensajes[1].startswith("fin usuario=ana motivo=None duracion=")
    # Ni lo que escribió ni lo que respondió el shell.
    assert secreto not in caplog.text


def test_el_motivo_queda_en_el_log(crear_cliente, caplog):
    cliente = crear_cliente(inactividad=0.2)
    with (
        caplog.at_level(logging.INFO),
        cliente.websocket_connect(RUTA, headers=CABECERAS) as ws,
    ):
        ws.receive_json()
        ws.receive_json()
    assert "fin usuario=ana motivo=inactividad" in caplog.text
