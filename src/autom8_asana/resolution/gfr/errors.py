"""GFR domain error hierarchy.

Per GFR TDD v2 §2 (Module Decomposition) and conventions inherited from
``resolution/``: every failure mode is a named domain subclass of ``GfrError``;
no bare ``Exception`` is raised or caught in the package (that would be a defect,
not a solution).

The hierarchy encodes the GFR design invariants:

* ``UnresolvedError`` is the ALL-OR-NOTHING surface (INVARIANT I4): any genuinely
  unresolvable requested field collapses the WHOLE call into this error, carrying
  the offending ``fields`` and a closed-vocabulary ``reason``.
* ``GuardViolationError`` is defense-in-depth for INVARIANT I1 / GFR-IDENTITY-1:
  it fires if any plan element ever attempts to reach a tenant-identity field
  (``company_id``) via an ``office_phone`` value-join. This should be
  unreachable by construction (the identity path is gid-exact), so a raise here
  is a hard structural-drift signal, not an expected runtime condition.
* ``AmbiguousCardinalityError`` enforces INVARIANT I5 (ROW-SET NATIVE): a
  ``.scalar()`` view on a result whose ``row_count != 1`` raises rather than
  silently collapsing N rows to one.
"""

from __future__ import annotations

from typing import Final

# Closed vocabulary for UnresolvedError.reason (INVARIANT I4). Surfaced here as a
# module constant so the planner/engine/guard all reference one source of truth
# and tests can assert membership rather than string-matching ad hoc.
UNRESOLVED_REASONS: Final[frozenset[str]] = frozenset(
    {
        "unknown-field",  # field not declared in any resolvable SchemaRegistry schema
        "empty-frame",  # the owning frame is genuinely empty (no rows)
        "entity-type-undetectable",  # detect_entity_type_async returned UNKNOWN
        "no-identity-path",  # parent chain cannot reach a Business (HydrationError)
        "business-row-not-found",  # anchored business_gid has no gid-exact row
    }
)


class GfrError(Exception):
    """Base class for all GID Field Resolver errors.

    Callers may catch ``GfrError`` to handle any GFR failure uniformly; the
    facade (``__init__.py``) re-exports only ``UnresolvedError`` because that is
    the single failure a fleet caller is expected to handle. The other
    subclasses signal structural problems (guard violation) or caller misuse
    (ambiguous cardinality).
    """


class UnresolvedError(GfrError):
    """Raised when the resolve call cannot satisfy the requested field SET.

    Enforces INVARIANT I4 (ALL-OR-NOTHING): if ANY requested field is genuinely
    unresolvable, the entire call fails with this error rather than returning a
    partial result. Stale-but-present fields do NOT trigger this — they count as
    resolved (INVARIANT I4 second clause).

    Attributes:
        fields: The requested field name(s) that could not be resolved.
        reason: A closed-vocabulary reason code (see ``UNRESOLVED_REASONS``).
    """

    def __init__(self, *, fields: list[str], reason: str) -> None:
        if reason not in UNRESOLVED_REASONS:
            # Defensive: an out-of-vocabulary reason is itself a programming error.
            raise ValueError(
                f"UnresolvedError.reason {reason!r} not in closed vocabulary "
                f"{sorted(UNRESOLVED_REASONS)}"
            )
        self.fields: list[str] = list(fields)
        self.reason: str = reason
        super().__init__(f"Unresolved fields {self.fields!r}: {reason}")


class GuardViolationError(GfrError):
    """Raised when a plan would reach a tenant-identity field via a phone join.

    Defense-in-depth for INVARIANT I1 / GFR-IDENTITY-1: the identity path is
    gid-exact by construction and STRUCTURALLY never consults the ``office_phone``
    value-join (which dedups ``keep='first'`` at ``query/join.py:157`` — the v1
    PHI-leak trap). If this error is ever raised in production it means a future
    change reintroduced the trap; the central guard catches it before any frame
    access.
    """


class AmbiguousCardinalityError(GfrError):
    """Raised by ``ResolvedFields.scalar()`` when ``row_count != 1``.

    Enforces INVARIANT I5 (ROW-SET NATIVE): ``resolve_async`` returns 1..N rows
    and never silently collapses N rows into a scalar. A caller that opts into
    scalar sugar accepts this error as the price of the convenience.

    Attributes:
        row_count: The actual number of rows in the result set.
    """

    def __init__(self, *, row_count: int) -> None:
        self.row_count: int = row_count
        super().__init__(
            f"scalar() requires exactly 1 row, got {row_count}; "
            "result is row-set native (INVARIANT I5)"
        )
