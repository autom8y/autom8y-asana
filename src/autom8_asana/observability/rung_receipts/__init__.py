"""RUNG E limb (a) receipt schema and join query.

EX-4 of the exec-insight-delivery wave. The durable, queryable join contract
that makes RUNG E limb (a) -- "two delivery occurrences, each with a generation
receipt, jointly showing no human assembled either" -- mechanically observable,
by joining a live delivery receipt (``report_posted``) to its generation
provenance (``report_generated``) on ``invocation_id``.

See ``schema.py`` module docstring for the founding finding (the delivery half
is live; the generation half is absent) and the FS-5 two-ladder fence.
"""

from autom8_asana.observability.rung_receipts.join import (
    join_occurrences,
    observe_limb_a,
)
from autom8_asana.observability.rung_receipts.query import run_query
from autom8_asana.observability.rung_receipts.schema import (
    DELIVERY_EVENT,
    DELIVERY_LOGS_INSIGHTS_QUERY,
    GENERATION_EVENT,
    GENERATION_LOGS_INSIGHTS_QUERY,
    LIMB_A_REQUIRED_OCCURRENCES,
    RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA,
    Assembler,
    DeliveryOccurrenceReceipt,
    DeliveryOutcome,
    DeliveryReceipt,
    GenerationReceipt,
    LimbAObservation,
    LimbAStatus,
    NotObservableReason,
    Rung4Status,
    RungEObservability,
)

__all__ = [
    # schema
    "Assembler",
    "DeliveryOccurrenceReceipt",
    "DeliveryOutcome",
    "DeliveryReceipt",
    "GenerationReceipt",
    "LimbAObservation",
    "LimbAStatus",
    "NotObservableReason",
    "Rung4Status",
    "RungEObservability",
    "DELIVERY_EVENT",
    "GENERATION_EVENT",
    "LIMB_A_REQUIRED_OCCURRENCES",
    "RUNG_E_LIMB_A_RECEIPT_JSON_SCHEMA",
    "DELIVERY_LOGS_INSIGHTS_QUERY",
    "GENERATION_LOGS_INSIGHTS_QUERY",
    # join + query
    "join_occurrences",
    "observe_limb_a",
    "run_query",
]
