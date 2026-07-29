"""S6 observability — two-sided RC-F teeth for the scheduled provability evaluator.

Every fixture injects a well-formed ``FreshnessProof`` and a faithful local
``is_provable`` (the frozen Seam-1 contract) — S2's body is NOT required to prove
S6's logic ([H19]). The teeth are two-sided throughout:

* the alarm-feeding evaluation FIRES on an unprovable artifact AND stays SILENT
  on a provable one;
* C7 catches an unregistered-but-stored artifact AND a registered-but-missing one;
* [H20] a partial run reads INCOMPLETE (it heartbeats but is not green);
* the heartbeat metric EXISTS on every run, so its absence is detectable.
"""

from __future__ import annotations

import hashlib
import inspect
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof, Provability
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.observe import (
    DEFAULT_ENVIRONMENT,
    DIMENSION_ENVIRONMENT,
    METRIC_ARTIFACT_PROVABLE,
    METRIC_COMPLETENESS,
    METRIC_EVALUATION_FAILED,
    METRIC_EVALUATOR_HEARTBEAT,
    METRIC_EXPECTED_COUNT,
    METRIC_EXPECTED_SET_MISMATCH_COUNT,
    METRIC_FUTURE_DATED_PROOF_COUNT,
    METRIC_MAX_STALENESS_AGE_SECONDS,
    METRIC_UNPROVABLE_COUNT,
    SUBSTRATE_PROVABILITY_NAMESPACE,
    ArtifactVerdict,
    CloudWatchProvabilityEmitter,
    EvaluationRun,
    ProvabilityEmitter,
    ProvabilityEvaluator,
    ScheduledProvabilityEvaluator,
)
from autom8_asana.substrate.store import ArtifactMissing

if TYPE_CHECKING:
    from autom8_asana.substrate.store import ETag, VersionId

# The AUTHORED-NOT-APPLIED terraform this emitter must bind to (F-1 identity seam).
_TF_ALARMS = (
    Path(__file__).resolve().parents[3]
    / "terraform/services/asana/substrate_v2_provability_alarms.tf"
)
_TF_SHARED = (
    Path(__file__).resolve().parents[3] / "terraform/services/asana/observability_alarms.tf"
)

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Injected fakes + fixture builders — no S2/S4 body, no AWS
# ---------------------------------------------------------------------------


def _digest_of(raw: bytes) -> str:
    """Re-derive the served digest from the actual bytes (the production shape)."""
    return hashlib.sha256(raw).hexdigest()


def _faithful_is_provable(
    proof: FreshnessProof, served_frame_digest: str, now: datetime
) -> Provability:
    """The frozen Seam-1 predicate, injected verbatim ([H19]) — S2 body not required."""
    if served_frame_digest != proof.content_digest:
        return Provability.CORRUPT
    if (now - proof.built_from_live_at).total_seconds() > proof.sla_seconds:
        return Provability.STALE
    return Provability.PROVABLE


def _aid(gid: str, entity: EntityType = EntityType.OFFER) -> ArtifactId:
    return ArtifactId(project_gid=gid, entity_type=entity)


def _provable_entry(raw: bytes = b"frame-provable") -> tuple[bytes, FreshnessProof]:
    """Fresh + digest-matched → PROVABLE."""
    proof = FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=60),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )
    return raw, proof


def _stale_entry(raw: bytes = b"frame-stale") -> tuple[bytes, FreshnessProof]:
    """Digest matches but age (7200s) exceeds sla (3600s) → STALE."""
    proof = FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=7200),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )
    return raw, proof


def _corrupt_entry(raw: bytes = b"frame-rotted") -> tuple[bytes, FreshnessProof]:
    """Stored bytes' fresh digest diverges from the recorded content_digest → CORRUPT.

    This ONLY surfaces if the evaluator RE-DERIVES the served digest from the
    bytes (an echo of ``proof.content_digest`` could never be corrupt).
    """
    proof = FreshnessProof(
        built_from_live_at=NOW - timedelta(seconds=60),
        content_digest=_digest_of(b"frame-original-before-rot"),
        sla_seconds=3600,
    )
    return raw, proof


