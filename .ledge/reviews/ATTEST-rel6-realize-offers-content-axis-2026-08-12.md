---
type: review
status: accepted             # Phase 0 + Phase 1 COMPLETE (00:00Z and 04:00Z ticks judged)
artifact_id: ATTEST-rel6-realize-offers-content-axis-2026-08-12
crusade: offers-freshness-axis-contract (formerly offers-false-staleness-cure)
initiative: offers-freshness-axis-contract — S5 LAND + REALIZE
handoff_item: REL-6
attester: eunomia/verification-auditor (rite-disjoint; borrowed co-seat in the releaser rite)
attester_rite: eunomia
target_initiative_owner_rite: releaser (execution) / 10x-dev (origin)
date: 2026-08-12
clock_discipline: all timestamps UTC, bound by `date -u` / epoch-UTC log queries (CEST-mislabel scar)
evidence_ceiling: STRONG on mechanism (Phases 0+1, N=3 organic/near-organic ticks); MODERATE on forward-looking analysis (§5, §7.6)
method: >
  Read-only against all infrastructure. No Lambda invoked. No request issued to the asana
  serve path — corroboration is LOGS-ONLY (CloudWatch filter-log-events + describe reads).
  No threshold touched. L4 keep-warm REFUSED throughout (the decayed cache IS the control arm).
  Every receipt below re-derived by my own reads; nothing inherited from the OBS artifact,
  which I treated as a claim to be corroborated or refuted.
scope:
  code: origin/main @ c21cab9d8317f7b2755ed742506489a23e9e3b8b (autom8y monorepo)
  running_image: 696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/account-status-recon@sha256:98423e5d522f1b119d3ead37d51c41b0864e8043f6943c5dbfd41afb0be8e8e8
  consumer_logs: /aws/lambda/autom8y-account-status-recon
  producer_logs: /ecs/autom8y-asana-service
source_artifacts:
  - .sos/wip/release/IGNITION-rel5-fixn-admit-2026-08-12.md
  - .ledge/decisions/RULING-operator-s5-gate-interview-2026-08-11.md
  - .sos/wip/release/OBS-tick-2000Z-first-gate-observation-2026-08-11.md
  - .ledge/handoffs/HANDOFF-offers-cure-to-releaser-release-2026-08-11.md
  - .sos/wip/release/RECEIPT-c-null-deployed-2026-08-11.md
---

# ATTEST — REL-6 REALIZE, offers content-freshness axis

Rite-disjoint attestation under the operator's strict R-2 bar. Two phases:
**Phase 0** is a MECHANISM attestation on the deploy-adjacent 20:00Z tick and carries
**ZERO REALIZE weight by rule**. **Phase 1** is the REALIZE judgment on the qualifying
organic ticks — **two** of them, 2026-08-12T00:00Z and 2026-08-12T04:00Z.

**HEADLINE:** both organic ticks are `REALIZED-MECHANISM-BUT-SUBSTRATE-STALE`. Neither is
DORMANT (no HALT tripwire). Neither is REFUSE. Neither is a PASS. §7.5 scores — and
fails — my own pre-registered forecast, and §7.6 states what the miss teaches.

---

## 0. The operator rulings this attestation is bound by (VERBATIM)

Reproduced verbatim from `.ledge/decisions/RULING-operator-s5-gate-interview-2026-08-11.md`.

### R-2 · Acceptance bar ("actually fixed") — **RATIFIED (strict)** (`:24-31`)

> ## R-2 · Acceptance bar ("actually fixed") — **RATIFIED (strict)**
> Verbatim: "Strict definition" → confirmed post-disclosure.
> Victory requires a scheduled run whose pass demonstrably comes FROM the new
> check (disposition=GATE on the content axis), cross-checked against the
> producer's same-trace record, with deploy-adjacent and old-fallback passes
> worth zero, no synthetic warming, no threshold moved. Matches the
> change-warden's honest REALIZE predicate.

### R-4 · Approach reversal triggers — **RATIFIED as REVIEW-PROMPTS** (`:39-42`)

> ## R-4 · Approach reversal triggers — **RATIFIED as REVIEW-PROMPTS**
> Any of: a false-fresh pass · a refusal storm on healthy runs · the
> edit-timestamp column proving unreliable → triggers a REVIEW, not an automatic
> halt. (Operator explicitly chose review-prompts over halt-triggers.)

### R-8 · Post-deploy rollback triggers — **RATIFIED (asymmetric)** (`:68-71`)

> ## R-8 · Post-deploy rollback triggers — **RATIFIED (asymmetric)**
> Roll back on: serving-path latency/availability regression OR new
> refusals/errors at the consuming job. Other unexpected-but-harmless behavior
> deltas → review first, not rollback. Asymmetry explicitly confirmed.

---

## 1. Substrate identity — what code actually ran

| Fact | Value | Probe |
|---|---|---|
| Running image tag | `…/autom8y/account-status-recon:c21cab9` | `aws lambda get-function --function-name autom8y-account-status-recon` |
| Resolved digest | `sha256:98423e5d522f1b119d3ead37d51c41b0864e8043f6943c5dbfd41afb0be8e8e8` | same |
| Lambda LastModified | `2026-08-11T19:57:54.000+0000` | same |
| `OFFER_STALENESS_THRESHOLD_SECONDS` | `3600` — **UNMOVED** | same |
| `OFFER_AXIS_FUTURE_SKEW_ALLOWANCE_SECONDS` | unset (code default governs) | same |

The tag `c21cab9` is the short form of merge commit
`c21cab9d8317f7b2755ed742506489a23e9e3b8b`, and the digest equals the one in
`RECEIPT-c-null-deployed-2026-08-11.md`. **The code I read at `origin/main` is the code
that ran.** Deploy landed 19:57:54Z; the tick under Phase 0 started 20:00:42.743Z — **3 m 27 s
later. Deploy-adjacent CONFIRMED; zero REALIZE weight by R-2.**

---

## 2. PHASE 0(a) — the emission contract, re-derived from code

**CLAIM M-1 (CONFIRMED): clean-GATE is the ONLY silent branch of the axis switch.**
Grade: **STRONG** (direct read of the deployed commit; two-sided — I name what each
non-GATE branch would have emitted and what value it would have carried).

`services/account-status-recon/src/account_status_recon/readiness.py` @ `c21cab9d`:

