"""Substrate-v2 Seam 5 — OBSERVABILITY (infra). RC-F.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 5. SEAM-0 landed the
``ProvabilityEvaluator`` Protocol signature + the ``EvaluationRun`` name; S6
(this build) FILLS ``EvaluationRun``'s field surface (sole-consumer authority)
and ADDS the concrete scheduled evaluator + emission plumbing. The frozen
Protocol and the two frozen names are preserved verbatim — S6 never restructures
the SEAM-0 root (the package ``__all__`` is unchanged; S6 symbols import from
this module, not the package root).

RC-F — "observability that cannot read green while broken":

* **[H19] shared-predicate invariant** — the evaluator consumes the SAME
  ``is_provable`` (Seam 1) that Seam-4 serving consumes, INJECTED as a callable.
  The DARK build tests it with injected fixtures; production wiring passes
  ``substrate.freshness.is_provable`` + ``lambda raw: canonical_digest(parse(raw))``
  once S2/S4 land. Re-deriving the served digest from the stored bytes is what
  lets the evaluator catch CORRUPT identically to serving — a bare
  ``proof.content_digest`` echo would make CORRUPT undetectable.
* **[H20] completeness ≠ heartbeat** — the heartbeat proves the evaluator RAN;
  completeness proves it COVERED every expected artifact. A partial run that
  heartbeats but SKIPS a broken artifact reads INCOMPLETE, never green.
* **C7 two-sided expected-set** — expected = registry-warm-targets ∪
  store-enumeration(``dataframes-v2/``). An artifact present in exactly one set
  FIRES ``ExpectedSetMismatchCount`` (closes AV-6: an unregistered-but-served
  frame can no longer rot green; a registered-but-absent one is loud too).
* **[H21] absence = alarm** — ``ArtifactMissing`` → ``provable=0``, never silence.
* **[H22] query-independence** — driven by a schedule (EventBridge→Lambda /
  warmer post-step), NEVER by ``read``.
* **[H23] emission** — reuses the house ``put_metric_data`` EMF shape (ADR-006 /
  ``metrics.cloudwatch_emit``): a Pascal namespace, frozen metric-name constants,
  a single best-effort batched call. Emission is DARK this sprint (no deploy);
  the terraform alarm-provisioning limb is Door #4 (``DP-4a``), out of this
  seam's CODE scope.

The self-heartbeat carries the run-id + schedule stamp so the evaluator's own
absence is detectable on a metric that EXISTS every run (the dead-man done right
— contrast the orphaned ``…-DMS-24h`` watching a now-empty namespace).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from autom8y_log import get_logger

from autom8_asana.substrate.freshness import Provability
from autom8_asana.substrate.store import ArtifactMissing

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.store import ArtifactStore

logger = get_logger(__name__)

# The injected shared predicate ([H19]) and served-digest derivation. PEP 695
# lazy aliases, so the annotation-only names above resolve without a runtime
# import edge (Dependency Rule: infra imports core, never the reverse).
type IsProvable = Callable[[FreshnessProof, str, datetime], Provability]
type DigestOfFrame = Callable[[bytes], str]


# ---------------------------------------------------------------------------
# Per-run record — EvaluationRun field surface (S6 sole-consumer fill authority)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactVerdict:
    """One artifact's provability verdict within a sweep. Seam 5, S6-filled.

    ``provability`` is ``None`` iff the artifact was MISSING ([H21] — absence is a
    determinate ``provable=0`` verdict, not a silence and not a skip). ``in_registry``
    / ``in_store`` carry the C7 two-sided set membership so a one-sided member is
    attributable at triage time.
    """

    aid: ArtifactId
    provability: Provability | None
    provable: bool
    age_seconds: float | None  # (now - built_from_live_at); None iff missing
    missing: bool
    in_registry: bool
    in_store: bool


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """Result of one scheduled provability sweep. Seam 5, FROZEN name / S6 fields.

    Green requires THREE independent gates to hold simultaneously — no two of them
    collapse into one, so ``evaluated_count == expected_count`` alone can never be
    satisfiable while a served artifact rots:

    * ``completeness == 100`` — every expected artifact got a verdict ([H20]).
    * ``unprovable_count == 0`` — every verdict is PROVABLE ([H19]/[H21]).
    * ``expected_set_mismatch_count == 0`` — registry and store agree (C7).

    ``run_id`` + ``scheduled_at`` are the self-heartbeat identity — the emission
    carries them so the evaluator's own absence is detectable.
    """

    run_id: str
    scheduled_at: datetime
    registry_targets: frozenset[ArtifactId]
    store_targets: frozenset[ArtifactId]
    verdicts: tuple[ArtifactVerdict, ...]
    # Expected members that produced NO verdict — an indeterminate read/check was
    # SKIPPED ([H20]); recorded loudly (never dropped) so the run reads INCOMPLETE.
    unevaluated: frozenset[ArtifactId]
    # True iff the expected-set FETCH itself failed (registry/store enumeration
    # raised). A failed run still emits (heartbeat + loud failure signal), never a
    # silent no-run — so an intermittent fetch failure fires PROV-3/PROV-5 at
    # schedule granularity rather than hiding until the PROV-2 dead-man window.
    evaluation_failed: bool = False

    @property
    def expected(self) -> frozenset[ArtifactId]:
        """C7 two-sided expected-set: registry-warm-targets ∪ store-enumeration."""
        return self.registry_targets | self.store_targets

    @property
    def expected_count(self) -> int:
        return len(self.expected)

    @property
    def evaluated_count(self) -> int:
        return len(self.verdicts)

    @property
    def is_complete(self) -> bool:
        """True iff every expected artifact produced a verdict ([H20]); False on fetch failure."""
        return (
            not self.evaluation_failed
            and not self.unevaluated
            and self.evaluated_count == self.expected_count
        )

    @property
    def completeness(self) -> float:
        """Percent [0, 100]: evaluated / expected. 100 only when nothing was skipped.

        A fetch failure reads 0.0 (coverage is UNKNOWN, not vacuously complete) so
        PROV-3 (Completeness < 100) fires. A legitimately-empty expected-set reads
        100.0 (0/0 covered) — the PROV-5 ExpectedCount floor catches that misconfig.
        """
        if self.evaluation_failed:
            return 0.0
        if self.expected_count == 0:
            return 100.0
        return 100.0 * self.evaluated_count / self.expected_count

    @property
    def provable_count(self) -> int:
        return sum(1 for v in self.verdicts if v.provable)

    @property
    def unprovable_count(self) -> int:
        """Verdicts that are NOT provable — STALE, CORRUPT, or MISSING ([H21])."""
        return sum(1 for v in self.verdicts if not v.provable)

    @property
    def registry_only(self) -> frozenset[ArtifactId]:
        """Registered but absent from the store (fires; also → ArtifactMissing → provable=0)."""
        return self.registry_targets - self.store_targets

    @property
    def store_only(self) -> frozenset[ArtifactId]:
        """Stored but unregistered — the AV-6 "rots green" class C7 closes."""
        return self.store_targets - self.registry_targets

    @property
    def expected_set_mismatch_count(self) -> int:
        """C7: count of one-sided members (registry △ store). >0 FIRES."""
        return len(self.registry_only) + len(self.store_only)

    @property
    def max_staleness_age_seconds(self) -> float:
        """Refusal-relevant staleness: max artifact age, CLAMPED to >= 0.

        A future-dated proof (clock skew / bad writer stamp) yields NEGATIVE age —
        the exact "reads super-fresh while broken" shape RC-F kills. The raw
        negative is NEVER emitted on this gauge (it would corrupt Max/percentile
        math and read artificially fresh); the anomaly is disclosed LOUDLY and
        separately by ``future_dated_count`` → the FutureDatedProofCount metric.
        """
        ages = [v.age_seconds for v in self.verdicts if v.age_seconds is not None]
        return max(0.0, max(ages)) if ages else 0.0

    @property
    def future_dated_count(self) -> int:
        """Verdicts whose proof is stamped in the FUTURE (negative age). >0 FIRES.

        Discloses the S2 future-stamp gap (`is_provable` returns PROVABLE for a
        negative age since it is <= sla) at the observability layer: even when the
        predicate is fooled, the evaluator cannot read green while a proof is
        future-dated — the anomaly is a distinct, alarm-bound signal (PROV-6).
        """
        return sum(1 for v in self.verdicts if v.age_seconds is not None and v.age_seconds < 0)


# ---------------------------------------------------------------------------
# Ports — the evaluator's injected collaborators
# ---------------------------------------------------------------------------


class ExpectedSetSource(Protocol):
    """The C7 two-sided expected-set source.

    ``registry_targets`` catches should-exist-but-missing; ``store_enumeration``
    (over ``dataframes-v2/``) catches exists-but-unregistered. Their UNION is the
    expected-set; their symmetric difference is the C7 drift signal.
    """

    async def registry_targets(self) -> set[ArtifactId]:
        """Artifacts the entity registry declares as warm-targets (should-exist)."""
        ...

    async def store_enumeration(self) -> set[ArtifactId]:
        """Artifacts actually present under ``dataframes-v2/`` (exists-in-store)."""
        ...


class ProvabilityEmitter(Protocol):
    """Emission port ([H23]). DARK this sprint — no implementation touches AWS in tests."""

    def emit_run(self, run: EvaluationRun) -> None:
        """Emit the run's provability metrics + per-artifact gauges + heartbeat."""
        ...


