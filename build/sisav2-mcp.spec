# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — `sisav2-mcp.exe` (one-file).

Empaqueta el entry dual (GUI de setup + servidor MCP) en un único ejecutable.
Recolecta `pywebview` y su backend de Windows (pythonnet/clr) y los assets web.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

proj = Path(SPECPATH).parent
web_dir = proj / "src" / "sisav2_mcp" / "setup_gui" / "web"

# Assets de la vista (HTML/CSS/JS/logo) → mismo path relativo que en el paquete.
datas = [(str(web_dir), "sisav2_mcp/setup_gui/web")]
binaries: list = []
# `webview` y `tomli_w` se importan de forma perezosa (dentro de funciones), así
# que PyInstaller no los ve por análisis estático: hay que declararlos.
hiddenimports = ["tomli_w"]

# Solo GUI (pywebview + backend Windows) y keychain. El stack de ML
# (torch/transformers/sentence-transformers) NO se empaqueta: el análisis
# semántico corre únicamente en el entorno de desarrollo. Excluirlo deja el .exe
# liviano y de arranque rápido, para que sea confiable en Claude Desktop y Codex
# sin exceder el timeout de arranque del servidor MCP.
for pkg in (
    "webview", "pythonnet", "clr_loader", "bottle", "proxy_tools",
    "keyring", "win32ctypes",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# `fastmcp` y `keyring` leen su versión / descubren backends vía
# importlib.metadata → hay que empacar los metadatos (dist-info) de ellos y sus
# dependencias, o el import falla dentro del .exe.
datas += copy_metadata("fastmcp", recursive=True)
datas += copy_metadata("keyring", recursive=True)

# El motor de embeddings y sus dependencias pesadas se excluyen a propósito para
# no arrastrar cientos de MB (torch) al ejecutable. `server.py` detecta su
# ausencia y no registra las tools semánticas cuando falta.
_ML_EXCLUDES = [
    "torch", "torchvision", "torchaudio",
    "transformers", "sentence_transformers",
    "tokenizers", "safetensors",
    "scipy", "sklearn", "sympy", "onnx", "onnxruntime",
]

a = Analysis(
    [str(proj / "build" / "entry.py")],
    pathex=[str(proj / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_ML_EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="sisav2-mcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # necesaria para el modo `serve` (MCP por stdio); la GUI la oculta
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
