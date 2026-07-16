"""Tests de auth con flujo OIDC mockeado (respx).

Cubren: login ROPC, expiración→refresh, refresh fallido→re-auth con keychain,
credencial ausente→onboarding, credencial inválida, verifica-token (RBAC), el
stub PKCE y el roundtrip del KeyringCredentialStore (keyring monkeypatcheado).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import keyring
import pytest
import respx

from sisav2_mcp.auth import (
    CredentialsNotFound,
    InvalidCredentials,
    KeyringCredentialStore,
    PkceTokenProvider,
    RopcTokenProvider,
)
from sisav2_mcp.config import Settings

SETTINGS = Settings()
TOKEN_ENDPOINT = SETTINGS.token_endpoint
VERIFICA_URL = f"{SETTINGS.api_base_url}/usuarios/verifica-token"
SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "discovery" / "samples"

LOGIN_TOKENS = {
    "access_token": "AT1",
    "refresh_token": "RT1",
    "expires_in": 600,
    "refresh_expires_in": 1800,
    "token_type": "Bearer",
}
REFRESH_TOKENS = {
    "access_token": "AT2",
    "refresh_token": "RT2",
    "expires_in": 600,
    "refresh_expires_in": 1800,
}


class FakeClock:
    """Reloj monótono controlable para tests de expiración."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class FakeStore:
    """CredentialStore en memoria (no toca el keychain real)."""

    def __init__(self, creds: tuple[str, str] | None) -> None:
        self._creds = creds

    def load(self) -> tuple[str, str] | None:
        return self._creds

    def save(self, username: str, password: str) -> None:
        self._creds = (username, password)

    def clear(self) -> None:
        self._creds = None


def _grant_router(request: httpx.Request) -> httpx.Response:
    """Responde según el grant_type del cuerpo (password vs refresh_token)."""
    body = request.content.decode()
    if "grant_type=refresh_token" in body:
        return httpx.Response(200, json=REFRESH_TOKENS)
    return httpx.Response(200, json=LOGIN_TOKENS)


def test_login_ropc() -> None:
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=LOGIN_TOKENS)
        )
        provider = RopcTokenProvider(
            SETTINGS, FakeStore(("user", "pass")), clock=FakeClock()
        )
        token = asyncio.run(provider.get_access_token())

    assert token == "AT1"
    body = route.calls.last.request.content.decode()
    assert "grant_type=password" in body
    assert "client_id=SISAV2" in body
    assert "username=user" in body


def test_expiration_triggers_refresh() -> None:
    clock = FakeClock()
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(side_effect=_grant_router)
        provider = RopcTokenProvider(SETTINGS, FakeStore(("u", "p")), clock=clock)
        assert asyncio.run(provider.get_access_token()) == "AT1"
        clock.advance(600)  # pasa el vencimiento (600 - margen 30)
        assert asyncio.run(provider.get_access_token()) == "AT2"


def test_refresh_failure_reauths_with_keychain() -> None:
    clock = FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        if "grant_type=refresh_token" in request.content.decode():
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(200, json=LOGIN_TOKENS)

    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(side_effect=handler)
        provider = RopcTokenProvider(SETTINGS, FakeStore(("u", "p")), clock=clock)
        assert asyncio.run(provider.get_access_token()) == "AT1"
        clock.advance(600)
        # refresh da 400 → re-login silencioso → AT1 de nuevo
        assert asyncio.run(provider.get_access_token()) == "AT1"


def test_missing_credentials_raises_onboarding() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=LOGIN_TOKENS)
        )
        provider = RopcTokenProvider(SETTINGS, FakeStore(None), clock=FakeClock())
        with pytest.raises(CredentialsNotFound):
            asyncio.run(provider.get_access_token())


def test_invalid_credentials_raises() -> None:
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        provider = RopcTokenProvider(
            SETTINGS, FakeStore(("u", "bad")), clock=FakeClock()
        )
        with pytest.raises(InvalidCredentials):
            asyncio.run(provider.get_access_token())


def test_verifica_token_resolves_rbac() -> None:
    usuario_json: Any = json.loads(
        (SAMPLES_DIR / "usuarios_verifica-token.json").read_text(encoding="utf-8")
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(200, json=LOGIN_TOKENS)
        )
        verifica = mock.get(VERIFICA_URL).mock(
            return_value=httpx.Response(200, json=usuario_json)
        )
        provider = RopcTokenProvider(SETTINGS, FakeStore(("u", "p")), clock=FakeClock())
        usuario = asyncio.run(provider.verifica_token())

    assert usuario.id == 401
    assert "IPOLIST" in usuario.permisos_nomenclaturas
    assert verifica.calls.last.request.headers["Authorization"] == "Bearer AT1"


def test_pkce_stub_not_implemented() -> None:
    provider = PkceTokenProvider()
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.get_access_token())


def test_keyring_store_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    mem: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        keyring, "set_password", lambda s, k, v: mem.__setitem__((s, k), v)
    )
    monkeypatch.setattr(keyring, "get_password", lambda s, k: mem.get((s, k)))
    monkeypatch.setattr(keyring, "delete_password", lambda s, k: mem.pop((s, k), None))

    store = KeyringCredentialStore("sisav2-mcp-test")
    assert store.load() is None
    store.save("analista", "secreta")
    assert store.load() == ("analista", "secreta")
    store.clear()
    assert store.load() is None
