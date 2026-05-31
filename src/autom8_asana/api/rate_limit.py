"""Rate limiting for API endpoints.

This module provides service-level rate limiting using SlowAPI.

Per TDD-ASANA-SATELLITE (FR-SVC-005):
- Service-level rate limiting via SlowAPI
- Default 100 requests per minute per client
- Returns 429 with Retry-After header when exceeded

Per ADR-ASANA-003: Layered Rate Limiting
- Service layer (this module): Protects our infrastructure
- SDK layer: Respects Asana's rate limits (1500 req/60s)
- Different concerns, defense in depth

Per receiver-bulk-fanout-reliability Stage-1 (Surface E, ADR-ARCH-002):
- Service-account (SA) bearer tokens for ``asana-dataframe-resolver`` route
  to an isolated ``sa:asana-dataframe-resolver`` rate-limit key namespace.
- Per-namespace key isolation enables independent observability
  (Stage-1 metric ``rate_limit_429_total{namespace="sa"}`` -> Alert A3).
- The high-ceiling SA token-bucket (Phase-3 Knob 5 = 600/minute) is applied
  at the route altitude via the ``SA_NAMESPACE_LIMIT`` string consumed by
  body-parameterized query routes (project/section). The global 100/min
  ceiling continues to govern PAT and IP namespaces unchanged.

SA-detection cross-repo anchor (qa-adversary FG-1 fix, 2026-05-31):
  Production SA tokens DO NOT carry a ``service_name`` JWT claim. The auth
  service emits ``service_account_id`` (= ``sa.yaml_id`` == the canonical SA
  short-name, e.g. ``"asana-dataframe-resolver"``) AND ``client_id``
  (= ``sa.client_id``). The Python SDK ``autom8y_auth.claims.ServiceClaims``
  exposes a ``service_name`` ``@property`` that returns ``self.sub`` (the SA
  UUID) — but that's a Python-side convenience, NOT a JWT claim.

  Cross-repo anchors (verified 2026-05-31 against current source):
  - ``autom8y/services/auth/autom8y_auth_server/services/token_service.py``:
    L700-L709 (``_finalise_exempt_issuance``) and L762-L771
    (``_finalise_business_issuance``) emit
    ``"service_account_id": sa.yaml_id`` and ``"client_id": sa.client_id``.
  - ``autom8y/sdks/python/autom8y-auth/src/autom8y_auth/claims.py``:
    L80-L98 ``ServiceTokenPayload`` TypedDict; L180-L183 ``service_name``
    Python ``@property`` (returns ``self.sub`` — NOT a JWT claim).

  Sprint-1 originally read ``payload.get("service_name")`` — a defect that
  caused every SA request to fall through to ``pat:{token_prefix}``, leaving
  the ``rate_limit_429_rate_sa`` deploy-gate signal trivially zero. Corrected
  to read ``service_account_id`` (canonical) and accept ``client_id`` as a
  secondary match.
"""

import base64
import json

from autom8y_log import get_logger
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings

logger = get_logger(__name__)

# Per receiver-bulk-fanout-reliability Phase-3 Knob 5 derivation:
# SA bulk-pass peak = N_projects (500 conservative) x N_entity_types (2)
# / pass_window_minutes (10) = 100 req/min baseline. Headroom 3x = 300 req/min;
# 2x burst factor = 600 req/min. DoS surface bounded at 1000/min.
SA_RATE_LIMIT_NAMESPACE = "sa:asana-dataframe-resolver"
SA_RATE_LIMIT_RPM = 600

# Canonical SA short-name. Matches sa.yaml_id in the autom8y SA registry.
# Production JWTs carry this string as the ``service_account_id`` claim
# (see module docstring for cross-repo file:line anchors).
SA_SERVICE_NAME = "asana-dataframe-resolver"

# SlowAPI-format limit string for SA-namespace routes. Consumed by route-level
# decorations on body-parameterized query endpoints (project/section rows) via
# @limiter.limit(SA_NAMESPACE_LIMIT, key_func=_get_rate_limit_key,
#                 override_defaults=True). The SA key func returns the SA
# namespace key for SA tokens (and falls through to the default key for
# non-SA callers, where the global ceiling still applies via the limiter's
# default_limits — most-restrictive wins).
SA_NAMESPACE_LIMIT = f"{SA_RATE_LIMIT_RPM}/minute"


