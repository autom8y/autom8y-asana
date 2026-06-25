"""GFR dynamic-tail override registry — sprint-3 FRAME-002 (the worked example).

A per-field override post-processes the raw value the tail extracted via
``_extract_raw_value`` (``default.py:234-287``). Overrides are:

* **NAME-keyed** — keyed by the canonical, normalized field NAME
  (``NameNormalizer.normalize`` — the same grain the model ``field_name`` /
  schema ``cf:Name`` / whole codebase uses). The cf ``gid`` is NEVER a key
  (operator NAME-keying correction, 2026-06-25). A cf rename is caught by the
  FRAME-005 drift gate, not by gid-keying.
* **EntityType-scoped** — keyed by ``(entry_entity_type, normalized_name)`` so
  cross-entity dtype divergence is expressible (the same field name can carry a
  different override on a different entity).

The worked example: ``asset_id`` (cf type ``text``) on an Offer entry whose raw
value is ``"a, b ,c"`` -> ``{"a","b","c"}`` (a SET), via a whitespace-agnostic
comma split. Adding a SECOND override is a DATA addition to ``OVERRIDE_REGISTRY``
(an extra mapping entry), NOT a code change — ``apply_override`` reads the mapping.

Boundary discipline (deliberate): an override NEVER manufactures a value from an
empty/null raw. ``asset_id`` text that is ``None`` / ``""`` (or otherwise empty)
returns the raw UNCHANGED so the tail's null predicate still classifies it as
PRESENT_BUT_NULL — an empty SET masquerading as a value would lie about
present-vs-null and break the three-state contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.dataframes.resolver.normalizer import NameNormalizer

if TYPE_CHECKING:
    from collections.abc import Callable


def _comma_split_to_set(raw: object) -> object:
    """Whitespace-agnostic comma split of a text value into a SET (FRAME-002).

    ``"a, b ,c"`` -> ``{"a","b","c"}``. Each token is stripped; empty tokens are
    dropped. A non-string or empty raw is returned UNCHANGED (the boundary
    discipline): the tail then judges it present-but-null rather than emitting an
    empty set that would masquerade as a populated value.
    """
    if not isinstance(raw, str):
        return raw
    tokens = {part.strip() for part in raw.split(",")}
    tokens.discard("")
    if not tokens:
        # Empty / whitespace-only text: do NOT manufacture an empty set. Return the
        # raw so the tail's _is_null predicate keeps it PRESENT_BUT_NULL.
        return raw
    return tokens


# The override registry. Keyed by (entry_entity_type_value, normalized_field_name)
# -> a pure transform applied AFTER _extract_raw_value. A SECOND override is a new
# entry here (data), never a code change to apply_override.
OVERRIDE_REGISTRY: dict[tuple[str, str], Callable[[object], object]] = {
    # asset_id (text) -> comma-split SET, scoped to the Offer entry (FRAME-002).
    ("offer", NameNormalizer.normalize("asset_id")): _comma_split_to_set,
}


def has_override(field_name: str, entity_type: str) -> bool:
    """Return True if a NAME-keyed, EntityType-scoped override is registered."""
    return (entity_type, NameNormalizer.normalize(field_name)) in OVERRIDE_REGISTRY


def apply_override(field_name: str, entity_type: str, raw: object) -> object:
    """Apply a registered override to ``raw``, or return ``raw`` unchanged.

    NAME-keyed (``NameNormalizer.normalize(field_name)``) and EntityType-scoped.
    If no override is registered for ``(entity_type, normalized_name)`` the raw
    value passes through untouched (the default-identity contract sprint-2 left).
    """
    transform = OVERRIDE_REGISTRY.get((entity_type, NameNormalizer.normalize(field_name)))
    if transform is None:
        return raw
    return transform(raw)