| Branch | Line | Log emitted | Level | `offer_staleness` value |
|---|---|---|---|---|
| **GATE, unclamped** | `:526-527` | **none** | — | `decision.content_age_seconds` |
| GATE, clamped | `:528-536` | `offer_freshness_axis_clamped` | warning | `decision.content_age_seconds` |
| REFUSE | `:537-550` | `offer_freshness_axis_refused` | **error** | `refusal_staleness_seconds()` = deterministic sentinel |
| DORMANT (`else`) | `:551-557` | `offer_freshness_axis_dormant` | **info** | `data_age_seconds` (serving-cache entry age) |

Two additional silent-looking paths, both closed:

- **Capability-absent (R-6 honest-quiet fallback)** — `fetcher.py:449-462` probes the installed
  SDK and, when absent, emits `offers_content_axis_unavailable` (warning, const at
  `fetcher.py:285`) **and** produces records with the axis keys OMITTED
  (`fetcher.py:412-415`), which `combine_offer_axis` reads as DORMANT
  (`readiness.py:225-232`) → the dormant log fires too. So capability-absence is
  **doubly loud**, never silent.
- **offers fetch failed** — the whole `if offers and offers.success:` block
  (`readiness.py:489`) is skipped, so no offers `SourceMetadata` is appended and **no
  offers `readiness_check_*` event can exist at all**. The presence of an offers
  `readiness_check_fail` therefore *proves* the block was entered.

**Sentinel arithmetic (the REFUSE falsifier):**
`refusal_staleness_seconds` = `threshold × warn_multiplier + 1.0` (`readiness.py:387-394`,
`REFUSAL_STALENESS_OVERSHOOT_SECONDS = 1.0` at `:384`) = `3600 × 2.0 + 1.0` = **exactly 7201.0**.

**Combination rule:** `combine_offer_axis` returns `content_age_seconds=max(ages)`
(`readiness.py:361-365`) — the **OLDEST** constituent watermark. Load-bearing for §5.

**SDK derivation** (`sdks/python/autom8y-core/src/autom8y_core/helpers/asana_freshness.py`):
`watermark = max(parsed)` over the `last_modified` column of the **returned rows**
(`:464`), `age_seconds = (reference - watermark).total_seconds()` (`:465`), returned with
`disposition=GATE` (`:512-517`). GATE additionally requires: axis opted-in (`:370-387`
else DORMANT), rows non-empty (`:396-403` else REFUSE), column present on **every** row
(`:407-424` else REFUSE), not all-null (`:427-441` else REFUSE), every value parseable
(`:444-462` else REFUSE), and `returned_count == total_count` (T-GUARD, `:467-499` else
REFUSE). `CONTENT_AXIS_COLUMN = "last_modified"` (`:63`).

**Verdict on the OBS artifact's inference (a): CORROBORATED, and strengthened** — the OBS
called it "by elimination"; the code shows the elimination set is *closed* (four branches,
three loud, one silent) and that two of the three loud branches also carry
numerically-distinct staleness values that can be tested independently of log presence.

---

## 3. PHASE 0(b) — the 20:00Z tick, re-pulled

Query: `aws logs filter-log-events --log-group-name /aws/lambda/autom8y-account-status-recon
--start-time 1786478280000 --end-time 1786479000000` (= 2026-08-11T19:58:00Z → 20:10:00Z, epoch UTC).
**20 events returned, single stream `2026/08/11/[$LATEST]bc194a06c4074dbcb676db4b967951aa`,
no `nextToken` — the pull is complete.**

Invocation `f418d9a9-a60f-4927-9457-e98ac49730be`, trace `c91369947c65a6defe632e04f2d8b94d`.

**The offers event (verbatim):**

```json
{"source": "offers", "staleness_seconds": 83123.287954, "threshold_seconds": 3600,
 "abort_threshold_seconds": 7200.0, "event": "readiness_check_fail", "service": "unknown",
 "level": "error", "trace_id": "c91369947c65a6defe632e04f2d8b94d",
 "span_id": "51c8564035d3da61", "timestamp": "2026-08-11T20:01:22.917682Z"}
```

followed at `20:01:22.917764Z` by
`readiness_gate_abort` — *"Source 'offers' is 1385 min stale (abort threshold: 120 min). Aborting reconciliation."*
Sibling sources PASSED: billing `290.599426 / 7200`, campaigns `137 / 3600`.

**Axis-event absence (the negative receipt):** zero occurrences of
`offer_freshness_axis_dormant`, `offer_freshness_axis_refused`, `offer_freshness_axis_clamped`,
or `offers_content_axis_unavailable` anywhere in the 20-event window.

**Info-level flow demonstrably alive** (so the absence is real, not a level filter):
`handler_invoked` (info, 20:00:46.225), `reconciliation_started` (info, 20:00:46.226),
`billing_coverage_disclosed` (info, 20:01:22.917126), `readiness_check_pass` ×2 (info,
20:01:22.9175/.9176), `slack_post_attempt` (info, 20:01:22.917820),
`slack_post_entered` (info), `report_posted` (info, 20:01:23.107883).
The axis log — had one fired — would sit **between** `billing_coverage_disclosed` (.917126)
and the first `readiness_check_pass` (.917554), a 428 µs gap that is populated on both sides.

**CLAIM M-2 (CONFIRMED): disposition = GATE, clean (unclamped). Grade: STRONG.**
Four independent legs, three of them numeric rather than absence-based:

| Leg | Hypothesis killed | How |
|---|---|---|
| L1 | DORMANT, REFUSE, CLAMPED | all three log lines absent with info flow alive |
| L2 | REFUSE | value would be **exactly 7201.0**; observed 83123.287954 |
| L3 | DORMANT | value would be `data_age_seconds`; producer logged it as **6581.2 s** same-trace (§4) |
| L4 | REFUSE (T-GUARD) | GATE's hardest precondition independently satisfied: producer logged `returned_count == total_count` on **both** constituents (67/67, 48/48) |

---

## 4. PHASE 0(c) — SAME-TRACE PRODUCER CORROBORATION (the decisive leg)

Producer log group discovered: **`/ecs/autom8y-asana-service`**. **The trace propagates
across the service boundary** — 843 events in `/ecs/autom8y-asana-service` carry
`trace_id c91369947c65a6defe632e04f2d8b94d` in the 20:00-20:06Z window.

Producer-side receipts, all on the ASR's trace:

