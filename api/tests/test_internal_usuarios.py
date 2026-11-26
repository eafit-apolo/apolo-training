"""Altas y bajas desde la VM de práctica (B-08, DoD 1): POST y PATCH
/api/internal/usuarios.

Las llama `apolo-training-admin` (V-04) con el token de servicio. Los cuerpos
son los que arma admin/apolo_training_admin.py: el cliente espera 201 en la
alta (cualquier otra cosa revierte la alta en la VM) y tolera el 404 en la
baja.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import verificar_clave
from app.models import Auditoria, Sesion, Usuario
from tests.ayuda_servicio import TOKEN, con_token
from tests.ayuda_sesion import con_csrf, cookies_puestas, crear_usuario, ingresar

ALTA = "/api/internal/usuarios"
CLAVE = "Kx7pQm2vRt9wNa"  # como las de clave_temporal() de la 116: 14 caracteres


def cuerpo_alta(**cambios) -> dict:
    """Lo que manda `apolo-training-admin alta` (sin --idioma)."""
    return {
        "username": "ana",
        "nombre": "Ana Pérez",
        "correo": "ana@example.com",
        "cluster": "apolo3",
        "clave_temporal": CLAVE,
        **cambios,
    }


async def alta(cliente: AsyncClient, cuerpo: dict, token: str = TOKEN):
    return await cliente.post(ALTA, json=cuerpo, headers=con_token(token))


async def estado(cliente: AsyncClient, username: str, activo: bool, token=TOKEN):
    return await cliente.patch(
        f"{ALTA}/{username}", json={"activo": activo}, headers=con_token(token)
    )


async def usuario(bd: AsyncSession, username: str = "ana") -> Usuario | None:
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


async def sesiones_abiertas(bd: AsyncSession, usuario_id: int) -> int:
    return await bd.scalar(
        select(func.count())
        .select_from(Sesion)
        .where(Sesion.usuario_id == usuario_id, Sesion.revocada_en.is_(None))
    )


# --- Alta --------------------------------------------------------------------------


async def test_alta_crea_al_estudiante_con_la_clave_de_la_vm(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    respuesta = await alta(vm, cuerpo_alta())

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "username": "ana",
        "nombre": "Ana Pérez",
        "correo": "ana@example.com",
        "cluster": "apolo3",
        "rol": "estudiante",
        "idioma": "es",
        "debe_cambiar_clave": True,
        "activo": True,
    }
    fila = await usuario(sesion_bd)
    assert fila.clave_hash != CLAVE
    assert fila.clave_hash.startswith("$argon2id$")
    assert await verificar_clave(fila.clave_hash, CLAVE)
    assert (fila.baja_en, fila.intentos_fallidos) == (None, 0)


async def test_con_la_clave_de_la_alta_entra_y_debe_cambiarla(
    vm: AsyncClient, cliente_bd: AsyncClient
) -> None:
    await alta(vm, cuerpo_alta())

    respuesta = await ingresar(cliente_bd, "ana", CLAVE)

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["debe_cambiar_clave"] is True
    otra = await cliente_bd.get("/api/me/progreso")
    assert otra.json()["codigo"] == "debe_cambiar_clave"


async def test_alta_con_idioma(vm: AsyncClient, sesion_bd: AsyncSession) -> None:
    respuesta = await alta(vm, cuerpo_alta(idioma="en"))

    assert respuesta.status_code == 201
    assert (await usuario(sesion_bd)).idioma == "en"


async def test_alta_queda_en_la_auditoria_sin_la_clave(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await alta(vm, cuerpo_alta())

    (fila,) = await auditoria(sesion_bd, "alta")
    assert (fila.actor_id, fila.actor_servicio, fila.objetivo) == (
        None,
        "vm-practica",
        "ana",
    )
    assert fila.detalle == {"cluster": "apolo3", "idioma": "es"}
    assert CLAVE not in str(fila.detalle)


@pytest.mark.parametrize("activo", [True, False])
async def test_alta_de_un_usuario_que_ya_existe_da_409(
    vm: AsyncClient, sesion_bd: AsyncSession, activo: bool
) -> None:
    # También si está de baja: se reactiva con PATCH, no con otra alta.
    existente = await crear_usuario(sesion_bd, "ana", activo=activo)
    hash_antes = existente.clave_hash

    respuesta = await alta(vm, cuerpo_alta())

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "usuario_existe"
    fila = await usuario(sesion_bd)
    assert (fila.clave_hash, fila.cluster, fila.activo) == (
        hash_antes,
        "apolo2",
        activo,
    )
    assert await auditoria(sesion_bd, "alta") == []


@pytest.mark.parametrize(
    "cambios",
    [
        {"username": "Ana"},
        {"username": "1ana"},
        {"username": "a" * 33},
        {"nombre": "   "},
        {"nombre": "n" * 121},
        {"nombre": "Ana\x00"},
        {"correo": "sin-arroba"},
        {"correo": "ana@eafit"},
        {"correo": "ana pérez@example.com"},
        {"cluster": "cronos"},
        {"idioma": "pt"},
        {"clave_temporal": "corta12"},
        {"clave_temporal": "x" * 129},
        # La 116 solo crea estudiantes: un rol en la alta no se acepta.
        {"rol": "admin"},
        {"rol": "estudiante"},
    ],
)
async def test_alta_mal_armada_da_422(
    vm: AsyncClient, sesion_bd: AsyncSession, cambios: dict
) -> None:
    respuesta = await alta(vm, cuerpo_alta(**cambios))

    assert respuesta.status_code == 422
    assert await usuario(sesion_bd, cambios.get("username", "ana")) is None


@pytest.mark.parametrize(
    "falta", ["username", "nombre", "correo", "cluster", "clave_temporal"]
)
async def test_alta_sin_un_campo_obligatorio_da_422(
    vm: AsyncClient, falta: str
) -> None:
    cuerpo = cuerpo_alta()
    del cuerpo[falta]

    respuesta = await alta(vm, cuerpo)

    assert respuesta.status_code == 422
    assert [e["campo"] for e in respuesta.json()["errores"]] == [falta]


async def test_el_nombre_se_guarda_sin_espacios_alrededor(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await alta(vm, cuerpo_alta(nombre="  Ana Pérez  "))

    assert (await usuario(sesion_bd)).nombre == "Ana Pérez"


# --- Token ------------------------------------------------------------------------


@pytest.mark.parametrize("token", ["x" * 64, TOKEN[:-1]])
async def test_sin_el_token_correcto_no_hay_alta_ni_baja(
    vm: AsyncClient, sesion_bd: AsyncSession, token: str
) -> None:
    await crear_usuario(sesion_bd, "bruno")

    respuestas = [
        await alta(vm, cuerpo_alta(), token=token),
        await estado(vm, "bruno", False, token=token),
        await vm.post(ALTA, json=cuerpo_alta()),
    ]

    assert [r.status_code for r in respuestas] == [401, 401, 401]
    assert {r.json()["codigo"] for r in respuestas} == {"token_servicio_invalido"}
    assert await usuario(sesion_bd) is None
    assert (await usuario(sesion_bd, "bruno")).activo is True


async def test_una_sesion_de_admin_no_sirve_para_las_altas(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "diego", rol="admin")
    assert (await ingresar(vm, "diego")).status_code == 200

    respuesta = await vm.post(ALTA, json=cuerpo_alta(), headers=con_csrf(vm))

    assert respuesta.status_code == 401
    assert await usuario(sesion_bd) is None


# --- Baja y reactivación ---------------------------------------------------------------


async def test_baja_impide_entrar_y_cierra_sus_sesiones(
    vm: AsyncClient, crear_cliente, app_bd, cliente_bd: AsyncClient, sesion_bd
) -> None:
    ana = await crear_usuario(sesion_bd, "ana")
    otro_navegador = crear_cliente(app_bd)
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    assert (await ingresar(otro_navegador, "ana")).status_code == 200
    assert await sesiones_abiertas(sesion_bd, ana.id) == 2

    respuesta = await estado(vm, "ana", False)

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
    fila = await usuario(sesion_bd)
    assert fila.activo is False
    assert fila.baja_en is not None
    assert await sesiones_abiertas(sesion_bd, ana.id) == 0
    # La sesión que tenía abierta ya no sirve, ni para renovarla: dentro de
    # los 30 s de gracia de la B-03 el refresh responde 204 sin cookies (como
    # si otra pestaña hubiera renovado) y después 401; nunca una sesión nueva.
    assert (await cliente_bd.get("/api/me")).status_code == 401
    renovar = await otro_navegador.post(
        "/api/auth/refresh", headers=con_csrf(otro_navegador)
    )
    assert renovar.status_code in (204, 401)
    assert cookies_puestas(renovar) == {}
    assert (await otro_navegador.get("/api/me")).status_code == 401
    # Y no puede volver a entrar.
    nueva = await ingresar(crear_cliente(app_bd), "ana")
    assert nueva.json()["codigo"] == "cuenta_inactiva"


async def test_baja_queda_en_la_auditoria(vm: AsyncClient, sesion_bd) -> None:
    await crear_usuario(sesion_bd, "ana")

    await estado(vm, "ana", False)

    (fila,) = await auditoria(sesion_bd, "baja")
    assert (fila.actor_id, fila.actor_servicio, fila.objetivo) == (
        None,
        "vm-practica",
        "ana",
    )


async def test_repetir_la_baja_no_cambia_nada(vm: AsyncClient, sesion_bd) -> None:
    # apolo-training-admin dice «repetir la baja para completar» si la API falló.
    await crear_usuario(sesion_bd, "ana")
    await estado(vm, "ana", False)
    primera = (await usuario(sesion_bd)).baja_en

    respuesta = await estado(vm, "ana", False)

    assert respuesta.status_code == 200
    assert (await usuario(sesion_bd)).baja_en == primera
    assert len(await auditoria(sesion_bd, "baja")) == 1


async def test_baja_de_un_usuario_que_no_existe_da_404(vm: AsyncClient) -> None:
    respuesta = await estado(vm, "nadie", False)

    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "no_encontrado"


async def test_reactivar(
    vm: AsyncClient, cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "ana", activo=False)

    respuesta = await estado(vm, "ana", True)

    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is True
    fila = await usuario(sesion_bd)
    assert (fila.activo, fila.baja_en) == (True, None)
    assert (await ingresar(cliente_bd, "ana")).status_code == 200
    (registro,) = await auditoria(sesion_bd, "reactivacion")
    assert registro.actor_servicio == "vm-practica"


async def test_reactivar_a_alguien_activo_no_cambia_nada(
    vm: AsyncClient, sesion_bd: AsyncSession
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await estado(vm, "ana", True)

    assert respuesta.status_code == 200
    assert await auditoria(sesion_bd, "reactivacion") == []


@pytest.mark.parametrize("cuerpo", [{}, {"activo": "quizas"}, {"activo": None}])
async def test_cambio_de_estado_mal_armado_da_422(
    vm: AsyncClient, sesion_bd: AsyncSession, cuerpo: dict
) -> None:
    await crear_usuario(sesion_bd, "ana")

    respuesta = await vm.patch(f"{ALTA}/ana", json=cuerpo, headers=con_token())

    assert respuesta.status_code == 422
    assert (await usuario(sesion_bd)).activo is True


async def test_alta_y_baja_de_punta_a_punta(
    vm: AsyncClient, cliente_bd: AsyncClient, sesion_bd: AsyncSession
) -> None:
    """Lo que hace apolo-training-admin: alta, primer ingreso y baja."""
    assert (await alta(vm, cuerpo_alta(idioma="en"))).status_code == 201
    assert (await ingresar(cliente_bd, "ana", CLAVE)).status_code == 200
    cambio = await cliente_bd.post(
        "/api/auth/cambiar-clave",
        json={"clave_actual": CLAVE, "clave_nueva": "otra-clave-larga"},
        headers=con_csrf(cliente_bd),
    )
    assert cambio.status_code == 204
    assert (await cliente_bd.get("/api/me/progreso")).status_code == 200

    assert (await estado(vm, "ana", False)).status_code == 200

    assert (await cliente_bd.get("/api/me")).status_code == 401
    acciones = [
        f.accion
        for f in await sesion_bd.scalars(
            select(Auditoria).where(Auditoria.objetivo == "ana").order_by(Auditoria.id)
        )
    ]
    assert acciones == ["alta", "login_ok", "cambio_clave", "baja"]
