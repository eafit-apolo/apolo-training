"""Videos y subtítulos pequeños para las pruebas de la B-05.

Los videos se generan con PyAV (la misma dependencia que lee el formato al
subir), así no hay archivos binarios en el repo. Cada uno pesa unos pocos KB.
"""

from fractions import Fraction
from pathlib import Path

import av

ANCHO, ALTO, FPS, MUESTREO = 64, 48, 10, 48000

VTT_ES = "WEBVTT\n\n00:00.000 --> 00:01.500\nHola, esto es una prueba.\n"
VTT_EN = "\ufeffWEBVTT - con BOM y título\n\n00:00.000 --> 00:01.500\nHi.\n"


def generar_video(
    ruta: Path,
    *,
    formato: str = "mp4",
    video: str = "libx264",
    audio: str | None = "aac",
    pixeles: str = "yuv420p",
    opciones: dict[str, str] | None = None,
    segundos: int = 2,
) -> Path:
    """Un video de colores lisos y audio en silencio. `opciones` va al
    codificador de video (por ejemplo {"qp": "0"} para x264 sin pérdida)."""
    with av.open(str(ruta), "w", format=formato) as salida:
        # Las dos pistas antes del primer paquete: ahí se escribe la cabecera.
        pista_video = salida.add_stream(video, rate=FPS, options=opciones)
        pista_video.width, pista_video.height = ANCHO, ALTO
        pista_video.pix_fmt = pixeles
        pista_audio = None
        if audio is not None:
            pista_audio = salida.add_stream(audio, rate=MUESTREO)
            pista_audio.layout = "mono"

        for i in range(segundos * FPS):
            cuadro = av.VideoFrame(ANCHO, ALTO, "yuv420p")
            for plano in cuadro.planes:
                plano.update(bytes([i * 9 % 256]) * plano.buffer_size)
            if pixeles != "yuv420p":
                cuadro = cuadro.reformat(format=pixeles)
            cuadro.pts, cuadro.time_base = i, Fraction(1, FPS)
            salida.mux(pista_video.encode(cuadro))
        salida.mux(pista_video.encode())

        if pista_audio is not None:
            contexto = pista_audio.codec_context
            muestras = contexto.frame_size or 1024
            for pts in range(0, segundos * MUESTREO, muestras):
                cuadro = av.AudioFrame(
                    format=contexto.format.name, layout="mono", samples=muestras
                )
                for plano in cuadro.planes:
                    plano.update(bytes(plano.buffer_size))
                cuadro.sample_rate = MUESTREO
                cuadro.pts, cuadro.time_base = pts, Fraction(1, MUESTREO)
                salida.mux(pista_audio.encode(cuadro))
            salida.mux(pista_audio.encode())
    return ruta


# Nombre → opciones de generar_video(): lo que la API rechaza, y por qué.
INVALIDOS: dict[str, dict[str, object]] = {
    "mpeg4.mp4": {"video": "mpeg4"},
    "diez-bits.mp4": {"pixeles": "yuv420p10le"},
    "yuv444.mp4": {"pixeles": "yuv444p"},
    # 4:2:0, pero sin pérdida: x264 usa el perfil High 4:4:4 Predictive.
    "sin-perdida.mp4": {"opciones": {"qp": "0"}},
    "mp3.mp4": {"audio": "libmp3lame"},
    "h264.mkv": {"formato": "matroska"},
    "vp9.webm": {"formato": "webm", "video": "libvpx-vp9", "audio": "libopus"},
}
