# Plan de implementación — Fase 0: Descubrimiento de la API de SISAV2

- **Spec:** `docs/superpowers/specs/2026-06-07-sisav2-mcp-fase0-descubrimiento-api-design.md`
- **Fecha:** 2026-06-07
- **Tipo:** recon autenticado + producción de inventario (poco código, mucha captura/documentación)
- **Resultado:** los artefactos de `docs/discovery/` que alimentan la Fase 1.

> **Naturaleza del trabajo.** Esto no es "escribir una feature": es una investigación
> estructurada. Cada paso *captura evidencia* del sistema real y *la documenta* en un artefacto
> versionado. La "prueba de que funciona" es que un revisor pueda reconstruir las llamadas de la
> Fase 1 leyendo solo `docs/discovery/`.

> **Antes de capturar:** confirmar que se usa una **cuenta de analista autorizada**, y no
> commitear jamás tokens/cookies/PII (ver Spec §7).

---

## Estado de ejecución (cerrado 2026-06-08)

| Paso | Estado | Nota |
|------|--------|------|
| 0 — Entorno de recon | ✅ | Esqueleto `docs/discovery/` + samples; recon vía Chrome DevTools MCP. |
| 1 — Auth (Keycloak/OIDC) | ✅ | Authorization Code + PKCE (S256), realm `prod`, cliente `SISAV2`. `AUTH_FLOW.md`. |
| 2 — Postulaciones/Ingresos | ✅ | `buscar` + `totales`; shape y paginación documentados. |
| 3 — Detalle, Bitácora, Admisibilidad | ✅ | Detalle form-builder; **Bitácora** = `listar-cambios`; **Evaluar** sin endpoint propio (reusa `obtener`+`fases`). |
| 4 — Planif/Ejec/CambioFase/Repos | ✅ | Planif+CambioFase = `buscar` (estado[]); **Ejecución = `proyectos/listar`** (endpoint distinto); Repositorios = `mantenedores/repositorios`. |
| 5 — Reportes (Avance Global) | ✅ parcial | KPIs `globales-proyectos` ✅; **grilla = 400 server-side → diferido a Fase 1**. |
| 6 — Hipótesis 3 ramas | ✅ | CONFIRMADO `modalidad` ∈ {PRE_GRADO, POST_GRADO, EXTENSION}; samples por rama. |
| 7 — Catálogos | ✅ parcial | convocatorias, carreras, facultades, **estados**, fases con shape; mantenedores profundos diferidos (por alcance). |
| 8 — Sanitización + ACTION_CATALOG | ✅ | 17 samples sanitizados (sin tokens/PII); `ACTION_CATALOG.md` completo. |
| 9 — DoD + cierre | ✅ | Checklist abajo; commit de `docs/discovery/`. |

**Hallazgos destacados de la sesión 2026-06-08:** idEstado 9 = "No-Realizada" (catálogo `estado/buscar`);
Ejecución usa el dominio `proyectos/` (no `buscar`); Export = `POST exportar-excel` → URL S3 prefirmada a XLSX;
grilla de Avance Global con 400 server-side (diferida). Detalle en `DISCOVERY_NOTES.md` y `API_INVENTORY.md`.

---

## Paso 0 — Preparación del entorno de recon

**Tareas**
1. Crear el esqueleto de artefactos (vacíos, con encabezados): `docs/discovery/API_INVENTORY.md`,
   `AUTH_FLOW.md`, `ACTION_CATALOG.md`, `DISCOVERY_NOTES.md`, y la carpeta `docs/discovery/samples/`.
2. Crear `docs/discovery/raw/` (ya excluida por `.gitignore`) para volcar capturas crudas
   (HAR/screenshots) sin riesgo de commitearlas.
3. Verificar acceso a la herramienta de recon: Chrome DevTools MCP y/o Playwright, capaces de
   listar `network requests` con cuerpos de respuesta.
4. Definir el **formato de ficha** de endpoint (plantilla copy-paste) al inicio de
   `API_INVENTORY.md`, según Spec §4.1 (nombre lógico, método, ruta, params, respuesta,
   vista/acción, notas).

