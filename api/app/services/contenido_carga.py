"""Carga en la base de lo que leyó contenido_lector (B-04).

Busca todo por slug o clave, así que cargar dos veces el mismo contenido no
crea ni cambia nada. Nunca borra progreso:

- una lección que sale del repo queda con `publicada = false` (y su `orden` se
  aparta, para que otra pueda tomar su lugar);
- una pregunta que sale se borra con sus opciones; los intentos guardan sus
  respuestas en jsonb y su puntaje;
- un quiz que sale se borra solo si nadie lo ha intentado.

No confirma la transacción: eso lo hace quien llama. Los `orden` únicos son
diferibles, así que reordenar no choca a mitad de camino.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Curso,
    Intento,
    Leccion,
    LeccionVideo,
    Modulo,
    Opcion,
    Pregunta,
    Quiz,
    Video,
)
from app.services.contenido_lector import (
    CursoLeido,
    ErrorContenido,
    LeccionLeida,
    ModuloLeido,
    PreguntaLeida,
)

# Una lección despublicada se corre a este rango de `orden` para no ocupar el
# de las publicadas (el único es por módulo y orden).
ORDEN_DESPUBLICADA = 100_000


@dataclass
class Resumen:
    """Cuántas filas creó, cambió, despublicó o borró la carga, por tabla."""

    creados: Counter[str] = field(default_factory=Counter)
    actualizados: Counter[str] = field(default_factory=Counter)
    despublicados: Counter[str] = field(default_factory=Counter)
    borrados: Counter[str] = field(default_factory=Counter)

    @property
    def sin_cambios(self) -> bool:
        return not (
            self.creados or self.actualizados or self.despublicados or self.borrados
        )

    def texto(self) -> str:
        if self.sin_cambios:
            return "sin cambios"
        partes = []
        for nombre, contador in (
            ("nuevos", self.creados),
            ("actualizados", self.actualizados),
            ("despublicados", self.despublicados),
            ("borrados", self.borrados),
        ):
            if contador:
                detalle = ", ".join(
                    f"{tabla} {n}" for tabla, n in sorted(contador.items())
                )
                partes.append(f"{nombre}: {detalle}")
        return "; ".join(partes)


def _asignar(fila: Any, **valores: Any) -> bool:
    """Pone los valores que cambian. Devuelve si cambió alguno."""
    cambio = False
    for columna, valor in valores.items():
        if getattr(fila, columna) != valor:
            setattr(fila, columna, valor)
            cambio = True
    return cambio


class _Carga:
    def __init__(self, bd: AsyncSession) -> None:
        self.bd = bd
        self.resumen = Resumen()

    def nueva(self, fila: Any) -> Any:
        self.bd.add(fila)
        self.resumen.creados[fila.__tablename__] += 1
        return fila

    def cambio(self, fila: Any, **valores: Any) -> None:
        if _asignar(fila, **valores):
            self.resumen.actualizados[fila.__tablename__] += 1

    async def curso(self, leido: CursoLeido) -> Curso:
        curso = await self.bd.scalar(select(Curso).where(Curso.slug == leido.slug))
        valores = {
            "titulo_es": leido.titulo_es,
            "titulo_en": leido.titulo_en,
            "descripcion_es": leido.descripcion_es,
            "descripcion_en": leido.descripcion_en,
            "publicado": True,
        }
        if curso is None:
            curso = self.nueva(Curso(slug=leido.slug, **valores))
            await self.bd.flush()
        else:
            self.cambio(curso, **valores)
        # content/ describe un solo curso: si cambió de id, el anterior se oculta.
        for otro in await self.bd.scalars(
            select(Curso).where(Curso.id != curso.id, Curso.publicado.is_(True))
        ):
            otro.publicado = False
            self.resumen.despublicados[Curso.__tablename__] += 1
        return curso

    async def modulos(
        self, curso: Curso, leidos: tuple[ModuloLeido, ...]
    ) -> dict[str, Modulo]:
        existentes = {
            m.slug: m
            for m in await self.bd.scalars(
                select(Modulo).where(Modulo.curso_id == curso.id)
            )
        }
        modulos: dict[str, Modulo] = {}
        nuevos: set[str] = set()
        for leido in leidos:
            valores = {
                "numero": leido.numero,
                "titulo_es": leido.titulo_es,
                "titulo_en": leido.titulo_en,
                "resumen_es": leido.resumen_es,
                "resumen_en": leido.resumen_en,
                "duracion_min": leido.duracion,
            }
            modulo = existentes.get(leido.slug)
            if modulo is None:
                modulo = self.nueva(
                    Modulo(curso_id=curso.id, slug=leido.slug, **valores)
                )
                nuevos.add(leido.slug)
            else:
                self.cambio(modulo, **valores)
            modulos[leido.slug] = modulo
        await self.bd.flush()
        # Cada módulo se abre al completar el anterior que siga en el repo.
        anterior: Modulo | None = None
        for leido in leidos:
            modulo = modulos[leido.slug]
            prerrequisito = anterior.id if anterior else None
            if leido.slug in nuevos:
                # Recién creado: ya cuenta como nuevo, no también como actualizado.
                modulo.prerrequisito_id = prerrequisito
            else:
                self.cambio(modulo, prerrequisito_id=prerrequisito)
            anterior = modulo
        return modulos

    async def lecciones(
        self, curso: Curso, leidos: tuple[ModuloLeido, ...], modulos: dict[str, Modulo]
    ) -> list[tuple[Leccion, LeccionLeida]]:
        existentes = {
            (leccion.modulo_id, leccion.slug): leccion
            for leccion in await self.bd.scalars(
                select(Leccion).join(Modulo).where(Modulo.curso_id == curso.id)
            )
        }
        cargadas: list[tuple[Leccion, LeccionLeida]] = []
        for leido_modulo in leidos:
            modulo = modulos[leido_modulo.slug]
            for leida in leido_modulo.lecciones:
                valores = {
                    "orden": leida.orden,
                    "titulo_es": leida.titulo_es,
                    "titulo_en": leida.titulo_en,
                    "contenido_es": leida.contenido_es,
                    "contenido_en": leida.contenido_en,
                    "duracion_min": leida.duracion,
                    "practicas": list(leida.practicas),
                    "publicada": True,
                }
                leccion = existentes.get((modulo.id, leida.slug))
                if leccion is None:
                    leccion = self.nueva(
                        Leccion(modulo_id=modulo.id, slug=leida.slug, **valores)
                    )
                elif _asignar(leccion, **valores):
                    leccion.actualizado_en = func.now()
                    self.resumen.actualizados[Leccion.__tablename__] += 1
                cargadas.append((leccion, leida))
        await self.bd.flush()
        vistas = {leccion.id for leccion, _ in cargadas}
        for leccion in existentes.values():
            if leccion.id not in vistas and leccion.publicada:
                leccion.publicada = False
                leccion.orden = ORDEN_DESPUBLICADA + leccion.id
                self.resumen.despublicados[Leccion.__tablename__] += 1
        return cargadas

    async def videos(self, cargadas: list[tuple[Leccion, LeccionLeida]]) -> None:
        claves = {clave for _, leida in cargadas for clave in leida.videos.values()}
        videos = {
            v.clave: v
            for v in await self.bd.scalars(select(Video).where(Video.clave.in_(claves)))
        }
        for clave in sorted(claves - videos.keys()):
            # Sin archivo: el instructor lo sube desde el panel (B-05).
            videos[clave] = self.nueva(Video(clave=clave))
        await self.bd.flush()

        ids = [leccion.id for leccion, _ in cargadas]
        actuales: dict[int, dict[str, LeccionVideo]] = {}
        for fila in await self.bd.scalars(
            select(LeccionVideo).where(LeccionVideo.leccion_id.in_(ids))
        ):
            actuales.setdefault(fila.leccion_id, {})[fila.sistema] = fila
        for leccion, leida in cargadas:
            tiene = actuales.get(leccion.id, {})
            for sistema, fila in tiene.items():
                if sistema not in leida.videos:
                    await self.bd.delete(fila)
                    self.resumen.borrados[LeccionVideo.__tablename__] += 1
            for sistema, clave in leida.videos.items():
                if sistema in tiene:
                    self.cambio(tiene[sistema], video_id=videos[clave].id)
                else:
                    self.nueva(
                        LeccionVideo(
                            leccion_id=leccion.id,
                            sistema=sistema,
                            video_id=videos[clave].id,
                        )
                    )

    async def quizzes(self, cargadas: list[tuple[Leccion, LeccionLeida]]) -> None:
        ids = [leccion.id for leccion, _ in cargadas]
        quizzes = {
            q.leccion_id: q
            for q in await self.bd.scalars(select(Quiz).where(Quiz.leccion_id.in_(ids)))
        }
        claves = {p.clave for _, leida in cargadas for p in leida.preguntas or ()}
        preguntas = {
            p.clave: p
            for p in await self.bd.scalars(
                select(Pregunta).where(Pregunta.clave.in_(claves))
            )
        }
        for leccion, leida in cargadas:
            quiz = quizzes.get(leccion.id)
            if leida.preguntas is None:
                if quiz is not None:
                    await self.quitar_quiz(quiz, leccion)
                continue
            if quiz is None:
                quiz = self.nueva(
                    Quiz(leccion_id=leccion.id, es_final=leida.quiz_final)
                )
                await self.bd.flush()
            else:
                self.cambio(quiz, es_final=leida.quiz_final)
            await self.preguntas(quiz, leida.preguntas, preguntas)

    async def quitar_quiz(self, quiz: Quiz, leccion: Leccion) -> None:
        intentos = await self.bd.scalar(
            select(func.count()).select_from(Intento).where(Intento.quiz_id == quiz.id)
        )
        if intentos:
            raise ErrorContenido(
                [
                    f"lección {leccion.slug}: ya tiene {intentos} intentos del quiz, así que "
                    "no se le puede quitar; deja al menos una pregunta"
                ]
            )
        await self.bd.delete(quiz)
        self.resumen.borrados[Quiz.__tablename__] += 1

    async def preguntas(
        self,
        quiz: Quiz,
        leidas: tuple[PreguntaLeida, ...],
        por_clave: dict[str, Pregunta],
    ) -> None:
        claves = {p.clave for p in leidas}
        sobran = await self.bd.scalars(
            select(Pregunta).where(
                Pregunta.quiz_id == quiz.id, Pregunta.clave.not_in(claves)
            )
        )
        for pregunta in sobran:
            await self.bd.delete(pregunta)
            self.resumen.borrados[Pregunta.__tablename__] += 1
        for orden, leida in enumerate(leidas, start=1):
            valores = {
                "quiz_id": quiz.id,
                "orden": orden,
                "enunciado_es": leida.enunciado_es,
                "enunciado_en": leida.enunciado_en,
                "explicacion_es": leida.explicacion_es,
                "explicacion_en": leida.explicacion_en,
                "multiple": leida.multiple,
            }
            pregunta = por_clave.get(leida.clave)
            if pregunta is None:
                pregunta = self.nueva(Pregunta(clave=leida.clave, **valores))
                await self.bd.flush()
            else:
                # Si la pregunta cambió de lección, se mueve con su clave.
                self.cambio(pregunta, **valores)
            await self.opciones(pregunta, leida)

    async def opciones(self, pregunta: Pregunta, leida: PreguntaLeida) -> None:
        actuales = list(
            await self.bd.scalars(
                select(Opcion)
                .where(Opcion.pregunta_id == pregunta.id)
                .order_by(Opcion.orden)
            )
        )
        for orden, opcion in enumerate(leida.opciones, start=1):
            valores = {
                "orden": orden,
                "texto_es": opcion.texto_es,
                "texto_en": opcion.texto_en,
                "correcta": opcion.correcta,
            }
            if orden <= len(actuales):
                self.cambio(actuales[orden - 1], **valores)
            else:
                self.nueva(Opcion(pregunta_id=pregunta.id, **valores))
        if len(actuales) > len(leida.opciones):
            await self.bd.execute(
                delete(Opcion).where(
                    Opcion.pregunta_id == pregunta.id,
                    Opcion.orden > len(leida.opciones),
                )
            )
            self.resumen.borrados[Opcion.__tablename__] += len(actuales) - len(
                leida.opciones
            )


async def cargar_contenido(bd: AsyncSession, leido: CursoLeido) -> Resumen:
    """Deja la base igual a `leido`. Lanza ErrorContenido si no se puede sin
    perder datos (quitar un quiz que ya tiene intentos)."""
    carga = _Carga(bd)
    curso = await carga.curso(leido)
    modulos = await carga.modulos(curso, leido.modulos)
    cargadas = await carga.lecciones(curso, leido.modulos, modulos)
    await carga.videos(cargadas)
    await carga.quizzes(cargadas)
    await bd.flush()
    return carga.resumen
