# Plan de implementación — Fase 1: MCP Server SISAV2 (solo lectura)

- **Spec:** `docs/superpowers/specs/2026-06-07-sisav2-mcp-fase1-servidor-readonly-design.md`
- **Reconciliación (Paso 1):** `docs/discovery/RECONCILIATION.md` (cerrada 2026-06-08, DoD ✅)
- **Fecha:** 2026-06-07 · **Refinado:** 2026-06-08
- **Estado:** ✅ **PLAN DEFINITIVO** — supersede a `...-plan-DRAFT.md`.

> **Qué cambió respecto al borrador.** La compuerta de reconciliación (Paso 1) ya se ejecutó: ver
> `RECONCILIATION.md`. Este plan absorbe sus 5 deltas + el cambio de grant de auth. Los nombres,
> params, modelos y endpoints de abajo son los **confirmados** contra los 17 samples y un probe de
> auth en vivo, no supuestos.

---

## Paso 1 — Compuerta de reconciliación ✅ HECHO

**Resultado:** `docs/discovery/RECONCILIATION.md`. Confirma superficie de tools, modelos (desde
samples), catálogos y el grant de auth. Cierra el caveat de loopback (probe: el cliente `SISAV2`
rechaza redirects loopback → v1 usa ROPC). **Solo entonces** se implementa (Pasos 2–10).

---

## Paso 2 — Scaffold del proyecto Python

**Tareas:** `pyproject.toml` con deps **`fastmcp`, `httpx`, `pydantic` v2, `keyring`** (dev:
`pytest`, `respx`, `ruff`, `mypy`). `authlib` queda **opcional** (ROPC se resuelve con `httpx`
directo contra el `token_endpoint`; reincorporar si se implementa PKCE). Layout
`src/sisav2_mcp/{auth,client,models,tools,resources}` + `config.py` + `server.py`; entrypoint
`sisav2-mcp`. `server.py` arranca un FastMCP vacío por stdio.
**Verificación:** `python -m sisav2_mcp.server` levanta y responde el handshake MCP; `ruff` y `mypy`
pasan en el esqueleto.

---

## Paso 3 — `config.py` + `models/` (desde los samples)

**Tareas:** `config.py` (base URL `https://sisav2-api.utem.cl`; OIDC issuer
`https://sso.utem.cl/auth/realms/prod`, `token_endpoint`, `client_id=SISAV2`; service name del
keychain; TTL de caché de catálogos). Modelos pydantic **derivados de los samples**, con su fuente:

| Modelo | Sample |
|---|---|
| `Postulacion` | `postulacion_buscar_{pregrado,postgrado,extension}.json` |
| `Proyecto` (≠ `Postulacion`: `id` ≠ `idpostulacion`, estados 8/10) | `proyectos_listar_pregrado.json` |
| `Indicador` (`{id:idEstado,total}`) | `convocatorias_postulacion_totales.json`, `postulacion_totales_pregrado.json` |
| `DetalleIniciativa` + `PasoWizard`/`BloquePaso` (form-builder genérico) | `postulacion_obtener_3033.json` |
| `Fase` | `convocatorias_fases_obtener_34.json` |
| `BitacoraEntry` (`fecha` = JS Date string) | `postulacion_listar-cambios_3033.json` |
| `ExportResult` (`{url,total,nombreArchivo}`) | `postulacion_exportar-excel.json` |
| `AvanceGlobalKPIs` (5 KPIs) | `estadisticas_globales-proyectos.json` |
| `Convocatoria`, `Carrera`, `Facultad`, `Estado` | `convocatorias_listar-combo`, `mantenedores_listarCarrera`, `mantenedores_listarFacultad`, `convocatorias_estado_buscar` |
| `Usuario`/`PermisosToken` (RBAC) | `usuarios_verifica-token.json` |

`Estado` como `Enum` (mapeo confirmado **1**=Incompleta, **2**=Ingresada, **3**=Admisible,
**4**=Pre-Aprobada, **5**=Agendar, **6**=Aprobada, **7**=Rechazada, **8**=Ejecución,
**9**=No-Realizada, **10**=Finalizado, **11**=Reformular). `modalidad` ∈ {`PRE_GRADO`,`POST_GRADO`,
`EXTENSION`}. Campos no esenciales `Optional`; tolerancia a campos desconocidos (log, no romper).
`FilaAvanceGlobal` **no** se modela en v1 (grilla diferida).
**Verificación:** tests unit que parsean **cada uno** de los 17 samples sin error (contract/golden).

---

## Paso 4 — `auth/` (ROPC + keychain, por usuario)

**Tareas:** implementar **`password` grant (ROPC)** contra
`https://sso.utem.cl/auth/realms/prod/protocol/openid-connect/token` con `client_id=SISAV2`
(público, sin secret), detrás de una interfaz **`TokenProvider`**. Credenciales en el **keychain del
SO** (`keyring` → Windows Credential Manager); onboarding las guarda una vez. Cachear y **refrescar**
el access token (~10 min) con `refresh_token` en silencio; al expirar la sesión, **re-autenticar en
silencio** con la credencial del keychain (sin navegador). Tras obtener token, resolver permisos vía
**`GET /usuarios/verifica-token`** (los roles de app NO están en el JWT). Dejar un `PkceTokenProvider`
**stub/documentado** como ruta de upgrade (bloqueado hasta que UTEM registre redirect loopback).
**Verificación:** tests con flujo OIDC mockeado (login ROPC, expiración→refresh,
refresh fallido→re-auth con keychain, credencial ausente→mensaje de onboarding).

---

