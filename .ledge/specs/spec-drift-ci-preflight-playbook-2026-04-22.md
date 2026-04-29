---
type: spec
artifact_id: spec-drift-ci-preflight-playbook-2026-04-22
schema_version: "1.0"
title: "Spec-Drift CI-Preflight Playbook (D-01 Class-of-Problem Durable Fix)"
status: proposed
lifecycle_state: proposed
rite: sre
initiative: fleet-ci-hygiene
created_at: "2026-04-22"
evidence_grade: WEAK
evidence_grade_ceiling_rationale: |
  Self-referential authoring (SRE observability-engineer specifies a CI gate whose
  implementation owner resolves to a cross-rite handoff, not a concrete individual
  at authoring time). Per self-ref-evidence-grade-rule, MODERATE is the in-rite
  ceiling; per deliverable brief explicit instruction, WEAK is warranted when the
  implementation owner cannot be named at authoring time as a concrete individual.
  Promotion to MODERATE requires hygiene/platform handoff acceptance + owner
  identification; promotion to STRONG requires a wild-caught spec-drift instance
  where this gate demonstrably catches a near-miss before merge.
handoff_targets:
  - hygiene-rite (reviewer; anchor-point for fleet CI hygiene gates)
  - platform-engineer (implementer; owns CI workflow YAML + scripts)
---

# Spec-Drift CI-Preflight Playbook

## 1. Problem Statement

**D-01 is the third spec-check-stale incident this arc.** Inherited-from-main after PR #132 OTEL router changes, the class-of-problem is: OpenAPI router code changes merge without a paired `openapi.json` regeneration, producing downstream `spec-check` failures that cascade into unrelated PRs and block CI on the main branch.

The failure shape is consistent across all three occurrences:
- A router file is modified (endpoint added, renamed, or signature changed).
- The committed `openapi.json` is NOT regenerated.
- CI passes on the originating PR because `spec-check` is run as an advisory/non-blocking gate OR the check was not wired for the affected surface.
- The next PR that runs `spec-check` fleet-wide surfaces the drift as a failure — but the offending change has already merged, so the blame is decorrelated from the cause.
- Rollback-on-red-main becomes the recovery path, costing 30–90 min per occurrence AND decorrelating blame from cause.

**Class-of-problem**: a cause-and-effect asymmetry where the author of a change cannot be held accountable at merge time because the gate enforcement runs at the wrong moment in the lifecycle.

## 2. Scope

### In-scope (what this playbook covers)
- OpenAPI spec drift: router code changes that require `openapi.json` regeneration.
- Detection runs **on the originating PR**, not on a downstream PR.
- Initially scoped to `autom8y-ads` repo (canary); extended fleet-wide on successful canary rollout.

### Out-of-scope (explicitly NOT this playbook)
- Non-OpenAPI contract drift (GraphQL schema, protobuf, SDK fixture regeneration) — separate but analogous playbooks may follow.
- Semantic API compatibility checking (breaking-change detection across spec versions) — covered by fleet `semantic-score` gate already landed in PR #12.
- Runtime API behavior drift (spec matches code, but code behavior changed) — contract-test responsibility, not spec-drift.

## 3. Detection Mechanism

### 3.1 File-glob triggers

A CI-preflight hook fires on any PR that modifies files matching these globs (union — any match triggers):

```
# Router sources
src/**/routers/**/*.py
src/**/router.py
src/**/routes.py
src/**/api/**/*.py
autom8y_*/api/**/*.py

# FastAPI app definitions + dependency wiring
src/**/main.py
src/**/app.py
src/**/dependencies.py
src/**/deps.py

# Pydantic models referenced in response/request schemas
src/**/schemas/**/*.py
src/**/models/**/*.py
```

### 3.2 Detection logic

The hook performs these steps:

1. **Snapshot spec at HEAD~1** (base commit before PR changes).
2. **Regenerate spec at HEAD** (current PR tip) by invoking the repo's spec-generator script (e.g., `uv run python -m autom8y_ads.tools.generate_openapi`) in a hermetic environment.
3. **Diff regenerated spec vs committed `openapi.json`**.
4. **Fail loudly** if the diff is non-empty — this means the PR changed router/schema code but did NOT commit a corresponding `openapi.json` update.

### 3.3 Hermeticity requirement

The preflight must run the spec-generator in the same Python env as the app code (same `uv sync`) to avoid false positives from env drift. If the app's `uv sync` fails, the preflight SKIPs with a warning (not a fail) — CI's environment-build gate catches that class separately.

### 3.4 Gated repos (canary → fleet rollout)

