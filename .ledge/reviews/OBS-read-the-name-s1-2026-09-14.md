---
id: OBS-read-the-name-s1-2026-09-14
date: 2026-09-14
station: observability-engineer
rite: sre
initiative: read-the-name
wave: 1
sprint: S1.1
status: S1.1 COMPLETE — design proof; K1..K5 PASS; instrument NOT BUILT, NOT ARMED; R1 NOT realized (R-168)
self_cap: MODERATE
---

# OBS — `read-the-name` wave 1 · S1.1 OBSERVE · the S-1 design proof

**Verdict line one: K1 PASS · K2 PASS (consistency check, DEF-4) · K3 PASS · K4 PASS · K5 PASS.
The sprint does NOT recede.** This is a **design proof only** — the instrument is **not built and
not armed**, and **R1 is NOT realized** (R-168). K1–K5 are gates on the *calibration*, not on the
*instrument*.
The founding office `ccb52f4c` fires the **RATE** floor under the ruled `(U-3, A′ = 20, r = 0.025)`
in **all three windows**; every office booking ≥ 7 % is quiet under **both** floors in all three
windows; the ZERO floor's firing set is fully enumerated with **no unexplained member**;
`933a026c` is quiet in all three windows by closed-form arithmetic; and `recordsScanned` is carried
on every query with `estimatedRecordsSkipped = 0` and `logGroupsScanned = 1`.

**But three measured facts change what the builder must build.** They are stated before the tables
because each of them falsifies or re-grounds a premise the ADR rules on. None of them fails a
K-gate; all three are the seat's own-hands measurement, not inheritance.

---

## §0 METHOD, REFS, FENCES

| item | value |
|---|---|
| Log group | `/aws/lambda/autom8-email-booking-intake` (us-east-1) |
| Access | **READ-ONLY**: `logs:StartQuery` / `logs:GetQueryResults` only. No mutation, no apply, no metric write. |
| AWS identity | `arn:aws:sts::696318035277:assumed-role/AWSReservedSSO_AdministratorAccess_072d916d21d2219c/tomtenuta` (`aws sts get-caller-identity`, rc = 0) |
| `autom8y-asana origin/main` at authoring | **`55dd171c`** (`docs(ledge): sitting XI shape ratification and the S-1 implementation ADR (#446)`) |
| Governing rulings | **R-160** (two page classes) · **R-161** (U-3, A = 5, A′ = 20, r = 0.025, K1–K5, RECEDE-not-retune) · **R-169** (test leads through real offices, no marker; replay with no exclusion + sensitivity) — all three read verbatim at `origin/main:.ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md` |
| Governing ADR | `origin/main:.ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md` §D1 · §D5 · §D8 |
| Fences honoured | **guid8 only** — office names are measured but **NOT printed** (ADR D8.1: *"`office_name` in full on the plane and on the page; **guid8 only in every `.ledge` artifact**"*); a `name?` column carries only the boolean. **No phone digits.** No reads under `.knossos/worktrees/` of other worktrees or under `.terraform/`. Insights polled in bounded loops (≤ 60 × 2 s). zsh arrays, rc unpiped, `"${REF}:path"` for every git read. |
| Self-cap | **MODERATE** — single seat, no rite-disjoint corroboration (`self-ref-evidence-grade-rule`). The rite-disjoint critic for this sprint is `qa-adversary` (shape S1.1 `critic:`), not yet run. |

**A note on the inherited pre-sitting measurements.** The two measurements named in the shape's
`context:` were taken against partially-open windows and a different query shape; their window-A
figure for `ccb52f4c` (580 lines / 4 `booking_completed`) does not reproduce here (552 / 3), and
their window-C scan (7,010 records) is roughly half this seat's (13,464) because window C
(…09-14T00:00Z) had not yet closed when they ran. **Nothing in this report is inherited from them.**
Every number below is this seat's own-hands query with its statistics block printed.

---

## §1 THE THREE MEASURED FACTS THAT CHANGE THE BUILD

### FACT-1 — `message_id` de-duplicates NOTHING. U-3's `A_id` branch is a line count wearing an identity's clothes. `[VERIFIED — own-hands]`

Measured over window A, per event, office-bearing lines only:

| event | lines | lines carrying `message_id` | **distinct `message_id`** | carries `office_name` | carries `lead_id` |
|---|---|---|---|---|---|
| `terminal_decline` | 962 | 533 | **533** | 255 | 0 |
| `stage_exception` | 276 | 0 | 0 | 276 | 0 |
| `terminal_decline_parked` | 149 | **0** | 0 | 149 | 0 |
| `booking_completed` | 86 | **0** | 0 | 86 | 0 |
| `ad_lead_gate_refused` | 58 | 0 | 0 | 58 | 58 |
| `booking_intake_fault` | 51 | 0 | 0 | 51 | 0 |
| `booking_gate_declined` | 38 | 0 | 0 | 38 | 0 |
| `contente_two_writer_overlap` | 18 | 0 | 0 | 0 | 0 |
| `contente_booking_booked` | 16 | **0** | 0 | 16 | 0 |
| `contente_booking_allowlist_suppressed` | 4 | 0 | 0 | 4 | 0 |
| `booking_contente_stage_failed` | 1 | 0 | 0 | 0 | 0 |

Three consequences, each load-bearing:

1. **`distinct message_id` == `lines carrying message_id` == 533.** Not one `message_id` repeats.
   The ADR's stated rationale for U-3 — *"Where the mail has an identity, the identity **is** the
   unit — exact, **retry-deflated**, immune to the `terminal_decline`/`terminal_decline_parked`
   double-count"* (D1.2) — **does not hold on this log plane in these windows.** `count_distinct`
   and `count` return the same number. U-3 is arithmetically identical to *"count terminal-outcome
   lines"*.
2. **That does not make U-3 wrong — it makes its VALUE different from its stated reason.** U-3 is
   still the right unit here, because what it actually strips is `stage_exception` (276 lines) and
   `terminal_decline_parked` (149 lines) — the two genuinely inflating non-terminal events. Window A:
   U-1 = 1,659 lines → U-3 = 1,211 arrivals. The inflation U-3 removes is **real and per-office
   variable**; the de-duplication it claims to perform is **zero everywhere**.
3. **`message_id` rides only `terminal_decline`, and only 55 % of those.** Bookings carry **no**
   `message_id` at all, so `bookings(U-3)` reduces exactly to the P3 **line** count. The ADR's
   `count_distinct(message_id | line)` booking form is well-defined but its `count_distinct` branch
   is dead code today.

> **This is the strongest single argument for DEFER §12 row 2 (U-4, the uniform `mail_arrived`
> line).** The fallback branch is not a "bounded degradation" — it is **100 % of the booking
> denominator and 45 % of the decline numerator**.

### FACT-2 — a regime break on **2026-09-11**: unattributed terminal outcomes go from 44 % to exactly zero. `[VERIFIED — own-hands, per-day control]`

Terminal-outcome lines across the whole log group (no office filter), by day, by guid-carrier class:

| day (UTC) | NO-GUID-FIELD | attributed | masked `***` | total | unattributed share |
|---|---|---|---|---|---|
| 2026-09-04 | 125 | 110 | 6 | 241 | 51.9 % |
| 2026-09-05 | 52 | 61 | 2 | 115 | 45.2 % |
| 2026-09-06 | 67 | 53 | 1 | 121 | 55.4 % |
| 2026-09-07 | 71 | 94 | 3 | 168 | 42.3 % |
| 2026-09-08 | 179 | 170 | 5 | 354 | 50.6 % |
| 2026-09-09 | 267 | 195 | 6 | 468 | 57.1 % |
| 2026-09-10 | 122 | 254 | 14 | 390 | 31.3 % |
| **2026-09-11** | **0** | 209 | 28 | 237 | **0.0 %** |
| **2026-09-12** | **0** | 101 | 3 | 104 | **0.0 %** |
| **2026-09-13** | **0** | 141 | 2 | 143 | **0.0 %** |

`status=Complete · recordsScanned=72,615 · recordsMatched=2,341 · bytesScanned=18,642,526 · estimatedRecordsSkipped=0 · logGroupsScanned=1`

This is the `name-the-client` office-identity landing arriving on production traffic. It means:

- **Window A and window B straddle a substrate change.** 883 terminal outcomes in window A and 389
  in window B carry **no office guid field at all** and are therefore absent from *every* office's
  denominator. The per-office arrival counts in A and B are systematic **undercounts of unknown
  per-office magnitude**.
- **Window C (09-11 .. 09-14) is the only window measured entirely in the live regime.** It is the
  only one of the three whose arithmetic transfers to what the instrument will actually see.
- **The §2(ii) historical positive control is therefore two-tiered**, and this report says so
  rather than presenting one number: A and B prove the instrument *would have named* `ccb52f4c` on
  the substrate as it then was; **C** proves it names `ccb52f4c` on the substrate as it now is.
  Both fire. The K1 verdict does not depend on the distinction — but the **threshold calibration
  does**, and window C is the tightest cell in the whole grid (§4).

### FACT-3 — the `***` residual is `office_identity_kind = absent`, not a naming failure; and 21 % of offices have no resolvable name at all. `[VERIFIED — own-hands]`

- **UV-P (ADR §11, `***` composition) — DISCHARGED.** Over 09-04 .. 09-14 the `***` bucket is
  **100 % `guid_carrier = flat`** (the `chiropractor_guid` field *is present*; its *value* is the
  mask) and splits `office_identity_kind`: **`absent` 133 lines · field-absent 23 lines · `resolved` 0**.
  So `***` is **"identity never resolved at the line"**, not "guid present but unresolvable to a
  name". The ADR's D5.3 ruling (excluded from evaluation, never suppressed) is correct under this
  composition; the **runbook action** is *"the resolver did not fire"*, not *"the name lookup failed"*.
- **Fleet-wide `office_identity_kind` over the same span:** `resolved` 1,177 · field-absent 733 ·
  `absent` 142 office-bearing lines.
- **The guid-prefix-only row (D5.4 / V-15) is LIVE, not hypothetical.** Offices with **no
  resolvable `office_name` on any line in the window**: window A **13 of 61 (21 %)**, window B
  **6 of 54**, window C **0 of 38**. The builder's `<guid8> —` render path is exercised by real
  traffic in the historical windows and must not crash or drop.
- **`contente_booking_allowlist_suppressed`** (4 lines, window A) is an office-bearing event the
  ADR's D1.1 enumeration does not classify. It is **not** in the terminal set and this report does
  not add it; it is raised as a UV-P for the builder (§8).

---

## §2 THE PINNED QUERY CONSTANT (ADR D8.3) — printed verbatim, once

