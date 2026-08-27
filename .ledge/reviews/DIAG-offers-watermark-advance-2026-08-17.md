---
type: review
status: accepted
title: "DIAG — offers watermark advance: the freeze was never a watermark freeze"
sprint: SPR-A1
wave: asr-insight-landing
authored_by: 10x-dev/architect
authored_at: 2026-08-18T04:45Z
content_window: 2026-08-17 / 2026-08-18 (straddling; filename date retained for edge-ID stability)
production_change: NONE
pins:
  autom8y-asana: 8e1b3964
  autom8y: origin/main 676ec9be
evidence_grade: STRONG (two disjoint legs — code-mechanism + live producer trace — converging; five ticks across TWO distinct anchors; one code prediction confirmed and four hypotheses falsified)
headline: >-
  The offers freshness gate measures business activity, not data freshness.
  CONJUNCT-1 (a passing organic tick) is NOT reachable by waiting; it is
  reachable only by curing. The frame's "42 tick opportunities by 2026-08-24"
  arithmetic is FALSE — see §6.5. FORK-GAMMA-relevant, operator needs it EARLY.
---

# DIAG — offers watermark advance

> **Filename note.** The `-2026-08-17` suffix is retained for edge-ID stability.
> The content straddles 2026-08-17 and 2026-08-18; authored 2026-08-18T04:30Z.
> SCAR-1 correction applied in the opposite direction from the usual: the sprint
> briefing carried 08-17 as "now"; actual UTC now is 2026-08-18T~04:00Z (local
> PDT, UTC−7). Two organic ticks (08-17T20:00Z, 08-18T00:00Z) that were absent
> from the briefing are load-bearing for this verdict.

---

## §0 — THE TWO-VALUED VERDICT

### V-1 — §5.7 null-watermark bypass: **FALSIFIED** as the cause.

The prime suspect named at sprint entry — `dataframes/builders/freshness.py:294-298`,
the guard `if section_info.watermark is not None:` that lets null-watermark sections
bypass the `modified_since` content check — is **not** the mechanism of the observed
offers staleness freeze. It is falsified on **three independent grounds**, any one of
which is sufficient:

1. **Wrong axis (code).** The quantity the ASR gate reads is not derived from section
   watermarks at all in the way the suspicion assumed, and the quantity the suspicion
   *would* affect (`data_age_seconds`) is not the quantity being gated. See §2.
2. **Wrong population (live).** Exactly 20/34 offer sections carry `watermark: null`,
   and **all 20 have `rows: 0` and `gid_hash: e3b0c44298fc1c14`**. That hash is
   `compute_gid_hash([])` — verified identical by direct computation (SVR-5). These are
   **empty-by-construction** sections (LAUNCH ERROR, PENDING APPROVAL, STAGING, CALL,
   MANUAL, ONE-OFF …), not sections where watermark tracking failed. On a coherently
   empty section the D8 false-CLEAN class is *unconstructable*: any content requires a
   task, any task changes the GID set away from empty, and the prober re-fetches and
   re-hashes the live GID set every warm. Hash-only detection **is** complete
   verification there.
3. **The predicted downstream symptom did not occur.** In my mechanism-leg pass I
   predicted the bypass would produce a self-perpetuating unstamped loop pinning
   `verification_age`. The live trace shows `section_last_verified_stamped
   stamped=34, healed_watermarks=0` — **34/34 stamped, every cycle.** The FIX-1
   coherently-empty exemption (`builders/progressive.py:561-567`) is firing exactly as
   designed and routing all 20 empties to the stamp at `:573`. My prediction is
   falsified, and the falsification is a **positive attestation of a prior cure**.

**Disposition:** §5.7 is a real, narrow, *latent* residual for a section that is
non-empty AND has a null watermark. **Zero such sections exist on the offer manifest
today (0/34).** It is not in the cure path. Card it as latent; do not spend on it.

### V-2 — The real mechanism: **the offers freshness gate measures business activity, not data freshness.**

The ASR readiness gate for `offers` reads a **CONTENT axis** — and the content axis is
`now − min( newest task edit in the "active" section pool, newest task edit in the
"activating" section pool )`. It is a measure of **how long since a human or bot last
touched an offer task in the quieter of two Asana pipeline pools.** It is a
business-activity latency wearing a data-freshness label.

The five-day "freeze" was not a freeze of any cache, watermark, sidecar, or clock. It
was a five-day **quiet stretch in the offer-launch funnel**: no task moved through
`{ACTIVATING, LAUNCH ERROR, IMPLEMENTING, NEW LAUNCH REVIEW, AWAITING ACCESS}` between
2026-08-12T11:33:40.703Z and 2026-08-17T21:41:07.639Z. The gate reported that quiet as
staleness and aborted reconciliation on a demonstrably healthy pipeline.

**It ended itself when the business moved.** No deploy, no intervention, no fix.

**And it immediately re-armed on a fresh anchor.** The reference stepped **once** at
21:41:07.639Z and has been pinned there ever since: the 04:01Z tick back-computes to the
*same* instant (§2.3), 6.3 h later, with staleness climbing again from the new pin. Five
ticks now fit across **two distinct anchors**. The mechanism reproduced itself in real
time, under observation, on an anchor that did not exist when the diagnosis began. That
is the strongest available confirmation that the quantity is *time since the newest task
moved* and not any property of the data pipeline. `[STRUCTURAL | STRONG]`

### V-3 — Reachability: **CONJUNCT-1 is not reachable by waiting.**

A passing organic tick requires a business event to land in a 60-minute window before a
tick, in **both** section pools. Over the fully observed 136.9-hour window there was
**exactly one** such event, and it landed 2 h 20 m before the next tick — missing not
only the 3600 s pass bar but the 7200 s abort bar. **Zero of the ~34 ticks in the
observed window were pass-eligible.** See §6.4. The wave's exit predicate cannot be
reached by patience; it can only be reached by curing. §6.5 states plainly why the
"42 tick opportunities by 2026-08-24" arithmetic is false.

---

## §1 — RECONCILIATION OF THE TWO LEGS

Both legs were internally correct. They answered **different questions**, and the seam
between them is the axis switch this sprint's own mechanism leg surfaced at §A.2 and
then failed to carry through.