**Hecho cuando:** existe el esqueleto de `docs/discovery/`, la plantilla de ficha está escrita, y
la herramienta de recon puede capturar tráfico autenticado en una prueba mínima (cargar
`/dashboard` y ver al menos una request XHR con su respuesta).

---

## Paso 1 — Descubrimiento de autenticación (Keycloak/OIDC)  ← prioridad, en paralelo desde el 1er login

**Tareas**
1. Iniciar sesión manual en `sisav2.utem.cl` con la cuenta de analista, observando la red.
2. Capturar el `.well-known/openid-configuration` del SSO (`sso.utem.cl`): `issuer`,
   `authorization_endpoint`, `token_endpoint`, `scopes`, grant types soportados.
3. Identificar `client_id` de la SPA, tipo de cliente (público/confidencial), si hay **PKCE**
   (parámetros `code_challenge`/`code_verifier` en el flujo).
4. Decodificar el **access token** (JWT): claims de roles/perfil, `exp`. Anotar forma del
   refresh token y cómo se adjunta el bearer a la API (`Authorization: Bearer`).
5. **Concluir el grant viable para un cliente local** sin intervención de TI: Authorization
   Code + PKCE (preferido) o password grant (fallback). Justificar con evidencia.

**Artefacto:** `AUTH_FLOW.md` completo, con la conclusión del grant **resaltada** (es la entrada
crítica para `auth/` en la Fase 1).
**Hecho cuando:** `AUTH_FLOW.md` responde sin ambigüedad "¿cómo obtendrá la Fase 1 un bearer por
usuario?", con el token **redactado** en todos los ejemplos.

---

## Paso 2 — Núcleo Pregrado: Postulaciones / Ingresos (camino crítico)

**Tareas**
1. Abrir `/vcm-pregrado/postulaciones`; capturar la(s) request(s) del **listado** + **indicadores**.
2. Ejercitar (read-only) y capturar las variaciones de params: **buscar**, **filtrar**
   (estado, convocatoria, facultad, carrera, año), **ordenar**, **paginar**. Documentar el
   formato exacto (ojo con la serialización de filtro/orden de Kendo).
3. Registrar la forma de la **paginación** (total/página/tamaño) y de los **indicadores** por estado.

**Artefacto:** fichas en `API_INVENTORY.md` (`listar_postulaciones`, `resumen_indicadores`) +
`samples/listar_postulaciones_pregrado.json` (sanitizado).
**Hecho cuando:** se puede describir en papel la request exacta para "postulaciones de Pregrado en
estado Ingresada, página 2" y su respuesta.

---

## Paso 3 — Núcleo Pregrado: Detalle (7 pasos), Bitácora y Admisibilidad

**Tareas**
1. Abrir el detalle de una iniciativa (p. ej. `/vcm-pregrado/gestionar-postulacion/3033`);
   capturar la(s) request(s) de **cabecera** y de **cada uno de los 7 pasos** del wizard
   (¿una llamada por paso o un único payload?). Documentar el shape de `BloquePaso`
   (field/options/table/doc/note).
2. Capturar la **Bitácora** (traza de estados/feedback): endpoint, shape de `BitacoraEntry`.
3. Capturar **Admisibilidad**: listado (`/vcm-pregrado/admisibilidad`) + vista **Evaluar**
   (`/vcm-pregrado/admisibilidad-evaluar/{id}`) — solo lectura del estado actual.

**Artefacto:** fichas (`obtener_detalle_iniciativa`, `ver_bitacora`, `consultar_admisibilidad`,
`obtener_evaluacion_admisibilidad`) + samples sanitizados (`detalle_iniciativa_3033.json`, etc.).
**Hecho cuando:** el detalle de 7 pasos + bitácora + admisibilidad están mapeados con sample cada uno.

---

## Paso 4 — Núcleo Pregrado: Planificación, Ejecución, Cambio de Fase, Repositorios

**Tareas:** capturar listados y filtros de `/planificacion-calendarizacion`,
`/ejecucion-seguimiento`, `/cambio-fase` (incluye sus indicadores) y `/repositorios-vcm`
(grupos/carpetas).
**Artefacto:** fichas + samples (`listar_planificacion`, `listar_ejecucion_seguimiento`,
`consultar_cambio_fase`, `listar_repositorios`).
**Hecho cuando:** las 6 vistas del núcleo Pregrado están en el inventario con sample.

