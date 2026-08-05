"""WS-A PR-2 -- the PURE enrollment-intent projection (no I/O).

GRANDEUR ANCHOR (the throughline this projection serves):
    "ONE intent surface reaching the gate through ONE governed, role-guarded,
    receipted write path; intent default-open, EXECUTION fail-closed; no silent
    enrollment states -- a bridge that cannot prove its frame is real REFUSES
    loudly and writes NOTHING."

Design of record: ``.ledge/specs/TDD-ws-a-intent-gate-bridge-2026-08-05.md``
(autom8y repo) §3.1 frame contract, §3.2 the R1 coercion point, §3.3 phone
authority, §3.6 the refusal predicate set. This module is the pure half; the
Lambda that performs the S3 reads and the governed PATCH is WS-A PR-3
(``lambda_handlers/enrollment_intent_bridge.py``).

------------------------------------------------------------------------------
THREE FRAMES, EACH READ FOR WHAT IT IS AUTHORITATIVE ABOUT (TDD §3.1)
------------------------------------------------------------------------------
The separation is not fastidiousness -- each frame is sound for its own role and
UNSOUND for the others:

  INTENT    ``unit_holder`` (project 1204433992667196)
            ``custom_cal_status`` is ``cf:``-sourced NATIVELY on the UnitHolder
            task (UNIT_HOLDER_SCHEMA, PR #316) -- zero ancestor traversal, so the
            depth-1 cascade-walk defect (CARD WS-B/1) cannot dark it.
            ★ The OFFER frame's ``custom_cal_status`` is measured at 2/4191 =
            0.05% populated on a FRESH frame and WS-B deliberately does NOT
            repair it. Reading intent from the offer frame is the defect this
            module exists to avoid.

  IDENTITY  ``business`` (project 1200653012566782)
            ``office_phone`` is THE GATE KEY and the Business tier is its origin
            (2400/2572 = 93.3%). ``company_id`` is a CROSS-CHECK, never a filter.

  ROSTER    ``offer`` (project 1143843662099250)
            ``section`` / ``is_completed`` / ``office_phone`` ONLY. Charter R7:
            "the offer frame is the roster authority." These three columns are
            native or locally-stamped -- NOT ``cascade:``-dependent -- so they are
            untouched by the collapse that darkened ``custom_cal_status``.

Joins:
  * INTENT x IDENTITY on ``unit_holder.parent_gid == business.gid`` (2082/2082 =
    100.0% -- the intact office spine).
  * (INTENT x IDENTITY) x ROSTER as a SET INTERSECTION on ``office_phone``
    (strip-only), NOT a row join: the spine supplies intent+identity and the
    offer frame answers exactly one question -- "is this phone on the
    active/activating roster?"

------------------------------------------------------------------------------
★ UNIVERSE FILTER -- DELIBERATELY DIFFERENT FROM THE PRODUCER'S (R-12)
------------------------------------------------------------------------------
The WS-B producer (``lambda_handlers/scheduling_stratum_snapshot.py``) filters its
universe to ``DISTINCT NON-NULL company_id`` because its downstream substrate is
guid-keyed. **This module MUST NOT copy that filter.** The scheduling gate is
PHONE-keyed (``business_offers.office_phone``), so the universe here is
``NON-NULL office_phone`` on the joined spine, intersected with the active roster.

Copying the producer's guid filter would silently inherit CARD WS-B/3 -- the
active offices whose Business ancestor carries no ``Company ID``. Those offices
are enrollment-INVISIBLE to the guid-keyed producer yet perfectly REACHABLE by a
phone-keyed writer. ``company_id`` is therefore a **cross-check, never a filter**:
where present it corroborates identity (and a phone mapping to >1 distinct guid is
counted as ``guid_ambiguous_phones``); where absent, the office still enrolls on
its phone and is counted as ``guid_null_in_scope``.

This is precisely the kind of thing a build leg copies from the adjacent module,
so it carries a dedicated two-sided test (``test_intent_projection.py``
``TestR12UniverseFilterIsPhoneNotGuid``).

------------------------------------------------------------------------------
★ R1 -- EXACTLY ONE COERCION POINT (TDD §3.2)
------------------------------------------------------------------------------
:func:`~autom8_asana.normalizer.scheduling_extractor.derive_enrolled` is REUSED BY
IMPORT. It is not redefined, not re-inlined, and its INACTIVE alias set is not
forked. A second definition of R1 is the exact failure the charter is written
against.

``intent_source`` is provenance ONLY. :data:`ACTIVE_STATUS_ALIASES` exists solely
to split the ``True`` bit into ``explicit_enabled`` vs ``unknown_option_defaulted``
for the receipt; it NEVER participates in the bit. That invariant is pinned by
``test_provenance_never_changes_the_bit``, which asserts
``intent_enabled == derive_enrolled(raw)`` across the whole vocabulary.

------------------------------------------------------------------------------
★ PHONE AUTHORITY (TDD §3.3) -- one value, one authority, one use for the copy
------------------------------------------------------------------------------
``office_phone`` appears on TWO of the three frames and they are the same value:
the Business tier owns it and ``persistence/cascade.py`` stamps it DOWNWARD onto
the Offer task.

  * ``business.office_phone`` is AUTHORITATIVE -- the origin. Every gate write is
    keyed from here.
  * ``offer.office_phone`` is the ROSTER JOIN ONLY -- the stamped copy. Used
    solely to answer "is this phone on the active roster?", NEVER as a write key.

Normalization is STRIP-ONLY on both sides. Do NOT introduce E.164
canonicalization here: a punctuation-normalizing join would silently merge
distinct offices, and a format mismatch would silently match nothing while the
bridge looked healthy. R-11 (stamped-copy divergence) is SIZED, not assumed away:
:attr:`ProjectionCounts.roster_only_phones` and
:attr:`ProjectionCounts.out_of_scope_phones` are the two directions of the
residual.

------------------------------------------------------------------------------
★ REFUSALS -- THE STRUCTURAL CURE FOR THE MASS-ENROLLMENT EDGE (TDD §3.6)
------------------------------------------------------------------------------
``derive_enrolled(None) -> True`` is POLICY, so a fossil/collapsed/schema-lagged
frame would project null intent for every reachable office, coerce each to
Enabled *correctly per policy*, and write it through the governed path *correctly
per R4*: mass silent enrollment executed flawlessly by a system with no defect in
it. ``EDGE-bridge-arm-after-PT02`` governs the SEQUENCE; these predicates make the
failure UNREPRESENTABLE regardless of sequencing:

  :func:`assert_intent_columns_present`  schema-lag  -> ``FrameSchemaLagError``
  :func:`assert_frames_fresh`            staleness   -> ``EnrollmentRefusedError``
  :func:`assert_universe_floor`          collapse    -> ``EnrollmentRefusedError``
  :func:`assert_delta_within_ceiling`    mass-change -> ``EnrollmentRefusedError``

All four REFUSE THE WHOLE CYCLE and write NOTHING. A partially-applied cycle
against a degenerate frame is strictly worse than no cycle: it writes real gate
state from unreal intent and leaves no single point to reverse.

★ ``assert_frame_fresh`` and ``active_roster_phones`` are REUSED BY IMPORT from
the WS-E tripwire (their public API) rather than re-derived -- including
``assert_frame_fresh``'s "unprovable age is itself a refusal" leg. The floor
predicate is deliberately NOT ``assert_posture_signal_floor``:
``MIN_POSTURE_SIGNAL_ROWS = 1`` (``scheduling_stratum_snapshot.py``) would pass the
observed 932 -> 1-44 collapse untouched (CARD WS-B/4). Reuse the SHAPE, re-derive
the THRESHOLD.

------------------------------------------------------------------------------
DISJOINTNESS FROM WS-E (do not conflate -- named in both modules by design)
------------------------------------------------------------------------------
The WS-E tripwire (``traffic_offer_divergence_tripwire.py``) surfaces offices
TRADING WITHOUT A ROSTER ROW and deliberately excludes ``scheduling_gate_rejected``.
WS-A closes the complementary class: ROSTER-ENABLED BUT GATE-DECLINED. WS-E is the
instrument that points at this lineage; this module is the R1 instrument itself.
They must never be merged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire import (
    EvaluationRefusedError,
    active_roster_phones,
    assert_frame_fresh,
)
from autom8_asana.normalizer.scheduling_extractor import (
    _INACTIVE_STATUS_ALIASES,
    FrameSchemaLagError,
    _normalize_status,
    derive_enrolled,
)
from autom8_asana.storage_namespace import DATAFRAMES_V2

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    import polars as pl

# ==============================================================================
# Frame identity (project gids + S3 key layout)
# ==============================================================================
#: The UnitHolder project gid -- the INTENT frame (UNIT_HOLDER_SCHEMA, PR #316).
UNIT_HOLDER_PROJECT_GID = "1204433992667196"
#: The Business project gid -- the IDENTITY frame (authoritative ``office_phone``).
BUSINESS_PROJECT_GID = "1200653012566782"
#: The Offer project gid -- the ROSTER frame (charter R7). Same gid the WS-E
#: tripwire reads; this module consumes only section/is_completed/office_phone.
OFFER_PROJECT_GID = "1143843662099250"


def frame_key(project_gid: str, entity: str) -> str:
    """S3 key of a warmed merged frame under the DATAFRAMES_V2 plane prefix.

    The prefix is DERIVED from the storage-namespace registry
    (``DATAFRAMES_V2.prefix``), never hand-pinned, so the namespace contract holds
    and the resolved key is byte-identical to the warmer's write key.
    """
    return f"{DATAFRAMES_V2.prefix}{project_gid}/{entity}/dataframe.parquet"


#: The three warmed frames this projection consumes, in read order.
UNIT_HOLDER_FRAME_KEY = frame_key(UNIT_HOLDER_PROJECT_GID, "unit_holder")
BUSINESS_FRAME_KEY = frame_key(BUSINESS_PROJECT_GID, "business")
OFFER_FRAME_KEY = frame_key(OFFER_PROJECT_GID, "offer")


# ==============================================================================
# Required columns (schema-lag surface) -- a rename REFUSES, never projects nulls
# ==============================================================================
# R-2 (cross-repo frame-schema desync, the WS-E hazard class): these tuples are
# the assertion surface AND are exported in __all__ so a rename trips CI rather
# than production. Absence is SCHEMA-LAG -> FrameSchemaLagError -> REFUSE.

#: INTENT frame. ``custom_cal_status`` is the R1 input; ``parent_gid`` joins onto
#: ``business.gid``; ``last_modified`` + ``gid`` are the representative tie-break.
REQUIRED_UNIT_HOLDER_COLUMNS: tuple[str, ...] = (
    "gid",
    "parent_gid",
    "custom_cal_status",
    "last_modified",
)
#: IDENTITY frame. ``office_phone`` is the gate key; ``company_id`` is the
#: cross-check (REQUIRED to be PRESENT as a column, never required to be POPULATED
#: -- see the R-12 universe note in the module docstring).
REQUIRED_BUSINESS_COLUMNS: tuple[str, ...] = ("gid", "office_phone", "company_id")
#: ROSTER frame. Identical to the WS-E tripwire's REQUIRED_OFFER_COLUMNS -- the two
#: instruments ask the offer frame the same roster question.
REQUIRED_OFFER_COLUMNS: tuple[str, ...] = ("office_phone", "section", "is_completed")


# ==============================================================================
# Intent provenance vocabulary (DIAGNOSTIC ONLY -- never touches the bit)
# ==============================================================================
#: ``intent_source`` values, carried into the ``scheduling_config_updated`` receipt
#: via the PATCH body's ``intent_source`` passthrough. They make the charter's
#: ratified silence-means-integrate VISIBLE in every receipt, which is what keeps
#: the policy honest and auditable.
INTENT_SOURCE_EXPLICIT_ENABLED = "explicit_enabled"
INTENT_SOURCE_EXPLICIT_DISABLED = "explicit_disabled"
INTENT_SOURCE_COERCED_UNSET = "coerced_unset"
INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED = "unknown_option_defaulted"

INTENT_SOURCES: frozenset[str] = frozenset(
    {
        INTENT_SOURCE_EXPLICIT_ENABLED,
        INTENT_SOURCE_EXPLICIT_DISABLED,
        INTENT_SOURCE_COERCED_UNSET,
        INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED,
    }
)

#: ★ DIAGNOSTIC MIRROR of ``_INACTIVE_STATUS_ALIASES`` -- the recognized ACTIVE
#: option names. This set exists ONLY to split ``derive_enrolled(...) is True``
#: into ``explicit_enabled`` (a recognized ACTIVE option) vs
#: ``unknown_option_defaulted`` (an option nobody has seen before, which R1 still
#: defaults to Enabled).
#:
#: It is NOT a fork of R1 and it is NOT policy: the enrolled bit is 100%
#: ``derive_enrolled``. If this set drifts from the live Asana vocabulary the ONLY
#: consequence is a receipt reading ``unknown_option_defaulted`` instead of
#: ``explicit_enabled`` -- a strictly LOUDER label, never a different gate state.
#: ``test_provenance_never_changes_the_bit`` pins that invariant mechanically.
ACTIVE_STATUS_ALIASES: frozenset[str] = frozenset(
    {"active", "enabled", "enable", "true", "on", "1"}
)


# ==============================================================================
# Refusal grammar (REUSED from the WS-E tripwire, not invented)
# ==============================================================================


class EnrollmentRefusedError(EvaluationRefusedError):
    """The projection could not be proven sound -- REFUSE the CYCLE, write NOTHING.

    Subclasses the WS-E tripwire's :class:`EvaluationRefusedError` so the refusal
    grammar (``EvaluationRefused``-style emit, bounded ``reason`` dimension, no
    verdict, no writes) is REUSED rather than re-invented, while still being
    distinguishable by type at the bridge boundary.

    Raised by the freshness, universe-floor, and delta-ceiling gates. Schema-lag
    raises :class:`FrameSchemaLagError` instead (also a refusal; a different
    remediation -- the columns do not exist yet).
    """


def assert_intent_columns_present(
    *,
    unit_holder_columns: Iterable[str],
    business_columns: Iterable[str],
    offer_columns: Iterable[str],
) -> None:
    """SCHEMA-LAG gate: every required column on every frame, or REFUSE.

    ★ This is the gate that fires TODAY. Until WS-B PR-1 (``UNIT_HOLDER_SCHEMA``)
    is DEPLOYED **and one warmer cycle has completed**, the ``unit_holder`` frame
    carries no posture columns at all -- so a dry run REFUSES loudly here. That is
    the designed outcome, and it is a structural improvement over the superseded
    frame contract: under that contract the intent columns were PRESENT BUT NULL,
    which ``derive_enrolled`` coerces to Enabled *silently*. ABSENT columns refuse;
    NULL columns enroll. The contract change converts the failure mode from silent
    mass-enable to loud refusal.

    Raises:
        FrameSchemaLagError: naming every missing column, per frame. Never
            fabricate posture from a frame that cannot carry it.
    """
    missing: list[str] = []
    for label, required, present in (
        ("unit_holder", REQUIRED_UNIT_HOLDER_COLUMNS, set(unit_holder_columns)),
        ("business", REQUIRED_BUSINESS_COLUMNS, set(business_columns)),
        ("offer", REQUIRED_OFFER_COLUMNS, set(offer_columns)),
    ):
        missing.extend(f"{label}.{col}" for col in required if col not in present)
    if missing:
        raise FrameSchemaLagError(
            f"enrollment frames lack required columns {missing} (schema-lag). The "
            "unit_holder posture columns arrive with WS-B PR-1 (UNIT_HOLDER_SCHEMA) "
            "and require one completed WARMER cycle -- not merely a merge. Refusing "
            "to project intent from frames that cannot carry it."
        )


def assert_frames_fresh(
    frame_ages: Sequence[tuple[str, float | None]],
    *,
    now_epoch: float,
    ceiling_seconds: float,
) -> None:
    """FRESHNESS gate applied to EACH of the three frames INDEPENDENTLY.

    ★ Bound to the OFFICE SPINE, not to the offer frame alone: a fresh offer frame
    says nothing about whether the INTENT source is fresh, and the intent source is
    the one that can mass-enroll. Any frame absent, unreadable, or of unprovable
    age is a refusal for the whole cycle (``source_complete = False``).

    The per-frame predicate is the WS-E tripwire's
    :func:`~autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire.assert_frame_fresh`
    REUSED VERBATIM -- including its ``None -> refuse`` leg, so a missing
    ``LastModified`` can never read as fresh. Only the reason string is
    re-attributed to the offending frame.

    Args:
        frame_ages: ``(frame_label, last_modified_epoch_or_None)`` per frame.
        now_epoch: evaluation time.
        ceiling_seconds: maximum admissible age.

    Raises:
        EnrollmentRefusedError: naming the frame that failed.
    """
    for label, last_modified_epoch in frame_ages:
        try:
            assert_frame_fresh(
                last_modified_epoch,
                now_epoch=now_epoch,
                ceiling_seconds=ceiling_seconds,
            )
        except EvaluationRefusedError as exc:
            raise EnrollmentRefusedError(f"frame '{label}' unusable: {exc}") from exc


def assert_universe_floor(in_scope_phone_count: int, *, floor: int) -> None:
    """UNIVERSE-FLOOR gate: refuse a collapsed office spine.

    ★ The floor is BASELINE-RELATIVE and is NOT defined in this module. It is
    supplied by the caller from the live recovered universe measured at build
    entry (TDD §6, measurement E-2). A floor invented here would be a fabricated
    threshold: the DIAG's ~921-guid / 475-guard anchor is the GUID-side number
    over a different filter, and this universe is PHONE-side. Derive; do not
    transpose.

    ★ Deliberately NOT ``assert_posture_signal_floor``: ``MIN_POSTURE_SIGNAL_ROWS
    = 1`` would pass the observed 932 -> 1-44 collapse untouched (CARD WS-B/4).
    Once the universe is ~900, a 1-row floor is close to no floor.

    Raises:
        EnrollmentRefusedError: when the in-scope universe is below the floor.
    """
    if floor <= 0:
        # ★ A refusal that withholds the number needed to fix it is a dead end. The
        # OBSERVED universe is named here so a dry-run against an unset floor tells
        # the operator exactly what to set it from -- refuse loudly AND usefully.
        raise EnrollmentRefusedError(
            f"universe floor is unset or non-positive ({floor}) -- refusing rather "
            "than running against an unbounded universe. Observed in-scope universe "
            f"this cycle: {in_scope_phone_count} phones. Set the floor from the live "
            "recovered universe (TDD build-entry measurement E-2, phone-side); it is "
            "deliberately not defaulted, because a guessed floor is no floor."
        )
    if in_scope_phone_count < floor:
        raise EnrollmentRefusedError(
            f"in-scope universe collapsed: {in_scope_phone_count} phones < floor "
            f"{floor}. A collapsed or fossil frame projects null intent, which R1 "
            "coerces to Enabled -- refusing the whole cycle rather than mass-enrolling."
        )


def assert_delta_within_ceiling(delta_count: int, *, ceiling: int) -> None:
    """MASS-CHANGE gate: refuse the WHOLE cycle when the flip-delta is too large.

    The operator-direction brake (the charter second-look: a bulk Asana mishap --
    mass field wipe -> mass UNSET -- reads as mass-Enable). The freshness and floor
    predicates are the same brake from the fossil-frame direction.

    ★ REFUSE WHOLE, never partially apply. A half-applied mass change writes real
    gate state from unreal intent and leaves no single point to reverse.

    Raises:
        EnrollmentRefusedError: when ``delta_count > ceiling``.
    """
    if ceiling <= 0:
        # ★ Same discipline as the floor: name the OBSERVED delta so a dry-run
        # against an unset ceiling is the very instrument that sizes it. Without
        # this, the pre-arm observation cycle could never report the number the
        # operator needs, and the ceiling would end up guessed.
        raise EnrollmentRefusedError(
            f"delta ceiling is unset or non-positive ({ceiling}) -- refusing rather "
            "than running without a mass-change brake. Observed flip-delta this "
            f"cycle: {delta_count} offices. Size the ceiling from a watched dry-run."
        )
    if delta_count > ceiling:
        raise EnrollmentRefusedError(
            f"delta ceiling tripped: {delta_count} offices would change state > "
            f"ceiling {ceiling}. Refusing the WHOLE cycle (never a partial apply) -- "
            "a mass intent change is an operator event, not a sync event."
        )


# ==============================================================================
# Projection value types
# ==============================================================================


class EnrollmentIntent(NamedTuple):
    """One in-scope office's projected intent, keyed by the AUTHORITATIVE phone.

    ``office_phone`` comes from ``business.office_phone`` (the origin), never from
    the offer frame's stamped copy. ``company_id`` is carried for the receipt as a
    CROSS-CHECK and may be ``None`` -- a guid-less office is fully enrollable here
    (R-12).
    """

    office_phone: str
    intent_enabled: bool
    intent_raw: str | None
    intent_source: str
    business_gid: str
    unit_holder_gid: str
    company_id: str | None


class ProjectionCounts(NamedTuple):
    """Bounded, non-PII counters -- the cycle-summary and metric surface.

    Every disposition the projection can reach is counted here. NFR-5 (every
    unresolved office appears in exactly one queue line per cycle) reconciles the
    per-office lines against these denominators.
    """

    #: Rows on the joined office spine (unit_holder x business) BEFORE the phone filter.
    spine_rows: int
    #: Spine rows dropped for a null/blank ``office_phone``. Mirrors the producer's
    #: guid-less DROP: fail SAFE by absence, never a fabricated identity.
    phoneless_dropped: int
    #: Distinct authoritative phones on the spine.
    spine_phones: int
    #: Distinct phones on the ACTIVE/ACTIVATING, non-completed offer roster.
    roster_phones: int
    #: The bridge's universe: spine phones ∩ roster phones.
    in_scope_phones: int
    #: R-11 direction A -- spine phones NOT on the active roster (R3: out of scope).
    out_of_scope_phones: int
    #: ★ R-11 direction B -- active-roster phones with NO office-spine row. The
    #: SILENTLY-EXCLUDED set (a stale/missing downward phone stamp, or an office
    #: whose UnitHolder is absent). Counted and emitted, never guessed.
    roster_only_phones: int
    #: Phones whose spine rows disagree on a non-null ``custom_cal_status``. Metered
    #: as DRIFT; does NOT block the cycle (same policy as the producer).
    status_drift_phones: int
    #: ★ R-12 -- in-scope offices reachable by phone whose ``company_id`` is NULL.
    #: Invisible to the guid-keyed producer; enrolled normally here.
    guid_null_in_scope: int
    #: Cross-check failure -- an in-scope phone mapping to >1 distinct non-null
    #: ``company_id``. Counted and emitted; the phone still enrolls (the guid is a
    #: diagnostic, and refusing an office over a diagnostic would be the wrong
    #: fail-direction).
    guid_ambiguous_phones: int
    #: intent_source split (the R1 audit surface).
    explicit_enabled: int
    explicit_disabled: int
    coerced_unset: int
    unknown_option_defaulted: int


class EnrollmentProjection(NamedTuple):
    """What :func:`project_enrollment_intent` returns."""

    intents: tuple[EnrollmentIntent, ...]
    counts: ProjectionCounts


# ==============================================================================
# PURE helpers
# ==============================================================================


def norm_phone(value: Any) -> str:
    """Normalize a phone to its comparison form -- STRIP-ONLY (TDD §3.3).

    Identical semantics to the WS-E tripwire's ``_norm_phone``. Deliberately
    conservative: every ``office_phone`` in play derives from the SAME
    ``Business.office_phone`` value, so they are byte-identical modulo whitespace.

    ★ Do NOT extend this to punctuation-stripping or E.164 canonicalization. Over-
    normalizing risks FALSE JOINS across distinct offices -- writing office X's
    enrollment onto office Y. Under-normalizing (this) risks a no-op, which the
    ``resolved == 0 while universe non-empty`` refusal and the UNRESOLVED counters
    make LOUD.
    """
    return str(value).strip() if value is not None else ""


def derive_intent_source(custom_cal_status: str | None) -> str:
    """Classify the PROVENANCE of the enrolled bit (diagnostic; never the bit).

    ``coerced_unset`` names the charter's ratified silence-means-integrate; making
    it visible in every receipt is what keeps R1 auditable rather than invisible.

    See :data:`ACTIVE_STATUS_ALIASES` for why the ACTIVE mirror cannot affect the
    gate outcome.
    """
    if custom_cal_status is None or not str(custom_cal_status).strip():
        return INTENT_SOURCE_COERCED_UNSET
    normalized = _normalize_status(str(custom_cal_status))
    if normalized in _INACTIVE_STATUS_ALIASES:
        return INTENT_SOURCE_EXPLICIT_DISABLED
    if normalized in ACTIVE_STATUS_ALIASES:
        return INTENT_SOURCE_EXPLICIT_ENABLED
    return INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED


def _blank_to_none(value: Any) -> str | None:
    """Collapse null/blank to ``None`` -- BIT-PRESERVING for R1.

    ``derive_enrolled(None)`` and ``derive_enrolled("")`` both return ``True``, so
    this normalization cannot change the gate outcome; it only lets a blank read as
    the honest ``coerced_unset`` provenance instead of a phantom explicit value.
    Pinned by ``test_blank_status_is_bit_identical_to_none``.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# ==============================================================================
