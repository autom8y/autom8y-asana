"""Two-sided teeth for the R7 traffic-vs-offer divergence tripwire (HALF-1 emitter).

The design contract (SPEC-ws-e-divergence-tripwire-2026-08-03 §2): the instrument is
LOUD on a real mismatch (RED) and SILENT on a matched office (GREEN) AND on the R1
gate-declined-with-active-offer boundary. A one-sided proof (only the RED breach) is
INSUFFICIENT -- the SILENT-on-matched and SILENT-on-R1 legs are what prove the
instrument does not cry wolf. The REFUSE leg proves a broken/stale frame yields NO
verdict (never a fabricated 0). Plus: the baseline-poisoning guard, the
anti-blind-instrument event-name teeth (the query selects booking_success/guid_resolved
and NEVER scheduling_gate_rejected), and the byte-exact cross-repo emit<->alarm contract.
"""

from __future__ import annotations

import re
from typing import Any

import polars as pl
import pytest

from autom8_asana.lambda_handlers import traffic_offer_divergence_tripwire as r7
from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
    CANARY_SENTINEL_EXCLUSION_CLAUSE,
    CANARY_SENTINEL_PHONE,
    CLASS_ABSENT_FROM_FRAME,
    CLASS_INFRAME_INACTIVE,
    EBI_RESOLVE_EVENTS,
    METRIC_EVALUATION_REFUSED,
    METRIC_LAST_RUN_EPOCH,
    METRIC_NAMESPACE,
    METRIC_NEWLY_TRADING,
    METRIC_ROSTER_SIZE,
    METRIC_TRADING_COUNT,
    SCHEDULING_BOOKING_EVENT,
    SCHEDULING_R1_GATE_EVENT_EXCLUDED,
    EvaluationRefusedError,
    TrafficTally,
    active_roster_phones,
    assert_frame_fresh,
    assert_frame_readable,
    build_ebi_query,
    build_scheduling_query,
    classify_divergent,
    compute_newly_divergent,
    resolve_divergence,
    run_divergence_evaluation,
)

# Fixture phones (deliberately-broken RED phone + healthy GREEN/R1 phones).
RED_PHONE = "+19097939355"  # Active Life Chiropractic (spike exemplar: only inactive rows)
GREEN_PHONE = "+15550001111"  # matched: has an ACTIVE offer row
R1_PHONE = "+15550002222"  # active offer + gate-declined (R1 intent-vs-gate; must be SILENT)
ABSENT_PHONE = "+18137483601"  # absent-from-frame exemplar (no offer row at all)


