---
type: handoff
artifact_id: HANDOFF-substrate-to-10x-dev-cure-2026-07-13
schema_version: "1.0"
source_rite: sre
target_rite: 10x-dev
handoff_type: execution
priority: high
blocking: false
initiative: "asana-substrate-attribution (C3 offer-frame freshness cure)"
created_at: "2026-07-13T21:40:00Z"
# status: HANDOFF-schema lifecycle (per @cross-rite-handoff HANDOFF-009); shelf-status is draft
status: proposed
shelf_status: draft
source_artifacts:
  - .ledge/handoffs/HANDOFF-asr-to-substrate-session-2026-07-13.md
  - .ledge/decisions/TELOS-asana-substrate-freshness-2026-07-13.md
evidence_grade: moderate
provenance:
  - source: "auth/bot_pat.py:57-75 (single-credential S2S callers)"
    type: code
    grade: strong
  - source: "transport/asana_http.py:200-213 (per-client AIMD semaphore)"
    type: code
    grade: strong
  - source: "config.py:184-191 (PAUSED-lane reserved_concurrency backfire note)"
    type: code
    grade: strong
  - source: "cache/integration/dataframe_cache.py:1251-1258 (FRESH/STALE semantics)"
    type: code
    grade: strong
  - source: "PR #97 sre/cache-warmer-fast-lane (+525/-9, FAST_LANE_HEAVY_GIDS)"
    type: code
    grade: moderate
tradeoff_points:
  - attribute: "time-to-mitigate"
    tradeoff: "The recommended tactical route (a)-then-(b) is config+small-code, not the durable arbitration end-state (c)."
    rationale: "The storm is attributed; a bounded warmer-side cure is now telos-permitted PROVIDED it does not add net concurrency on the shared PAT. (c) is the correct end-state but is arch-grade and out of this wave."
items:
  - id: CURE-001
    summary: "Restore ASR offer-frame freshness for project_gid 1143843662099250 by curing the shared-PAT self-inflicted 429 storm that starves its hierarchy warm — WITHOUT adding net concurrency on the shared token bucket."
    priority: high
    acceptance_criteria:
      - "Offer GID 1143843662099250 frame age < 3600s SUSTAINED across >= 2 consecutive warm cycles (this bar is LOOSER than code-fresh; see Freshness Semantics below — it MUST NOT be described as 'fresh')."
      - "The hierarchy warm for that GID actually SUCCEEDS: hierarchy_gap_warming_failed clears and gaps_warmed > 0 (currently gaps_warmed:0 on 429)."
      - "The cure is net-concurrency-neutral-or-negative on the shared ASANA_PAT budget: it does NOT introduce a new concurrent lane that races the existing serve + warmer lanes on the same 1500/60s ceiling (respects the config.py:184-191 reserved_concurrency backfire finding)."
      - "The live AL-5 alarm asana-AL5-offer-frame-stale-1143843662099250 (non-paging, threshold 3600) is observed transitioning to OK and holding across the >= 2 cycles — this alarm is the ASR arc resume-gate's instrument, not a proxy dashboard."
      - "Implementation is routed through 10x-dev/framing (this handoff SPECIFIES; 10x-dev frames and implements). No production-mutating lever (merge, terraform apply/import, paging) is taken on agent authority."
    notes: "Cure-mechanism slate is enumerated in §F1 below; recommended sequencing is (a)-then-(b) tactical, (c) durable end-state. PR #97 is adjudicated in §PR-97 — it is NOT a drop-in cure for this GID."
    estimated_effort: "framing + config + small code change (route a+b); arch ADR if (c) is elected"
---

## Skills (named pointers — bind, do not inline)

