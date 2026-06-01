---
artifact_id: HANDOFF-eunomia-to-10x-dev-consumer-gate-zero-consumer-skip-semantics-2026-06-01
schema_version: "1.0"
type: handoff
source_rite: eunomia
target_rite: 10x-dev
handoff_type: assessment
priority: medium
blocking: false
altitude: OPERATIONAL
initiative: ci-cd-test-ecosystem-rationalization-consumer-gate-zero-consumer-skip-semantics
created_at: "2026-06-01T16:00:00Z"
status: proposed
source_artifacts:
  - .sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - .ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - .sos/wip/eunomia/pipeline-inventory-2026-06-01.md
  - .sos/wip/eunomia/test-inventory-2026-06-01.md
evidence_grade: strong
---

# HANDOFF — eunomia → 10x-dev: consumer-gate zero-consumer skip semantics

## Premise

The `autom8y/.github/workflows/sdk-publish-v2.yml` consumer-gate enforces an all-5-satellites-green requirement with `allow_breaking_change=true` as the sole, globally-scoped escape valve — no formal per-consumer skip semantics exist for the case where zero satellites consume the published SDK (or where matching consumers are red for unrelated reasons), so an SDK with an empty consumer-graph (e.g., `autom8y-stt@0.1.0`) is gated by any pre-existing satellite red unrelated to that SDK.

## Evidence

- **Gate surface and override scope (verified at claim-time)**:
  - `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md:143-159` — Section 6 "Consumer-Gate Semantics (ASSESS-3)": documents the all-5-green requirement, hard-coded satellite matrix (`autom8y-ads, autom8y-asana, autom8y-data, autom8y-scheduling, autom8y-sms`) at `autom8y/.github/workflows/sdk-publish-v2.yml:533-538`, and the gate-blocking expression `(needs.consumer-gate.result == 'success' || github.event.inputs.allow_breaking_change == 'true')` at `sdk-publish-v2.yml:690-697`.
  - `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md:466` — ASSESS-3 surface table row pinning the upstream-root locations: `autom8y/.github/workflows/sdk-publish-v2.yml:533-538,690-697`. Classified `UV-P — autom8y monorepo` (cross-repo for eunomia; out-of-scope for in-repo IMPL).

- **Field-incident anchor (operator-supplied)**:
  - `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:54-61` — ASSESS-3 entry: "autom8y-stt@0.1.0 (zero-consumer SDK) blocked by pre-existing red on autom8y-data (DB-creds env gap) and autom8y-asana (lint debt) during consumer-gate validation. Each satellite carries unrelated red; gate demands all 5 green."
  - `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:133` — operator inventory line "Consumer-gate whack-a-mole on a zero-consumer SDK (gate-semantic mismatch)."
  - `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:22` — source-tier row citing the user-pasted whack-a-mole report (`grade: strong`).

- **PT-α verdict (eunomia consolidation pass)**:
  - `.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md:12` — PT-α verdict header; ASSESS-1 root reclassified to branch-protection-required-check-gap (separate finding; documents that PT-α reasoning was applied during this assessment cycle).
  - `.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md:20-24` — batch table B1/B2/B3/B6/B8 (all `ready`). Consumer-gate work appears NOWHERE in the in-repo ready-batch slate, confirming the rite-boundary disposition: surface acknowledged, in-repo CHANGE infeasible.

- **Override-leak open question (cross-rite escalation)**:
  - `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:61` — operator-posed question: "Does the gate's `allow_breaking_change=true` override leak around tests it shouldn't (per the analysis: 'verified in workflow if: conditions')?" — unresolved; requires inspection of the `autom8y/sdk-publish-v2.yml` dispatcher in the autom8y monorepo, which is out of eunomia's working tree.

## Recommended actions

10x-dev should treat this as an upstream-workflow design assessment in the autom8y monorepo. The fix requires editing `autom8y/.github/workflows/sdk-publish-v2.yml` and (optionally) the consumer-gate CLI at `autom8y/.../consumer_gate/cli.py`; both live outside the autom8y-asana satellite tree. Recommended sequence:

1. **Reproduce the false-negative class in the dispatcher repo.** Pull `autom8y/autom8y` (monorepo); confirm at `.github/workflows/sdk-publish-v2.yml:523-697` that the consumer-gate matrix is the hard-coded 5-satellite list and that the gate-blocking expression collapses any unrelated satellite red into a global block unless `allow_breaking_change=true`.
2. **Enumerate the option slate before recommending a fix.** At minimum: (a) all-green strict (status quo); (b) zero-consumer skip — gate auto-passes when the candidate SDK's consumer-graph is empty for the matrix row; (c) impacted-consumer-only gating — gate evaluates only the satellites that import the candidate SDK (requires a satellite→SDK consumer-graph manifest); (d) per-satellite `allow_breaking_change` scoping — narrow the override from global to per-(sdk × satellite). Capture rationale and trade-offs per `option-enumeration-discipline`.
3. **Build the consumer-graph manifest as a prerequisite for (b)/(c)/(d).** A canonical `consumer_graph.yml` (or equivalent) keyed by `sdk → [satellites_that_import_sdk]`, sourced from each satellite's `pyproject.toml` `[tool.uv.sources]` or equivalent, is the structural data the dispatcher needs to compute "zero-consumer" vs "impacted-consumer." Without it, any per-consumer skip logic is heuristic.
4. **Land the fix in the autom8y monorepo via a dedicated initiative.** Author an ADR in `autom8y/.ledge/decisions/` proposing the chosen option, then implement in `sdk-publish-v2.yml`. The change is YAML-and-Python only; no satellite-side changes required (this satellite's `test.yml` is a passive receiver of consumer-gate dispatches).
5. **Verify against the field-incident anchor.** Re-run the publish path for `autom8y-stt@0.1.0` (zero-consumer SDK). Acceptance: gate passes without requiring `allow_breaking_change=true` and without bypassing genuine SDK-impacting failures in the consumer-having SDKs.
6. **Resolve the override-leak open question concurrently.** Inspect the `if:` conditions on every job downstream of the consumer-gate in `sdk-publish-v2.yml` to confirm `allow_breaking_change=true` does not bypass any test or safety check it shouldn't. Document in the same ADR.

**Rollback plan**: The change is contained to `autom8y/.github/workflows/sdk-publish-v2.yml` and (if introduced) a new `consumer_graph.yml`. Revert is a single-PR `git revert` of the workflow edit. No satellite-side coupling means satellites continue receiving consumer-gate dispatches unchanged; the rollback restores the all-5-green requirement immediately on the next dispatched publish. Pin a known-good `sdk-publish-v2.yml` SHA in the rollback PR description for fast recovery.

## Out-of-scope

eunomia explicitly did NOT touch:

- **Any file under `autom8y/.github/workflows/`** — the consumer-gate root surface is in the autom8y monorepo, outside the autom8y-asana working tree. eunomia's authority is satellite-internal; the rite classified this as a `UV-P — autom8y monorepo` finding (`pipeline-inventory-2026-06-01.md:466`).
- **The autom8y-asana `.github/workflows/test.yml` consumer-gate receiver path** — only the unrelated B1 fuzz-artifact-name CHANGE-001 (templated `consumer-gate-wheel-${{ inputs.candidate_sdk_name }}-autom8y-asana`) was made on this satellite's side; the in-repo dispatch-receive contract was not modified to introduce skip semantics.
- **The consumer-gate CLI** (`autom8y/.../consumer_gate/cli.py`, referenced in inventory at the cli.py:259-261 dispatch site) — no behavioural change to the CLI was made or designed.
- **The `allow_breaking_change` override semantics** — eunomia surfaced the global-scope concern (PLAN B1-B8 ready set excludes consumer-gate work entirely) and recorded the operator's open question about override-leak, but did not investigate downstream `if:` conditions in the dispatcher workflow.
- **The satellite consumer-graph manifest** — no `consumer_graph.yml` or equivalent was authored. The structural data required for options (b)/(c)/(d) does not yet exist in either repo.
- **Field-empirical reproduction** — eunomia worked from the user-pasted incident report (`HANDOFF-10x-dev-to-eunomia ...:22`) and the dispatcher YAML it cites; the rite did not re-trigger an `autom8y-stt@0.1.0` publish or otherwise live-reproduce the false-negative.

## Acceptance criteria

10x-dev's work on this handoff is complete when ALL of the following hold:

1. **Option slate enumerated and recorded.** An ADR exists in `autom8y/.ledge/decisions/` (or equivalent in the autom8y monorepo) enumerating at minimum the four options listed in Recommended action 2, with explicit rationale for the chosen option and explicit rejection rationale for each rejected option (per `option-enumeration-discipline`).
2. **Consumer-graph data source identified and either authored or explicitly deferred with a watch-trigger.** Either `consumer_graph.yml` (or equivalent canonical artifact) is committed and consumed by the chosen dispatcher logic, OR the ADR records that the chosen option (e.g., scoped `allow_breaking_change`) does not require it and explains why.
3. **`autom8y/.github/workflows/sdk-publish-v2.yml` modified to implement the chosen semantics.** The gate-blocking expression at `sdk-publish-v2.yml:690-697` (or its replacement) reflects the new policy; the change is committed via a dedicated PR with the ADR referenced.
4. **Field-incident anchor verified-resolved.** A live publish of a zero-consumer SDK (anchored on `autom8y-stt@0.1.0` per the incident report) completes successfully without invoking `allow_breaking_change=true`, captured via a CI run-id linked from the ADR or a follow-up handoff.
5. **Override-leak open question discharged.** The ADR (or a paired analysis artifact) documents the result of inspecting every `if:` condition downstream of the consumer-gate in `sdk-publish-v2.yml`, with a verdict on whether `allow_breaking_change=true` bypasses any test/safety check it shouldn't, plus remediation if leak is confirmed.
6. **Rollback-tested.** The chosen PR's revert path has been mentally or actually walked: pinning the prior `sdk-publish-v2.yml` SHA in the PR description, confirming no satellite-side coupling, and confirming the revert is a single-PR no-data-migration operation.
7. **Satellite-side no-op verified.** No autom8y-asana `.github/workflows/test.yml` change is required by the chosen fix (confirmed by direct inspection of the dispatcher → satellite contract); if any satellite-side change IS required, a follow-up HANDOFF is filed to each affected satellite team.
