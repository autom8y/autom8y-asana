"""Two-sided teeth for the WS-A pure enrollment-intent projection (PR-2).

The design contract (TDD-ws-a-intent-gate-bridge-2026-08-05 §3.1/§3.2/§3.3/§3.6):
the projection is the surface where the R1 policy and all four refusals live, so
its teeth must be TWO-SIDED everywhere -- each guard RED on its broken input AND
GREEN on the healthy variant. A one-sided proof (only the refusal) is
INSUFFICIENT: it cannot distinguish a guard that bites from a guard that bites
everything.

The four named risks this file is written against, each with its own class:
    R-12  universe-filter transposition (guid filter copied into a phone-keyed
          bridge) -- the single likeliest build-leg defect, because the adjacent
          producer module is right there to copy from.
    R-11  stamped-copy divergence on the roster join (sized, not assumed away).
    R-3   mass Asana wipe -> mass enable (the delta ceiling).
    R-9   mass silent enrollment from a dark intent source (schema-lag +
          freshness + universe floor).
Plus the R3 ROSTER WALL: an office outside active/activating must be
STRUCTURALLY ABSENT from the output, not merely skipped downstream.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import polars as pl
import pytest

from autom8_asana.enrollment.intent_projection import (
    ACTIVE_STATUS_ALIASES,
    INTENT_SOURCE_COERCED_UNSET,
    INTENT_SOURCE_EXPLICIT_DISABLED,
    INTENT_SOURCE_EXPLICIT_ENABLED,
    INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED,
    INTENT_SOURCES,
    REQUIRED_BUSINESS_COLUMNS,
    REQUIRED_OFFER_COLUMNS,
    REQUIRED_UNIT_HOLDER_COLUMNS,
    EnrollmentRefusedError,
    FrameSchemaLagError,
    assert_delta_within_ceiling,
    assert_frames_fresh,
    assert_intent_columns_present,
    assert_universe_floor,
    derive_intent_source,
    norm_phone,
    project_enrollment_intent,
)
from autom8_asana.normalizer.scheduling_extractor import (
    _INACTIVE_STATUS_ALIASES,
    derive_enrolled,
)

# Fixture phones. Each names the class it exists to prove.
PHONE_ENABLED = "+15550001111"  # explicit Enabled, guid present -- the healthy GREEN
PHONE_UNSET = "+15550002222"  # UNSET + guid NULL -- the R1 x R-12 compound case
PHONE_DISABLED = "+15550003333"  # explicit Inactive -- intent False, still projected
PHONE_SALES = "+15550004444"  # Sales Process -- the R3 WALL (must be ABSENT)
PHONE_ROSTER_ONLY = "+15550005555"  # on the roster, no spine row -- R-11 direction B
PHONE_PHONELESS = ""  # null/blank authoritative phone -- DROP

_T0 = dt.datetime(2026, 8, 1, 12, 0, 0)


# Explicit schemas so an EMPTY fixture still carries its columns -- otherwise a
# zero-row frame would trip the schema-lag gate and mask the case under test.
_UH_SCHEMA = {
    "gid": pl.Utf8,
    "parent_gid": pl.Utf8,
    "custom_cal_status": pl.Utf8,
    "last_modified": pl.Datetime,
}
_BIZ_SCHEMA = {"gid": pl.Utf8, "office_phone": pl.Utf8, "company_id": pl.Utf8}
_OFFER_SCHEMA = {"office_phone": pl.Utf8, "section": pl.Utf8, "is_completed": pl.Boolean}


def _uh_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build a unit_holder (INTENT) frame carrying the required columns."""
    complete = [
        {
            "gid": r.get("gid", f"uh{i}"),
            "parent_gid": r.get("parent_gid", f"b{i}"),
            "custom_cal_status": r.get("custom_cal_status"),
            "last_modified": r.get("last_modified", _T0),
        }
        for i, r in enumerate(rows)
    ]
    return pl.DataFrame(complete, schema=_UH_SCHEMA)