## Paso 5 — `client/` (HTTP, GET-only + 1 excepción allowlisted, errores tipados)

**Tareas:** cliente `httpx` con base URL, inyección de bearer (vía `TokenProvider`), paginación
(`offset`/`limit`), reintentos con backoff, timeouts. **Guardia read-only: rechaza método ≠ GET**,
con una **allowlist explícita de (método, path)** cuyo único par sancionado es
`POST /convocatorias/postulacion/exportar-excel` (POST de solo-lectura). Excepciones tipadas:
`AuthError` (→ re-login), `NotFound`, `RateLimited` (→ backoff), `ServerError`, `NetworkTimeout`.
**Verificación:** tests con `respx`: paginación, mapeo de cada error, que un POST/PUT fuera de la
allowlist lanza excepción, y que el `POST exportar-excel` allowlisted **sí** pasa.

---

## Paso 6 — Tools del núcleo

**Tareas:** superficie confirmada (wrappers de conveniencia + `listar_proyectos` separado):

- `listar_postulaciones(modalidad, estado?, convocatoria?, facultad?, carrera?, ingreso?, busqueda?, ordenamiento?, offset?, limit?)` → `GET /convocatorias/postulacion/buscar` (tool base).
- Wrappers (presets sobre la base): `listar_admisibilidad` (`estado=[3,6,2,4]`,`ingreso=false`),
  `listar_planificacion` (`estado=[5]`,`ingreso=false`), `listar_cambio_fase`
  (`estado=[3,5,6,8,10,1,2,4,7,11,9]`,`ingreso=false`).
- `listar_proyectos(modalidad, busqueda?, ordenamiento?, offset?, limit?)` → `GET /proyectos/listar` (modelo `Proyecto`).
- `obtener_detalle_iniciativa(idPostulacion)` → `GET .../postulacion/obtener/{id}` (+ `GET .../fases/obtener/{idFase}`; cubre la vista *Evaluar admisibilidad*).
- `ver_bitacora(idPostulacion, offset?, limit?)` → `GET .../postulacion/listar-cambios`.
- `listar_repositorios(modalidad|roles)` → `GET /mantenedores/repositorios?vista=REPOSITORIO_VCM&roles={csv}`.

(`obtener_evaluacion_admisibilidad` **eliminada** — colapsa en el detalle.) Validación de args;
salida concisa/legible. **Verificación:** tests tool-level con `client` mockeado (forma de salida
estable); smoke real read-only de al menos `listar_postulaciones` y `obtener_detalle_iniciativa`.

---

## Paso 7 — Tools de reportes + escape hatch

**Tareas:**
- `resumen_indicadores(idUsuario, modalidad?)` → `GET /convocatorias/postulacion/totales/{idUsuario}`.
- `avance_global()` → `GET /proyectos/estadisticas/globales-proyectos` (**solo KPIs**; la grilla
  `/proyectos/estadisticas/proyectos` está **diferida**, da 400 server-side).
- `exportar_postulaciones(convocatoriaId, estado?, modalidad, idUsuario, roles?, ...)` →
  `POST .../postulacion/exportar-excel`; **v1 devuelve `ExportResult` (URL S3 prefirmada + total +
  nombreArchivo)**, no datos.
- `sisav2_consulta_generica(path, params)` **GET-only** con **allowlist** de paths de
  `API_INVENTORY.md`.

**Verificación:** tests; el escape hatch rechaza paths fuera de la allowlist y cualquier no-GET;
`exportar_postulaciones` retorna la URL sin descargar el binario.

---

## Paso 8 — Resources de catálogos

**Tareas:** **5 Resources confirmados** con caché TTL:
`sisav2://catalogo/{convocatorias,carreras,facultades,estados,fases}` →
`listar-combo`, `listarCarrera[?facultadId=]`, `listarFacultad`, `estado/buscar`,
`fases/obtener/{id}`. Catálogos **diferidos** (sin sample): unidades, servicios, roles, perfiles,
centros-costo, plantillas, usuarios. Fallback: tool `consultar_catalogo(nombre)` si el cliente MCP
no soporta Resources bien (Spec §13).
**Verificación:** tests de caché (hit/expiración); un Resource devuelve datos parseados.

---

## Paso 9 — Pulido de errores, empaquetado y smoke

**Tareas:** mensajes accionables a Claude (no stack traces); logging de shapes inesperados; README
con instalación + config MCP lista para pegar (Claude Desktop / Claude Code) + **guía de onboarding
de credenciales en el keychain**; checklist de **smoke manual** read-only contra el sitio real.
**Verificación:** suite completa verde (unit + contract + tool-level); smoke manual documentado.

---

## Paso 10 — Distribución para la demo

**Tareas:** empaquetar; instrucciones para que un par de analistas lo instalen y prueben (incluido el
guardado de credenciales en su keychain); recoger feedback como insumo para SISAV3.
**Hecho cuando (DoD del Spec §12):** un analista instala desde el README y, por chat, lista/filtra
iniciativas, ve un detalle de 7 pasos, lee una bitácora y obtiene KPIs de Avance Global — sin UI.

---

## Notas de seguridad / operación

- **PII:** los 17 samples están anonimizados; `docs/discovery/raw/` está en `.gitignore`. No
  versionar tokens ni la URL prefirmada de export.
- **Auth:** ROPC implica que el proceso MCP ve la clave UTEM al pedir token; se persiste **solo** en
  el keychain del SO (cifrado), nunca en config en texto plano ni en el repo. Upgrade a PKCE
  documentado (requiere acción de UTEM).
- **Identidad por usuario:** cada analista usa su cuenta → respeta sus roles/permisos
  (`verifica-token`).
