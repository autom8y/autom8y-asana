---
type: review
status: accepted
pr: 205
branch: feat/rep-template-v3-tenant-match
head: 3e81c4f0
date: 2026-07-07
mode: FULL
scan: SCAN-pr205-v3-template.md
assess: ASSESS-pr205-v3-template.md
verdict: MERGE-WITH-CONDITIONS (n=1 Path B) / NO-GO (BATCH)
---

# Code Review: PR #205 — v3 rep-template tenant-match (autom8y-asana)

## Executive Summary

PR #205 introduces the `post_template_comment` primitive — a tenant-matched rep-template comment poster — reviewed FULL mode with adversarial /qa execution. The verdict is **split**: the single-office n=1 path (Path B: resolve-from-task, no `--office-guid`) is **MERGE-WITH-CONDITIONS**; the batch use-case (8 ACTIVE offices, explicit `--office-guid` loop) is **NO-GO**. The crown finding (C-1) is a QA-executed receipt: `post_template_comment(task=<office-B PLAY>, office_guid=<office-A>)` → office-A's routing address posted onto office-B's PLAY task — cross-tenant contamination proven in execution. The load-bearing insight: the tenant-match guard (`assert_template_tenant_match`) validates `address⟷guid-arg`, NOT `task⟷office` — guard and preflight are orthogonal, non-substitutable invariants, and the dropped preflight is what exposed the batch to fleet-wide cross-tenant contamination. A fix is in flight that closes C-1 and M-2 before any batch loop is scheduled.

## Health Report Card

### Batch use-case (explicit `--office-guid`, 8 ACTIVE offices)

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Security | D | C-1: cross-tenant posting proven in QA execution (office-A address on office-B PLAY) |
| Structure | C | H-1: missing PLAY/ACTIVE-section preflight — structural parallel to `link_on_play._preflight` deliberately absent |
| Testing | B | M-1: `_business_gid_by_phone` returns-None branch untested; 2 Low |
| Hygiene | A | L-3: stray docs commit `e95a9de6` interleaved (unrelated telos/ledger files) |
| Complexity | A | 415 LOC, ~315 functional; below threshold |
| **Overall (BATCH)** | **C** | Security=D floor-drags overall; cannot exceed C |

### Single-office n=1 use-case (Path B: resolve-from-task)

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Security | C | H-1: no task identity gate; no proven cross-tenant contamination on Path B |
| Structure | C | H-1: same structural preflight gap; lower blast radius when guid is task-resolved |
| Testing | B | M-1: same missing branch test |
| Hygiene | A | L-3: same stray commit |
| Complexity | A | Same |
| **Overall (n=1)** | **B** | Median B; no D or F; 2 categories at C (below 3+ threshold) |

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| Files scanned | 9 changed (2 new source, 1 new test, 1 TDD spec, 1 v3 spec, 1 ADR, 3 minor updates) |
| Total findings | 8 (1 critical, 1 high, 2 medium, 4 low) |
| Test coverage signal | EXISTS — 403-line test file, 25 tests, ratio 0.97 |
| Review complexity | FULL (adversarial /qa executed) |
| QA execution receipt | C-1 proven live; M-2 AMBER; S4 AMBER; remaining GREEN |

## Findings by Priority

### Critical

#### C-1: Dropped PLAY/ACTIVE-section preflight enables cross-tenant posting (BATCH)

