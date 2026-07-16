# Informe técnico — MCP SISAV2 (Grupo 2)

**Curso:** INFB6093 Procesamiento de Lenguaje Natural · UTEM 2026-I
**Equipo:** Welinton Barrera (jefe) · Joaquín Araya · Felipe Martínez · Benjamín Zamorano
**Socio comunitario:** Dirección de Vinculación con el Medio (VcM), UTEM
**Repositorio:** `github.com/utem-ia-biomedical-nlp/sisav2-mcp` · Fase 2

> Uso de IA declarado: el desarrollo y la redacción se apoyaron en asistentes LLM (Claude). Las
> decisiones de diseño, la verificación de la suite y la comprensión del sistema son del equipo.

---

## 1. Introducción

SISAV2 es el sistema con que la Dirección de VcM de la UTEM gestiona el ciclo de las iniciativas de
vinculación (postulación, admisibilidad, planificación, ejecución y seguimiento). Hoy los analistas lo
operan por **navegación manual**: abrir el sistema, filtrar, buscar y exportar a Excel para agregar
resultados a mano. Preguntas cotidianas —"¿cuántas iniciativas de pregrado están en admisibilidad?",
"resúmeme la iniciativa 3033 y su bitácora", "¿qué iniciativas se parecen a esta?"— exigen múltiples
pasos y trabajo repetitivo.