# ---------------------------------------------------------------------------
# The scheduled evaluator (RC-F)
# ---------------------------------------------------------------------------


def _stable_order(aids: Iterable[ArtifactId]) -> list[ArtifactId]:
    """Deterministic iteration order (frozenset is unordered) for stable runs/emission."""
    return sorted(aids, key=lambda a: (a.project_gid, a.entity_type.value))


class ScheduledProvabilityEvaluator:
    """Query-independent scheduled provability evaluator — the concrete RC-F seam.

    Structurally satisfies the frozen ``ProvabilityEvaluator`` Protocol. Driven by
    a schedule ([H22]); consumes the injected SAME ``is_provable`` ([H19]) and a
    ``digest_of_frame`` that RE-DERIVES the served digest from the stored bytes
    (so CORRUPT is caught exactly as serving catches it). All collaborators are
    injected — the logic is provable with fixtures, no S2/S4 body required.
    """

    def __init__(
        self,
        *,
        store: ArtifactStore,
        expected_set: ExpectedSetSource,
        is_provable: IsProvable,
        digest_of_frame: DigestOfFrame,
        emitter: ProvabilityEmitter,
    ) -> None:
        self._store = store
        self._expected_set = expected_set
        self._is_provable = is_provable
        self._digest_of_frame = digest_of_frame
        self._emitter = emitter

    async def evaluate_all(self, now: datetime) -> EvaluationRun:
        """Sweep the C7 two-sided expected-set; emit; return the per-run record.

        Per artifact: ``read_current`` → derive served digest → ``is_provable``.
        ``ArtifactMissing`` is a determinate ``provable=0`` verdict ([H21]); any
        OTHER per-artifact read/check failure is an indeterminate SKIP recorded in
        ``unevaluated`` ([H20]) — never silently green.

        The sweep NEVER produces a silent no-run: an expected-set FETCH failure
        (registry/store enumeration raised) still emits — a LOUD failed run
        (heartbeat + ExpectedCount=0 + Completeness=0 + EvaluationFailed=1) — so an
        intermittent enumeration failure fires PROV-3/PROV-5 at schedule
        granularity instead of hiding until the PROV-2 dead-man window.
        """
        try:
            registry = frozenset(await self._expected_set.registry_targets())
            store = frozenset(await self._expected_set.store_enumeration())
        except Exception:  # noqa: BLE001 — fetch failure → LOUD failed run, never a silent crash
            logger.warning("substrate_provability_expected_set_failed", exc_info=True)
            failed_run = EvaluationRun(
                run_id=uuid.uuid4().hex,
                scheduled_at=now,
                registry_targets=frozenset(),
                store_targets=frozenset(),
                verdicts=(),
                unevaluated=frozenset(),
                evaluation_failed=True,
            )
            self._emitter.emit_run(failed_run)
            return failed_run
        expected = registry | store

        verdicts: list[ArtifactVerdict] = []
        unevaluated: list[ArtifactId] = []

        for aid in _stable_order(expected):
            in_registry = aid in registry
            in_store = aid in store

            try:
                raw, proof = await self._store.read_current(aid)
            except ArtifactMissing:
                # [H21] absence is loud: a determinate provable=0 verdict, never silence.
                verdicts.append(
                    ArtifactVerdict(
                        aid=aid,
                        provability=None,
                        provable=False,
                        age_seconds=None,
                        missing=True,
                        in_registry=in_registry,
                        in_store=in_store,
                    )
                )
                continue
            except Exception:  # noqa: BLE001 — indeterminate read → [H20] skip, not silence/crash
                logger.warning(
                    "substrate_provability_indeterminate_read",
                    extra={
                        "project_gid": aid.project_gid,
                        "entity_type": aid.entity_type.value,
                    },
                    exc_info=True,
                )
                unevaluated.append(aid)
                continue

            try:
                served_digest = self._digest_of_frame(raw)
                provability = self._is_provable(proof, served_digest, now)
                age_seconds = (now - proof.built_from_live_at).total_seconds()
            except Exception:  # noqa: BLE001 — indeterminate check → [H20] skip, not false-green
                logger.warning(
                    "substrate_provability_indeterminate_check",
                    extra={
                        "project_gid": aid.project_gid,
                        "entity_type": aid.entity_type.value,
                    },
                    exc_info=True,
                )
                unevaluated.append(aid)
                continue

            verdicts.append(
                ArtifactVerdict(
                    aid=aid,
                    provability=provability,
                    provable=provability is Provability.PROVABLE,
                    age_seconds=age_seconds,
                    missing=False,
                    in_registry=in_registry,
                    in_store=in_store,
                )
            )

        run = EvaluationRun(
            run_id=uuid.uuid4().hex,
            scheduled_at=now,
            registry_targets=registry,
            store_targets=store,
            verdicts=tuple(verdicts),
            unevaluated=frozenset(unevaluated),
        )
        self._emitter.emit_run(run)
        return run