This is `Q-S1`, the single Insights query string, parameterised **only** by `(log_group,
start_epoch, end_epoch)`. Every per-office number in §3, §4 and §5 of this report was produced
by this exact text; the S1.3 evaluator pins this text; the S1.6 soak receipt cites this text.
A divergence between "the query the replay ran" and "the query the instrument runs" is
impossible by construction, not by review.

```
fields coalesce(chiropractor_guid, office.chiropractor_guid) as office_guid,
       coalesce(office_name, office.office_name) as office_nm
| filter ispresent(office_guid)
| fields if(event = "terminal_decline" or event = "ad_lead_gate_refused" or event = "booking_gate_declined" or event = "booking_completed" or event = "contente_booking_booked" or event = "booking_intake_fault", 1, 0) as t_line,
         if(event = "booking_completed" or event = "contente_booking_booked", 1, 0) as b_line,
         if(event = "booking_completed", 1, 0) as p2_line,
         if(event = "contente_booking_booked", 1, 0) as p1_line,
         if(ispresent(message_id), 1, 0) as mid_line,
         if((event = "terminal_decline" or event = "ad_lead_gate_refused" or event = "booking_gate_declined" or event = "booking_completed" or event = "contente_booking_booked" or event = "booking_intake_fault") and not ispresent(message_id), 1, 0) as t_noid,
         if((event = "booking_completed" or event = "contente_booking_booked") and not ispresent(message_id), 1, 0) as b_noid,
         if(event = "booking_completed" or event = "contente_booking_booked", message_id, no_such_field_sentinel) as b_mid
| stats count(*) as u1_lines,
        sum(t_line) as terminal_lines,
        sum(mid_line) as id_bearing_lines,
        count_distinct(message_id) as arr_id,
        sum(t_noid) as arr_noid,
        count_distinct(b_mid) as bk_id,
        sum(b_noid) as bk_noid,
        sum(b_line) as booking_lines,
        sum(p2_line) as p2_booking_completed,
        sum(p1_line) as p1_contente_booked
      by office_guid, office_nm
| sort u1_lines desc
```

**How the evaluator folds it.** Group grain is `(office_guid, office_nm)` so that the
name-present / name-absent split is *surfaced* rather than silently collapsed (FACT-3). The
evaluator folds to `office_guid` and carries `office_nm` from whichever subgroup has it, rendering
`<guid8> —` when none does. **Two-sided check performed:** the folded totals were compared, field
by field, against an otherwise-identical run grouped by `office_guid` alone — **0 mismatches across
all 10 numeric fields in all three windows** (61 / 54 / 38 offices). Note that the additivity of
`arr_id` across the fold is only safe *because* of FACT-1; once U-4 lands and `message_id` actually
de-duplicates, `count_distinct` stops being additive and the fold must move into the query.

**Derived quantities (evaluator-side, not in the query):**

```
arrivals_U3(office, W) = arr_id + arr_noid          # the RULED unit (R-161)
bookings_U3(office, W) = bk_id  + bk_noid           # P3 = booking_completed UNION contente_booking_booked
arrivals_U1(office, W) = u1_lines                   # the COMPARISON unit: any office-bearing line
bookings_U1(office, W) = booking_lines
inflation(office, W)   = u1_lines / arrivals_U3
FLOOR-ZERO  <=>  arrivals >= A   AND bookings == 0
FLOOR-RATE  <=>  arrivals >= A'  AND bookings >= 1 AND bookings/arrivals < r
```

**UV-P DISCHARGED (ADR §11, item 1) — chained `stats` IS supported.** Probed own-hands:
`stats count_distinct(event) as kinds, count(*) as n by park_key | stats count(*) as park_keys, sum(n) as tot_lines by kinds`
returned `status=Complete`, `recordsScanned=65,762`, `bytesScanned=16,771,500` — **byte-identical to
the single-pass run over the same window**, confirming D6.1's *"Insights bills SCANNED, not MATCHED"*
and the UV-P's cost-equivalence claim. The two-stage form is available to the builder; `Q-S1` does
not need it.

> Gotcha the builder will hit: Insights rejects a `stats` alias that reuses an ephemeral field name
> already defined upstream (`MalformedQueryException: Ephemeral field is already defined`). This is
> why `Q-S1` uses `t_noid`/`b_noid` upstream and `arr_noid`/`bk_noid` as the stats aliases.

---

## §3 THE SENSITIVITY TABLE — 3 windows × 2 units × the floor grid

