# Inventario de API — SISAV2

> Capturado por recon autenticado de `https://sisav2.utem.cl` (SPA Angular + Kendo).
> Una ficha por endpoint. **Tokens/cookies REDACTADOS. PII de personas anonimizada.**
> Fecha de inicio de captura: 2026-06-07.

---

## Plantilla de ficha (copiar para cada endpoint)

```
### `<nombre_logico>` · `<MÉTODO> <ruta-con-plantilla>`
- **Descripción:** <qué devuelve / hace>
- **Origen:** vista frontend `<ruta>` · **Acción del analista:** <…>
- **Parámetros:**
  | nombre | tipo | req | valores observados |
  |--------|------|-----|--------------------|
  |        |      |     |                    |
- **Respuesta (shape):**
  { campo: tipo, … }
  Paginación: <total / page / size / …>
- **Sample:** `samples/<archivo>.json`
- **Notas:** <rate limit, errores, idiosincrasias de params Kendo, etc.>
- **Capturado:** 2026-06-07
```

---

## 0. Infraestructura y auth
- **Base URL:** `https://sisav2-api.utem.cl` (AWS API Gateway).
- **Auth:** header `Authorization: Bearer <JWT Keycloak>` en cada request. Detalle en `AUTH_FLOW.md`.
- **CORS:** `access-control-allow-origin: *`. **Formato:** `application/json`.

