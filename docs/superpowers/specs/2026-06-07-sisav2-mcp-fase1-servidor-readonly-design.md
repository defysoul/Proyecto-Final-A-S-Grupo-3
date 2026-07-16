# Spec — Fase 1: MCP Server SISAV2 (solo lectura)

- **Proyecto:** MCP Server SISAV2 (UTEM · Vinculación con el Medio)
- **Fase:** 1 de 2 — Servidor MCP de solo lectura (v1)
- **Fecha:** 2026-06-07
- **Estado:** Diseño aprobado · **bloqueado por la Fase 0** (ver §2)
- **Spec previo (dependencia):** `2026-06-07-sisav2-mcp-fase0-descubrimiento-api-design.md`

---

## 1. Contexto y objetivo

MVP / prueba de concepto: permitir al equipo de analistas de VcM hacer su **seguimiento y
análisis diario de SISAV2 por chat con Claude** (Claude Desktop / Claude Code), en **solo
lectura**. Es una **demo** que probarán algunos analistas, insumo para la continuación hacia
**SISAV3** el próximo semestre (donde el MCP se integraría de forma nativa). Construido sobre el
Inventario de API de la Fase 0.

**No-objetivo de v1:** escrituras (crear postulaciones, evaluar admisibilidad, dar feedback,
cambios de fase). Se difieren a v2, detrás de confirmación explícita.

## 2. Dependencia de la Fase 0 y compuerta de reconciliación

Esta fase **consume** los artefactos de `docs/discovery/` (Fase 0): `API_INVENTORY.md`,
`AUTH_FLOW.md`, `ACTION_CATALOG.md`, `samples/*.json`.

**Compuerta de reconciliación (primer paso obligatorio de la implementación):** antes de
escribir código de producción, contrastar el diseño de §4–§8 contra lo que la Fase 0 encontró
realmente y **ajustar el diseño donde difiera**. En concreto, verificar:

- **Endpoints reales** vs. las tools propuestas (§5): nombres lógicos, params, paginación.
- **Hipótesis "3 ramas comparten endpoints con parámetro `rama`":** si es falsa, las tools
  dejan de parametrizarse por `rama` y se ajusta la estructura de `client/`.
- **Grant type de auth** concluido en `AUTH_FLOW.md`: PKCE (preferido) o password (fallback) —
  define la implementación de `auth/` (§7).
- **Shapes de respuesta** vs. los modelos pydantic (§4): los `samples/` son los *fixtures
  golden*; los modelos se derivan de ellos, no al revés.

El resultado de la reconciliación se anota en `docs/discovery/RECONCILIATION.md` (qué cambió
respecto a este spec y por qué). Solo entonces se implementa.

## 3. Arquitectura — capas aisladas y testeables

Proyecto Python (>=3.11) con capas de responsabilidad única, cada una entendible y testeable por
separado:

```
sisav2-mcp/
  src/sisav2_mcp/
    auth/         # cliente OIDC/PKCE Keycloak: identidad -> bearer válido (+ refresh)
    client/       # cliente HTTP (httpx) de la API SISAV2; GET-only; errores tipados
    models/       # modelos pydantic del dominio (espejo de los samples de Fase 0)
    tools/        # tools FastMCP nombradas por dominio (orquestación delgada)
    resources/    # MCP Resources para catálogos (datos de referencia)
    config.py     # configuración (base URL, OIDC) por env / archivo de usuario
    server.py     # app FastMCP, transporte stdio, wiring
  docs/discovery/ # (entrada, de la Fase 0)
  tests/
  pyproject.toml
```

- **`auth/`** — Una responsabilidad: convertir la identidad del analista en un bearer válido.
  Obtiene, cachea y refresca el token; gatilla re-login cuando el refresh falla. No sabe de
  endpoints de negocio ni de MCP.
- **`client/`** — Cliente `httpx` de la API: base URL, inyección del bearer, paginación,
  reintentos con backoff, timeouts, y mapeo HTTP → excepciones tipadas. **Guardia read-only:
  rechaza cualquier método ≠ GET** (incluido el escape hatch). No conoce MCP.
