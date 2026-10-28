"""El WebSocket solo sigue abierto con una sesión válida de la plataforma."""

import httpx

from tests.conftest import CABECERAS, CONECTADO, ORIGEN, RUTA, cerrado


def test_sin_cookie_la_sesion_es_invalida(cliente, ssh):
    with cliente.websocket_connect(RUTA, headers={"origin": ORIGEN}) as ws:
        assert ws.receive_json() == cerrado("sesion_invalida")
    assert ssh.usuarios == []


def test_cookie_ajena_la_sesion_es_invalida(cliente, ssh):
    cabeceras = {"origin": ORIGEN, "cookie": "at=token-inventado"}
    with cliente.websocket_connect(RUTA, headers=cabeceras) as ws:
        assert ws.receive_json() == cerrado("sesion_invalida")
    assert ssh.usuarios == []


def test_api_caida_cierra_con_error(crear_cliente, ssh):
    async def api_caida(_cookie_at: str | None) -> str:
        raise httpx.ConnectError("la API no responde")

    with crear_cliente(validar=api_caida).websocket_connect(
        RUTA, headers=CABECERAS
    ) as ws:
        assert ws.receive_json() == cerrado("error")
    assert ssh.usuarios == []


def test_entra_a_la_vm_como_el_usuario_de_la_sesion(cliente, ssh):
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_json() == CONECTADO
    assert ssh.usuarios == ["ana"]
