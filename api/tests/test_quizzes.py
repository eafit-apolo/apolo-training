"""Quizzes (B-06): GET /api/quizzes/{id} y POST /api/quizzes/{id}/intentos.

El curso de prueba (tests/ayuda_contenido.py): m00/bienvenida tiene un video
sin subir y un quiz de una pregunta; m01/ssh, un quiz de una pregunta de varias
respuestas (m01 está bloqueado al empezar). Para el umbral se usa una
bienvenida con cinco preguntas (`CINCO`).

Las pruebas no saben cuál opción es la correcta por la API (nunca la da): la
leen de la base.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Curso,
    Intento,
    Leccion,
    Opcion,
    Pregunta,
    ProgresoLeccion,
    Quiz,
    Usuario,
    Video,
)
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import BIENVENIDA, armar_contenido
from tests.ayuda_sesion import con_csrf, crear_usuario, ingresar

CURSO = "/api/cursos/induccion"


def _cinco_preguntas() -> str:
    """La bienvenida con cinco preguntas: cuatro de una respuesta (la primera
    opción es la correcta) y la quinta de varias (la primera y la tercera)."""
    preguntas = "".join(
        f"""  - clave: m00-p{n}
    enunciado: Pregunta {n}
    opciones:
      - texto: Bien {n}.
        correcta: true
      - texto: Mal {n}.
    explicacion: Explicación {n}.
"""
        for n in range(1, 5)
    )
    preguntas += """  - clave: m00-p5
    enunciado: Pregunta 5, de varias
    opciones:
      - texto: Sí, una.
        correcta: true
      - texto: No.
      - texto: Sí, otra.
        correcta: true
    explicacion: Explicación 5.