- **@cross-rite-handoff** — this artifact's schema (`handoff_type: execution`, `items[].acceptance_criteria`). The work-transfer plane; the disjoint attestation charge (if minted) is authored by `ari procession charge`, not hand-written.
- **@telos-integrity-ref** — the rung ladder (authored < specified < cured) governing the un-rounded rung claim in §Rung, and the Gate-C handoff receipt discipline every claim-token below satisfies.
- **@option-enumeration-discipline** — governs §F1: the cure-mechanism slate MUST be exhaustive (>= 4 enumerated) before a recommendation is ratified; a truncated option slate is the failure this discipline guards.
- **@defer-watch-manifest** — governs §DEFER: each deferred item carries a refutable watch-trigger and a named reactivation recipient; DEFER is a verdict, not a silence.

---

## §Context — why this cure is shaped the way it is

This handoff hands 10x-dev/framing a fully-attributed defect and a bounded cure spec. The attribution is not a hypothesis — it is the mechanism, and it dictates the cure's shape: **the ASR offer frame goes stale because the offer's hierarchy warm loses a race for a shared, un-arbitrated rate-limit budget.** Any cure that "warms harder" by adding a concurrent lane on that same budget makes the storm worse, not better. That constraint is the load-bearing input to the option slate.

The felt-line question — is any client-serving flow being throttled by agent action here — is **NO**: this is an internal warmer/substrate freshness concern, not a client-facing throttle. So the ASR-GID cure does not trip the "never throttle a client-serving flow on agent authority" non-ruling (that non-ruling still binds for any route that would touch the serve path — see §Escalation).

## §Attribution (C1) — the storm's mechanism (cite; do NOT re-derive)

- **Single shared credential.** One bot PAT `ASANA_PAT` backs the ECS serve path + all 3 cache-warmer lanes + EBI receipts — "single credential ... all S2S callers" (`auth/bot_pat.py:57-75`). ONE shared 1500/60s budget across all consumers.
- **Rate limiting is PER-PROCESS only; cross-consumer arbitration is CONFIRMED ABSENT.** `TokenBucketRateLimiter` is per `AsanaClient` (`client.py:158-163`); the per-client AIMD `AsyncAdaptiveSemaphore` lives at `transport/asana_http.py:200-213` and `config.py:392-413`. Each process throttles only itself; concurrent lanes overshoot the shared ceiling and mutually inflict 429s. In-tree self-description: "the proven ROOT-1a self-inflicted 429 storm" (`transport/adaptive_semaphore.py:75`).
- **Warmer fan-out is the burst source.** Bulk sweep = 34 GIDs x 2 arms = 68 keys; per starved key ≈ 3,291 `GET /tasks/{gid}` (`parent_gids_count=3291`), recursing depth 5, partly UNBOUNDED `asyncio.gather` (`cache/providers/unified.py:638-641`). The PAUSED-lane comment records the backfire directly: the section lane hit ~896 429s/12min, and "raising reserved_concurrency WORSENS it (more parallel links -> more concurrent 429s on the same token bucket)" (`config.py:184-191`). There is NO deployed `ASANA_RATELIMIT` override (code-default 1500/60s everywhere); warmer `reserved_concurrency=1`.
- **The storm is BURST-driven, not sustained-average exhaustion.** Service = 17,449 Asana calls/1h ≈ 19% of the average budget; the 6h 429-line splits service=79,881 / warmer-bulk=25,669 / warmer=3,095. The 07-10T15:50Z onset hypothesis is **FALSIFIED**: 07-08 21Z=895 and 07-09 21Z=1010 429s/3h, BEFORE the 07-10 15Z=723 "onset" — the storm was already raging, diurnal-bursty.
- **EBI holds NO own token.** `api/routes/receipts.py:160` routes via the bot PAT (`/v1/receipts` -> live `tasks/search`); it folds into the service line — a contributor, not the sole onset (`api/routes/receipts.py:127` carries `forwarding_receipt_request.caller_service`, but no per-route budget).

## §Target (C3) — cure target + Freshness Semantics

**Target GID**: ASR offer, `project_gid 1143843662099250`.

**Acceptance** (canonical form is in the frontmatter `CURE-001.acceptance_criteria`): frame age < 3600s SUSTAINED across >= 2 warm cycles **with the hierarchy warm actually succeeding** — today it reports `hierarchy_gap_warming_failed` / `gaps_warmed:0` on 429, so "frame present" is not sufficient; the warm must complete.