class FakeStore:
    """Minimal ``ArtifactStore`` — only ``read_current`` is exercised by the evaluator."""

    def __init__(
        self,
        entries: dict[ArtifactId, tuple[bytes, FreshnessProof]] | None = None,
        errors: dict[ArtifactId, Exception] | None = None,
    ) -> None:
        self._entries = entries or {}
        self._errors = errors or {}

    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]:
        if aid in self._errors:
            raise self._errors[aid]
        if aid not in self._entries:
            raise ArtifactMissing(f"no current pointer for {aid.project_gid}")
        return self._entries[aid]

    async def stage_version(
        self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof
    ) -> VersionId:
        raise NotImplementedError

    async def swap_pointer(self, aid: ArtifactId, to: VersionId, *, if_match: ETag) -> None:
        raise NotImplementedError

    async def list_versions(self, aid: ArtifactId) -> list[VersionId]:
        raise NotImplementedError

    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int:
        raise NotImplementedError


class FakeExpectedSet:
    """Two-sided expected-set source with independently-controllable registry / store sides."""

    def __init__(self, registry: set[ArtifactId], store: set[ArtifactId]) -> None:
        self._registry = set(registry)
        self._store = set(store)

    async def registry_targets(self) -> set[ArtifactId]:
        return set(self._registry)

    async def store_enumeration(self) -> set[ArtifactId]:
        return set(self._store)


class RecordingEmitter:
    """Captures runs without emitting anything (DARK)."""

    def __init__(self) -> None:
        self.runs: list[EvaluationRun] = []

    def emit_run(self, run: EvaluationRun) -> None:
        self.runs.append(run)


class RecordingCwClient:
    """Fake boto3 CloudWatch client — records ``put_metric_data`` calls; never touches AWS."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._fail = fail

    def put_metric_data(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        if self._fail:
            raise RuntimeError("simulated CloudWatch put_metric_data failure")


def _build_evaluator(
    *,
    store: FakeStore,
    registry: set[ArtifactId],
    store_set: set[ArtifactId],
    emitter: ProvabilityEmitter | None = None,
) -> ScheduledProvabilityEvaluator:
    # No type: ignore — the fakes structurally satisfy the injected Protocols
    # (F-4: the ports are honestly typed, not dodged via Any).
    return ScheduledProvabilityEvaluator(
        store=store,
        expected_set=FakeExpectedSet(registry, store_set),
        is_provable=_faithful_is_provable,
        digest_of_frame=_digest_of,
        emitter=emitter or RecordingEmitter(),
    )


def _run_metric(metric_data: list[dict[str, Any]], name: str) -> float:
    """The run-level datum (dimensioned {environment} only — not the per-artifact gauge)."""
    for datum in metric_data:
        if datum["MetricName"] != name:
            continue
        dim_names = {d["Name"] for d in datum.get("Dimensions", [])}
        if "project_gid" not in dim_names:  # exclude the per-artifact ArtifactProvable gauge
            return float(datum["Value"])
    raise AssertionError(f"run-level metric {name!r} not emitted")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_concrete_evaluator_satisfies_frozen_protocol() -> None:
    """The S6 class structurally satisfies the FROZEN ``ProvabilityEvaluator`` Protocol.

    The frozen Protocol is intentionally NOT ``@runtime_checkable`` (that would be a
    seam edit), so conformance is asserted structurally: the sole method exists and
    is a coroutine, and the class is assignable to the Protocol type (mypy-enforced).
    """
    evaluator = _build_evaluator(store=FakeStore(), registry=set(), store_set=set())
    _typed: ProvabilityEvaluator = evaluator  # mypy-checked structural conformance
    assert inspect.iscoroutinefunction(_typed.evaluate_all)


# ---------------------------------------------------------------------------
# Two-sided teeth #1 — alarm FIRES on unprovability, SILENT on a provable number
# ---------------------------------------------------------------------------


async def test_provable_artifact_keeps_the_alarm_silent() -> None:
    """GREEN side: an all-provable run → UnprovableCount == 0 → alarm SILENT."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})
    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)

    assert run.unprovable_count == 0
    assert run.provable_count == 1
    assert run.is_complete
    assert run.expected_set_mismatch_count == 0

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_UNPROVABLE_COUNT) == 0.0  # alarm (a) SILENT
    assert _run_metric(metric_data, METRIC_COMPLETENESS) == 100.0
    assert _run_metric(metric_data, METRIC_EXPECTED_SET_MISMATCH_COUNT) == 0.0