| Time (UTC) | Event | Payload |
|---|---|---|
| 20:01:21.269729 | `dataframe_cache_memory_lkg_serve` | `entity_type=offer`, `row_count=4192`, **`age_seconds=6581.2`**, `freshness="stale"` |
| 20:01:21.269850 | `swr_refresh_triggered` | `entity_type=offer` |
| 20:01:21.283793 | `swr_build_started` | `entity_type=offer` |
| 20:01:21.403563 | `query_rows_complete` | `classification=active`, **`returned_count=67`, `total_count=67`** |
| 20:01:21.459557 | `dataframe_cache_memory_lkg_serve` | 2nd constituent, `age_seconds=6581.3` (same LKG frame) |
| 20:01:21.561198 | `query_rows_complete` | `classification=activating`, **`returned_count=48`, `total_count=48`** |
| 20:01:22.011986 | httpx | `GET …/tasks?…&section=1202496785025459&modified_since=2026-08-10T20:55:58.289000+00:00&limit=2` |
| 20:02:46.492737 | `final_artifacts_written` | `entity_type=offer`, `row_count=4193`, `watermark=2026-08-11T20:01:41.297583+00:00` |

### 4.1 The question the charge asked: content age, or cache age?

**Answer: CONTENT age. Decisively.**

`data_age_seconds` — the quantity the DORMANT branch would have gated on — is defined in the
producer as the **cache entry's `created_at` age**:
`src/autom8_asana/cache/integration/dataframe_cache.py:1145` →
`age = (datetime.now(UTC) - entry.created_at).total_seconds()`, surfaced at `:1156` as
`data_age_seconds=round(age, 1)` and threaded into the query response meta at
`src/autom8_asana/query/engine.py:539`. It is the same object logged as `age_seconds` on the
LKG-serve line. **Its value on this trace was 6581.2 (active) / 6581.3 (activating).**

Three candidate quantities, all falsified against the observed 83123.287954:

| Candidate | Value on this trace | Match? |
|---|---|---|
| cache-entry age (`data_age_seconds`, the DORMANT quantity) | **6581.2** | NO |
| serving frame's build watermark (`2026-08-11T18:07:42.118782Z`) age | **6819.46** | NO |
| REFUSE sentinel (`3600×2.0+1.0`) | **7201.0** | NO |
| **content watermark age (`max(last_modified)` over returned rows)** | **83123.287954** | **YES** |

### 4.2 The microsecond-exact cross-stream identity

