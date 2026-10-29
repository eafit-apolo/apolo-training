"""Importador de contenido (B-04): lectura, validación y carga.

DoD 1: importar dos veces no duplica. DoD 4: acepta las plantillas de la C-01.
DoD 5: carga el módulo de ejemplo (el m00 real) con su lección, video y quiz.
"""

import logging
import shutil
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.importar import main
from app.models import (
    Curso,
    Intento,
    Leccion,
    LeccionVideo,
    Modulo,
    Opcion,
    Pregunta,
    ProgresoLeccion,
    Quiz,
    Video,
)
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import (
    ErrorContenido,
    leer_contenido,
    revisar_plantillas,
)
from tests.ayuda_contenido import BIENVENIDA, SSH, armar_contenido, contenido_real
from tests.ayuda_sesion import crear_usuario

TABLAS = (Curso, Modulo, Leccion, Video, LeccionVideo, Quiz, Pregunta, Opcion)


def errores_de(raiz: Path) -> list[str]:
    with pytest.raises(ErrorContenido) as error:
        leer_contenido(raiz)
    return error.value.errores


async def contar(bd: AsyncSession) -> dict[str, int]:
    return {
        tabla.__tablename__: await bd.scalar(select(func.count()).select_from(tabla))
        for tabla in TABLAS
    }


# ─── Lectura y validación (sin base) ─────────────────────────────────────────


def test_el_contenido_real_y_las_plantillas_son_validos() -> None:
    raiz = contenido_real()
    curso = leer_contenido(raiz)

    assert curso.slug == "induccion"
    assert curso.modulos[0].slug == "m00"
    assert revisar_plantillas(raiz) == []


def test_lee_el_curso_de_ejemplo(tmp_path: Path) -> None:
    curso = leer_contenido(armar_contenido(tmp_path / "content"))

    assert [m.slug for m in curso.modulos] == ["m00", "m01", "m02"]
    m01 = curso.modulos[1]
    assert [leccion.slug for leccion in m01.lecciones] == ["vpn", "ssh"]
    assert m01.lecciones[0].videos == {
        "windows": "m01-vpn-windows",
        "macos": "m01-vpn-macos",
        "linux": "m01-vpn-linux",
    }
    ssh = m01.lecciones[1]
    assert ssh.practicas == ("conexion",)
    assert ssh.preguntas[0].multiple is True
    assert curso.modulos[0].lecciones[0].contenido_es.startswith("## Objetivos")