@pytest.mark.parametrize(
    ("entry_builder", "expected_verdict"),
    [
        (_stale_entry, Provability.STALE),
        (_corrupt_entry, Provability.CORRUPT),
    ],
)
async def test_unprovable_artifact_fires_the_alarm(
    entry_builder: Any, expected_verdict: Provability
) -> None:
    """RED side: a STALE or CORRUPT artifact → UnprovableCount == 1 → alarm FIRES."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: entry_builder()})
    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)

    (verdict,) = run.verdicts
    assert verdict.provability is expected_verdict
    assert verdict.provable is False
    assert run.unprovable_count == 1

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_UNPROVABLE_COUNT) == 1.0  # alarm (a) FIRES


async def test_corrupt_requires_digest_rederivation_from_bytes() -> None:
    """The CORRUPT verdict proves the evaluator re-derives the served digest (not an echo)."""
    aid = _aid("1143843662099250")
    raw, proof = _corrupt_entry()
    # Sanity: the recorded content_digest deliberately does NOT match the bytes.
    assert _digest_of(raw) != proof.content_digest
    store = FakeStore(entries={aid: (raw, proof)})

    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)
    (verdict,) = run.verdicts
    assert verdict.provability is Provability.CORRUPT


async def test_evaluator_delegates_to_the_injected_predicate() -> None:
    """[H19]: verdicts come from the injected ``is_provable``, not a private reimplementation."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})  # fixture is genuinely provable

    def always_corrupt(proof: FreshnessProof, digest: str, now: datetime) -> Provability:
        return Provability.CORRUPT

    evaluator = ScheduledProvabilityEvaluator(
        store=store,
        expected_set=FakeExpectedSet({aid}, {aid}),
        is_provable=always_corrupt,
        digest_of_frame=_digest_of,
        emitter=RecordingEmitter(),
    )
    run = await evaluator.evaluate_all(NOW)
    # A genuinely-fresh fixture reads CORRUPT ONLY because the injected predicate said so.
    assert run.unprovable_count == 1
    assert run.verdicts[0].provability is Provability.CORRUPT


# ---------------------------------------------------------------------------
# [H21] absence = alarm — ArtifactMissing → provable=0, never silence
# ---------------------------------------------------------------------------


async def test_missing_artifact_is_a_loud_provable_zero_verdict() -> None:
    """[H21]: ArtifactMissing is a determinate provable=0 verdict — counted, never dropped."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={})  # read_current raises ArtifactMissing
    run = await _build_evaluator(store=store, registry={aid}, store_set=set()).evaluate_all(NOW)

    (verdict,) = run.verdicts
    assert verdict.missing is True
    assert verdict.provable is False
    assert verdict.provability is None
    assert run.unprovable_count == 1  # counted as evaluated, not a silent skip
    assert run.is_complete  # a determinate verdict — the run still COVERED the artifact
    assert aid not in run.unevaluated


# ---------------------------------------------------------------------------
# Two-sided teeth #2 — C7 two-sided expected-set (registry ∪ store)
# ---------------------------------------------------------------------------


async def test_c7_registered_but_missing_fires_both_signals() -> None:
    """Registered-but-absent → ExpectedSetMismatchCount FIRES AND UnprovableCount FIRES."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={})  # registered, but nothing in the store
    run = await _build_evaluator(store=store, registry={aid}, store_set=set()).evaluate_all(NOW)

    assert aid in run.registry_only
    assert run.expected_set_mismatch_count == 1
    assert run.unprovable_count == 1  # absence also fires the provability alarm

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EXPECTED_SET_MISMATCH_COUNT) == 1.0  # alarm (d) FIRES
    assert _run_metric(metric_data, METRIC_UNPROVABLE_COUNT) == 1.0  # alarm (a) FIRES


