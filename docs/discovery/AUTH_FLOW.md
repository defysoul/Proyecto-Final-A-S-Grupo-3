# Flujo de autenticación — SISAV2 (Keycloak / OIDC)

> SSO en `sso.utem.cl`, realm **`prod`**. **Tokens/cookies REDACTADOS en todo este documento.**
> Fecha de captura: 2026-06-07.

## 1. Endpoints OIDC (`.well-known/openid-configuration`)
Fuente: `GET https://sso.utem.cl/auth/realms/prod/.well-known/openid-configuration` (200).

- `issuer`: `https://sso.utem.cl/auth/realms/prod`
- `authorization_endpoint`: `https://sso.utem.cl/auth/realms/prod/protocol/openid-connect/auth`
- `token_endpoint`: `https://sso.utem.cl/auth/realms/prod/protocol/openid-connect/token`
- `userinfo_endpoint`: `.../openid-connect/userinfo`
- `end_session_endpoint`: `.../openid-connect/logout`
- `jwks_uri`: `.../openid-connect/certs`
- `introspection_endpoint`: `.../openid-connect/token/introspect`
- `grant_types_supported`: **`authorization_code`**, `implicit`, **`refresh_token`**, **`password`**, `client_credentials`
- `response_types_supported`: `code`, `none`, `id_token`, `token`, …
- `response_modes_supported`: `query`, `fragment`, `form_post`
- `scopes_supported`: `openid`, `address`, `email`, `profile`, `roles`, **`offline_access`**, `employeeNumber`, `web-origins`, `phone`
- `code_challenge_methods_supported`: `plain`, **`S256`**
- `token_endpoint_auth_methods_supported`: `private_key_jwt`, `client_secret_basic`, `client_secret_post`, `client_secret_jwt` (para clientes **confidenciales**; un cliente público usa `none`)
- `id_token_signing_alg`: RS256/ES256/… · `claims`: sub, iss, name, given_name, family_name, preferred_username, email

## 2. Cliente de la SPA (observado en el redirect de login)
Al abrir `https://sisav2.utem.cl` se redirige a:
```
.../openid-connect/auth?client_id=SISAV2
  &redirect_uri=https%3A%2F%2Fsisav2.utem.cl%2F
  &response_type=code&response_mode=fragment&scope=openid
  &state=<...>&nonce=<...>
  &code_challenge=<REDACTED>&code_challenge_method=S256
```
- `client_id`: **`SISAV2`**
- Tipo de cliente: **público** (usa PKCE, sin client_secret en el flujo)
- **PKCE: SÍ — `code_challenge_method=S256`** (la SPA ya lo usa)
- `redirect_uri`: `https://sisav2.utem.cl/` · `response_mode=fragment`
- **Observación 2026-06-08:** el cliente acepta `redirect_uri` con **rutas variables** bajo el mismo
  origen — al navegar a una ruta profunda, el redirect usa p. ej.
  `redirect_uri=https://sisav2.utem.cl/vcm-pregrado/postulaciones`. Es decir, la validación de
  redirect parece basada en patrón/origen `https://sisav2.utem.cl/*`, no en una URI exacta. **Esto
  NO confirma loopback** (origen distinto).
- **PROBE 2026-06-08 (caveat de loopback RESUELTO — solo GETs, sin cambiar estado del servidor):**
  contra `authorization_endpoint` con `client_id=SISAV2`, mismos `response_type/scope/code_challenge`,
  variando solo `redirect_uri`:
  | Probe | `redirect_uri` | Resultado |
  |---|---|---|
  | A | `http://localhost:8765/callback` | **HTTP 400** (página de error con `redirect_uri`) |
  | B (control) | `https://sisav2.utem.cl/` | **HTTP 200** (login `kc-form-login`/`username`/`password`) |
  | C | `http://127.0.0.1:8765/callback` | **HTTP 400** (mismo error) |
  Como A/C difieren de B **solo** en `redirect_uri`, queda **PROBADO que el cliente `SISAV2` rechaza
  redirects loopback** (localhost y 127.0.0.1). → PKCE-loopback **no es viable** en v1 sin que UTEM
  registre un redirect loopback para el cliente.

## 3. Tokens (confirmado tras login — 2026-06-07)
- **Access token: JWT firmado RS256** (header `alg=RS256`, `kid=<...>`).
- **Vida del access token: 600 s (~10 min)** → `exp - iat = 600`. Implica refresh frecuente.
- Claims observados: `iss=https://sso.utem.cl/auth/realms/prod`, `aud=account`, `azp=SISAV2`,
  `sub=<uuid>`, `acr=1`, `allowed-origins=["https://sisav2.utem.cl"]`,
  `scope="openid email profile employeeNumber"`, `session_state`, `nonce`, `auth_time`, +
  claims de PII (`name`, `preferred_username`, `email`, `given_name`, `family_name`,
  `group`, `employeeNumber`) — **redactados/anonimizados** en los samples.
- `realm_access.roles = ["offline_access","uma_authorization"]` y
  `resource_access.account.roles = ["manage-account","manage-account-links","view-profile"]`.
  ⚠️ **Los roles de aplicación de SISAV2 (Admin, Analista, Aprobador, etc.) NO vienen en el JWT** —
  se resuelven con `GET /usuarios/verifica-token` (RBAC a nivel de app). **Dato clave Fase 1:**
  para conocer permisos del usuario, el server debe llamar a `verifica-token`, no leer el JWT.
- Se adjunta a la API como header `Authorization: Bearer <REDACTED>` (confirmado en todas las
  llamadas a `sisav2-api.utem.cl`).

## 5. API protegida
- **Base URL del backend: `https://sisav2-api.utem.cl`** (AWS API Gateway — headers `x-amz-*`).
- CORS abierto (`access-control-allow-origin: *`); métodos `GET/POST/PUT/PATCH/DELETE/...`.
- Primera llamada tras login: `GET /usuarios/verifica-token` (perfil + roles + permisos).

## 4. CONCLUSIÓN — grant para la Fase 1  ⭐ (ACTUALIZADA 2026-06-08 tras el probe)
- **Caveat de loopback: RESUELTO (rechazado).** El probe A/B/C (ver §2) prueba que el cliente
  público `SISAV2` **rechaza** `redirect_uri` loopback (`http://localhost:*` y `http://127.0.0.1:*`
  → HTTP 400). Por lo tanto **Authorization Code + PKCE con callback local no es viable en v1.**
- **DECISIÓN v1: `password` grant (ROPC)** — habilitado en el realm (`grant_types_supported` incluye
  `password`), no requiere `redirect_uri` registrado, funciona para cliente público. Credenciales en
  el **keychain del SO** (Windows Credential Manager vía `keyring`): login, refresh (`refresh_token`)
  y re-autenticación **silenciosos**, sin navegador. Roles de app vía `GET /usuarios/verifica-token`
  (no están en el JWT).
- **Ruta de upgrade a PKCE (diferida):** habilitar Authorization Code + PKCE en cuanto **UTEM
  registre un redirect loopback** (`http://localhost:*` / `http://127.0.0.1:*`) para el cliente
  `SISAV2`, o registre un cliente aparte para la app local. La capa `auth/` se diseña tras una
  interfaz `TokenProvider` para conmutar sin reescribir tools/client.
- Detalle de la decisión y su impacto en el diseño: `docs/discovery/RECONCILIATION.md` §4.