class ProvabilityEvaluator(Protocol):
    """Query-independent scheduled provability evaluator (RC-F). Seam 5, FROZEN v1.0.

    Consumes the SAME ``is_provable`` + ``Provability`` (Seam 1) that Seam 4
    serving calls ([H19]) — the mechanical basis of "cannot read green while
    serving refuses." ``ScheduledProvabilityEvaluator`` is the S6 realization.
    """

    async def evaluate_all(self, now: datetime) -> EvaluationRun:
        """expected-set = registry-warm-targets ∪ store-enumeration(dataframes-v2/) (C7 two-sided).

        per-aid: read_current + is_provable → emit provable=1/0; ArtifactMissing → provable=0 (never silence).
        run-level: emit heartbeat(run_count) AND evaluated_count; evaluated_count < len(expected) FIRES; either-set-only member FIRES.
        """
        ...


# ---------------------------------------------------------------------------
# Emission plumbing ([H23]) — DARK this sprint (no deploy)
# ---------------------------------------------------------------------------

# Pascal namespace per the ADR-006 assignment convention (cf. the live
# ``Autom8y/AsanaSubstrateFreshness`` AL-5 series). The terraform alarms bind to
# these verbatim names — a rename here is a seam change, not a silent edit.
SUBSTRATE_PROVABILITY_NAMESPACE: str = "Autom8y/SubstrateProvability"

