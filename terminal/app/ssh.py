"""Conexión SSH a la VM de práctica con keyboard-interactive.

El servidor (sshd con PAM) manda las preguntas: «Password:» y, en el primer
ingreso, las de cambio de clave. El gateway las muestra en la terminal del
navegador y devuelve lo que el usuario escribe. No guarda ni registra las
respuestas: solo existen en memoria mientras dura la autenticación.
"""

from typing import Protocol

import asyncssh

from app.config import Settings


class Terminal(Protocol):
    """Lo que la conexión necesita del lado del navegador (ver sesion.Sesion)."""

    async def mostrar(self, texto: str) -> None: ...

    async def pedir(self, pregunta: str, eco: bool) -> str: ...


class _Cliente(asyncssh.SSHClient):
    """asyncssh llama a estos métodos durante la autenticación."""

    def __init__(self, terminal: Terminal) -> None:
        self._terminal = terminal
        # El aviso de sshd (Banner, /etc/issue.net), pendiente de mostrar.
        self._banner = ""

    def auth_banner_received(self, msg: str, lang: str) -> None:
        # Llega antes de la primera pregunta. Este método no es async: se
        # guarda y se muestra junto con la pregunta.
        self._banner += msg

    def kbdint_auth_requested(self) -> str:
        # Cadena vacía: que el servidor decida qué preguntar (PAM).
        return ""

    async def kbdint_challenge_received(
        self,
        name: str,
        instructions: str,
        lang: str,
        prompts: list[tuple[str, bool]],
    ) -> list[str]:
        if self._banner:
            # xterm necesita \r\n; el banner puede traer \n o \r\n.
            texto = self._banner.replace("\r\n", "\n").replace("\n", "\r\n")
            self._banner = ""
            await self._terminal.mostrar(texto)
        # instructions trae avisos de PAM, como el de clave vencida.
        if instructions:
            await self._terminal.mostrar(instructions.replace("\n", "\r\n"))
        # Cada pregunta viene con su eco: False para contraseñas.
        return [await self._terminal.pedir(pregunta, eco) for pregunta, eco in prompts]


async def conectar_ssh(
    settings: Settings, username: str, terminal: Terminal
) -> asyncssh.SSHClientConnection:
    """Abre SSH a la VM de práctica como `username`.

    El host, el puerto y la llave del servidor salen de la configuración; el
    usuario, de la sesión de la plataforma. Nada de esto lo elige el navegador.
    """
    conexion, _ = await asyncssh.create_connection(
        lambda: _Cliente(terminal),
        settings.ssh_host,
        settings.ssh_puerto,
        username=username,
        known_hosts=settings.known_hosts,
        # Solo la contraseña que escribe el usuario: sin llaves ni agente.
        preferred_auth="keyboard-interactive",
        client_keys=None,
        agent_path=None,
        # Sin connect_timeout: en asyncssh incluye la autenticación, o sea, el
        # tiempo que el usuario tarda en escribir la clave (y en el primer
        # ingreso, la clave nueva dos veces). login_timeout cuenta solo desde
        # que hay conexión; 120 s, igual que LoginGraceTime de sshd.
        login_timeout=120,
    )
    return conexion
