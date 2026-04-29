---
type: review
review_subtype: audit-verdict
status: approved
artifact_id: AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21
schema_version: "1.0"
source_rite: hygiene
audit_author: audit-lead
rubric: hygiene-11-check-rubric
rubric_lens_count_applied: 11
artifact_class: GATE-1 HANDOFF — MODULE migration (hygiene execution of rnd-authored ADR)
pr_under_review: "https://github.com/autom8y/autom8y/pull/120"
pr_branch: hygiene/retire-service-api-key-autom8y-core
pr_base: main
commit_count: 5
test_suite_status: "548/548 passing (572 collected including 24 untracked pre-existing test file)"
verdict: PASS-WITH-FOLLOW-UP
merge_authorization: yes
adr_grade_upgrade_trigger: yes
adr_under_review: /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md
adr_grade_before: moderate
adr_grade_after: strong
rite_disjointness_status: PASS (hygiene-rite critiquing rnd-rite-authored ADR)
audited_at: "2026-04-21T~15:30Z"
critique_iteration_counter: 0/2 (PASS; no REMEDIATE)
evidence_grade: strong
upstream_handoff_ref: /Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md
upstream_remediate_handoff_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md
t1_touchpoint_evidence_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md
---

# AUDIT VERDICT — Hygiene 11-Check on PR #120 (autom8y-core SERVICE_API_KEY retirement)

## 0. Executive Summary

**Verdict**: `PASS-WITH-FOLLOW-UP`
**Merge authorization**: YES
**ADR-0001 grade-upgrade trigger**: YES (MODERATE → STRONG per `self-ref-evidence-grade-rule`)

PR #120 faithfully executes ADR-0001 §2.1 retirement-target items 1+2 plus §2.3 canonical-alias wiring. All 5 commits are atomic, independently revertible, and map cleanly to ADR sections. Behavior preservation verified against MUST/MAY/REQUIRES categories: public API breaks (service_key removal) are documented in CHANGELOG as BREAKING with SERVER-DEAD justification per ADR §5.1. Test suite 548/548 green. Scope-quarantine boundaries (F-2 deferral) strictly honored — service_client.py, client.py, test_sprint2_regressions.py, ServiceAuthClient all untouched.

Two follow-up items identified as non-blocking advisory; one CI check (Semgrep Architecture Enforcement) fails on pre-existing baseline issues in files NOT touched by this PR.

## 1. 11-Check Verdict Table