Inverting the reported figure against the code's own definition of the reference instant
(`fetcher.py:533-540`: *"ONE reference instant for both constituents, captured AFTER both
responses are in hand"*):

```
content_watermark = axis_now − 83123.287954
```

Solving with `content_watermark = 2026-08-10T20:55:58.289000+00:00`:

```
axis_now = 2026-08-11T20:01:21.576954Z
```

- That instant lands **+15.756 ms after** the producer's `query_rows_complete` for the
  **second** (activating) constituent at `20:01:21.561198Z` — exactly where `fetcher.py:540`
  says `axis_now` is captured, and 173 ms after the first.
- `2026-08-10T20:55:58.289000+00:00` is **byte-identical** to the `modified_since` value the
  producer emitted **on this same trace** at `20:01:22.011986Z` for section
  `1202496785025459`.
- And that `modified_since` value **is** `max(last_modified)` over that section's rows, by
  code: the per-section persisted watermark is computed as
  `max_val = section_df["last_modified"].max()`
  (`src/autom8_asana/dataframes/builders/progressive.py:1727-1730`, mirrored at
  `src/autom8_asana/dataframes/builders/freshness.py:645-648`) and is emitted verbatim as the
  probe's `modified_since` at `src/autom8_asana/dataframes/builders/freshness.py:299-305`.
- And `last_modified` is the Asana task's own `modified_at`
  (`src/autom8_asana/dataframes/extractors/base.py:481-493`) — a **genuine content-edit
  timestamp**, not a build stamp.

**CLAIM M-3 (CONFIRMED): the served content watermark at the 20:00Z tick was
`2026-08-10T20:55:58.289000Z`, and `83123.287954` is `decision.content_age_seconds` —
a content-watermark age. Grade: STRONG.**

The producer's own independently-computed content watermark and the consumer's derived one
agree **to the microsecond**, across two services, two repositories, and two log streams, on
one trace. The compound coincidence required for this to be spurious (exact µs equality of the
watermark *and* an implied `axis_now` landing 15.8 ms after the second query's server-side
completion) is not credible.

**Consequence:** the OBS artifact's derived watermark (`≈2026-08-10T20:56:20Z`) was correct to
within ~22 s; its inference class was correct; its evidence grade (`moderate-inferred`,
elimination-only, no producer corroboration) was honest and is now **superseded by STRONG**.
No part of the OBS artifact is refuted.

### 4.3 Did the 20:01Z request trigger an SWR refresh? — YES

`swr_refresh_triggered` at `20:01:21.269850Z`; `swr_build_started` at `.283793Z`;
`build_result_classified` `status=success, sections_probed=34, sections_delta_updated=1,
total_time_ms=85199.81`; `final_artifacts_written entity_type=offer` at `20:02:46.492737Z`
with `row_count=4193` and `watermark=2026-08-11T20:01:41.297583+00:00`.

**This is the SWR trap, receipted:** the ASR was served the **stale LKG frame** (built
18:11:40Z) and only *then* triggered the rebuild that completed **85 s after its own read**.
The tick can never see the frame its own read produces. This governs the 00:00Z substrate
state (§5.3).

The rebuild picked up exactly **one** changed section — `1143843662099256`
(`freshness_delta_section_updated`, `verdict=content_changed`, `delta_tasks=2`,
`final_rows=45`) — **not** section `1202496785025459`, which holds the binding (oldest)
watermark.

---

## 5. PHASE 0(e) — ANALYSIS (NOT a verdict): the structural PASS precondition

> **PARTIALLY FALSIFIED BY PHASE 1 — read §7.5 and §7.6 before relying on this section.**
> §5.4's "the binding cohort has been edit-dormant ~23 h" is **FALSE as a statement about
> edits**: the producer record shows that cohort was edited at `2026-08-11T19:29:37.657`,
> 31 min 44 s BEFORE the 20:00Z tick. §5 mis-attributed a **frame-lag** failure to an
> **edit-dormancy** failure. §5's overnight-quiet finding, its combination-rule finding,
> and its D-5b surfacings all SURVIVE and are re-confirmed; the cadence model does not.
> The corrected model, the corrected first-PASS window, and the corrected D-5b framing are
> at §7.6. Section 5 is left standing verbatim rather than silently rewritten, so the
> correction is auditable.

> Surfaced for operator card **D-5b** per the charge. This section rules on nothing.

### 5.1 The precondition, stated exactly

A tick PASSes iff `content_age ≤ 3600`, where (by `readiness.py:361-365`)

```
content_age = tick_now − MIN( max(last_modified | active rows) ,
                              max(last_modified | activating rows) )   [as captured in the SERVED frame]
```

Because the combination is `max(ages)`, the gate is governed by the **least-recently-edited
of the two cohorts**. Two things must both hold: **(i)** an offer edit inside 3600 s of the
tick **in each cohort**, and **(ii)** an offer-entity frame rebuild between the later edit
and the tick.

### 5.2 Is there non-ASR organic traffic on the offers surface?

Measured: all `entity_type=offer` query events in `/ecs/autom8y-asana-service` over
2026-08-10T18:00Z → 2026-08-11T20:50Z (26.8 h).

| Caller service | Events | Shape |
|---|---|---|
| `8156aa10-9731-464c-bfb2-c85a884d3d11` (**the ASR**) | 14 (7 ticks × 2) | active + activating |
| `f55e4cdd-ab10-4851-b4b8-de98cfe8abeb` | 1 @ 12:20:10Z | full frame, 4192 rows |
| `e1459bc4-0714-4860-8858-593c5c18591a` | 2 @ 13:00:08/09Z | active 67 + activating 48 |

**Non-ASR organic traffic on the offers surface exists but is very sparse: 3 events in 26.8 h,
both inside business hours.** For a 6-minute sample around the tick itself, offers traffic was
**100 % ASR** (the other 81 `query_rows_complete` in that window were `entity_type=project`
from a different caller).

However — and this is the load-bearing correction to the naive "structurally can never pass"
worry — **the offer frame is refreshed independently of queries**, by the cache warmers
(`/aws/lambda/autom8-asana-cache-warmer`, `-bulk`; 73 and 155 starts in the same window,
running around the clock). Offer-entity `final_artifacts_written` puts: **22 in 26.8 h**.

### 5.3 Frame lag at each tick (empirical)

| Tick (UTC) | Last offer frame put before it | Frame lag | (ii) satisfiable? |
|---|---|---|---|
| 2026-08-11T00:00:45 | 2026-08-10T23:43:43 (wm 23:41:00) | 17 min | YES |
| 04:00:46 | 00:02:22 (wm 00:00:34) | 4 h 00 m | NO |
| 08:00:46 | 04:02:16 (wm 03:59:38) | 3 h 58 m | NO |
| 12:00:45 | 11:21:42 (wm 11:20:37) | 39 min | YES |
| 16:00:46 | 15:55:35 (wm 15:53:25) | 5 min | YES |
| 20:01:21 | 18:11:40 (wm 18:07:42) | 1 h 50 m | MARGINAL |

Overnight the offer entity is warmed only sporadically (gaps 00:02→04:02 and 04:02→08:02 are
**empty**), so **the 04:00Z and 08:00Z ticks are structurally incapable of passing**
regardless of edit activity.

### 5.4 Edit cadence on the offers project

From `freshness_probe_complete` / `freshness_delta_section_updated` on project
`1143843662099250` (34 sections) over the same 26.8 h:

- **00:00Z → 10:27Z: eight consecutive probe passes, ALL `{clean: 34}`.** Zero content or
  structure change overnight.
- Change events cluster in business hours: 10:27 (1 section), 17:04 (2), 18:06/18:07 (2),
  19:06 (2), 20:01 (1), 20:05 (1) — and on the 10th at 20:01 (5) and 21:05 (2).
- Changes are concentrated in a handful of sections; `1143843662099256` accounts for 6 of the
  11 change events.
- **The binding section `1202496785025459` last changed at the 2026-08-10T21:05 probe pass**
  (`structure_changed`, `delta_tasks=2`), leaving watermark `2026-08-10T20:55:58.289`.
  Every probe since — 20 passes over ~23 h — has returned it CLEAN.
  **[FALSIFIED IN PART @ §7.5 — that section changed again at the 2026-08-11T21:05 probe
  (watermark → `2026-08-11T20:37:11.719`), and the OTHER cohort's section
  `1143843662099256` changed at `2026-08-11T19:29:37.657`, before the 20:00Z tick. The
  binding constituent SWAPPED. See §7.5/§7.6.]**

### 5.5 Realistic first-PASS window

**Candidate ticks are 12:00Z, 16:00Z and (marginally) 00:00Z / 20:00Z — never 04:00Z or 08:00Z.**
On those candidate ticks condition (ii) is routinely met (frame lag 5–40 min). Condition (i)
is the binding one, and it is much harder than it looks, because `max(ages)` requires an edit
**in both cohorts** inside the same pre-tick hour. Over the full 26.8 h observed:

- **zero ticks would have passed on the content axis**;
- one cohort has been edit-dormant for ~23 h continuously.

**Honest statement of the window:** a first PASS is *possible* at a 12:00Z or 16:00Z tick on a
business day on which both the active and the activating offer cohorts are touched within the
same hour before the tick. On the observed cadence that is an **occasional coincidence, not a
scheduled event** — plausibly days away, and not guaranteed to recur on a fixed period. I do
not put a probability on it: one 26.8 h window is not enough to estimate a rate, and I will not
synthesize one.

### 5.6 Two facts the operator should hold alongside D-5b (surfaced, not ruled)

**(1) The threshold's referent changed; its value did not.** `OFFER_STALENESS_THRESHOLD_SECONDS=3600`
formerly asked *"was the serving cache built within the last hour?"* — a question whose natural
scale is minutes-to-hours and which the system was engineered to satisfy. It now asks
*"was an offer row edited within the last hour?"* — a question whose natural scale is set by the
business, not the platform, and which the observed data says is normally answered "no". R-11
deliberately deferred this ("Both one-hour numbers stand as-is", ruling `:85-89`); this is the
empirical substrate that decision was deferred to await. **The number is unmoved and must stay
unmoved for the REALIZE test; the observation is that its meaning moved underneath it.**

**(2) There is a behaviour delta at the consuming job, and R-8 names that class.**
Baseline from the ASR's own logs (2026-08-09T00:00Z → 2026-08-11T16:00Z, old clock): 10 ticks
PASSED (offers staleness 834.9–3087.8 s), 4 ABORTED (9129.9 / 10083.3 / 14303.4 / 14309.7 s).
Aborts therefore **pre-date** the cure. But at the 20:00Z tick the old clock would have reported
≈6581 s — above threshold (warn) yet **below** the 7200 s abort line, so the job would have
**proceeded**; the content axis reported 83123 s and the job **aborted**. Combined with §5.5,
the expected steady state is *abort on every tick until both cohorts are edited within the same
hour*.

R-8 verbatim: *"Roll back on: serving-path latency/availability regression OR new
refusals/errors at the consuming job. Other unexpected-but-harmless behavior deltas → review
first, not rollback."* R-4 verbatim names *"a refusal storm on healthy runs"* as a **review**
prompt. **I surface this as squarely inside the R-4 review-prompt class and adjacent to the
R-8 trigger class. I do NOT recommend rollback — that adjudication is the operator's, and the
abort is the honest control-arm behaviour this wave deliberately preserved (L4 keep-warm
REFUSED).** Serving-path latency/availability: **no regression observed** — the producer served
both constituents in 2.89 ms and 3.43 ms and the ASR's total duration (47.2 s) is dominated by
a pre-existing token-exchange retry storm (4 warnings, 20:00:58→20:01:10Z) unrelated to this change.

### 5.7 One residual defect class worth registering (mechanism, not verdict)

`src/autom8_asana/dataframes/builders/freshness.py:293-299` documents that null-watermark
sections (**"~21/34 offer … per QA 2026-05-27"**) bypass the `modified_since` content check
entirely and retain hash-only detection. In-place edits that preserve a section's GID set are
therefore **invisible** in those sections, so the served `last_modified` can lag a real edit.
Direction of error: the gate reports content **older** than truth — it errs **stale, never
fresh**. That is the safe direction and is not a false-fresh risk (R-4's first trigger),
but it does mean §5.5's first-PASS window is if anything *further out* than the edit cadence
alone implies. Registered for D-5b; no action proposed here.

---

## 6. PHASE 0(d) — PRELIMINARY MECHANISM ATTESTATION

> **MECHANISM-ONLY. TICK WEIGHT: ZERO (deploy-adjacent — image live 19:57:54Z, invocation
> 20:00:42.743Z, Δ = 3 m 27 s). This section establishes NOTHING about REALIZE, by R-2.**

**Verdict (three-valued vocabulary): `REALIZED-MECHANISM-BUT-SUBSTRATE-STALE`
— mechanism half only, carrying zero REALIZE weight.**

| # | Claim | Verdict | Grade |
|---|---|---|---|
| M-1 | Clean-GATE is the only silent branch; DORMANT/REFUSE/clamp all log; capability-absence is doubly loud | CONFIRMED | STRONG |
| M-2 | The 20:00Z tick's disposition was **GATE (clean)** — the content axis is LIVE in production | CONFIRMED | STRONG |
| M-3 | `83123.287954` is `content_age_seconds`; watermark = `2026-08-10T20:55:58.289000Z` | CONFIRMED | STRONG |
| M-4 | Producer-side same-trace corroboration obtained, µs-exact, cross-service | CONFIRMED | STRONG |
| M-5 | Threshold unmoved (3600), no synthetic warm, no manual invoke, L4 keep-warm still REFUSED | CONFIRMED | STRONG |
| M-6 | The substrate is genuinely stale: the binding cohort has been edit-dormant ~23 h | CONFIRMED | STRONG |
| M-7 | The DORMANT-on-first-tick HALT tripwire is NOT in play | CONFIRMED | STRONG |
| E-1 | First-PASS window analysis (§5) | ANALYSIS | MODERATE (single 26.8 h window) |

**What this does NOT establish:** REALIZE. Zero weight by rule. The 00:00Z tick owns that.

**Falsifiers I would accept:** an `offer_freshness_axis_*` event in the 19:58–20:10Z window
that my pull missed (pull was complete, no `nextToken`, single stream); a producer
`data_age_seconds` equal to 83123.29 (it was 6581.2/6581.3); or a section watermark other than
`2026-08-10T20:55:58.289000` reconciling the arithmetic (none does, to the microsecond).

---

## 7. PHASE 1 — the REALIZE verdict (00:00Z and 04:00Z ticks)

**Completed 2026-08-12T06:0xZ, retrospectively, on logs.** Disclosure first: the
2026-08-11T21:06Z background waiter armed for 00:02:30Z was **KILLED** before it fired
(harness task `b93z6qvwm`, terminal status `killed`), so no re-invocation occurred and §7
sat PENDING until the coordinator re-dispatched at ~06:05Z. **Consequence for the evidence:
none.** Both ticks are cron-driven and were already complete and immutable in CloudWatch;
judging them retrospectively from logs is identical in kind to judging them at 00:02Z, and
it delivered a *second* organic tick (04:00Z) that the original single-tick plan would not
have had. **Consequence for process: recorded as a real miss** — a parked verification that
depends on a live process surviving 3 h is fragile; the durable form is a re-dispatch at the
target time, which is what happened.

### 7.0 The two ticks, re-pulled

Query: `aws logs filter-log-events --log-group-name /aws/lambda/autom8y-account-status-recon
--start-time 1786492680000 --end-time 1786508100000` (= 2026-08-11T23:58:00Z →
2026-08-12T04:15:00Z, epoch UTC). **32 events, two streams, no `nextToken` — pull complete.**

| | tick A | tick B |
|---|---|---|
| Scheduled | **2026-08-12T00:00Z** | **2026-08-12T04:00Z** |
| Invocation | `aba84962-67f5-458d-969b-c224eb8ded7a` | `d095e10c-a5bf-4cd6-babb-defa3b516e29` |
| Trace | `a0dc4a5e259e65229ee3d779764322b9` | `1adaac49dcdcb50c16cf63a6800590d0` |
| Log stream | `…983b5e9a17d64bc8b203998005dbaa64` | `…a9fba352d4be40f381af15976b37f5a7` |
| offers `staleness_seconds` | **16269.568696** | **30668.480824** |
| threshold / abort | 3600 / 7200.0 | 3600 / 7200.0 |
| `readiness_gate_abort` | "271 min stale" @00:01:02.373071Z | "511 min stale" @04:01:04.875027Z |
| billing | PASS 282.764908 / 7200 | PASS 290.184150 / 7200 |
| campaigns | PASS 892 / 3600 | PASS 784 / 3600 |
| Deploy-adjacent? | **NO** — 4 h 03 m after image live | **NO** — 8 h 03 m after image live |

Verbatim, tick A:

```json
{"source": "offers", "staleness_seconds": 16269.568696, "threshold_seconds": 3600,
 "abort_threshold_seconds": 7200.0, "event": "readiness_check_fail", "level": "error",
 "trace_id": "a0dc4a5e259e65229ee3d779764322b9", "span_id": "e49e5a36839e0a83",
 "timestamp": "2026-08-12T00:01:02.372968Z"}
```

Verbatim, tick B:

```json
{"source": "offers", "staleness_seconds": 30668.480824, "threshold_seconds": 3600,
 "abort_threshold_seconds": 7200.0, "event": "readiness_check_fail", "level": "error",
 "trace_id": "1adaac49dcdcb50c16cf63a6800590d0", "span_id": "ee425834e15d70db",
 "timestamp": "2026-08-12T04:01:04.874920Z"}
```

**The coordinator's raw fact is independently CONFIRMED** (invocation id, trace id,
timestamp, value, thresholds, abort text, and both sibling PASSes all match my own pull).

### 7.1 DORMANT and REFUSE excluded POSITIVELY, not merely by absence

Absence leg (mechanical, not eyeballed): a regex sweep for
`offer_freshness_axis_dormant|offer_freshness_axis_refused|offer_freshness_axis_clamped|offers_content_axis_unavailable|dormant|refus|clamp`
over **all 32 events returns 0 hits**. Info-level flow is alive on **both** invocations —
7 info events each (`handler_invoked`, `reconciliation_started`, `billing_coverage_disclosed`,
`readiness_check_pass` ×2, `slack_post_attempt`, `slack_post_entered`, `report_posted`).
Level census across the pull: 14 info, 2 error, 4 warning.

Positive exclusion legs, per §2's emission contract, using numbers rather than silence:

| Hypothesis | Would have produced | Tick A observed | Tick B observed | Excluded |
|---|---|---|---|---|
| **REFUSE** | exactly **7201.0** (`readiness.py:387-394`, `3600×2.0+1.0`) | 16269.568696 | 30668.480824 | YES, numerically |
| **DORMANT** | `data_age_seconds` = cache `created_at` age, logged same-trace by the producer | **6619.6** | **6584.6** | YES, numerically |
| **GATE, clamped** | a `offer_freshness_axis_clamped` warning | absent | absent | YES |
| **T-GUARD REFUSE** | `returned_count != total_count` on either constituent | **68/68** and **48/48** | **68/68** and **48/48** | YES, producer-logged |
| offers fetch failed | no offers `readiness_check_*` at all (`readiness.py:489`) | event present | event present | YES |

**No refusing constituents to report — REFUSE did not fire on either tick.**
**No DORMANT disposition on either tick — the HALT+escalate tripwire is NOT triggered.**

### 7.2 Same-trace producer corroboration — microsecond-exact, on both ticks

Producer log group `/ecs/autom8y-asana-service`, filtered on each trace id
(911 and 912 events respectively; trace propagates across the service boundary on both).

| Producer receipt | Tick A (trace `a0dc4a5e…`) | Tick B (trace `1adaac49…`) |
|---|---|---|
| `dataframe_cache_memory_lkg_serve` | @00:00:46.797723Z `age_seconds=6619.6` (2nd: 6619.9) | @04:00:45.605439Z `age_seconds=6584.6` (2nd: 6585.0) |
| `query_rows_complete` active | @00:00:47.023322Z **68/68** | @04:00:45.750978Z **68/68** |
| `query_rows_complete` activating | @00:00:47.216531Z **48/48** | @04:00:46.130648Z **48/48** |
| `swr_refresh_triggered` | @00:00:46.797818Z | @04:00:45.605541Z |
| served frame `dataframe_cache_put` | @2026-08-11T22:10:27.470644Z, wm `2026-08-11T22:05:06.294045Z` | @2026-08-12T02:11:01.185268Z, wm `2026-08-12T02:05:07.888329Z` |
| section `1143843662099256` persisted watermark | `2026-08-11T19:29:37.657000+00:00` | `2026-08-11T19:29:37.657000+00:00` |

Inverting each reported figure against `fetcher.py:533-540` (`axis_now` captured after both
responses are in hand), **with the SAME solved watermark on both ticks**:

```
W = 2026-08-11T19:29:37.657000+00:00

tick A:  axis_now = W + 16269.568696 = 2026-08-12T00:00:47.225696Z
         producer 2nd query_rows_complete = 00:00:47.216531Z   ->  axis_now is +9.165 ms after
tick B:  axis_now = W + 30668.480824 = 2026-08-12T04:00:46.137824Z
         producer 2nd query_rows_complete = 04:00:46.130648Z   ->  axis_now is +7.176 ms after
```

`W` is **byte-identical** to the producer's own persisted per-section watermark for section
`1143843662099256`, emitted verbatim as `modified_since` in both traces. That stamp *is*
`max(last_modified)` over the section's rows by code (`progressive.py:1727-1730`, emitted at
`freshness.py:299-305`); `last_modified` is the Asana task's `modified_at`
(`extractors/base.py:481-493`). Cache `created_at` implied by the LKG ages
(22:10:27.198Z and 02:11:01.005Z) matches the two `dataframe_cache_put` log times
(22:10:27.470Z and 02:11:01.185Z) on both ticks.

