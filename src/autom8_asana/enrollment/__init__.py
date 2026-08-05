"""Enrollment intent -> scheduling-gate lineage (WS-A of enrollment-integration).

The ONE intent surface (Asana ``custom_cal_status``) reaching the scheduling gate
through ONE governed, role-guarded, receipted write path. Intent is default-OPEN
(charter R1: UNSET -> Enabled is ratified POLICY); EXECUTION is fail-CLOSED (a
bridge that cannot prove its frame is real REFUSES loudly and writes NOTHING).

Design of record:
    ``.ledge/specs/TDD-ws-a-intent-gate-bridge-2026-08-05.md`` (autom8y repo)
    ``.ledge/decisions/ADR-ws-a-bridge-placement-2026-08-05.md`` (FORK-1 -> Option B)

Module map:
    :mod:`~autom8_asana.enrollment.intent_projection`
        WS-A PR-2. PURE (no I/O): the three-frame projection + the four refusal
        predicates. Unit-testable with constructed DataFrames.

★ NOT the WS-B producer. This package NEVER writes the ``scheduling_stratum``
substrate and shares no universe filter with it -- the producer is guid-keyed,
this lineage is PHONE-keyed (see :mod:`~autom8_asana.enrollment.intent_projection`
"UNIVERSE FILTER" for why copying the producer's filter is a named defect, R-12).
"""

from __future__ import annotations

__all__: list[str] = []