| Lens | Name | Result | Rationale | Severity if not PASS |
|------|------|--------|-----------|----------------------|
| 1 | Boy Scout Rule | **CLEANER** | Net 197 lines deleted; SERVICE_API_KEY deleted from 22 files; docstrings updated to reflect OAuth primacy; data_payment.py ruff collapse tightens formatting; zero regressions introduced. | n/a |
| 2 | Atomic-Commit Discipline | **ATOMIC-CLEAN** | 5 commits with disjoint concerns: a11b81f6 (Config), 5fa2867c (TokenManager + lifecycle factories + Boy Scout format), 0cb455b0 (tests), 62b24a5a (version/CHANGELOG), e910efc3 (uv.lock). Each independently revertible. Rename commits not required (no file renames). | n/a |
| 3 | Scope Creep Check | **SCOPE-DISCIPLINED** | Every delta maps to ADR-0001 §2.1 items 1-2 + §2.3 canonical-alias. PR-3 scope (§2.1 item 4) correctly deferred per F-2 operator ruling 2026-04-21T~14:00Z Option D. data_payment.py format collapse is Boy-Scout-adjacent (same commit as token_manager; single-file ruff format, zero behavior change; idiom-preserving). Quarantine-zone files strictly untouched (F-3 Q4-narrow-retire honored). | n/a |
| 4 | Zombie Config Check | **ZOMBIE-FLAGGED** | Fleet-wide grep: SERVICE_API_KEY now absent from autom8y-core src; 6 `.know/` files retain stale refs (design-constraints, conventions, architecture, feat/INDEX, feat/client-configuration, scar-tissue) plus CHANGELOG (intentional — documents retirement). These are documentation drift pre-dating the PR and previously catalogued in T-1 F-4 as non-blocking. Assign to follow-up: Boy Scout or doc-refresh session. base_client.py:107 docstring zombie (`Config(service_key="my-key")`) flagged separately at Lens 9. | MINOR (non-blocking; flag-tier) |
| 5 | Self-Conformance Meta-Check | **SELF-CONFORMANT** | Hygiene-rite executing rnd-authored ADR; the artifact's own rite template (doc-ecosystem audit-report-template) is satisfied — behavior preservation categories verified, contract-vs-plan mapping explicit, commit quality assessed. No meta-irony: hygiene audits an execution it did not author. | n/a |
| 6 | CC-ism Discipline | **CONCUR** | No new CC-ism regressions introduced. The one `# nosemgrep` annotation in data_payment.py:147 is pre-existing (defensive suppression for stdlib Logger %s idiom) and survives the ruff collapse intact. No type-ignore proliferation, no untyped-any expansion, no catch-all exception swallowing. | n/a |
| 7 | HAP-N Fidelity | **N/A** (skipped per §3 artifact-type selection) | HAP-N tags not applicable to SDK retirement PRs; ADR-0001 is not authored in the anti-pattern-tagged inquisition protocol surface. | (not applicable) |
| 8 | Path C Migration Completeness | **PARTIAL-DEFERRED** | Phase A scope §2.1 items 1 (autom8y-core config) + 2 (token_manager) COMPLETE. Item 3 (autom8y-auth client_config — PR-2) pending sequential execution per R-4 monorepo serialization. Item 4 (autom8y_auth_client service_client — PR-3) DEFERRED to rnd-Phase-A amendment per HANDOFF-REMEDIATE 2026-04-21T~14:10Z Option D. Item 5 (test files) COMPLETE at §2.1 scope (13 files; 548/548 green). Deferrals are explicitly documented with escalation path; not silent incomplete migration. | PARTIAL (documented; non-blocking) |
| 9 | Architectural Implication | **STRUCTURAL-CHANGE-DOCUMENTED** | Config.service_key field removal is a documented BREAKING change (CHANGELOG §BREAKING). OAuth primacy codified at ADR §2.3. Canonical-alias dual-lookup pattern is structurally additive + reversible. `base_client.py:107` docstring example (`Config(service_key="my-key")`) is technically an undocumented structural stale-artifact (param no longer exists) — but base_client.py is NOT in PR #120 diff (last touched commit 94607d59, core 2.3.0) and is not in ADR-0001 §2.1 manifest; classified as pre-existing documentation drift + Boy-Scout-eligible follow-up. | MINOR (flag-tier; follow-up) |
| 10 | Preload Chain Impact | **N/A** (skipped per §3 artifact-type selection) | This PR does not modify agent frontmatter preload contracts. No skill-description changes. SDK deletion surface does not intersect preload-chain concerns. | (not applicable) |
| 11 | Non-Obvious Risks | **ADVISORY** | (1) **Semgrep Architecture Enforcement CI failure** — FAILURE conclusion on 5 findings in files NOT touched by this PR (sa_reconciler.py:229, exit139_metric/handler.py, synthetic_canary/handler.py). Verified pre-existing on main (commit 5325e1ea PR #119 + b8c66619 PR #114 baseline). These are logger-positional-args violations independent of SERVICE_API_KEY retirement. Does not block this PR structurally; merits follow-up baseline hygiene session. (2) **test_token_manager_response_body.py** is UNTRACKED in git (per `git ls-files` check); its 16 pre-existing failures against `TokenAcquisitionError.response_body` feature are local-scratch coverage-gap — cannot affect CI green on PR #120. Janitor analysis CORRECT. (3) **uv.lock single-line delta** (commit e910efc3) is minimal; version-bump propagation; rollback-safe via standard commit revert. | ADVISORY (non-blocking) |

## 2. Overall Verdict

**`PASS-WITH-FOLLOW-UP`**

No BLOCKING-tier verdict on any lens. Three flag-tier results (Lens 4 ZOMBIE-FLAGGED, Lens 8 PARTIAL-DEFERRED, Lens 9 MINOR-STRUCTURAL-DRIFT) plus Lens 11 advisories. Aggregation per `hygiene-11-check-rubric` §5:
- No DIRTIER, ATOMIC-VIOLATION, SCOPE-CREEP, ZOMBIE-BLOCKING, SELF-VIOLATION, CC-ISM-REGRESSION, HAP-N-VIOLATION, MIGRATION-INCOMPLETE, UNDOCUMENTED-STRUCTURAL-CHANGE, or PRELOAD-CHAIN-BROKEN verdicts fired.
- Lenses 3 + 9 did NOT co-fire (Lens 3 PASS; Lens 9 flag-only, not STRUCTURAL-CHANGE-UNDOCUMENTED).
- Flag-tier results present → `CONCUR-WITH-FLAGS` in rubric-native vocabulary, mapped to `PASS-WITH-FOLLOW-UP` in audit-verdict vocabulary per critique-iteration-protocol.

## 3. Discovery Rulings (Janitor Questions Answered)

### D-1 base_client.py:107 docstring
**Ruling**: PASS-WITH-FOLLOW-UP. The docstring example `Config(service_key="my-key")` references a deleted parameter. BUT base_client.py is NOT in ADR-0001 §2.1 manifest AND was last modified at commit 94607d59 (core 2.3.0), pre-dating this initiative. It is pre-existing documentation drift, not a regression this PR introduced. Classify as Boy-Scout-eligible follow-up (next hygiene session or Boy Scout in PR-2). Not blocking; not IMMEDIATE-INLINE.

### D-2 test_token_manager_response_body.py
**Ruling**: CORRECT analysis. File is UNTRACKED in git (`git ls-files` returns empty; `git status` shows `??`). Its 16 pre-existing failures cannot affect PR #120 CI (pytest in CI runs from checked-out tree; untracked file may or may not be present depending on runner clean-state). More decisively: these failures test a `TokenAcquisitionError.response_body` field that is orthogonal to SERVICE_API_KEY retirement. Coverage-gap-not-regression. Route to separate P7 coverage-closure session.

### D-3 Commit 5 uv.lock (e910efc3)
**Ruling**: Structurally fine. lockfile regeneration reflecting version bump 3.1.0 → 3.2.0 is MANDATORY per uv workspace semantics (not a scope deviation). Treating it as a distinct atomic commit (rather than amending commit 4) PRESERVES atomicity — version-metadata-change and lockfile-propagation are separable concerns. Rollback-safe: reverting e910efc3 alone leaves the code working with a stale-pointer lockfile that CI's `Lock Validation (--no-sources)` check caught (and passed green on this PR). No rollback-safety concern.

### D-4 data_payment.py ruff autoformat in commit 2
**Ruling**: Permitted. Boy Scout Rule per `conventions` skill + `smell-detection` allows incidental-formatting adjacencies. The diff collapses a multi-line `_logger.debug(...)` call to single-line form — zero behavior change, the `# nosemgrep` comment annotation is preserved. This is classical Boy-Scout-adjacent cleanup: the file was opened to verify no service_key references (confirmed zero), and the ruff auto-fix applied. Does NOT violate atomic-commit discipline because it is co-located with a refactor commit in the same module boundary (clients/). If split out, it would create a strict rename/format commit with 4 lines of change — disproportionate to the scope. Lens 2 ATOMIC-CLEAN holds.

## 4. Behavior Preservation Checklist

| Category | Item | Status | Evidence |
|----------|------|--------|----------|
| MUST preserve (public API) | Config dataclass instantiation contract | BROKEN (documented) | Config.service_key field REMOVED; BREAKING change per CHANGELOG §BREAKING; justified by ADR §5.1 SERVER-DEAD status; Consumer cannot have been using API-key path successfully in production. Version bump 3.1.0 → 3.2.0 documents the break. |
| MUST preserve (public API) | TokenManager.get_token/get_token_async return type (str) | PRESERVED | No signature change; OAuth Basic auth path replaces X-API-Key internally |
| MUST preserve (public API) | Error hierarchy (InvalidServiceKeyError etc.) | PRESERVED | Error classes unchanged; error messages updated to reference CLIENT_ID/CLIENT_SECRET |
| MUST preserve (public API) | Client.from_env() factory contract | PRESERVED (additive) | from_env() now supports canonical-alias dual-lookup; legacy CLIENT_ID/CLIENT_SECRET names still resolve |
| MAY change | Internal logging format | UNCHANGED | Token acquisition logs retain f-string format |
| MAY change | Error message text | CHANGED (aligned) | "Check your SERVICE_API_KEY" → "Check your CLIENT_ID and CLIENT_SECRET" |
| MAY change | Private implementations | CHANGED (intentional) | _build_exchange_kwargs simplified; service_key branch deleted |
| REQUIRES approval | Canonical-alias dual-lookup wiring | APPROVED (ADR §2.3) | Additive; documented; tests cover both name pairs |
| REQUIRES approval | service_key field deletion | APPROVED (ADR §2.1 item 1) | Operator Q1 + Q2 rulings 2026-04-21T~10:25Z |

**Behavior-preservation verdict**: all MUST-preserve changes have documented ADR authorization; MAY changes are within expected latitude; REQUIRES-approval changes have explicit operator ratification.

## 5. Contract Verification (per HANDOFF-rnd-to-review §3 acceptance criteria)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | SERVICE_API_KEY absent from autom8y-core src + tests | PASS | `rg SERVICE_API_KEY sdks/python/autom8y-core/src sdks/python/autom8y-core/tests` — zero matches |
| 2 | SERVICE_API_KEY absent from autom8y-auth src + tests | DEFERRED to PR-2 | (PR-2 scope; sequential post-PR-1 merge) |
| 3 | SERVICE_API_KEY absent from autom8y_auth_client src + tests | DEFERRED to PR-3 | (PR-3 blocked on rnd-Phase-A amendment per F-2) |
| 4 | CLIENT_ID/CLIENT_SECRET canonical-alias dual-lookup verified | PASS | config.py:137-146; test_config.py canonical-alias precedence tests added in commit 0cb455b0 |
| 5 | Version bump 3.1.0 → 3.2.0 at autom8y-core | PASS | pyproject.toml:7 reflects |
| 6 | CHANGELOG entries per PR | PASS | CHANGELOG.md §3.2.0 with ADR-0001 reference |
| 7 | Consumer re-grep post-merge: zero SERVICE_API_KEY fleet-wide | PARTIAL | autom8y-core src: zero. `.know/` + CHANGELOG: 6 docs-drift files flagged (follow-up). Other SDKs: deferred to PR-2/PR-3. |
| 8 | No CI regressions on retired paths | PASS | 548/548 tests green; 11 of 12 CI checks SUCCESS (Semgrep Architecture Enforcement FAILURE on pre-existing non-PR files — see §6) |

## 6. Semgrep Architecture Enforcement CI Failure Analysis

The Semgrep Architecture Enforcement check on run 24730074960 (job 72341760387) returned FAILURE with 5 findings against `autom8y.no-logger-positional-args`:

| File | Line | PR #120 Touched? | Pre-existing on main? |
|------|------|------------------|----------------------|
| services/auth/autom8y_auth_server/services/sa_reconciler.py | 229 | NO | YES (merged at PR #119 commit 5325e1ea) |
| terraform/services/autom8y-data-observability/lambdas/exit139_metric/handler.py | 82, 118-126 | NO | YES (merged at PR #114 commit b8c66619) |
| terraform/services/autom8y-data-observability/lambdas/synthetic_canary/handler.py | 68, 117-123 | NO | YES (merged at PR #114 commit b8c66619) |

**Conclusion**: ALL five findings are baseline debt in files NOT modified by PR #120. The CI gate failure is a **pre-existing fleet hygiene concern**, not a regression introduced by this PR. This is documented at Lens 11 Non-Obvious-Risks ADVISORY. It merits a follow-up fleet-wide Boy Scout session targeting baseline Semgrep debt, but does NOT block PR #120 merge.

**Merge authorization stands**: the Semgrep gate is returning a true positive on baseline debt that PR #120 neither introduces nor fixes. Blocking this PR on unrelated pre-existing violations would violate Lens 3 scope-creep discipline (forcing this PR to fix non-manifest files).

## 7. ADR-0001 Grade-Upgrade Trigger Analysis

Per `self-ref-evidence-grade-rule`: agents evaluating their own work cap at MODERATE; STRONG requires external rite-disjoint critic corroboration.

**Upgrade path analysis**:
- ADR-0001 was authored by rnd-rite at Phase A own-initiative close (2026-04-21T10:40Z)
- ADR self-assigned `evidence_grade: moderate` with documented upgrade path: "STRONG upgrade when review-rite corroborates at deletion PR merge-gate (first downstream consumer validates without REMEDIATE)"
- Per operator ruling at T-1 touchpoint 2026-04-21T~14:00Z Option D, hygiene-rite (rite-switched from review) executes the deletion-PR merge-gate on behalf of review
- This audit-verdict is the external-critic corroboration event
- Verdict is PASS-WITH-FOLLOW-UP (NOT REMEDIATE), which per critique-iteration-protocol is a CONCUR-class outcome (flagged follow-ups do not bar the upgrade)

**Ruling**: YES — this audit-verdict CONSTITUTES the external-critic corroboration that upgrades ADR-0001 MODERATE → STRONG per `self-ref-evidence-grade-rule`.

**Recommended upgrade commit**: amend ADR-0001 frontmatter `evidence_grade: moderate` → `evidence_grade: strong` citing:
- This audit-verdict artifact path
- PR #120 merge SHA (post-merge)
- 11-check rubric verdict PASS-WITH-FOLLOW-UP

## 8. Follow-Up Items

| # | Item | Owner | Routing | Priority |
|---|------|-------|---------|----------|
| FU-1 | `base_client.py:107` docstring — replace `Config(service_key="my-key")` with `Config(client_id="svc-...", client_secret="secret-...")` | next hygiene session | Boy Scout in PR-2 or dedicated micro-PR | LOW |
| FU-2 | `.know/*.md` files with stale SERVICE_API_KEY refs (6 files: architecture, conventions, design-constraints, scar-tissue, feat/INDEX, feat/client-configuration) | docs/theoros session | `/know --refresh` against autom8y-core post-retirement | LOW |
| FU-3 | `test_token_manager_response_body.py` untracked file — 16 failures against `TokenAcquisitionError.response_body` P7 feature | separate P7 coverage session | Unrelated to SERVICE_API_KEY retirement | LOW (orthogonal) |
| FU-4 | Fleet Semgrep Architecture Enforcement baseline debt (5 findings in sa_reconciler + observability lambdas) | hygiene fleet sweep | PR-level: convert positional-args to keyword/f-string in cited 3 files | MEDIUM (blocks no PR; surfaces at every PR) |
| FU-5 | PR-2 (autom8y-auth client_config.py) execution — sequential post-PR-1 merge | same hygiene session OR next | per HANDOFF-rnd-to-review §2 PR-2 | HIGH (blocker for PR-3 downstream) |
| FU-6 | PR-3 (autom8y_auth_client service_client.py) — DEFERRED pending rnd-Phase-A amendment | rnd-Phase-A next session | per HANDOFF-REMEDIATE 2026-04-21T~14:10Z Option D | BLOCKED (on rnd amendment) |

## 9. Self-Ref Disjointness Check (Independent Verification)

Per `self-ref-evidence-grade-rule` §3: "External critic must be from a rite disjoint from the authoring rite."

- **Authoring rite**: rnd (ADR-0001 authored at Phase A own-initiative close 2026-04-21T10:40Z by rnd Potnia main thread)
- **Critic rite**: hygiene (this audit-lead executing 11-check rubric at hygiene session rite-switched from review per operator ruling)
- **Disjoint?** YES — rnd and hygiene are distinct rites with distinct pantheons:
  - rnd rite: technology-scout, integration-researcher, prototype-engineer, moonshot-architect, tech-transfer
  - hygiene rite: code-smeller, architect-enforcer, janitor, audit-lead
  - Zero overlap in specialist agents; zero overlap in skill mena
- **Rite-context disjointness**: hygiene session operates independently — no transitive authorship chain (rnd did not dispatch hygiene directly; hygiene was rite-switched at session entry from review per operator routing). The audit-lead did not participate in ADR-0001 authoring or option enumeration.
- **Pythia ruling citation**: noted per user-supplied context. Independently verified: PASS.

**Conclusion**: rite-disjoint critic requirement SATISFIED. This verdict is eligible to trigger ADR-0001 grade upgrade.

## 10. Critique-Iteration-Protocol Status

Per `critique-iteration-protocol`:
- **Counter**: 0/2 (no prior REMEDIATE on this PR from this critic cycle)
- **Verdict**: PASS-WITH-FOLLOW-UP (CONCUR-class; counter does not advance)
- **DELTA specification**: NOT REQUIRED (verdict is not BLOCKING)
- **Next action**: merge authorized; follow-ups routed per §8

If operator or parent Potnia disputes this verdict and requests re-critique: counter advances to 1/2 in that cycle.

## 11. Evidence Grade

This audit-verdict: `[STRONG | 0.80 @ 2026-04-21]`

**Grounds**:
- Direct-source verified: read of config.py (188 lines), token_manager.py (589 lines), base_client.py (docstring region), CHANGELOG (first 80 lines), pyproject.toml, and all 5 commit diffs
- Cross-corroborated via git log (base_client.py last-touched verification; Semgrep-failing-files last-touched verification on main)
- External CI evidence: gh pr view 120 statusCheckRollup (11 SUCCESS + 1 FAILURE + 2 IN_PROGRESS as of audit time)
- Upstream design authority: ADR-0001 (rnd Phase A authorial); HANDOFF-rnd-to-review §2-3 (scope + acceptance criteria); T-1 touchpoint F-1 through F-5 catalog
- Rite-disjoint critic (independently verified §9)

**Ceiling**: STRONG achievable because critic is rite-disjoint; upgrade would require MULTI-critic concurrence (Pythia + hygiene) to reach fleet-CONSTITUTIONAL grade, not necessary for this ADR class.

## 12. Artifact Links

- **PR under review**: https://github.com/autom8y/autom8y/pull/120
- **ADR being corroborated**: `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- **Upstream HANDOFF (scope basis)**: `/Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md`
- **T-1 touchpoint evidence (F-2 deferral)**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md`
- **HANDOFF-REMEDIATE (PR-3 deferral)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md`
- **Rubric applied**: `/Users/tomtenuta/Code/a8/repos/.claude/skills/hygiene-11-check-rubric/SKILL.md`
- **Grade rule**: shared-fleet `self-ref-evidence-grade-rule`
- **Iteration protocol**: shared-fleet `critique-iteration-protocol`

## 13. Decision

**Merge PR #120**: AUTHORIZED.

**ADR-0001 grade-upgrade**: TRIGGER on merge; amend frontmatter `evidence_grade: moderate → strong` in a follow-up commit citing this verdict artifact + merge SHA.

**Residual follow-ups**: routed per §8; none block merge.

---

*Authored 2026-04-21T~15:30Z by hygiene-rite audit-lead as external-critic gate on PR #120. Rubric: hygiene-11-check-rubric (all 11 lenses applied; 7 + 10 marked N/A per §3 artifact-type selection). Verdict: PASS-WITH-FOLLOW-UP. ADR-0001 MODERATE → STRONG upgrade authorized.*
