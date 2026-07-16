# Bitácora del descubrimiento — Fase 0

> Qué se exploró, qué quedó incierto, supuestos a validar en la Fase 1.
> Fecha de inicio: 2026-06-07.

## Hipótesis a validar
- [x] **Las 3 ramas comparten endpoints** → CONFIRMADO: discriminador `modalidad` ∈
      {`PRE_GRADO`, `POST_GRADO`, `EXTENSION`}, verificado en `/postulacion/buscar` y
      `/postulacion/totales` para las 3 ramas.
- [x] **Grant de auth** → la SPA usa **Authorization Code + PKCE (S256)**, cliente público
      `SISAV2`, realm `prod`. El realm también soporta `password`. Ver `AUTH_FLOW.md`. (Caveat
      redirect loopback a validar en Fase 1.)
- [x] **Detalle del wizard** → **un único payload** `GET /postulacion/obtener/{id}` con
      `formulario.formulario[]` = secciones (los pasos); NO una llamada por paso.
- [x] **Un solo endpoint de listado** sirve varias vistas (Postulaciones/Admisibilidad…) variando
      `estado[]` + `ingreso`. → `listar_postulaciones` parametrizada.

## Hallazgos clave (sesión 2026-06-07)
- **Base API:** `https://sisav2-api.utem.cl` (AWS API Gateway, CORS `*`).
- **Auth:** `Authorization: Bearer <JWT RS256>`, vida ~10 min (`exp-iat=600`). Roles de app NO
  en el JWT → vía `GET /usuarios/verifica-token` (devuelve perfil + mapa de módulos/permisos).
- **Cuenta usada:** perfil **Administrador** (ve todo) — ideal para descubrir.
- **Avance Global grilla** (`/proyectos/estadisticas/proyectos`) → **HTTP 400** para esta cuenta
  (sin datos), igual que notó el clon. KPIs (`globales-proyectos`) sí responden.

## Hallazgos clave (sesión 2026-06-08) — cierre del núcleo + reportes
- **idEstado resuelto** vía catálogo `GET /convocatorias/estado/buscar`: `9` = **No-Realizada**
  (era la incógnita). Mapa completo confirmado (1=Incompleta … 11=Reformular).
- **Bitácora** = `GET /convocatorias/postulacion/listar-cambios?idPostulacion=&offset=&limit=` →
  `{cambios:[{estadoActual, estadoAnterior, fecha, observacion, nombrePostulacion, nombreUsuario}]}`.
- **Evaluar admisibilidad** NO tiene endpoint de lectura propio: reutiliza `obtener/{id}` + `fases/obtener/{idFase}`.
  El veredicto (Admisible/Reformular/Rechazar) es escritura (v2).
- **Planificación** = `buscar?estado=[5]&ingreso=false` (estado 5 = Agendar). **Cambio de Fase** =
  `buscar?estado=[todos]&ingreso=false`. Ambas reutilizan `buscar` (shape idéntico).
- **Ejecución y Seguimiento** = endpoint **distinto** `GET /proyectos/listar` (dominio `proyectos/`,
  clave raíz `data`, `id` de proyecto ≠ `idpostulacion`; estados 8/10). → tool propia `listar_proyectos`.
- **Repositorios** (módulo 25) = `GET /mantenedores/repositorios?vista=REPOSITORIO_VCM&roles={csv}`
  (grupos/carpetas por categoría; sin PII). Documentos dentro del repo = endpoint más profundo, no capturado.
- **Exportar a Excel** = `POST /convocatorias/postulacion/exportar-excel` (body JSON) → devuelve
  **URL prefirmada de S3** a un XLSX (no datos JSON). POST de solo lectura. Datos reconstruibles vía
  `buscar`+N×`obtener/{id}` pero con N+1 llamadas + re-aplanado. Tool `exportar_postulaciones`: v1 (URL) / v2 (parseo XLSX).
- **fases/obtener/{id}** y **listarCarrera** shapes capturados (catálogos para Resources).
- **Postgrado/Extensión** CONFIRMADOS: mismos endpoints con `modalidad=POST_GRADO`/`EXTENSION`, shape idéntico.

## Pendientes / diferidos a Fase 1
- **Avance Global grilla** (`/proyectos/estadisticas/proyectos`): **400 server-side** ante la request
  exacta del SPA (`?offset=0&limit=10`), no es param faltante. Como `/proyectos/listar` sí trae datos
  (1299), se descarta "sin datos" → feature posiblemente rota en prod / error de backend. Shape pendiente.
  Mitigación: KPIs (`globales-proyectos`) sí responden.
- **Catálogos de mantenedor** (parciales por decisión de alcance): plantillas, unidades, servicios,
  perfiles, centros-costo, usuarios; y `usuarios/roles/listar/si` (shape no leído). Capturar en Fase 1 si se necesitan.
- **Documentos dentro de un repositorio** (REPDOCLIST): endpoint no capturado, prioridad menor.

## Supuestos que la Fase 1 debe reconciliar (entran en RECONCILIATION.md)
1. **Auth:** Authorization Code + PKCE (S256) cliente `SISAV2` realm `prod`. **Caveat loopback:** el
   `redirect_uri` registrado admite rutas variables bajo `https://sisav2.utem.cl/*` (observado:
   `.../vcm-pregrado/postulaciones`), pero **NO se confirmó** que admita `http://localhost:<port>`.
   Validar antes de implementar PKCE local; si no, fallback a `password` grant. JWT vida ~10 min
   (refrescar de forma transparente; la SPA re-hace el code-flow en cada navegación).
2. **No todo es `buscar`:** Ejecución usa `proyectos/listar`; modelar `Proyecto` (con `id`+`idpostulacion`)
   aparte de `Postulacion`. Avance Global vive en el dominio `proyectos/estadisticas`.
3. **Export = POST de lectura:** romper la regla GET-only del cliente con una allowlist explícita.
4. **idEstado y rama** son enums confirmados (catálogo de estados + `modalidad`).
