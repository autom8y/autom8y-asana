"""S2 — FRESHNESS law tests (RC-B / F2). Two-sided (the P7 bar).

These prove the freshness-law bodies S2 fills in ``substrate.freshness``:

- ``canonical_digest`` five [H1] pins: value-column set, row order, parquet-
  independent encoding, null canonicalization, float canonicalization — proven
  BOTH ways (a value change moves the digest; a GID/layout change does not).
  Plus the DELTA fixes: F1 missing-column fail-loud, F2 thread-context-independence,
  F3 Decimal non-finite fail-loud, F4 the deliberate type-erasure pin, and a
  known-good byte-identity regression proving the fix touched no valid output.
- The v1 **D8** false-CLEAN pattern has no probe-stamp home on the S2 surface: a
  GID-set-preserving value edit changes the digest, no S2 verb advances freshness
  without a content fetch, and the honest floor (``dataclasses.replace`` re-stamp,
  [H2] holds through it) is documented (F7).
- ``is_provable`` verdicts + the [H2] naive-``now`` guard.
- ``FreshnessProof.__post_init__`` [H2] tz-reject + the frozen in-place-mutation block.
- ``fold_built_from_live_at`` MIN-fold incl. the AV-1 reused-stale-section
  regression (a reused old section honestly drags the artifact age back).
- ``sla_seconds_for`` (C8) reads the per-entity SLA from the entity registry.
"""

from __future__ import annotations

import decimal
import inspect
from dataclasses import replace
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
    MissingValueColumnsError,
    Provability,
    canonical_digest,
    fold_built_from_live_at,
    is_provable,
    sla_seconds_for,
)

_T0 = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)


def _offer_row(
    *,
    cost: object = "500",
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


def test_non_finite_float_in_value_column_fails_loud() -> None:
    """A NaN/inf float (a Float64 column CAN hold these) reaches the digest and fails loud."""
    for value in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="non-finite"):
            canonical_digest(_frame([_offer_row(mrr=value)]))


def test_non_finite_decimal_fails_loud_at_canonicalizer() -> None:
    """F3: Decimal NaN/Inf/sNaN is corruption — the guard rejects it at the canonicalizer.

    A polars Decimal column cannot physically hold a non-finite value (construction
    panics), so the F3 pin is asserted at ``_canon_number`` directly — the same locus
    the qa-adversary probed via object dtype. Regression: before the fix the guard was
    float-scoped, so Decimal NaN/Infinity canonicalized to strings colliding with the
    literals "NaN"/"Infinity", and Decimal sNaN escaped as InvalidOperation.
    """
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("sNaN")):
        with pytest.raises(ValueError, match="non-finite"):
            freshness._canon_number(value)


# --------------------------------------------------------------------------- #
# DELTA fixes — F1 (missing columns), F2 (context), F4 (type-erasure), regression
# --------------------------------------------------------------------------- #


def test_missing_value_column_fails_loud() -> None:
    """F1: a frame missing ANY pinned value column is refused, not silently digested.

    Regression: before the fix, ``canonical_digest`` filtered pinned columns by
    presence, so a foreign frame, a column-dropped frame, and even an empty frame
    all shared ONE digest — yielding PROVABLE over changed content (RC-B-1
    falsification). Now each goes loud.
    """
    foreign = pl.DataFrame([{"business_gid": "B-1", "active_mrr": 5000}])
    with pytest.raises(MissingValueColumnsError, match="missing pinned value column"):
        canonical_digest(foreign)
    column_dropped = _frame([_offer_row()]).drop("cost")
    with pytest.raises(MissingValueColumnsError, match="cost"):
        canonical_digest(column_dropped)


def test_empty_but_fully_columned_offer_frame_still_digests() -> None:
    """F1 boundary: a zero-row frame that HAS all four value columns keeps a defined digest."""
    empty_full = pl.DataFrame(
        schema={
            "cost": pl.Utf8,
            "mrr": pl.Float64,
            "offer_id": pl.Utf8,
            "weekly_ad_spend": pl.Float64,
        }
    )
    assert len(canonical_digest(empty_full)) == 64


def test_missing_value_columns_error_is_a_value_error() -> None:
    """The F1 named error subclasses ValueError so existing catch paths still work."""
    assert issubclass(MissingValueColumnsError, ValueError)


def test_digest_is_independent_of_ambient_decimal_context() -> None:
    """F2: a hostile thread-local decimal precision does NOT change the digest.

    Regression: ``Decimal.normalize()`` used the ambient thread-local context, so a
    library setting ``getcontext().prec = 5`` elsewhere in the process silently
    changed every digest. The fix pins a fixed local Context(prec=60).
    """
    frame = _frame([_offer_row(mrr=Decimal("1234.5678"), weekly_ad_spend=Decimal("99.99"))])
    baseline = canonical_digest(frame)
    with decimal.localcontext() as ctx:
        ctx.prec = 5
        under_hostile_context = canonical_digest(frame)
    assert baseline == under_hostile_context


