"""The recurring exec readout: item-1a generation mechanism (EX-5, WS-2).

A new autom8y-asana capability that assembles the item-1a offers-freshness
readout from a ``POST /v1/query/offer/rows`` response and emits the
``report_generated`` provenance event EX-4's ``GenerationReceipt`` contract
consumes. Built to the SPEC (SPEC-recurring-readout-template-2026-08-13.md) and
folding the design critique's FLAG F-2 (the truncation / §1.2b T-GUARD branch is
now DECLARED in the per-render G4' enumeration).

DF-1: this package reads only the ``/rows`` response bytes; it never touches the
story cache, ``section-timelines``, or ``TemporalFilter``.
"""

from autom8_asana.readout.generation import (
    ASSEMBLED_BY,
    GENERATOR_NAME,
    GENERATOR_VERSION,
    HUMAN_IN_LOOP,
    GeneratedOccurrence,
    extract_rows_and_meta,
    render,
)
from autom8_asana.readout.item_1a import (
    G4PrimeBound,
    G4PrimeBranch,
    G4PrimeSign,
    Item1aError,
    Item1aFigure,
    compute_item_1a,
    enumerate_g4_prime,
)
from autom8_asana.readout.template import (
    DenominatorSlot,
    Ex2Disposition,
    ReadoutSlot,
    render_blocks,
    render_fallback_text,
)

__all__ = [
    # generation mechanism
    "ASSEMBLED_BY",
    "GENERATOR_NAME",
    "GENERATOR_VERSION",
    "HUMAN_IN_LOOP",
    "GeneratedOccurrence",
    "extract_rows_and_meta",
    "render",
    # item 1a computation
    "G4PrimeBound",
    "G4PrimeBranch",
    "G4PrimeSign",
    "Item1aError",
    "Item1aFigure",
    "compute_item_1a",
    "enumerate_g4_prime",
    # template
    "DenominatorSlot",
    "Ex2Disposition",
    "ReadoutSlot",
    "render_blocks",
    "render_fallback_text",
]
