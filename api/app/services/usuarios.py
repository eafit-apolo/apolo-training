"""Cuentas de la plataforma (B-08).

**Altas y bajas** solo desde la VM de práctica (`apolo-training-admin`, V-04),
por las rutas internas con el token de servicio: así la cuenta existe en los
dos lados o en ninguno (docs/diseno/flujos.md, flujo 1). La plataforma no crea
ni borra cuentas desde la web.

- Alta: el mismo usuario de su clúster, con la clave temporal de la VM (solo
  el hash) y `debe_cambiar_clave`. Siempre estudiante. Si el usuario ya
  existe, aunque esté de baja, 409 `usuario_existe` (la 116 revierte su alta).
- Baja (`activo: false`): no vuelve a entrar y se cierran todas sus sesiones.
  Se puede repetir: si ya estaba de baja, no cambia nada (ni la fecha).
  `activo: true` la reactiva; la clave sigue siendo la que tenía.

**Administración** (solo admin, `/api/admin`): la lista con el estado de cada
cuenta, el detalle con su Mi progreso, el cambio de rol (nunca deja la
plataforma sin admin activo: 409 `ultimo_admin`) y el reinicio de la clave de
la plataforma (no la de la VM): una clave temporal nueva que se ve una sola
vez, `debe_cambiar_clave`, la cuenta desbloqueada y todas sus sesiones
cerradas.

Todo cambio queda en la auditoría; nunca una clave.
"""

from typing import Literal

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.core.seguridad import ahora, clave_temporal, hash_clave
from app.models import Sesion, Usuario
from app.schemas import admin as esquemas
from app.schemas.usuario import AltaUsuario, UsuarioSalida
from app.services import auditoria, progreso
from app.services.resumen import Resumen, resumenes

# Quién firma en la auditoría cuando no es una persona.
SERVICIO_VM = "vm-practica"
SERVICIO_CONSOLA = "consola"


def _no_existe() -> ErrorApi:
    return ErrorApi(404, "no_encontrado", "No existe ese usuario")


async def _cerrar_sesiones(bd: AsyncSession, usuario_id: int) -> None:
    await bd.execute(
        update(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.revocada_en.is_(None))
        .values(revocada_en=ahora())
    )


