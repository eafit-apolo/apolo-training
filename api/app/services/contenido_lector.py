"""Lectura y validación de content/ (B-04). No toca la base de datos.

Lee content/es (y content/en si existe), valida cada front matter con los
esquemas de content/schema/ y revisa las reglas de content/README.md que un
esquema no puede expresar: id = ruta, orden único, claves de preguntas únicas
y con el prefijo del módulo, y pares es/en. Junta todos los errores antes de
fallar, para que quien escribe el contenido los vea de una vez.
"""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

IDIOMA_BASE = "es"
IDIOMA_TRADUCIDO = "en"
ARCHIVO_CURSO = "_curso.md"
ARCHIVO_MODULO = "_modulo.md"
PLANTILLAS = {"_plantilla.md": "leccion", "_plantilla-modulo.md": "modulo"}
CARPETA_MODULO = re.compile(r"^m[0-9]{2}$")
# Front matter entre dos líneas `---` al inicio del archivo.
FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)(.*)\Z", re.DOTALL)
# Datos de la lección que no se traducen: en/ debe traer los mismos que es/.
DATOS_FIJOS = ("orden", "duracion", "video", "practicas", "quiz_final")


class ErrorContenido(Exception):
    """El contenido no se puede cargar. `errores` trae una línea por problema,
    con el archivo (relativo a content/) y el campo."""

    def __init__(self, errores: list[str]) -> None:
        super().__init__(f"{len(errores)} errores en content/")
        self.errores = errores


@dataclass(frozen=True)
class OpcionLeida:
    texto_es: str
    texto_en: str | None
    correcta: bool


@dataclass(frozen=True)
class PreguntaLeida:
    clave: str
    enunciado_es: str
    enunciado_en: str | None
    explicacion_es: str
    explicacion_en: str | None
    opciones: tuple[OpcionLeida, ...]

    @property
    def multiple(self) -> bool:
        return sum(o.correcta for o in self.opciones) > 1


@dataclass(frozen=True)
class LeccionLeida:
    slug: str
    orden: int
    titulo_es: str
    titulo_en: str | None
    contenido_es: str
    contenido_en: str | None
    duracion: int
    # sistema → clave: {"todos": "m05-trabajos"} o uno por sistema en la de VPN.
    videos: dict[str, str]
    practicas: tuple[str, ...]
    preguntas: tuple[PreguntaLeida, ...] | None
    quiz_final: bool


@dataclass(frozen=True)
class ModuloLeido:
    slug: str
    numero: int
    titulo_es: str
    titulo_en: str | None
    resumen_es: str
    resumen_en: str | None
    duracion: int
    lecciones: tuple[LeccionLeida, ...]


@dataclass(frozen=True)
class CursoLeido:
    slug: str
    titulo_es: str
    titulo_en: str | None
    descripcion_es: str
    descripcion_en: str | None
    modulos: tuple[ModuloLeido, ...]

    @property
    def lecciones(self) -> int:
        return sum(len(m.lecciones) for m in self.modulos)

    @property
    def preguntas(self) -> int:
        return sum(
            len(leccion.preguntas or ())
            for modulo in self.modulos
            for leccion in modulo.lecciones
        )


@dataclass
class _Archivo:
    """Un .md ya separado en front matter y texto."""

    ruta: str
    datos: dict[str, Any]
    texto: str


