# Enterprise deployment guide

This document describes how to run RAG-DocQA in an **enterprise-style** environment: SSO/OIDC, tenant isolation, auditability, observability, and safe API boundaries.

## API versioning

- **Stable contract**: HTTP routes live under **`/api/v1/*`**.
- **Browser / gateway**: You may keep calling **`/api/*`** from the SPA; the bundled **nginx** rewrites `/api/...` → `/api/v1/...`.
- **Local Vite dev**: `vite.config.js` rewrites `/api` → `/api/v1` for the same behavior.

## Authentication models

### 1) JWT / OIDC (recommended for users)

Configure one of:

| Method | Environment |
|--------|-------------|
| **JWKS** (Auth0, Azure AD, Okta, Keycloak, etc.) | `JWT_JWKS_URL` |
| **RS256 public key PEM** | `JWT_PUBLIC_KEY` or `JWT_PUBLIC_KEY_FILE` |
| **HS256 (dev only)** | `JWT_SECRET` + `JWT_ALGORITHM=HS256` |

Optional validation:

- `JWT_ISSUER`, `JWT_AUDIENCE`
- `JWT_ALGORITHMS` (comma list) when using JWKS (default `RS256,ES256`)

Claims:

- **`sub`** (required) — stable user id  
- **Tenant** — `tenant_id` by default (`JWT_TENANT_CLAIM` to override). Falls back to `_default` if absent.
- **Roles** — `roles` claim (`JWT_ROLES_CLAIM`), list or space-separated string.

Storage isolation uses a stable hash of **`tenant_id` + `sub`** (never stores raw PII in `owner_id`).

### 2) API keys (machine-to-machine)

- `API_KEY` and/or comma-separated `API_KEYS`
- Header `X-API-Key` (override with `API_KEY_HEADER_NAME`)

### 3) Mode

`AUTH_MODE`:

| Value | Behavior |
|-------|----------|
| `jwt_or_api_key` | Bearer JWT if present; else API key; else anonymous only if neither JWT nor API keys are configured |
| `jwt` | Bearer JWT only |
| `api_key` | API key only |
| `anonymous` | **Dev only** — no auth |

## Authorization (RBAC)

- **`GET /api/v1/stats`**: optional role gate via `STATS_ALLOWED_ROLES` (comma-separated).  
- API-key callers: allowed by default (`STATS_ALLOW_API_KEY=true`). Set to `false` to force JWT roles for stats.

## Audit logging

Logger: **`app.audit`**. Each line is **one JSON object** suitable for centralized logging (Splunk, ELK, Datadog, CloudWatch).

Toggle: `AUDIT_LOG_ENABLED` (default `true`).

Optional high-volume events:

- `AUDIT_LOG_ASK=true` — logs ask/stream (can include sensitive text in metadata; use carefully).

## Observability

- **Prometheus**: `GET /metrics` when `ENABLE_METRICS=true` (default). Restrict at the network / ingress (do not expose publicly).
- **Request correlation**: `X-Request-ID` echoed on responses; also logged on access lines.

## Security hardening checklist

- [ ] Set `AUTH_MODE` to `jwt` or `jwt_or_api_key` with real IdP config; avoid `anonymous` outside dev.
- [ ] Configure `API_KEY` / `API_KEYS` for automation, or rely on JWT only.
- [ ] Set `ENABLE_API_DOCS=false` in production unless Swagger is required internally.
- [ ] Keep backend off the public internet; terminate TLS at ingress; nginx → backend on Docker network only.
- [ ] Do **not** ship end-user JWTs via `VITE_BEARER_TOKEN` (build-time). Prefer `sessionStorage` + your login flow, or a BFF pattern.
- [ ] Review `CORS_ALLOWED_ORIGINS` for your real front-end origins.

## Frontend token storage (SSO)

The SPA reads an access token from:

1. `import.meta.env.VITE_BEARER_TOKEN` (demo / CI only), or  
2. `sessionStorage[VITE_AUTH_TOKEN_STORAGE_KEY]` (default key `rag_access_token`)

Integrate your OIDC client to set `sessionStorage` after login, or switch to a backend-for-frontend that sets HttpOnly cookies (requires CSRF design).
