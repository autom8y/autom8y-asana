"""Unit activity: the single definition of whether a Unit is active.

The ratified rule
-----------------
- A **marketing** Unit takes its activity from its Offers' sections. It is the
  highest group any of its Offers is in (active > activating > inactive >
  ignored). A marketing Unit with no Offer, or whose Offers sit only in sections
  no list names, has no activity.
- A **non-marketing** Unit takes its activity from its own section, by legacy's
  Unit lists (``activity.LEGACY_UNIT_SECTIONS``). A section in no list gives no
  activity.
- **Engaged is counted apart from activating.** It is in legacy's inactive list,
  so a non-marketing Unit in Engaged is inactive and never activating. A
  marketing Unit in Engaged takes its Offers' activity; its own section is not
  read. A separate Engaged tally reads the Unit's ``section``.
- A Unit with **no products** (an empty ``products`` list) is read like a
  non-marketing Unit. Legacy's test is "a product names marketing"
  (UM:1207-1210), which an empty list fails, so legacy reads its own section.
- A Unit whose ``products`` value is **missing** (null: the field did not
  resolve) has no activity. Which branch applies is unknown, and guessing would
  push a confidently wrong row. When more than half the Units are missing it
  (``PRODUCTS_NULL_SHARE_LIMIT``), the frame itself is refused: the field failed
  to resolve, and no Unit's activity can be read from it.

"Marketing" means a product whose name contains ``marketing``, case-insensitive.

Name matching
-------------
Every comparison against a section list folds both sides with ``snake_lower``,
legacy's fold: spaces, tabs, no-break spaces, hyphens and dots become ``_``,
the text is lowercased, runs of ``_`` collapse, and outer ``_`` are stripped.

The Offer sections a Unit reads
-------------------------------
A Unit reads an Offer's section through ``OFFER_CLASSIFIER``'s groups, plus three
names this module settles for the Unit read only (``SETTLED_OFFER_SECTIONS``).
``OFFER_CLASSIFIER`` itself is unchanged: it also feeds the served Offer metrics,
which this rule does not touch.

Pure: no I/O. ``with_unit_activity`` applies the rule to a Unit frame and an Offer
frame and adds the ``unit_activity`` column; it imports polars lazily.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    LEGACY_UNIT_SECTIONS,
    OFFER_CLASSIFIER,
    AccountActivity,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import polars as pl

__all__ = [
    "MARKETING_PRODUCT_MARKER",
    "PRODUCTS_NULL_SHARE_LIMIT",
    "SETTLED_OFFER_SECTIONS",
    "UNIT_ACTIVITY_COLUMN",
    "UnitActivityInputError",
    "classify_offer_section",
    "classify_unit_activity",
    "classify_unit_section",
    "is_marketing_unit",
    "snake_lower",
    "with_unit_activity",
]

#: Column ``with_unit_activity`` adds to a Unit frame: an ``AccountActivity``
#: value, or null when the Unit has no activity.
UNIT_ACTIVITY_COLUMN = "unit_activity"

#: A Unit is a marketing Unit when a product's name contains this, any case.
MARKETING_PRODUCT_MARKER = "marketing"

#: The share of Units whose ``products`` value is null above which the Unit frame
#: cannot ground Unit activity at all. The rule: refuse when strictly more than
#: this share is null (an all-null column included); exactly half still passes.
#: A null value means the field did not resolve. A failed resolution of the
#: Products field is frame-wide, so it reads as an all-null column. An empty
#: selection is an empty list, not null, so the healthy null share is near zero.
#: Half leaves a wide margin on both sides: it cannot be reached by stray nulls,
#: and it is still crossed by any failure that hits most of the frame. Under it,
#: the null Units get no activity and the rest of the frame is read.
PRODUCTS_NULL_SHARE_LIMIT = 0.5

#: Offer sections settled for the Unit read and absent from OFFER_CLASSIFIER.
#: LAUNCH ERROR and SYSTEM ERROR are not live sections today, but legacy names
#: them and a modern Offer-section writer may target them. By the section name,
#: LAUNCH ERROR holds an Offer whose launch failed (activating in legacy's lists)
#: and SYSTEM ERROR one that was already running (active in legacy's lists). ADD NEW
#: OFFER is live and in no legacy list, so it never counts toward a Unit; ignored
#: is the group with that effect.
SETTLED_OFFER_SECTIONS: dict[str, AccountActivity] = {
    "LAUNCH ERROR": AccountActivity.ACTIVATING,
    "SYSTEM ERROR": AccountActivity.ACTIVE,
    "ADD NEW OFFER": AccountActivity.IGNORED,
}

_SEPARATOR = re.compile(r"[ \t\u00a0.\-]")
_UNDERSCORE_RUN = re.compile(r"_+")


class UnitActivityInputError(ValueError):
    """A frame cannot ground Unit activity (a column is missing, or no Offers)."""


def snake_lower(name: str) -> str:
    """Fold a section name the way legacy compares names to its lists.

    Applied twice, as legacy applies its ``to_snake`` twice; the second pass is
    a no-op on its own output.
    """
    folded = name
    for _ in range(2):
        folded = _UNDERSCORE_RUN.sub("_", _SEPARATOR.sub("_", folded).lower()).strip("_")
    return folded


def _fold_index(groups: Iterable[tuple[str, AccountActivity]]) -> dict[str, AccountActivity]:
    """Index section names by their fold; refuse a fold that lands in two groups."""
    index: dict[str, AccountActivity] = {}
    for name, activity in groups:
        key = snake_lower(name)
        existing = index.get(key)
        if existing is not None and existing is not activity:
            raise ValueError(
                f"section name {name!r} folds to {key!r}, which is already in "
                f"group {existing.value!r}; it cannot also be {activity.value!r}"
            )
        index[key] = activity
    return index


def _offer_read_pairs() -> list[tuple[str, AccountActivity]]:
    pairs = [
        (name, activity)
        for activity in AccountActivity
        for name in OFFER_CLASSIFIER.sections_for(activity)
    ]
    pairs.extend(SETTLED_OFFER_SECTIONS.items())
    return pairs


_OFFER_READ: dict[str, AccountActivity] = _fold_index(_offer_read_pairs())

_UNIT_READ: dict[str, AccountActivity] = _fold_index(
    (name, activity) for activity, names in LEGACY_UNIT_SECTIONS.items() for name in names
)

_PRIORITY_RANK: Mapping[AccountActivity, int] = {
    activity: rank for rank, activity in enumerate(ACTIVITY_PRIORITY)
}


def classify_offer_section(section_name: str | None) -> AccountActivity | None:
    """The group an Offer's section gives its Unit; None if no list names it."""
    if not section_name:
        return None
    return _OFFER_READ.get(snake_lower(section_name))


