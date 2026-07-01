"""OfferWarmComplete attestation -> AMP Prometheus remote-write (node-1).

Emits the per-entity ``OfferWarmComplete`` attestation as the Prometheus
timestamp gauge

    autom8y_offer_warm_complete_timestamp{entity_type="<entity>"}

to Amazon Managed Service for Prometheus (AMP) via the SAME remote-write path
the reconciliation service (ASR) already uses -- ``autom8y_telemetry.aws``
(``TimeSeries`` / ``Sample`` / ``emit_timeseries`` / ``resolve_credentials`` /
``RemoteWriteConfig``). This is NOT a CloudWatch->AMP stream: the warmer signs a
single SigV4 remote-write POST per warmed entity, exactly mirroring
``ReconciliationMetrics.emit_amp`` (autom8y-reconciliation ``metrics.py``).

Cross-repo series contract (load-bearing -- both sides MUST agree verbatim):
autom8y-asana PRODUCES ``autom8y_offer_warm_complete_timestamp{entity_type=...}``;
the monorepo's ``slo_offer_freshness`` recording rules + node-4 freshness alerts
CONSUME the ``entity_type="offer"`` series. A name/label drift silently breaks the
downstream freshness arm, so the name and label key are frozen module constants
and guarded by the two-sided canary (``test_offer_warm_amp.py``).

Emission discipline (mirrors ASR ADR-ASR-009 / ADR-ASR-010):
  * SUCCESS-ONLY. The caller invokes this ONLY on ``WarmResult.SUCCESS`` for a
    given entity; a FAILURE / PARTIAL / SKIPPED warm MUST NOT emit (a stale or
    absent series is what the downstream freshness alert is built to catch).
  * Last-write-wins GAUGE. One sample per call; the value is the completion epoch
    in SECONDS (a freshness timestamp the consumer reads as "last offer warm
    completion"), the sample's own timestamp is now in MILLISECONDS (the
    remote-write wire contract).
  * Flag-gated, default-OFF. ``RemoteWriteConfig.from_env()`` resolves
    ``ASR_AMP_EMIT_ENABLED`` / ``AMP_REMOTE_WRITE_ENDPOINT`` / ``AWS_REGION``;
    ``is_active`` is False unless emission is enabled AND an endpoint is set, so
    the warmer stays INERT until the operator arms the path (terraform lever).
  * Loud-on-failure, best-effort. Past the ``is_active`` gate, a missing
    credential or a push exception emits a positive ``OfferWarmAmpFailed=1``
    CloudWatch break-glass counter (a sink that is up -- never AMP, the path that
    failed) and logs at error, so a stalled / mis-keyed / non-emitting sync is
    structurally falsifiable rather than a silent green. The whole emit is
    wrapped so an AMP failure NEVER crashes the warm cycle.
"""

from __future__ import annotations

import time

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric

logger = get_logger(__name__)

# --- Cross-repo series contract (FROZEN -- must match the monorepo consumer) ---
# autom8y-asana produces; slo_offer_freshness recording rules + node-4 alerts
# consume the entity_type="offer" series. Do NOT rename either constant without
# a coordinated change to the consuming recording rules.
OFFER_WARM_COMPLETE_METRIC = "autom8y_offer_warm_complete_timestamp"
ENTITY_TYPE_LABEL = "entity_type"

# CloudWatch break-glass counter name for an attempted-and-failed AMP emit.
# Emitted via CloudWatch (the value-blind path that is up), NOT via AMP (the
# path being reported failed). Mirrors ASR's AmpRemoteWriteFailed loudness.
AMP_FAILED_METRIC = "OfferWarmAmpFailed"


