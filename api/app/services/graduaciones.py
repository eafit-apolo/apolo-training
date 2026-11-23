"""Graduación (B-07): el usuario la envía desde Mi progreso y un instructor la
revisa en el panel.

- El usuario hace en su clúster real el trabajo de graduación (V-07) y pega el
  JobID y la salida de `apolo-training verificar graduacion JOBID`. Se puede
  enviar en cualquier momento (decisión del 20-nov): la graduación está en el
  módulo 7 y después siguen el 8 y el 9. `aprobado` igual exige todo.
- Mientras no esté aprobada se puede reenviar: reemplaza la anterior, vuelve a
  `enviada` y borra la revisión. Aprobada → 409 `graduacion_aprobada`.
- El clúster es el del perfil del usuario.
- Revisar: solo una `enviada` (si no, 409 `sin_graduacion_pendiente`).
  Rechazar exige un comentario (422 `comentario_obligatorio`), que el usuario
  ve en Mi progreso.
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errores import ErrorApi
from app.models import Graduacion, Practica, Usuario
from app.schemas import labs as esquemas
from app.services import auditoria


def a_esquema(fila: Graduacion) -> esquemas.Graduacion:
    return esquemas.Graduacion(
        cluster=fila.cluster,
        jobid=fila.jobid,
        salida_verificador=fila.salida_verificador,
        estado=fila.estado,
        enviada_en=fila.enviada_en,
        revisada_en=fila.revisada_en,
        comentario=fila.comentario,
        qos_aplicada_en=fila.qos_aplicada_en,
    )


async def enviar(
    bd: AsyncSession,
    usuario: Usuario,
    entrada: esquemas.GraduacionEntrada,
    ip: str | None,
) -> esquemas.Graduacion:
    valores = {
        "cluster": usuario.cluster,
        "jobid": entrada.jobid,
        "salida_verificador": entrada.salida,
        "estado": "enviada",
        "enviada_en": func.now(),
        "revisada_por": None,
        "revisada_en": None,
        "comentario": None,
    }
    sentencia = insert(Graduacion).values(usuario_id=usuario.id, **valores)
    # Un solo INSERT … ON CONFLICT: una aprobada no se reemplaza, aunque la
    # aprueben justo mientras llega el reenvío.
    guardada = await bd.scalar(
        sentencia.on_conflict_do_update(
            index_elements=[Graduacion.usuario_id],
            set_=valores,
            where=Graduacion.estado != "aprobada",
        ).returning(Graduacion),
        execution_options={"populate_existing": True},
    )
    if guardada is None:
        raise ErrorApi(409, "graduacion_aprobada", "Tu graduación ya está aprobada")
    auditoria.registrar(
        bd,
        "graduacion_enviada",
        actor_id=usuario.id,
        objetivo=usuario.username,
        detalle={"jobid": entrada.jobid},
        ip=ip,
    )
    await bd.commit()
    return a_esquema(guardada)


def _consulta_admin():
    """Graduaciones con el usuario, quién la revisó y sus prácticas aprobadas."""
    revisor = aliased(Usuario)
    aprobadas = (
        select(func.count())
        .where(Practica.usuario_id == Graduacion.usuario_id)
        .where(Practica.estado == "aprobado")
        .correlate(Graduacion)
        .scalar_subquery()
    )
    return (
        select(
            Graduacion, Usuario.username, Usuario.nombre, revisor.username, aprobadas
        )
        .join(Usuario, Usuario.id == Graduacion.usuario_id)
        .outerjoin(revisor, revisor.id == Graduacion.revisada_por)
    )


def _admin(fila, username, nombre, revisor, aprobadas) -> esquemas.GraduacionAdmin:
    return esquemas.GraduacionAdmin(
        **a_esquema(fila).model_dump(),
        username=username,
        nombre=nombre,
        revisada_por=revisor,
        labs_aprobados=aprobadas,
    )


async def listar(
    bd: AsyncSession, estado: esquemas.EstadoGraduacion | None
) -> list[esquemas.GraduacionAdmin]:
    """Las más viejas primero: es el orden en que se revisan."""
    consulta = _consulta_admin().order_by(Graduacion.enviada_en, Graduacion.usuario_id)
    if estado is not None:
        consulta = consulta.where(Graduacion.estado == estado)
    return [_admin(*fila) for fila in await bd.execute(consulta)]


async def revisar(
    bd: AsyncSession,
    username: str,
    revision: esquemas.RevisionGraduacion,
    revisor: Usuario,
    ip: str | None,
) -> esquemas.GraduacionAdmin:
    comentario = (revision.comentario or "").strip() or None
    if revision.decision == "rechazar" and comentario is None:
        raise ErrorApi(
            422,
            "comentario_obligatorio",
            "Para rechazar hay que decir qué falta en el comentario",
        )
    usuario_id = await bd.scalar(select(Usuario.id).where(Usuario.username == username))
    if usuario_id is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese usuario")
    fila = await bd.scalar(
        select(Graduacion)
        .where(Graduacion.usuario_id == usuario_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if fila is None or fila.estado != "enviada":
        raise ErrorApi(
            409,
            "sin_graduacion_pendiente",
            "No hay una graduación enviada para revisar",
        )
    fila.estado = "aprobada" if revision.decision == "aprobar" else "rechazada"
    fila.revisada_por = revisor.id
    fila.revisada_en = func.now()
    fila.comentario = comentario
    auditoria.registrar(
        bd,
        "graduacion_revisada",
        actor_id=revisor.id,
        objetivo=username,
        detalle={"decision": revision.decision},
        ip=ip,
    )
    await bd.commit()
    return _admin(
        *(
            await bd.execute(
                _consulta_admin()
                .where(Graduacion.usuario_id == usuario_id)
                .execution_options(populate_existing=True)
            )
        ).one()
    )
