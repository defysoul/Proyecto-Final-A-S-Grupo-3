# SCOPE — alcance de la demo segura SISAV2 MCP

Este documento define exactamente qué demuestra esta versión y qué no. Para el diseño de la base
read-only y el descubrimiento de API, ver [`docs/superpowers/specs/`](docs/superpowers/specs/) y
[`docs/discovery/`](docs/discovery/).

## 1. Objetivo

`sisav2-mcp` conecta un cliente MCP local con SISAV2 para que un analista consulte datos autorizados
en lenguaje natural. La Fase 2 añade dos capacidades para una **demo conectada y segura**:

- análisis sobre una cohorte local autorizada y saneada; y
- previews de intenciones de escritura a nivel de tarea del analista.

La segunda capacidad **no escribe** en SISAV2. Su objetivo es hacer visible el contrato, las
validaciones, el permiso requerido y el diff que una futura integración autorizada tendría que
revisar.

## 2. Superficie de la demo

### Consultas conectadas

Las 13 tools de la Fase 1 y los 5 resources siguen siendo la superficie conectada a SISAV2:
listados, detalle de siete pasos, bitácora, repositorios, indicadores, KPIs, exportación a enlace y
catálogos. Se autentican con la cuenta UTEM del usuario y respetan el alcance de esa identidad.

### Análisis local con datos autorizados

| Tool | Resultado |
|---|---|
| `buscar_iniciativas_similares` | Iniciativas de la cohorte ordenadas por similitud semántica. |
| `detectar_duplicados` | Pares o grupos candidatos a revisión humana; no dicta una decisión. |
| `ranking_facultades_por_ods` | Resumen agregado de la cohorte por facultad y ODS. |

El índice se genera antes de la demo con `sisav2-mcp index-demo --cohort <RUTA_LOCAL_COHORTE>`. Usa
de forma perezosa `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; el primer preflight
puede descargar/cargar ese modelo. La cohorte y la caché son locales, no se versionan y deben excluir
RUT, correos, nombres y otros datos personales. La preparación debe indicar claramente si no puede
construir el índice.

### Previews de escritura (*dry-run*)

| Tool | Intención que previsualiza |
|---|---|
| `crear_postulacion` | Crear una postulación. |
| `editar_postulacion` | Modificar campos de una postulación. |
| `evaluar_admisibilidad` | Emitir un veredicto de admisibilidad. |
| `cambiar_fase` | Proponer un cambio de fase/estado. |
| `agregar_comentario_bitacora` | Agregar un comentario de bitácora. |
| `crear_postulacion_espejo` | Preparar una copia adaptada a otra carrera/convocatoria. |
| `cargar_asistencia` | Preparar una carga de asistentes. |

Todas devuelven una estructura de preview con `permiso`, `validaciones`, `advertencias`, `diff`,
`efecto_previsto` y un contrato hipotético. Sus invariantes son:

```json
{
  "modo": "dry_run",
  "aplicado": false,
  "solicitud_mutante_enviada": false,
  "would_request": { "verificado": false }
}
```

`would_request` es una representación hipotética de la futura integración, no un endpoint descubierto
ni una solicitud enviada. Las validaciones y el RBAC ayudan a mostrar qué se revisaría; no conceden
autorización de escritura remota.

### Commit contra backend simulado (opcional, `SISAV2_MOCK_WRITES=1`)

Para demostrar el patrón completo *dry-run → commit* sin tocar SISAV2 real, existe un modo opt-in.
Con `SISAV2_MOCK_WRITES=1`, las tools de escritura aceptan `confirmar=True` y aplican la intención
contra un **backend SIMULADO en memoria** (`MockSisav2Backend`), devolviendo un `CommitResult` con
`aplicado: true`, `backend: "mock"`, `sisav2_real_modificado: false` y un **read-back** del efecto.
Cada commit deja una línea de auditoría JSONL (actor pseudonimizado, operación, `request_id`, sello
temporal). El simulador **no tiene cliente HTTP**: por construcción, un commit jamás llega a SISAV2.

## 3. Invariantes de seguridad

- Por defecto las tools son dry-run (`aplicado: false`). El único camino de `commit`/`confirmar`
  aplica contra el backend **mock en memoria** (`SISAV2_MOCK_WRITES=1`); no existe ninguna ruta de
  código que mute SISAV2 real.
- Las tools de preview no emiten `POST`, `PUT`, `PATCH` ni `DELETE` mutantes contra SISAV2. El único
  POST histórico permitido corresponde a la exportación que devuelve un enlace, no a una modificación.
  El cliente HTTP conserva su allowlist read-only como defensa en profundidad.
- Si falta red, autenticación, permiso, cohorte o índice, el preflight o la tool falla de forma clara;
  **no** usa un fallback offline para aparentar una demo conectada.
- La validación de contratos de escritura contra SISAV2 queda fuera de esta versión. Requiere
  autorización institucional, endpoints capturados bajo supervisión y una revisión de seguridad.

## 4. Instalación y demostración

En Windows hay dos rutas respaldadas:

1. **Portable:** `sisav2-mcp.exe` abre la GUI, verifica la credencial UTEM y registra el servidor en
   clientes locales compatibles. Se distribuye como artefacto de release; su fuente y cómo construirlo
   están en [`build/BUILD.md`](build/BUILD.md).
2. **Entorno de desarrollo/respaldo:** checkout + Python 3.11 + `uv` + `.venv`; la configuración del
   cliente MCP apunta al intérprete del entorno y a `-m sisav2_mcp.server`.

Antes de mostrar Claude Desktop, se ejecuta el preflight conectado: verificar credencial, ejecutar
`index-demo` sobre la cohorte local autorizada y realizar una consulta de lectura real. La secuencia
y los prompts están en [`docs/DEMO.md`](docs/DEMO.md).

## 5. Verificación de release

- Ejecutar `uv run ruff check .`, `uv run mypy src` y `uv run python -m pytest -q` desde el checkout.
- El texto **“90 tests verdes”** solo puede usarse si esa ejecución concreta muestra 90 pruebas
  aprobadas. Para la Fase 2 debe publicarse la cifra real de la suite resultante, nunca reutilizar un
  número histórico sin verificar.
- Ensayar la demo en Claude Desktop usando el preflight conectado y al menos una consulta, una tool
  de análisis y una preview de escritura. Confirmar en pantalla `aplicado: false` y
  `solicitud_mutante_enviada: false`.

## 6. Próxima etapa, deliberadamente fuera de alcance

La escritura real solo podrá considerarse tras recon supervisado de contratos, autorización explícita,
un modelo de aprobación y auditoría. La arquitectura propuesta para ese salto —sesión por usuario,
PKCE para un servicio remoto, roles y trazabilidad— está en
[`docs/arquitectura-multi-usuario.md`](docs/arquitectura-multi-usuario.md). No forma parte de la demo
actual.
