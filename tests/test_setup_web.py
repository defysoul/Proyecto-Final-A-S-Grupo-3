"""Contratos mínimos de la interfaz web del instalador."""

from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).parents[1] / "src" / "sisav2_mcp" / "setup_gui" / "web"


def test_setup_page_prioritizes_codex_desktop() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    javascript = (WEB / "app.js").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")

    assert 'value="codex_desktop"' in html
    assert 'id="other-clients"' in html
    assert "Codex Desktop" in javascript
    assert "codex_desktop" in javascript
    assert ".card {" in css
    assert "flex: 1" not in css.split(".card {", 1)[1].split("}", 1)[0]
