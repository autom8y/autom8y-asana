---
type: review
status: accepted
---

# SRE BUILD CRITIC VERDICT — IMPLEMENT half (N3 build + N4 verify)

**Critic:** rite-disjoint external (NOT sre). Default skeptical.
**Date:** 2026-06-24
**Target:** worktree `/tmp/wt-sre-obs`, branch `sre/obs-statuspush-skipped-alarms`, commit `615d477d`
**PR:** https://github.com/autom8y/autom8y-asana/pull/148 — OPEN, `mergedAt:null`
**Fork point:** `4f05876b` (merge-base with origin/main). origin/main has since advanced to `aecb2702` via one unrelated commit (#147 cache-warmer) that touches **none** of the 8 PR files — no conflict, no staleness defect.

## VERDICT: CONCUR-WITH-FLAGS

No G-HALT. No BLOCKING. The build matches its claims; every fixture is genuinely two-sided (independently re-proven via fresh defect-reinjection); no prod lever fired; the benign dirty tree was kept out of the PR. Flags are environmental tool-absence (terraform/ruff/mypy/xdist binaries not resolvable in this critic environment), surfaced honestly — NOT defects in the build.

## GREEN/RED matrix

| # | Check (from dispatch) | Result | Evidence |
|---|------------------------|--------|----------|
| 1 | PR OPEN, NOT merged; NO prod lever fired (alarm-arm / env / IaC deploy / schedule re-enable / cross-repo edit) | **GREEN** | `gh pr view 148` → `state:OPEN, mergedAt:null`; diff is +890/-0 across exactly 8 additive files; zero knossos-owned contamination in PR diff; worktree tree clean before AND after all probes; worktree remote bound to `autom8y-asana` only (no cross-repo edit possible) |
| 2 | Every fixture genuinely TWO-SIDED (RED on defect, GREEN on no-defect) — not green-only theater | **GREEN** | Re-read both fixtures; ran green baseline **11 passed**; **fresh defect-reinjection** (neuter `_emit_status_push_skipped` + orchestrator else-emit + stub `_legacy_query_410_armed`→False) → **6 failed / 5 passed**: all 4 StatusPushSkipped positives RED, canary armed-positive RED, canary gate-predicate test RED; ALL 5 no-defect negatives stayed GREEN. Reverted; **11 passed** again |
| 3 | Any rung rounded up (metric 'proven'/'alerting' when only 'emitting'/'authored'; retire claimed as past) | **GREEN (no inflation)** | Metrics are `emitting` in fixtures only — no Lambda deployed. Alarms `authored` (un-applied, un-armed). FORK-1 is a reversible env-flag canary; route STILL mounted at `main.py:470` (unmount SURFACED as separate step). AL-4 doc honestly states `{environment=production}` dim does NOT exist until AI-5 deploys → alarm sits INSUFFICIENT_DATA. SURFACED rung ledger labels all 5 levers PROD-MUTATING |
| 4 | Benign dirty tree kept unstaged; worktree off origin/main | **GREEN** | PR diff clean of `.claude/.gemini/.knossos/.know/.mcp.json/uv.lock`; worktree forked at `4f05876b` (was origin/main HEAD at build time); worktree `git status` empty throughout |
| 5 | Cross-repo data-side fix (AI-6) + insights (AI-2) SURFACED, not executed | **GREEN** | `observability_alarms.SURFACED.md` notes cross-repo apply pipeline + AI-6/AI-2 as out-of-scope/operator levers; worktree is single-repo so no foreign edit could occur |

## Independent two-sided RED proof (fresh construction, not inherited)

Defects re-injected into the working tree by THIS critic (distinct stubs from the builder's), then reverted via file restore — committed build never mutated:
- **StatusPushSkipped**: all 4 positive tests → RED with `AssertionError: expected exactly one StatusPushSkipped emit, got 0`; all 4 no-defect negatives GREEN. The counter genuinely distinguishes a misconfigured skip from a benign idle skip.
- **FORK-1 canary**: armed-path positive → RED (route fell through to its real handler, returned non-410); unit-level gate test `test_explicit_false_serves_and_logs_marker` → RED (predicate no longer returns True for "true"); OFF behavioral leg stayed GREEN.

This is a stronger RED set than the build report's 4-failed count (my predicate stub was broader than the builder's), confirming the teeth are not narrowly tuned to one injection.

## Source-diff verification (additive-only blast radius)

- `gid_push.py`: 3 emits each sit IMMEDIATELY before an UNCHANGED `return False` on the disabled/url-absent/invalid-key skip paths; new module-level `_emit_status_push_skipped` helper + `emit_metric` import. No return value altered.
- `push_orchestrator.py`: new `else` branch on the empty-`all_entries` path (previously metric-silent) emitting `three_way_denominator_null`. No existing branch touched.
- `query.py`: env-gated 410 short-circuit at top of `query_entities`; route stays mounted. `_legacy_query_410_armed()` reads `QUERY_LEGACY_410_GONE`.
- `emit_metric` (cloudwatch.py:79-85) BROAD-catches `Exception` and only logs → observability cannot fail the push seam. Blast radius is genuinely additive.

## IaC zero-arm verification (static — terraform binary absent here)

Default vars resolve all alarm actions to `[]`:
- `arm_paging=false`, `page_sns_topic_arn=""` → `local.page_action=[]`
- `ticket_sns_topic_arn=""` → `local.ticket_action=[]`
- `paging_armed_alarms=[]` → every `alX_actions` selects `local.ticket_action` = `[]`
- AL-2 has additional `recon_rule_enabled` gate (won't page on intended-off cron).
Result: **zero SNS actions wired on apply.** Nothing pages. `terraform validate` claimed GREEN by builder under tf 1.14.6 — NOT re-run here (binary unresolvable via mise).

## Regression

Touched-module suites (`push_orchestrator`, `gid_push`, `cloudwatch`, `routes_query` + 2 new): **105 passed, 0 failed.** No behavior change. (Build report cited 113; difference is suite enumeration scope — both all-green.)

## FLAGS (environmental, NOT defects — uncertified-by-critic, not RED)

1. **terraform validate**: NOT re-run — terraform binary unresolvable (mise shim unset). Zero-arm wiring verified statically instead. Builder's GREEN claim uncertified by me.
2. **ruff check / format**: NOT re-run — `ruff` absent from worktree `.venv`. Builder's clean claim uncertified by me.
3. **mypy --strict**: NOT re-run — `mypy` absent + `uv` re-resolve fails on CodeArtifact 401. Builder's clean claim uncertified by me.
4. **xdist `--dist=loadgroup`**: NOT exercised — `pytest-xdist` absent; ran single-process with `addopts=""`. The `xdist_group("query_routes")` marker IS present in the canary fixture (honors the async-teardown worker-crash scar) but its parallel behavior was not run here. Single-process all-green.

## Cleared to STRONG

- The StatusPushSkipped counter (4 skip_reason values) — emitting-rung, two-sided proven.
- The FORK-1 410-canary — reversible, route-mounted, two-sided proven.
- Blast radius is additive-only; PR is clean and OPEN; no prod mutation fired.

The alarm-suite teeth (AL-1..AL-4 actually firing in CloudWatch) and the terraform/ruff/mypy gates remain CONDITIONALLY cleared pending an environment with those binaries — surfaced, not green-washed.
