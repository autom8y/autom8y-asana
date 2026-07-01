---
type: review
status: accepted
---

# Asana Closing — Rite-Disjoint External Critic Verdict

- **Date:** 2026-06-24
- **Critic stance:** Rite-disjoint, independent re-derivation (NOT inherited from scan/case-file). Default skeptical.
- **Subject:** `asana-closing-case-file-2026-06-24.md` (overall grade C; SCAR-REG-001 framed as the one action that ends the live BI incident)
- **Refs:** working HEAD = `f4f924d2` (branch `chore/bump-core-4.6.0`); `origin/main` = `8bc31a6a`; merge-base = `723dbb11`

## VERDICT: CONCUR-WITH-FLAGS

The mechanical spine of the case file holds: the three landed-holds (#149/#135/#148) are genuinely MERGED on origin/main and genuinely ABSENT from the working branch; SCAR-REG-001's 19 placeholder GIDs are real; the bare-`DataServiceClient()` roster of exactly 2 is complete; PR #151 is genuinely OPEN; the BI incident is genuinely LIVE. I CONCUR that the cutover is not clear-to-ship.

I FLAG one structural mis-attribution that the case file's headline gets wrong, and three rung/severity inaccuracies. None reverse the "not-clear-to-ship" conclusion; together they re-point the single most important action.

---

## GREEN/RED Matrix (with self-run receipts)

### GREEN — confirmed by independent receipt

| # | Claim | Receipt |
|---|-------|---------|
| G1 | #149 (finalize propagation + claims discriminator) MERGED on main, ABSENT at working HEAD | `gh pr view 149` → `state:MERGED, mergeCommit f795d7dc`. `git merge-base --is-ancestor f795d7dc HEAD` → **149-NOT-IN-HEAD**. origin/main idempotency.py emits `IdempotencyFinalizeFailure`, re-sources `request.state.claims`, checks `finalize()` bool (lines ~752-806). Working HEAD line 719 still shows the OLD bare `except Exception` "VERIFY-BEFORE-PROD double-execution risk" with the bool DISCARDED. |
| G2 | #135 (deprecated POST /{entity_type} retired) MERGED on main, ABSENT at HEAD | `gh pr view 135` → `MERGED, 5e31bb48`. `git show origin/main:.../query.py \| grep -c deprecated\|sunset\|410` → **0**. Working HEAD → **9**. NOT-IN-HEAD confirmed. |
| G3 | #148 (StatusPushSkipped counter) MERGED on main, ABSENT at HEAD | `gh pr view 148` → `MERGED, 9b698280`. origin/main gid_push.py emits `StatusPushSkipped` (lines 31-53). Working HEAD → **empty (absent)**. NOT-IN-HEAD confirmed. |
| G4 | SCAR-REG-001: exactly 19 sequential placeholder GIDs | `grep -oE '120108107373(15\|16)[0-9]{2}' \| sort -u \| grep -v ...555` → **19** (4 excluded `...600-603` + 15 unit `...610-624`). The 20th grep match is the project GID `...555` in comments. Count is HONEST. All flagged VERIFY-BEFORE-PROD; `_validate_gid_set` WARNING heuristic present (line 52-83). |
| G5 | Bare `DataServiceClient()` roster = exactly 2 real sites | `git grep 'DataServiceClient()'` on origin/main: only `workflows.py:361` and `workflow_handler.py:158` are real code. All `client.py`/`business.py` hits are `>>>` docstrings; `dependencies.py:505` and `query/__main__.py:501` pass `auth_provider=`. Roster COMPLETE — no third site. |
| G6 | D-2: workflows.py:355-365 data-client branch has zero unit coverage | `grep 'requires_data_client=True'` in test_workflows.py → **no match (exit 1)**; no `patch(...DataServiceClient)` anywhere. The `async with DataServiceClient()` branch is never exercised. PROVEN. |
| G7 | #151 genuinely OPEN | `gh pr view 151` → `state:OPEN, mergedAt:null, mergeCommit:null`. |
| G8 | **Insights BI incident genuinely LIVE** | Logs Insights `/aws/lambda/autom8-asana-insights-export`, last 24h, recordsScanned=**1177** (>0). Latest run 2026-06-24T11:01:10Z: `insights_export_completed {"succeeded":0,"failed":60,"skipped":1,"total_tables_failed":720}`. Cause in logs: `AUTH-TEB-001: No authorization token provided` per-table. CONFIRMED LIVE. |

### RED — flags against the case file

| # | Flag | Severity | Receipt |
|---|------|----------|---------|
| **R1** | **Headline mis-attribution: SCAR-REG-001 is NOT the cause of the live BI incident.** The case file's "One Action That Ends the Live BI Incident" = fix the section-registry placeholder GIDs. But the live `succeeded:0` incident is caused by **AUTH-TEB-001 (no auth token)** in insights-export — i.e. the bare `DataServiceClient()` at `workflow_handler.py:158`, fixed by the OPEN **#151**, NOT by section_registry (a different Lambda, `unit-reconciliation`). The single highest-value action to end the live BI incident is **merge #151**, not the W-IRIS section-GID fetch. | HIGH (re-points the headline) | Logs: `error_message:{'code':'AUTH-TEB-001'...}` + `total_tables_failed:720`; PR #151 body root-cause = "workflow_handler built DataServiceClient() with no auth_provider → AUTH-TEB-001". section_registry feeds `reconciliation/processor.py`, a separate Lambda. |
| **R2** | **SCAR-REG-001 rung is UNDER-graded on liveness.** Case file (quoting #149) says GIDs are "wired NOWHERE live; zero live GIDs" → `proven-in-code-only`. FALSE for the frozensets themselves: `EXCLUDED_SECTION_GIDS`/`UNIT_SECTION_GIDS` are imported by `reconciliation/processor.py:34-35` and `EXCLUDED_SECTION_GIDS` is the **live default** for `self._excluded_section_gids` (processor.py:164-165). Only the `join_section_registry` *scaffold function* is wired nowhere. The placeholder GIDs flow into live reconciliation exclusion logic → arguably past `proven-in-code-only`. | MEDIUM | `git grep` shows processor.py:165 `... else EXCLUDED_SECTION_GIDS`. |
| **R3** | **Incident start date understated.** #151 body / case file say "since 2026-06-10". Earliest `succeeded:0` run in CloudWatch is **2026-06-03** (28927 records over the window). Incident is ≥1 week older than stated. | LOW | Logs Insights asc sort: earliest `succeeded:0` = `2026-06-03 11:01:38`. |
| **R4** | **NEW live defect not in the ledger: `cloudwatch:PutMetricData` AccessDenied.** insights-export role lacks the IAM action → `WorkflowSuccessRate` and `WorkflowDuration` metrics silently fail to emit. The incident's own alarm-observability is partly dark. | MEDIUM (NEW) | Logs: `metric_emit_error ... AccessDenied ... cloudwatch:PutMetricData ... no identity-based policy allows`. Role `autom8-asana-insights-export-lambda-role`. |
| R5 | LOW finding imprecise: "10 unannotated except Exception (all re-raise)". | LOW | `git grep 'except Exception' \| grep -v noqa` → ~12 no-noqa lines, but most carry inline `# BROAD-CATCH:` annotations; ~8 truly bare. "All re-raise" is FALSE: `health.py:381` (degrade), `factory.py:136`, `dataframe_cache.py:1242` (isolation/swallow) do not re-raise. Count and qualifier both loose. Does not affect verdict. |

---

## Rung-honesty audit (checklist #4)

- #149/#135/#148 graded `merged on main` + CLOSED-LIVE: **HONEST** (gh + git-grep confirm merge AND absence-at-HEAD). The "operator: merge local branch" routing is correct — these are NOT in the working branch.
- SCAR-REG-001 graded `proven-in-code-only`: **PARTIALLY DISHONEST** (R2) — frozensets are wired live into processor.py; only the join scaffold is dark.
- Bare-DataServiceClient / D-1 / D-2 graded `proven`: **HONEST**.
- Nothing graded CLOSED that is only `proven`. No manufactured finding without a HEAD receipt (checklist #5: **PASS** — every case-file finding I sampled reproduced against a real ref).

## Manufactured-finding check (checklist #5): CLEAR
Every sampled finding has a reproducing receipt. No phantom findings detected. The case file UNDER-states (R1-R4), it does not fabricate.

---

## Cleared to STRONG
- Three landed-holds are STRONG-merged-on-main and STRONG-absent-from-working-branch. Operator merge of the working branch onto main is the residual action for these three.
- SCAR-REG-001 placeholder-GID count (19) and VERIFY-BEFORE-PROD posture: STRONG.
- DataServiceClient roster completeness (exactly 2): STRONG.
- D-2 zero-coverage: STRONG.

## BLOCKING items (against the cutover, not against the case file)
1. **#151 must merge** — it is the actual fix for the LIVE `succeeded:0` BI incident (AUTH-TEB-001). This is more cutover-critical than SCAR-REG-001 and is mis-prioritized in the case file. (R1)
2. **IAM PutMetricData gap (R4)** — incident alarms are partly dark; fix before relying on `WorkflowSuccessRate` as a deploy gate.

## Net
**CONCUR-WITH-FLAGS.** The case file's evidence is sound and its "not-clear-to-ship" conclusion is correct, but its single headline action is mis-pointed: the live BI incident is ended by merging **#151** (auth), not by the W-IRIS section-GID fetch (SCAR-REG-001). SCAR-REG-001 remains a real HIGH pre-prod blocker for the reconciliation Lambda, but it is not the live-incident cause. Re-point the "one action," re-grade SCAR-REG-001 liveness up (R2), correct the incident start date (R3), and add the PutMetricData IAM gap (R4).
