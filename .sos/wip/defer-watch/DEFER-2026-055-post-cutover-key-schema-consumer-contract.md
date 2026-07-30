---
type: triage
id: DEFER-2026-055
initiative: substrate-v2-epoch
registered_by: S8-0 pre-gate hardening (principal-engineer)
registered_at: 2026-07-30
status: NOT-MET
---

# DEFER-2026-055 — post-cutover key/schema + consumer-contract evolution

> Registered from the substrate-v2-epoch shape Defer Registry (DEFER-4 row,
> `.sos/wip/frames/substrate-v2-epoch.shape.md:783`) per the `defer-watch-manifest`
> §2 per-item schema.

```yaml
defer_entry:
  id: DEFER-2026-055
  title: >
    post-cutover key/schema + consumer-contract evolution — any change to the storage
    keys, frame schema, or consumer-facing contract AFTER the v2 cutover commits
  source_decision:
    artifact: ".sos/wip/frames/substrate-v2-epoch.shape.md:783"
    verdict_id: >
      substrate-v2-epoch shape §10 Defer Registry — DEFER-4 row (rationale: doors
      #2/#3 committed = load-bearing; future changes are NEW doors)
    deferred_at: "2026-07-29"
  deferral_rationale:
    why_not_now: >
      The cutover COMMITS doors #2 (keys) and #3 (schema) as load-bearing contracts.
      Evolving them post-cutover is not a continuation of this epoch — it is a NEW
      door decision (its own decision-packet), so it must not ride in on the cutover.
    smaller_change_available: false
    smaller_change_reference: null
  watch_trigger:
    trigger_type: event
    trigger_definition: >
      A post-cutover CONSUMER NEED emerges (a downstream consumer requires a key,
      schema, or contract change) → open a NEW door decision-packet; do NOT amend the
      committed cutover contract in place.
    evaluation_cadence: on-signal
    last_evaluated_at: "2026-07-30"
    last_evaluation_result: NOT-MET
  escalation_path:
    reactivation_signal_recipient: >
      operator (new decision-packet) — a key/schema/contract change is an operator
      door decision, authored as a fresh packet.
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-055-reactivation-handoff.md"
    reactivation_invocation: "/frame substrate-v2-post-cutover-contract-evolution"
  owner_rite: >
    operator (new decision-packet)
  scope_boundary:
    must_not_collapse_into:
      - "the committed cutover contract (doors #2/#3 — load-bearing, frozen at cutover)"
      - "S8-0 pre-gate hardening (P5 gate preconditions only)"
    boundary_violation_signal: >
      Any in-place edit to the committed storage keys / frame schema / consumer
      contract after cutover, instead of a new door decision-packet.
```

## Context (non-schema prose)

At cutover, doors #2 (keys) and #3 (schema) become committed, load-bearing contracts
that downstream consumers rely on. Future evolution of those contracts is legitimate but
is a NEW door decision — a fresh operator packet — not a silent amendment of the
just-committed cutover. Registered here so a post-cutover consumer need routes to a new
packet rather than an in-place contract mutation.

## Provenance

- Shape: `.sos/wip/frames/substrate-v2-epoch.shape.md` §10 Defer Registry, DEFER-4
  row (line 783); rationale: doors #2/#3 committed = load-bearing.
- Registered at: S8-0 pre-gate hardening (this PR).
