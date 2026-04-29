---
type: handoff
artifact_id: HANDOFF-sre-to-hygiene-main-recovery-plus-pr136-amendment-2026-04-22
schema_version: "1.0"
source_rite: sre (CI diagnosis Lane 1 close)
target_rite: hygiene
handoff_type: implementation
priority: high
blocking: false  # unblocks 7/10 CI failures fleet-wide once merged
status: proposed
handoff_status: pending
initiative_parent: autom8y-core-aliaschoices-platformization (Phase C operationalization)
sprint_source: "SRE Lane 1 CI diagnosis 2026-04-22; agent aba75022c55e0a926"
sprint_target: "hygiene janitor + audit-lead execution of main-branch-recovery + PR #136 interop stub amendment"
emitted_at: "2026-04-22T00:30Z"
expires_after: "14d"
design_references:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/DIAGNOSIS-ci-failures-3pr-2026-04-21.md  # Lane 1 diagnosis; §4.1 + §4.3 scope
  - /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md  # STRONG; §2.1 items 2+5 are the deferred scope completing here
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md  # PR #120 PASS-WITH-FOLLOW-UP audit (verifies these items were known-deferred)
evidence_grade: strong  # cross-rite boundary artifact synthesizing Lane 1 diagnosis + ADR-0001 §2.1 audit follow-up + operator R1 ruling
operator_ruling: R1 hygiene (janitor + audit-lead pattern)
---

# HANDOFF — SRE → Hygiene (Main-Recovery + PR #136 Interop Stub)

## 1. Context

Per CI diagnosis Lane 1 (`DIAGNOSIS-ci-failures-3pr-2026-04-21.md`), 7 of 10 failing signatures across PR #131/#136/#13 trace to **main-branch brokenness inherited by downstream PRs** — NOT to PR-specific regressions. The dominant sub-causes:

1. **PR #120 incomplete ADR-0001 §2.1 landing** (items 2+5 deferred at PASS-WITH-FOLLOW-UP audit):
   - `autom8y/sdks/python/autom8y-core/src/autom8y_core/token_manager.py:375,378` still reference retired `Config.service_key`
   - 5 test files in autom8y-auth test suite still reference SERVICE_API_KEY / Config.service_key expectations

2. **PR #119 (unrelated sprint) left 5 Semgrep `no-logger-positional-args` violations** in:
   - `sa_reconciler/` (likely `handler.py` + supporting modules)
   - `terraform observability lambdas/` (likely custom metric emitters)

