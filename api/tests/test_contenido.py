"""Rutas de contenido (B-04): cursos, módulos y lecciones por slug.

DoD 2: una lección sin inglés devuelve la española con `fallback`.
DoD 3: el módulo n+1 se abre al completar el n.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import ahora
from app.models import Leccion, ProgresoLeccion, Usuario, Video
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from tests.ayuda_contenido import BIENVENIDA, armar_contenido
from tests.ayuda_sesion import crear_usuario, ingresar

CURSO = "/api/cursos/induccion"


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    ingles = BIENVENIDA.replace("titulo: Bienvenida", "titulo: Welcome").replace(
        "Texto de la bienvenida.", "Welcome text."
    )
    raiz = armar_contenido(tmp_path / "content", {"en/m00/bienvenida.md": ingles})
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def estudiante(sesion_bd: AsyncSession, contenido: Path) -> Usuario:
    return await crear_usuario(sesion_bd, "ana")


async def entrar(cliente: AsyncClient, usuario: Usuario) -> None:
    respuesta = await ingresar(cliente, usuario.username)
    assert respuesta.status_code == 200


async def completar(bd: AsyncSession, usuario: Usuario, *slugs: str) -> None:
    for slug in slugs:
        leccion = await bd.scalar(select(Leccion).where(Leccion.slug == slug))
        bd.add(
            ProgresoLeccion(
                usuario_id=usuario.id, leccion_id=leccion.id, completada_en=ahora()
            )
        )
    await bd.flush()


def estados(curso: dict) -> dict[str, str]:
    return {m["slug"]: m["estado"] for m in curso["modulos"]}


# ─── Desbloqueo (DoD 3) ──────────────────────────────────────────────────────


async def test_sin_avance_solo_el_modulo_0_esta_abierto(
    cliente_bd: AsyncClient, estudiante: Usuario
) -> None:
    await entrar(cliente_bd, estudiante)

    curso = (await cliente_bd.get(CURSO)).json()

    assert estados(curso) == {"m00": "en_curso", "m01": "bloqueado", "m02": "bloqueado"}
    m01 = curso["modulos"][1]
    # Las lecciones de cada módulo vienen con el curso (la web hace una sola petición).
    assert [leccion["slug"] for leccion in m01["lecciones"]] == ["vpn", "ssh"]
    assert m01["lecciones"][0]["completada"] is False
    assert m01["bloqueado_por"]["slug"] == "m00"
    assert curso["modulos"][0]["bloqueado_por"] is None
    assert curso["continuar"] == {
        "id": curso["continuar"]["id"],
        "slug": "bienvenida",
        "modulo": "m00",
        "modulo_numero": 0,
        "titulo": "Bienvenida",
    }
    assert curso["avance_pct"] == 0
    assert curso["lecciones_total"] == 4


async def test_completar_un_modulo_abre_el_siguiente(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida")
    await entrar(cliente_bd, estudiante)

    curso = (await cliente_bd.get(CURSO)).json()

    assert estados(curso) == {"m00": "completo", "m01": "en_curso", "m02": "bloqueado"}
    assert curso["modulos"][0]["lecciones"][0]["completada"] is True
    assert curso["continuar"]["slug"] == "vpn"
    assert curso["modulos_completos"] == 1
    assert curso["avance_pct"] == 25


async def test_el_modulo_sigue_en_curso_mientras_falte_una_leccion(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida", "vpn")
    await entrar(cliente_bd, estudiante)

    curso = (await cliente_bd.get(CURSO)).json()

    assert estados(curso)["m01"] == "en_curso"
    assert estados(curso)["m02"] == "bloqueado"
    assert curso["continuar"]["slug"] == "ssh"
    assert curso["modulos"][1]["lecciones_completas"] == 1


async def test_una_leccion_de_un_modulo_bloqueado_no_cuenta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "lectura")
    await entrar(cliente_bd, estudiante)

    curso = (await cliente_bd.get(CURSO)).json()

    assert estados(curso)["m02"] == "bloqueado"
    assert curso["lecciones_completas"] == 0


async def test_con_todo_completo_no_hay_que_continuar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida", "vpn", "ssh", "lectura")
    await entrar(cliente_bd, estudiante)

    curso = (await cliente_bd.get(CURSO)).json()

    assert set(estados(curso).values()) == {"completo"}
    assert curso["continuar"] is None
    assert curso["avance_pct"] == 100


async def test_el_catalogo_trae_el_avance(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida")
    await entrar(cliente_bd, estudiante)

    cursos = (await cliente_bd.get("/api/cursos")).json()

    assert [c["slug"] for c in cursos] == ["induccion"]
    assert cursos[0]["lecciones_completas"] == 1
    assert cursos[0]["duracion_min"] == 14
    assert cursos[0]["videos"] == 2
    assert "modulos" not in cursos[0]


# ─── Módulos y lecciones ─────────────────────────────────────────────────────


async def test_un_modulo_bloqueado_se_ve_con_sus_lecciones(
    cliente_bd: AsyncClient, estudiante: Usuario
) -> None:
    await entrar(cliente_bd, estudiante)

    modulo = (await cliente_bd.get(f"{CURSO}/modulos/m01")).json()

    assert modulo["estado"] == "bloqueado"
    assert [leccion["slug"] for leccion in modulo["lecciones"]] == ["vpn", "ssh"]
    assert modulo["lecciones"][1]["componentes"] == ["lectura", "practica", "quiz"]
    assert (modulo["videos"], modulo["practicas"], modulo["preguntas"]) == (1, 1, 1)
    assert modulo["componentes"] == ["video", "lectura", "practica", "quiz"]


async def test_un_estudiante_no_abre_una_leccion_de_un_modulo_bloqueado(
    cliente_bd: AsyncClient, estudiante: Usuario
) -> None:
    await entrar(cliente_bd, estudiante)

    respuesta = await cliente_bd.get(f"{CURSO}/lecciones/m01/ssh")

    assert respuesta.status_code == 403
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == "modulo_bloqueado"
    assert cuerpo["bloqueado_por"]["slug"] == "m00"


@pytest.mark.parametrize("rol", ["instructor", "admin"])
async def test_instructores_y_admins_abren_lecciones_bloqueadas(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, contenido: Path, rol: str
) -> None:
    usuario = await crear_usuario(sesion_bd, "carla", rol=rol)
    await entrar(cliente_bd, usuario)

    respuesta = await cliente_bd.get(f"{CURSO}/lecciones/m02/lectura")

    assert respuesta.status_code == 200
    assert respuesta.json()["slug"] == "lectura"


async def test_la_leccion_trae_lo_que_tiene_y_su_progreso(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida")
    await entrar(cliente_bd, estudiante)

    vpn = (await cliente_bd.get(f"{CURSO}/lecciones/m01/vpn")).json()

    assert vpn["modulo"]["slug"] == "m01"
    assert vpn["curso"] == "induccion"
    assert [v["sistema"] for v in vpn["videos"]] == ["linux", "macos", "windows"]
    video = vpn["videos"][0]["video"]
    assert video["clave"] == "m01-vpn-linux"
    assert video["disponible"] is False
    assert video["url"] is None
    assert vpn["practicas"] == []
    assert vpn["quiz_id"] is None
    assert vpn["anterior"]["slug"] == "bienvenida"
    assert vpn["siguiente"]["slug"] == "ssh"
    assert vpn["progreso"]["completada"] is False
    assert vpn["contenido"] == "## Objetivos\n\nConéctate a la VPN."

    ssh = (await cliente_bd.get(f"{CURSO}/lecciones/m01/ssh")).json()
    assert ssh["practicas"] == ["conexion"]
    assert ssh["quiz_id"] is not None
    assert ssh["siguiente"] == {
        "id": ssh["siguiente"]["id"],
        "slug": "lectura",
        "modulo": "m02",
        "modulo_numero": 2,
        "titulo": "Una lectura",
    }
    # Las respuestas correctas nunca salen con la lección (B-06).
    assert "correcta" not in (await cliente_bd.get(f"{CURSO}/lecciones/m01/ssh")).text


async def test_un_video_subido_trae_su_url_y_subtitulos(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    video = await sesion_bd.scalar(select(Video).where(Video.clave == "m00-bienvenida"))
    video.archivo = "m00/m00-bienvenida-es.mp4"
    video.duracion_seg = 150
    video.vtt_en = "m00/m00-bienvenida-en.vtt"
    await sesion_bd.flush()
    await entrar(cliente_bd, estudiante)

    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()

    ref = leccion["videos"][0]["video"]
    assert ref["disponible"] is True
    assert ref["url"] == f"/api/media/{video.id}"
    assert ref["subtitulos"] == [
        {"idioma": "en", "url": f"/api/media/{video.id}/subtitulos/en"}
    ]


@pytest.mark.parametrize(
    "ruta",
    [
        "/api/cursos/otro",
        f"{CURSO}/modulos/m09",
        f"{CURSO}/lecciones/m00/no-existe",
        f"{CURSO}/lecciones/m09/x",
    ],
)
async def test_lo_que_no_existe_da_404(
    cliente_bd: AsyncClient, estudiante: Usuario, ruta: str
) -> None:
    await entrar(cliente_bd, estudiante)

    respuesta = await cliente_bd.get(ruta)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"


async def test_una_leccion_despublicada_no_se_ve(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    vpn = await sesion_bd.scalar(select(Leccion).where(Leccion.slug == "vpn"))
    vpn.publicada = False
    await sesion_bd.flush()
    await entrar(cliente_bd, estudiante)

    modulo = (await cliente_bd.get(f"{CURSO}/modulos/m01")).json()

    assert [leccion["slug"] for leccion in modulo["lecciones"]] == ["ssh"]
    assert (await cliente_bd.get(f"{CURSO}/lecciones/m01/vpn")).status_code == 404


# ─── Idioma (DoD 2) ──────────────────────────────────────────────────────────


async def test_sin_ingles_devuelve_el_espanol_con_fallback(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    await completar(sesion_bd, estudiante, "bienvenida")
    await entrar(cliente_bd, estudiante)

    vpn = (await cliente_bd.get(f"{CURSO}/lecciones/m01/vpn?lang=en")).json()

    assert vpn["titulo"] == "La VPN"
    assert vpn["fallback"] is True


async def test_con_ingles_devuelve_el_ingles(
    cliente_bd: AsyncClient, estudiante: Usuario
) -> None:
    await entrar(cliente_bd, estudiante)

    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida?lang=en")).json()
    en_espanol = (
        await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida?lang=es")
    ).json()

    assert leccion["titulo"] == "Welcome"
    assert "Welcome text." in leccion["contenido"]
    # El módulo no tiene _modulo.md en inglés: su título sale en español.
    assert leccion["modulo"]["titulo"] == "Bienvenida"
    assert leccion["fallback"] is True
    assert en_espanol["titulo"] == "Bienvenida"
    assert en_espanol["fallback"] is False


async def test_sin_lang_usa_el_idioma_del_perfil(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, estudiante: Usuario
) -> None:
    estudiante.idioma = "en"
    await sesion_bd.flush()
    await entrar(cliente_bd, estudiante)

    leccion = (await cliente_bd.get(f"{CURSO}/lecciones/m00/bienvenida")).json()

    assert leccion["titulo"] == "Welcome"


async def test_un_idioma_que_no_existe_es_un_error_de_validacion(
    cliente_bd: AsyncClient, estudiante: Usuario
) -> None:
    await entrar(cliente_bd, estudiante)

    respuesta = await cliente_bd.get(f"{CURSO}?lang=fr")

    assert respuesta.status_code == 422
    assert respuesta.json()["errores"][0]["campo"] == "lang"