async def test_c7_stored_but_unregistered_fires_even_while_fresh() -> None:
    """The AV-6 cure: a FRESH but unregistered artifact still FIRES the mismatch alarm.

    This is the "rots green" class — counts alone (evaluated == expected, all
    provable) MUST NOT read clean while a served artifact is unregistered.
    """
    aid = _aid("9999999999999999")
    store = FakeStore(entries={aid: _provable_entry()})  # present + provable, but unregistered
    run = await _build_evaluator(store=store, registry=set(), store_set={aid}).evaluate_all(NOW)

    assert aid in run.store_only
    assert run.expected_set_mismatch_count == 1
    assert run.unprovable_count == 0  # it IS fresh — provability alone would read green
    assert run.is_complete  # it IS evaluated — completeness alone would read green

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    # Neither (a) nor (c) fires — ONLY the C7 mismatch alarm catches this drift.
    assert _run_metric(metric_data, METRIC_UNPROVABLE_COUNT) == 0.0
    assert _run_metric(metric_data, METRIC_COMPLETENESS) == 100.0
    assert _run_metric(metric_data, METRIC_EXPECTED_SET_MISMATCH_COUNT) == 1.0  # alarm (d) FIRES


async def test_c7_aligned_sets_stay_silent() -> None:
    """SILENT side of C7: registry == store and provable → mismatch 0, everything quiet."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})
    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)

    assert run.registry_only == frozenset()
    assert run.store_only == frozenset()
    assert run.expected_set_mismatch_count == 0

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EXPECTED_SET_MISMATCH_COUNT) == 0.0


# ---------------------------------------------------------------------------
# [H20] completeness ≠ heartbeat — a partial run reads INCOMPLETE, not green
# ---------------------------------------------------------------------------


async def test_partial_run_reads_incomplete_but_still_heartbeats() -> None:
    """[H20]: an indeterminate read is SKIPPED → completeness < 100, yet the run heartbeats."""
    healthy = _aid("1143843662099250")
    broken = _aid("2222222222222222")
    store = FakeStore(
        entries={healthy: _provable_entry()},
        errors={broken: RuntimeError("transient S3 read failure")},  # NOT ArtifactMissing
    )
    emitter = RecordingEmitter()
    run = await _build_evaluator(
        store=store, registry={healthy, broken}, store_set={healthy, broken}, emitter=emitter
    ).evaluate_all(NOW)

    assert run.expected_count == 2
    assert run.evaluated_count == 1  # the broken artifact produced NO verdict
    assert broken in run.unevaluated
    assert run.is_complete is False
    assert run.completeness == 50.0
    # The skip is NEITHER silently green NOR counted as unprovable — it is INCOMPLETE.
    assert run.provable_count == 1
    assert run.unprovable_count == 0

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_COMPLETENESS) == 50.0  # alarm (c) FIRES
    # Yet the evaluator RAN — the heartbeat still lands (completeness ≠ heartbeat).
    assert _run_metric(metric_data, METRIC_EVALUATOR_HEARTBEAT) == 1.0
    assert emitter.runs == [run]  # emission happened despite the partial sweep


async def test_indeterminate_check_also_reads_incomplete() -> None:
    """A digest/predicate blow-up (not a read failure) is ALSO an [H20] skip, not a false-green."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})

    def exploding_digest(_raw: bytes) -> str:
        raise ValueError("frame parse exploded")

    evaluator = ScheduledProvabilityEvaluator(
        store=store,
        expected_set=FakeExpectedSet({aid}, {aid}),
        is_provable=_faithful_is_provable,
        digest_of_frame=exploding_digest,
        emitter=RecordingEmitter(),
    )
    run = await evaluator.evaluate_all(NOW)
    assert aid in run.unevaluated
    assert run.evaluated_count == 0
    assert run.completeness == 0.0
    assert run.unprovable_count == 0  # NOT counted as unprovable — it is INDETERMINATE


# ---------------------------------------------------------------------------
# Self-heartbeat — the metric EXISTS every run, so its absence is detectable
# ---------------------------------------------------------------------------


