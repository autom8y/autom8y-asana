"""Foundation-first floodgates batch seam (MVP).

A per-office **two-phase state machine** that turns the ACTIVE onboarding set into a
repeatable one-command-per-office motion, composing the already-proven onboarding
primitives **pure-Asana, operator-run** (NOT the DEPLOYED-DARK
``OnboardingWalkthroughWorkflow``). Design of record:
``.ledge/specs/TDD-floodgates-batch-seam-2026-07-07.md``.

Reserved-lever boundary (module contract):

* **DOES**: resolve office guid (pure-Asana, task-bound), compose the gated routing
  address, freeze the deck (Node producer), mint + pin the capability slug, host-stage
  into a per-office Cloudflare-Pages deploy root, verify SERVED byte-parity, post the
  three marker-idempotent PLAY comments (link / rep-template-v3 / contact-card).
* **SURFACES**: the exact ``wrangler pages deploy`` command (Phase-1 HALT) — printed for
  the operator, NEVER executed.
* **NEVER**: runs ``wrangler`` (the CF deploy is a reserved operator lever); sends the
  client email (the Nova/Intercom SEND is a reserved operator lever).
"""

from __future__ import annotations