def _offer_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build an offer frame carrying the R7 required columns.

    Each row dict may set office_phone / section / is_completed (defaults: null phone,
    'INACTIVE', not-completed). ``company_id`` is included null to mirror the live
    guid-dark active roster (spec §5) -- the join must NOT depend on it.
    """
    complete: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        complete.append(
            {
                "gid": row.get("gid", f"o{i}"),
                "office_phone": row.get("office_phone"),
                "section": row.get("section", "INACTIVE"),
                "is_completed": row.get("is_completed", False),
                "company_id": row.get("company_id"),  # null on the active roster (spec §5)
            }
        )
    return pl.DataFrame(
        complete,
        schema_overrides={"is_completed": pl.Boolean, "office_phone": pl.Utf8},
    )


# ---------------------------------------------------------------------------
# The four-case two-sided teeth (RED / GREEN / R1 / REFUSE)
# ---------------------------------------------------------------------------


class TestFourCaseTeeth:
    def test_RED_trading_without_active_offer_is_counted(self) -> None:
        """RED: an office trading with only inactive offer rows -> DIVERGENT (count +1)."""
        df = _offer_df(
            [
                {"office_phone": RED_PHONE, "section": "INACTIVE"},
                {"office_phone": RED_PHONE, "section": "Sales Process"},
            ]
        )
        traffic = TrafficTally(phones=frozenset({RED_PHONE}), bookings_by_phone={RED_PHONE: 155})
        verdict = resolve_divergence(df, traffic)
        assert verdict.divergent_phones == frozenset({RED_PHONE})
        assert verdict.matched_offices == 0
        assert verdict.classes[RED_PHONE] == CLASS_INFRAME_INACTIVE
        assert verdict.class_counts[CLASS_INFRAME_INACTIVE] == 1
        assert verdict.divergent_bookings == 155

    def test_GREEN_matched_office_is_silent(self) -> None:
        """GREEN: an office trading WITH an active offer -> NOT counted (silent)."""
        df = _offer_df([{"office_phone": GREEN_PHONE, "section": "ACTIVE"}])
        traffic = TrafficTally(phones=frozenset({GREEN_PHONE}), bookings_by_phone={GREEN_PHONE: 40})
        verdict = resolve_divergence(df, traffic)
        assert verdict.divergent_phones == frozenset()
        assert verdict.matched_offices == 1
        assert verdict.divergent_bookings == 0

    def test_R1_gate_declined_with_active_offer_is_silent(self) -> None:
        """R1 boundary: gate-declined WHILE holding an active offer -> SILENT.

        R7 keys ONLY on roster membership. An office can be gate-declined
        (scheduling_gate_rejected=business_disabled) yet still hold an active offer;
        that is the R1 intent-vs-gate instrument, NOT R7. The traffic tally carries
        the office's booking_success traffic; its active offer makes it non-divergent
        -- proving R7 != R1."""
        df = _offer_df([{"office_phone": R1_PHONE, "section": "ACTIVATING"}])
        # The office took committed booking traffic AND is (conceptually) gate-declined.
        traffic = TrafficTally(phones=frozenset({R1_PHONE}), bookings_by_phone={R1_PHONE: 3})
        verdict = resolve_divergence(df, traffic)
        assert R1_PHONE not in verdict.divergent_phones
        assert verdict.divergent_phones == frozenset()
        assert verdict.matched_offices == 1

    def test_REFUSE_stale_frame_raises_no_verdict(self) -> None:
        """REFUSE: a stale frame (warmer died) yields NO verdict, never a fabricated 0."""
        now = 1_800_000_000.0
        stale = now - 50_000  # > 43200s ceiling
        with pytest.raises(EvaluationRefusedError, match="stale"):
            assert_frame_fresh(stale, now_epoch=now, ceiling_seconds=43200)

    def test_REFUSE_schema_lag_missing_columns(self) -> None:
        """REFUSE: a pre-projection frame lacking office_phone -> refuse (schema-lag)."""
        df = pl.DataFrame({"gid": ["x"], "section": ["ACTIVE"], "is_completed": [False]})
        with pytest.raises(EvaluationRefusedError, match="required columns"):
            assert_frame_readable(df)

    def test_REFUSE_empty_frame(self) -> None:
        """REFUSE: a 0-row frame (columns present) is indistinguishable from a broken read."""
        df = _offer_df([{"office_phone": RED_PHONE}]).clear()  # retains columns, 0 rows
        assert df.height == 0 and "office_phone" in df.columns
        with pytest.raises(EvaluationRefusedError, match="empty"):
            assert_frame_readable(df)


# ---------------------------------------------------------------------------
# Roster predicate: terminal override + case-insensitive classify
# ---------------------------------------------------------------------------


class TestRosterPredicate:
    def test_is_completed_terminal_override_excludes_active_row(self) -> None:
        """SD-6: an ACTIVE-section offer that is is_completed=True is NOT on the roster."""
        df = _offer_df(
            [
                {"office_phone": GREEN_PHONE, "section": "ACTIVE", "is_completed": True},
            ]
        )
        assert active_roster_phones(df) == frozenset()

    def test_activating_and_active_both_count_case_insensitive(self) -> None:
        df = _offer_df(
            [
                {"office_phone": "+1a", "section": "active"},  # lower-case
                {"office_phone": "+1b", "section": "ACTIVATING"},
                {"office_phone": "+1c", "section": "INACTIVE"},  # excluded
            ]
        )
        assert active_roster_phones(df) == frozenset({"+1a", "+1b"})

    def test_absent_from_frame_class_attribution(self) -> None:
        df = _offer_df([{"office_phone": RED_PHONE, "section": "INACTIVE"}])
        traffic = TrafficTally(
            phones=frozenset({RED_PHONE, ABSENT_PHONE}),
            bookings_by_phone={RED_PHONE: 155, ABSENT_PHONE: 29},
        )
        verdict = resolve_divergence(df, traffic)
        assert verdict.classes[RED_PHONE] == CLASS_INFRAME_INACTIVE
        assert verdict.classes[ABSENT_PHONE] == CLASS_ABSENT_FROM_FRAME
        assert verdict.class_counts[CLASS_INFRAME_INACTIVE] == 1
        assert verdict.class_counts[CLASS_ABSENT_FROM_FRAME] == 1

    def test_classify_helper_two_sided(self) -> None:
        present = frozenset({RED_PHONE})
        assert classify_divergent(RED_PHONE, present) == CLASS_INFRAME_INACTIVE
        assert classify_divergent(ABSENT_PHONE, present) == CLASS_ABSENT_FROM_FRAME


# ---------------------------------------------------------------------------
# Fast-burn delta + baseline-poisoning guard
# ---------------------------------------------------------------------------


class TestNewlyDivergentAndPoisoningGuard:
    def test_previously_matched_office_reads_as_newly_divergent(self) -> None:
        """A previously-clean office that just went divergent -> newly=1."""
        prior = {r7.phone_hash("+1oldalready")}  # baseline had ONE other divergent office
        newly, new_hashes = compute_newly_divergent(frozenset({RED_PHONE}), prior)
        assert newly == 1
        assert new_hashes == {r7.phone_hash(RED_PHONE)}

    def test_already_baselined_office_is_not_newly(self) -> None:
        prior = {r7.phone_hash(RED_PHONE)}
        newly, _ = compute_newly_divergent(frozenset({RED_PHONE}), prior)
        assert newly == 0

    def test_baseline_is_hashed_never_plaintext(self) -> None:
        _, new_hashes = compute_newly_divergent(frozenset({RED_PHONE}), set())
        assert RED_PHONE not in new_hashes
        assert new_hashes == {r7.phone_hash(RED_PHONE)}

    def test_refused_run_does_NOT_commit_baseline(self) -> None:
        """POISONING GUARD: a refused run must not overwrite the baseline (else the
        next run reads every office as newly-divergent and false-pages)."""
        committed: list[set[str]] = []

        def _load_stale() -> tuple[pl.DataFrame, float]:
            # Fresh returns, but the frame is stale by mtime -> refuse.
            return _offer_df([{"office_phone": RED_PHONE, "section": "INACTIVE"}]), 1.0

        result = run_divergence_evaluation(
            gate=lambda: True,
            load_frame=_load_stale,
            gather_traffic=lambda: TrafficTally(frozenset({RED_PHONE}), {RED_PHONE: 1}),
            read_baseline=lambda: {r7.phone_hash("+1prior")},
            commit_baseline=committed.append,
            now_epoch=1_000_000.0,  # >> frame mtime 1.0 => stale => refuse
            ceiling_seconds=43200,
        )
        assert result.status == "refused"
        assert committed == []  # baseline untouched

    def test_evaluated_run_DOES_commit_baseline(self) -> None:
        committed: list[set[str]] = []
        now = 1_000_000.0
        result = run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (
                _offer_df([{"office_phone": RED_PHONE, "section": "INACTIVE"}]),
                now,
            ),
            gather_traffic=lambda: TrafficTally(frozenset({RED_PHONE}), {RED_PHONE: 1}),
            read_baseline=lambda: set(),
            commit_baseline=committed.append,
            now_epoch=now,
            ceiling_seconds=43200,
        )
        assert result.status == "evaluated"
        assert result.divergent_count == 1
        assert committed == [{r7.phone_hash(RED_PHONE)}]


# ---------------------------------------------------------------------------
# Emission: refused emits ONLY the refuse+heartbeat; evaluated emits the verdict
# ---------------------------------------------------------------------------


class TestEmission:
    @pytest.fixture
    def captured(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, str | None, Any]]:
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

    def test_refused_run_emits_refused_1_and_no_count(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (_offer_df([{"office_phone": RED_PHONE}]), 1.0),
            gather_traffic=lambda: TrafficTally(frozenset({RED_PHONE}), {RED_PHONE: 1}),
            read_baseline=lambda: set(),
            commit_baseline=lambda _h: None,
            now_epoch=1_000_000.0,  # stale => refuse
            ceiling_seconds=43200,
        )
        emitted = {m for (m, _v, _ns, _d) in captured}
        assert (METRIC_EVALUATION_REFUSED, 1) in {(m, v) for (m, v, _ns, _d) in captured}
        assert METRIC_LAST_RUN_EPOCH in emitted  # heartbeat present even on refuse
        assert METRIC_TRADING_COUNT not in emitted  # NO fabricated verdict
        assert METRIC_ROSTER_SIZE not in emitted

    def test_evaluated_run_emits_full_verdict_in_r7_namespace(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        now = 1_000_000.0
        run_divergence_evaluation(
            gate=lambda: True,
            load_frame=lambda: (
                _offer_df(
                    [
                        {"office_phone": RED_PHONE, "section": "INACTIVE"},
                        {"office_phone": GREEN_PHONE, "section": "ACTIVE"},
                    ]
                ),
                now,
            ),
            gather_traffic=lambda: TrafficTally(
                frozenset({RED_PHONE, GREEN_PHONE}), {RED_PHONE: 155, GREEN_PHONE: 40}
            ),
            read_baseline=lambda: set(),
            commit_baseline=lambda _h: None,
            now_epoch=now,
            ceiling_seconds=43200,
        )
        by_metric = {m: (v, ns) for (m, v, ns, _d) in captured}
        assert by_metric[METRIC_TRADING_COUNT] == (1, METRIC_NAMESPACE)  # only RED counts
        assert by_metric[METRIC_ROSTER_SIZE] == (1, METRIC_NAMESPACE)  # GREEN is the roster
        assert by_metric[METRIC_EVALUATION_REFUSED] == (0, METRIC_NAMESPACE)  # real 0
        # EVERY emitted metric rides the byte-exact R7 namespace (the alarm contract).
        assert all(ns == METRIC_NAMESPACE for (_m, _v, ns, _d) in captured)

    def test_gate_off_emits_heartbeat_only(
        self, captured: list[tuple[str, float, str | None, Any]]
    ) -> None:
        """DEFAULT-DARK: gate off -> skipped, LastRunEpoch heartbeat still emitted so the
        dead-man tracks invocation (honest 'alive but intentionally dark')."""
        result = run_divergence_evaluation(
            gate=lambda: False,
            load_frame=lambda: pytest.fail("load_frame must NOT run when DARK"),  # type: ignore[arg-type,return-value]
            gather_traffic=lambda: pytest.fail("gather must NOT run when DARK"),  # type: ignore[return-value]
            read_baseline=lambda: pytest.fail("baseline must NOT run when DARK"),  # type: ignore[return-value]
            commit_baseline=lambda _h: pytest.fail("commit must NOT run when DARK"),
            now_epoch=1_000_000.0,
            ceiling_seconds=43200,
        )
        assert result.status == "skipped"
        emitted = {m for (m, _v, _ns, _d) in captured}
        assert emitted == {METRIC_LAST_RUN_EPOCH}


# ---------------------------------------------------------------------------
# ★ Anti-blind-instrument: the query selects the RIGHT events, NEVER gate_rejected
# ---------------------------------------------------------------------------


class TestQueryEventVocabulary:
    def test_ebi_query_selects_guid_resolved_events(self) -> None:
        q = build_ebi_query(7)
        for ev in EBI_RESOLVE_EVENTS:
            assert f'event = "{ev}"' in q
        assert "office_phone" in q

    def test_scheduling_query_selects_booking_success(self) -> None:
        q = build_scheduling_query(7)
        assert f'event = "{SCHEDULING_BOOKING_EVENT}"' in q
        assert "extra.office_phone" in q

    def test_no_query_selects_the_R1_gate_event(self) -> None:
        """The sharpest tooth: neither traffic query may select scheduling_gate_rejected
        (that would conflate R7 with the R1 intent-vs-gate instrument, spec §1)."""
        assert SCHEDULING_R1_GATE_EVENT_EXCLUDED == "scheduling_gate_rejected"
        assert SCHEDULING_R1_GATE_EVENT_EXCLUDED not in build_ebi_query(7)
        assert SCHEDULING_R1_GATE_EVENT_EXCLUDED not in build_scheduling_query(7)

    def test_typod_event_would_be_caught_RED(self) -> None:
        """RED control: a query built on a MISSPELLED event must NOT match the real
        vocabulary (else the GREEN assertions above are vacuous)."""
        typo = 'filter event = "booking_succes"'
        assert f'event = "{SCHEDULING_BOOKING_EVENT}"' not in typo


# ---------------------------------------------------------------------------
# ★ Cross-repo emit<->alarm contract pin (byte-exact; a rename trips CI)
# ---------------------------------------------------------------------------


class TestCrossRepoContract:
    def test_namespace_is_the_frozen_contract(self) -> None:
        assert METRIC_NAMESPACE == "Autom8y/AsanaOfferDivergence"

    def test_alarm_bound_metric_names_are_frozen(self) -> None:
        assert (
            frozenset(
                {
                    "TradingWithoutActiveOfferCount",
                    "NewlyTradingWithoutActiveOfferCount",
                    "ActiveOfferRosterSize",
                    "EvaluationRefused",
                    "LastRunEpoch",
                }
            )
            == r7.ALARM_BOUND_METRICS
        )
        # The constants and the literals must agree (the terraform half quotes the literals).
        assert METRIC_TRADING_COUNT == "TradingWithoutActiveOfferCount"
        assert METRIC_NEWLY_TRADING == "NewlyTradingWithoutActiveOfferCount"
        assert METRIC_ROSTER_SIZE == "ActiveOfferRosterSize"
        assert METRIC_EVALUATION_REFUSED == "EvaluationRefused"
        assert METRIC_LAST_RUN_EPOCH == "LastRunEpoch"


# ---------------------------------------------------------------------------
# ★ Canary-sentinel exclusion -- two-sided teeth on the divergence NUMERATOR
#
# The canary tenant is seeded with no offer row, so its reserved phone is absent
# from the roster BY CONSTRUCTION while canary cycles log traffic for it. Both
# traffic queries must exclude it or a synthetic office scores DIVERGENT forever.
# Ruled: autom8y repo `.ledge/decisions/ADR-resolve-cure-F1-canary-vertical-2026-08-08.md`
# § "Denominator-leak check" (b). Precedent: autom8y repo
# `terraform/services/auth/token_exchange_alarms.tf:172-183`.
# ---------------------------------------------------------------------------

#: Matches ONE Logs Insights ``| filter <field> != "<literal>"`` stage.
_EXCLUSION_STAGE_RE = re.compile(r'^\|\s*filter\s+([A-Za-z0-9_.]+)\s*!=\s*"([^"]*)"$')


def _exclusion_stages(query: str) -> set[tuple[str, str]]:
    """Extract the inequality-exclusion stages ``(field, excluded_literal)`` from a query.

    DELIBERATELY PARTIAL -- it models ONLY the exclusion stage under test. Any stage it
    does not recognize simply contributes no exclusion, so this reader can only ever be
    MORE permissive than CloudWatch, never less. That one-sided error is what makes the
    RED arm below a genuine leak proof rather than a simulator artifact: if the reader
    is wrong, it fails toward "the row survives", i.e. toward FAILING the cured query.
    """
    return {
        (m.group(1), m.group(2))
        for m in (_EXCLUSION_STAGE_RE.match(line.strip()) for line in query.splitlines())
        if m is not None
    }


def _phone_survives(query: str, office_phone: str) -> bool:
    """True iff a row carrying ``office_phone`` survives the query's exclusion stages."""
    return all(
        excluded != office_phone
        for field, excluded in _exclusion_stages(query)
        if field == "office_phone"
    )