def _biz_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build a business (IDENTITY) frame -- the AUTHORITATIVE office_phone source."""
    complete = [
        {
            "gid": r.get("gid", f"b{i}"),
            "office_phone": r.get("office_phone"),
            "company_id": r.get("company_id"),
        }
        for i, r in enumerate(rows)
    ]
    return pl.DataFrame(complete, schema=_BIZ_SCHEMA)


def _offer_df(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """Build an offer (ROSTER) frame. ``company_id`` is deliberately absent -- the
    roster read must never depend on the guid-dark side of the offer frame."""
    complete = [
        {
            "office_phone": r.get("office_phone"),
            "section": r.get("section", "ACTIVE"),
            "is_completed": r.get("is_completed", False),
        }
        for r in rows
    ]
    return pl.DataFrame(complete, schema=_OFFER_SCHEMA)


def _healthy_frames() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """The canonical healthy fixture -- the GREEN side of every two-sided leg."""
    uh = _uh_df(
        [
            {"gid": "uh1", "parent_gid": "b1", "custom_cal_status": "Enabled"},
            {"gid": "uh2", "parent_gid": "b2", "custom_cal_status": None},
            {"gid": "uh3", "parent_gid": "b3", "custom_cal_status": "Inactive"},
            {"gid": "uh4", "parent_gid": "b4", "custom_cal_status": "Enabled"},
        ]
    )
    biz = _biz_df(
        [
            {"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "guid-1"},
            # ★ R-12 compound: guid NULL but phone present -- MUST survive.
            {"gid": "b2", "office_phone": PHONE_UNSET, "company_id": None},
            {"gid": "b3", "office_phone": PHONE_DISABLED, "company_id": "guid-3"},
            {"gid": "b4", "office_phone": PHONE_SALES, "company_id": "guid-4"},
        ]
    )
    offer = _offer_df(
        [
            {"office_phone": PHONE_ENABLED, "section": "ACTIVE"},
            {"office_phone": PHONE_UNSET, "section": "Activating"},
            {"office_phone": PHONE_DISABLED, "section": "ACTIVE"},
            {"office_phone": PHONE_SALES, "section": "Sales Process"},
            {"office_phone": PHONE_ROSTER_ONLY, "section": "ACTIVE"},
        ]
    )
    return uh, biz, offer


# ===========================================================================
# ★ R-12 -- company_id is a CROSS-CHECK, never a FILTER (two-sided)
# ===========================================================================


class TestR12UniverseFilterIsPhoneNotGuid:
    """The named build-leg defect: copying the WS-B producer's guid universe filter.

    The producer filters ``DISTINCT NON-NULL company_id`` because its substrate is
    guid-keyed. The gate is PHONE-keyed. Copying that filter silently inherits
    CARD WS-B/3 -- active offices whose Business ancestor has no ``Company ID``,
    invisible to the producer but perfectly reachable by a phone-keyed writer.
    """

    def test_SIDE_A_guid_less_phone_bearing_office_survives_projection(self) -> None:
        """RED-side: an in-scope office with company_id NULL is PROJECTED, not dropped."""
        uh, biz, offer = _healthy_frames()
        projection = project_enrollment_intent(uh, biz, offer)

        phones = {i.office_phone for i in projection.intents}
        assert PHONE_UNSET in phones, (
            "R-12 TRANSPOSITION: an office with office_phone present and "
            "company_id NULL was excluded. The bridge's universe is NON-NULL "
            "office_phone; company_id is a cross-check, never a filter. This is "
            "the producer's guid filter leaking into a phone-keyed writer."
        )
        (guidless,) = [i for i in projection.intents if i.office_phone == PHONE_UNSET]
        assert guidless.company_id is None
        assert projection.counts.guid_null_in_scope == 1

    def test_SIDE_B_guid_cross_check_emits_on_ambiguity_without_excluding(self) -> None:
        """GREEN-side: a phone mapping to >1 distinct guid is COUNTED, still enrolled.

        The cross-check must be observable (an identity ambiguity is real signal)
        AND non-excluding (refusing an office over a diagnostic would be the wrong
        fail-direction -- the guid is not the key).
        """
        uh = _uh_df(
            [
                {"gid": "uh1", "parent_gid": "b1", "custom_cal_status": "Enabled"},
                {"gid": "uh2", "parent_gid": "b2", "custom_cal_status": "Enabled"},
            ]
        )
        biz = _biz_df(
            [
                {"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "guid-A"},
                {"gid": "b2", "office_phone": PHONE_ENABLED, "company_id": "guid-B"},
            ]
        )
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        projection = project_enrollment_intent(uh, biz, offer)

        assert projection.counts.guid_ambiguous_phones == 1, (
            "a phone mapping to two distinct company_id values must be EMITTED as "
            "an identity cross-check failure"
        )
        assert [i.office_phone for i in projection.intents] == [PHONE_ENABLED], (
            "the ambiguity must not exclude the office -- the phone is the key"
        )

    def test_unambiguous_guid_does_not_false_fire_the_cross_check(self) -> None:
        """Non-vacuity: the cross-check counter is 0 on clean identity."""
        uh, biz, offer = _healthy_frames()
        assert project_enrollment_intent(uh, biz, offer).counts.guid_ambiguous_phones == 0


# ===========================================================================
# ★ R1 -- the ONE coercion point (two-sided)
# ===========================================================================


class TestR1CoercionPoint:
    def test_SIDE_A_unset_coerces_to_enabled_with_honest_provenance(self) -> None:
        """UNSET -> Enabled is ratified POLICY, and the receipt SAYS it was coerced."""
        uh, biz, offer = _healthy_frames()
        projection = project_enrollment_intent(uh, biz, offer)

        (unset,) = [i for i in projection.intents if i.office_phone == PHONE_UNSET]
        assert unset.intent_enabled is True
        assert unset.intent_raw is None
        assert unset.intent_source == INTENT_SOURCE_COERCED_UNSET, (
            "coerced_unset is what keeps silence-means-integrate auditable; a "
            "receipt claiming explicit_enabled here would launder the policy"
        )
        assert projection.counts.coerced_unset == 1

    def test_SIDE_B_explicit_disabled_stays_out(self) -> None:
        """An explicitly-Disabled office projects intent_enabled=False.

        It is still PROJECTED (never omitted) -- omission would leave the gate at
        whatever it happened to be, which is a silent enrollment state.
        """
        uh, biz, offer = _healthy_frames()
        projection = project_enrollment_intent(uh, biz, offer)

        (disabled,) = [i for i in projection.intents if i.office_phone == PHONE_DISABLED]
        assert disabled.intent_enabled is False
        assert disabled.intent_source == INTENT_SOURCE_EXPLICIT_DISABLED
        assert projection.counts.explicit_disabled == 1

    @pytest.mark.parametrize(
        "raw",
        [
            None,
            "",
            "   ",
            *sorted(_INACTIVE_STATUS_ALIASES),
            *sorted(ACTIVE_STATUS_ALIASES),
            "Enabled",
            "Inactive",
            "INACTIVE",
            "In-Active",
            "In Active",
            "Some Brand New Option",
            "pending",
        ],
    )
    def test_provenance_never_changes_the_bit(self, raw: str | None) -> None:
        """★ THE INVARIANT: intent_enabled is 100% derive_enrolled, for EVERY value.

        ``ACTIVE_STATUS_ALIASES`` exists only to split the True bit into
        explicit_enabled vs unknown_option_defaulted for the receipt. If it ever
        drifted into policy this test goes RED -- so the diagnostic vocabulary can
        never silently become a second definition of R1 (the exact failure the
        charter is written against).
        """
        uh = _uh_df([{"gid": "uh1", "parent_gid": "b1", "custom_cal_status": raw}])
        biz = _biz_df([{"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g"}])
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        (intent,) = project_enrollment_intent(uh, biz, offer).intents

        assert intent.intent_enabled is derive_enrolled(intent.intent_raw), (
            "the projected bit diverged from derive_enrolled -- R1 has been forked"
        )
        assert intent.intent_source in INTENT_SOURCES

    def test_blank_status_is_bit_identical_to_none(self) -> None:
        """Collapsing blank -> None is BIT-PRESERVING (both are True under R1).

        It only buys the honest ``coerced_unset`` label instead of a phantom
        explicit value; it must never change the gate outcome.
        """
        assert derive_enrolled(None) is derive_enrolled("")
        assert derive_intent_source("") == INTENT_SOURCE_COERCED_UNSET
        assert derive_intent_source("   ") == INTENT_SOURCE_COERCED_UNSET

    def test_unknown_option_is_labelled_not_silently_enabled(self) -> None:
        """An option nobody has seen defaults to Enabled per R1 -- and SAYS so."""
        assert derive_intent_source("Some Brand New Option") == (
            INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED
        )
        assert derive_enrolled("Some Brand New Option") is True

    def test_recognized_active_option_is_labelled_explicit(self) -> None:
        assert derive_intent_source("Enabled") == INTENT_SOURCE_EXPLICIT_ENABLED


# ===========================================================================
# ★ R3 ROSTER WALL -- out-of-roster offices are STRUCTURALLY ABSENT
# ===========================================================================


class TestRosterWall:
    def test_SIDE_A_sales_process_office_never_projects(self) -> None:
        """The R3 wall: a Sales-Process office is ABSENT from the output entirely.

        Not "skipped later", not "projected with a flag" -- absent. A bridge cannot
        write an office it never produced, which is what makes this structural
        rather than procedural.
        """
        uh, biz, offer = _healthy_frames()
        projection = project_enrollment_intent(uh, biz, offer)

        assert PHONE_SALES not in {i.office_phone for i in projection.intents}, (
            "an office outside active/activating entered the projection -- the R3 "
            "wall is procedural, not structural"
        )
        assert projection.counts.out_of_scope_phones == 1

    def test_SIDE_B_active_and_activating_both_project(self) -> None:
        """Non-vacuity: the wall admits the sections it is supposed to admit."""
        uh, biz, offer = _healthy_frames()
        phones = {i.office_phone for i in project_enrollment_intent(uh, biz, offer).intents}
        assert PHONE_ENABLED in phones  # section ACTIVE
        assert PHONE_UNSET in phones  # section Activating

    def test_completed_offer_is_terminal_override(self) -> None:
        """``is_completed=True`` removes an otherwise-ACTIVE row from the roster."""
        uh = _uh_df([{"gid": "uh1", "parent_gid": "b1", "custom_cal_status": "Enabled"}])
        biz = _biz_df([{"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g"}])

        live = _offer_df([{"office_phone": PHONE_ENABLED, "is_completed": False}])
        done = _offer_df([{"office_phone": PHONE_ENABLED, "is_completed": True}])

        assert len(project_enrollment_intent(uh, biz, live).intents) == 1
        assert len(project_enrollment_intent(uh, biz, done).intents) == 0


# ===========================================================================
# ★ R-11 -- stamped-copy divergence, SIZED in both directions
# ===========================================================================


class TestR11StampedCopyResidual:
    def test_roster_only_phone_is_counted_not_silently_dropped(self) -> None:
        """Direction B: an active-roster phone with no office-spine row is EMITTED.

        This is the silently-excluded set. A stale or missing downward phone stamp
        drops an office from the intersection; the count is what makes that
        visible before arming rather than discovered after.
        """
        uh, biz, offer = _healthy_frames()
        counts = project_enrollment_intent(uh, biz, offer).counts
        assert counts.roster_only_phones == 1, (
            "the roster-side residual must be sized -- PHONE_ROSTER_ONLY is on the "
            "active roster with no spine row"
        )

    def test_both_residual_directions_are_reported(self) -> None:
        """Direction A (spine ∖ roster) and B (roster ∖ spine) are separate counters."""
        uh, biz, offer = _healthy_frames()
        counts = project_enrollment_intent(uh, biz, offer).counts
        assert counts.out_of_scope_phones == 1
        assert counts.roster_only_phones == 1
        assert counts.in_scope_phones == 3
        assert counts.spine_phones == counts.in_scope_phones + counts.out_of_scope_phones
        assert counts.roster_phones == counts.in_scope_phones + counts.roster_only_phones


# ===========================================================================
# Phone authority + strip-only normalization (TDD §3.3)
# ===========================================================================


class TestPhoneAuthority:
    def test_write_key_comes_from_business_not_the_offer_stamp(self) -> None:
        """The AUTHORITATIVE phone wins. The offer frame is roster-membership only.

        Divergent-but-strip-equal values would join; here the offer stamp carries
        surrounding whitespace, which strip-only normalization folds -- proving the
        roster test is on the normalized copy while the emitted key is the
        Business-tier value.
        """
        uh = _uh_df([{"gid": "uh1", "parent_gid": "b1", "custom_cal_status": "Enabled"}])
        biz = _biz_df([{"gid": "b1", "office_phone": f"  {PHONE_ENABLED}  ", "company_id": "g"}])
        offer = _offer_df([{"office_phone": f"\t{PHONE_ENABLED}\n", "section": "ACTIVE"}])

        (intent,) = project_enrollment_intent(uh, biz, offer).intents
        assert intent.office_phone == PHONE_ENABLED

    def test_normalization_is_strip_only_never_e164_canonicalizing(self) -> None:
        """★ Punctuation must NOT be stripped: that would FALSE-JOIN distinct offices.

        A canonicalizing normalizer would collapse these three into one key and
        write one office's enrollment onto another's row.
        """
        assert norm_phone(" +1 (555) 000-1111 ") == "+1 (555) 000-1111"
        variants = {
            norm_phone("+15550001111"),
            norm_phone("(555) 000-1111"),
            norm_phone("555.000.1111"),
        }
        assert len(variants) == 3, (
            "phone normalization collapsed distinct spellings -- an over-normalizing "
            "join silently merges distinct offices"
        )

    def test_phoneless_spine_row_is_dropped_and_counted(self) -> None:
        """Null/blank authoritative phone -> DROP, counted. Fail SAFE by absence."""
        uh = _uh_df(
            [
                {"gid": "uh1", "parent_gid": "b1", "custom_cal_status": "Enabled"},
                {"gid": "uh2", "parent_gid": "b2", "custom_cal_status": "Enabled"},
            ]
        )
        biz = _biz_df(
            [
                {"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g1"},
                {"gid": "b2", "office_phone": PHONE_PHONELESS, "company_id": "g2"},
            ]
        )
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        projection = project_enrollment_intent(uh, biz, offer)
        assert projection.counts.phoneless_dropped == 1
        assert len(projection.intents) == 1


# ===========================================================================
# Deterministic representative + drift metering
# ===========================================================================


class TestRepresentativeAndDrift:
    def test_representative_is_max_last_modified_tie_broken_by_gid(self) -> None:
        """One deterministic row speaks for an office -- same rule as the producer."""
        uh = _uh_df(
            [
                {
                    "gid": "uh_old",
                    "parent_gid": "b1",
                    "custom_cal_status": "Inactive",
                    "last_modified": dt.datetime(2026, 1, 1),
                },
                {
                    "gid": "uh_new",
                    "parent_gid": "b1",
                    "custom_cal_status": "Enabled",
                    "last_modified": dt.datetime(2026, 8, 1),
                },
            ]
        )
        biz = _biz_df([{"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g"}])
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        (intent,) = project_enrollment_intent(uh, biz, offer).intents
        assert intent.unit_holder_gid == "uh_new"
        assert intent.intent_enabled is True

    def test_status_drift_is_metered_and_does_not_block_the_cycle(self) -> None:
        """Per-phone disagreement is DRIFT signal, not a refusal (producer policy)."""
        uh = _uh_df(
            [
                {"gid": "uh_a", "parent_gid": "b1", "custom_cal_status": "Enabled"},
                {"gid": "uh_b", "parent_gid": "b1", "custom_cal_status": "Inactive"},
            ]
        )
        biz = _biz_df([{"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g"}])
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        projection = project_enrollment_intent(uh, biz, offer)
        assert projection.counts.status_drift_phones == 1
        assert len(projection.intents) == 1

    def test_output_order_is_deterministic(self) -> None:
        """Byte-stable output on identical input (cycle-summary reconciliation)."""
        uh, biz, offer = _healthy_frames()
        first = [i.office_phone for i in project_enrollment_intent(uh, biz, offer).intents]
        second = [i.office_phone for i in project_enrollment_intent(uh, biz, offer).intents]
        assert first == second == sorted(first)


# ===========================================================================
# ★ THE FOUR REFUSAL PREDICATES -- each RED on its break, GREEN on health
# ===========================================================================


class TestSchemaLagRefusal:
    """R-9 layer 1. This is the leg that fires TODAY (unit_holder posture columns
    do not exist until WS-B PR-1 deploys AND one warmer cycle completes)."""

    @pytest.mark.parametrize("missing", REQUIRED_UNIT_HOLDER_COLUMNS)
    def test_RED_missing_intent_column_refuses(self, missing: str) -> None:
        uh, biz, offer = _healthy_frames()
        with pytest.raises(FrameSchemaLagError, match=f"unit_holder.{missing}"):
            project_enrollment_intent(uh.drop(missing), biz, offer)

    @pytest.mark.parametrize("missing", REQUIRED_BUSINESS_COLUMNS)
    def test_RED_missing_identity_column_refuses(self, missing: str) -> None:
        uh, biz, offer = _healthy_frames()
        with pytest.raises(FrameSchemaLagError, match=f"business.{missing}"):
            project_enrollment_intent(uh, biz.drop(missing), offer)

    @pytest.mark.parametrize("missing", REQUIRED_OFFER_COLUMNS)
    def test_RED_missing_roster_column_refuses(self, missing: str) -> None:
        uh, biz, offer = _healthy_frames()
        with pytest.raises(FrameSchemaLagError, match=f"offer.{missing}"):
            project_enrollment_intent(uh, biz, offer.drop(missing))

    def test_GREEN_complete_schema_projects(self) -> None:
        uh, biz, offer = _healthy_frames()
        assert project_enrollment_intent(uh, biz, offer).intents

    def test_absent_columns_refuse_rather_than_projecting_null_intent(self) -> None:
        """★ The load-bearing asymmetry: ABSENT refuses, NULL enrolls.

        Under the superseded frame contract the intent column was PRESENT-but-NULL,
        which R1 coerces to Enabled for every reachable office -- silent mass
        enrollment. Under this contract the column is ABSENT until WS-B lands, so
        the same premature run REFUSES loudly. Prove both halves so the
        improvement cannot be undone by a well-meaning ``fill_null``.
        """
        uh, biz, offer = _healthy_frames()

        with pytest.raises(FrameSchemaLagError):
            project_enrollment_intent(uh.drop("custom_cal_status"), biz, offer)

        all_null = uh.with_columns(pl.lit(None, dtype=pl.Utf8).alias("custom_cal_status"))
        projected = project_enrollment_intent(all_null, biz, offer)
        assert all(i.intent_enabled for i in projected.intents), (
            "documents the R1 consequence a null-bearing frame has -- which is "
            "exactly why the freshness + floor guards below are load-bearing"
        )
        assert projected.counts.coerced_unset == len(projected.intents)


class TestFreshnessRefusal:
    """R-9 layer 3a. Bound to the OFFICE SPINE -- all three frames, independently."""

    FRESH = 1_000_000.0
    NOW = 1_000_100.0
    CEILING = 3600.0

    def test_GREEN_all_three_frames_fresh_passes(self) -> None:
        assert_frames_fresh(
            [("unit_holder", self.FRESH), ("business", self.FRESH), ("offer", self.FRESH)],
            now_epoch=self.NOW,
            ceiling_seconds=self.CEILING,
        )

    @pytest.mark.parametrize("stale_frame", ["unit_holder", "business", "offer"])
    def test_RED_any_single_stale_frame_refuses_the_cycle(self, stale_frame: str) -> None:
        """A fresh offer frame says NOTHING about whether the intent source is fresh."""
        ages = [
            (name, self.NOW - 999_999.0 if name == stale_frame else self.FRESH)
            for name in ("unit_holder", "business", "offer")
        ]
        with pytest.raises(EnrollmentRefusedError, match=f"frame '{stale_frame}'"):
            assert_frames_fresh(ages, now_epoch=self.NOW, ceiling_seconds=self.CEILING)

    @pytest.mark.parametrize("unprovable_frame", ["unit_holder", "business", "offer"])
    def test_RED_unprovable_age_is_itself_a_refusal(self, unprovable_frame: str) -> None:
        """★ Absence of a timestamp must NOT read as fresh (the reused WS-E leg)."""
        ages = [
            (name, None if name == unprovable_frame else self.FRESH)
            for name in ("unit_holder", "business", "offer")
        ]
        with pytest.raises(EnrollmentRefusedError, match="unprovable"):
            assert_frames_fresh(ages, now_epoch=self.NOW, ceiling_seconds=self.CEILING)


class TestUniverseFloorRefusal:
    """R-9 layer 3b. The floor is baseline-relative and supplied, never defaulted."""

    def test_GREEN_universe_at_or_above_floor_passes(self) -> None:
        assert_universe_floor(475, floor=475)
        assert_universe_floor(900, floor=475)

    def test_RED_collapsed_universe_refuses(self) -> None:
        with pytest.raises(EnrollmentRefusedError, match="collapsed"):
            assert_universe_floor(44, floor=475)

    def test_RED_unset_floor_refuses_rather_than_running_unbounded(self) -> None:
        """★ A guessed floor is no floor -- absent fuel REFUSES, never defaults.

        MIN_POSTURE_SIGNAL_ROWS = 1 (the producer's floor) would pass the observed
        932 -> 1-44 collapse untouched. A zero/unset floor here must therefore be a
        refusal, not a permissive default.
        """
        with pytest.raises(EnrollmentRefusedError, match="unset or non-positive") as exc:
            assert_universe_floor(900, floor=0)
        # ★ The refusal must NAME the observed universe, so a dry-run against an
        # unset floor is the instrument that sizes it. A refusal that withholds the
        # number needed to fix it is a dead end.
        assert "900 phones" in str(exc.value)

    def test_a_one_row_floor_would_not_have_caught_the_observed_collapse(self) -> None:
        """Documents CARD WS-B/4 mechanically: why the producer's floor is decorative."""
        assert_universe_floor(44, floor=1)  # a 1-floor PASSES the collapse
        with pytest.raises(EnrollmentRefusedError):
            assert_universe_floor(44, floor=475)  # the derived floor CATCHES it


class TestDeltaCeilingRefusal:
    """R-3. The operator-direction brake: refuse WHOLE, never partially apply."""

    def test_GREEN_normal_delta_passes(self) -> None:
        assert_delta_within_ceiling(7, ceiling=25)
        assert_delta_within_ceiling(25, ceiling=25)

    def test_RED_mass_change_refuses_the_whole_cycle(self) -> None:
        with pytest.raises(EnrollmentRefusedError, match="delta ceiling tripped"):
            assert_delta_within_ceiling(26, ceiling=25)

    def test_RED_unset_ceiling_refuses(self) -> None:
        with pytest.raises(EnrollmentRefusedError, match="unset or non-positive") as exc:
            assert_delta_within_ceiling(7, ceiling=0)
        # Same discipline: the pre-arm dry-run reports the delta it would have made.
        assert "7 offices" in str(exc.value)

    def test_refusal_is_at_the_boundary_not_approximate(self) -> None:
        """Non-vacuity: the ceiling bites at exactly ceiling+1, not before."""
        assert_delta_within_ceiling(100, ceiling=100)
        with pytest.raises(EnrollmentRefusedError):
            assert_delta_within_ceiling(101, ceiling=100)


class TestRefusalGrammarIsReusedNotInvented:
    def test_enrollment_refusal_is_an_evaluation_refusal(self) -> None:
        """The WS-E ``EvaluationRefused`` grammar is REUSED, so one except clause
        at the bridge boundary covers both instruments' refusals."""
        from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
            EvaluationRefusedError,
        )

        assert issubclass(EnrollmentRefusedError, EvaluationRefusedError)

    def test_schema_lag_reuses_the_normalizer_exception_type(self) -> None:
        """Schema-lag is the normalizer's own exception type, not a parallel one."""
        from autom8_asana.normalizer.scheduling_extractor import (
            FrameSchemaLagError as NormalizerFrameSchemaLagError,
        )

        assert FrameSchemaLagError is NormalizerFrameSchemaLagError

    def test_required_column_tuples_are_exported_so_a_rename_trips_ci(self) -> None:
        """R-2 cross-repo frame-schema desync guard."""
        from autom8_asana.enrollment import intent_projection

        for name in (
            "REQUIRED_UNIT_HOLDER_COLUMNS",
            "REQUIRED_BUSINESS_COLUMNS",
            "REQUIRED_OFFER_COLUMNS",
        ):
            assert name in intent_projection.__all__


