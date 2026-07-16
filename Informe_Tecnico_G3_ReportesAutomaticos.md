# Informe Técnico — Grupo 3: Reportes Automáticos

**INFB6093 Procesamiento de Lenguaje Natural · 2026-I**
**Proyecto Final (A+S) · Presentación Final S16**
**Socio comunitario:** Dirección VcM (Claudia Urrutia)

---

## 1. Introducción

El problema abordado por este grupo es la generación de reportes que la Dirección VcM debe producir periódicamente para dar seguimiento a sus iniciativas registradas en SISAV2. Actualmente esta tarea se realiza de forma manual, consumiendo tiempo del equipo de analistas y dependiendo de que cada persona recopile y redacte la información dispersa en el sistema.

La propuesta del grupo consiste en un **skill** que, apoyándose en el MCP de lectura desarrollado por el Grupo 2 (G2), permite generar automáticamente reportes en formato docx a partir de los datos ya disponibles en SISAV2, reduciendo el trabajo manual del analista a completar únicamente aquello que el sistema no puede resolver por sí solo (imágenes y listas de asistencia).

Un condicionante central del desarrollo fue el cronograma: el MCP del G2 fue entregado recién el **lunes 13 de julio**, dos días antes de la presentación final, lo que limitó de forma importante el tiempo disponible para iterar, medir y validar la solución con el socio comunitario.

## 2. Trabajo relacionado

El diseño se apoya en dos conceptos vistos en el curso:

- **Structured output**: el MCP del G2 expone tools que retornan los campos de una iniciativa de SISAV2 de forma estructurada (parámetros tipados) en lugar de texto libre. Esto permite que el skill de G3 consuma esos campos de manera determinística y los mapee directamente a las plantillas docx, sin depender de que un LLM interprete texto no estructurado para extraer los datos. Se trata de una inferencia razonada sobre el diseño del MCP recibido, no de una decisión documentada explícitamente por el G2.
- **Arquitectura basada en skills sobre un MCP unificado**: en lugar de levantar una plataforma o UI propia, se optó por construir el reporte como un skill que llama al mismo MCP que ya usa el resto del ecosistema (Claude Desktop, otros flujos de VcM), evitando duplicar la capa de acceso a datos.

No se incorporó RAG ni RAGAS en esta iteración, dado que el flujo no requiere recuperación semántica sobre un corpus: los datos provienen directamente de los campos estructurados que entrega el MCP.

## 3. Método

### 3.1 Arquitectura elegida

Se optó por construir un **skill** que se conecta al MCP adaptado del G2, en lugar de una plataforma o UI independiente. La razón principal es que así todo el acceso a datos de SISAV2 queda **unificado en un mismo MCP**, evitando mantener dos integraciones distintas contra el sistema y simplificando el uso: el analista opera desde la misma herramienta (Claude Desktop) que usará para el resto de sus tareas con VcM, sin aprender una interfaz adicional.

Como alternativa se consideró implícitamente una plataforma propia (p. ej. una app Streamlit independiente), pero se descartó por duplicar esfuerzo de integración y fragmentar la experiencia del usuario final.

### 3.2 Plantillas

Se implementaron **2 tipos de plantilla docx**:

- **Catastro**
- **Evidencia de iniciativas**

Estas dos se priorizaron porque fueron las que el equipo de VcM indicó por correo como prioritarias. El resto de los tipos de reporte que emite VcM quedaron fuera del alcance de esta entrega, principalmente porque **no se recibió ningún ejemplo de plantilla** para esos otros formatos, lo que impidió modelarlos con el mismo nivel de certeza.

### 3.3 Flujo técnico

El flujo de generación es el siguiente:

1. El usuario solicita, a través del skill, un reporte de tipo catastro o evidencia para una iniciativa específica.
2. El skill invoca una tool del MCP del G2 (adaptado por G3 el 13 de julio) que retorna los campos estructurados de la iniciativa desde SISAV2.
3. El skill mapea esos campos a la plantilla docx correspondiente y genera el documento.

**Qué queda automatizado:** todos los campos que ya existen estructurados en SISAV2 y que el MCP expone (datos de la iniciativa, metadatos del catastro/evidencia).

