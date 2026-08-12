"""Substrate-v2 — the publish-time TIERED POPULATION FLOOR (the floor-set definition).

BRIDGE per ``.ledge/spikes/SPIKE-population-floor-scope-2026-08-12.md`` (ratification
digest items 1/2/4). This module is the SOLE home of the *serve-blocking column set* —
deliberately SEPARATE from ``substrate.freshness._VALUE_COLUMNS``, which is the FROZEN
content-digest value set (``sv2-canonical-digest-1``) and carries a different question.

**Why the split** (spike §"Load-bearing facts" #2). Before this module the floor re-used
``_VALUE_COLUMNS`` as its column set, so ONE tuple answered two unrelated questions:

* *digest*: "which columns' VALUES define this artifact's content identity?" — frozen for
  the life of the v1.0 seam; changing it is a digest-scheme version event.
* *floor*:  "which columns' nulls make the SERVED NUMBER wrong?" — a serving-policy
  question that must be free to move as consumers change.

Answering both with one tuple means a floor rescope silently re-keys every digest. This
module answers only the SECOND question; ``_VALUE_COLUMNS`` stays byte-untouched.

**The tiering** (digest item 1). The floor is TWO-TIER, not one:

* **blocking** — a null on a classifier-active row makes the served number WRONG. Publish
  REFUSES. For the offer plane this is ``{mrr, office_phone, vertical}``: ``mrr`` is the
  sum input, and ``(office_phone, vertical)`` are the dedup keys — polars
  ``unique(subset, keep="first")`` treats nulls as EQUAL, so a null dedup key on two
  distinct active offers silently COLLAPSES them into one and the sum loses value
  (``metrics/compute.py:116``). The dedup keys are therefore correctness-bearing for the
  NUMBER, not metadata — a guard the strict economic floor never had.
* **warning** — a null is a real data wound but the served number does not read the
  column. Publish PROCEEDS and the wound surfaces LOUDLY per-offer (receipt
  ``data_quality_warnings`` + the ``ActiveRowEconomicNullCount`` metric → PROV-7). For the
  offer plane: ``{cost, offer_id, weekly_ad_spend}``. Three provisioning-lag ``offer_id``
  nulls halted three consecutive parity days on a column the served number never consumes
  — the W2 over-refusal shape this tier retires.

**Extensibility** (the operator's BINDING qualifier — the dataframes substrate serves an
insights pipeline with MANY consumers; ``active_mrr`` is ONE consumer implementation).
``TieredPopulationFloor`` is a plain value object and the floor is a PARAMETER of
``DefaultAcceptancePredicates`` (seam-use, not a frozen internal): a second consumer
declares its own instance and injects it. Nothing here names ``active_mrr``, and no
consumer inherits another's tiering by default — an un-wired caller gets
``STRICT_ECONOMIC_FLOOR`` (fail-closed, the pre-bridge behaviour).

**Endstate note**: WHERE the floor set ultimately lives (serve-time per-consumer derived /
registry-governed per-entity / schema-tagged columns) is EXPLICITLY DEFERRED to the
architect-led locus adjudication (spike digest item 5). This module is the bridge, and it
is deliberately shaped so the adjudication can replace its *source of truth* without
touching the seam that consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    import polars as pl

__all__ = [
    "OFFER_PUBLISH_FLOOR",
    "STRICT_ECONOMIC_FLOOR",
    "ColumnNullWarning",
    "TieredPopulationFloor",
    "warning_blocks",
]


@dataclass(frozen=True, slots=True)
class ColumnNullWarning:
    """One classifier-active row carrying >= 1 null in a WARNING-tier column.

    PII discipline (§6 #8, inherited from the parity receipt contract): only the row's
    Asana ``gid``, its ``section``, and the offending COLUMN NAMES are carried — never a
    cell VALUE, and never a dedup key (``office_phone`` is blocking-tier, so it can never
    appear in ``null_columns``).
    """

    gid: str | None
    section: str | None
    null_columns: tuple[str, ...]

    def as_block(self) -> dict[str, Any]:
        """The receipt/digest wire form — ``{gid, section, null_cols}``."""
        return {"gid": self.gid, "section": self.section, "null_cols": list(self.null_columns)}


@dataclass(frozen=True, slots=True)
class TieredPopulationFloor:
    """A publish-time population floor split into a BLOCKING and a WARNING tier.

    ``blocking`` columns gate the publish: a null (or an ABSENT column — fail-closed, an
    unestablished population is not a passing one) on any evaluated row REFUSES.
    ``warning`` columns never gate; their nulls are surfaced per-row so the wound stays
    loud without halting a provably-correct number.

    The two tiers MUST be disjoint (a column cannot both block and merely warn) and
    ``blocking`` MUST be non-empty (an all-warning floor is not a floor — it would admit
    an arbitrarily broken publish, the exact regression the tiering must not introduce).
    """

    blocking: tuple[str, ...]
    warning: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.blocking:
            raise ValueError(
                "a population floor with no blocking columns is not a floor — it would "
                "admit an arbitrarily broken publish; declare at least one blocking column"
            )
        overlap = sorted(set(self.blocking) & set(self.warning))
        if overlap:
            raise ValueError(
                f"population-floor tiers must be disjoint; {overlap} appear in BOTH the "
                "blocking and warning tiers (a column cannot both refuse and merely warn)"
            )

    def blocking_columns_with_nulls(self, frame: pl.DataFrame) -> set[str]:
        """The BLOCKING columns carrying >= 1 null in ``frame`` (absent counts as null).

        An absent blocking column is a null-equivalent: the population it attests is not
        established, and for a dedup key its absence means the frame cannot be deduped at
        all (``served_active_mrr`` raises ``ActiveMrrColumnMissing`` on exactly this).
        Fail-closed here rather than publishing a frame whose number cannot be derived.
        """
        present = set(frame.columns)
        offenders: set[str] = set()
        for column in self.blocking:
            if column not in present or frame.get_column(column).null_count() > 0:
                offenders.add(column)
        return offenders

    def null_warnings(
        self,
        frame: pl.DataFrame,
        *,
        gid_column: str = "gid",
        section_column: str = "section",
    ) -> tuple[ColumnNullWarning, ...]:
        """Per-row WARNING-tier nulls in ``frame``, in frame order (empty when clean).

        ``frame`` is the ALREADY-EVALUATED population (i.e. the classifier-active subset
        the caller selected) — a warning is never raised for a row the served number does
        not read. A warning column ABSENT from the frame is skipped rather than reported:
        absence is a schema-level fault with no per-row attribution, and for the offer
        plane the digest's own ``MissingValueColumnsError`` already refuses it upstream.
        """
        present = [column for column in self.warning if column in frame.columns]
        if not present:
            return ()
        if not any(frame.get_column(column).null_count() > 0 for column in present):
            return ()  # fast path: no nulls anywhere in the warning tier

        identity = [c for c in (gid_column, section_column) if c in frame.columns]
        records = frame.select([*identity, *present]).to_dicts()
        warnings: list[ColumnNullWarning] = []
        for row in records:
            nulls = tuple(column for column in present if row.get(column) is None)
            if not nulls:
                continue
            warnings.append(
                ColumnNullWarning(
                    gid=_as_identity(row.get(gid_column)),
                    section=_as_identity(row.get(section_column)),
                    null_columns=nulls,
                )
            )
        return tuple(warnings)


def _as_identity(value: object) -> str | None:
    """Coerce an identity cell to ``str`` (or ``None``) — never a raw polars object."""
    return None if value is None else str(value)


def warning_blocks(warnings: Iterable[ColumnNullWarning]) -> list[dict[str, Any]]:
    """The receipt wire form for a warning sequence — ``[{gid, section, null_cols}, ...]``."""
    return [warning.as_block() for warning in warnings]


# --------------------------------------------------------------------------- floors ---

# The PRE-BRIDGE behaviour, restated here as an INDEPENDENT tuple. It is intentionally a
# copy-by-value of what ``freshness._VALUE_COLUMNS`` happens to hold today and NOT an
# import of it: that decoupling is the whole point (a future floor move must not re-key
# the frozen digest, and a digest-scheme event must not silently re-scope serving). It is
# the default for any caller that does not declare its own floor — fail-closed, strictly
# no weaker than the behaviour that shipped before this module existed.
STRICT_ECONOMIC_FLOOR: TieredPopulationFloor = TieredPopulationFloor(
    blocking=("cost", "mrr", "offer_id", "weekly_ad_spend")
)

# The BRIDGE floor for the offer plane (digest item 4). Blocking = exactly what the live
# served number consumes: ``mrr`` (the sum input) + ``(office_phone, vertical)`` (the
# dedup keys, whose nulls silently collapse distinct offers). Warning = the economic
# columns the served number does NOT read, demoted to the loud channel.
OFFER_PUBLISH_FLOOR: TieredPopulationFloor = TieredPopulationFloor(
    blocking=("mrr", "office_phone", "vertical"),
    warning=("cost", "offer_id", "weekly_ad_spend"),
)