- **`models/`** — Modelos `pydantic` del dominio. Única fuente de verdad de shapes; validación
  + serialización concisa hacia Claude.
- **`tools/`** — Definiciones FastMCP, un archivo por área. Llaman al `client`, validan args y
  devuelven datos de `models`. Sin lógica de red propia.
- **`resources/`** — MCP Resources de catálogos, con caché por TTL.
- **`server.py`** — Ensambla todo, expone stdio.

**Stack:** Python 3.11+, **FastMCP** (SDK MCP oficial), `httpx`, `pydantic` v2, `authlib`
(OIDC/PKCE), `respx` (tests). Empaquetado con `pyproject.toml`; ejecutable como `sisav2-mcp`.

## 4. Modelos de dominio (pydantic)

Derivados de los `samples/` de la Fase 0. Conjunto inicial:
`Postulacion` (codigo, convocatoria, proyecto, encargado, carrera, facultad, estado),
`Indicador` (label, value), `DetalleIniciativa` (cabecera + lista de `PasoWizard`),
`PasoWizard`/`BloquePaso` (field | options | table | doc | note), `BitacoraEntry`
(autor, desde, hacia, fecha, observacion), `EvaluacionAdmisibilidad`, `FilaAvanceGlobal`
(proyecto + hitos + presupuesto), y catálogos (`Convocatoria`, `Fase`, `Unidad`, `Servicio`,
`Rol`, `Perfil`, `CentroCosto`, `Plantilla`, `Usuario`).

**Tolerancia:** campos no esenciales como `Optional` con default; campos desconocidos se
loguean (no rompen el parse). Estados como `Enum` con los valores observados
(Ingresada, Incompleta, Rechazada, Admisible, Finalizada, Reformular, Agendar, Ejecución,
Finalizado, Aprobada).

## 5. Superficie de tools (v1, read-only)

**Núcleo** (parametrizadas por `rama` ∈ {pregrado, postgrado, extension} — *sujeto a la
reconciliación de §2*):

| Tool | Entrada | Salida |
|---|---|---|
| `listar_postulaciones` | rama, filtros (estado, convocatoria, facultad, carrera, año, búsqueda), orden, paginación | filas `Postulacion` + `Indicador[]` |
| `obtener_detalle_iniciativa` | rama, codigo | `DetalleIniciativa` (cabecera + 7 pasos) |
| `ver_bitacora` | rama, codigo | `BitacoraEntry[]` |
| `consultar_admisibilidad` | rama, filtros | filas + indicadores de admisibilidad |
| `obtener_evaluacion_admisibilidad` | rama, codigo | `EvaluacionAdmisibilidad` |
| `listar_planificacion` | rama, filtros | filas en estado "Agendar" |
| `listar_ejecucion_seguimiento` | rama, filtros | filas en Ejecución/Finalizado |
| `consultar_cambio_fase` | rama, filtros | filas + indicadores |
| `listar_repositorios` | rama | grupos/carpetas de repositorios |

**Reportes/análisis:** `avance_global(filtros)` (KPIs + grilla agrupada),
`resumen_indicadores(rama)` (contadores por estado).

**Escape hatch:** `sisav2_consulta_generica(path, params)` — **GET-only**, con *allowlist* de
paths descubiertos en la Fase 0; para endpoints aún no envueltos en una tool de dominio.

**Catálogos → Resources** (no tools): `sisav2://catalogo/convocatorias`, `/fases`, `/unidades`,
`/servicios`, `/roles`, `/perfiles`, `/centros-costo`, `/plantillas`, `/usuarios`. Datos de
referencia, direccionables, cacheados por TTL.

## 6. Flujo de datos

Analista (chat) → Claude elige tool → validación de args (pydantic) → `client` hace **GET** con
bearer (`auth` refresca si expiró) → respuesta JSON → parse a `models` → la tool devuelve una
estructura concisa y legible → Claude resume/analiza en el chat. Los Resources se sirven
on-demand con caché TTL.

## 7. Autenticación

