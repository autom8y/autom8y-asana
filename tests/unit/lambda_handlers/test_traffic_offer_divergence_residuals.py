"""Two-sided teeth for the R7 tripwire's two seam-blocking residual defects.

Both defects were found live by the sre wave's own arm leg, and both made the
instrument QUIETLY WRONG -- it published a confident number while half-blind, which is
the never-silent doctrine's exact inversion.

DEFECT 1 (HIGH) -- the scheduling traffic leg was STRUCTURALLY DEAD and failed SOFT.
    ``DEFAULT_SCHEDULING_LOG_GROUP`` was ``/ecs/autom8-prod``, a PHANTOM (``autom8-prod``
    is the legacy ALB name; the group does not exist in the account). Every armed run
    logged ``traffic_offer_divergence_scheduling_leg_failed:
    ResourceNotFoundException`` and then SWALLOWED it, so ``TrafficOfficesEvaluated``
    and ``TradingWithoutActiveOfferCount`` were EBI-ONLY undercounts published
    alongside ``EvaluationRefused=0``. R-eps: post-cutover, bookings migrate ONTO the
    scheduling plane, so the instrument degrades in DIRECT PROPORTION to the campaign
    succeeding.
    CURE: (a) the real group ``/ecs/autom8y-scheduling-service``; (b) BOTH legs are
    REQUIRED -- an unreadable leg REFUSES the cycle (routed through the already-armed
    ``EvaluationRefused`` alarm) and stamps ``TrafficLegUnavailable{leg}``.

DEFECT 2 (MEDIUM) -- baseline-absent was INDISTINGUISHABLE from a permissions failure.
    ``_read_baseline`` caught EVERY exception and returned an empty prior. Cycle 1's
    ``baseline_absent`` in fact carried ``AccessDenied ... s3:ListBucket``: without
    ListBucket, S3 answers a MISSING key with 403, not 404. It was correct BY LUCK
    once; under policy drift the emitter silently re-seeds and emits
    ``newly ~= <whole standing divergent population>`` into the >=1 fast-burn alarm --
    a FALSE PAGE to a live SMS subscriber.
    CURE: only a proven-absent key (``NoSuchKey``/404) seeds; every other code REFUSES.

LOW (folded in) -- the alarm runbooks pointed triage at "the per-office structured log
    (event=traffic_offer_divergence_evaluated)", but that event is AGGREGATE-ONLY. The
    documented triage path did not exist. CURE: emit a real per-office line
    (``traffic_offer_divergence_office``), non-PII (phone HASH, the same digest the
    baseline commits) and loudly truncated.

Every leg here is TWO-SIDED: the fixed behavior is asserted GREEN, and the PRE-FIX
shape is reconstructed inline and asserted to produce the exact silent-wrong outcome
(RED) -- a one-sided green proof of a "now it refuses" claim is vacuous.
"""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from autom8_asana.lambda_handlers import traffic_offer_divergence_tripwire as r7
from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
    BASELINE_ABSENT_ERROR_CODES,
    DEFAULT_SCHEDULING_LOG_GROUP,
    METRIC_EVALUATION_REFUSED,
    METRIC_LAST_RUN_EPOCH,
    METRIC_NEWLY_TRADING,
    METRIC_ROSTER_SIZE,
    METRIC_TRADING_COUNT,
    METRIC_TRAFFIC_LEG_UNAVAILABLE,
    METRIC_TRAFFIC_OFFICES,
    PER_OFFICE_LOG_CAP,
    PHANTOM_SCHEDULING_LOG_GROUP,
    TRAFFIC_LEG_EBI,
    TRAFFIC_LEG_SCHEDULING,
    EvaluationRefusedError,
    TrafficLeg,
    TrafficLegUnavailableError,
    baseline_error_code,
    classify_baseline_read_failure,
    compute_newly_divergent,
    emit_per_office_triage,
    phone_hash,
    resolve_divergence,
    resolve_traffic_legs,
    run_divergence_evaluation,
    union_traffic_legs,
)

