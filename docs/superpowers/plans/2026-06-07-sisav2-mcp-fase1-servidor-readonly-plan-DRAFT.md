# Plan de implementación — Fase 1: MCP Server SISAV2 (solo lectura) — **BORRADOR (SUPERSEDED)**

- **Spec:** `docs/superpowers/specs/2026-06-07-sisav2-mcp-fase1-servidor-readonly-design.md`
- **Fecha:** 2026-06-07
- **Estado:** ⛔ **SUPERSEDED (2026-06-08)** — reemplazado por el plan definitivo
  `2026-06-07-sisav2-mcp-fase1-servidor-readonly-plan.md`, tras cerrar la compuerta de
  reconciliación (`docs/discovery/RECONCILIATION.md`). Este borrador se conserva solo como
  historial; **no ejecutar desde aquí.**

> **Por qué es un borrador.** El contenido concreto de esta fase (endpoints exactos, grant de
> auth, shapes de respuesta, si las 3 ramas comparten endpoints) **depende de los resultados de
> la Fase 0**. Este borrador fija la *estructura y el orden* del trabajo; los detalles se
> confirman/ajustan en la **compuerta de reconciliación** (Paso 1).
>
> **Cómo se usará.** Tras cerrar la Fase 0: `session-handoff` → **sesión limpia** que recibe como
> insumos (1) los dos specs, (2) este borrador, (3) los artefactos `docs/discovery/`. En esa
> sesión se refina este borrador a un plan definitivo y se ejecuta.

---

## Paso 1 — Compuerta de reconciliación (PRIMERO, antes de cualquier código)

**Tareas**
1. Leer `docs/discovery/` (`API_INVENTORY.md`, `AUTH_FLOW.md`, `ACTION_CATALOG.md`, `samples/`).
2. Contrastar contra el diseño del Spec §4–§8 y resolver:
   - ¿Las 3 ramas comparten endpoints con parámetro `rama`? (Si no → reestructurar `client/`/tools.)
   - ¿Grant de auth real? (PKCE preferido / password fallback → define `auth/`.)
   - ¿Los shapes de los `samples/` calzan con los modelos previstos? (Los samples mandan.)
   - ¿Hay endpoints no previstos / faltantes respecto a la superficie de tools?
3. Escribir `docs/discovery/RECONCILIATION.md`: qué cambió respecto al spec y por qué; ajustar el
   Spec 2 si algún supuesto se invalidó.

**Hecho cuando:** existe `RECONCILIATION.md` y la lista de tools/modelos/auth está confirmada
contra la realidad. **Solo entonces** se implementa.

---

## Paso 2 — Scaffold del proyecto Python

**Tareas:** `pyproject.toml` (deps: fastmcp, httpx, pydantic, authlib; dev: pytest, respx, ruff,
mypy); layout `src/sisav2_mcp/{auth,client,models,tools,resources}` + `config.py` + `server.py`;
entrypoint `sisav2-mcp`. `server.py` arranca un FastMCP vacío por stdio.
**Verificación:** `python -m sisav2_mcp.server` levanta y responde el handshake MCP; `ruff` y
`mypy` pasan en el esqueleto.

---

## Paso 3 — `config.py` + `models/` (desde los samples)

**Tareas:** `config.py` (base URL, OIDC issuer/client_id/redirect local, ruta token store, TTL).
Modelos pydantic derivados de `samples/`: `Postulacion`, `Indicador`, `DetalleIniciativa`,
`PasoWizard`/`BloquePaso`, `BitacoraEntry`, `EvaluacionAdmisibilidad`, `FilaAvanceGlobal`, y
catálogos. Estados como `Enum`; campos no esenciales `Optional`; tolerancia a campos desconocidos.
**Verificación:** tests unit que parsean **cada** sample sin error (contract/golden).

---

## Paso 4 — `auth/` (OIDC por usuario)

**Tareas:** implementar el grant concluido en Fase 0 — Authorization Code + PKCE (abrir navegador,
callback local, intercambio) o password grant fallback. Cachear y **refrescar** token; guardar
refresh token **cifrado** con permisos restringidos; gatillar re-login al fallar el refresh.
**Verificación:** tests con flujo OIDC mockeado (éxito, expiración→refresh, refresh fallido→re-login).

---

## Paso 5 — `client/` (HTTP, GET-only, errores tipados)

**Tareas:** cliente `httpx` con base URL, inyección de bearer (vía `auth/`), paginación,
reintentos con backoff, timeouts. **Guardia read-only: rechaza método ≠ GET.** Excepciones
tipadas: `AuthError`, `NotFound`, `RateLimited`, `ServerError`, `NetworkTimeout`.
**Verificación:** tests con `respx`: paginación, mapeo de cada error, y que un intento POST/PUT
lanza excepción (read-only).

---

## Paso 6 — Tools del núcleo

**Tareas:** implementar (parametrizadas por `rama` según reconciliación) `listar_postulaciones`,
`obtener_detalle_iniciativa`, `ver_bitacora`, `consultar_admisibilidad`,
`obtener_evaluacion_admisibilidad`, `listar_planificacion`, `listar_ejecucion_seguimiento`,
`consultar_cambio_fase`, `listar_repositorios`. Validación de args; salida concisa/legible.
**Verificación:** tests tool-level con `client` mockeado (forma de salida estable); smoke real
read-only de al menos `listar_postulaciones` y `obtener_detalle_iniciativa`.

---

## Paso 7 — Tools de reportes + escape hatch

**Tareas:** `avance_global`, `resumen_indicadores`; `sisav2_consulta_generica(path, params)`
**GET-only** con **allowlist** de paths de la Fase 0.
**Verificación:** tests; el escape hatch rechaza paths fuera de la allowlist y cualquier no-GET.

---

## Paso 8 — Resources de catálogos

**Tareas:** Resources `sisav2://catalogo/{convocatorias,fases,unidades,servicios,roles,perfiles,
centros-costo,plantillas,usuarios}` con caché TTL. Fallback: tool `consultar_catalogo(nombre)` si
el cliente MCP no soporta Resources bien (Spec §13).
**Verificación:** tests de caché (hit/expiración); un Resource devuelve datos parseados.

---

## Paso 9 — Pulido de errores, empaquetado y smoke

**Tareas:** mensajes accionables a Claude (no stack traces); logging de shapes inesperados;
README con instalación + config MCP lista para pegar (Claude Desktop / Claude Code) + guía de
primer login; checklist de **smoke manual** read-only contra el sitio real.
**Verificación:** suite completa verde (unit + contract + tool-level); smoke manual documentado.

---

## Paso 10 — Distribución para la demo

**Tareas:** empaquetar; instrucciones para que un par de analistas lo instalen y prueben; recoger
feedback como insumo para SISAV3.
**Hecho cuando (DoD del Spec §12):** un analista instala desde el README y, por chat, lista/filtra
iniciativas, ve un detalle de 7 pasos, lee una bitácora y obtiene KPIs de Avance Global — sin UI.

---

## Notas de refinamiento (a resolver en la sesión limpia con resultados de Fase 0)

- Confirmar nombres lógicos y params reales de cada tool contra `API_INVENTORY.md`.
- Confirmar el grant de auth y ajustar el Paso 4.
- Confirmar parametrización por `rama` (Paso 6) o reestructurar si las ramas difieren.
- Derivar los modelos exactos (Paso 3) de los `samples/` definitivos.
- Ajustar la allowlist del escape hatch (Paso 7) a los paths efectivamente descubiertos.