**Freshness Semantics (say this precisely; do NOT call < 3600s "fresh")**: the code defines FRESH ≤ TTL (offer TTL = 180s) and, for offer, STALE > **540s** (TTL 180 × `SWR_GRACE_MULTIPLIER` 3.0 — `config.py:137` + `cache/integration/dataframe_cache.py:1247-1258`; the oft-quoted 900s is the *default*-TTL figure, 300×3, not offer's). The **< 3600s acceptance bar is LOOSER than code-fresh and looser than the code STALE boundary** — it is a "not-catastrophically-stale" restoration target chosen to match the live AL-5 alarm threshold, NOT a freshness guarantee. Any implementation report or attestation MUST describe the < 3600s bar as "AL-5-clear / not-catastrophically-stale," never as "fresh."

## §PR-97 — attribution-informed adjudication of the existing F1(b) machinery (the crux)

**PR #97** — title "feat(warmer): dedicated 15-min fast lane for the two heaviest GIDs", branch `sre/cache-warmer-fast-lane`, **OPEN 5+ weeks**, +525/-9 (`cache_warmer.py`, `project_registry.py`, `timeout.py` + tests). It adds `prematerialize_fast_set` + `FAST_LANE_HEAVY_GIDS = (DNA_HOLDER 1167650840134033, UNIT/BusinessUnits 1201081073731555)` as a **separate concurrent 15-min lane**.

**Adjudication against the attribution — two structural problems:**
1. **Coverage gap**: PR #97 does NOT include the ASR offer GID `1143843662099250`. As-is, merging it does nothing for the C3 target.
2. **Concurrency backfire risk**: a *separate concurrent lane* ADDS net concurrency on the shared PAT — exactly the pattern the in-tree `config.py:184-191` note documents as WORSENING the storm ("more parallel links -> more concurrent 429s on the same token bucket"). This is the most plausible reason #97 has sat unmerged for 5+ weeks: it was authored before the shared-budget/no-arbitration mechanism was attributed, and under that mechanism a naked concurrent fast lane is net-harmful.

**Verdict**: PR #97's *machinery* (the `FAST_LANE_HEAVY_GIDS` prioritization primitive) is the right lever for route (b), but PR #97 *as currently shaped* is NOT a drop-in cure. It is safe ONLY if paired with a budget partition (route a) OR if the fast lane **replaces** bulk coverage for those GIDs rather than **adding** a concurrent lane. 10x-dev/framing owns that reshaping decision.

## §F1 — cure-mechanism enumeration (>= 4; @option-enumeration-discipline)

**(a) Static PAT-budget partition** via env `ASANA_RATELIMIT_MAX_REQUESTS` per consumer, summing to < 1500/60s across serve + warmer lanes.
- *Character*: tactical, config-only, no code. *Attribution fit*: directly addresses the shared-budget-with-no-arbitration mechanism by hard-capping each consumer below the shared ceiling so lanes stop mutually overshooting.
- *Constraint*: the CI apply lane is currently wedged (pending-zero-jobs), so the deploy path for a config-only change is itself gated — 10x-dev/framing must account for this deploy-wedge.

**(b) Per-GID warm prioritization** = EXTEND PR #97's `FAST_LANE_HEAVY_GIDS` to include the ASR offer GID `1143843662099250` (small, pattern-consistent code change).
- *Character*: small code change on existing machinery. *Attribution fit*: net-concurrency-neutral **ONLY IF** paired with (a), OR IF the fast lane REPLACES bulk coverage for those GIDs rather than adding a concurrent lane (per §PR-97). Standalone (b) inherits PR #97's backfire risk.

**(c) Cross-consumer budget arbitration / allocator** — a shared allocator that arbitrates the single PAT budget across all consumers.
- *Character*: arch-grade ADR; **does NOT exist today** (ADR-ASANA-003 is per-client AIMD only, no cross-consumer arbitration). *Attribution fit*: this is the DURABLE end-state — it removes the root mechanism (absent arbitration) rather than working around it. Out of this wave's scope; requires an architecture decision.

**(d) Hold-attributed + alert-only** via the live AL-5 detection — accept "attributed-but-uncured this wave," watch the AL-5 alarm, cure later.
- *Character*: no code, no config. *Attribution fit*: per telos, "attributed-but-uncured this wave" is the MOST tolerable failure — the storm is now understood and instrumented (AL-5 has two-sided teeth proven live via canary). This is the honest fallback if (a)'s deploy-wedge or (b)'s reshaping cannot land safely this wave.

**RECOMMENDATION**: **(a)-then-(b)** as the tactical cure — partition the budget first so the shared ceiling stops being overshot, THEN add the ASR GID to the prioritized set (safe because the partition has removed the concurrency-backfire hazard, or pair with the replace-not-add reshaping of #97). **(c)** is the durable end-state and should be filed as an arch ADR (see §DEFER). **(d)** is the telos-tolerable fallback if neither (a) nor (b) can land safely this wave. ALL routes go through **10x-dev/framing**.

## §NAMED-INTOLERABLE (telos)

The telos names as intolerable: "a warmer-side patch shipped under an UN-attributed fleet storm — it burns the wave without moving the gate." **The storm is NOW attributed** (§Attribution), so a warmer-side patch is no longer that intolerable act — **BUT** it remains intolerable if it ignores the shared-budget finding. Concretely: shipping route (b) standalone (a naked concurrent fast lane) under the attributed shared-budget mechanism would re-enter the intolerable class by the concurrency-backfire path. The recommended (a)-then-(b) sequencing exists precisely to stay out of that class.

## §Rung (un-rounded; @telos-integrity-ref ladder authored < specified < cured)

C3 is **ATTRIBUTED -> SPECIFIED this wave, NOT cured.** This handoff moves the rung from ATTRIBUTED to SPECIFIED; it does not claim CURED. The cure is out-of-wave (10x-dev implements). The instrument the ASR arc's resume-gate watches is the live AL-5 alarm `asana-AL5-offer-frame-stale-1143843662099250` (non-paging, threshold 3600) — the resume-gate fires on frame age < 3600s sustained across 2 cycles [UNATTESTED — DEFER-POST-HANDOFF: cure not yet implemented; see DEFER-2026-C3a]. No rounding-up to CURED is asserted here.

## §Escalation (non-rulings preserved)

- **Never throttle a client-serving flow on agent authority** (non-ruling #3 -> ESCALATE). The felt-line for THIS cure is NO (internal warmer/substrate only), so the ASR-GID cure is not a client-throttle. But if 10x-dev/framing elects a route that would cap or reshape the **serve path** budget (a plausible sub-choice of route (a)'s partition, since the serve path shares the PAT), that touches a client-serving flow and MUST be escalated to the user, not taken on agent authority.
- All production-mutating levers (merge of the cure PR, `terraform apply`/`import` of any IaC codifying the partition, paging changes, DMS retire, node-4) remain the user's.

## §DEFER — watch-register (do NOT scope-creep; @defer-watch-manifest)

Three items are explicitly DEFERRED out of this cure's scope. Each carries a refutable watch-trigger and a named reactivation recipient (always a rite Potnia, never a specialist).

```yaml
defer_entry:
  id: DEFER-2026-C3a
  title: "EBI per-route attribution query (caller_service breakdown)"
  source_decision:
    artifact: HANDOFF-substrate-to-10x-dev-cure-2026-07-13.md:§Attribution
    verdict_id: "substrate-attribution wave §Attribution — EBI folded into service line"
    deferred_at: "2026-07-13"
  deferral_rationale:
    why_not_now: "EBI (api/routes/receipts.py:160) has no own token and folds into the service line; per-route attribution via forwarding_receipt_request.caller_service (receipts.py:127) is a refinement, not required to shape the C3 cure."
    smaller_change_available: false
  watch_trigger:
    trigger_type: external-event
    trigger_definition: "Post-cure, if the service-line 429 share fails to fall below its pre-cure fraction AND EBI receipt traffic is suspected as a residual contributor, run the per-route caller_service attribution query."
    evaluation_cadence: on-explicit-invocation
  escalation_path:
    reactivation_signal_recipient: "potnia@sre"
    reactivation_artifact_path: ".ledge/handoffs/HANDOFF-sre-ebi-per-route-attribution-{date}.md"
    reactivation_invocation: "/go (sre) then frame EBI per-route attribution"

defer_entry:
  id: DEFER-2026-C3b
  title: "AL-5 threshold tightening 3600 -> TTL post-cure"
  source_decision:
    artifact: HANDOFF-substrate-to-10x-dev-cure-2026-07-13.md:§Target
    verdict_id: "substrate-attribution wave §Target — <3600s is looser than code-fresh"
    deferred_at: "2026-07-13"
  deferral_rationale:
    why_not_now: "The 3600 AL-5 threshold is the resume-gate instrument for THIS wave; tightening it toward the code TTL (offer 180s) is only meaningful once the cure holds frame age well below 3600s."
    smaller_change_available: false
  watch_trigger:
    trigger_type: empirical-count
    trigger_definition: "Once the cure has held offer-frame age < 3600s across >= 2 cycles for >= 7 consecutive days, tighten AL-5 threshold toward the code FRESH/TTL boundary."
    evaluation_cadence: at-wave-retrospective
  escalation_path:
    reactivation_signal_recipient: "potnia@sre"
    reactivation_artifact_path: ".ledge/handoffs/HANDOFF-sre-al5-threshold-tighten-{date}.md"
    reactivation_invocation: "/go (sre) then frame AL-5 threshold tighten"

defer_entry:
  id: DEFER-2026-C3c
  title: "Cross-consumer budget arbitrator ADR (F1 route c — durable end-state)"
  source_decision:
    artifact: HANDOFF-substrate-to-10x-dev-cure-2026-07-13.md:§F1
    verdict_id: "substrate-attribution wave §F1 route (c)"
    deferred_at: "2026-07-13"
  deferral_rationale:
    why_not_now: "Route (c) is arch-grade and does not exist today (ADR-ASANA-003 is per-client AIMD only). The tactical (a)-then-(b) cure restores C3 without it; (c) is the durable removal of the root mechanism (absent cross-consumer arbitration) and warrants its own architecture decision."
    smaller_change_available: true
    smaller_change_reference: "F1 routes (a)-then-(b) tactical cure — covers the C3 gap without the arbitrator."
  watch_trigger:
    trigger_type: composite
    trigger_definition: "If a SECOND shared-PAT starvation incident recurs on a DIFFERENT GID after the tactical (a)-then-(b) cure lands, the per-GID/per-consumer partition has proven insufficient and the arbitrator ADR (c) reactivates."
    evaluation_cadence: at-wave-retrospective
  escalation_path:
    reactivation_signal_recipient: "potnia@arch"
    reactivation_artifact_path: ".ledge/decisions/ADR-asana-cross-consumer-budget-arbitrator-{date}.md"
    reactivation_invocation: "/go (arch) then frame cross-consumer budget arbitrator"
```

## §Routing note

This handoff routes to **10x-dev/framing**. It does NOT dispatch any 10x-dev specialist — 10x-dev's Potnia frames the cure from this spec, selects the route ((a)-then-(b) recommended), and reshapes-or-supersedes PR #97 per §PR-97. Implementing the cure is OUT-OF-WAVE for the sre-rite substrate wave.

## §Self-assessment

Evidence grade **MODERATE** (ceiling). Rationale: the attribution claims each carry a code-path file:line receipt (STRONG at the individual-claim level), but this handoff's *recommendation and sequencing* are single-author sre-rite judgment authored under a self-referential vantage (the recommending rite is proposing the cure it scoped); per `self-ref-evidence-grade-rule` the document-level grade caps at MODERATE pending 10x-dev/framing's independent option review (the @option-enumeration-discipline external check). No claim above is asserted without its receipt from the attribution pack; the one forward-looking rung claim is DEFER-tagged (DEFER-2026-C3a), not asserted as fact.