"""
    inicio = BIENVENIDA.index("quiz:\n") + len("quiz:\n")
    fin = BIENVENIDA.index("---\n", inicio)
    return BIENVENIDA[:inicio] + preguntas + BIENVENIDA[fin:]


CINCO = {"es/m00/bienvenida.md": _cinco_preguntas()}

# La bienvenida traducida: mismo id, mismos datos y las mismas preguntas.
EN = {
    "en/m00/bienvenida.md": BIENVENIDA.replace("titulo: Bienvenida", "titulo: Welcome")
    .replace("¿Qué se hace en el login?", "What do you do on the login node?")
    .replace("Enviar trabajos.", "Submit jobs.")
    .replace("Correr simulaciones.", "Run simulations.")
    .replace(
        "El login es para preparar y enviar.",
        "The login node is for preparing and submitting.",
    )
    .replace("Texto de la bienvenida.", "Welcome text.")
}


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


async def recargar(bd: AsyncSession, contenido: Path, archivos: dict) -> None:
    await cargar_contenido(bd, leer_contenido(armar_contenido(contenido, archivos)))


@pytest.fixture
async def estudiante(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path
) -> Usuario:
    usuario = await crear_usuario(sesion_bd, "ana")
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    return usuario


async def id_de(bd: AsyncSession, slug: str) -> int:
    return await bd.scalar(select(Leccion.id).where(Leccion.slug == slug))


async def quiz_de(bd: AsyncSession, slug: str) -> int:
    return await bd.scalar(
        select(Quiz.id)
        .join(Leccion, Leccion.id == Quiz.leccion_id)
        .where(Leccion.slug == slug)
    )


async def claves(
    bd: AsyncSession, quiz_id: int
) -> list[tuple[int, list[int], set[int]]]:
    """Por pregunta, en orden: su id, sus opciones y las correctas."""
    resultado = []
    for pregunta in await bd.scalars(
        select(Pregunta).where(Pregunta.quiz_id == quiz_id).order_by(Pregunta.orden)
    ):
        opciones = list(
            await bd.scalars(
                select(Opcion)
                .where(Opcion.pregunta_id == pregunta.id)
                .order_by(Opcion.orden)
            )
        )
        resultado.append(
            (
                pregunta.id,
                [o.id for o in opciones],
                {o.id for o in opciones if o.correcta},
            )
        )
    return resultado


def respuestas(
    preguntas: list[tuple[int, list[int], set[int]]], aciertos: int
) -> list[dict]:
    """Las primeras `aciertos` preguntas bien y el resto con una opción incorrecta."""
    elegidas = []
    for n, (pregunta_id, opciones, correctas) in enumerate(preguntas):
        if n < aciertos:
            marcadas = sorted(correctas)
        else:
            marcadas = [next(o for o in opciones if o not in correctas)]
        elegidas.append({"pregunta_id": pregunta_id, "opciones": marcadas})
    return elegidas


async def enviar(
    cliente: AsyncClient,
    quiz_id: int | str,
    elegidas: list[dict],
    lang: str | None = None,
) -> Response:
    return await cliente.post(
        f"/api/quizzes/{quiz_id}/intentos",
        json={"respuestas": elegidas},
        headers=con_csrf(cliente),
        params={"lang": lang} if lang else None,
    )


async def aprobar(cliente: AsyncClient, bd: AsyncSession, slug: str) -> Response:
    quiz_id = await quiz_de(bd, slug)
    preguntas = await claves(bd, quiz_id)
    return await enviar(cliente, quiz_id, respuestas(preguntas, len(preguntas)))


async def subir_video(bd: AsyncSession, clave: str, duracion: int = 100) -> int:
    """Hace como si el MP4 ya estuviera subido y devuelve el id del video."""
    return await bd.scalar(
        update(Video)
        .where(Video.clave == clave)
        .values(archivo=f"{clave}.mp4", duracion_seg=duracion)
        .returning(Video.id)
    )


async def reportar(
    cliente: AsyncClient, leccion: int, video: int, segundo: int
) -> Response:
    return await cliente.post(
        "/api/progreso/video",
        json={"leccion_id": leccion, "video_id": video, "segundo": segundo},
        headers=con_csrf(cliente),
    )


async def fila(bd: AsyncSession, usuario: Usuario, leccion_id: int) -> ProgresoLeccion:
    return await bd.scalar(
        select(ProgresoLeccion)
        .where(
            ProgresoLeccion.usuario_id == usuario.id,
            ProgresoLeccion.leccion_id == leccion_id,
        )
        .execution_options(populate_existing=True)
    )


def estados(curso: dict) -> dict[str, str]:
    return {m["slug"]: m["estado"] for m in curso["modulos"]}


# --- Leer el quiz -------------------------------------------------------------


async def test_el_quiz_llega_sin_la_opcion_correcta(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()

    respuesta = await cliente_bd.get(f"/api/quizzes/{leccion['quiz_id']}")

    assert respuesta.status_code == 200
    quiz = respuesta.json()
    assert "correcta" not in respuesta.text
    assert quiz["leccion_id"] == leccion["id"]
    assert (quiz["umbral"], quiz["es_final"], quiz["mejor_puntaje"]) == (
        0.8,
        False,
        None,
    )
    assert [p["orden"] for p in quiz["preguntas"]] == [1, 2, 3, 4, 5]
    assert [p["multiple"] for p in quiz["preguntas"]] == [False] * 4 + [True]
    quinta = quiz["preguntas"][4]
    assert quinta["enunciado"] == "Pregunta 5, de varias"
    assert [set(o) for o in quinta["opciones"]] == [{"id", "orden", "texto"}] * 3
    assert [o["texto"] for o in quinta["opciones"]] == ["Sí, una.", "No.", "Sí, otra."]


async def test_el_quiz_en_ingles(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")

    sin_traducir = (await cliente_bd.get(f"/api/quizzes/{quiz_id}?lang=en")).json()
    await recargar(sesion_bd, contenido, EN)
    traducido = (await cliente_bd.get(f"/api/quizzes/{quiz_id}?lang=en")).json()

    assert sin_traducir["fallback"] is True
    assert sin_traducir["preguntas"][0]["enunciado"] == "¿Qué se hace en el login?"
    assert traducido["fallback"] is False
    assert traducido["preguntas"][0]["enunciado"] == "What do you do on the login node?"
    assert [o["texto"] for o in traducido["preguntas"][0]["opciones"]] == [
        "Submit jobs.",
        "Run simulations.",
    ]


@pytest.mark.parametrize(
    ("rol", "codigo"), [("estudiante", 403), ("instructor", 200), ("admin", 200)]
)
async def test_el_quiz_de_un_modulo_bloqueado_se_lee_como_la_leccion(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    rol: str,
    codigo: int,
) -> None:
    await crear_usuario(sesion_bd, "carla", rol=rol)
    await ingresar(cliente_bd, "carla")

    respuesta = await cliente_bd.get(f"/api/quizzes/{await quiz_de(sesion_bd, 'ssh')}")

    assert respuesta.status_code == codigo
    if codigo == 403:
        assert respuesta.json()["codigo"] == "modulo_bloqueado"
        assert respuesta.json()["bloqueado_por"]["slug"] == "m00"


async def test_un_quiz_que_no_existe_o_sin_publicar_da_404(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    elegidas = respuestas(await claves(sesion_bd, quiz_id), 1)
    assert (await cliente_bd.get("/api/quizzes/999999999")).status_code == 404
    assert (await enviar(cliente_bd, 999999999, elegidas)).status_code == 404

    await sesion_bd.execute(
        update(Leccion).where(Leccion.slug == "bienvenida").values(publicada=False)
    )
    leer = await cliente_bd.get(f"/api/quizzes/{quiz_id}")
    responder = await enviar(cliente_bd, quiz_id, elegidas)

    assert (leer.status_code, leer.json()["codigo"]) == (404, "no_encontrado")
    assert (responder.status_code, responder.json()["codigo"]) == (404, "no_encontrado")
    assert await sesion_bd.scalar(select(func.count()).select_from(Intento)) == 0


# --- Calificar ----------------------------------------------------------------


async def test_aprobar_completa_una_leccion_sin_video_subido(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    respuesta = await aprobar(cliente_bd, sesion_bd, "bienvenida")

    assert respuesta.status_code == 201
    resultado = respuesta.json()
    assert (resultado["puntaje"], resultado["aprobado"], resultado["umbral"]) == (
        100,
        True,
        0.8,
    )
    assert resultado["mejor_puntaje"] == 100
    assert resultado["preguntas"] == [
        {
            "pregunta_id": (
                await claves(sesion_bd, await quiz_de(sesion_bd, "bienvenida"))
            )[0][0],
            "correcta": True,
            "explicacion": "El login es para preparar y enviar.",
        }
    ]
    assert resultado["progreso"]["quiz_aprobado"] is True
    assert resultado["progreso"]["completada"] is True
    curso = (await cliente_bd.get(CURSO)).json()
    assert estados(curso) == {"m00": "completo", "m01": "en_curso", "m02": "bloqueado"}


async def test_reprobar_no_completa_y_se_puede_reintentar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)

    mal = (await enviar(cliente_bd, quiz_id, respuestas(preguntas, 0))).json()
    bien = (await enviar(cliente_bd, quiz_id, respuestas(preguntas, 1))).json()

    assert (mal["puntaje"], mal["aprobado"], mal["mejor_puntaje"]) == (0, False, 0)
    assert mal["preguntas"][0]["correcta"] is False
    assert mal["preguntas"][0]["explicacion"] == "El login es para preparar y enviar."
    assert mal["progreso"]["quiz_aprobado"] is False
    assert mal["progreso"]["completada"] is False
    assert (bien["aprobado"], bien["progreso"]["completada"]) == (True, True)
    intentos = await sesion_bd.scalar(select(func.count()).select_from(Intento))
    assert intentos == 2


@pytest.mark.parametrize(
    ("aciertos", "puntaje", "aprobado"),
    [(5, 100, True), (4, 80, True), (3, 60, False), (0, 0, False)],
)
async def test_aprueba_con_el_80_por_ciento(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
    aciertos: int,
    puntaje: int,
    aprobado: bool,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")

    resultado = (
        await enviar(
            cliente_bd, quiz_id, respuestas(await claves(sesion_bd, quiz_id), aciertos)
        )
    ).json()

    assert (resultado["puntaje"], resultado["aprobado"]) == (puntaje, aprobado)
    assert [p["correcta"] for p in resultado["preguntas"]] == [
        n < aciertos for n in range(5)
    ]
    assert resultado["progreso"]["completada"] is aprobado


@pytest.mark.parametrize(
    ("marcadas", "correcta"),
    [((0, 2), True), ((0,), False), ((2,), False), ((0, 1, 2), False), ((1,), False)],
)
async def test_en_una_de_varias_hay_que_marcar_todas_y_solo_las_correctas(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
    marcadas: tuple[int, ...],
    correcta: bool,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    elegidas = respuestas(preguntas, 4)
    pregunta_id, opciones, _ = preguntas[4]
    elegidas[4] = {
        "pregunta_id": pregunta_id,
        "opciones": [opciones[i] for i in marcadas],
    }

    resultado = (await enviar(cliente_bd, quiz_id, elegidas)).json()

    assert resultado["preguntas"][4]["correcta"] is correcta
    assert resultado["puntaje"] == (100 if correcta else 80)


async def test_la_respuesta_nunca_dice_cual_opcion_era_la_correcta(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")

    resultado = (
        await enviar(
            cliente_bd, quiz_id, respuestas(await claves(sesion_bd, quiz_id), 0)
        )
    ).json()

    assert set(resultado) == {
        "id",
        "puntaje",
        "aprobado",
        "umbral",
        "mejor_puntaje",
        "preguntas",
        "progreso",
    }
    # Por pregunta, solo si acertó y la explicación: ninguna opción.
    assert all(
        set(p) == {"pregunta_id", "correcta", "explicacion"}
        for p in resultado["preguntas"]
    )
    assert "opcion" not in json.dumps(resultado)


async def test_cuenta_el_mejor_y_lo_aprobado_no_vuelve_atras(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    primero = (await enviar(cliente_bd, quiz_id, respuestas(preguntas, 1))).json()

    despues = (await enviar(cliente_bd, quiz_id, respuestas(preguntas, 0))).json()

    assert (despues["puntaje"], despues["aprobado"], despues["mejor_puntaje"]) == (
        0,
        False,
        100,
    )
    assert despues["progreso"]["quiz_aprobado"] is True
    assert despues["progreso"]["completada_en"] == primero["progreso"]["completada_en"]
    quiz = (await cliente_bd.get(f"/api/quizzes/{quiz_id}")).json()
    assert quiz["mejor_puntaje"] == 100


async def test_el_intento_guarda_las_respuestas_y_el_puntaje(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    elegidas = respuestas(preguntas, 4)
    # Marcadas en desorden: se guardan ordenadas.
    elegidas[4]["opciones"] = sorted(preguntas[4][2], reverse=True)

    resultado = (await enviar(cliente_bd, quiz_id, elegidas)).json()

    intento = await sesion_bd.get(Intento, resultado["id"])
    assert intento.usuario_id == estudiante.id
    assert intento.quiz_id == quiz_id
    assert (intento.puntaje, intento.aprobado) == (Decimal("100.00"), True)
    assert intento.respuestas == {
        str(e["pregunta_id"]): sorted(e["opciones"]) for e in elegidas
    }


async def test_un_puntaje_con_decimales(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    # Con tres preguntas, dos aciertos son 66,67 % (no aprueba).
    cinco = CINCO["es/m00/bienvenida.md"]
    inicio = cinco.index("  - clave: m00-p4")
    fin = cinco.index("---\n", inicio)
    await recargar(
        sesion_bd, contenido, {"es/m00/bienvenida.md": cinco[:inicio] + cinco[fin:]}
    )
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    assert len(preguntas) == 3

    resultado = (await enviar(cliente_bd, quiz_id, respuestas(preguntas, 2))).json()

    assert (resultado["puntaje"], resultado["aprobado"]) == (66.67, False)
    intento = await sesion_bd.get(Intento, resultado["id"])
    assert intento.puntaje == Decimal("66.67")


@pytest.mark.parametrize(
    "caso",
    [
        "falta_una",
        "repetida",
        "de_otra_pregunta",
        "opcion_repetida",
        "dos_en_una_de_una",
        "de_otro_quiz",
    ],
)
async def test_respuestas_que_no_corresponden_al_quiz_dan_422(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
    caso: str,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    elegidas = respuestas(preguntas, 5)
    primera, segunda = elegidas[0], elegidas[1]
    if caso == "falta_una":
        elegidas.pop()
    elif caso == "repetida":
        elegidas.append(dict(primera))
    elif caso == "de_otra_pregunta":
        primera["opciones"] = [preguntas[1][1][0]]
    elif caso == "opcion_repetida":
        segunda["opciones"] = segunda["opciones"] * 2
    elif caso == "dos_en_una_de_una":
        primera["opciones"] = preguntas[0][1]
    else:
        otra = (await claves(sesion_bd, await quiz_de(sesion_bd, "ssh")))[0]
        elegidas.append({"pregunta_id": otra[0], "opciones": sorted(otra[2])})

    respuesta = await enviar(cliente_bd, quiz_id, elegidas)

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "respuestas_invalidas"
    assert await sesion_bd.scalar(select(func.count()).select_from(Intento)) == 0


@pytest.mark.parametrize(
    "cuerpo",
    [{"respuestas": []}, {"respuestas": [{"pregunta_id": 1, "opciones": []}]}, {}],
)
async def test_un_cuerpo_mal_formado_da_422(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario, cuerpo: dict
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")

    respuesta = await cliente_bd.post(
        f"/api/quizzes/{quiz_id}/intentos", json=cuerpo, headers=con_csrf(cliente_bd)
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"


async def test_la_explicacion_en_el_idioma_pedido(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    await recargar(sesion_bd, contenido, EN)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)

    resultado = (
        await enviar(cliente_bd, quiz_id, respuestas(preguntas, 0), lang="en")
    ).json()

    assert resultado["preguntas"][0]["explicacion"] == (
        "The login node is for preparing and submitting."
    )


@pytest.mark.parametrize("rol", ["estudiante", "instructor", "admin"])
async def test_un_modulo_bloqueado_no_se_responde_con_ningun_rol(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path, rol: str
) -> None:
    await crear_usuario(sesion_bd, "carla", rol=rol)
    await ingresar(cliente_bd, "carla")

    respuesta = await aprobar(cliente_bd, sesion_bd, "ssh")

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "modulo_bloqueado"
    assert await sesion_bd.scalar(select(func.count()).select_from(Intento)) == 0


async def test_sin_el_token_csrf_da_403(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)

    respuesta = await cliente_bd.post(
        f"/api/quizzes/{quiz_id}/intentos",
        json={"respuestas": respuestas(preguntas, 1)},
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"


@pytest.mark.parametrize("quiz", ["0", str(2**63), "abc"])
async def test_un_id_invalido_da_422(
    cliente_bd: AsyncClient, estudiante: Usuario, quiz: str
) -> None:
    leer = await cliente_bd.get(f"/api/quizzes/{quiz}")
    responder = await enviar(cliente_bd, quiz, [{"pregunta_id": 1, "opciones": [1]}])

    assert (leer.status_code, leer.json()["codigo"]) == (422, "datos_invalidos")
    assert (responder.status_code, responder.json()["codigo"]) == (
        422,
        "datos_invalidos",
    )


# --- Video y quiz juntos ------------------------------------------------------


async def test_con_video_subido_primero_el_quiz_y_luego_el_video(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir_video(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")

    aprobado = (await aprobar(cliente_bd, sesion_bd, "bienvenida")).json()
    visto = (await reportar(cliente_bd, leccion, video, 90)).json()

    assert aprobado["progreso"]["quiz_aprobado"] is True
    assert aprobado["progreso"]["completada"] is False
    assert (visto["video_completo"], visto["completada"]) == (True, True)


async def test_con_video_subido_primero_el_video_y_luego_el_quiz(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir_video(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")

    visto = (await reportar(cliente_bd, leccion, video, 100)).json()
    reprobado = (
        await enviar(
            cliente_bd,
            await quiz_de(sesion_bd, "bienvenida"),
            respuestas(
                await claves(sesion_bd, await quiz_de(sesion_bd, "bienvenida")), 0
            ),
        )
    ).json()
    aprobado = (await aprobar(cliente_bd, sesion_bd, "bienvenida")).json()

    assert (visto["video_completo"], visto["completada"]) == (True, False)
    assert reprobado["progreso"]["completada"] is False
    assert aprobado["progreso"]["completada"] is True
    curso = (await cliente_bd.get(CURSO)).json()
    assert estados(curso)["m01"] == "en_curso"


async def test_con_avance_previo_del_video_aprobar_no_basta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    # La fila ya existe (vio 30 s): aprobar la actualiza sin completarla.
    video = await subir_video(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")
    await reportar(cliente_bd, leccion, video, 30)

    aprobado = (await aprobar(cliente_bd, sesion_bd, "bienvenida")).json()
    visto = (await reportar(cliente_bd, leccion, video, 90)).json()

    assert aprobado["progreso"]["quiz_aprobado"] is True
    assert aprobado["progreso"]["completada"] is False
    assert (visto["video_completo"], visto["completada"]) == (True, True)


async def test_con_quiz_ver_el_video_por_partes_no_basta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await subir_video(sesion_bd, "m00-bienvenida", duracion=100)
    leccion = await id_de(sesion_bd, "bienvenida")
    await reportar(cliente_bd, leccion, video, 30)

    visto = (await reportar(cliente_bd, leccion, video, 95)).json()
    aprobado = (await aprobar(cliente_bd, sesion_bd, "bienvenida")).json()

    assert (visto["video_completo"], visto["completada"]) == (True, False)
    assert aprobado["progreso"]["completada"] is True


async def test_completar_a_mano_da_409_en_una_leccion_con_quiz(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    leccion = await id_de(sesion_bd, "bienvenida")
    ruta = f"/api/lecciones/{leccion}/completar"

    antes = await cliente_bd.post(ruta, headers=con_csrf(cliente_bd))
    aprobado = (await aprobar(cliente_bd, sesion_bd, "bienvenida")).json()
    despues = await cliente_bd.post(ruta, headers=con_csrf(cliente_bd))

    assert antes.status_code == 409
    assert antes.json()["codigo"] == "requisitos_pendientes"
    assert despues.status_code == 200
    assert despues.json()["completada_en"] == aprobado["progreso"]["completada_en"]


async def test_con_el_quiz_aprobado_falta_el_video_subido(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await subir_video(sesion_bd, "m00-bienvenida")
    leccion = await id_de(sesion_bd, "bienvenida")
    await aprobar(cliente_bd, sesion_bd, "bienvenida")

    respuesta = await cliente_bd.post(
        f"/api/lecciones/{leccion}/completar", headers=con_csrf(cliente_bd)
    )

    assert respuesta.status_code == 409
    assert "video" in respuesta.json()["detail"]
    guardada = await fila(sesion_bd, estudiante, leccion)
    assert (guardada.quiz_aprobado, guardada.completada_en) == (True, None)


async def test_el_progreso_sobrevive_a_cerrar_sesion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await aprobar(cliente_bd, sesion_bd, "bienvenida")

    salir = await cliente_bd.post("/api/auth/logout", headers=con_csrf(cliente_bd))
    assert salir.status_code == 204
    await ingresar(cliente_bd, "ana")

    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()
    assert leccion["progreso"]["quiz_aprobado"] is True
    assert leccion["progreso"]["completada"] is True
    quiz = (await cliente_bd.get(f"/api/quizzes/{leccion['quiz_id']}")).json()
    assert quiz["mejor_puntaje"] == 100


# --- Mi progreso --------------------------------------------------------------

MI = "/api/me/progreso"


def leccion(progreso: dict, slug: str) -> dict:
    return next(
        lec
        for modulo in progreso["modulos"]
        for lec in modulo["lecciones"]
        if lec["slug"] == slug
    )


async def test_mi_progreso_al_empezar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    respuesta = await cliente_bd.get(MI)

    assert respuesta.status_code == 200
    progreso = respuesta.json()
    assert (progreso["curso"], progreso["avance_pct"], progreso["fallback"]) == (
        "induccion",
        0,
        False,
    )
    assert (progreso["lecciones_total"], progreso["lecciones_completas"]) == (4, 0)
    assert [(m["slug"], m["numero"], m["estado"]) for m in progreso["modulos"]] == [
        ("m00", 0, "en_curso"),
        ("m01", 1, "bloqueado"),
        ("m02", 2, "bloqueado"),
    ]
    assert [[lec["slug"] for lec in m["lecciones"]] for m in progreso["modulos"]] == [
        ["bienvenida"],
        ["vpn", "ssh"],
        ["lectura"],
    ]
    assert leccion(progreso, "bienvenida") == {
        "id": await id_de(sesion_bd, "bienvenida"),
        "slug": "bienvenida",
        "titulo": "Bienvenida",
        "completada": False,
        "video_completo": False,
        "tiene_quiz": True,
        "quiz_aprobado": False,
        "quiz_mejor_puntaje": None,
    }
    assert leccion(progreso, "vpn")["tiene_quiz"] is False
    assert leccion(progreso, "ssh")["tiene_quiz"] is True


async def test_mi_progreso_despues_de_aprobar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await aprobar(cliente_bd, sesion_bd, "bienvenida")

    progreso = (await cliente_bd.get(MI)).json()

    assert (progreso["lecciones_completas"], progreso["avance_pct"]) == (1, 25)
    m00, m01, m02 = progreso["modulos"]
    assert (m00["estado"], m00["lecciones_completas"], m00["lecciones_total"]) == (
        "completo",
        1,
        1,
    )
    assert (m01["estado"], m01["lecciones_completas"], m01["lecciones_total"]) == (
        "en_curso",
        0,
        2,
    )
    assert m02["estado"] == "bloqueado"
    bienvenida = leccion(progreso, "bienvenida")
    assert (bienvenida["completada"], bienvenida["quiz_aprobado"]) == (True, True)
    assert bienvenida["quiz_mejor_puntaje"] == 100


async def test_mi_progreso_muestra_el_mejor_puntaje_aunque_no_apruebe(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    await recargar(sesion_bd, contenido, CINCO)
    quiz_id = await quiz_de(sesion_bd, "bienvenida")
    preguntas = await claves(sesion_bd, quiz_id)
    await enviar(cliente_bd, quiz_id, respuestas(preguntas, 3))
    await enviar(cliente_bd, quiz_id, respuestas(preguntas, 1))

    bienvenida = leccion((await cliente_bd.get(MI)).json(), "bienvenida")

    assert bienvenida["quiz_mejor_puntaje"] == 60
    assert (bienvenida["quiz_aprobado"], bienvenida["completada"]) == (False, False)


async def test_mi_progreso_no_cuenta_lo_de_un_modulo_bloqueado(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    # Una fila completa en m02 (p. ej. de antes de que agregaran una lección a
    # m01) no cuenta mientras m02 esté bloqueado.
    sesion_bd.add(
        ProgresoLeccion(
            usuario_id=estudiante.id,
            leccion_id=await id_de(sesion_bd, "lectura"),
            completada_en=datetime.now(UTC),
        )
    )
    await sesion_bd.flush()

    progreso = (await cliente_bd.get(MI)).json()

    assert progreso["lecciones_completas"] == 0
    assert leccion(progreso, "lectura")["completada"] is False
    assert progreso["modulos"][2]["lecciones_completas"] == 0


async def test_mi_progreso_es_de_cada_usuario(
    cliente_bd: AsyncClient,
    crear_cliente,
    app_bd,
    sesion_bd: AsyncSession,
    estudiante: Usuario,
) -> None:
    await crear_usuario(sesion_bd, "bruno")
    otro = crear_cliente(app_bd)
    await ingresar(otro, "bruno")
    await aprobar(cliente_bd, sesion_bd, "bienvenida")

    mio = (await cliente_bd.get(MI)).json()
    suyo = (await otro.get(MI)).json()

    assert (mio["lecciones_completas"], suyo["lecciones_completas"]) == (1, 0)
    assert leccion(suyo, "bienvenida")["quiz_mejor_puntaje"] is None


async def test_mi_progreso_en_ingles(
    cliente_bd: AsyncClient,
    sesion_bd: AsyncSession,
    contenido: Path,
    estudiante: Usuario,
) -> None:
    sin_traducir = (await cliente_bd.get(MI, params={"lang": "en"})).json()
    await recargar(sesion_bd, contenido, EN)
    traducido = (await cliente_bd.get(MI, params={"lang": "en"})).json()

    assert sin_traducir["fallback"] is True
    assert leccion(sin_traducir, "bienvenida")["titulo"] == "Bienvenida"
    assert leccion(traducido, "bienvenida")["titulo"] == "Welcome"


async def test_mi_progreso_sin_un_curso_publicado(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await sesion_bd.execute(update(Curso).values(publicado=False))

    progreso = (await cliente_bd.get(MI)).json()

    assert progreso == {
        "curso": None,
        "avance_pct": 0,
        "lecciones_total": 0,
        "lecciones_completas": 0,
        "modulos": [],
        "fallback": False,
    }


async def test_mi_progreso_pide_sesion(
    cliente_bd: AsyncClient, contenido: Path
) -> None:
    respuesta = await cliente_bd.get(MI)

    assert respuesta.status_code == 401