| Phase | Repos | Trigger |
|-------|-------|---------|
| Phase 1 (canary) | `autom8y-ads` | Proven on one repo before fleet expansion |
| Phase 2 (expansion) | `autom8y`, `autom8y-asana`, `autom8y-agent` | Canary must run 2 weeks with zero false positives |
| Phase 3 (fleet) | All fleet service repos with OpenAPI surfaces | Phase 2 must report zero false positives AND ≥1 true positive catch |

## 4. Fail-Loud Signal

### 4.1 CI status name

`spec-drift / ci-preflight` — appears as a distinct check in the PR's check suite.

### 4.2 Failure message (printed to CI logs + PR annotation)

```
FAIL: Spec drift detected on this PR.

Router/schema code changes were found, but the committed openapi.json does
not match the spec regenerated from current HEAD.

Affected files (globs matched):
  - src/autom8y_ads/routers/campaigns.py
  - src/autom8y_ads/schemas/ad_unit.py

Regenerate and commit the spec BEFORE merge:

    cd <repo-root>
    uv sync
    uv run python -m <module>.tools.generate_openapi > openapi.json
    git add openapi.json
    git commit -m "chore: regenerate openapi.json"

Why this gate exists: the D-01 class-of-problem (third occurrence this arc)
means router changes that merge without paired spec regeneration cascade
into downstream PRs as inherited-from-main failures, costing rollback time
and decorrelating blame from cause.

Playbook: autom8y-asana/.ledge/specs/spec-drift-ci-preflight-playbook-2026-04-22.md
```

### 4.3 PR annotation

GitHub check annotations attach inline comments to the offending router files with: "This file triggered spec-drift preflight; regenerate openapi.json before merge."

## 5. Remediation Flow (Developer-Facing)

If you hit this gate on your PR:

1. **Do not bypass**. The gate exists because of a recurring cost-shift pattern where bypassed drift becomes someone else's rollback.
2. **Regenerate the spec locally**:
   ```bash
   uv sync
   uv run python -m <your-module>.tools.generate_openapi > openapi.json
   ```
3. **Review the diff**: `git diff openapi.json`. Unexpected changes? Your router refactor may have unintentionally changed the API shape (removed response field, changed status code). **Fix the router** if the spec diff is wrong, then regenerate.
4. **Commit the regenerated spec**: `git add openapi.json && git commit -m "chore: regenerate openapi.json for <change>"`.
5. **Push**; the preflight re-runs and should pass.

### Common false-positive patterns (escape hatches)

| Scenario | Action |
|----------|--------|
| You modified a router file but made no API-surface change (e.g., added a comment, renamed an internal helper) | The preflight will pass because regenerated spec matches committed. No action. If it DOES fail: the regenerator is nondeterministic — file a complaint. |
| You touched a router to reference a new schema that isn't wired into an endpoint yet | Commit an unchanged `openapi.json`; the preflight passes. The schema only affects spec when referenced by an endpoint. |
| The regenerator itself is broken (bug in spec-generation tooling) | SKIP label: apply `skip-spec-drift-preflight` label + comment reason + link to regenerator-fix PR. CODEOWNERS approval required for label application. |

## 6. Integration Points

### 6.1 Where this hooks in existing CI

- **Position**: runs as part of the **hygiene** rite's PR-validation workflow, alongside `ruff`, `mypy`, `semantic-score` (PR #12 baseline lock).
- **Ordering**: runs AFTER `uv sync` (needs deps to invoke generator) and BEFORE `pytest` (fails fast on drift before slow test suite runs).
- **Blocking status**: BLOCKING on protected branches (`main`). Advisory on feature branches. CODEOWNERS for `.github/workflows/` must approve any transition from blocking to advisory.

### 6.2 Relationship to existing gates