@dataclass
class _Lectura:
    raiz: Path
    errores: list[str] = field(default_factory=list)
    validadores: dict[str, Draft202012Validator] = field(default_factory=dict)

    def error(self, ruta: str, mensaje: str) -> None:
        self.errores.append(f"{ruta}: {mensaje}")

    def validador(self, nombre: str) -> Draft202012Validator | None:
        if nombre not in self.validadores:
            archivo = self.raiz / "schema" / f"{nombre}.schema.json"
            try:
                esquema = json.loads(archivo.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                self.error(f"schema/{nombre}.schema.json", f"no se pudo leer ({exc})")
                return None
            self.validadores[nombre] = Draft202012Validator(esquema)
        return self.validadores[nombre]

    def leer(self, archivo: Path, esquema: str) -> _Archivo | None:
        """Lee un .md, separa el front matter y lo valida con su esquema."""
        ruta = archivo.relative_to(self.raiz).as_posix()
        try:
            texto = archivo.read_text(encoding="utf-8").replace("\r\n", "\n")
        except (OSError, UnicodeDecodeError) as exc:
            self.error(ruta, f"no se pudo leer ({exc})")
            return None
        partes = FRONT_MATTER.match(texto)
        if partes is None:
            self.error(ruta, "falta el front matter entre dos líneas ---")
            return None
        try:
            datos = yaml.safe_load(partes.group(1))
        except yaml.YAMLError as exc:
            self.error(ruta, f"el front matter no es YAML válido ({exc})")
            return None
        if not isinstance(datos, dict):
            self.error(ruta, "el front matter debe ser un objeto (campo: valor)")
            return None
        validador = self.validador(esquema)
        if validador is None:
            return None
        errores = sorted(validador.iter_errors(datos), key=lambda e: list(e.path))
        for error in errores:
            self.error(ruta, f"{error.json_path}: {error.message}")
        if errores:
            return None
        return _Archivo(ruta=ruta, datos=datos, texto=partes.group(2).strip())


def _videos(datos: dict[str, Any]) -> dict[str, str]:
    video = datos.get("video")
    if video is None:
        return {}
    if isinstance(video, str):
        return {"todos": video}
    return dict(video)


def _preguntas(
    es: list[dict[str, Any]] | None, en: list[dict[str, Any]] | None
) -> tuple[PreguntaLeida, ...] | None:
    if es is None:
        return None
    traducidas = {p["clave"]: p for p in en or []}
    preguntas = []
    for pregunta in es:
        par = traducidas.get(pregunta["clave"])
        opciones_en = par["opciones"] if par else [None] * len(pregunta["opciones"])
        preguntas.append(
            PreguntaLeida(
                clave=pregunta["clave"],
                enunciado_es=pregunta["enunciado"].strip(),
                enunciado_en=par["enunciado"].strip() if par else None,
                explicacion_es=pregunta["explicacion"].strip(),
                explicacion_en=par["explicacion"].strip() if par else None,
                opciones=tuple(
                    OpcionLeida(
                        texto_es=opcion["texto"].strip(),
                        texto_en=traducida["texto"].strip() if traducida else None,
                        correcta=bool(opcion.get("correcta", False)),
                    )
                    for opcion, traducida in zip(
                        pregunta["opciones"], opciones_en, strict=True
                    )
                ),
            )
        )
    return tuple(preguntas)


def _correctas(pregunta: dict[str, Any]) -> list[bool]:
    return [bool(o.get("correcta", False)) for o in pregunta["opciones"]]


def _revisar_par(
    lectura: _Lectura, es: _Archivo, en: _Archivo, fijos: tuple[str, ...]
) -> bool:
    """en/ traduce a es/: mismo id, mismos datos fijos y mismas preguntas."""
    bien = True
    if en.datos["id"] != es.datos["id"]:
        lectura.error(
            en.ruta,
            f"id: {en.datos['id']!r} no es el de {es.ruta} ({es.datos['id']!r})",
        )
        bien = False
    for campo in fijos:
        if en.datos.get(campo) != es.datos.get(campo):
            lectura.error(en.ruta, f"{campo}: debe ser igual al de {es.ruta}")
            bien = False
    preguntas_es = es.datos.get("quiz") or []
    preguntas_en = en.datos.get("quiz") or []
    if [p["clave"] for p in preguntas_en] != [p["clave"] for p in preguntas_es]:
        lectura.error(
            en.ruta, f"quiz: las claves deben ser las de {es.ruta}, en el mismo orden"
        )
        return False
    for p_es, p_en in zip(preguntas_es, preguntas_en, strict=True):
        if _correctas(p_en) != _correctas(p_es):
            lectura.error(
                en.ruta,
                f"quiz {p_en['clave']}: las opciones (y cuáles son correctas) deben ser "
                f"las de {es.ruta}, en el mismo orden",
            )
            bien = False
    return bien


def _revisar_leccion(lectura: _Lectura, archivo: _Archivo, modulo: str) -> None:
    """Reglas de una lección que el esquema no cubre (sin la de id = ruta)."""
    for pregunta in archivo.datos.get("quiz") or []:
        if not pregunta["clave"].startswith(f"{modulo}-"):
            lectura.error(
                archivo.ruta,
                f"quiz {pregunta['clave']}: la clave debe empezar por {modulo}-",
            )


def _leer_modulo(lectura: _Lectura, carpeta: Path) -> ModuloLeido | None:
    slug = carpeta.name
    traducida = lectura.raiz / IDIOMA_TRADUCIDO / slug
    modulo = None
    if not (carpeta / ARCHIVO_MODULO).is_file():
        lectura.error(f"{IDIOMA_BASE}/{slug}", f"falta {ARCHIVO_MODULO}")
    else:
        modulo = lectura.leer(carpeta / ARCHIVO_MODULO, "modulo")
    if modulo is not None and modulo.datos["id"] != slug:
        lectura.error(
            modulo.ruta,
            f"id: {modulo.datos['id']!r} debe ser {slug!r}, el nombre de la carpeta",
        )
        modulo = None

    modulo_en = None
    if modulo is not None and (traducida / ARCHIVO_MODULO).is_file():
        modulo_en = lectura.leer(traducida / ARCHIVO_MODULO, "modulo")
        if modulo_en is not None and not _revisar_par(
            lectura, modulo, modulo_en, ("duracion",)
        ):
            modulo_en = None

    lecciones: list[LeccionLeida] = []
    ordenes: Counter[int] = Counter()
    for archivo in sorted(carpeta.glob("*.md")):
        if archivo.name == ARCHIVO_MODULO:
            continue
        leccion = lectura.leer(archivo, "leccion")
        if leccion is None:
            continue
        esperado = f"{slug}/{archivo.stem}"
        if leccion.datos["id"] != esperado:
            lectura.error(
                leccion.ruta,
                f"id: {leccion.datos['id']!r} debe ser {esperado!r}, la ruta del archivo",
            )
            continue
        _revisar_leccion(lectura, leccion, slug)
        ordenes[leccion.datos["orden"]] += 1

        leccion_en = None
        if (traducida / archivo.name).is_file():
            leccion_en = lectura.leer(traducida / archivo.name, "leccion")
            if leccion_en is not None and not _revisar_par(
                lectura, leccion, leccion_en, DATOS_FIJOS
            ):
                leccion_en = None
        lecciones.append(
            LeccionLeida(
                slug=archivo.stem,
                orden=leccion.datos["orden"],
                titulo_es=leccion.datos["titulo"],
                titulo_en=leccion_en.datos["titulo"] if leccion_en else None,
                contenido_es=leccion.texto,
                contenido_en=leccion_en.texto if leccion_en else None,
                duracion=leccion.datos["duracion"],
                videos=_videos(leccion.datos),
                practicas=tuple(leccion.datos.get("practicas", ())),
                preguntas=_preguntas(
                    leccion.datos.get("quiz"),
                    leccion_en.datos.get("quiz") if leccion_en else None,
                ),
                quiz_final=bool(leccion.datos.get("quiz_final", False)),
            )
        )

    for orden, veces in sorted(ordenes.items()):
        if veces > 1:
            lectura.error(
                f"{IDIOMA_BASE}/{slug}",
                f"orden {orden}: lo tienen {veces} lecciones del módulo",
            )
    if not lecciones and not any(
        e.startswith(f"{IDIOMA_BASE}/{slug}/") for e in lectura.errores
    ):
        lectura.error(f"{IDIOMA_BASE}/{slug}", "el módulo no tiene lecciones")
    if modulo is None:
        return None
    return ModuloLeido(
        slug=slug,
        numero=int(slug[1:]),
        titulo_es=modulo.datos["titulo"],
        titulo_en=modulo_en.datos["titulo"] if modulo_en else None,
        resumen_es=modulo.datos["resumen"].strip(),
        resumen_en=modulo_en.datos["resumen"].strip() if modulo_en else None,
        duracion=modulo.datos["duracion"],
        lecciones=tuple(sorted(lecciones, key=lambda leccion: leccion.orden)),
    )


def _revisar_carpetas(lectura: _Lectura) -> list[Path]:
    """Las carpetas de módulos de es/, y que en/ no traiga nada sin par."""
    base = lectura.raiz / IDIOMA_BASE
    carpetas = []
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir()):
        if CARPETA_MODULO.match(carpeta.name):
            carpetas.append(carpeta)
        else:
            lectura.error(
                f"{IDIOMA_BASE}/{carpeta.name}",
                "una carpeta de módulo se llama mNN (m00 a m99)",
            )

    traducida = lectura.raiz / IDIOMA_TRADUCIDO
    if traducida.is_dir():
        for archivo in sorted(traducida.rglob("*.md")):
            par = base / archivo.relative_to(traducida)
            if not par.is_file():
                ruta = archivo.relative_to(lectura.raiz).as_posix()
                lectura.error(
                    ruta, f"no tiene par en {IDIOMA_BASE}/ (mismo nombre y carpeta)"
                )
    return carpetas