# Offices: EBI-visible (divergent), scheduling-ONLY (divergent, and INVISIBLE to an
# EBI-only read -- this is the office the pre-fix instrument could not see), matched.
EBI_ONLY_PHONE = "+19097939355"
SCHED_ONLY_PHONE = "+14804544776"
MATCHED_PHONE = "+15550001111"


def _offer_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    complete: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        complete.append(
            {
                "gid": row.get("gid", f"o{i}"),
                "office_phone": row.get("office_phone"),
                "section": row.get("section", "INACTIVE"),
                "is_completed": row.get("is_completed", False),
            }
        )
    return pl.DataFrame(
        complete,
        schema_overrides={"is_completed": pl.Boolean, "office_phone": pl.Utf8},
    )


class _ClientErrorStub(Exception):
    """Shape-compatible botocore ``ClientError`` stub (``.response`` dict)."""

    def __init__(self, code: str, status: int | None = None) -> None:
        super().__init__(code)
        self.response: dict[str, Any] = {"Error": {"Code": code, "Message": code}}
        if status is not None:
            self.response["ResponseMetadata"] = {"HTTPStatusCode": status}


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, str | None, Any]]:
    """Capture every ``emit_metric`` call as (name, value, namespace, dimensions)."""
    calls: list[tuple[str, float, str | None, Any]] = []

    def _fake_emit(
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
        namespace: str | None = None,
    ) -> None:
        calls.append((metric_name, value, namespace, dimensions))

    monkeypatch.setattr(r7, "emit_metric", _fake_emit)
    return calls


