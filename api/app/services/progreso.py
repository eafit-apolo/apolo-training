"""Progreso de las lecciones: «Marcar como completada» (F-04), el avance del
video (F-05) y Mi progreso (B-06 y B-07).

Cuándo se completa una lección (docs/diseno/modelo-datos.md):

- Con un video **ya subido**, hay que verlo: el reproductor reporta el segundo
  cada 15 s (`reportar_video`) y, cuando lo más lejos que llegó pasa el 90 %
  de la duración, el video queda visto. Si el video todavía no se ha subido,
  no cuenta.
- Con quiz, hay que aprobarlo (80 %, `app/services/quizzes.py`).
- Lo último que llegue (video visto o quiz aprobado) la completa sola. Sin
  video subido ni quiz, se marca a mano. «Marcar como completada» responde 409
  `requisitos_pendientes` en una lección con quiz y mientras el video subido
  no esté visto.
- Las prácticas nunca bloquean una lección.
- Completar, reportar el video y enviar un intento exigen el módulo abierto,
  también a instructores y admins (ellos pueden leer un módulo bloqueado,
  pero no avanzar en él).

`completada_en` se llena una sola vez: nada de esto vuelve atrás.

Mi progreso suma, desde la B-07, las siete prácticas (las sincroniza la VM,
`app/services/labs.py`), la última sincronización, la graduación
(`app/services/graduaciones.py`), si aprobó y el siguiente paso.
"""

import math
from datetime import timedelta
from typing import Literal

from sqlalchemy import and_, case, func, or_, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.core.seguridad import ahora
from app.models import (
    Curso,
    Graduacion,
    Intento,
    Practica,
    ProgresoLeccion,
    Sincronizacion,
    Usuario,
)
from app.models.valores import PRACTICAS
from app.schemas import contenido as esquemas
from app.schemas import labs as esquemas_labs
from app.schemas.contenido import Idioma
from app.services import contenido, graduaciones

# El video cuenta como visto al llegar a esta parte de su duración.
PARTE_VISTA = 0.9
# La VM reporta cada 5 minutos: con 15 sin reporte, Mi progreso avisa.
SINCRONIZACION_ATRASADA = timedelta(minutes=15)

# Un paso del curso para el «siguiente paso»: una lección sin completar o una
# práctica que nombra alguna lección.
Paso = tuple[Literal["leccion"], esquemas.LeccionRef] | tuple[Literal["practica"], str]


def segundos_para_ver(duracion_seg: int) -> int:
    """El segundo a partir del cual un video de esa duración queda visto."""
    return math.ceil(duracion_seg * PARTE_VISTA)


async def leccion_abierta(
    bd: AsyncSession, leccion_id: int, usuario: Usuario
) -> contenido.LeccionArmada:
    """La lección para avanzar en ella: 403 `modulo_bloqueado` para todos."""
    armada = await contenido.leccion_por_id(bd, leccion_id, usuario)
    if armada.modulo.estado == "bloqueado":
        raise contenido.error_bloqueado(armada.modulo, contenido.Textos(usuario.idioma))
    return armada