# The deployment-scope dimension EVERY metric carries. This is the load-bearing
# identity contract with the terraform alarms: CloudWatch identity =
# (namespace, name, EXACT dimension set), and every PROV-* alarm queries
# ``dimensions = { environment = var.environment }``. Emitting run-level metrics
# WITHOUT this key would bind the alarms to series that never receive a datapoint
# (the DMS-24h dead-metric class). ``tests/unit/substrate/test_observe.py`` string-
# diffs the .tf against this emitter so the identity cannot drift silently.
DIMENSION_ENVIRONMENT: str = "environment"
# Matches the terraform ``variable "environment"`` default in observability_alarms.tf.
DEFAULT_ENVIRONMENT: str = "production"

# Run-level metrics — bounded cardinality (dimensioned {environment} only, 1-2
# values); the ALARMED set.
METRIC_UNPROVABLE_COUNT: str = "UnprovableCount"
METRIC_PROVABLE_COUNT: str = "ProvableCount"
METRIC_MAX_STALENESS_AGE_SECONDS: str = "MaxStalenessAgeSeconds"
METRIC_COMPLETENESS: str = "Completeness"
METRIC_EVALUATOR_HEARTBEAT: str = "EvaluatorHeartbeat"
METRIC_EXPECTED_SET_MISMATCH_COUNT: str = "ExpectedSetMismatchCount"
METRIC_EXPECTED_COUNT: str = "ExpectedCount"
METRIC_EVALUATED_COUNT: str = "EvaluatedCount"
# 1.0 iff the expected-set fetch itself failed (PROV-5 floor + PROV-3 fire).
METRIC_EVALUATION_FAILED: str = "EvaluationFailed"
# Count of future-dated proofs (negative age) — the "super-fresh-while-broken"
# anomaly, disclosed distinctly rather than smoothed into the staleness gauge (PROV-6).
METRIC_FUTURE_DATED_PROOF_COUNT: str = "FutureDatedProofCount"
# Per-artifact gauge — dimensioned {environment, project_gid, entity_type};
# diagnostic, bounded by the registered expected-set (same discipline as AL-5).
METRIC_ARTIFACT_PROVABLE: str = "ArtifactProvable"