| | Mechanism leg (code, 08-17) | Live leg (traces, 08-18) |
|---|---|---|
| Question answered | "What is `data_age_seconds` and what could freeze it?" | "What is the gate actually reading?" |
| Answer | `now − S3 frame watermark`; a build clock | section content watermarks, 4/4 ticks ≤0.6s residual |
| Correct? | **Yes, for that quantity** | **Yes, for the gated quantity** |
| Error | Reasoned as if the DORMANT branch were live | (none — deferred the section-set question correctly) |

**The reconciliation is the axis switch.** On `origin/main`,
`services/account-status-recon/src/account_status_recon/readiness.py:522-556` is a
three-branch switch whose own comment reads verbatim:

```
# THE AXIS SWITCH. `data_age_seconds` is reached only on the DORMANT
# branch, and only with a disclosure log -- it is a disclosure quantity
# (the serving cache entry's age), not a freshness axis, and once a
# content axis is available nothing may gate on it.
```

- `GATE` → `offer_staleness = decision.content_age_seconds`
- `REFUSE` → `offer_staleness = refusal_staleness_seconds(check)` (sentinel)
- `DORMANT` → `offer_staleness = data_age_seconds` (+ disclosure log)

**The gate is on the GATE branch.** Proved by elimination against the live numbers:

- If DORMANT: staleness would equal `data_age_seconds` = `now − S3 frame watermark`.
  The sidecar advances hourly (L-2: `dataframe.parquet` LastModified
  2026-08-18T03:15:23Z, user-metadata `watermark=2026-08-18T03:15:22.494401+00:00`), so
  DORMANT staleness would be ≤ ~1 h. Observed 404 825 s. **Excluded.**
- If REFUSE: staleness would be exactly `3600 × 2.0 + 1.0 = 7201.0` s
  (`readiness.py:387-393`, `REFUSAL_STALENESS_OVERSHOOT_SECONDS = 1.0`). Observed
  8 379.6 and 462 425.4. **Excluded.**
- Therefore **GATE**, on all six ticks.

**Corollary — UV-P-2 is discharged, in the direction opposite my lean.** The GATE
branch requires `disposition == GATE` on both constituents, which requires the SDK to
have derived a per-response verdict, which requires
`detect_content_axis_capability().available == True` (`fetcher.py:309-368`), which
requires **autom8y-core ≥ 4.14.0 installed in the deployed ASR Lambda**. It is. The
Lane-K content axis is not merely merged — **it is live and gating in production.**
`offers_content_axis_unavailable` is not firing.

