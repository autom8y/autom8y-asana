---
type: handoff
handoff_type: validation
status: accepted
from: 10x-dev (W-COLDFRAME procession)
to: sre
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — 10x-dev W-COLDFRAME → sre

> **Grandeur anchor (closed at the root):** The asana `POST /v1/query/offer/rows` 503 starving ASR was a COLD offer frame caused by a hierarchy-gap warm crash. Root cause proven = a reserved-LogRecord-key `KeyError("Attempt to overwrite 'name'")` — but it was **version skew (C1)**, NOT a missing code fix, and the already-completed `2f75d79` deploy HEALED it. No code change shipped (FORK-2: do not fix a healed path).

## OUTCOME — FORK-2 heal, no code fix (proven live)

The W-COLDFRAME build was **halted at the gate** and **PR #154 CLOSED as moot + mis-based**. The discipline caught three things:
1. **The architect refused to invent a colliding site** — proved the warm path uses structlog `get_logger` (cannot raise the stdlib `makeRecord` KeyError), so the only crash-capable surface is the `DefaultLogProvider`, which **#150 already sanitizes on `origin/main`** (`_defaults/log.py:108` → `autom8y_log.sanitize_log_extra`; `pyproject.toml:23` `autom8y-log>=0.7.0`). The live crash was the OLD receiver image (version skew, C1).
2. **The build agent's worktree was mis-based** on stale `f4f924d2` (pre-#150) — the branch-state trap — so PR #154 re-fixed a bug main already carried; CONFLICTING/DIRTY. Closed.
3. **The `2f75d79` deploy (task-def :554, rollout COMPLETED 2026-06-24 21:31Z) already healed it.**

### Live receipts (post-deploy, on `2f75d79`)
- **KeyError gone:** `"Attempt to overwrite"` since 21:31Z = **0 matched / 107,820 scanned** (G-DENOM PASS).
- **Offer frame warming:** `dataframe_cache_put project_gid=1143843662099250 row_count=1380` @ 22:10:15Z; `store_populate_batch_starting warm_hierarchy=true` 22:08–22:09Z.
- **Latest warm-fails are now Asana 429/Timeout, NOT the KeyError:** `hierarchy_gap_warming_failed` @ 22:07Z carries `error_type: RateLimitError (HTTP 429)` / `TimeoutError` on LARGE projects (parent_gids 2606/824/364).
- **No ASR 503 since the deploy:** last `offer_fetch_failed:503` @ 20:28Z (pre-deploy); zero since.

## Realization rungs (honest; never round up)
- Cold-frame ROOT (KeyError-crash): **fixed-live** — healed by the `2f75d79` deploy (version reconciliation), proven by zero KeyErrors + the frame warming.
- Incident (ASR offer read 2xx): **NOT yet `protecting-prod`** — ASR is periodic and has **not run since 20:28Z**, so there is no live ASR-2xx receipt yet. The proximate cause (cold frame) is resolved; the final close awaits a live ASR run.

## VALIDATION ASK (sre)
1. **Re-run the ASR dry-run** (account-status-recon, caller `8156aa10`) and confirm `offer_fetch` returns **2xx** (not 503) against the now-warm offer frame `1143843662099250`.
2. Confirm **`3_of_3` recovery** (was 0 / 99 critical when the frame was cold).
3. **Re-evaluate node-4 (ASR schedule-enable)** — it stays **DEFERRED** until `3_of_3` recovers; this validation is its gate.

## Watch-registered DEFER (distinct from the healed KeyError — do NOT bundle)
- **Asana HTTP 429 / TimeoutError on large-project hierarchy-gap warm** (parent_gids 2606/824/364) — a pre-existing rate-limit/AIMD concern that could intermittently re-cold LARGE frames under load. Route: AIMD/warmer reliability (H-4-adjacent / sre). The offer frame (1143843662099250, ~1380 rows) warmed fine; this risk is for the big projects.
- **`asctime` absent from #150's reserved-key set** (`_LOGRECORD_RESERVED`, 23/24 stdlib-protected keys) — a LOW-severity pre-existing SDK/#150 gap; `asctime` is a log-format token, not a plausible payload key. Route: know/SDK track.
- **R8 coverage gap:** `project_gid=1143843662099250` absent from warmer-bulk/section coverage entirely — orthogonal to the warm-crash.
- Inherited: FORK-2 interop substrate (2026-09-29), H-4 cache_warmer decomposition, W-REG/SCAR-REG-001 (until W-IRIS), stale `test_fleet_query_adapter.py:370`.

## Production-mutating levers — status
The `2f75d79` deploy was NOT fired by this procession (it was already in-progress, someone's core-4.7.0 rollout, which incidentally carried the heal). No merge/deploy executed by 10x-dev this phase (the only build artifact, PR #154, was closed unmerged). Token rotation / section-GID WRITE / deploy-freeze / paging remain user-sovereign and untouched.

## Inherited receipts / context
`autom8y-asana-query503-coldframe` (operator memory, RESOLUTION recorded); inbound `@.ledge/handoffs/HANDOFF-sre-offer-axis-root-2-arm-landed-asana503-frontier-2026-06-24.md`; the discrimination + build workflows (`wf_f7276701-b9d`, `wf_7897e967-bed`). Closed PR: #154.
