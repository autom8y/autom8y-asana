---
type: review
review_subtype: audit-verdict
status: accepted
artifact_id: AUDIT-VERDICT-hygiene-11check-pr125-autom8y-auth-2026-04-21
schema_version: "1.0"
source_rite: hygiene
audit_author: audit-lead
rubric: hygiene-11-check-rubric
rubric_lens_count_applied: 11
artifact_class: GATE-1 HANDOFF — MODULE migration (hygiene execution of rnd-authored ADR; T-2 in-session expansion)
pr_under_review: "https://github.com/autom8y/autom8y/pull/125"
pr_branch: hygiene/retire-service-api-key-autom8y-auth
pr_base: main (at 82ba4147 — PR-1 merge)
commit_count: 3
test_suite_status: "PR-2 scope tests: 117/117 green (test_client_config.py + tests/clients/test_base.py + tests/clients/test_auth_admin_client.py). Full suite: 646 passed, 10 failed, 80 errors — all failures/errors in quarantine zone (test_http_client.py, test_token_manager*.py, test_client_errors.py) inherited from PR-1 baseline. Delta vs main: +42 passing, -35 failures, ±0 errors (PR-2 strictly improves baseline)."
verdict: PASS-WITH-FOLLOW-UP
merge_authorization: yes
t2_expansion_verdict: VALIDATED
t2_expansion_precedent_set: "layer-depth discriminator (dataclass-refactor with pattern-precedent is in-rite-scope; HTTP/auth-flow refactor requires cross-rite-handoff) is VALIDATED. Future F-2-class findings may apply this discriminator to expand in-session when (a) pattern precedent exists from prior PR in same initiative, (b) refactor stays within single dataclass boundary + direct tests, (c) quarantine-zone boundaries strictly honored."
adr_grade_upgrade_trigger: no  # per self-ref-evidence-grade-rule: ADR-0001 already STRONG from PR-1; PR-2 is ratification-ripple, not a grade-motion event
adr_under_review: /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md
adr_grade_before: strong
adr_grade_after: strong
rite_disjointness_status: PASS (hygiene-rite audit-lead critiquing rnd-rite-authored ADR execution; no new disjointness concerns introduced by T-2 expansion)
audited_at: "2026-04-21T~18:00Z"
critique_iteration_counter: 0/2 (PASS-WITH-FOLLOW-UP; no REMEDIATE fired)
evidence_grade: strong
upstream_handoff_ref: /Users/tomtenuta/Code/a8/repos/.ledge/reviews/HANDOFF-rnd-to-review-sdk-deletion-prs-2026-04-21.md
upstream_remediate_handoff_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md
t1_touchpoint_evidence_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/T1-touchpoint-2026-04-21-f2-scope-undercapture.md
pr1_precedent_verdict_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-VERDICT-hygiene-11check-pr120-autom8y-core-2026-04-21.md
t2_ruling_ref: "hygiene-Potnia Option AA in-session expansion ruling 2026-04-21T~15:00Z (layer-depth discriminator)"
pattern_precedent_commit: a11b81f6  # PR-1 canonical-alias wiring in autom8y-core/src/autom8y_core/config.py
---

# AUDIT VERDICT — Hygiene 11-Check on PR #125 (autom8y-auth SERVICE_API_KEY retirement; T-2 expanded)

## 0. Executive Summary

**Verdict**: `PASS-WITH-FOLLOW-UP`
**Merge authorization**: YES
**T-2 expansion verdict**: **VALIDATED** — layer-depth discriminator holds as scar-tissue precedent
**ADR-0001 grade impact**: NONE (already STRONG from PR-1; PR-2 is ratification-ripple, not grade-motion)

PR #125 faithfully executes ADR-0001 §2.1 retirement-target item 3 (autom8y-auth `ClientConfig`) PLUS the T-2-authorized expansion (field replacement + canonical-alias dual-lookup + repr masking). All 3 commits are atomic, independently revertible, and map cleanly to ADR sections. The refactor mirrors PR-1 commit `a11b81f6` precisely — no novel design, no auth-flow layer intrusion, no quarantine-zone touches. Test suite 117/117 green within PR-2 scope; full suite baseline strictly improved (+42 passing, -35 failures vs main). Behavior preservation verified: public API break (`service_key` field removal) documented as BREAKING in CHANGELOG with ADR-0001 authorization.

