# Guion — Presentación Final G3 (Reportes automáticos VcM)

INFB6093 · S16 · 15 de julio de 2026 · 15-20 min + 10 min Q&A
Equipo: Yenderi Albayay · Pablo Ibáñez · Christian Pérez

> Nota: el reparto de turnos es una sugerencia de referencia. Cada integrante debe poder explicar **todas** las decisiones, no solo su tramo — el Q&A puede preguntar sobre cualquier parte a cualquier persona.

---

## Slide 1 — Portada (Yenderi) · 0:30
"Buenas tardes. Somos el Grupo 3 — Yenderi Albayay, Pablo Ibáñez y Christian Pérez. Vamos a presentar el proyecto de reportes automáticos para la Dirección VcM, nuestro socio comunitario en este curso, representado por Claudia Urrutia."

## Slide 2 — El problema (Yenderi) · 1:00
"VcM tiene que generar reportes periódicos de seguimiento de sus iniciativas, que están registradas en SISAV2. Hoy eso se hace a mano: cada analista entra al sistema, recopila la información y la redacta en un Word. Eso consume tiempo del equipo y depende de que una persona junte todo correctamente."

## Slide 3 — Nuestra propuesta (Yenderi) · 1:00
"Nuestra propuesta es un skill que se conecta al MCP de lectura que desarrolló el Grupo 2 sobre SISAV2. El skill toma los campos que ya están estructurados en el sistema y los usa para generar automáticamente el reporte en Word. Lo que el sistema no puede resolver por sí solo — imágenes y listas de asistencia — queda para que el analista lo complete."

## Slide 4 — Decisión de arquitectura (Pablo) · 1:30
"Acá tomamos una decisión de diseño importante: ¿construíamos una plataforma propia, tipo Streamlit, o un skill sobre el MCP existente? Descartamos la plataforma propia porque habría significado duplicar la integración con SISAV2 y obligar al analista a aprender una herramienta nueva. Optamos por un skill porque así todo el acceso a datos queda unificado en un mismo MCP, y el analista sigue trabajando desde Claude Desktop, la misma herramienta que usará para el resto de sus tareas con VcM."

## Slide 5 — Por qué no RAG (Pablo) · 1:00
"Una pregunta que probablemente nos van a hacer: ¿por qué no usamos RAG, si la pauta nos agrupa con G1 como sistemas RAG? Porque no lo necesitamos. El MCP del G2 nos entrega los campos de la iniciativa como parámetros tipados — structured output —, no como texto libre que haya que recuperar semánticamente desde un corpus. El mapeo del campo a la plantilla es determinístico. Por eso tampoco calculamos RAGAS en esta iteración: no hay texto generado que evaluar con esa métrica."

## Slide 6 — Flujo técnico (Pablo) · 1:00
"El flujo tiene tres pasos: el analista pide el reporte desde el skill, el skill llama a la tool del MCP del G2 que devuelve los campos estructurados de la iniciativa, y el skill mapea esos campos a la plantilla docx correspondiente y genera el documento."

## Slide 7 — Mapa de campos (Christian) · 1:00
"Para dejarlo explícito: todo lo que ya está estructurado en SISAV2 y que el MCP expone, se completa solo — fechas, responsables, estado, metadatos de catastro y evidencia. Lo que queda a mano son las imágenes, las listas de asistencia y el texto narrativo, por ejemplo si hay que explicar un cambio de fecha."

## Slide 8 — Plantillas priorizadas (Christian) · 1:00
"Implementamos dos plantillas: catastro y evidencia. Las priorizamos porque VcM nos las indicó por correo como las más urgentes. Los demás tipos de reporte que emite VcM quedaron fuera de esta entrega porque no recibimos ningún ejemplo de plantilla para modelarlos con el mismo nivel de certeza."

## Slide 9 — Restricción de cronograma (Christian) · 1:00
"Esto es importante para entender el alcance: el MCP del G2 lo recibimos recién el lunes 13 de julio, dos días antes de esta presentación. Tuvimos, en la práctica, un día efectivo de desarrollo. Eso condicionó tanto el alcance — dos plantillas, sin redacción automática — como la validación: no alcanzamos a probar el flujo completo con VcM."

## Slide 10 — Resultados (Christian) · 0:45
"Con ese día generamos 5 reportes de evidencia y 2 de catastro, todos sobre iniciativas reales de SISAV2."

## Slide 11 — Cómo lo usa el analista / demo (quien haga la demo en vivo) · 2:00
"Así lo usaría un analista: abre Claude Desktop con el skill instalado, pide el tipo de reporte e indica la iniciativa, y el skill genera el docx con los campos ya completados. Después revisa y completa a mano lo que falta.
[Aquí va la demo en vivo: generar un reporte de evidencia real y mostrar el docx resultante.]"

## Slide 12 — Limitaciones (quien no haya hablado aún) · 1:00
"La limitación más relevante que detectamos es que el skill no redacta las partes narrativas del reporte, porque no tiene contexto sobre lo que efectivamente ocurrió más allá de los campos estructurados. Además, la cobertura quedó en dos tipos de reporte, y las imágenes y listas de asistencia siguen siendo manuales porque VcM no las tiene centralizadas."

## Slide 13 — Riesgo de alucinación · 1:00
"Como no generamos texto libre en esta versión — los campos se insertan directo desde datos estructurados —, el riesgo de alucinación hoy es bajo. Ese riesgo aparecería recién si en una próxima iteración agregamos redacción narrativa sin un mecanismo de grounding, por ejemplo una bitácora verificada por el analista."

## Slide 14 — Autoevaluación frente a la pauta (idealmente todo el equipo, en conjunto) · 1:30
"Queremos ser transparentes sobre dónde estamos respecto a las metas técnicas de la pauta. Llegamos a 2 de 3 plantillas, por falta de plantillas de referencia. Superamos el mínimo de reportes generados. No aplicamos RAGAS porque no hay texto libre que medir todavía. Y no alcanzamos a construir una UI de revisión, por la restricción de tiempo que ya explicamos. Creemos que el diseño es sólido y viable; lo que faltó fue tiempo de iteración, no una decisión de arquitectura equivocada."

## Slide 15 — Trabajo futuro · 1:00
"Para la siguiente iteración: incorporar redacción narrativa a partir de una bitácora de eventos, ampliar la cobertura de plantillas, automatizar imágenes y asistencia si VcM logra centralizarlas, medir RAGAS cuando exista texto libre, y validar todo el flujo con el equipo de VcM — eso queda como insumo para el próximo semestre."

## Slide 16 — Cierre (Yenderi) · 0:30
"Eso es todo de nuestra parte. Quedamos atentos a sus preguntas."

## Slide 17 — Declaración de uso de IA (Yenderi o quien cierre) · 0:30
"Por transparencia: usamos Claude para el manejo de código, la creación de las tools del MCP y la adaptación del skill a partir del MCP del Grupo 2. Usamos Gemini como apoyo puntual en partes del desarrollo del tool, por costo de procesamiento y de tokens de Claude."

---

**Tiempo total estimado:** ~17 minutos, dentro del rango 15-20 min pedido en la pauta.

**Recordatorio para el Q&A:** cualquiera del equipo puede recibir preguntas sobre cualquier parte del proyecto (mecanismo anti-delegación de la pauta). Revisar el documento `qa_preparacion_g3.md` antes de la presentación.