**A single watermark solves both ticks and lands both `axis_now` values inside 10 ms of
their own second constituent query. This is not fittable by coincidence.**

Rival-quantity refutation, per tick, numerically:

| Quantity | Tick A | Tick B | Matches observed? |
|---|---|---|---|
| cache `created_at` age (the DORMANT quantity) | 6619.6 | 6584.6 | NO |
| served frame build watermark age | 6940.93 | 6938.25 | NO |
| REFUSE sentinel | 7201.0 | 7201.0 | NO |
| **content watermark age (`max(last_modified)`)** | **16269.568696** | **30668.480824** | **YES, exactly** |

### 7.3 The cross-tick discriminator — CONTENT, not CACHE

This is the cleanest single test in the whole attestation, and it is decisive.

```
reported value advance, tick A -> tick B :  30668.480824 - 16269.568696 = 14398.912128 s
tick separation (readiness log to readiness log)                        = 14402.501952 s
cache created_at age at the two ticks                                   = 6619.6 and 6584.6 s
```

- If the axis tracked **CACHE**, tick B would have reported ≈ **6584.6**. It reported
  **30668.48** — **4.7×** larger.
- If the axis tracked **CONTENT** with an unmoved watermark, the value would advance by
  exactly the tick separation. It advanced by **14398.912128 s vs a 14402.501952 s
  separation — 99.975 % of it.**
