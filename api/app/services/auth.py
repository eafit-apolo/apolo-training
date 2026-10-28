"""Inicio y cierre de sesión, renovación y cambio de contraseña (B-03).

No sabe de cookies ni de Request: recibe los valores y devuelve los tokens; el
router los pone en la respuesta. Los errores salen como ErrorApi, con los
códigos del contrato.
"""

from dataclasses import dataclass
from datetime import datetime

import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errores import ErrorApi
from app.core.seguridad import (
    CLAVE_MINIMA,
    DURACION_BLOQUEO,
    DURACION_REFRESH,
    GRACIA_REUSO,
    INTENTOS_MAXIMOS,
    ahora,
    crear_token_acceso,
    csrf_valido,
    hash_clave,
    hash_refresh,
    leer_token_acceso,
    necesita_rehash,
    nuevo_refresh,
    token_csrf,
    verificar_clave,
    verificar_senuelo,
)
from app.models import Sesion, Usuario
from app.services.auditoria import registrar


@dataclass(frozen=True)
class Tokens:
    acceso: str
    refresh: str
    csrf: str


async def _abrir_sesion(
    bd: AsyncSession, settings: Settings, usuario_id: int
) -> Tokens:
    refresh, refresh_hash = nuevo_refresh()
    sesion = Sesion(
        usuario_id=usuario_id,
        refresh_hash=refresh_hash,
        expira_en=ahora() + DURACION_REFRESH,
    )
    bd.add(sesion)
    await bd.flush()
    return Tokens(
        acceso=crear_token_acceso(settings, usuario_id, sesion.id),
        refresh=refresh,
        csrf=token_csrf(settings, sesion.id),
    )


def _bloqueada(hasta: datetime) -> ErrorApi:
    return ErrorApi(
        403,
        "cuenta_bloqueada",
        "Cuenta bloqueada por intentos fallidos",
        extra={"bloqueado_hasta": hasta.isoformat()},
    )


async def iniciar_sesion(
    bd: AsyncSession,
    settings: Settings,
    username: str,
    clave: str,
    ip: str | None,
) -> tuple[Usuario, Tokens]:
    momento = ahora()
    # FOR UPDATE: dos intentos a la vez no pierden la cuenta de fallos.
    usuario = await bd.scalar(
        select(Usuario).where(Usuario.username == username).with_for_update()
    )

    if usuario is None:
        # Mismo tiempo y misma respuesta que una clave errada. No se guarda lo
        # que escribió: podría ser su contraseña en el campo equivocado.
        await verificar_senuelo(clave)
        registrar(bd, "login_fallido", detalle={"motivo": "usuario_inexistente"}, ip=ip)
        await bd.commit()
        raise ErrorApi(401, "clave_incorrecta", "Usuario o clave incorrectos")

    auditar = {"actor_id": usuario.id, "objetivo": usuario.username, "ip": ip}

    if usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > momento:
        hasta = usuario.bloqueado_hasta
        registrar(
            bd, "login_fallido", detalle={"motivo": "cuenta_bloqueada"}, **auditar
        )
        await bd.commit()
        raise _bloqueada(hasta)

    if not await verificar_clave(usuario.clave_hash, clave):
        if usuario.activo:
            usuario.intentos_fallidos += 1
        if usuario.activo and usuario.intentos_fallidos >= INTENTOS_MAXIMOS:
            # Al bloquear, el contador vuelve a 0: tras los 15 min hay otros 5.
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = momento + DURACION_BLOQUEO
            hasta = usuario.bloqueado_hasta
            registrar(bd, "cuenta_bloqueada", **auditar)
            await bd.commit()
            raise _bloqueada(hasta)
        registrar(
            bd, "login_fallido", detalle={"motivo": "clave_incorrecta"}, **auditar
        )
        await bd.commit()
        raise ErrorApi(401, "clave_incorrecta", "Usuario o clave incorrectos")

    if not usuario.activo:
        # Solo se dice con la clave correcta.
        registrar(bd, "login_fallido", detalle={"motivo": "cuenta_inactiva"}, **auditar)
        await bd.commit()
        raise ErrorApi(403, "cuenta_inactiva", "La cuenta está dada de baja")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_ingreso = momento
    if necesita_rehash(usuario.clave_hash):
        usuario.clave_hash = await hash_clave(clave)
    tokens = await _abrir_sesion(bd, settings, usuario.id)
    registrar(bd, "login_ok", **auditar)
    await bd.commit()
    return usuario, tokens


