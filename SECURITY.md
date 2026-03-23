# Security notes

## Authentication

- **Production**: set `JWT_*` and/or `API_KEY` / `API_KEYS`. Anonymous access to the API is **off** by default when `ENV=production` and `ALLOW_ANONYMOUS_ACCESS` is not `true`.
- **API keys**: compared with constant-time equality per key length class (`hmac.compare_digest`).
- **JWT**: signature required; **`none` algorithm** is not allowed; JWKS client is **cached** to reduce DoS risk against the IdP.

## Metrics

- `GET /metrics` (Prometheus): set **`METRICS_TOKEN`** and send it as **`X-Metrics-Token`** or **`Authorization: Bearer ...`**. Do not expose `/metrics` on the public internet.

## Uploads

- **Content-Length** is validated safely (invalid header → 400).
- **Filename** is sanitized to basename-only safe strings before metadata/storage (path traversal mitigation).
- **PDF / text** extraction is bounded by **`MAX_PDF_PAGES`** and **`MAX_EXTRACTED_TEXT_CHARS`**.

## HTTP headers

- **CSP** is not applied to JSON API responses (`/api/*`, `/metrics`) to avoid confusing security scanners and clients; HTML UIs should set CSP at the CDN/reverse proxy.

## Frontend tokens

- Storing **access tokens in `sessionStorage`** is visible to XSS. Prefer **HttpOnly cookies** + CSRF protections with a BFF, or a hardened OIDC client; never commit real tokens to the repo.
