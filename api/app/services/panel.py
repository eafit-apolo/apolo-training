"""Cifras del panel de instructor (F-08): `GET /api/panel/resumen`.

Cuentan solo los **estudiantes activos** (instructores, admins y bajas no
entran, igual que en la medición), con la regla de Mi progreso que ya aplica
`app/services/resumen.py`:

- **Sin empezar:** ninguna lección completa (que cuente) ni práctica aprobada.
- **Aprobados:** las tres condiciones de `aprobado` (todas las lecciones, las
  siete prácticas y la graduación aprobada).
- **En curso:** el resto.
- **Por módulo** («dónde se atascan»): cuántos completaron cada módulo. Como un
  módulo se abre al completar el anterior y una lección de un módulo bloqueado
  no cuenta, la cifra nunca sube de un módulo al siguiente.
- **Graduaciones por revisar:** las `enviada`, las mismas que lista
  `GET /panel/graduaciones?estado=enviada`.
- **Aprobados pendientes de QOS:** los de `GET /admin/aprobados-pendientes`.

Los títulos de los módulos van en el idioma del perfil (español si falta la
traducción), como `GET /panel/videos`.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Graduacion, Sincronizacion, Usuario
from app.schemas.contenido import Idioma
from app.schemas.panel import AvanceModulo, ResumenPanel
from app.services import aprobados
from app.services.contenido import Textos
from app.services.resumen import modulos_del_curso, resumenes


async def resumen(bd: AsyncSession, idioma: Idioma) -> ResumenPanel:
    activos = list(
        await bd.scalars(
            select(Usuario.id).where(
                Usuario.rol == "estudiante", Usuario.activo.is_(True)
            )
        )
    )
    datos = list((await resumenes(bd, activos)).values())
    sin_empezar = sum(
        1 for r in datos if r.lecciones_completas == 0 and r.labs_aprobados == 0
    )
    aprobados_total = sum(1 for r in datos if r.aprobado)
    por_revisar = await bd.scalar(
        select(func.count())
        .select_from(Graduacion)
        .where(Graduacion.estado == "enviada")
    )
    pendientes = await aprobados.pendientes(bd)
    ultima = await bd.scalar(select(func.max(Sincronizacion.recibida_en)))
    t = Textos(idioma)
    por_modulo = [
        AvanceModulo(
            numero=modulo.numero,
            titulo=t(modulo.titulo_es, modulo.titulo_en),
            completos=sum(1 for r in datos if r.modulos_completos > i),
        )
        for i, (modulo, _) in enumerate(await modulos_del_curso(bd))
    ]
    return ResumenPanel(
        estudiantes_activos=len(datos),
        sin_empezar=sin_empezar,
        en_curso=len(datos) - sin_empezar - aprobados_total,
        aprobados=aprobados_total,
        graduaciones_por_revisar=por_revisar or 0,
        aprobados_pendientes_qos=len(pendientes),
        ultima_sincronizacion=ultima,
        avance_por_modulo=por_modulo,
    )
