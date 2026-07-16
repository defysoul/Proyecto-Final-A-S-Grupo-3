# Build — ejecutable portable `sisav2-mcp.exe`

Genera un único `.exe` (Windows) que sirve a la vez de **instalador** (abre la GUI
de configuración), de **servidor MCP** (cuando se invoca con `serve`) y de
preflight de índice (`index-demo`). El artefacto habilita consultas conectadas y previews
*dry-run*; no habilita escritura real en SISAV2.

## Requisitos
- Windows · Python 3.11 · [uv](https://docs.astral.sh/uv/).
- **WebView2 Runtime** (viene preinstalado en Windows 11; en Windows 10 puede
  requerir instalarlo desde Microsoft).

## Construir
```bash
cd sisav2-mcp
uv pip install -e ".[dev,gui,build]"
uv run pyinstaller build/sisav2-mcp.spec --clean --noconfirm
```
Resultado: **`dist/sisav2-mcp.exe`** (un solo archivo, portable, ~43 MB).

> **El ejecutable es liviano a propósito: NO incluye el stack de ML**
> (torch/transformers/sentence-transformers). El `.spec` los excluye para que el
> binario pese decenas de MB (no >1 GB) y arranque en ~3–4 s, y así sea confiable
> en **Claude Desktop y Codex** sin exceder su timeout de arranque MCP.
> Consecuencia: el `.exe` expone **20 tools** (lectura + escritura dry-run);
> `server.py` detecta la ausencia del motor de embeddings y **no registra** las 3
> tools de análisis semántico ni habilita `index-demo`. Para esas se usa el
> **entorno de desarrollo (venv)**, que sí trae `sentence-transformers` → 23 tools.

> Reconstruye el binario para cada release. Un `.exe` generado antes de la versión 0.2.0 no contiene
> necesariamente las tools de escritura; no lo uses para la demo Fase 2.

## Probar el ejecutable
- **Doble-clic** → abre la GUI: credenciales UTEM → verifica → registra el MCP.
- `dist\sisav2-mcp.exe --help` → muestra la ayuda.
- Tras configurar, los clientes quedan apuntando a `"<ruta>\sisav2-mcp.exe" serve`.
- Handshake MCP sin GUI: `dist\sisav2-mcp.exe serve` habla JSON-RPC por stdio (es lo que lanzan los
  clientes). Debe listar **20 tools** (lectura + escritura dry-run).
- `index-demo` y las 3 tools de análisis semántico **no** están en el `.exe` (no trae el motor de
  embeddings): se ejecutan desde el venv → `python -m sisav2_mcp.app index-demo --cohort <RUTA>`.

El primer `index-demo` puede descargar/cargar el modelo semántico; por eso el preflight de la demo
requiere red. `sentence-transformers` está instalado en el venv (para tests y para el análisis
semántico), pero el `.spec` lo **excluye** del ejecutable: construir con `.[dev,gui,build]` es
suficiente; el ML no se empaqueta.

## Checklist de release

Desde el checkout, antes de compartir el `.exe`:

```bash
uv run ruff check .
uv run mypy src
uv run python -m pytest -q
```

Ensaya la GUI, registra un cliente y confirma una consulta conectada y una preview con
`aplicado: false` / `solicitud_mutante_enviada: false`. El rótulo **“90 tests verdes”** solo se puede
usar si la última ejecución de la suite para ese artefacto/corte muestra exactamente 90 pruebas
aprobadas; en otro caso, publica la cifra real.

## Notas
- El `.exe` va **sin firmar** → Windows SmartScreen mostrará un aviso; el usuario
  debe elegir **"Más información → Ejecutar de todos modos"**. (Firmar el binario
  elimina el aviso; pendiente.)
- **one-file**: el primer arranque se descomprime a un temporal (~3–4 s medidos con el build liviano).
  Es holgado para el timeout de Codex (~10 s) y de Claude Desktop. Si a futuro se empaquetara ML, pasar
  a *one-folder* para evitar la descompresión pesada en cada arranque.
- **Reemplazar un `.exe` en uso** (Windows lo bloquea si algún cliente lo tiene corriendo): renómbralo
  (`sisav2-mcp.exe` → `sisav2-mcp.old.exe`, permitido aunque esté en uso) y copia el nuevo con el nombre
  canónico. Los procesos vivos siguen con el viejo; los lanzamientos nuevos toman el nuevo. Borra el
  `.old.exe` cuando ya no lo use ningún proceso.
- Distribución: comparte `dist/sisav2-mcp.exe` (no subir a Git; ya está en `.gitignore` `dist/`).
- El `.exe` es la ruta cómoda de Windows, no la única: [`SETUP.md`](../SETUP.md) documenta el fallback
  con Python + `uv` + `.venv` para desarrollo y recuperación.
