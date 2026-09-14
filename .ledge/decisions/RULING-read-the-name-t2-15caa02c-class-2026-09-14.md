---
type: ruling
initiative: read-the-name
node: T2 (critic: pythia adjudicates the class)
object: asana #454 → 24886bca · .ledge/reviews/READ-read-the-name-15caa02c-books-while-dark-2026-09-14.md
provenance: posted by pythia as PR review 5194481909 on autom8y/autom8y-asana#454 at 2026-09-14T06:18:38Z; transcribed verbatim here so the ruling has a file:line anchor on main (Gate C flag F-4)
date: 2026-09-14
---

# RULING — read-the-name T2 · the class of office `15caa02c`

Verbatim body of pythia's review (PR #454, review id 5194481909). Nothing edited; the READ it rules on is the measurement, this is the verdict.

---

**VERDICT — CERTIFY-WITH-ERRATA (E-1, E-2).** Class of `15caa02c` for this wave's record: **`inactive` at the Offer grain with an UNRECORDED transition — expressly NOT ruled "stale"**; the E2 snapshot is **LEFT AS-IS** (there is no row to correct — `15caa02c` is absent from all 29 rows, so the page already renders `class=unknown`); E-2's wire-decides **is** sufficient for this office today, by two independent branches; the pre-2026-10-09 "no booking in 30 d" branch is a **dated calibration hazard**, cured by a **computed** attribution floor printed on the page (no re-tune of A/A′/r); `SIZING-15caa02c` **"NO WATCHER" is SUPERSEDED by erratum E-2** and re-stamps to WATCHED-AS-STALL with the naming half owned by S-1 and the provenance half deferred to WS-2.

---

**Seat:** pythia · **Node:** `read-the-name` wave 1, charge-DAG **T2** (critic/adjudication) · **Mode:** READ-ONLY, rules-does-not-re-measure. Nothing measured here; every number below is the station's, cited.

**Refs of record (named, not inherited from a checkout):** autom8y-asana `origin/main` = **`2ef49ff6`** · READ under adjudication = PR #454 `FETCH_HEAD` **`a13ba69d`** · ADR `ADR-read-the-name-s1-implementation-2026-09-14.md`, snapshot `SNAPSHOT-offer-class-2026-09-11.json`, sizing read `READ-offer-activity-sizing-2026-09-11.md`, all read at `origin/main` `2ef49ff6`. (The working tree shows these as untracked; that is a stale-tree artifact — they are on `origin/main`. Named per the worktree/decoy scar.)

**Fence:** guid8 only; no task/project GIDs reproduced; no client names; no phone digits.

---

## R-1 — THE CLASS of `15caa02c`, and the disposition of the snapshot row

### R-1.a A fact that reframes the question: **there is no row to correct.**

`SNAPSHOT-offer-class-2026-09-11.json` at `origin/main` carries **29 guid8 keys. `15caa02c` is not one of them.** Under **D5.1 rule 2** ("a guid absent from the snapshot renders `class=unknown` — never blank, never inferred, never suppressed"), the S-1 page renders this office **`class=unknown` today**, not `inactive`. The dispatch's fork — "corrected by hand, annotated, or left as-is" — presupposes an extant row. The live options are therefore *insert*, *annotate*, or *leave*.

### R-1.b RULED — the class for the record