### `verifica_token` · `GET /usuarios/verifica-token`
- **Descripción:** perfil del usuario autenticado + perfil/roles/**permisos** (RBAC de la app).
- **Origen:** carga inicial post-login · **Acción:** resolver identidad y permisos del analista.
- **Parámetros:** ninguno (usa el bearer).
- **Respuesta (shape):** `{ id, username, nombre, email, rut, idPerfil, idUnidad, estado, alta,
  celular, idTipoContrato, fechaActualizacion, unidad:{id,nombre},
  perfil:{ id, nombre, roles:[ { id, nombre, estado, permisos:[ {id,nombre,nomenclatura,idModulo} ] } ] },
  carreras:[] }`
- **Sample:** `samples/usuarios_verifica-token.json` (PII anonimizada; roles/permisos íntegros).
- **Notas:** los roles de app NO están en el JWT; este endpoint es la fuente de permisos.
- **Capturado:** 2026-06-07

### `postulacion_totales` · `GET /convocatorias/postulacion/totales/{idUsuario}`
- **Descripción:** conteo de postulaciones por estado para el alcance del usuario (KPIs).
- **Origen:** dashboard INICIO · **Acción:** indicadores por estado.
- **Parámetros:** `idUsuario` (path) = `id` del usuario (de `verifica-token`; aquí 401).
- **Respuesta (shape):** `[ { id:<idEstado>, total:"<n>" } ]`.
- **Sample:** `samples/convocatorias_postulacion_totales.json`
- **Notas:** mapea idEstado→total. Ver "Mapa de estados" abajo.
- **Capturado:** 2026-06-07

## Mapa de módulos (de `verifica-token`, permisos `idModulo`)
| idModulo | Módulo | Nomenclaturas (acciones) |
|---|---|---|
| 1 | Ingresos y Postulaciones | IPOLIST, IPOVER, IPOCRE, IPOEDI, IPOFIN, IPOGBO, IPOCIN, GCONDES |
| 2 | Admisibilidad / Evaluación | AEVLIST, AEVADM, AEVPAP, AEVAPR |
| 3 | Planificación y Calendarización | PCALIST, PCAEDI, PCAVCA |
| 4 | Ejecución y Seguimiento | EJSLIST, EJSGES, EACEAC, IGESCI, IGESIR, EJSACCE, EJSGCSO, EJSPRSR, EJSRHIC, EJSRHCS |
| 5 | Cambio de Fase | CFLIST, IPRCES |
| 6 | Centro de Costo | ICCOLIST, ICCOSI |
| 7 | Gestionar Personas | GPELIST, GPEVER, GPECRE, GPEEDI |
| 8 | Gestionar Equipos | GEQLIST, GEQVIS, GEQASO |
| 9 | Solicitudes de Gasto | SSGLIST, SSGAPL, SSGMOD |
| 10 | Solicitudes RRHH / Informe gestión | SSRHLIST, SSRHAPL, SSRHMOD, INFGESTEDIT |
| 11 | Ajustes de Presupuesto | SSAPLIST, SSAPREA |
| 12 | Avance Global / Estadísticas | ESTAVGL |
| 13 | Convocatorias | GCONLIST, GCONCR, GCONED, GCONCO, GCONPU |
| 14 | Plantillas de Ingreso | GPLIST, GPLICR, GPLIED, GPLIDES |
| 15 | Fases de Proyecto | GCFLIST, GCFACR, GCFAED, GCFDES |
| 16 | Usuarios | GUSLIST, GUSCRE, GUSEDI, GUSDES, GUSAUA |
| 17 | Mantenedores (Unidades/Servicios/Roles/Perfiles/Trámites) | MANUNI, MANSER, MANROL, MANPER, MMTF |
| 24 | Postulaciones (transversal) | POSVERT, ADMIN, VESUUNI, DOCPOSI |
| 25 | Repositorios | REPDOCLIST, REPGEST, REPDOCGEST |

## Mapa de estados (idEstado) — CONFIRMADO vía catálogo `GET /convocatorias/estado/buscar`
`1`=Incompleta · `2`=Ingresada · `3`=Admisible · `4`=Pre-Aprobada · `5`=Agendar · `6`=Aprobada
· `7`=Rechazada · `8`=Ejecución · `9`=**No-Realizada** · `10`=Finalizado · `11`=Reformular.
_(El idEstado 9, antes incógnita, es "No-Realizada".)_ Cada `buscar`/`proyectos/listar` además
devuelve `nombreestado` por fila. **Sample:** `samples/convocatorias_estado_buscar.json`.

### `catalogo_estados` · `GET /convocatorias/estado/buscar`
- **Descripción:** catálogo maestro de estados de postulación `[ { id, nombre, orden } ]` (11 estados).
- **Origen:** cargado por la vista Cambio de Fase (filtro de estados). **Resource Fase 1:** `sisav2://catalogo/estados`.
- **Parámetros:** ninguno. **Sample:** `samples/convocatorias_estado_buscar.json` · Sin PII.
- **Capturado:** 2026-06-08

## 1. Núcleo de iniciativas

### Pregrado

#### `listar_postulaciones` · `GET /convocatorias/postulacion/buscar`
- **Descripción:** listado de postulaciones/ingresos paginado y filtrable.
- **Origen:** `/vcm-pregrado/postulaciones` · **Acción:** listar/filtrar/ordenar/paginar.
- **Parámetros (query):**
  | nombre | tipo | req | valores observados |
  |--------|------|-----|--------------------|
  | `modalidad` | string | sí | `PRE_GRADO` (rama; presumible `POST_GRADO`/`EXTENSION`) |
  | `idUsuario` | int | sí | `401` (id del usuario) |
  | `roles` | int[] (JSON) | sí | `[8,3,1,24]` (ids de roles del usuario) |
  | `estado` | int[] (JSON) | sí | `[3,10,1,2,7,11,8]` (idEstado a incluir) |
  | `ingreso` | bool | sí | `true` (vista Ingresos) |
  | `ordenamiento` | string | sí | `codigo_desc` (y variantes) |
  | `offset` | int | sí | `0` |
  | `limit` | int | sí | `10` (10/25/50/100) |
- **Respuesta (shape):** `{ postulaciones: [ { idpostulacion, nombrepostulacion, encargado|null,
  carreraformulario, facultadformulario, idconvocatoria, nombreconvocatoria, idestado,
  nombreestado, anioInicioConvocatoria, fecha(ISO) } ], total }`
- **Sample:** `samples/postulacion_buscar_pregrado.json`
- **Notas:** `total` para paginación. `content-type: application/x-www-form-urlencoded` en GET (inocuo).
- **Capturado:** 2026-06-07

#### `postulacion_totales` (por rama) · `GET /convocatorias/postulacion/totales/{idUsuario}?modalidad=PRE_GRADO`
- Igual shape que el del dashboard (`[{id:idEstado,total}]`) pero filtrado por `modalidad`.
- **Sample:** `samples/postulacion_totales_pregrado.json` · **Capturado:** 2026-06-07

#### Catálogos usados por los filtros (capturar shape en Paso 7)
`GET /convocatorias/listar-combo` (convocatorias) · `GET /mantenedores/listarCarrera` ·
`GET /mantenedores/listarFacultad`.

#### `obtener_detalle_iniciativa` · `GET /convocatorias/postulacion/obtener/{idPostulacion}`
- **Descripción:** postulación completa como **form-builder** (los 7 pasos = secciones).
- **Origen:** `/vcm-pregrado/gestionar-postulacion/{id}` · **Acción:** ver detalle de la iniciativa.
- **Parámetros:** `idPostulacion` (path).
- **Respuesta (shape):** `{ id, nombre, fecha, formulario:{ nombre, tipo, formulario:[
  { descripcion, posicion, tipo, eliminable, json:[ <campo> ] } ] } }`.
  Cada `<campo>`: `{ name, label, type, value, obligatorio, size, options?[{value,label,selected}],
  validations?, dependency?{name,value}, urlApi?(type=endpoint), isEditable?, limit? }`.
  Tipos de campo: `email | text | textarea | radio | checkbox | checkbox-dependent | endpoint | ...`.
- **Sample:** `samples/postulacion_obtener_3033.json` (recortado; ~138 KB en real).
- **Notas:** payload grande (incluye options de TODAS las carreras vía `dependency`). La Fase 1
  debe modelar secciones+campos genéricos, no campos fijos. `value` puede ser escalar o array (multiselect).
- **Capturado:** 2026-06-07

#### `obtener_fases_plantilla` · `GET /convocatorias/fases/obtener/{idFase}`
- **Descripción:** configuración de la **fase** de la convocatoria: qué rol evalúa hacia qué estado,
  plantillas (postulación/informe), calendarización y convocatorias asociadas.
- **Parámetros:** `idFase` (path, p. ej. `34`).
- **Respuesta (shape):** `{ id, nombre, activo, siempreVisible, rolEvalua,
  estadoPostulacion:[ { id, idFase, idEstado, idRol, rol:{id,nombre,estado}, estado:{id,nombre,orden} } ],
  plantillas:{ postulacion, informe }, calendarizacion:[ {id,estado,rol} ], convocatorias:[ {id,nombre,publicacion,estado} ], formulario }`.
- **Notas:** revela el workflow rol→estado (p. ej. Analista→Admisible, Aprobador→Aprobada). Sin PII.
- **Sample:** `samples/convocatorias_fases_obtener_34.json` · **Capturado:** 2026-06-08

#### `ver_bitacora` · `GET /convocatorias/postulacion/listar-cambios?offset=&limit=&idPostulacion={id}`
- **Descripción:** traza de cambios de estado/feedback de una postulación (la "Bitácora").
- **Origen:** botón **BITÁCORA** en `/vcm-pregrado/gestionar-postulacion/{id}` · **Acción:** ver historial.
- **Parámetros:** `idPostulacion` (query, requerido), `offset`, `limit` (def. 0/20).
- **Respuesta (shape):** `{ cambios:[ { estadoActual, estadoAnterior, fecha, idPostulacion,
  observacion, nombrePostulacion, nombreUsuario } ] }`.
- **Notas:** `nombreUsuario` = quien hizo el cambio (PII → anonimizar). `fecha` en formato JS Date string (no ISO).
- **Sample:** `samples/postulacion_listar-cambios_3033.json` · **Capturado:** 2026-06-08

#### `obtener_evaluacion_admisibilidad` — NO tiene endpoint propio (lectura)
- La vista **Evaluar** (`/vcm-pregrado/admisibilidad-evaluar/{id}`) reutiliza `GET .../postulacion/obtener/{id}`
  (detalle form-builder) + `GET .../fases/obtener/{idFase}` + catálogos. **No hay endpoint de lectura
  de "evaluación actual"** más allá del `idestado` de la postulación. La emisión del veredicto
  (Admisible/Reformular/Rechazar) sería **escritura (v2)**. → en Fase 1, `obtener_evaluacion_admisibilidad`
  colapsa en `obtener_detalle_iniciativa`.
- **Capturado:** 2026-06-08

#### `consultar_admisibilidad` · `GET /convocatorias/postulacion/buscar` (mismo endpoint)
- **CONFIRMADO:** Admisibilidad **reutiliza** `buscar` con `estado=[3,6,2,4]` (Admisible, Aprobada,
  Ingresada, Pre-Aprobada) e `ingreso=false` (vs `ingreso=true` en postulaciones) + `modalidad`.
- **Conclusión de diseño:** una sola tool `listar_postulaciones(rama, vista, filtros…)` cubre
  Postulaciones, Admisibilidad y (presumiblemente) Planificación/Ejecución/Cambio de Fase, variando
  `estado[]` + `ingreso`. Misma respuesta que `listar_postulaciones`.
- **Capturado:** 2026-06-07

#### Planificación / Cambio de Fase — REUTILIZAN `buscar` (CONFIRMADO)
- **Planificación y Calendarización** (`/vcm-pregrado/planificacion-calendarizacion`):
  `GET .../postulacion/buscar?estado=[5]&ingreso=false&ordenamiento=codigo_desc` (estado 5 = Agendar).
  Set de params **reducido** (sin `modalidad`/`idUsuario`/`roles`). Mismo shape que `listar_postulaciones`.
- **Cambio de Fase** (`/vcm-pregrado/cambio-fase`): `GET .../postulacion/buscar?estado=[3,5,6,8,10,1,2,4,7,11,9]`
  (los 11 estados) `&idUsuario=401&ingreso=false&roles=[8,3,1,24]&modalidad=PRE_GRADO`. Mismo shape.
  Carga además el catálogo `GET /convocatorias/estado/buscar`.
- **Conclusión:** `listar_postulaciones` parametrizada por `estado[]`+`ingreso`(+`modalidad`) cubre
  Postulaciones, Admisibilidad, Planificación y Cambio de Fase. No requiere samples extra (shape idéntico).

#### `listar_proyectos` (Ejecución y Seguimiento) · `GET /proyectos/listar` — ENDPOINT DISTINTO
- **Hallazgo:** Ejecución y Seguimiento **NO** usa `buscar`; usa el dominio `proyectos/`. Una postulación
  aprobada se materializa como **proyecto** con `id` propio (distinto de `idpostulacion`).
- **Origen:** `/vcm-pregrado/ejecucion-seguimiento`.
- **Parámetros (query):** `offset`, `limit`, `idUsuario` (401), `searchTerm` (str), `ordenamiento`
  (`codigo_desc`), `modalidad` (`PRE_GRADO`).
- **Respuesta (shape):** `{ data:[ { id (idProyecto), idpostulacion, nombrepostulacion, encargado,
  nombrefacultad, idconvocatoria, nombreconvocatoria, idestado, nombreestado, carreraformulario,
  facultadformulario } ], total }`. Estados observados: 8 (Ejecución) y 10 (Finalizado). `total`: 1299.
- **Notas:** clave raíz `data` (no `postulaciones`). `encargado` = PII → anonimizar.
- **Sample:** `samples/proyectos_listar_pregrado.json` · **Capturado:** 2026-06-08

#### `listar_repositorios` (módulo 25) · `GET /mantenedores/repositorios?vista=REPOSITORIO_VCM&roles={csv}`
- **Descripción:** repositorios documentales agrupados por categoría (Docencia, Extensión, I+D+i+e).
  Lista **grupos/carpetas** y su config (no los documentos en sí).
- **Origen:** `/vcm-pregrado/repositorios-vcm`. (También se dispara `GET /usuarios/roles/listar/si`.)
- **Parámetros (query):** `vista` = `REPOSITORIO_VCM`; `roles` = csv de roles (`8,3,1,24`).
- **Respuesta (shape):** `{ success, data:[ { categoria:{ id, nombre, bucket, path, vista, orden,
  icono, vigencia, fechaCreacion, fechaActualizacion }, repositorios:[ { id, nombre, descripcion,
  categoriaRepositorioId, esPublico, tiposArchivosPermitidos:[...], cantidadMaximaArchivos, orden,
  vigencia, fechaCreacion, fechaActualizacion, care_id, roles:[...] } ] } ] }`.
- **Notas:** config institucional, sin PII. Los **documentos dentro** de cada repositorio serían un
  endpoint más profundo (REPDOCLIST) — no capturado, prioridad menor para v1.
- **Sample:** `samples/mantenedores_repositorios.json` · **Capturado:** 2026-06-08

#### `exportar_postulaciones` · `POST /convocatorias/postulacion/exportar-excel`
- **Descripción:** genera un **XLSX** con las postulaciones de una convocatoria, **aplanando las
  respuestas del form-builder** en columnas dinámicas (la convocatoria define la estructura).
- **Origen:** botón **EXPORTAR** en `/vcm-pregrado/postulaciones`.
- **Request:** `content-type: application/json`, body `{ convocatoriaId (req), convocatoriaNombre,
  estado:[], modalidad, idUsuario, roles:[], esAdmin }`.
- **Respuesta (shape):** `{ url, total, nombreArchivo }` donde `url` es una **URL prefirmada de S3**
  al `.xlsx` (expira ~900s). Los datos NO vienen en el JSON; están en el binario XLSX.
- **Notas (Fase 1):** (1) es **POST de solo lectura** → requiere excepción a la regla GET-only del
  cliente. (2) Para exponer datos por chat habría que descargar+parsear el XLSX (openpyxl/pandas) →
  tool más pesada, candidata a **v2**; v1 puede devolver solo la URL de descarga. (3) El dato subyacente
  es reconstruible vía `buscar`(filtrado)+N×`obtener/{id}`, pero con N+1 llamadas y re-aplanado.
  (4) La URL prefirmada lleva credenciales → **no versionar** (redactada en el sample).
- **Sample:** `samples/postulacion_exportar-excel.json` (request+response, URL redactada) · **Capturado:** 2026-06-08

### Postgrado — CONFIRMADO reutiliza endpoints con `modalidad=POST_GRADO`
- `GET .../postulacion/buscar?...&modalidad=POST_GRADO` → mismo shape; `facultadformulario`="Escuela de Postgrado",
  carreras de postgrado (magísteres/doctorados). `total`: 22. **Sample:** `samples/postulacion_buscar_postgrado.json`.
- `GET .../postulacion/totales/401?modalidad=POST_GRADO` → mismo shape.

### Extensión — CONFIRMADO reutiliza endpoints con `modalidad=EXTENSION`
- `GET .../postulacion/buscar?...&modalidad=EXTENSION` → mismo shape. `total`: 1. **Sample:** `samples/postulacion_buscar_extension.json`.
- `GET .../postulacion/totales/401?modalidad=EXTENSION` → mismo shape.

## 2. Reportes — módulo `proyectos/estadisticas`

#### `avance_global_kpis` · `GET /proyectos/estadisticas/globales-proyectos`
- **Descripción:** las 5 KPI cards de Avance Global. **Origen:** `/reportes/avance-global`.
- **Parámetros:** ninguno observado (alcance por el usuario/token).
- **Respuesta (shape):** `{ totalProyectos, totalObjetivosEspecificos, totalHitos,
  totalActividades, totalPresupuesto }`.
- **Sample:** `samples/estadisticas_globales-proyectos.json` · **Capturado:** 2026-06-07

#### `avance_global_grid` · `GET /proyectos/estadisticas/proyectos?offset=&limit=` — 400 (DIFERIDO a Fase 1)
- **Descripción:** grilla agrupada de proyectos (objetivos/hitos/actividades/presupuesto) — paginada.
- **Estado: HTTP 400 confirmado.** El SPA dispara **exactamente** `?offset=0&limit=10` (sin más params)
  y recibe `400 {"message":"Ocurrió un error al intentar obtener la información"}`. **No es un param
  faltante** que el front olvide — el propio front falla. Como `/proyectos/listar` SÍ devuelve datos
  (1299 proyectos), se descarta "sin datos": es un **error server-side / feature posiblemente rota en
  prod** para este dataset/perfil. **Shape: indescubrible desde esta cuenta → DIFERIDO a Fase 1.**
  Mitigación: los KPIs (`globales-proyectos`) sí responden y cubren el reporte a nivel agregado.
- **Capturado (request+400):** 2026-06-08

## 3. Catálogos (Mantenedores / Configuración)

#### `catalogo_facultades` · `GET /mantenedores/listarFacultad`
- **Shape:** `[ { id, sigla, nombre, campus, direccion, telefono, idUnidad } ]` (sin PII).
- **Sample:** `samples/mantenedores_listarFacultad.json` · **Capturado:** 2026-06-07

#### `catalogo_carreras` · `GET /mantenedores/listarCarrera[?facultadId={id}]`
- **Descripción:** carreras; opcional filtro por `facultadId` (confirmado, p. ej. `?facultadId=7`).
- **Respuesta (shape):** `[ { id, nombre, codigo, facultadId|null } ]` (~56 carreras, sin PII;
  `facultadId` null en programas transversales/legacy). **Resource Fase 1:** `sisav2://catalogo/carreras`.
- **Sample:** `samples/mantenedores_listarCarrera.json` · **Capturado:** 2026-06-08

#### `catalogo_convocatorias` · `GET /convocatorias/listar-combo`
- **Shape:** `[ { id, nombre } ]` (~44 convocatorias, sin PII).
- **Sample:** `samples/convocatorias_listar-combo.json` · **Capturado:** 2026-06-07

#### `catalogo_estados` · `GET /convocatorias/estado/buscar`
- Ver ficha en "Mapa de estados" arriba. `[ {id, nombre, orden} ]` (11 estados). **Resource Fase 1:** `sisav2://catalogo/estados`.

#### `catalogo_roles` · `GET /usuarios/roles/listar/si`
- **Descripción:** catálogo de roles (cargado por Repositorios). **Shape:** _(pendiente leer cuerpo; patrón `{id, nombre, estado}`)_. **Capturado (URL):** 2026-06-08

#### Pendientes (catálogos de mantenedor — parciales, por decisión de alcance): plantillas (`mantenedor-plantillas`),
unidades, servicios, perfiles, centros de costos, usuarios (Mantenedores módulos 16–17). Endpoints
accesibles desde el menú MANTENEDORES; capturar en Fase 1 si se necesitan como Resources adicionales.

## Confirmación: parámetro de rama `modalidad`
Las 3 ramas comparten endpoints; el discriminador es **`modalidad`**:
`PRE_GRADO` (Pregrado) · `POST_GRADO` (Postgrado) · `EXTENSION` (Extensión). Confirmado en
`/postulacion/buscar` y `/postulacion/totales`.
