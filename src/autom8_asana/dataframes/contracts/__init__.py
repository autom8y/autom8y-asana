"""Field-contract substrate for the dataframe layer.

Per FPC (Field-Provenance-&-Population-Contract) Phase-1: this package holds the
single-source-of-truth maps that bind a Python value type to (a) its canonical
Polars schema dtype string and (b) the set of model field-classes that produce
that value type. The schema↔model dtype parity check derives its expectations
EXCLUSIVELY from these maps -- there are no per-cell hardcoded dtype facts -- so
the dtype↔field-class invariant has exactly one propagation point.

FM-5 ARM-B (Phase-3): the same module is the SOLE propagation point for the
CONSUMER-required-column contract — the vendored manifest is ingested and the
per-query-shape required SET is derived here (``derive_required_columns``).
"""

from autom8_asana.dataframes.contracts.field_contract_maps import (
    DTYPE_MAP,
    FIELDCLASS_MAP,
    VENDORED_MANIFEST_PATH,
    ConsumerManifestError,
    ConsumerRequirement,
    ConsumerRequirements,
    DriftReport,
    QueryShape,
    derive_required_columns,
    load_consumer_requirements,
    requirements_drift_check,
)

__all__ = [
    "DTYPE_MAP",
    "FIELDCLASS_MAP",
    "VENDORED_MANIFEST_PATH",
    "ConsumerManifestError",
    "ConsumerRequirement",
    "ConsumerRequirements",
    "DriftReport",
    "QueryShape",
    "derive_required_columns",
    "load_consumer_requirements",
    "requirements_drift_check",
]