Three follow-up items identified as non-blocking advisory (.know/ doc drift, README drift, token_manager.py legacy-ref mypy-latent). Four janitor-flagged anomalies all resolved as PASS or follow-up (none BLOCKING).

## 1. 11-Check Verdict Table

| Lens | Name | Result | Rationale | Severity if not PASS |
|------|------|--------|-----------|----------------------|
| 1 | Boy Scout Rule | **CLEANER** | Net +307/-112 lines (additions predominantly in tests to cover canonical-alias dual-lookup paths + new OAuth fixtures). Source: +35/-14 in client_config.py — same sign as PR-1 (canonical-alias dual-lookup is additive). Zero regressions introduced. PR-2 scope-test pass count 117/117 up from main's 82/117 (35 tests previously broken on main by PR-1 now GREEN because autom8y-auth ClientConfig is now field-aligned with autom8y-core Config). | n/a |
| 2 | Atomic-Commit Discipline | **ATOMIC-CLEAN** | 3 commits with disjoint concerns: eaf918b1 (source refactor), e107311f (test migration), 937a6bad (CHANGELOG). Each independently revertible. Janitor-flagged "commit collapse" (planned 2 source commits merged into 1) is LEGITIMATE per `conventions` spirit — both planned splits modified the same file (`client_config.py`) and mid-file split violates atomic-revert discipline (a partial revert of the "field-swap" commit would leave from_env() referencing non-existent fields). Boundary decision accepts same-file-same-concern coalescing. No rename commits required (no file renames in diff). | n/a |
| 3 | Scope Creep Check | **SCOPE-DISCIPLINED** | T-2 expansion EXCEEDS HANDOFF §2 PR-2 literal scope but is AUTHORIZED by hygiene-Potnia 2026-04-21T~15:00Z (Option AA) via layer-depth discriminator. Every delta maps to either (a) ADR-0001 §2.1 item 3 (literal) or (b) ADR-0001 §2.3 canonical-alias (by-extension, rehearsed at PR-1 commit a11b81f6). PR deltas: (1) env-read delete + (2) error msg + (3) docstrings = literal; (4) field swap + (5) canonical-alias + (6) repr masking = T-2 expansion rehearsed from PR-1. CHANGELOG addition (commit 3) is Boy-Scout-adjacent and package-norm-compliant (autom8y-auth has pre-existing CHANGELOG per Keep-a-Changelog). Quarantine-zone files strictly untouched: zero touches to service_client.py (N/A here), token_manager.py, clients/_base.py (source), test_sprint2_regressions.py, ServiceAuthClient refs. Operator Q4 "narrow retire (SDK-cores only)" compliance: autom8y-auth ClientConfig IS an SDK-core dataclass (parallel to autom8y-core Config); retirement at this layer is WITHIN Q4 scope, not adjacent violation. | n/a |
| 4 | Zombie Config Check | **ZOMBIE-FLAGGED** | Fleet-wide grep of `SERVICE_API_KEY\|service_key` in autom8y-auth/src returns 22 hits — all accounted: (a) `token_manager.py` lines 353/355/357/375/378/382/472 → PR-3 quarantine zone (auth-flow layer; cross-rite-handoff pending rnd-Phase-A amendment via HANDOFF-REMEDIATE). These are expected legacy-fallback references in the HTTP/auth-flow layer that the T-2 discriminator intentionally defers. (b) `clients/__init__.py` + `clients/auth_admin.py` + `clients/_base.py:107` → all are `list_service_keys()`/`create_service_key()` etc. — these are AuthAdminClient METHOD names (OAuth service-account provisioning API surface), NOT the SERVICE_API_KEY retirement target. Method names mirror the `/internal/service-keys` admin endpoint naming; unchanged by ADR-0001 (admin endpoints retain naming per Zero Trust uniform-retire Q2 scope which targets auth FLOW not admin RESOURCE name). (c) `_base.py:107` docstring `ClientConfig(service_key="my-key")` → stale example after PR-2 field removal; flag-tier follow-up (same class as PR-1's D-1 base_client.py:107). `.know/` doc drift: 4 files retain SERVICE_API_KEY/service_key refs (architecture.md, feat/token-manager.md, feat/INDEX.md, feat/http-client.md); README.md also drift. All pre-existing documentation drift previously catalogued under PR-1 FU-2 pattern; non-blocking. | MINOR (non-blocking; flag-tier — inherits FU-2 pattern from PR-1) |
| 5 | Self-Conformance Meta-Check | **SELF-CONFORMANT** | Hygiene-rite audit-lead executing 11-check on hygiene-rite janitor's execution of rnd-Phase-A-authored ADR. Meta-test: does audit-lead's OWN rubric grade this artifact conformant? Yes — contracts verified, behavior preservation categories mapped, commit quality assessed, T-2 expansion justification audited against layer-depth discriminator criteria. No self-irony: the rubric's own "scope-creep" lens explicitly accommodates authorized expansion via "untracked deltas are scope additions" — T-2 expansion is TRACKED (documented in PR body, operator-surfaced risk flag, Potnia ruling). No meta-violation. | n/a |
| 6 | CC-ism Discipline | **CONCUR** | No new CC-ism regressions introduced. No `# type: ignore` additions in source. No exception-swallowing. No untyped `Any` expansion. mypy clean on client_config.py (verified). ruff check clean on client_config.py (verified). ruff format clean (verified). One `# type: ignore[arg-type]` survives in token_manager.py lines 392/409 (pre-existing on `client.post(url, **kwargs)`; unchanged by PR-2; quarantine zone). | n/a |
| 7 | HAP-N Fidelity | **N/A** (skipped per §3 artifact-type selection) | HAP-N tags not applicable to SDK retirement PRs; ADR-0001 is not authored in the anti-pattern-tagged inquisition protocol surface. Matches PR-1 Lens 7 ruling. | (not applicable) |
| 8 | Path C Migration Completeness | **PARTIAL-DEFERRED** | ADR-0001 §2.1 item 3 (autom8y-auth client_config) COMPLETE via T-2 expansion. Items 1+2 (autom8y-core) COMPLETE via PR-1. Item 4 (autom8y_auth_client service_client / PR-3) DEFERRED to rnd-Phase-A amendment per HANDOFF-REMEDIATE 2026-04-21T~14:10Z Option D. Item 5 (test files) COMPLETE at PR-2 scope (117 tests green; 35 formerly-broken tests on main now passing). Deferrals are explicitly documented with escalation path via existing HANDOFF-REMEDIATE artifact; not silent incomplete migration. Live touchpoints enumerated: (a) cross-file refs → token_manager.py 6 hits intentionally deferred; (b) shared templates → N/A for this PR; (c) potnia frontmatter → N/A for this PR. Fleet-wide grep mandatory discharge: executed above at Lens 4. | PARTIAL (documented; non-blocking; inherits PR-1's Lens 8 ruling pattern) |
| 9 | Architectural Implication | **STRUCTURAL-CHANGE-DOCUMENTED** | `ClientConfig.service_key` field removal is a BREAKING change documented in CHANGELOG §Breaking Changes. Two new fields (`client_id`, `client_secret`) added with matching defaults (empty string) and `__post_init__` validation. `__repr__` boundary correctly redrawn: `client_id` exposed plaintext (public OAuth identifier per RFC 6749 §2.3.1 — client IDs are NOT secrets), `client_secret` masked as `***` (matches PR-1 precedent at commit a11b81f6). Canonical-first / legacy-fallback ordering in `from_env()` is consistent with ADR-0001 §2.3 and val01b ADR-ENV-NAMING-CONVENTION Decision 4 (`AUTOM8Y_DATA_SERVICE_CLIENT_ID` preferred, `CLIENT_ID` fallback). Structural diff from PR-1 Config: autom8y-auth ClientConfig uses plain `os.environ.get` (no `_resolve_secret()` Lambda Extension protocol) — intentional, because autom8y-auth ClientConfig is a thin client-side config dataclass, not the server-integrated Config. No AP-7 waiver triggered (not applicable to SDK deletion). | n/a |
| 10 | Preload Chain Impact | **N/A** (skipped per §3 artifact-type selection) | This PR does not modify agent frontmatter preload contracts. No skill-description changes. SDK dataclass refactor surface does not intersect preload-chain concerns. Matches PR-1 Lens 10 ruling. | (not applicable) |
| 11 | Non-Obvious Risks | **ADVISORY** | (1) **token_manager.py lines 375-378 unreachability**: after PR-2, `self.config.service_key` references 3 distinct Config sources depending on import path. `ClientConfig` from `autom8y_auth.client_config` no longer has `service_key` field (PR-2 removed it). But `token_manager.py` imports from `autom8y_core` and operates on `autom8y_core.Config` — which ALSO no longer has `service_key` (removed in PR-1 commit a11b81f6). Therefore `self.config.service_key` references in token_manager.py are now mypy-latent UNREACHABLE code paths — mypy strict mode would surface `attr-defined` errors. Verified via inspection: `token_manager.py:375` is dead-code reachable only if `self.config` is neither autom8y_core.Config nor autom8y_auth.ClientConfig (impossible by construction). This is a PR-3 cleanup prerequisite — not a PR-2 regression. (2) **test_client_errors.py::test_invalid_key_error_guidance_no_key pre-existing failure**: error message "Service API key is invalid, expired, or revoked. Check your SERVICE_API_KEY environment variable." in `token_manager.py:470-473` fails assertion `"SERVICE_API_KEY" in message or "environment" in message.lower()`. Wait — message contains BOTH "SERVICE_API_KEY" AND "environment". Assertion SHOULD pass. Verified via direct test execution: assertion failure reads `'SERVICE_API_KEY' in 'Service API key is invalid, expired, or revoked.'` — this shows the InvalidServiceKeyError is being raised WITHOUT the full 2-sentence message (only first sentence). The test construction likely instantiates the error class directly with 1-arg default, bypassing the multi-sentence message. PRE-EXISTING on main; not introduced by PR-2; auth-flow layer → PR-3 scope. (3) **CI status**: GitHub PR shows `mergeStateStatus: UNSTABLE` — flagged for follow-up. Likely the same Semgrep Architecture Enforcement CI baseline issue from PR-1 verdict Lens 11. Not structurally blocking. (4) **Worktree execution note**: initial test run from wrong directory (main checkout) produced misleading 82-failure count; correct worktree at `.worktrees/retire-service-api-key-auth` produced 10-failure/646-pass count. Operational hygiene note: future audits should verify worktree path before test execution. | ADVISORY (non-blocking) |

## 2. Overall Verdict

**`PASS-WITH-FOLLOW-UP`**

No BLOCKING-tier verdict on any lens. Three flag-tier results (Lens 4 ZOMBIE-FLAGGED, Lens 8 PARTIAL-DEFERRED, Lens 11 ADVISORY x4). Aggregation per `hygiene-11-check-rubric` §5:
- No DIRTIER, ATOMIC-VIOLATION, SCOPE-CREEP, ZOMBIE-BLOCKING, SELF-VIOLATION, CC-ISM-REGRESSION, HAP-N-VIOLATION, MIGRATION-INCOMPLETE, UNDOCUMENTED-STRUCTURAL-CHANGE, or PRELOAD-CHAIN-BROKEN verdicts fired.
- Lenses 3 + 9 did NOT co-fire (Lens 3 PASS; Lens 9 STRUCTURAL-CHANGE-DOCUMENTED, not STRUCTURAL-CHANGE-UNDOCUMENTED).
- Flag-tier results present → `CONCUR-WITH-FLAGS` in rubric-native vocabulary, mapped to `PASS-WITH-FOLLOW-UP` in audit-verdict vocabulary per critique-iteration-protocol.

## 3. Discovery Rulings (Janitor-Flagged Anomalies Resolved)

### Anomaly 1: test_client_errors.py pre-existing failure
**Ruling**: PASS (NOT IN PR-2 SCOPE). Confirmed pre-existing on main (baseline also failed this test). The `InvalidServiceKeyError` default message in `token_manager.py:470-473` references `SERVICE_API_KEY` literal — this is the PR-3 quarantine zone (auth-flow layer error messages). Assigning to PR-3 error-message update is the correct disposition. This is janitor-flagged Option (b) "PASS-with-follow-up; assign to PR-3 error-message update." Confirmed.

### Anomaly 2: `.know/` + README.md SERVICE_API_KEY doc drift
**Ruling**: PASS-WITH-FOLLOW-UP. Inherits PR-1 FU-2 pattern exactly. Files: `.know/architecture.md`, `.know/feat/token-manager.md`, `.know/feat/INDEX.md`, `.know/feat/http-client.md`, `README.md`. All are documentation drift pre-dating the initiative. Route to separate `/know --scope=feature` refresh session OR Boy-Scout absorbtion in future PR. Non-blocking.

### Anomaly 3: token_manager.py legacy-refs (lines 375, 378, 472)
**Ruling**: PASS-WITH-FOLLOW-UP (PR-3 scope). These references are now UNREACHABLE post-PR-2 (see Lens 11 Advisory #1) but remain in source. mypy strict mode would flag `attr-defined` errors on `self.config.service_key` since both autom8y_core.Config and autom8y_auth.ClientConfig lack `service_key` field post-PR-1+PR-2. mypy run on client_config.py alone passes (verified). Full mypy sweep deferred to PR-3 cleanup alongside auth-flow layer retirement via HANDOFF-REMEDIATE to rnd-Phase-A. This is janitor-flagged "PR-3 quarantine zone" — ruling confirmed.

### Anomaly 4: Collapsed commits 1+2 (planned 2 source-refactor commits merged into 1)
**Ruling**: LEGITIMATE (per `conventions` spirit). Both planned splits modified `client_config.py`. Splitting field-removal from canonical-alias addition would create an intermediate state where `from_env()` references a non-existent `service_key` field — a structurally-broken partial revert. Atomic-revert discipline REQUIRES that each commit leave the tree in a structurally-coherent state. Coalescing same-file-same-concern changes into one commit preserves this. Lens 2 ATOMIC-CLEAN ruling holds. Janitor deviation justified.

### Anomaly 5: CHANGELOG added as commit 3 (deviation from plan: optional → executed)
**Ruling**: LEGITIMATE. autom8y-auth has pre-existing CHANGELOG at `sdks/python/autom8y-auth/CHANGELOG.md` following Keep-a-Changelog + SemVer per header. Adding breaking-change entry to `[Unreleased]` is package-norm-compliant and documents the breaking change for downstream consumers. This commit being separate (vs. folded into commit 1) preserves atomic-revert: reverting 937a6bad alone leaves source+tests intact and drops only the documentation entry — cleanly revertible. Lens 2 ATOMIC-CLEAN ruling reinforced by this split.

## 4. T-2 Expansion Validation Analysis

The PR expanded HANDOFF §2 PR-2 literal scope (delete env-read + error msg + docstrings) to include field replacement + canonical-alias wiring + repr masking. Validation criteria from dispatch context:

| Criterion | Evidence | Verdict |
|-----------|----------|---------|
| Mirrors PR-1 canonical-alias pattern precisely (no novel design) | Side-by-side diff comparison: PR-1 commit a11b81f6 and PR-2 commit eaf918b1 share identical structure — `_resolve_secret` replaced with `os.environ.get` chain (because autom8y-auth has no Lambda Extension protocol, intentional architectural divergence); canonical-first `AUTOM8Y_DATA_SERVICE_*` → legacy `*` fallback identical; docstring language copied near-verbatim | PASS |
| Stays within client_config.py + its direct tests (no spread to ServiceAuthClient/token_manager/etc.) | `git diff --stat`: 5 files, all within autom8y-auth. Source: client_config.py only. Tests: test_client_config.py + tests/clients/test_base.py + tests/clients/test_auth_admin_client.py (all direct consumers of ClientConfig via construction). Docs: CHANGELOG only. ZERO touches to token_manager.py, service_client.py (N/A), client.py (N/A), test_sprint2_regressions.py, ServiceAuthClient refs | PASS |
| Canonical-first / legacy-fallback ordering consistent with ADR §2.3 | client_config.py:87-92 — `os.environ.get("AUTOM8Y_DATA_SERVICE_CLIENT_ID") or os.environ.get("CLIENT_ID", "")` matches PR-1 pattern and ADR-0001 §2.3 canonical-first semantics | PASS |
| `__repr__` masking boundary correct (client_id plaintext, client_secret masked) | client_config.py:117-129 — `f"client_id={self.client_id!r}"` (plaintext repr) + `secret_masked = "***"` | PASS |
| T-2 expansion does NOT violate operator Q4 "narrow retire" (SDK-cores only) | autom8y-auth ClientConfig IS an SDK-core dataclass (parallel to autom8y-core Config; both are client-side credential dataclasses). Q4 Narrow-retire interpretation: applies at SDK-core credential-config layer, NOT at auth-flow/admin-tooling/test layers. ClientConfig dataclass refactor is WITHIN Q4 scope; token_manager.py auth-flow refactor (PR-3) is adjacent and correctly deferred. No Q4 violation | PASS |

**T-2 expansion verdict: VALIDATED.**

Layer-depth discriminator holds: dataclass-refactor with rehearsed pattern is in-rite-scope; HTTP/auth-flow refactor requires cross-rite-handoff. This sets scar-tissue precedent per §9.

## 5. Behavior Preservation Checklist

| Category | Item | Status | Evidence |
|----------|------|--------|----------|
| MUST preserve (public API) | ClientConfig dataclass instantiation contract | BROKEN (documented) | `service_key` field REMOVED; BREAKING change per CHANGELOG §Breaking Changes; ADR-0001 §2.1 item 3 authorization + T-2 expansion ruling by hygiene-Potnia. Callers using `ClientConfig(service_key=...)` must migrate to `ClientConfig(client_id=..., client_secret=...)`. |
| MUST preserve (public API) | `ClientConfig.from_env()` factory contract | PRESERVED (additive) | from_env() now supports canonical-alias dual-lookup; legacy `CLIENT_ID`/`CLIENT_SECRET` env names still resolve. No caller-visible break. |
| MUST preserve (public API) | `__post_init__` validation contract (raises ValueError on missing credentials) | PRESERVED | Still raises ValueError; error message updated to reference `client_id`+`client_secret`. |
| MUST preserve (public API) | `__repr__` secret-masking invariant | PRESERVED | Secrets still masked (`client_secret` → `***`); client_id exposed plaintext (public OAuth identifier per RFC 6749 §2.3.1). |
| MAY change | Error message text | CHANGED (aligned) | "service_key is required. Set SERVICE_API_KEY environment variable" → "client_id and client_secret are required. Set CLIENT_ID+CLIENT_SECRET environment variables" |
| MAY change | Internal dataclass field names | CHANGED (intentional) | service_key → client_id + client_secret |
| MAY change | from_env() internal implementation | CHANGED (intentional) | service_key os.environ read → canonical-alias dual-lookup chain |
| REQUIRES approval | Canonical-alias dual-lookup wiring | APPROVED (ADR §2.3 + T-2 Option AA) | Additive; documented; tests cover both name pairs (4 new tests in TestClientConfigFromEnv assert AUTOM8Y_DATA_SERVICE_CLIENT_ID takes precedence over CLIENT_ID fallback) |
| REQUIRES approval | service_key field deletion | APPROVED (ADR §2.1 item 3 + T-2 ruling) | Operator Q1 RETIRE + Q4 narrow-retire (SDK-cores) rulings; hygiene-Potnia T-2 Option AA ruling 2026-04-21T~15:00Z |

**Behavior-preservation verdict**: all MUST-preserve changes have documented ADR + T-2 authorization; MAY changes within expected latitude; REQUIRES-approval changes have explicit operator + Potnia ratification chain.

## 6. Contract Verification (per HANDOFF-rnd-to-review §3 acceptance criteria)

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | SERVICE_API_KEY absent from autom8y-auth src | `rg SERVICE_API_KEY sdks/python/autom8y-auth/src/autom8y_auth/` — 1 hit: token_manager.py:472 error message (PR-3 quarantine; literal in error string, NOT an env-var read). Src-level env-read deletion at ClientConfig scope: COMPLETE. | PASS (per PR-2 scope; PR-3 defers remaining token_manager.py literal) |
| 2 | ClientConfig field surface updated | `client_id`, `client_secret` replace `service_key`; verified via Read | PASS |
| 3 | Canonical-alias dual-lookup implemented | from_env() at client_config.py:87-92 implements canonical-first semantics | PASS |
| 4 | Tests cover canonical-alias behavior | 4 tests in TestClientConfigFromEnv assert precedence ordering (per janitor report) | PASS |
| 5 | Quarantine zone untouched | `git diff --stat main...hygiene/retire-service-api-key-autom8y-auth`: 5 files, zero touches to service_client.py (N/A), client.py (N/A here), token_manager.py, test_sprint2_regressions.py, ServiceAuthClient refs | PASS |
| 6 | No --no-verify bypasses | Inferred from clean commit stream; verified mypy + ruff clean on client_config.py | PASS |
| 7 | Test suite green | PR-2 scope: 117/117 green; full suite baseline improved (+42 passing, -35 failures) | PASS |

## 7. Commit Quality Assessment

| Commit | Message | Atomic? | Revertible? | Maps to? |
|--------|---------|---------|-------------|----------|
| eaf918b1 | refactor(autom8y-auth): replace service_key field with client_id+client_secret in ClientConfig | YES (same-file-same-concern coalescing per Lens 2) | YES (reverting leaves tests failing but tree structurally coherent) | ADR §2.1 item 3 + §2.3 + T-2 Option AA |
| e107311f | test(autom8y-auth): migrate ClientConfig tests from service_key to OAuth client_credentials | YES | YES (reverting leaves stale tests against new source — revealing gap, not corruption) | ADR §2.1 item 5 (test cleanup) |
| 937a6bad | docs(autom8y-auth): CHANGELOG entry for ClientConfig SERVICE_API_KEY retirement | YES | YES (reverting drops only documentation) | ADR §2.1 item 3 documentation ripple |

Commit messages: all use conventional-commits prefix (refactor/test/docs); scope tag `autom8y-auth`; first-line summary <72 chars; multi-line body documents T-2 authorization + quarantine-respect + test count. Quality: high.

## 8. Improvement Assessment

- **Before** (main at 82ba4147): autom8y-auth ClientConfig references legacy `service_key` field; diverged from autom8y-core Config post-PR-1 (which had `service_key` removed); 35 tests in tests/clients/ failing because fixtures reference autom8y-core's removed `service_key` via `autom8y_core.Config as ClientConfig` import aliasing.
- **After** (PR-2 branch at 937a6bad): autom8y-auth ClientConfig aligns with autom8y-core Config field surface (both now use client_id + client_secret); 35 formerly-failing tests now pass; canonical-alias dual-lookup documented; CHANGELOG entry documents breaking change; doc-drift identified and scoped for follow-up.

Net maintainability delta: POSITIVE. The two SDK credential dataclasses are now structurally aligned, reducing developer cognitive load when switching between autom8y-core and autom8y-auth usage.

## 9. T-2 Expansion Precedent Statement (SCAR-TISSUE ESTABLISHED)

This verdict establishes the **layer-depth discriminator** as scar-tissue precedent for future F-2-class (scope-undercapture) findings during hygiene-rite execution of cross-rite HANDOFF artifacts.

**Precedent codified**:

> **Layer-depth discriminator**: When an inherited HANDOFF §N literal scope is insufficient to achieve structural coherence of the target artifact (F-2-class finding), hygiene-rite execution MAY expand in-session WITHOUT cross-rite-handoff IF the following three conditions hold:
>
> 1. **Pattern precedent exists**: a prior PR in the same initiative has already executed the pattern being replicated (provides rehearsed design authority; not novel design).
> 2. **Shallow-layer constraint**: the expansion stays within a single dataclass boundary + its direct tests. No spread to adjacent layers (HTTP/auth-flow, admin-tooling, protocol state machines).
> 3. **Quarantine-zone discipline**: explicit files listed in the HANDOFF as out-of-scope receive ZERO touches.
>
> When all three hold, in-session expansion is IN-RITE-SCOPE (hygiene has Exousia to execute).
>
> When any fail, F-2-class finding requires CROSS-RITE-HANDOFF via HANDOFF-REMEDIATE to the originating rite for formal scope amendment (precedent: PR-3 deferral to rnd-Phase-A via HANDOFF-REMEDIATE-hygiene-to-rnd-phase-a-pr3-scope-amendment-2026-04-21.md).

**Falsification conditions for this precedent** (future audits should re-evaluate if any fire):
- Future in-session expansion under layer-depth discriminator produces production incident
- Future expansion exceeds shallow-layer constraint without BLOCKING verdict (false-negative on the rubric)
- Operator/Pythia override ruling invalidates discriminator

**Symmetric alternative rejected by this verdict**: The symmetric routing rule ("all F-2 class findings route REMEDIATE; no discriminator") was the Option BB fallback if this audit had fired BLOCKING. Because BLOCKING did NOT fire, the asymmetric (discriminator-based) routing is validated as the operative precedent.

**Scope of precedent applicability**: hygiene-rite execution of cross-rite HANDOFF artifacts where the source rite is rnd-Phase-A or review-rite. NOT yet validated for hygiene-to-hygiene or hygiene-to-sre handoff flows (single-event demonstration; rubric §8 generalizability limitation applies).

## 10. Self-Ref-Disjointness Check

**Hygiene audit-lead is rite-disjoint from rnd-Phase-A ADR-authoring chain.** Per `self-ref-evidence-grade-rule`:
- ADR-0001 author: rnd-Phase-A (rnd rite)
- PR-2 janitor: hygiene-rite janitor
- PR-2 critic (this verdict): hygiene-rite audit-lead
- **Disjointness status**: audit-lead did not author ADR-0001; audit-lead did not execute PR-2 janitor work; audit-lead applied independent rubric (hygiene-11-check-rubric) to assess conformance.

No new disjointness concerns introduced by T-2 expansion — the layer-depth discriminator ruling came from hygiene-Potnia (also hygiene-rite), which preserves the hygiene→hygiene coordination pattern validated at PR-1. The rnd-rite ADR-authoring chain was NOT re-engaged for T-2; the discriminator operates at hygiene-Potnia's rite-authority scope.

**ADR-0001 grade-motion**: ADR-0001 already STRONG from PR-1 hygiene-rite audit (per verdict artifact pr1_precedent_verdict_ref). PR-2 is ratification-ripple (additional evidence of ADR applicability to autom8y-auth surface), NOT grade-motion event. Grade remains STRONG; `adr_grade_before == adr_grade_after`.

## 11. Follow-Up Items (Prioritized)

| Priority | Item | Scope | Route |
|----------|------|-------|-------|
| P1 | Complete PR-3: autom8y-auth token_manager.py auth-flow retirement (removes service_key references at lines 375/378/382/472 + `_build_exchange_kwargs` legacy branch) | rnd-Phase-A amendment (HANDOFF-REMEDIATE pending) | Cross-rite-handoff to rnd; blocks mypy-strict baseline cleanup |
| P2 | Refresh `.know/feat/token-manager.md` + `.know/feat/INDEX.md` + `.know/feat/http-client.md` + `.know/architecture.md` + `README.md` — remove SERVICE_API_KEY references | autom8y-auth repo doc refresh | `/know --scope=feature` refresh session OR Boy-Scout in PR-3 |
| P3 | Update `clients/_base.py:107` docstring `ClientConfig(service_key="my-key")` example (stale post-PR-2) | autom8y-auth code-comment cleanup | Boy-Scout in PR-3 or standalone doc-fix commit |
| P3 | Resolve `mergeStateStatus: UNSTABLE` on PR #125 (likely Semgrep Architecture Enforcement baseline from PR-1 Lens 11 advisory) | CI baseline hygiene | Standalone hygiene session (same class as PR-1 FU) |
| P4 | Consider renaming `InvalidServiceKeyError` → `InvalidCredentialError` (error class name is SERVICE_API_KEY-era artifact; OAuth flows raise same HTTP 401 semantic) | autom8y-auth API design | Future architect-enforcer sprint (out of retirement-initiative scope) |

## 12. Merge Authorization

**APPROVED — merge PR #125 to main.**

All acceptance criteria met. Behavior preservation verified against documented MUST/MAY/REQUIRES categories. Commit hygiene strong. Test suite strictly improves baseline. T-2 expansion VALIDATED as layer-depth-discriminator precedent.

Merge sequence:
1. Verify CI green on final push (address `mergeStateStatus: UNSTABLE` if Semgrep-baseline or other blocker; permissible to merge with pre-existing main-baseline CI noise per PR-1 precedent)
2. Merge to main via squash OR merge-commit (preserve 3-commit atomic history is PREFERRED; squash acceptable if PR template requires)
3. Update ADR-0001 ratification-ripple log with PR-2 merge SHA (no grade motion; ratification-ripple only)
4. Trigger P1 follow-up (rnd-Phase-A amendment for PR-3) per existing HANDOFF-REMEDIATE artifact

## 13. Provenance

| Field | Value |
|-------|-------|
| Audit executed at | 2026-04-21T~18:00Z |
| Audit duration | ~35 min (evidence gathering + worktree resolution + 11-lens sweep + verdict authoring) |
| Critic rite | hygiene |
| Critic agent | audit-lead |
| Rubric | hygiene-11-check-rubric (11 lenses; selection per §3 MODULE-migration profile) |
| Rite-disjointness | PASS (hygiene critiquing rnd-authored ADR + hygiene-janitor execution; hygiene-rite-internal discipline via Potnia+janitor+audit-lead triad preserved) |
| T-2 expansion precedent grade | STRONG-at-single-event (matches PR-1 precedent evidence ceiling; generalizability to hygiene-to-hygiene handoff flows unvalidated beyond this single-event demonstration) |
| Verdict | PASS-WITH-FOLLOW-UP |
| Merge authorization | YES |
| ADR grade motion | NONE (already STRONG; ratification-ripple only) |
