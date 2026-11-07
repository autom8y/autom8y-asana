---
type: decision
status: accepted
artifact_class: redacted pointer to a private ratification
ratified_at: 2026-11-07
scope: the onboarding-deck workflow (floodgates `onboard-deck-*` recipes; the calendar-integration PLAY card story)
record_of_truth: private operator repository, `.ledge/decisions/RATIFICATION-onboarding-deck-workflow-decision-space-2026-11-07.md`
---

# Pointer: onboarding-deck workflow decision-space (redacted)

The operator ratified the decision-space for the onboarding-deck workflow in a structured
interview on 2026-11-07. The full record lives in the operator's private repository (see
`record_of_truth`). This file is the public-repo pointer. It carries the rulings that shape
the code in this repository and omits every client name, account identifier and forwarding
address.

## Rulings that bind this repository

| # | Ruling |
|---|---|
| D1 | Correctness first. The forwarding address and the clinic name are never wrong, even if a run is delayed or refused. |
| D2 | Done, per client, means the three comments (deck link, rep template, contact card) are on the client's PLAY card. |
| D3 | Delivery to the client is the rep's job and out of scope. The workflow ends at the card. |
| D5 | Stage A only: the one-command recipes, run on demand. No automatic trigger. |
| D6 | Stage B (an automatic trigger) is deferred until activations exceed about eight a month. |
| D7 | An agent may run the recipes under a standing written grant. The operator reviews each run's log afterward. |
| D8 | The grant covers produce, the Cloudflare deploy and the Asana post for any qualifying card, and requires a log of each run. |
| D9 | The agent proceeds only if the clinic name in the card title matches the parent Business task's name. On a mismatch it stops and asks. |
| D10 | Before go-live: (a) the forwarding address comes from the client's own Business record; (b) an automated rendered-deck check shows only that address, with no placeholder or unfilled field; (c) the name is confirmed per D9. The live byte-parity check stays. |
| D11 | The "binds every SEND" ruling (DW-7) does not apply: the send is the rep's, and the deploy publishes an unlinked, noindex page. |
| D12 | The full record is private; this redacted pointer sits beside the code. |
| D13 | Build the D9 and D10(b) additions on the Stage A branch first, then scan with gitleaks at the CI pin and open the PR. |
| D14 | No review bench sits between the grant and a run. |

## Where the rulings land in code

- D9: `onboarding_walkthrough/floodgates/name_match.py`, wired into the produce path of `floodgates/office_runner.py` before any freeze or mint.
- D10(b): `onboarding_walkthrough/render_check.py`, run after staging in produce and again as the deploy gate in the `onboard-deck-deploy` recipe. It fails closed when no browser is found; it never skips and never downloads one.
- Runbook: `docs/runbooks/RUNBOOK-onboard-deck.md`.

## Deferred (not taken up here)

Stage B (trigger, durable state, producer in ECS); Stage C (Cloudflare deploy in CI); delivery tracking; the dark sweep Lambda; backfill of clients activated while the flow was dark.