def _strip_the_clause(query: str) -> str:
    """The PRE-CURE query: the built query with the exclusion stage removed.

    The count assertion is the mutation ANCHOR -- without it a reformat that changed the
    clause text would make the strip a silent no-op and this file would report a false
    GREEN on the RED arm (proving only that the probe missed).
    """
    assert query.count(CANARY_SENTINEL_EXCLUSION_CLAUSE) == 1
    mutated = query.replace(CANARY_SENTINEL_EXCLUSION_CLAUSE + "\n", "", 1)
    assert mutated != query
    assert CANARY_SENTINEL_EXCLUSION_CLAUSE not in mutated
    return mutated


class TestCanarySentinelExclusion:
    def test_sentinel_literal_is_the_reserved_canary_phone(self) -> None:
        """Byte-exact pin: this is the phone the canary seed writes (E.164)."""
        assert CANARY_SENTINEL_PHONE == "+15550000000"

    def test_clause_is_derived_from_the_constant(self) -> None:
        """One source of truth -- the clause is built FROM the sentinel, not retyped."""
        derived = f'| filter office_phone != "{CANARY_SENTINEL_PHONE}"'
        assert derived == CANARY_SENTINEL_EXCLUSION_CLAUSE

    def test_both_traffic_queries_carry_the_exclusion(self) -> None:
        """traffic(O,W) is a UNION -- an exclusion on one leg only still leaks."""
        for query in (build_ebi_query(7), build_scheduling_query(7)):
            assert query.count(CANARY_SENTINEL_EXCLUSION_CLAUSE) == 1

    def test_exclusion_is_a_filter_stage_not_a_comment(self) -> None:
        """It must sit IN the filter chain, before ``| stats`` -- a ``#`` comment filters
        nothing, and a stage after the aggregation would never see the raw rows."""
        for query in (build_ebi_query(7), build_scheduling_query(7)):
            lines = [line.strip() for line in query.splitlines()]
            idx = lines.index(CANARY_SENTINEL_EXCLUSION_CLAUSE)
            stats_idx = next(i for i, line in enumerate(lines) if line.startswith("| stats"))
            assert lines[idx].startswith("| filter")
            assert not lines[idx].startswith("#")
            assert idx < stats_idx
            # The reader agrees it is a real exclusion stage (not just a matching string).
            assert ("office_phone", CANARY_SENTINEL_PHONE) in _exclusion_stages(query)

    def test_scheduling_clause_binds_the_ALIASED_field(self) -> None:
        """The scheduling leg reads ``extra.office_phone``; the alias must precede the
        clause or the exclusion would bind a field that does not exist on that leg."""
        lines = [line.strip() for line in build_scheduling_query(7).splitlines()]
        alias_idx = next(
            i for i, line in enumerate(lines) if "extra.office_phone as office_phone" in line
        )
        assert alias_idx < lines.index(CANARY_SENTINEL_EXCLUSION_CLAUSE)

    def test_RED_the_pre_cure_query_would_admit_a_sentinel_row(self) -> None:
        """★ The mutation arm. Strip the clause (the exact pre-cure shape at origin/main)
        and a sentinel-shaped row SURVIVES -- that surviving row is the +1 on
        TradingWithoutActiveOfferCount the cure exists to prevent."""
        for query in (build_ebi_query(7), build_scheduling_query(7)):
            pre_cure = _strip_the_clause(query)
            assert _phone_survives(pre_cure, CANARY_SENTINEL_PHONE) is True  # the LEAK
            assert _phone_survives(query, CANARY_SENTINEL_PHONE) is False  # cured

    def test_GREEN_real_offices_still_survive_the_exclusion(self) -> None:
        """The complement: the exclusion must not be over-broad. Real offices -- including
        the RED/absent divergence exemplars this instrument exists to catch -- pass."""
        for query in (build_ebi_query(7), build_scheduling_query(7)):
            for phone in (RED_PHONE, GREEN_PHONE, R1_PHONE, ABSENT_PHONE):
                assert _phone_survives(query, phone) is True

    def test_exclusion_is_EXACT_match_never_a_prefix(self) -> None:
        """A prefix/wildcard exclusion could swallow a real office. Near-misses survive."""
        near_misses = (
            CANARY_SENTINEL_PHONE + "1",  # longer
            CANARY_SENTINEL_PHONE[:-1],  # shorter
            "15550000000",  # unprefixed
        )
        for query in (build_ebi_query(7), build_scheduling_query(7)):
            for phone in near_misses:
                assert _phone_survives(query, phone) is True

    def test_an_unexcluded_sentinel_scores_DIVERGENT_absent_from_frame(self) -> None:
        """Grounds the consequence in the REAL predicate, not prose: run the sentinel
        through resolve_divergence against a roster that (correctly) has no offer row
        for it -- it lands +1 divergent, class absent_from_frame. That is exactly the
        numerator poisoning the query-level exclusion prevents upstream."""
        df = _offer_df([{"office_phone": GREEN_PHONE, "section": "ACTIVE"}])
        leaked = TrafficTally(
            phones=frozenset({CANARY_SENTINEL_PHONE}),
            bookings_by_phone={CANARY_SENTINEL_PHONE: 1},
        )
        verdict = resolve_divergence(df, leaked)
        assert verdict.divergent_phones == frozenset({CANARY_SENTINEL_PHONE})
        assert verdict.classes[CANARY_SENTINEL_PHONE] == CLASS_ABSENT_FROM_FRAME
        assert verdict.class_counts[CLASS_ABSENT_FROM_FRAME] == 1

        # And the cured path: the sentinel never reaches the tally at all.
        clean = TrafficTally(phones=frozenset({GREEN_PHONE}), bookings_by_phone={GREEN_PHONE: 1})
        assert resolve_divergence(df, clean).divergent_phones == frozenset()
