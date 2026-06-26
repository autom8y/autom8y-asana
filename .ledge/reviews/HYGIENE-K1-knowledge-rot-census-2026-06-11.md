---
type: review
status: accepted
evidence_grade: MODERATE
self_cap: MODERATE
station: K1 (code-smeller)
procession: Freeze-Window Capitalization (hygiene-rite)
authored_at: 2026-06-11
truth_anchor: origin/main fa265ce1bde8be1d003f39501877d17fe600b0c0
method: file:line receipts vs origin/main; READ-ONLY; no commits/stash; seam2 worktree untouched
consumers: [K2 re-baseline, K4 seam2-rescue, K5 naxos-archive]
---

# HYGIENE-K1 — Knowledge-Plane Rot Census

> Census of three surfaces against `origin/main fa265ce1` (34-day-stale knowledge
> plane, seed `8980bcd7`). Every verdict carries a file:line receipt or a
> command-output receipt. Self-ref ceiling MODERATE (single-station authorship,
> no rite-disjoint corroboration at census time).

## Denominators (G-DENOM)

| Surface | Whole-surface denominator | Sampled |
|---------|---------------------------|---------|
| `.know/` core + feat/ + telos/ | 13 core + 39 feat + 3 telos = **55 files** | frontmatter: 55/55; load-bearing claims: 9 core + INDEX coverage + 3 seed-gap files |
| seam2 worktree dirty files | **16** (6 src + 7 test + uv.lock + 2 untracked) — prompt under-counted (said 10) | 6 src diffs + 7 test strata + collision proof |
| `.sos/wip/` (non-complaint) | **26 files + 1 thermia dir (7) + complaints 325** | 26 + thermia + complaint-bucket verdict |

---

## TABLE 1 — `.know/` Rot Census