# THE PROJECTION
# ==============================================================================


def project_enrollment_intent(
    unit_holder_df: pl.DataFrame,
    business_df: pl.DataFrame,
    offer_df: pl.DataFrame,
) -> EnrollmentProjection:
    """Project Asana enrollment intent onto the phone-keyed scheduling-gate universe.

    PURE: no I/O, no clock, no environment. The caller (WS-A PR-3) performs the S3
    reads, applies the freshness/floor/delta refusals, and drives the governed
    PATCH.

    Pipeline:
      1. SCHEMA-LAG gate on all three frames (:func:`assert_intent_columns_present`).
      2. Join INTENT x IDENTITY on ``unit_holder.parent_gid == business.gid``.
      3. DROP spine rows with a null/blank authoritative ``office_phone`` (counted).
      4. Collapse to ONE deterministic representative per phone -- max
         ``last_modified``, tie-broken by ``gid`` descending. Identical rule to the
         producer's ``project_offer_frame``, so the two instruments cannot disagree
         about which row speaks for an office.
      5. Intersect with the ACTIVE/ACTIVATING roster (the WS-E predicate, reused).
      6. Project ``intent_enabled`` via ``derive_enrolled`` + provenance.

    ★ Offices outside the active/activating roster are STRUCTURALLY ABSENT from
    ``intents`` -- the R3 wall. A Sales-Process office cannot be written by this
    bridge because it never enters the output, not because a downstream check
    happens to skip it.

    Raises:
        FrameSchemaLagError: any required column absent on any frame.
    """
    import polars as pl

    assert_intent_columns_present(
        unit_holder_columns=unit_holder_df.columns,
        business_columns=business_df.columns,
        offer_columns=offer_df.columns,
    )

    # --- 2. INTENT x IDENTITY on the office spine -----------------------------
    # Suffix collision guard: BASE_COLUMNS are shared by both frames (gid, name,
    # last_modified, ...). Select exactly what each frame is authoritative for, so
    # no ambiguity about which frame a column came from can arise.
    uh = unit_holder_df.select(
        pl.col("gid").cast(pl.Utf8).alias("unit_holder_gid"),
        pl.col("parent_gid").cast(pl.Utf8).alias("_parent_gid"),
        pl.col("custom_cal_status").cast(pl.Utf8).alias("custom_cal_status"),
        pl.col("last_modified").alias("_last_modified"),
    )
    biz = business_df.select(
        pl.col("gid").cast(pl.Utf8).alias("business_gid"),
        # AUTHORITATIVE phone (TDD §3.3) -- the origin, never the stamped copy.
        pl.col("office_phone").cast(pl.Utf8).str.strip_chars().alias("office_phone"),
        pl.col("company_id").cast(pl.Utf8).str.strip_chars().alias("company_id"),
    )
    spine = uh.join(biz, left_on="_parent_gid", right_on="business_gid", how="inner")
    # `join` consumes the right key; restore it under its own name for the receipt.
    spine = spine.with_columns(pl.col("_parent_gid").alias("business_gid"))
    spine_rows = spine.height

    # --- 3. Phone filter -- the UNIVERSE (phone-keyed, NOT the producer's guid) --
    phoned = spine.filter(pl.col("office_phone").is_not_null() & (pl.col("office_phone") != ""))
    phoneless_dropped = spine_rows - phoned.height

    # --- 4. Deterministic representative per phone ----------------------------
    # Drift BEFORE the collapse (the collapse hides the disagreement by design).
    if phoned.height:
        drift_phones = set(
            phoned.filter(
                pl.col("custom_cal_status").is_not_null()
                & (pl.col("custom_cal_status").str.strip_chars() != "")
            )
            .group_by("office_phone")
            .agg(pl.col("custom_cal_status").n_unique().alias("_n"))
            .filter(pl.col("_n") > 1)
            .get_column("office_phone")
            .to_list()
        )
        # ★ CROSS-CHECK, never a filter: a phone carrying >1 distinct non-null guid
        # is an identity ambiguity worth emitting -- it does NOT exclude the office.
        ambiguous_guid_phones = set(
            phoned.filter(pl.col("company_id").is_not_null() & (pl.col("company_id") != ""))
            .group_by("office_phone")
            .agg(pl.col("company_id").n_unique().alias("_n"))
            .filter(pl.col("_n") > 1)
            .get_column("office_phone")
            .to_list()
        )
        representatives = phoned.sort(
            ["_last_modified", "unit_holder_gid"],
            descending=[True, True],
            nulls_last=True,
        ).unique(subset=["office_phone"], keep="first", maintain_order=True)
    else:
        drift_phones = set()
        ambiguous_guid_phones = set()
        representatives = phoned

    spine_phones = {norm_phone(p) for p in representatives.get_column("office_phone").to_list()}

    # --- 5. Roster intersection (the R3 wall) ---------------------------------
    # REUSED from WS-E: classify(section) in billable_sections AND NOT is_completed.
    roster = active_roster_phones(offer_df)
    in_scope = spine_phones & roster
    # ★ R-11 both directions, sized rather than assumed away.
    out_of_scope = spine_phones - roster
    roster_only = roster - spine_phones

    # --- 6. Project intent ----------------------------------------------------
    intents: list[EnrollmentIntent] = []
    guid_null_in_scope = 0
    source_counts = dict.fromkeys(INTENT_SOURCES, 0)

    for row in representatives.iter_rows(named=True):
        phone = norm_phone(row["office_phone"])
        if phone not in in_scope:
            continue
        raw = _blank_to_none(row["custom_cal_status"])
        # ★ R1: the ONE coercion point, reused by import. Never re-derived here.
        enabled = derive_enrolled(raw)
        source = derive_intent_source(raw)
        source_counts[source] += 1
        company_id = _blank_to_none(row["company_id"])
        if company_id is None:
            guid_null_in_scope += 1
        intents.append(
            EnrollmentIntent(
                office_phone=phone,
                intent_enabled=enabled,
                intent_raw=raw,
                intent_source=source,
                business_gid=str(row["business_gid"]),
                unit_holder_gid=str(row["unit_holder_gid"]),
                company_id=company_id,
            )
        )

    counts = ProjectionCounts(
        spine_rows=spine_rows,
        phoneless_dropped=phoneless_dropped,
        spine_phones=len(spine_phones),
        roster_phones=len(roster),
        in_scope_phones=len(in_scope),
        out_of_scope_phones=len(out_of_scope),
        roster_only_phones=len(roster_only),
        status_drift_phones=len(drift_phones & in_scope),
        guid_null_in_scope=guid_null_in_scope,
        guid_ambiguous_phones=len(ambiguous_guid_phones & in_scope),
        explicit_enabled=source_counts[INTENT_SOURCE_EXPLICIT_ENABLED],
        explicit_disabled=source_counts[INTENT_SOURCE_EXPLICIT_DISABLED],
        coerced_unset=source_counts[INTENT_SOURCE_COERCED_UNSET],
        unknown_option_defaulted=source_counts[INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED],
    )
    # Deterministic output order (phone ascending) so a cycle summary and its
    # per-office lines are byte-stable across runs on identical input.
    return EnrollmentProjection(
        intents=tuple(sorted(intents, key=lambda i: i.office_phone)),
        counts=counts,
    )


