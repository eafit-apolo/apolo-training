"""Cursos, módulos y lecciones con el avance del usuario (B-04).

Regla de desbloqueo: los módulos van en orden de `numero` y el n+1 se abre
cuando todas las lecciones publicadas del n están completas. Una lección
marcada en un módulo bloqueado no cuenta (como `armarCurso()` de la web).
Los módulos sin lecciones publicadas no se muestran.

Idioma: cada texto sale en el idioma pedido; si falta la traducción, en
español, y la respuesta lleva `fallback = true`.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errores import ErrorApi
from app.models import (
    Curso,
    Leccion,
    LeccionVideo,
    Modulo,
    Pregunta,
    ProgresoLeccion,
    Quiz,
    Usuario,
    Video,
)
from app.schemas import contenido as esquemas
from app.schemas.contenido import Componente, EstadoModulo, Idioma

# Instructores y admins pueden abrir lecciones de módulos bloqueados, para
# revisar el contenido (decisión del 29-oct).
ROLES_SIN_BLOQUEO = frozenset({"instructor", "admin"})


class Textos:
    """Elige el texto del idioma pedido y recuerda si tuvo que usar el español."""

    def __init__(self, idioma: Idioma) -> None:
        self.idioma = idioma
        self.fallback = False

    def __call__(self, es: str, en: str | None) -> str:
        if self.idioma == "es":
            return es
        if en is None:
            self.fallback = True
            return es
        return en

    def opcional(self, es: str | None, en: str | None) -> str | None:
        return None if es is None else self(es, en)


@dataclass
class _ModuloArmado:
    modulo: Modulo
    lecciones: list[Leccion]
    estado: EstadoModulo = "en_curso"
    completas: set[int] = field(default_factory=set)
    anterior: Modulo | None = None


@dataclass
class _Curso:
    """Un curso con todo lo que hace falta para responder, en pocas consultas."""

    curso: Curso
    modulos: list[_ModuloArmado]
    videos: dict[int, list[tuple[str, Video]]]
    quizzes: dict[int, tuple[int, int]]  # leccion_id → (quiz_id, preguntas)
    progreso: dict[int, ProgresoLeccion]

    def lecciones(self) -> list[tuple[_ModuloArmado, Leccion]]:
        return [(m, leccion) for m in self.modulos for leccion in m.lecciones]


async def _armar(bd: AsyncSession, curso: Curso, usuario: Usuario) -> _Curso:
    modulos = list(
        await bd.scalars(
            select(Modulo).where(Modulo.curso_id == curso.id).order_by(Modulo.numero)
        )
    )
    lecciones: dict[int, list[Leccion]] = defaultdict(list)
    for leccion in await bd.scalars(
        select(Leccion)
        .where(
            Leccion.modulo_id.in_([m.id for m in modulos]), Leccion.publicada.is_(True)
        )
        .order_by(Leccion.orden)
    ):
        lecciones[leccion.modulo_id].append(leccion)
    ids = [leccion.id for lista in lecciones.values() for leccion in lista]

    videos: dict[int, list[tuple[str, Video]]] = defaultdict(list)
    for leccion_id, sistema, video in await bd.execute(
        select(LeccionVideo.leccion_id, LeccionVideo.sistema, Video)
        .join(Video, Video.id == LeccionVideo.video_id)
        .where(LeccionVideo.leccion_id.in_(ids))
        .order_by(LeccionVideo.sistema)
    ):
        videos[leccion_id].append((sistema, video))
    quizzes = {
        leccion_id: (quiz_id, preguntas)
        for leccion_id, quiz_id, preguntas in await bd.execute(
            select(Quiz.leccion_id, Quiz.id, func.count(Pregunta.id))
            .outerjoin(Pregunta, Pregunta.quiz_id == Quiz.id)
            .where(Quiz.leccion_id.in_(ids))
            .group_by(Quiz.id)
        )
    }
    progreso = {
        p.leccion_id: p
        for p in await bd.scalars(
            select(ProgresoLeccion).where(
                ProgresoLeccion.usuario_id == usuario.id,
                ProgresoLeccion.leccion_id.in_(ids),
            )
        )
    }

    armados: list[_ModuloArmado] = []
    anterior: _ModuloArmado | None = None
    for modulo in modulos:
        if not lecciones[modulo.id]:
            continue
        armado = _ModuloArmado(modulo=modulo, lecciones=lecciones[modulo.id])
        armado.anterior = anterior.modulo if anterior else None
        if anterior is not None and anterior.estado != "completo":
            armado.estado = "bloqueado"
        else:
            armado.completas = {
                leccion.id
                for leccion in armado.lecciones
                if leccion.id in progreso
                and progreso[leccion.id].completada_en is not None
            }
            if len(armado.completas) == len(armado.lecciones):
                armado.estado = "completo"
        armados.append(armado)
        anterior = armado
    return _Curso(
        curso=curso, modulos=armados, videos=videos, quizzes=quizzes, progreso=progreso
    )


async def _buscar(bd: AsyncSession, slug: str, usuario: Usuario) -> _Curso:
    curso = await bd.scalar(
        select(Curso).where(Curso.slug == slug, Curso.publicado.is_(True))
    )
    if curso is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese curso")
    return await _armar(bd, curso, usuario)


def _componentes(datos: _Curso, leccion: Leccion) -> list[Componente]:
    componentes: list[Componente] = []
    if datos.videos.get(leccion.id):
        componentes.append("video")
    componentes.append("lectura")
    if leccion.practicas:
        componentes.append("practica")
    if leccion.id in datos.quizzes:
        componentes.append("quiz")
    return componentes


def _ref_modulo(modulo: Modulo, t: Textos) -> esquemas.ModuloRef:
    return esquemas.ModuloRef(
        id=modulo.id,
        slug=modulo.slug,
        numero=modulo.numero,
        titulo=t(modulo.titulo_es, modulo.titulo_en),
    )


def _ref_leccion(modulo: Modulo, leccion: Leccion, t: Textos) -> esquemas.LeccionRef:
    return esquemas.LeccionRef(
        id=leccion.id,
        slug=leccion.slug,
        modulo=modulo.slug,
        modulo_numero=modulo.numero,
        titulo=t(leccion.titulo_es, leccion.titulo_en),
    )


def _modulo(datos: _Curso, armado: _ModuloArmado, t: Textos) -> esquemas.ModuloResumen:
    componentes: list[Componente] = []
    for leccion in armado.lecciones:
        for componente in _componentes(datos, leccion):
            if componente not in componentes:
                componentes.append(componente)
    orden: list[Componente] = ["video", "lectura", "practica", "quiz"]
    modulo = armado.modulo
    return esquemas.ModuloResumen(
        id=modulo.id,
        slug=modulo.slug,
        numero=modulo.numero,
        titulo=t(modulo.titulo_es, modulo.titulo_en),
        resumen=t(modulo.resumen_es, modulo.resumen_en),
        duracion_min=modulo.duracion_min,
        estado=armado.estado,
        bloqueado_por=_ref_modulo(armado.anterior, t)
        if armado.estado == "bloqueado" and armado.anterior
        else None,
        lecciones_total=len(armado.lecciones),
        lecciones_completas=len(armado.completas),
        videos=sum(1 for leccion in armado.lecciones if datos.videos.get(leccion.id)),
        practicas=sum(len(leccion.practicas) for leccion in armado.lecciones),
        preguntas=sum(
            datos.quizzes.get(leccion.id, (0, 0))[1] for leccion in armado.lecciones
        ),
        componentes=[c for c in orden if c in componentes],
    )


def _resumen(datos: _Curso, t: Textos) -> dict[str, object]:
    curso = datos.curso
    lecciones = datos.lecciones()
    completas = sum(len(m.completas) for m in datos.modulos)
    continuar = next(
        (
            _ref_leccion(m.modulo, leccion, t)
            for m in datos.modulos
            if m.estado == "en_curso"
            for leccion in m.lecciones
            if leccion.id not in m.completas
        ),
        None,
    )
    return {
        "id": curso.id,
        "slug": curso.slug,
        "titulo": t(curso.titulo_es, curso.titulo_en),
        "descripcion": t.opcional(curso.descripcion_es, curso.descripcion_en),
        "duracion_min": sum(m.modulo.duracion_min for m in datos.modulos),
        "videos": sum(1 for _, leccion in lecciones if datos.videos.get(leccion.id)),
        "avance_pct": round(100 * completas / len(lecciones)) if lecciones else 0,
        "modulos_total": len(datos.modulos),
        "modulos_completos": sum(1 for m in datos.modulos if m.estado == "completo"),
        "lecciones_total": len(lecciones),
        "lecciones_completas": completas,
        "continuar": continuar,
    }


async def listar_cursos(
    bd: AsyncSession, usuario: Usuario, idioma: Idioma
) -> list[esquemas.CursoResumen]:
    cursos = await bd.scalars(
        select(Curso).where(Curso.publicado.is_(True)).order_by(Curso.orden, Curso.id)
    )
    resultado = []
    for curso in cursos:
        t = Textos(idioma)
        datos = await _armar(bd, curso, usuario)
        resultado.append(
            esquemas.CursoResumen(**_resumen(datos, t), fallback=t.fallback)
        )
    return resultado


async def obtener_curso(
    bd: AsyncSession, slug: str, usuario: Usuario, idioma: Idioma
) -> esquemas.CursoDetalle:
    datos = await _buscar(bd, slug, usuario)
    t = Textos(idioma)
    resumen = _resumen(datos, t)
    modulos = [
        esquemas.ModuloConLecciones(
            **_modulo(datos, m, t).model_dump(), lecciones=_lecciones(datos, m, t)
        )
        for m in datos.modulos
    ]
    return esquemas.CursoDetalle(**resumen, modulos=modulos, fallback=t.fallback)


def _armado(datos: _Curso, slug: str) -> _ModuloArmado:
    armado = next((m for m in datos.modulos if m.modulo.slug == slug), None)
    if armado is None:
        raise ErrorApi(404, "no_encontrado", "No existe ese módulo")
    return armado


def _lecciones(
    datos: _Curso, armado: _ModuloArmado, t: Textos
) -> list[esquemas.LeccionResumen]:
    return [
        esquemas.LeccionResumen(
            id=leccion.id,
            slug=leccion.slug,
            orden=leccion.orden,
            titulo=t(leccion.titulo_es, leccion.titulo_en),
            duracion_min=leccion.duracion_min,
            completada=leccion.id in armado.completas,
            componentes=_componentes(datos, leccion),
        )
        for leccion in armado.lecciones
    ]


async def obtener_modulo(
    bd: AsyncSession, curso: str, modulo: str, usuario: Usuario, idioma: Idioma
) -> esquemas.ModuloDetalle:
    """Un módulo bloqueado también se ve (título y lecciones); lo que no se
    abre son sus lecciones."""
    datos = await _buscar(bd, curso, usuario)
    armado = _armado(datos, modulo)
    t = Textos(idioma)
    return esquemas.ModuloDetalle(
        **_modulo(datos, armado, t).model_dump(),
        lecciones=_lecciones(datos, armado, t),
        curso_id=datos.curso.id,
        curso=datos.curso.slug,
        fallback=t.fallback,
    )


def _video(video: Video) -> esquemas.VideoRef:
    disponible = video.archivo is not None
    subtitulos = [
        esquemas.Subtitulo(
            idioma=idioma, url=f"/api/media/{video.id}/subtitulos/{idioma}"
        )
        for idioma, vtt in (("es", video.vtt_es), ("en", video.vtt_en))
        if disponible and vtt is not None
    ]
    return esquemas.VideoRef(
        id=video.id,
        clave=video.clave,
        disponible=disponible,
        duracion_seg=video.duracion_seg,
        url=f"/api/media/{video.id}" if disponible else None,
        subtitulos=subtitulos,
    )


async def obtener_leccion(
    bd: AsyncSession,
    curso: str,
    modulo: str,
    leccion: str,
    usuario: Usuario,
    idioma: Idioma,
) -> esquemas.Leccion:
    datos = await _buscar(bd, curso, usuario)
    armado = _armado(datos, modulo)
    actual = next((x for x in armado.lecciones if x.slug == leccion), None)
    if actual is None:
        raise ErrorApi(404, "no_encontrado", "No existe esa lección")
    t = Textos(idioma)
    if armado.estado == "bloqueado" and usuario.rol not in ROLES_SIN_BLOQUEO:
        anterior = _ref_modulo(armado.anterior, t) if armado.anterior else None
        raise ErrorApi(
            403,
            "modulo_bloqueado",
            "Este módulo se abre al completar el anterior",
            extra={"bloqueado_por": anterior.model_dump() if anterior else None},
        )

    # Anterior y siguiente en todo el curso, también entre módulos. La web sabe
    # por el estado de cada módulo si la siguiente ya se puede abrir.
    todas = [(m.modulo, x) for m, x in datos.lecciones()]
    posicion = next(i for i, (_, x) in enumerate(todas) if x.id == actual.id)
    anterior_ref = _ref_leccion(*todas[posicion - 1], t) if posicion > 0 else None
    siguiente_ref = (
        _ref_leccion(*todas[posicion + 1], t) if posicion + 1 < len(todas) else None
    )

    fila = datos.progreso.get(actual.id)
    progreso = esquemas.ProgresoLeccion(
        leccion_id=actual.id,
        video_posicion_seg=fila.video_posicion_seg if fila else 0,
        video_max_seg=fila.video_max_seg if fila else 0,
        video_completo=fila.video_completo if fila else False,
        quiz_aprobado=fila.quiz_aprobado if fila else False,
        completada=actual.id in armado.completas,
        completada_en=fila.completada_en
        if fila and actual.id in armado.completas
        else None,
    )
    quiz = datos.quizzes.get(actual.id)
    return esquemas.Leccion(
        id=actual.id,
        slug=actual.slug,
        curso=datos.curso.slug,
        modulo=_ref_modulo(armado.modulo, t),
        orden=actual.orden,
        titulo=t(actual.titulo_es, actual.titulo_en),
        contenido=t(actual.contenido_es, actual.contenido_en),
        duracion_min=actual.duracion_min,
        componentes=_componentes(datos, actual),
        videos=[
            esquemas.VideoLeccion(sistema=sistema, video=_video(video))
            for sistema, video in datos.videos.get(actual.id, [])
        ],
        practicas=list(actual.practicas),
        quiz_id=quiz[0] if quiz else None,
        anterior=anterior_ref,
        siguiente=siguiente_ref,
        progreso=progreso,
        fallback=t.fallback,
    )