class _LogRecorder:
    """Record ``logger.<level>(event, extra=...)`` calls without a real logger."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, Any]]] = []

    def _record(self, level: str, event: str, extra: dict[str, Any] | None = None) -> None:
        self.lines.append((level, event, dict(extra or {})))

    def info(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._record("info", event, extra)

    def warning(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._record("warning", event, extra)

    def error(self, event: str, extra: dict[str, Any] | None = None, **_: Any) -> None:
        self._record("error", event, extra)

    def events(self) -> list[str]:
        return [e for (_lvl, e, _x) in self.lines]

    def of(self, event: str) -> list[dict[str, Any]]:
        return [x for (_lvl, e, x) in self.lines if e == event]


@pytest.fixture
def logs(monkeypatch: pytest.MonkeyPatch) -> _LogRecorder:
    rec = _LogRecorder()
    monkeypatch.setattr(r7, "logger", rec)
    return rec


# ===========================================================================
# DEFECT 1a -- the scheduling leg points at a REAL log group
# ===========================================================================


class TestSchedulingLogGroupIsReal:
    def test_default_is_the_scheduling_SERVICE_group(self) -> None:
        """The booking_success emitter is the MODERN autom8y-scheduling ECS service.

        Anchors (file-read, no AWS): emit site autom8y-scheduling
        src/autom8_scheduling/scheduling/booking.py:221; log-group construction autom8y
        terraform/modules/platform/primitives/ecs-fargate-service/main.tf:10 (name_prefix
        = autom8y-${service_name}-service) + :54 (name = /ecs/${local.name_prefix});
        the prefix is pinned to autom8y-scheduling-service at
        terraform/services/scheduling/main.tf:42.
        """
        assert DEFAULT_SCHEDULING_LOG_GROUP == "/ecs/autom8y-scheduling-service"

    def test_default_is_NOT_the_phantom_RED(self) -> None:
        """RED: the pre-fix default. ``autom8-prod`` is the legacy ALB name -- there is
        no such log group, so the leg raised ResourceNotFoundException on EVERY run."""
        assert PHANTOM_SCHEDULING_LOG_GROUP == "/ecs/autom8-prod"
        assert DEFAULT_SCHEDULING_LOG_GROUP != PHANTOM_SCHEDULING_LOG_GROUP

    def test_both_legs_are_resolved_with_real_groups(self) -> None:
        legs = resolve_traffic_legs(7)
        assert [leg.name for leg in legs] == [TRAFFIC_LEG_EBI, TRAFFIC_LEG_SCHEDULING]
        by_name = {leg.name: leg for leg in legs}
        assert by_name[TRAFFIC_LEG_EBI].log_group == "/aws/lambda/autom8-email-booking-intake"
        assert by_name[TRAFFIC_LEG_SCHEDULING].log_group == DEFAULT_SCHEDULING_LOG_GROUP
        # The scheduling leg still selects the committed-write event, never the R1 gate event.
        assert "booking_success" in by_name[TRAFFIC_LEG_SCHEDULING].query
        assert "scheduling_gate_rejected" not in by_name[TRAFFIC_LEG_SCHEDULING].query

    def test_env_override_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(r7.SCHEDULING_LOG_GROUP_ENV_VAR, "/ecs/other-service")
        legs = {leg.name: leg for leg in resolve_traffic_legs(7)}
        assert legs[TRAFFIC_LEG_SCHEDULING].log_group == "/ecs/other-service"


# ===========================================================================
# DEFECT 1b -- a failed traffic leg is LOUD (refuses), never a silent partial
# ===========================================================================


def _leg(name: str, group: str = "/g") -> TrafficLeg:
    return TrafficLeg(name=name, log_group=group, query="q")


class TestTrafficLegIsRequired:
    def test_GREEN_healthy_two_surface_read_produces_the_UNION(self) -> None:
        """Both legs readable -> the union of phones and the SUM of per-office counts."""
        tallies = {
            TRAFFIC_LEG_EBI: {EBI_ONLY_PHONE: 2, MATCHED_PHONE: 1},
            TRAFFIC_LEG_SCHEDULING: {SCHED_ONLY_PHONE: 3, MATCHED_PHONE: 4},
        }
        tally = union_traffic_legs(
            [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)],
            run_leg=lambda leg: tallies[leg.name],
        )
        assert tally.phones == frozenset({EBI_ONLY_PHONE, SCHED_ONLY_PHONE, MATCHED_PHONE})
        assert tally.bookings_by_phone[MATCHED_PHONE] == 5  # 1 (EBI) + 4 (scheduling)
        assert tally.bookings_by_phone[SCHED_ONLY_PHONE] == 3  # invisible to an EBI-only read

    def test_RED_unreadable_scheduling_leg_REFUSES(self) -> None:
        """The exact live failure: ResourceNotFoundException on the scheduling group."""

        def run_leg(leg: TrafficLeg) -> dict[str, int]:
            if leg.name == TRAFFIC_LEG_SCHEDULING:
                raise RuntimeError("ResourceNotFoundException: Log group does not exist")
            return {EBI_ONLY_PHONE: 1}

        with pytest.raises(TrafficLegUnavailableError) as exc:
            union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)], run_leg=run_leg
            )
        assert exc.value.leg == TRAFFIC_LEG_SCHEDULING
        # A refusal routed through the ARMED EvaluationRefused alarm (no new alarm needed).
        assert isinstance(exc.value, EvaluationRefusedError)

    def test_RED_unreadable_ebi_leg_REFUSES_symmetrically(self) -> None:
        def run_leg(leg: TrafficLeg) -> dict[str, int]:
            if leg.name == TRAFFIC_LEG_EBI:
                raise RuntimeError("ThrottlingException")
            return {SCHED_ONLY_PHONE: 1}

        with pytest.raises(TrafficLegUnavailableError) as exc:
            union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)], run_leg=run_leg
            )
        assert exc.value.leg == TRAFFIC_LEG_EBI

    def test_RED_blank_log_group_REFUSES_rather_than_skipping(self) -> None:
        """Pre-fix an unset scheduling group was SKIPPED -- config alone could halve the
        denominator with no signal at all."""
        with pytest.raises(TrafficLegUnavailableError) as exc:
            union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING, group="   ")],
                run_leg=lambda _leg: {},
            )
        assert exc.value.leg == TRAFFIC_LEG_SCHEDULING

    def test_GREEN_an_empty_leg_result_is_a_real_read_not_a_failure(self) -> None:
        """A genuinely quiet window must NOT refuse -- only an UNREADABLE leg refuses."""
        tally = union_traffic_legs(
            [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)],
            run_leg=lambda leg: {} if leg.name == TRAFFIC_LEG_SCHEDULING else {EBI_ONLY_PHONE: 1},
        )
        assert tally.phones == frozenset({EBI_ONLY_PHONE})

    def test_no_legs_configured_REFUSES(self) -> None:
        with pytest.raises(EvaluationRefusedError):
            union_traffic_legs([], run_leg=lambda _leg: {})

    def test_refusal_message_NAMES_the_leg_and_group(self) -> None:
        """A refusal the operator cannot act on is a wedge -- it must name what died."""
        err = TrafficLegUnavailableError(TRAFFIC_LEG_SCHEDULING, "/ecs/nope", "boom")
        assert TRAFFIC_LEG_SCHEDULING in str(err)
        assert "/ecs/nope" in str(err)


class TestFullCycleTrafficLegSemantics:
    def _frame(self) -> pl.DataFrame:
        return _offer_df(
            [
                {"office_phone": EBI_ONLY_PHONE, "section": "inactive"},
                {"office_phone": SCHED_ONLY_PHONE, "section": "inactive"},
                {"office_phone": MATCHED_PHONE, "section": "active"},
            ]
        )

    def test_RED_dead_scheduling_leg_refuses_emits_no_count_and_does_not_commit(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        """★ THE HEADLINE. Pre-fix this run published a CONFIDENT EBI-only count with
        EvaluationRefused=0. Post-fix: refused, no verdict, leg attributed, no commit."""
        committed: list[set[str]] = []

        def gather() -> Any:
            return union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)],
                run_leg=lambda leg: (
                    {EBI_ONLY_PHONE: 1}
                    if leg.name == TRAFFIC_LEG_EBI
                    else (_ for _ in ()).throw(RuntimeError("ResourceNotFoundException"))
                ),
            )

        result = run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (self._frame(), 1_000_000.0),
            gather_traffic=gather,
            read_baseline=lambda: set(),
            commit_baseline=committed.append,
            now_epoch=1_000_000.0,
            ceiling_seconds=43200,
        )

        assert result.status == "refused"
        pairs = {(m, v) for (m, v, _ns, _d) in captured}
        emitted = {m for (m, _v, _ns, _d) in captured}
        assert (METRIC_EVALUATION_REFUSED, 1) in pairs
        assert METRIC_LAST_RUN_EPOCH in emitted  # dead-man heartbeat still flows
        # NO fabricated / half-denominator verdict.
        assert METRIC_TRADING_COUNT not in emitted
        assert METRIC_TRAFFIC_OFFICES not in emitted
        assert METRIC_ROSTER_SIZE not in emitted
        # The refusal is ATTRIBUTED to the leg that died.
        leg_dims = [d for (m, _v, _ns, d) in captured if m == METRIC_TRAFFIC_LEG_UNAVAILABLE]
        assert leg_dims == [{"leg": TRAFFIC_LEG_SCHEDULING}]
        # Poisoning guard holds on this refusal path too.
        assert committed == []

    def test_GREEN_two_surface_union_counts_the_scheduling_only_office(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        """★ The other side: with BOTH legs healthy the scheduling-only divergent office
        is counted. An EBI-only read would report 1; the union reports 2."""
        committed: list[set[str]] = []

        def gather() -> Any:
            return union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)],
                run_leg=lambda leg: (
                    {EBI_ONLY_PHONE: 2, MATCHED_PHONE: 1}
                    if leg.name == TRAFFIC_LEG_EBI
                    else {SCHED_ONLY_PHONE: 3}
                ),
            )

        result = run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (self._frame(), 1_000_000.0),
            gather_traffic=gather,
            read_baseline=lambda: set(),
            commit_baseline=committed.append,
            now_epoch=1_000_000.0,
            ceiling_seconds=43200,
        )

        assert result.status == "evaluated"
        assert result.divergent_count == 2  # EBI-only office + scheduling-only office
        pairs = {(m, v) for (m, v, _ns, _d) in captured}
        assert (METRIC_TRADING_COUNT, 2) in pairs
        assert (METRIC_TRAFFIC_OFFICES, 3) in pairs
        assert (METRIC_EVALUATION_REFUSED, 0) in pairs
        assert METRIC_TRAFFIC_LEG_UNAVAILABLE not in {m for (m, _v, _ns, _d) in captured}
        assert len(committed) == 1

    def test_RED_the_PRE_FIX_best_effort_shape_yields_a_SILENT_PARTIAL(self) -> None:
        """RED reconstruction of the swallowed-exception shape that shipped.

        This is what the deployed emitter did: catch the scheduling failure, log a
        warning, and carry on with an EBI-only tally -- yielding divergent_count=1 for a
        population that is really 2, with NO refusal signal anywhere. Asserting the
        defect explicitly keeps the cure honest: the fixed union CANNOT produce this."""
        ebi_only = {EBI_ONLY_PHONE: 2, MATCHED_PHONE: 1}
        tally = dict(ebi_only)
        try:
            raise RuntimeError("ResourceNotFoundException: /ecs/autom8-prod")
        except Exception:  # noqa: BLE001 -- deliberately reproducing the pre-fix swallow
            pass  # <- the pre-fix behavior: degrade to EBI-only, emit no refusal

        pre_fix = r7.TrafficTally(phones=frozenset(tally), bookings_by_phone=tally)
        verdict = resolve_divergence(self._frame(), pre_fix)
        assert len(verdict.divergent_phones) == 1  # UNDERCOUNT: misses SCHED_ONLY_PHONE
        assert SCHED_ONLY_PHONE not in verdict.divergent_phones

        # And the fixed path refuses on the same input rather than reporting that 1.
        with pytest.raises(TrafficLegUnavailableError):
            union_traffic_legs(
                [_leg(TRAFFIC_LEG_EBI), _leg(TRAFFIC_LEG_SCHEDULING)],
                run_leg=lambda leg: (
                    ebi_only
                    if leg.name == TRAFFIC_LEG_EBI
                    else (_ for _ in ()).throw(RuntimeError("ResourceNotFoundException"))
                ),
            )


# ===========================================================================
# DEFECT 2 -- baseline 403 REFUSES; only a proven 404 seeds
# ===========================================================================


class TestBaselineFailureClassification:
    def test_GREEN_NoSuchKey_is_a_genuine_first_run(self) -> None:
        assert classify_baseline_read_failure(_ClientErrorStub("NoSuchKey")) is True

    def test_GREEN_404_status_fallback_is_a_genuine_first_run(self) -> None:
        exc = _ClientErrorStub("", status=404)
        exc.response["Error"] = {}
        assert baseline_error_code(exc) == "404"
        assert classify_baseline_read_failure(exc) is True

    def test_RED_AccessDenied_is_NOT_a_first_run(self) -> None:
        """★ THE DEFECT. Absent s3:ListBucket a MISSING key answers 403 -- so this code
        is exactly what cycle 1 observed, and pre-fix it read as "seed the baseline"."""
        assert classify_baseline_read_failure(_ClientErrorStub("AccessDenied", 403)) is False

    def test_RED_403_status_fallback_is_NOT_a_first_run(self) -> None:
        exc = _ClientErrorStub("", status=403)
        exc.response["Error"] = {}
        assert classify_baseline_read_failure(exc) is False

    def test_RED_unknown_failure_is_fail_CLOSED(self) -> None:
        """A timeout / connection error / anything unrecognised must NOT seed."""
        assert classify_baseline_read_failure(TimeoutError("connect timeout")) is False

    def test_absent_codes_are_the_frozen_allowlist(self) -> None:
        assert "AccessDenied" not in BASELINE_ABSENT_ERROR_CODES
        assert "403" not in BASELINE_ABSENT_ERROR_CODES
        assert set(BASELINE_ABSENT_ERROR_CODES) == {"NoSuchKey", "404", "NotFound"}


class TestReadBaselineWiring:
    def _patch_s3(self, monkeypatch: pytest.MonkeyPatch, raise_exc: Exception) -> None:
        import boto3

        class _S3:
            def get_object(self, **_: Any) -> Any:
                raise raise_exc

        monkeypatch.setattr(boto3, "client", lambda _svc, **_kw: _S3())

    def test_RED_403_read_REFUSES_and_names_the_code(
        self, monkeypatch: pytest.MonkeyPatch, logs: _LogRecorder
    ) -> None:
        self._patch_s3(monkeypatch, _ClientErrorStub("AccessDenied", 403))
        with pytest.raises(EvaluationRefusedError) as exc:
            r7._read_baseline()
        # Actionable: names the observed code AND the remedy.
        assert "AccessDenied" in str(exc.value)
        assert "s3:ListBucket" in str(exc.value)
        # It must NOT have logged the misleading "absent" line.
        assert "traffic_offer_divergence_baseline_absent" not in logs.events()

    def test_GREEN_404_read_seeds_once(
        self, monkeypatch: pytest.MonkeyPatch, logs: _LogRecorder
    ) -> None:
        self._patch_s3(monkeypatch, _ClientErrorStub("NoSuchKey", 404))
        assert r7._read_baseline() == set()
        absent = logs.of("traffic_offer_divergence_baseline_absent")
        assert len(absent) == 1
        assert absent[0]["error_code"] == "NoSuchKey"
        assert absent[0]["seeding"] is True


class TestFullCycleBaselineSemantics:
    def _frame(self) -> pl.DataFrame:
        return _offer_df([{"office_phone": EBI_ONLY_PHONE, "section": "inactive"}])

    def _traffic(self) -> Any:
        return r7.TrafficTally(frozenset({EBI_ONLY_PHONE}), {EBI_ONLY_PHONE: 4})

    def test_RED_403_baseline_refuses_the_cycle_and_does_not_commit(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        """★ THE HEADLINE. Pre-fix this run seeded from empty and published
        NewlyTradingWithoutActiveOfferCount = the whole divergent population, which the
        >=1 fast-burn alarm pages on (live SMS subscriber)."""
        committed: list[set[str]] = []

        def read_baseline() -> set[str]:
            raise EvaluationRefusedError("baseline read failed with 'AccessDenied'")

        result = run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (self._frame(), 1_000_000.0),
            gather_traffic=self._traffic,
            read_baseline=read_baseline,
            commit_baseline=committed.append,
            now_epoch=1_000_000.0,
            ceiling_seconds=43200,
        )

        assert result.status == "refused"
        emitted = {m for (m, _v, _ns, _d) in captured}
        assert (METRIC_EVALUATION_REFUSED, 1) in {(m, v) for (m, v, _ns, _d) in captured}
        assert METRIC_NEWLY_TRADING not in emitted  # NO false fast-burn datapoint
        assert METRIC_TRADING_COUNT not in emitted
        assert committed == []  # baseline untouched -- nothing to re-seed from

    def test_RED_pre_fix_swallow_would_have_published_a_full_population_newly(self) -> None:
        """RED reconstruction: the catch-all returned an empty prior, so EVERY standing
        divergent office read as NEWLY divergent."""
        standing = frozenset({EBI_ONLY_PHONE, SCHED_ONLY_PHONE, MATCHED_PHONE})
        pre_fix_prior: set[str] = set()  # <- what the catch-all returned on a 403
        newly, _ = compute_newly_divergent(standing, pre_fix_prior)
        assert newly == len(standing)  # fast-burn threshold is >=1: this pages

        # With an honest prior the same population is quiet.
        honest_prior = {phone_hash(p) for p in standing}
        newly_ok, _ = compute_newly_divergent(standing, honest_prior)
        assert newly_ok == 0


# ===========================================================================
# LOW (folded in) -- the per-office triage surface the runbooks name
# ===========================================================================


class TestPerOfficeTriageLine:
    def _verdict(self, phones: list[str]) -> Any:
        frame = _offer_df([{"office_phone": p, "section": "inactive"} for p in phones])
        tally = r7.TrafficTally(frozenset(phones), {p: 7 for p in phones})
        return resolve_divergence(frame, tally), tally

    def test_one_line_per_divergent_office(self, logs: _LogRecorder) -> None:
        verdict, tally = self._verdict([EBI_ONLY_PHONE, SCHED_ONLY_PHONE])
        emitted = emit_per_office_triage(verdict, set(), tally.bookings_by_phone)
        assert emitted == 2
        lines = logs.of("traffic_offer_divergence_office")
        assert len(lines) == 2
        assert {line["phone_hash"] for line in lines} == {
            phone_hash(EBI_ONLY_PHONE),
            phone_hash(SCHED_ONLY_PHONE),
        }
        assert all(line["bookings"] == 7 for line in lines)

    def test_RED_no_plaintext_phone_or_guid_leaks_into_the_line(self, logs: _LogRecorder) -> None:
        """I-NO-PII: the triage surface identifies an office by the SAME digest the
        baseline commits, never a phone."""
        verdict, tally = self._verdict([EBI_ONLY_PHONE, SCHED_ONLY_PHONE])
        emit_per_office_triage(verdict, set(), tally.bookings_by_phone)
        blob = repr(logs.lines)
        assert EBI_ONLY_PHONE not in blob
        assert SCHED_ONLY_PHONE not in blob

    def test_newly_flag_is_two_sided(self, logs: _LogRecorder) -> None:
        verdict, tally = self._verdict([EBI_ONLY_PHONE, SCHED_ONLY_PHONE])
        prior = {phone_hash(EBI_ONLY_PHONE)}  # already baselined
        emit_per_office_triage(verdict, prior, tally.bookings_by_phone)
        by_hash = {line["phone_hash"]: line for line in logs.of("traffic_offer_divergence_office")}
        assert by_hash[phone_hash(EBI_ONLY_PHONE)]["newly"] is False
        assert by_hash[phone_hash(SCHED_ONLY_PHONE)]["newly"] is True

    def test_truncation_is_LOUD_never_silent(
        self, logs: _LogRecorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(r7, "PER_OFFICE_LOG_CAP", 2)
        phones = [f"+1555000{i:04d}" for i in range(5)]
        verdict, tally = self._verdict(phones)
        emitted = emit_per_office_triage(verdict, set(), tally.bookings_by_phone)
        assert emitted == 2
        truncated = logs.of("traffic_offer_divergence_office_log_truncated")
        assert len(truncated) == 1
        assert truncated[0]["withheld"] == 3
        assert truncated[0]["emitted"] == 2

    def test_cap_is_above_the_observed_traffic_denominator(self) -> None:
        """Spec §5 observed 70 EBI traffic phones/30d; the cap must not bite in practice."""
        assert PER_OFFICE_LOG_CAP >= 250

    def test_evaluated_run_emits_BOTH_the_aggregate_and_the_per_office_lines(
        self, logs: _LogRecorder, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        """The runbook names both surfaces; both must actually exist on one run."""
        run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (
                _offer_df([{"office_phone": EBI_ONLY_PHONE, "section": "inactive"}]),
                1_000_000.0,
            ),
            gather_traffic=lambda: r7.TrafficTally(
                frozenset({EBI_ONLY_PHONE}), {EBI_ONLY_PHONE: 9}
            ),
            read_baseline=lambda: set(),
            commit_baseline=lambda _h: None,
            now_epoch=1_000_000.0,
            ceiling_seconds=43200,
        )
        events = logs.events()
        assert "traffic_offer_divergence_evaluated" in events  # aggregate
        assert "traffic_offer_divergence_office" in events  # per-office
        office = logs.of("traffic_offer_divergence_office")[0]
        assert office["bookings"] == 9
        assert office["newly"] is True