- **Primer uso:** Authorization Code + **PKCE** → abre el navegador a Keycloak UTEM → callback a
  un puerto local captura el `code` → intercambio por tokens → guarda el **refresh token cifrado**
  en disco local del analista (con permisos restringidos).
- **Llamadas siguientes:** usa el access token; ante 401/expiración refresca en silencio; si el
  refresh falla, devuelve a Claude un mensaje accionable de re-login.
- **Fallback:** *password grant* si `AUTH_FLOW.md` (Fase 0) concluye que es lo único viable.
- Cero credenciales hardcodeadas; toda la config de OIDC viene de `config.py` (env/archivo).
- Identidad **por usuario**: cada analista usa su propia cuenta → respeta sus roles/permisos.

## 8. Manejo de errores

- Excepciones tipadas en `client`: `AuthError` (→ re-login), `NotFound`, `RateLimited`
  (→ backoff), `ServerError`, `NetworkTimeout`.
- Las tools traducen excepciones a **mensajes accionables** para Claude, no stack traces
  ("Tu sesión expiró, vuelve a iniciar sesión"; "No existe la iniciativa 9999 en pregrado").
- Validación pydantic **tolerante** + logging de shapes inesperados: un campo nuevo en la API no
  rompe la tool entera.
- **Read-only enforcement** a nivel de `client` (método ≠ GET → excepción), de modo que ni el
  escape hatch pueda escribir en v1.

## 9. Configuración y despliegue

- **Local / stdio, por analista.** Se instala en la máquina del analista y se conecta a su
  cliente (Claude Desktop / Claude Code) vía la config MCP estándar (comando + args).
- `config.py` lee: base URL de SISAV2, parámetros OIDC (issuer, client_id, redirect local),
  ruta del token store, TTL de caché. Documentado en el README con un ejemplo de configuración
  MCP listo para pegar.
- Distribución a los analistas de la demo: instrucciones de instalación + primer login.

## 10. Testing

- **Unit:** `models` parsean los `samples/` de la Fase 0; `client` con `respx`/mocks; `auth` con
  flujo OIDC mockeado.
- **Contract/golden:** los `samples/` sanitizados como fixtures → el parsing matchea la API real
  capturada.
- **Tool-level:** cada tool con `client` mockeado → forma de salida estable y legible.
- **Smoke manual:** checklist read-only contra el sitio real con cuenta de analista, documentado
  en `docs/`.
- El clon (`sisav2-clone`) **no** es dependencia de tests, pero sirve de referencia visual/UX y
  para validar nombres de campos.

## 11. Fuera de alcance (v1) → v2

Escrituras (crear postulaciones, evaluar, feedback, cambio de fase, calendarizar) detrás de
confirmación explícita; despliegue remoto/hosted con OAuth por usuario; notificaciones; edición
de mantenedores. La arquitectura por capas (tools delgadas sobre un `client` que hoy es GET-only)
deja la puerta abierta a v2 sin reescritura.

## 12. Criterios de éxito (Definition of Done)

- Compuerta de reconciliación (§2) ejecutada y `RECONCILIATION.md` escrito.
- Todas las tools del §5 implementadas y devolviendo datos reales contra una cuenta de analista.
- Auth por usuario funcionando (login + refresh + re-login) según el grant concluido en Fase 0.
- Resources de catálogos servidos y cacheados.
- Suite de tests verde (unit + contract + tool-level) y smoke manual documentado.
- Un analista puede instalarlo siguiendo el README y, por chat, listar/filtrar iniciativas, ver
  un detalle de 7 pasos, leer una bitácora y obtener KPIs de Avance Global — sin tocar la UI.

## 13. Riesgos

- **Cambios de la API** entre Fase 0 y Fase 1 → mitigado por la compuerta de reconciliación y la
  validación tolerante.
- **Keycloak sin PKCE para cliente público** → fallback a password grant (definido en Fase 0).
- **Volumen/paginación** en listados grandes (~1.471 en pregrado) → paginación explícita en las
  tools y límites por defecto sensatos.
- **Soporte de MCP Resources desigual entre clientes** → si un cliente no los soporta bien, los
  catálogos se exponen además como una tool `consultar_catalogo(nombre)`.
