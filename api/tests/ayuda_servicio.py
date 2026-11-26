"""El token de servicio de las pruebas de las rutas internas (B-07 y B-08).

Los fixtures `settings_con_token` y `vm` están en conftest.py.
"""

TOKEN = "t" * 64


def con_token(token: str = TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