def emit_offer_warm_complete(entity_type: str) -> None:
    """Emit ``OfferWarmComplete`` for ``entity_type`` to AMP (SUCCESS-only).

    Build a single last-write-wins gauge sample for
    ``autom8y_offer_warm_complete_timestamp{entity_type=<entity_type>}`` and push
    it to AMP with one SigV4-signed remote-write POST, via the same telemetry
    primitive ASR uses. Call ONLY on ``WarmResult.SUCCESS`` -- this function does
    not itself check the warm result; the SUCCESS gate is the caller's
    responsibility (so a silent drop of THIS call on the success path fails the
    canary).

    Flag-gated (default-OFF until armed), loud-on-failure, best-effort: an AMP
    failure emits the ``OfferWarmAmpFailed`` break-glass counter and is swallowed
    so the warm cycle is never crashed by telemetry.

    Args:
        entity_type: The entity type that reached ``WarmResult.SUCCESS`` (e.g.
            ``"offer"``). Becomes the ``entity_type`` label value verbatim.
    """
    try:
        from autom8y_telemetry.aws.config import RemoteWriteConfig

        cfg = RemoteWriteConfig.from_env()
        if not cfg.is_active or cfg.endpoint is None:
            # Disabled / unconfigured is a benign skip: prod stays inert until the
            # operator arms ASR_AMP_EMIT_ENABLED + AMP_REMOTE_WRITE_ENDPOINT (the
            # terraform lever). Stay SILENT here -- a true series absence is caught
            # loudly by the downstream freshness alert, not by this skip.
            logger.debug(
                "offer_warm_amp_skipped_disabled",
                extra={
                    "entity_type": entity_type,
                    "enabled": cfg.enabled,
                    "has_endpoint": bool(cfg.endpoint),
                },
            )
            return
        endpoint: str = cfg.endpoint  # is_active guarantees non-None; narrow for mypy

        from autom8y_telemetry.aws.remote_write import (
            Sample,
            TimeSeries,
            emit_timeseries,
            resolve_credentials,
        )

        now = time.time()
        # Last-write-wins gauge: value = completion epoch SECONDS (freshness
        # timestamp the consumer reads); sample timestamp = now MILLISECONDS (the
        # remote-write wire contract is ms).
        series = [
            TimeSeries(
                labels={
                    "__name__": OFFER_WARM_COMPLETE_METRIC,
                    ENTITY_TYPE_LABEL: entity_type,
                },
                samples=[Sample(value=now, timestamp_ms=int(now * 1000))],
            )
        ]

        creds = resolve_credentials()
        if creds is None:
            # Past the is_active gate (armed + endpoint set) with no resolvable
            # execution-role credentials: an attempted-and-failed emit, NOT a
            # benign skip. Make it loud so a mis-keyed / unauthorized warmer role
            # is structurally falsifiable, then return without pushing.
            logger.error(
                "offer_warm_amp_failed_no_credentials",
                extra={"entity_type": entity_type},
            )
            _emit_failure_counter(entity_type=entity_type, reason="no_credentials")
            return

        emit_timeseries(endpoint, series, region=cfg.region, creds=creds)
        logger.debug(
            "offer_warm_amp_emitted",
            extra={"entity_type": entity_type, "metric": OFFER_WARM_COMPLETE_METRIC},
        )
    except Exception:  # BROAD-CATCH: telemetry -- an AMP failure must never crash the warm cycle
        # Past the is_active gate an ATTEMPT failed (import / series-build /
        # resolve_credentials / SigV4 / 5xx / snappy). A bare debug-and-swallow
        # here would be the silent-green the freshness arm exists to escape: make
        # it loud (error + positive break-glass counter), but PRESERVE best-effort
        # (never propagate into the warm cycle). The counter reaches CloudWatch (a
        # sink that is up), never AMP (the path that just failed).
        logger.exception(
            "offer_warm_amp_emission_failed",
            extra={"entity_type": entity_type},
        )
        _emit_failure_counter(entity_type=entity_type, reason="push_failed")


def _emit_failure_counter(*, entity_type: str, reason: str) -> None:
    """Emit a positive ``OfferWarmAmpFailed`` counter via the CloudWatch sink.

    Mirrors ASR's INV-2/C7 loudness: an enabled-and-attempted-but-FAILED AMP emit
    must be structurally falsifiable. The counter is emitted via CloudWatch
    (``emit_metric``) -- NOT via AMP -- because the path being reported failed is
    precisely the AMP remote-write path; the failure signal must reach a sink that
    is up. Wrapped in its own guard so a CloudWatch failure cannot crash the warm
    cycle either, but stays loud (warning, never debug).

    Args:
        entity_type: The entity whose AMP emit failed (``entity_type`` dimension).
        reason: Short machine-readable cause (``"no_credentials"`` /
            ``"push_failed"``) recorded as a ``reason`` dimension.
    """
    try:
        emit_metric(
            AMP_FAILED_METRIC,
            1,
            dimensions={"entity_type": entity_type, "reason": reason},
        )
    except (
        Exception  # noqa: BLE001
    ):  # BROAD-CATCH: break-glass -- losing loudness must not crash the warm cycle
        logger.warning(
            "offer_warm_amp_failure_counter_emission_failed",
            extra={"entity_type": entity_type, "reason": reason},
        )
