# Arquitectura multiusuario — evolución posterior a la demo

## Decisión y límite actual

La demo actual es un MCP **local por usuario**: Claude Desktop inicia un proceso `stdio`, el proceso
recupera la credencial UTEM de ese usuario desde su keychain y las tools de escritura devuelven solo
previews *dry-run*. No hay servicio compartido, escritura remota ni cuenta de servicio en esta versión.

Para una operación institucional multiusuario, la dirección recomendada es un MCP remoto con transporte
HTTP, autenticación **OAuth 2.1/OIDC con PKCE**, sesión aislada por usuario y autorización contra la
fuente de roles de SISAV2. No se debe reutilizar la contraseña ROPC ni un keychain local como mecanismo
de autenticación de un servicio central.

## Alternativas evaluadas

| Alternativa | Ventaja | Límite | Decisión |
|---|---|---|---|
| MCP local por usuario | Simple, conserva la identidad de SISAV2 y no centraliza secretos. | No permite colaboración ni operación centralizada. | Adecuada para la demo actual. |
| MCP remoto + PKCE | Sesión individual, revocación, auditoría y despliegue centralizado. | Requiere registrar redirect URIs, hosting y aprobación institucional. | Recomendada para producción. |
| Cuenta de servicio compartida | Simple para tareas programadas. | Pierde trazabilidad personal y amplía el radio de impacto. | Solo para jobs de lectura aprobados, nunca para suplantar usuarios. |

## Flujo objetivo del servicio remoto

```text
Cliente MCP
  -> OAuth/OIDC + PKCE
  -> sesión cifrada y de corta vida del MCP remoto
  -> resolución de usuario y permisos en SISAV2
  -> policy/RBAC + validación de herramienta
  -> lectura o workflow de aprobación de escritura
  -> auditoría inmutable de la operación
```

1. El cliente inicia OAuth/OIDC con PKCE; el servicio recibe tokens de sesión de corta duración, no la
   contraseña del usuario.
2. El MCP asocia cada llamada a `subject`, audiencia, expiración, organización y una `request_id`.
3. Antes de cada tool, resuelve o refresca roles/permisos desde la fuente autorizada de SISAV2. Los
   permisos cacheados expiran pronto y nunca se comparten entre sujetos.
4. Las herramientas aplican la política de mínimo privilegio. Un rol habilita solo la intención
   correspondiente, no acceso general a endpoints.
5. Para una futura escritura real, el servicio registra el preview, exige una aprobación explícita
   ligada a ese `request_id`, aplica el cambio solo con un contrato de API verificado y relee el efecto.

## Autenticación: ciclo del token y factibilidad de Keycloak

En la demo local el grant es ROPC (password) contra Keycloak: `auth/ropc.py` cachea el access token, lo
renueva con el `refresh_token` mientras siga vigente y, al expirar también el refresh, hace re-login
silencioso con la credencial del keychain. El access token dura ~10 min (ver
`docs/discovery/AUTH_FLOW.md`), así que el refresh es frecuente; el token nunca se persiste en disco.

Salvedad de factibilidad: el realm de SISAV2 ya usa PKCE (S256) para su cliente web, pero un cliente
público nuevo para el MCP podría no tener PKCE habilitado por el administrador del realm. Mientras no se
registre y autorice ese cliente (con sus redirect URIs), el authorization-code + PKCE no está disponible
y el fallback es el ROPC actual. Registrar el cliente público MCP y confirmar PKCE es, por tanto, un
prerrequisito institucional del servicio remoto, no un detalle de implementación.

En el servicio remoto el refresh deja de vivir en el cliente: la sesión de corta vida se emite y rota del
lado del MCP remoto, se revoca al cerrar, expirar o cambiar permisos, y el cliente nunca ve la contraseña.

## Datos, secretos y auditoría

- **Secretos:** cifrar tokens en reposo, limitar su TTL y no registrar `Authorization`, contraseñas,
  cuerpos sensibles ni PII. Rotar claves y revocar sesión al cerrar, expirar o cambiar permisos.
- **Aislamiento:** separar cachés por `subject` y organización. Una cohorte semántica debe tener control
  de acceso, minimización de texto y un TTL; las cachés locales de la demo no migran automáticamente al
  servicio.
- **Auditoría:** almacenar `request_id`, sujeto pseudonimizado, herramienta, resultado de RBAC,
  timestamp, huella del preview, acción aprobada/rechazada y resultado de read-back. El log no guarda
  el texto completo ni datos personales salvo que una política institucional lo autorice.
- **Operación:** alertar por denegaciones anómalas, errores de autenticación, reintentos y cambios de
  permiso. Rate limiting por identidad: una ventana por `subject` (p. ej. N llamadas/min de lectura) con
  un presupuesto más estricto para las tools mutantes, respuesta `429` con `Retry-After` y backoff; ante
  abuso o error sistémico, un circuito de apagado desactiva toda tool mutante sin frenar la lectura. Hoy
  el cliente ya respeta `429` + backoff contra SISAV2; el límite por identidad se agrega en el borde del
  servicio remoto.

## Distribución y onboarding a escala (5–10 analistas)

Hoy cada analista se instala con un ejecutable portable de auto-servicio (`setup_gui/`): una pantalla
pide la cuenta UTEM, auto-detecta los clientes (Claude Desktop / Codex), guarda la credencial cifrada en
el keychain del SO y registra el servidor, sin pasos de desarrollador. Para 5–10 analistas eso es
distribuir un `.exe` y la guía de una página (`docs/MANUAL-ANALISTA.md`); no hay servidor que operar.

El límite es que ese modelo corre un proceso local por analista, con la credencial en cada máquina: no
hay estado compartido ni operación centralizada, y depende de que cada quien ejecute el instalador.

Escalar significa mover el servidor a un MCP remoto único (sección anterior): el analista deja de instalar
un binario y solo inicia sesión OAuth desde su cliente; el onboarding pasa a ser dar de alta la identidad
en el proveedor, con revocación y auditoría centralizadas. El instalador de auto-servicio es el puente de
la fase local; el servicio remoto es el destino cuando el número de analistas o la necesidad de
colaboración lo justifiquen.

## Camino de adopción

1. Mantener la demo en *dry-run* y terminar el recon supervisado de contratos de escritura en un entorno
   autorizado.
2. Registrar los redirects PKCE y definir dueño institucional de OAuth, secretos, auditoría y soporte.
3. Implementar el transporte remoto con lectura primero; probar aislamiento con al menos dos identidades
   y roles distintos.
4. Incorporar una única escritura de bajo riesgo detrás de aprobación, allowlist, auditoría y pruebas de
   no regresión; ampliar solo tras revisión de seguridad.

Nada de este diseño activa escritura en la demo ni valida endpoints de escritura de SISAV2. Es una guía
de arquitectura para una fase posterior autorizada.