- **Location**: `template_comment.py:254-325` (`post_template_comment`); absence of any call matching `link_on_play.py:151-197` (`_preflight`) + `link_on_play.py:219`
- **Description**: `post_template_comment` accepts any arbitrary `--task-gid` with no positive-selection gate on task identity. `link_on_play.post_link_on_play` calls `_preflight` at step 2, asserting (a) task name matches `PLAY_NAME_RE` and (b) task is in `CALENDAR_INTEGRATIONS_PROJECT_GID` under a CANONICAL ACTIVE section. `post_template_comment` has no equivalent. When `--office-guid` is supplied directly (Path A / batch loop), step 2 (`if office_guid is None`) is skipped entirely.
- **QA executed receipt**: `post_template_comment(task_gid=<office-B PLAY>, office_guid=<office-A>, execute=True)` → `outcome=posted`. Office-A's routing address posted onto office-B's PLAY task. The tenant-match guard passed — it validates `address⟷guid-arg` only, NOT `task⟷office`. Guard and preflight are non-substitutable. The TDD (`TDD-rep-template-v3-tenant-match-2026-07-07.md:224-230`) justified the dropped preflight with "the tenant-match guard is where the value concentrates" — this premise was directly falsified by the QA execution.
- **Severity**: Critical for BATCH; High for n=1 Path A (single-office, same execution path); lower for n=1 Path B (resolve-from-task — guid locked to task's own phone bridge)
- **Recommendation**: Add `_play_preflight` to `post_template_comment` before both path branches — task name must match `PLAY_NAME_RE` AND task must be in `CALENDAR_INTEGRATIONS_PROJECT_GID` under a CANONICAL ACTIVE section. Reuse `resolve_section_gids` already imported by `link_on_play.py:179`. Add corresponding preflight-miss test.
- **Effort**: Moderate (reuse existing `_preflight` from `link_on_play.py:151-197`)
- **Status**: Fix in flight; pre-batch blocker

### High

#### H-1: No task identity gate on n=1 Path A (`--office-guid` supplied, single office)

- **Location**: `template_comment.py:275-277` (the `if office_guid is None` guard — Path A bypasses it entirely)
- **Description**: When `--office-guid` is supplied at the CLI (single-office manual invocation), the function posts to any `task_gid` without confirming it is a PLAY task in an ACTIVE section. Blast radius is a single wrong-task post rather than fleet-wide contamination, hence High (not Critical) at n=1 scope. Covered by the same C-1 fix — placing preflight before the guid resolution branch gates all callers.
- **Effort**: Covered by C-1 fix (no incremental cost)

### Medium / Low (summarized)

| ID | Severity | Finding | Recommendation | Status |
|----|----------|---------|----------------|--------|
| M-1 | Medium | `_business_gid_by_phone` returns-None branch untested (`template_comment.py:211-216`); other two refusal branches are covered | Add `test_no_business_for_phone`; patch returns `None`; assert `TemplateCommentRefused` raised | Pre-batch hardening |
| M-2 | Medium | `{clinic}` in `_BODY_TEMPLATE` Subject line (`template_comment.py:87`) has no newline strip; `\n` in clinic arg corrupts carrier email subject | Strip newlines from `clinic` before `.format()` in `compose_template_comment`; add test | Pre-batch blocker; fix in flight |
| L-1 | Low | Read-back (`_assert_marker_present`, `:230-251`) asserts marker but not routing-address persistence post-Asana write round-trip | Future hardening: add `own_address not in text → raise` alongside existing marker check | Fleet follow-up only |
| L-2 | Low | `main()` CLI entrypoint (87 LOC, `:328-415`) has no test; argument parsing / exit-code branches untested | Opportunistic argparse smoke tests | No urgency |
| L-3 | Low | Stray docs commit `e95a9de6` interleaved in feature PR (GitHub web identity, touches `.know/telos/` and `.ledge/reviews/` only) | Extract to separate docs PR before next batch execution | Hygiene |
| L-4 | Low | Guard regex (`tenant_binding.py:68-70`) does not match embedded whitespace/Unicode/URL-encoded `%40` | No action — system-composed surface, existing fleet standard; near-zero attack surface | None |

**S4 marker substring (fleet follow-up)**: All three PLAY-comment posters use `if marker in (s.text or "")` for idempotency. Substring-scan is accepted fleet-debt shared with `link_on_play`, not a new regression. No rite dispatch now; AMBER QA verdict on this pattern.

## Load-Bearing Insight

> **Guard ⟂ Preflight — non-substitutable invariants.**
>
> `assert_template_tenant_match` checks: does this composed text contain the routing address belonging to `office_guid`? It answers the address-authenticity question.
>
> `_preflight` (missing from this PR) checks: is `task_gid` actually a PLAY task for this office in a CANONICAL ACTIVE section? It answers the task-identity question.
>
> Passing the guard with a mismatched task proves the guard is silent on task identity. The TDD's premise that "the guard is where the value concentrates" was not wrong about what the guard does — it was wrong about what the guard prevents. A batch caller holding valid `office_guid` values for all 8 offices and a scrambled `task_gid` list would post every routing address to the wrong task while every guard call returned PASS.

## Cross-Rite Recommendations

| Concern | Recommended Rite | Action | Priority |
|---------|-----------------|--------|----------|
| C-1 / H-1: preflight gap (cross-tenant post QA-proven) | **10x-dev** | Implement `_play_preflight` in `post_template_comment`; add preflight-miss test; closes batch blocker | PRE-BATCH BLOCKER |
| M-2: `clinic` newline sanitization (email subject corruption) | **10x-dev** | Strip `\n` from `clinic` in `compose_template_comment`; add test | PRE-BATCH BLOCKER |
| M-1: missing `_business_gid_by_phone` returns-None test | **10x-dev** | Add `test_no_business_for_phone` (5-line test, mirrors existing refusal-path tests) | Pre-batch hardening |
| L-3: stray docs commit `e95a9de6` | **hygiene** | Extract to docs PR; or accept with merge acknowledgment | Low urgency |
| S4 marker substring idempotency (shared fleet pattern) | **10x-dev** (fleet follow-up) | Harden idempotency across poster family when fleet seam allows | Opportunistic |
| Hosting seam (7/8 offices unhosted; no batch runner exists) | **10x-dev** (floodgates build) | Build hosting seam + batch runner separately; this PR gates on that work, not the reverse | Separate initiative |

## Merge Recommendation

**MERGE-WITH-CONDITIONS for n=1 Path B (resolve-from-task, no `--office-guid`).**

Path B is tenant-safe in isolation: guid is resolved from the task's own Business phone bridge; routing address is always this task's own. The tenant-match guard confirms no foreign address in the composed text. The dry-run backstop provides operator visibility before mutation. The 25-test matrix validates happy-path, refusal-path, and guard behaviors. The single-office n=1 primitive may be merged and operated manually (Nova/Intercom send flow, one office at a time) while the pre-batch blockers are closed.

**Batch is NO-GO until all pre-batch conditions are resolved:**

1. **BLOCKING — C-1/H-1**: Implement `_play_preflight` in `post_template_comment` (preflight before both Path A and Path B branches). Add preflight-miss test.
2. **BLOCKING — M-2**: Strip `\n` from `clinic` in `compose_template_comment`. Add test.
3. **RECOMMENDED — M-1**: Add `test_no_business_for_phone`.
4. **HYGIENE — L-3**: Extract stray commit `e95a9de6` to a docs PR.

Note: a fix closing conditions 1 and 2 is already in flight per operator context.

## Recommended Next Steps

1. **[Highest impact / lowest effort]** Land the in-flight fix for C-1 (preflight) + M-2 (clinic newline) — two blockers closed in one targeted PR; unblocks the batch primitive.
2. **[Medium impact / quick]** Add `test_no_business_for_phone` in `test_template_comment.py` — 5-line test; closes M-1 and completes the `_resolve_office_guid` branch coverage trifecta.
3. **[Low impact / hygiene]** Extract commit `e95a9de6` to a standalone docs PR — keeps the feature branch history clean before any batch scheduling.
4. **[Separate initiative]** Build the hosting seam (deck provision for 7/8 unhosted offices) + batch runner — the floodgates batch is gated on this work independently of the pre-batch code fixes above.

---
*Review mode: FULL | Generated by review rite | 2026-07-07*
