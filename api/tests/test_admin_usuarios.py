"""Administración de usuarios (B-08): la lista, el detalle, el cambio de rol
(DoD 1), el reinicio de la clave (DoD 1), la auditoría (DoD 2) y el avance en
lote de `app/services/resumen.py`, comparado con Mi progreso.

El curso de prueba (tests/ayuda_contenido.py): m00/bienvenida; m01/vpn y
m01/ssh; m02/lectura.
"""

import logging
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import rol as consola
from app.core.errores import ErrorApi
from app.core.seguridad import (
    ALFABETO_CLAVE_TEMPORAL,
    LARGO_CLAVE_TEMPORAL,
    ahora,
    clave_temporal,
    verificar_clave,
)
from app.models import Auditoria, Sesion, Usuario
from app.models.valores import PRACTICAS
from app.services import progreso, usuarios
from app.services.contenido_carga import cargar_contenido
from app.services.contenido_lector import leer_contenido
from app.services.resumen import resumenes
from tests.ayuda_contenido import armar_contenido
from tests.ayuda_progreso import completar, graduacion, practica
from tests.ayuda_sesion import CLAVE, con_csrf, crear_usuario, ingresar

USUARIOS = "/api/admin/usuarios"


@pytest.fixture
async def contenido(tmp_path: Path, sesion_bd: AsyncSession) -> Path:
    raiz = armar_contenido(tmp_path / "content")
    await cargar_contenido(sesion_bd, leer_contenido(raiz))
    return raiz


@pytest.fixture
async def diego(cliente_bd: AsyncClient, sesion_bd: AsyncSession) -> Usuario:
    """El admin, con sesión en cliente_bd."""
    admin = await crear_usuario(sesion_bd, "diego", rol="admin")
    assert (await ingresar(cliente_bd, "diego")).status_code == 200
    return admin


async def fila(bd: AsyncSession, username: str) -> Usuario:
    return await bd.scalar(
        select(Usuario)
        .where(Usuario.username == username)
        .execution_options(populate_existing=True)
    )


async def auditoria(bd: AsyncSession, accion: str) -> list[Auditoria]:
    return list(
        await bd.scalars(
            select(Auditoria).where(Auditoria.accion == accion).order_by(Auditoria.id)
        )
    )