def _revisar_claves(lectura: _Lectura, modulos: list[ModuloLeido]) -> None:
    claves = Counter(
        pregunta.clave
        for modulo in modulos
        for leccion in modulo.lecciones
        for pregunta in leccion.preguntas or ()
    )
    for clave, veces in sorted(claves.items()):
        if veces > 1:
            lectura.error(
                IDIOMA_BASE,
                f"quiz {clave}: la clave está en {veces} preguntas; debe ser única en el curso",
            )


def leer_contenido(raiz: Path) -> CursoLeido:
    """Lee y valida todo content/. Si algo falla, ErrorContenido con todos los errores."""
    lectura = _Lectura(raiz=raiz)
    base = raiz / IDIOMA_BASE
    if not base.is_dir():
        raise ErrorContenido(
            [f"{raiz}: no encuentro la carpeta {IDIOMA_BASE}/ (¿es content/?)"]
        )

    curso = None
    if (base / ARCHIVO_CURSO).is_file():
        curso = lectura.leer(base / ARCHIVO_CURSO, "curso")
    else:
        lectura.error(IDIOMA_BASE, f"falta {ARCHIVO_CURSO} con los datos del curso")
    curso_en = None
    if curso is not None and (raiz / IDIOMA_TRADUCIDO / ARCHIVO_CURSO).is_file():
        curso_en = lectura.leer(raiz / IDIOMA_TRADUCIDO / ARCHIVO_CURSO, "curso")
        if curso_en is not None and not _revisar_par(lectura, curso, curso_en, ()):
            curso_en = None

    modulos = [
        m
        for c in _revisar_carpetas(lectura)
        if (m := _leer_modulo(lectura, c)) is not None
    ]
    if not modulos and not lectura.errores:
        lectura.error(IDIOMA_BASE, "no hay ningún módulo (carpetas mNN/)")
    _revisar_claves(lectura, modulos)
    if lectura.errores or curso is None:
        raise ErrorContenido(lectura.errores)
    return CursoLeido(
        slug=curso.datos["id"],
        titulo_es=curso.datos["titulo"],
        titulo_en=curso_en.datos["titulo"] if curso_en else None,
        descripcion_es=curso.datos["descripcion"].strip(),
        descripcion_en=curso_en.datos["descripcion"].strip() if curso_en else None,
        modulos=tuple(modulos),
    )


def revisar_plantillas(raiz: Path) -> list[str]:
    """Las plantillas de es/ (C-01) cumplen el esquema y las reglas, salvo id =
    ruta (no están en una carpeta mNN/). No se importan."""
    lectura = _Lectura(raiz=raiz)
    for nombre, esquema in PLANTILLAS.items():
        archivo = raiz / IDIOMA_BASE / nombre
        if not archivo.is_file():
            lectura.error(f"{IDIOMA_BASE}/{nombre}", "falta la plantilla")
            continue
        leido = lectura.leer(archivo, esquema)
        if leido is not None and esquema == "leccion":
            _revisar_leccion(lectura, leido, leido.datos["id"].split("/")[0])
    return lectura.errores