async def test_heartbeat_and_identity_emitted_on_every_run() -> None:
    """The dead-man done right: heartbeat=1 lands even on an EMPTY sweep, with run-id + stamp."""
    run = await _build_evaluator(store=FakeStore(), registry=set(), store_set=set()).evaluate_all(
        NOW
    )
    assert run.run_id  # non-empty self-heartbeat identity
    assert run.scheduled_at == NOW  # the schedule stamp

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EVALUATOR_HEARTBEAT) == 1.0
    # Every datum carries the schedule stamp as its Timestamp.
    assert all(datum["Timestamp"] == NOW for datum in metric_data)


@pytest.mark.parametrize(
    "scenario",
    ["empty", "provable", "unprovable", "incomplete"],
)
async def test_heartbeat_present_regardless_of_run_content(scenario: str) -> None:
    """Absence-detectability: the heartbeat metric is emitted on EVERY run shape."""
    aid = _aid("1143843662099250")
    if scenario == "empty":
        store, registry, store_set = FakeStore(), set(), set()
    elif scenario == "provable":
        store, registry, store_set = FakeStore(entries={aid: _provable_entry()}), {aid}, {aid}
    elif scenario == "unprovable":
        store, registry, store_set = FakeStore(entries={aid: _stale_entry()}), {aid}, {aid}
    else:  # incomplete
        store = FakeStore(errors={aid: RuntimeError("boom")})
        registry, store_set = {aid}, {aid}

    run = await _build_evaluator(store=store, registry=registry, store_set=store_set).evaluate_all(
        NOW
    )
    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EVALUATOR_HEARTBEAT) == 1.0


async def test_each_run_has_a_distinct_run_id() -> None:
    """Heartbeat datapoints are correlatable — each sweep mints a fresh run-id."""
    evaluator = _build_evaluator(store=FakeStore(), registry=set(), store_set=set())
    first = await evaluator.evaluate_all(NOW)
    second = await evaluator.evaluate_all(NOW + timedelta(minutes=5))
    assert first.run_id != second.run_id


# ---------------------------------------------------------------------------
# Emission plumbing — DARK, best-effort, per-artifact gauges
# ---------------------------------------------------------------------------


async def test_per_artifact_gauge_carries_env_gid_and_entity_dimensions() -> None:
    """Per-aid provable=1/0 gauge is emitted with {environment, project_gid, entity_type}."""
    provable = _aid("1143843662099250", EntityType.OFFER)
    stale = _aid("2222222222222222", EntityType.UNIT)
    store = FakeStore(entries={provable: _provable_entry(), stale: _stale_entry()})
    run = await _build_evaluator(
        store=store, registry={provable, stale}, store_set={provable, stale}
    ).evaluate_all(NOW)

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    gauges: dict[str, tuple[float, dict[str, str]]] = {}
    for datum in metric_data:
        if datum["MetricName"] != METRIC_ARTIFACT_PROVABLE:
            continue
        dims = {d["Name"]: d["Value"] for d in datum["Dimensions"]}
        gauges[dims["project_gid"]] = (float(datum["Value"]), dims)

    assert gauges["1143843662099250"][0] == 1.0
    assert gauges["2222222222222222"][0] == 0.0
    assert gauges["2222222222222222"][1]["entity_type"] == "unit"
    # The deployment-scope dimension rides the per-artifact gauge too (F-1 identity key).
    assert gauges["2222222222222222"][1]["environment"] == "production"


