---
type: handoff
status: draft
handoff_status: pending
source_rite: sre
target_rite: arch/10x-dev
from_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
to_repo: /Users/tomtenuta/Code/autom8
created: 2026-06-04
in_reply_to: HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2-2026-06-03
supersedes_item: "RETURN-3 §1 CQ-RETURN-3 — now carries the data-backed evidence to answer it"
ledge_status: AUTHORED-and-delivered
reversible: true
evidence_ceiling: MODERATE  # SRE-authored; STRONG only where live-measured (project §D baseline) or rite-disjoint
discipline: REVERSIBLE/READ-ONLY authorship. Section lane STAYS PAUSED. No merge/apply/deploy/secret/knob-land by this artifact. Secrets redacted.
---

# HANDOFF — autom8y-asana (SRE) → autom8 (consumer): CR-3 RETURN-4 — §D re-scoped (serve-stale-section / V6): PROJECT clears, SECTION needs your call

> In reply to your RETURN-2 (CQ-4 keep max_workers=10; CQ-5 CDC-routing accepted; (B)/(C) committed `ae41170c`). Carries the **data-backed evidence** to answer CQ-RETURN-3 (raised in RETURN-3). Reversible/read-only; section lane stays PAUSED; the cutover ≥99% verdict is the chaos §D re-gate's to issue.

## §0. DECISION / STATUS FIRST — a SPLIT disposition

The re-scoped §D re-gate (serve-stale-section / V6) was run this phase on the headroom-applied substrate (`origin/main=e57a3cba`, running task-def **:473** cpu/mem **2048/8192 HEALTHY**). Outcome is a **SPLIT**:

- **PROJECT arm → DISSOLVE path (PASS-pending).** Steady-state is near-idle (CPU **~1.28% avg / ~3.06% max** — the single-worker CPU-starvation thesis is **REFUTED LIVE**), /health p99 ~0.44s, green target healthy, target-5XX=0. The serve-stale + 2048/8192-headroom paradigm **dissolves the project bulk-fanout 502 problem** without CDC. The headline ≥99% satellite/fallback-ratio PASS is **baseline-consistent but not yet load-measured** — see §1.
- **SECTION arm → CDC-blocked (HELD).** 576s section freshness is **infeasible via warming** (~8× the Asana-429 ceiling — falsified). Serve-stale-section delivers **~30-50 min** frame-age. Held this phase (knob inversion); needs your CQ-RETURN-3 answer.

## §1. PROJECT arm — one prerequisite to a measured PASS (our prong, no action needed from you)

The §D ratio PASS is currently **un-measurable** because the receiver's EMF SLI (#98 3-cause split) is **dark on the deployed image** — the `/metrics` exposition (`instrument_app()`, `api/main.py`) is on an **unmerged branch (PR #107), one commit ahead of deployed main**. `up{job="asana"}=0`, `scrape_samples{asana}=0` (vs the data service's 898). **Fix is ours: merge+deploy PR #107 → `/metrics` lights up → AMP scrape → chaos §D drives the ratio PASS.** This is a receiver-prong SLI-restore; it does not need consumer action.

**Recommendation: cut PROJECT over independently** of the section contract renegotiation — project rides 24h LKG, has no section-lane dependence, and the knob is not in tension for project (`project=86400` unchanged). *(One UV-P for your confirm: is the #55 repoint flag arm-granular, or all-or-nothing? If all-or-nothing, the arms can't split at the merge boundary.)*

## §2. SECTION frame-age data — your decision input for CQ-RETURN-3

- **576s-warm is INFEASIBLE** (~8× the Asana API rate-limit ceiling for the 34-GID section set; the section warm lane is PAUSED).
- **Serve-stale-section delivers ~30-50 min** frame-age today (bulk heaviest-GID inter-warm ~46 min + the 50-min LKG ceiling), served immediately from LKG — **no build, no 502** — *once the knob is lifted off the build path*.
- As-deployed (`section=576`), section is forced onto build→502 under load, so it is **HELD** this phase.

## §3. Knob recommendation (PR #106, draft, gated)

PR **#106** sets `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]: 576 → 3000` (the LKG ceiling, so section **joins project on serve-stale**). **Gated** on your answer + a deliberate land gate. Recommended bound **3000** (maximal relief, zero surprise).

## §4. ACTION — answer CQ-RETURN-3

> **Is 576s SECTION freshness load-bearing for offer-join correctness, or is serve-stale-section at ~30-50 min acceptable as an interim until CDC materialization lands?**

- **(a) accept-interim** → we land PR #106 (section→3000), the re-scoped §D measures BOTH arms on serve-stale, both cut over; section freshness chased by CDC (rnd, off critical path).
- **(b) wait-for-CDC** → section stays HELD, PR #106 moot until CDC lands; **cut PROJECT over alone now.**

Either way, **PROJECT is ready to cut over independently** once we deploy PR #107 (SLI-restore) and the chaos §D measures the ratio PASS. You can answer CQ-RETURN-3 **now, in parallel** — it is independent of our SLI-restore work.

## §5. Carry-forward (your prong, unchanged)
- **PRE-SB-1** — the Section rollback-lever TEST (drive `Section.get_df` flag-OFF → assert `emit_fallback_signals(reason=REASON_FLAG_DISABLED, source=SOURCE_SECTION)` → `_get_df_legacy_sdk`). BLOCKS Stage-B(section) independent of the re-gate verdict. The H-2 branch is code-present (`section/main.py:679`); the TEST is the gap.
- **#55** repoint stays HELD behind the §D PASS + your QA-green (IC-GATE-7). Secret-2 decommission stays IC-gated.

*RETURN-4 from the autom8y-asana SRE rite, 2026-06-04. AUTHORED-and-delivered (`pending` until accepted). Reversible/read-only; section lane PAUSED; secrets redacted; the cutover ≥99% PASS is the chaos §D re-gate's to issue.*
