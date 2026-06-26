"""Single source of truth for the dtype <-> field-class invariant (FPC Phase-1).

The Field-Provenance-&-Population-Contract lattice has a recurring failure mode:
a schema ``ColumnDef.dtype`` string and the model field-class that populates that
column drift apart silently (e.g. a number-sourced cell typed ``Utf8`` in the
schema, or an enum-sourced cell typed ``Decimal``). Nothing in the build path
asserts the two agree, so the drift is unrepresentable-as-an-error until it
surfaces as a null-at-rest or a coercion divergence downstream.

This module makes the invariant STRUCTURAL by giving it a single propagation
point. Two maps key off the Python value type a field carries:

- ``DTYPE_MAP`` -- value type -> the canonical schema dtype string for it.
- ``FIELDCLASS_MAP`` -- value type -> the model field-class tokens that produce it
  (descriptor class names like ``NumberField`` AND the asset_edit helper-method
  tokens like ``_get_number_field`` that the method/property style fields call).

The parity check (``tests/unit/dataframes/test_field_contract_parity.py``) reads
ONLY these maps to compute the expected dtype for a cell from its model
field-class. No per-cell dtype is hardcoded anywhere; adding or changing the
invariant happens here and nowhere else (the G-PROPAGATE guarantee).

SCOPE NOTE (FPC Phase-1, G-DEFER): this is the maps + the parity CHECK only. The
full ``FieldContract`` dataclass/registry, schema-FROM-model derivation, and the
in-repo generator are explicitly Phase-3 work and are NOT built here.
"""

from __future__ import annotations

from decimal import Decimal

__all__ = [
    "DTYPE_MAP",
    "FIELDCLASS_MAP",
    "expected_dtype_for_value_type",
    "value_type_for_field_class",
]


# Python value type -> canonical schema dtype string (the ``ColumnDef.dtype``
# vocabulary). "Decimal" and "Float64" both resolve to ``pl.Float64`` at runtime
# (see ColumnDef.get_polars_dtype), but the schema STRING is the contract surface
# the parity check audits: a number-sourced cell's canonical string is "Decimal".
DTYPE_MAP: dict[type, str] = {
    Decimal: "Decimal",
    int: "Int64",
    str: "Utf8",
    bool: "Boolean",
    float: "Float64",
}


# Python value type -> the set of model field-class identifiers that produce it.
# Membership tokens are matched against BOTH:
#   - descriptor class names (Unit/Offer fields are class-level descriptor
#     instances: NumberField, IntField, EnumField, TextField, ...), and
#   - asset_edit helper-method tokens (AssetEdit's number/int cells are
#     @property getters whose body calls ``self._get_number_field(...)`` /
#     ``self._get_int_field(...)``).
# A field-class identifier resolving into one of these frozensets pins the value
# type, and DTYPE_MAP then pins the expected schema dtype string.
FIELDCLASS_MAP: dict[type, frozenset[str]] = {
    Decimal: frozenset({"NumberField", "_get_number_field"}),
    int: frozenset({"IntField", "_get_int_field"}),
    str: frozenset({"TextField", "EnumField"}),
}


def value_type_for_field_class(field_class_token: str) -> type | None:
    """Return the Python value type a model field-class identifier produces.

    Args:
        field_class_token: A descriptor class name (e.g. ``"NumberField"``) or an
            asset_edit helper-method token (e.g. ``"_get_number_field"``).

    Returns:
        The Python value type per ``FIELDCLASS_MAP``, or ``None`` if the token is
        not a number/int/text-producing field class (e.g. MultiEnumField).
    """
    for value_type, tokens in FIELDCLASS_MAP.items():
        if field_class_token in tokens:
            return value_type
    return None


def expected_dtype_for_value_type(value_type: type) -> str | None:
    """Return the canonical schema dtype string for a Python value type.

    Args:
        value_type: A Python type key present in ``DTYPE_MAP``.

    Returns:
        The canonical schema dtype string, or ``None`` if the value type has no
        mapped dtype.
    """
    return DTYPE_MAP.get(value_type)
