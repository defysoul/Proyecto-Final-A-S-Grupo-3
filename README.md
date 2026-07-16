# SISAV2 MCP — consultas reales y previews seguros para SISAV2 (VcM · UTEM)

Material del curso **INFB6093 — Procesamiento de Lenguaje Natural** (UTEM, Ing. Civil en Ciencia de
Datos). Es un **servidor MCP** funcional que conecta un asistente (Claude) con una API real, con
controles de seguridad explícitos.

El caso real: **SISAV2** es el sistema de **Vinculación con el Medio (VcM)** de la UTEM
(postulaciones e iniciativas académicas). Con este servidor, un analista (o un estudiante en un
entorno controlado) **consulta SISAV2 conversando con Claude**: lista y filtra iniciativas, ve el
detalle de una postulación (formulario de 7 pasos), lee su bitácora de cambios y obtiene indicadores
y KPIs, sin abrir la interfaz web. Además, la demo Fase 2 prepara previews de acciones de escritura
antes de aplicarlas.

> **Estado de demo:** las consultas usan SISAV2 con la identidad UTEM de cada usuario. Las tools de
> escritura son **dry-run por defecto**: validan, revisan permisos y devuelven el efecto previsto sin
> tocar SISAV2. Un commit opcional (`SISAV2_MOCK_WRITES=1`) aplica la intención contra un **mock en
> memoria** con read-back y auditoría; **SISAV2 real nunca se modifica**. Ver [SCOPE.md](SCOPE.md) para
> el contrato y los límites de la demo.

> **Control de release:** el corte actual es de **136 tests verdes** (85.31 % de cobertura). Para
> publicar una cifra, `uv run python -m pytest -q` debe reproducirla en el mismo corte.

---

## ¿Qué es un servidor MCP? (en 30 segundos)

**MCP (Model Context Protocol)** es un estándar abierto para darle **herramientas** y **datos** a un
modelo de lenguaje. Un *servidor MCP* expone:

- **Tools** — funciones que el modelo puede invocar (aquí: "listar postulaciones", "ver detalle"…).
- **Resources** — datos que el modelo puede leer (aquí: catálogos de convocatorias, carreras…).

