# SETUP — instalación, preflight y conexión

Esta guía ofrece una ruta portable para la demo y un respaldo reproducible con Python/`uv`. Ambas
ejecutan un MCP local por `stdio`: no abren un puerto ni suben credenciales a este repositorio.

> **Límite de seguridad:** las tools de intención de escritura de esta versión siempre devuelven un
> *dry-run*. No existe un paso de confirmación que las convierta en escritura real en SISAV2.

## 1. Requisitos

- Cuenta UTEM con acceso a SISAV2 y conexión a la red UTEM/VPN.
- Un cliente MCP local, idealmente **Claude Desktop** para la demo.
- Para la ruta de respaldo: **Python 3.11+** y [uv](https://docs.astral.sh/uv/).
- Para la ruta portable en Windows: el artefacto de release `sisav2-mcp.exe`. Windows 10 puede
  requerir WebView2 Runtime; Windows 11 normalmente ya lo incluye.

## 2. Ruta A — ejecutable portable (Windows)

1. Obtén el `sisav2-mcp.exe` de una release preparada por el equipo; no se distribuye desde el
   checkout ni se versiona en Git.
2. Ábrelo sin argumentos. La GUI solicita la credencial UTEM, la verifica y permite registrar el MCP
   en los clientes locales detectados.
3. Selecciona Claude Desktop y termina el asistente. El cliente quedará configurado para ejecutar:

```text
<RUTA_ESTABLE>\sisav2-mcp.exe serve
```

4. Reinicia Claude Desktop por completo.

El ejecutable no firmado puede activar SmartScreen. Verifica que provenga de la release acordada antes
de decidir cómo proceder. Para construir o verificar el artefacto, consulta
[`build/BUILD.md`](build/BUILD.md).

> Antes de usar la ruta portable para Fase 2, ejecuta `sisav2-mcp.exe --help`: debe listar
> `index-demo`. Si solo muestra `serve`, el binario es anterior a 0.2.0; usa la ruta B o reconstruye
> el artefacto.

## 3. Ruta B — entorno `uv` / `.venv` (respaldo y desarrollo)

Esta ruta no depende del ejecutable y es la recomendada para corregir una configuración o ejecutar
la suite de pruebas.

```powershell
git clone <URL_DEL_REPO> sisav2-mcp
cd sisav2-mcp
uv venv --python 3.11
uv pip install -e ".[dev]"
uv run python -m sisav2_mcp.onboarding
```

El onboarding pide la clave con entrada oculta, verifica la identidad y la guarda en el keychain del
sistema operativo (Credential Manager en Windows). No la deja en archivos del repo. Útiles:

```powershell
uv run python -m sisav2_mcp.onboarding --check  # verificar credencial guardada
uv run python -m sisav2_mcp.onboarding --clear  # eliminarla del keychain
```

## 4. Preflight conectado de la demo

Ejecuta el preflight desde el mismo equipo y con la misma cuenta que usarás en Claude Desktop:

```powershell
uv run python -m sisav2_mcp.onboarding --check
uv run sisav2-mcp index-demo --cohort <RUTA_LOCAL_COHORTE>
```

`index-demo` lee por GET los detalles de los IDs declarados en el manifiesto local de cohorte, prepara
o refresca el índice de análisis y solo escribe la caché local. No modifica SISAV2. El primer preflight
puede descargar/cargar el modelo semántico, por lo que requiere red. No uses una cohorte con datos
personales ni la agregues a Git. Después, en Claude Desktop, ejecuta una consulta de lectura real antes
de iniciar la presentación. Si falla la red, la autenticación, la cohorte o el índice, detén la demo:
no hay fallback offline diseñado para simular una conexión.

El archivo de cohorte es JSON local: una lista de objetos, o un objeto con la clave `miembros`. Cada
miembro debe incluir al menos `idPostulacion`; puede agregar metadatos no sensibles como modalidad,
facultad o año. Por ejemplo:

> Parte de `docs/demo-cohort.example.json`, cópialo a `docs/demo-cohort.local.json` y amplíalo con la
> cohorte real autorizada de la demostración. El archivo `.local.json` está ignorado por Git.

```json
{
  "miembros": [
    { "idPostulacion": 1234, "modalidad": "PRE_GRADO", "anio": 2026 }
  ]
}
```

La secuencia completa y los prompts de ensayo están en [`docs/DEMO.md`](docs/DEMO.md).

## 5. Conectar Claude Desktop

Abre **Settings → Developer → Edit Config** y elige una de estas entradas dentro de `mcpServers`.

**Portable:**

```json
{
  "mcpServers": {
    "sisav2": {
      "command": "C:\\Users\\<USUARIO>\\AppData\\Local\\sisav2-mcp\\sisav2-mcp.exe",
      "args": ["serve"]
    }
  }
}
```

**Entorno `uv` / `.venv`:**

```json
{
  "mcpServers": {
    "sisav2": {
      "command": "<RUTA_REPO>\\.venv\\Scripts\\python.exe",
      "args": ["-m", "sisav2_mcp.server"]
    }
  }
}
```

Reinicia Claude Desktop por completo (Quit desde la bandeja, no solo cerrar la ventana). Algunas
instalaciones gestionadas pueden bloquear servidores locales; en ese caso usa un cliente MCP local
permitido por tu organización, sin sustituir la demo por datos inventados.

## 6. Desarrollo y verificación de release

Desde el checkout:

```powershell
uv run ruff check .
uv run mypy src
uv run python -m pytest -q
```

El hito histórico de **90 tests verdes** solo es válido cuando el último comando termina con éxito y
reporta precisamente 90 pruebas aprobadas. Para cualquier corte posterior, documenta el conteo real
que produzca la suite, junto con la fecha y el commit/revisión que corresponda.

## 7. Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| *No hay credenciales guardadas* | Corre `onboarding` y confirma red UTEM/VPN. |
| `index-demo` no puede preparar el índice | Revisa que la cohorte exista, esté autorizada, no contenga PII y que las dependencias estén instaladas. |
| El servidor no aparece en Claude Desktop | Confirma la ruta/args de la configuración y reinicia por completo. |
| Error de autenticación o timeout | Ejecuta `onboarding --check` y confirma acceso a `sso.utem.cl` y SISAV2. |
| Quiero ver logs | Define `SISAV2_LOG_LEVEL=DEBUG`; los logs salen por `stderr`, nunca por `stdout` del protocolo MCP. |