async def completar_leccion(
    bd: AsyncSession, leccion_id: int, usuario: Usuario
) -> esquemas.ProgresoLeccion:
    armada = await leccion_abierta(bd, leccion_id, usuario)

    fila = armada.datos.progreso.get(leccion_id)
    ya_completa = fila is not None and fila.completada_en is not None
    quiz_pendiente = leccion_id in armada.datos.quizzes and not (
        fila is not None and fila.quiz_aprobado
    )
    video_pendiente = armada.video_subido() and not (
        fila is not None and fila.video_completo
    )
    if not ya_completa and quiz_pendiente:
        raise ErrorApi(
            409, "requisitos_pendientes", "La lección se completa al aprobar su quiz"
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
    - Con lo más lejos ≥ 90 % de la duración, `video_completo`; la lección
      queda completa si no tiene quiz o si ya está aprobado. Nada de eso
      vuelve atrás.
    - En la lección de VPN el avance es de la lección, no de cada video: el
      90 % se mide con la duración del que se está viendo.
    """
    armada = await leccion_abierta(bd, entrada.leccion_id, usuario)
    tiene_quiz = entrada.leccion_id in armada.datos.quizzes
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
        # En una fila nueva el quiz todavía no está aprobado.
        completada_en=func.now() if segundo >= umbral and not tiene_quiz else None,
    )
    # La fila ya existía: todo se calcula en la misma sentencia, así dos
    # reportes a la vez (dos pestañas) no se pisan.
    maximo = func.greatest(tabla.video_max_seg, nueva.excluded.video_max_seg)
    visto = or_(tabla.video_completo, maximo >= umbral)
    quiz_listo = tabla.quiz_aprobado if tiene_quiz else true()
    nueva = nueva.on_conflict_do_update(
        index_elements=[tabla.usuario_id, tabla.leccion_id],
        set_={
            "video_posicion_seg": nueva.excluded.video_posicion_seg,
            "video_max_seg": maximo,
            "video_completo": visto,
            "completada_en": func.coalesce(
                tabla.completada_en,
                case((and_(visto, quiz_listo), func.now()), else_=None),
            ),
            "actualizado_en": func.now(),
        },
    ).returning(tabla)
    guardada = await bd.scalar(nueva, execution_options={"populate_existing": True})
    await bd.commit()
    return contenido.progreso_de(
        guardada, entrada.leccion_id, completada=guardada.completada_en is not None
    )


async def _avance(
    bd: AsyncSession, usuario: Usuario, idioma: Idioma
) -> tuple[esquemas.AvanceCurso, list[Paso]]:
    """La parte de la B-06: el avance del curso de inducción (el primero
    publicado) por módulo y por lección. Devuelve además, en el orden del
    curso, los pasos de lecciones y prácticas: ("leccion", id) o
    ("practica", nombre), con las lecciones de cada módulo antes que sus
    prácticas.

    Una lección de un módulo bloqueado no cuenta como completa, igual que en
    el resto de las rutas de contenido.
    """
    curso = await bd.scalar(
        select(Curso)
        .where(Curso.publicado.is_(True))
        .order_by(Curso.orden, Curso.id)
        .limit(1)
    )
    if curso is None:
        vacio = esquemas.AvanceCurso(
            curso=None,
            avance_pct=0,
            lecciones_total=0,
            lecciones_completas=0,
            modulos=[],
            fallback=False,
        )
        return vacio, []
    datos = await contenido.armar_curso(bd, curso, usuario)
    quiz_ids = [quiz_id for quiz_id, _ in datos.quizzes.values()]
    mejores = dict(
        (
            await bd.execute(
                select(Intento.quiz_id, func.max(Intento.puntaje))
                .where(Intento.usuario_id == usuario.id, Intento.quiz_id.in_(quiz_ids))
                .group_by(Intento.quiz_id)
            )
        ).all()
    )
    t = contenido.Textos(idioma)
    modulos = []
    pasos: list[Paso] = []
    for armado in datos.modulos:
        lecciones = []
        practicas: list[str] = []
        for leccion in armado.lecciones:
            fila = datos.progreso.get(leccion.id)
            quiz = datos.quizzes.get(leccion.id)
            mejor = mejores.get(quiz[0]) if quiz else None
            completada = leccion.id in armado.completas
            lecciones.append(
                esquemas.LeccionProgreso(
                    id=leccion.id,
                    slug=leccion.slug,
                    titulo=t(leccion.titulo_es, leccion.titulo_en),
                    completada=completada,
                    video_completo=fila.video_completo if fila else False,
                    tiene_quiz=quiz is not None,
                    quiz_aprobado=fila.quiz_aprobado if fila else False,
                    quiz_mejor_puntaje=float(mejor) if mejor is not None else None,
                )
            )
            if not completada:
                pasos.append(
                    ("leccion", contenido._ref_leccion(armado.modulo, leccion, t))
                )
            practicas += [p for p in leccion.practicas if p not in practicas]
        pasos += [("practica", practica) for practica in practicas]
        modulos.append(
            esquemas.ModuloProgreso(
                id=armado.modulo.id,
                slug=armado.modulo.slug,
                numero=armado.modulo.numero,
                titulo=t(armado.modulo.titulo_es, armado.modulo.titulo_en),
                estado=armado.estado,
                lecciones_total=len(armado.lecciones),
                lecciones_completas=len(armado.completas),
                lecciones=lecciones,
            )
        )
    total = sum(m.lecciones_total for m in modulos)
    completas = sum(m.lecciones_completas for m in modulos)
    avance = esquemas.AvanceCurso(
        curso=curso.slug,
        avance_pct=round(100 * completas / total) if total else 0,
        lecciones_total=total,
        lecciones_completas=completas,
        modulos=modulos,
        fallback=t.fallback,
    )
    return avance, pasos


def _paso(
    tipo: str,
    leccion: esquemas.LeccionRef | None = None,
    lab: str | None = None,
) -> esquemas_labs.SiguientePaso:
    return esquemas_labs.SiguientePaso(tipo=tipo, leccion=leccion, lab=lab)


def _siguiente_paso(
    pasos: list[Paso],
    labs: dict[str, esquemas_labs.LabEstadoUsuario],
    graduacion: Graduacion | None,
) -> esquemas_labs.SiguientePaso:
    """Lo primero pendiente, en el orden del curso (decisión del 20-nov):
    módulo por módulo, sus lecciones y luego sus prácticas; después las
    prácticas que ninguna lección nombra, la graduación, la revisión y la QOS.
    """
    vistas: set[str] = set()
    for tipo, valor in pasos:
        if tipo == "leccion":
            return _paso("leccion", leccion=valor)
        vistas.add(valor)
        if labs[valor].estado != "aprobado":
            return _paso("laboratorio", lab=valor)
    for practica in PRACTICAS:
        if practica not in vistas and labs[practica].estado != "aprobado":
            return _paso("laboratorio", lab=practica)
    if graduacion is None or graduacion.estado == "rechazada":
        return _paso("graduacion")
    if graduacion.estado == "enviada":
        return _paso("esperar_revision")
    if graduacion.qos_aplicada_en is None:
        return _paso("esperar_qos")
    return _paso("terminado")


async def mi_progreso(
    bd: AsyncSession, usuario: Usuario, idioma: Idioma
) -> esquemas_labs.MiProgreso:
    """`GET /api/me/progreso`: el avance del curso (B-06) más las prácticas,
    la sincronización, la graduación, si aprobó y el siguiente paso (B-07)."""
    avance, pasos = await _avance(bd, usuario, idioma)

    filas = {
        p.practica: p
        for p in await bd.scalars(
            select(Practica).where(Practica.usuario_id == usuario.id)
        )
    }
    labs = {
        practica: esquemas_labs.LabEstadoUsuario(
            lab=practica,
            estado=fila.estado if fila else "sin_intentar",
            jobid=fila.jobid if fila else None,
            fecha=fila.fecha if fila else None,
            detalle=fila.detalle if fila else None,
        )
        for practica in PRACTICAS
        for fila in [filas.get(practica)]
    }
    ultima = await bd.scalar(select(func.max(Sincronizacion.recibida_en)))
    graduacion = await bd.get(Graduacion, usuario.id, populate_existing=True)

    completo = avance.lecciones_total > 0 and (
        avance.lecciones_completas == avance.lecciones_total
    )
    aprobado = (
        completo
        and all(lab.estado == "aprobado" for lab in labs.values())
        and graduacion is not None
        and graduacion.estado == "aprobada"
    )
    return esquemas_labs.MiProgreso(
        **avance.model_dump(),
        labs=list(labs.values()),
        ultima_sincronizacion=ultima,
        sincronizacion_atrasada=ultima is not None
        and ahora() - ultima > SINCRONIZACION_ATRASADA,
        graduacion=graduaciones.a_esquema(graduacion) if graduacion else None,
        aprobado=aprobado,
        siguiente_paso=_siguiente_paso(pasos, labs, graduacion),
    )
