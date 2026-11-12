"""primera(): la primera corrutina que termina gana y las demás se cancelan."""

import anyio
import anyio.lowlevel
import pytest

from app.sesion import primera


async def _espera_para_siempre(nombre: str, canceladas: list[str]) -> str:
    try:
        await anyio.sleep_forever()
    except anyio.get_cancelled_exc_class():
        canceladas.append(nombre)
        raise
    return nombre


async def _rapida(valor: str) -> str:
    await anyio.lowlevel.checkpoint()
    return valor


async def _falla() -> str:
    await anyio.lowlevel.checkpoint()
    raise ValueError("ssh")


async def test_devuelve_la_primera_y_cancela_las_demas():
    canceladas: list[str] = []
    resultado = await primera(_espera_para_siempre("vigia", canceladas), _rapida("ssh"))
    assert resultado == "ssh"
    assert canceladas == ["vigia"]


async def test_relanza_el_error_de_la_primera():
    canceladas: list[str] = []
    with pytest.raises(ValueError, match="ssh"):
        await primera(_espera_para_siempre("vigia", canceladas), _falla())
    assert canceladas == ["vigia"]


async def test_si_cancelan_a_quien_llama_cancela_a_todas():
    # Lo que hace Starlette al cerrar el WebSocket: cancelar el endpoint. La
    # cancelación debe quedarse en el ámbito que la pidió, sin escaparse.
    canceladas: list[str] = []
    with anyio.move_on_after(0.05) as ambito:
        await primera(
            _espera_para_siempre("ssh", canceladas),
            _espera_para_siempre("vigia", canceladas),
        )
    assert ambito.cancelled_caught
    assert sorted(canceladas) == ["ssh", "vigia"]
