"""El WebSocket solo se abre desde la plataforma y sin parámetros en la URL."""

import pytest
from fastapi import WebSocketDisconnect, status

from tests.conftest import CABECERAS, CONECTADO, RUTA


def test_desde_la_plataforma_se_acepta(cliente):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO


@pytest.mark.parametrize(
    "cabeceras",
    [
        {"origin": "https://otro-sitio.example"},  # otra página
        {},  # sin Origin: no viene de un navegador
    ],
)
def test_otro_origen_se_rechaza(cliente, ssh, cabeceras):
    with (
        pytest.raises(WebSocketDisconnect) as error,
        cliente.websocket_connect(RUTA, headers=cabeceras),
    ):
        pass
    assert error.value.code == status.WS_1008_POLICY_VIOLATION
    assert ssh.usuarios == []


def test_no_se_puede_elegir_host_ni_usuario(cliente, ssh):
    # Con la cookie de ana y parámetros en la URL: se rechaza antes de abrir nada.
    with (
        pytest.raises(WebSocketDisconnect) as error,
        cliente.websocket_connect(
            f"{RUTA}?host=otra-maquina&usuario=root", headers=CABECERAS
        ),
    ):
        pass
    assert error.value.code == status.WS_1008_POLICY_VIOLATION
    assert ssh.usuarios == []

    # Sin parámetros, el usuario SSH es el de la sesión de la plataforma.
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        ws.receive_json()
    assert ssh.usuarios == ["ana"]