@pytest.mark.parametrize(
    ("archivos", "esperado"),
    [
        ({"es/_curso.md": None}, "falta _curso.md"),
        (
            {
                "es/m03/_modulo.md": None,
                "es/m03/x.md": BIENVENIDA.replace("m00/bienvenida", "m03/x"),
            },
            "es/m03: falta _modulo.md",
        ),
        ({"es/m00/bienvenida.md": "sin front matter\n"}, "falta el front matter"),
        ({"es/m00/bienvenida.md": "---\nid: [\n---\n"}, "no es YAML válido"),
        (
            {
                "es/m00/bienvenida.md": BIENVENIDA.replace(
                    "orden: 1", "orden: 1\ntipo: video"
                )
            },
            "'tipo' was unexpected",
        ),
        (
            {
                "es/m00/bienvenida.md": BIENVENIDA.replace(
                    "        correcta: true\n", ""
                )
            },
            "$.quiz[0].opciones",
        ),
        (
            {
                "es/m00/bienvenida.md": BIENVENIDA.replace(
                    "id: m00/bienvenida", "id: m00/otra"
                )
            },
            "debe ser 'm00/bienvenida', la ruta del archivo",
        ),
        (
            {"es/m01/ssh.md": SSH.replace("orden: 2", "orden: 1")},
            "es/m01: orden 1: lo tienen 2 lecciones",
        ),
        (
            {"es/m01/ssh.md": SSH.replace("clave: m01-ssh", "clave: m00-login")},
            "la clave debe empezar por m01-",
        ),
        (
            {
                "es/m01/ssh.md": SSH.replace(
                    "clave: m01-ssh",
                    "clave: m01-ssh\n    enunciado: x\n    opciones: [{texto: a, correcta: true}, {texto: b}]\n    explicacion: x\n  - clave: m01-ssh",
                )
            },
            "quiz m01-ssh: la clave está en 2 preguntas",
        ),
        ({"es/m02/lectura.md": None}, "es/m02: el módulo no tiene lecciones"),
        (
            {"es/modulo-5/_modulo.md": "x"},
            "es/modulo-5: una carpeta de módulo se llama mNN",
        ),
        ({"en/m00/otra.md": BIENVENIDA}, "en/m00/otra.md: no tiene par en es/"),
        (
            {"en/m00/bienvenida.md": BIENVENIDA.replace("duracion: 3", "duracion: 4")},
            "duracion: debe ser igual al de es/m00/bienvenida.md",
        ),
        (
            {
                "en/m00/bienvenida.md": BIENVENIDA.replace(
                    "clave: m00-login", "clave: m00-otra"
                )
            },
            "las claves deben ser las de es/m00/bienvenida.md",
        ),
        (
            {
                "en/m00/bienvenida.md": BIENVENIDA.replace(
                    "      - texto: Correr simulaciones.\n",
                    "      - texto: Correr simulaciones.\n        correcta: true\n",
                )
            },
            "cuáles son correctas",
        ),
    ],
)
def test_rechaza_el_contenido_que_no_cumple(
    tmp_path: Path, archivos: dict[str, str | None], esperado: str
) -> None:
    errores = errores_de(armar_contenido(tmp_path / "content", archivos))

    assert any(esperado in e for e in errores), errores


def test_junta_todos_los_errores(tmp_path: Path) -> None:
    raiz = armar_contenido(
        tmp_path / "content",
        {
            "es/m00/bienvenida.md": BIENVENIDA.replace("orden: 1", "orden: 0"),
            "es/m01/ssh.md": SSH.replace("[conexion]", "[ondemand]"),
        },
    )

    errores = errores_de(raiz)

    assert any(e.startswith("es/m00/bienvenida.md: $.orden") for e in errores)
    assert any(e.startswith("es/m01/ssh.md: $.practicas[0]") for e in errores)


def test_una_plantilla_rota_se_detecta(tmp_path: Path) -> None:
    raiz = armar_contenido(tmp_path / "content")
    plantilla = raiz / "es" / "_plantilla.md"
    plantilla.write_text(
        plantilla.read_text().replace("duracion: 13", "duracion: trece")
    )

    assert any("$.duracion" in e for e in revisar_plantillas(raiz))