class TestFrameKeyContract:
    def test_frame_keys_are_derived_from_the_namespace_registry(self) -> None:
        """Keys are DERIVED (never hand-pinned) so the namespace contract holds."""
        from autom8_asana.enrollment.intent_projection import (
            BUSINESS_FRAME_KEY,
            OFFER_FRAME_KEY,
            UNIT_HOLDER_FRAME_KEY,
        )
        from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
            OFFER_FRAME_KEY as WS_E_OFFER_FRAME_KEY,
        )

        assert UNIT_HOLDER_FRAME_KEY.endswith("/1204433992667196/unit_holder/dataframe.parquet")
        assert BUSINESS_FRAME_KEY.endswith("/1200653012566782/business/dataframe.parquet")
        # ★ Byte-identical to the WS-E tripwire's key: both instruments read the
        # SAME warmed offer object. A divergence here would mean two instruments
        # disagreeing about the roster while both looked healthy.
        assert OFFER_FRAME_KEY == WS_E_OFFER_FRAME_KEY


class TestEmptyAndDegenerateFrames:
    def test_empty_spine_projects_nothing_and_reports_zero(self) -> None:
        """Empty is not a crash and not a fabricated verdict -- the floor guard is
        what turns a zero universe into a refusal at the bridge boundary."""
        uh = _uh_df([])
        biz = _biz_df([])
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        projection = project_enrollment_intent(uh, biz, offer)
        assert projection.intents == ()
        assert projection.counts.in_scope_phones == 0
        with pytest.raises(EnrollmentRefusedError):
            assert_universe_floor(projection.counts.in_scope_phones, floor=475)

    def test_orphan_unit_holder_without_a_business_ancestor_is_dropped(self) -> None:
        """An inner join on the office spine -- no ancestor, no identity, no write."""
        uh = _uh_df([{"gid": "uh1", "parent_gid": "b_missing", "custom_cal_status": "Enabled"}])
        biz = _biz_df([{"gid": "b1", "office_phone": PHONE_ENABLED, "company_id": "g"}])
        offer = _offer_df([{"office_phone": PHONE_ENABLED, "section": "ACTIVE"}])

        projection = project_enrollment_intent(uh, biz, offer)
        assert projection.intents == ()
        assert projection.counts.spine_rows == 0


class TestColumnPresenceGateIsIndependentOfData:
    def test_gate_operates_on_column_names_only(self) -> None:
        """The schema-lag gate is callable without frames (the bridge calls it early)."""
        assert_intent_columns_present(
            unit_holder_columns=REQUIRED_UNIT_HOLDER_COLUMNS,
            business_columns=REQUIRED_BUSINESS_COLUMNS,
            offer_columns=REQUIRED_OFFER_COLUMNS,
        )
        with pytest.raises(FrameSchemaLagError, match="unit_holder.custom_cal_status"):
            assert_intent_columns_present(
                unit_holder_columns=("gid", "parent_gid", "last_modified"),
                business_columns=REQUIRED_BUSINESS_COLUMNS,
                offer_columns=REQUIRED_OFFER_COLUMNS,
            )
