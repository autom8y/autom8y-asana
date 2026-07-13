"""Operator-plane batch endpoint for DataServiceClient (GAP-1 PR-A).

Consumes the data plane's operator-only per-office read surface
``POST /api/v1/insights/operator/execute-batch`` (autom8y-data origin/main
3169fa96), authenticated by a minted ``OperatorClaims`` Bearer token (NEVER the SA
ServiceClaims token). It serves the cross-tenant agency-BI export, bounded to the
operator's data-resolved owned set ``O`` -- DATA-VAL-003 SIDESTEPPED, not re-asserted.

Call pattern (TDD §5.3, RULED): batch-over-O -- ONE call per insight over the whole
owned set, then distribute per-office (the OQ-2 adapter). NOT per-office-per-table
(``N_offices x N_tables`` calls would blow the 10/min ``LIMIT_HEAVY_ANALYTICS``).

EC-4 (all-or-nothing x ownership-drift): the route is all-or-nothing -- ONE requested
office not in ``O`` makes the WHOLE batch 404, and ``O`` is server-internal (asana
cannot pre-filter). On a batch 404 over >1 office we fall back to a BOUNDED per-office
sweep ON THE SAME OPERATOR ROUTE (serve the owned subset, skip the drift office). The
sweep is NOT an SA fleet-read (G-NO-FALLBACK holds).

G-NO-FALLBACK (the load-bearing invariant): on a mint refusal (403) or a route denial
(the bare 404-as-oracle) this path raises a typed error / yields empty and NEVER falls
back to ``/data-service/insights`` (the SA fleet-read). A fleet-read fallback would
re-assert DATA-VAL-003 -- the precise telos antithesis.

This module is NOT part of the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data._endpoints._pacer import BudgetExhausted, OperatorCallPacer
from autom8_asana.errors import (
    OperatorAccessDeniedError,
    OperatorBatchVersionSkewError,
    OperatorMintRefusedError,
)

if TYPE_CHECKING:
    from datetime import date

    from autom8_asana.clients.data.client import DataServiceClient

# The mounted path of the operator-plane per-office batch route (data plane
# OPERATOR_BATCH_ROUTE_PATH). Single literal here; the data plane owns the SoT.
OPERATOR_BATCH_PATH = "/api/v1/insights/operator/execute-batch"

# The weight-governed consumer metrics whose emitted numbers carry provenance
# (weights_version). MIRRORS the data plane's authoritative frozen set
# ``core/metrics/weights_provenance_projection.py::WEIGHTED_CONSUMER_METRICS``
# (origin/main) byte-for-byte -- the SINGLE source of truth is the data plane;
# this client-side mirror exists only to name the render-time C2 population
# (which rendered columns REQUIRE a weights_version disclosure). If the data
# plane's set ever changes, this mirror is revisited under a NAMED ruling, never
# silently widened (§3.1 row-grain / C2 scope fence, RULING R-WP-2).
WEIGHTED_CONSUMER_METRICS: frozenset[str] = frozenset(
    {
        "ns_rate",
        "nc_rate",
        "conv_rate",
        "nsr_ncr",
        "xcps",
    }
)

# Server office-batch ceiling for the operator route: OperatorBatchInsightRequest
# inherits BatchInsightExecuteRequest whose phones field is max_length = 100 (data
# plane models.py MAX_BATCH_SIZE). Chunk the owned set to <=100 before batching so a
# large fleet never 422s (TDD FILE-3 / RISK-3). The data plane owns the true SoT;
# this mirror is the conservative client-side guard.
OPERATOR_BATCH_CEILING = 100

# Bisection-local cap on Retry-After honored 429 retries of one sub-batch before it
# is skipped (marked unreached, prior deck protected). Keeps a throttled sub-batch
# from burning the whole run budget (TDD §5.2 step 5 / RISK-7).
_MAX_THROTTLE_RETRIES = 1


def distribute_per_office(body: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """OQ-2 adapter: ``SuccessResponse[BatchInsightResponse]`` -> ``{phone: rows}``.

    The operator route returns the EXISTING per-office batch envelope
    (``{"data": {BatchInsightResponse}, "meta": ...}``). Each per-phone result
    carries ``data.data`` -- the SAME row-of-dicts list the export reads today as
    ``response.data``. This folds the batch back into the per-office shape the
    workflow distributes, with NO data loss: a failed / absent office yields an
    EMPTY list (an empty deck for that office), never a crash and never a dropped
    key. Handles BOTH the phone-only (``results``) and compound-key
    (``pair_results``) response modes.

    Returns:
        Mapping of ``office_phone`` -> list of row dicts (empty list on per-office
        error / missing data).
    """
    payload = body.get("data") or {}
    per_office: dict[str, list[dict[str, Any]]] = {}

    for key in ("results", "pair_results"):
        entries = payload.get(key)
        if not entries:
            continue
        for entry in entries:
            phone = entry.get("phone")
            if phone is None:
                continue
            rows: list[dict[str, Any]] = []
            if entry.get("status") == "success":
                inner = entry.get("data")
                if isinstance(inner, dict):
                    candidate = inner.get("data")
                    if isinstance(candidate, list):
                        rows = candidate
            per_office[phone] = rows

    return per_office


@dataclass(frozen=True)
class AttributionCoverage:
    """Client-side typed mirror of the data plane's ``AttributionCoverage`` sidecar.

    provenance-to-the-human Sprint 4 (coverage-disclosure-at-render): a small frozen
    mirror of the coverage block the data plane emits alongside ``weights_version``
    in the operator batch's per-phone ``data.meta`` (autom8y-data ``_insights.py:396``
    build + ``from_sidecar_payload:568`` shape). The values are read VERBATIM from
    the sidecar; this carrier only NAMES the render-time contract (which fields the
    OFFER TABLE coverage line reads) -- the data plane owns the single source of
    truth. If the sidecar's shape changes this mirror is revisited under a NAMED
    ruling, never silently widened (mirrors the WEIGHTED_CONSUMER_METRICS discipline).

    ``status`` is the discriminant (the three-valued coverage envelope's tag):

    - ``"measured"``: the window HAS attribution coverage; ``orphan_spend_share`` is
      the fraction of spend NOT attributed to a specific ad (the ignorance FLOOR the
      render discloses as ``>= X% unattributed``). The complement is a LOWER bound on
      attribution, never a point "coverage 86%" claim, never a CI-shaped interval.
    - ``"no_data"``: the window has NO coverage measurement (disclosed-unknown, never
      rendered as 0% or 100% -- an absence of measurement is not full or zero
      attribution). The share fields are not meaningful in this state.

    Absence of the WHOLE block (no ``AttributionCoverage`` at all) is carried on
    :class:`OperatorBatchMeta` as ``coverage=None`` + ``coverage_expected`` -- a
    distinct, typed "this table makes no coverage promise" state (see there). None is
    a first-class typed state the render reads, NOT a null-coerced stand-in (G4).

    Attributes:
        status: ``"measured"`` or ``"no_data"`` -- the coverage envelope discriminant.
        coverage_pct: Fraction (or percent, verbatim from the sidecar) of spend that
            IS attributed. The render does NOT surface this as a point claim; the
            disclosed floor rides ``orphan_spend_share`` instead. Carried for parity
            with the sidecar and possible future disclosure, None when absent.
        orphan_spend_share: Fraction of spend NOT attributed to a specific ad (the
            "orphan ads" share). The render's MEASURED line discloses this as the
            ``>=``-floor of unattributed spend. None when absent.
        total_spend: Total spend over the window the shares are computed against
            (verbatim from the sidecar), or None when absent.
    """

    status: Literal["measured", "no_data"]
    coverage_pct: float | None = None
    orphan_spend_share: float | None = None
    total_spend: float | None = None


def _coverage_from_meta_block(meta: dict[str, Any]) -> tuple[AttributionCoverage | None, bool]:
    """Read ``(coverage, coverage_expected)`` from one per-phone ``data.meta`` block.

    The coverage siblings live NEXT TO ``weights_version`` / ``data_freshness`` in the
    per-phone meta (autom8y-data ``from_sidecar_payload:568``):

    - ``coverage_expected`` (bool): ``False`` == "this table makes no coverage
      promise" (honest-absent); ``True`` == a coverage block is contractually
      expected for this table. Defaults to ``False`` when the key is absent (the
      truthful DECK state: the batch path never runs the coverage processor, so no
      promise is made -- contract §2 supersession).
    - ``coverage`` (dict | absent): the ``AttributionCoverage`` sidecar. Parsed to the
      typed :class:`AttributionCoverage` mirror when present with a recognized
      ``status``; ``None`` when the block is absent or malformed (declared absence,
      NOT a throw -- the transport is passthrough, §2.1 corollary; a would-be dropped
      ``coverage_expected=True``+absent state is carried truthfully, never fabricated
      into a ceiling).

    Returns:
        ``(AttributionCoverage | None, coverage_expected)``. ``(None, False)`` is the
        deck honest-absent state; ``(None, True)`` is the would-be-dropped state the
        render discloses as unknown (never a fabricated full-attribution reading).
    """
    coverage_expected = bool(meta.get("coverage_expected", False))
    raw = meta.get("coverage")
    if not isinstance(raw, dict):
        return None, coverage_expected
    status = raw.get("status")
    if status not in ("measured", "no_data"):
        # Unrecognized/malformed coverage payload: declared absence, not a throw.
        return None, coverage_expected
    return (
        AttributionCoverage(
            status=status,
            coverage_pct=_as_float_or_none(raw.get("coverage_pct")),
            orphan_spend_share=_as_float_or_none(raw.get("orphan_spend_share")),
            total_spend=_as_float_or_none(raw.get("total_spend")),
        ),
        coverage_expected,
    )


def _as_float_or_none(value: Any) -> float | None:
    """Coerce a sidecar numeric to float, else None (no throw on a bad/absent value)."""
    if isinstance(value, bool):
        # bool is an int subclass; a coverage share is never a bool. Reject it.
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


@dataclass(frozen=True)
class OperatorBatchMeta:
    """Response/META-grain provenance carried across the operator batch seam.

    provenance-to-the-human Sprint 1 (render-wiring, H5): the SIBLING of
    :func:`distribute_per_office`. The rows-fold is FROZEN (its 30+ callers and the
    denial-union contract are unchanged); this typed carrier ADDS the provenance
    that fold structurally drops -- the per-phone ``entry["data"]["meta"]`` block
    (data plane ``StandardResponse.meta`` == ``ResponseMetadata``), sibling to the
    rows at ``entry["data"]["data"]``.

    Grain (contract §3.1 / §3.2): RESPONSE/META -- ONE ``weights_version`` and ONE
    ``synced_at`` per batch response (every office in a single ``execute-batch`` is
    scored by the SAME process-global registry version). These fields are therefore
    a property of the batch, not the office; the carrier holds a single value each.

    Absence is DECLARED, not coerced: ``weights_version=None`` / ``synced_at=None``
    mean "the batch carried no such stamp" (e.g. an all-unweighted insight, or a
    meta-less legacy envelope). None is a first-class typed state the render's C2
    guard reads -- it is NOT a null-coerced stand-in for a value (G4).

    Attributes:
        weights_version: The applied show-probability weight-scheme version-id
            (the single provenance token, e.g. ``2026-03-24-static-UNRATIFIED``),
            or None when the batch response carried no ``weights_version``.
        synced_at: ISO-8601 asOf timestamp of the data snapshot the batch was
            computed over (``DataFreshness.synced_at``), or None when unknown.
        coverage: provenance-to-the-human Sprint 4: the attribution-coverage sidecar
            (:class:`AttributionCoverage`), sibling to ``weights_version`` in the
            per-phone ``data.meta``. ``None`` == the batch carried NO coverage block.
            Read together with ``coverage_expected``: ``coverage=None`` +
            ``coverage_expected=False`` is the deck honest-absent state ("not
            measured"); ``coverage=None`` + ``coverage_expected=True`` is the
            would-be-dropped state the render discloses as unknown. None is a typed
            state, never a null-coerced full-attribution reading (G4).
        coverage_expected: provenance-to-the-human Sprint 4: whether a coverage block
            is CONTRACTUALLY expected for this table. ``False`` == "this table makes
            no coverage promise" (honest-absent; the truthful DECK state -- the batch
            path never runs the coverage processor, contract §2 supersession).
            ``True`` == coverage is expected (a ``coverage=None`` alongside it is the
            would-be-dropped state, disclosed as unknown -- NOT armable on the deck
            today, F5-coverage-THROW watch). Defaults ``False`` (no promise).
    """

    weights_version: str | None = None
    synced_at: str | None = None
    coverage: AttributionCoverage | None = None
    coverage_expected: bool = False


# The empty/absent-provenance carrier: a served-but-provenance-free batch. A
# module-level singleton so callers can compare identity and so an empty batch and
# a meta-less batch share one canonical "nothing to disclose" value.
_EMPTY_OPERATOR_BATCH_META = OperatorBatchMeta()


def _extract_entry_meta(entry: dict[str, Any]) -> dict[str, Any] | None:
    """Return a successful per-phone entry's ``data.meta`` dict, else None."""
    if entry.get("status") != "success":
        return None
    inner = entry.get("data")
    if not isinstance(inner, dict):
        return None
    meta = inner.get("meta")
    return meta if isinstance(meta, dict) else None


def distribute_per_office_meta(body: dict[str, Any]) -> OperatorBatchMeta:
    """Extract the RESPONSE/META-grain provenance from an operator batch envelope.

    The SIBLING extractor to :func:`distribute_per_office`. Walks the same
    per-phone ``results`` / ``pair_results`` entries but reads the ``data.meta``
    provenance block instead of the ``data.data`` rows, returning a single typed
    :class:`OperatorBatchMeta` at response grain.

    The G1 cardinality invariant (contract §3.1 row-grain trigger) is enforced
    HERE, at the fold, where the whole batch is visible: every successful
    per-phone entry that carries a ``weights_version`` MUST carry the SAME one. A
    batch whose offices disagree on the version-id is a divergent-scheme batch for
    which a single META token would be a LIE (§3.1). That is ORDERED BEFORE any
    single token is chosen -- the divergent state is caught before it can be
    silently collapsed to one office's id -- and raises the typed
    :class:`OperatorBatchVersionSkewError` (never returns a fabricated single
    token, never null-coerces the disagreement away; G3/G4).

    ``synced_at`` rides ``data.meta.data_freshness.synced_at`` (the existing asOf
    slot, contract §3.2); a meta-less or freshness-less batch yields ``None``
    (declared absence, not a throw -- the transport is passthrough, §2.1 corollary).

    ``coverage`` / ``coverage_expected`` (Sprint 4) ride ``data.meta.coverage`` /
    ``data.meta.coverage_expected``, siblings of ``weights_version``. Coverage is a
    property of the batch RESPONSE (one processor decision scores every office in a
    single execute-batch), so the FIRST observed block is taken, mirroring the
    ``synced_at`` first-non-None rule. Absence yields ``coverage=None`` +
    ``coverage_expected=False`` (deck honest-absent) -- a typed state, never a throw.

    Returns:
        OperatorBatchMeta at response grain. ``_EMPTY_OPERATOR_BATCH_META`` (all
        fields empty) when the body carries no successful entry or no provenance.

    Raises:
        OperatorBatchVersionSkewError: two or more offices in the SAME batch carry
            DISTINCT ``weights_version`` ids -- the META-grain precondition (one id
            per batch) is violated. Fails loud; the caller must not render a single
            token that lies for the divergent offices.
    """
    payload = body.get("data") or {}

    distinct_versions: set[str] = set()
    synced_at: str | None = None
    coverage: AttributionCoverage | None = None
    coverage_expected = False
    coverage_seen = False

    for key in ("results", "pair_results"):
        entries = payload.get(key)
        if not entries:
            continue
        for entry in entries:
            meta = _extract_entry_meta(entry)
            if meta is None:
                continue
            version = meta.get("weights_version")
            if isinstance(version, str):
                distinct_versions.add(version)
            if synced_at is None:
                freshness = meta.get("data_freshness")
                if isinstance(freshness, dict):
                    candidate = freshness.get("synced_at")
                    if isinstance(candidate, str):
                        synced_at = candidate
            if not coverage_seen:
                # First observed per-phone meta owns the batch coverage (one
                # processor decision per execute-batch). coverage_expected is read
                # even when the coverage block itself is absent (honest-absent).
                coverage, coverage_expected = _coverage_from_meta_block(meta)
                coverage_seen = True

    # G1 CARDINALITY (ordered before a token is chosen): a batch MUST NOT carry
    # >1 distinct weights_version at META grain. Caught here, loud and typed.
    if len(distinct_versions) > 1:
        raise OperatorBatchVersionSkewError(
            "operator batch carries divergent weights_version ids at META grain: "
            f"{sorted(distinct_versions)!r}",
            reason="weights_version_skew",
            versions=sorted(distinct_versions),
        )

    if not distinct_versions and synced_at is None and coverage is None and not coverage_expected:
        return _EMPTY_OPERATOR_BATCH_META

    weights_version = next(iter(distinct_versions), None)
    return OperatorBatchMeta(
        weights_version=weights_version,
        synced_at=synced_at,
        coverage=coverage,
        coverage_expected=coverage_expected,
    )


def _build_request_body(
    insight_name: str,
    phones: list[str],
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
) -> dict[str, Any]:
    """Build the ``OperatorBatchInsightRequest`` body (period normalized)."""
    request_body: dict[str, Any] = {"insight_name": insight_name, "phones": phones}
    if period is not None:
        # The data plane expects normalized presets (LIFETIME / T30 / ...), the
        # same normalization the SA batch path applies.
        request_body["period"] = _normalize_mod.normalize_period(period)
    if start_date is not None:
        request_body["start_date"] = start_date.isoformat()
    if end_date is not None:
        request_body["end_date"] = end_date.isoformat()
    if filters:
        request_body["filters"] = filters
    if limit is not None:
        request_body["limit"] = limit
    return request_body


async def _post_operator_batch(
    client: DataServiceClient,
    request_body: dict[str, Any],
    *,
    pacer: OperatorCallPacer | None = None,
    force_refresh_on_401: bool = True,
) -> Any:
    """POST one operator batch with the operator Bearer (no SA token, ever).

    Mints/reuses the operator token via the provider and injects it as a
    PER-REQUEST ``Authorization`` header on the dedicated operator client. One
    forced re-mint + retry on a 401.

    When a ``pacer`` is supplied, EACH HTTP attempt (the initial post AND the 401
    re-auth retry) reserves one budget token first, so the run budget counts actual
    wire calls (== server-side rate-limit consumption). ``pacer.acquire`` may raise
    :class:`BudgetExhausted`; callers serve what they reached and flag the run
    partial.
    """
    provider = client._get_operator_token_provider()
    http_client = await client._get_operator_client()

    async def _post(token: str) -> Any:
        if pacer is not None:
            # One token per HTTP attempt -- the 401 retry below is a second wire
            # call and a second server-side rate-limit hit, so it is budgeted too.
            await pacer.acquire()
        return await http_client.post(
            OPERATOR_BATCH_PATH,
            json=request_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    token = await provider.get_token()
    response = await _post(token)
    if response.status_code == 401 and force_refresh_on_401:
        token = await provider.get_token(force_refresh=True)
        response = await _post(token)
    return response


async def _acquire_and_post(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    pacer: OperatorCallPacer,
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
) -> Any:
    """POST one operator sub-batch under the pacer; honor Retry-After on 429.

    Returns the FINAL response (which may still be 429 after the bounded retries).
    Re-issues the SAME sub-batch (not a split) after honoring ``Retry-After``, up to
    ``_MAX_THROTTLE_RETRIES`` (TDD §5.2 step 5). Raises :class:`BudgetExhausted`
    (from :func:`_post_operator_batch`) when the run budget is spent.
    """
    body = _build_request_body(
        insight_name,
        phones,
        period=period,
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        limit=limit,
    )
    attempt = 0
    while True:
        response = await _post_operator_batch(client, body, pacer=pacer)
        if response.status_code == 429 and attempt < _MAX_THROTTLE_RETRIES:
            await pacer.honor_retry_after(response)
            attempt += 1
            continue
        return response


async def _bounded_bisect_serve(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    pacer: OperatorCallPacer,
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
    meta_sink: list[OperatorBatchMeta] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """EC-4 drift-resilient BOUNDED BISECTION on the operator route (never SA).

    Replaces the O(N) linear per-office sweep. On an all-or-nothing batch 404 over a
    >1-office sub-batch, binary-splits and recurses: an all-owned half 200s in ONE
    call (serving every office in it); a drift-bearing half 404s and splits further
    -> O(drift . log N) calls for clustered drift vs O(N) for the linear sweep. Every
    wire call is reserved from the shared run budget (``pacer``); when the budget or
    throttle stops it, the unreached offices are marked for prior-deck protection
    (RISK-4) and an empty (partial) result is returned -- NEVER a crash, NEVER the SA
    fleet-read (G-NO-FALLBACK).

    Status handling (TDD §5.2):
      - 200         -> distribute_per_office: serve EVERY office in this sub-batch.
      - 404, len==1 -> drift office: {} (empty deck, no oracle leak; definitive).
      - 404, len>1  -> split in half, recurse left then right, merge.
      - 403         -> raise OperatorMintRefusedError: the plane is closed (whole-run
                       INERT no-op upstream; NO prior deck overwritten).
      - 429 / 5xx / 401-after-retry / malformed -> mark_unreached + {} (skip this
                       sub-batch; prior deck protected; siblings already served are
                       preserved -- this path NEVER raises and NEVER falls back to SA).
    """
    try:
        response = await _acquire_and_post(
            client,
            insight_name,
            phones,
            pacer,
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            limit=limit,
        )
    except BudgetExhausted:
        # Run budget spent before this sub-batch could be served. Protect its
        # offices' prior decks (the per-office mirror of the INERT no-op guard).
        pacer.mark_unreached(phones)
        return {}

    status_code = response.status_code

    if status_code == 200:
        try:
            body = response.json()
        except ValueError:
            # Malformed 200: protect rather than overwrite prior decks with empty.
            pacer.mark_unreached(phones)
            return {}
        # Provenance side-channel (Sprint 1): capture this sub-batch's META-grain
        # provenance ADDITIVELY. The rows-fold below is byte-identical to the
        # pre-carry path; the meta extraction never alters it. A version-skew
        # WITHIN this sub-batch raises typed here (G1) -- the divergent state is
        # not merged silently.
        if meta_sink is not None:
            meta_sink.append(distribute_per_office_meta(body))
        return distribute_per_office(body)

    if status_code == 404:
        if len(phones) == 1:
            # Definitive drift office: empty deck, no oracle leak. NOT marked
            # unreached -- the route gave a definitive "not owned" answer, so the
            # existing publish-empty behavior for drift offices is preserved.
            return {}
        mid = len(phones) // 2
        served = await _bounded_bisect_serve(
            client,
            insight_name,
            phones[:mid],
            pacer,
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            limit=limit,
            meta_sink=meta_sink,
        )
        served.update(
            await _bounded_bisect_serve(
                client,
                insight_name,
                phones[mid:],
                pacer,
                period=period,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
                limit=limit,
                meta_sink=meta_sink,
            )
        )
        return served

    if status_code == 403:
        # The operator plane is closed (mint/route forbidden). Fail closed -- raise
        # so the workflow goes INERT (no-op) and NO prior deck is overwritten.
        raise OperatorMintRefusedError(
            "operator batch forbidden (HTTP 403)",
            reason="route_forbidden_403",
            status_code=403,
        )

    # 429 (after retries) / 401-after-retry / 5xx / other: a transient or contract
    # failure for THIS sub-batch. Skip it (mark unreached -> prior deck protected),
    # NEVER an SA fleet-read, NEVER raise to lose already-served siblings.
    pacer.mark_unreached(phones)
    return {}


def _chunked(phones: list[str], size: int) -> list[list[str]]:
    """Split ``phones`` into contiguous chunks of at most ``size`` offices."""
    return [phones[i : i + size] for i in range(0, len(phones), size)]


async def _serve_unbisected(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    pacer: OperatorCallPacer,
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
    meta_sink: list[OperatorBatchMeta] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """POST one batch with NO bisection; fail closed (raise) on a non-200.

    Used for the single whole-request office and the ``allow_bisect=False`` path. A
    bare 404-as-oracle here is a definitive denial of the entire request (there is no
    owned subset to recover via splitting), so it raises -- the workflow renders that
    request's table empty (RT-2/RT-3). A spent budget returns {} gracefully.
    """
    try:
        response = await _acquire_and_post(
            client,
            insight_name,
            phones,
            pacer,
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            limit=limit,
        )
    except BudgetExhausted:
        pacer.mark_unreached(phones)
        return {}

    status_code = response.status_code
    if status_code == 404:
        raise OperatorAccessDeniedError(
            "operator batch refused (bare 404-as-oracle)",
            reason="route_denied_404",
            status_code=404,
        )
    if status_code == 403:
        # Defensive: surface as a mint refusal (the operator plane is closed).
        raise OperatorMintRefusedError(
            "operator batch forbidden (HTTP 403)",
            reason="route_forbidden_403",
            status_code=403,
        )
    if status_code >= 400:
        # 401 (after retry), 429, 5xx, etc. Fail closed -- NO SA fleet-read fallback.
        raise OperatorAccessDeniedError(
            f"operator batch failed (HTTP {status_code})",
            reason=f"route_error_{status_code}",
            status_code=status_code,
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise OperatorAccessDeniedError(
            "operator batch returned a malformed response",
            reason="route_malformed_response",
        ) from exc

    if meta_sink is not None:
        meta_sink.append(distribute_per_office_meta(body))
    return distribute_per_office(body)


def _merge_batch_metas(metas: list[OperatorBatchMeta]) -> OperatorBatchMeta:
    """Reduce per-sub-batch metas to ONE response-grain :class:`OperatorBatchMeta`.

    The whole operator run over ``O`` may fan out into multiple sub-batches
    (chunking to <=100 + drift bisection); each served 200 yields its own META.
    The G1 cardinality invariant applies to the WHOLE run: every sub-batch that
    carried a ``weights_version`` MUST have carried the SAME one (contract §3.1 --
    one registry scheme scores the whole owned set). A cross-sub-batch divergence
    is caught here, ORDERED BEFORE a single token is chosen, and raised typed
    (never silently reduced to the first sub-batch's id; G3/G4).

    ``synced_at`` takes the first non-None asOf observed across sub-batches (all
    sub-batches of one run read the same materialization snapshot, §3.2).

    ``coverage`` / ``coverage_expected`` (Sprint 4) take the first sub-batch that
    OBSERVED a coverage decision (one processor decision scores the whole owned set),
    mirroring ``synced_at``. A run where no sub-batch carried coverage collapses to
    ``coverage=None`` + ``coverage_expected=False`` (deck honest-absent).
    """
    distinct_versions = {m.weights_version for m in metas if m.weights_version is not None}
    if len(distinct_versions) > 1:
        raise OperatorBatchVersionSkewError(
            "operator run carries divergent weights_version ids across sub-batches: "
            f"{sorted(distinct_versions)!r}",
            reason="weights_version_skew",
            versions=sorted(distinct_versions),
        )
    weights_version = next(iter(distinct_versions), None)
    synced_at = next((m.synced_at for m in metas if m.synced_at is not None), None)
    # First sub-batch that observed a coverage decision owns the run's coverage. A
    # sub-batch "observed" coverage iff it carried the block OR was told a promise is
    # expected (coverage_expected True); a bare all-default meta did not observe it.
    coverage_meta = next(
        (m for m in metas if m.coverage is not None or m.coverage_expected),
        None,
    )
    coverage = coverage_meta.coverage if coverage_meta is not None else None
    coverage_expected = coverage_meta.coverage_expected if coverage_meta is not None else False
    if weights_version is None and synced_at is None and coverage is None and not coverage_expected:
        return _EMPTY_OPERATOR_BATCH_META
    return OperatorBatchMeta(
        weights_version=weights_version,
        synced_at=synced_at,
        coverage=coverage,
        coverage_expected=coverage_expected,
    )


async def execute_operator_batch(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    *,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    pacer: OperatorCallPacer | None = None,
    allow_bisect: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """POST the operator batch over the owned offices; return ``{phone: rows}``.

    Mints (or reuses) a single operator Bearer token and POSTs the
    ``OperatorBatchInsightRequest`` shape (``insight_name`` + ``phones`` + period/
    range/filters/limit) with ``Authorization: Bearer <operator_token>``, folding the
    response per-office via :func:`distribute_per_office`. Every wire call is reserved
    from ``pacer`` (a shared run budget when threaded by the workflow, else a fresh
    per-call budget) so the AGGREGATE wire count self-limits strictly below the
    server's 10/min DoS guard (INV-1).

    Shape (TDD §5.2/§5.4):

    - ``phones`` chunked to <=100 (FILE-3 / RISK-3) so a large fleet never 422s.
    - A single whole-request office (or ``allow_bisect=False``) posts once and fails
      closed on a non-200 (the bare 404-as-oracle raises -- RT-2/RT-3).
    - A multi-office chunk that 404s is bisected (:func:`_bounded_bisect_serve`):
      owned sub-batches 200 in one call; a drift office costs O(drift . log N) and is
      skipped (empty deck, no oracle leak). Offices the budget/throttle could not
      reach are marked on the pacer for prior-deck protection (RISK-4).

    Raises:
        OperatorMintRefusedError: the mint refused (incl. the INERT empty-allowlist
            403) or the route returned 403. Fails closed -- NO SA fleet-read fallback.
        OperatorAccessDeniedError: a single whole-request office (or unbisected batch)
            returned the bare 404-as-oracle or another error status. Fails closed --
            NO SA fleet-read fallback.
    """
    # The rows-only public contract (30+ callers, denial union) is UNCHANGED: it is
    # the meta-carrying path with the provenance side-channel discarded.
    served, _meta = await _execute_operator_batch_inner(
        client,
        insight_name,
        phones,
        period=period,
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        limit=limit,
        pacer=pacer,
        allow_bisect=allow_bisect,
        collect_meta=False,
    )
    return served


async def execute_operator_batch_with_meta(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    *,
    period: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    filters: dict[str, Any] | None = None,
    limit: int | None = None,
    pacer: OperatorCallPacer | None = None,
    allow_bisect: bool = True,
) -> tuple[dict[str, list[dict[str, Any]]], OperatorBatchMeta]:
    """As :func:`execute_operator_batch`, but ALSO carry the response-grain meta.

    provenance-to-the-human Sprint 1 (render-wiring, H5): the sibling entry point
    that surfaces the ``weights_version`` + asOf the plain rows-fold drops. Returns
    ``(per_office_rows, OperatorBatchMeta)``. The rows are byte-identical to
    :func:`execute_operator_batch` (same wire path, same fold); the meta is the
    additive provenance side-channel merged across all served sub-batches (§3.1
    G1 cardinality enforced by :func:`_merge_batch_metas`).

    Raises:
        OperatorMintRefusedError / OperatorAccessDeniedError: as
            :func:`execute_operator_batch`.
        OperatorBatchVersionSkewError: the served offices carry >1 distinct
            ``weights_version`` (G1; the META-grain precondition is violated).
    """
    return await _execute_operator_batch_inner(
        client,
        insight_name,
        phones,
        period=period,
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        limit=limit,
        pacer=pacer,
        allow_bisect=allow_bisect,
        collect_meta=True,
    )


async def _execute_operator_batch_inner(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
    pacer: OperatorCallPacer | None,
    allow_bisect: bool,
    collect_meta: bool,
) -> tuple[dict[str, list[dict[str, Any]]], OperatorBatchMeta]:
    """The single wire+fold path shared by the rows-only and meta-carrying entries.

    ``collect_meta`` threads a ``meta_sink`` through the serve functions so each
    served 200 sub-batch appends its META additively; the sink is merged to one
    response-grain :class:`OperatorBatchMeta` at the end (empty meta when
    ``collect_meta`` is False or nothing was served).
    """
    # Honor the existing emergency kill switch for the live era (INERT today).
    client._check_feature_enabled()

    if not phones:
        # Nothing owned to read -- an empty batch is a no-op (no wire call).
        return {}, _EMPTY_OPERATOR_BATCH_META

    # A fresh per-call budget when the caller does not thread a shared one. The
    # workflow threads ONE pacer across all 4 insights so the cap is per-RUN, not
    # per-insight (RISK-5).
    pacer = pacer if pacer is not None else OperatorCallPacer()

    meta_sink: list[OperatorBatchMeta] | None = [] if collect_meta else None

    if len(phones) == 1 or not allow_bisect:
        served_single = await _serve_unbisected(
            client,
            insight_name,
            phones,
            pacer,
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            limit=limit,
            meta_sink=meta_sink,
        )
        meta = (
            _merge_batch_metas(meta_sink) if meta_sink is not None else _EMPTY_OPERATOR_BATCH_META
        )
        return served_single, meta

    served: dict[str, list[dict[str, Any]]] = {}
    for chunk in _chunked(phones, OPERATOR_BATCH_CEILING):
        served.update(
            await _bounded_bisect_serve(
                client,
                insight_name,
                chunk,
                pacer,
                period=period,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
                limit=limit,
                meta_sink=meta_sink,
            )
        )
    meta = _merge_batch_metas(meta_sink) if meta_sink is not None else _EMPTY_OPERATOR_BATCH_META
    return served, meta