Grid is a **superset** of R-161's 12 rate settings `(A' ∈ {20,30,50}) × (r ∈ {0.020,0.025,0.030,0.050})`:
A' is extended to `{10,20,30,40,50}` and the zero floor to `A ∈ {3,5,10}` so the ruled cell's
neighbourhood is visible on both sides. Cells are the **firing-set size**; `***` is excluded from
evaluation in every cell (ADR D5.3). **No smoke-lead exclusion is applied anywhere** (R-169).

### ZERO FLOOR — firing-set SIZE (*** excluded from evaluation)
| unit | A | win A (8d) | win B (3d) | win C (3d) |
|---|---|---|---|---|
| U3 | 3 | 18 | 6 | 5 |
| U3 | 5 | 12 | 6 | 3 |
| U3 | 10 | 5 | 4 | 0 |
| U1 | 3 | 21 | 16 | 7 |
| U1 | 5 | 15 | 8 | 5 |
| U1 | 10 | 8 | 6 | 3 |

### RATE FLOOR — firing-set SIZE
| unit | A' | r | win A | win B | win C | ccb52f4c fires? A/B/C |
|---|---|---|---|---|---|---|
| U3 | 10 | 0.020 | 1 | 1 | 0 | Y/Y/n |
| U3 | 10 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 10 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 10 | 0.050 | 2 | 2 | 1 | Y/Y/Y |
| U3 | 20 | 0.020 | 1 | 1 | 0 | Y/Y/n |
| U3 | 20 | 0.025 | 1 | 1 | 1 | Y/Y/Y **<-- RULED** |
| U3 | 20 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 20 | 0.050 | 2 | 2 | 1 | Y/Y/Y |
| U3 | 30 | 0.020 | 1 | 1 | 0 | Y/Y/n |
| U3 | 30 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 30 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 30 | 0.050 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 40 | 0.020 | 1 | 1 | 0 | Y/Y/n |
| U3 | 40 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 40 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 40 | 0.050 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 50 | 0.020 | 1 | 1 | 0 | Y/Y/n |
| U3 | 50 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 50 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U3 | 50 | 0.050 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 10 | 0.020 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 10 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 10 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 10 | 0.050 | 3 | 2 | 2 | Y/Y/Y |
| U1 | 20 | 0.020 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 20 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 20 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 20 | 0.050 | 3 | 2 | 2 | Y/Y/Y |
| U1 | 30 | 0.020 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 30 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 30 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 30 | 0.050 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 40 | 0.020 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 40 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 40 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 40 | 0.050 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 50 | 0.020 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 50 | 0.025 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 50 | 0.030 | 1 | 1 | 1 | Y/Y/Y |
| U1 | 50 | 0.050 | 1 | 1 | 1 | Y/Y/Y |

**Reading the grid — the three things it says:**

1. **The ruled cell `(U-3, A′ = 20, r = 0.025)` fires exactly ONE office in every window, and that
   office is `ccb52f4c`.** The RATE floor is not merely satisfiable — it is *maximally selective* at
   the ruled setting: a firing set of one, in all three windows, with no second member to triage.
2. **`r = 0.020` breaks in window C.** `ccb52f4c` measures **2.02 %** in the live-regime window, so
   at `r = 0.020` it goes **silent** (`Y/Y/n` on every `A′`). The ADR rejected `r = 0.020` for a
   4 %-headroom argument on an unmeasured de-dup factor; **the fresh measurement rejects it outright,
   for a different and harder reason.** The ruling survives; its stated reason is superseded by data.
3. **`A′` is inert across its whole range, exactly as D1.5 predicted.** `A′ ∈ {10 … 50}` changes
   nothing at `r ≤ 0.030` — `r` dominates (`arrivals > 1/r = 40` is required to fire on one booking).
   `A′ = 20` is confirmed as a statistical-confidence guard, not an operative lever.
4. **U-1 is more permissive than U-3 on the rate floor and more permissive on the zero floor** (its
   arrivals are inflated), which is why U-1 fires `ccb52f4c` even at `r = 0.020`. U-1 is the
   comparator, not a candidate: the same threshold means a different number of mails per office
   (inflation ranges **1.00 → 9.20** across offices in window A — see §4).

---

## §4 PER-OFFICE ROWS AND PER-QUERY STATISTICS

Every zero below is paired with its control: the same query, same log group, same statistics
block. `estimatedRecordsSkipped = 0` and `logGroupsScanned = 1` on **every** query in this
report — no zero here is an unscanned zero (charge §10 UNTAKEN-ZERO).

#### Per-query statistics (K5 — every zero is paired with its control)

| window | bounds (UTC) | status | recordsScanned | recordsMatched | bytesScanned | estRecordsSkipped | logGroupsScanned |
|---|---|---|---|---|---|---|---|
| A | 2026-09-04T00:00Z .. 2026-09-12T00:00Z (8 d) | Complete | 65,762 | 1,659 | 16,771,500 | 0 | 1 |
| B | 2026-09-09T00:00Z .. 2026-09-12T00:00Z (3 d) | Complete | 31,007 | 1,152 | 7,953,053 | 0 | 1 |
| C | 2026-09-11T00:00Z .. 2026-09-14T00:00Z (3 d) | Complete | 13,464 | 819 | 3,657,761 | 0 | 1 |

#### Window A — per-office rows (2026-09-04T00:00Z .. 2026-09-12T00:00Z (8 d)); `***` reported separately, never evaluated

| guid8 | name? | lines (U-1) | mails (distinct msg_id) | arrivals U-3 (= id + noid) | arrivals U-1 | P1 | P2 | bookings U-3 (P3) | rate U-3 | rate U-1 | inflation | floor_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ccb52f4c` | y | 552 | 352 | 369 (= 352 + 17) | 552 | 0 | 3 | 3 | 0.81% | 0.54% | 1.50 | **RATE** |
| `c2ab6637` | y | 132 | 4 | 122 (= 4 + 118) | 132 | 0 | 18 | 18 | 14.75% | 13.64% | 1.08 | quiet |
| `7a1e83fd` | y | 68 | 18 | 48 (= 18 + 30) | 68 | 0 | 4 | 4 | 8.33% | 5.88% | 1.42 | quiet |
| `15caa02c` | y | 51 | 8 | 44 (= 8 + 36) | 51 | 1 | 6 | 7 | 15.91% | 13.73% | 1.16 | quiet |
| `d167d635` | y | 48 | 1 | 43 (= 1 + 42) | 48 | 2 | 3 | 5 | 11.63% | 10.42% | 1.12 | quiet |
| `e63bbbe0` | y | 47 | 23 | 24 (= 23 + 1) | 47 | 0 | 0 | 0 | 0.00% | 0.00% | 1.96 | **ZERO** |
| `2b591e43` | y | 46 | 5 | 5 (= 5 + 0) | 46 | 0 | 0 | 0 | 0.00% | 0.00% | 9.20 | **ZERO** |
| `4ec260bf` | y | 38 | 7 | 33 (= 7 + 26) | 38 | 3 | 8 | 11 | 33.33% | 28.95% | 1.15 | quiet |
| `087d7de5` | y | 37 | 9 | 37 (= 9 + 28) | 37 | 0 | 9 | 9 | 24.32% | 24.32% | 1.00 | quiet |
| `8e56f6e1` | y | 34 | 0 | 34 (= 0 + 34) | 34 | 2 | 1 | 3 | 8.82% | 8.82% | 1.00 | quiet |
| `87bd31d7` | y | 33 | 1 | 33 (= 1 + 32) | 33 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `ca70baa8` | y | 30 | 1 | 24 (= 1 + 23) | 30 | 3 | 4 | 7 | 29.17% | 23.33% | 1.25 | quiet |
| `933a026c` | y | 28 | 0 | 27 (= 0 + 27) | 28 | 0 | 1 | 1 | 3.70% | 3.57% | 1.04 | quiet |
| `8a9b1a84` | y | 26 | 12 | 15 (= 12 + 3) | 26 | 0 | 0 | 0 | 0.00% | 0.00% | 1.73 | **ZERO** |
| `53295a22` | y | 24 | 0 | 19 (= 0 + 19) | 24 | 0 | 1 | 1 | 5.26% | 4.17% | 1.26 | quiet |
| `6b93fb76` | y | 24 | 1 | 24 (= 1 + 23) | 24 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `816db7b3` | y | 24 | 8 | 22 (= 8 + 14) | 24 | 0 | 4 | 4 | 18.18% | 16.67% | 1.09 | quiet |
| `21b09c5c` | y | 22 | 5 | 20 (= 5 + 15) | 22 | 0 | 4 | 4 | 20.00% | 18.18% | 1.10 | quiet |
| `40f86e73` | y | 15 | 0 | 13 (= 0 + 13) | 15 | 0 | 0 | 0 | 0.00% | 0.00% | 1.15 | **ZERO** |
| `79be1b75` | y | 14 | 1 | 8 (= 1 + 7) | 14 | 0 | 1 | 1 | 12.50% | 7.14% | 1.75 | quiet |
| `ed88a4a9` | y | 13 | 1 | 11 (= 1 + 10) | 13 | 0 | 1 | 1 | 9.09% | 7.69% | 1.18 | quiet |
| `06a9afb0` | y | 12 | 0 | 10 (= 0 + 10) | 12 | 0 | 2 | 2 | 20.00% | 16.67% | 1.20 | quiet |
| `8320ee8a` | y | 12 | 1 | 12 (= 1 + 11) | 12 | 0 | 1 | 1 | 8.33% | 8.33% | 1.00 | quiet |
| `9fcf1507` | y | 11 | 0 | 8 (= 0 + 8) | 11 | 0 | 1 | 1 | 12.50% | 9.09% | 1.38 | quiet |
| `e5a68603` | y | 10 | 6 | 6 (= 6 + 0) | 10 | 0 | 0 | 0 | 0.00% | 0.00% | 1.67 | **ZERO** |
| `ea98e732` | y | 10 | 8 | 8 (= 8 + 0) | 10 | 0 | 0 | 0 | 0.00% | 0.00% | 1.25 | **ZERO** |
| `4a2f351c` | y | 9 | 0 | 8 (= 0 + 8) | 9 | 0 | 1 | 1 | 12.50% | 11.11% | 1.12 | quiet |
| `b149a403` | y | 9 | 3 | 7 (= 3 + 4) | 9 | 0 | 1 | 1 | 14.29% | 11.11% | 1.29 | quiet |
| `7081d9d4` | y | 8 | 4 | 4 (= 4 + 0) | 8 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `4416989f` | y | 8 | 0 | 8 (= 0 + 8) | 8 | 0 | 1 | 1 | 12.50% | 12.50% | 1.00 | quiet |
| `2786b72d` | y | 7 | 1 | 5 (= 1 + 4) | 7 | 0 | 0 | 0 | 0.00% | 0.00% | 1.40 | **ZERO** |
| `03859024` | y | 7 | 2 | 5 (= 2 + 3) | 7 | 1 | 1 | 2 | 40.00% | 28.57% | 1.40 | quiet |
| `b167331c` | y | 7 | 0 | 5 (= 0 + 5) | 7 | 2 | 2 | 4 | 80.00% | 57.14% | 1.40 | quiet |
| `5a19f1ad` | **n** | 7 | 3 | 7 (= 3 + 4) | 7 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `800f9fe1` | y | 7 | 0 | 5 (= 0 + 5) | 7 | 2 | 2 | 4 | 80.00% | 57.14% | 1.40 | quiet |
| `735416d5` | y | 7 | 2 | 5 (= 2 + 3) | 7 | 0 | 0 | 0 | 0.00% | 0.00% | 1.40 | **ZERO** |
| `cf6ae0f2` | y | 6 | 0 | 6 (= 0 + 6) | 6 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `b1569808` | y | 6 | 0 | 6 (= 0 + 6) | 6 | 0 | 1 | 1 | 16.67% | 16.67% | 1.00 | quiet |
| `2943ade4` | **n** | 6 | 0 | 3 (= 0 + 3) | 6 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `fa59bf58` | y | 6 | 1 | 4 (= 1 + 3) | 6 | 0 | 0 | 0 | 0.00% | 0.00% | 1.50 | quiet |
| `b61452e6` | y | 5 | 0 | 5 (= 0 + 5) | 5 | 0 | 1 | 1 | 20.00% | 20.00% | 1.00 | quiet |
| `bfabc3f0` | y | 5 | 1 | 4 (= 1 + 3) | 5 | 0 | 1 | 1 | 25.00% | 20.00% | 1.25 | quiet |
| `921e5d14` | y | 4 | 2 | 2 (= 2 + 0) | 4 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `783b40aa` | **n** | 4 | 0 | 4 (= 0 + 4) | 4 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `0e703796` | y | 4 | 2 | 2 (= 2 + 0) | 4 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `949bc690` | y | 4 | 0 | 4 (= 0 + 4) | 4 | 0 | 1 | 1 | 25.00% | 25.00% | 1.00 | quiet |
| `1c20d27c` | y | 4 | 0 | 3 (= 0 + 3) | 4 | 0 | 0 | 0 | 0.00% | 0.00% | 1.33 | quiet |
| `9917ca35` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `0dd74a31` | **n** | 3 | 3 | 3 (= 3 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `83d69605` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `c0ab0953` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `a5857a02` | **n** | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `2b03a2dd` | **n** | 2 | 1 | 2 (= 1 + 1) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `7363c7ea` | **n** | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `98c18f4c` | **n** | 2 | 1 | 2 (= 1 + 1) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `e3267756` | **n** | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `4ad24874` | **n** | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `42bdf67f` | **n** | 1 | 1 | 1 (= 1 + 0) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `7d2d87da` | **n** | 1 | 0 | 1 (= 0 + 1) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `51144b61` | **n** | 1 | 0 | 1 (= 0 + 1) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |

**ATTRIBUTION RESIDUAL `***` (not an office; excluded from both floors, never suppressed):** lines=141 · mails=33 · U-3 arrivals=65 · bookings=0 · share = 141/1659 = **8.5%** of window office-bearing lines

#### Window B — per-office rows (2026-09-09T00:00Z .. 2026-09-12T00:00Z (3 d)); `***` reported separately, never evaluated

| guid8 | name? | lines (U-1) | mails (distinct msg_id) | arrivals U-3 (= id + noid) | arrivals U-1 | P1 | P2 | bookings U-3 (P3) | rate U-3 | rate U-1 | inflation | floor_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ccb52f4c` | y | 371 | 175 | 188 (= 175 + 13) | 371 | 0 | 3 | 3 | 1.60% | 0.81% | 1.97 | **RATE** |
| `c2ab6637` | y | 91 | 4 | 81 (= 4 + 77) | 91 | 0 | 18 | 18 | 22.22% | 19.78% | 1.12 | quiet |
| `2b591e43` | y | 46 | 5 | 5 (= 5 + 0) | 46 | 0 | 0 | 0 | 0.00% | 0.00% | 9.20 | **ZERO** |
| `7a1e83fd` | y | 42 | 10 | 22 (= 10 + 12) | 42 | 0 | 4 | 4 | 18.18% | 9.52% | 1.91 | quiet |
| `e63bbbe0` | y | 37 | 13 | 14 (= 13 + 1) | 37 | 0 | 0 | 0 | 0.00% | 0.00% | 2.64 | **ZERO** |
| `15caa02c` | y | 35 | 2 | 28 (= 2 + 26) | 35 | 1 | 6 | 7 | 25.00% | 20.00% | 1.25 | quiet |
| `d167d635` | y | 32 | 1 | 27 (= 1 + 26) | 32 | 2 | 3 | 5 | 18.52% | 15.62% | 1.19 | quiet |
| `4ec260bf` | y | 29 | 2 | 24 (= 2 + 22) | 29 | 3 | 8 | 11 | 45.83% | 37.93% | 1.21 | quiet |
| `087d7de5` | y | 24 | 2 | 24 (= 2 + 22) | 24 | 0 | 9 | 9 | 37.50% | 37.50% | 1.00 | quiet |
| `ca70baa8` | y | 23 | 1 | 17 (= 1 + 16) | 23 | 3 | 4 | 7 | 41.18% | 30.43% | 1.35 | quiet |
| `8a9b1a84` | y | 23 | 9 | 12 (= 9 + 3) | 23 | 0 | 0 | 0 | 0.00% | 0.00% | 1.92 | **ZERO** |
| `933a026c` | y | 22 | 0 | 21 (= 0 + 21) | 22 | 0 | 1 | 1 | 4.76% | 4.55% | 1.05 | quiet |
| `8e56f6e1` | y | 18 | 0 | 18 (= 0 + 18) | 18 | 2 | 1 | 3 | 16.67% | 16.67% | 1.00 | quiet |
| `816db7b3` | y | 18 | 4 | 16 (= 4 + 12) | 18 | 0 | 4 | 4 | 25.00% | 22.22% | 1.12 | quiet |
| `53295a22` | y | 17 | 0 | 12 (= 0 + 12) | 17 | 0 | 1 | 1 | 8.33% | 5.88% | 1.42 | quiet |
| `21b09c5c` | y | 16 | 3 | 14 (= 3 + 11) | 16 | 0 | 4 | 4 | 28.57% | 25.00% | 1.14 | quiet |
| `79be1b75` | y | 14 | 1 | 8 (= 1 + 7) | 14 | 0 | 1 | 1 | 12.50% | 7.14% | 1.75 | quiet |
| `ed88a4a9` | y | 12 | 1 | 10 (= 1 + 9) | 12 | 0 | 1 | 1 | 10.00% | 8.33% | 1.20 | quiet |
| `87bd31d7` | y | 12 | 1 | 12 (= 1 + 11) | 12 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `06a9afb0` | y | 11 | 0 | 9 (= 0 + 9) | 11 | 0 | 2 | 2 | 22.22% | 18.18% | 1.22 | quiet |
| `6b93fb76` | y | 11 | 0 | 11 (= 0 + 11) | 11 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | **ZERO** |
| `40f86e73` | y | 11 | 0 | 9 (= 0 + 9) | 11 | 0 | 0 | 0 | 0.00% | 0.00% | 1.22 | **ZERO** |
| `9fcf1507` | y | 10 | 0 | 7 (= 0 + 7) | 10 | 0 | 1 | 1 | 14.29% | 10.00% | 1.43 | quiet |
| `b167331c` | y | 7 | 0 | 5 (= 0 + 5) | 7 | 2 | 2 | 4 | 80.00% | 57.14% | 1.40 | quiet |
| `7081d9d4` | y | 6 | 2 | 2 (= 2 + 0) | 6 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `e5a68603` | y | 6 | 2 | 2 (= 2 + 0) | 6 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `03859024` | y | 6 | 2 | 4 (= 2 + 2) | 6 | 1 | 1 | 2 | 50.00% | 33.33% | 1.50 | quiet |
| `800f9fe1` | y | 6 | 0 | 4 (= 0 + 4) | 6 | 2 | 2 | 4 | 100.00% | 66.67% | 1.50 | quiet |
| `b149a403` | y | 5 | 1 | 3 (= 1 + 2) | 5 | 0 | 1 | 1 | 33.33% | 20.00% | 1.67 | quiet |
| `8320ee8a` | y | 5 | 0 | 5 (= 0 + 5) | 5 | 0 | 1 | 1 | 20.00% | 20.00% | 1.00 | quiet |
| `b1569808` | y | 4 | 0 | 4 (= 0 + 4) | 4 | 0 | 1 | 1 | 25.00% | 25.00% | 1.00 | quiet |
| `ea98e732` | y | 4 | 2 | 2 (= 2 + 0) | 4 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `4a2f351c` | y | 4 | 0 | 3 (= 0 + 3) | 4 | 0 | 1 | 1 | 33.33% | 25.00% | 1.33 | quiet |
| `921e5d14` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `9917ca35` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `2786b72d` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `4416989f` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `0e703796` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `fa59bf58` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `83d69605` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `b61452e6` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `949bc690` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `735416d5` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `bfabc3f0` | y | 3 | 0 | 2 (= 0 + 2) | 3 | 0 | 1 | 1 | 50.00% | 33.33% | 1.50 | quiet |
| `1c20d27c` | y | 3 | 0 | 2 (= 0 + 2) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 1.50 | quiet |
| `c0ab0953` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `cf6ae0f2` | y | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `783b40aa` | **n** | 2 | 0 | 2 (= 0 + 2) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `2943ade4` | **n** | 2 | 0 | 1 (= 0 + 1) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 2.00 | quiet |
| `5a19f1ad` | **n** | 2 | 1 | 2 (= 1 + 1) | 2 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `a5857a02` | **n** | 1 | 0 | 1 (= 0 + 1) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `7363c7ea` | **n** | 1 | 0 | 1 (= 0 + 1) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |
| `7d2d87da` | **n** | 1 | 0 | 1 (= 0 + 1) | 1 | 0 | 0 | 0 | 0.00% | 0.00% | 1.00 | quiet |

**ATTRIBUTION RESIDUAL `***` (not an office; excluded from both floors, never suppressed):** lines=124 · mails=16 · U-3 arrivals=48 · bookings=0 · share = 124/1152 = **10.8%** of window office-bearing lines — **above the 10 % `residual share HIGH` tripwire (D5.3)**

#### Window C — per-office rows (2026-09-11T00:00Z .. 2026-09-14T00:00Z (3 d)); `***` reported separately, never evaluated

| guid8 | name? | lines (U-1) | mails (distinct msg_id) | arrivals U-3 (= id + noid) | arrivals U-1 | P1 | P2 | bookings U-3 (P3) | rate U-3 | rate U-1 | inflation | floor_class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ccb52f4c` | y | 262 | 70 | 99 (= 70 + 29) | 262 | 0 | 2 | 2 | 2.02% | 0.76% | 2.65 | **RATE** |
| `c2ab6637` | y | 65 | 6 | 52 (= 6 + 46) | 65 | 0 | 15 | 15 | 28.85% | 23.08% | 1.25 | quiet |
| `87bd31d7` | y | 63 | 9 | 45 (= 9 + 36) | 63 | 0 | 12 | 12 | 26.67% | 19.05% | 1.40 | quiet |
| `d167d635` | y | 38 | 5 | 23 (= 5 + 18) | 38 | 4 | 7 | 11 | 47.83% | 28.95% | 1.65 | quiet |
| `e63bbbe0` | y | 26 | 8 | 9 (= 8 + 1) | 26 | 0 | 0 | 0 | 0.00% | 0.00% | 2.89 | **ZERO** |
| `79be1b75` | y | 23 | 4 | 11 (= 4 + 7) | 23 | 0 | 1 | 1 | 9.09% | 4.35% | 2.09 | quiet |
| `53295a22` | y | 21 | 0 | 21 (= 0 + 21) | 21 | 0 | 7 | 7 | 33.33% | 33.33% | 1.00 | quiet |
| `7a1e83fd` | y | 18 | 1 | 16 (= 1 + 15) | 18 | 0 | 5 | 5 | 31.25% | 27.78% | 1.12 | quiet |
| `4ec260bf` | y | 18 | 1 | 14 (= 1 + 13) | 18 | 2 | 5 | 7 | 50.00% | 38.89% | 1.29 | quiet |
| `ca70baa8` | y | 15 | 1 | 11 (= 1 + 10) | 15 | 2 | 4 | 6 | 54.55% | 40.00% | 1.36 | quiet |
| `15caa02c` | y | 15 | 0 | 15 (= 0 + 15) | 15 | 0 | 5 | 5 | 33.33% | 33.33% | 1.00 | quiet |
| `087d7de5` | y | 15 | 2 | 11 (= 2 + 9) | 15 | 0 | 3 | 3 | 27.27% | 20.00% | 1.36 | quiet |
| `8a9b1a84` | y | 15 | 3 | 6 (= 3 + 3) | 15 | 0 | 0 | 0 | 0.00% | 0.00% | 2.50 | **ZERO** |
| `933a026c` | y | 12 | 0 | 12 (= 0 + 12) | 12 | 0 | 4 | 4 | 33.33% | 33.33% | 1.00 | quiet |
| `ed88a4a9` | y | 12 | 0 | 12 (= 0 + 12) | 12 | 0 | 4 | 4 | 33.33% | 33.33% | 1.00 | quiet |
| `40f86e73` | y | 10 | 0 | 8 (= 0 + 8) | 10 | 0 | 0 | 0 | 0.00% | 0.00% | 1.25 | **ZERO** |
| `e5a68603` | y | 9 | 3 | 3 (= 3 + 0) | 9 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `06a9afb0` | y | 9 | 1 | 6 (= 1 + 5) | 9 | 0 | 2 | 2 | 33.33% | 22.22% | 1.50 | quiet |
| `4416989f` | y | 9 | 0 | 8 (= 0 + 8) | 9 | 1 | 3 | 4 | 50.00% | 44.44% | 1.12 | quiet |
| `b167331c` | y | 9 | 0 | 6 (= 0 + 6) | 9 | 3 | 3 | 6 | 100.00% | 66.67% | 1.50 | quiet |
| `6b93fb76` | y | 9 | 0 | 8 (= 0 + 8) | 9 | 1 | 3 | 4 | 50.00% | 44.44% | 1.12 | quiet |
| `9fcf1507` | y | 9 | 0 | 9 (= 0 + 9) | 9 | 0 | 3 | 3 | 33.33% | 33.33% | 1.00 | quiet |
| `ea98e732` | y | 8 | 2 | 3 (= 2 + 1) | 8 | 0 | 0 | 0 | 0.00% | 0.00% | 2.67 | quiet |
| `800f9fe1` | y | 6 | 0 | 4 (= 0 + 4) | 6 | 2 | 2 | 4 | 100.00% | 66.67% | 1.50 | quiet |
| `4a2f351c` | y | 6 | 0 | 4 (= 0 + 4) | 6 | 0 | 2 | 2 | 50.00% | 33.33% | 1.50 | quiet |
| `b149a403` | y | 6 | 1 | 4 (= 1 + 3) | 6 | 0 | 1 | 1 | 25.00% | 16.67% | 1.50 | quiet |
| `8320ee8a` | y | 6 | 0 | 6 (= 0 + 6) | 6 | 0 | 2 | 2 | 33.33% | 33.33% | 1.00 | quiet |
| `a5857a02` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `9917ca35` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `b1569808` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `2786b72d` | y | 3 | 1 | 1 (= 1 + 0) | 3 | 0 | 0 | 0 | 0.00% | 0.00% | 3.00 | quiet |
| `7363c7ea` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `83d69605` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `8e56f6e1` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `b61452e6` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |
| `e715d36c` | y | 3 | 0 | 2 (= 0 + 2) | 3 | 1 | 1 | 2 | 100.00% | 66.67% | 1.50 | quiet |
| `816db7b3` | y | 3 | 0 | 3 (= 0 + 3) | 3 | 0 | 1 | 1 | 33.33% | 33.33% | 1.00 | quiet |

**ATTRIBUTION RESIDUAL `***` (not an office; excluded from both floors, never suppressed):** lines=75 · mails=9 · U-3 arrivals=33 · bookings=0 · share = 75/819 = **9.2%** of window office-bearing lines

---

## §5 THE DE-DUP FACTOR FOR `ccb52f4c`, AND THE PARKED/DECLINE CO-OCCURRENCE CHECK

### §5.1 The de-dup factor `f = lines / (A_id + A_noid)` — the arithmetic the ruled `r` rests on

| window | U-1 lines | U-3 arrivals (`A_id` + `A_noid`) | **`f`** | bookings U-3 | rate U-3 | ADR ceiling for K1 | verdict |
|---|---|---|---|---|---|---|---|
| A (8 d) | 552 | **369** (352 + 17) | **1.50** | 3 | 0.81 % | — | fires |
| **B (3 d)** | 371 | **188** (175 + 13) | **1.97** | 3 | 1.60 % | **`f` < 2.15** | **fires — UV-P DISCHARGED, `f` = 1.97 < 2.15** |
| C (3 d) | 262 | **99** (70 + 29) | **2.65** | 2 | 2.02 % | — | fires |

**ADR §11 UV-P #2 — DISCHARGED TRUE.** *"the de-duplication factor `f` for `ccb52f4c` over
09-09 .. 09-12 is below 2.15"*: measured **1.97**. K1 holds in window B, and it holds with the
`f`-margin the ADR designed for.

**But the margin the ADR reasoned about is not where the risk actually sits.** The ADR's arithmetic
held `bookings = 4` fixed and asked how far `f` could move. In the fresh measurement `f` moved past
2.15 in **window C** (2.65) *and the office still fires* — because `bookings` fell to 2 at the same
time. The real margins on the ruled `r = 0.025`:

| window | rate U-3 | margin to `r` | reading |
|---|---|---|---|
| A | 0.81 % | **×3.07** | comfortable |
| B | 1.60 % | **×1.57** | comfortable |
| **C** | **2.02 %** | **×1.24** | **the thinnest cell in the grid** — and it is the only window measured entirely in the live regime (FACT-2) |

> **Named risk for S1.3/S1.6, not a re-tune.** The founding office's live-regime margin is ×1.24.
> One additional booking in a 3-day window silences the page — and **the denominator moves with
> it**: `booking_completed` is *inside* the terminal set and carries no `message_id` (FACT-1), so an
> added booking increments `arr_noid` as well as `bookings`. Correctly under U-3 that is
> **`3/100 = 3.00 % > r`**, not `3/99 = 3.03 %`; the latter holds the denominator fixed, which is
> U-1's idiom inside a U-3 claim. The verdict is unchanged (both exceed `r = 2.5 %`) and the ×1.24
> margin is unaffected (`0.025 / 0.020202`), but the arithmetic is now in the unit this report rules in.

**Both halves, stated plainly — because only one of them is usually said.**

**Half one — the floor is behaving exactly as ruled.** ADR D1.2 chose P3 (the union) precisely so
that *any* evidence of a booking silences the floor, because a false page is the expensive error for
a consumer whose attention is the scarce resource. An office that books is not below the floor. The
×1.24 margin is not a malfunction; it is the ruled design meeting a quieter window.

**Half two — the ADR's safety argument does not bind the quantity that actually moved, and this is a
calibration hazard.** D1.5's *"×1.30 headroom"* was computed on the de-dup factor `f` **with bookings
pinned at 4** (`4f/344 < r ⇒ f < 2.15`). The fresh measurement shows `f` **blew through that ceiling**
in window C — **2.65 against a 2.15 bound** — and the founding office fired the RATE floor **anyway**,
because its bookings *fell* at the same time (3 in window B → **2** in window C; the ADR's arithmetic
held them at 4). **The quantity the ADR reasoned about is not the quantity that binds.** What binds is
the rate margin, and in the only window measured entirely in the live regime (FACT-2) it is **×1.24
and one event wide**.

> **Carried to the handoff as a CALIBRATION HAZARD, not a re-tune.** Re-ruling `r` is a VALUE fork
> (R-161: *"on K1/K2 failure the seat recedes to the operator, it does not re-tune"* — and K1 did not
> fail, so there is nothing here that even reaches the recede rule). What S1.3 and S1.6 must carry is
> that the ADR's headroom argument has been measured and found to be about the wrong variable, and
> that the live-regime margin should be watched on every soak day rather than assumed from D1.5.

> *A measurement note on the `bookings fell to 1` figure in circulation:* window C's booking count is
> **2**, not 1, on this seat's own-hands query and on the rite-disjoint critic's independent
> re-derivation. The `1` belongs to the pre-sitting measurement taken before window C closed (§0). The
> argument is unaffected — bookings fell, `f` rose past its ceiling, and the office fired regardless.

### §5.2 The `terminal_decline` / `terminal_decline_parked` co-occurrence — measured, not inferred

The ADR's FINDING-2 discharges co-occurrence *from source*. R-161's S1.1 contract requires it
**quantified**. `park_key` is the only field both events share (`terminal_decline_parked` carries
**no** `message_id`, FACT-1). **The query is pinned here, verbatim** — §2's thesis is that a
divergence between the query that ran and the query that is cited must be impossible by
construction, and that discipline binds this query too:

```
filter ispresent(park_key)
| stats count(*) as n,
        sum(if(event = "terminal_decline", 1, 0)) as td,
        sum(if(event = "terminal_decline_parked", 1, 0)) as tdp,
        count_distinct(event) as kinds
      by park_key
| stats count(*) as park_keys, sum(n) as lines by kinds, if(td > 0, 1, 0) as has_td, if(tdp > 0, 1, 0) as has_tdp
| sort park_keys desc
```

Window A · `status=Complete · recordsScanned=65,762 · recordsMatched=1,064 · bytesScanned=16,771,500 · estimatedRecordsSkipped=0 · logGroupsScanned=1`

| `kinds` | `has_td` | `has_tdp` | `park_key` count | lines | reading |
|---|---|---|---|---|---|
| **2** | 1 | 1 | **524** | 1,062 | **the two events ARE `terminal_decline` + `terminal_decline_parked`** |
| 1 | 1 | **0** | 2 | 2 | a decline that was never parked |
| 1 | 0 | 1 | **0** | 0 | an **orphan park** — does not occur |

**524 of 526 park events (99.6 %) emit both lines for the same mail.** A naive sum of the two events
over-counts by **524 mails in 8 days**. The ADR's ruling — `terminal_decline_parked` excluded from
the terminal set (D1.1) — is **confirmed correct by measurement**, and `U-3` is immune to the
double-count by construction.

**Two corrections to the first version of this section, both from the rite-disjoint critique.**
(a) The earlier fold printed only `count_distinct(event) as kinds by park_key`, and **`kinds = 2`
does not identify *which* two events** — it was consistent with any co-occurring pair and therefore
did not entail the sentence it was cited for. The `has_td` / `has_tdp` split above closes that: the
pair is named by the query, not by the prose. (b) The earlier statistics line was quoted against a
`filter ispresent(park_key)` variant while the query text printed in §2 omitted that filter; run
**un**filtered the same fold returns a third bucket — `kinds = 62 · park_keys = 1 · lines = 64,698`,
the no-`park_key` group — which the table silently dropped. The query above carries its filter.

**The residual's direction is the part a runbook needs, and it is benign.** The 2 asymmetric keys
are both `td = 1 / tdp = 0` — declines that were never parked. **Zero park events occur without a
matching decline**, so there is no orphan-park class and no lost-mail signal hiding in the residual.

**Correction to how the double-count must be detected.** The ADR states the over-count is visible as
message_ids carrying both events. It is **not**: `terminal_decline_parked` carries no `message_id`,
so that count is structurally 0 and would read as a false all-clear. The detectable key is
**`park_key`**. Any future guard against this class must key on `park_key`, not `message_id`.

---

## §6 SMOKE-LEAD SENSITIVITY (R-169)

**R-169 verbatim** (`origin/main:.ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md`):
*"**Test leads go through real offices with no marker today.** The replay runs with no exclusion plus
a sensitivity check; live evaluation counts them as arrivals; the convention is named by the operator
and codified (F5-1) **before** any arming."*

**Run with no exclusion: done.** Every table in §3 and §4 is the no-exclusion run. **Candidate
exclusions could not be constructed**: there is no marker field, no reserved guid, and no
`is_test` / `smoke` predicate anywhere on the office-bearing lines (the key census in §1 FACT-1
enumerates every key that appears; none of them discriminates a synthetic lead). The ADR's own
UV-P records the convention as **VERIFIED-ABSENT in code** at both repos. A side-by-side
"with each candidate exclusion" table is therefore **unconstructible, not omitted** — and the
sensitivity check R-169 asks for is supplied instead, in the form the charge requests: *how many
arrivals per office would have to be synthetic to flip each floor verdict.*

**Direction 1 — SILENCE a firing office** (how many of its measured arrivals must be synthetic before it goes quiet):

| win | guid8 | floor | arrivals U-3 | bookings | rate U-3 | `S_flip` | as % of its arrivals | binding constraint |
|---|---|---|---|---|---|---|---|---|
| A | `ccb52f4c` | **RATE** | 369 | 3 | 0.81% | **249** | 67.5% | rate (b/(a−S) ≥ r) |
| A | `87bd31d7` | ZERO | 33 | 0 | — | **29** | 87.9% | A (a−S < 5) |
| A | `e63bbbe0` | ZERO | 24 | 0 | — | **20** | 83.3% | A (a−S < 5) |
| A | `6b93fb76` | ZERO | 24 | 0 | — | **20** | 83.3% | A (a−S < 5) |
| A | `8a9b1a84` | ZERO | 15 | 0 | — | **11** | 73.3% | A (a−S < 5) |
| A | `40f86e73` | ZERO | 13 | 0 | — | **9** | 69.2% | A (a−S < 5) |
| A | `ea98e732` | ZERO | 8 | 0 | — | **4** | 50.0% | A (a−S < 5) |
| A | `5a19f1ad` | ZERO | 7 | 0 | — | **3** | 42.9% | A (a−S < 5) |
| A | `e5a68603` | ZERO | 6 | 0 | — | **2** | 33.3% | A (a−S < 5) |
| A | `cf6ae0f2` | ZERO | 6 | 0 | — | **2** | 33.3% | A (a−S < 5) |
| A | `2b591e43` | ZERO | 5 | 0 | — | **1** | 20.0% | A (a−S < 5) |
| A | `2786b72d` | ZERO | 5 | 0 | — | **1** | 20.0% | A (a−S < 5) |
| A | `735416d5` | ZERO | 5 | 0 | — | **1** | 20.0% | A (a−S < 5) |
| B | `ccb52f4c` | **RATE** | 188 | 3 | 1.60% | **68** | 36.2% | rate (b/(a−S) ≥ r) |
| B | `e63bbbe0` | ZERO | 14 | 0 | — | **10** | 71.4% | A (a−S < 5) |
| B | `8a9b1a84` | ZERO | 12 | 0 | — | **8** | 66.7% | A (a−S < 5) |
| B | `87bd31d7` | ZERO | 12 | 0 | — | **8** | 66.7% | A (a−S < 5) |
| B | `6b93fb76` | ZERO | 11 | 0 | — | **7** | 63.6% | A (a−S < 5) |
| B | `40f86e73` | ZERO | 9 | 0 | — | **5** | 55.6% | A (a−S < 5) |
| B | `2b591e43` | ZERO | 5 | 0 | — | **1** | 20.0% | A (a−S < 5) |
| C | `ccb52f4c` | **RATE** | 99 | 2 | 2.02% | **19** | 19.2% | rate (b/(a−S) ≥ r) |
| C | `e63bbbe0` | ZERO | 9 | 0 | — | **5** | 55.6% | A (a−S < 5) |
| C | `40f86e73` | ZERO | 8 | 0 | — | **4** | 50.0% | A (a−S < 5) |
| C | `8a9b1a84` | ZERO | 6 | 0 | — | **2** | 33.3% | A (a−S < 5) |

**Direction 2 — FALSELY FIRE a quiet office** (how many synthetic non-booking arrivals would push it over a floor):

| win | guid8 | arrivals U-3 | bookings | rate U-3 | synthetic arrivals to false-fire RATE |
|---|---|---|---|---|---|
| A | `933a026c` | 27 | 1 | 3.70% | **14** |
| A | `53295a22` | 19 | 1 | 5.26% | **22** |
| A | `8320ee8a` | 12 | 1 | 8.33% | **29** |
| B | `933a026c` | 21 | 1 | 4.76% | **20** |
| B | `53295a22` | 12 | 1 | 8.33% | **29** |
| B | `ed88a4a9` | 10 | 1 | 10.00% | **31** |
| C | `79be1b75` | 11 | 1 | 9.09% | **30** |
| C | `b149a403` | 4 | 1 | 25.00% | **37** |
| C | `7363c7ea` | 3 | 1 | 33.33% | **38** |

**Direction 2b — FALSELY FIRE the ZERO floor** (offices sitting just under A = 5 with zero bookings):

| win | offices with 0 bookings and arrivals < A=5 | closest guid8s (arrivals → synthetic needed) |
|---|---|---|
| A | 18 | `7081d9d4` (4→1), `fa59bf58` (4→1), `783b40aa` (4→1), `2943ade4` (3→2) |
| B | 17 | `7081d9d4` (2→3), `e5a68603` (2→3), `ea98e732` (2→3), `1c20d27c` (2→3) |
| C | 4 | `e5a68603` (3→2), `ea98e732` (3→2), `9917ca35` (1→4), `2786b72d` (1→4) |

### §6.1 What the arithmetic says

| | **FLOOR-RATE (the primary class)** | **FLOOR-ZERO (the secondary class)** |
|---|---|---|
| Silencing the true positive | needs **249 / 68 / 19** synthetic arrivals (**67.5 % / 36.2 % / 19.2 %** of `ccb52f4c`'s entire traffic) | needs **1** synthetic arrival for the 3 window-A members sitting at exactly `arrivals = 5` |
| Creating a false positive | needs **≥ 14** synthetic non-booking arrivals on the nearest quiet office (`933a026c`, window A) | needs **1** synthetic arrival for each of the 3 window-A offices sitting at `arrivals = 4` |
| **Verdict** | **ROBUST.** No plausible smoke-lead volume reaches these numbers. The founding case cannot be created or destroyed by test traffic. | **FRAGILE at the boundary.** The ZERO floor's smoke exposure is **± 1 arrival**, and 18 offices sit below `A = 5` with zero bookings in window A. |

**Consequence, stated plainly:** R-169's uncharacterised smoke channel is **immaterial to the class
the instrument was chartered on** and **material to its secondary class**. This is consistent with
the ADR's own ordering (*"the RATE floor is the primary class; the zero floor is the secondary"*)
and it gives the operator a sized answer to the F6 fork: the smoke-lead convention must be codified
**before the ZERO floor is armed**, and need not gate the RATE floor. That is a ruling this seat
does not take — it is recorded as the measurement the operator asked for.

---

## §7 K1–K5 — EVALUATED EXACTLY AS THE ADR STATES THEM

### K1 — `ccb52f4c` fires the **RATE** floor under `(U-3, A′ = 20, r = 0.025)` in all three windows

| window | arrivals U-3 | ≥ A′ = 20 ? | bookings U-3 | ≥ 1 ? | rate U-3 | < r = 0.025 ? | **FIRES?** |
|---|---|---|---|---|---|---|---|
| A (8 d) | 369 | yes | 3 | yes | 0.81 % | yes (×3.07) | **YES** |
| B (3 d) | 188 | yes | 3 | yes | 1.60 % | yes (×1.57) | **YES** |
| C (3 d) | 99 | yes | 2 | yes | 2.02 % | yes (×1.24) | **YES** |

**K1 — PASS.** No re-tune performed, none required. (Margin in window C is ×1.24 — recorded as a
named risk in §5.1, not as a threshold change.)

### K2 — every office whose U-3 booking rate is ≥ 7 % is quiet under **both** floors, all three windows

| window | offices with U-3 rate ≥ 7 % | of those, firing FLOOR-RATE | firing FLOOR-ZERO | breaches |
|---|---|---|---|---|
| A | 27 | 0 | 0 | **0** |
| B | 28 | 0 | 0 | **0** |
| C | 29 | 0 | 0 | **0** |

**K2 — PASS, but scored as a CONSISTENCY CHECK, not an independent gate.**

K2 is **tautological given K1's floors** and this report says so rather than banking the bit:
`rate ≥ 7 %` ⇒ `bookings ≥ 1` ⇒ FLOOR-ZERO excluded **by construction**; and `7 % > r = 2.5 %` ⇒
FLOOR-RATE excluded **by construction**. K2 therefore **cannot fail** unless the evaluator computes
the selection rate and the floor rate by different code paths — which is a real defect class, and
is the only thing K2 actually tests. The 84 office-windows swept above confirm the two paths agree.

**What K2 should become at S1.3 (carried to the handoff):** a test that *can* fail — e.g.
*"no office with ≥ 1 booking and rate ≥ 7 % in the PRIOR rolling window fires in the CURRENT
window"*. A cross-window form has genuine falsifying power; the within-window form does not.

### K3 — the ZERO floor's firing set, fully enumerated and class-labelled, no unexplained member

Ruled setting `(U-3, A = 5)`. **Class labels are the ruled E2 Offer-grain snapshot**, not a proxy.

**Correction, from the rite-disjoint critique (DEF-1).** The first version of this report declared the
E2 snapshot source *"VERIFIED-ABSENT"* and labelled these members from a 30-day booking-history proxy
— the **E4** option ADR D5.1 explicitly rejected as *"a proxy, not the class"*. **That absence call was
wrong, and it was wrong because the probe was narrower than the claim**: `git ls-tree -r origin/main`
plus a working-tree grep can establish "not on `origin/main`"; only a **ref-wide** probe can establish
"not resolvable", and it was never run. Corrected scope, own-hands receipts:

```
git cat-file -e origin/main:.ledge/reviews/READ-offer-activity-sizing-2026-09-11.md
  -> fatal: path does not exist in 'origin/main'                                   rc=128
git log --all --oneline --diff-filter=A -- '*offer-activity-sizing*' '*SNAPSHOT-offer-class*'
  -> 84186c6d docs(reviews): land the 09-11 offer-grain sizing read and the E2 class snapshot   rc=0
git merge-base --is-ancestor origin/docs/e2-offer-class-snapshot-2026-09-14 origin/main
  -> rc=1   (not an ancestor of main)
git show origin/docs/e2-offer-class-snapshot-2026-09-14:.ledge/reviews/SNAPSHOT-offer-class-2026-09-11.json
  -> 29 guid8 -> class rows; branch head 5c2e1cae                                   rc=0
```

**The corrected claim: the E2 snapshot is ABSENT AT `origin/main` and PRESENT on the named branch**
`docs/e2-offer-class-snapshot-2026-09-14` (PR #449, armed) at
`.ledge/reviews/SNAPSHOT-offer-class-2026-09-11.json` — `snapshot_date = 2026-09-11`,
**29 `guid8 → class` rows**, `fallback = "unknown"`, `stale_after_days = 30`, source report beside it.
It is a **build input available to S1.3 today**, not a gap to route to the operator.

The table below is re-labelled from that snapshot. Where the snapshot covers a member its E2 class is
authoritative; where it does not the member renders **`class=unknown`** per D5.1 rule 2 (never blank,
never inferred). The 30-day booking column is **retained only as a clearly-labelled comparison** — it
is not the label and it is not a build input.

| win | guid8 | arrivals U-3 | **E2 class (snapshot 2026-09-11)** | D8.1 section | name? | 30 d bookings *(proxy — comparison only)* | unexplained? |
|---|---|---|---|---|---|---|---|
| A | `87bd31d7` | 33 | **inactive** | [2] EXPECTED SILENCE | y | 12 | **no** |
| A | `e63bbbe0` | 24 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `6b93fb76` | 24 | **inactive** | [2] EXPECTED SILENCE | y | 4 | **no** |
| A | `8a9b1a84` | 15 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `40f86e73` | 13 | **inactive** | [2] EXPECTED SILENCE | y | 0 | **no** |
| A | `ea98e732` | 8 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `5a19f1ad` | 7 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | **n** | 0 | **no** |
| A | `e5a68603` | 6 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `cf6ae0f2` | 6 | **inactive** | [2] EXPECTED SILENCE | y | 0 | **no** |
| A | `2b591e43` | 5 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `2786b72d` | 5 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A | `735416d5` | 5 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| B | `e63bbbe0` | 14 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| B | `8a9b1a84` | 12 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| B | `87bd31d7` | 12 | **inactive** | [2] EXPECTED SILENCE | y | 12 | **no** |
| B | `6b93fb76` | 11 | **inactive** | [2] EXPECTED SILENCE | y | 4 | **no** |
| B | `40f86e73` | 9 | **inactive** | [2] EXPECTED SILENCE | y | 0 | **no** |
| B | `2b591e43` | 5 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| C | `e63bbbe0` | 9 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| C | `40f86e73` | 8 | **inactive** | [2] EXPECTED SILENCE | y | 0 | **no** |
| C | `8a9b1a84` | 6 | `unknown` (not in snapshot) | [3] CLASS UNKNOWN | y | 0 | **no** |
| A/B/C | `***` | — | n/a — not an office | [4] ATTRIBUTION RESIDUAL | — | — | **no** |

- window **A**: snapshot covers **4 of 12** ZERO members; **8** render `class=unknown`.
- window **B**: snapshot covers **3 of 6** ZERO members; **3** render `class=unknown`.
- window **C**: snapshot covers **1 of 3** ZERO members; **2** render `class=unknown`.

Snapshot coverage of the two offices that matter most elsewhere in this report:
- `ccb52f4c` — **`active`** → renders in **[1] ACTIONABLE** — the FLOOR-RATE firing office (K1)
- `933a026c` — **`ignored`** → renders in ****no ADR section**** — the K4 quiet-side anchor

**K3 — PASS. Every member is explained; there is no unexplained member in any window.**

Three findings inside the PASS that the builder and the runbook need:

- **Snapshot coverage of the ZERO firing set is partial: 4 / 12 · 3 / 6 · 1 / 3.** Eight of the twelve
  window-A members render `class=unknown`. So the readability concern this report raised **survives at
  8/12, not 12/12** — the finding stands, its magnitude is one third smaller than first stated, and the
  cure is a snapshot re-run over the plane's office set (already a defer in the snapshot's own `note`),
  **not** a re-take of the Asana read.
- **`933a026c` carries `class = "ignored"` — a FIFTH class value with no ADR D8.1 section.** D8.1 maps
  `active|activating` → `[1] ACTIONABLE`, `inactive|dark` → `[2] EXPECTED SILENCE`, `unknown` →
  `[3] CLASS UNKNOWN`. The snapshot's vocabulary is `{active, activating, inactive, ignored}` and
  **`ignored` falls through every section.** A row matching no section is a blank-page risk against
  telos Law 4. S1.3 must either map `ignored` or reject it at load. Raised as a UV-P (§9).
- **The two members the 30-day proxy called "genuine stalls" are `inactive` at the Offer grain.**
  `87bd31d7` (12 bookings in 30 d) and `6b93fb76` (4 in 30 d) are **`inactive`** in the E2 snapshot —
  the proxy and the ruled class **disagree**, which is exactly why the ADR rejected E4. Under the ruled
  labels both render in `[2] EXPECTED SILENCE`. This is the `15caa02c` books-while-dark pattern
  (charge §7) appearing twice more: an Offer-grain data question, not a floor question.
- **`ccb52f4c`, the FLOOR-RATE firing office, is `class = active`** — it renders in
  **`[1] ACTIONABLE`**, which is the section the founding case must land in for the page to do its job.

### K4 — `933a026c` is quiet in all three windows, and the receipt states why

| window | U-1 lines | arrivals U-3 (`A_id` + `A_noid`) | bookings U-3 | rate U-3 | FLOOR-ZERO? | FLOOR-RATE? |
|---|---|---|---|---|---|---|
| A | 28 | 27 (0 + 27) | 1 | **3.70 %** | no (`bookings ≥ 1`) | no (3.70 % > 2.5 %) |
| B | 22 | 21 (0 + 21) | 1 | **4.76 %** | no | no |
| C | 12 | 12 (0 + 12) | 4 | **33.33 %** | no | no |

**K4 — PASS, and the ADR's closed-form proof is confirmed on both of its legs:**

1. **The rate leg holds, and it is the operative one.** The ADR's argument was `1 booking / ≤ 27
   arrivals ⇒ rate ≥ 3.70 % > r` whatever the de-dup factor. Measured: `A_id = 0` in all three
   windows, so `arrivals = A_noid = ` the terminal-line count exactly, and the rate lands at
   **3.70 % / 4.76 % / 33.33 %** — above `r` in every window, with the tightest margin **×1.48** in
   window A. This is the margin the ADR predicted.
2. **The secondary leg is FALSIFIED as stated, and it does not matter.** The ADR speculated
   `933a026c` might also be "plausibly below `A′ = 20`". It is **not**: arrivals are 27 / 21 / 12,
   so it clears `A′ = 20` in windows A and B. **Only the rate leg keeps it quiet.** The receipt
   states which of the two kept it quiet, as K4 requires: **the rate leg, in every window.**

### K5 — `recordsScanned` reported for every query and comparable to the control

| query | window | status | recordsScanned | recordsMatched | bytesScanned | estRecSkipped | logGroups |
|---|---|---|---|---|---|---|---|
| `Q-S1` (pinned) | A | Complete | 65,762 | 1,659 | 16,771,500 | 0 | 1 |
| `Q-S1` (pinned) | B | Complete | 31,007 | 1,152 | 7,953,053 | 0 | 1 |
| `Q-S1` (pinned) | C | Complete | 13,464 | 819 | 3,657,761 | 0 | 1 |
| `Q-S1` (pinned) | 30 d | Complete | 603,344 | 4,637 | 155,221,152 | 0 | 1 |
| per-event census | A | Complete | 65,762 | 1,659 | 16,771,500 | 0 | 1 |
| attribution-class census | A | Complete | 65,762 | **65,762** | 16,771,500 | 0 | 1 |
| attribution-class census | B | Complete | 31,007 | 31,007 | 7,953,053 | 0 | 1 |
| attribution-class census | C | Complete | 13,464 | 13,464 | 3,657,761 | 0 | 1 |
| per-day regime control | 09-04..09-14 | Complete | 72,615 | 2,341 | 18,642,526 | 0 | 1 |
| `park_key` co-occurrence (chained `stats`) | A | Complete | 65,762 | 1,064 | 16,771,500 | 0 | 1 |
| `office_identity_kind` census | 09-04..09-14 | Complete | 72,615 | 2,052 | 18,642,526 | 0 | 1 |

**K5 — PASS.** The **control** is the unfiltered scan: the attribution-class census over each window
matches `recordsMatched` to `recordsScanned` exactly (65,762 / 31,007 / 13,464), proving the scan
reached every record the filtered queries could have reached. Every filtered query over the same
window reports the **identical** `recordsScanned` and `bytesScanned` as its control — which is also
a direct own-hands confirmation of ADR D6.1 (*"Insights bills SCANNED, not MATCHED; a `filter` buys
exactly zero cost reduction"*). No zero in this report is an unscanned zero.

### Verdict

| gate | result |
|---|---|
| **K1** | **PASS** — with the window-C margin at **×1.24, one booking wide** (§5.1); the margin is a named calibration hazard, not a re-tune |
| **K2** | **PASS — consistency check, not an independent gate** (tautological given K1's floors; see above) |
| **K3** | **PASS** |
| **K4** | **PASS** |
| **K5** | **PASS** |
| **RECEDE rule (ADR D1.7)** | **NOT TRIGGERED.** K1 and K2 both pass; nothing was re-tuned. S1.1 exits to S1.2 ‖ S1.3. |

---

## §8 THE FOUR §2(ii) COLUMNS — defined for the live control

Charge §2(ii) requires that on production traffic the instrument **EVALUATES** (non-zero evaluations
measured, with a firing control on the identical query shape). ADR D3.4 / §10 row D3 require the
four columns **never summed into one number**. This sprint produces the **historical** positive
control (§4, §7 K1); the **live** control is S1.6's seven-day soak. The four columns are DEFINED
here so S1.6 measures the thing S1.1 specified.

| # | column | definition (measurement method, per UTC day) | expected value under the ruled cadence | what a wrong value means |
|---|---|---|---|---|
| **1** | `evaluations/day` | `count(*)` of `office_floor_evaluated` log lines emitted by the evaluator, `stats count(*) by bin(1d)` over the evaluator's own log group. Counts **every** invocation that completed the pinned query, **regardless of control outcome or page outcome**. | **24** (hourly EventBridge, ADR D3) | `< 24` → schedule gaps or crashes: cross-check signal #1 (`…-lambda-freshness`) and #3 (`${name}-lambda-errors`). `0` → the instrument is dark and the prober deadman must already be firing. |
| **2** | `controlled evaluations/day` | `sum(if(control_status = "PASS", 1, 0))` over the same lines — the subset whose **in-run control** (ADR D2.6 / L3) passed: `query_status = Complete` **AND** `records_scanned` comparable to the day's baseline **AND** `offices_with_bookings > 0`. | **24** in a healthy day | `< evaluations/day` → the evaluator ran but its read was untrustworthy; each shortfall must have a matching `FLOOR-REFUSED` publish. **`evaluations/day > 0` with `controlled = 0` is the exact "green light over an unread substrate" failure the epoch exists to end.** |
| **3** | `pages/day` | `sum(if(paged = true, 1, 0))` over the same lines — SNS publishes actually issued. | **0 or 1** (D8.1: at most ONE publish per UTC day, gated on `hour == 11`Z) | `> 1` → the publish gate leaked; `0` on a day when `zero_floor_count + rate_floor_count > 0` **and** `controlled = 24` → the page path is broken while the evaluation path is healthy: the silent-instrument class. |
| **4** | `page-class distribution` | `stats count(*) by page_class` over the same lines, `page_class ∈ {digest, refused, none}`; **and**, within `digest`, the split `{FLOOR-ZERO members, FLOOR-RATE members}` carried from `zero_floor_count` / `rate_floor_count`. Reported as a vector, **never collapsed to a total**. | `none` × 23, `digest` × 1 | `refused > 0` → column 2 shortfall corroborated from the page side (two-sided). `digest` with `zero_floor_count = 0 AND rate_floor_count = 0` → a blank page was published, violating telos Law 4. |

**Two-sidedness of the control.** Column 1 alone cannot distinguish "ran and read correctly" from
"ran and read nothing" — that is column 2's job (the in-run control). Column 3 alone cannot
distinguish "nothing to say" from "could not speak" — that is column 4's job (the `refused` class).
**A control proves the PROBE ran; it cannot prove the SUBJECT runs** (charge §2). The subject-live
evidence is columns 1+2 measured on production traffic; §4 of this report is its historical half.

**Baseline `records_scanned` for column 2's comparability test**, from this sprint's own-hands
measurement of the 3-day rolling window: **~13.5 k – 31 k records / ~3.7 – 8.0 MB per evaluation**
(window C and window B respectively; the spread is real day-to-day traffic variance, so the
control's threshold must be a floor — e.g. `records_scanned > 1,000` — not an equality).

---

## §9 UV-P REGISTER — frozen syntax, carried to the handoff

```
[UV-P: the E2 offer-class snapshot at origin/docs/e2-offer-class-snapshot-2026-09-14 .ledge/reviews/SNAPSHOT-offer-class-2026-09-11.json will be on origin/main by S1.3 entry, and its 29 rows will still be within stale_after_days=30 of snapshot_date 2026-09-11 | METHOD: git merge-base --is-ancestor against origin/main re-run at S1.3 entry, plus a date check; if PR #449 has not merged the builder reads it from the named branch ref, which resolves today | REASON: CORRECTED CLAIM - the first version of this report said VERIFIED-ABSENT on the strength of an origin/main-only probe, which cannot decide resolvability. Own-hands ref-wide probe: absent at origin/main (rc=128), present on the named branch at head 5c2e1cae (rc=0). It is a build input available today. Residual: the snapshot covers 4 of 12 window-A ZERO members, so 8 render class=unknown until the sizing resolver is re-run over the plane's office set]

[UV-P: the E2 snapshot class value "ignored" maps to one of ADR D8.1's four page sections | METHOD: rule it at S1.3 - either map ignored to a section or reject the value at snapshot load | REASON: VERIFIED-UNMAPPED by this seat. D8.1 enumerates active/activating, inactive/dark, unknown and the residual; the snapshot vocabulary is {active, activating, inactive, ignored}. 933a026c carries ignored and matches no section, which is a blank-page risk against telos Law 4]

[UV-P: the per-office arrival denominators measured in windows A and B transfer to the live regime | METHOD: re-run Q-S1 over a fully post-09-11 3-day window at S1.6 and compare per-office arrivals against the window-B cell | REASON: FALSIFIED-IN-PART by this seat's per-day control (FACT-2): 883 terminal outcomes in window A and 389 in window B carry no office guid field at all and are absent from every office's denominator; the class is exactly zero from 2026-09-11. Window C is the only window measured entirely in the live regime and it is the tightest cell in the grid (ccb52f4c margin x1.24)]

[UV-P: contente_booking_allowlist_suppressed (4 office-bearing lines in window A) is correctly EXCLUDED from the ADR D1.1 terminal set | METHOD: read the emitter at autom8y origin/main services/email-booking-intake/src/** and rule it terminal or non-terminal at S1.3 | REASON: the event is office-bearing and was not enumerated in ADR D1.1's ten-row table; this seat does not add events to a ruled set. At 4 lines / 8 days it cannot move any K-gate, but an unclassified terminus is the silent-miss class]

[UV-P: the office_name field resolves for every office the live instrument will page | METHOD: the builder renders the guid-prefix-only row path and proves no crash and no drop (ADR §10 row D5 receipt b) | REASON: MEASURED-FALSE historically - 13 of 61 offices in window A (21 percent) and 6 of 54 in window B carry no resolvable office_name on any line; 0 of 38 in window C. The <guid8> em-dash render path is exercised by real traffic, not hypothetical]

[UV-P: a naive sum of terminal_decline and terminal_decline_parked can be detected as message_id values carrying both events, as ADR D1.4 specifies | METHOD: key the detection on park_key instead | REASON: VERIFIED-FALSE by this seat - terminal_decline_parked carries NO message_id on any of its 149 window-A lines, so the message_id co-occurrence count is structurally 0 and reads as a false all-clear. Measured on park_key the co-occurrence is 524 of 526 keys (99.6 percent)]

[UV-P: U-3's A_id branch performs de-duplication, making the unit retry-deflated as ADR D1.2 states | METHOD: re-measure count_distinct(message_id) vs sum(ispresent(message_id)) per event after U-4 lands (DEFER 12.2) | REASON: VERIFIED-FALSE for these windows - the two are equal at 533 on terminal_decline and message_id appears on no other event. U-3 remains the correct unit because it strips stage_exception and terminal_decline_parked, but its de-dup property is zero today and its booking denominator is 100 percent fallback]

[UV-P: the smoke-lead convention can be expressed as a candidate exclusion predicate over the log plane | METHOD: operator word per R-169 / F5-1, then re-run Q-S1 with the exclusion and diff the office set against this report's no-exclusion tables | REASON: no marker field exists on any office-bearing line (full key census taken this sprint); R-169 states it verbatim. The side-by-side exclusion table R-161 asks for is UNCONSTRUCTIBLE, not omitted; the flip-sensitivity arithmetic of section 6 is supplied in its place]

[UV-P: the two pre-sitting measurements named in the shape's context block were taken over the same window bounds and query shape as this sprint | METHOD: none available - the outputs record window labels but not epoch bounds or the query text | REASON: their window-A figure for ccb52f4c (580 lines / 4 booking_completed) does not reproduce here (552 / 3) and their window-C scan is roughly half this seat's because window C had not closed when they ran. Nothing in this report is inherited from them; the divergence is recorded so it is not rediscovered]
```

---

## §10 WHAT THIS SPRINT DOES **NOT** DO

1. **It does not re-tune any threshold.** `A = 5`, `A′ = 20`, `r = 0.025`, `W = 3 d`, `U-3` and
   `P3` are R-150/R-161 as ruled. Where the fresh measurement supports a different reason for a
   ruling (`r = 0.020` rejection) the ruling is confirmed and the reason is corrected in place.
2. **It does not rule on the `contente_booking_allowlist_suppressed` event** (UV-P above).
3. **It does not choose the page-repeat policy** (D7, operator's), the consumer word (F4,
   operator's), or the smoke-lead practice (F6, operator's) — it sizes the third one (§6).
4. **It does not build, apply, arm, or mutate anything.** Read-only throughout: `logs:StartQuery` and
   `logs:GetQueryResults` only.

## §11 EVIDENCE GRADE AND ANTI-THEATER SELF-CHECK

**Grade: MODERATE** — single seat, no rite-disjoint corroboration (`self-ref-evidence-grade-rule`).
The shape assigns `qa-adversary` as this sprint's rite-disjoint critic; that critique has not run.

| check | result |
|---|---|
| Every zero paired with a firing control on the identical call shape? | Yes — §7 K5; the attribution-class census is the unfiltered control and matches `recordsMatched` to `recordsScanned` exactly in all three windows. |
| Any number inherited rather than measured? | **No.** The two inherited pre-sitting measurements are explicitly *not* used; their divergence is recorded as a UV-P. Every figure is this seat's own query with its statistics block printed. |
| Did the seat's own probe match the width of its own claim? | **No — and this is the defect the rite-disjoint critique caught (DEF-1).** An `origin/main`-scoped probe was used to assert *unresolvability*, which it cannot decide. The corrected claim is scoped (`absent at origin/main, present on the named branch`) and the ref-wide command is printed. Recorded here rather than quietly fixed: **the same narrow-probe error is exactly the class this report accuses the ADR of elsewhere.** |
| Does the report merely ratify the ADR? | **No.** It **falsifies** U-3's stated de-dup rationale (FACT-1), **falsifies** the ADR's specified detection key for the parked/decline double-count (§5.2), **falsifies** K4's secondary leg (§7 K4), **discovers** a mid-window substrate regime break the ADR did not know about (FACT-2), **discharges** two ADR UV-Ps by measurement (chained `stats`; `f` < 2.15) and **discharges** a third (`***` composition). Every ruling nonetheless survives. |
| Is any headline claim checked against its own discipline? | Yes, and one was caught: the fold from `(office_guid, office_nm)` to `office_guid` was **not** assumed safe — it was diffed field-by-field against a separate by-guid-only run (0 mismatches, 3 windows), and the reason it is safe (FACT-1) is stated along with the condition under which it stops being safe (U-4). |
| Does any conclusion rest on a number this seat did not measure? | **No longer.** The first version's K3 labels were 30-day plane proxies resting on a **false absence call** for the E2 snapshot; the rite-disjoint critique falsified it and the labels are now the ruled E2 snapshot (§7 K3). The residual is honest coverage, not inference: 8 of 12 window-A members are `class=unknown` because the snapshot does not reach them. |
| Fences honoured | guid8 only; **no office names printed** (ADR D8.1 binds `.ledge` artifacts to guid8); no phone digits; no reads under other worktrees or `.terraform/`; bounded Insights polling; rc unpiped; `"${REF}:path"` for git reads; read-only AWS. |

**The acid test — *can we catch degradation before customers do with this monitoring?*** For the
RATE class, yes and with room: the founding office is named in every window, it carries
`class = active` so it lands in `[1] ACTIONABLE`, no plausible smoke-lead volume can silence it, and
the firing set is one office wide. For the ZERO class, **conditionally**: it catches real stalls but
its boundary is one arrival wide and it fires 12 offices in 8 days. With the ruled E2 snapshot applied
(§7 K3), **4 of those 12 are class-labelled and 8 render `class=unknown`** — so the reader's triage
load is real but **one third smaller than the first version of this report claimed**, and the cure is
a snapshot re-run over the plane's office set, which the snapshot's own `note` already carries as a
defer. **The E2 snapshot is not a cosmetic — it is what makes the ZERO class readable — and it
exists.** That, and the `ignored` class value that maps to no page section, are the sharpest things
this sprint hands S1.2 and S1.3.

---

## §12 DEFECT-CORRECTION LOG — rite-disjoint critique applied

Critique: `qa-adversary` (10x-dev, rite-disjoint to sre), verdict **PASS-WITH-DEFECTS**, posted on
PR #448. Every headline figure in this report was re-derived by the critic own-hands and reproduced
**exactly** — per-office rows, firing sets, ZERO membership, `S_flip` arithmetic and the four-field
statistics block. **No K-gate failed on rite-disjoint re-derivation, and nothing was re-tuned.**

| # | defect | severity | what changed in this artifact |
|---|---|---|---|
| **DEF-1** | E2 snapshot declared `VERIFIED-ABSENT`; the probe was `origin/main`-scoped while the claim was resolvability-scoped | **MEDIUM** | §7 K3 re-labelled from the ruled E2 snapshot (`origin/docs/e2-offer-class-snapshot-2026-09-14`, 29 rows); the 30-day proxy demoted to a labelled comparison column; the claim re-scoped to *"absent at `origin/main`, present on the named branch"*; UV-P #1 re-pointed and *"re-take the Asana read"* struck; §11 and the acid test corrected; coverage sized honestly at 4/12 · 3/6 · 1/3 |
| **DEF-2** | `3/99 = 3.03 %` held the denominator fixed — U-1 arithmetic inside a U-3 claim | LOW-MED | §5.1 flip sentence corrected to **`3/100 = 3.00 %`**, with the reason (`booking_completed` is in the terminal set and carries no `message_id`, so it increments `arr_noid` too). Verdict and ×1.24 margin unchanged |
| **DEF-3** | §5.2's `kinds = 2` fold did not identify *which* two events; its query text was never pinned; its statistics line came from a filtered variant of an unfiltered printed query | LOW | §5.2 rewritten: query pinned verbatim with its filter, `has_td`/`has_tdp` split added so the pair is named **by the query**, the dropped third bucket disclosed, and the residual's direction stated (**zero orphan parks**) |
| **DEF-4** | K2 scored as an independent gate though it is tautological given K1's floors | LOW | §7 K2 re-scored as a **consistency check**, the tautology stated in the gate body and the verdict table, and a cross-window form with real falsifying power handed to S1.3 |
| **DEF-5** | `status:` frontmatter readable by a machine as "R1 realized"; K1 line carried no margin caveat | LOW | frontmatter → `S1.1 COMPLETE — design proof; K1..K5 PASS; instrument NOT BUILT, NOT ARMED; R1 NOT realized (R-168)`; verdict line and K1 row carry the scope and the ×1.24 margin |

**Two corrections made this artifact's claims narrower, not wider** (DEF-1 shrank the readability
finding by a third; DEF-4 removed a gate's worth of asserted evidential width), and **one strengthened
a conclusion** (DEF-3: the park residual is now known to be one-directional and benign). The
measurement layer required no change.

**Still true after correction:** RECEDE **not triggered**; K1–K5 **PASS**; nothing re-tuned; the
instrument is **not built and not armed**; **R1 is NOT realized** (R-168).