El docente entregó una **Fase 1** de `sisav2-mcp`: un servidor [MCP](https://modelcontextprotocol.io)
(Model Context Protocol) que expone SISAV2 a un LLM (Claude Desktop) en **solo lectura**. Este trabajo
es la **Fase 2**: evolucionar ese servidor hacia una herramienta utilizable por analistas reales,
sumando (i) **tools de escritura** con un modelo de seguridad explícito, (ii) **tools de análisis
semántico**, y (iii) el **diseño multi-usuario** para distribuirlo. El objetivo del contexto A+S es
dejar algo que VcM pueda usar y sobre lo cual levantar los requerimientos del próximo semestre.

## 2. Trabajo relacionado

- **MCP (Model Context Protocol).** Protocolo cliente-servidor que estandariza cómo un LLM accede a
  *tools*, *resources* y *prompts* de un sistema externo. El servidor declara herramientas con esquema
  tipado; el cliente (Claude Desktop) decide cuándo invocarlas. Resuelve el problema de dar al modelo
  acceso a datos frescos y acciones sin *hardcodear* integraciones en el prompt.
- **Tool use / function calling y patrón ReAct** (Yao et al., 2023, *ReAct: Synergizing Reasoning and
  Acting in Language Models*). El LLM alterna *razonar* y *actuar* (llamar una tool, observar el
  resultado, continuar). En nuestra arquitectura el bucle ReAct lo ejecuta el **cliente** (Claude
  Desktop); el servidor MCP sólo expone herramientas — ver §5 la justificación de por qué no usamos un
  orquestador adicional (LangGraph).
- **Búsqueda semántica con embeddings** (Reimers & Gurevych, 2019, *Sentence-BERT*). Representamos el
  objetivo/descripción de cada iniciativa como un vector denso multilingüe y medimos cercanía por
  **similitud coseno**, que captura relación de significado más allá de la coincidencia de palabras.
- **Structured output con Pydantic v2.** Validar entradas y salidas con modelos tipados reduce errores
  y "alucinaciones estructurales": el modelo no puede inventar campos fuera del esquema, y los datos
  que devuelve la tool provienen de SISAV2, no del LLM.
- **RBAC.** El control de acceso basado en roles/permisos de SISAV2 se replica localmente antes de
  cualquier intención de escritura.

## 3. Método (arquitectura, decisiones, stack)

**Stack.** FastMCP (SDK de MCP en Python), `httpx` (HTTP async), Pydantic v2 (validación),
`sentence-transformers` con el modelo `paraphrase-multilingual-MiniLM-L12-v2` (embeddings multilingües),
`keyring` (credencial en el Windows Credential Manager). Cliente LLM: Claude Desktop (principal) y
Claude Code / Codex (secundarios).

**Superficie de tools.** 20 en el ejecutable liviano / 23 en el entorno de desarrollo:

| Capa | Tools |
|---|---|
| **Lectura (Fase 1)** | 12 de consulta + `consultar_catalogo` + 5 *resources* de catálogos con caché. |
| **Escritura (Foco 2)** | 7: `crear_postulacion`, `editar_postulacion`, `evaluar_admisibilidad`, `cambiar_fase`, `agregar_comentario_bitacora`, `crear_postulacion_espejo`, `cargar_asistencia`. |
| **Análisis (Foco 3)** | 3: `buscar_iniciativas_similares`, `detectar_duplicados`, `ranking_facultades_por_ods`. |

**Autenticación.** Cada analista se autentica con su cuenta UTEM (grant ROPC contra Keycloak); el token
se cachea y se renueva (refresh + re-login silencioso) respetando expiración (`auth/ropc.py`). La
clave nunca se guarda en texto: vive cifrada en el keychain del SO. Las consultas respetan el alcance
(permisos) de esa identidad.

**Modelo de seguridad de escritura (contribución central).** Las tools de escritura no exponen un CRUD
ciego. Cada una:

1. Valida la entrada (Pydantic) y el permiso requerido (RBAC local por códigos: IPOCRE, IPOEDI,
   AEVADM/AEVAPR, IPRCES, EJSGES/EACEAC…), fallando *antes* de construir nada si el permiso es
   insuficiente.
2. Lee contexto real por `GET` cuando corresponde (p. ej. `editar_postulacion` sólo previsualiza si la
   bitácora confirma estado *Incompleta*).
3. Devuelve, por defecto, un *preview* `dry_run` con `aplicado: false`,
   `solicitud_mutante_enviada: false` y un `would_request` (contrato hipotético `verificado: false`).
4. **Patrón dry-run → commit.** Con la bandera opt-in `SISAV2_MOCK_WRITES=1` y `confirmar: true`, la
   intención se aplica contra un backend simulado en memoria (`MockSisav2Backend`) y se relee
   (`read_back`), devolviendo `modo: "commit_mock"`, `aplicado: true` y `sisav2_real_modificado: false`.
   El simulador no tiene cliente HTTP: por construcción, un commit jamás llega a SISAV2 real, que
   además conserva una *allowlist* read-only en el cliente como defensa en profundidad.
5. **Auditoría.** Cada commit deja una línea JSONL (actor pseudonimizado `usuario#<id>`, operación,
   `request_id`, sello temporal): el rastro de "quién hizo qué".
6. **PII.** Se enmascaran identificadores (RUT, correo, id) en `cargar_asistencia`, se bloquean campos
   personales/dependientes de carrera en `crear_postulacion_espejo`, y los campos sensibles se excluyen
   antes de generar embeddings.

**Análisis semántico.** Sobre una cohorte local autorizada (25–50 iniciativas, saneada de PII), se
generan embeddings del objetivo/descripción y se cachean en disco con TTL 24 h e invalidación por
huella SHA-256 de la cohorte (no se recalcula en cada llamada). `buscar_iniciativas_similares` devuelve
top-*k* por coseno; `detectar_duplicados` marca pares sobre un umbral (apoyo a revisión humana, no
decisión automática).

## 4. Resultados

- **Cobertura funcional:** 23 tools (20 en el `.exe` liviano sin el stack de ML) + 5 resources; las 4
  metas técnicas del Foco 2/3 cumplidas (≥5 casos, ≥3 escritura, ≥3 análisis, doc multi-usuario).
- **Calidad del código:** 136 tests verdes, 85.31 % de cobertura (umbral del proyecto 80 %);
  `ruff` y `mypy` sin observaciones (45 archivos). La suite incluye *contract tests* contra 17 muestras
  reales anonimizadas de la API.
- **Escritura de principio a fin (demostrada):** el flujo dry-run → `commit_mock` → `read_back` con
  auditoría en disco funciona end-to-end sobre el mock; el SISAV2 real no se modifica.
- **Casos de uso:** 6 prompts validados de principio a fin en Claude Desktop (`docs/DEMO.md`): consulta
  conectada, detalle+bitácora, similares, duplicados, preview de escritura y preview de flujo.
- **Experimentación (Foco 3):** el notebook `notebooks/experimentos.ipynb` (ejecutado) compara
  configuraciones y mide el aporte de cada componente. Hallazgos con MiniLM multilingüe sobre un corpus
  etiquetado por tema: los embeddings separan por significado (coseno medio intra-tema 0.506 vs.
  inter-tema 0.206; separación 0.300); la búsqueda semántica supera a keyword ante una consulta
  parafraseada (rankea el objetivo correcto en el puesto 1 vs. 4 de TF-IDF); k es un
  trade-off recuperación↔precisión (precision@k 0.80 → 0.40 → 0.24 de k=1 a 5); y el umbral de
  duplicados es sensible (el par casi-duplicado, coseno 0.848, queda justo bajo 0.85 → se entrega como
  *candidato* a revisión humana, no como decisión).

## 5. Discusión (limitaciones, alucinaciones, trade-offs)

- **¿Por qué dry-run por defecto y commit sólo contra mock?** La escritura real en SISAV2 exige
  autorización institucional, recon supervisado de los contratos mutantes y una política de auditoría
  que no están en el alcance del curso. Simular un commit "real" sería deshonesto; no mostrar escritura
  incumpliría la meta de "lectura y escritura de principio a fin". Por eso aplicamos la intención contra
  un simulador rotulado, con read-back y auditoría, y así demostramos el patrón completo sin poner en
  riesgo el sistema institucional.
- **¿Por qué NO fine-tuning?** La tarea no es enseñarle *lenguaje* nuevo al modelo, sino darle
  **acceso a datos y acciones** y controlar el formato. El árbol de decisión prompting → RAG → tool use
  → PEFT se resuelve en *tool use*: MCP + structured output cubren el problema sin el costo, los datos
  etiquetados ni el mantenimiento de un fine-tuning.
- **Sobre LangGraph.** El patrón ReAct ya lo ejecuta el cliente MCP (Claude Desktop): él razona y
  decide qué tool llamar. El servidor expone herramientas tipadas; agregar un orquestador de agentes
  sería una segunda capa redundante para una arquitectura cliente-servidor. Queda como evolución si se
  necesitara un agente autónomo *sin* humano en el loop.
- **Alucinaciones.** Se mitigan estructuralmente: los datos provienen de tools (no del modelo), la
  salida es tipada (Pydantic), la escritura pasa por RBAC + dry-run, y el commit relee el efecto
  (`read_back`) en vez de "confiar" en que se aplicó.
- **Similitud semántica.** Puede producir falsos positivos (dos iniciativas con objetivos parecidos
  pero legítimamente distintas). Por eso `detectar_duplicados` entrega *candidatos* a revisión humana,
  nunca un veredicto.
- **No determinismo.** Un LLM no es determinista (muestreo); dos corridas pueden frasear y decidir
  distinto. Por eso las decisiones sensibles se anclan a tools verificables y a estados reales leídos de
  SISAV2, no a la generación libre.
- **Límites.** No se validó ningún endpoint de escritura real; el análisis opera sobre una cohorte
  acotada; el ejecutable liviano omite las tools semánticas (se documenta y degradan de forma explícita,
  no silenciosa).

## 6. Conclusiones y trabajo futuro

La Fase 2 deja un MCP que un analista instala con un onboarding asistido, consulta SISAV2 con su propia
identidad, obtiene análisis semántico sobre una cohorte autorizada y prueba el ciclo de escritura de
principio a fin con garantías de seguridad (dry-run por defecto, commit sólo contra mock, RBAC,
auditoría, minimización de PII). Como trabajo futuro queda habilitar la escritura real tras autorización
institucional y recon supervisado de contratos, con aprobación explícita y auditoría persistente;
distribuir el servidor como MCP remoto con OAuth 2.1/OIDC + PKCE, con sesión aislada por analista y
rate limiting por identidad (ver `docs/arquitectura-multi-usuario.md`); y recoger el feedback de uso
real de los analistas (`docs/FEEDBACK.md`) como insumo de requerimientos del próximo semestre.

## 7. Referencias

1. Anthropic. *Model Context Protocol (MCP) — Specification.* https://modelcontextprotocol.io
2. Yao, S. et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models.* ICLR.
3. Reimers, N. & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.*
   EMNLP.
4. Documentación de FastMCP, Pydantic v2, `sentence-transformers` (paraphrase-multilingual-MiniLM-L12-v2).
5. Material del curso INFB6093, sesiones S11–S14 (agentes, tool use, MCP, structured output).

**Anexos:** repositorio `sisav2-mcp` (`SCOPE.md`, `docs/DEMO.md`, `docs/arquitectura-multi-usuario.md`,
`notebooks/experimentos.ipynb`); suite de tests reproducible (`uv run python -m pytest`).