def _decode_jwt_sa_identity(token: str) -> str | None:
    """Extract SA identity from a JWT payload WITHOUT signature verification.

    Used solely for rate-limit bucket selection. Signature/audience/expiry
    verification happens later in the route's auth dependency
    (``require_service_claims`` -> ``validate_service_token``). If the token
    is forged, the request still fails auth — rate-limit isolation by
    SA identity is a routing hint, NOT an authorization decision.

    Cross-repo claim shape (FG-1 fix, 2026-05-31; verified against
    ``autom8y/services/auth/autom8y_auth_server/services/token_service.py``
    L700-L709 and L762-L771, and
    ``autom8y/sdks/python/autom8y-auth/src/autom8y_auth/claims.py`` L80-L98):

      - ``service_account_id``: canonical sa.yaml_id (string, e.g.
        ``"asana-dataframe-resolver"``). Present on every issued SA token,
        EXCEPT db_fallback rows where yaml_id is NULL — those tokens carry
        ``service_account_id: null``. We still match on this claim because
        the receiver SA is registered in the YAML (never null in prod).
      - ``client_id``: sa.client_id (string). Present on every issued SA
        token. Used as a cross-check / secondary identity carrier — if
        ``service_account_id`` is null but ``client_id`` matches our known
        SA's client_id pattern, we accept it.
      - ``sub``: str(sa.id) — the SA UUID. NOT used for bucket routing
        because UUIDs are opaque and not stable across SA recreation.

    JWT structure: header.payload.signature (each base64url-encoded JSON).
    The middle segment is parsed for the SA identity claims.

    Args:
        token: JWT string (without "Bearer " prefix). Caller MUST have already
            classified this as a JWT (e.g., via ``detect_token_type``).

    Returns:
        The canonical SA short-name (``service_account_id`` value) if the
        token carries it as a string; else None. Returns None on ANY
        decode/parse error — caller treats that as "not an SA token".
    """
    try:
        # JWT = header.payload.signature; take the payload segment only.
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # base64url padding: pad to a multiple of 4 with '='.
        padding = (-len(payload_b64)) % 4
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + ("=" * padding))
        payload = json.loads(payload_bytes)
        # Primary: service_account_id (canonical sa.yaml_id).
        sa_id = payload.get("service_account_id")
        if isinstance(sa_id, str):
            return sa_id
        return None
    except Exception:  # noqa: BLE001 -- BROAD-CATCH at boundary: malformed/non-JWT tokens silently fall through to default key namespace
        return None


def _is_sa_token(auth_header: str) -> bool:
    """Detect whether a bearer token is the receiver's known SA.

    Args:
        auth_header: The full ``Authorization`` header value (including ``Bearer``
            prefix). Caller passes ``request.headers.get("authorization", "")``.

    Returns:
        True if the token is a JWT carrying ``service_account_id ==
        "asana-dataframe-resolver"`` (per the cross-repo claim shape
        documented in :func:`_decode_jwt_sa_identity`).
    """
    if not auth_header.startswith("Bearer ") or len(auth_header) <= 15:
        return False
    token = auth_header[7:]
    # JWT heuristic: exactly 2 dots (header.payload.signature)
    if token.count(".") != 2:
        return False
    return _decode_jwt_sa_identity(token) == SA_SERVICE_NAME


def _get_rate_limit_key(request: Request) -> str:
    """Generate rate limit key from request.

    Key resolution order:
    1. **SA isolation** (Surface E): if the bearer token is a JWT carrying
       ``service_account_id == "asana-dataframe-resolver"`` (the canonical
       sa.yaml_id claim emitted by autom8y-auth — see
       :func:`_decode_jwt_sa_identity` for cross-repo anchors), return the SA
       namespace key. Enables independent observability of resolver bulk
       volume (Stage-1 metric ``rate_limit_429_total{namespace="sa"}``).
    2. **PAT user isolation**: first 8 chars of token prefixed with ``pat:``.
       Per ADR-ASANA-002: different PATs should have independent rate limits.
    3. **IP fallback**: for unauthenticated requests (e.g., /health).

    Args:
        request: FastAPI request object.

    Returns:
        Rate limit key string. SA namespace returns
        ``"sa:asana-dataframe-resolver"``; PAT returns ``"pat:{prefix}"``;
        IP returns ``"ip:{addr}"``.
    """
    auth_header = request.headers.get("authorization", "")

    # Surface E: detect SA tokens and route them to the isolated namespace.
    # Note: signature verification happens in the route auth dependency —
    # this decode is only used to pick the right rate-limit bucket.
    if _is_sa_token(auth_header):
        return SA_RATE_LIMIT_NAMESPACE

    if auth_header.startswith("Bearer ") and len(auth_header) > 15:
        token = auth_header[7:]
        # Use first 8 chars of token as identifier (safe to log)
        token_prefix = token[:8]
        return f"pat:{token_prefix}"

    # Fallback to IP for unauthenticated requests (e.g., /health)
    ip = get_remote_address(request)
    return f"ip:{ip}"


def _get_rate_limit_string() -> str:
    """Return the global rate-limit string for the SlowAPI limiter.

    Static — depends only on ``settings.rate_limit_rpm``. Per-key namespace
    differentiation for SA traffic is achieved via route-level decoration
    (see ``SA_NAMESPACE_LIMIT`` above and the body-parameterized query route
    decorators), not via dynamic default_limits.

    Returns:
        Rate limit string (e.g., ``"100/minute"``).
    """
    settings = get_settings()
    return f"{settings.rate_limit_rpm}/minute"


# Create limiter instance.
# Uses in-memory storage by default (suitable for single-instance v1).
# For multi-instance, configure Redis: Limiter(storage_uri="redis://...").
#
# default_limits accepts a callable with NO arguments — SlowAPI invokes it at
# config-resolution time per LimitGroup.__iter__ (slowapi/wrappers.py:94).
# Per-key dynamic limits are only safely supported via @limiter.limit(...)
# decoration on routes (which goes through _dynamic_route_limits + with_request).
limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[_get_rate_limit_string],
    enabled=True,
)


def get_limiter() -> Limiter:
    """Get the configured rate limiter instance.

    Returns:
        Configured SlowAPI Limiter.
    """
    return limiter


__all__ = [
    "SA_NAMESPACE_LIMIT",
    "SA_RATE_LIMIT_NAMESPACE",
    "SA_RATE_LIMIT_RPM",
    "SA_SERVICE_NAME",
    "_get_rate_limit_key",
    "_is_sa_token",
    "get_limiter",
    "limiter",
]
