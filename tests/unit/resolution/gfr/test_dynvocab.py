"""Tests for the GFR dynamic-tail resolver (TDD-delta sprint-2 §9.1).

The tail is the ``is_identity=False``, NAME-keyed contract S3/S4 attach to. These
tests lock the three-state result model (PRESENT / PRESENT_BUT_NULL / ABSENT), the
NAME-keying grain, the ``_extract_raw_value`` reuse, the cache-only guarantee, and
the §4.2 structural guarantee (a NAME in a returned row => the cf exists; value=None
=> present-but-null, never absent).
"""

from __future__ import annotations

from typing import Any

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.resolution.gfr.dynvocab import (
    DynFieldState,
    _build_manifest,
    _is_null,
    resolve_dynamic_fields,
)
from autom8_asana.resolution.gfr.entry import EntryAnchor
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import FieldStatus, ResolvedFields, TruthTier
from tests.unit.resolution.gfr.conftest import make_entry_task

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


def _anchor(custom_fields: list[dict[str, Any]] | None, *, gid: str = "O") -> EntryAnchor:
    """An Offer EntryAnchor whose entry_task carries the given cf manifest."""
    return EntryAnchor(
        gid=gid,
        entity_type=EntityType.OFFER,
        business_gid="B",
        path_len=3,
        entry_task=make_entry_task(gid=gid, custom_fields=custom_fields),
    )


# A representative manifest exercising each reuse path (TDD §5.1) plus the present-
# but-null date hole (S3 FRAME-003 dependency) and an explicit null control.
_FULL_MANIFEST: list[dict[str, Any]] = [
    # Generic (non-overridden) text field — isolates the bare-text reuse path from
    # the asset_id comma-split override (TestAssetIdOverride covers that separately).
    {
        "gid": "cf-text",
        "name": "Account Health Score",
        "resource_subtype": "text",
        "text_value": "a",
    },
    {"gid": "cf-num", "name": "Seat Count", "resource_subtype": "number", "number_value": 7},
    {
        "gid": "cf-enum",
        "name": "Tier",
        "resource_subtype": "enum",
        "enum_value": {"name": "Gold"},
    },
    {
        "gid": "cf-menum",
        "name": "Tags",
        "resource_subtype": "multi_enum",
        "multi_enum_values": [{"name": "x"}, {"name": "y"}],
    },
    {
        "gid": "cf-people",
        "name": "Owners",
        "resource_subtype": "people",
        "people_value": [{"gid": "p1"}, {"gid": "p2"}],
    },
    # date cf with no date_value fetched (the S3 FRAME-003 hole) -> present-but-null.
    {"gid": "cf-date", "name": "Renews On", "resource_subtype": "date"},
    # explicit empty text -> present-but-null.
    {"gid": "cf-empty", "name": "Notes", "resource_subtype": "text", "text_value": ""},
]