async def _para_cambiar(bd: AsyncSession, username: str) -> Usuario:
    """El usuario bloqueado para esta transacción (FOR UPDATE), o 404."""
    usuario = await bd.scalar(
        select(Usuario)
        .where(Usuario.username == username)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if usuario is None:
        raise _no_existe()
    return usuario


# --- Altas y bajas (rutas internas) ---------------------------------------------


async def alta(bd: AsyncSession, entrada: AltaUsuario, ip: str | None) -> Usuario:
    clave_hash = await hash_clave(entrada.clave_temporal.get_secret_value())
    # Un solo INSERT … ON CONFLICT DO NOTHING: dos altas del mismo usuario a la
    # vez no chocan; la segunda recibe el 409.
    usuario = await bd.scalar(
        insert(Usuario)
        .values(
            username=entrada.username,
            nombre=entrada.nombre,
            correo=entrada.correo,
            cluster=entrada.cluster,
            idioma=entrada.idioma,
            rol="estudiante",
            clave_hash=clave_hash,
            debe_cambiar_clave=True,
        )
        .on_conflict_do_nothing(index_elements=[Usuario.username])
        .returning(Usuario),
        execution_options={"populate_existing": True},
    )
    if usuario is None:
        raise ErrorApi(409, "usuario_existe", "Ya existe un usuario con ese username")
    auditoria.registrar(
        bd,
        "alta",
        actor_servicio=SERVICIO_VM,
        objetivo=usuario.username,
        detalle={"cluster": usuario.cluster, "idioma": usuario.idioma},
        ip=ip,
    )
    await bd.commit()
    return usuario


async def cambiar_estado(
    bd: AsyncSession, username: str, activo: bool, ip: str | None
) -> Usuario:
    usuario = await _para_cambiar(bd, username)
    if usuario.activo and not activo:
        usuario.activo = False
        usuario.baja_en = ahora()
        await _cerrar_sesiones(bd, usuario.id)
        accion = "baja"
    elif not usuario.activo and activo:
        usuario.activo = True
        usuario.baja_en = None
        accion = "reactivacion"
    else:
        accion = None
    if accion:
        auditoria.registrar(
            bd, accion, actor_servicio=SERVICIO_VM, objetivo=username, ip=ip
        )
    await bd.commit()
    return usuario


# --- Administración ------------------------------------------------------------


def estado_cuenta(momento):
    """El estado de la cuenta como expresión de SQL: el mismo para la columna
    `estado` de la lista y para su filtro."""
    return case(
        (Usuario.activo.is_(False), "baja"),
        (Usuario.bloqueado_hasta > momento, "bloqueado"),
        (Usuario.debe_cambiar_clave.is_(True), "debe_cambiar_clave"),
        else_="activo",
    )


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _admin(usuario: Usuario, estado: str, resumen: Resumen) -> esquemas.UsuarioAdmin:
    return esquemas.UsuarioAdmin(
        **UsuarioSalida.model_validate(usuario).model_dump(),
        estado=estado,
        bloqueado_hasta=usuario.bloqueado_hasta,
        creado_en=usuario.creado_en,
        ultimo_ingreso=usuario.ultimo_ingreso,
        baja_en=usuario.baja_en,
        avance_pct=resumen.avance_pct,
        labs_aprobados=resumen.labs_aprobados,
        graduacion_estado=resumen.graduacion_estado,
    )


async def listar(
    bd: AsyncSession,
    *,
    q: str | None,
    cluster: str | None,
    rol: str | None,
    estado: esquemas.EstadoCuenta | None,
    pagina: int,
    por_pagina: int,
) -> esquemas.ListaUsuarios:
    """Por username. `q` busca en username, nombre y correo (sin distinguir
    mayúsculas); los demás filtros son exactos."""
    momento = ahora()
    condiciones = []
    texto = (q or "").strip()
    if texto:
        patron = f"%{_escapar_like(texto)}%"
        condiciones.append(
            or_(
                Usuario.username.ilike(patron, escape="\\"),
                Usuario.nombre.ilike(patron, escape="\\"),
                Usuario.correo.ilike(patron, escape="\\"),
            )
        )
    if cluster:
        condiciones.append(Usuario.cluster == cluster)
    if rol:
        condiciones.append(Usuario.rol == rol)
    if estado:
        condiciones.append(estado_cuenta(momento) == estado)

    total = await bd.scalar(
        select(func.count()).select_from(Usuario).where(*condiciones)
    )
    filas = (
        await bd.execute(
            select(Usuario, estado_cuenta(momento))
            .where(*condiciones)
            .order_by(Usuario.username)
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
            .execution_options(populate_existing=True)
        )
    ).all()
    datos = await resumenes(bd, [usuario.id for usuario, _ in filas])
    return esquemas.ListaUsuarios(
        total=total or 0,
        pagina=pagina,
        por_pagina=por_pagina,
        items=[_admin(usuario, e, datos[usuario.id]) for usuario, e in filas],
    )


async def _con_estado(
    bd: AsyncSession, username: str
) -> tuple[Usuario, esquemas.UsuarioAdmin]:
    fila = (
        await bd.execute(
            select(Usuario, estado_cuenta(ahora()))
            .where(Usuario.username == username)
            .execution_options(populate_existing=True)
        )
    ).first()
    if fila is None:
        raise _no_existe()
    usuario, estado = fila
    resumen = (await resumenes(bd, [usuario.id]))[usuario.id]
    return usuario, _admin(usuario, estado, resumen)


async def detalle(
    bd: AsyncSession, username: str, idioma: Literal["es", "en"]
) -> esquemas.UsuarioDetalleAdmin:
    """La cuenta y su Mi progreso (la pantalla 04 en modo lectura), en el idioma
    de quien la mira."""
    usuario, base = await _con_estado(bd, username)
    return esquemas.UsuarioDetalleAdmin(
        **base.model_dump(), progreso=await progreso.mi_progreso(bd, usuario, idioma)
    )


async def cambiar_rol(
    bd: AsyncSession,
    username: str,
    rol: str,
    *,
    actor_id: int | None = None,
    actor_servicio: str | None = None,
    ip: str | None = None,
) -> tuple[str, str]:
    """(rol de antes, rol de ahora). Lo usan la ruta de admin y `python -m
    app.rol` (el primer admin de la plataforma)."""
    # Primero los admins activos, en orden de id, y después el usuario: dos
    # cambios a la vez esperan en las mismas filas, en el mismo orden, y el
    # segundo ve lo que dejó el primero (no se quedan los dos sin admin).
    admins = list(
        await bd.scalars(
            select(Usuario.id)
            .where(Usuario.rol == "admin", Usuario.activo.is_(True))
            .order_by(Usuario.id)
            .with_for_update()
        )
    )
    usuario = await _para_cambiar(bd, username)
    antes = usuario.rol
    if antes != rol:
        if admins == [usuario.id]:
            raise ErrorApi(
                409, "ultimo_admin", "No se puede quitar el rol al último admin activo"
            )
        usuario.rol = rol
        auditoria.registrar(
            bd,
            "cambio_rol",
            actor_id=actor_id,
            actor_servicio=actor_servicio,
            objetivo=username,
            detalle={"antes": antes, "despues": rol},
            ip=ip,
        )
    await bd.commit()
    return antes, rol


async def cambiar_rol_admin(
    bd: AsyncSession, username: str, rol: str, admin: Usuario, ip: str | None
) -> esquemas.UsuarioAdmin:
    await cambiar_rol(bd, username, rol, actor_id=admin.id, ip=ip)
    _, resultado = await _con_estado(bd, username)
    return resultado


async def reiniciar_clave(
    bd: AsyncSession, username: str, admin: Usuario, ip: str | None
) -> esquemas.ClaveTemporal:
    usuario = await _para_cambiar(bd, username)
    if not usuario.activo:
        raise ErrorApi(
            409,
            "usuario_inactivo",
            "La cuenta está dada de baja; se reactiva desde la VM de práctica",
        )
    clave = clave_temporal()
    usuario.clave_hash = await hash_clave(clave)
    usuario.debe_cambiar_clave = True
    # «No puedo entrar» suele ser una cuenta bloqueada: el reinicio la libera.
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    await _cerrar_sesiones(bd, usuario.id)
    auditoria.registrar(
        bd, "reinicio_clave", actor_id=admin.id, objetivo=username, ip=ip
    )
    await bd.commit()
    return esquemas.ClaveTemporal(username=username, clave_temporal=clave)