# Count of classifier-active rows carrying >= 1 null in a WARNING-tier (demoted) economic
# column at publish-time floor evaluation — the loud channel for the columns the tiered
# floor no longer blocks on (SPIKE-population-floor-scope-2026-08-12, digest item 2).
# ALARMED PROV-7. Emitted on EVERY floor evaluation including the clean case (value 0.0),
# so the series is DENSE and the alarm can return to OK — the same discipline the run-level
# PROV metrics follow. Dimensioned {environment} ONLY: the per-offer attribution lives in
# the parity receipt's ``data_quality_warnings``, never in metric dimensions (an offer-gid
# dimension would be unbounded cardinality).
METRIC_ACTIVE_ROW_ECONOMIC_NULL_COUNT: str = "ActiveRowEconomicNullCount"

# CloudWatch put_metric_data caps MetricData at 1000 items per call.
_PUT_METRIC_DATA_MAX_ITEMS: int = 1000


def _get_cloudwatch_client() -> Any:
    """Return a boto3 CloudWatch client (lazy import — keeps this module boto3-free).

    Mirrors ``metrics.cloudwatch_emit._get_cloudwatch_client`` (ADR-006 house pattern).
    """
    import os

    import boto3

    region = os.environ.get("AWS_REGION") or os.environ.get("ASANA_CACHE_S3_REGION", "us-east-1")
    return boto3.client("cloudwatch", region_name=region)