class TestThreeStateContract:
    def test_present_field_resolves_typed(self) -> None:
        """PRESENT: cf on manifest with non-null typed value -> typed FieldWithProvenance.

        Uses a generic (non-overridden) field so this asserts the bare-typed contract;
        asset_id's override-to-SET behavior is covered by TestAssetIdOverride.
        """
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Account Health Score",
                    "resource_subtype": "text",
                    "text_value": "a",
                }
            ]
        )
        result = resolve_dynamic_fields(anchor=anchor, fields=["account_health_score"])
        assert isinstance(result, ResolvedFields)
        row = result.scalar()
        assert row["account_health_score"].value == "a"
        assert row["account_health_score"].status is FieldStatus.FRESH
        assert row["account_health_score"].source is TruthTier.CACHE

    def test_present_but_null_is_distinct_from_absent(self) -> None:
        """PRESENT_BUT_NULL (value=None, in rows) is NOT conflated with ABSENT (raises)."""
        # present-but-null: cf exists, value slot null.
        present_null = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": None}]
        )
        row = resolve_dynamic_fields(anchor=present_null, fields=["asset_id"]).scalar()
        assert "asset_id" in row
        assert row["asset_id"].value is None

        # absent: cf genuinely not on the manifest -> raises unknown-field.
        absent = _anchor([{"gid": "cf1", "name": "Other Field", "resource_subtype": "text"}])
        with pytest.raises(UnresolvedError) as exc:
            resolve_dynamic_fields(anchor=absent, fields=["asset_id"])
        assert exc.value.reason == "unknown-field"

    def test_present_but_null_field_appears_in_rows(self) -> None:
        """§4.2 structural guarantee: a present-but-null NAME IS a key in the row."""
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": ""}]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        # The field name is present as a key, with value=None => present-but-null,
        # never absent. (value=None in a returned row ALWAYS means present-but-null.)
        assert "asset_id" in row
        assert row["asset_id"].value is None

    def test_absent_field_raises_unknown_field(self) -> None:
        """ABSENT: a field not on the manifest -> UnresolvedError(unknown-field)."""
        anchor = _anchor([{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text"}])
        with pytest.raises(UnresolvedError) as exc:
            resolve_dynamic_fields(anchor=anchor, fields=["nonexistent_field"])
        assert exc.value.reason == "unknown-field"
        assert exc.value.fields == ["nonexistent_field"]

    def test_absent_is_all_or_nothing_within_dynamic_subset(self) -> None:
        """One absent field collapses the whole dynamic subset (governed-strict I4)."""
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "a"}]
        )
        with pytest.raises(UnresolvedError) as exc:
            # asset_id is PRESENT, but missing_one is ABSENT -> the whole call fails.
            resolve_dynamic_fields(anchor=anchor, fields=["asset_id", "missing_one"])
        assert exc.value.reason == "unknown-field"
        assert exc.value.fields == ["missing_one"]

    def test_multiple_absent_all_reported(self) -> None:
        """All genuinely-absent fields are carried on the raise (all-or-nothing)."""
        anchor = _anchor([{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text"}])
        with pytest.raises(UnresolvedError) as exc:
            resolve_dynamic_fields(anchor=anchor, fields=["nope1", "nope2"])
        assert set(exc.value.fields) == {"nope1", "nope2"}


class TestNameKeying:
    def test_name_keying_normalizes(self) -> None:
        """NAME-keyed: requested snake_case matches a Title Case cf name via normalize.

        Uses a generic (non-overridden) field so this isolates the NAME-normalization
        contract from the asset_id override transform.
        """
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Account Health Score",
                    "resource_subtype": "text",
                    "text_value": "v",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["account_health_score"]).scalar()
        assert row["account_health_score"].value == "v"

    def test_match_is_not_gid_keyed(self) -> None:
        """The cf gid is never the match key — requesting a gid string is absent."""
        anchor = _anchor(
            [{"gid": "cf-xyz", "name": "Asset ID", "resource_subtype": "text", "text_value": "v"}]
        )
        with pytest.raises(UnresolvedError) as exc:
            # "cf-xyz" is the cf gid, NOT a name -> must be ABSENT, never a match.
            resolve_dynamic_fields(anchor=anchor, fields=["cf-xyz"])
        assert exc.value.reason == "unknown-field"

    def test_build_manifest_is_name_keyed_first_match_wins(self) -> None:
        """_build_manifest indexes normalize(name); first duplicate name wins."""
        manifest = _build_manifest(
            [
                {"gid": "a", "name": "Asset ID", "resource_subtype": "text", "text_value": "1st"},
                {"gid": "b", "name": "asset_id", "resource_subtype": "text", "text_value": "2nd"},
            ]
        )
        assert "assetid" in manifest
        # First-match-wins: the earlier cf is not clobbered by the normalized dup.
        assert manifest["assetid"]["gid"] == "a"


class TestTypingReuse:
    @pytest.mark.parametrize(
        ("field", "expected"),
        [
            ("account_health_score", "a"),  # text (generic, no override)
            ("seat_count", 7),  # number
            ("tier", "Gold"),  # enum -> label
            ("tags", ["x", "y"]),  # multi_enum -> list[label]
            ("owners", ["p1", "p2"]),  # people -> list[gid]
        ],
    )
    def test_each_cf_type_extracts_via_reuse(self, field: str, expected: Any) -> None:
        """Each cf type resolves through _extract_raw_value to the §5.1 typed result."""
        anchor = _anchor(_FULL_MANIFEST)
        row = resolve_dynamic_fields(anchor=anchor, fields=[field]).scalar()
        assert row[field].value == expected

    def test_date_cf_is_present_but_null_pre_s3(self) -> None:
        """A date cf with no date_value fetched is PRESENT_BUT_NULL, not absent (S3 dep)."""
        anchor = _anchor(_FULL_MANIFEST)
        row = resolve_dynamic_fields(anchor=anchor, fields=["renews_on"]).scalar()
        # On the manifest (so a key), but null today (date_value not fetched).
        assert "renews_on" in row
        assert row["renews_on"].value is None

    def test_date_cf_with_date_value_resolves_to_value(self) -> None:
        """FRAME-003: once date_value is fetched, the SAME date cf flips
        PRESENT_BUT_NULL -> PRESENT and resolves to its value, not None.

        This is the contract side of the date-hole closure: the tail's date arm
        reads date_value via the reused _extract_raw_value. Closing the LIVE hole
        is adding custom_fields.date_value to STANDARD_TASK_OPT_FIELDS so the live
        fetch actually carries it (asserted in test_fields.py)."""
        anchor = _anchor(
            [
                {
                    "gid": "cf-date",
                    "name": "Renews On",
                    "resource_subtype": "date",
                    "date_value": {"date": "2026-07-01"},
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["renews_on"]).scalar()
        assert row["renews_on"].value == "2026-07-01"
        assert row["renews_on"].cf_type == "date"


class TestCacheOnly:
    def test_tail_makes_no_asana_call(self) -> None:
        """Cache-only: the tail resolves off entry_task with ZERO client calls.

        The tail receives only an EntryAnchor and reads its in-hand cf manifest; it
        is given no client and constructs none. There is no I/O surface to fire.
        """
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "a"}]
        )
        # No client argument exists on the tail signature => structurally cache-only.
        result = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"])
        assert result.row_count == 1

    def test_empty_manifest_makes_every_field_absent(self) -> None:
        """An entry task with no custom fields -> every requested field is absent."""
        anchor = _anchor([])
        with pytest.raises(UnresolvedError) as exc:
            resolve_dynamic_fields(anchor=anchor, fields=["asset_id"])
        assert exc.value.reason == "unknown-field"


class TestNullPredicate:
    @pytest.mark.parametrize("raw", [None, "", [], (), set(), {}])
    def test_is_null_true_for_empty(self, raw: Any) -> None:
        assert _is_null(raw) is True

    @pytest.mark.parametrize("raw", ["a", 0, 7, ["x"], {"k": "v"}, False])
    def test_is_null_false_for_populated(self, raw: Any) -> None:
        # Note: 0 / False are NOT null (a populated numeric/bool value).
        assert _is_null(raw) is False


class TestDynFieldStateEnum:
    def test_three_states_present(self) -> None:
        """The contract enum is exactly the three states (frozen surface)."""
        assert {s.value for s in DynFieldState} == {"present", "present-but-null", "absent"}


# =============================================================================
# Sprint-3 FRAME-002 — asset_id override (NAME-keyed, EntityType-scoped)
# =============================================================================


class TestAssetIdOverride:
    """FRAME-002: per-field override registry keyed by canonical field NAME,
    EntityType-scoped. asset_id (text) -> whitespace-agnostic comma-split -> SET,
    applied AFTER the tail extracts the raw text value. NAME-keyed
    (NameNormalizer.normalize), never gid-keyed.
    """

    def test_asset_id_text_resolves_to_set(self) -> None:
        """cf 'Asset ID' text_value='a, b ,c' -> {'a','b','c'} (the worked example)."""
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Asset ID",
                    "resource_subtype": "text",
                    "text_value": "a, b ,c",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        assert row["asset_id"].value == {"a", "b", "c"}

    def test_asset_id_whitespace_agnostic(self) -> None:
        """Whitespace around each token is stripped; empty tokens are dropped."""
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Asset ID",
                    "resource_subtype": "text",
                    "text_value": "  a1,a2 ,  a3 ,a4  ",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        assert row["asset_id"].value == {"a1", "a2", "a3", "a4"}

    def test_asset_id_single_token_is_a_set(self) -> None:
        """A single value still resolves to a one-element SET, not a bare string."""
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "solo"}]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        assert row["asset_id"].value == {"solo"}

    def test_asset_id_empty_is_present_but_null_not_empty_set(self) -> None:
        """empty/None text -> present-but-null (value=None), NOT an empty set.

        Deliberate boundary: an empty set masquerading as a value would lie about
        present-vs-null. The override must NOT manufacture a value from an empty
        raw; the field stays PRESENT_BUT_NULL (value=None) so the three-state
        contract holds.
        """
        empty = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": ""}]
        )
        row = resolve_dynamic_fields(anchor=empty, fields=["asset_id"]).scalar()
        assert "asset_id" in row
        assert row["asset_id"].value is None

        none_val = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": None}]
        )
        row2 = resolve_dynamic_fields(anchor=none_val, fields=["asset_id"]).scalar()
        assert "asset_id" in row2
        assert row2["asset_id"].value is None

    def test_asset_id_override_is_entity_scoped(self) -> None:
        """The override is keyed (EntityType, normalized-name); a non-Offer entry
        whose registry has no asset_id override returns the raw text unchanged."""
        from autom8_asana.resolution.gfr.dynvocab_overrides import apply_override

        # Offer-scoped asset_id override -> set.
        assert apply_override("asset_id", "offer", "a,b") == {"a", "b"}
        # An entity with no registered override for the field -> raw passthrough.
        assert apply_override("asset_id", "some_unregistered_entity", "a,b") == "a,b"

    def test_override_is_name_keyed_not_gid_keyed(self) -> None:
        """The override matches normalize('Asset ID')==normalize('asset_id'); a cf
        gid string is never the override key."""
        from autom8_asana.resolution.gfr.dynvocab_overrides import apply_override

        # Name forms normalize to the same key and hit the override.
        assert apply_override("Asset ID", "offer", "a,b") == {"a", "b"}
        # A gid-shaped string is not a field name -> no override, raw passthrough.
        assert apply_override("cf-12345", "offer", "a,b") == "a,b"

    def test_second_override_is_data_not_code(self) -> None:
        """A 2nd override must be a data addition to the registry, not a code change.

        Structural assertion: the registry is a plain mapping of (entity, name) ->
        callable. Adding an entry is a literal append; resolution reads the mapping.
        """
        from autom8_asana.resolution.gfr import dynvocab_overrides as ov

        # The registry is a dict the build/data layer extends; apply_override reads it.
        assert isinstance(ov.OVERRIDE_REGISTRY, dict)
        # The asset_id-for-offer entry is present and keyed by (entity, normalized).
        from autom8_asana.dataframes.resolver.normalizer import NameNormalizer

        key = ("offer", NameNormalizer.normalize("asset_id"))
        assert key in ov.OVERRIDE_REGISTRY
        assert callable(ov.OVERRIDE_REGISTRY[key])


