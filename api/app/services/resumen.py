"""El avance de muchos usuarios a la vez (B-08): la lista de administración,
los aprobados pendientes de QOS y el CSV de la medición.

Mi progreso (`app/services/progreso.py`) arma el curso entero para una
persona; para una lista de 50 o un CSV de todos sería una consulta por cabeza.
Aquí se lee la estructura del curso una vez y lo de todos los usuarios en
cuatro consultas, con **la misma regla**: el primer curso publicado, los
módulos en orden, un módulo se abre al completar el anterior y una lección de
un módulo bloqueado no cuenta. `tests/test_admin_usuarios.py` compara el
resultado con Mi progreso.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Curso, Graduacion, Leccion, Modulo, Practica, ProgresoLeccion
from app.models.valores import PRACTICAS


@dataclass(frozen=True)
class Resumen:
    lecciones_total: int
    lecciones_completas: int
    modulos_completos: int
    # La última lección completa que cuenta, y la última práctica aprobada
    # (cuando la plataforma lo supo: `sincronizado_en`).
    ultima_leccion: datetime | None
    labs_aprobados: int
    ultima_practica: datetime | None
    graduacion: Graduacion | None

    @property
    def avance_pct(self) -> int:
        # La misma cuenta de Mi progreso (`_avance`).
        if not self.lecciones_total:
            return 0
        return round(100 * self.lecciones_completas / self.lecciones_total)

    @property
    def graduacion_estado(self) -> str | None:
        return self.graduacion.estado if self.graduacion else None

    @property
    def aprobado(self) -> bool:
        """Las tres condiciones de docs/diseno/modelo-datos.md, como `aprobado`
        de Mi progreso."""
        return (
            self.lecciones_total > 0
            and self.lecciones_completas == self.lecciones_total
            and self.labs_aprobados == len(PRACTICAS)
            and self.graduacion is not None
            and self.graduacion.estado == "aprobada"
        )

    @property
    def aprobado_en(self) -> datetime | None:
        """Cuándo se cumplió la última de las tres condiciones."""
        if not self.aprobado or self.graduacion is None:
            return None
        fechas = [
            self.graduacion.revisada_en,
            self.ultima_leccion,
            self.ultima_practica,
        ]
        return max(fecha for fecha in fechas if fecha is not None)


async def _modulos_del_curso(bd: AsyncSession) -> list[list[int]]:
    """Los ids de las lecciones publicadas de cada módulo, en orden. Los módulos
    sin lecciones publicadas no cuentan (igual que `armar_curso`)."""
    curso_id = await bd.scalar(
        select(Curso.id)
        .where(Curso.publicado.is_(True))
        .order_by(Curso.orden, Curso.id)
        .limit(1)
    )
    if curso_id is None:
        return []
    por_modulo: dict[int, list[int]] = defaultdict(list)
    for modulo_id, leccion_id in await bd.execute(
        select(Leccion.modulo_id, Leccion.id)
        .join(Modulo, Modulo.id == Leccion.modulo_id)
        .where(Modulo.curso_id == curso_id, Leccion.publicada.is_(True))
        .order_by(Modulo.numero, Leccion.orden)
    ):
        por_modulo[modulo_id].append(leccion_id)
    # dict conserva el orden de llegada: el de Modulo.numero.
    return list(por_modulo.values())


def _avance(
    modulos: list[list[int]], completadas: dict[int, datetime]
) -> tuple[int, int, datetime | None]:
    """(lecciones completas que cuentan, módulos completos, la última)."""
    completas = modulos_completos = 0
    ultima: datetime | None = None
    for lecciones in modulos:
        fechas = [completadas[i] for i in lecciones if i in completadas]
        completas += len(fechas)
        if fechas and (ultima is None or max(fechas) > ultima):
            ultima = max(fechas)
        if len(fechas) < len(lecciones):
            # Este queda en curso y los que siguen, bloqueados: no cuentan.
            break
        modulos_completos += 1
    return completas, modulos_completos, ultima


async def resumenes(bd: AsyncSession, usuario_ids: Sequence[int]) -> dict[int, Resumen]:
    """Usuario → su resumen. Pensado para listas del tamaño del curso (decenas o
    cientos); cada id es un parámetro de la consulta."""
    ids = list(dict.fromkeys(usuario_ids))
    if not ids:
        return {}
    modulos = await _modulos_del_curso(bd)
    todas = [i for lecciones in modulos for i in lecciones]

    completadas: dict[int, dict[int, datetime]] = defaultdict(dict)
    if todas:
        for usuario_id, leccion_id, fecha in await bd.execute(
            select(
                ProgresoLeccion.usuario_id,
                ProgresoLeccion.leccion_id,
                ProgresoLeccion.completada_en,
            ).where(
                ProgresoLeccion.usuario_id.in_(ids),
                ProgresoLeccion.leccion_id.in_(todas),
                ProgresoLeccion.completada_en.is_not(None),
            )
        ):
            completadas[usuario_id][leccion_id] = fecha

    practicas = {
        usuario_id: (cuantas, ultima)
        for usuario_id, cuantas, ultima in await bd.execute(
            select(
                Practica.usuario_id, func.count(), func.max(Practica.sincronizado_en)
            )
            .where(Practica.usuario_id.in_(ids), Practica.estado == "aprobado")
            .group_by(Practica.usuario_id)
        )
    }
    graduaciones = {
        g.usuario_id: g
        for g in await bd.scalars(
            select(Graduacion)
            .where(Graduacion.usuario_id.in_(ids))
            .execution_options(populate_existing=True)
        )
    }

    total = len(todas)
    resultado = {}
    for usuario_id in ids:
        completas, modulos_completos, ultima = _avance(modulos, completadas[usuario_id])
        labs, ultima_practica = practicas.get(usuario_id, (0, None))
        resultado[usuario_id] = Resumen(
            lecciones_total=total,
            lecciones_completas=completas,
            modulos_completos=modulos_completos,
            ultima_leccion=ultima,
            labs_aprobados=labs,
            ultima_practica=ultima_practica,
            graduacion=graduaciones.get(usuario_id),
        )
    return resultado