async def lista(cliente: AsyncClient, **params) -> dict:
    respuesta = await cliente.get(USUARIOS, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def nombres(datos: dict) -> list[str]:
    return [u["username"] for u in datos["items"]]


# --- Lista ---------------------------------------------------------------------------


async def test_la_lista_trae_el_estado_y_el_avance(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario, contenido
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    await completar(sesion_bd, ana, "bienvenida")
    await practica(sesion_bd, ana, "conexion")
    await practica(sesion_bd, ana, "memoria", estado="intentado")
    await graduacion(sesion_bd, ana, "enviada")

    datos = await lista(cliente_bd)

    assert (datos["total"], datos["pagina"], datos["por_pagina"]) == (2, 1, 50)
    assert nombres(datos) == ["ana", "diego"]
    item = datos["items"][0]
    assert {k: item[k] for k in item if k not in ("creado_en",)} == {
        "username": "ana",
        "nombre": "Prueba ana",
        "correo": None,
        "cluster": "apolo2",
        "rol": "estudiante",
        "idioma": "es",
        "debe_cambiar_clave": False,
        "activo": True,
        "estado": "activo",
        "bloqueado_hasta": None,
        "ultimo_ingreso": None,
        "baja_en": None,
        "avance_pct": 25,
        "labs_aprobados": 1,
        "graduacion_estado": "enviada",
    }
    assert item["creado_en"]
    assert datos["items"][1]["ultimo_ingreso"] is not None


async def test_estado_de_cada_cuenta(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "baja", activo=False, debe_cambiar_clave=True)
    bloqueado = await crear_usuario(sesion_bd, "bloq", debe_cambiar_clave=True)
    bloqueado.bloqueado_hasta = ahora() + timedelta(minutes=10)
    vencido = await crear_usuario(sesion_bd, "venc")
    vencido.bloqueado_hasta = ahora() - timedelta(minutes=1)
    await crear_usuario(sesion_bd, "nueva", debe_cambiar_clave=True)
    await sesion_bd.flush()

    datos = await lista(cliente_bd)
    estados = {u["username"]: u["estado"] for u in datos["items"]}

    # Gana el primero que se cumple: baja, bloqueado, debe_cambiar_clave, activo.
    assert estados == {
        "baja": "baja",
        "bloq": "bloqueado",
        "diego": "activo",
        "nueva": "debe_cambiar_clave",
        "venc": "activo",
    }
    for estado in ("baja", "bloqueado", "debe_cambiar_clave", "activo"):
        filtrada = await lista(cliente_bd, estado=estado)
        esperados = sorted(u for u, e in estados.items() if e == estado)
        assert (nombres(filtrada), filtrada["total"]) == (esperados, len(esperados))


async def test_buscar_y_filtrar(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    ana.correo = "ana.perez@example.com"
    bruno = await crear_usuario(sesion_bd, "bruno", rol="instructor")
    bruno.nombre = "Bruno Díaz"
    bruno.cluster = "apolo3"
    await crear_usuario(sesion_bd, "carla_100")
    await sesion_bd.flush()

    assert nombres(await lista(cliente_bd, q="PEREZ")) == ["ana"]
    assert nombres(await lista(cliente_bd, q="díaz")) == ["bruno"]
    assert nombres(await lista(cliente_bd, q="  bru  ")) == ["bruno"]
    assert nombres(await lista(cliente_bd, cluster="apolo3")) == ["bruno"]
    assert nombres(await lista(cliente_bd, rol="instructor")) == ["bruno"]
    assert nombres(await lista(cliente_bd, rol="admin", cluster="apolo2")) == ["diego"]
    # % y _ se buscan tal cual, no como comodines.
    assert nombres(await lista(cliente_bd, q="_1")) == ["carla_100"]
    assert nombres(await lista(cliente_bd, q="%")) == []
    assert (await lista(cliente_bd, q=""))["total"] == 4


async def test_paginas(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    for nombre in ("ana", "bruno", "carla", "elena"):
        await crear_usuario(sesion_bd, nombre)

    primera = await lista(cliente_bd, por_pagina=2)
    tercera = await lista(cliente_bd, por_pagina=2, pagina=3)
    vacia = await lista(cliente_bd, por_pagina=2, pagina=4)

    assert (nombres(primera), primera["total"]) == (["ana", "bruno"], 5)
    assert (nombres(tercera), tercera["pagina"]) == (["elena"], 3)
    assert (nombres(vacia), vacia["total"]) == ([], 5)


@pytest.mark.parametrize(
    "params",
    [
        {"por_pagina": 201},
        {"por_pagina": 0},
        {"pagina": 0},
        {"pagina": 100_001},
        {"q": "x" * 101},
        {"q": "a\x00"},
        {"estado": "suspendido"},
        {"rol": "root"},
        {"cluster": "cronos"},
    ],
)
async def test_filtros_invalidos_dan_422(
    cliente_bd: AsyncClient, diego: Usuario, params: dict
) -> None:
    respuesta = await cliente_bd.get(USUARIOS, params=params)

    assert respuesta.status_code == 422


# --- Detalle -----------------------------------------------------------------------------


async def test_el_detalle_trae_su_mi_progreso(
    crear_cliente, app_bd, cliente_bd: AsyncClient, sesion_bd, diego, contenido
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    await completar(sesion_bd, ana, "bienvenida")
    await practica(sesion_bd, ana, "conexion")
    cliente_ana = crear_cliente(app_bd)
    await ingresar(cliente_ana, "ana")
    lo_que_ve_ana = (await cliente_ana.get("/api/me/progreso")).json()

    respuesta = await cliente_bd.get(f"{USUARIOS}/ana")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert (datos["username"], datos["estado"], datos["avance_pct"]) == (
        "ana",
        "activo",
        25,
    )
    assert datos["progreso"] == lo_que_ve_ana


async def test_el_detalle_va_en_el_idioma_de_quien_mira(
    cliente_bd: AsyncClient, sesion_bd, diego, contenido
) -> None:
    await crear_usuario(sesion_bd, "ana")
    diego.idioma = "en"
    await sesion_bd.flush()

    datos = (await cliente_bd.get(f"{USUARIOS}/ana")).json()

    # El curso de prueba no tiene inglés: español con fallback.
    assert datos["progreso"]["fallback"] is True


async def test_el_detalle_de_alguien_que_no_existe_da_404(
    cliente_bd: AsyncClient, diego: Usuario
) -> None:
    respuesta = await cliente_bd.get(f"{USUARIOS}/nadie")

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"


# --- Avance en lote = Mi progreso ------------------------------------------------------------


async def test_el_avance_en_lote_es_el_de_mi_progreso(
    sesion_bd: AsyncSession, contenido
) -> None:
    casos = {
        "nada": [],
        "m00": ["bienvenida"],
        "media": ["bienvenida", "ssh"],
        # m00 sin terminar: m01 y m02 están bloqueados y sus lecciones no cuentan.
        "saltos": ["ssh", "lectura"],
        "m01": ["bienvenida", "vpn", "ssh"],
        "todo": ["bienvenida", "vpn", "ssh", "lectura"],
        "aprobado": ["bienvenida", "vpn", "ssh", "lectura"],
    }
    por_nombre = {}
    for nombre, lecciones in casos.items():
        usuario = await crear_usuario(sesion_bd, nombre)
        await completar(sesion_bd, usuario, *lecciones)
        por_nombre[nombre] = usuario
    for nombre in PRACTICAS:
        await practica(sesion_bd, por_nombre["aprobado"], nombre)
    await practica(sesion_bd, por_nombre["todo"], "conexion")
    await practica(sesion_bd, por_nombre["todo"], "memoria", estado="intentado")
    await graduacion(sesion_bd, por_nombre["aprobado"], "aprobada", revisada_en=ahora())
    await graduacion(sesion_bd, por_nombre["todo"], "rechazada")

    datos = await resumenes(sesion_bd, [u.id for u in por_nombre.values()])

    for nombre, usuario in por_nombre.items():
        mio = await progreso.mi_progreso(sesion_bd, usuario, "es")
        resumen = datos[usuario.id]
        assert (
            resumen.avance_pct,
            resumen.lecciones_completas,
            resumen.lecciones_total,
            resumen.modulos_completos,
            resumen.labs_aprobados,
            resumen.aprobado,
        ) == (
            mio.avance_pct,
            mio.lecciones_completas,
            mio.lecciones_total,
            sum(m.estado == "completo" for m in mio.modulos),
            sum(lab.estado == "aprobado" for lab in mio.labs),
            mio.aprobado,
        ), nombre
    assert datos[por_nombre["saltos"].id].avance_pct == 0
    assert datos[por_nombre["aprobado"].id].aprobado is True


async def test_sin_curso_publicado_el_avance_es_cero(sesion_bd: AsyncSession) -> None:
    ana = await crear_usuario(sesion_bd, "ana")

    resumen = (await resumenes(sesion_bd, [ana.id]))[ana.id]

    assert (resumen.avance_pct, resumen.lecciones_total, resumen.aprobado) == (
        0,
        0,
        False,
    )
    assert await resumenes(sesion_bd, []) == {}


# --- Cambio de rol ----------------------------------------------------------------------------


async def cambiar(cliente: AsyncClient, username: str, rol: str, csrf=True):
    cabeceras = con_csrf(cliente) if csrf else {}
    return await cliente.patch(
        f"{USUARIOS}/{username}", json={"rol": rol}, headers=cabeceras
    )


async def test_cambiar_el_rol(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await cambiar(cliente_bd, "ana", "instructor")

    assert respuesta.status_code == 200
    assert (respuesta.json()["rol"], respuesta.json()["estado"]) == (
        "instructor",
        "activo",
    )
    assert (await fila(sesion_bd, "ana")).rol == "instructor"
    (registro,) = await auditoria(sesion_bd, "cambio_rol")
    assert (registro.actor_id, registro.actor_servicio, registro.objetivo) == (
        diego.id,
        None,
        "ana",
    )
    assert registro.detalle == {"antes": "estudiante", "despues": "instructor"}


async def test_el_rol_nuevo_vale_en_la_siguiente_peticion(
    crear_cliente, app_bd, cliente_bd: AsyncClient, sesion_bd, diego
) -> None:
    await crear_usuario(sesion_bd, "carla", rol="instructor")
    cliente_carla = crear_cliente(app_bd)
    await ingresar(cliente_carla, "carla")
    assert (await cliente_carla.get("/api/panel/videos")).status_code == 200

    await cambiar(cliente_bd, "carla", "estudiante")

    # El rol se lee de la base en cada petición (B-03): sin cerrar la sesión.
    assert (await cliente_carla.get("/api/panel/videos")).status_code == 403


async def test_el_mismo_rol_no_cambia_nada(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await cambiar(cliente_bd, "ana", "estudiante")

    assert respuesta.status_code == 200
    assert await auditoria(sesion_bd, "cambio_rol") == []


async def test_no_se_quita_al_ultimo_admin(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    # Un admin dado de baja no cuenta.
    await crear_usuario(sesion_bd, "elena", rol="admin", activo=False)

    respuesta = await cambiar(cliente_bd, "diego", "instructor")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "ultimo_admin"
    assert (await fila(sesion_bd, "diego")).rol == "admin"
    assert await auditoria(sesion_bd, "cambio_rol") == []


async def test_con_otro_admin_activo_si_se_puede(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "gloria", rol="admin")

    assert (await cambiar(cliente_bd, "gloria", "instructor")).status_code == 200
    # Ahora diego es el único: ya no se puede quitar a sí mismo.
    assert (await cambiar(cliente_bd, "diego", "estudiante")).status_code == 409


async def test_a_un_admin_de_baja_se_le_puede_quitar_el_rol(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "elena", rol="admin", activo=False)

    respuesta = await cambiar(cliente_bd, "elena", "estudiante")

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "baja"


async def test_cambiar_el_rol_de_alguien_que_no_existe_da_404(
    cliente_bd: AsyncClient, diego: Usuario
) -> None:
    assert (await cambiar(cliente_bd, "nadie", "admin")).status_code == 404


@pytest.mark.parametrize("cuerpo", [{}, {"rol": "root"}, {"rol": None}])
async def test_un_cambio_de_rol_mal_armado_da_422(
    cliente_bd: AsyncClient, sesion_bd, diego, cuerpo: dict
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await cliente_bd.patch(
        f"{USUARIOS}/ana", json=cuerpo, headers=con_csrf(cliente_bd)
    )

    assert respuesta.status_code == 422


async def test_cambiar_el_rol_pide_el_token_csrf(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await cambiar(cliente_bd, "ana", "admin", csrf=False)

    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "csrf_invalido"
    assert (await fila(sesion_bd, "ana")).rol == "estudiante"


# --- El primer admin desde la consola (python -m app.rol) ---------------------------------------


async def test_la_consola_cambia_el_rol_con_la_misma_regla(
    sesion_bd: AsyncSession,
) -> None:
    await crear_usuario(sesion_bd, "hugo")

    resultado = await usuarios.cambiar_rol(
        sesion_bd, "hugo", "admin", actor_servicio=usuarios.SERVICIO_CONSOLA
    )

    assert resultado == ("estudiante", "admin")
    (registro,) = await auditoria(sesion_bd, "cambio_rol")
    assert (registro.actor_id, registro.actor_servicio) == (None, "consola")
    with pytest.raises(ErrorApi) as error:
        await usuarios.cambiar_rol(
            sesion_bd, "hugo", "estudiante", actor_servicio="consola"
        )
    assert error.value.codigo == "ultimo_admin"


def test_la_linea_de_comandos(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    llamadas = []

    async def falso(username: str, rol: str) -> tuple[str, str]:
        llamadas.append((username, rol))
        if username == "nadie":
            raise ErrorApi(404, "no_encontrado", "No existe ese usuario")
        return ("estudiante", rol)

    monkeypatch.setattr(consola, "_cambiar", falso)
    with caplog.at_level(logging.INFO):
        assert consola.main(["hugo", "admin"]) == 0
        assert consola.main(["nadie", "admin"]) == 1
        assert consola.main(["Hugo", "admin"]) == 2
    with pytest.raises(SystemExit):
        consola.main(["hugo", "root"])

    assert llamadas == [("hugo", "admin"), ("nadie", "admin")]
    assert "hugo: estudiante → admin." in caplog.text
    assert "No existe ese usuario" in caplog.text


# --- Reinicio de clave -------------------------------------------------------------------------


async def reiniciar(cliente: AsyncClient, username: str):
    return await cliente.post(
        f"{USUARIOS}/{username}/reiniciar-clave", headers=con_csrf(cliente)
    )


def test_la_clave_temporal_es_como_la_de_la_116() -> None:
    claves = {clave_temporal() for _ in range(200)}

    assert len(claves) == 200
    for clave in claves:
        assert len(clave) == LARGO_CLAVE_TEMPORAL == 14
        assert set(clave) <= set(ALFABETO_CLAVE_TEMPORAL)
        assert not set(clave) & set("0O1lI")
        assert any(c.islower() for c in clave)
        assert any(c.isupper() for c in clave)
        assert any(c.isdigit() for c in clave)


async def test_reiniciar_la_clave(
    crear_cliente, app_bd, cliente_bd: AsyncClient, sesion_bd, diego
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    cliente_ana = crear_cliente(app_bd)
    await ingresar(cliente_ana, "ana")
    ana.intentos_fallidos = 3
    ana.bloqueado_hasta = ahora() + timedelta(minutes=10)
    await sesion_bd.flush()

    respuesta = await reiniciar(cliente_bd, "ana")

    assert respuesta.status_code == 200
    assert respuesta.headers["cache-control"] == "no-store"
    datos = respuesta.json()
    assert datos["username"] == "ana"
    nueva = datos["clave_temporal"]
    assert len(nueva) == 14
    guardada = await fila(sesion_bd, "ana")
    assert await verificar_clave(guardada.clave_hash, nueva)
    assert not await verificar_clave(guardada.clave_hash, CLAVE)
    assert (
        guardada.debe_cambiar_clave,
        guardada.intentos_fallidos,
        guardada.bloqueado_hasta,
    ) == (True, 0, None)
    # Sus sesiones se cerraron.
    abiertas = await sesion_bd.scalar(
        select(func.count())
        .select_from(Sesion)
        .where(Sesion.usuario_id == ana.id, Sesion.revocada_en.is_(None))
    )
    assert abiertas == 0
    assert (await cliente_ana.get("/api/me")).status_code == 401
    # Y entra con la temporal, que debe cambiar.
    otra = crear_cliente(app_bd)
    entrada = await ingresar(otra, "ana", nueva)
    assert entrada.json()["usuario"]["debe_cambiar_clave"] is True


async def test_el_reinicio_queda_en_la_auditoria_sin_la_clave(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    await crear_usuario(sesion_bd, "ana")

    nueva = (await reiniciar(cliente_bd, "ana")).json()["clave_temporal"]

    (registro,) = await auditoria(sesion_bd, "reinicio_clave")
    assert (registro.actor_id, registro.objetivo, registro.detalle) == (
        diego.id,
        "ana",
        None,
    )
    todas = await sesion_bd.scalars(select(Auditoria.detalle))
    assert all(nueva not in str(detalle) for detalle in todas)


async def test_reiniciar_la_clave_de_una_baja_da_409(
    cliente_bd: AsyncClient, sesion_bd: AsyncSession, diego: Usuario
) -> None:
    antes = (await crear_usuario(sesion_bd, "elena", activo=False)).clave_hash

    respuesta = await reiniciar(cliente_bd, "elena")

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "usuario_inactivo"
    assert (await fila(sesion_bd, "elena")).clave_hash == antes
    assert await auditoria(sesion_bd, "reinicio_clave") == []


async def test_reiniciar_la_clave_de_alguien_que_no_existe_da_404(
    cliente_bd: AsyncClient, diego: Usuario
) -> None:
    assert (await reiniciar(cliente_bd, "nadie")).status_code == 404
