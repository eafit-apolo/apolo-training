"""La contraseña por la terminal del navegador, y a dónde se conecta el SSH."""

import logging

import asyncssh

from app.config import Settings
from app.ssh import conectar_ssh
from tests.conftest import CABECERAS, CLAVE, CONECTADO, RUTA, SSHFalso, cerrado


def entrada(datos: str) -> dict:
    return {"tipo": "entrada", "datos": datos}


def test_la_clave_no_se_ve_ni_se_registra(crear_cliente, caplog):
    cliente = crear_cliente(conectar=SSHFalso(pedir_clave=True))
    with (
        caplog.at_level(logging.DEBUG),
        cliente.websocket_connect(RUTA, headers=CABECERAS) as ws,
    ):
        assert ws.receive_bytes() == b"Password: "
        # Letra por letra, como xterm, con un error corregido con Retroceso.
        for caracter in CLAVE[:-1] + "x\x7f" + CLAVE[-1]:
            ws.send_json(entrada(caracter))
        ws.send_json(entrada("\r"))
        # Sin eco: solo el salto de línea, ningún carácter de la clave.
        assert ws.receive_bytes() == b"\r\n"
        assert ws.receive_json() == CONECTADO
    assert CLAVE not in caplog.text


def test_mensajes_que_no_son_entrada_se_ignoran(crear_cliente):
    cliente = crear_cliente(conectar=SSHFalso(pedir_clave=True))
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_bytes() == b"Password: "
        ws.send_json({"tipo": "conectar", "host": "otra-maquina", "usuario": "root"})
        ws.send_text("esto no es JSON")
        ws.send_json(entrada(f"{CLAVE}\r"))
        assert ws.receive_bytes() == b"\r\n"
        assert ws.receive_json() == CONECTADO


def test_clave_errada(crear_cliente):
    cliente = crear_cliente(conectar=SSHFalso(pedir_clave=True))
    with cliente.websocket_connect(RUTA, headers=CABECERAS) as ws:
        assert ws.receive_bytes() == b"Password: "
        ws.send_json(entrada("otra-clave\r"))
        assert ws.receive_bytes() == b"\r\n"
        assert ws.receive_json() == cerrado("ssh_rechazado")


def test_vm_inalcanzable(crear_cliente):
    async def sin_red(_username, _terminal):
        raise OSError("No route to host")

    with crear_cliente(conectar=sin_red).websocket_connect(
        RUTA, headers=CABECERAS
    ) as ws:
        assert ws.receive_json() == cerrado("error")


async def test_ssh_va_siempre_a_la_vm_de_practica(monkeypatch):
    """conectar_ssh real, sin red: se reemplaza asyncssh.create_connection."""
    llamada = {}

    async def create_connection(_fabrica, host, port, **opciones):
        llamada.update(host=host, port=port, **opciones)
        return "conexion", None

    monkeypatch.setattr(asyncssh, "create_connection", create_connection)
    settings = Settings(ssh_host="vm-practica.test", known_hosts="/kh")

    assert await conectar_ssh(settings, "ana", terminal=None) == "conexion"
    assert llamada["host"] == "vm-practica.test"
    assert llamada["port"] == 22
    assert llamada["username"] == "ana"
    # Verifica la llave del servidor y no usa llaves propias.
    assert llamada["known_hosts"] == "/kh"
    assert llamada["preferred_auth"] == "keyboard-interactive"
    assert llamada["client_keys"] is None
    # connect_timeout incluiría el tiempo de escribir la clave: con 10 s, la
    # conexión se cortaba mientras el usuario escribía. Solo login_timeout.
    assert "connect_timeout" not in llamada
    assert llamada["login_timeout"] == 120
