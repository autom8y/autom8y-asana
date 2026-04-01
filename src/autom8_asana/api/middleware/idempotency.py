"""RFC 8791 Idempotency-Key middleware for mutating S2S endpoints.

Per ADR-omniscience-idempotency:
- HD-05: Client-provided Idempotency-Key header with server-derived fallback
- R-006: Requests without the header behave exactly as before (additive contract)
- HD-05-06: Two-phase claim protocol for /v1/intake/business

Eligible endpoints (IDEMPOTENT_ENDPOINTS):
    POST  /v1/intake/business
    POST  /v1/intake/route
    POST  /v1/tasks/{task_gid}/custom-fields
    PATCH /api/v1/entity/{entity_type}/{gid}

Middleware stack position (outer to inner execution):
    1. CORSMiddleware
    2. IdempotencyMiddleware   <-- this module
    3. SlowAPIMiddleware
    4. RequestLoggingMiddleware
    5. RequestIDMiddleware
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from autom8_asana.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.types import ASGIApp

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Key validation constants (per ADR Section 3.2)
# ---------------------------------------------------------------------------

_KEY_MIN_LENGTH = 8
_KEY_MAX_LENGTH = 256
_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9\-_.]+$")

# ---------------------------------------------------------------------------
# Eligible endpoint path templates (per ADR Section 3.5)
#
# Path matching is done via string patterns against the actual request path.
# Path parameters are matched via regex groups.
# ---------------------------------------------------------------------------

IDEMPOTENT_ENDPOINTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/v1/intake/business"),
        ("POST", "/v1/intake/route"),
        ("POST", "/v1/tasks/{task_gid}/custom-fields"),
        ("PATCH", "/api/v1/entity/{entity_type}/{gid}"),
    }
)

# Compiled regex patterns for path matching.
# Converts path templates like "/v1/tasks/{task_gid}/custom-fields"
# into regex patterns like r"^/v1/tasks/[^/]+/custom-fields$".


def _compile_endpoint_pattern(template: str) -> re.Pattern[str]:
    """Convert a path template to a compiled regex pattern.

    Replaces ``{param}`` placeholders with ``[^/]+`` to match a single
    path segment, then anchors the pattern with ``^...$``.
    """
    regex = re.sub(r"\{[^}]+\}", r"[^/]+", template)
    return re.compile(f"^{regex}$")


_ENDPOINT_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (method, _compile_endpoint_pattern(template), template)
    for method, template in IDEMPOTENT_ENDPOINTS
]

# Default TTL for stored responses (24 hours per RFC 8791)
DEFAULT_TTL_SECONDS = 86400

# Default service name when JWT claims are unavailable
_DEFAULT_SERVICE = "unknown"


# ---------------------------------------------------------------------------
# Stored response dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredResponse:
    """Immutable record of a previously executed response.

    Attributes:
        status: "processing" (sentinel) or "complete" (finalized).
        request_fingerprint: SHA-256 hex digest of the original request body.
        response_status: HTTP status code of the original response.
        response_body: Raw response body bytes.
        response_headers: Subset of headers to replay (Content-Type, etc.).
        created_at: ISO 8601 timestamp of original execution.
    """

    status: str
    request_fingerprint: str
    response_status: int
    response_body: bytes
    response_headers: dict[str, str]
    created_at: str


# ---------------------------------------------------------------------------
# Store protocol and in-memory implementation
# ---------------------------------------------------------------------------


@runtime_checkable
class IdempotencyStore(Protocol):
    """Protocol for idempotency key storage backends.

    Three concrete implementations exist:
    - InMemoryIdempotencyStore: for dev/test (this module)
    - DynamoDBIdempotencyStore: for production (this module)
    - NoopIdempotencyStore: passthrough for graceful degradation (this module)
    """

    async def get(self, pk: str, sk: str) -> StoredResponse | None:
        """Read stored response for a key. Returns None if not found or expired."""
        ...

    async def claim(self, pk: str, sk: str, fingerprint: str) -> bool:
        """Atomically claim a key (write "processing" sentinel).

        Returns True if this call claimed the key.
        Returns False if the key was already claimed/finalized.
        """
        ...

    async def finalize(
        self,
        pk: str,
        sk: str,
        response_status: int,
        response_body: bytes,
        response_headers: dict[str, str],
    ) -> bool:
        """Finalize a claimed key with the actual response data."""
        ...

    async def delete(self, pk: str, sk: str) -> bool:
        """Delete a stored key (for future Idempotency-Key-Clear support)."""
        ...


class InMemoryIdempotencyStore:
    """In-memory idempotency store for development and testing.

    Uses a dict keyed by (pk, sk) tuples. Supports TTL-based expiration
    checked on read. NOT suitable for production (not shared across
    ECS tasks). See DynamoDBIdempotencyStore for the production backend.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._store: dict[tuple[str, str], StoredResponse] = {}
        self._ttl_seconds = ttl_seconds
        self._timestamps: dict[tuple[str, str], float] = {}

    async def get(self, pk: str, sk: str) -> StoredResponse | None:
        key = (pk, sk)
        stored = self._store.get(key)
        if stored is None:
            return None
        # Check TTL
        created_epoch = self._timestamps.get(key, 0.0)
        if time.time() - created_epoch > self._ttl_seconds:
            # Expired -- remove and treat as not found
            del self._store[key]
            del self._timestamps[key]
            return None
        return stored

    async def claim(self, pk: str, sk: str, fingerprint: str) -> bool:
        key = (pk, sk)
        existing = await self.get(pk, sk)
        if existing is not None:
            return False
        now = time.time()
        self._store[key] = StoredResponse(
            status="processing",
            request_fingerprint=fingerprint,
            response_status=0,
            response_body=b"",
            response_headers={},
            created_at=datetime.now(tz=UTC).isoformat(),
        )
        self._timestamps[key] = now
        return True

    async def finalize(
        self,
        pk: str,
        sk: str,
        response_status: int,
        response_body: bytes,
        response_headers: dict[str, str],
    ) -> bool:
        key = (pk, sk)
        existing = self._store.get(key)
        if existing is None:
            return False
        self._store[key] = StoredResponse(
            status="complete",
            request_fingerprint=existing.request_fingerprint,
            response_status=response_status,
            response_body=response_body,
            response_headers=response_headers,
            created_at=existing.created_at,
        )
        return True

    async def delete(self, pk: str, sk: str) -> bool:
        key = (pk, sk)
        if key in self._store:
            del self._store[key]
            self._timestamps.pop(key, None)
            return True
        return False