- The 3.589824 s residual is **fully explained and is not a watermark movement**: the lag
  between `axis_now` and the `readiness_check_fail` log line was 15.147272 s on tick A and
  18.737096 s on tick B; the difference is 3.589824 s **to the microsecond**. Measured
  `axis_now`-to-`axis_now`, the watermark is *identical* on both ticks.

**CLAIM P-1: the offers freshness gate is measuring CONTENT age, not cache age.
Grade: STRONG.** Three independent tick observations (20:00Z, 00:00Z, 04:00Z), each
microsecond-reconciled against an independently-logged producer watermark, with the
cache-age quantity co-logged on the same traces and differing by 2.5×–4.7×.

### 7.4 Verdicts (three-valued)

> Judged under the STRICT R-2 bar quoted verbatim at §0.

**Tick A — 2026-08-12T00:00Z — `REALIZED-MECHANISM-BUT-SUBSTRATE-STALE`**

- `disposition = GATE` on the **content axis** — established positively (§7.1, §7.2),
  **not** via the DORMANT fallback. ✅
- Content age corroborated **same-trace** against the producer's own watermark,
  byte-identical, `axis_now` +9.165 ms after the producer's second query. ✅
- No synthetic warm; no manual invoke; threshold `3600` unmoved; L4 keep-warm still REFUSED. ✅
- **NOT deploy-adjacent** (4 h 03 m after the image went live) — this is a qualifying
  organic tick and carries full weight. ✅