def _chunk(items: Sequence[dict[str, Any]], size: int) -> Iterable[Sequence[dict[str, Any]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class CloudWatchProvabilityEmitter:
    """Emits an ``EvaluationRun`` to CloudWatch via the house ``put_metric_data`` shape.

    Reuses the ADR-006 emission SHAPE ([H23]): a Pascal namespace, frozen
    metric-name constants, a single logical best-effort batch (chunked at the
    1000-item API cap). Every datum's ``Timestamp`` is the run's ``scheduled_at``
    so the emission carries the schedule stamp; ``run_id`` rides the structured
    heartbeat log line. Best-effort: a CloudWatch failure is logged, never raised
    — an observability emit must not take down the scheduled evaluator.

    DARK this sprint: no deploy, no live AWS call. ``cw_client`` is injectable so
    the shape is unit-provable with a fake; production passes ``None`` and the
    lazy boto3 client is constructed on first emit. ``environment`` is the
    deployment-scope dimension VALUE stamped on every metric — it MUST match the
    terraform ``var.environment`` (both default ``"production"``) or the alarms
    bind to a different series (identity contract, enforced by the binding test).
    ``emit_run`` returns ``None`` to satisfy the ``ProvabilityEmitter`` port;
    the wire payload is inspectable via ``build_metric_data`` (pure).
    """

    def __init__(
        self, *, environment: str = DEFAULT_ENVIRONMENT, cw_client: Any | None = None
    ) -> None:
        self._environment = environment
        self._cw_client = cw_client

    def emit_run(self, run: EvaluationRun) -> None:
        """Build + send the run's metric data (best-effort). Conforms to ProvabilityEmitter."""
        metric_data = self.build_metric_data(run, environment=self._environment)

        # The self-heartbeat identity — emitted on a metric that EXISTS every run
        # (the dead-man done right), carrying run-id + schedule stamp. Greppable as
        # the ``substrate_provability_heartbeat`` event (a metric filter can key on
        # its absence, mirroring the AL-5 serve-event pattern).
        logger.info(
            "substrate_provability_heartbeat",
            extra={
                "run_id": run.run_id,
                "scheduled_at": run.scheduled_at.isoformat(),
                "expected_count": run.expected_count,
                "evaluated_count": run.evaluated_count,
                "provable_count": run.provable_count,
                "unprovable_count": run.unprovable_count,
                "completeness": run.completeness,
                "expected_set_mismatch_count": run.expected_set_mismatch_count,
            },
        )

        client = self._cw_client if self._cw_client is not None else _get_cloudwatch_client()
        for batch in _chunk(metric_data, _PUT_METRIC_DATA_MAX_ITEMS):
            try:
                client.put_metric_data(
                    Namespace=SUBSTRATE_PROVABILITY_NAMESPACE,
                    MetricData=list(batch),
                )
            except Exception as exc:  # noqa: BLE001 — best-effort emit; never block the evaluator
                logger.warning(
                    "substrate_provability_emit_failed",
                    extra={
                        "run_id": run.run_id,
                        "namespace": SUBSTRATE_PROVABILITY_NAMESPACE,
                        "error": repr(exc),
                    },
                )

    @staticmethod
    def build_metric_data(
        run: EvaluationRun, *, environment: str = DEFAULT_ENVIRONMENT
    ) -> list[dict[str, Any]]:
        """Translate an ``EvaluationRun`` into CloudWatch ``MetricData`` (pure; no I/O).

        Every datum carries the ``{environment}`` dimension the PROV-* alarms query
        — that shared identity is the F-1 cure and is string-diffed by the binding
        test against the terraform.
        """
        stamp = run.scheduled_at

        def _run_metric(name: str, value: float, unit: str) -> dict[str, Any]:
            return {
                "MetricName": name,
                "Value": value,
                "Unit": unit,
                "Timestamp": stamp,
                "Dimensions": [{"Name": DIMENSION_ENVIRONMENT, "Value": environment}],
            }

        metric_data: list[dict[str, Any]] = [
            # ALARMED PROV-1: fires on unprovability; silent on an all-provable run.
            _run_metric(METRIC_UNPROVABLE_COUNT, float(run.unprovable_count), "Count"),
            # ALARMED PROV-2: the dead-man — a metric that EXISTS every run.
            _run_metric(METRIC_EVALUATOR_HEARTBEAT, 1.0, "Count"),
            # ALARMED PROV-3: fires when a broken artifact was skipped OR fetch failed ([H20]/F-2).
            _run_metric(METRIC_COMPLETENESS, run.completeness, "Percent"),
            # ALARMED PROV-4: C7 — fires on a one-sided (registry △ store) member.
            _run_metric(
                METRIC_EXPECTED_SET_MISMATCH_COUNT,
                float(run.expected_set_mismatch_count),
                "Count",
            ),
            # ALARMED PROV-5 floor: empty/failed expected-set (evaluator watching nothing).
            _run_metric(METRIC_EXPECTED_COUNT, float(run.expected_count), "Count"),
            # ALARMED PROV-6: future-dated proof anomaly (negative age; super-fresh-while-broken).
            _run_metric(METRIC_FUTURE_DATED_PROOF_COUNT, float(run.future_dated_count), "Count"),
            # Diagnostic: 1 iff the expected-set fetch itself failed (F-2).
            _run_metric(METRIC_EVALUATION_FAILED, 1.0 if run.evaluation_failed else 0.0, "Count"),
            # Refusal-relevant staleness age, CLAMPED >= 0 (never a raw negative gauge).
            _run_metric(METRIC_MAX_STALENESS_AGE_SECONDS, run.max_staleness_age_seconds, "Seconds"),
            _run_metric(METRIC_PROVABLE_COUNT, float(run.provable_count), "Count"),
            _run_metric(METRIC_EVALUATED_COUNT, float(run.evaluated_count), "Count"),
        ]

        # Per-artifact provable=1/0 gauge (diagnostic; bounded by the registered set).
        for verdict in run.verdicts:
            metric_data.append(
                {
                    "MetricName": METRIC_ARTIFACT_PROVABLE,
                    "Value": 1.0 if verdict.provable else 0.0,
                    "Unit": "Count",
                    "Timestamp": stamp,
                    "Dimensions": [
                        {"Name": DIMENSION_ENVIRONMENT, "Value": environment},
                        {"Name": "project_gid", "Value": verdict.aid.project_gid},
                        {"Name": "entity_type", "Value": verdict.aid.entity_type.value},
                    ],
                }
            )

        # EMIT-1 (autom8y monorepo terraform/services/asana/offer_freshness_prov_alarms.tf
        # §D): per-artifact staleness gauge on the SAME dimension trio as
        # ArtifactProvable — {environment, project_gid, entity_type}. This is the
        # series PROV-8 (asana-PROV-8-offer-content-stale) binds to; the run-level
        # {environment}-only MaxStalenessAgeSeconds above is a DISTINCT CloudWatch
        # identity and is kept for its existing consumers. Value = that verdict's
        # age CLAMPED >= 0 (a future-dated proof is disclosed by
        # FutureDatedProofCount, never smoothed into this gauge as a negative).
        # A MISSING artifact emits NO datapoint here BY DESIGN: absence is
        # PROV-9's remit (ArtifactProvable=0 above + treat_missing_data=breaching);
        # fabricating 0.0 would read PERFECTLY FRESH on PROV-8 — the exact
        # false-green §C of the alarm file exists to kill.
        for verdict in run.verdicts:
            if verdict.age_seconds is None:
                continue
            metric_data.append(
                {
                    "MetricName": METRIC_MAX_STALENESS_AGE_SECONDS,
                    "Value": max(0.0, verdict.age_seconds),
                    "Unit": "Seconds",
                    "Timestamp": stamp,
                    "Dimensions": [
                        {"Name": DIMENSION_ENVIRONMENT, "Value": environment},
                        {"Name": "project_gid", "Value": verdict.aid.project_gid},
                        {"Name": "entity_type", "Value": verdict.aid.entity_type.value},
                    ],
                }
            )

        return metric_data


# ---------------------------------------------------------------------------
# Data-quality emission (PROV-7) — the tiered population floor's LOUD channel
# ---------------------------------------------------------------------------


class DataQualityEmitter(Protocol):
    """Emission port for publish-time data-quality signals (the tiered floor's warn tier)."""

    def emit_active_row_economic_nulls(self, count: int, *, at: datetime | None = None) -> None:
        """Emit ``ActiveRowEconomicNullCount`` for ONE floor evaluation (0 is a real value)."""
        ...


class CloudWatchDataQualityEmitter:
    """Emits ``ActiveRowEconomicNullCount`` via the SAME house ``put_metric_data`` shape ([H23]).

    Deliberately a sibling of ``CloudWatchProvabilityEmitter`` rather than a method on it:
    the provability sweep is SCHEDULED and artifact-scoped ([H22]), whereas this fires at
    publish-time floor evaluation inside a rebuild. Same namespace, same ``{environment}``
    dimension, same best-effort semantics — a CloudWatch failure is logged, never raised
    (a data-quality emit must not fail a publish that the floor accepted).

    ``cw_client`` is injectable so the wire shape is unit-provable with a fake; production
    passes ``None`` and the lazy boto3 client is built on first emit. ``build_metric_data``
    is pure and is what the terraform↔emitter identity tripwire diffs against.
    """

    def __init__(
        self, *, environment: str = DEFAULT_ENVIRONMENT, cw_client: Any | None = None
    ) -> None:
        self._environment = environment
        self._cw_client = cw_client

    def emit_active_row_economic_nulls(self, count: int, *, at: datetime | None = None) -> None:
        """Build + send one ``ActiveRowEconomicNullCount`` datum (best-effort)."""
        metric_data = self.build_metric_data(count, environment=self._environment, at=at)
        logger.info(
            "substrate_active_row_economic_nulls",
            extra={
                "active_row_economic_null_count": count,
                "namespace": SUBSTRATE_PROVABILITY_NAMESPACE,
                "environment": self._environment,
            },
        )
        client = self._cw_client if self._cw_client is not None else _get_cloudwatch_client()
        try:
            client.put_metric_data(
                Namespace=SUBSTRATE_PROVABILITY_NAMESPACE, MetricData=metric_data
            )
        except Exception as exc:  # noqa: BLE001 — best-effort emit; never block the publish
            logger.warning(
                "substrate_data_quality_emit_failed",
                extra={
                    "namespace": SUBSTRATE_PROVABILITY_NAMESPACE,
                    "metric": METRIC_ACTIVE_ROW_ECONOMIC_NULL_COUNT,
                    "error": repr(exc),
                },
            )

    @staticmethod
    def build_metric_data(
        count: int, *, environment: str = DEFAULT_ENVIRONMENT, at: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Translate a floor-evaluation null count into CloudWatch ``MetricData`` (pure; no I/O).

        Carries the ``{environment}`` dimension PROV-7 queries — the same identity contract
        the PROV-1..6 alarms hold, string-diffed by the terraform binding test.
        """
        datum: dict[str, Any] = {
            "MetricName": METRIC_ACTIVE_ROW_ECONOMIC_NULL_COUNT,
            "Value": float(count),
            "Unit": "Count",
            "Dimensions": [{"Name": DIMENSION_ENVIRONMENT, "Value": environment}],
        }
        if at is not None:
            datum["Timestamp"] = at
        return [datum]
