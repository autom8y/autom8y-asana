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

from typing import TYPE_CHECKING, Any

from autom8_asana.clients.data import _normalize as _normalize_mod
from autom8_asana.clients.data._endpoints._pacer import BudgetExhausted, OperatorCallPacer
from autom8_asana.errors import OperatorAccessDeniedError, OperatorMintRefusedError

if TYPE_CHECKING:
    from datetime import date

    from autom8_asana.clients.data.client import DataServiceClient

# The mounted path of the operator-plane per-office batch route (data plane
# OPERATOR_BATCH_ROUTE_PATH). Single literal here; the data plane owns the SoT.
OPERATOR_BATCH_PATH = "/api/v1/insights/operator/execute-batch"

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
            return distribute_per_office(response.json())
        except ValueError:
            # Malformed 200: protect rather than overwrite prior decks with empty.
            pacer.mark_unreached(phones)
            return {}

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

    return distribute_per_office(body)


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
    # Honor the existing emergency kill switch for the live era (INERT today).
    client._check_feature_enabled()

    if not phones:
        # Nothing owned to read -- an empty batch is a no-op (no wire call).
        return {}

    # A fresh per-call budget when the caller does not thread a shared one. The
    # workflow threads ONE pacer across all 4 insights so the cap is per-RUN, not
    # per-insight (RISK-5).
    pacer = pacer if pacer is not None else OperatorCallPacer()

    if len(phones) == 1 or not allow_bisect:
        return await _serve_unbisected(
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
            )
        )
    return served