**My §Q1.2 claim is CORRECT-BUT-NOT-LOAD-BEARING.** `data_age_seconds` *is* `now −
(instant of the last durable frame write)` — the live trace confirms it exactly
(serving ages 4457.2 / 4538.2 / 4600.7 / 4503.9 s against an hourly-advancing sidecar).
That quantity was simply never the one aborting the wave. The inherited premise ("the
ASR gate reads `data_age_seconds` verbatim") was one I had *already falsified in my own
§A.2* and then reasoned past in §Q1. **Apply the discipline inward: the disjoint leg's
correction was derivable from evidence already inside my own artifact.**

**Three of my mechanism-leg hypotheses are falsified by the live trace:**

- **M1 (fail-closed PRESERVE gate latched).** Falsified. `write_decision="write_as_is"`
  on every cycle; the converged gate's PRESERVE branch
  (`section_persistence.py:885-903`) is not entered.
- **M2 (entity-plane split-brain).** Falsified. The v2 offer key
  `dataframes/1143843662099250/offer/` is the key being written *and* read.
- **M3 (immortal memory entry / SWR never completes).** Falsified. Serving ages
  **oscillate** (1 063 – 9 522 s) rather than climbing monotonically;
  `swr_refresh_triggered` + `swr_build_started` fire on every stale serve and the entry
  is being replaced. SWR is working.

**One of my code predictions is CONFIRMED, and it is the load-bearing one.** §Q4.0
predicted, from code alone, that the frame watermark advances on a build clock and
therefore cannot carry a RED tooth. The 03:15Z warm cycle proves it empirically:
`build_result_classified sections_succeeded=0, sections_failed=0, total_rows=4191,
fetched_rows=0, sections_probed=34, sections_delta_updated=0, fetch_time_ms=0.0` with
`freshness_probe_complete verdicts={"clean":34}` — and the S3 watermark was
nevertheless stamped `2026-08-18T03:15:22.494401Z`. **A warm that fetched zero rows
advanced the substrate watermark by an hour.** Code prediction + live confirmation, two
disjoint legs. `[STRUCTURAL | STRONG]`

---

## §2 — THE MECHANISM, NAMED PRECISELY

### §2.1 The derivation chain (file:line, both repos)

```
ASR fetch_offers  (origin/main services/account-status-recon/src/account_status_recon/fetcher.py:497-520)
  ├─ query_rows_async("offer", classification="active",     select=[...], limit=1000, include_content_axis=True)
  └─ query_rows_async("offer", classification="activating", select=[...], limit=1000, include_content_axis=True)
       │   (`last_modified` is NOT in select_fields; the SDK appends it under the
       │    include_content_axis opt-in — fetcher.py:467-478)
       ▼
asana query engine  (autom8y-asana src/autom8_asana/query/engine.py)
  :123-124  classification_sections = self._resolve_classification(request.classification, entity_type)
  :438-490  _resolve_classification -> SectionClassifier group expansion
  :153-161  pl.col("section").str.to_lowercase().is_in(list(classification_sections))
       ▼
OFFER_CLASSIFIER  (src/autom8_asana/models/business/activity.py:181-226)
  "active"     -> 22 sections {PENDING APPROVAL, CALL, OPTIMIZE-*, STAGING, STAGED,
                               ACTIVE, RESTART-*, SYSTEM ERROR, REJECTIONS / REVIEW,
                               REVIEW OPTIMIZATION, MANUAL, ONE-OFF, RUN OPTIMIZATIONS}
  "activating" ->  5 sections {ACTIVATING, LAUNCH ERROR, IMPLEMENTING,
                               NEW LAUNCH REVIEW, AWAITING ACCESS}      <-- activity.py:209-215
       ▼
SDK derive_response_freshness  (autom8y-core >= 4.14.0)
  per response:  content_watermark_returned = max(last_modified over RETURNED rows)
                 content_age_seconds        = axis_now - content_watermark_returned
       ▼
ASR combine_offer_axis  (origin/main readiness.py:190-370)
  :362  content_age_seconds = max(ages)
  :367-369  disclosure: "age is the max (oldest) of [...]"
       ▼
readiness.py:526  offer_staleness = decision.content_age_seconds
readiness.py:515  StalenessCheck(threshold_seconds=settings.offer_staleness_threshold_seconds)  # 3600
       ▼
SDK ReadinessGate: PASS iff staleness <= 3600 ; ABORT at threshold x warn_multiplier(2.0) = 7200
```

### §2.2 The quantity, stated exactly

> **gate_age = now − min( max(last_modified over rows in the 22-section `active` pool),
> max(last_modified over rows in the 5-section `activating` pool) )**

`max(ages)` over the two constituents is arithmetically `now − min(watermark)`. The
gate is therefore pinned to **whichever of the two pipeline pools has been quiet
longest.** This is fail-conservative by design (`readiness.py:367-369` says so
explicitly: *"the max (oldest)"*), and it is precisely why the gate is so easy to trip.

### §2.3 CORRECTION to the live leg's section-set inference

The live leg proposed: *"fits `max(watermark)` over EXACTLY {ACTIVATING, IMPLEMENTING}
and no other subset — it must EXCLUDE ACTIVE (1143843662099256, watermark
2026-08-17T16:43:49.745Z) which would otherwise dominate the 16:01Z tick."*

**That inference is an artifact of comparing a CURRENT manifest snapshot against
HISTORICAL tick values.** Direct arithmetic (SVR-8):

| tick (UTC) | observed staleness | back-computed REF | anchor | residual vs anchor | age if `ACTIVE` section were the active-pool max |
|---|---|---|---|---|---|
| 08-17T12:01:24 | 433 625.3 | 2026-08-12T11:34:18.700 | IMPLEMENTING | +38.00 s | **−16 945.7 s (NEGATIVE)** |
| 08-17T16:01:11 | 448 025.9 | 2026-08-12T11:34:05.100 | IMPLEMENTING | +24.40 s | **−2 558.7 s (NEGATIVE)** |
| 08-17T20:01:09 | 462 425.4 | 2026-08-12T11:34:03.600 | IMPLEMENTING | +22.90 s | +11 839.3 s |
| 08-18T00:01:08 | 8 379.6 | 2026-08-17T21:41:28.400 | ACTIVATING | +20.76 s | +26 238.3 s |
| **08-18T04:01:26.069** | **22 778.198** | **2026-08-17T21:41:47.871** | **ACTIVATING** | **+40.23 s** | — |

*(IMPLEMENTING wm = 2026-08-12T11:33:40.703Z; ACTIVATING wm = 2026-08-17T21:41:07.639Z.)*

The `ACTIVE` section's watermark of 08-17T16:43:49.745Z **did not exist** at the 12:01Z
or 16:01Z ticks — the implied ages are negative. It could not have "dominated" them.
The residual column (+20.76 to +40.23 s, all positive, all inside a 20-second band) is
the serve-vs-sample lag the live leg identified, so the correlation is far tighter than
the raw residual suggests once the lag is modelled.

> **Arithmetic note, stated rather than smoothed.** The fifth point was relayed with a
> "+0.55 s serve-lag residual." I cannot reproduce that figure: `04:01:26.069 −
> 22778.197727 s = 2026-08-17T21:41:47.871Z`, which is **+40.23 s** past the ACTIVATING
> watermark — at the upper edge of, but inside, the band the other four points already
> established. **The conclusion is unchanged and in fact better supported by a different
> statistic:** the 00:01Z and 04:01Z back-refs are **19.47 s apart** despite their ticks
> being **four hours apart**. Two independent measurements four hours apart that resolve
> to references twenty seconds apart are explicable only if the underlying anchor is
> *identical* and the residual is measurement lag. That is a stronger identification than
> any single-point residual.

**Corrected statement:** `ACTIVE` is **not excluded from the derivation.** It belongs to
the `active` constituent, which is evaluated, produces its own age, and then **loses
`max(ages)`** because the `activating` pool's max was older at every tick. At the
00:01Z tick the active-pool max must have been *newer* than 21:41:28 (else `max(ages)`
would have returned 26 238.3, not 8 379.6) — i.e. some section in the 22-section active
pool other than `ACTIVE` held the pool max. The 4-point correlation the live leg found
identifies **which section held the losing pool's max**, not which sections are in scope.

The mechanism conclusion is **unchanged and strengthened**: the gate reads the quieter
of two business pools. `[STRUCTURAL | STRONG]`

### §2.4 — Can ANY threshold on this quantity be correct? **No.**

Stated plainly, as asked.

The quantity has no upper bound derivable from system health. It is bounded only by
**how often a human or bot edits an Asana task in the quieter pool.** The `activating`
pool is 5 sections wide and is the new-launch funnel — structurally low-traffic. Two
consequences:

1. **The threshold is unsatisfiable on a schedule.** For PASS at 3600 s, some task in
   the quieter pool must have been modified within the **60 minutes preceding each
   4-hourly tick**. The ticks are 00:01 / 04:01 / 08:01 / 12:01 / 16:01 / 20:01 UTC =
   17:01 / 21:01 / 01:01 / 05:01 / 09:01 / 13:01 PDT. **Three of six ticks land between
   21:00 and 05:00 local.** Absent machine activity, the overnight ticks are
   structurally incapable of passing. No number fixes that; it is a shape problem.
2. **Raising the threshold destroys the signal without fixing the gate.** To cover a
   normal weekend the threshold would need to exceed ~72 h. At that point the gate can
   no longer detect a genuinely dead producer either, because a dead producer and a
   quiet weekend are *the same number*. The quantity does not separate the two states
   at any threshold. This is construct-invalidity, not mis-calibration
   [SRC-001 Messick 1989] [STRONG] — the instrument measures something outside the
   construct it names (construct-irrelevant variance, P-08), so no re-anchoring of the
   cut-score can rescue its validity for this use [SRC-006 Kane 2006] [STRONG].
3. **The coupling makes it worse.** `offer_staleness_threshold_seconds` moves warn AND
   abort together (abort is derived as `threshold × warn_multiplier`); there is no knob
   that moves one alone. Contract §1.6 already recorded this as operator card D-3.

**Two-sided bar consequence — can a genuinely-halted warmer still be distinguished?**

| Axis | Quiet business, healthy warmer | Halted warmer | Distinguishes? |
|---|---|---|---|
| `content_age_seconds` (today) | climbs without bound → **ABORT** | climbs without bound → ABORT | **NO.** Both arms produce the identical signal. The RED tooth exists but bites the wrong thing; the GREEN arm is unreachable. |
| `data_age_seconds` (build clock) | ~0–1 h → PASS | **~0–1 h → PASS** (proved: `fetched_rows=0` still stamped a fresh watermark) | **NO.** No tooth at all. |
| `verification_age` (§1.2, Option 7) | stamp advances on every CLEAN probe → **PASS** | no probe ⇒ no stamp (`progressive.py:515-516` skips `PROBE_FAILED`; `:561-572` withholds an unverifiable stamp) ⇒ climbs → **ABORT** | **YES.** Only axis that separates the two arms. |

**The current axis fails the two-sided bar in the opposite direction from the one this
sprint was chartered to guard against.** We guarded against a false-GREEN; what shipped
is a permanent false-RED that a genuinely-halted warmer would be *indistinguishable*
from. `[STRUCTURAL | STRONG]`

This is independent confirmation, from the mechanism side, of the operator ruling
recorded at §3.

---

## §3 — OPERATOR RULING ON THE RECORD (§1.2 vs §1.6)

The §1.2 / §1.6 self-divergence surfaced by this sprint's mechanism leg (§Q3.2) has been
**RULED**: **§1.2 [A-2026-08-12] GOVERNS.** The later operator-ruled amendment
supersedes the unconformed §1.6 prose. **`verification_age_seconds` is the axis of
record for the `offers` source**, and realizing it end-to-end (mechanism-leg Option 7)
is sanctioned as the strategic target.

The mechanism finding at §2.4 is **concordant and independent**: the verification axis
is the only one of the three that satisfies the two-sided bar. The ruling and the
mechanism agree without either having been derived from the other.

**Consequence for the shipped content axis.** Lane K is live and correct *as an
implementation of §1.6*. Under the §1.2 ruling it is now a **superseded axis running in
production** — and, per §2.4, one that cannot be made correct by threshold. It should
be treated as a transitional state with a named exit, not as the destination.

**Concrete Option-7 grain finding (code-level, new).** `compute_verification_age`
(`metrics/freshness.py:785`) scopes to `classifier.active_sections()` —
`sections_for(AccountActivity.ACTIVE)` (`activity.py:88-90`), the **22-section active
pool only**. The ASR offers request spans **both** `active` and `activating`. §1.2's
binding VERIFICATION GRAIN says *"every section the producer's classifier assigns to the
requested classification(s)"* — plural. The correct primitive already exists:
`billable_sections()` at `activity.py:92-94` returns `ACTIVE ∪ ACTIVATING`. **Option 7
must select the grain from the request's classification set, not hardcode
`active_sections()`.** Using `active_sections()` would under-scope the denominator and
violate the ruled grain on day one.

---

## §4 — RESIDUAL DEFECTS, WITH DISPOSITIONS

### R-1 — Substrate-v2 content-addressed lane frozen 5.7 days against its own 1 h SLA
`dataframes-v2/1143843662099250/offer/current.json` LastModified 2026-08-12T09:58:02Z;
`proof.built_from_live_at = 2026-08-12T09:57:00.916Z`; `sla_seconds = 3600`. Note this
predates the 11:34Z cure-wave deploy by ~1.5 h.
**Code corroboration:** `src/autom8_asana/substrate/` has **zero importers** anywhere in
`src/` outside itself, and `built_from_live_at` has **zero hits** in the v1 path
(SVR-6). The Seam-1 freshness core is built and **UNWIRED**; the v2 lane has no live
producer in this tree.
**Why it matters to this DIAG:** `fold_built_from_live_at` is the v2 realization of
exactly the axis the operator just ruled as the axis of record. A frozen, unwired v2
lane silently breaching its own declared SLA is both a dark-instrument defect and a
partial duplicate of the Option-7 target.
**Disposition: SEPARATE CARD**, routed to whoever owns Seam-1. Must be reconciled with
Option 7 before Option 7 designs a third derivation of the same quantity.
`[STRUCTURAL | MODERATE]`

### R-2 — `population_degraded=true` on every warm; a below-floor frame is persisted hourly
Live: `dataframe_cache_put_memory_skip_degraded`, `write_decision="write_as_is"`,
`population_degraded=true`, `reason="degraded_frame_not_promoted_to_hot_tier"`.
**Code reading:** `dataframe_cache.py:952` — `if self._is_degrade_decision(write_decision)
or population_degraded:` → the memory-tier eviction fires on the **second** disjunct
(`_is_degrade_decision("write_as_is")` is False, `dataframe_cache.py:552-553`). And the
converged gate's backstop (`section_persistence.py:905`) requires `write_decision is
None`, so with `WRITE_AS_IS` recorded it does **not** refuse. **Net: the offer frame is
breaching the population floor and being durably persisted anyway, every hour.**
The hot-tier eviction is also a no-op for serving — the warmer is a Lambda
(`lambda_handlers/cache_warmer.py`), out-of-process from the ECS serving task, so it is
evicting from its own short-lived memory tier.
**This is the most serious residual.** It is a *data-quality* defect on the frame the
gate is protecting, and it is fully independent of every freshness axis. It says the
served offer rows have null value-cells below the active-subset floor.
**Disposition: SEPARATE CARD, HIGH.** Not in the freshness cure. Should be triaged
before any freshness threshold is trusted, because a correct freshness signal over a
below-floor frame is still a wrong answer. `[TACTICAL | STRONG]`

### R-3 — `s3_storage_dataframe_saved` absent after 00:24:21Z while the parquet advanced to 03:15:23Z
**These two observations are in direct contradiction**, and I decline to build any part
of the verdict on either until one more probe resolves it. `save_dataframe`
(`storage.py:931-962`) has exactly one PUT site for the dataframe key and emits
`s3_storage_dataframe_saved` iff `df_ok and wm_ok`. Either (a) the log is present and
the query missed it, or (b) the object advanced without that code path running — which
would imply a writer this DIAG has not enumerated.
**Highest-prior cause: the selector trap.** `s3_storage_dataframe_saved` is a
**bare-kwargs** call site (`logger.info("s3_storage_dataframe_saved", project_gid=…,
row_count=…, watermark=…)`), so under the structlog backend its fields render **FLAT**
(`$.watermark`), whereas `cache_warm_success` / `final_artifacts_written` /
`fail_closed_write_preserve_prior_good_enforced` use `extra={…}` and render **NESTED**
(`$.extra.watermark`). A single Insights query written against one shape silently
misses the other. This trap was flagged in the mechanism leg before the traces were
pulled.
**Disposition: IN-CURE as a one-query re-probe** (re-run the L-3 query with a FLAT
selector and no field filter, event-name only). If the log is genuinely absent at
03:15Z, escalate immediately — an unenumerated writer to the durable frame key is a
first-class finding. `[TACTICAL | WEAK]` pending the re-probe.

### R-4 — §5.7 null-watermark bypass (latent)
Falsified as this incident's cause (§0 V-1). Non-empty sections with a null watermark
would still be hash-only; **0/34 exist today**.
**Disposition: CARD AS LATENT.** Re-check if the empty-section count ever drops while
the null-watermark count does not. `[TACTICAL | MODERATE]`

### R-5 — T-GUARD cliff at 1000 rows (latent, newly identified)
Both constituent queries carry `limit=1000` (`fetcher.py:504-518`). If either pool's
`total_available` exceeds 1000, T-GUARD fires (`returned_count < total_available`), the
SDK returns REFUSE, and `combine_offer_axis` returns the **refusal sentinel**
(`7201.0 s`) — a *guaranteed permanent abort*, with a failure mode that looks nothing
like growth. The frame is 4191 rows today; the pools are under 1000 today (proved by the
GATE branch being live). **This is a cliff, not a slope.**
**Disposition: SEPARATE CARD, LATENT-HIGH.** `[STRUCTURAL | MODERATE]`

---

## §5 — RE-RANKED CURE LEVERS

The mechanism-leg ranking was built for a frozen-anchor mechanism that is now falsified.
Re-ranked against the mechanism **as now known**, and against the two-sided bar
(**GREEN on a cold serving cache** AND **RED tooth preserved**):

| Rank | Lever | GREEN | RED tooth | Disposition |
|---|---|---|---|---|
| **1** | **Option 7 — realize `verification_age_seconds` end-to-end** (operator-ruled axis of record). Producer: `compute_verification_age` (`metrics/freshness.py:735-831`) plumbed onto the serve path via the manifest read the engine already performs for `honest_contract_complete`; grain from `billable_sections()` per §3, **not** `active_sections()`. SDK: a separately-named field (§1.2 NON-ALIASING clause 2 — no `or`, no fallback, no shared parse branch). ASR: a fourth disposition path, frame-scoped, alongside the existing content switch. | **YES** — frame-scoped, identical on a cold worker and a warm one (satisfies §1.6's fresh-task acceptance case by construction). | **YES** — the only axis that does. Advances only on a live probe with a non-`PROBE_FAILED` verdict whose delta applied; cannot advance on a build clock; §1.2 NON-ALIASING clause 1 forbids sourcing it from one. | **IN-CURE, PRIMARY.** ~2 sprints. Was rank-2; promoted by the ruling *and* by §2.4. |
| **2** | **L6 — alarm re-home** | n/a | n/a | **IN-CURE, DO FIRST, ZERO-RISK.** Six consecutive `readiness_check_fail` over five days produced no alarm, and the recovery produced no alarm either. Whatever the axis, that blindness is its own defect and it is the cheapest thing on this list. |
| **3** | **L7 (enumeration-gap lever, mechanism-leg §Q4.2) — reframed.** Originally "unfreeze the durable write." The durable write is **not** frozen (falsified). L7 survives in re-pointed form: **the warm does no work** — `fetched_rows=0`, `sections_delta_updated=0`, 34/34 CLEAN, 5.8 min wall time, and it still stamps a fresh watermark. | n/a | This is the *proof* that the build clock has no tooth (§1). | **RETAINED, RE-POINTED, SEPARATE CARD.** A zero-fetch warm is not necessarily wrong (nothing changed in Asana is a legitimate CLEAN), but a 5.8-minute zero-fetch cycle stamping a freshness-shaped instant is a signal-integrity defect. Bundle with R-2. |
| **4** | **Threshold change** (raise `offer_staleness_threshold_seconds`) | Would produce GREEN. | **DESTROYS IT** — see §2.4 item 2: a dead producer and a quiet weekend become the same number. | **REFUSED.** Explicitly, and on the record. §1.6's own threshold-alignment note already recommends changing no threshold; §2.4 supplies the stronger reason (no threshold on this quantity can be correct). **Not because a number is hard to pick — because the quantity is the wrong construct.** |
| **5** | **L3 — re-point probe at the substrate watermark** | YES | **NO** — `fetched_rows=0` + fresh `now()` stamp is the empirical proof (§1). | **REFUSED as a cure; RETAINED as a diagnostic.** Downgraded from "predicted to fail" to "proven to fail." |
| **6** | **L1 read-through / L2 blocking SWR / L5 resolve vanished client** | — | — | **OUT OF SCOPE.** All three targeted the serving-cache attractor. The attractor is falsified: SWR completes, ages oscillate, the sidecar advances, memory-first is not pinning anything. These levers address a condition that does not obtain. |

**Interim posture while Option 7 is built (design note, not an instruction to act).** The
gate is currently guaranteed to abort on any overnight tick. The honest options are (a)
accept the aborts and let R-2/L6 carry the signal, or (b) route the offers source to
DORMANT deliberately — which is *worse*, because `data_age_seconds` has no tooth at all
(§2.4). Neither is good; that is the cost of the current axis and is itself an argument
for Option 7's priority. **No change is proposed or made by this DIAG.**

**Reachability changes the SCHEDULING of this ranking, not its order.** Because
CONJUNCT-1 is unreachable by waiting (§6.4), Option 7 is not merely the best lever — it is
**on the critical path to the wave's exit predicate**, and every day spent waiting for an
organic pass is a day spent on an outcome with an observed base rate of zero. The
sequencing consequence: **L6 (rank 2) should land immediately** — it is hours of work,
zero-risk, and it is the only thing that will tell anyone the next time this recurs —
while Option 7 (rank 1, ~2 sprints) is scoped. Do not serialize L6 behind Option 7.

---

## §6 — RECURRENCE AND REACHABILITY

### §6.1 — Is the wave chasing a resolved condition? **Partly yes, and the distinction is load-bearing.**

**The 5-day freeze is OVER and will not be "fixed" — it ended itself.** The condition was
a quiet `activating` pool from 08-12T11:33:40.703Z to 08-17T21:41:07.639Z. It cleared at
21:41 when a task in the `ACTIVATING` section was edited. **No deploy, no intervention.**
Any remediation aimed at "unfreezing the watermark" is aimed at a state that no longer
exists and never was what its name said.

### §6.2 — The current abort is a DIFFERENT, RECOVERED state — and it is the more damning one

At 08-18T00:01:08Z the pool had moved **2 h 20 m earlier** and the gate **still aborted**
(8 379.6 s > 7 200 s). Operator text: *"Source 'offers' is 139 min stale."* A pipeline
that saw real activity two hours before the tick is reported as stale data.

> **This is the strongest single argument in the DIAG.** The 5-day freeze could be
> dismissed as an extreme outlier. The 00:01Z tick cannot: it is the *recovered,
> healthy, normal* state, and the gate still fails it. The defect is not the tail —
> **it is the median.**

### §6.3 — The mechanism reproduced itself in real time, on a fresh anchor

The 04:01Z tick (staleness 22 778.198 s, trace `7d356a1ed41e`) back-computes to
**2026-08-17T21:41:47.871Z** — the *same* anchor the 00:01Z tick matched. The reference
did not resume advancing after the 21:41 step; it **stepped once and re-pinned**, and the
counter is climbing again from the new pin (6.3 h and counting at the 04:01Z tick; ~6.7 h
at the 04:25Z probe). Two anchors, five ticks, one mechanism. See §2.3.

### §6.4 — REACHABILITY: is CONJUNCT-1 reachable by WAITING, or only by CURING?

**Only by curing.** Four independent arguments, in increasing strength:

**(a) The bars.** PASS requires `gate_age ≤ 3600 s`; ABORT fires above `7 200 s`.
Therefore **any business-quiet window longer than 2 hours aborts the tick, by
construction, on a perfectly healthy pipeline.**

**(b) It is a CONJUNCTION over two pools, and the binding pool is the small one.**
Because the combination is `max(ages)` (§2.2, SVR-2), a tick passes only if **both** the
22-section `active` pool **and** the 5-section `activating` pool saw a task edit within
the preceding 60 minutes. This is materially stricter than "some offer moved" — and the
`activating` pool is the new-launch funnel, structurally the quieter of the two.

**(c) The schedule kills half the ticks before probability enters.** Ticks fire
00/04/08/12/16/20 UTC = **17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00 Pacific**. The
04:00Z, 08:00Z and 12:00Z ticks land at **21:00 / 01:00 / 05:00 PT** — overnight, when
nobody is moving offers through ACTIVATING or IMPLEMENTING. **Those three of six can
essentially never pass.** The 16:00Z tick (09:00 PT) additionally requires an edit in the
08:00–09:00 PT hour, before most of the working day. Realistically **two of six ticks
(13:00 PT and 17:00 PT) are live candidates at all.**

**(d) The deterministic count — no probability model required, and it is decisive.**
Over the fully observed window **2026-08-12T11:33:40.703Z → 2026-08-18T04:25Z**
(492 679 s = 136.9 h = 5.70 d), containing **~34.2 ticks**:

| quantity | value |
|---|---|
| attested `activating`-pool advance events | **1** (at 21:41:07.639Z) |
| pass-eligible wall-clock (1 event × 3600 s) | 3 600 s = **0.73 %** of the window |
| lead time from that event to the next tick | **8 400 s** — past the 3600 s pass bar *and* past the 7200 s abort bar |
| ticks in the window that were pass-eligible | **ZERO of ~34** |

**The single business event that occurred in five and a half days did not land inside any
tick's pass window.** It missed by 4 800 s. That is not a low probability — it is an
observed zero.

**(e) The order-of-magnitude rate, with its weakness stated.** Treating the one attested
event as a rate estimate gives λ ≈ 1/136.9 h ≈ 0.0073 events/hour; P(≥1 event in a given
1-hour pass window) ≈ 0.73 %; expected passing ticks ≈ **0.044/day ≈ one pass every ~23
days** — and that is the *optimistic* bound, because it prices only the `activating`
conjunct and ignores (b) and (c). **This estimate rests on n = 1 and must not be quoted as
a forecast.** It is offered only to show that the honest number is fractions-of-a-percent,
not tens-of-percent. `[TACTICAL | WEAK]` — the deterministic count in (d) is the
load-bearing evidence; this is colour. `[Cone-of-uncertainty discipline: EST:SRC-002
McConnell 2006 — a point estimate from n=1 carries a 4×–16× band and must be reported as
a range or not at all.]`

**(f) A structural ceiling that holds even under continuous activity.** The pass window
is 1 hour and the tick period is 4 hours, so **at most 25 % of wall-clock is
pass-reachable** no matter how busy the business is. A pool receiving exactly one edit per
day has a ~25 % chance of that edit landing usefully. The schedule itself discards 75 % of
all activity before the threshold is even consulted.

### §6.5 — The "42 tick opportunities by 2026-08-24" arithmetic is FALSE

**Confirmed. The frame's denominator does not measure what it is being used to measure,
and the operator needs this EARLY, not at deadline.** This is FORK-GAMMA-relevant.

The 42 is `7 days × 6 ticks/day`. It is a correct count of **scheduled samples**. It is
not a count of **opportunities**, for four reasons, each independently sufficient:

1. **Ticks are a sampling schedule, not trials.** A tick is an *observation* of a
   business-activity process, not an attempt at anything. Counting observations as
   opportunities assumes the system under test can influence the outcome. It cannot: the
   outcome is set by whether someone edited an Asana task, which is exogenous to every
   component this wave can touch.
2. **The trials are not independent and not identically distributed.** Success is driven
   by a diurnal, weekly-seasonal human-activity process. Three of every six ticks are
   overnight (§6.4c) and are **dead on arrival — 21 of the 42 by construction.**
3. **The per-trial success probability is not a property of the system under test.**
   Raising it requires the business to launch more offers, not the pipeline to work
   better. Any denominator that improves when the sales team is busy is not measuring
   pipeline health [SRC-001 Messick 1989] [STRONG] — construct-irrelevant variance.
4. **The empirical base rate falsifies the implied rate directly.** The observed window
   contained ~34 ticks and **zero** pass-eligible ones (§6.4d). Extrapolating the observed
   activating-pool rate over the remaining ~6 days (~36 ticks) gives an expected event
   count of ~1.2, of which at most ~25 % would land in a pass window (§6.4f), further
   conditioned on the `active` pool being simultaneously fresh (§6.4b). **Expected passing
   ticks by 2026-08-24: well under one.**

> **The honest denominator is not 42. It is "the number of times, in the next six days,
> that a task moves through BOTH offer pools within the same 60-minute pre-tick window" —
> a quantity whose observed value over the preceding 5.7 days was ZERO.**

Planning on 42 treats a near-certain non-event as a 42-trial near-certainty. **The
predicate `report_posted` with **no** `abort_reason` cannot be satisfied by waiting.** The
wave's exit is gated on precisely the quantity that §2.4 shows no threshold can make
correct, so **the exit condition is currently unreachable except through the cure.**

### §6.6 — The user-visible symptom is unchanged and the mission is fully live

The abort notice continues to post **6×/day**, with `report_posted` carrying
`abort_reason=readiness_gate_abort` and a varying `content_hash` on each tick
(20:01Z `sha256:2d10fdee…`, 00:01Z `sha256:a79debe9…`, 04:01Z `sha256:3c9bb1b1…`).

Two facts sharpen this. First, at the 04:01Z tick **billing PASSED at 310.9 s and
campaigns PASSED at 532 s** — 2 of 3 sources are healthy and current; `offers` is the sole
blocker. Second, the wave's exit predicate requires `SourceCoverage3of3 > 0` on a
`report_posted` with **no** `abort_reason` — so the predicate is blocked by exactly the
one source whose axis is construct-invalid. **The client-visible artifact is a
reconciliation report that refuses to reconcile, six times a day, because the sales team
did not launch an offer in the last hour.**

### §6.7 — What makes it recur

Nothing special. Any window in which either pool goes untouched for 60 minutes before a
tick. Given 4-hourly ticks, three of six landing between 21:00 and 05:00 PT, and a
5.7-day observed window containing exactly one qualifying business event, recurrence is
**the default state**, not an exceptional one. It recurred within 6.3 hours of clearing.

### §6.8 — Therefore

The wave should be re-aimed: not at "restore watermark advance" (nothing is stuck), but at
**replacing a construct-invalid axis (Option 7) and closing the independent data-quality
defect (R-2)**. The self-clearing at 21:41Z and the immediate re-arming at 04:01Z are
evidence *for* that re-aim — the second event is what proves the first was not a fix.

---

## §7 — UV-P DISCHARGE RECEIPTS

**UV-P-1** *(mechanism leg)*: `[UV-P: the S3 sidecar dataframes/1143843662099250/offer/watermark.json currently holds 2026-08-12T11:34:05Z | METHOD: deferred-to-live-trace-leg (S3 head-object + get-object) | REASON: this is the M1/M2-vs-M3 discriminator and is a live-substrate fact, not derivable from code]`

**DISCHARGED — claim FALSIFIED.** Live probe (leg L-2):
`dataframes/1143843662099250/offer/dataframe.parquet` LastModified **2026-08-18T03:15:23Z**,
user-metadata `watermark=2026-08-18T03:15:22.494401+00:00`, `row-count 4191`;
`manifest.json` LastModified 2026-08-18T03:09:54Z. **The sidecar advances hourly.** It was
never frozen. M1 and M2 are both excluded by this single receipt, and M3 is excluded by
the oscillating serve ages. Per SVR RULE-1 the UV-P is consumed within-initiative by
this artifact.

**UV-P-2** *(mechanism leg)*: `[UV-P: the deployed ASR Lambda's autom8y-core wheel is below 4.14.0, so the offers gate is running the DORMANT branch | METHOD: deferred-to-live-trace-leg (ASR log query for offers_content_axis_unavailable / offer_freshness_axis_dormant) | REASON: the installed wheel version is a deployment fact; the code only establishes the probe and the fallback]`

**DISCHARGED — claim FALSIFIED.** Discharged by elimination against the live staleness
values rather than by log presence (§1): DORMANT is excluded (would read ≤ ~1 h against
an hourly-advancing sidecar; observed 404 825 s), REFUSE is excluded (would read exactly
7 201.0 s). GATE is therefore live, which requires
`detect_content_axis_capability().available == True`, which requires **autom8y-core ≥
4.14.0 installed**. The wheel is current; the axis is live and gating.

**No open UV-P remains for this sprint.** RULE-3 close-gate fail-safe does not fire.

---

## §8 — SVR TUPLES

**SVR-1 — the axis switch and the branch selection**
```yaml
claim: "the ASR offers gate selects among three named dispositions and reaches data_age_seconds only on the fallback branch, so the gated quantity on all six observed ticks is the SDK-derived content age, not the serving-cache entry age"
verification_method: bash-probe
verification_anchor:
  source: "git show origin/main:services/account-status-recon/src/account_status_recon/readiness.py | sed -n '522,556p'"
  command_output_verbatim: "# THE AXIS SWITCH. `data_age_seconds` is reached only on the DORMANT\n        # branch, and only with a disclosure log -- it is a disclosure quantity"
  exit_code: 0
  claim: "origin/main carries a merged three-branch disposition switch whose fallback arm is explicitly labelled a disclosure quantity; the working tree at the same path does not carry it (SCAR-2)"
```

**SVR-2 — the combination rule is max-of-ages (= oldest watermark)**
```yaml
claim: "the two offer constituents are combined by taking the LARGER age, which is arithmetically the age of the OLDER of the two pool watermarks, pinning the gate to whichever pipeline pool has been quiet longest"
verification_method: bash-probe
verification_anchor:
  source: "git show origin/main:services/account-status-recon/src/account_status_recon/readiness.py | sed -n '355,370p'"
  command_output_verbatim: "content_age_seconds=max(ages),"
  exit_code: 0
  claim: "the combination is a max over per-constituent ages, and the adjacent disclosure string names the intent as taking the oldest"
```

**SVR-3 — the activating pool is five sections wide**
```yaml
claim: "the classification the gate was pinned to for five days spans only the new-launch funnel, a structurally low-traffic set, which is why an ordinary quiet stretch reads as multi-day staleness"
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/models/business/activity.py"
  line_range: "L209-L215"
  marker_token: "\"activating\": {\n            \"ACTIVATING\",\n            \"LAUNCH ERROR\",\n            \"IMPLEMENTING\",\n            \"NEW LAUNCH REVIEW\",\n            \"AWAITING ACCESS\",\n        },"
  claim: "the classifier group named by the fetcher's second query resolves to exactly five section names, all belonging to the offer-launch funnel"
```

**SVR-4 — classification is expanded to a section-name IN predicate by the engine**
```yaml
claim: "the producer narrows the returned rows to the classifier's section-name set before the SDK derives a watermark, so the content axis is scoped by classification group rather than by the whole frame"
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/query/engine.py"
  line_range: "L153-L161"
  marker_token: "classification_expr = (\n                pl.col(\"section\").str.to_lowercase().is_in(list(classification_sections))"
  claim: "the row set the SDK derives its watermark from is the classification-filtered subset, which is what makes the derived quantity a per-pool activity measure"
```

**SVR-5 — the 20 null-watermark sections are empty-by-construction**
```yaml
claim: "every null-watermark offer section is a coherently empty section rather than one where watermark tracking failed, which is why hash-only detection is complete verification there and why the bypass is not this incident's mechanism"
verification_method: bash-probe
verification_anchor:
  source: "python3 -c \"import hashlib;print(hashlib.sha256('|'.join(sorted([])).encode()).hexdigest()[:16])\""
  command_output_verbatim: "e3b0c44298fc1c14"
  exit_code: 0
  claim: "the constant computed by the builder's empty-GID-set helper equals the gid_hash observed on all 20 null-watermark sections in the live manifest, establishing they hold no tasks"
```

**SVR-6 — the substrate-v2 freshness core has no live consumer**
```yaml
claim: "the frozen Seam-1 freshness primitives are unreachable from the serving path, so the v2 lane's five-day-old proof has no producer keeping it current and its declared SLA is unenforced"
verification_method: bash-probe
verification_anchor:
  source: "grep -rn 'from autom8_asana.substrate' src/ | grep -v '^src/autom8_asana/substrate/' ; grep -rn 'built_from_live_at' src/ | grep -v '^src/autom8_asana/substrate/'"
  command_output_verbatim: ""
  exit_code: 1
  claim: "both probes return empty: no module outside the substrate package imports it, and the v1 path never references the v2 freshness instant"
```

**SVR-7 — the population floor is breached on a frame that is nonetheless persisted**
```yaml
claim: "a below-floor offer frame is durably written every warm because the converged gate's backstop refusal is conditioned on an absent decision, and the recorded decision is present"
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/section_persistence.py"
  line_range: "L905"
  marker_token: "if population_degraded is True and write_decision is None and not df.is_empty():"
  claim: "the guard requires a null decision, so the live WRITE_AS_IS decision bypasses it while the degraded flag is true, and save_dataframe proceeds"
```

**SVR-8 — the ACTIVE-section exclusion inference is a snapshot-vs-historical artifact**
```yaml
claim: "the ACTIVE section could not have participated in the 12:01Z or 16:01Z tick derivations because its watermark postdates them, so its apparent exclusion is an artifact of comparing a current manifest against historical ticks rather than a property of the derivation"
verification_method: bash-probe
verification_anchor:
  source: "python3 back-computation of tick REF vs section watermarks (see §2.3 table)"
  command_output_verbatim: "tick 2026-08-17T16:01:11+00:00  obs=448025.9  back-ref=2026-08-12T11:34:05.100000+00:00  d(IMPL)=+24.4s  d(ACTG)=-468422.5s  age_if_ACTsection=-2558.7"
  exit_code: 0
  claim: "the implied age for that section at that tick is negative, which is impossible for a real watermark and therefore falsifies its participation; the residual against the IMPLEMENTING watermark is the serve-versus-sample lag"
```

**SVR-9 — two ticks four hours apart resolve to the same anchor, and the window contained zero pass-eligible ticks**
```yaml
claim: "the reference stepped once and re-pinned rather than resuming advance, and the single business event in the observed window missed every tick's pass window, so a passing tick was not merely improbable but observably absent"
verification_method: bash-probe
verification_anchor:
  source: "python3 back-computation over the five observed ticks and the 2026-08-12T11:33:40.703Z -> 2026-08-18T04:25Z window (see §2.3 and §6.4d)"
  command_output_verbatim: "00:01Z back-ref vs 04:01Z back-ref spread: +19.47s  (two ticks 4h apart)\nevent 21:41:07.639 -> 00:01Z tick lead time: 8400s  (pass bar 3600, abort bar 7200)\npass-eligible wall-clock = 1 x 3600s = 0.73% of window\nticks in window (4h cadence): 34.2"
  exit_code: 0
  claim: "measurements taken four hours apart differ by twenty seconds, which is only explicable if the underlying instant is identical; and the lone qualifying event preceded its next sample by more than twice the abort bar"
```

---

## §9 — WHAT THIS DIAG DOES NOT CLAIM

- It does **not** claim R-3 is resolved. §4 R-3 states a contradiction and names the
  re-probe. No verdict rests on it.
- It does **not** claim the offer frame's *contents* are correct. R-2 says the opposite:
  the frame is below the population floor. A correct freshness axis over a below-floor
  frame is still a wrong answer.
- It does **not** propose or make any production change. No threshold touched,
  `readiness.py` untouched, no file in either repo modified by this sprint except this
  artifact and the architect's own memory.
- It does **not** rule on §1.2 vs §1.6. The operator ruled (§3); this DIAG records the
  ruling and supplies concordant mechanism evidence.
- It does **not** forecast a pass rate. The §6.4e rate estimate rests on **n = 1** and is
  labelled `[TACTICAL | WEAK]` on purpose. The reachability verdict rests on the
  **deterministic count** at §6.4d (zero pass-eligible ticks out of ~34 observed), not on
  the extrapolation. If the reachability conclusion is challenged, challenge §6.4d.
- It does **not** claim the sales team is underperforming. Five days without a
  new-launch-funnel task edit may be entirely normal for this business. **That is the
  point**: a gate whose PASS condition is indistinguishable from a business KPI is
  measuring the wrong thing regardless of what the KPI reads.

---

*Authored by 10x-dev/architect, SPR-A1 MECHANISM leg, reconciled against the
principal-engineer LIVE PRODUCER leg across two trace deliveries. Evidence grade STRONG
on the mechanism: two disjoint legs converging, **five ticks fitting across two distinct
anchors** (the second anchor created under observation, after the diagnosis began), one
code prediction confirmed (`fetched_rows=0` still stamps a fresh watermark), and four
hypotheses falsified — three of mine (M1 PRESERVE-latch, M2 plane-split, M3 immortal
memory entry) and one of the live leg's (the ACTIVE-section exclusion inference). k1-ib1
bar met: every verdict-bearing claim stands on the real emitter, not a reconstruction.*