**Qué queda fuera del automatismo:** las **imágenes** y las **listas de asistencia**, ya que VcM no las tiene unificadas en un sistema del que se puedan leer de forma programática; estas deben ser incorporadas manualmente por el analista.

**Limitación identificada en la redacción de texto:** el skill no logra redactar de forma autónoma las secciones narrativas del reporte (por ejemplo, explicar qué ocurrió con una iniciativa, como un cambio de fecha), porque no cuenta con contexto sobre los eventos ocurridos más allá de los campos estructurados. Para resolver esto se requeriría entregarle al modelo un contexto adicional (p. ej. una bitácora o notas del analista) del cual redactar; con más tiempo de desarrollo esto se habría incorporado.

## 4. Resultados

Debido a que el MCP del G2 se recibió recién el 13 de julio, el grupo dispuso de aproximadamente **un día de trabajo efectivo** antes de la presentación final. En ese plazo se generaron:

- **5 reportes de evidencia** sobre iniciativas reales.
- **2 reportes de catastro** sobre iniciativas reales.

No se calcularon métricas RAGAS (faithfulness) sobre los reportes generados, dado que el flujo no involucra recuperación ni generación de texto libre en esta iteración: los datos se insertan de forma directa desde los campos estructurados del MCP, no hay redacción generada por el modelo que evaluar con esa métrica.

No se implementó una UI o flujo de revisión (tipo Streamlit) por la misma restricción de tiempo.

## 5. Discusión

**Limitaciones principales:**

- El skill no redacta las secciones narrativas de los reportes (por ejemplo, justificar un cambio de fecha o describir un evento de la iniciativa), ya que no dispone del contexto necesario sobre lo ocurrido. Esto es la brecha más relevante detectada por el equipo.
- La cobertura de tipos de reporte quedó limitada a 2 de los que emite VcM, por falta de plantillas de referencia para los demás.
- Las imágenes y listas de asistencia no están automatizadas porque VcM no las tiene centralizadas en un sistema consultable.
- No hubo tiempo para instrumentar métricas de calidad (RAGAS u otras) ni para iterar sobre los resultados generados.

**Riesgo de alucinación:** al no generarse texto libre en esta versión (los campos se insertan directamente desde datos estructurados), el riesgo de alucinación en los reportes actuales es bajo. Este riesgo se activaría si, en una siguiente iteración, se agrega redacción automática de las secciones narrativas sin un mecanismo de grounding adecuado (por ejemplo, contexto verificado por el analista antes de generar el texto).

**Sobre el tiempo disponible:** la principal restricción de este entregable fue la dependencia del MCP del G2, recibido dos días antes de la presentación. Esto condicionó tanto el alcance (2 plantillas, sin redacción automática) como la validación (no se alcanzó a probar con VcM ni a medir calidad).

## 6. Conclusiones y trabajo futuro

El grupo logró un flujo funcional de generación automática de reportes de catastro y evidencia, integrado con el MCP del G2, en un plazo de desarrollo muy acotado. El resultado demuestra la viabilidad de la arquitectura elegida (skill unificado sobre el MCP), pero deja pendientes mejoras relevantes para una siguiente iteración:

- Incorporar generación de texto narrativo a partir de contexto adicional (bitácora de eventos de la iniciativa), en lugar de solo campos estructurados.
- Ampliar la cobertura a los demás tipos de reporte de VcM, una vez se cuente con plantillas de referencia.
- Automatizar la incorporación de imágenes y listas de asistencia si VcM logra centralizarlas.
- Medir calidad de la redacción generada (RAGAS faithfulness) una vez el skill incorpore texto libre.
- Validar el flujo completo con el equipo de VcM y levantar su feedback, insumo previsto para el siguiente semestre.

## 7. Referencias

- MCP SISAV2 (Grupo 2), versión adaptada entregada el 13 de julio de 2026.
- Material y sesiones del curso INFB6093 sobre structured output (S11-S14).

## 8. Anexos

Los reportes generados (5 de evidencia, 2 de catastro) y el código del skill se encuentran en el repositorio entregado por el grupo.
