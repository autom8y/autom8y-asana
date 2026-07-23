---
type: triage
id: DEFER-2026-051
initiative: fleet-delegation-portfolio
registered_by: eunomia rationalization-executor (P0 provenance-floor sprint)
registered_at: 2026-07-23
status: DISCHARGED
---

# DEFER-2026-051 — stranded-ADR landing (PREMISE-3) — DISCHARGED at P0

> Registered AND discharged in the same P0 landing per fleet-delegation-
> portfolio `/shape` §9 DEFER Registry: "discharged by P0 -> moves
> DEFER-watch to done at P0 landing." Per the `defer-watch-manifest` skill
> §2 schema, extended with a `promotion_status: DISCHARGED` field (Contract
> 4 lifecycle: this initiative's own wording is DISCHARGED rather than the
> skill's generic SHIPPED terminus — same append-only-provenance
> semantics; the entry is never deleted).
>
> **Precision note (no-overclaim)**: "DISCHARGED" here means the 2 ADRs +
> 2 companion TDDs are tracked in git on branch `feat/p0-provenance-floor`
> (this PR's own exit criteria). The watch-trigger's boolean predicate
> (`git cat-file -e origin/main:<path>`) only resolves TRUE once this PR
> MERGES to origin/main — merge is explicitly NOT performed by this sprint
> (a rite-disjoint critic gates the merge). Any consumer evaluating the
> trigger against `origin/main:` before merge will correctly see NOT-YET;
> re-evaluate after merge lands.

```yaml
defer_entry:
  id: DEFER-2026-051
  title: >
    stranded-ADR landing (PREMISE-3) — entity-resolution-primitive and
    taskcache-projection-coverage ADRs (+ companion TDDs) were phantom
    anchors pending commit to origin/main
  source_decision:
    artifact: ".sos/wip/frames/fleet-delegation-portfolio.md:156-167"
    verdict_id: >
      fleet-delegation-portfolio frame §3 PREMISE-3 (CONFIRMED, SVR
      bash-probe) + /shape §9 DEFER Registry — stranded-ADR-landing row
      (.sos/wip/frames/fleet-delegation-portfolio.shape.md:425); frame §7
      Next Actions item 3b (:416-419)
    deferred_at: "2026-07-22"
  deferral_rationale:
    why_not_now: >
      At frame time (2026-07-22), 2 of the 3 2026-07-07/08 founding ADRs
      (entity-resolution-primitive, taskcache-projection-coverage) were
      confirmed LOCAL-ONLY / NOT-ON-origin/main by direct bash-probe
      (`git cat-file -e origin/main:<path>`, both exit non-zero; the
      third, contact-synthesis-card-on-play, WAS already on origin/main).
      Any downstream stream (notably WS-5/WS-7's org-graph/entity-
      resolution anchor, glint G-15) citing the stranded pair would anchor
      a phantom. Landing them was explicitly routed to a dedicated
      attester-disjoint P0 sprint (eunomia native) rather than folded as a
      side-effect of a build-stream's own commit — a deliberate
      minimal-provenance-closure scope (ADR + companion TDD only; the
      Spike/Defect/Handoff docs the ADRs also reference remain untracked,
      out of this narrow closure's scope).
    smaller_change_available: true
    smaller_change_reference: >
      P0 provenance-floor sprint (this entry's own discharge vehicle) — a
      dedicated minimal-provenance-closure landing, not a build-stream
      side-effect
  watch_trigger:
    trigger_type: external-event
    trigger_definition: >
      any stream needs the entity-resolution (or taskcache-projection-
      coverage) anchor. Boolean-evaluable: `git cat-file -e
      origin/main:.ledge/decisions/ADR-entity-resolution-primitive-2026-07-08.md`
      AND the taskcache-projection-coverage sibling both exit 0 (i.e. both
      committed to origin/main — TRUE only after this PR merges).
    evaluation_cadence: on-explicit-invocation
    last_evaluated_at: "2026-07-23"
    last_evaluation_result: MET
  escalation_path:
    reactivation_signal_recipient: "fleet-delegation-portfolio/potnia"
    reactivation_artifact_path: ".ledge/spikes/DEFER-2026-051-reactivation-handoff.md"
    reactivation_invocation: "/frame stranded-adr-landing-regression-check"
  owner_rite: >
    eunomia (P0 provenance-floor sprint executed the discharge; no
    standing owner required post-discharge)
  scope_boundary:
    must_not_collapse_into:
      - "WS-5/WS-7 entity-resolution/org-graph consumption (MAY anchor to these ADRs once merged to origin/main; must not re-open the provenance-floor question itself)"
    boundary_violation_signal: >
      Any future claim that the entity-resolution-primitive or
      taskcache-projection-coverage ADR is still uncommitted/phantom
      after this PR merges to origin/main — re-verify via the same
      bash-probe (git cat-file -e origin/main:<path>) before asserting
      either way; if the probe contradicts DISCHARGED post-merge, invoke
      /frame stranded-adr-landing-regression-check.
  promotion_status: DISCHARGED
```

## Discharge Receipt

- **Discharged at**: 2026-07-23
- **Discharged by**: eunomia rationalization-executor, P0 provenance-floor
  sprint, branch `feat/p0-provenance-floor`
- **Discharge evidence** (commit SHAs on this branch, PRE-MERGE — the PR
  URL / merge-commit SHA supersedes these once merged):
  - `d70d98d621c2e10b443d09a46551d77aa4b1c775` —
    `docs(ledge): land entity-resolution ADR+TDD` [CHANGE-001]
  - `ef5f1fdae6b6fe5d36e0fdadec6374f025a13017` —
    `docs(ledge): land taskcache-projection ADR+TDD` [CHANGE-002]
- **Residual (explicitly NOT discharged by this entry)**: the ADRs' own
  References sections still cite
  `.ledge/spikes/SPIKE-office-guid-resolution-hierarchy-vs-phone-2026-07-08.md`,
  `.ledge/reviews/DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.md`,
  and their respective `HANDOFF-arch-to-10xdev-*` companions — all still
  untracked at this landing. Per this sprint's explicit scope (ADR +
  companion TDD only — the "minimal provenance closure"), those remain
  phantom references. This is a KNOWN, accepted residual of the P0 scope,
  not a silent gap: any stream that follows those specific citations still
  needs its own landing pass.

## Provenance

- Frame: `.sos/wip/frames/fleet-delegation-portfolio.md` §3 PREMISE-3
  (lines 156-167, SVR CONFIRMED), §7 Next Actions item 3b (lines 416-419)
- Shape: `.sos/wip/frames/fleet-delegation-portfolio.shape.md` §9 DEFER
  Registry, stranded-ADR-landing row (line 425)
- This PR: branch `feat/p0-provenance-floor`, commits `d70d98d6` +
  `ef5f1fda`
