"""Tests del CLI de onboarding (keyring monkeypatcheado + respx).

No tocan el keychain real ni la red real.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import keyring
import pytest
import respx

from sisav2_mcp import onboarding
from sisav2_mcp.config import Settings

SETTINGS = Settings()
TOKEN_ENDPOINT = SETTINGS.token_endpoint
VERIFICA_URL = f"{SETTINGS.api_base_url}/usuarios/verifica-token"
SERVICE = SETTINGS.keyring_service
USERNAME_KEY = "__sisav2_username__"
SAMPLES_DIR = Path(__file__).resolve().parents[1] / "docs" / "discovery" / "samples"


def _mem_keyring(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[str, str], str]:
    mem: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        keyring, "set_password", lambda s, k, v: mem.__setitem__((s, k), v)
    )
    monkeypatch.setattr(keyring, "get_password", lambda s, k: mem.get((s, k)))
    monkeypatch.setattr(keyring, "delete_password", lambda s, k: mem.pop((s, k), None))
    return mem


def test_onboarding_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    mem = _mem_keyring(monkeypatch)
    mem[(SERVICE, USERNAME_KEY)] = "analista"
    mem[(SERVICE, "analista")] = "secreta"

    assert onboarding.main(["--clear"]) == 0
    assert mem == {}


def test_onboarding_store_and_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    mem = _mem_keyring(monkeypatch)
    monkeypatch.setattr(
        onboarding, "input", lambda _prompt="": "analista", raising=False
    )
    monkeypatch.setattr(onboarding.getpass, "getpass", lambda _prompt="": "secreta")

    usuario_json: Any = json.loads(
        (SAMPLES_DIR / "usuarios_verifica-token.json").read_text(encoding="utf-8")
    )
    tokens = {"access_token": "AT", "refresh_token": "RT", "expires_in": 600}

    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(return_value=httpx.Response(200, json=tokens))
        mock.get(VERIFICA_URL).mock(
            return_value=httpx.Response(200, json=usuario_json)
        )
        rc = onboarding.main([])

    assert rc == 0
    assert mem[(SERVICE, USERNAME_KEY)] == "analista"
    assert mem[(SERVICE, "analista")] == "secreta"


def test_onboarding_verify_failure_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    _mem_keyring(monkeypatch)
    monkeypatch.setattr(
        onboarding, "input", lambda _prompt="": "analista", raising=False
    )
    monkeypatch.setattr(onboarding.getpass, "getpass", lambda _prompt="": "mala")

    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "invalid_grant"})
        )
        rc = onboarding.main([])

    assert rc == 1
