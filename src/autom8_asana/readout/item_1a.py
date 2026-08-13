"""Item-1a computation: the one say-able number of the recurring exec readout.

EX-5 (WS-2) of the exec-insight-delivery wave. Pure functions that turn a
``POST /v1/query/offer/rows`` response into item 1a — ``max(last_modified)``
grouped by section, floored to the ``min`` over constituents (DR-2) — together
with its typed ``k of n`` denominator (C-6 / DENOM-FENCE) and its per-render
G4' sign enumeration (C-5), including the truncation / §1.2b T-GUARD branch that
the design critique's FLAG F-2 required be declared.

Design anchors (all in ``autom8y-asana``):
  * SPEC-recurring-readout-template-2026-08-13.md §1 (the number), §3 (G4'),
    §4 (denominator / DENOM-FENCE).
  * CRITIQUE-recurring-readout-2026-08-13.md §2 FLAG F-2 (truncation branch).

DF-1 (the single easiest thing here to get wrong): this module reads ONLY the
``/rows`` response bytes handed to it. It imports NOTHING from ``query.temporal``
(``TemporalFilter``), ``section_timelines``, or the story cache. The figure is a
pure function of the served bytes — the same discipline as Lane-G co-sourcing
(``CONTRACT-offers-freshness-axis-frozen-2026-08-11.md:519-524``): if the figure
is a pure function of the bytes, no cross-surface contamination is expressible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class Item1aError(ValueError):
    """The response cannot yield a well-formed item-1a figure.

    Raised loudly rather than papering a missing say-able number over with a
    silent default — a silent narrow readout is the founding-wound shape this
    initiative exists to end. A readout with zero contributing constituents has
    no ``min`` floor to report (DR-2 is undefined over an empty set), so the
    mechanism refuses rather than inventing one.
    """


class G4PrimeSign(StrEnum):
    """The sign a branch contributes to item 1a's error, per the G4' gate.

    Item 1a measures *age* (``now - max(last_modified)``). A branch that makes
    the reported as-of read OLDER than the truth OVERSTATES the age — the
    alarm-safe, stale-forward direction. A branch that makes it read FRESHER
    would UNDERSTATE the age — the dangerous direction. ``NEUTRAL`` branches do
    not move the value at all.
    """

    NEUTRAL = "neutral"
    OVERSTATE_AGE = "overstate_age"  # reads OLDER than truth — alarm-safe
    UNDERSTATE_AGE = "understate_age"  # reads FRESHER than truth — dangerous


@dataclass(frozen=True)
class G4PrimeBranch:
    """One enumerated branch on the path from source event to rendered figure.

    ``present`` records whether the branch is live *on this render* (C-5 is
    per-render, not per-artifact). A branch is always DECLARED (it appears in
    the enumeration) even when absent — the FLAG F-2 lesson: a branch marked
    "neutral/none" silently is worse than a branch declared and shown absent.
    """

    name: str
    present: bool
    sign: G4PrimeSign
    note: str


@dataclass(frozen=True)
class G4PrimeBound:
    """The per-render G4' sign statement that rides ON item 1a's number.

    ``single_signed`` is True iff every *present, non-neutral* branch points the
    same direction. Item 1a is single-signed toward OVERSTATE_AGE: it can only
    read older than the truth, never fresher. This is the companion the number
    is malformed without (SPEC §3).
    """

    branches: tuple[G4PrimeBranch, ...]
    single_signed: bool
    dominant_sign: G4PrimeSign
    text: str


@dataclass(frozen=True)
class Item1aFigure:
    """Item 1a: the one say-able number, with its typed denominator surface.

    * ``as_of`` — the DR-2 ``min`` floor over the ``k`` contributing sections'
      per-section ``max(last_modified)``. The oldest per-section max; the
      readout can never read fresher than its stalest constituent.
    * ``k`` / ``n`` — the DENOM-FENCE denominator: ``n`` in-scope sections,
      ``k`` of which contributed a non-null ``max``. Integers + unit "sections";
      never an age, a rate, or a headline (C-6).
    * ``truncated`` — whether the ``/rows`` result was filter+limit truncated
      (``returned_count < total_count``). Drives the F-2 truncation branch.
    """

    as_of: datetime
    k: int
    n: int
    per_section_max: Mapping[str, datetime]
    truncated: bool
    returned_count: int | None
    total_count: int | None

    @property
    def as_of_iso(self) -> str:
        """The as-of rendered as ISO-8601 UTC (``...Z``) — the ``{t_s}`` slot."""
        return _fmt_dt(self.as_of)


def _parse_dt(value: object) -> datetime:
    """Parse a ``last_modified`` cell to a timezone-aware UTC datetime.

    Accepts a ``datetime`` or an ISO-8601 string (``Z`` or offset). Naive
    inputs are read as UTC. Comparisons are always aware-vs-aware.
    """
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _fmt_dt(dt: datetime) -> str:
    """Render a UTC datetime as ISO-8601 with a trailing ``Z``."""
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def compute_item_1a(
    rows: Sequence[Mapping[str, object]],
    in_scope_sections: Sequence[str],
    meta: Mapping[str, object] | None = None,
) -> Item1aFigure:
    """Compute item 1a from a ``/rows`` response's rows + meta.

    Args:
        rows: the ``/rows`` result rows (``response["data"]["data"]``), each a
            dict carrying at least ``section`` and ``last_modified``.
        in_scope_sections: the request's declared in-scope sections. This is
            ``n``. Sections that contribute no non-null ``max`` are counted in
            ``n`` but not in ``k`` — that gap is exactly what the denominator
            discloses.
        meta: the ``/rows`` response meta (``response["data"]["meta"]``), read
            ONLY for ``total_count`` / ``returned_count`` to detect truncation
            (F-2 / §1.2b T-GUARD). Optional; absent meta means truncation is
            not asserted (conservatively not-truncated).

    Returns:
        The ``Item1aFigure`` — pure function of the passed bytes.

    Raises:
        Item1aError: if no in-scope section contributed a non-null ``max``
            (``k == 0``); DR-2's ``min`` floor is undefined over an empty set.
    """
    per_section_max: dict[str, datetime] = {}
    for row in rows:
        section = row.get("section")
        last_modified = row.get("last_modified")
        if section is None or last_modified is None:
            # A null last_modified cannot happen for a served offer row
            # (nullable=False), but a defensive skip keeps the min floor honest
            # if a caller hands in a mixed frame.
            continue
        dt = _parse_dt(last_modified)
        current = per_section_max.get(str(section))
        if current is None or dt > current:
            per_section_max[str(section)] = dt

    in_scope = list(dict.fromkeys(str(s) for s in in_scope_sections))
    contributing = {s: per_section_max[s] for s in in_scope if s in per_section_max}
    n = len(in_scope)
    k = len(contributing)
    if k == 0:
        raise Item1aError(
            "no in-scope section contributed a non-null max(last_modified); "
            "DR-2 min floor is undefined over zero constituents — refusing to "
            f"render a say-able number over {n} in-scope sections with 0 present"
        )

    as_of = min(contributing.values())  # DR-2: the oldest per-section max

    truncated = False
    total_count: int | None = None
    returned_count: int | None = None
    if meta is not None:
        raw_total = meta.get("total_count")
        raw_returned = meta.get("returned_count")
        if isinstance(raw_total, int) and isinstance(raw_returned, int):
            total_count = raw_total
            returned_count = raw_returned
            truncated = raw_returned < raw_total

    return Item1aFigure(
        as_of=as_of,
        k=k,
        n=n,
        per_section_max=dict(contributing),
        truncated=truncated,
        returned_count=returned_count,
        total_count=total_count,
    )


def enumerate_g4_prime(figure: Item1aFigure) -> G4PrimeBound:
    """Enumerate item 1a's G4' sign branches for THIS render (C-5, per-render).

    Every imputation, default, filter, clipping and staleness branch on the
    path from source event to rendered figure, with the sign on each — the
    frozen table from ``PREDICATE...:1214-1232`` PLUS the truncation branch the
    critique's FLAG F-2 required be declared.

    The truncation branch is DECLARED on every render (not silently marked
    "neutral/none"): when the ``/rows`` result is truncated, a dropped
    max-bearing row pushes that section's ``max`` — and hence the ``min`` floor
    — OLDER, so it is an OVERSTATE_AGE contributor; when not truncated it is
    declared-and-absent. Either way the reader can see the branch was considered.
    """
    truncation_branch = (
        G4PrimeBranch(
            name="clipping / truncation (§1.2b T-GUARD)",
            present=True,
            sign=G4PrimeSign.OVERSTATE_AGE,
            note=(
                "the /rows result was filter+limit truncated "
                f"({figure.returned_count} of {figure.total_count} rows); a "
                "dropped max-bearing row pushes its section's max — and the min "
                "floor — OLDER (never fresher). Alarm-safe, but a real "
                "overstate-age contributor, disclosed per FLAG F-2. Note the "
                "k-of-n denominator discloses SECTION-level completeness only "
                "and does NOT surface this intra-section truncation."
            ),
        )
        if figure.truncated
        else G4PrimeBranch(
            name="clipping / truncation (§1.2b T-GUARD)",
            present=False,
            sign=G4PrimeSign.NEUTRAL,
            note=(
                "declared and considered per FLAG F-2: this render is NOT "
                "truncated (returned_count >= total_count), so no max-bearing "
                "row was dropped. Were it truncated, this branch would "
                "contribute OVERSTATE_AGE — the same alarm-safe direction."
            ),
        )
    )

    branches: tuple[G4PrimeBranch, ...] = (
        G4PrimeBranch(
            name="imputation",
            present=False,
            sign=G4PrimeSign.NEUTRAL,
            note="no value is imputed on item 1a's path.",
        ),
        G4PrimeBranch(
            name="default substitution",
            present=False,
            sign=G4PrimeSign.NEUTRAL,
            note="last_modified is nullable=False (base.py:76-82); no default is ever substituted.",
        ),
        G4PrimeBranch(
            name="row filters",
            present=True,
            sign=G4PrimeSign.NEUTRAL,
            note="filters narrow WHICH rows enter, not the value of the max — "
            "neutral on the figure.",
        ),
        truncation_branch,
        G4PrimeBranch(
            name="frame staleness",
            present=True,
            sign=G4PrimeSign.OVERSTATE_AGE,
            note="if the pipeline stalls, max(last_modified) freezes while now "
            "advances, so now - max grows — reads OLDER than truth.",
        ),
        G4PrimeBranch(
            name="understatement path",
            present=False,
            sign=G4PrimeSign.UNDERSTATE_AGE,
            note="would need a served last_modified NEWER than Asana's "
            "modified_at — structurally impossible (copy relationship, "
            "source='modified_at'). Absent.",
        ),
    )

    present_non_neutral = {
        b.sign for b in branches if b.present and b.sign is not G4PrimeSign.NEUTRAL
    }
    single_signed = len(present_non_neutral) <= 1
    dominant_sign = next(iter(present_non_neutral)) if present_non_neutral else G4PrimeSign.NEUTRAL

    disclosure = (
        " This render is over a truncated result window "
        f"({figure.returned_count} of {figure.total_count} rows); a dropped "
        "max-bearing row can only push the as-of older, never fresher."
        if figure.truncated
        else ""
    )
    text = (
        "This figure can only read as older than the truth, never fresher "
        "(it fails toward stale). Its as-of is the oldest of the "
        f"{figure.k} constituents." + disclosure
    )

    return G4PrimeBound(
        branches=branches,
        single_signed=single_signed,
        dominant_sign=dominant_sign,
        text=text,
    )
