# Codex Desktop First Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make the Windows SISAV2 MCP installer detect and prioritize Codex Desktop while preserving the existing shared Codex MCP registration.

**Architecture:** Detection remains read-only in setup_gui.clients and returns separate codex_desktop and codex_cli flags. Both Codex options use the existing TOML writer, but wrappers supply an accurate user-facing client label. The web view renders Codex Desktop as the auto-selected primary destination and moves the other integrations into an opt-in disclosure.

**Tech Stack:** Python 3.11, pytest, tomli-w, PyWebView, HTML, CSS, vanilla JavaScript, PyInstaller.

## Global Constraints

- Target Windows only; do not add macOS or Linux detection.
- Identify Codex Desktop from the installed OpenAI.Codex package or %LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe.
- A generic codex found in PATH is Codex CLI, not Desktop.
- Do not use ~/.codex as installation evidence; still write [mcp_servers.sisav2] there.
- Preserve existing parsed TOML tables; comment preservation is out of scope.
- Keep Claude Code and Claude Desktop available but not selected by default.
- Do not change SISAV2 authentication, MCP protocol, or server tools.
- Do not stage or alter unrelated worktree changes.

---

## File structure

- Modify src/sisav2_mcp/setup_gui/clients.py: Windows-aware detection and accurate Codex result labels.
- Modify tests/test_setup_clients.py: isolated tests for detection precedence and Codex Desktop registration.
- Create tests/test_setup_web.py: static contract tests for primary Codex Desktop copy, opt-in secondary clients, and compact layout selectors.
- Modify src/sisav2_mcp/setup_gui/app.py: resizable window with content-appropriate initial height.
- Modify src/sisav2_mcp/setup_gui/web/index.html: primary destination card and secondary-client disclosure.
- Modify src/sisav2_mcp/setup_gui/web/app.js: render selection state from the new detection keys and summarize correct labels.
- Modify src/sisav2_mcp/setup_gui/web/style.css: content-sized card and compact responsive arrangement.
- Build dist/sisav2-mcp.exe and update the stable executable only after all automated verification passes.

### Task 1: Separate Codex Desktop detection from CLI and preserve registration

**Files:**

- Modify: src/sisav2_mcp/setup_gui/clients.py
- Modify: tests/test_setup_clients.py

**Interfaces:**

- Produces: codex_desktop_executable_path() -> Path, _appx_package_installed(package_name: str) -> bool, and is_codex_desktop_installed() -> bool.
- Produces: detect() -> dict[str, bool] with exactly claude_code, claude_desktop, codex_desktop, and codex_cli.
- Produces: configure_codex_desktop(command: str, args: list[str]) -> dict[str, str] and configure_codex_cli(command: str, args: list[str]) -> dict[str, str].
- Consumes: configure_codex(command: str, args: list[str], *, client_label: str = "Codex") -> dict[str, str] to write the shared TOML entry.

- [ ] **Step 1: Write the failing tests**

