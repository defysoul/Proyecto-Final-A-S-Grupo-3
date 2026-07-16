# Spec — Fase 0: Descubrimiento de la API de SISAV2

- **Proyecto:** MCP Server SISAV2 (UTEM · Vinculación con el Medio)
- **Fase:** 0 de 2 — Descubrimiento de API y Capacidades
- **Fecha:** 2026-06-07
- **Estado:** Diseño aprobado (pendiente de plan de implementación)
- **Spec siguiente (encadenado):** `2026-06-07-sisav2-mcp-fase1-servidor-readonly-design.md`

---

## 1. Contexto y objetivo

SISAV2 (`https://sisav2.utem.cl`) es el *Sistema de Ingreso y Seguimiento de Actividades de
Vinculación con el Medio* de la UTEM: una SPA Angular + Kendo con autenticación Keycloak (SSO
en `sso.utem.cl`). El equipo de analistas de Vinculación con el Medio (VcM) hace hoy, **de
forma manual** en la UI, el seguimiento, análisis y feedback de las iniciativas que postulan
los docentes.

El objetivo del proyecto global es un **MVP / prueba de concepto** que demuestre que ese
trabajo puede hacerse **por chat con Claude**, vía un MCP server. Es una **demo** para que
algunos analistas la prueben, como insumo para la continuación del proyecto el próximo
semestre (hacia **SISAV3** como producto final, donde el MCP quedaría integrado de forma
nativa). Hay **autorización del cliente** para construir y probar este MVP.

Existe un **clon visual** del frontend en un repo aparte `sisav2-clone` (Next.js, solo UI,
datos mock). El clon documentó a fondo el **frontend** (DOM, CSS, comportamientos y el modelo
de dominio), pero **no** la **API REST del backend**: no hay endpoints, ni shapes de
request/response, ni el flujo de tokens de Keycloak documentados. **Esa capa es lo que esta
Fase 0 debe descubrir.**

**Objetivo de la Fase 0:** producir un **Inventario de Capacidades y API** de SISAV2 — el mapa
"acción del analista → endpoint → datos" — con calidad suficiente para que la Fase 1 (el MCP
server de solo lectura) se construya sobre él sin tener que volver a investigar.

## 2. Alcance

### En alcance (descubrir y documentar)
Cobertura **de todo el sistema** (decisión de diseño), capturando para cada vista las llamadas
de red a la API:

1. **Núcleo de iniciativas** (3 ramas: Pregrado, Postgrado, Extensión — estructura idéntica):
   - Postulaciones / Ingresos (listado + indicadores por estado + filtros + paginación).
   - Detalle de iniciativa (wizard de 7 pasos: Descripción, Instrumento VCM, Cátedras,
     Actividades, Participantes, Requerimientos, Documentos).
   - Bitácora (traza de cambios de estado / feedback).
   - Admisibilidad (listado + vista de evaluación).
   - Planificación y Calendarización, Ejecución y Seguimiento, Cambio de Fase, Repositorios.
2. **Reportes:** Avance Global (KPIs + grilla agrupada: proyectos/objetivos/hitos/actividades/
   presupuesto).
3. **Catálogos (Mantenedores y Configuración):** convocatorias, fases de proyecto, plantillas
   de ingreso, unidades, servicios, roles, perfiles, centros de costos, usuarios.
4. **Autenticación:** flujo OIDC/Keycloak completo (ver §5).

### Fuera de alcance
- **No** se implementa el MCP server (eso es la Fase 1).
- **No** se descubren ni documentan endpoints de **escritura** más allá de registrar su
  existencia (método + ruta) cuando aparezcan de forma incidental; v1 es solo lectura. No se
  ejecuta ninguna acción de escritura durante el recon.
- **No** se modifica dato alguno en el sistema real.

## 3. Método de descubrimiento

Recon **autenticado** sobre el sitio en vivo, con una **cuenta de analista real** (identidad
propia, autorizada), en una sesión controlada:

1. **Herramienta:** Chrome DevTools MCP (preferente) y/o Playwright, contra `sisav2.utem.cl`.
   El analista inicia sesión manualmente; el recon observa el tráfico ya autenticado.
2. **Por cada vista** del §2: recorrer la vista, registrar el panel de red (XHR/fetch),
   y para cada request a la API capturar:
   - URL completa + método HTTP.
   - Query params y/o cuerpo de la request (filtros, paginación, orden).
   - Headers relevantes (auth, content-type) — el bearer **redactado**.
   - Código de respuesta y **shape del cuerpo de respuesta** (estructura de campos, tipos,
     anidamiento, forma de la paginación: total/página/tamaño).
3. **Acciones de UI a ejercitar** (read-only): buscar, filtrar (estado/convocatoria/facultad/
   carrera/año), ordenar, paginar, abrir detalle, expandir filas, cambiar de pestaña del
   wizard, abrir bitácora. Cada interacción mapea a una o más llamadas a la API.
4. **Muestreo:** guardar 1–3 respuestas de ejemplo por endpoint, **sanitizadas** (ver §7), como
   fixtures para la Fase 1.

## 4. Entregables (artefactos)

Todos en el repo `sisav2-mcp`, bajo `docs/discovery/`:

1. **`API_INVENTORY.md`** — una entrada por endpoint, con esta estructura mínima por cada uno:
   - `nombre lógico` (p. ej. `listar_postulaciones`), `método`, `ruta` (con plantilla de
     params: `/api/.../{rama}/postulaciones?estado=&page=`), `descripción`.
   - **Parámetros:** nombre, tipo, requerido/opcional, valores válidos observados.
   - **Respuesta:** árbol de campos con tipos y ejemplo abreviado; forma de la paginación.
   - **Vista/origen** del frontend donde se observó y **acción del analista** que cubre.
   - Notas (rate limits observados, errores, peculiaridades de Kendo en params de grilla).
2. **`AUTH_FLOW.md`** — el flujo OIDC/Keycloak documentado (ver §5).
3. **`ACTION_CATALOG.md`** — tabla "acción del analista → endpoint(s) → tool propuesta para la
   Fase 1 → tipo (lectura/escritura) → estado (cubierto v1 / diferido v2)". Es el puente
   explícito hacia el Spec 2.
4. **`samples/`** — payloads de respuesta de ejemplo, **sanitizados**, nombrados por endpoint
   (`listar_postulaciones_pregrado.json`, `detalle_iniciativa_3033.json`, …). Serán los
   *fixtures golden* de los tests de la Fase 1.
5. **`DISCOVERY_NOTES.md`** — bitácora del recon: qué se exploró, qué quedó incierto, vistas sin
   datos en la cuenta usada, y supuestos a validar en la Fase 1.

## 5. Descubrimiento de autenticación (OIDC/Keycloak)

Documentar en `AUTH_FLOW.md`:
- El documento de descubrimiento OIDC: `https://sso.utem.cl/.../.well-known/openid-configuration`
  (authorization_endpoint, token_endpoint, issuer, scopes, grant types soportados).
- `client_id` que usa la SPA, tipo de cliente (público/confidencial), si admite **PKCE**.
- Forma del **access token** (JWT: claims de roles/perfil, expiración) y del **refresh token**.
- Cómo se adjunta el token a las llamadas a la API (header `Authorization: Bearer`).
- **Determinación clave para la Fase 1:** qué grant type es viable para un cliente local sin
  intervención de TI — **Authorization Code + PKCE** (preferido) o **password grant**
  (fallback). Esta conclusión condiciona la implementación de `auth/` en la Fase 1.

## 6. Priorización (orden del recon)

1. **Núcleo de iniciativas, rama Pregrado** (mayor volumen y uso): listado, detalle 7 pasos,
   bitácora, admisibilidad. Es el camino crítico.
2. Resto del núcleo Pregrado (planificación, ejecución, cambio de fase, repositorios).
3. **Auth** documentado en paralelo desde el primer login.
4. **Reportes** (Avance Global).
5. **Postgrado y Extensión** (validar que reusan los mismos endpoints con distinto parámetro de
   rama — hipótesis del clon).
6. **Catálogos** (Mantenedores/Configuración).

Si el tiempo aprieta, los catálogos pueden quedar como inventario parcial sin samples completos
(se anota en `DISCOVERY_NOTES.md`); el núcleo + auth + reportes es el mínimo no negociable.

## 7. PII y seguridad

- **Sanitizar** todos los samples: anonimizar nombres, RUTs, correos de personas (igual que
  hizo el clon); conservar nombres institucionales (unidades, carreras, convocatorias).
- **Nunca** commitear tokens, cookies de sesión ni credenciales. El bearer va **redactado** en
  toda documentación.
- `.gitignore` excluye capturas crudas (HAR completos, screenshots con PII) — solo entran al
  repo los artefactos sanitizados.

## 8. Criterios de éxito (Definition of Done)

- `API_INVENTORY.md` cubre **todos** los endpoints del núcleo de iniciativas (3 ramas) y de
  Reportes, con params y shape de respuesta; catálogos cubiertos al menos a nivel de
  endpoint+params (samples opcionales).
- `AUTH_FLOW.md` concluye **qué grant type usará la Fase 1** (PKCE o password), con evidencia.
- `ACTION_CATALOG.md` mapea cada acción de analista de v1 a endpoint(s) concretos y marca qué
  queda diferido a v2.
- Hay al menos un `sample` sanitizado por cada endpoint del núcleo y de Reportes.
- Un revisor puede, leyendo solo `docs/discovery/`, entender qué llamadas haría la Fase 1 sin
  volver a tocar el sitio en vivo.

## 9. Riesgos y mitigaciones

- **La API interna puede cambiar sin aviso** → el inventario incluye fecha de captura; la Fase 1
  añade validación tolerante y una compuerta de reconciliación.
- **Vistas sin datos en la cuenta usada** (p. ej. Admisibilidad/Avance Global vacíos para
  ciertos perfiles, como notó el clon) → se documenta el endpoint igual, con sample vacío y nota;
  se intenta con una cuenta/period con datos si está disponible.
- **Keycloak podría no permitir PKCE en cliente público** → por eso §5 obliga a concluir el
  grant viable; condiciona la Fase 1.
- **Params de grilla Kendo** pueden ser verbosos/idiosincráticos (filtro/orden serializados) →
  documentar el formato exacto observado.

## 10. Encadenamiento con la Fase 1

Los artefactos de `docs/discovery/` son **entrada obligatoria** del Spec 2. El Spec 2 abre con
una **compuerta de reconciliación**: contrastar la superficie de tools/modelos/auth diseñada
contra lo que esta Fase 0 encontró, y ajustar el diseño donde la realidad difiera, **antes** de
implementar. Si la Fase 0 revela algo que invalida un supuesto del Spec 2 (p. ej. las 3 ramas
no comparten endpoints, o no hay grant viable sin TI), se actualiza el Spec 2 antes de planificar
su implementación.