def classify_unit_section(section_name: str | None) -> AccountActivity | None:
    """The group a Unit's own section has in legacy's lists; None if unlisted."""
    if not section_name:
        return None
    return _UNIT_READ.get(snake_lower(section_name))


def is_marketing_unit(products: Any) -> bool | None:
    """Whether a Unit is a marketing Unit, from its ``products`` value.

    Returns None when ``products`` is None (the field did not resolve), so the
    caller can refuse to guess. An empty list is a Unit with no products: False.
    """
    if products is None:
        return None
    values = [products] if isinstance(products, str) else list(products)
    return any(isinstance(p, str) and MARKETING_PRODUCT_MARKER in p.lower() for p in values)


def classify_unit_activity(
    *,
    products: Any,
    unit_section: str | None,
    offer_sections: Iterable[str | None],
) -> AccountActivity | None:
    """Apply the rule to one Unit. See the module docstring for the rule table.

    Args:
        products: The Unit's ``products`` multi-enum (a list of option names),
            or None when it did not resolve.
        unit_section: The Unit's own section name.
        offer_sections: The section names of the Unit's Offers.
    """
    marketing = is_marketing_unit(products)
    if marketing is None:
        return None
    if not marketing:
        return classify_unit_section(unit_section)

    groups = [g for g in (classify_offer_section(s) for s in offer_sections) if g is not None]
    if not groups:
        return None
    return min(groups, key=_PRIORITY_RANK.__getitem__)


_UNIT_COLUMNS = ("office_phone", "vertical", "section", "products")
_OFFER_COLUMNS = ("office_phone", "vertical", "section")


def _require_columns(df: pl.DataFrame, columns: tuple[str, ...], frame: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise UnitActivityInputError(f"the {frame} frame lacks column(s) {missing}")


def _require_products_resolved(unit_df: pl.DataFrame) -> None:
    """Refuse a Unit frame whose ``products`` column is mostly or wholly null.

    The share is taken over every row of the Unit frame. An empty Unit frame
    never reaches this check: ``with_unit_activity`` refuses it first. See
    ``PRODUCTS_NULL_SHARE_LIMIT`` for the rule.
    """
    unit_count = unit_df.height
    null_count = int(unit_df["products"].null_count())
    if null_count > PRODUCTS_NULL_SHARE_LIMIT * unit_count:
        raise UnitActivityInputError(
            f"products is null for {null_count} of {unit_count} units, "
            f"more than the {PRODUCTS_NULL_SHARE_LIMIT:.0%} limit"
        )


def _offer_key(phone: Any, vertical: Any) -> tuple[str, str] | None:
    if not phone:
        return None
    return (str(phone), "" if vertical is None else str(vertical))


def with_unit_activity(unit_df: pl.DataFrame, offer_df: pl.DataFrame) -> pl.DataFrame:
    """Return ``unit_df`` with the ``unit_activity`` column added.

    A Unit's Offers are the Offer rows sharing its ``(office_phone, vertical)``,
    the grain the account-status push keys on. A null vertical joins as ``""``
    on both sides.

    Raises:
        UnitActivityInputError: when either frame lacks a column the rule reads,
            either frame is empty, or ``products`` is null for more than
            ``PRODUCTS_NULL_SHARE_LIMIT`` of the Units. An empty Offer frame
            cannot ground any marketing Unit, an empty Unit frame would push a
            snapshot with no Unit rows (the receiver replaces the whole
            snapshot, so it would delete them), and a mostly-null ``products``
            column cannot tell which branch any Unit takes, so the caller must
            not push a reading built on any of them.
    """
    import polars as pl

    _require_columns(unit_df, _UNIT_COLUMNS, "unit")
    _require_columns(offer_df, _OFFER_COLUMNS, "offer")
    if offer_df.height == 0:
        raise UnitActivityInputError("the offer frame has no rows")
    if unit_df.height == 0:
        raise UnitActivityInputError("the unit frame has no rows")
    _require_products_resolved(unit_df)

    offer_sections: dict[tuple[str, str], list[str]] = {}
    for phone, vertical, section in offer_df.select(_OFFER_COLUMNS).iter_rows():
        key = _offer_key(phone, vertical)
        if key is None or not section:
            continue
        offer_sections.setdefault(key, []).append(str(section))

    values: list[str | None] = []
    for phone, vertical, section, products in unit_df.select(_UNIT_COLUMNS).iter_rows():
        key = _offer_key(phone, vertical)
        activity = classify_unit_activity(
            products=products,
            unit_section=section,
            offer_sections=offer_sections.get(key, ()) if key is not None else (),
        )
        values.append(None if activity is None else activity.value)

    return unit_df.with_columns(pl.Series(UNIT_ACTIVITY_COLUMN, values, dtype=pl.Utf8))
