"""SEAM-2 unit-economics drop repro: NUMBER custom fields + ENUM discount.

Grandeur anchor: the entity-keyed unit frame (1201081073731555/unit/sections/)
must carry POPULATED mrr/weekly_ad_spend so Consumer-2's per-PVP MRR is real,
not silent DEGRADED/$0. This module is the deliberately-broken fixture that
fires RED on the true defects -- never a green dashboard.

EMPIRICAL GROUNDING (live S3 probe of unit project 1201081073731555, the
``dataframes/unit:1201081073731555.parquet`` frame + its stored task.json dicts,
2026-06-09). Two findings, one of which CORRECTS the originally-hypothesized
root cause:

1. Branch-1 ("number_value stripped on the unit-axis store/warm path while
   display_value survives") is REFUTED for the live stored substrate. Across
   8/8 sampled null-mrr stored task dicts, ``number_value`` AND ``display_value``
   were BOTH null (null-at-source -- the operator has not entered MRR on those
   tasks). Across 6/6 populated rows, ``number_value`` was present end-to-end
   (the warm/store path does NOT strip it). So the partial null in the live
   parquet (~27% mrr populated) is operator data-entry, not a code seam, and is
   only curable by a re-warm after data entry (an operator lever, not a code fix).

2. The genuine, code-curable defects (this module's RED targets):
   (a) DEFENSE PARITY: the number-branch in BOTH the direct resolver
       (``DefaultCustomFieldResolver._extract_raw_value``, resolver/default.py)
       and the cascade path (``cf_utils.extract_cf_value``, views/cf_utils.py)
       returned ``number_value`` with NO ``display_value`` fallback -- unlike
       text/enum. The ``display_value`` recovery lived only in ``case _``, which
       never fires for a known "number" subtype. Asana's LIST endpoint can return
       a populated ``display_value`` with ``number_value`` null even when
       ``number_value`` is requested in opt_fields; without the fallback that
       recoverable magnitude is silently dropped. THE FIX gives the number-branch
       the same display_value robustness text/enum already have.
   (b) COERCER CONVERGENCE: ``resolver/coercer.py:_to_numeric`` had no
       percentage/currency/locale parse, so a recovered display string like
       "10%"/"$4,500" coerced to None -- while ``builders/fields._coerce_value``
       DID strip "%". The two coercers diverged. THE FIX ports the safe parse
       into the resolver coercer (only when the residue is cleanly numeric --
       never an invented value).
   (c) DISCOUNT CONTRACT: Discount is an Asana ENUM (stored task dict:
       ``resource_subtype="enum"``, ``enum_value.name="0%"``, ``display_value="0%"``),
       NOT a number. The model declares ``EnumField()`` (authoritative). The
       schema previously declared ``dtype="Decimal"``, so the resolver coercer
       dropped enum "0%" to None. THE FIX sets the schema dtype (and UnitRow
       field) to the honest enum string (Utf8 / ``str``).

These tests exercise the REAL extraction path -- DefaultCustomFieldResolver +
UnitExtractor(UNIT_SCHEMA, resolver) -- NOT MockCustomFieldResolver. The mock
would trivially pass (it returns pre-baked values and never touches the
number/enum branches), hiding the bug.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from autom8_asana.dataframes.extractors.unit import UnitExtractor
from autom8_asana.dataframes.resolver import DefaultCustomFieldResolver
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
from autom8_asana.models.custom_field import CustomField
from autom8_asana.models.task import Task

# ---------------------------------------------------------------------------
# Fixture builders -- realistic Unit Task with NUMBER custom fields.
# ---------------------------------------------------------------------------

# Live custom-field GIDs are opaque; any stable gid works for the name->gid index.
_MRR_GID = "1201081073731600"
_WAS_GID = "1201081073731601"

_EXPECTED_MRR = Decimal("2500")
_EXPECTED_WAS = Decimal("600")


def _build_unit_task(custom_fields: list[dict]) -> Task:
    """Construct a realistic Unit Task carrying the given custom_fields.

    ``Task.custom_fields`` is typed ``list[dict[str, Any]] | None`` (task.py),
    so the dicts pass through verbatim -- exactly the shape the resolver iterates.
    """
    return Task(
        gid="1201081073731555",
        name="Acme Unit",
        resource_subtype="Unit",
        created_at="2026-01-01T00:00:00.000Z",
        modified_at="2026-01-01T00:00:00.000Z",
        custom_fields=custom_fields,
    )


def _real_resolver_for(task: Task) -> DefaultCustomFieldResolver:
    """Build a production DefaultCustomFieldResolver indexed off the task.

    Mirrors DataFrameBuilder._ensure_resolver_initialized (builders/base.py):
    validates each dict to CustomField to build the name->gid index, then the
    resolver reads values back off the raw task.custom_fields dicts.
    """
    resolver = DefaultCustomFieldResolver()
    resolver.build_index([CustomField.model_validate(cf) for cf in (task.custom_fields or [])])
    return resolver


def _extract_unit(task: Task):
    """Run the REAL extraction path and return the UnitRow."""
    resolver = _real_resolver_for(task)
    extractor = UnitExtractor(UNIT_SCHEMA, resolver)
    return extractor.extract(task)


# ---------------------------------------------------------------------------
# Baseline: number_value populated -> resolves cleanly (proves the harness is
# wired to the real path and the resolver number-branch works when fed a value).
# ---------------------------------------------------------------------------


class TestExtractorBoundaryBaseline:
    """GREEN baseline -- number_value present resolves to populated Decimal."""

    def test_number_value_present_resolves_to_decimal(self) -> None:
        task = _build_unit_task(
            [
                {
                    "gid": _MRR_GID,
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 2500,
                    "display_value": "2500",
                },
                {
                    "gid": _WAS_GID,
                    "name": "Weekly Ad Spend",
                    "resource_subtype": "number",
                    "number_value": 600,
                    "display_value": "600",
                },
            ]
        )

        row = _extract_unit(task)

        assert row.mrr == _EXPECTED_MRR, (
            "baseline: number_value present must resolve to populated Decimal"
        )
        assert row.weekly_ad_spend == _EXPECTED_WAS


# ---------------------------------------------------------------------------
# DEFECT (a) DEFENSE PARITY: number_value null/absent but display_value present
# -> dropped to None. This is the Asana LIST-endpoint shape (number_value null
# even when requested; display_value carries the magnitude). text/enum survive
# this shape; NUMBER did not until the display_value fallback was added.
# ---------------------------------------------------------------------------


class TestNumberValueAbsentDropsToNull:
    """Defense-parity guard -- number cf with display_value but no number_value.

    Fires RED on the un-fixed number-branch (no display_value fallback); GREEN
    once the branch falls back to display_value like text/enum do.
    """

    def test_number_cf_with_display_value_only_drops_to_null(self) -> None:
        # List-endpoint shape: resource_subtype="number", number_value null,
        # display_value still carries the human-readable number.
        task = _build_unit_task(
            [
                {
                    "gid": _MRR_GID,
                    "name": "MRR",
                    "resource_subtype": "number",
                    "display_value": "2500",  # value IS present here
                    # number_value intentionally absent (warm round-trip stripped it)
                },
                {
                    "gid": _WAS_GID,
                    "name": "Weekly Ad Spend",
                    "resource_subtype": "number",
                    "display_value": "600",
                },
            ]
        )

        row = _extract_unit(task)

        # The value "2500" is sitting in display_value; the un-fixed number-branch
        # ignores it and returns None. THIS ASSERTION FIRES RED without the fix.
        assert row.mrr == _EXPECTED_MRR, (
            "DEFECT (defense parity): NUMBER cf with display_value='2500' but no "
            f"number_value drops to {row.mrr!r}; the resolver number-branch needs a "
            "display_value fallback (text/enum already have one; only case _ "
            "recovered display_value before). This is the Asana list-endpoint shape "
            "where number_value is null but display_value carries the magnitude."
        )
        assert row.weekly_ad_spend == _EXPECTED_WAS

    def test_text_and_enum_survive_same_shape(self) -> None:
        """Contrast: text/enum custom fields survive the value-stripped shape.

        Proves the drop is TYPE-SELECTIVE (matches the live receipt: office_phone/
        vertical/specialty survive while number cf drop). Documents that the bug
        is confined to the number-branch, not a blanket value-stripping.
        """
        task = _build_unit_task(
            [
                {
                    "gid": "1201081073731602",
                    "name": "Specialty",
                    "resource_subtype": "text",
                    "text_value": "Dental",
                    "display_value": "Dental",
                },
                {
                    "gid": "1201081073731603",
                    "name": "Vertical",
                    "resource_subtype": "enum",
                    "enum_value": {"gid": "e1", "name": "Healthcare"},
                    "display_value": "Healthcare",
                },
            ]
        )

        row = _extract_unit(task)

        assert row.specialty == "Dental", "text cf must survive (selectivity proof)"
        assert row.vertical == "Healthcare", "enum cf must survive (selectivity proof)"


# ---------------------------------------------------------------------------
# Round-trip variant: drive the number cf through model_dump(exclude_none=True)
# -- the warm-path serializer (task_cache.py / hierarchy_warmer.py) -- after the
# number_value has been nulled, then re-validate and extract. Proves the
# display_value fallback survives the full warm round-trip (where exclude_none
# strips the None number_value key), not just a hand-built dict. This is the
# specific shape that makes the number-branch's display_value fallback
# load-bearing: a NULL number_value key vanishes under exclude_none, so
# display_value is the ONLY surviving carrier of the magnitude.
# ---------------------------------------------------------------------------


class TestWarmRoundTripDropsNumberValue:
    """Defense-parity guard across the model_dump(exclude_none=True) round-trip."""

    def test_warm_round_trip_nulls_mrr(self) -> None:
        # Source task carries number cf with number_value EXPLICITLY None (the
        # state a null-number cf is left in) plus a live display_value.
        source = _build_unit_task(
            [
                {
                    "gid": _MRR_GID,
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": None,
                    "display_value": "2500",
                },
                {
                    "gid": _WAS_GID,
                    "name": "Weekly Ad Spend",
                    "resource_subtype": "number",
                    "number_value": None,
                    "display_value": "600",
                },
            ]
        )

        # Warm-path serializer: model_dump(exclude_none=True) (task_cache.py:379,
        # hierarchy_warmer.py:94). exclude_none drops the None number_value key
        # entirely, leaving display_value as the only surviving carrier.
        dumped = source.model_dump(exclude_none=True)
        warm_task = Task.model_validate(dumped)

        for cf in warm_task.custom_fields or []:
            if cf.get("name") == "MRR":
                assert "number_value" not in cf or cf.get("number_value") is None, (
                    "round-trip precondition: number_value must be dropped by "
                    "exclude_none, leaving display_value to carry the value"
                )
                assert cf.get("display_value") == "2500"

        row = _extract_unit(warm_task)

        assert row.mrr == _EXPECTED_MRR, (
            "DEFECT (warm round-trip): after model_dump(exclude_none=True) the "
            f"number_value key is gone; mrr resolves to {row.mrr!r} instead of "
            "the display_value-recoverable 2500. End-to-end proof of the live drop."
        )
        assert row.weekly_ad_spend == _EXPECTED_WAS


# ---------------------------------------------------------------------------
# DEFECT (c) DISCOUNT CONTRACT: Discount is an Asana ENUM ("0%", "10%"), not a
# number. Proven against the live stored task dict for unit project
# 1201081073731555 (resource_subtype="enum", enum_value.name="0%",
# display_value="0%"). With the schema previously typed Decimal, the resolver
# coercer dropped enum "0%" -> None. With the honest Utf8 contract the enum
# string survives.
# ---------------------------------------------------------------------------


class TestDiscountEnumSurvives:
    """Discount enum string survives extraction with the honest Utf8 contract."""

    def test_discount_enum_zero_percent_survives_as_string(self) -> None:
        # The exact live stored shape (per S3 task.json for gid 1201122816966593).
        task = _build_unit_task(
            [
                {
                    "gid": "1200653169280807",
                    "name": "Discount",
                    "resource_subtype": "enum",
                    "enum_value": {
                        "gid": "1200653169280807",
                        "name": "0%",
                        "resource_type": "enum_option",
                    },
                    "display_value": "0%",
                },
            ]
        )

        row = _extract_unit(task)

        assert row.discount == "0%", (
            "DEFECT (discount contract): enum Discount '0%' must survive as the "
            f"honest enum string, not drop to {row.discount!r}. With dtype=Decimal "
            "the resolver coercer dropped it to None; Utf8 carries it intact."
        )

    def test_discount_enum_ten_percent_survives_as_string(self) -> None:
        task = _build_unit_task(
            [
                {
                    "gid": "1200653169280808",
                    "name": "Discount",
                    "resource_subtype": "enum",
                    "enum_value": {
                        "gid": "1200653169280808",
                        "name": "10%",
                        "resource_type": "enum_option",
                    },
                    "display_value": "10%",
                },
            ]
        )

        row = _extract_unit(task)

        assert row.discount == "10%", (
            f"enum Discount '10%' must survive as a string, got {row.discount!r}"
        )


# ---------------------------------------------------------------------------
# DEFECT (b) COERCER CONVERGENCE: the resolver coercer must normalize decorated
# numeric display strings ("10%", "$4,500", "4,500") like builders/fields does,
# AND must NOT invent a value from a non-numeric string. This is the unit test
# of the parse that makes the display_value fallback (defect (a)) actually yield
# a number rather than a None-after-coercion.
# ---------------------------------------------------------------------------


class TestCoercerConvergence:
    """resolver/coercer normalizes currency/percent/locale numeric strings."""

    def test_percent_string_coerces_to_decimal(self) -> None:
        from autom8_asana.dataframes.resolver.coercer import coerce_value

        assert coerce_value("10%", "Decimal") == Decimal("10")
        assert coerce_value("0%", "Decimal") == Decimal("0")

    def test_currency_and_thousands_coerce_to_decimal(self) -> None:
        from autom8_asana.dataframes.resolver.coercer import coerce_value

        assert coerce_value("$4,500", "Decimal") == Decimal("4500")
        assert coerce_value("4,500", "Decimal") == Decimal("4500")
        assert coerce_value("$4,500.50", "Decimal") == Decimal("4500.50")

    def test_non_numeric_string_returns_none_never_invented(self) -> None:
        from autom8_asana.dataframes.resolver.coercer import coerce_value

        # Honest failure: a non-numeric string must NOT fabricate a magnitude.
        assert coerce_value("N/A", "Decimal") is None
        assert coerce_value("1.2.3", "Decimal") is None
        assert coerce_value("", "Decimal") is None

    def test_display_value_fallback_with_percent_resolves_via_coercer(self) -> None:
        # End-to-end of (a)+(b): number cf with number_value null and a decorated
        # display_value "$2,500" resolves to a real Decimal through the extractor.
        task = _build_unit_task(
            [
                {
                    "gid": _MRR_GID,
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": None,
                    "display_value": "$2,500",
                },
            ]
        )

        row = _extract_unit(task)

        assert row.mrr == Decimal("2500"), (
            "number_value-null + decorated display_value '$2,500' must resolve to "
            f"Decimal(2500) via display_value fallback + coercer normalization, got "
            f"{row.mrr!r}"
        )


# ---------------------------------------------------------------------------
# ROOT-PATH PROOF (distinct from defense parity): the live stored-dict shape --
# number_value PRESENT alongside display_value -- carries the magnitude
# end-to-end through model_dump(exclude_none=True) and re-validation. This proves
# the warm/store path does NOT strip a populated number_value (the empirically
# established truth: 6/6 populated live rows kept number_value), so a re-warm
# after data entry yields a populated frame -- the operator lever.
# ---------------------------------------------------------------------------


class TestRootPathPopulatedNumberValuePersists:
    """Populated number_value survives the warm round-trip and extracts cleanly."""

    def test_populated_number_value_survives_warm_round_trip(self) -> None:
        # The live populated shape (per S3 task.json gid 1201122816966593:
        # number_value=550, display_value="550").
        source = _build_unit_task(
            [
                {
                    "gid": _MRR_GID,
                    "name": "MRR",
                    "resource_subtype": "number",
                    "number_value": 550,
                    "display_value": "550",
                },
                {
                    "gid": _WAS_GID,
                    "name": "Weekly Ad Spend",
                    "resource_subtype": "number",
                    "number_value": 250,
                    "display_value": "250",
                },
            ]
        )

        # Warm-path serializer. A POPULATED number_value SURVIVES exclude_none
        # (only None keys are dropped) -- this is the root-path invariant.
        dumped = source.model_dump(exclude_none=True)
        warm_task = Task.model_validate(dumped)

        carried = {cf.get("name"): cf.get("number_value") for cf in (warm_task.custom_fields or [])}
        assert carried.get("MRR") == 550, (
            "ROOT INVARIANT: populated number_value must survive "
            f"model_dump(exclude_none=True); got {carried.get('MRR')!r}"
        )
        assert carried.get("Weekly Ad Spend") == 250

        row = _extract_unit(warm_task)

        assert row.mrr == Decimal("550"), (
            "ROOT PROOF: populated number_value resolves to Decimal end-to-end "
            f"through the warm round-trip + real extractor; got {row.mrr!r}"
        )
        assert row.weekly_ad_spend == Decimal("250")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q", "--no-header", "-p", "no:randomly"])