- **PASS not achieved**: content age 16269.57 s > 3600 → `readiness_check_fail`;
  > 7200 → `readiness_gate_abort`. The mechanism is realized; the substrate is stale.

**Tick B — 2026-08-12T04:00Z — `REALIZED-MECHANISM-BUT-SUBSTRATE-STALE`**

- Same four ✅ legs, plus the independent cross-tick discriminator of §7.3.
- Content age 30668.48 s > 3600 → fail; > 7200 → abort.

**Neither tick is a PASS-REALIZED. Neither tick is DORMANT. Neither tick is REFUSE.
No HALT+escalate tripwire fires. No refusing constituents exist to report.**

What IS realized, at full (non-zero) weight, on two consecutive organic ticks:
the content axis is live in production, it gates on a real content watermark, it agrees
with the producer to the microsecond, and it fails honestly when the content is old.
What is NOT realized: the operator's `PASS` — victory under R-2 requires a scheduled run
that **passes** from the new check, and that has not happened.

### 7.5 Scoring my own pre-registered forecast — a MISS on magnitude

Frozen at 2026-08-11T21:05Z, before the tick:

| Pre-registered | Actual (tick A) | Score |
|---|---|---|
| staleness ≈ **97 487 s** if the binding watermark is unchanged | **16 269.57 s** | **MISS — 6.0× over** |
| floor case **≥ 14 340 s** | 16 269.57 s | HELD (actual is 1 930 s above the floor) |
| `> 7200` → `readiness_gate_abort` | abort fired | HIT |
| expected verdict `REALIZED-MECHANISM-BUT-SUBSTRATE-STALE` | that verdict | HIT |
| "exactly 7201.0 ⇒ REFUSE" discriminator | not 7201.0 | correctly not fired |
| "value = producer `age_seconds` ⇒ DORMANT ⇒ HALT" discriminator | 16269.57 ≠ 6619.6 | correctly not fired |
| served frame "the 20:02:46Z put **unless an overnight warmer rebuild lands**" | overnight warmer DID land (22:10:27Z put) | hedge correctly stated |

**The point forecast was wrong, and the reason it was wrong is the substantively
interesting part.** My §5 asserted the binding cohort had been "edit-dormant ~23 h". That
inference was **FALSE as a statement about edits.** It was true only as a statement about
the *served frame's* watermark. The producer record shows what actually happened:

- Section `1143843662099256` was edited at **2026-08-11T19:29:37.657** — **31 min 44 s
  BEFORE the 20:00Z tick.** The tick did not see it, because the frame it was served had
  been built at 18:11:40Z, before the edit. The `20:01:40.634891Z`
  `freshness_delta_section_updated` (`delta_tasks=2`) is the producer picking that edit up
  — 19 seconds *after* the tick had already read the stale frame.
- Section `1202496785025459` — the section that held the binding watermark at the 20:00Z
  tick at `2026-08-10T20:55:58.289` — was edited at **2026-08-11T20:37:11.719**, ~36 min
  *after* that tick, and picked up by the `21:05:22.240225Z` delta pass.

So at the 20:00Z tick, condition **(i)** (an edit inside 3600 s) was *already satisfied* for
one cohort; it was condition **(ii)** (frame rebuilt between the edit and the tick) that
failed. **My §5 mis-attributed a frame-lag failure to an edit-dormancy failure.** The SWR
trap I described mechanically at §4.3 was the real cause; I then reasoned about cadence as
if the frame were transparent. That is the correction, and it moves the honest first-PASS
picture in the *favourable* direction on the edit axis and the *unfavourable* direction on
the frame axis.

Two §5 claims survive intact and are re-confirmed by a second night of data:

- **Overnight quiet holds.** Between the `21:05` probe on 2026-08-11 and `06:05` on
  2026-08-12 there were **11 consecutive `freshness_probe_complete` passes on the offers
  project with zero `content_changed` and zero `structure_changed`** (22:05, 22:08, 23:05,
  00:01, 01:05, 02:05, 02:05, 02:34, 04:01, 06:03, 06:05). Both SWR builds triggered by the
  00:00Z and 04:00Z ticks reported `sections_delta_updated: 0`.
- **The combination rule is the binding constraint** (`readiness.py:361-365`, `max(ages)`).
  Confirmed empirically: the binding constituent **swapped** between the 20:00Z and 00:00Z
  ticks — from the `1202496785025459` cohort (then at `2026-08-10T20:55:58.289`) to the
  `1143843662099256` cohort (at `2026-08-11T19:29:37.657`) — precisely because the former
  advanced past the latter. Only the older of the two ever governs.

### 7.6 What the miss teaches about the real edit cadence, and what it does to §5.5

**Corrected model.** Content-change events on the offers project (34 sections), from the
producer's own probe/delta record over 2026-08-10T18:00Z → 2026-08-12T06:05Z:

- Business hours (roughly 10:00–21:10 UTC): recurrent — 10:27, 17:04, 18:06/18:07, 19:06,
  20:01, 21:05 on 2026-08-11, plus 20:01 and 21:05 on 2026-08-10. Concentrated in a small
  set of sections, `1143843662099256` most active.
