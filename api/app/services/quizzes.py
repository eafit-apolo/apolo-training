"""Quizzes (B-06): obtenerQuiz y enviarIntento del contrato.

- La opción correcta nunca sale de la API: ni al pedir el quiz ni al
  calificar. Al calificar se dice, por pregunta, si acertó y su explicación,
  para que reintentar sirva.
- Una pregunta cuenta si se marcaron exactamente sus opciones correctas
  (todas y solo ellas; en las de varias respuestas no hay puntos parciales).
- Puntaje: porcentaje de preguntas acertadas. Aprueba si acierta al menos el
  `umbral` (0.80) de las preguntas. Intentos ilimitados; cuenta el mejor.
- Aprobar marca `quiz_aprobado` y completa la lección si su video subido ya
  está visto o si no tiene video subido. Nada de eso vuelve atrás.
- Leer el quiz sigue las reglas de leer la lección (un estudiante no lo ve si
  el módulo está bloqueado); enviar un intento exige el módulo abierto a todos.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, case, func, or_, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import Intento, Opcion, Pregunta, ProgresoLeccion, Quiz, Usuario
from app.schemas import quizzes as esquemas
from app.schemas.contenido import Idioma
from app.services import contenido, progreso

CENTESIMA = Decimal("0.01")


async def _quiz(
    bd: AsyncSession, quiz_id: int, usuario: Usuario
) -> tuple[Quiz, contenido.LeccionArmada]:
    """El quiz y su lección: 404 si no existe o su lección no está publicada."""
    quiz = await bd.get(Quiz, quiz_id)
    if quiz is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese quiz")
    armada = await contenido.leccion_por_id(bd, quiz.leccion_id, usuario)
    return quiz, armada


async def _preguntas(
    bd: AsyncSession, quiz_id: int
) -> list[tuple[Pregunta, list[Opcion]]]:
    preguntas = list(
        await bd.scalars(
            select(Pregunta).where(Pregunta.quiz_id == quiz_id).order_by(Pregunta.orden)
        )
    )
    opciones: dict[int, list[Opcion]] = defaultdict(list)
    for opcion in await bd.scalars(
        select(Opcion)
        .where(Opcion.pregunta_id.in_([p.id for p in preguntas]))
        .order_by(Opcion.orden)
    ):
        opciones[opcion.pregunta_id].append(opcion)
    return [(pregunta, opciones[pregunta.id]) for pregunta in preguntas]


async def _mejor_puntaje(
    bd: AsyncSession, usuario: Usuario, quiz_id: int
) -> float | None:
    mejor = await bd.scalar(
        select(func.max(Intento.puntaje)).where(
            Intento.usuario_id == usuario.id, Intento.quiz_id == quiz_id
        )
    )
    return float(mejor) if mejor is not None else None


async def obtener_quiz(
    bd: AsyncSession, quiz_id: int, usuario: Usuario, idioma: Idioma
) -> esquemas.Quiz:
    quiz, armada = await _quiz(bd, quiz_id, usuario)
    t = contenido.Textos(idioma)
    if (
        armada.modulo.estado == "bloqueado"
        and usuario.rol not in contenido.ROLES_SIN_BLOQUEO
    ):
        raise contenido.error_bloqueado(armada.modulo, t)
    preguntas = [
        esquemas.PreguntaQuiz(
            id=pregunta.id,
            orden=pregunta.orden,
            enunciado=t(pregunta.enunciado_es, pregunta.enunciado_en),
            multiple=pregunta.multiple,
            opciones=[
                esquemas.OpcionQuiz(
                    id=opcion.id,
                    orden=opcion.orden,
                    texto=t(opcion.texto_es, opcion.texto_en),
                )
                for opcion in opciones
            ],
        )
        for pregunta, opciones in await _preguntas(bd, quiz.id)
    ]
    return esquemas.Quiz(
        id=quiz.id,
        leccion_id=quiz.leccion_id,
        umbral=float(quiz.umbral),
        es_final=quiz.es_final,
        fallback=t.fallback,
        mejor_puntaje=await _mejor_puntaje(bd, usuario, quiz.id),
        preguntas=preguntas,
    )


def _marcadas(
    entrada: esquemas.IntentoEntrada, preguntas: list[tuple[Pregunta, list[Opcion]]]
) -> dict[int, set[int]]:
    """Las opciones marcadas en cada pregunta, o 422 `respuestas_invalidas`.

    Hay que responder todas las preguntas, una vez cada una, con opciones de
    esa pregunta y sin repetirlas; en una de una sola respuesta, exactamente una.
    """
    invalidas = ErrorApi(
        422,
        "respuestas_invalidas",
        "Responde cada pregunta del quiz una vez, con opciones de esa pregunta",
    )
    por_id = {pregunta.id: (pregunta, opciones) for pregunta, opciones in preguntas}
    marcadas: dict[int, set[int]] = {}
    for respuesta in entrada.respuestas:
        if respuesta.pregunta_id in marcadas or respuesta.pregunta_id not in por_id:
            raise invalidas
        pregunta, opciones = por_id[respuesta.pregunta_id]
        elegidas = set(respuesta.opciones)
        if len(elegidas) != len(respuesta.opciones):
            raise invalidas
        if not elegidas <= {opcion.id for opcion in opciones}:
            raise invalidas
        if not pregunta.multiple and len(elegidas) != 1:
            raise invalidas
        marcadas[pregunta.id] = elegidas
    if marcadas.keys() != por_id.keys():
        raise invalidas
    return marcadas


async def enviar_intento(
    bd: AsyncSession,
    quiz_id: int,
    entrada: esquemas.IntentoEntrada,
    usuario: Usuario,
    idioma: Idioma,
) -> esquemas.IntentoResultado:
    quiz = await bd.get(Quiz, quiz_id)
    if quiz is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese quiz")
    armada = await progreso.leccion_abierta(bd, quiz.leccion_id, usuario)
    preguntas = await _preguntas(bd, quiz.id)
    marcadas = _marcadas(entrada, preguntas)

    t = contenido.Textos(idioma)
    resultados = []
    for pregunta, opciones in preguntas:
        correctas = {opcion.id for opcion in opciones if opcion.correcta}
        resultados.append(
            esquemas.ResultadoPregunta(
                pregunta_id=pregunta.id,
                correcta=marcadas[pregunta.id] == correctas,
                explicacion=t(pregunta.explicacion_es, pregunta.explicacion_en),
            )
        )
    aciertos = sum(1 for r in resultados if r.correcta)
    total = len(resultados)
    puntaje = (Decimal(100 * aciertos) / total).quantize(CENTESIMA, ROUND_HALF_UP)
    # Con fracciones exactas: 7 de 8 aprueba (87,5 %), 6 de 8 no (75 %).
    aprobado = aciertos >= quiz.umbral * total

    intento = Intento(
        usuario_id=usuario.id,
        quiz_id=quiz.id,
        puntaje=puntaje,
        aprobado=aprobado,
        respuestas={str(pid): sorted(ops) for pid, ops in marcadas.items()},
    )
    bd.add(intento)

    # El progreso, en una sola sentencia como en progreso.py: quiz_aprobado
    # no vuelve atrás y completada_en se llena una sola vez.
    sin_video = not armada.video_subido()
    tabla = ProgresoLeccion
    nueva = insert(tabla).values(
        usuario_id=usuario.id,
        leccion_id=quiz.leccion_id,
        quiz_aprobado=aprobado,
        completada_en=func.now() if aprobado and sin_video else None,
    )
    quiz_listo = or_(tabla.quiz_aprobado, nueva.excluded.quiz_aprobado)
    video_listo = true() if sin_video else tabla.video_completo
    nueva = nueva.on_conflict_do_update(
        index_elements=[tabla.usuario_id, tabla.leccion_id],
        set_={
            "quiz_aprobado": quiz_listo,
            "completada_en": func.coalesce(
                tabla.completada_en,
                case((and_(quiz_listo, video_listo), func.now()), else_=None),
            ),
            "actualizado_en": func.now(),
        },
    ).returning(tabla)
    guardada = await bd.scalar(nueva, execution_options={"populate_existing": True})
    await bd.flush()
    mejor = await _mejor_puntaje(bd, usuario, quiz.id)
    await bd.commit()

    return esquemas.IntentoResultado(
        id=intento.id,
        puntaje=float(puntaje),
        aprobado=aprobado,
        umbral=float(quiz.umbral),
        mejor_puntaje=mejor if mejor is not None else float(puntaje),
        preguntas=resultados,
        progreso=contenido.progreso_de(
            guardada, quiz.leccion_id, completada=guardada.completada_en is not None
        ),
    )
