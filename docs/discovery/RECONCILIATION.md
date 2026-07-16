# Reconciliación — Diseño Fase 1 vs. Hallazgos Fase 0

> **Compuerta de reconciliación (Paso 1 del plan, obligatorio antes de código).**
> Contrasta el diseño del Spec §4–§8
> (`docs/superpowers/specs/2026-06-07-sisav2-mcp-fase1-servidor-readonly-design.md`) contra lo que
> el recon autenticado de la Fase 0 encontró realmente, y fija las decisiones que el plan final
> debe absorber. Fuentes: `API_INVENTORY.md`, `AUTH_FLOW.md`, `ACTION_CATALOG.md`,
> `DISCOVERY_NOTES.md` y los 17 `samples/*.json`.
>
> **Fecha:** 2026-06-08 · **Estado:** cerrada (DoD del Paso 1 ✅).

---

## 1. Propósito y alcance

El Spec §2 ordena que, **antes de escribir código de producción**, se contraste el diseño de §4–§8
contra los hallazgos de la Fase 0 y se **ajuste el diseño donde difiera**, dejando el registro en
este documento. Los `samples/` son los *fixtures golden*: **los modelos se derivan de ellos, no al
revés**.

La Fase 0 cerró con recon autenticado (cuenta con perfil Administrador → ve todo) que mapeó el
núcleo + reportes a endpoints reales. Esta reconciliación concluye que **el diseño es viable con
cinco ajustes materiales** (§3) y **un cambio de grant de auth forzado por un hallazgo en vivo**
(§4). No se invalida la arquitectura de capas (Spec §3).

---

## 2. Reconciliación tool por tool (Spec §5 → endpoint real → decisión)

| Tool del Spec §5 | Endpoint real (Fase 0) | Decisión |
|---|---|---|
| `listar_postulaciones` | `GET /convocatorias/postulacion/buscar` | **Mantener** como tool base genérica (params `modalidad`,`idUsuario`,`roles[]`,`estado[]`,`ingreso`,`ordenamiento`,`offset`,`limit`). |
| `consultar_admisibilidad` | `GET .../postulacion/buscar` (`estado=[3,6,2,4]`,`ingreso=false`) | **Renombrar → `listar_admisibilidad`**, implementado como *wrapper* (preset) sobre `listar_postulaciones`. |
| `listar_planificacion` | `GET .../postulacion/buscar` (`estado=[5]`,`ingreso=false`) | **Mantener como wrapper** (preset estado=Agendar) sobre `listar_postulaciones`. |
| `consultar_cambio_fase` | `GET .../postulacion/buscar` (`estado=[todos]`,`ingreso=false`) | **Renombrar → `listar_cambio_fase`**, wrapper (preset 11 estados) sobre `listar_postulaciones`. |
| `listar_ejecucion_seguimiento` | **`GET /proyectos/listar`** (endpoint DISTINTO; clave raíz `data`) | **Renombrar → `listar_proyectos`** y **separar** (no es `buscar`). Modelo `Proyecto` aparte (ver §3a, §5). |
| `obtener_detalle_iniciativa` | `GET /convocatorias/postulacion/obtener/{id}` (+ `GET /convocatorias/fases/obtener/{idFase}`) | **Mantener.** Absorbe además la vista *Evaluar admisibilidad* (no tiene endpoint propio). |
| `obtener_evaluacion_admisibilidad` | **sin endpoint de lectura propio** | **Eliminar como tool standalone** → colapsa en `obtener_detalle_iniciativa` (ver §3c). |
| `ver_bitacora` | `GET /convocatorias/postulacion/listar-cambios?idPostulacion=&offset=&limit=` | **Mantener.** Respuesta `{cambios:[...]}`. |
| `listar_repositorios` | `GET /mantenedores/repositorios?vista=REPOSITORIO_VCM&roles={csv}` | **Mantener.** Lista grupos/carpetas (no documentos). |
| `avance_global` | `GET /proyectos/estadisticas/globales-proyectos` (KPIs) | **Mantener pero acotar a KPIs.** La grilla `/proyectos/estadisticas/proyectos` da **400 server-side** → diferida (§3e). |
| `resumen_indicadores` | `GET /convocatorias/postulacion/totales/{idUsuario}?modalidad=` | **Mantener.** Respuesta `[{id:idEstado,total}]`. |
| `sisav2_consulta_generica` | escape hatch GET-only + allowlist | **Mantener.** Allowlist = paths de `API_INVENTORY.md`. |
| *(no existía en §5)* | **`POST /convocatorias/postulacion/exportar-excel`** | **Agregar tool `exportar_postulaciones`** (POST de solo-lectura, ver §3d). |

