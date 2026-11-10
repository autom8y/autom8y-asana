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

Verified-identity keying (2026-11-10):
  Buckets are chosen from VERIFIED identity only. SlowAPI runs inside
  ``JWTAuthMiddleware`` (see :func:`ensure_rate_limit_runs_after_auth`), and
  the key function reads the claims that middleware verified. A token's bytes
  are never trusted to pick a bucket on their own. This matches autom8y-data,
  whose key function reads an identity its auth layer stored after
  verification.
"""

import base64
import hashlib
import hmac
import json
import os
import warnings
from collections.abc import Callable
from typing import Any, TypeVar, cast

from autom8y_auth import ServiceClaims
from autom8y_log import get_logger
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.applications import Starlette

from autom8_asana.auth.dual_mode import AuthMode, detect_token_type

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

# Namespace for every other verified JWT caller: "jwt:{identity}[:{business_id}]".
VERIFIED_JWT_NAMESPACE = "jwt"

# Per-process HMAC key for PAT bucket keys. Never logged or exported.
_PAT_HASH_KEY = os.urandom(32)


def _bearer_token(request: Request) -> str | None:
    """Return the bearer token from the ``Authorization`` header, if any.

    Tokens of 8 characters or fewer are treated as absent, which keeps the
    previous minimum-length rule (``len("Bearer ") + 8``).
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    if len(token) <= 8:
        return None
    return token