__all__ = [
    "ACTIVE_STATUS_ALIASES",
    "BUSINESS_FRAME_KEY",
    "BUSINESS_PROJECT_GID",
    "INTENT_SOURCES",
    "INTENT_SOURCE_COERCED_UNSET",
    "INTENT_SOURCE_EXPLICIT_DISABLED",
    "INTENT_SOURCE_EXPLICIT_ENABLED",
    "INTENT_SOURCE_UNKNOWN_OPTION_DEFAULTED",
    "OFFER_FRAME_KEY",
    "OFFER_PROJECT_GID",
    "REQUIRED_BUSINESS_COLUMNS",
    "REQUIRED_OFFER_COLUMNS",
    "REQUIRED_UNIT_HOLDER_COLUMNS",
    "UNIT_HOLDER_FRAME_KEY",
    "UNIT_HOLDER_PROJECT_GID",
    "EnrollmentIntent",
    "EnrollmentProjection",
    "EnrollmentRefusedError",
    "FrameSchemaLagError",
    "ProjectionCounts",
    "assert_delta_within_ceiling",
    "assert_frames_fresh",
    "assert_intent_columns_present",
    "assert_universe_floor",
    "derive_intent_source",
    "frame_key",
    "norm_phone",
    "project_enrollment_intent",
]
