"""Generated schema<->model dtype parity check (FPC Phase-1, pillar C2).

THE INVARIANT. For every number/int-sourced cell in the dataframe schema
registries, the schema ``ColumnDef.dtype`` string must agree with the value type
the model field-class produces. A ``NumberField`` (or an asset_edit
``_get_number_field`` getter) produces ``Decimal`` -> the schema string must be
"Decimal"; an ``IntField`` / ``_get_int_field`` produces ``int`` -> "Int64"; an
``EnumField`` / ``TextField`` produces ``str`` -> "Utf8".

There is NO per-cell hardcoded dtype in this file. The expected dtype for a cell
is DERIVED from ``field_contract_maps`` (DTYPE_MAP + FIELDCLASS_MAP) -- the single
propagation point for the invariant (G-PROPAGATE). The cell->model registry below
records WHICH cells to audit and WHICH model field supplies each; the expected
dtype is computed from the maps, never written by hand.

Model-side field-class resolution is dual-mode:
  - descriptor fields (Unit, Offer): walk the model class MRO collecting
    ``CustomFieldDescriptor`` instances (NumberField/IntField/EnumField/TextField);
    each binds its ``public_name`` via ``__set_name__``.
  - method/property fields (AssetEdit): the cell is a ``@property`` whose getter
    body calls ``_get_number_field`` / ``_get_int_field``; we read the getter
    source (``inspect.getsource``) and match the helper token.

G-THEATER teeth (must survive into main):
  - ``test_positive_control_flags_synthetic_mismatch`` builds a deliberately wrong
    ColumnDef and asserts the parity function FLAGS it. The checker has teeth
    independent of any live cell.
  - ``test_d3_asset_edit_score_dtype_parity`` is the D3 SSOT-reconcile cell. At
    commit C2 (this commit) it is RED -- schema ``asset_edit.score`` is "Float64"
    while ``_get_number_field`` expects "Decimal". Commit C1 flips the schema to
    "Decimal" and this row goes GREEN. The RED->GREEN transition is the
    broken-fixture-RED proof in CI history.

D1/D2 drift cells (``unit.discount`` schema-Decimal-vs-EnumField,
``offer.cost`` schema-Utf8-vs-NumberField) are HELD on UK-2 / PRD-0024. They are
recorded as ``xfail(strict=True)`` -- visible, not buried -- and will XPASS-fail
loudly the moment UK-2 reconciles them.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest

from autom8_asana.dataframes.contracts.field_contract_maps import (
    expected_dtype_for_value_type,
    value_type_for_field_class,
)
from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas import (
    ASSET_EDIT_SCHEMA,
    OFFER_SCHEMA,
    UNIT_SCHEMA,
)
from autom8_asana.models.business.asset_edit import AssetEdit
from autom8_asana.models.business.descriptors import CustomFieldDescriptor
from autom8_asana.models.business.offer import Offer
from autom8_asana.models.business.unit import Unit

# ---------------------------------------------------------------------------
# Model-side field-class resolution (dual-mode introspection)
# ---------------------------------------------------------------------------


def _property_field_token(attr: property) -> str | None:
    """Return the helper-method token a property getter calls, if any.

    AssetEdit's number/int cells are ``@property`` getters whose body calls
    ``self._get_number_field(...)`` / ``self._get_int_field(...)``. Reads the
    getter source and returns the matched helper token, or ``None``.
    """
    if attr.fget is None:
        return None
    source = inspect.getsource(attr.fget)
    for token in ("_get_number_field", "_get_int_field"):
        if token in source:
            return token
    return None


def resolve_field_class_token(model_cls: type, field_name: str) -> str | None:
    """Resolve the model field-class token for a cell, MRO-respecting.

    Resolution mirrors what the model class ACTUALLY exposes for ``field_name``:
    we take the single most-derived definition via ``inspect.getattr_static``
    (which respects the MRO and so does not see attributes shadowed by a
    subclass), then classify it:

      - a ``CustomFieldDescriptor`` instance -> its class name (e.g.
        "NumberField") -- the Unit/Offer descriptor-style cells.
      - a ``property`` whose getter calls a known helper -> that helper token
        (e.g. "_get_number_field") -- the AssetEdit method-style cells.

    This MRO-respecting resolution is load-bearing: ``AssetEdit.score`` is a
    ``@property`` calling ``_get_number_field``, but a deeper base class
    (``Process``) defines ``score`` as an ``EnumField`` descriptor. A naive
    full-MRO descriptor scan would wrongly report the shadowed EnumField; the
    most-derived definition is the property, which is what AssetEdit actually
    serves.

    Returns a token consumable by ``value_type_for_field_class``, or ``None``
    when ``field_name`` resolves to neither a custom-field descriptor nor a
    recognised helper-method property (the introspection-infeasible case -> the
    cell is not auditable dynamically and must not silently pass).
    """
    attr = inspect.getattr_static(model_cls, field_name, None)
    if isinstance(attr, CustomFieldDescriptor):
        return type(attr).__name__
    if isinstance(attr, property):
        return _property_field_token(attr)
    return None


# ---------------------------------------------------------------------------
# The parity function under test (teeth proven by the positive control)
# ---------------------------------------------------------------------------


def parity_mismatch(column: ColumnDef, field_class_token: str) -> bool:
    """Return True iff the schema dtype DISAGREES with the model field-class.

    Expected dtype is DERIVED via the SSOT maps:
    ``field_class_token`` -> value type (FIELDCLASS_MAP) -> dtype string
    (DTYPE_MAP). No dtype literal is written here. A token outside the
    number/int/text universe (e.g. MultiEnumField) yields no expected dtype and
    is treated as not-a-mismatch (out of the parity check's scope).
    """
    value_type = value_type_for_field_class(field_class_token)
    if value_type is None:
        return False
    expected = expected_dtype_for_value_type(value_type)
    if expected is None:
        return False
    return column.dtype != expected


# ---------------------------------------------------------------------------
# Cell registry: WHICH cells to audit + WHICH model supplies each.
# Expected dtype is DERIVED from the maps via resolve_field_class_token; the
# registry holds NO dtype literals (G-PROPAGATE).
# ---------------------------------------------------------------------------

_SCHEMA_BY_ENTITY: dict[str, DataFrameSchema] = {
    "unit": UNIT_SCHEMA,
    "offer": OFFER_SCHEMA,
    "asset_edit": ASSET_EDIT_SCHEMA,
}

_MODEL_BY_ENTITY: dict[str, type] = {
    "unit": Unit,
    "offer": Offer,
    "asset_edit": AssetEdit,
}

# (entity, cell_name): the number/int-sourced cells whose schema dtype must match
# the model field-class. mrr/weekly_ad_spend appear on unit (descriptor source)
# and offer (cascade-sourced from Unit, same NumberField provenance). The three
# asset_edit cells (offer_id/template_id/videos_paid) are int-sourced @property
# getters calling ``_get_int_field`` (-> Int64); they round out the architect's
# ratified parity table (spec ss.C.3, 9 cells) -- earlier registries omitted them,
# leaving an Int64->Utf8 drift on these cells able to pass silently. score is the
# D3 cell (its own row below). D1 (unit.discount) and D2 (offer.cost) are HELD --
# see the dedicated xfail rows below; intentionally NOT in this clean registry.
#
# asset_edit.offer_id resolves on the AssetEdit class to a property -> Int64;
# this is DISTINCT from offer.offer_id (a TextField -> Utf8 on the Offer model).
# The cross-frame Utf8<->Int64 offer_id asymmetry is HELD on UK-3 and is a join-
# key coherence concern, NOT in scope for this per-cell intra-frame parity check.
_PARITY_CELLS: tuple[tuple[str, str], ...] = (
    ("unit", "mrr"),
    ("unit", "weekly_ad_spend"),
    ("offer", "mrr"),
    ("offer", "weekly_ad_spend"),
    ("asset_edit", "offer_id"),
    ("asset_edit", "template_id"),
    ("asset_edit", "videos_paid"),
)


# ---------------------------------------------------------------------------
# Permanent positive control (G-THEATER teeth, survives into main)
# ---------------------------------------------------------------------------


def test_positive_control_flags_synthetic_mismatch() -> None:
    """The parity function FLAGS a deliberately wrong cell.

    A number-sourced ``mrr`` typed "Utf8" in the schema must be reported as a
    mismatch against the NumberField class. This proves the checker has teeth
    independent of any live schema cell -- if the maps or the comparison ever go
    inert, this test fails.
    """
    broken = ColumnDef(name="mrr", dtype="Utf8", source="cf:MRR")
    assert parity_mismatch(broken, "NumberField") is True, (
        "positive control failed: a Utf8-typed NumberField cell was NOT flagged "
        "as a mismatch -- the parity checker is inert (G-THEATER violation)"
    )


def test_positive_control_passes_correct_cell() -> None:
    """The parity function does NOT flag a correctly-typed cell (no false-positive)."""
    correct = ColumnDef(name="mrr", dtype="Decimal", source="cf:MRR")
    assert parity_mismatch(correct, "NumberField") is False


def test_positive_control_int_and_text() -> None:
    """Int and text cells derive their expected dtype from the SSOT maps too."""
    assert parity_mismatch(ColumnDef("n", "Utf8", source="cf:N"), "IntField") is True
    assert parity_mismatch(ColumnDef("n", "Int64", source="cf:N"), "IntField") is False
    assert parity_mismatch(ColumnDef("t", "Int64", source="cf:T"), "TextField") is True
    assert parity_mismatch(ColumnDef("t", "Utf8", source="cf:T"), "EnumField") is False


# ---------------------------------------------------------------------------
# Live-cell parity (the clean, must-be-GREEN cells)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("entity", "cell"), _PARITY_CELLS)
def test_live_cell_dtype_parity(entity: str, cell: str) -> None:
    """Each clean number-sourced cell's schema dtype matches its model field-class.

    The expected dtype is DERIVED from the SSOT maps via the resolved
    field-class token -- not asserted against a literal.
    """
    schema = _SCHEMA_BY_ENTITY[entity]
    model_cls = _MODEL_BY_ENTITY[entity]
    column = schema.get_column(cell)
    assert column is not None, f"{entity}.{cell} missing from schema"

    token = resolve_field_class_token(model_cls, cell)
    assert token is not None, (
        f"could not resolve a model field-class for {entity}.{cell}; the cell is "
        "not dynamically auditable and must not silently pass"
    )
    value_type = value_type_for_field_class(token)
    assert value_type is not None, (
        f"{entity}.{cell} resolves to field-class token {token!r} which is outside "
        "the number/int/text parity universe"
    )
    expected = expected_dtype_for_value_type(value_type)
    assert not parity_mismatch(column, token), (
        f"DTYPE DRIFT {entity}.{cell}: schema dtype is {column.dtype!r} but the "
        f"model field-class {token!r} (-> {value_type.__name__}) expects "
        f"{expected!r}"
    )


# ---------------------------------------------------------------------------
# D3 -- asset_edit.score SSOT reconcile (RED at C2 -> GREEN at C1)
# ---------------------------------------------------------------------------


def test_d3_asset_edit_score_dtype_parity() -> None:
    """D3: asset_edit.score schema dtype matches _get_number_field (-> Decimal).

    The D3 SSOT-reconcile cell, now GREEN. ``asset_edit.score`` is read via
    ``_get_number_field`` (Decimal) on the model, so its canonical schema dtype
    string is "Decimal".

    G-THEATER history: at commit C2 (the test commit, before this cell's schema
    fix) this assertion was RED -- the schema was "Float64" while the model
    expects "Decimal". Commit C1 reconciled the schema to "Decimal" (byte-
    identical at runtime: both map to pl.Float64 via ColumnDef.get_polars_dtype)
    and this row went GREEN. This permanent guard now fails loudly if the cell
    ever drifts back.
    """
    column = ASSET_EDIT_SCHEMA.get_column("score")
    assert column is not None, "asset_edit.score missing from schema"

    token = resolve_field_class_token(AssetEdit, "score")
    assert token == "_get_number_field", (
        f"expected asset_edit.score to resolve to _get_number_field, got {token!r}"
    )
    value_type = value_type_for_field_class(token)
    assert value_type is Decimal
    expected = expected_dtype_for_value_type(value_type)
    assert not parity_mismatch(column, token), (
        f"D3 DTYPE DRIFT asset_edit.score: schema dtype is {column.dtype!r} but "
        f"_get_number_field expects {expected!r}. C1 reconciles this by setting "
        "the schema dtype to 'Decimal' (zero runtime delta)."
    )


# ---------------------------------------------------------------------------
# D1 / D2 -- HELD drift cells (visible-deferred, not buried; XPASS-fails on cure)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(strict=True, reason="HELD on UK-2 / PRD-0024 ruling (D1)")
def test_d1_unit_discount_dtype_parity_HELD() -> None:
    """D1: unit.discount schema-Decimal vs EnumField (-> Utf8). HELD on UK-2.

    Recorded as strict xfail: it fails today (the drift is real), so xfail passes
    the suite. When UK-2 reconciles ``discount`` (schema -> "Utf8"), this test
    will start PASSING and the strict-xfail will FLIP to a loud XPASS failure --
    forcing this marker's removal. Anti-burial by construction.
    """
    column = UNIT_SCHEMA.get_column("discount")
    assert column is not None
    token = resolve_field_class_token(Unit, "discount")
    assert token == "EnumField"
    assert not parity_mismatch(column, token), (
        f"unit.discount schema dtype {column.dtype!r} disagrees with EnumField "
        "(expects 'Utf8')"
    )


@pytest.mark.xfail(strict=True, reason="HELD on UK-2 / PRD-0024 ruling (D2)")
def test_d2_offer_cost_dtype_parity_HELD() -> None:
    """D2: offer.cost schema-Utf8 vs NumberField (-> Decimal). HELD on UK-2.

    Strict xfail, same anti-burial mechanic as D1: fails today; will XPASS-fail
    the moment UK-2 retypes ``cost`` to "Decimal".
    """
    column = OFFER_SCHEMA.get_column("cost")
    assert column is not None
    token = resolve_field_class_token(Offer, "cost")
    assert token == "NumberField"
    assert not parity_mismatch(column, token), (
        f"offer.cost schema dtype {column.dtype!r} disagrees with NumberField "
        "(expects 'Decimal')"
    )
