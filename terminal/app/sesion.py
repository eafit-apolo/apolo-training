"""Una sesión de terminal: el puente entre el WebSocket y el SSH.

Mientras dura, corren a la vez tres tareas:

- el SSH: primero la autenticación y después el puente con la PTY, con dos
  copias en paralelo (navegador → SSH y SSH → navegador);
- el vigía de tiempos: 15 minutos sin escribir o 2 horas en total;
- la espera de otra sesión del mismo usuario, que reemplaza a esta.

La primera que termina decide el motivo del cierre y las demás se cancelan.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import asyncssh
from fastapi import WebSocket, WebSocketDisconnect

from app import mensajes
from app.config import Settings
from app.mensajes import Entrada, Motivo, Tamano
from app.ssh import Terminal

log = logging.getLogger("terminal")

# Recibe el username y la terminal del navegador, y devuelve la conexión SSH.
Conectar = Callable[[str, Terminal], Awaitable[asyncssh.SSHClientConnection]]


async def primera[T](*corrutinas: Coroutine[Any, Any, T]) -> T:
    """Corre las corrutinas a la vez y devuelve el resultado de la primera que
    termina (o relanza su error). Las demás se cancelan siempre, también si la
    tarea que llama a esta función es cancelada.
    """
    tareas = [asyncio.create_task(c) for c in corrutinas]
    try:
        hechas, _ = await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
        return hechas.pop().result()
    finally:
        for tarea in tareas:
            tarea.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)


class Sesion:
    def __init__(
        self, ws: WebSocket, username: str, settings: Settings, conectar: Conectar
    ) -> None:
        self.ws = ws
        self.username = username
        self._settings = settings
        self._conectar = conectar
        self.inicio = time.monotonic()
        self._ultima_entrada = self.inicio
        # Tamaño de xterm; puede llegar antes de que exista la PTY.
        self._tamano = (80, 24)
        self._proceso: asyncssh.SSHClientProcess | None = None
        self._reemplazada = asyncio.Event()
        # False cuando el navegador se fue: ya no hay a quién avisarle.
        self.navegador_conectado = True

    async def correr(self) -> Motivo | None:
        """Corre hasta que algo cierra la sesión.

        None si el usuario salió del shell (exit) o cerró la pestaña.
        """
        return await primera(self._ssh(), self._vigilar(), self._esperar_reemplazo())

    def reemplazar(self) -> None:
        """Otra sesión del mismo usuario empezó: esta termina con otra_sesion."""
        self._reemplazada.set()

    # Lo que pide ssh.Terminal, para la autenticación.

    async def mostrar(self, texto: str) -> None:
        # Lo que se muestra en xterm va en marcos binarios (bytes tal cual).
        await self.ws.send_bytes(texto.encode())

    async def pedir(self, pregunta: str, eco: bool) -> str:
        """Muestra la pregunta del servidor y lee una línea.

        Hace de editor de línea, porque todavía no hay terminal del lado de la
        VM: Enter termina y Retroceso borra. Sin eco (contraseñas) no se
        muestra nada de lo que se escribe.
        """
        await self.mostrar(pregunta)
        linea: list[str] = []
        while True:
            for caracter in await self._siguiente_entrada():
                if caracter in "\r\n":
                    await self.mostrar("\r\n")
                    return "".join(linea)
                if caracter in "\x7f\b":  # Retroceso
                    if linea:
                        linea.pop()
                        if eco:
                            await self.mostrar("\b \b")
                elif caracter.isprintable():
                    linea.append(caracter)
                    if eco:
                        await self.mostrar(caracter)

    # Las tres tareas de correr().

    async def _ssh(self) -> Motivo | None:
        try:
            async with await self._conectar(self.username, self) as conexion:
                # PTY con el tamaño de xterm; encoding=None: bytes, sin decodificar.
                proceso = await conexion.create_process(
                    term_type="xterm-256color", term_size=self._tamano, encoding=None
                )
                self._proceso = proceso
                await self.ws.send_json(mensajes.estado("conectado"))
                return await primera(
                    self._ssh_a_navegador(proceso), self._navegador_a_ssh(proceso)
                )
        except WebSocketDisconnect:
            self.navegador_conectado = False
            return None
        except asyncssh.PermissionDenied:
            return "ssh_rechazado"
        except (OSError, asyncssh.Error) as exc:
            # Red, DNS, llave del servidor distinta... El mensaje de asyncssh
            # describe la conexión, nunca lo que el usuario escribió.
            # El tipo va aparte: un TimeoutError no trae mensaje.
            log.warning(
                "ssh falló usuario=%s error=%s %s",
                self.username,
                type(exc).__name__,
                exc,
            )
            return "error"

    async def _vigilar(self) -> Motivo:
        while True:
            ahora = time.monotonic()
            fin_maximo = self.inicio + self._settings.maximo
            fin_inactividad = self._ultima_entrada + self._settings.inactividad
            if ahora >= fin_maximo:
                return "tiempo_maximo"
            if ahora >= fin_inactividad:
                return "inactividad"
            # Duerme hasta el plazo más cercano y vuelve a mirar: quizá el
            # usuario escribió mientras tanto.
            await asyncio.sleep(min(fin_maximo, fin_inactividad) - ahora)

    async def _esperar_reemplazo(self) -> Motivo:
        await self._reemplazada.wait()
        return "otra_sesion"

    # El puente, cuando la autenticación ya pasó.

    async def _ssh_a_navegador(self, proceso: asyncssh.SSHClientProcess) -> None:
        while datos := await proceso.stdout.read(64 * 1024):
            await self.ws.send_bytes(datos)
        # Fin de la salida: el shell terminó (exit o Ctrl+D).

    async def _navegador_a_ssh(self, proceso: asyncssh.SSHClientProcess) -> None:
        while True:
            datos = await self._siguiente_entrada()
            # Tal cual, sin editor de línea: ahora la PTY de la VM lo procesa.
            proceso.stdin.write(datos.encode())

    async def _siguiente_entrada(self) -> str:
        """Espera lo próximo que escriba el usuario.

        Los cambios de tamaño se aplican aquí mismo y los mensajes inválidos se
        ignoran. Lanza WebSocketDisconnect si el navegador se fue.
        """
        while True:
            marco = await self.ws.receive()
            if marco["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(marco.get("code", 1000))
            # Un marco binario no trae "text": también se ignora.
            mensaje = mensajes.leer(marco.get("text") or "")
            if isinstance(mensaje, Tamano):
                self._tamano = (mensaje.columnas, mensaje.filas)
                if self._proceso is not None:
                    self._proceso.change_terminal_size(*self._tamano)
            elif isinstance(mensaje, Entrada):
                self._ultima_entrada = time.monotonic()
                return mensaje.datos


class Registro:
    """La sesión abierta de cada usuario.

    Vive en memoria: por eso el gateway corre en un solo proceso. Con dos, cada
    uno tendría su propio registro y no vería las sesiones del otro.
    """

    def __init__(self) -> None:
        self._abiertas: dict[str, Sesion] = {}

    def abrir(self, sesion: Sesion) -> None:
        anterior = self._abiertas.get(sesion.username)
        if anterior is not None:
            anterior.reemplazar()
        self._abiertas[sesion.username] = sesion

    def cerrar(self, sesion: Sesion) -> None:
        # Solo si sigue siendo la registrada: la que fue reemplazada termina
        # después de que la nueva ocupó su lugar, y no debe borrarla.
        if self._abiertas.get(sesion.username) is sesion:
            del self._abiertas[sesion.username]