class DynamoDBIdempotencyStore:
    """DynamoDB-backed idempotency store for production use.

    Uses boto3 synchronous client wrapped with ``asyncio.to_thread()`` for
    non-blocking async operation. Stores response bodies as base64-encoded
    strings (DynamoDB does not support raw bytes in standard attributes).

    Key schema:
        - pk (partition key): ``{service_name}#{idempotency_key}``
        - sk (sort key): ``{method}#{path_template}``
        - ttl (number): epoch seconds for DynamoDB TTL auto-expiry
    """

    def __init__(
        self,
        table_name: str,
        region: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        import boto3

        self._table_name = table_name
        self._ttl_seconds = ttl_seconds
        self._client = boto3.client("dynamodb", region_name=region)

    async def get(self, pk: str, sk: str) -> StoredResponse | None:
        """Read stored response for a key. Returns None if not found."""
        try:
            result = await asyncio.to_thread(
                self._client.get_item,
                TableName=self._table_name,
                Key={
                    "pk": {"S": pk},
                    "sk": {"S": sk},
                },
            )
        except Exception:  # noqa: BLE001 — ADVISORY: DynamoDB read failure degrades to cache-miss; request executes normally (HG-01 passthrough)
            logger.warning(
                "dynamodb_get_item_failed",
                extra={"pk": pk, "sk": sk},
                exc_info=True,
            )
            return None

        item = result.get("Item")
        if item is None:
            return None

        # Decode response_body from base64
        response_body_b64 = item.get("response_body", {}).get("S", "")
        response_body = (
            base64.b64decode(response_body_b64) if response_body_b64 else b""
        )

        # Decode response_headers from JSON string
        response_headers_json = item.get("response_headers", {}).get("S", "{}")
        try:
            response_headers = json.loads(response_headers_json)
        except (json.JSONDecodeError, TypeError):
            response_headers = {}

        return StoredResponse(
            status=item.get("status", {}).get("S", "processing"),
            request_fingerprint=item.get("request_fingerprint", {}).get("S", ""),
            response_status=int(item.get("response_status", {}).get("N", "0")),
            response_body=response_body,
            response_headers=response_headers,
            created_at=item.get("created_at", {}).get("S", ""),
        )

    async def claim(self, pk: str, sk: str, fingerprint: str) -> bool:
        """Atomically claim a key using conditional PutItem.

        Uses ``attribute_not_exists(pk)`` condition to ensure only one caller
        can claim a given key. Returns True if this call claimed the key,
        False if the key was already claimed/finalized.
        """
        now = datetime.now(tz=UTC)
        ttl_epoch = int(now.timestamp()) + self._ttl_seconds

        try:
            await asyncio.to_thread(
                self._client.put_item,
                TableName=self._table_name,
                Item={
                    "pk": {"S": pk},
                    "sk": {"S": sk},
                    "status": {"S": "processing"},
                    "request_fingerprint": {"S": fingerprint},
                    "response_status": {"N": "0"},
                    "response_body": {"S": ""},
                    "response_headers": {"S": "{}"},
                    "created_at": {"S": now.isoformat()},
                    "ttl": {"N": str(ttl_epoch)},
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except self._client.exceptions.ConditionalCheckFailedException:
            return False
        except Exception:  # noqa: BLE001 — ADVISORY: DynamoDB claim failure (non-ConditionalCheck) degrades to False; middleware falls back to pass-through
            logger.warning(
                "dynamodb_claim_failed",
                extra={"pk": pk, "sk": sk},
                exc_info=True,
            )
            return False

    async def finalize(
        self,
        pk: str,
        sk: str,
        response_status: int,
        response_body: bytes,
        response_headers: dict[str, str],
    ) -> bool:
        """Finalize a claimed key with the actual response data.

        Overwrites the existing item with status "complete" and the response
        payload. The TTL is recalculated from finalization time (not preserved from claim).
        """
        try:
            # Re-read to preserve created_at and ttl from the claim
            existing = await self.get(pk, sk)
            created_at = (
                existing.created_at if existing else datetime.now(tz=UTC).isoformat()
            )

            now_epoch = int(datetime.now(tz=UTC).timestamp())
            ttl_epoch = now_epoch + self._ttl_seconds

            await asyncio.to_thread(
                self._client.put_item,
                TableName=self._table_name,
                Item={
                    "pk": {"S": pk},
                    "sk": {"S": sk},
                    "status": {"S": "complete"},
                    "request_fingerprint": {
                        "S": existing.request_fingerprint if existing else ""
                    },
                    "response_status": {"N": str(response_status)},
                    "response_body": {
                        "S": base64.b64encode(response_body).decode("ascii")
                    },
                    "response_headers": {"S": json.dumps(response_headers)},
                    "created_at": {"S": created_at},
                    "ttl": {"N": str(ttl_epoch)},
                },
            )
            return True
        except Exception:  # noqa: BLE001 — ADVISORY: DynamoDB finalize failure; idempotency key not persisted, retry will re-execute (see dispatch handler annotation)
            logger.warning(
                "dynamodb_finalize_failed",
                extra={"pk": pk, "sk": sk},
                exc_info=True,
            )
            return False

    async def delete(self, pk: str, sk: str) -> bool:
        """Delete a stored key."""
        try:
            await asyncio.to_thread(
                self._client.delete_item,
                TableName=self._table_name,
                Key={
                    "pk": {"S": pk},
                    "sk": {"S": sk},
                },
            )
            return True
        except Exception:  # noqa: BLE001 — ADVISORY: DynamoDB delete failure; key remains in store until TTL expiry; no correctness impact
            logger.warning(
                "dynamodb_delete_failed",
                extra={"pk": pk, "sk": sk},
                exc_info=True,
            )
            return False


class NoopIdempotencyStore:
    """Passthrough store for graceful degradation when DynamoDB is unavailable.

    All operations succeed immediately without storing anything. This allows
    the middleware to function in passthrough mode -- requests execute normally
    without store-and-replay, which is the safest degradation posture (HG-01).
    """

    async def get(self, pk: str, sk: str) -> StoredResponse | None:
        return None

    async def claim(self, pk: str, sk: str, fingerprint: str) -> bool:
        return True

    async def finalize(
        self,
        pk: str,
        sk: str,
        response_status: int,
        response_body: bytes,
        response_headers: dict[str, str],
    ) -> bool:
        return True

    async def delete(self, pk: str, sk: str) -> bool:
        return True


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _validate_key(key: str) -> str | None:
    """Validate an idempotency key per ADR Section 3.2.

    Returns an error message if invalid, None if valid.
    """
    if not key:
        return "Idempotency-Key header must not be empty."
    if len(key) < _KEY_MIN_LENGTH:
        return f"Idempotency-Key must be at least {_KEY_MIN_LENGTH} characters."
    if len(key) > _KEY_MAX_LENGTH:
        return f"Idempotency-Key must not exceed {_KEY_MAX_LENGTH} characters."
    if not _KEY_PATTERN.match(key):
        return "Idempotency-Key contains invalid characters. Allowed: [a-zA-Z0-9-_.]"
    return None


def _is_eligible(method: str, path: str) -> str | None:
    """Check if the request matches an eligible endpoint.

    Returns the path template string if eligible, None otherwise.
    """
    for ep_method, pattern, template in _ENDPOINT_PATTERNS:
        if method == ep_method and pattern.match(path):
            return template
    return None


def _get_service_name(request: Request) -> str:
    """Extract service name from auth context or JWT claims.

    Falls back to "unknown" if not available (graceful for tests
    and unauthenticated requests).
    """
    # Check request state for auth context (set by auth middleware)
    auth_ctx = getattr(request.state, "auth_context", None)
    if auth_ctx is not None:
        svc: str | None = getattr(auth_ctx, "caller_service", None)
        if svc:
            return svc
    return _DEFAULT_SERVICE


def derive_fallback_key(
    method: str,
    path: str,
    body: bytes,
    service_name: str,
) -> str:
    """Derive a deterministic fallback key from request attributes.

    Per ADR Section 3.3: Used for logging/observability only.
    Does NOT activate the store-and-replay mechanism.
    """
    payload = json.dumps(
        {
            "method": method,
            "path": path,
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "service": service_name,
        },
        sort_keys=True,
    )
    return f"derived:{hashlib.sha256(payload.encode()).hexdigest()[:32]}"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """RFC 8791 idempotency key middleware for mutating S2S endpoints.

    Additive design: requests without ``Idempotency-Key`` header pass through
    unchanged (R-006). Only requests with the header activate store-and-replay.

    Per ADR Section 3.1, this middleware is positioned between SlowAPI (rate
    limiting) and RequestLogging in the Starlette middleware stack.
    """

    def __init__(self, app: ASGIApp, *, store: IdempotencyStore) -> None:
        super().__init__(app)
        self.store = store

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request through the idempotency protocol.

        Flow (per ADR Section 3.7):
        1. Check endpoint eligibility
        2. Extract idempotency key from header
        3. Validate key format
        4. Compute request fingerprint
        5. Check store for existing response (claim or replay)
        6. Execute handler if new key
        7. Store response for future replay
        """
        # 1. Check if endpoint is eligible
        path_template = _is_eligible(request.method, request.url.path)
        if path_template is None:
            return await call_next(request)

        # 2. Extract idempotency key from header
        key = request.headers.get("idempotency-key")
        if key is None:
            # R-006: no header = no idempotency = existing behavior
            # Log derived fallback key for observability (ADR Section 3.3)
            body = await request.body()
            service_name = _get_service_name(request)
            fallback = derive_fallback_key(
                request.method, request.url.path, body, service_name
            )
            logger.info(
                "idempotency_fallback_derived",
                derived_key=fallback,
                endpoint=path_template,
                service_name=service_name,
            )
            return await call_next(request)

        # 3. Validate key format
        validation_error = _validate_key(key)
        if validation_error is not None:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_IDEMPOTENCY_KEY",
                    "message": validation_error,
                },
            )

        # 4. Extract service name and compute fingerprint
        service_name = _get_service_name(request)
        body = await request.body()
        fingerprint = hashlib.sha256(body).hexdigest()

        # Construct composite keys per DynamoDB schema
        pk = f"{service_name}#{key}"
        sk = f"{request.method}#{path_template}"

        # 5. Try to claim the key (two-phase protocol)
        try:
            claimed = await self.store.claim(pk, sk, fingerprint)
        except Exception:  # noqa: BLE001 — ADVISORY: store unavailable at claim time; X-Idempotent-Degraded header signals passthrough to client
            # Graceful degradation: store unavailable
            logger.warning(
                "idempotency_store_unavailable",
                operation="claim",
                endpoint=path_template,
                key=key,
                exc_info=True,
            )
            response = await call_next(request)
            response.headers["Idempotency-Key"] = key
            response.headers["X-Idempotent-Degraded"] = "true"
            return response

        if not claimed:
            # Key already exists -- check if processing or complete
            try:
                existing = await self.store.get(pk, sk)
            except Exception:  # noqa: BLE001 — ADVISORY: store unavailable at replay-check time; X-Idempotent-Degraded header signals passthrough to client
                logger.warning(
                    "idempotency_store_unavailable",
                    operation="get",
                    endpoint=path_template,
                    key=key,
                    exc_info=True,
                )
                response = await call_next(request)
                response.headers["Idempotency-Key"] = key
                response.headers["X-Idempotent-Degraded"] = "true"
                return response

            if existing is None:
                # Race condition: key was claimed then expired between claim and get.
                # Fall through to execute handler.
                pass
            elif existing.status == "processing":
                # Two-phase claim: another request is currently processing
                logger.info(
                    "idempotency_key_in_flight",
                    key=key,
                    endpoint=path_template,
                )
                return JSONResponse(
                    status_code=409,
                    headers={"Retry-After": "1"},
                    content={
                        "error": "IDEMPOTENCY_KEY_IN_FLIGHT",
                        "message": "Request with this key is currently being processed. Retry shortly.",
                    },
                )
            else:
                # Complete -- check fingerprint
                if existing.request_fingerprint != fingerprint:
                    logger.warning(
                        "idempotency_key_mismatch",
                        key=key,
                        endpoint=path_template,
                        service_name=service_name,
                    )
                    return JSONResponse(
                        status_code=422,
                        content={
                            "error": "IDEMPOTENCY_KEY_MISMATCH",
                            "message": "This idempotency key was used with a different request body.",
                        },
                    )
                # Replay stored response
                logger.info(
                    "idempotency_key_replayed",
                    key=key,
                    endpoint=path_template,
                    original_status=existing.response_status,
                    age_seconds=int(
                        (
                            datetime.now(tz=UTC)
                            - datetime.fromisoformat(existing.created_at)
                        ).total_seconds()
                    ),
                )
                replay = Response(
                    content=existing.response_body,
                    status_code=existing.response_status,
                    headers=dict(existing.response_headers),
                )
                replay.headers["Idempotency-Key"] = key
                replay.headers["X-Idempotent-Replayed"] = "true"
                replay.headers["X-Idempotent-Original-Time"] = existing.created_at
                return replay
        else:
            # Successfully claimed -- log receipt
            logger.info(
                "idempotency_key_received",
                key=key,
                endpoint=path_template,
                service_name=service_name,
            )

        # 6. Execute route handler
        response = await call_next(request)

        # 7. Read response body for storage
        # BaseHTTPMiddleware wraps the response as a StreamingResponse.
        # We need to consume the body to store it.
        response_body = b""
        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
            if isinstance(chunk, str):
                response_body += chunk.encode("utf-8")
            else:
                response_body += chunk

        # Capture response headers to store
        stored_headers: dict[str, str] = {}
        if "content-type" in response.headers:
            stored_headers["content-type"] = response.headers["content-type"]

        # 8. Finalize the key with the actual response
        try:
            await self.store.finalize(
                pk=pk,
                sk=sk,
                response_status=response.status_code,
                response_body=response_body,
                response_headers=stored_headers,
            )
            logger.info(
                "idempotency_key_stored",
                key=key,
                endpoint=path_template,
                status=response.status_code,
            )
        except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD — finalize failure means key NOT persisted; a client retry will re-execute the mutation (double-execution risk). Acceptable only if: (a) DynamoDBIdempotencyStore.finalize() already logs at warning with exc_info, AND (b) the upstream caller is a human or idempotent system. For S2S callers with strict-once semantics this must be promoted to an error metric. See ADR-omniscience-idempotency Section 3.7.
            logger.error(
                "idempotency_store_finalize_failed",
                extra={
                    "operation": "finalize",
                    "endpoint": path_template,
                    "key": key,
                    "impact": "idempotency_key_not_persisted_retry_will_re_execute",
                },
                exc_info=True,
            )

        # 9. Return response with echo header
        final_response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
        final_response.headers["Idempotency-Key"] = key
        return final_response