| Existing gate | Relationship |
|---------------|--------------|
| `semantic-score` (PR #12 baseline lock) | Complementary. `semantic-score` detects breaking API changes across spec versions. This playbook detects when spec is stale relative to code on the **current** PR. Different layer. |
| `ruff` + `mypy` | Independent. Runs in parallel. |
| `pytest` | Upstream of this preflight. If `uv sync` fails, pytest also won't run; preflight SKIPs with warning. |
| `spec-check` (existing, advisory) | This playbook SUPERSEDES the advisory spec-check with a blocking equivalent. Advisory version should be retired once blocking version is Phase 3 fleet-wide. |

### 6.3 Hook point in settings/config

Canonical hook location: `.github/workflows/ci-preflight-spec-drift.yml` in each gated repo. Configuration lives in the workflow YAML; no separate config file required.

## 7. Rollout Plan

### Phase 1: Canary (`autom8y-ads`, weeks 1–2)

**Entry criteria**: playbook approved by hygiene-rite + platform-engineer.

**Deliverables**:
1. `.github/workflows/ci-preflight-spec-drift.yml` in `autom8y-ads`.
2. Workflow runs on every PR; reports BLOCKING status.
3. Runbook link in failure message points to this playbook.

**Exit criteria**:
- 2 weeks of operation with zero false positives, OR
- Any false positive root-caused and fixed (in the regenerator, not bypassed in the gate), before expansion.

### Phase 2: Expansion (autom8y + autom8y-asana + autom8y-agent, weeks 3–4)

**Entry criteria**: Phase 1 exit criteria met.

**Deliverables**:
1. Workflow replicated in 3 additional repos (templated via shared workflow if feasible; otherwise per-repo YAML).
2. Telemetry: track catches (true positives), bypass-label uses, SKIPs.

**Exit criteria**:
- Zero false positives across 4 repos for 2 weeks.
- At least 1 true positive catch (a real spec drift blocked at origin PR) — this validates the gate is doing useful work.

### Phase 3: Fleet (all OpenAPI surfaces, weeks 5+)

**Entry criteria**: Phase 2 exit criteria met.

**Deliverables**:
1. Workflow extended to all fleet repos with OpenAPI surfaces.
2. Retire the advisory `spec-check` gate on protected branches fleet-wide.
3. Update fleet hygiene docs to list this gate in the canonical gate catalog.

### Rollback plan (any phase)

If the gate produces >2 false positives/week at any phase: pause rollout, investigate regenerator determinism, fix root cause, resume. Do NOT demote from blocking to advisory as a false-positive mitigation — this reintroduces the D-01 class-of-problem.

## 8. Implementation Owner

**Named owner**: **unresolved at authoring time**.

**Why unresolved**: this playbook is authored by the SRE rite (observability-engineer), but the implementation is a CI workflow — platform-engineer territory. The owner assignment requires:
- hygiene-rite acceptance that this gate belongs alongside existing hygiene CI gates.
- platform-engineer commitment to implement the workflow YAML.

**Handoff path to resolve ownership**:
1. This spec is consumed by the main thread after Wave 1 return.
2. Main thread dispatches a cross-rite HANDOFF to hygiene-rite (playbook acceptance) + platform-engineer (implementation).
3. On HANDOFF acceptance, a concrete owner is named, and this field is updated. Evidence grade can then promote from WEAK to MODERATE.

**Explicit WEAK-grade rationale**: per the deliverable brief's anti-phantom-implementation guidance, shipping a playbook without a named owner is shipping a phantom. The grade is downgraded to WEAK and the owner-resolution is a gating condition for any promotion. This is documented here so the consuming main thread can make an informed routing decision.

## 9. Anti-Pattern Guard: "Creating Alerts Without Runbooks"

This playbook IS the runbook for a CI alert class. The CI failure message (§4.2) explicitly points to this playbook's path. Any future modification to the gate that adds a new failure mode must update this playbook in the same PR — the gate and the runbook co-evolve.

## 10. Success Criteria

- **6 months post Phase 3**: zero inherited-from-main spec-drift incidents. (Current baseline: 3 in recent arc.)
- **Gate catches** (true positives) tracked in fleet hygiene telemetry; trend should match or exceed the baseline drift rate.
- **Developer friction** measured via PR-cycle-time on PRs that hit the gate. Expected: small increase (+1 cycle to regenerate and push) vs. the current cost (rollback-on-red-main for the fleet).

## 11. References

- PR #132 — OTEL router changes that introduced the D-01 instance inherited-from-main.
- PR #12 — `semantic-score` baseline lock (complementary gate).
- PR #14 — `semantic-score` workflow canonical location (`.github/workflows/`).
- Anti-pattern: "Creating alerts without runbooks" — sre observability-engineer domain knowledge.
- HANDOFF-sre-to-10x-dev-pr131-11-blocking-remediation-2026-04-22 §D-9 (related but distinct: spec-check on PR #131 needs a manual regen this cycle; this playbook prevents future recurrences).

## 12. Evidence Grade

**WEAK** at authoring. Promotion path:
- **→ MODERATE** upon: owner named + hygiene/platform handoff accepted.
- **→ STRONG** upon: wild-caught spec-drift incident where this gate demonstrably blocks the drift at origin PR (the "canary catches a real fish" bar per deliverable brief).

---

*Authored 2026-04-22 by SRE observability-engineer as Phase α deliverable of parallel dispatch. For 10x-dev consumption at next CC restart; non-committing at authoring (main thread owns commit-authoring after Wave 1 returns).*
