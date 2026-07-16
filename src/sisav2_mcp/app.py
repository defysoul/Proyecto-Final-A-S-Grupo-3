"""Entry dual del paquete `sisav2-mcp`.

Un único ejecutable con dos modos, para que el mismo binario sirva como
**instalador** y como **servidor**:

- ``sisav2-mcp``            (doble-clic / sin argumentos) → abre la **GUI de
  configuración**: pide la credencial UTEM, la verifica de verdad contra
  Keycloak, la guarda en el keychain y registra el MCP en los clientes
  instalados (Claude Code / Claude Desktop / Codex).
- ``sisav2-mcp serve``     → arranca el **servidor MCP por stdio** (es lo que
  lanzan los clientes MCP). Equivale al entrypoint clásico ``server:main``.

Así el usuario descarga UN archivo, lo ejecuta para configurar, y los clientes
quedan apuntando a ``<ese archivo> serve``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_USAGE = (
    "Uso: sisav2-mcp [serve | index-demo]\n"
    "  (sin argumentos)  abre la GUI de configuración (credenciales + auto-registro)\n"
    "  serve             arranca el servidor MCP por stdio (lo usan los clientes MCP)\n"
    "  index-demo        crea el índice semántico desde una cohorte SISAV2 real\n"
)


def _load_cohort(path: str) -> list[dict[str, Any]]:
    """Carga el manifiesto local de IDs autorizado para la demo conectada."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"No se pudo leer la cohorte '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"La cohorte '{path}' no contiene JSON válido: {exc}") from exc

    members = payload.get("miembros") if isinstance(payload, dict) else payload
    if not isinstance(members, list) or not members:
        raise ValueError(
            "La cohorte debe ser una lista, o un objeto con la clave 'miembros', "
            "y contener al menos una iniciativa."
        )
    if not all(isinstance(member, dict) for member in members):
        raise ValueError("Cada miembro de la cohorte debe ser un objeto JSON.")
    return members


async def _build_demo_index(
    cohort: list[dict[str, Any]], *, cache_path: Path, ttl_seconds: int
) -> tuple[int, bool, str]:
    """Autentica, lee la cohorte por GET y escribe únicamente la caché local."""
    from .config import Settings
    from .tools.analysis import construir_indice_cohorte
    from .tools.context import SisavContext

    context = SisavContext(Settings.from_env())
    try:
        user = await context.usuario()  # preflight de credencial/red/RBAC
        index, cache_used = await construir_indice_cohorte(
            context.client,
            cohort,
            cache_path=cache_path,
            ttl_seconds=ttl_seconds,
        )
        return len(index.iniciativas), cache_used, str(user.id)
    finally:
        await context.aclose()


def _main_index_demo(argv: list[str]) -> int:
    """CLI de preflight: nunca emite solicitudes mutantes a SISAV2."""
    from .tools.semantic import default_semantic_cache_path

    parser = argparse.ArgumentParser(
        prog="sisav2-mcp index-demo",
        description=(
            "Construye el índice semántico desde una cohorte real autorizada. "
            "Solo realiza GET a SISAV2."
        ),
    )
    parser.add_argument(
        "--cohort",
        required=True,
        help="JSON local con miembros [{idPostulacion, modalidad?, facultad?, anio?}].",
    )
    parser.add_argument(
        "--cache",
        default=str(default_semantic_cache_path()),
        help="Ruta local de la caché de embeddings (por defecto, perfil del usuario).",
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=24 * 60 * 60,
        help=(
            "Tiempo máximo para reutilizar embeddings sin recalcular "
            "(default: 86400)."
        ),
    )
    args = parser.parse_args(argv)
    if args.ttl_seconds < 0:
        parser.error("--ttl-seconds debe ser mayor o igual a cero.")

    try:
        cohort = _load_cohort(args.cohort)
        documents, cache_used, user_id = asyncio.run(
            _build_demo_index(
                cohort,
                cache_path=Path(args.cache),
                ttl_seconds=args.ttl_seconds,
            )
        )
    except Exception as exc:
        print(f"Preflight semántico falló: {exc}", file=sys.stderr)
        return 1
    origin = "caché vigente" if cache_used else "embeddings generados"
    print(
        f"OK: índice semántico listo ({documents} iniciativas, {origin}, "
        f"usuario id={user_id})."
    )
    return 0


def _hide_console_window() -> None:
    """En Windows, oculta la consola del .exe en modo GUI (doble-clic).

    El binario se compila **con consola** porque el modo ``serve`` necesita
    stdin/stdout reales para hablar MCP; en modo GUI esa consola sobra y se oculta.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: despacha entre modo servidor (`serve`) y GUI de setup."""
    args = sys.argv[1:] if argv is None else list(argv)

    if args and args[0] in ("serve", "--serve"):
        # Modo servidor: NO imprimir nada a stdout (stdout = protocolo MCP).
        from .server import main as serve_main

        serve_main()
        return 0

    if args and args[0] == "index-demo":
        return _main_index_demo(args[1:])

    if args and args[0] in ("-h", "--help"):
        sys.stdout.write(_USAGE)
        return 0

    # Sin argumentos (caso típico: doble-clic) → GUI de configuración.
    _hide_console_window()
    from .setup_gui.app import run_setup

    run_setup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
