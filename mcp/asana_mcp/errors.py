"""Tool-layer error taxonomy for the asana_mcp sidecar.

The LOAD-BEARING invariant (spike guardrail + C3 / R2 timeout-inversion scar):
a cold-frame ``503`` is surfaced as a RETRYABLE error naming cache-warming as the
true cause — NEVER auth-shaped. Auth failures (``401``/``403``) are a DISTINCT,
non-retryable class. Conflating the two is the ``query503`` scar this taxonomy
exists to prevent, so the classes are asserted disjoint by ``tests/test_errors_c3``.
"""

from __future__ import annotations

from typing import Any

import httpx

# 503 warming codes emitted by the satellite (api/routes/query.py, health.py,
# resolver.py) — all mean "cache warming / startup discovery incomplete" => retry.
_WARMING_CODES = {
    "CACHE_NOT_WARMED",
    "CACHE_BUILD_IN_PROGRESS",
    "DATAFRAME_BUILD_IN_PROGRESS",
    "DISCOVERY_INCOMPLETE",
}


class McpToolError(Exception):
    """A tool-layer error carrying an explicit, honest cause classification."""

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        retryable: bool,
        status: int | None = None,
        retry_after: float | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        # kind in {warming, auth, rate_limit, client, not_found, server}
        self.kind = kind
        self.retryable = retryable
        self.status = status
        self.retry_after = retry_after
        self.code = code

    def to_tool_payload(self) -> dict[str, Any]:
        """A flat, LLM-legible error dict (the true cause is never hidden)."""
        return {
            "error": True,
            "kind": self.kind,
            "retryable": self.retryable,
            "message": self.message,
            "status": self.status,
            "retry_after": self.retry_after,
            "code": self.code,
        }


def _body_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 — a non-JSON body simply has no code
        return None
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict) and isinstance(err.get("code"), str):
            return err["code"]
        if isinstance(body.get("code"), str):
            return body["code"]
    return None


def _retry_after(response: httpx.Response) -> float | None:
    header = response.headers.get("retry-after")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        body = response.json()
        details = body.get("details") if isinstance(body, dict) else None
        if isinstance(details, dict):
            for key in ("retry_after_seconds", "retry_after"):
                if key in details:
                    return float(details[key])
    except Exception:  # noqa: BLE001
        pass
    return None


def _body_error_context(response: httpx.Response) -> tuple[str | None, dict[str, Any] | None]:
    """Extract the satellite error envelope's (message, details), if any."""
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 — a non-JSON body carries no context
        return None, None
    if not isinstance(body, dict):
        return None, None
    err = body.get("error")
    if isinstance(err, dict):
        message = err.get("message") if isinstance(err.get("message"), str) else None
        details = err.get("details") if isinstance(err.get("details"), dict) else None
        return message, details
    return None, None


def _upstream_suffix(response: httpx.Response, *, code: str | None) -> str:
    """MCP-1 (limb-(a) witness cure, 2026-07-19): carry the satellite's own
    diagnosis through to the LLM instead of flattening it.

    The 404 ``available_types`` list is the exact recovery hint whose loss cost
    the witness agent a four-call guess loop; ``validation_errors`` /
    ``missing_field`` do the same for 4xx bodies. Deliberately NOT applied to
    the 503-warming branch — its curated attribution text (warming, NOT auth)
    is the C3 load-bearing message and stays authoritative.
    """
    message, details = _body_error_context(response)
    parts: list[str] = []
    if code:
        parts.append(f"Satellite code: {code}.")
    if message:
        parts.append(f"Satellite message: {message}")
    if details:
        available = details.get("available_types")
        if isinstance(available, list) and available:
            parts.append("Known entity types: " + ", ".join(str(a) for a in available) + ".")
        validation = details.get("validation_errors")
        if isinstance(validation, list) and validation:
            fields = [
                f"{v.get('field', '?')}: {v.get('message', '')}"
                for v in validation[:3]
                if isinstance(v, dict)
            ]
            if fields:
                parts.append("Validation: " + "; ".join(fields) + ".")
        missing = details.get("missing_field")
        if isinstance(missing, str):
            parts.append(f"Missing field: {missing}.")
    return (" " + " ".join(parts)) if parts else ""


def map_http_error(response: httpx.Response) -> McpToolError:
    """Map a non-200 satellite response to an honest, correctly-classified error.

    C3 invariant: 503 -> ``warming`` (retryable), NEVER ``auth``. 401/403 ->
    ``auth`` (not retryable). These branches are mutually exclusive by status.
    """
    status = response.status_code
    code = _body_code(response)

    if status == 503:
        return McpToolError(
            "The asana satellite cache is warming (or startup discovery is "
            "incomplete). This is transient — retry shortly. This is NOT an "
            "authentication failure.",
            kind="warming",
            retryable=True,
            status=503,
            retry_after=_retry_after(response) or 30.0,
            code=code or "CACHE_WARMING",
        )
    if status in (401, 403):
        return McpToolError(
            "Authentication/authorization to the S2S surface failed (the S2S JWT "
            "was rejected). This is NOT a cache-warming condition."
            + _upstream_suffix(response, code=code),
            kind="auth",
            retryable=False,
            status=status,
            code=code,
        )
    if status == 429:
        return McpToolError(
            "Rate budget exhausted on the shared-PAT surface. Retry after backoff.",
            kind="rate_limit",
            retryable=True,
            status=429,
            retry_after=_retry_after(response),
            code=code,
        )
    if status == 404:
        return McpToolError(
            "The requested entity type or route was not found."
            + _upstream_suffix(response, code=code),
            kind="not_found",
            retryable=False,
            status=404,
            code=code,
        )
    if 400 <= status < 500:
        return McpToolError(
            "The request was rejected as invalid (bad predicate, unknown field, "
            "or malformed body). Fix the request; it is not retryable as-is."
            + _upstream_suffix(response, code=code),
            kind="client",
            retryable=False,
            status=status,
            code=code,
        )
    return McpToolError(
        "The satellite returned a server error; it may be transient.",
        kind="server",
        retryable=True,
        status=status,
        code=code,
    )