def test_high_precision_decimal_neighbours_do_not_collide() -> None:
    """F2: 30-significant-digit neighbours stay distinct (default prec=28 would collide)."""
    a = canonical_digest(_frame([_offer_row(mrr=Decimal("1234567890123456789012345678.91"))]))
    b = canonical_digest(_frame([_offer_row(mrr=Decimal("1234567890123456789012345678.92"))]))
    assert a != b


def test_number_string_type_erasure_is_a_deliberate_pin() -> None:
    """F4: numeric 500 and string "500" (True vs "true") canonicalize identically.

    A DELIBERATE, documented pin property — the digest compares values, not Python
    types. Within one frozen schema a column's dtype is stable, so this is
    cross-representation convenience, not a production collision. Pinned either way.
    """
    numeric = canonical_digest(_frame([_offer_row(cost=500)]))
    string = canonical_digest(_frame([_offer_row(cost="500")]))
    assert numeric == string


def test_known_good_digests_are_byte_identical_regression() -> None:
    """The DELTA fix touched NO currently-valid canonical output (no scheme bump).

    These hex constants were captured from the pre-fix (536650d4) implementation.
    They pin the FROZEN v1.0 canonical output: any future change to a pin MUST bump
    ``_DIGEST_SCHEME`` and land these deliberately.
    """
    single = _frame(
        [
            _offer_row(
                gid="G", name="Acme", cost="500", mrr=1000.0, offer_id="OF-1", weekly_ad_spend=200.0
            )
        ]
    )
    multi = _frame(
        [
            _offer_row(
                gid="G1", name="A", cost="500", mrr=1000.0, offer_id="OF-1", weekly_ad_spend=200.0
            ),
            _offer_row(
                gid="G2",
                name="B",
                cost="750",
                mrr=Decimal("99.99"),
                offer_id="OF-2",
                weekly_ad_spend=0.0,
            ),
        ]
    )
    assert canonical_digest(single) == (
        "295f7ffee5b013d335867a0ec90ce050f66543d0cd141f91abdf81580ae4d3d4"
    )
    assert canonical_digest(multi) == (
        "1fabb37710022b0fcb27d429e8ae112109ef9aadb49504c6c04e947c482415fb"
    )


# --------------------------------------------------------------------------- #
# D8 false-CLEAN pattern has no probe-stamp home on the S2 surface (honest floor)
# --------------------------------------------------------------------------- #


def test_no_s2_verb_advances_freshness_without_a_content_fetch() -> None:
    """No probe-stamp verb on the S2 surface: nothing here freshens without content.

    Scoped honestly to the S2 surface (W9 never-overclaim): the module exposes no
    touch/refresh/stamp/mark-fresh verb, and the sole S2 producer of an instant is
    the fold, whose only input is content-fetch instants. (Proof-minting custody is
    an S3/S4 property — see the honest-floor ``dataclasses.replace`` test below.)
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


def test_freshness_proof_is_frozen_against_in_place_mutation() -> None:
    """A built proof is not re-stamped in place — normal attribute assignment raises."""
    proof = _proof()
    with pytest.raises(AttributeError):
        proof.built_from_live_at = datetime.now(tz=UTC)  # type: ignore[misc]


def test_dataclasses_replace_honest_floor_h2_holds() -> None:
    """F7 honest floor: ``dataclasses.replace`` CAN mint a re-stamped proof — but [H2] re-fires.

    S2 does not claim proof-minting is impossible (that custody is S3/S4). What it
    guarantees is that the [H2] tz-guard runs through ``replace`` too, so a re-stamp
    with a naive instant still fails loud.
    """
    proof = _proof(built=_T0)
    restamped = replace(proof, built_from_live_at=_T0 + timedelta(days=365))
    assert restamped.built_from_live_at == _T0 + timedelta(days=365)  # replace succeeds
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(proof, built_from_live_at=datetime(2026, 7, 29, 12, 0, 0))  # naive -> [H2] fires


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


def test_future_dated_proof_is_provable_negative_age_carry_to_s5() -> None:
    """F8: a future-dated proof (negative age) is PROVABLE under the frozen ``<= sla``.

    S2 does not alter the frozen predicate; this pins the behavior and marks the
    negative-age anomaly as a Seam-5 observability-emission carry.
    """
    proof = _proof(built=_T0 + timedelta(days=365), digest="abc", sla=100)
    assert is_provable(proof, "abc", _T0) is Provability.PROVABLE


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