async def renovar_sesion(
    bd: AsyncSession,
    settings: Settings,
    refresh: str | None,
    csrf_cabecera: str | None,
    csrf_cookie: str | None,
    ip: str | None,
) -> Tokens | None:
    """Rota el refresh. Devuelve None si otra pestaña acaba de rotarlo."""
    if not refresh:
        raise ErrorApi(401, "sin_sesion", "Falta la cookie de refresh")
    momento = ahora()
    fila = (
        await bd.execute(
            select(Sesion, Usuario)
            .join(Usuario, Usuario.id == Sesion.usuario_id)
            .where(Sesion.refresh_hash == hash_refresh(refresh))
            .with_for_update(of=Sesion)
        )
    ).first()
    if fila is None:
        raise ErrorApi(401, "token_invalido", "Refresh token desconocido")
    sesion, usuario = fila

    if not csrf_valido(settings, sesion.id, csrf_cabecera, csrf_cookie):
        raise ErrorApi(403, "csrf_invalido", "Falta el token CSRF o no coincide")

    if sesion.revocada_en is not None:
        if momento - sesion.revocada_en <= GRACIA_REUSO:
            # Otra pestaña renovó al mismo tiempo: el navegador ya tiene las
            # cookies nuevas, basta con no tocar nada.
            return None
        # Un refresh viejo que vuelve a aparecer: posible robo. Se cierran
        # todas las sesiones de la persona.
        await bd.execute(
            update(Sesion)
            .where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None))
            .values(revocada_en=momento)
        )
        registrar(
            bd,
            "reuso_refresh",
            actor_id=usuario.id,
            objetivo=usuario.username,
            ip=ip,
        )
        await bd.commit()
        raise ErrorApi(401, "token_invalido", "Refresh token ya usado")

    if sesion.expira_en <= momento:
        raise ErrorApi(401, "token_vencido", "La sesión venció")
    if not usuario.activo:
        raise ErrorApi(401, "sin_sesion", "La cuenta está dada de baja")

    sesion.revocada_en = momento
    sesion.ultimo_uso_en = momento
    tokens = await _abrir_sesion(bd, settings, usuario.id)
    await bd.commit()
    return tokens


async def cerrar_sesion(
    bd: AsyncSession,
    settings: Settings,
    refresh: str | None,
    acceso: str | None,
    csrf_cabecera: str | None,
    csrf_cookie: str | None,
) -> None:
    """Revoca la sesión de rt (o, si no hay, la de at). Sin sesión no hace nada."""
    sesion_id = None
    if refresh:
        sesion_id = await bd.scalar(
            select(Sesion.id).where(Sesion.refresh_hash == hash_refresh(refresh))
        )
    if sesion_id is None and acceso:
        try:
            _, sesion_id = leer_token_acceso(
                settings, acceso, verificar_vencimiento=False
            )
        except jwt.InvalidTokenError:
            sesion_id = None
    if sesion_id is None:
        return
    if not csrf_valido(settings, sesion_id, csrf_cabecera, csrf_cookie):
        raise ErrorApi(403, "csrf_invalido", "Falta el token CSRF o no coincide")
    await bd.execute(
        update(Sesion)
        .where(Sesion.id == sesion_id, Sesion.revocada_en.is_(None))
        .values(revocada_en=ahora())
    )
    await bd.commit()


def _problema_de_clave(usuario: Usuario, actual: str, nueva: str) -> ErrorApi | None:
    if len(nueva) < CLAVE_MINIMA:
        return ErrorApi(
            400, "clave_debil", f"La clave debe tener {CLAVE_MINIMA} caracteres o más"
        )
    if nueva.casefold() == usuario.username.casefold():
        return ErrorApi(400, "clave_debil", "La clave no puede ser el usuario")
    if nueva == actual:
        return ErrorApi(400, "clave_repetida", "La clave nueva es igual a la actual")
    return None


async def cambiar_clave(
    bd: AsyncSession,
    usuario: Usuario,
    sesion_id: int,
    clave_actual: str,
    clave_nueva: str,
    ip: str | None,
) -> None:
    """Cambia la clave de la plataforma (no la de la VM) y cierra las demás
    sesiones de la persona; la actual sigue abierta."""
    if not await verificar_clave(usuario.clave_hash, clave_actual):
        raise ErrorApi(400, "clave_incorrecta", "La clave actual no coincide")
    problema = _problema_de_clave(usuario, clave_actual, clave_nueva)
    if problema is not None:
        raise problema

    usuario.clave_hash = await hash_clave(clave_nueva)
    usuario.debe_cambiar_clave = False
    await bd.execute(
        update(Sesion)
        .where(
            Sesion.usuario_id == usuario.id,
            Sesion.id != sesion_id,
            Sesion.revocada_en.is_(None),
        )
        .values(revocada_en=ahora())
    )
    registrar(bd, "cambio_clave", actor_id=usuario.id, objetivo=usuario.username, ip=ip)
    await bd.commit()