# =============================================================================
# Sprint-3 FRAME-004 — typing provenance (typing_origin + cf_type)
# =============================================================================


class TestTypingProvenance:
    """FRAME-004: the resolved payload carries typing_origin in
    {schema, heuristic, override, absent, fallback} + cf_type, additively.
    FieldWithProvenance stays extra='forbid'-safe.
    """

    def test_heuristic_origin_on_plain_typed_field(self) -> None:
        """A cf resolved straight through _extract_raw_value (no override) -> heuristic."""
        anchor = _anchor(
            [{"gid": "cf1", "name": "Seat Count", "resource_subtype": "number", "number_value": 7}]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["seat_count"]).scalar()
        assert row["seat_count"].typing_origin == "heuristic"
        assert row["seat_count"].cf_type == "number"

    def test_override_origin_on_asset_id(self) -> None:
        """asset_id passes through the comma-split override -> typing_origin='override'."""
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "a,b"}]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        assert row["asset_id"].typing_origin == "override"
        assert row["asset_id"].cf_type == "text"

    def test_fallback_origin_on_unknown_subtype(self) -> None:
        """An unknown resource_subtype hits the case _ fallthrough -> typing_origin='fallback'."""
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Mystery",
                    "resource_subtype": "brand_new_2027_type",
                    "display_value": "shrug",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["mystery"]).scalar()
        assert row["mystery"].typing_origin == "fallback"

    def test_present_but_null_carries_cf_type(self) -> None:
        """A present-but-null field still stamps cf_type and a heuristic origin."""
        anchor = _anchor([{"gid": "cf1", "name": "Renews On", "resource_subtype": "date"}])
        row = resolve_dynamic_fields(anchor=anchor, fields=["renews_on"]).scalar()
        assert row["renews_on"].value is None
        assert row["renews_on"].cf_type == "date"
        # present-but-null is a heuristic extraction whose value slot is null.
        assert row["renews_on"].typing_origin == "heuristic"

    def test_provenance_is_extra_forbid_safe(self) -> None:
        """FieldWithProvenance with the new fields still rejects unknown keys."""
        from pydantic import ValidationError

        from autom8_asana.resolution.gfr.models import FieldWithProvenance

        with pytest.raises(ValidationError):
            FieldWithProvenance(
                value=1,
                status=FieldStatus.FRESH,
                source=TruthTier.CACHE,
                typing_origin="heuristic",
                cf_type="number",
                bogus_unknown_key="x",
            )

    # -- provenance-honesty fix (sprint-3 FRAME-004 self-defect) ----------------
    # The typing_origin MUST reflect how the RETURNED value was actually derived.
    # An applied override is the last transform that produced the value, so it
    # wins the stamp even under fallthrough; a declined/no-op override must NOT
    # claim 'override'.

    def test_applied_override_under_fallthrough_stamps_override_not_fallback(self) -> None:
        """MEDIUM defect: an override-registered field arriving with an UNKNOWN
        resource_subtype (fallthrough) whose value the override DID transform must
        stamp typing_origin='override' (the override produced the returned value),
        NOT 'fallback'. The S5a fallthrough COUNTER must still increment — the
        counter is decoupled from the stamp.
        """
        from autom8_asana.resolution.gfr import dynvocab as dv

        before = dv.fallthrough_count()
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Asset ID",
                    "resource_subtype": "weird_future",
                    "display_value": "p, q",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        # The override comma-split SET ran on the fallthrough-extracted display_value.
        assert row["asset_id"].value == {"p", "q"}
        # Provenance is honest: the override produced the value, so it owns the stamp.
        assert row["asset_id"].typing_origin == "override"
        # S5a observability is preserved: the unknown subtype still counted.
        assert dv.fallthrough_count() == before + 1

    def test_declined_override_known_subtype_is_heuristic_not_override(self) -> None:
        """LOW defect: a registered override that DECLINES (boundary discipline —
        whitespace/comma-only text returns the raw UNCHANGED) must NOT stamp
        'override'. For a KNOWN subtype with no actual transform, the honest origin
        is 'heuristic'.
        """
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Asset ID",
                    "resource_subtype": "text",
                    "text_value": "  ,  ",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        # Boundary discipline: the comma/whitespace-only raw passes through unchanged.
        assert row["asset_id"].value == "  ,  "
        # No transform occurred, so 'override' would be a lie; known subtype -> heuristic.
        assert row["asset_id"].typing_origin == "heuristic"

    def test_declined_override_unknown_subtype_is_fallback_not_override(self) -> None:
        """LOW defect (fallthrough arm): a declined override on an UNKNOWN subtype
        falls to 'fallback' (the unknown-subtype signal), NEVER 'override' — no
        transform produced the value.
        """
        from autom8_asana.resolution.gfr import dynvocab as dv

        before = dv.fallthrough_count()
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Asset ID",
                    "resource_subtype": "weird_future",
                    "display_value": "  ,  ",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        # Boundary discipline declines -> raw passthrough, no transform.
        assert row["asset_id"].value == "  ,  "
        assert row["asset_id"].typing_origin == "fallback"
        # Counter still fires on the unknown subtype.
        assert dv.fallthrough_count() == before + 1

    def test_applied_override_known_subtype_stamps_override(self) -> None:
        """Regression (unchanged behavior): an override that transforms on a KNOWN
        subtype still stamps 'override'.
        """
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "a,b"}]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["asset_id"]).scalar()
        assert row["asset_id"].value == {"a", "b"}
        assert row["asset_id"].typing_origin == "override"

    def test_non_override_unknown_subtype_is_fallback(self) -> None:
        """Regression (unchanged behavior): a field with NO registered override on
        an unknown subtype stamps 'fallback'.
        """
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Mystery",
                    "resource_subtype": "brand_new_2027_type",
                    "display_value": "shrug",
                }
            ]
        )
        row = resolve_dynamic_fields(anchor=anchor, fields=["mystery"]).scalar()
        assert row["mystery"].typing_origin == "fallback"


# =============================================================================
# Sprint-3 FRAME-003 — fallthrough counter (observable)
# =============================================================================


class TestFallthroughCounter:
    """FRAME-003: an unknown cf subtype increments an observable fallthrough counter
    and stamps typing_origin='fallback'."""

    def test_fallthrough_increments_counter(self) -> None:
        from autom8_asana.resolution.gfr import dynvocab as dv

        before = dv.fallthrough_count()
        anchor = _anchor(
            [
                {
                    "gid": "cf1",
                    "name": "Mystery",
                    "resource_subtype": "totally_new_subtype",
                    "display_value": "x",
                }
            ]
        )
        resolve_dynamic_fields(anchor=anchor, fields=["mystery"])
        assert dv.fallthrough_count() == before + 1

    def test_known_subtype_does_not_increment(self) -> None:
        from autom8_asana.resolution.gfr import dynvocab as dv

        before = dv.fallthrough_count()
        anchor = _anchor(
            [{"gid": "cf1", "name": "Asset ID", "resource_subtype": "text", "text_value": "a"}]
        )
        resolve_dynamic_fields(anchor=anchor, fields=["asset_id"])
        assert dv.fallthrough_count() == before