Add these isolated cases to tests/test_setup_clients.py:

    def test_detect_marks_appx_codex_as_desktop(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(clients, "_appx_package_installed", lambda _: True)
        monkeypatch.setattr(
            clients, "codex_desktop_executable_path", lambda: Path("C:/missing.exe")
        )
        monkeypatch.setattr(clients.shutil, "which", lambda _: None)

        detected = clients.detect()

        assert detected["codex_desktop"] is True
        assert detected["codex_cli"] is False


    def test_detect_does_not_infer_desktop_from_config(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(clients, "_appx_package_installed", lambda _: False)
        monkeypatch.setattr(
            clients, "codex_desktop_executable_path", lambda: tmp_path / "missing.exe"
        )
        monkeypatch.setattr(clients.shutil, "which", lambda _: None)
        monkeypatch.setattr(
            clients, "codex_config_path", lambda: tmp_path / ".codex" / "config.toml"
        )
        (tmp_path / ".codex").mkdir()

        detected = clients.detect()

        assert detected["codex_desktop"] is False
        assert detected["codex_cli"] is False


    def test_detect_classifies_generic_codex_as_cli(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(clients, "_appx_package_installed", lambda _: False)
        monkeypatch.setattr(
            clients, "codex_desktop_executable_path", lambda: Path("C:/missing.exe")
        )
        monkeypatch.setattr(clients.shutil, "which", lambda _: "C:/tools/codex.exe")

        detected = clients.detect()

        assert detected["codex_desktop"] is False
        assert detected["codex_cli"] is True

Extend the TOML merge test with configure_codex_desktop(EXE, ["serve"]) and assert the result client is Codex Desktop plus the existing parsed-TOML assertions.

- [ ] **Step 2: Run the test to verify it fails**

Run:

    .venv\Scripts\python.exe -m pytest tests/test_setup_clients.py -q

Expected: fail because the helpers, detection keys, and Codex Desktop wrapper do not yet exist.

- [ ] **Step 3: Implement the minimal read-only detector and labeled wrappers**

Add CODEX_DESKTOP_PACKAGE = "OpenAI.Codex". Implement codex_desktop_executable_path() using LOCALAPPDATA with the documented user-install path. Implement _appx_package_installed() by calling PowerShell with -NoProfile, -NonInteractive, and a fixed Get-AppxPackage command; return false on an OS or subprocess error. Implement is_codex_desktop_installed() as the package check OR the known-path is_file() check.

Change detect() to call is_codex_desktop_installed() once. Set codex_desktop from that result and codex_cli only when shutil.which("codex") is present while Desktop is false. Keep the existing Claude signals unchanged.

Change configure_codex() to take keyword-only client_label. Add configure_codex_desktop() and configure_codex_cli() wrappers that pass Codex Desktop and Codex CLI, respectively. Point _CONFIGURERS at these wrappers.

- [ ] **Step 4: Run focused tests and lint**

Run:

    .venv\Scripts\python.exe -m pytest tests/test_setup_clients.py -q
    .venv\Scripts\python.exe -m ruff check src/sisav2_mcp/setup_gui/clients.py tests/test_setup_clients.py

Expected: both commands pass and a stale .codex directory cannot produce a Desktop detection.

- [ ] **Step 5: Commit the isolated Python behavior**

Run:

    git add src/sisav2_mcp/setup_gui/clients.py tests/test_setup_clients.py
    git commit -m "feat: detect Codex Desktop separately"

### Task 2: Make Codex Desktop the deliberate primary destination

**Files:**

- Create: tests/test_setup_web.py
- Modify: src/sisav2_mcp/setup_gui/app.py
- Modify: src/sisav2_mcp/setup_gui/web/index.html
- Modify: src/sisav2_mcp/setup_gui/web/app.js
- Modify: src/sisav2_mcp/setup_gui/web/style.css

**Interfaces:**

- Consumes: SetupApi.detectar() result with codex_desktop and codex_cli keys.
- Produces: a primary checkbox value="codex_desktop" and a collapsed secondary container id="other-clients".
- Produces: renderClients() that auto-checks only codex_desktop when detected.

- [ ] **Step 1: Write the failing static web contract test**

Create tests/test_setup_web.py:

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

- [ ] **Step 2: Run the test to verify it fails**

Run:

    .venv\Scripts\python.exe -m pytest tests/test_setup_web.py -q

Expected: fail because the current markup has one generic client list, JavaScript labels only codex, and the card uses flex: 1.

- [ ] **Step 3: Restructure markup, rendering, and layout**

Replace the generic client block in index.html with a primary Codex section containing a checkbox id="codex-desktop", value="codex_desktop", and data-client. Add a closed details id="other-clients" with the existing clients-list inside.

In app.js, retain labels only for claude_code, claude_desktop, and codex_cli. In renderClients(), set the primary checkbox checked only from det.codex_desktop and disable it when absent. Render the other labels into clients-list but start them unchecked regardless of detection. Update seleccionados() to collect input[data-client]:checked from both areas. Keep existing credential validation and status rendering.

Use this exact selection rule:

    const desktop = $("codex-desktop");
    desktop.checked = Boolean(det.codex_desktop);
    desktop.disabled = !det.codex_desktop;

    const selected = Array.from(
      document.querySelectorAll("input[data-client]:checked")
    ).map((input) => input.value);

In style.css, remove flex: 1 from .card; let the footer follow content; add compact primary-client and details styling using the established palette; reduce excess vertical padding; and style disabled desktop state distinctly. In app.py, change the window to height=680 and resizable=True.

- [ ] **Step 4: Run the web contract and setup tests**

Run:

    .venv\Scripts\python.exe -m pytest tests/test_setup_web.py tests/test_setup_clients.py -q

Expected: all tests pass, including the static guarantees for Codex Desktop and the absence of flex: 1 in the card rule.

- [ ] **Step 5: Perform visual smoke verification**

Run:

    .venv\Scripts\python.exe -m sisav2_mcp.app

Confirm manually that Codex Desktop is first and selected, the other clients are collapsed and unselected, the card ends after its content, and no oversized blank panel appears above the footer. Close the window without submitting credentials.

- [ ] **Step 6: Commit the UI change**

Run:

    git add src/sisav2_mcp/setup_gui/app.py src/sisav2_mcp/setup_gui/web/index.html src/sisav2_mcp/setup_gui/web/app.js src/sisav2_mcp/setup_gui/web/style.css tests/test_setup_web.py
    git commit -m "feat: prioritize Codex Desktop in setup"

### Task 3: Verify and publish the updated local executable

**Files:**

- Build: dist/sisav2-mcp.exe
- Replace locally: %LOCALAPPDATA%\sisav2-mcp\sisav2-mcp.exe

**Interfaces:**

- Consumes: the verified source tree and build/sisav2-mcp.spec.
- Produces: an executable that opens the updated setup screen with no arguments and serves MCP over stdio with serve.

- [ ] **Step 1: Run the complete source verification suite**

Run:

    .venv\Scripts\python.exe -m ruff check .
    .venv\Scripts\python.exe -m mypy src
    .venv\Scripts\python.exe -m pytest -q

Expected: all checks pass without reducing the configured coverage threshold.

- [ ] **Step 2: Build a fresh portable executable**

Run:

    .venv\Scripts\pyinstaller.exe build/sisav2-mcp.spec --clean --noconfirm

Expected: dist/sisav2-mcp.exe exists and includes the updated web assets.

- [ ] **Step 3: Verify the built executable before replacing the stable copy**

Run:

    dist\sisav2-mcp.exe --help

Expected: exit code 0, usage output that includes serve, and no GUI window. Then launch it with no arguments, perform the same non-authenticated visual check from Task 2, and close it.

- [ ] **Step 4: Replace the stable executable with a recoverable backup**

If the stable executable is locked, rename it to sisav2-mcp.previous.exe and copy dist/sisav2-mcp.exe to %LOCALAPPDATA%\sisav2-mcp\sisav2-mcp.exe. If it is not locked, overwrite it directly. Do not delete older backup files.

Run:

    Get-FileHash dist\sisav2-mcp.exe
    Get-FileHash "$env:LOCALAPPDATA\sisav2-mcp\sisav2-mcp.exe"

Expected: both SHA-256 values are identical.

- [ ] **Step 5: Verify the installed executable and hand off**

Launch %LOCALAPPDATA%\sisav2-mcp\sisav2-mcp.exe without arguments, confirm the Codex Desktop-first window, and close it. Report the path, checks run, build-artifact hash, and the need to restart Codex Desktop after registering the MCP.
