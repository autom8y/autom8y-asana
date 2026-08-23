"""Write-class authorization for the Asana write surface (RE-2 / SEC-001, layer 1).

Closes SEC-001: *"which service may invoke which Asana write class?"* Before this
module, `require_service_claims` (`internal.py:83-162`) was authenticate-and-
pass-through and `admin.py:456` was the ONLY authorization decision in the whole
service — and it does not guard an Asana write. Any caller holding a valid fleet
service JWT could drive any Asana write route, because the JWT branch of
`get_auth_context` (`dependencies.py:239-267`) lends that caller the shared bot
PAT. CR-1 (an operator process fence) was the only control.

Design of record: ``.ledge/decisions/DESIGN-re2-two-layer-authz-2026-08-13.md``
(§5.1 layer 1 — L1-1..L1-4). Ratified as the build target by
``.ledge/decisions/RULINGS-coc-phase2-operator-sitting-2026-08-14.md:38-48`` (R-7).

Layer 1 (this module) is *enforcement*: a deny-by-default allowlist keyed on the
issuer-asserted service identity, resolved in-service, requiring **no**
minting-layer change. Layer 2 (deferred, cross-repo) mints per-write-class
scopes upstream and swaps only this gate's *predicate* — the door is the same
door, re-keyed. That is why layer 1 is not throwaway.

THE AXIS RULING (CORRECTION-3 — the most consequential decision here)
---------------------------------------------------------------------
**Enforcement is NOT keyed on ``ServiceClaims.has_scope()``.**

``autom8y_auth.claims.ServiceClaims.has_scope`` (4.1.0, ``claims.py:220-222``)
opens with a wildcard shortcut::

    # Wildcard shortcut (legacy sentinel — grants everything).
    if self.scope == "*":
        return True

Any token carrying ``scope == "*"`` satisfies ``has_scope("asana:write")``
unconditionally. A write gate built on that predicate is **fail-open** against
that carrier — it would ship a control that reads as enforcement and is not one.

This is not a local inference. The fleet's own auth service documents the hazard
and routes around it at ``services/auth/service-accounts.yaml:682-683``:

    "The guard resolves through ``ServiceClaims.has_permission`` (plain
    membership), NOT ``has_scope``, which short-circuits True on ``scope == '*'``."

So the admissible axes are, in preference order:

1. **Issuer-asserted principal identity** (this module, layer 1) — ``sub`` /
   ``client_id`` / ``service_account_id`` are signature-covered and carry no
   wildcard sentinel of any kind. Fleet precedent:
   ``SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS``.
2. **The ``permissions`` axis** (layer 2) — plain list membership, no wildcard.
   Already the idiom at ``admin.py:456``.

The ``scope``/``scopes`` axis is REFUSED for authorization at any layer.
``has_permission_no_wildcard`` below is the layer-2-ready predicate, and it
refuses ``"*"`` explicitly rather than inheriting a permissive default.
``tests/unit/api/test_write_authz_coverage.py`` (GUARD-2) is the drift guard that
keeps the refused axis out of ``src/`` permanently.

FAIL-CLOSED POSTURE
-------------------
Every resolution in this module fails toward denial:

* mode unset            -> ENFORCE (never silently observe)
* mode malformed        -> ENFORCE (never silently observe)
* allowlist unset       -> empty -> deny-all, loudly
* allowlist empty string -> empty -> deny-all, loudly
* allowlist malformed   -> empty -> deny-all, loudly
* principal unresolvable -> deny

There is deliberately no "allow on error" branch anywhere below.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable  # noqa: TC003 — runtime return annotation
from enum import StrEnum
from typing import Annotated, Any, NamedTuple

from autom8y_log import get_logger
from fastapi import Depends, Request

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.errors import raise_api_error
from autom8_asana.auth.dual_mode import AuthMode

logger = get_logger("autom8_asana.api.write_authz")


# ---------------------------------------------------------------------------
# Write classes
#
# Spellings are REUSED from the pre-existing (documentation-only) taxonomy at
# `main.py:150-168` `_OAUTH2_SCOPE_DEFINITIONS` rather than invented here —
# CORRECTION-1 of the design: the vocabulary was already drafted and route-
# mapped in this repo, it was merely inert. `receipts:write` is the one genuinely
# new member: the comment-create class was absent from the taxonomy entirely
# (design §2.2 "the hole"), which DEV-4 closes on the documentation side.
# ---------------------------------------------------------------------------


class WriteClass(StrEnum):
    """An Asana write class subject to per-service authorization."""

    TASKS = "tasks:write"
    PROJECTS = "projects:write"
    SECTIONS = "sections:write"
    INTAKE = "intake:write"
    RECEIPTS = "receipts:write"
    WORKFLOWS = "workflows:execute"


class AuthzMode(StrEnum):
    """Enforcement posture for the write gate."""

    ENFORCE = "enforce"
    """Unauthorized callers receive 403. The ratified terminal state."""

    OBSERVE = "observe"
    """Decision is computed and logged, but the request proceeds.

    A rollout-only shadow posture so an operator can populate allowlists from
    observed traffic without an availability cliff. It is NOT a control: while
    OBSERVE is set, this service is in exactly the pre-RE-2 state and CR-1 is
    still the only control. Selecting it is an explicit operator act — it is
    never the default and is never reached by accident (see `resolve_mode`).
    """


MODE_ENV = "ASANA_WRITE_AUTHZ_MODE"
"""Env var selecting enforcement posture. Unset or malformed -> ENFORCE."""

_ALLOWLIST_ENV_PREFIX = "ASANA_WRITERS_"

# Env var name per write class. Mirrors the fleet-precedent naming of
# `SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS` (services/auth/service-accounts.yaml:680-683).
ALLOWLIST_ENV: dict[WriteClass, str] = {
    WriteClass.TASKS: f"{_ALLOWLIST_ENV_PREFIX}TASKS_WRITE",
    WriteClass.PROJECTS: f"{_ALLOWLIST_ENV_PREFIX}PROJECTS_WRITE",
    WriteClass.SECTIONS: f"{_ALLOWLIST_ENV_PREFIX}SECTIONS_WRITE",
    WriteClass.INTAKE: f"{_ALLOWLIST_ENV_PREFIX}INTAKE_WRITE",
    WriteClass.RECEIPTS: f"{_ALLOWLIST_ENV_PREFIX}RECEIPTS_WRITE",
    WriteClass.WORKFLOWS: f"{_ALLOWLIST_ENV_PREFIX}WORKFLOWS_EXECUTE",
}

DENIED_ERROR_CODE = "INSUFFICIENT_PRIVILEGE"
"""Matches the shape already emitted by `admin.py:466-473` — one 403 vocabulary."""


# ---------------------------------------------------------------------------
# Mode + allowlist resolution (both fail closed)
# ---------------------------------------------------------------------------


def resolve_mode() -> AuthzMode:
    """Resolve enforcement posture, failing closed on absence or garbage.

    ENFORCE is returned for unset, empty, whitespace, and every unrecognized
    value. OBSERVE is reachable ONLY by the exact literal ``"observe"`` (case-
    and whitespace-insensitive). A typo such as ``"observ"`` or ``"OBSERVE!"``
    yields ENFORCE, never a silent pass-through.

    This asymmetry is deliberate: a misconfiguration must degrade toward
    refusing writes, never toward permitting them.
    """
    raw = os.environ.get(MODE_ENV, "").strip().lower()
    if raw == AuthzMode.OBSERVE.value:
        return AuthzMode.OBSERVE
    if raw and raw != AuthzMode.ENFORCE.value:
        logger.warning(
            "write_authz_mode_unrecognized_failing_closed",
            extra={"raw_mode": raw, "resolved_mode": AuthzMode.ENFORCE.value},
        )
    return AuthzMode.ENFORCE


def load_writer_allowlist(write_class: WriteClass) -> frozenset[str]:
    """Load the authorized-principal allowlist for a write class.

    Format: comma-separated principals. Blank entries are dropped. Every
    misconfiguration mode — unset, empty string, whitespace-only, all-separators
    — collapses to the EMPTY set, which `is_authorized` treats as deny-all.
    There is no value of this env var that means "allow everyone"; ``"*"`` is
    not a wildcard here, it is a principal name no issuer will ever assert
    (see `is_authorized`).
    """
    raw = os.environ.get(ALLOWLIST_ENV[write_class], "")
    return frozenset(entry.strip() for entry in raw.split(",") if entry.strip())


# ---------------------------------------------------------------------------
# Principal resolution
# ---------------------------------------------------------------------------


class PrincipalResolution(NamedTuple):
    """A resolved caller identity and the claim tier it came from."""

    principal: str | None
    tier: str


_UNRESOLVED = PrincipalResolution(None, "unresolved")


def resolve_principal(request: Request | None, claims: Any) -> PrincipalResolution:
    """Resolve the issuer-asserted principal for an authorization decision.

    Precedence is IDENTICAL to the SA-identity ordering already proven in this
    repo at `idempotency.py:508-530` and documented at `rate_limit.py:25-46`:

      1. ``service_account_id`` — the canonical ``sa.yaml_id``. The SDK's
         ``ServiceClaims`` declares ``extra="ignore"`` and has NO such field, so
         it is read from the middleware-dumped ``request.state.claims_dict``.
      2. ``client_id`` — a real ``ServiceClaims`` field, present on
         ServiceAccount tokens; survives JWT validation.
      3. ``sub`` / ``service_name`` — the SA UUID; stable carrier of last resort.

    A SINGLE resolved principal is returned — deliberately not the *set* of all
    identity values present. Matching an allowlist against "any identity field"
    would let a caller who controls one field satisfy a rule written against a
    different field. Strict precedence means the highest-authority claim present
    is the one that must be allowlisted, and a caller cannot demote itself into
    a more permissive tier.

    Every tier is signature-covered: these values arrive only from a JWT that
    already cleared JWKS/signature/issuer/expiry/audience validation. The caller
    cannot author them.

    ``rate_limit.py:42-46`` records a prior in-repo defect of exactly this class
    (Sprint-1 read ``payload.get("service_name")``, which no issuer emits, so
    every SA silently fell through). Reading the wrong field here would produce
    a gate that denies everyone or allows everyone; the precedence above is the
    corrected ordering, reused rather than re-derived.
    """
    if claims is None:
        return _UNRESOLVED

    # 1. service_account_id (canonical) — only ever present on the dumped dict.
    if request is not None:
        claims_dict = getattr(request.state, "claims_dict", None)
        if isinstance(claims_dict, dict):
            sa_id = claims_dict.get("service_account_id")
            if isinstance(sa_id, str) and sa_id.strip():
                return PrincipalResolution(sa_id.strip(), "service_account_id")

    # 2. client_id — a real ServiceClaims field on ServiceAccount tokens.
    client_id = getattr(claims, "client_id", None)
    if isinstance(client_id, str) and client_id.strip():
        return PrincipalResolution(client_id.strip(), "client_id")

    # 3. sub / service_name — the SA UUID.
    for attr in ("service_name", "sub"):
        value = getattr(claims, attr, None)
        if isinstance(value, str) and value.strip():
            return PrincipalResolution(value.strip(), attr)

    return _UNRESOLVED


# ---------------------------------------------------------------------------
# The predicates
# ---------------------------------------------------------------------------


def is_authorized(principal: str | None, allowlist: frozenset[str]) -> bool:
    """Deny-by-default membership test.

    Returns False for an unresolved principal and for an empty allowlist. There
    is no wildcard: a literal ``"*"`` in the allowlist authorizes a principal
    *named* ``"*"`` and nothing else. That is the whole point of the axis ruling
    in this module's docstring — the fail-open sentinel that makes
    ``has_scope`` unsafe has no analogue here, by construction.
    """
    if principal is None:
        return False
    return principal in allowlist


def has_permission_no_wildcard(claims: Any, permission: str) -> bool:
    """Layer-2-ready permission predicate with the wildcard sentinel REFUSED.

    Plain membership over ``claims.permissions`` — the same axis
    ``admin.py:456`` already uses, and the axis the fleet auth service directs
    consumers to at ``service-accounts.yaml:682-683``.

    Two sentinels are refused explicitly rather than by omission:

    * A ``"*"`` entry in ``permissions`` does NOT grant ``permission``.
    * ``claims.scope == "*"`` is NEVER consulted — this predicate does not read
      ``scope`` or ``scopes`` at all, which is precisely how it avoids the
      ``has_scope`` fail-open at ``claims.py:220-222``.

    Refusing ``"*"`` inside ``permissions`` is defence in depth: the
    ``permissions`` axis carries no wildcard convention today, so this branch
    should be unreachable in production. It exists so that if a future issuer
    ever adopts a ``"*"`` permission sentinel, this gate does not silently
    inherit a fail-open the way ``has_scope`` did.
    """
    permissions = getattr(claims, "permissions", None)
    if not isinstance(permissions, (list, tuple, set, frozenset)):
        return False
    if permission == "*":
        # Never let a caller ask for, and be granted, "everything".
        return False
    return permission in set(permissions) and permission != "*"


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def authorize_write(
    write_class: WriteClass,
    claims: Any,
    request: Request | None = None,
    *,
    request_id: str = "unknown",
) -> None:
    """Authorize a write-class invocation, or raise 403.

    In ENFORCE mode an unauthorized caller gets 403 ``INSUFFICIENT_PRIVILEGE``
    and the handler never runs — so no Asana write is attempted and the shared
    bot PAT is never spent on that request.

    In OBSERVE mode the identical decision is computed and logged with
    ``would_deny``, and the request proceeds. OBSERVE never denies; it is a
    rollout instrument, not a control.

    Raises:
        ApiError: 403 INSUFFICIENT_PRIVILEGE when denied under ENFORCE.
    """
    mode = resolve_mode()
    allowlist = load_writer_allowlist(write_class)
    resolution = resolve_principal(request, claims)
    allowed = is_authorized(resolution.principal, allowlist)

    if allowed:
        logger.info(
            "write_authz_allowed",
            extra={
                "request_id": request_id,
                "write_class": write_class.value,
                "principal": resolution.principal,
                "principal_tier": resolution.tier,
                "mode": mode.value,
            },
        )
        return

    # Denied. Emit the same structured shape in both modes so that an OBSERVE
    # soak produces exactly the evidence an ENFORCE flip will act on.
    logger.warning(
        "write_authz_denied" if mode is AuthzMode.ENFORCE else "write_authz_would_deny",
        extra={
            "request_id": request_id,
            "write_class": write_class.value,
            "principal": resolution.principal,
            "principal_tier": resolution.tier,
            "mode": mode.value,
            "allowlist_env": ALLOWLIST_ENV[write_class],
            "allowlist_size": len(allowlist),
            "would_deny": True,
        },
    )

    if mode is AuthzMode.OBSERVE:
        return

    raise_api_error(
        request_id,
        403,
        DENIED_ERROR_CODE,
        (
            f"Service is not authorized for write class '{write_class.value}'. "
            f"Authorized principals are configured via {ALLOWLIST_ENV[write_class]}."
        ),
    )


# ---------------------------------------------------------------------------
# FastAPI wiring
# ---------------------------------------------------------------------------


def require_write_authz(write_class: WriteClass) -> Callable[..., Awaitable[None]]:
    """Build a route dependency enforcing `write_class` authorization.

    Attach via the route decorator's ``dependencies=[...]`` list::

        @router.post(
            "/receipts",
            dependencies=[Depends(require_write_authz(WriteClass.RECEIPTS))],
            ...
        )

    The gate hangs off ``get_auth_context``, which is in the dependency graph of
    **every** Asana write route in this service — the S2S family reaches it via
    ``AuthContextDep`` and the dual-mode family via ``AsanaClientDualMode`` ->
    ``get_asana_client_from_context`` -> ``get_auth_context``. One dependency
    therefore covers both families with one plumbing path and one decision site.
    FastAPI caches ``get_auth_context`` per request, so attaching this gate does
    not re-validate the JWT.

    Route dependencies are resolved BEFORE the handler body runs, so a denial
    raises 403 without the handler executing and without any Asana call being
    attempted — the shared bot PAT is never spent on a refused request.

    PAT-mode requests pass through unauthorized-by-this-gate BY DESIGN: those
    callers present their own Asana credential and are authorized by Asana's own
    ACL (see ``AuthContext``). This gate exists for the JWT branch, where the
    caller is lent the shared bot PAT.
    """

    async def _write_authz_gate(
        request: Request,
        auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> None:
        if auth_context.mode == AuthMode.PAT:
            return
        authorize_write(
            write_class,
            auth_context.claims,
            request,
            request_id=getattr(request.state, "request_id", "unknown"),
        )

    _write_authz_gate.__name__ = f"write_authz_{write_class.name.lower()}"
    return _write_authz_gate


__all__ = [
    "ALLOWLIST_ENV",
    "DENIED_ERROR_CODE",
    "MODE_ENV",
    "AuthzMode",
    "PrincipalResolution",
    "WriteClass",
    "authorize_write",
    "has_permission_no_wildcard",
    "is_authorized",
    "load_writer_allowlist",
    "require_write_authz",
    "resolve_mode",
    "resolve_principal",
]
