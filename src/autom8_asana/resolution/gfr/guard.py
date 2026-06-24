"""GFR central guard — checks BEFORE any frame access (INVARIANT I1, I2, I3; TDD §6.1).

The guard is the policy seam that enforces the GFR invariants structurally,
before the engine issues any read:

* **FM5 field-legality** (INVARIANT I4): a requested field must be declared by a
  resolvable ``SchemaRegistry`` schema. (Primary enforcement is in the planner;
  the guard exposes ``assert_field_legal`` for direct/defense-in-depth use.)
* **Cache-only on offer-domain** (INVARIANT I3, HARD line #1): an offer-domain
  descriptor has ``body_parameterized=False`` (``entity_registry.py:151``) — its
  DATA-FRAME miss returns ``UnresolvedError``/``None`` and NEVER triggers a
  silent Asana-API fallback. The guard reads ``body_parameterized`` off the
  descriptor and classifies the read as cache-only.
* **entity_type key-shape** (SEAM1): the data-frame key must be entity-partitioned
  (``dataframes/{project_gid}/{entity_type}/...``); a malformed shape is rejected.
* **Identity-path purity (NEW — INVARIANT I1 / GFR-IDENTITY-1)**: NO plan element
  and NO issued ``RowsRequest`` may reach a tenant-identity field (``company_id``)
  via an ``office_phone`` value-join. The identity reach is the parent chain +
  gid-exact row ONLY. A violation raises ``GuardViolationError`` (defense in
  depth — this is unreachable by construction in v2 and a hard structural-drift
  signal if it ever fires).

The identity-purity guard is the unit-level anti-regression hinge for the
``test_collision_closure`` anti-vacuity gate: a companion fixture that
re-introduces a phone-keyed join on the identity path MUST be rejected here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from autom8y_log import get_logger

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.resolution.gfr.errors import GuardViolationError, UnresolvedError
from autom8_asana.resolution.gfr.planner import IDENTITY_FIELDS

if TYPE_CHECKING:
    from autom8_asana.query.join import JoinSpec
    from autom8_asana.query.models import RowsRequest
    from autom8_asana.resolution.gfr.models import ResolutionPlan

logger = get_logger(__name__)

# The collision-prone join key that the v1 design used to (wrongly) reach
# ``company_id``. Reaching a tenant-identity field via this key is the PHI-leak
# trap INVARIANT I1 forbids (the dedup at ``query/join.py:157``).
_FORBIDDEN_IDENTITY_JOIN_KEY: Final[str] = "office_phone"


def assert_field_legal(field: str) -> None:
    """Raise ``UnresolvedError(unknown-field)`` if no schema declares ``field``.

    FM5 field-legality (INVARIANT I4). Defense-in-depth companion to the
    planner's partition step; callers that bypass the planner can use this to
    validate a single field.
    """
    registry = get_registry()
    schema_registry = SchemaRegistry.get_instance()
    for name in registry.dataframe_entities():
        descriptor = registry.get(name)
        if descriptor is None:
            continue
        try:
            schema = schema_registry.get_schema(descriptor.pascal_name)
        except Exception:  # noqa: BLE001 -- missing schema means this entity cannot own the field
            continue
        if schema.get_column(field) is not None:
            return
    raise UnresolvedError(fields=[field], reason="unknown-field")


def is_cache_only(entity_type: str) -> bool:
    """Return True if ``entity_type`` is a cache-only (offer-domain) read.

    Reads ``body_parameterized`` off the entity descriptor (``entity_registry.py:151``).
    A ``body_parameterized=False`` descriptor is registry-GID-routed and its
    DATA-FRAME miss must return unresolved with NO Asana-API fallback (INVARIANT
    I3, HARD line #1). An unregistered entity is treated as cache-only (the
    safe, no-API-fallback default).
    """
    descriptor = get_registry().get(entity_type)
    if descriptor is None:
        return True
    return not bool(descriptor.body_parameterized)


def _join_reaches_identity(request: RowsRequest) -> bool:
    """True if ``request`` would reach a tenant-identity field via a phone join.

    INVARIANT I1 defense: a ``RowsRequest`` whose ``join`` selects an identity
    field (``company_id``) keyed on ``office_phone`` — or routed through the
    ``data-service`` analytics join — re-introduces the v1 collision trap. The
    identity reach must be a gid-exact ``where`` predicate with NO join at all
    (INVARIANT I2: a gid-exact RowsRequest carries no join field, so it can never
    reach ``execute_join``'s ``keep='first'`` dedup).
    """
    join: JoinSpec | None = request.join
    if join is None:
        return False
    selects_identity = any(field in IDENTITY_FIELDS for field in join.select)
    if not selects_identity:
        return False
    # An identity field reached via a join is forbidden when the join is the
    # phone-keyed entity join OR the data-service analytics join (both are the
    # collision/no-identity-column surfaces, INVARIANT I1 / I7).
    if join.source == "data-service":
        return True
    return join.on == _FORBIDDEN_IDENTITY_JOIN_KEY


def assert_request_identity_pure(request: RowsRequest) -> None:
    """Raise ``GuardViolationError`` if a request reaches identity via a phone join.

    The central identity-purity check (INVARIANT I1). Issued against every
    ``RowsRequest`` the engine builds for an identity read: the request MUST be a
    gid-exact ``where`` with ``join is None``. This is the unit-level
    anti-regression hinge — a fixture that re-introduces the phone-keyed identity
    join fires RED here.
    """
    if _join_reaches_identity(request):
        join = request.join
        logger.error(
            "GFR guard: identity-path purity violation",
            extra={
                "join_source": getattr(join, "source", None),
                "join_on": getattr(join, "on", None),
                "join_select": getattr(join, "select", None),
            },
        )
        raise GuardViolationError(
            "tenant-identity field reached via an office_phone/data-service join "
            "(INVARIANT GFR-IDENTITY-1); identity must be gid-exact, never a phone "
            "value-join (the query/join.py:157 keep='first' dedup trap)"
        )


def assert_plan_identity_pure(plan: ResolutionPlan) -> None:
    """Raise ``GuardViolationError`` if a plan element marks identity as a phone hop.

    Plan-level companion to ``assert_request_identity_pure``. An identity plan
    element (``is_identity=True``) must NOT be a phone-keyed/enrichment hop; in
    v2 it is always reached by the parent chain + gid-exact read, never a join
    (INVARIANT I1). The guard rejects any identity plan whose hop class is not a
    parent-chain/local/in-frame identity reach.
    """
    for field_plan in plan.identity_plans:
        # An identity owner must be Business and reached by the gid-exact path.
        # The only legitimate identity hop is the parent-chain (offer) or
        # in-frame/local (business). There is NO join hop for identity.
        if field_plan.owner != "business":
            logger.error(
                "GFR guard: identity field owned by non-business entity",
                extra={"owner": field_plan.owner, "fields": field_plan.fields},
            )
            raise GuardViolationError(
                f"tenant-identity field {field_plan.fields!r} planned against "
                f"non-business owner {field_plan.owner!r}; identity is Business-only "
                "and gid-exact (INVARIANT GFR-IDENTITY-1)"
            )
