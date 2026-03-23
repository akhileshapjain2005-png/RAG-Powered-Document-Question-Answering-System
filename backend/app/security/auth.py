"""Authentication: API keys and JWT / OIDC (JWKS) bearer tokens."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from typing import FrozenSet, Optional, Set

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidAlgorithmError, PyJWTError

logger = logging.getLogger(__name__)

# JWKS client reused to avoid per-request IdP hammering and CPU DoS
_jwks_client: Optional[PyJWKClient] = None

API_KEY_HEADER_NAME = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
API_KEY = os.getenv("API_KEY")
API_KEYS: Set[str] = {
    k.strip()
    for k in os.getenv("API_KEYS", "").split(",")
    if k.strip()
}
if API_KEY:
    API_KEYS.add(API_KEY)

# anonymous | api_key | jwt | jwt_or_api_key
AUTH_MODE = os.getenv("AUTH_MODE", "jwt_or_api_key").lower()

_ENV = os.getenv("ENV", "development").lower()
_ALLOW_ANON_EXPLICIT = os.getenv("ALLOW_ANONYMOUS_ACCESS", "").strip().lower()


def _allow_anonymous_access() -> bool:
    """Anonymous API access (no JWT / API key). Off by default in production."""
    if _ALLOW_ANON_EXPLICIT == "true":
        return True
    if _ALLOW_ANON_EXPLICIT == "false":
        return False
    return _ENV in ("development", "dev", "local", "test")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "").strip() or None
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "").strip() or None
JWT_TENANT_CLAIM = os.getenv("JWT_TENANT_CLAIM", "tenant_id")
JWT_ROLES_CLAIM = os.getenv("JWT_ROLES_CLAIM", "roles")
JWT_SECRET = os.getenv("JWT_SECRET", "").strip() or None
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "").strip().replace("\\n", "\n") or None
JWT_PUBLIC_KEY_FILE = os.getenv("JWT_PUBLIC_KEY_FILE", "").strip() or None
JWT_JWKS_URL = os.getenv("JWT_JWKS_URL", "").strip() or None

# Roles allowed to call /stats (comma-separated). Empty = any authenticated caller.
STATS_ALLOWED_ROLES: FrozenSet[str] = frozenset(
    r.strip()
    for r in os.getenv("STATS_ALLOWED_ROLES", "").split(",")
    if r.strip()
)

api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class SecurityContext:
    """Resolved caller identity for RBAC and audit."""

    owner_id: str
    subject: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: FrozenSet[str] = frozenset()
    auth_method: str = "anonymous"


def _stable_owner_id(tenant: str, subject: str) -> str:
    raw = f"{tenant}::{subject}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _roles_from_payload(payload: dict) -> FrozenSet[str]:
    raw = payload.get(JWT_ROLES_CLAIM)
    if raw is None:
        return frozenset()
    if isinstance(raw, list):
        return frozenset(str(x) for x in raw)
    if isinstance(raw, str):
        return frozenset(r.strip() for r in raw.replace(",", " ").split() if r.strip())
    return frozenset()


def _load_public_key_pem() -> Optional[str]:
    if JWT_PUBLIC_KEY:
        return JWT_PUBLIC_KEY
    if JWT_PUBLIC_KEY_FILE and os.path.isfile(JWT_PUBLIC_KEY_FILE):
        with open(JWT_PUBLIC_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def _jwt_configured() -> bool:
    return bool(JWT_SECRET or JWT_JWKS_URL or _load_public_key_pem())


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not JWT_JWKS_URL:
            raise HTTPException(status_code=503, detail="JWT JWKS not configured")
        ttl = int(os.getenv("JWT_JWKS_CACHE_TTL_SECONDS", "3600"))
        max_keys = int(os.getenv("JWT_JWKS_MAX_CACHED_KEYS", "32"))
        _jwks_client = PyJWKClient(
            JWT_JWKS_URL,
            cache_ttl=ttl,
            max_cached_keys=max_keys,
        )
    return _jwks_client


_JWT_DECODE_OPTS = {
    "verify_signature": True,
    "verify_exp": True,
    "verify_nbf": True,
    "verify_aud": bool(JWT_AUDIENCE),
    "verify_iss": bool(JWT_ISSUER),
}


def _decode_jwt(token: str) -> dict:
    leeway = int(os.getenv("JWT_LEEWAY_SECONDS", "60"))

    if JWT_JWKS_URL:
        jwks = _get_jwks_client()
        signing_key = jwks.get_signing_key_from_jwt(token)
        algs = [
            a.strip()
            for a in os.getenv("JWT_ALGORITHMS", "RS256,ES256").split(",")
            if a.strip()
        ]
        if not algs or "none" in {a.lower() for a in algs}:
            raise HTTPException(status_code=401, detail="Invalid JWT configuration")
        try:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=algs,
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
                options=_JWT_DECODE_OPTS,
                leeway=leeway,
            )
        except InvalidAlgorithmError as exc:
            logger.warning("JWT rejected (algorithm): %s", exc)
            raise HTTPException(status_code=401, detail="Invalid token algorithm") from exc

    if JWT_SECRET and JWT_ALGORITHM.upper().startswith("HS"):
        if JWT_ALGORITHM.upper() in ("HS256", "HS384", "HS512"):
            return jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                audience=JWT_AUDIENCE,
                issuer=JWT_ISSUER,
                options=_JWT_DECODE_OPTS,
                leeway=leeway,
            )

    pem = _load_public_key_pem()
    if not pem:
        raise HTTPException(status_code=503, detail="JWT validation not configured")

    alg = JWT_ALGORITHM.upper()
    if alg == "NONE" or not alg:
        raise HTTPException(status_code=401, detail="Invalid JWT algorithm")

    try:
        return jwt.decode(
            token,
            pem,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
            options=_JWT_DECODE_OPTS,
            leeway=leeway,
        )
    except InvalidAlgorithmError as exc:
        logger.warning("JWT rejected (algorithm): %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token algorithm") from exc


def _context_from_jwt_payload(payload: dict) -> SecurityContext:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub")

    tenant = payload.get(JWT_TENANT_CLAIM) or payload.get("tid") or payload.get("org_id")
    if tenant is None:
        tenant = "_default"
    tenant = str(tenant)

    roles = _roles_from_payload(payload)
    owner_id = _stable_owner_id(tenant, str(sub))
    return SecurityContext(
        owner_id=owner_id,
        subject=str(sub),
        tenant_id=tenant,
        roles=roles,
        auth_method="jwt",
    )


def _api_key_matches(provided: Optional[str]) -> bool:
    """Constant-time comparison per key (length must match for compare_digest)."""
    if not provided:
        return False
    for candidate in API_KEYS:
        if len(provided) != len(candidate):
            continue
        if hmac.compare_digest(provided.encode("utf-8"), candidate.encode("utf-8")):
            return True
    return False


def _context_from_api_key(key: str) -> SecurityContext:
    owner_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return SecurityContext(
        owner_id=owner_id,
        subject="api_key",
        tenant_id="_api_key",
        roles=frozenset({"api_key"}),
        auth_method="api_key",
    )


async def get_security_context(
    _request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> SecurityContext:
    """
    Resolve caller identity.

    AUTH_MODE:
      - anonymous: no auth (dev only)
      - api_key: require valid API key
      - jwt: require Bearer JWT
      - jwt_or_api_key: Bearer if present, else API key
    """
    jwt_ready = _jwt_configured()
    has_keys = bool(API_KEYS)

    token: Optional[str] = None
    if bearer and bearer.scheme.lower() == "bearer":
        token = bearer.credentials

    # Explicit modes
    if AUTH_MODE == "anonymous":
        return SecurityContext(owner_id="anonymous", subject="anonymous", tenant_id="_public", auth_method="anonymous")

    if AUTH_MODE == "jwt":
        if not jwt_ready:
            raise HTTPException(status_code=503, detail="JWT auth requested but not configured")
        if not token:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        try:
            payload = _decode_jwt(token)
            return _context_from_jwt_payload(payload)
        except HTTPException:
            raise
        except PyJWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if AUTH_MODE == "api_key":
        if not has_keys:
            raise HTTPException(status_code=503, detail="API key auth requested but no API_KEY(S) configured")
        if not _api_key_matches(api_key):
            raise HTTPException(status_code=401, detail="Unauthorized")
        return _context_from_api_key(api_key)

    # jwt_or_api_key (default)
    if token:
        if not jwt_ready:
            raise HTTPException(status_code=401, detail="Bearer token not accepted (JWT not configured)")
        try:
            payload = _decode_jwt(token)
            return _context_from_jwt_payload(payload)
        except HTTPException:
            raise
        except PyJWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if api_key and has_keys and _api_key_matches(api_key):
        return _context_from_api_key(api_key)

    if not has_keys and not jwt_ready and _allow_anonymous_access():
        return SecurityContext(owner_id="anonymous", subject="anonymous", tenant_id="_public", auth_method="anonymous")

    raise HTTPException(status_code=401, detail="Unauthorized")


async def get_owner_id(ctx: SecurityContext = Depends(get_security_context)) -> str:
    """Dependency: tenant-scoped storage owner id."""
    return ctx.owner_id


def require_stats_role(ctx: SecurityContext = Depends(get_security_context)) -> SecurityContext:
    """Stats may be restricted to certain JWT roles in enterprise deployments."""
    if not STATS_ALLOWED_ROLES:
        return ctx
    if ctx.auth_method == "api_key":
        allow_api = os.getenv("STATS_ALLOW_API_KEY", "true").lower() == "true"
        if allow_api:
            return ctx
        raise HTTPException(status_code=403, detail="Insufficient permissions for this endpoint")
    if not STATS_ALLOWED_ROLES.intersection(ctx.roles):
        raise HTTPException(status_code=403, detail="Insufficient permissions for this endpoint")
    return ctx