**Superficie final de tools (v1):** `listar_postulaciones` + 3 wrappers (`listar_admisibilidad`,
`listar_planificacion`, `listar_cambio_fase`), `listar_proyectos`, `obtener_detalle_iniciativa`,
`ver_bitacora`, `listar_repositorios`, `resumen_indicadores`, `avance_global`,
`exportar_postulaciones`, `sisav2_consulta_generica`. (12 tools; `obtener_evaluacion_admisibilidad`
eliminada.)

---

## 3. Decisiones clave (deltas respecto al Spec)

### (a) `listar_proyectos` separado de `listar_postulaciones` — modelo `Proyecto` aparte
Ejecución y Seguimiento **no** usa `buscar`: vive en el dominio `proyectos/` (`GET /proyectos/listar`,
clave raíz **`data`** y no `postulaciones`). Una postulación aprobada se materializa como **proyecto**
con **`id` propio ≠ `idpostulacion`**; estados observados 8 (Ejecución) y 10 (Finalizado); `total`
1299. → El Spec §4, que preveía un único `Postulacion`, se ajusta: **se modela `Proyecto`
independiente** (con `id`, `idpostulacion`, `nombrepostulacion`, `encargado`, `nombreestado`, etc.).
Fuente: `samples/proyectos_listar_pregrado.json`.

### (b) Wrappers de conveniencia sobre `buscar` (decisión de UX)
Admisibilidad, Planificación y Cambio de Fase son **el mismo** `GET .../postulacion/buscar` variando
`estado[]` + `ingreso` (confirmado, mismo shape, sin samples extra). En vez de una sola tool genérica
o de tools por endpoint distinto, se exponen **wrappers delgados nombrados por vista** sobre
`listar_postulaciones` — mejor descubribilidad para Claude/analista y respeta el mapa mental de la
SPA. Mapeo de presets:
- `listar_admisibilidad` → `estado=[3,6,2,4]`, `ingreso=false`
- `listar_planificacion` → `estado=[5]`, `ingreso=false`
- `listar_cambio_fase` → `estado=[3,5,6,8,10,1,2,4,7,11,9]`, `ingreso=false`
- (la vista "Postulaciones" = `listar_postulaciones` con `ingreso=true`)

### (c) "Evaluar admisibilidad" sin endpoint de lectura propio
La vista *Evaluar* (`/vcm-pregrado/admisibilidad-evaluar/{id}`) reutiliza `obtener/{id}` (detalle
form-builder) + `fases/obtener/{idFase}` + catálogos; **no hay endpoint de "evaluación actual"** más
allá del `idestado` de la postulación (emitir veredicto es **escritura → v2**). → `obtener_evaluacion_admisibilidad`
del Spec §5 **se elimina como tool standalone** y se modela como vista derivada del detalle.

### (d) Export = POST de **solo lectura** → excepción a la regla GET-only
`POST /convocatorias/postulacion/exportar-excel` (body JSON `{convocatoriaId, convocatoriaNombre,
estado[], modalidad, idUsuario, roles[], esAdmin}`) devuelve `{url, total, nombreArchivo}`, donde
`url` es una **URL prefirmada de S3** al `.xlsx` (expira ~900s). **Los datos NO vienen en el JSON.**
→ Rompe la regla "método≠GET→excepción" del `client` mediante una **allowlist explícita de
(método, path)** con un único par sancionado: `POST /convocatorias/postulacion/exportar-excel`. **v1
= devolver la URL** (`ExportResult`); **v2 = descargar+parsear XLSX** (openpyxl/pandas). La URL
prefirmada lleva credenciales → **no versionar** (redactada en el sample).

### (e) Grilla de Avance Global diferida (400 server-side)
`GET /proyectos/estadisticas/proyectos?offset=0&limit=10` devuelve **`400 {"message":"Ocurrió un
error al intentar obtener la información"}`** con la request **exacta** que dispara el SPA (no es un
param faltante; el propio front falla). Como `/proyectos/listar` sí trae 1299 proyectos, se descarta
"sin datos": es un **error server-side / feature posiblemente rota en prod**. → **Shape indescubrible
desde esta cuenta → diferido.** `avance_global` v1 expone **solo los KPIs** (`globales-proyectos`,
que sí responden): `{totalProyectos, totalObjetivosEspecificos, totalHitos, totalActividades,
totalPresupuesto}`.

---

## 4. Autenticación — el Spec §7 se reescribe (hallazgo en vivo)

El Spec §7 y `AUTH_FLOW.md` (Fase 0) recomendaban **Authorization Code + PKCE** con callback
loopback, dejando como caveat "verificar si el cliente permite redirects de loopback". **Probe en
vivo del 2026-06-08 (solo GETs, sin cambiar estado del servidor)** contra Keycloak UTEM (`realm
prod`, cliente público `SISAV2`):