**Frontmatter denominator: 55/55 inspected.** All core + feat files carry
`source_hash: 8980bcd7`, `generated_at: 2026-05-08`, `expires_after: 7d`/`14d`/`30d`.
Today = 2026-06-11 → **every core (7d) and feat (14d) file is EXPIRED**; all are
34 days past generation. origin/main HEAD is `fa265ce1` — **source_hash drift
8980bcd7 → fa265ce1 across the entire saga (#111/#115/#118/#123/#127/#128) is
unrepresented**.

| File | claims-checked / sampled | Verdict (receipt) | K2 refresh-priority |
|------|--------------------------|-------------------|---------------------|
| `architecture.md` | 10/10 | **STALE** — 9/9 asserted paths CURRENT (`services/{resolution_result,universal_strategy,query_service}.py`, `dataframes/builders/cascade_validator.py`, `api/{lifespan,metrics}.py`, `storage_namespace.py`, `cache/durable_task_cache.py` all `git cat-file -e` EXISTS). 1 FALSIFIED: L24 "**33 top-level packages**" — `git ls-tree origin/main:src/autom8_asana \| wc -l` = **30**. Whole saga-layer (storage_namespace, durable_task_cache, BuildCoordinator wiring) undocumented. | **P1** |
| `feat/INDEX.md` | coverage | **STALE** — census "@ HEAD 8980bcd7", "41 features". `grep -ci storage_namespace\|durable_task_cache\|cure.recovery\|receiver.sli` = **0**. All 4 saga features exist on origin/main but are absent from the index. | **P1** |
| `scar-tissue.md` | seed 3/3 | **STALE** — `grep -ci "trap 6\|one-gate\|content-not-log"` = **0**. Missing Trap 6, One-Gate saga, content-not-log lesson (all post-05-08). | **P1** |
| `design-constraints.md` | seed 1/1 | **STALE** — `grep -ci "frozen-4\|single-worker"` = **0**. FROZEN-4 × single-worker tension (the live double-gate) absent. | **P1** |
| `conventions.md` | seed 1/1 | **STALE** — `grep -ci "50.char\|em-dash\|commit-gate"` = **0**. Commit-gate (≤50-char subject, no em-dash) absent. | **P2** |
| `feat/*.md` (37 @ 8980bcd7) | frontmatter | **STALE** (bulk) — all `source_hash 8980bcd7`, 14d expiry, 34d old. `dataframe-layer.md` mtime 06-08 but frontmatter still 8980bcd7. | **P2** (bulk re-stamp) |
| `feat/{batch-api-client,search-service}.md` | frontmatter | **STALE** — older seed `c213958` (2026-04-01), pre-everything. | **P3** |
| `telos/dataframe-resolution-coherence.md` | spot | **CURRENT** — authored 2026-06-08, docs-station, live FM-1..FM-4 frame. | keep |
| `telos/{cache-freshness-2026-04-27, sprint3-path-b-2026-04-30}.md` | spot | **STALE** (status: proposed, superseded-era) | **P3** archive-eligible |
| `db.md` | 1/1 | **CURRENT** — "No database layer detected" still true (DuckDB is MCP-attached, not a layer). | keep |
| `env-loader.md` | frontmatter | **CURRENT-window** — 90d expiry from 04-20, not yet expired. | keep |

**Top-3 .know rot findings**: (1) `architecture.md` "33 packages"→**30 FALSIFIED** + whole saga-layer undocumented; (2) `feat/INDEX.md` **0/4 saga features indexed** (storage_namespace, durable_task_cache, cure-recovery, receiver-SLI all live, all absent); (3) `scar-tissue.md` **0/3 seed traps present** (Trap 6 / One-Gate / content-not-log).

---

## TABLE 2 — seam2 Worktree Archaeology (K4 rescue seed)

Worktree `PRESENT` at `/Users/tomtenuta/code/a8/repos/seam2-unit-econ`, branch
`cr3-dfr/seam2-unit-economics-population`, HEAD `e686ba06` (confirmed via
`git -C … rev-parse`). **Intent: FM-4 unit-economics population cure** —
honest enum `discount` (Decimal→Utf8/str), number→display_value fallback parity,
currency/percent normalization, and unit value-column registration.

**Stratum check** (`git log e686ba06..origin/main -- <file>`): **only 1 of 6 src
files moved underneath.** The other 5 are byte-identical to e686ba06 on origin/main
(0 commits underneath) → clean apply. No #111/#118/#123/#127/#128 commit touched
these 5 paths in the base→fa265ce1 window.

| File (a) intent | (b) moved underneath | (c) conflict-risk |
|-----------------|----------------------|-------------------|
| `builders/post_build_population_receipt.py` — adds `"unit": ("mrr","weekly_ad_spend")` to `_VALUE_COLUMNS_BY_ENTITY` | **#115 `b2c2beb5` (FPC Phase-1)** already added `"unit": ("mrr",)` — 1 commit underneath | **REDESIGN-LIKELY** — semantic conflict, not textual: origin **deliberately chose `("mrr",)` only**, with an inline rationale rejecting `weekly_ad_spend` as `LegitimatelySparse` and citing the **$8,775/7-row null-fossil anti-precedent** ("manufacture false WARNs"). Worktree wants to ADD weekly_ad_spend back. K4 must reconcile against origin's explicit refusal, not just re-apply the hunk. |
| `models/task_row.py` — `discount: Decimal\|None` → `str\|None` (enum) | 0 commits | **CLEAN-APPLY** |
| `resolver/coercer.py` — +`_normalize_numeric_string`, `_CURRENCY_PREFIXES` (additive, +84) | 0 commits | **CLEAN-APPLY** |
| `resolver/default.py` — number-branch `display_value` fallback parity | 0 commits | **CLEAN-APPLY** (verify no downstream caller now relies on the prior null-on-number contract) |
| `schemas/unit.py` — discount `dtype Decimal`→`Utf8`, source comment enum | 0 commits | **CLEAN-APPLY** — but **CROSS-FILE COHERENCE**: must land atomically with task_row.py (model/schema dtype contract pair) |
| `views/cf_utils.py` — `extract_cf_value` number-branch display_value fallback (mirrors default.py) | 0 commits | **CLEAN-APPLY** |

**Test strata**: all 7 modified test files = **0 commits underneath** (e686ba06..origin/main) → tests apply clean; +2 untracked (`test_seam2_unit_economics.py`, `tests/spikes/`). Prompt listed 4 tests; **actual = 7 modified + 2 untracked + uv.lock**.

**K4 directive**: 5 src + all tests are CLEAN-APPLY/RECONCILE-light. The ONE
load-bearing decision is `post_build_population_receipt.py`: the worktree's
2-column unit floor **contradicts a ratified origin decision** (#115's 1-column
floor + anti-precedent rationale). Rescue must adjudicate this as a design
question (does weekly_ad_spend belong in the population floor?), not a merge.

---

## TABLE 3 — `.sos/wip/` Sprawl Inventory (K5 naxos archive seed)

| Item | Date | Superseded-by | Verdict |
|------|------|---------------|---------|
| `NORTH-STAR-…-2026-06-09.md` | 06-09 | -06-10 → -06-11 → -06-11-prerelease/-11b | **ARCHIVE** |
| `NORTH-STAR-…-2026-06-10.md` | 06-10 | -06-11 chain | **ARCHIVE** |
| `NORTH-STAR-…-2026-06-11.md` | 06-11 | -06-11-prerelease / -11b | **ARCHIVE** (superseded same-day) |
| `NORTH-STAR-…-2026-06-11-prerelease.md` | 06-11 | candidate-current | **KEEP** (pending K2 confirm which of prerelease/-11b is canonical) |
| `NORTH-STAR-…-2026-06-11b.md` | 06-11 | candidate-current | **KEEP** (dedupe vs prerelease — one is stale) |
| `CONSULT-column-fidelity-orientation-2026-06-11.md` | 06-11 | active (FM-5 contract live) | **KEEP** |
| `*-2026-04-28.md` (refactor-plan, audit-verdict, janitor-log, review-signals/assessment, case-file, smell-report) ×7 | 04-28 | prior hygiene cycle consumed | **ARCHIVE** |
| `SPIKE-staging-vs-canary-prod-gap-2026-04-28.md` | 04-28 | canary saga resolved | **ARCHIVE** |
| `SPIKE-pr67-ruff-format-fail-2026-05-27.md` | 05-27 | resolved | **ARCHIVE** |
| `G2-RECV-*-2026-05-26.md` ×3 | 05-26 | G2-RECV deployed (memory: FIXED 05-26) | **ARCHIVE** |
| `cr3-{producer-sprint-ledger,verified-findings}-2026-06-03.md` | 06-03 | CR-3 landed | **ARCHIVE** |
| `SPIKE-active-mrr-offer-economics-null.md` | (04) | resolved ($8,775 fossil diagnosed) | **ARCHIVE** |
| `SPIKE-{cascade-surface-area,freshness-last-verified-at,lockfile-propagator-tooling-fix}.md` | (04-05) | consumed | **ARCHIVE** (verify each not re-referenced) |
| `DEFER-WATCH-cr3-cutover.md` | — | mirrors `.know/defer-watch.yaml` | **KEEP** (cross-check vs canonical) |
| `shelf-bootstrap-approval-queue.yaml` | — | active queue | **KEEP** |
| `thermia/` (7 files) | 04-27→06-02 | thermal saga; TDD-receiver-warm-convergence-06-02 most recent | **ARCHIVE 6, KEEP TDD-06-02** (pending thermia confirm) |
| `complaints/*.yaml` (**325**) | 04-12→06-10 | drift-detector auto-emit bucket | **BULK-ARCHIVE candidate** — flag to naxos: 325 auto-complaints, mostly `drift-detector`; needs triage-sweep not per-file. |

---

## TABLE 4 — MEMORY-vs-Reality Spot-Check

The falsified-claims patch (BuildCoordinator/LKG/Retry-After) is confirmed landed:
`api/lifespan.py:226-244` wires `initialize_build_coordinator` inside lifespan.
Spot-checked 3 OTHER index lines:

| Memory index line | Load-bearing claim | Verdict (receipt) |
|-------------------|--------------------|--------------------|
| `offline-reader-entity-blind-fossil` (RESOLVED) | offline reader entity-aware on origin/main; "offline.py:83 still entity-blind" is STALE | **ACCURATE** — `origin/main:src/autom8_asana/dataframes/offline.py:10-16`: "ONE reader that historically had no entity_type in scope … It now accepts an optional `entity_type`". RESOLVED claim holds. (Note: path is `dataframes/offline.py`, not bare `offline.py`.) |
| `active-mrr-offer-economics-null-fossil` | entity-agnostic S3 key → fixed (entity-segmented namespace) | **ACCURATE** — `origin/main:src/autom8_asana/storage_namespace.py` EXISTS; offline.py:7-8 documents legacy(entity-agnostic)→v2(entity-segmented) key shapes. Fix landed. |
| `satellite-deploy-gate-and-ci-traps` | workflow_handler xdist crash trap | **CURRENT** — `tests/unit/api/routes/test_workflows.py` + conftest present on origin/main; trap surface intact. |

**No additional falsified/stale memory entries found** in this spot-check. The
memory index is healthy post-patch; the rot is concentrated in `.know/` (Table 1).

---

## Directives

- **K2 (re-baseline)**: consume Table 1. P1 = `architecture.md` (fix "33"→30, add saga-layer), `feat/INDEX.md` (+4 saga features), `scar-tissue.md` (+Trap 6/One-Gate/content-not-log), `design-constraints.md` (+FROZEN-4×single-worker). Re-stamp all 55 to `source_hash fa265ce1`. Dedupe NORTH-STAR prerelease vs -11b first.
- **K4 (seam2 rescue)**: 5 src + 7 tests CLEAN-APPLY. The single load-bearing blocker is `post_build_population_receipt.py` — adjudicate worktree's 2-column unit floor vs origin #115's ratified 1-column floor + $8,775 anti-precedent. Land schemas/unit.py ⊗ task_row.py atomically (dtype contract pair).
- **K5 (naxos)**: Table 3 — ARCHIVE ~20 dated artifacts + 6 thermia + triage-sweep 325 complaints; KEEP 6 active. Resolve the NORTH-STAR -11-prerelease/-11b duplicate.

**Evidence grade**: MODERATE (self-cap). Single-station authorship; receipts are
`git`-reproducible against `fa265ce1` but uncorroborated by a rite-disjoint attester
at census time.
