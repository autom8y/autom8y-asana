---
type: spec
status: draft
name: PLAN-eunomia-stub-theater-remediation
slug: stub-theater-remediation
authored: "2026-06-10"
author: "eunomia consolidation-planner (station E5)"
mode: PLAN-ONLY
throughline: integration-boundary-fidelity
companion_spec: THROUGHLINE-integration-boundary-fidelity-2026-06-10.md
---

# PLAN — eunomia stub-theater remediation (2026-06-10)

> **PLAN-ONLY.** No tests/src touched, no commits, no staging. This document
> specifies five atomic, independently `git revert`-safe CHANGE-NNN units for
> the rationalization-executor. The benign dirty tree is NOT staged. Every
> change preserves or increases test-function count (GUARD).

## Target State

Post-remediation, the repo's DataFrame hot-store / cache boundary is guarded by
the four-layer **integration-boundary-fidelity** discipline with no
permanently-skippable Layer-4 hole:

1. The live read-only smoke (Layer-4) carries a **forcing function** — it cannot
   silently skip forever (CHANGE-001).
2. The two HIGH lurking stub-theater instances are hardened to route through
   real boundary objects instead of above-boundary stand-ins (CHANGE-002,
   CHANGE-003).
3. The null_number_recovery hot-path test is consolidated (§1+§2 merged,
   parameterized) with ZERO loss of assertions or coverage (CHANGE-004).
4. The dev-setup docs make the pre-commit + justfile lint→fmt forcing path
   discoverable (CHANGE-005, E4 FINDING-1).

## Baseline test-function counts (GUARD — count before/after, assert >=)

- `tests/unit/services/test_universal_strategy.py`: count via
  `grep -cE 'def test_|async def test_'` at execution time (CHANGE-002 target).
- `tests/unit/api/routes/test_matching.py`: count via same (CHANGE-003 target).
- `tests/unit/dataframes/builders/test_null_number_recovery.py`: **7** test
  functions at plan-time (`test_single_batch_read_never_n_plus_1`,
  `test_heal_proof_specific_values_from_cache`,
  `test_never_fabricate_null_cache_and_cache_miss_stay_null`,
  `test_never_overwrite_already_populated_cell`,
  `test_g_propagate_one_loop_excludes_cascade_and_nonnumeric`,
  `test_additive_never_raises_on_store_error`,
  `test_noop_guards_make_no_store_call`). CHANGE-004 merges §1+§2 into ONE
  parameterized test = **6 functions, 2 param cases** → distinct assertion
  count PRESERVED (see CHANGE-004 GUARD). [SVR file-read: structure outlined at
  `.worktrees/fpc-phase2/tests/unit/dataframes/builders/test_null_number_recovery.py:75-135`]

> NOTE: the null_number_recovery + live-smoke files live in the `fpc-phase2`
> worktree, not the main tree, at plan-time. The executor MUST confirm the
> active branch/worktree before editing (CHANGE-001 step 0 + CHANGE-004 step 0).

---

## CHANGE-001 — live-smoke forcing function (Layer-4 PERMANENT-SKIP-RISK closure)

- **Type**: `enforce-coverage` (forcing-function for an existing skip-gated test)
- **Rationale**: The E3a census records the live read-only smoke as correctly
  skip-gated in CI but with NO forcing function: zero references outside the
  file, a hardcoded gid (1207519540893045) + MRR (1500) whose staleness it
  cannot self-verify, and no scheduled run / deploy-gate / pre-land hook. It can
  silently skip forever — Layer-4 of integration-boundary-fidelity is UNGUARDED
  on its own mint instance. This is the FIRST remediation named by the
  throughline §6.
- **Step 0 (REQUIRED pre-flight, SVR bash-probe)**: re-pin the exact live-smoke
  path before any edit:
  `grep -rln '1207519540893045' . --include='*.py'`. Confirm the file, its
  current skip-gate expression, and that it calls the unit's REAL read function
  (not a re-implementation). If the gid is absent from the active worktree, HALT
  and reconcile worktree/branch (the file is in `fpc-phase2` at plan-time).
- **Files affected**:
  - NEW: `.github/workflows/live-smoke-nightly.yml` (recommended option — see
    below).
  - The live-smoke test file: a non-functional touch ONLY if the skip-gate
    needs a named env trigger (`RUN_LIVE_SMOKE`) so the nightly job can force
    execution. No assertion changes.
