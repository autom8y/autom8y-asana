"""S2 — FRESHNESS law tests (RC-B / F2). Two-sided (the P7 bar).

These prove the freshness-law bodies S2 fills in ``substrate.freshness``:

- ``canonical_digest`` five [H1] pins: value-column set, row order, parquet-
  independent encoding, null canonicalization, float canonicalization — proven
  BOTH ways (a value change moves the digest; a GID/layout change does not).
- The v1 **D8** class is UNCONSTRUCTABLE: a GID-set-preserving value edit (v1's
  blind spot) changes the digest, AND there is no public API that advances
  freshness without a content fetch (the falsifying construction is asserted
  absent).
- ``is_provable`` verdicts + the [H2] naive-``now`` guard.
- ``FreshnessProof.__post_init__`` [H2] tz-reject + the frozen no-restamp property.
- ``fold_built_from_live_at`` MIN-fold incl. the AV-1 reused-stale-section
  regression (a reused old section honestly drags the artifact age back).
- ``sla_seconds_for`` (C8) reads the per-entity SLA from the entity registry.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import polars as pl
import pytest

import autom8_asana.substrate.freshness as freshness
from autom8_asana.core.types import EntityType
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.substrate.freshness import (
    _VALUE_COLUMNS,
    FreshnessProof,
    Provability,
    canonical_digest,
    fold_built_from_live_at,
    is_provable,
    sla_seconds_for,
)

_T0 = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)


def _offer_row(
    *,
    cost: str | None = "500",
    mrr: object = 1000.0,
    offer_id: str = "OF-1",
    weekly_ad_spend: object = 200.0,
    gid: str = "G-1",
    name: str = "Acme",
) -> dict[str, object]:
    """One offer row: the four value columns + non-value (gid/name) columns."""
    return {
        "gid": gid,  # structural — MUST be excluded from the digest (RC-B/P10)
        "name": name,  # non-value schema column — also excluded
        "cost": cost,
        "mrr": mrr,
        "offer_id": offer_id,
        "weekly_ad_spend": weekly_ad_spend,
    }


def _frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def _proof(*, built: datetime = _T0, digest: str = "d0", sla: int = 3600) -> FreshnessProof:
    return FreshnessProof(built_from_live_at=built, content_digest=digest, sla_seconds=sla)


# --------------------------------------------------------------------------- #
# [H1] canonical_digest — the five pins, proven both ways
# --------------------------------------------------------------------------- #


def test_registry_declared_value_columns_exist_in_schema() -> None:
    """[H1](a): every pinned value column is a REGISTRY-DECLARED offer schema column.

    Direct-read receipt (dataframes/schemas/offer.py OFFER_SCHEMA): drift in a
    column name breaks this, not the digest silently.
    """
    schema_columns = set(OFFER_SCHEMA.column_names())
    assert set(_VALUE_COLUMNS) == {"cost", "mrr", "offer_id", "weekly_ad_spend"}
    for column in _VALUE_COLUMNS:
        assert column in schema_columns, f"pinned value column {column!r} absent from OFFER_SCHEMA"


def test_digest_is_deterministic_same_frame_twice() -> None:
    """[H1] same-bytes-twice: two calls on the same frame yield the identical digest."""
    frame = _frame([_offer_row(), _offer_row(offer_id="OF-2", cost="750")])
    assert canonical_digest(frame) == canonical_digest(frame)


def test_digest_is_sha256_hex() -> None:
    """The digest is a 64-char lowercase hex string (sha256)."""
    digest = canonical_digest(_frame([_offer_row()]))
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_value_change_with_gids_preserved_changes_digest() -> None:
    """The D8 killer: a GID-set-preserving VALUE edit moves the digest.

    v1 hashed GIDs, so a value edit that preserved the GID set was invisible
    (false CLEAN — the D8 blind spot). v2's digest is value-derived, so the SAME
    gid with a changed ``cost`` produces a DIFFERENT digest. The blind spot is dead.
    """
    before = _frame([_offer_row(gid="G-1", cost="500")])
    after = _frame([_offer_row(gid="G-1", cost="600")])  # same GID, changed value
    assert canonical_digest(before) != canonical_digest(after)


def test_gid_change_with_values_preserved_keeps_digest() -> None:
    """The dual: re-keying rows (GID/structural change) with values preserved is invisible.

    Proves the digest is EXACTLY value-derived — insensitive to GIDs and to the
    non-value ``name`` column.
    """
    original = _frame([_offer_row(gid="G-1", name="Acme")])
    rekeyed = _frame([_offer_row(gid="G-999", name="Renamed Co")])  # only non-value cols differ
    assert canonical_digest(original) == canonical_digest(rekeyed)


def test_cross_representation_same_content_same_digest() -> None:
    """[H1](b)+(c): same logical content, different physical layout -> same digest.

    Different row order, different column order, an extra structural column, and a
    parquet-independent path (never write_parquet bytes) all collapse to one digest.
    """
    layout_a = _frame([_offer_row(offer_id="OF-1"), _offer_row(offer_id="OF-2", cost="9")])
    # reversed row order, reordered columns, extra structural column
    reordered_rows = [_offer_row(offer_id="OF-2", cost="9"), _offer_row(offer_id="OF-1")]
    layout_b = (
        _frame(reordered_rows)
        .select(["mrr", "weekly_ad_spend", "gid", "offer_id", "cost", "name"])
        .with_columns(pl.lit("extra").alias("last_modified"))
    )
    assert canonical_digest(layout_a) == canonical_digest(layout_b)


def test_duplicate_rows_are_deterministic() -> None:
    """Row-order pin is stable even with duplicate value-records."""
    frame = _frame([_offer_row(), _offer_row(), _offer_row(gid="G-2")])
    assert canonical_digest(frame) == canonical_digest(frame)


def test_null_canonicalization_is_distinct_from_empty_and_literal_null() -> None:
    """[H1](d): null, ``""`` and the string ``"null"`` are three distinct digests."""
    real_null = canonical_digest(_frame([_offer_row(cost=None)]))
    empty_str = canonical_digest(_frame([_offer_row(cost="")]))
    literal_null = canonical_digest(_frame([_offer_row(cost="null")]))
    assert len({real_null, empty_str, literal_null}) == 3


def test_float_canonicalization_equivalent_forms_match() -> None:
    """[H1](e): 1000 / 1000.0 / 1000.00 / Decimal('1E+3') all canonicalize identically."""
    forms: list[object] = [1000, 1000.0, Decimal("1000.00"), Decimal("1E+3")]
    digests = {canonical_digest(_frame([_offer_row(mrr=form)])) for form in forms}
    assert len(digests) == 1


def test_float_canonicalization_distinguishes_real_difference() -> None:
    """[H1](e): a genuinely different magnitude produces a different digest."""
    a = canonical_digest(_frame([_offer_row(mrr=1000.0)]))
    b = canonical_digest(_frame([_offer_row(mrr=1000.01)]))
    assert a != b


def test_float_and_decimal_columns_agree() -> None:
    """[H1](e) cross-representation: a float column and an equal Decimal column agree."""
    as_float = _frame([_offer_row(mrr=1000.0, weekly_ad_spend=200.0)])
    as_decimal = _frame([_offer_row(mrr=Decimal("1000.00"), weekly_ad_spend=Decimal("200"))])
    assert canonical_digest(as_float) == canonical_digest(as_decimal)


def test_non_finite_number_in_value_column_fails_loud() -> None:
    """A NaN/inf in a value column is corruption — fail loud, never a silent digest."""
    with pytest.raises(ValueError, match="non-finite"):
        canonical_digest(_frame([_offer_row(mrr=float("nan"))]))


# --------------------------------------------------------------------------- #
# D8-unconstructable — the falsifying construction is ABSENT (both-ways closure)
# --------------------------------------------------------------------------- #


def test_no_public_api_advances_freshness_without_a_content_fetch() -> None:
    """There is NO probe-stamp path: nothing here freshens without content.

    The falsifying construction ("advance freshness without a fetch") is asserted
    IMPOSSIBLE via the public surface — the module exposes no touch/refresh/stamp/
    mark-fresh verb, and the sole producer of ``built_from_live_at`` is the fold,
    whose only input is content-fetch instants.
    """
    forbidden = {
        "touch",
        "refresh",
        "restamp",
        "stamp",
        "stamp_fresh",
        "mark_fresh",
        "freshen",
        "advance",
        "bump",
        "set_built_from_live_at",
    }
    module_public = {name for name in dir(freshness) if not name.startswith("_")}
    assert not (module_public & forbidden), f"probe-stamp API leaked: {module_public & forbidden}"
    assert not (set(dir(FreshnessProof)) & forbidden)

    fold_params = list(inspect.signature(fold_built_from_live_at).parameters)
    assert fold_params == ["section_fetch_instants"], (
        "the MIN-fold must take content-fetch instants ONLY — a probe cannot feed it"
    )


def test_freshness_proof_is_frozen_and_cannot_be_restamped() -> None:
    """A built proof cannot be re-stamped fresh — the D8 re-stamp bridge is gone."""
    proof = _proof()
    with pytest.raises(AttributeError):
        proof.built_from_live_at = datetime.now(tz=UTC)  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# [H2] FreshnessProof.__post_init__ tz-reject
# --------------------------------------------------------------------------- #


def test_freshness_proof_rejects_naive_built_from_live_at() -> None:
    """[H2]: a naive built_from_live_at is refused at construction."""
    with pytest.raises(ValueError, match="timezone-aware"):
        FreshnessProof(
            built_from_live_at=datetime(2026, 7, 29, 12, 0, 0),  # naive
            content_digest="d0",
            sla_seconds=3600,
        )


def test_freshness_proof_accepts_aware_non_utc_offset() -> None:
    """[H2] guards NAIVE, not non-UTC: an aware fixed-offset instant is accepted."""
    aware_plus_two = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    proof = FreshnessProof(built_from_live_at=aware_plus_two, content_digest="d0", sla_seconds=60)
    assert proof.built_from_live_at is aware_plus_two


# --------------------------------------------------------------------------- #
# is_provable — verdicts + [H2] naive-now guard
# --------------------------------------------------------------------------- #


def test_provable_when_fresh_and_digest_matches() -> None:
    proof = _proof(built=_T0, digest="abc", sla=3600)
    assert is_provable(proof, "abc", _T0 + timedelta(seconds=10)) is Provability.PROVABLE


def test_stale_when_age_exceeds_sla() -> None:
    proof = _proof(built=_T0, digest="abc", sla=100)
    assert is_provable(proof, "abc", _T0 + timedelta(seconds=101)) is Provability.STALE


def test_age_boundary_is_inclusive() -> None:
    """age == sla is PROVABLE (<=); one second past is STALE."""
    proof = _proof(built=_T0, digest="abc", sla=100)
    assert is_provable(proof, "abc", _T0 + timedelta(seconds=100)) is Provability.PROVABLE
    assert (
        is_provable(proof, "abc", _T0 + timedelta(seconds=100, microseconds=1)) is Provability.STALE
    )


def test_corrupt_when_digest_mismatches_but_age_is_fresh() -> None:
    proof = _proof(built=_T0, digest="abc", sla=3600)
    assert is_provable(proof, "XYZ", _T0 + timedelta(seconds=10)) is Provability.CORRUPT


def test_stale_takes_precedence_over_corrupt() -> None:
    """When both fail, the age arm (STALE) is reported first per the frozen contract."""
    proof = _proof(built=_T0, digest="abc", sla=100)
    assert is_provable(proof, "MISMATCH", _T0 + timedelta(seconds=200)) is Provability.STALE


def test_is_provable_rejects_naive_now() -> None:
    """[H2]: a naive now is refused (monotonic decay only holds in UTC)."""
    proof = _proof()
    with pytest.raises(ValueError, match="timezone-aware"):
        is_provable(proof, proof.content_digest, datetime(2026, 7, 29, 12, 0, 0))  # naive


def test_real_content_change_is_not_provable_as_same() -> None:
    """End-to-end: a proof over frame A, served frame B (value changed) -> CORRUPT.

    Ties the digest law to the provability verdict: real content change ->
    digest differs -> not provable-as-same.
    """
    frame_a = _frame([_offer_row(cost="500")])
    frame_b = _frame([_offer_row(cost="600")])
    proof = _proof(built=_T0, digest=canonical_digest(frame_a), sla=3600)
    verdict = is_provable(proof, canonical_digest(frame_b), _T0 + timedelta(seconds=1))
    assert verdict is Provability.CORRUPT


# --------------------------------------------------------------------------- #
# C1 MIN-fold — built_from_live_at = MIN over section content-fetch instants
# --------------------------------------------------------------------------- #


def test_fold_returns_the_stalest_section_instant() -> None:
    fresh = _T0
    stale = _T0 - timedelta(hours=3)
    folded = fold_built_from_live_at(
        {"sec-a": fresh, "sec-b": stale, "sec-c": _T0 - timedelta(hours=1)}
    )
    assert folded == stale


def test_fold_single_section_returns_its_instant() -> None:
    assert fold_built_from_live_at({"only": _T0}) == _T0


def test_reused_stale_section_drags_artifact_age_back(  # AV-1 regression
) -> None:
    """AV-1: re-fetching one section but REUSING a stale one keeps the artifact old.

    A probe cannot advance an instant — only a content fetch does — so a reused
    (not re-fetched) section honestly keeps its old instant and the MIN-fold ages
    the whole artifact by its stalest constituent.
    """
    stale_reused = _T0 - timedelta(days=1)
    # section A re-fetched to now, section B reused-stale
    before = fold_built_from_live_at({"a": _T0 - timedelta(hours=2), "b": stale_reused})
    after_refetch_a = fold_built_from_live_at({"a": _T0, "b": stale_reused})
    assert before == stale_reused
    assert after_refetch_a == stale_reused  # advancing A did NOT freshen the artifact


def test_fold_rejects_empty_provenance() -> None:
    with pytest.raises(ValueError, match="empty section-provenance"):
        fold_built_from_live_at({})


def test_fold_rejects_naive_section_instant() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        fold_built_from_live_at({"sec-a": datetime(2026, 7, 29, 12, 0, 0)})  # naive


# --------------------------------------------------------------------------- #
# C8 — sla_seconds sourced from the entity registry (no new config home)
# --------------------------------------------------------------------------- #


def test_sla_seconds_for_reads_the_registry_ttl() -> None:
    """C8: offer's SLA IS the registry's default_ttl_seconds (180s), not a new home."""
    assert sla_seconds_for(EntityType.OFFER) == 180


def test_sla_seconds_per_entity_is_discoverable() -> None:
    """Per-entity SLA values are discoverable and distinct (business 3600 vs offer 180)."""
    assert sla_seconds_for(EntityType.BUSINESS) == 3600
    assert sla_seconds_for(EntityType.OFFER) == 180
    assert sla_seconds_for(EntityType.BUSINESS) != sla_seconds_for(EntityType.OFFER)


def test_sla_seconds_for_unregistered_entity_fails_loud() -> None:
    """An entity with no registry descriptor has no governed SLA — fail loud."""
    with pytest.raises(ValueError, match="no entity-registry descriptor"):
        sla_seconds_for(EntityType.UNKNOWN)
