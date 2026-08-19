"""Derivation-level tests for the WIRE verification axis (compute_serve_verification).

The quantity under test is "how long since these rows were confirmed against the
live source", folded over the REQUEST's resolved section set. It is a different
quantity from ``compute_verification_age`` (the ADR-006 metrics-CLI SLI), and the
two must never be interchanged even though they share one fold.

Two canaries live here. Both are deliberately-broken **INPUTS** that a correct
surface handles correctly — no production code is edited to make either fire:

  CAN-A  a genuinely halted warmer: every in-scope section stamped, but stamped
         LONG ago. The axis derives and the number crosses the gate bar.
         Two-sided: the same fixture with recent stamps stays under the bar.

  CAN-B  a never-probed section: ``last_verified_at`` absent, ``written_at``
         fresh. The axis REFUSES (null + backfill flag) rather than reading the
         write clock as a verification instant.
         Two-sided: the same fixture with the stamp present derives normally.

CAN-A is the halted-warmer tooth; CAN-B is the backfill refusal. They exercise
different mechanisms and neither substitutes for the other.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)
from autom8_asana.metrics.freshness import (
    ServeVerification,
    compute_serve_verification,
    compute_verification_age,
)

# The production offers gate bar. Spelled as a literal, not imported: this test
# asserts a wire-visible number crosses a threshold another repo owns, and an
# import would silently follow that threshold if it moved.
_GATE_BAR_SECONDS = 3600.0

_NOW = datetime(2026, 8, 19, 15, 0, 0, tzinfo=UTC)


def _section(
    name: str,
    *,
    last_verified_at: datetime | None = None,
    written_at: datetime | None = None,
    rows: int = 5,
) -> SectionInfo:
    return SectionInfo(
        status=SectionStatus.COMPLETE,
        rows=rows,
        name=name,
        written_at=written_at,
        last_verified_at=last_verified_at,
    )


def _manifest(sections: dict[str, SectionInfo]) -> SectionManifest:
    return SectionManifest(
        project_gid="1143843662099250",
        entity_type="offer",
        sections=sections,
        total_sections=len(sections),
        completed_sections=len(sections),
        schema_version="1.6.0",
    )


class TestCanaryAHaltedWarmer:
    """CAN-A — the halted-warmer RED, two-sided.

    A halted warmer does NOT remove stamps: no probe runs, so
    ``min(last_verified_at)`` simply stops advancing and the age climbs. This
    is the tooth the whole cure rests on, and it is a different code path from
    a missing stamp (which routes through AXIS-NULL).

    The gate decision itself lives in the consumer. What the producer leg owns
    — and what this canary proves — is that a halted warmer makes the EMITTED
    number cross the bar while a healthy warmer keeps it well under.
    """

    _SCOPE = frozenset({"active", "staging"})

    def _fixture(self, age_seconds: float) -> SectionManifest:
        stamp = _NOW - timedelta(seconds=age_seconds)
        return _manifest(
            {
                "g1": _section("ACTIVE", last_verified_at=stamp),
                "g2": _section("STAGING", last_verified_at=stamp),
            }
        )

    def test_can_a_red_arm_halted_warmer_crosses_the_bar(self) -> None:
        """RED: stamps present but 7200s old -> axis derives, number is over the bar."""
        result = compute_serve_verification(
            manifest=self._fixture(7200.0),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.derivable is True, "a halted warmer still has stamps; the axis derives"
        assert result.verification_age_seconds == pytest.approx(7200.0)
        assert result.verification_age_seconds > _GATE_BAR_SECONDS
        assert result.verification_backfill_used is False

    def test_can_a_green_arm_healthy_warmer_stays_under_the_bar(self) -> None:
        """GREEN: the SAME fixture at 600s -> under the bar. One arm is not a proof."""
        result = compute_serve_verification(
            manifest=self._fixture(600.0),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.derivable is True
        assert result.verification_age_seconds == pytest.approx(600.0)
        assert result.verification_age_seconds < _GATE_BAR_SECONDS
        assert result.verification_backfill_used is False

    def test_can_a_oldest_section_sets_the_number_not_the_freshest(self) -> None:
        """A partial halt is caught: one stale section drags the fold, MIN not MAX.

        This is the property that makes the axis conservative. A fold that took
        the freshest stamp would report GREEN on a pool where one section has
        not been probed for two hours.
        """
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=7200)),
                    "g2": _section("STAGING", last_verified_at=_NOW - timedelta(seconds=60)),
                }
            ),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.verification_age_seconds == pytest.approx(7200.0)
        assert result.verification_age_seconds > _GATE_BAR_SECONDS


class TestCanaryBBackfillRefusal:
    """CAN-B — ``written_at`` never enters the fold, two-sided.

    ``written_at`` is a write clock: a zero-fetch warm advances it. Reading it
    as a verification instant would report a never-probed section as verified
    seconds ago — the exact false-GREEN the axis exists to prevent. The
    contract names ``written_at`` verbatim in the forbidden-source list.
    """

    _SCOPE = frozenset({"active", "staging"})

    def test_can_b_red_arm_missing_stamp_refuses_despite_fresh_written_at(self) -> None:
        """RED: one section unstamped with a 1-second-old write clock -> AXIS-NULL."""
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=600)),
                    "g2": _section(
                        "STAGING",
                        last_verified_at=None,
                        written_at=_NOW - timedelta(seconds=1),
                    ),
                }
            ),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.verified_at is None
        assert result.verification_age_seconds is None, (
            "a fresh write clock must not become a fresh verification age"
        )
        assert result.verification_backfill_used is True
        assert result.refusal_reason == ServeVerification.REASON_UNSTAMPED_SECTIONS

    def test_can_b_green_arm_same_fixture_with_the_stamp_present_derives(self) -> None:
        """GREEN: the SAME shape with a real stamp on g2 -> derives normally."""
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=600)),
                    "g2": _section(
                        "STAGING",
                        last_verified_at=_NOW - timedelta(seconds=300),
                        written_at=_NOW - timedelta(seconds=1),
                    ),
                }
            ),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.derivable is True
        assert result.verification_age_seconds == pytest.approx(600.0)
        assert result.verification_backfill_used is False

    def test_can_b_all_unstamped_with_fresh_write_clocks_still_refuses(self) -> None:
        """Every section unstamped, every write clock fresh -> still null, never 0s."""
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", written_at=_NOW),
                    "g2": _section("STAGING", written_at=_NOW),
                }
            ),
            section_names=self._SCOPE,
            now=_NOW,
        )

        assert result.verified_at is None
        assert result.verification_age_seconds is None
        assert result.verification_backfill_used is True

    def test_the_two_policies_diverge_on_the_identical_manifest(self) -> None:
        """The discriminating proof: same input, CLI backfills, wire refuses.

        This is what "one fold, two policies" has to mean. If a future edit
        collapsed the policies, one of these two assertions would break — and
        the dangerous direction (the wire inheriting the CLI's backfill) breaks
        the second one loudly rather than shipping a false-GREEN number.
        """
        manifest = _manifest({"g1": _section("ACTIVE", written_at=_NOW)})

        cli = compute_verification_age(
            manifest=manifest,
            entity_type="offer",
            threshold_seconds=3600,
            now=_NOW,
        )
        wire = compute_serve_verification(
            manifest=manifest,
            section_names=frozenset({"active"}),
            now=_NOW,
        )

        assert cli.available is True, "the CLI's ruled Decision-6 backfill is unchanged"
        assert cli.backfill_used is True
        assert cli.max_age_seconds == 0

        assert wire.verified_at is None, "the wire never substitutes the write clock"
        assert wire.verification_age_seconds is None
        assert wire.verification_backfill_used is True


class TestGrainIsTheRequestResolvedSet:
    """The divergent-stamp grain fixture, in TWO variants.

    Every stamp in production today carries an identical instant, because one
    ``now`` is taken for a whole warm pass. So ``active``, ``activating``,
    their union, and the whole manifest all yield the SAME number live — a
    wrong grain is numerically invisible in production and stays invisible
    until a partial warm failure. Only a fixture with divergent per-pool stamps
    can discriminate the grain, and it needs both directions: a single variant
    cannot tell a correct fold from one that always returns the union's min.
    """

    _ACTIVE = frozenset({"active", "staging"})
    _ACTIVATING = frozenset({"activating", "launch error"})

    @staticmethod
    def _divergent(active_age: float, activating_age: float) -> SectionManifest:
        return _manifest(
            {
                "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=active_age)),
                "g2": _section("STAGING", last_verified_at=_NOW - timedelta(seconds=active_age)),
                "g3": _section(
                    "ACTIVATING", last_verified_at=_NOW - timedelta(seconds=activating_age)
                ),
                "g4": _section(
                    "LAUNCH ERROR", last_verified_at=_NOW - timedelta(seconds=activating_age)
                ),
                # In the manifest, in NEITHER requested classification. Must not
                # enter either fold — it is not in either response's bytes.
                "g5": _section("COMPLETE", last_verified_at=_NOW - timedelta(seconds=99999)),
            }
        )

    def test_variant_1_active_pool_older(self) -> None:
        """ACTIVE at 5000s, ACTIVATING at 100s: each request gets its OWN min."""
        manifest = self._divergent(active_age=5000.0, activating_age=100.0)

        active = compute_serve_verification(manifest=manifest, section_names=self._ACTIVE, now=_NOW)
        activating = compute_serve_verification(
            manifest=manifest, section_names=self._ACTIVATING, now=_NOW
        )

        assert active.verification_age_seconds == pytest.approx(5000.0)
        assert activating.verification_age_seconds == pytest.approx(100.0)
        assert active.verification_age_seconds != activating.verification_age_seconds

    def test_variant_2_activating_pool_older(self) -> None:
        """The INVERSE: ACTIVATING at 5000s, ACTIVE at 100s.

        A fold hardcoded to the billable union would answer 5000.0 to BOTH
        requests here and 5000.0 to both in variant 1 — right by coincidence in
        one direction only. Running both directions is what closes that.
        """
        manifest = self._divergent(active_age=100.0, activating_age=5000.0)

        active = compute_serve_verification(manifest=manifest, section_names=self._ACTIVE, now=_NOW)
        activating = compute_serve_verification(
            manifest=manifest, section_names=self._ACTIVATING, now=_NOW
        )

        assert active.verification_age_seconds == pytest.approx(100.0)
        assert activating.verification_age_seconds == pytest.approx(5000.0)

    def test_out_of_scope_sections_never_enter_the_fold(self) -> None:
        """The 99999s COMPLETE section is in the manifest and in neither response."""
        manifest = self._divergent(active_age=100.0, activating_age=200.0)

        active = compute_serve_verification(manifest=manifest, section_names=self._ACTIVE, now=_NOW)

        assert active.verification_age_seconds == pytest.approx(100.0)
        assert active.in_scope_count == 2

    def test_consumer_combination_reconstitutes_the_billable_grain(self) -> None:
        """max(age_active, age_activating) == the union's min, on both variants.

        The billable grain the contract requires is assembled at the consumer
        from two co-sourcing-correct legs, never hardcoded at the producer.
        """
        for active_age, activating_age in ((5000.0, 100.0), (100.0, 5000.0)):
            manifest = self._divergent(active_age=active_age, activating_age=activating_age)
            active = compute_serve_verification(
                manifest=manifest, section_names=self._ACTIVE, now=_NOW
            )
            activating = compute_serve_verification(
                manifest=manifest, section_names=self._ACTIVATING, now=_NOW
            )
            union = compute_serve_verification(
                manifest=manifest,
                section_names=self._ACTIVE | self._ACTIVATING,
                now=_NOW,
            )

            assert active.verification_age_seconds is not None
            assert activating.verification_age_seconds is not None
            combined = max(active.verification_age_seconds, activating.verification_age_seconds)
            assert combined == pytest.approx(union.verification_age_seconds)


class TestMissingMeansAbsentOrUnstamped:
    """An in-scope section the manifest does not carry at all is `missing`.

    The manifest-side iteration cannot see this state — only subtracting the
    matched names from the requested set can. A fold that iterated the manifest
    alone would silently narrow the denominator and report GREEN over whichever
    sections happened to be present.
    """

    def test_section_absent_from_the_manifest_is_missing(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest(
                {"g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=60))}
            ),
            section_names=frozenset({"active", "staging"}),
            now=_NOW,
        )

        assert result.verified_at is None
        assert result.verification_backfill_used is True
        assert result.missing_count == 1
        assert result.in_scope_count == 2, "the absent section stays in the denominator"

    def test_full_coverage_derives(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=60)),
                    "g2": _section("STAGING", last_verified_at=_NOW - timedelta(seconds=90)),
                }
            ),
            section_names=frozenset({"active", "staging"}),
            now=_NOW,
        )

        assert result.derivable is True
        assert result.missing_count == 0
        assert result.in_scope_count == 2

    def test_join_is_case_insensitive(self) -> None:
        """Manifest names are ALL CAPS; the resolved classification set is lower."""
        result = compute_serve_verification(
            manifest=_manifest({"g1": _section("OPTIMIZE - Human Review", last_verified_at=_NOW)}),
            section_names=frozenset({"optimize - human review"}),
            now=_NOW,
        )

        assert result.derivable is True


class TestUndecidableStates:
    """AXIS-NULL states that are not a backfill claim."""

    def test_manifest_unavailable(self) -> None:
        result = compute_serve_verification(manifest=None, section_names=frozenset({"active"}))

        assert result.verified_at is None
        assert result.verification_age_seconds is None
        assert result.verification_backfill_used is None, (
            "no section was inspected; claiming 'no backfill used' would overstate"
        )
        assert result.refusal_reason == ServeVerification.REASON_MANIFEST_UNAVAILABLE

    def test_empty_requested_scope(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest({"g1": _section("ACTIVE", last_verified_at=_NOW)}),
            section_names=frozenset(),
            now=_NOW,
        )

        assert result.verified_at is None
        assert result.verification_backfill_used is None
        assert result.refusal_reason == ServeVerification.REASON_EMPTY_SCOPE

    def test_empty_manifest_on_the_whole_frame_path(self) -> None:
        result = compute_serve_verification(manifest=_manifest({}), section_names=None, now=_NOW)

        assert result.verified_at is None
        assert result.refusal_reason == ServeVerification.REASON_EMPTY_SCOPE

    def test_no_path_emits_zero_for_an_underivable_axis(self) -> None:
        """An unprovable axis is never a number, and never the freshest number.

        The metrics CLI's ``unavailable()`` sentinel returns ``max_age_seconds=0``
        with ``available=False``; a consumer that read the number without first
        reading the flag would see maximally fresh. The wire shape has no such
        trapdoor: the value itself is null.
        """
        for manifest, names in (
            (None, frozenset({"active"})),
            (_manifest({}), None),
            (_manifest({"g1": _section("ACTIVE", written_at=_NOW)}), frozenset({"active"})),
        ):
            result = compute_serve_verification(manifest=manifest, section_names=names, now=_NOW)
            assert result.verification_age_seconds is None
            assert result.verification_age_seconds != 0


class TestWholeFrameScope:
    """``classification is None`` scopes to every section in the manifest."""

    def test_whole_frame_folds_all_named_sections(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=100)),
                    "g2": _section("COMPLETE", last_verified_at=_NOW - timedelta(seconds=900)),
                }
            ),
            section_names=None,
            now=_NOW,
        )

        assert result.verification_age_seconds == pytest.approx(900.0)
        assert result.in_scope_count == 2

    def test_whole_frame_null_named_entry_is_unprovable_not_invisible(self) -> None:
        """A null-named manifest entry is in the frame and cannot be proven verified."""
        result = compute_serve_verification(
            manifest=_manifest(
                {
                    "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=100)),
                    "g2": SectionInfo(status=SectionStatus.COMPLETE, name=None),
                }
            ),
            section_names=None,
            now=_NOW,
        )

        assert result.verified_at is None
        assert result.verification_backfill_used is True
        assert result.in_scope_count == 2


class TestClockSkewIsUnclamped:
    """A future-dated stamp is disclosed as a negative age, never clamped to 0."""

    def test_negative_age_is_carried(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest(
                {"g1": _section("ACTIVE", last_verified_at=_NOW + timedelta(seconds=300))}
            ),
            section_names=frozenset({"active"}),
            now=_NOW,
        )

        assert result.verification_age_seconds == pytest.approx(-300.0)
        assert result.verification_age_seconds < 0, (
            "clamping to 0 would make a defective stamp read as maximally fresh"
        )

    def test_the_cli_still_clamps(self) -> None:
        """The CLI's clamp is a ruled behaviour and is NOT changed by this work."""
        cli = compute_verification_age(
            manifest=_manifest(
                {"g1": _section("ACTIVE", last_verified_at=_NOW + timedelta(seconds=300))}
            ),
            entity_type="offer",
            threshold_seconds=3600,
            now=_NOW,
        )

        assert cli.max_age_seconds == 0


class TestVerifiedAtIsAnIsoInstant:
    def test_verified_at_round_trips(self) -> None:
        stamp = _NOW - timedelta(seconds=1132, microseconds=400000)
        result = compute_serve_verification(
            manifest=_manifest({"g1": _section("ACTIVE", last_verified_at=stamp)}),
            section_names=frozenset({"active"}),
            now=_NOW,
        )

        assert result.verified_at is not None
        assert datetime.fromisoformat(result.verified_at) == stamp
        assert result.verification_age_seconds == pytest.approx(1132.4)

    def test_backfill_flag_is_never_true_alongside_a_value(self) -> None:
        result = compute_serve_verification(
            manifest=_manifest({"g1": _section("ACTIVE", last_verified_at=_NOW)}),
            section_names=frozenset({"active"}),
            now=_NOW,
        )

        assert result.verified_at is not None
        assert result.verification_backfill_used is False
