"""Tests de la verificación de credenciales de la GUI de setup (respx).

Cubren la ``SetupApi.verificar``: credencial válida (guarda en keychain), inválida
(401), sin red (error de transporte) y entrada vacía.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from sisav2_mcp.config import Settings
from sisav2_mcp.setup_gui.app import SetupApi

SETTINGS = Settings()
TOKEN_ENDPOINT = SETTINGS.token_endpoint
VERIFICA_URL = f"{SETTINGS.api_base_url}/usuarios/verifica-token"

LOGIN_TOKENS = {
    "access_token": "AT1",
    "refresh_token": "RT1",
    "expires_in": 600,
    "refresh_expires_in": 1800,
    "token_type": "Bearer",
}
USUARIO_JSON = {
    "id": 409,
    "nombre": "WELINTON BARRERA",
    "perfil": {
        "id": 1,
        "nombre": "Analista",
        "roles": [
            {
                "id": 1,
                "nombre": "rol",
                "permisos": [
                    {"id": 1, "nombre": "Listar", "nomenclatura": "IPOLIST"},
                    {"id": 2, "nombre": "Ver", "nomenclatura": "IPOVER"},
                ],
            }
        ],
    },
}


def test_verificar_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, str] = {}
    monkeypatch.setattr(
        "sisav2_mcp.setup_gui.app.store_credentials",
        lambda s, u, p: saved.update(u=u, p=p),
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=LOGIN_TOKENS)
        )
        mock.get(VERIFICA_URL).mock(
            return_value=httpx.Response(200, json=USUARIO_JSON)
        )
        r = SetupApi().verificar("welinton", "secreta")
    assert r["ok"] is True
    assert r["nombre"] == "WELINTON BARRERA"
    assert r["permisos"] == 2
    assert saved == {"u": "welinton", "p": "secreta"}


def test_verificar_credencial_invalida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sisav2_mcp.setup_gui.app.store_credentials", lambda *a: None)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        r = SetupApi().verificar("welinton", "mala")
    assert r["ok"] is False
    assert "incorrect" in r["error"].lower()


def test_verificar_sin_red(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sisav2_mcp.setup_gui.app.store_credentials", lambda *a: None)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(side_effect=httpx.ConnectError("sin red"))
        r = SetupApi().verificar("welinton", "secreta")
    assert r["ok"] is False
    assert "utem" in r["error"].lower()


def test_verificar_vacio() -> None:
    r = SetupApi().verificar("", "")
    assert r["ok"] is False
    assert "usuario" in r["error"].lower()