- Overnight (≈22:05 → 06:05): **zero**, two nights running.

So offers ARE organically edited, several times per business day — considerably livelier
than §5.5 implied. **The obstacle is not edit-scarcity. It is the conjunction.**

**The sharp finding, quantified on the one day where BOTH cohorts were edited.** A PASS needs

```
max over constituents of (tick_now − cohort_max) ≤ 3600
   ⟺  tick_now ≤ older_cohort_max + 3600
AND the served frame must have been rebuilt after the LATER cohort_max.
```

On 2026-08-11 the two cohort maxima ended at `19:29:37.657` and `20:37:11.719` — a spread of
**4 054 s (67.6 min)**. The passing window is therefore

```
[ 2026-08-11T20:37:11.719 , 2026-08-11T20:29:37.657 ]      ← start > end
```

**empty.** No tick placement, at any cadence, could have passed on the best-observed day —
because the *inter-cohort edit spread exceeded the 3600 s threshold itself.* Frame lag was
not even the binding constraint that day.

**Revised first-PASS expectation** (ANALYSIS, not a ruling — feeds D-5b):

| Tick (2026-08-12) | Frame-freshness leg (ii) | Content leg (i) | Expectation |
|---|---|---|---|
| **08:00Z** | last offer put 06:05:52Z (wm 06:05:11Z) → lag ~1 h 55 m | overnight quiet; binding watermark still `2026-08-11T19:29:37.657` | **ABORT, near-certain.** Pre-registered point forecast: **staleness ≈ 45 068 s** (12.52 h) at a ~08:00:46Z `axis_now`, i.e. the 04:00Z value + ~14 400 s |
| **12:00Z** | historically good (39-min lag observed on 2026-08-11) | needs BOTH cohorts edited inside the same pre-tick hour | ABORT expected; a PASS requires an edit conjunction not yet observed in 36 h |
| **16:00Z** | historically best (5-min lag observed) | same | ABORT expected; **this is the most favourable tick of the day** and is where a first PASS would most plausibly appear |

**Honest bottom line on the window:** in 36 hours of continuous observation covering nine
organic ticks, the passing window has been empty at every tick — twice for frame-lag
reasons and, on the one day both cohorts moved, because the cohorts moved 67.6 minutes
apart against a 60-minute tolerance. A first PASS-REALIZED is *possible* at a 12:00Z or
16:00Z tick, but it requires a genuinely tighter edit conjunction than anything observed so
far. I will not put a probability on it: N=1 day of two-cohort edit data cannot support a
rate. **[MODERATE]** — and I explicitly flag that this materially sharpens, rather than
merely restates, the D-5b question: the threshold's 3600 s value is now competing not with
frame-rebuild latency (which the warmers handle well) but with the **spread between two
independently-edited business cohorts**, which no amount of platform tuning controls.

### 7.7 R-4 / R-8 positioning after three ticks (surfaced, not ruled)

Nothing in tick A or tick B changes the §5.6 positioning; both sharpen it.

- **R-4 verbatim** names *"a refusal storm on healthy runs"* as a **review** prompt. Three
  consecutive organic aborts (20:00Z, 00:00Z, 04:00Z) on runs whose sibling sources all PASS
  (billing 282.8/290.2 s, campaigns 892/784 s) is squarely that shape. **Also relevant:
  R-4's first trigger — "a false-fresh pass" — has NOT occurred and cannot occur on this
  evidence; every observed reading errs stale.**
- **R-8 verbatim**: *"Roll back on: serving-path latency/availability regression OR new
  refusals/errors at the consuming job."* Serving-path health is **good** and independently
  receipted: producer query times 2.72 / 2.81 / 2.89 / 2.64 ms across the four constituent
  queries; both LKG serves succeeded; no producer error events on either trace. The
  consuming job is aborting — but the abort is the honest control-arm behaviour this wave
  deliberately preserved (L4 keep-warm REFUSED), and aborts pre-date the cure (4 of 14
  baseline ticks under the old clock). **I do not recommend rollback. That adjudication is
  the operator's.**
- One new, unrelated observation worth a line: the 00:00Z tick's producer build hit a
  429 storm (`aimd_at_minimum`, `hierarchy_gap_fetch_rate_limited` on parent
  `1203136853369412`, `hierarchy_gap_warming_partial` 647/648) and the build took 126.5 s.
  This did **not** affect the gate reading (the gate read the LKG frame before the build).
  Recorded for the standing 429/warmer watch, not attributed to this change.

---

## 8. Altitude note (product-altitude gate did not fire)

Per `telos-integrity-ref §3` Gate B, the product-altitude close gate triggers only when
`.know/telos/{slug}.md` exists for the active initiative. **No
`.know/telos/offers-freshness-axis-contract.md` exists** (`ls .know/telos/` — 16 entries, none
matching). No product-altitude `PASS-ADVISORY` / `FLAG-ADVISORY` / `REFUSE-ADVISORY` is
emitted here, and none may be inferred. The *absence* of a telos declaration for an
initiative that reached a REALIZE gate is itself an **inception-gap signal** worth surfacing
to the `/go` dashboard; it is recorded as an observation, not a verdict, and it does not block
anything. The verdicts in §6 and §7 are execution-altitude and carry no `-ADVISORY` suffix.

---

## 9. Fence compliance

| Fence | Status | Evidence |
|---|---|---|
| Read-only against all infrastructure | HELD (Phases 0 **and** 1) | only `filter-log-events`, `describe-log-groups`, `lambda get-function`, `git show` |
| Never invoke the ASR Lambda manually | HELD | no `lambda invoke` issued at any point; the only three invocations across both phases are cron (`f418d9a9…` 20:00Z, `aba84962…` 00:00Z, `d095e10c…` 04:00Z) |
| Never touch the asana serve path | HELD | corroboration is LOGS-ONLY; zero HTTP requests to asana issued by this attestation |
| No threshold changes | HELD | `OFFER_STALENESS_THRESHOLD_SECONDS=3600` read, never written |
| L4 keep-warm REFUSED | HELD | no warm requested or induced; the decayed cache stands as the control arm |
| UTC only via `date -u` | HELD | all windows converted to epoch UTC before querying; `date -u` bound at 2026-08-11T20:47:17Z, 21:02:00Z, 21:06:46Z and 2026-08-12T06:06:20Z |
| No remediation on a DORMANT finding | N/A — no DORMANT disposition occurred on any tick | §7.1 |