| Probe | `redirect_uri` | Resultado |
|---|---|---|
| A | `http://localhost:8765/callback` | **HTTP 400** — página de error con `redirect_uri` |
| B (control) | `https://sisav2.utem.cl/` | **HTTP 200** — formulario de login (`kc-form-login`, `username`, `password`) |
| C | `http://127.0.0.1:8765/callback` | **HTTP 400** — mismo error |

Como A y C difieren de B **solo** en `redirect_uri` (mismos `client_id`, `response_type`, `scope`,
`code_challenge`), queda probado que el cliente `SISAV2` **rechaza redirects loopback** (localhost y
127.0.0.1). → **El flujo PKCE-loopback no es viable** sin que UTEM registre un redirect loopback para
el cliente.

**Decisión (confirmada con el usuario):**
- **v1 = `password` grant (ROPC)** — habilitado en el realm (`grant_types_supported` incluye
  `password`), no requiere `redirect_uri` registrado, funciona para cliente público.
- **Credenciales en el keychain del SO** (Windows Credential Manager vía `keyring`): onboarding las
  guarda una vez; login, refresh (`refresh_token`) y re-autenticación **silenciosos**, sin navegador.
  El access token (~10 min) se refresca en silencio; al expirar la sesión SSO, re-autentica con la
  credencial guardada. La clave queda cifrada en reposo por el SO; el proceso MCP la ve en claro solo
  al pedir el token.
- **Roles de app NO en el JWT** → tras obtener token, llamar `GET /usuarios/verifica-token` para
  perfil/roles/permisos (RBAC de la app).
- **`auth/` se diseña tras una interfaz `TokenProvider`** para conmutar a PKCE **sin reescribir**
  tools ni client, en cuanto UTEM registre `http://localhost:*` / `http://127.0.0.1:*`. Esa es la
  **ruta de upgrade** documentada.

(El detalle del probe queda registrado también en `AUTH_FLOW.md` para no re-probar.)

---

## 5. Modelos confirmados desde los samples (los samples mandan)

| Modelo | Sample fuente | Notas |
|---|---|---|
| `Postulacion` | `postulacion_buscar_{pregrado,postgrado,extension}.json` | `idpostulacion, nombrepostulacion, encargado?, carreraformulario, facultadformulario, idconvocatoria, nombreconvocatoria, idestado, nombreestado, anioInicioConvocatoria, fecha`. |
| `Proyecto` | `proyectos_listar_pregrado.json` | **Distinto de `Postulacion`**: `id` (idProyecto) ≠ `idpostulacion`; estados 8/10; `encargado` (PII). |
| `Indicador` | `convocatorias_postulacion_totales.json`, `postulacion_totales_pregrado.json` | `[{id:idEstado, total}]`. |
| `DetalleIniciativa` + `PasoWizard`/`BloquePaso` | `postulacion_obtener_3033.json` | Form-builder: `formulario.formulario[]` = secciones (los "7 pasos"); cada bloque tiene `json:[campos]`. Modelar secciones+campos **genéricos**, no fijos; `value` escalar o array. |
| `Fase` | `convocatorias_fases_obtener_34.json` | Workflow rol→estado, plantillas, calendarización. |
| `BitacoraEntry` | `postulacion_listar-cambios_3033.json` | `{estadoActual, estadoAnterior, fecha, idPostulacion, observacion, nombrePostulacion, nombreUsuario}`. `fecha` = JS Date string (no ISO). |
| `ExportResult` | `postulacion_exportar-excel.json` | `{url, total, nombreArchivo}` (URL S3 prefirmada). |
| `AvanceGlobalKPIs` | `estadisticas_globales-proyectos.json` | 5 KPIs agregados. |
| `Convocatoria`, `Carrera`, `Facultad`, `Estado` | `convocatorias_listar-combo`, `mantenedores_listarCarrera`, `mantenedores_listarFacultad`, `convocatorias_estado_buscar` | Catálogos (ver §6). |
| `Usuario` / `PermisosToken` | `usuarios_verifica-token.json` | Perfil + `perfil.roles[].permisos[].{nomenclatura,idModulo}` (RBAC). |
| `EvaluacionAdmisibilidad` | *(derivado, sin sample propio)* | Vista derivada de `DetalleIniciativa` + `Fase` (no es endpoint). |

**Enum de estados (CONFIRMADO** vía `convocatorias_estado_buscar.json`**):**
`1`=Incompleta · `2`=Ingresada · `3`=Admisible · `4`=Pre-Aprobada · `5`=Agendar · `6`=Aprobada ·
`7`=Rechazada · `8`=Ejecución · `9`=No-Realizada · `10`=Finalizado · `11`=Reformular.
**`modalidad`** ∈ {`PRE_GRADO`, `POST_GRADO`, `EXTENSION`} (endpoints idénticos entre ramas).
**Tolerancia:** campos no esenciales `Optional` con default; campos desconocidos se loguean (no
rompen el parse).