async def test_cloudwatch_emitter_sends_via_injected_client() -> None:
    """DARK: the CloudWatch emitter batches through an INJECTED fake client — no AWS."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})
    cw = RecordingCwClient()
    emitter = CloudWatchProvabilityEmitter(cw_client=cw)
    run = await _build_evaluator(
        store=store, registry={aid}, store_set={aid}, emitter=emitter
    ).evaluate_all(NOW)

    assert len(cw.calls) == 1
    call = cw.calls[0]
    assert call["Namespace"] == "Autom8y/SubstrateProvability"
    names = {datum["MetricName"] for datum in call["MetricData"]}
    assert METRIC_EVALUATOR_HEARTBEAT in names
    assert METRIC_UNPROVABLE_COUNT in names
    assert run.run_id


def test_cloudwatch_emitter_is_best_effort_on_failure() -> None:
    """A CloudWatch failure is swallowed — an observability emit never blocks the evaluator."""
    run = EvaluationRun(
        run_id="abc123",
        scheduled_at=NOW,
        registry_targets=frozenset(),
        store_targets=frozenset(),
        verdicts=(),
        unevaluated=frozenset(),
    )
    cw = RecordingCwClient(fail=True)
    emitter = CloudWatchProvabilityEmitter(cw_client=cw)

    # emit_run returns None (ProvabilityEmitter port, mypy-checked) and must NOT raise
    # despite put_metric_data blowing up.
    emitter.emit_run(run)
    assert len(cw.calls) == 1  # the call was attempted
    assert cw.calls[0]["Namespace"] == "Autom8y/SubstrateProvability"


def test_evaluation_run_derived_properties_are_consistent() -> None:
    """The EvaluationRun field surface (S6 fill) computes the three green-gates coherently."""
    a = _aid("1")
    b = _aid("2")
    run = EvaluationRun(
        run_id="r1",
        scheduled_at=NOW,
        registry_targets=frozenset({a, b}),
        store_targets=frozenset({a}),
        verdicts=(
            ArtifactVerdict(
                aid=a,
                provability=Provability.PROVABLE,
                provable=True,
                age_seconds=120.0,
                missing=False,
                in_registry=True,
                in_store=True,
            ),
            ArtifactVerdict(
                aid=b,
                provability=None,
                provable=False,
                age_seconds=None,
                missing=True,
                in_registry=True,
                in_store=False,
            ),
        ),
        unevaluated=frozenset(),
    )
    assert run.expected == frozenset({a, b})
    assert run.expected_count == 2
    assert run.evaluated_count == 2
    assert run.provable_count == 1
    assert run.unprovable_count == 1
    assert run.registry_only == frozenset({b})
    assert run.store_only == frozenset()
    assert run.expected_set_mismatch_count == 1
    assert run.max_staleness_age_seconds == 120.0
    assert run.is_complete


# ---------------------------------------------------------------------------
# F-1 CURE — the tf ↔ emitter metric-identity binding tripwire
# ---------------------------------------------------------------------------


def _parse_tf_variable_default(tf_text: str, name: str) -> str:
    """Extract a `variable "name" { … default = "VALUE" }` default from HCL text."""
    block = re.search(rf'variable\s+"{re.escape(name)}"\s*\{{(.*?)\n\}}', tf_text, re.DOTALL)
    assert block, f"variable {name!r} not found"
    default = re.search(r'default\s*=\s*"([^"]*)"', block.group(1))
    assert default, f"variable {name!r} has no string default"
    return default.group(1)


def _parse_tf_alarm_identities(tf_text: str) -> list[tuple[str, str, frozenset[str]]]:
    """Per alarm: (metric_name, namespace_ref, dimension-key-set) — textual parse of the .tf."""
    chunks = re.split(r'resource\s+"aws_cloudwatch_metric_alarm"\s+"[^"]+"\s*\{', tf_text)[1:]
    identities: list[tuple[str, str, frozenset[str]]] = []
    for chunk in chunks:
        metric = re.search(r'metric_name\s*=\s*"([^"]+)"', chunk)
        namespace = re.search(r"namespace\s*=\s*(\S+)", chunk)
        dims = re.search(r"dimensions\s*=\s*\{([^}]*)\}", chunk)
        assert metric and namespace, "alarm missing metric_name/namespace"
        keys: set[str] = set()
        if dims:
            for pair in dims.group(1).split(","):
                pair = pair.strip()
                if pair:
                    keys.add(pair.split("=")[0].strip())
        identities.append((metric.group(1), namespace.group(1), frozenset(keys)))
    return identities


def _emitter_identities(metric_data: list[dict[str, Any]]) -> dict[str, frozenset[str]]:
    """metric_name → the set of dimension KEYS the emitter stamps on it."""
    out: dict[str, frozenset[str]] = {}
    for datum in metric_data:
        keys = frozenset(d["Name"] for d in datum.get("Dimensions", []))
        out[datum["MetricName"]] = keys
    return out


def test_terraform_alarms_bind_to_emitted_metric_identities() -> None:
    """SEAM TRIPWIRE (F-1 cure): every PROV alarm's (namespace, metric, dim-keys) MUST be an
    identity the emitter actually emits. A rename/re-dimension on EITHER side goes RED here —
    the discipline the tf header states for the NAME, now enforced as a test for the DIMENSIONS.
    """
    tf_text = _TF_ALARMS.read_text()

    # namespace: the alarm var default must equal the emitter constant.
    ns_default = _parse_tf_variable_default(tf_text, "substrate_provability_namespace")
    assert ns_default == SUBSTRATE_PROVABILITY_NAMESPACE

    # environment dimension VALUE: emitter default must equal the shared tf var default,
    # else the alarm series (…{environment=production}) and the emitted series diverge.
    env_default = _parse_tf_variable_default(_TF_SHARED.read_text(), "environment")
    assert env_default == DEFAULT_ENVIRONMENT

    # Build the emitter's emitted identities (a run WITH a verdict so ArtifactProvable exists too).
    aid = _aid("1143843662099250")
    verdict = ArtifactVerdict(
        aid=aid,
        provability=Provability.PROVABLE,
        provable=True,
        age_seconds=60.0,
        missing=False,
        in_registry=True,
        in_store=True,
    )
    run = EvaluationRun(
        run_id="r",
        scheduled_at=NOW,
        registry_targets=frozenset({aid}),
        store_targets=frozenset({aid}),
        verdicts=(verdict,),
        unevaluated=frozenset(),
    )
    emitted = _emitter_identities(CloudWatchProvabilityEmitter.build_metric_data(run))

    alarms = _parse_tf_alarm_identities(tf_text)
    assert len(alarms) == 6, "expected PROV-1..6 alarm resources"
    for metric_name, ns_ref, dim_keys in alarms:
        resolved_ns = (
            ns_default if ns_ref == "var.substrate_provability_namespace" else ns_ref.strip('"')
        )
        assert resolved_ns == SUBSTRATE_PROVABILITY_NAMESPACE, f"{metric_name}: namespace drift"
        assert metric_name in emitted, f"alarm metric {metric_name} is NOT emitted (dead series)"
        assert dim_keys == emitted[metric_name], (
            f"{metric_name}: alarm queries dims {set(dim_keys)} but emitter emits "
            f"{set(emitted[metric_name])} — CloudWatch identity mismatch (F-1 class)"
        )
    # Every alarm queries the environment key — the F-1 defect was its absence emitter-side.
    assert all(DIMENSION_ENVIRONMENT in keys for _, _, keys in alarms)


# ---------------------------------------------------------------------------
# F-2 — expected-set fetch failure emits a LOUD failed run, never a silent no-run
# ---------------------------------------------------------------------------


class _ExplodingExpectedSet:
    """An ExpectedSetSource whose enumeration raises (registry backend 500 / S3 AccessDenied)."""

    async def registry_targets(self) -> set[ArtifactId]:
        raise RuntimeError("registry backend 500")

    async def store_enumeration(self) -> set[ArtifactId]:
        raise RuntimeError("S3 ListObjectsV2 AccessDenied")


async def test_expected_set_fetch_failure_emits_loud_run_not_silent_crash() -> None:
    """F-2: a fetch failure still EMITS (heartbeat + ExpectedCount=0 + Completeness=0 +
    EvaluationFailed=1) and returns — never raises out of evaluate_all pre-emission."""
    emitter = RecordingEmitter()
    evaluator = ScheduledProvabilityEvaluator(
        store=FakeStore(),
        expected_set=_ExplodingExpectedSet(),
        is_provable=_faithful_is_provable,
        digest_of_frame=_digest_of,
        emitter=emitter,
    )

    run = await evaluator.evaluate_all(NOW)  # must NOT raise

    assert run.evaluation_failed is True
    assert emitter.runs == [run]  # emission happened despite the fetch failure
    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EVALUATOR_HEARTBEAT) == 1.0  # evaluator RAN
    assert _run_metric(metric_data, METRIC_EXPECTED_COUNT) == 0.0  # PROV-5 floor FIRES
    assert _run_metric(metric_data, METRIC_COMPLETENESS) == 0.0  # PROV-3 FIRES (not vacuous 100)
    assert _run_metric(metric_data, METRIC_EVALUATION_FAILED) == 1.0


# ---------------------------------------------------------------------------
# F-3 — empty expected-set fires the PROV-5 floor (evaluator watching nothing)
# ---------------------------------------------------------------------------


async def test_empty_expected_set_fires_the_floor() -> None:
    """F-3: registry=∅ ∧ store=∅ → ExpectedCount=0 (PROV-5 floor FIRES), not vacuous green."""
    run = await _build_evaluator(store=FakeStore(), registry=set(), store_set=set()).evaluate_all(
        NOW
    )
    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_EXPECTED_COUNT) == 0.0  # PROV-5 (< 1) FIRES
    # The other four still read clean on an empty set — PROV-5 is the ONLY floor that catches it.
    assert _run_metric(metric_data, METRIC_UNPROVABLE_COUNT) == 0.0
    assert _run_metric(metric_data, METRIC_EXPECTED_SET_MISMATCH_COUNT) == 0.0


# ---------------------------------------------------------------------------
# F-4 — CloudWatchProvabilityEmitter honestly satisfies the ProvabilityEmitter port
# ---------------------------------------------------------------------------


def test_cloudwatch_emitter_conforms_to_the_emitter_port() -> None:
    """F-4: the concrete emitter satisfies ProvabilityEmitter under mypy-strict (no Any-dodge)."""
    # Inject a fake client so the port call stays offline (DARK — no AWS).
    port: ProvabilityEmitter = CloudWatchProvabilityEmitter(cw_client=RecordingCwClient())
    run = EvaluationRun(
        run_id="p",
        scheduled_at=NOW,
        registry_targets=frozenset(),
        store_targets=frozenset(),
        verdicts=(),
        unevaluated=frozenset(),
    )
    port.emit_run(run)  # the port's -> None signature is mypy-enforced by the assignment above


# ---------------------------------------------------------------------------
# Addendum — future-dated proof anomaly (S2-GO condition): disclosed, never smoothed
# ---------------------------------------------------------------------------


def _future_dated_entry(raw: bytes = b"frame-future") -> tuple[bytes, FreshnessProof]:
    """A proof stamped 24h in the FUTURE → negative age (writer clock skew / bad stamp)."""
    proof = FreshnessProof(
        built_from_live_at=NOW + timedelta(hours=24),
        content_digest=_digest_of(raw),
        sla_seconds=3600,
    )
    return raw, proof


async def test_future_dated_proof_fires_anomaly_and_never_emits_negative_gauge() -> None:
    """Addendum RED side: a future-dated proof FIRES FutureDatedProofCount and the staleness
    gauge is CLAMPED >= 0 — never the raw negative "super-fresh-while-broken" value."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _future_dated_entry()})
    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)

    # is_provable is FOOLED (negative age <= sla → PROVABLE) — that is the S2 gap …
    (verdict,) = run.verdicts
    assert verdict.provable is True
    assert verdict.age_seconds is not None and verdict.age_seconds < 0  # raw age is negative
    # … but S6 DISCLOSES it: the anomaly count fires and the gauge is clamped.
    assert run.future_dated_count == 1
    assert run.max_staleness_age_seconds == 0.0  # clamped, NOT -86400

    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_FUTURE_DATED_PROOF_COUNT) == 1.0  # PROV-6 FIRES
    assert _run_metric(metric_data, METRIC_MAX_STALENESS_AGE_SECONDS) >= 0.0  # never negative


async def test_normal_proof_keeps_the_future_dated_anomaly_silent() -> None:
    """Addendum GREEN side: an ordinary fresh proof → FutureDatedProofCount==0, gauge >= 0."""
    aid = _aid("1143843662099250")
    store = FakeStore(entries={aid: _provable_entry()})
    run = await _build_evaluator(store=store, registry={aid}, store_set={aid}).evaluate_all(NOW)

    assert run.future_dated_count == 0
    metric_data = CloudWatchProvabilityEmitter.build_metric_data(run)
    assert _run_metric(metric_data, METRIC_FUTURE_DATED_PROOF_COUNT) == 0.0  # PROV-6 SILENT
    assert _run_metric(metric_data, METRIC_MAX_STALENESS_AGE_SECONDS) >= 0.0
