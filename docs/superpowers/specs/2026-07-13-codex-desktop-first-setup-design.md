# SISAV2 MCP — Instalación prioritaria en Codex Desktop

## Objetivo

Hacer que el instalador de SISAV2 MCP reconozca explícitamente Codex Desktop en
Windows y lo presente como el destino principal de instalación. La experiencia
debe evitar instalaciones accidentales en clientes secundarios y eliminar el
espacio visual innecesario de la ventana actual.

## Alcance

- Plataforma: Windows.
- Cliente principal: Codex Desktop.
- Clientes secundarios conservados: Claude Code y Claude Desktop.
- Transporte: MCP local por `stdio`.
- Registro para Codex: conservar `~/.codex/config.toml` y la tabla
  `[mcp_servers.sisav2]`; Desktop y CLI comparten esa configuración.

No se modifica el servidor MCP, el flujo de credenciales UTEM ni el formato de
configuración ya soportado por Claude.

## Problema confirmado

La detección actual reúne bajo `codex` dos señales genéricas: `shutil.which`
para `codex` y la existencia de `~/.codex`. En este equipo, el binario que se
encuentra es el de Codex Desktop, pero la interfaz lo etiqueta como “Codex CLI”.
Además, una carpeta de configuración existente no prueba que el producto esté
instalado. La misma pantalla preselecciona todos los clientes detectados y su
tarjeta usa el alto restante de una ventana fija, dejando espacio en blanco.

## Diseño aprobado

### 1. Detección de Codex Desktop

Se incorporará una comprobación específica y sin efectos laterales para Windows:

1. Consultar el paquete instalado `OpenAI.Codex` mediante la API del sistema.
2. Si esa consulta no está disponible, buscar la instalación de usuario en
   `%LOCALAPPDATA%\\Programs\\OpenAI\\Codex\\bin\\codex.exe`.
3. Si solo existe un binario genérico `codex` en `PATH`, clasificarlo como
   `codex_cli`, no como Desktop.

El resultado incluirá señales diferenciadas `codex_desktop` y `codex_cli`. La
existencia de `~/.codex` no se usará para afirmar que uno de los productos está
instalado; solo sigue siendo la ruta donde se escribe la configuración.

### 2. Elección de destino

La vista inicial tendrá una tarjeta destacada “Codex Desktop”, con estado
“Detectado en este equipo” y seleccionada por defecto únicamente cuando se
confirme la instalación. Si Codex Desktop no se detecta, la tarjeta indicará que
no está disponible y no quedará seleccionada.

Claude Code, Claude Desktop y Codex CLI se agruparán bajo un control desplegable
“Otros clientes compatibles”. Se mantienen disponibles, pero cerrados y sin
seleccionar por defecto. Seleccionarlos requiere una acción deliberada de la
persona usuaria.

Si no hay ningún destino marcado, el botón debe explicar que se debe elegir un
cliente compatible. Si Codex Desktop es el único cliente detectado, el recorrido
normal requiere solo ingresar las credenciales y presionar “Conectar”.

### 3. Registro y resultado

La selección `codex_desktop` llamará al mismo configurador TOML existente para
escribir `mcp_servers.sisav2` con el ejecutable estable y `args = ["serve"]`.
El resultado y la pantalla final dirán “Codex Desktop”, mostrarán la ruta de
configuración escrita y solicitarán cerrar y volver a abrir Codex Desktop antes
de abrir una tarea nueva.

El configurador será idempotente: una nueva ejecución reemplaza solo la entrada
`sisav2` y conserva el resto de las tablas TOML. La serialización actual no
conserva comentarios; retenerlos no forma parte de este cambio. Los resultados
de los clientes secundarios conservarán sus nombres actuales.

### 4. Ajuste visual

- Reducir la ventana a una altura ajustada al contenido y permitir redimensionar
  verticalmente si el sistema usa escalado de texto.
- Dejar que la tarjeta tenga altura de contenido, no `flex: 1`.
- Sustituir “Instalar en (detectados en tu equipo)” por jerarquía clara:
  “Destino recomendado” y “Otros clientes compatibles”.
- Mantener la paleta UTEM/SISAV2, pero usar menos bordes pesados y espaciado
  vertical compacto.
- Mantener visibles las credenciales y el botón de acción sin requerir
  desplazamiento en la ventana estándar.

## Componentes y flujo

```text
Windows / rutas conocidas ──> detect_codex_desktop() ──> SetupApi.detectar()
                                                        │
                                                        v
                                                renderClients()
                                                        │
Usuario selecciona destino ──> SetupApi.configurar() ──┼──> configure_codex()
                                                        │          │
                                                        └──────────v
                                                   config.toml preservado
```

La detección se mantiene separada de la escritura: no crea directorios, no
modifica configuraciones y no depende de que Codex esté abierto. El adaptador de
registro conserva la responsabilidad de escribir el archivo TOML.

## Errores y estados

- La ausencia de PowerShell, la consulta del paquete o una ruta no accesible se
  tratan como señal no disponible y activan el siguiente respaldo; no bloquean la
  interfaz.
- Si se detecta Codex Desktop pero el TOML no puede leerse o escribirse, se
  muestra el error existente con la etiqueta “Codex Desktop”.
- La vista no afirmará que una app está instalada solo porque una carpeta de
  configuración antigua existe.

## Pruebas de aceptación

1. Un paquete `OpenAI.Codex` detectado produce `codex_desktop=True` aunque
   `~/.codex` no exista.
2. Un `~/.codex` existente sin paquete ni binario no produce una detección de
   Codex Desktop.
3. La ruta de instalación de usuario detecta Codex Desktop si la consulta del
   paquete no está disponible.
4. Un binario genérico `codex` en `PATH` sin una señal de Desktop se expone como
   `codex_cli=True`, no como `codex_desktop=True`.
5. Elegir `codex_desktop` escribe la tabla TOML existente y conserva las demás
   tablas de configuración ya serializadas.
6. La interfaz muestra “Codex Desktop”, lo marca solo cuando está detectado y
   deja Claude como opción secundaria no seleccionada.
7. La tarjeta no se estira artificialmente ni deja espacio blanco en una ventana
   estándar de Windows con escalado de pantalla habitual.

## Fuera de alcance

- Instalar Codex Desktop si no existe.
- Cambiar el protocolo MCP o los permisos SISAV2.
- Cambiar la gestión de contraseñas UTEM.
- Soportar macOS o Linux en esta mejora.
