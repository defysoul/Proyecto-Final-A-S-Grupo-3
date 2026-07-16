# Guía de demo conectada — SISAV2 MCP

La demo usa consultas reales autorizadas contra SISAV2 y previews locales de escritura. La regla que
debe aparecer durante toda la presentación es:

> **DEMO SEGURA:** ninguna tool de escritura modifica SISAV2 real. Por defecto responden en
> `modo: "dry_run"` con `aplicado: false` y `solicitud_mutante_enviada: false`.

La demo tiene **dos modos**:

- **Dry-run (por defecto):** `would_request` describe un contrato hipotético (`verificado: false`); no
  representa un endpoint real capturado ni una petición emitida.
- **Commit contra mock (opcional):** con `SISAV2_MOCK_WRITES=1` y `confirmar: true`, la tool aplica la
  intención contra un **simulador en memoria** y devuelve `modo: "commit_mock"`, `aplicado: true`,
  `sisav2_real_modificado: false` y un **read-back** del efecto. Sirve para mostrar el patrón
  dry-run → commit de principio a fin; **SISAV2 real nunca se toca** (el mock no tiene cliente HTTP) y
  cada commit deja auditoría JSONL.

## 1. Antes de abrir Claude Desktop

Haz esto en el mismo equipo, red y cuenta UTEM que usarás en la demo.

1. Comprueba conexión a la red UTEM/VPN y que la cuenta ya fue guardada mediante onboarding.
2. Verifica autenticación:

   ```powershell
   uv run python -m sisav2_mcp.onboarding --check
   ```

3. Copia `docs/demo-cohort.example.json` a `docs/demo-cohort.local.json`, reemplaza o amplía sus
   IDs hasta la cohorte ensayada de 25–50 iniciativas, y mantén ese archivo fuera de Git.
4. Prepara/refresca el índice de análisis con la cohorte local autorizada:

   ```powershell
   uv run sisav2-mcp index-demo --cohort <RUTA_LOCAL_COHORTE>
   ```

   Con un instalador portable reconstruido para 0.2.0, ejecuta el mismo subcomando sobre el
   ejecutable instalado:

   ```powershell
   <RUTA_ESTABLE>\sisav2-mcp.exe index-demo --cohort <RUTA_LOCAL_COHORTE>
   ```

   Confirma antes con `sisav2-mcp.exe --help` que el binario lista `index-demo`; si no, usa la ruta
   `uv` hasta reconstruirlo.

5. Abre/reinicia Claude Desktop y comprueba que el servidor `sisav2` aparece conectado.
6. Haz una consulta real breve, por ejemplo: *“Con SISAV2, lista 3 postulaciones de pregrado.”*

El preflight lee por GET los detalles de los IDs del manifiesto de cohorte y guarda solo la caché local
del índice; el primer uso puede descargar/cargar el modelo semántico y requiere red. La cohorte debe
estar aprobada para la demo, ser local y excluir RUT, correos, nombres y otros datos personales. Si
falla cualquiera de estos pasos, no continúes usando una respuesta almacenada o inventada como
sustituto de la conexión.

## 2. Guion de 6 prompts

Los IDs y resultados reales dependen de los permisos de la cuenta y de la cohorte. Toma un ID devuelto
por el primer prompt y úsalo en los siguientes cuando corresponda.

1. **Consulta conectada**

   > “Con SISAV2, lista 5 postulaciones de pregrado y dime cuántas hay en cada estado de esta página.”

   Muestra una tool de lectura, autenticación por usuario y datos reales.

2. **Detalle y trazabilidad**

   > “Dame el detalle de siete pasos y la bitácora de la postulación `<ID>`.”

   Muestra que el MCP recupera contenido de SISAV2 sin abrir la interfaz.

3. **Análisis semántico**

   > “Busca iniciativas similares a `<ID>` y explícame por qué se parecen.”

   La tool esperada es `buscar_iniciativas_similares`. Aclara que compara la cohorte preparada, no
   todo SISAV2, y que el resultado es apoyo para revisión humana.