> **`15caa02c` = `inactive` at the Offer grain (measured twice: offline resolver over the 2026-09-11 dumps, and a live refreshed pass 2026-09-14), carrying a NAMED PROVENANCE DEFECT — the transition into `INACTIVE` is unrecorded across a complete 354-story pagination — while the office is LIVE ON THE WIRE (108 U-3 terminal outcomes on 21 of 31 days, 91 % of the active control's volume).**
>
> **On the page: `class=unknown` (no snapshot row).** The record string is the finding; `unknown` is the render.

**REJECTED — `active (Asana section stale)`.** *Discriminator:* the **Unit grain independently reads dark (`Paused`) and its darkening IS properly recorded** (`Month 1 -> Paused`, 2025-04-27). Two Asana grains agree on "dark"; one of them has clean provenance. Ruling "stale" declares both wrong on the strength of one grain's *missing* story. The station's own falsifier (c) — that `INACTIVE` is the **correct** present label and the **bookings** are the anomaly (a parked office being worked by the live wire) — is not merely unexcluded, it is **corroborated** by the Unit. The evidence taken measures the Asana plane and the log plane; **neither carries the serving/billing fact that would discriminate "label is stale" from "parked client is being served."** That is the missing discriminator, and it is not in this READ's scope to have had.

**REJECTED — `inactive-by-label / live-by-wire` as a minted sixth class.** *Discriminator:* divergence is a **page-time JOIN (snapshot × plane)**, not a snapshot value. The snapshot is a build-time constant baked from a dated Asana read (D5.1 "shape"); it structurally cannot carry a value that depends on the log plane. **Erratum E-2 already computes this exact join** via `last_booking_age_days`. Minting the class would duplicate E-2's mechanism as a label and would require the static file to know the wire. Rejected for the same reason D5.2 rejected E1: wrong object.

**REJECTED — hand-insert `"15caa02c": "inactive"` into the snapshot.** Three independent reasons, any one sufficient:
1. **Provenance break.** The file's `source` names a dated live Asana read and `vocabulary` names its derivation; a hand value is un-sourced and falsifies both fields for the whole file.
2. **It is strictly harmful to visibility.** Under E-2, `class=unknown` + no booking in 30 d → **CLASS UNKNOWN**; `class=inactive` + no booking in 30 d → **EXPECTED SILENCE**. Inserting `inactive` would move this office **out of the operator's eye the moment it stops booking** — reproducing, for the single office this wave exists to name, the founding silence E-2 was written to prevent.
3. It repairs a symptom while leaving the file's population claim unverified for the other 28 (see R-1.d).

**REJECTED — annotate the snapshot.** *Discriminator:* JSON carries no comments, and mutating `note` still breaks the "derived from the report's ratified tables" provenance. **The annotation of record is this READ, merged, plus this ruling** — precedent: the ADR's own ERRATUM block, which "is part of this ADR and travels with it" rather than editing the rulings it corrects.

> **RULED: leave the snapshot AS-IS. Do not insert, do not annotate. The wire decides.**

### R-1.c Is E-2's wire-decides sufficient for THIS office, given finding 7? **Yes — today, by two independent branches.**

The dispatch asks this because the 30-day lookback is effectively 6 days. For this office that does not bite:

1. **Booking branch:** the subject booked **2026-09-13** — inside the stamped era. `last_booking_age_days` = 1 ≤ 30 → **ACTIONABLE regardless of class**. A 6-day-effective lookback catches it with 5 days to spare.
2. **Class branch:** even if it stops booking entirely, it is **absent from the snapshot** → `class=unknown` → **CLASS UNKNOWN**, never EXPECTED SILENCE.

**But it is sufficient by luck, not by design, and branch 2 has an expiry.** The next legitimate snapshot refresh (D5.1/§12 row 1, due when `snapshot_age_days > 30`, i.e. **2026-10-11**) will insert a **sourced** `15caa02c: inactive` row — at which instant branch 2 silently inverts and this office becomes EXPECTED-SILENCE-eligible. That inversion is the refutable trigger carried in R-3.

### R-1.d Flagged to the snapshot owner — a selection asymmetry, NOT fixed here

The file's `note` claims it covers "…and the named positive controls." The sizing read named five: `4ec260bf`, `d167d635`, `8e56f6e1`, `ca70baa8` — **all four that fired `active` are present** — and `15caa02c`, **the sole control that did NOT fire, which is absent.** The file's stated population and actual population disagree by exactly the disconfirming control. I make no claim as to cause. **Routed to §12 row 1 (owner: the S-1 consumer, via the S1.2 runbook row); to be resolved at the next sourced refresh, not by hand.**

---

## R-2 — THE GENERAL HAZARD: the first 30 days of the "no booking in 30 d" branch

**RULED: a DATED CALIBRATION HAZARD.** Not a UV-P, not a defect.

**REJECTED — UV-P.** *Discriminator:* a UV-P names a premise **not taken**. This one was taken and measured: 1,443 fleet bookings across all 31 days with `count_distinct(guid)` = **0 every day through 2026-09-08**, non-zero from 09-09. A measured fact cannot be carried as unverified.

**REJECTED — defect.** *Discriminator:* no code is wrong. The evaluator will compute `last_booking_age_days` correctly over the plane it is given; **the plane was not stamped.** A defect demands a fix; this demands a **disclosure** and expires on a known date without intervention.

**Scope, stated exactly:** for every office whose last booking fell in **2026-08-15 .. 2026-09-08** and which has not booked since 09-09, the evaluator sees "no booking in 30 d" and falls through to the class branch. Where that class is `inactive` or `ignored`, a **real stall is routed to EXPECTED SILENCE** — the precise failure E-2 was written to prevent, arriving through E-2's own input rather than its predicate. Self-heals when the lookback is wholly inside the stamped era: **2026-10-09**.

### What the page must print — and the design fork inside it

**RULED: the attribution floor is COMPUTED, never a hard-coded constant.** Define it as *the earliest day in W carrying a guid-stamped booking line*, and render, on every page where it exceeds the window start:

`lookback effective <N>d of 30 (booking attribution floor <date>) — EXPECTED SILENCE may hide stalls`

**REJECTED — hard-coding `2026-09-09`.** *Discriminator:* a constant **cannot detect a regression**. If guid stamping lapses, a computed floor moves and the page says so; a constant keeps asserting 30-day coverage that no longer exists, and becomes a *second* dated artifact needing its own refresh — the exact failure D5.1 rule 3 exists to make visible. The computed floor is simultaneously the disclosure **and** the stamping-regression detector, which is why no separate alarm is owed (R-4).

**This is not a re-tune, and sitting XI's "recede, not re-tune" is honoured.** The bias lives in `last_booking_age_days` — an **input horizon** — not in A / A′ / r. **A, A′ and r are untouched.** Printing a horizon is neither a tune nor a threshold. It is D5.1 rule 3's own pattern (a dated substrate whose age is rendered on the page, converting silent staleness into a page-visible state) applied to a second dated substrate; I rule by that precedent rather than minting a new one.

**Soak note (charge §3, ≥ 7 d):** the soak must record that **any EXPECTED SILENCE population measured before 2026-10-09 is not evidence of correct sectioning** — that section is under-populated by construction for the whole soak. The soak may certify ACTIONABLE and CLASS UNKNOWN; it may **not** certify EXPECTED SILENCE. Re-check the section at first page on/after 2026-10-09.

---

## R-3 — "Asana dark AND wire live" as a SIGNAL

**RULED: a NAMED DEFER with an owner and a refutable trigger — never `NO WATCHER`.** Binding precedent, in the ADR's own words at D5.4: *"Snapshot refresh — a DEFER with an owner, never `NO WATCHER`."*

**First, a supersession the dispatch could not have known when the row was written.** `HANDOFF-name-the-client` §3 row `SIZING-15caa02c` — *"non-Offer booking path or stale section? — NO WATCHER"* — **predates erratum E-2.** Under E-2, an office with `class ∈ {inactive, ignored}` **and** `last_booking_age_days ≤ 30` lands in **ACTIONABLE**. That is this signal, already computed, already routed to the operator's eye.

> **Re-stamp the row: `SIZING-15caa02c` — SUPERSEDED-IN-PART by ADR erratum E-2. WATCHED-AS-STALL. Naming deferred (R-3a); provenance deferred (R-3b).** Both halves get owners; neither remains `NO WATCHER`.

**R-3a — NAMING · owner: the S1.3/S1.4 builder seat · trigger: ships with S-1.**
E-2 routes the office correctly but **diagnoses it wrongly**: the operator reads *"ACTIONABLE — `15caa02c`, bookings=8"* and is never told *"and Asana says this client is dark."* The cure is one rendered token on a row E-2 already computes — where `class ∈ {inactive, ignored}` **and** `last_booking_age_days ≤ 30`, render `⚠ DARK-BUT-BOOKING`. **This is not a new instrument and not a new mechanism:** it prints a join E-2 already performs, inside the ruled evaluator. Lands with D8.1's section rendering.

**R-3b — PROVENANCE · owner: WS-2 (offer-grain observer) · trigger below.**
Detecting *a current section with no `section_changed` story explaining it* (READ §4 gap 3) **is** a new instrument on the story cache that backs `/section-timelines` — whose own `imputation.basis` of `"inferred-from-story-cache-warmth"` is, as the station says, an admission that unobserved offers are imputed rather than flagged. Offer-grain state reconciliation is WS-2's definition. **WS-2 sequencing is an operator-held fork (ADR §12 row 7); I assign the lane, not the schedule.**
**Refutable trigger:** *"a sourced snapshot refresh inserts a `15caa02c` row with class `inactive` while the office's last recorded `section_changed` remains an active-class move."* Date-bounded — the refresh is due when `snapshot_age_days > 30`, i.e. **2026-10-11**. **Watcher:** §12 row 1's refresh act, which is itself self-surfacing via D5.1 rule 3.

**REJECTED lane — the census owner (who holds the `40f86e73` row).** *Discriminator:* `40f86e73` is a **disabled** office — a census / served-set fact. `15caa02c` is an **Asana Offer-section provenance** fact. Routing this there repeats D5.2's E1 **WRONG-OBJECT** error verbatim: the census answers *"is it served?"*, `OFFER_CLASSIFIER` answers *"what does Asana say the Offer is?"* — two objects, two questions. (Note this is also the question that would have discriminated R-1's two readings — which makes it a *consultable* plane for a future node, not the owner of this signal.)

