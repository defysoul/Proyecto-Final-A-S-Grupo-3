(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const api = () => (window.pywebview && window.pywebview.api) || null;

  const CLIENT_LABELS = {
    claude_code: "Claude Code",
    claude_desktop: "Claude Desktop",
    codex_cli: "Codex CLI",
  };

  function setStatus(el, kind, msg) {
    el.hidden = false;
    el.className = "status " + kind;
    el.textContent = msg;
  }

  // Auto-detección al abrir la ventana: pinta los clientes y pre-marca los
  // detectados. Se llama en cuanto pywebview inyecta su API.
  async function renderClients() {
    const a = api();
    if (!a) return;
    let det = {};
    try {
      det = await a.detectar();
    } catch (e) {
      det = {};
    }
    const list = $("clients-list");
    const desktop = $("codex-desktop");
    const desktopCard = $("codex-desktop-card");
    const desktopDescription = $("codex-desktop-description");
    const desktopStatus = $("codex-desktop-status");
    const desktopFound = Boolean(det.codex_desktop);
    desktop.checked = desktopFound;
    desktop.disabled = !desktopFound;
    desktopCard.classList.toggle("dim", !desktopFound);
    desktopDescription.textContent = desktopFound
      ? "Detectado en este equipo; se configurará primero."
      : "No se detectó Codex Desktop en este equipo.";
    desktopStatus.textContent = desktopFound ? "recomendado" : "no detectado";
    list.innerHTML = "";
    Object.keys(CLIENT_LABELS).forEach((key) => {
      const found = !!det[key];
      const row = document.createElement("label");
      row.className = "check" + (found ? "" : " dim");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = key;
      cb.dataset.client = "";
      cb.checked = false;
      const span = document.createElement("span");
      span.textContent = CLIENT_LABELS[key];
      const em = document.createElement("em");
      em.textContent = found ? "detectado" : "no detectado";
      row.appendChild(cb);
      row.appendChild(span);
      row.appendChild(em);
      list.appendChild(row);
    });
  }

  function seleccionados() {
    return Array.from(document.querySelectorAll("input[data-client]:checked")).map(
      (input) => input.value
    );
  }

  // Acción única: verifica la credencial y, si es válida, registra el MCP en los
  // clientes marcados — todo con un solo clic.
  async function conectar() {
    const a = api();
    if (!a) return;
    const u = $("usuario").value.trim();
    const p = $("clave").value;
    if (!u || !p) {
      setStatus($("status"), "error", "Ingresa usuario y clave.");
      return;
    }
    const checks = seleccionados();
    if (checks.length === 0) {
      setStatus($("status"), "error", "Marca al menos un agente donde instalarlo.");
      return;
    }
    const btn = $("btn-conectar");
    btn.disabled = true;
    setStatus($("status"), "loading", "Verificando con UTEM…");
    try {
      const r = await a.verificar(u, p);
      if (!r.ok) {
        setStatus($("status"), "error", r.error || "No se pudo verificar.");
        return;
      }
      setStatus($("status"), "loading", "✓ " + r.nombre + " · registrando el MCP…");
      const c = await a.configurar(checks);
      const lines = c.resultados
        .map((x) => (x.estado === "ok" ? "✓ " : "✗ ") + x.cliente + (x.estado !== "ok" ? " — " + x.detalle : ""))
        .join("\n");
      const bad = c.resultados.filter((x) => x.estado !== "ok").length;
      const ok = c.resultados.length - bad;
      setStatus($("status"), bad ? "warn" : "ok", lines);
      if (ok > 0) {
        $("done-text").textContent =
          "Conectado como " + r.nombre + " · configurado en " + ok + " agente(s).";
        $("step-done").hidden = false;
        $("step-done").scrollIntoView({ behavior: "smooth" });
      }
    } catch (e) {
      setStatus($("status"), "error", "Error: " + e);
    } finally {
      btn.disabled = false;
    }
  }

  function init() {
    renderClients();
  }

  $("btn-conectar").addEventListener("click", conectar);
  $("btn-cerrar").addEventListener("click", () => {
    const a = api();
    if (a) a.salir();
  });
  $("clave").addEventListener("keydown", (e) => {
    if (e.key === "Enter") conectar();
  });

  // pywebview inyecta su API de forma asíncrona: si ya está lista, detectar ya;
  // si no, esperar el evento `pywebviewready`.
  if (window.pywebview && window.pywebview.api) {
    init();
  } else {
    window.addEventListener("pywebviewready", init);
  }
})();