> Ajuste al Spec §4: `FilaAvanceGlobal` (proyecto+hitos+presupuesto) **se difiere** con la grilla
> (§3e); v1 solo usa `AvanceGlobalKPIs`.

---

## 6. Catálogos → Resources: confirmados vs. diferidos

**Confirmados (con sample, shape conocido) — 5 Resources v1:**

| Resource URI | Endpoint | Sample |
|---|---|---|
| `sisav2://catalogo/convocatorias` | `GET /convocatorias/listar-combo` | `convocatorias_listar-combo.json` |
| `sisav2://catalogo/carreras` | `GET /mantenedores/listarCarrera[?facultadId=]` | `mantenedores_listarCarrera.json` |
| `sisav2://catalogo/facultades` | `GET /mantenedores/listarFacultad` | `mantenedores_listarFacultad.json` |
| `sisav2://catalogo/estados` | `GET /convocatorias/estado/buscar` | `convocatorias_estado_buscar.json` |
| `sisav2://catalogo/fases` | `GET /convocatorias/fases/obtener/{id}` | `convocatorias_fases_obtener_34.json` |

**Diferidos (sin sample / shape no confirmado):** `unidades`, `servicios`, `roles` (shape de
`GET /usuarios/roles/listar/si` pendiente de leer el cuerpo), `perfiles`, `centros-costo`,
`plantillas`, `usuarios` (Mantenedores módulos 16–17). → El Spec §5 listaba 9 catálogos; v1 entrega
los **5 confirmados** y deja el resto como ampliación.

> Nota: `carreras`, `facultades` y `estados` **no** estaban en la lista de catálogos del Spec §5 pero
> sí son necesarios (filtros de `buscar`) y están confirmados → se incorporan.

---

## 7. Items diferidos (consolidado)

1. **Avance Global — grilla** (`/proyectos/estadisticas/proyectos`): 400 server-side; shape
   indescubrible desde esta cuenta. KPIs sí funcionan.
2. **Catálogos sin sample:** unidades, servicios, perfiles, centros-costo, plantillas, usuarios; y el
   shape de `roles/listar/si`.
3. **Parseo del XLSX de exportación → v2** (v1 devuelve la URL prefirmada).
4. **Documentos dentro de un repositorio** (`REPDOCLIST`): endpoint no capturado, prioridad menor.
5. **Upgrade a PKCE:** bloqueado hasta que UTEM registre un redirect loopback para el cliente
   `SISAV2` (§4).

---

## 8. Ajustes al Spec (supuestos invalidados)

- **§5 (superficie de tools):** `obtener_evaluacion_admisibilidad` eliminada; `consultar_admisibilidad`/
  `consultar_cambio_fase` renombradas y convertidas en wrappers; `listar_ejecucion_seguimiento` →
  `listar_proyectos` (endpoint y modelo distintos); `exportar_postulaciones` agregada; catálogos v1
  reducidos a 5 (con `carreras`/`facultades`/`estados` incorporados).
- **§7 (auth):** Authorization Code + PKCE con loopback **descartado para v1** (probe: loopback
  rechazado); **v1 = ROPC + keychain**, con `TokenProvider` para futuro PKCE.
- **§4 (modelos):** `Postulacion` y `Proyecto` son modelos **separados**; `FilaAvanceGlobal`
  diferido; modelos derivados estrictamente de los 17 samples.
- **§5 (escape hatch):** la regla GET-only del `client` admite **una excepción allowlisted**
  (`POST exportar-excel`).

La arquitectura de capas (Spec §3) y el flujo de datos (§6) se mantienen sin cambios.

---

## 9. Impacto en el plan (resumen)

El plan final (`2026-06-07-sisav2-mcp-fase1-servidor-readonly-plan.md`, supersede al `-DRAFT.md`)
absorbe estos deltas en: **Paso 2** (dep `keyring`; `authlib` opcional), **Paso 3** (modelos exactos
con sample fuente + Enum de estados), **Paso 4** (ROPC+keychain tras `TokenProvider`; `verifica-token`
para roles), **Paso 5** (GET-only + allowlist para el POST de export), **Paso 6** (wrappers +
`listar_proyectos`; sin `obtener_evaluacion_admisibilidad`), **Paso 7** (`avance_global` solo KPIs;
`exportar_postulaciones` devuelve URL; allowlist del escape hatch desde `API_INVENTORY.md`), **Paso
8** (5 Resources confirmados; resto diferido). Pasos 9–10 sin cambios materiales (añadir onboarding
de credenciales en keychain a la guía de instalación).