- **Options + tradeoffs**:
  - **(A) RECOMMENDED — scheduled nightly CI job with AWS OIDC running ONLY the
    live-smoke file.** A new `live-smoke-nightly.yml` on a `schedule:` cron, with
    `permissions: id-token: write` assuming the runtime-equivalent IAM role via
    OIDC (NOT dev creds — Layer-4 fidelity), running `pytest -m live_smoke` or the
    single file. **Pro**: forces execution daily; uses the runtime principal so
    Layer-4 is genuinely exercised; failure surfaces in the Actions tab without
    blocking PR latency. **Con**: nightly lag (up to ~24h staleness detection);
    requires an OIDC role with read-only grant provisioned (coordinate with
    autom8y#481 IAM substrate).
  - **(B) Pre-deploy gate step.** Add the live-smoke to the deploy workflow as a
    gate before the receiver/Lambda deploy. **Pro**: blocks an inert cure from
    deploying — the strongest forcing function (matches the throughline STRONG
    bar: prevent, not detect). **Con**: couples deploy latency to a live external
    call (Asana/S3 flakiness blocks deploys); the deploy gate already gates on
    the whole Test conclusion (per memory: satellite deploy-gate sensitivity) —
    adding a live external dependency risks deploy-blocking flakes.
  - **(C) Pre-land checklist hook.** A `pre-commit`/PR-template checklist item.
    **Pro**: zero CI cost. **Con**: human forcing function = weakest; relies on
    discipline, which is exactly the failure mode (no structural compulsion).
- **Recommendation**: **(A)** as the primary forcing function NOW; evaluate **(B)**
  as a follow-on once the OIDC read-only role is stable (B is the STRONG-bar
  endgame but carries deploy-flake risk that must be de-risked first). (C) is
  insufficient alone.
- **Risk**: `needs-human-review` — touches live CI pipeline behavior + requires
  an AWS OIDC role with a real (read-only) grant. Per Exousia, CI-pipeline +
  IAM-adjacent changes ESCALATE to user with risk disclosure before execution.
- **Verification**: (a) `actionlint .github/workflows/live-smoke-nightly.yml`
  exit 0; (b) a `workflow_dispatch` manual trigger of the new workflow runs the
  live-smoke and exits 0 against the read-only role (NOT dev creds); (c) confirm
  the smoke is NO LONGER reference-orphaned: `grep -rl '{live-smoke-file}'
  .github/` returns the new workflow.
- **Revert-safety**: deleting `live-smoke-nightly.yml` + reverting the optional
  one-line env-gate touch fully restores prior state. The smoke test itself is
  unchanged in assertion content; revert removes only the forcing function.
- **Depends-on**: none (front-loaded; introduces no shared infra other code
  imports). Independent of CHANGE-002..005.
- **Est size**: 1 new workflow file (~40 lines) + at most 1 one-line test
  env-gate touch. 1 commit.

---

## CHANGE-002 — harden test_universal_strategy.py Rank-1 (boundary-level cache stub)

- **Type**: `consolidate-mocks` (replace above-boundary injection with real
  object + boundary stub)
- **Rationale**: E3a Top-2 HIGH #1.
  `tests/unit/services/test_universal_strategy.py:122` (and the parallel
  injection in the sibling `test_resolve_multiple_criteria` immediately below)
  sets `strategy._cached_dataframe = unit_dataframe` directly — this assigns the
  resolved DataFrame onto a private attribute, SKIPPING the entire cache-read
  path (`get_dataframe_cache_provider()` → `DataFrameCache.get_async` → entry
  unwrap). It is Layer-1 + Layer-3 stub-theater: the resolution logic is tested,
  but the boundary the strategy depends on in production is never exercised.
  [SVR file-read: `tests/unit/services/test_universal_strategy.py:122-136`
  shows `strategy._cached_dataframe = unit_dataframe`.]
- **Files affected**: `tests/unit/services/test_universal_strategy.py` ONLY.
- **Scope**: replace the `_cached_dataframe` private-attr injection with routing
  through a real `DataFrameCache` (or the production provider seam
  `get_dataframe_cache_provider`, `src/autom8_asana/cache/dataframe/factory.py:261`)
  whose lowest boundary (the backend / boto3 client) is stubbed to return a real
  `DataFrameCacheEntry` (`src/autom8_asana/cache/integration/dataframe_cache.py:68`)
  wrapping `unit_dataframe` with real freshness fields. Each affected test method
  gets the same boundary-level setup (candidate for a shared fixture in the
  module's conftest if the construction is identical across both methods —
  classify per Fixture Consolidation Template before extracting; a `def` inside
  the test class is a method not a fixture).
- **Risk**: `moderate` — test-only; no src change. Risk is that the strategy may
  not currently CALL the cache-read path at all (it may accept an injected frame
  by design); if so, this CHANGE surfaces a genuine production-path gap that
  ESCALATES (would require a src change to wire the read path — out of scope for
  a test-only plan). Executor MUST verify the strategy's real read path exists
  before rewriting; if the only entry is `_cached_dataframe`, FLAG to user
  rather than fabricate a path.
- **Verification**: `pytest tests/unit/services/test_universal_strategy.py -x`
  exit 0; test-function count >= baseline (GUARD); grep confirms ZERO remaining
  `_cached_dataframe =` direct assignments in the file.
- **Revert-safety**: single-file diff; `git revert` restores the injection.
  No shared infra introduced (unless a conftest fixture is added — if so, that
  fixture lives in CHANGE-002's commit and nothing else depends on it).
- **Depends-on**: none structurally. Independent of CHANGE-001/003/004/005.
- **Est size**: 1 file, ~2 test methods rewired (+ optional 1 fixture). 1 commit.

---

## CHANGE-003 — harden test_matching.py Rank-2 (_FakeEntry → real DataFrameCacheEntry)

- **Type**: `consolidate-mocks` (replace stand-in entry with real boundary object)
- **Rationale**: E3a Top-2 HIGH #2.
  `tests/unit/api/routes/test_matching.py:65` defines
  `@dataclass class _FakeEntry: dataframe: object` — a minimal stand-in for
  `DataFrameCacheEntry` carrying ONLY a `dataframe` attr. The success-path tests
  (`test_matching.py:334-358`, `_patch_auth_and_cache`) wrap it in a `MagicMock`
  cache whose `get_async` returns `_FakeEntry`. This SKIPS freshness
  (`watermark`, `created_at`, `is_stale`, `is_fresh_by_watermark`) and
  schema-version validation — Layer-3 stub-theater: the route's entry-unwrap +
  freshness checks are never exercised against the real shape.
  [SVR file-read: `tests/unit/api/routes/test_matching.py:64-70` defines
  `class _FakeEntry` with only `dataframe: object`; the real shape at
  `src/autom8_asana/cache/integration/dataframe_cache.py:68` carries
  project_gid/entity_type/watermark/created_at/schema_version/row_count.]
- **Files affected**: `tests/unit/api/routes/test_matching.py` ONLY.
- **Scope**: replace `_FakeEntry(dataframe=fake_df)` with a real
  `DataFrameCacheEntry(project_gid=..., entity_type=..., dataframe=fake_df,
  watermark=<recent>, created_at=<recent>, schema_version=<current>)` so the
  route exercises the real freshness/schema-version path. Keep the boundary stub
  at `get_dataframe_cache_provider` (the route's real seam,
  `src/autom8_asana/api/routes/matching.py` per the existing
  `patch("autom8_asana.api.routes.matching.get_dataframe_cache_provider", ...)`).
  Delete the now-dead `_FakeEntry` dataclass once no references remain.
- **Risk**: `moderate` — test-only. Risk: constructing a real
  `DataFrameCacheEntry` requires valid freshness values; if the route applies
  staleness logic the fake bypassed, tests may now (correctly) require fresh
  watermarks — that is the POINT (it un-hides Layer-3). Executor verifies the
  route's freshness expectation and supplies fresh values; if a test was
  passing ONLY because `_FakeEntry` bypassed a real staleness check, the
  corrected test is the cure, not a regression.
- **Verification**: `pytest tests/unit/api/routes/test_matching.py -x` exit 0;
  test-function count >= baseline (GUARD); grep confirms ZERO remaining
  `_FakeEntry` references in the file (definition + usages all replaced).
- **Revert-safety**: single-file diff; `git revert` restores `_FakeEntry`.
- **Depends-on**: none structurally. Shares the real `DataFrameCacheEntry` shape
  with CHANGE-002 but introduces no shared TEST infra — each change references
  the production class directly, so neither commit depends on the other
  (LSC-safe per SCAR-CP-005).
- **Est size**: 1 file, `_FakeEntry` def removed + ~1 construction site +
  helper updated. 1 commit.

---

## CHANGE-004 — merge test_null_number_recovery.py §1+§2 (parameterized hot-path test)

- **Type**: `merge-adversarial-tests` (consolidate two overlapping hot-path tests)
- **Rationale**: E3a consolidation candidate. §1
  `test_single_batch_read_never_n_plus_1` (line 99) and §2
  `test_heal_proof_specific_values_from_cache` (line 123) both use the same
  `_CountingStore` infra (line 75) and assert overlapping hot-path heal
  behavior (both: heal from cache, both assert `receipt.healed_cells`). They are
  mergeable into ONE parameterized test without losing any assertion.
  [SVR file-read: both tests outlined at
  `.worktrees/fpc-phase2/tests/unit/dataframes/builders/test_null_number_recovery.py:99-135`,
  both constructing `_CountingStore(...)`.]
- **Step 0 (REQUIRED pre-flight)**: confirm active worktree contains the file
  (`fpc-phase2` at plan-time). `git ls-files | grep test_null_number_recovery`
  or operate within the worktree.
- **Files affected**:
  `tests/unit/dataframes/builders/test_null_number_recovery.py` ONLY (path
  relative to the active worktree).
- **Scope**: merge §1 and §2 into a single
  `@pytest.mark.parametrize`d async test with TWO cases — one preserving §1's
  not-N+1 + batch-bound assertions (4-row frame, `batch_calls == 1`,
  `total_gids_requested == 4`, `healed_cells == 8`, both null_count == 0), one
  preserving §2's exact-value heal-proof assertions (1-row frame,
  `mrr == [1800.0]`, `weekly_ad_spend == [300.0]`, `attempted is True`,
  `healed_cells == 2`, `healed_by_column == {"mrr": 1, "weekly_ad_spend": 1}`).
  Distinct frame + distinct cache dict per param case; assertions guarded per
  case (param-conditional or per-case assert blocks). §3-§7 (lines 138-195)
  are LEFT UNTOUCHED — load-bearing, no deletion.
- **GUARD [GUARD-CP-001]**: test-FUNCTION count goes 7 → 6, but the merge is a
  parameterization (2 cases) not a deletion — EVERY assertion from both §1 and
  §2 is preserved in the param cases. The executor MUST enumerate the assertion
  set before/after and assert the union is preserved (the not-N+1 batch-bound
  assertions AND the exact-value heal-proof assertions both survive). This is
  consolidation, not coverage reduction (SCAR-CP-001).
- **Risk**: `safe` — pure test refactor; same infra, same assertions, fewer
  function headers. Lowest-risk change in the plan.
- **Verification**:
  `pytest tests/unit/dataframes/builders/test_null_number_recovery.py -x` exit 0;
  collected-test count = previous-collected-count (7 functions → 6 functions +
  2 params on the merged one = same number of test CASES collected); assertion
  union preserved (manual diff of asserts).
- **Revert-safety**: single-file diff; `git revert` restores §1 and §2 as
  separate functions.
- **Depends-on**: none. Independent of all other changes.
- **Est size**: 1 file, 2 functions → 1 parameterized function. 1 commit.

---

## CHANGE-005 — docs: dev-setup pre-commit install + justfile lint→fmt note (E4 FINDING-1)

- **Type**: `enforce-coverage` (documentation forcing-path for the local lint gate)
- **Rationale**: E4 FINDING-1. The README dev-setup omits `pre-commit install`,
  so the local pre-commit forcing function (the structural compulsion that would
  catch lint/format drift before push) is not installed by default — a
  discoverability gap that lets the local quality gate silently no-op. The
  justfile `lint`→`fmt` ordering note documents the canonical local sequence.
- **Files affected**: `README.md` (dev-setup section) ONLY. Possibly a one-line
  cross-reference in the justfile header comment (no recipe behavior change).
- **Scope**: add a dev-setup step `pre-commit install` after dependency install;
  add a short note that `just lint` then `just fmt` is the canonical local
  pre-push sequence. Documentation only — NO recipe / hook behavior change.
- **Risk**: `safe` — docs-only; no code, no CI, no test behavior.
- **Verification**: `grep -n 'pre-commit install' README.md` returns the new
  line; markdown renders (no broken fences); `just --list` still parses if the
  justfile header was touched.
- **Revert-safety**: single-file doc diff; `git revert` restores prior README.
- **Depends-on**: none.
- **Est size**: 1 file, ~3 lines. 1 commit.

---

## Dependency Graph (acyclic)

```
CHANGE-001 (live-smoke forcing fn) ── independent
CHANGE-002 (universal_strategy)    ── independent
CHANGE-003 (matching _FakeEntry)   ── independent
CHANGE-004 (null_number §1+§2)     ── independent
CHANGE-005 (docs)                  ── independent
```

All five are mutually independent — each is a single-file (or single-new-file)
diff touching disjoint paths, introducing no shared test infra that another
change imports. No commit depends on a prior commit (SCAR-CP-005 / Google LSC
clean). Recommended landing order is by ascending risk for review ergonomics
(004 safe → 005 safe → 003 moderate → 002 moderate → 001 needs-human-review),
but ordering is NOT load-bearing since the graph has zero edges.

## Risk Summary

| Change | Type | Risk | Files |
|--------|------|------|-------|
| CHANGE-001 | enforce-coverage | **needs-human-review** (CI + IAM/OIDC) | +1 workflow, ~1 test env-gate |
| CHANGE-002 | consolidate-mocks | moderate | 1 test file |
| CHANGE-003 | consolidate-mocks | moderate | 1 test file |
| CHANGE-004 | merge-adversarial-tests | safe | 1 test file |
| CHANGE-005 | enforce-coverage | safe | README (+ justfile comment) |

## Escalations (per Exousia — acknowledge before execution)

- **CHANGE-001** modifies live CI pipeline behavior AND requires an AWS OIDC
  role with a real read-only IAM grant → ESCALATE to user with risk disclosure
  before the executor runs it. Recommend landing CHANGE-002..005 first
  (test/docs only, no escalation) and gating CHANGE-001 on user ack.
- **CHANGE-002** carries a conditional escalation: if the strategy's ONLY
  data-entry seam is `_cached_dataframe` (i.e. there is no production cache-read
  path to route through), hardening the test would require a SRC change to wire
  the read path — that exceeds a test-only plan and ESCALATES to user / re-routes
  to assessment (potnia) rather than being fabricated by the executor.

## Deferred Items (assessment findings NOT addressed, with rationale)

- **Live-smoke staleness self-verification** (hardcoded gid 1207519540893045 /
  MRR 1500 cannot self-verify): DEFERRED. CHANGE-001 closes the SKIP risk (forces
  execution); making the smoke self-verify its expected value dynamically
  (query-against-source rather than hardcoded) is a separate hardening that
  requires a source-of-truth read and risks coupling the smoke to live data
  mutation. Defer to a follow-on once CHANGE-001's forcing function is stable.
- **CHANGE-001 Option (B) pre-deploy gate** (the STRONG-bar endgame): DEFERRED to
  follow-on. Adding a live external call to the deploy gate risks deploy-blocking
  flakes against the existing whole-Test-conclusion deploy gate; de-risk the OIDC
  read-only role + nightly stability (Option A) first.
- **Broader stub-theater census beyond Top-2 HIGH**: DEFERRED. E3a ranked only
  the Top-2 HIGH lurking instances; a full census sweep across the suite is
  out of this plan's scope (grounded only in the assessment's named findings —
  no scope creep per planning principles).