3. **autom8y-interop 5-line purge-stub lacks `[dependency-groups]` metadata** (PR #136 inherits the breakage)

## 2. Scope — 2 Bundles (Main-Recovery + PR #136)

### Bundle A — Main-Branch Recovery PR (new PR, targets `autom8y/autom8y` main)

Complete ADR-0001 §2.1 deferred items + fix PR #119 lint debt + fix interop purge-stub:

| Sub-task | File | Action |
|---|---|---|
| A.1 | `autom8y/sdks/python/autom8y-core/src/autom8y_core/token_manager.py:375` | Delete SERVICE_API_KEY-path reference |
| A.2 | `autom8y/sdks/python/autom8y-core/src/autom8y_core/token_manager.py:378` | Delete SERVICE_API_KEY-path reference |
| A.3 | 5 autom8y-auth test files (identify via grep) | Migrate test expectations from SERVICE_API_KEY/Config.service_key to OAuth 2.0 CLIENT_ID/CLIENT_SECRET canonical-alias path |
| A.4 | sa_reconciler — 5 Semgrep violations | Apply `no-logger-positional-args` fix (quote-escape or keyword-args conversion) |
| A.5 | terraform observability lambdas — Semgrep violations subset | Same fix pattern as A.4 |
| A.6 | autom8y/packages/autom8y-interop/pyproject.toml (or purge-stub location) | Add `[dependency-groups]\ndev = []` to satisfy CI dep-group discovery |

CHANGELOG entry:
```
- COMPLETE ADR-0001 §2.1 items 2+5 deferred at PR #120 PASS-WITH-FOLLOW-UP
- FIX PR #119 Semgrep no-logger-positional-args violations
- FIX autom8y-interop purge-stub [dependency-groups]
```

### Bundle B — PR #136 amendment (val01b SDK mirror; already open)

Bundle A above addresses the interop purge-stub dependency-groups fix at main-branch altitude. PR #136 MAY auto-pass post-main-recovery merge on rebase. If residual PR-specific failures remain after rebase (val01b-local test fixtures etc.), author minimal amendment commits within the existing PR.

## 3. Acceptance Criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | Main-recovery PR merged to `autom8y/autom8y` main | gh pr view; merge SHA recorded |
| 2 | Post-merge fleet re-grep `rg SERVICE_API_KEY autom8y/` confirms zero hits in `token_manager.py` + autom8y-auth tests | Grep output captured |
| 3 | Post-merge fleet Semgrep clean re-run passes on `autom8y/` | Semgrep log captured |
| 4 | PR #136 rebased onto main-recovery merge → CI re-runs → green OR explicit residual-amendment commits land + CI green | PR #136 CI statusCheckRollup |
| 5 | Hygiene audit-lead 11-check-rubric applied to main-recovery PR | AUDIT-VERDICT file at `autom8y-asana/.ledge/reviews/` |
| 6 | ADR-0001 evidence_grade remains STRONG (audit-lead verdict is 4th corroboration event) | ADR-0001 frontmatter verified |
| 7 | Evidence grade [STRONG] cross-rite-boundary on handoff-response | Per self-ref-evidence-grade-rule |

## 4. Entry Conditions

1. Read this HANDOFF
2. Read DIAGNOSIS artifact (`DIAGNOSIS-ci-failures-3pr-2026-04-21.md`) §1+§4.1+§4.3 for evidence substrate
3. Read ADR-0001 §2.1 items 2+5 (deferred scope completing here)
4. Read PR #120 AUDIT-VERDICT (`AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md`) — verify whether the FOLLOW-UP items list matches Bundle A scope; if DIVERGES, surface to operator as scar-scope mismatch
5. Hygiene-Potnia orchestrates standard janitor + audit-lead cycle

## 5. Escalation Triggers

| Trigger | Action |
|---------|--------|
| PR #120 AUDIT-VERDICT FOLLOW-UP items list diverges from Bundle A Lane 1 findings | ESCALATE to SRE main-thread for reconciliation before authoring |
| Bundle A item discovers ADDITIONAL inherited-from-main brokenness not in Lane 1 scope | Expand Bundle A scope OR file separate HANDOFF if beyond hygiene authority |
| PR #119 Semgrep violations root to a ruleset change rather than code-authoring miss | Consult forge/ecosystem rite before fix execution |
| PR #136 residual amendment exceeds 3 REMEDIATE+DELTA cycles | ESCALATE per critique-iteration-protocol cap |

## 6. Response Protocol

Hygiene-Potnia emits at session close:
- Path: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-hygiene-main-recovery-plus-pr136-to-sre-{date}.md`
- Verdict: ACCEPTED-WITH-MERGE / PARTIAL-MERGE / REMEDIATE+DELTA / ESCALATE
- Includes: main-recovery merge SHA + ADR-0001 audit-lead verdict + PR #136 post-rebase CI status

## 7. Evidence Grade

`[STRONG]` at emission.

## 8. Artifact Links

- DIAGNOSIS (primary): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/DIAGNOSIS-ci-failures-3pr-2026-04-21.md`
- ADR-0001: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- PR #120 AUDIT-VERDICT: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md`
- PR #136: `https://github.com/autom8y/autom8y/pull/136`

---

*Emitted 2026-04-22T00:30Z SRE Lane 1 close → hygiene dispatch.*
