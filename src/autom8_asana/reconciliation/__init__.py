"""Reconciliation module for unit-to-offer activity matching.

Per REVIEW-reconciliation-deep-audit: This module implements the reconciliation
pipeline that matches unit activity states against offer activity states,
identifies mismatches, and optionally moves Asana tasks to corrected sections.

Module: src/autom8_asana/reconciliation/__init__.py
"""

from __future__ import annotations

from autom8_asana.reconciliation.engine import (
    ReconciliationResult,
    run_reconciliation,
)
from autom8_asana.reconciliation.processor import ReconciliationBatchProcessor
from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_GIDS,
    EXCLUDED_SECTION_NAMES,
    UNIT_SECTION_GIDS,
)

__all__ = [
    "EXCLUDED_SECTION_GIDS",
    "EXCLUDED_SECTION_NAMES",
    "ReconciliationBatchProcessor",
    "ReconciliationResult",
    "UNIT_SECTION_GIDS",
    "run_reconciliation",
]
