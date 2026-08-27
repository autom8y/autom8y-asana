"""Lambda handler for the scheduled substrate-v2 provability sweep (EMIT-2).

This is option (b) of the RULING's G2 — the terraform EventBridge schedule the
in-process driver (``substrate/prov_sweep.py``) explicitly DEFERRED to a
post-window packet. Scheduled every 900s (rate(15 minutes)) by the autom8y
monorepo module ``prov_sweep`` in ``terraform/services/asana`` — the cadence
``offer_freshness_prov_alarms.tf`` (PROV-8/9, ``var.offer_freshness_evaluation_
cadence_seconds = 900``) and ``substrate_v2_provability_alarms.tf`` (PROV-1..6)
assume. With this handler live, ``EvaluatorHeartbeat`` becomes DENSE and
query-independent: PROV-2 (in ALARM since 2026-08-12, when the last operator-run
S8-2 parity-window sweep stopped) clears on the first scheduled run, and PROV-8/9
receive the per-artifact series EMIT-1 added in ``observe.build_metric_data``.

The sweep touches ONLY S3 (read the v2 store) and CloudWatch (``put_metric_data``).
No Asana calls, no Redis, no secrets.

Deploy as AWS Lambda with handler:
    autom8_asana.lambda_handlers.prov_sweep.handler

Environment Variables:
    SUBSTRATE_V2_S3_BUCKET: bucket holding the ``dataframes-v2/`` store
        (default: "autom8-s3" — the live store, s3://autom8-s3/dataframes-v2/).
    SUBSTRATE_PROV_ENVIRONMENT: the ``environment`` dimension VALUE stamped on
        every emitted metric (default: ``observe.DEFAULT_ENVIRONMENT`` ==
        "production"). MUST match the terraform alarms' ``var.environment`` or
        every PROV-* alarm binds to a series that never receives a datapoint.

Expected-set semantics (mirrors the S8-2 window runbook's
"registry targets union dataframes-v2 enumeration"):
    * registry_targets — the PINNED registered set: today exactly the offer
      artifact (``live.OFFER_PROJECT_GID``, entity_type=offer). A registered
      artifact the store lacks fires PROV-4 (registry-only) + PROV-9.
    * store_enumeration — live S3 listing of ``dataframes-v2/`` pointer keys
      (``dataframes-v2/{project_gid}/{entity_type}/current.json``). A stored
      artifact the registry lacks fires PROV-4 (store-only, the "rots green"
      C7 class). Keys that do not parse as a valid ``ArtifactId`` are logged
      and skipped (non-numeric gid / non-servable entity — key debris, not
      artifacts).
    * A fetch failure raises INTO ``evaluate_all``, which emits the loud F-2
      failed-run shape (heartbeat + ExpectedCount=0 + Completeness=0 +
      EvaluationFailed=1) — never a silent no-run.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from autom8y_telemetry.aws import instrument_lambda

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.live import OFFER_PROJECT_GID
from autom8_asana.substrate.observe import (
    DEFAULT_ENVIRONMENT,
    SUBSTRATE_PROVABILITY_NAMESPACE,
)
from autom8_asana.substrate.prov_sweep import build_prov_sweep_evaluator, run_prov_sweep
from autom8_asana.substrate.store import S3ArtifactStore

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.substrate.observe import ExpectedSetSource
    from autom8_asana.substrate.store import ArtifactStore

logger = get_logger(__name__)

__all__ = [
    "REGISTRY_TARGETS",
    "S3PointerExpectedSetSource",
    "handler",
    "handler_async",
]

_DEFAULT_BUCKET = "autom8-s3"
_STORE_PREFIX = "dataframes-v2/"
# A pointer key names an artifact: dataframes-v2/{project_gid}/{entity_type}/current.json
# (identity.artifact_key + store.S3ArtifactStore._pointer_key). Anything else under
# the prefix (version blobs, historical key debris at the wrong depth) is not an
# artifact pointer and is not enumerated.
_POINTER_KEY_PATTERN = re.compile(rf"^{_STORE_PREFIX}([0-9]+)/([a-z_]+)/current\.json$")

# The PINNED registered set (the window runbook's "registry targets" leg).
# Substrate-v2 publishes exactly ONE artifact today; registering a second
# entity here is a deliberate seam change, reviewed like one.
REGISTRY_TARGETS: frozenset[ArtifactId] = frozenset(
    {ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)}
)


class S3PointerExpectedSetSource:
    """``ExpectedSetSource`` over the LIVE store: pinned registry + pointer enumeration.

    Injectable ``client`` (moto/tests); a real boto3 S3 client is built lazily.
    Blocking boto3 calls route ``asyncio.to_thread`` (the house async-over-sync
    pattern, same as ``S3ArtifactStore``). Enumeration errors are NOT swallowed —
    they propagate so ``evaluate_all`` records the loud F-2 failed run.
    """

    def __init__(
        self,
        bucket: str,
        *,
        client: Any = None,
        region: str = "us-east-1",
        registry: frozenset[ArtifactId] = REGISTRY_TARGETS,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._client = client
        self._registry = registry

    def _s3(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("s3", region_name=self._region)
        return self._client

    async def registry_targets(self) -> set[ArtifactId]:
        return set(self._registry)

    def _list_keys(self) -> list[str]:
        paginator = self._s3().get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=_STORE_PREFIX):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys

    async def store_enumeration(self) -> set[ArtifactId]:
        keys = await asyncio.to_thread(self._list_keys)
        found: set[ArtifactId] = set()
        for key in keys:
            match = _POINTER_KEY_PATTERN.fullmatch(key)
            if match is None:
                continue
            project_gid, entity_raw = match.group(1), match.group(2)
            try:
                aid = ArtifactId(project_gid=project_gid, entity_type=EntityType(entity_raw))
            except ValueError:
                # Pointer-shaped key that is not a servable artifact identity —
                # disclosed, then skipped (it cannot be evaluated OR alarmed on).
                logger.warning(
                    "prov_sweep_unenumerable_store_key",
                    extra={"bucket": self._bucket, "key": key},
                )
                continue
            found.add(aid)
        return found


async def handler_async(
    event: dict[str, Any] | None,
    context: Any,
    *,
    store: ArtifactStore | None = None,
    expected_set: ExpectedSetSource | None = None,
    cw_client: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run ONE provability sweep + emit; return the one-screen run summary.

    All seams injectable for tests (fakes/recording stubs — never a live call);
    production passes nothing and the real S3 store, live enumeration and lazy
    boto3 CloudWatch client are constructed here.
    """
    bucket = os.environ.get("SUBSTRATE_V2_S3_BUCKET", _DEFAULT_BUCKET)
    environment = os.environ.get("SUBSTRATE_PROV_ENVIRONMENT", DEFAULT_ENVIRONMENT)

    evaluator = build_prov_sweep_evaluator(
        store=store if store is not None else S3ArtifactStore(bucket),
        expected_set=(
            expected_set if expected_set is not None else S3PointerExpectedSetSource(bucket)
        ),
        environment=environment,
        cw_client=cw_client,
    )
    run = await run_prov_sweep(evaluator, now=now)

    summary = {
        "run_id": run.run_id,
        "namespace": SUBSTRATE_PROVABILITY_NAMESPACE,
        "environment": environment,
        "bucket": bucket,
        "heartbeat_emitted": True,
        "expected_count": run.expected_count,
        "evaluated_count": run.evaluated_count,
        "provable_count": run.provable_count,
        "unprovable_count": run.unprovable_count,
        "completeness": run.completeness,
        "expected_set_mismatch_count": run.expected_set_mismatch_count,
        "max_staleness_age_seconds": run.max_staleness_age_seconds,
        "evaluation_failed": run.evaluation_failed,
    }
    logger.info("prov_sweep_lambda_complete", extra=summary)
    return summary


@instrument_lambda
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point (EventBridge scheduled; event payload unused)."""
    return asyncio.run(handler_async(event, context))
