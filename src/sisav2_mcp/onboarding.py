"""Onboarding interactivo: guarda la credencial UTEM en el keychain del SO.

Ejecutar en TU terminal (la clave se pide con entrada oculta; no apto para
entornos no interactivos):

    uv run python -m sisav2_mcp.onboarding            # guarda y verifica
    uv run python -m sisav2_mcp.onboarding --check    # solo verifica lo guardado
    uv run python -m sisav2_mcp.onboarding --clear    # borra la credencial

La clave se almacena cifrada en el gestor de credenciales del SO (en Windows,
Credential Manager) bajo el *service* configurado. Nunca se escribe en texto
plano, ni en el repo, ni se registra en logs. ROPC implica que el proceso ve la
clave solo al pedir el token a Keycloak.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from .auth import KeyringCredentialStore, store_credentials
from .auth.ropc import RopcTokenProvider
from .config import Settings


async def _verify(settings: Settings) -> int:
    """Confirma la credencial guardada: login ROPC + verifica-token (red)."""
    store = KeyringCredentialStore(settings.keyring_service)
    provider = RopcTokenProvider(settings, store)
    usuario = await provider.verifica_token()
    permisos = len(usuario.permisos_nomenclaturas)
    print(
        f"OK: autenticado como {usuario.nombre} (id={usuario.id}), "
        f"{permisos} permisos resueltos."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sisav2-mcp-onboarding",
        description="Guarda/verifica la credencial UTEM en el keychain del SO.",
    )
    parser.add_argument(
        "--check", action="store_true", help="solo verificar la credencial guardada"
    )
    parser.add_argument(
        "--clear", action="store_true", help="borrar la credencial del keychain"
    )
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    store = KeyringCredentialStore(settings.keyring_service)

    if args.clear:
        store.clear()
        print(
            f"Credencial eliminada del keychain (service '{settings.keyring_service}')."
        )
        return 0

    if not args.check:
        print(f"Onboarding SISAV2 — keychain service '{settings.keyring_service}'.")
        username = input("Usuario UTEM: ").strip()
        password = getpass.getpass("Clave UTEM (oculta): ")
        if not username or not password:
            print("Usuario/clave vacíos; operación abortada.", file=sys.stderr)
            return 2
        store_credentials(settings, username, password)
        print(f"Guardado en keychain para '{username}'. Verificando contra Keycloak...")

    try:
        return asyncio.run(_verify(settings))
    except Exception as exc:
        print(f"Verificación falló: {exc}", file=sys.stderr)
        print(
            "Revisa usuario/clave y la conectividad a sso.utem.cl / "
            "sisav2-api.utem.cl, y vuelve a ejecutar el onboarding para corregir.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
