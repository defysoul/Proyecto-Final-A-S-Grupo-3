# Manual del analista — Asistente SISAV2 (MCP)

Guía para **usar** el asistente en tu día a día. No necesitas saber programar.

## ¿Qué es?

Un asistente (dentro de Claude Desktop) que se conecta a **SISAV2 con tu propia cuenta UTEM** y responde
en lenguaje natural. Te ayuda a **consultar**, **analizar** y **preparar** trabajo que hoy haces a mano.

## Instalación (una vez, ~2 minutos)

1. Abre el instalador **`sisav2-mcp.exe`** (te lo entregamos en la capacitación).
2. Se abre una ventana. Escribe tu **usuario y clave UTEM** (la misma de SISAV2).
3. El instalador detecta solo tus asistentes (Claude Desktop / Codex) y los deja marcados.
4. Presiona **Conectar**. Cuando diga "Listo", cierra la ventana.
5. Abre (o reinicia) **Claude Desktop**: ya verás el asistente `sisav2` conectado.

> Tu clave queda guardada **cifrada** en tu equipo (no en un archivo, no en la nube). El asistente sólo
> ve lo que **tu cuenta** puede ver en SISAV2.

## Cómo usarlo (ejemplos)

Escríbele como le hablarías a un colega:

- *"Con SISAV2, lista 5 postulaciones de pregrado y dime en qué estado está cada una."*
- *"Resúmeme la iniciativa 3033 y su bitácora: ¿qué pasó?"*
- *"Busca iniciativas parecidas a la 2606 y explícame por qué se parecen."*
- *"¿Hay posibles duplicados en esta cohorte?"*
- *"Prepara la creación de una postulación de pregrado para la convocatoria 71, título '…', objetivo
  '…'; muéstrame qué se validaría (no apliques nada)."*

## Qué hace y qué NO hace (importante)

- **Consultar y analizar:** trae datos reales de SISAV2 y te ayuda a comparar/resumir.
- **Preparar acciones:** cuando pides crear/editar/evaluar/cambiar de fase, por defecto te muestra un
  **borrador revisable** (qué haría, con qué permiso), pero **no modifica SISAV2**. Verás `aplicado: false`.
- **Nunca** cambia datos sin que se habilite y confirmes; y todo lo que se aplica queda **registrado**.
- Los resultados de "parecidas" o "duplicados" son **apoyo a tu criterio**, no decisiones automáticas.

## Si algo falla

- **No aparece `sisav2` conectado:** reinicia Claude Desktop por completo. Si sigue, vuelve a abrir el
  instalador y presiona Conectar.
- **Dice que no tienes permiso para algo:** es correcto — el asistente respeta tus permisos de SISAV2.
- **Necesitas red UTEM/VPN** para consultar datos reales.

## Tu opinión nos sirve

Estamos levantando cómo mejorar la herramienta para el próximo semestre. Cuéntanos qué te resultó útil,
qué faltó y qué acción te gustaría que **sí** aplicara (ver `docs/FEEDBACK.md`).
