"""Progreso de las lecciones: «Marcar como completada» (F-04).

Regla de hoy (decisión del 4-nov), dentro de la de docs/diseno/modelo-datos.md:

- Una lección con un video **ya subido** se completa al verlo (B-06, F-05):
  aquí responde 409 `requisitos_pendientes` mientras no esté visto. Si el
  video todavía no se ha subido, se marca a mano como una de solo texto.
- Mientras no haya calificación de quizzes (B-06), el quiz no la bloquea.
- Las prácticas nunca bloquean una lección.
- Completar exige el módulo abierto, también a instructores y admins (ellos
  pueden leer un módulo bloqueado, pero no avanzar en él).

`completada_en` se llena una sola vez: completar dos veces no la cambia.
"""

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import ProgresoLeccion, Usuario
from app.schemas import contenido as esquemas
from app.services import contenido


async def completar_leccion(
    bd: AsyncSession, leccion_id: int, usuario: Usuario
) -> esquemas.ProgresoLeccion:
    armada = await contenido.leccion_por_id(bd, leccion_id, usuario)
    if armada.modulo.estado == "bloqueado":
        raise contenido.error_bloqueado(armada.modulo, contenido.Textos(usuario.idioma))

    fila = armada.datos.progreso.get(leccion_id)
    ya_completa = fila is not None and fila.completada_en is not None
    video_pendiente = any(v.archivo is not None for v in armada.videos()) and not (
        fila is not None and fila.video_completo
    )
    if not ya_completa and video_pendiente:
        raise ErrorApi(
            409, "requisitos_pendientes", "La lección se completa al ver su video"
        )

    # Insertar o actualizar en una sola sentencia: dos clics a la vez no chocan.
    nueva = insert(ProgresoLeccion).values(
        usuario_id=usuario.id, leccion_id=leccion_id, completada_en=func.now()
    )
    nueva = nueva.on_conflict_do_update(
        index_elements=[ProgresoLeccion.usuario_id, ProgresoLeccion.leccion_id],
        set_={
            "completada_en": func.coalesce(
                ProgresoLeccion.completada_en, nueva.excluded.completada_en
            ),
            "actualizado_en": func.now(),
        },
    ).returning(ProgresoLeccion)
    guardada = await bd.scalar(nueva, execution_options={"populate_existing": True})
    await bd.commit()
    return contenido.progreso_de(guardada, leccion_id, completada=True)