def _decode_payload_segment(token: str) -> dict[str, Any] | None:
    """Decode the payload segment of a JWT-shaped token WITHOUT verifying it.

    The result is NEVER used on its own. :func:`_bound_verified_payload` only
    returns it after checking that it matches the claims the auth middleware
    verified for this request.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_b64 = parts[1]
    padding = (-len(payload_b64)) % 4
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + ("=" * padding)))
    except (ValueError, TypeError):
        # binascii.Error and json.JSONDecodeError are both ValueError subclasses.
        return None
    return payload if isinstance(payload, dict) else None


def _bound_verified_payload(token: str, claims: object) -> dict[str, Any] | None:
    """Return the token payload only if it is the token the claims came from.

    ``JWTAuthMiddleware`` sets ``request.state.claims`` only after it has
    verified the signature, issuer, expiry and audience of the token in this
    request's ``Authorization`` header. The payload is accepted here only when
    its ``sub``, ``iat`` and ``exp`` equal the verified claims, so a value read
    from it is covered by that signature. Claims that did not come from this
    token (for example the auth SDK's dev-mode bypass claims) do not bind, and
    the request is then treated as unverified.
    """
    payload = _decode_payload_segment(token)
    if payload is None:
        return None
    for field in ("sub", "iat", "exp"):
        if payload.get(field) != getattr(claims, field, None):
            return None
    return payload


def _non_empty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _verified_identity_key(token: str, claims: object) -> str | None:
    """Build a rate-limit key from verified JWT claims.

    Identity precedence matches ``write_authz.resolve_principal``:
    ``service_account_id`` (canonical ``sa.yaml_id``), then ``client_id``, then
    ``sub``. ``service_account_id`` is a ``ServiceClaims`` field from
    autom8y-auth 4.4.0. On 4.1.0 the SDK drops it during validation, so it is
    read from the bound, signature-covered payload instead. Both versions give
    the same key.

    Returns None when the claims do not bind to the presented token.
    """
    payload = _bound_verified_payload(token, claims)
    if payload is None:
        return None

    sa_id = None
    if isinstance(claims, ServiceClaims):
        sa_id = _non_empty_str(getattr(claims, "service_account_id", None)) or _non_empty_str(
            payload.get("service_account_id")
        )

    # Surface E: only a verified service token for the resolver SA goes to
    # the isolated SA namespace, whatever its business_id.
    if sa_id == SA_SERVICE_NAME:
        return SA_RATE_LIMIT_NAMESPACE

    identity = (
        sa_id
        or _non_empty_str(getattr(claims, "client_id", None))
        or _non_empty_str(getattr(claims, "sub", None))
    )
    if identity is None:
        return None
    key = f"{VERIFIED_JWT_NAMESPACE}:{identity}"
    business_id = _non_empty_str(getattr(claims, "business_id", None))
    if business_id is not None:
        key = f"{key}:{business_id}"
    return key


def _pat_key(token: str) -> str:
    """Key a PAT by a keyed hash of the WHOLE token, never a raw prefix.

    The HMAC key is random per process, which matches the per-process
    in-memory limiter storage. If the limiter moves to shared storage, this
    key must become a shared configured value so buckets agree across
    processes.
    """
    digest = hmac.new(_PAT_HASH_KEY, token.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"pat:{digest[:32]}"


def _get_rate_limit_key(request: Request) -> str:
    """Generate the rate-limit key from the verified caller identity.

    Bucket selection never trusts unverified token bytes. It relies on
    :func:`ensure_rate_limit_runs_after_auth`, which places SlowAPI inside
    ``JWTAuthMiddleware`` so verified claims are on ``request.state`` when this
    runs. Route-level ``@limiter.limit`` checks run inside the endpoint, which
    is also after authentication.

    Key resolution order:

    1. **Verified JWT.** If ``request.state.claims`` holds claims verified for
       this request's own bearer token:

       - a service token whose ``service_account_id`` is
         ``"asana-dataframe-resolver"`` returns ``"sa:asana-dataframe-resolver"``
         (Surface E isolation and the ``namespace="sa"`` 429 metric);
       - any other verified token returns ``"jwt:{identity}[:{business_id}]"``.

    2. **PAT** (a bearer token that is not JWT-shaped): ``"pat:{hmac}"``, a
       keyed hash of the full token. PATs are not verified locally, so each
       distinct PAT gets its own bucket, and PATs that share a prefix do not
       share a bucket. Per ADR-ASANA-002, different PATs have independent
       limits.
    3. **IP fallback**: unauthenticated requests (e.g. ``/docs``) and
       JWT-shaped tokens that were not verified return ``"ip:{addr}"``. The
       health probes (``/health``, ``/ready``, ``/health/deps``) are exempt
       from the limiter and never reach this function.

    Args:
        request: FastAPI request object.

    Returns:
        Rate limit key string.
    """
    token = _bearer_token(request)
    if token is not None:
        claims = getattr(request.state, "claims", None)
        if claims is not None:
            verified_key = _verified_identity_key(token, claims)
            if verified_key is not None:
                return verified_key
        if detect_token_type(token) is AuthMode.PAT:
            return _pat_key(token)

    ip = get_remote_address(request)
    return f"ip:{ip}"


def ensure_rate_limit_runs_after_auth(app: Starlette) -> None:
    """Place ``SlowAPIMiddleware`` inside ``JWTAuthMiddleware``.

    ``create_fleet_app`` documents the order "JWT before rate-limiting so
    limits can key on identity". Starlette's ``add_middleware`` puts each new
    middleware OUTSIDE the earlier ones, so registering JWT first and SlowAPI
    second made SlowAPI the outer layer, and it chose buckets before any token
    was verified. This moves SlowAPI to sit just inside ``JWTAuthMiddleware``
    and keeps every other relative position. If the order is already correct,
    it does nothing.

    Must be called before the app serves its first request (Starlette builds
    the middleware stack lazily on startup).

    Raises:
        RuntimeError: If either middleware is missing or registered more than
            once, so a factory change cannot silently undo this ordering.
    """
    from autom8y_auth import JWTAuthMiddleware
    from slowapi.middleware import SlowAPIMiddleware

    stack = app.user_middleware
    # Compare as plain objects: Starlette types ``Middleware.cls`` as a
    # factory protocol, which does not overlap a concrete middleware class.
    classes: list[object] = [mw.cls for mw in stack]
    rate_idx = [i for i, cls in enumerate(classes) if cls is SlowAPIMiddleware]
    auth_idx = [i for i, cls in enumerate(classes) if cls is JWTAuthMiddleware]
    if len(rate_idx) != 1 or len(auth_idx) != 1:
        raise RuntimeError(
            "rate-limit ordering: expected exactly one SlowAPIMiddleware and one "
            f"JWTAuthMiddleware, found {len(rate_idx)} and {len(auth_idx)}"
        )
    # user_middleware[0] is the OUTERMOST layer.
    if rate_idx[0] > auth_idx[0]:
        return
    rate_mw = stack.pop(rate_idx[0])
    remaining: list[object] = [mw.cls for mw in stack]
    new_auth_idx = next(i for i, cls in enumerate(remaining) if cls is JWTAuthMiddleware)
    stack.insert(new_auth_idx + 1, rate_mw)


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
#
# config_filename: without it, Limiter loads settings from a dotenv file in the
# working directory whenever one exists. Limiter settings come from code and
# the environment only, so point it at a fixed path that never exists. Starlette
# warns once when the named file is absent; that warning is expected here.
LIMITER_CONFIG_FILENAME = "/nonexistent/autom8-asana/slowapi-limiter-settings"

# In-process storage, matching the per-process limits documented above.
LIMITER_STORAGE_URI = "memory://"


def _build_limiter() -> Limiter:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=f"Config file '{LIMITER_CONFIG_FILENAME}' not found.",
        )
        return Limiter(
            key_func=_get_rate_limit_key,
            default_limits=[_get_rate_limit_string],
            enabled=True,
            config_filename=LIMITER_CONFIG_FILENAME,
            # Explicit, so RATELIMIT_* environment settings cannot redirect storage.
            storage_uri=LIMITER_STORAGE_URI,
        )


limiter = _build_limiter()


def get_limiter() -> Limiter:
    """Get the configured rate limiter instance.

    Returns:
        Configured SlowAPI Limiter.
    """
    return limiter


_HandlerT = TypeVar("_HandlerT", bound=Callable[..., Any])


def exempt_from_rate_limit(handler: _HandlerT) -> _HandlerT:
    """Exempt a route handler from every limit on :data:`limiter`.

    A typed wrapper around ``limiter.exempt`` (slowapi's decorator is
    unannotated). Apply it UNDER the route decorator, so the router registers
    the exempt wrapper as the endpoint.

    SlowAPI records the exemption as ``"{module}.{function name}"`` of the
    handler and ``SlowAPIMiddleware`` matches the endpoint by that string, so
    renaming or moving an exempt handler silently restores its limit. Pin the
    name in a test.
    """
    # slowapi 0.1.9 ships Limiter.exempt without annotations; this is the one
    # place that call is made.
    return cast("_HandlerT", limiter.exempt(handler))  # type: ignore[no-untyped-call]


__all__ = [
    "SA_NAMESPACE_LIMIT",
    "SA_RATE_LIMIT_NAMESPACE",
    "SA_RATE_LIMIT_RPM",
    "SA_SERVICE_NAME",
    "VERIFIED_JWT_NAMESPACE",
    "_get_rate_limit_key",
    "ensure_rate_limit_runs_after_auth",
    "exempt_from_rate_limit",
    "get_limiter",
    "limiter",
]
