"""Qué video acepta la plataforma (DoD 4 de la B-05), sin base de datos."""

from pathlib import Path

import pytest

from app.services.video_formato import FormatoInvalido, leer_formato
from tests.ayuda_medios import INVALIDOS, generar_video

# Lo que dice el error de cada caso de INVALIDOS.
MENSAJES = {
    "mpeg4.mp4": "El video es mpeg4; tiene que ser H.264",
    "diez-bits.mp4": "H.264 yuv420p10le; tiene que ser de 8 bits 4:2:0",
    "yuv444.mp4": "H.264 yuv444p; tiene que ser de 8 bits 4:2:0",
    "sin-perdida.mp4": "perfil High 4:4:4 Predictive; tiene que ser Baseline",
    "mp3.mp4": "El audio es mp3; tiene que ser AAC",
    "h264.mkv": "El contenedor es matroska,webm; tiene que ser MP4",
    "vp9.webm": "El contenedor es matroska,webm; tiene que ser MP4",
}


def test_cubre_todos_los_invalidos() -> None:
    assert MENSAJES.keys() == INVALIDOS.keys()


def test_h264_y_aac_se_acepta_con_su_duracion(tmp_path: Path) -> None:
    video = generar_video(tmp_path / "bueno.mp4", segundos=3)

    assert leer_formato(video).duracion_seg == 3


def test_sin_audio_tambien_vale(tmp_path: Path) -> None:
    video = generar_video(tmp_path / "mudo.mp4", audio=None)

    assert leer_formato(video).duracion_seg == 2


@pytest.mark.parametrize("nombre", sorted(INVALIDOS))
def test_otro_formato_se_rechaza_diciendo_que_trae(tmp_path: Path, nombre: str) -> None:
    video = generar_video(tmp_path / nombre, **INVALIDOS[nombre])

    with pytest.raises(FormatoInvalido, match=MENSAJES[nombre]):
        leer_formato(video)


@pytest.mark.parametrize("contenido", [b"", b"hola, no soy un video"])
def test_lo_que_no_es_video_se_rechaza(tmp_path: Path, contenido: bytes) -> None:
    archivo = tmp_path / "falso.mp4"
    archivo.write_bytes(contenido)

    with pytest.raises(FormatoInvalido, match="No es un video que se pueda leer"):
        leer_formato(archivo)


def test_un_mp4_cortado_se_rechaza(tmp_path: Path) -> None:
    """Una subida que se cortó a la mitad (sin el índice del MP4)."""
    video = generar_video(tmp_path / "bueno.mp4")
    cortado = tmp_path / "cortado.mp4"
    cortado.write_bytes(video.read_bytes()[:1000])

    with pytest.raises(FormatoInvalido):
        leer_formato(cortado)
