"""Piezas de la sesión (B-03): contraseñas, tokens, CSRF y cookies.

- Contraseñas con argon2id (argon2-cffi). Verificar cuesta ~50 ms de CPU, así
  que va en un hilo aparte para no frenar las demás peticiones.
- Cookie `at`: JWT HS256 de 15 min con el id del usuario (`sub`) y el de su
  sesión (`sid`). No lleva el rol: se lee de la base en cada petición.
- Cookie `rt`: refresh token aleatorio de 7 días; la base solo guarda su sha256.
- Cookie `csrf`: HMAC del id de la sesión. La app la devuelve en la cabecera
  X-CSRF-Token en todo lo que no sea GET, y la API comprueba que cabecera,
  cookie y sesión coincidan (doble envío ligado a la sesión).
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from functools import cache

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings

DURACION_ACCESO = timedelta(minutes=15)
# Desde el último uso: cada renovación da 7 días más.
DURACION_REFRESH = timedelta(days=7)
INTENTOS_MAXIMOS = 5
DURACION_BLOQUEO = timedelta(minutes=15)
# Un refresh ya rotado que llega dentro de este margen es otra pestaña que
# renovó a la vez, no un robo.
GRACIA_REUSO = timedelta(seconds=30)

CLAVE_MINIMA = 8
CLAVE_MAXIMA = 128

COOKIE_ACCESO = "at"
COOKIE_REFRESH = "rt"
COOKIE_CSRF = "csrf"
CABECERA_CSRF = "X-CSRF-Token"
# rt solo viaja a las rutas de sesión.
RUTA_REFRESH = "/api/auth"
METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS"})

_ALGORITMO = "HS256"
_hasher = PasswordHasher()


def ahora() -> datetime:
    return datetime.now(UTC)


# --- Contraseñas -------------------------------------------------------------


async def hash_clave(clave: str) -> str:
    return await run_in_threadpool(_hasher.hash, clave)


def _verificar(clave_hash: str, clave: str) -> bool:
    try:
        return _hasher.verify(clave_hash, clave)
    except (VerificationError, InvalidHashError):
        return False


async def verificar_clave(clave_hash: str, clave: str) -> bool:
    return await run_in_threadpool(_verificar, clave_hash, clave)


@cache
def _hash_senuelo() -> str:
    return _hasher.hash(secrets.token_urlsafe(16))


async def verificar_senuelo(clave: str) -> None:
    """Gasta lo mismo que una verificación real cuando el usuario no existe."""
    await run_in_threadpool(_verificar, _hash_senuelo(), clave)


def necesita_rehash(clave_hash: str) -> bool:
    return _hasher.check_needs_rehash(clave_hash)


# --- Tokens ------------------------------------------------------------------


def _secreto(settings: Settings) -> bytes:
    if settings.secreto is None:
        raise RuntimeError("Falta API_SECRETO")
    return settings.secreto.get_secret_value().encode()


def crear_token_acceso(settings: Settings, usuario_id: int, sesion_id: int) -> str:
    momento = ahora()
    datos = {
        "sub": str(usuario_id),
        "sid": sesion_id,
        "iat": momento,
        "exp": momento + DURACION_ACCESO,
    }
    return jwt.encode(datos, _secreto(settings), algorithm=_ALGORITMO)


def leer_token_acceso(
    settings: Settings, token: str, *, verificar_vencimiento: bool = True
) -> tuple[int, int]:
    """Devuelve (usuario_id, sesion_id).

    Lanza jwt.ExpiredSignatureError si venció y jwt.InvalidTokenError si no es
    válido.
    """
    datos = jwt.decode(
        token,
        _secreto(settings),
        algorithms=[_ALGORITMO],
        options={
            "require": ["sub", "sid", "exp"],
            "verify_exp": verificar_vencimiento,
        },
    )
    try:
        return int(datos["sub"]), int(datos["sid"])
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("sub o sid no son números") from exc


def nuevo_refresh() -> tuple[str, str]:
    """Devuelve (token para la cookie, sha256 para la base)."""
    token = secrets.token_urlsafe(32)
    return token, hash_refresh(token)


def hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_csrf(settings: Settings, sesion_id: int) -> str:
    mensaje = f"csrf:{sesion_id}".encode()
    return hmac.new(_secreto(settings), mensaje, hashlib.sha256).hexdigest()


def csrf_valido(
    settings: Settings, sesion_id: int, cabecera: str | None, cookie: str | None
) -> bool:
    if not cabecera or not cookie:
        return False
    esperado = token_csrf(settings, sesion_id)
    return hmac.compare_digest(cabecera, cookie) and hmac.compare_digest(
        cabecera, esperado
    )


# --- Cookies -----------------------------------------------------------------


def poner_cookies(
    response: Response,
    settings: Settings,
    *,
    acceso: str,
    refresh: str,
    csrf: str,
) -> None:
    comunes = {"secure": settings.cookies_seguras, "samesite": "strict"}
    # at en / para que también la reciba el gateway de terminal.
    response.set_cookie(
        COOKIE_ACCESO,
        acceso,
        max_age=int(DURACION_ACCESO.total_seconds()),
        path="/",
        httponly=True,
        **comunes,
    )
    response.set_cookie(
        COOKIE_REFRESH,
        refresh,
        max_age=int(DURACION_REFRESH.total_seconds()),
        path=RUTA_REFRESH,
        httponly=True,
        **comunes,
    )
    # La app la lee para mandarla en X-CSRF-Token; dura lo mismo que rt para
    # que la renovación la tenga aunque at haya vencido.
    response.set_cookie(
        COOKIE_CSRF,
        csrf,
        max_age=int(DURACION_REFRESH.total_seconds()),
        path="/",
        httponly=False,
        **comunes,
    )


def borrar_cookies(response: Response, settings: Settings) -> None:
    comunes = {"secure": settings.cookies_seguras, "samesite": "strict"}
    response.delete_cookie(COOKIE_ACCESO, path="/", httponly=True, **comunes)
    response.delete_cookie(COOKIE_REFRESH, path=RUTA_REFRESH, httponly=True, **comunes)
    response.delete_cookie(COOKIE_CSRF, path="/", httponly=False, **comunes)