---

## Paso 5 — Reportes: Avance Global

**Tareas:** capturar `/reportes/avance-global`: las **KPI cards** (proyectos, objetivos, hitos,
actividades, presupuesto) y la **grilla agrupada expandible** (logrados/no logrados/por lograr;
asignado/solicitado/aprobado). Si la cuenta no tiene datos, capturar el endpoint igual con sample
vacío y anotarlo (Spec §9).
**Artefacto:** ficha `avance_global` + sample.
**Hecho cuando:** el endpoint de Avance Global y sus params/filtros están documentados.

---

## Paso 6 — Validar hipótesis de "3 ramas comparten endpoints"

**Tareas:** repetir un subconjunto representativo (listado + detalle) en **Postgrado**
(`/vcm-postgrado/*`) y **Extensión** (`/extension-universitaria/*`). Verificar si reutilizan los
mismos endpoints con un **parámetro de rama** o si difieren.
**Artefacto:** nota explícita en `DISCOVERY_NOTES.md` (confirmada/refutada). **Si se refuta**, es
un hallazgo que la Fase 1 debe absorber en su compuerta de reconciliación (afecta la
parametrización por `rama`).
**Hecho cuando:** la hipótesis está confirmada o refutada con evidencia.

---

## Paso 7 — Catálogos (Mantenedores y Configuración)

**Tareas:** capturar endpoints (y params de filtro/paginación) de: convocatorias, fases de
proyecto, plantillas de ingreso, unidades, servicios, roles, perfiles, centros de costos,
usuarios. Samples opcionales (al menos convocatorias y fases, que la Fase 1 expone como Resources).
**Artefacto:** fichas en `API_INVENTORY.md` (sección Catálogos).
**Hecho cuando:** cada catálogo tiene al menos endpoint + params; convocatorias y fases con sample.

> Si el tiempo aprieta (Spec §6), los catálogos pueden quedar como inventario parcial; el mínimo
> no negociable es **núcleo + auth + reportes**. Anotar lo que quede pendiente.

---

## Paso 8 — Sanitización y mapa de acciones

**Tareas**
1. Revisar **todos** los `samples/`: anonimizar nombres/RUTs/correos de personas; conservar
   nombres institucionales (Spec §7). Verificar que ningún token/cookie quedó en los artefactos.
2. Escribir `ACTION_CATALOG.md`: tabla "acción del analista → endpoint(s) → tool propuesta para
   Fase 1 → tipo (lectura/escritura) → estado (v1/diferido v2)". Es el puente explícito al Spec 2.

**Hecho cuando:** todos los samples están sanitizados y `ACTION_CATALOG.md` cubre las acciones
de v1 mapeadas a endpoints concretos.

---

## Paso 9 — Verificación contra la Definition of Done y cierre

**Tareas (checklist del Spec §8):** — cerrado 2026-06-08
- [x] `API_INVENTORY.md` cubre núcleo (3 ramas) y Reportes con params + shape; catálogos al menos
      endpoint+params. _(Grilla Avance Global queda como 400 documentado/diferido.)_
- [x] `AUTH_FLOW.md` concluye el grant type de la Fase 1 con evidencia (PKCE S256 + fallback password; caveat loopback anotado).
- [x] `ACTION_CATALOG.md` mapea cada acción de v1 a endpoint(s) y marca lo diferido a v2.
- [x] ≥1 sample sanitizado por endpoint del núcleo y de Reportes.
- [x] Un revisor entiende las llamadas de la Fase 1 leyendo solo `docs/discovery/`.
- [x] `git status` limpio respecto a PII (nada crudo commiteado; tokens/PII anonimizados o redactados).

**Cierre:** completar `DISCOVERY_NOTES.md` (qué quedó incierto, supuestos a validar en Fase 1),
y **commit** de `docs/discovery/`.

---

## Transición a la Fase 1

Tras el cierre: ejecutar **session-handoff** y arrancar la Fase 1 en una **sesión limpia**, con
estos insumos: los dos specs, el borrador de plan de la Fase 1, y `docs/discovery/`. El primer
paso de la Fase 1 es su **compuerta de reconciliación** (contrastar diseño vs. hallazgos).