def test_revisar_por_la_linea_de_comandos(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.importar")
    bien = armar_contenido(tmp_path / "bien")
    mal = armar_contenido(tmp_path / "mal", {"es/m02/lectura.md": LECTURA_SIN_TITULO})

    assert main(["--revisar", "--dir", str(bien)]) == 0
    assert (
        "Contenido válido: curso induccion, 3 módulos, 4 lecciones y 2 preguntas."
        in caplog.text
    )
    assert main(["--revisar", "--dir", str(mal)]) == 1
    assert "es/m02/lectura.md: $: 'titulo' is a required property" in caplog.text
    assert "no se cargó nada" in caplog.text


LECTURA_SIN_TITULO = "---\nid: m02/lectura\norden: 1\nduracion: 2\n---\n\nTexto.\n"


# ─── Carga en la base ────────────────────────────────────────────────────────


async def test_importar_dos_veces_no_duplica(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    curso = leer_contenido(armar_contenido(tmp_path / "content"))

    primera = await cargar_contenido(sesion_bd, curso)
    filas = await contar(sesion_bd)
    segunda = await cargar_contenido(sesion_bd, curso)

    assert primera.creados["lecciones"] == 4
    assert primera.creados["modulos"] == 3
    # Lo recién creado no se cuenta también como actualizado.
    assert not primera.actualizados
    assert primera.creados["videos"] == 4
    assert primera.creados["opciones"] == 5
    assert segunda.sin_cambios, segunda.texto()
    assert await contar(sesion_bd) == filas


async def test_carga_el_modulo_de_ejemplo_real(sesion_bd: AsyncSession) -> None:
    resumen = await cargar_contenido(sesion_bd, leer_contenido(contenido_real()))

    leccion = await sesion_bd.scalar(
        select(Leccion).where(Leccion.slug == "bienvenida")
    )
    assert leccion is not None
    assert leccion.publicada
    video = await sesion_bd.scalar(
        select(Video).join(LeccionVideo).where(LeccionVideo.leccion_id == leccion.id)
    )
    assert video.clave == "m00-bienvenida"
    assert video.archivo is None
    quiz = await sesion_bd.scalar(select(Quiz).where(Quiz.leccion_id == leccion.id))
    preguntas = list(
        await sesion_bd.scalars(select(Pregunta).where(Pregunta.quiz_id == quiz.id))
    )
    assert {p.clave for p in preguntas} == {"m00-login", "m00-aprobar"}
    assert resumen.creados["modulos"] >= 1


async def test_acepta_las_plantillas_como_un_modulo(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    real = contenido_real() / "es"
    raiz = armar_contenido(
        tmp_path / "content",
        {
            "es/m05/_modulo.md": (real / "_plantilla-modulo.md").read_text(
                encoding="utf-8"
            ),
            "es/m05/trabajos.md": (real / "_plantilla.md").read_text(encoding="utf-8"),
        },
    )

    await cargar_contenido(sesion_bd, leer_contenido(raiz))

    leccion = await sesion_bd.scalar(select(Leccion).where(Leccion.slug == "trabajos"))
    assert leccion.practicas == ["memoria"]
    assert leccion.contenido_es.startswith("<!--")


async def test_los_cambios_se_aplican_sin_perder_progreso(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    raiz = tmp_path / "content"
    await cargar_contenido(sesion_bd, leer_contenido(armar_contenido(raiz)))
    usuario = await crear_usuario(sesion_bd)
    ssh = await sesion_bd.scalar(select(Leccion).where(Leccion.slug == "ssh"))
    sesion_bd.add(
        ProgresoLeccion(usuario_id=usuario.id, leccion_id=ssh.id, quiz_aprobado=True)
    )
    await sesion_bd.flush()

    # Se cambia un título, se invierte el orden de m01 y sale la lección de VPN.
    cambios = {
        "es/m00/bienvenida.md": BIENVENIDA.replace(
            "titulo: Bienvenida", "titulo: Hola"
        ),
        "es/m01/ssh.md": SSH.replace("orden: 2", "orden: 1"),
        "es/m01/vpn.md": None,
    }
    resumen = await cargar_contenido(
        sesion_bd, leer_contenido(armar_contenido(raiz, cambios))
    )

    assert resumen.despublicados["lecciones"] == 1
    assert resumen.actualizados["lecciones"] == 2
    assert not resumen.creados
    vpn = await sesion_bd.scalar(select(Leccion).where(Leccion.slug == "vpn"))
    assert vpn.publicada is False
    await sesion_bd.refresh(ssh)
    assert ssh.orden == 1
    bienvenida = await sesion_bd.scalar(
        select(Leccion).where(Leccion.slug == "bienvenida")
    )
    assert bienvenida.titulo_es == "Hola"
    progreso = await sesion_bd.get(ProgresoLeccion, (usuario.id, ssh.id))
    assert progreso is not None
    assert progreso.quiz_aprobado

    # Vuelve la lección de VPN, con un orden que ya no choca.
    resumen = await cargar_contenido(
        sesion_bd,
        leer_contenido(
            armar_contenido(raiz, {**cambios, "es/m01/vpn.md": VPN_TERCERA})
        ),
    )
    await sesion_bd.refresh(vpn)
    assert vpn.publicada is True
    assert vpn.orden == 3


VPN_TERCERA = """---
id: m01/vpn
titulo: La VPN
orden: 3
duracion: 4
video: m01-vpn
---

Texto.
"""


async def test_preguntas_y_opciones_siguen_al_repo(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    raiz = tmp_path / "content"
    await cargar_contenido(sesion_bd, leer_contenido(armar_contenido(raiz)))
    antes = await sesion_bd.scalar(select(Pregunta).where(Pregunta.clave == "m01-ssh"))

    sin_opcion = SSH.replace("      - texto: Con FTP.\n", "")
    resumen = await cargar_contenido(
        sesion_bd, leer_contenido(armar_contenido(raiz, {"es/m01/ssh.md": sin_opcion}))
    )

    assert resumen.borrados["opciones"] == 1
    despues = await sesion_bd.scalar(
        select(Pregunta).where(Pregunta.clave == "m01-ssh")
    )
    assert despues.id == antes.id
    textos = list(
        await sesion_bd.scalars(
            select(Opcion.texto_es)
            .where(Opcion.pregunta_id == despues.id)
            .order_by(Opcion.orden)
        )
    )
    assert textos == ["Con SSH.", "Con la terminal de la plataforma."]

    # Sin quiz y sin intentos, el quiz se borra con sus preguntas.
    sin_quiz = SSH.split("quiz:")[0] + "---\n\nTexto.\n"
    resumen = await cargar_contenido(
        sesion_bd, leer_contenido(armar_contenido(raiz, {"es/m01/ssh.md": sin_quiz}))
    )
    assert resumen.borrados["quizzes"] == 1
    assert (
        await sesion_bd.scalar(select(Pregunta).where(Pregunta.clave == "m01-ssh"))
        is None
    )


async def test_no_quita_un_quiz_que_ya_tiene_intentos(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    raiz = tmp_path / "content"
    await cargar_contenido(sesion_bd, leer_contenido(armar_contenido(raiz)))
    usuario = await crear_usuario(sesion_bd)
    quiz = await sesion_bd.scalar(
        select(Quiz).join(Leccion).where(Leccion.slug == "ssh")
    )
    sesion_bd.add(
        Intento(
            usuario_id=usuario.id,
            quiz_id=quiz.id,
            puntaje=50,
            aprobado=False,
            respuestas={},
        )
    )
    await sesion_bd.flush()

    sin_quiz = SSH.split("quiz:")[0] + "---\n\nTexto.\n"
    with pytest.raises(ErrorContenido, match="errores") as error:
        await cargar_contenido(
            sesion_bd,
            leer_contenido(armar_contenido(raiz, {"es/m01/ssh.md": sin_quiz})),
        )
    assert "ya tiene 1 intentos del quiz" in error.value.errores[0]


async def test_el_ingles_llena_las_columnas_en(
    tmp_path: Path, sesion_bd: AsyncSession
) -> None:
    ingles = (
        BIENVENIDA.replace("titulo: Bienvenida", "titulo: Welcome")
        .replace("¿Qué se hace en el login?", "What do you do on the login node?")
        .replace("Enviar trabajos.", "Submit jobs.")
        .replace("Texto de la bienvenida.", "Welcome text.")
    )
    raiz = armar_contenido(tmp_path / "content", {"en/m00/bienvenida.md": ingles})

    await cargar_contenido(sesion_bd, leer_contenido(raiz))

    leccion = await sesion_bd.scalar(
        select(Leccion).where(Leccion.slug == "bienvenida")
    )
    assert leccion.titulo_en == "Welcome"
    assert "Welcome text." in leccion.contenido_en
    pregunta = await sesion_bd.scalar(
        select(Pregunta).where(Pregunta.clave == "m00-login")
    )
    assert pregunta.enunciado_en == "What do you do on the login node?"
    ssh = await sesion_bd.scalar(select(Leccion).where(Leccion.slug == "ssh"))
    assert ssh.titulo_en is None


def test_copia_del_contenido_real_sin_curso_falla(tmp_path: Path) -> None:
    copia = tmp_path / "content"
    shutil.copytree(contenido_real(), copia)
    (copia / "es" / "_curso.md").unlink()

    assert any("falta _curso.md" in e for e in errores_de(copia))
