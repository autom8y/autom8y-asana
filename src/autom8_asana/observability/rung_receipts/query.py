"""Query surface for RUNG E limb (a): raw events -> limb (a) observation.

Two entry points:

* ``run_query(events)`` -- pure function. Takes an iterable of raw log events
  (each a dict carrying an ``event`` field), splits them into the delivery and
  generation streams by event name, runs the join, and returns the durable
  ``LimbAObservation`` dict. This is what an attester (eunomia
  verification-auditor) calls; it is deterministic and hermetic.

* ``main(argv)`` -- a thin CLI reading newline-delimited JSON events from a file
  or stdin and printing the observation as JSON. Demonstrates the schema is
  mechanically consumable, not a document.

The production ingestion path pairs this with the two read-only CloudWatch Logs
Insights queries in ``schema.py``
(``DELIVERY_LOGS_INSIGHTS_QUERY`` / ``GENERATION_LOGS_INSIGHTS_QUERY``) over
``/aws/lambda/autom8y-account-status-recon``. This module does not itself call
AWS -- keeping it hermetic and reproducible by any consumer without credentials.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from autom8_asana.observability.rung_receipts.join import (
    join_occurrences,
    observe_limb_a,
)
from autom8_asana.observability.rung_receipts.schema import (
    DELIVERY_EVENT,
    GENERATION_EVENT,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def run_query(events: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Split raw events by type, join, and return the limb (a) observation dict.

    Args:
        events: raw log events; each dict SHOULD carry an ``event`` field of
            ``report_posted`` (delivery) or ``report_generated`` (generation).
            Events of any other type are ignored.

    Returns:
        The durable ``LimbAObservation`` dict (both ladders, receipts inline).
    """
    delivery_events: list[Mapping[str, object]] = []
    generation_events: list[Mapping[str, object]] = []
    for evt in events:
        name = evt.get("event")
        if name == DELIVERY_EVENT:
            delivery_events.append(evt)
        elif name == GENERATION_EVENT:
            generation_events.append(evt)
    receipts = join_occurrences(delivery_events, generation_events)
    return observe_limb_a(receipts).to_dict()


def _load_jsonl(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def main(argv: list[str] | None = None) -> int:
    """CLI: read JSONL events from a path (or stdin) and print the observation."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("-", "/dev/stdin"):
        with open(argv[0], encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()
    observation = run_query(_load_jsonl(text))
    print(json.dumps(observation, indent=2))  # noqa: T201 — CLI stdout is the interface
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
