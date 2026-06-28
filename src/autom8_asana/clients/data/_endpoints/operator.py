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
from autom8_asana.errors import OperatorAccessDeniedError, OperatorMintRefusedError

if TYPE_CHECKING:
    from datetime import date

    from autom8_asana.clients.data.client import DataServiceClient

# The mounted path of the operator-plane per-office batch route (data plane
# OPERATOR_BATCH_ROUTE_PATH). Single literal here; the data plane owns the SoT.
OPERATOR_BATCH_PATH = "/api/v1/insights/operator/execute-batch"


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
    force_refresh_on_401: bool = True,
) -> Any:
    """POST one operator batch with the operator Bearer (no SA token, ever).

    Mints/reuses the operator token via the provider and injects it as a
    PER-REQUEST ``Authorization`` header on the dedicated operator client. One
    forced re-mint + retry on a 401.
    """
    provider = client._get_operator_token_provider()
    http_client = await client._get_operator_client()

    async def _post(token: str) -> Any:
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


async def _drift_sweep(
    client: DataServiceClient,
    insight_name: str,
    phones: list[str],
    *,
    period: str | None,
    start_date: date | None,
    end_date: date | None,
    filters: dict[str, Any] | None,
    limit: int | None,
) -> dict[str, list[dict[str, Any]]]:
    """EC-4 bounded per-office sweep ON THE OPERATOR ROUTE (never SA).

    Fired only when an all-or-nothing batch 404s over >1 office. Calls the SAME
    operator route once per office: a 200 contributes that office's rows; ANY
    other status (404 drift, 429, 5xx) skips that office (empty deck). Never an SA
    fleet-read. If EVERY office 404s (e.g. a non-allowlisted insight, not drift),
    returns an empty map -- the workflow renders empty decks, no crash.
    """
    swept: dict[str, list[dict[str, Any]]] = {}
    for phone in phones:
        single_body = _build_request_body(
            insight_name,
            [phone],
            period=period,
            start_date=start_date,
            end_date=end_date,
            filters=filters,
            limit=limit,
        )
        try:
            response = await _post_operator_batch(client, single_body)
        except Exception:  # noqa: BLE001 -- per-office isolation; one office never fails the sweep
            continue
        if response.status_code != 200:
            # Drift / denial / transient for THIS office: skip (empty), no SA path.
            continue
        try:
            swept.update(distribute_per_office(response.json()))
        except ValueError:
            continue
    return swept


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
    allow_drift_sweep: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """POST one operator batch over the owned offices; return ``{phone: rows}``.

    Mints (or reuses) a single operator Bearer token, POSTs the
    ``OperatorBatchInsightRequest`` shape (``insight_name`` + ``phones`` + period/
    range/filters/limit) with ``Authorization: Bearer <operator_token>``, and folds
    the response per-office via :func:`distribute_per_office`. On an all-or-nothing
    batch 404 over >1 office, falls back to the EC-4 :func:`_drift_sweep` (still on
    the operator route).

    Raises:
        OperatorMintRefusedError: the mint refused (incl. the INERT empty-allowlist
            403). Propagated from the token provider. Fails closed -- no SA fallback.
        OperatorAccessDeniedError: the route returned the bare 404-as-oracle for a
            single-office request (no sweep possible) or another error status.
            Fails closed -- no SA fleet-read fallback.
    """
    # Honor the existing emergency kill switch for the live era (INERT today).
    client._check_feature_enabled()

    if not phones:
        # Nothing owned to read -- an empty batch is a no-op (no wire call).
        return {}

    request_body = _build_request_body(
        insight_name,
        phones,
        period=period,
        start_date=start_date,
        end_date=end_date,
        filters=filters,
        limit=limit,
    )
    response = await _post_operator_batch(client, request_body)
    status_code = response.status_code

    if status_code == 404:
        # The bare 404-as-oracle. Over >1 office this is indistinguishable from
        # ownership drift, so try the bounded per-office sweep (operator route
        # only). Over a single office there is nothing to sweep -- fail closed.
        if allow_drift_sweep and len(phones) > 1:
            return await _drift_sweep(
                client,
                insight_name,
                phones,
                period=period,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
                limit=limit,
            )
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