**REJECTED lane — a standalone alarm now.** *Discriminator:* charge §3 — any new metric soaks ≥ 7 d before its alarm arms, and this wave's telos law is *consumer before instrument*. R-3a delivers the naming inside an instrument already being built; a second instrument for one known office is instrument-ahead-of-consumer.

---

## R-4 — The booking-arm attribution gap before 2026-09-09

**RULED: nothing new to build. One mechanism (R-2's computed floor) discharges the forward path; the back-window folds into an existing owned defer; the instrumentation half is closed.**

1. **Forward (09-09 →):** stamping is landed. The **computed attribution floor of R-2 is the whole remedy** — it is simultaneously the dating note, the disclosure, and the regression detector. **No separate alarm, no new metric, no soak clock.** Owner: the S1.3/S1.4 builder seat.
2. **Dating note:** not prose-only. **RULED mechanical** — every guid-attributed booking figure on a window crossing 2026-09-09 must render its effective horizon. A note in an artifact goes stale; a rendered horizon cannot.
3. **Back-window (2026-08-15 .. 2026-09-08):** **not recoverable by guid on this plane** — but the station's §2.3 key inventory shows **`office_name` present on booking lines**, and `ADR-ws-join-office-naming-path-2026-09-08` already establishes a name→office join. So the back-window may be **retro-attributable by name**. I do not rule that it is. `[UV-P: whether office_name is present on booking lines BEFORE 2026-09-09 | METHOD: stats count() by ispresent(office_name) over booking events, @timestamp < 2026-09-09 | REASON: the station's key inventory was taken from 25 raw lines, all inside the stamped era]`
   **FOLDED into ADR §12 row 3** — *"Characterise the `***` residual and cure the attribution gap"*, **owner: the WS-1 successor seat**. Same defect class (office attribution degrading), different arm. **Row 3's trigger must be widened**, because `residual_share > 10 %` is an **arrivals-line** predicate and would never have fired for a booking-arm gap: add *"the booking attribution floor is later than the window start on any page."* One owner, two triggers, no new row.
4. **Fleet frame (`ari ask`, 2026-09-14):** this is a named platform pattern, not a local quirk — `integrity-architect` / `pipeline-steward` / `/dre`: *"the producing path must emit the fuel the consuming path needs, and the consuming path must refuse to proceed against empty or absent fuel."* The producing path did not emit the guid; the consuming path **did not refuse** — it read *absent fuel* as *a measured zero*. That is exactly the failure the computed floor prevents, and it is the reason the floor is ruled **computed**: a consuming path that derives its own horizon can refuse; one handed a constant cannot.

---

## R-5 — Is the READ fit to merge as the record of T2?

**CERTIFY-WITH-ERRATA.** It is measurement, not verdict, and it holds that line explicitly in four places, including the §5 row *"Class ruling / verdict — RESERVED to pythia."* Every load-bearing claim carries a control taken **in the same run** — negative (`00000000` → absent), positives (4/4 → active), a **firing control for the mechanism itself** (`ca70baa8`: 9 `section_changed`, most recent 19 days old — which is what converts the subject's silence from *an API limit* into *informative silence*), a fleet control that reclassifies the booking onset from behaviour-change to stamping-gap, and a retention control proving the window is fully covered. Not-takens are enumerated with METHOD and REASON. Refs and file:line anchors are named. The fence holds. It self-caps at MODERATE correctly and states falsifiers for **both** readings, including the one that would relocate its own conclusion. **This is the standard.**

The errata travel with this ruling and with the READ; **they require no edit to the merged artifact** (precedent: the ADR's own ERRATUM block).

**E-1 — §0 BLUF, line beginning `**H2 (the Asana section is stale) — STRONGLY SUPPORTED`.** The BLUF grades the **interpretive label** at STRONG. What the evidence supports at that strength is the narrower measured fact the READ itself states two lines later and again in §4 — *"the move into `INACTIVE` was never recorded at all."* "Stale" is an inference that falsifier (c) contests and that §3.4's properly-recorded `Paused` Unit actively counterweights. **Read as:** *"H2's measured core — the transition into `INACTIVE` is unrecorded — STRONGLY SUPPORTED. H2's interpretation (the label is wrong) — NOT DISCRIMINATED from falsifier (c) by the evidence taken."* §4's own wording is already correct; only the BLUF headline over-reaches. This is the line R-1 turns on.

**E-2 — §2.4, `"Bookings, however, are zero for both offices every day through 2026-09-09"` vs §0's `"0 every day through 2026-09-08"`.** Both are true at different scopes — §0 is **fleet** (first stamped booking 09-09), §2.4 is **subject-and-control** (both first book 09-10) — but the two sit one day apart on the number R-2 and R-4 now make a mechanism depend on. **Read as:** *fleet booking-attribution floor = **2026-09-09**; the subject's first guid-stamped booking = **2026-09-10**.* The floor is the fleet value.

Neither erratum requires re-measurement; neither blocks merge. **Merge it.**

---

## Not done here, by charge

No file edited (READ, snapshot, code: untouched). No merge, no arm, no alarm, no Asana write, no re-measurement. `15caa02c` is **not** inserted into the snapshot. A/A′/r **not** re-tuned. WS-2 **sequencing** not assigned (operator fork, ADR §12 row 7). The serving/billing plane that would discriminate R-1's two readings was **not** consulted — named as the missing discriminator, not resolved.

