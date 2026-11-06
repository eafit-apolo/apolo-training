"""Qué trae un video subido (B-05), leído con PyAV (FFmpeg dentro del paquete `av`).

Se acepta lo que reproduce cualquier navegador: contenedor MP4, video H.264 de
8 bits 4:2:0 (yuv420p) con perfil Baseline, Main o High (lo que graba OBS con
la guía de docs/video.md) y audio AAC, o sin audio. Un H.264 de 10 bits, 4:4:4
o sin pérdida (perfil High 4:4:4 Predictive, aunque sea 4:2:0) también es
«H.264», pero los navegadores no lo reproducen: por eso se revisan los píxeles
y el perfil.

Es código síncrono (FFmpeg lee el archivo): la API lo llama en un hilo aparte.
"""

from dataclasses import dataclass
from pathlib import Path

# Los nombres son los de FFmpeg (`codec.canonical_name` y el demuxer).
CONTENEDOR = "mp4"
VIDEO = "h264"
PIXELES = frozenset({"yuv420p", "yuvj420p"})
PERFILES = frozenset({"Constrained Baseline", "Baseline", "Main", "High"})
AUDIO = "aac"


class FormatoInvalido(Exception):
    """El archivo no es un video que la plataforma pueda servir; el mensaje
    dice qué trae y qué se espera."""


@dataclass(frozen=True)
class Formato:
    duracion_seg: int


def leer_formato(ruta: Path) -> Formato:
    # Se importa aquí: así FFmpeg se carga solo en el worker que recibe una
    # subida, no en cada worker al arrancar.
    import av

    try:
        with av.open(str(ruta)) as contenedor:
            demuxer = contenedor.format.name
            duracion = contenedor.duration
            videos = [
                (
                    s.codec_context.codec.canonical_name,
                    s.codec_context.pix_fmt,
                    s.profile,
                )
                for s in contenedor.streams.video
                # Una carátula guardada como «video» no cuenta.
                if not s.disposition & av.stream.Disposition.attached_pic
            ]
            audios = [
                s.codec_context.codec.canonical_name for s in contenedor.streams.audio
            ]
    except av.FFmpegError as exc:
        raise FormatoInvalido("No es un video que se pueda leer") from exc

    # El demuxer de MP4 se llama «mov,mp4,m4a,3gp,3g2,mj2».
    if CONTENEDOR not in demuxer.split(","):
        raise FormatoInvalido(f"El contenedor es {demuxer}; tiene que ser MP4")
    if not videos:
        raise FormatoInvalido("El archivo no trae video")
    for codec, pixeles, perfil in videos:
        if codec != VIDEO:
            raise FormatoInvalido(f"El video es {codec}; tiene que ser H.264")
        if pixeles not in PIXELES:
            raise FormatoInvalido(
                f"El video es H.264 {pixeles}; tiene que ser de 8 bits 4:2:0 (yuv420p)"
            )
        if perfil not in PERFILES:
            raise FormatoInvalido(
                f"El video es H.264 con perfil {perfil}; tiene que ser Baseline, "
                "Main o High"
            )
    for codec in audios:
        if codec != AUDIO:
            raise FormatoInvalido(f"El audio es {codec}; tiene que ser AAC")
    if not duracion or duracion <= 0:
        raise FormatoInvalido("No se pudo leer la duración del video")
    return Formato(duracion_seg=max(1, round(duracion / av.time_base)))
