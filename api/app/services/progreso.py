"""Progreso de las lecciones: «Marcar como completada» (F-04) y el avance del
video (F-05).

Regla de hoy, dentro de la de docs/diseno/modelo-datos.md:

- Una lección con un video **ya subido** se completa al verlo: el reproductor
  reporta el segundo cada 15 s (`reportar_video`) y, cuando lo más lejos que
  llegó pasa el 90 % de la duración, el video queda visto y la lección
  completa. «Marcar como completada» responde 409 `requisitos_pendientes`
  mientras no esté visto. Si el video todavía no se ha subido, se marca a mano
  como una de solo texto.
- Mientras no haya calificación de quizzes (B-06), el quiz no la bloquea.
- Las prácticas nunca bloquean una lección.
- Completar y reportar exigen el módulo abierto, también a instructores y
  admins (ellos pueden leer un módulo bloqueado, pero no avanzar en él).

`completada_en` se llena una sola vez: completar dos veces no la cambia.
"""

import math

from sqlalchemy import case, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import ProgresoLeccion, Usuario
from app.schemas import contenido as esquemas
from app.services import contenido

# El video cuenta como visto al llegar a esta parte de su duración.
PARTE_VISTA = 0.9


def segundos_para_ver(duracion_seg: int) -> int:
    """El segundo a partir del cual un video de esa duración queda visto."""
    return math.ceil(duracion_seg * PARTE_VISTA)


async def _leccion_abierta(
    bd: AsyncSession, leccion_id: int, usuario: Usuario
) -> contenido.LeccionArmada:
    armada = await contenido.leccion_por_id(bd, leccion_id, usuario)
    if armada.modulo.estado == "bloqueado":
        raise contenido.error_bloqueado(armada.modulo, contenido.Textos(usuario.idioma))
    return armada


async def completar_leccion(
    bd: AsyncSession, leccion_id: int, usuario: Usuario
) -> esquemas.ProgresoLeccion:
    armada = await _leccion_abierta(bd, leccion_id, usuario)

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


async def reportar_video(
    bd: AsyncSession, entrada: esquemas.ProgresoVideoEntrada, usuario: Usuario
) -> esquemas.ProgresoLeccion:
    """`POST /api/progreso/video`: dónde va el usuario en el video de una lección.

    - `video_posicion_seg` es el último segundo reportado (de ahí se reanuda,
      aunque haya retrocedido); `video_max_seg`, lo más lejos que llegó.
    - El segundo se recorta a la duración del video.
    - Con lo más lejos ≥ 90 % de la duración, `video_completo` y, como el quiz
      todavía no bloquea (B-06), la lección queda completa. Nada de eso vuelve
      atrás.
    - En la lección de VPN el avance es de la lección, no de cada video: el
      90 % se mide con la duración del que se está viendo.
    """
    armada = await _leccion_abierta(bd, entrada.leccion_id, usuario)
    video = next(
        (
            v
            for v in armada.videos()
            if v.id == entrada.video_id and v.archivo is not None
        ),
        None,
    )
    if video is None or not video.duracion_seg:
        raise ErrorApi(404, "no_encontrado", "Esa lección no tiene ese video subido")

    segundo = min(entrada.segundo, video.duracion_seg)
    umbral = segundos_para_ver(video.duracion_seg)
    tabla = ProgresoLeccion
    nueva = insert(tabla).values(
        usuario_id=usuario.id,
        leccion_id=entrada.leccion_id,
        video_posicion_seg=segundo,
        video_max_seg=segundo,
        video_completo=segundo >= umbral,
        completada_en=func.now() if segundo >= umbral else None,
    )
    # La fila ya existía: todo se calcula en la misma sentencia, así dos
    # reportes a la vez (dos pestañas) no se pisan.
    maximo = func.greatest(tabla.video_max_seg, nueva.excluded.video_max_seg)
    visto = or_(tabla.video_completo, maximo >= umbral)
    nueva = nueva.on_conflict_do_update(
        index_elements=[tabla.usuario_id, tabla.leccion_id],
        set_={
            "video_posicion_seg": nueva.excluded.video_posicion_seg,
            "video_max_seg": maximo,
            "video_completo": visto,
            "completada_en": func.coalesce(
                tabla.completada_en, case((visto, func.now()), else_=None)
            ),
            "actualizado_en": func.now(),
        },
    ).returning(tabla)
    guardada = await bd.scalar(nueva, execution_options={"populate_existing": True})
    await bd.commit()
    return contenido.progreso_de(
        guardada, entrada.leccion_id, completada=guardada.completada_en is not None
    )