El *cliente MCP* (Claude Desktop, Claude Code, etc.) arranca el servidor, descubre sus tools/resources
y deja que el modelo los use durante la conversación. Este repo es un servidor MCP escrito en Python
con [FastMCP](https://gofastmcp.com).

## ¿Qué se puede hacer en la demo?

Conversando con Claude, en lenguaje natural:

| Acción | Tool |
|---|---|
| Listar / filtrar iniciativas por modalidad y estado | `listar_postulaciones` (+ `listar_admisibilidad`, `listar_planificacion`, `listar_cambio_fase`) |
| Listar proyectos en ejecución/seguimiento | `listar_proyectos` |
| Ver el **detalle de 7 pasos** de una iniciativa | `obtener_detalle_iniciativa` |
| Ver la **bitácora** de cambios de estado | `ver_bitacora` |
| Ver repositorios documentales | `listar_repositorios` |
| **Indicadores** por estado y **KPIs** de Avance Global | `resumen_indicadores`, `avance_global` |
| Exportar postulaciones a Excel (devuelve enlace) | `exportar_postulaciones` |
| Consulta genérica a un endpoint permitido | `sisav2_consulta_generica` |
| Catálogos (convocatorias, carreras, facultades, estados, fases) | Resources `sisav2://catalogo/*` |
| Buscar iniciativas similares en la cohorte preparada | `buscar_iniciativas_similares` |
| Detectar candidatos a duplicado | `detectar_duplicados` |
| Ver ranking por ODS y facultad | `ranking_facultades_por_ods` |
| Preparar una creación, edición, evaluación o cambio de fase | `crear_postulacion`, `editar_postulacion`, `evaluar_admisibilidad`, `cambiar_fase` |
| Preparar un comentario, una postulación espejo o una carga de asistencia | `agregar_comentario_bitacora`, `crear_postulacion_espejo`, `cargar_asistencia` |

Las consultas y el análisis leen datos autorizados. Las siete tools de escritura describen una
**intención** y producen una vista previa. Por defecto su respuesta incluye `modo: "dry_run"`,
`aplicado: false`, `solicitud_mutante_enviada: false` y un `would_request` marcado como
`verificado: false`: un contrato de demostración, **no** evidencia de un endpoint real. Con el commit
opcional (mock) la respuesta pasa a `modo: "commit_mock"` con `read_back` y `sisav2_real_modificado: false`.

## Instalación rápida

En Windows, la opción más simple para la demo es el ejecutable portable `sisav2-mcp.exe`: se abre,
verifica la cuenta UTEM y registra el servidor local. La alternativa soportada para desarrollo y
respaldo es el entorno `uv`/`.venv`. Ambas rutas están explicadas en **[SETUP.md](SETUP.md)**.

Con el checkout del repositorio:

```bash
uv venv --python 3.11
uv pip install -e .
uv run python -m sisav2_mcp.onboarding   # guarda tu credencial UTEM en el keychain del SO
uv run sisav2-mcp index-demo --cohort <RUTA_LOCAL_COHORTE>
```

`index-demo` es el preflight de la demo: prepara/actualiza el índice local desde una cohorte local
autorizada y no realiza escrituras. Luego conéctalo a tu cliente MCP (Claude Code o Claude Desktop)
— ver [SETUP.md](SETUP.md) y la [guía de demo](docs/DEMO.md).

## Ejemplos de uso y resultados esperados

> Los datos mostrados son **ilustrativos/anonimizados** (nombres de personas reemplazados). Reflejan
> la **forma** real de la respuesta.

### 1. Listar iniciativas

**Pides:** *"Lista 5 postulaciones de pregrado"*
**Claude usa:** `listar_postulaciones(modalidad="PRE_GRADO", limit=5)`
**Devuelve:**

```json
{
  "total": 1427,
  "modalidad": "PRE_GRADO",
  "mostrando": 5,
  "postulaciones": [
    { "idpostulacion": 3014, "nombre": "Seminario de Introducción a la Ing. Civil Biomédica",
      "carrera": "Ingeniería Civil en Ciencia de Datos", "facultad": "Facultad de Ingeniería",
      "estado": { "id": 2, "nombre": "Ingresada" },
      "encargado": "Académico/a responsable", "anio": 2026 }
  ]
}
```

### 2. Detalle de una iniciativa (formulario de 7 pasos)

**Pides:** *"Dame el detalle de la iniciativa 3014"*
**Claude usa:** `obtener_detalle_iniciativa(id_postulacion=3014)`
**Devuelve** (resumido): los 7 pasos del formulario con sus campos —

```
Paso 1 · Identificación: responsable, facultad, carrera, objetivos, dominio disciplinar…
Paso 2 · Marco formativo: ciclo, competencias, logros de aprendizaje…
Paso 3 · Asignatura: cátedra asociada (p. ej. INFB6012) + programa adjunto
Paso 4 · Actividades: lista de actividades (lugar, fecha)
Paso 5 · Participación esperada: estudiantes, docentes, contraparte…
Paso 6 · Requerimientos
Paso 7 · Documentos: cartas y anexos
```

### 3. Bitácora de cambios

**Pides:** *"Muéstrame la bitácora de la postulación 3033"*
**Claude usa:** `ver_bitacora(id_postulacion=3033)`
**Devuelve:**

```json
{ "idPostulacion": 3033,
  "cambios": [
    { "estadoAnterior": "Ingresada", "estadoActual": "Reformular",
      "fecha": "Wed Jun 03 2026 15:34:29 GMT+0000 (...)",
      "observacion": "Cambio de Fase", "nombreUsuario": "Analista VcM" }
  ] }
```

(Una iniciativa recién ingresada devuelve `"cambios": []` — aún sin historial.)

### 4. Indicadores y KPIs

**Pides:** *"Dame el resumen de indicadores y el avance global"*
**Claude usa:** `resumen_indicadores()` + `avance_global()`
**Devuelve:** conteo de iniciativas por estado (Incompleta, Ingresada, Admisible… Finalizado) con su
total, y los KPIs de Avance Global (`totalProyectos`, `totalActividades`, `totalPresupuesto`, …).

## Arquitectura (capas aisladas y testeables)

```
src/sisav2_mcp/
  auth/        # OIDC ROPC + credencial en el keychain del SO (interfaz TokenProvider)
  client/      # cliente httpx: lecturas permitidas, errores tipados y reintentos
  models/      # modelos pydantic derivados de respuestas reales (fixtures "golden")
  tools/       # consulta, reportes, análisis y previews dry-run de intención
  resources/   # catálogos con caché TTL
  server.py    # arma el FastMCP y registra todo
  onboarding.py# CLI para guardar la credencial
  app.py       # ejecutable: GUI de setup, servidor stdio e index-demo
```

Diseño, plan paso a paso y notas de descubrimiento de la API: carpeta [`docs/`](docs/).

## Seguridad y privacidad

- **Escritura sin efectos sobre SISAV2 real.** Por defecto las tools de intención son dry-run. El
  commit opcional (`SISAV2_MOCK_WRITES=1` + `confirmar`) aplica sólo contra un **mock en memoria** —sin
  cliente HTTP—, de modo que ningún `POST`, `PUT`, `PATCH` ni `DELETE` mutante llega a SISAV2. El único
  POST histórico permitido contra la API real es la generación de un enlace de exportación.
- **Contrato aún no verificado.** Los endpoints y cuerpos que aparecen en `would_request` son
  hipótesis de integración para la futura validación supervisada; no se presentan como contratos de
  la API real.
- **Identidad por usuario.** Cada quien usa **su** cuenta UTEM → se respetan sus permisos. La clave
  se guarda **cifrada en el keychain del sistema operativo**, nunca en texto plano ni en el repo.
- **Sin datos sensibles versionados.** No hay tokens, credenciales ni datos personales reales en
  este repositorio; los ejemplos en `docs/discovery/samples/` están **anonimizados**.

## Documentación

- **[SETUP.md](SETUP.md)** — instalación, onboarding y conexión a Claude (paso a paso).
- **[SCOPE.md](SCOPE.md)** — specs, alcance, qué se puede hacer hoy, limitaciones y pendientes.
- **[docs/DEMO.md](docs/DEMO.md)** — preflight conectado y prompts seguros para la demostración.
- **[docs/arquitectura-multi-usuario.md](docs/arquitectura-multi-usuario.md)** — evolución segura a
  una integración multiusuario autorizada.
- **[build/BUILD.md](build/BUILD.md)** — construcción y verificación del instalador portable.
- **[docs/](docs/)** — diseño (specs), plan de implementación y descubrimiento de la API (Fase 0).

## Licencia

MIT. Material educativo del curso INFB6093 (UTEM).
