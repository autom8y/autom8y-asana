"""Forwarding-Stage backfill (S4): derive each existing clinic's stage from
monolith log evidence and (optionally) stamp the Calendar Integrations board.

Pre-flip, EBI is dark -- there are no satellite witness rows -- so the ONLY
truth about the whole flowing book is the legacy monolith's own
``/ecs/monolith-prod`` logs. This package reads that trail, derives a proposed
Forwarding Stage per clinic (pure ``domain.forwarding_stage_backfill``), feeds it
through the UNCHANGED S1 ``StageTransitionValidator`` (never-downgrade,
fail-closed, idempotent), and produces a PLAN artifact (``--dry-run`` DEFAULT,
zero writes) or per-task stamps (``--apply``, gated on the S1 write config).

Modules:
  - ``config``          BackfillConfig (log group, window, query templates,
                        regexes; env/CLI-bound -- the monolith log grammar is DATA)
  - ``evidence_source`` MonolithEvidenceSource port + CloudWatchInsightsEvidenceSource
  - ``backfill``        orchestrator: gather -> derive -> resolve -> validate -> plan/apply
  - ``cli``             argparse `plan` (default) | `apply`; `python -m` entry
"""
