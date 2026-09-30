---
type: spec
initiative: read-the-name
subject: S-1 post-arm bundle (evaluator s1.5 → s1.6)
authority: asana SLATE-read-the-name-operator-words-2026-09-16.md §11 D12, §12, §13 (operator-ruled in this seat's room)
repo_touched: autom8y services/email-booking-intake/src/email_booking_intake/office_floor/** + its tests ONLY
evidence_grade: MODERATE (one seat's design; critic-graded before merge)
---

# S-1 post-arm bundle: the definition change

**One change, one soak restart.** The evaluator version goes from `s1.5` to `s1.6`, and `PINNED_QUERY_SHA256` is re-pinned. The epoch closes and opens at the first `s1.6` run line.

## Items and exact semantics

**Notation.** `T` = the terminal event set (`TERMINAL_OUTCOME_EVENTS`). `ul` = `ispresent(intake_class) and intake_class = "unknown_loud"`, computed in an EARLIER `fields` stage as a 0/1 flag so that null semantics cannot leak. A **delivery key** = `message_id` if present, else `trace_id`.

1. **Arrivals once per delivery (§13 B3).** `arrivals = count_distinct(message_id on T∧¬ul lines) + count_distinct(trace_id on T∧¬ul lines without message_id) + a keyless fallback (T∧¬ul lines with neither key, summed)`. Measured: 0 of 1,936 deliveries mix keyed and unkeyed terminal lines, so no delivery is counted under both keys.
2. **F-D.** `unknown_loud` terminal lines are excluded from arrivals (the `¬ul` above). They are NOT excluded from `window_lines`.
3. **Gate refusals as evidence (§12).** `refused = count_distinct(delivery key) over event = "ad_lead_gate_refused"` lines, with a keyless fallback. **`evidence = written + parked + refused`** is used by the floor classification AND the in-run control (offices with evidence > 0). **Credit, last-booking age and attribution stay WRITTEN-only**, unchanged. New fields: `refused` on the office line; `refused_total` and `offices_with_refused` on the run line.
4. **§3b.** The `***` residual is counted in **deliveries (the arrival unit of item 1)**, not lines. It collapses redeliveries exactly where `message_id` is present; the residual's `terminal_decline` lines carry it (23 of 23 over 7 days). The 3-hour-bucket heuristic is NOT needed: the redelivery ladder it targeted is extinct (traces = lines for every residual class over 7 days).
5. **§3e.** A `***` line that carries `office_handle` is **attributable** and does not count in the residual numerator. The per-office floors stay on guid8; the handle is a residual-only concern.
6. **§3a.** `residual_share` = residual deliveries ÷ window deliveries. It is **judged only when `window_lines ≥ 200`**; below that, `residual_status = "untaken"` and `residual_share_high` is false. The tripwire stays at 0.10.
7. **`pinned_query_sha`** (the full digest) rides every `office_floor_evaluated` run line.

`DAILY_QUERY` mirrors the same projection. `dedup_is_inert` / FACT-1 must be re-derived: arrival keys are now distinct per day bin, and a delivery does not span a day boundary.

**Not in scope:** the reserved test office (dropped, §13 B1); any change outside `office_floor/` and its tests; thresholds (ZERO ≥5/0, RATE ≥20/≥1/<2.5 %, control ≥500 records and ≥5 offices, W = 3 days).

## Proof obligations

Proofs 1 and 2 are the builder's; all the live proofs are this seat's, as for S1b.

1. **Unit tests, two-sided, one per item:**
   - a refusal pair counts 1 arrival and 1 refused;
   - `unknown_loud` is excluded while a line with NO `intake_class` still counts. **This is the null trap, and it gets its own test.**
   - `office_handle` removes a line from the residual;
   - the residual reads UNTAKEN below 200 window lines;
   - the run line carries the digest.
2. **Digest pinned;** the old digest is recoverable only through the documented diff.
3. **LIVE, pre-merge, on today's plane** (old s1.5 query vs new s1.6 query, same window):
   - (a) written and parked per office are **unchanged**;
   - (b) arrivals fall **only** where deliveries had more than one terminal line, or `unknown_loud`. Each office's delta must be explained by those two causes;
   - (c) `refused` equals an independent count of refusal deliveries;
   - (d) the residual numerator equals an independent count of `***` deliveries without `office_handle`;
   - (e) the floor-class changes are listed office by office, with a cause for each.
4. **Rite-disjoint critic** (the EBI critic session), graded against the live plane.
5. **Lever-holder (ASR)** merges and deploys, with the S-1 pre-act notice. **The serving instant is the first `s1.6` run line.** At it, the epoch closes and opens.

## AMENDMENT 2026-09-30: the build, the defects the live legs caught, and the final shape

**Build:** autom8y #2694, draft. Evaluator s1.6.

**Defects caught before merge, each by a LIVE leg, not by the unit tests:**
1. **The null trap (draft `a0bcece1`).** In Insights, `ispresent(x) and x = "…"` evaluates to NULL, not false, when `x` is absent, so lines with no `intake_class` or `office_handle` silently left the arrivals and the residual. **Fixed:** nested `if(ispresent(x), if(…, 1, 0), 0)` flags, and a test interpreter that now propagates NULL through `and`.
2. **Evidence without arrival (critic Condition 1, at `e9a9110c`).** Ruled B4 (§13 addendum). **Fixed at `b7115ebc`:** `unknown_loud` stop parks are subtracted from parked evidence.
3. **Name-split double count (window A).** Grouping by `(office_guid, office_nm)` counted a delivery twice when its lines carried different office-name forms: +1 at 2 offices across 09-04..09-12, and 0 in the last 14 days. **Fix in flight:** group by `office_guid` only.

**The legs, run on windows that exercise the change** (not only on the outage-thinned last 3 days):
- **W1** = [T0, 09-26T10:36:30Z):
  - written identical;
  - parked = old − independent `unknown_loud` parks (21);
  - arrivals match (306 → 165);
  - refused exact; residual 14 = 14;
  - 0 floor-class changes.
- **W2** = [09-20, 09-23), before the flip:
  - arrivals 973 → 384 (−357 multi-line, −232 `unknown_loud`); refused 177, exact;
  - **the 4 old ZERO offices all exit to quiet**, and all 4 were already judged non-actionable in the arming receipt's third-plane resolution (dormant or unprovisioned). Two exit on duplicate or `unknown_loud` arrivals, two on refusal evidence.
- **Window A** = [09-04, 09-12), the runbook's true-stall window: **both TRUE STALLS (`87bd31d7`, `6b93fb76`) STAY ZERO**, and 11 of 12 ZERO offices stay. The only exit is `40f86e73`, on one refusal (a dormant account). **The pager still fires on a genuine stall.**

**Merge timing:** after the 09-30 11:27:17Z digest, so today stays on s1.5 and the first s1.6 digest is 10-01.

**Served (2026-09-30).** autom8y #2694 merged as `3bf4bbf3` at 11:27:51Z, from match-head `3133b44c`. That head is blob-identical to the critic-passed `bad75beb`, and both digests were recomputed at it. Office-floor `$LATEST` has served image `3bf4bbf` since 11:35:40Z. **The first `s1.6` run line, at 12:27:18.588Z, is the serving instant**: control pass, and `pinned_query_sha` equals `fac5641c…`. The epoch record is SOAK §3n.

**Known limit, accepted at the critic's PASS.** Offices are grouped by the raw `office_guid` string, not by a canonical form.
- **What would break:** two spellings of one office (case, or a full GUID against a redacted one) would split it into two thinner rows. That means a possible false ZERO on one half, or a missed floor.
- **Why it cannot happen today:** `redact_uuid` is the only producer of `office_guid` on the lines the query reads.
- **What would re-open it:** a second writer, or a change to `redact_uuid`'s format.
- **The tell:** one guid8 on two office lines in the same run.