4. **Control de duplicados**

   > “Detecta posibles duplicados en la cohorte y muéstrame solo los candidatos con mayor similitud.”

   La tool esperada es `detectar_duplicados`; “posible” no significa que el sistema haya dictaminado un
   duplicado.

5. **Preview de escritura — espejo**

   > “Prepara una postulación espejo de `<ID_ORIGEN>` para modalidad `<MODALIDAD_DESTINO>`, convocatoria
   > `<CONVOCATORIA_DESTINO_ID>` y carrera `<CARRERA_DESTINO_ID>`; muéstrame el diff y no apliques nada.”

   La tool esperada es `crear_postulacion_espejo`. Señala en la respuesta:

   ```text
   modo: dry_run
   aplicado: false
   solicitud_mutante_enviada: false
   would_request.verificado: false
   ```

6. **Preview de flujo**

   > “Prepara la evaluación de admisibilidad de `<ID>` en modalidad `<MODALIDAD>`, fase `<ID_FASE>`,
   > con veredicto `Admisible` y comentario `<COMENTARIO>`; no apliques nada.”

   La tool esperada es `evaluar_admisibilidad`. Si el permiso o el contexto no es válido, muestra el
   error claro como parte de la seguridad; no sustituyas el resultado por una aplicación simulada.

Opcionalmente, muestra `ranking_facultades_por_ods` para un resumen agregado de la cohorte, o una
segunda preview con `cambiar_fase`, `crear_postulacion`, `editar_postulacion`,
`agregar_comentario_bitacora` o `cargar_asistencia`.

## 3. Qué decir al mostrar una tool de escritura

- “Esta es una intención de negocio, no un CRUD expuesto a ciegas.”
- “Se validaron los campos y el permiso aplicable; el resultado enseña el diff y el contrato que se
  revisaría.”
- “No se hizo una solicitud mutante; `aplicado` sigue en `false`.”
- “Los contratos de escritura de SISAV2 aún no se han validado supervisadamente, por eso
  `would_request.verificado` es `false`.”
- “En `cargar_asistencia`, la preview marca `would_request.body_redactado: true` y enmascara
  identificadores para no exhibir PII en la grabación.”

Al mostrar el **commit contra mock** (`confirmar: true` con `SISAV2_MOCK_WRITES=1`), di explícitamente:
- “Esto se aplica contra un **simulador en memoria**, no contra SISAV2; `sisav2_real_modificado` es
  `false` y el `read-back` relee el efecto desde el mock.”
- “Cada commit queda en el log de auditoría (quién, qué, `request_id`, cuándo).”

Sobre SISAV2 real: no digas que se creó, editó, evaluó o cambió de fase una postulación real. El único
lugar donde algo se "aplica" es el mock rotulado; el sistema institucional permanece intocable.

## 4. Plan de contingencia honesto

| Problema | Acción |
|---|---|
| No hay red UTEM/VPN o falla onboarding | Detener la demo conectada y explicar la dependencia; no usar un fallback offline. |
| `index-demo` falla | Revisar ruta, autorización y saneamiento de la cohorte; no mostrar análisis como si estuviera fresco. |
| La tool de preview rechaza permiso/entrada | Mostrar la validación/RBAC como resultado esperado de seguridad. |
| Claude Desktop no carga el servidor | Verificar la configuración de [`SETUP.md`](../SETUP.md), reiniciar por completo o usar un cliente local permitido. |

## 5. Cierre y evidencia mínima

Al terminar, conserva capturas o el registro de:

- el preflight exitoso (credencial e índice);
- una consulta conectada;
- una respuesta de análisis; y
- una preview donde sean visibles los tres campos de seguridad (`modo`, `aplicado`,
  `solicitud_mutante_enviada`).

Antes de etiquetar una release, ejecuta `uv run ruff check .`, `uv run mypy src` y
`uv run python -m pytest -q`. La referencia a **90 tests verdes** solo aplica si esa última ejecución
del corte a presentar informa exactamente 90 aprobados; de otro modo se publica la cifra real.
