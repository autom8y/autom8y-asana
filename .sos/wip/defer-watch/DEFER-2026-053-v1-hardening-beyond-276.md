---
type: triage
id: DEFER-2026-053
initiative: substrate-v2-epoch
registered_by: S8-0 pre-gate hardening (principal-engineer)
registered_at: 2026-07-30
status: NOT-MET
---

# DEFER-2026-053 — v1 hardening beyond #276

> Registered from the substrate-v2-epoch shape Defer Registry (DEFER-2 row,
> `.sos/wip/frames/substrate-v2-epoch.shape.md:781`) per the `defer-watch-manifest`
> §2 per-item schema.

```yaml
defer_entry:
  id: DEFER-2026-053
  title: >
    v1 hardening beyond #276 — any further investment in the legacy v1 serving path
    past the #276 entity-aware prober fix
  source_decision:
    artifact: ".sos/wip/frames/substrate-v2-epoch.shape.md:781"
    verdict_id: >
      substrate-v2-epoch shape §10 Defer Registry — DEFER-2 row (rationale: P6 freeze)
    deferred_at: "2026-07-29"
  deferral_rationale:
    why_not_now: >
      P6 FREEZE: v1 is being cut over, not hardened. Investing in new v1 code
      contradicts the extinction path and the legacy-floor-isolation stance (v1 is a
      FLOOR to clear, never a benchmark to keep improving).
    smaller_change_available: false
    smaller_change_reference: null
  watch_trigger:
    trigger_type: event
    trigger_definition: >
      A v1 refusal FIRES in production → the response is an operator RE-BASELINE
      (re-anchor the cutover baseline), NOT new v1 code. The trigger reactivates a
      re-baseline decision, never a v1 hardening sprint.
    evaluation_cadence: on-signal
    last_evaluated_at: "2026-07-30"
    last_evaluation_result: NOT-MET
  escalation_path:
    reactivation_signal_recipient: >
      operator (until S11 extinction) — the operator owns the re-baseline call; no
      rite is authorized to open new v1 code.
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-053-reactivation-handoff.md"
    reactivation_invocation: "operator re-baseline (NOT /frame v1-hardening)"
  owner_rite: >
    operator (until S11 extinction)
  scope_boundary:
    must_not_collapse_into:
      - "S8-0 pre-gate hardening (v2-harness scope; ZERO src/ edits)"
      - "any epoch sprint (all v2 cutover work)"
    boundary_violation_signal: >
      Any change that adds NEW v1 serving-path code in response to a v1 refusal,
      instead of an operator re-baseline.
```

## Context (non-schema prose)

The #276 entity-aware prober fix is the LAST v1 investment. Past that, v1 is frozen
(P6) and on a path to extinction (S11). If v1 refuses in production, the correct move
is an operator re-baseline of the cutover, never a new v1 patch. Registered here so a
v1 refusal does not silently reopen v1 development.

## Provenance

- Shape: `.sos/wip/frames/substrate-v2-epoch.shape.md` §10 Defer Registry, DEFER-2
  row (line 781); rationale P6 freeze.
- Registered at: S8-0 pre-gate hardening (this PR).
