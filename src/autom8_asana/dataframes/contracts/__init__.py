"""Field-contract substrate for the dataframe layer.

Per FPC (Field-Provenance-&-Population-Contract) Phase-1: this package holds the
single-source-of-truth maps that bind a Python value type to (a) its canonical
Polars schema dtype string and (b) the set of model field-classes that produce
that value type. The schema↔model dtype parity check derives its expectations
EXCLUSIVELY from these maps -- there are no per-cell hardcoded dtype facts -- so
the dtype↔field-class invariant has exactly one propagation point.
"""

from autom8_asana.dataframes.contracts.field_contract_maps import (
    DTYPE_MAP,
    FIELDCLASS_MAP,
)

__all__ = [
    "DTYPE_MAP",
    "FIELDCLASS_MAP",
]