## Estimated Scope

- **Files touched**: 5 distinct paths (1 new workflow, 3 test files, 1 README;
  + optional 1-line touches to a test env-gate and justfile comment).
- **Commits**: 5 (one per CHANGE, atomic + independently revertible).
- **Test-function delta**: null_number_recovery 7→6 (parameterized, assertions
  preserved); universal_strategy + matching counts PRESERVED (mock hardening,
  no function removal); net coverage preserved-or-increased per SCAR-CP-001 /
  GUARD-CP-001.

---

## Handoff Criteria checklist

- [x] PLAN written to the ledge (`.ledge/specs/`). NOTE: brief named
      `.ledge/specs/`; the `.sos/wip/eunomia/` convention from the base agent
      spec is superseded by this dispatch's explicit deliverable path.
- [x] Every change has ID, type, files, risk, verification, rollback.
- [x] Dependency graph is acyclic (zero edges).
- [ ] `needs-human-review` change (CHANGE-001) acknowledged by user — PENDING
      user ack before executor runs it.
- [x] Deferred items documented with rationale.
- [x] Estimated scope documented.
- [x] Test-function counts documented for consolidation changes (GUARD-CP-001).

*PLAN-ONLY. Executor receives this for atomic-commit execution; verification-
auditor validates against this plan + baseline. No execution performed here.*
