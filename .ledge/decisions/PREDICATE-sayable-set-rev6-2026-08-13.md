---
type: decision
status: proposed
---

# PREDICATE — say-able set, REVISION 6: re-derivation under R-4 and G4′

> **Status.** Revision, not replacement. Stacks on
> `PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md` (rev-1..rev-5,
> "the base artifact" below). Rev-5 CLOSED the base artifact at **ONE say-able
> readout: item 1a**. This revision executes the **unassigned act** R-4 names
> (`RULING-operator-morning-set-2026-08-13.md:62`): re-derive **item 1b** and
> **§2.7 row 3** on their *remaining* grounds now that the K-lane fence is
> mutation-only, and dispose of the **`honest_contract_complete`** vacuous-True
> that item 1a rests on.
>
> **Author.** `10x-dev` / `architect` (EX-2, WS-4). **Self-attestation caps
> MODERATE** — self-authored; the rite-disjoint corroborator is
> `hygiene` / `audit-lead`, who sweeps the §4 refuters independently and returns
> CONCUR / DISSENT. This artifact is NOT self-certified.
>
> **Scope fence.** This decides **say-ability**, not build authorization
> (base §0). It promotes **nothing** it cannot re-run the gates on. It resolves
> **no** Q-3 (§6). It mutates **no** K-lane surface (C-8; R-4 narrows C-8 to
> permit read-only consumption — read-only is all this dispatch did). No Asana
> write (CR-1). No `s3://autom8y-asr-verdicts` read (CR-2). No live API or AWS
> call this dispatch — every claim below is a static code-read at this repo's
> working tree on `main` (4b converse: working tree is authoritative here).

---

## §0 The result in one line

**R-4 removes the fence. It promotes nothing.** The say-able set is **unchanged
by R-4: item 1a only.** Item 1b and §2.7 row 3 each move from
*withheld-on-fence-grounds* to **reachable**, and each is then **re-derived to
`WITHHELD-PENDING` on a surviving non-fence ground** — different grounds, both
named, both proved rather than assumed. Item 1a's `SAY-ABLE` **stands on its four
gates**, but its *disclosure* inherits a defect (`honest_contract_complete` is a
failure-absence receipt, vacuously True on an empty manifest) that requires a new
disclosure clause and that neither S1 nor its critic flagged.

**"Reachable" is not "say-able."** That distinction is the whole of this
revision (base §"Must not"; R-4:62 *"not auto-promoted"*).

---

## §1 What R-4 and G4′ change — and what they do not

**R-4** (`RULING…:55-68`): read-only consumption of a **shipped response field**
is not a "touch"; the zero-K-lane fence is now about **mutation only** and *"no
longer constrains read-coupling to K-lane-derived values"* (`:67`). It does
**not** authorize a build, a new endpoint, a mutation, or reaching into a
substrate that is neither a shipped response field nor a K-lane-derived value.

**G4′** (base §2.4, adopted rev-5): *enumerate every imputation, default, filter
and clipping branch from source event to rendered figure; state the sign on each;
PASS iff all non-neutral branches share one sign; an unenumerated branch is an
undeclared direction.* **G4′ is adopted by the S1 author, not operator-ruled**
(`RULING…:202`, standing item 8). This revision operates **under** G4′ and
**surfaces** the question of its authority as **Q-3** (§6) — it does not assume
the answer and does not wait for it.

**A premise correction, surfaced not papered** (handoff-premise-validation §10.5).
R-4:62 characterises 1b and §2.7 row 3 as both *"withheld-on-fence-grounds."*
That inherits **O-7's rev-2 framing** (base `:1582-1592`, which lumped the two
items as both fence-bound). But **1b's ground was already sharpened off the fence
at rev-3** (base `:1177`: *"The K-lane fence is no longer load-bearing here — the
binding constraint is the event-class mismatch"*). O-7 was never reconciled with
that sharpening. So for **1b**, R-4's fence-removal is largely a **no-op** — 1b's
live ground was never the fence. For **§2.7 row 3**, the fence ground **is** live
(base `:326` F-3: *"fenced, not invisible"*) and R-4 genuinely bites. The two
items are **not symmetric** under R-4, and treating them as symmetric is the
error R-4:62's own *"re-derived on their remaining grounds"* clause guards
against. This revision executes that clause.

---

## §2 Per-item G4′ branch tables (exit criterion 1)

Every branch from source event to rendered figure, with a stated sign. A **neutral**
branch introduces no error and does not break the conjunction (rev-5 clarification).
PASS iff all **non-neutral** branches share one sign.

### 2.1 Item 1a — `now − max(last_modified)` per section (the say-able readout)

Reproduced from base §2.4 (`:823`) and **extended** with the disclosure branch
this revision surfaces.

| # | branch (source event → figure) | class | sign | anchor |
|---|---|---|---|---|
| 1 | `last_modified` copied from Asana `modified_at` into the row | provenance | **neutral** (exact; cannot lead its source) | `dataframes/schemas/base.py:76-82` (`nullable=False`, `source="modified_at"`) |
| 2 | imputation on the measurand | — | **none** (no imputation on this path) | — |
| 3 | default substitution | — | **none** (`nullable=False`) | `base.py:76-82` |
| 4 | `where`/section filters | filter | **neutral** (narrow *which rows*, not the value) | — |
| 5 | clipping | — | **none** | — |
| 6 | frame staleness → `now − max(last_modified)` grows | staleness | **OVERSTATE** (never understate; column cannot lead `modified_at`) | base `:1219-1227` (C-6 both-branch re-test) |
| **7** | **`honest_contract_complete` read into the render as a completeness attestation, vacuously True on an empty manifest** | **disclosure** | **OVERSTATE completeness** (attests "roster complete" when zero sections were attempted) | `dataframes/section_persistence.py:270-271` |

**Measurand axis (branches 1-6): PASS.** The only non-neutral measurand branch is
frame staleness → overstate; single-signed. Unchanged from rev-5.

**Disclosure axis (branch 7): a distinct, same-signed defect that does NOT flip
the verdict but DOES require a new rule.** Branch 7 is not a branch on the
*quiet-time value* — it is a branch on the *completeness attestation the render
carries alongside it*. Its sign (overstate-completeness) happens to agree with
branch 6, so 1a does **not** become sign-ambiguous. But an overstated completeness
attestation is a **different kind of error** from an overstated quiet-time, and
G4′ (a measurand-sign gate) is the wrong gate to catch it. It is caught here, one
axis over, and disposed in §3.3. **Item 1a remains `SAY-ABLE`; its render acquires
a constraint (DR-9, §3.3).**

### 2.2 Item 1b — per-section quiet-time leaderboard, *"week by week"*

The rendered figure would be a **per-section, per-week series** of edit-quiet-time.
The G4′ table cannot be completed **because the path never reaches a rendered
figure on any shipped surface** — it terminates upstream, at G2, for want of a
carrier:

| # | branch | class | sign | status |
|---|---|---|---|---|
| — | source event = per-offer **edit** timestamps over time | — | — | the substrate **retains** these (§4 refuter (a): 6 edit-class story subtypes, cached unnarrowed) |
| — | carrier to a rendered series | **transport** | — | **NO SHIPPED RESPONSE FIELD CARRIES IT** — path stops here (§3.1) |

**G4′ is not reached.** 1b fails **G2 (denominator/exhibitability)** before any
error-direction question arises. The branch table is **vacuous by construction**:
you cannot state the sign on branches of a figure no surface renders. That
vacancy **is** the finding — localised precisely to G2, not G4′. Disposition §3.1.

### 2.3 §2.7 row 3 — *"At the {t} observation, these sections held zero offer rows"*

The rendered figure is the **zero-row section set**, exhibited against the
**complete section roster** (the denominator). Same structure as 1b: the path
terminates at **G2**, on the roster's exhibitability, not at G4′.

| # | branch | class | sign | status |
|---|---|---|---|---|
| 1 | value = (all sections) − (sections appearing in offer `/rows`) | set-difference | **neutral** (exact given a roster) | — |
| 2 | roster source = persisted section manifest (K-lane-derived) | denominator | **neutral IF single-clock with the frame** | read-back existence **UV-P** (§3.2) |
| 3 | roster source = `section`-entity `/rows` | denominator | neutral if it enumerates empties | **UV-P** — does the frame include zero-task sections? (base `:1741`) |
| 4 | roster source = live `GET /api/v1/projects/{gid}/sections` | denominator | **TWO-CLOCK** (live roster vs ≤4h frame) → a section created after {t} reads as falsely quiet | **OVERSTATE** the zero-row set (§3.2) |

**G4′ passes on branch 1 (the value is exact given a roster); the withholding is
at G2** (no roster source is verified single-clock-complete this dispatch).
Disposition §3.2.

---

## §3 Dispositions, with the ground named (exit criteria 2 & 3)

### 3.1 Item 1b — **STILL-WITHHELD** (`WITHHELD-PENDING`), ground CORRECTED

**Verdict unchanged. R-4 does not reach it.** The ground stated at rev-3 (base
`:1177`) — *"the binding constraint is the event-class mismatch, which no fence
ruling can dissolve"* — is **partially stale** and is corrected here:

- The **strong** form of the mismatch (*"edit history is movement-only / not
  constructible"*, base rev-3 `:1140`) was **WITHDRAWN at rev-4 under C-7** (base
  `:191-227`). The substrate does **not** exclude edit history:
  `DEFAULT_STORY_TYPES` admits nine subtypes of which **six are edit-class**, the
  fetcher applies **no** subtype filter, and the cache is written **unnarrowed**
  (§4 refuters (a); verified own-hands this dispatch). So *"the mismatch that no
  ruling can dissolve"* is the **wrong name** for 1b's surviving ground.
- The **surviving** ground is a **carrier gap, not an event-class mismatch**:
  the retained edit-class stories live in the **story cache**
  (`cache/integration/stories.py`), which is **neither a shipped response field
  nor a K-lane-derived value**. R-4 grants read-coupling to *shipped response
  fields* (`:56`) and *K-lane-derived values* (`:67`). It grants **nothing** over
  the story cache. The two shipped surfaces R-4 does reach —
  `/rows` (`last_modified`, a **current snapshot** that overwrites; no series)
  and `section-timelines` (`OfferTimelineEntry`, seven **move/dwell** scalars,
  `extra="forbid"`, no transitions; §4 refuter (c)) — carry **no edit-time
  series**. Rendering 1b would require a **new consumer** reading the story cache
  = a build past the shipped-response boundary, which R-4 does not authorize.

**Restated ground (1b):** *no shipped response field exposes the retained
edit-class history as a per-offer/per-section series; R-4's read grant does not
extend to mining the story cache; a series carrier is a build, not a read.*
Additionally the **one genuinely open link** carried since rev-4 remains open —
whether the story cache is populated for **offer** tasks at all (base `:1739`);
R-2 authorized the probe that closes it, but that probe is EX-1/eunomia's lane,
not this dispatch's. **Verdict: `WITHHELD-PENDING`.** R-4 = no-op for 1b.

### 3.2 §2.7 row 3 — **STILL-WITHHELD** (`WITHHELD-PENDING`), ground NARROWED; now REACHABLE

**R-4's fence-removal genuinely bites here** (unlike 1b): §2.7 row 3's live ground
*was* the K-lane fence (base `:326`, `:893` — the roster enumerable only from
`section_status_updated`, on the manifest **write** path,
`section_persistence.py:537-560`). R-4 removes that ground. **The item is now
reachable.** It does **not** thereby become say-able, because **no roster source
is verified single-clock-complete this dispatch** (§2.3 table):

- The **single-clock** candidate (persisted section manifest, built alongside the
  frame) is now read-permitted under R-4:67, **but** whether a **shipped read-back
  of the roster** exists — as distinct from the write-path emission — is a **UV-P**
  not resolvable by static read.
- The **`section`-entity `/rows`** candidate is the base artifact's own UV-P
  (`:1741`): whether that frame enumerates zero-task sections is *"not determinable
  by static read."*
- The **live Asana proxy** `GET /api/v1/projects/{gid}/sections` (verified shipped,
  `api/routes/sections.py:50`; enumerates all sections incl. empties) — **an option
  S1 did not enumerate** — is **two-clock** against the ≤4h offer frame and would
  **overstate** the zero-row set (a section created after {t} reads falsely quiet).
  It does **not** cleanly rescue the item. Flagged for `audit-lead` and S4 as an
  **enumeration addition** (option-enumeration discipline), evaluated and rejected
  here rather than silently dropped.

**Restated ground (§2.7 row 3):** *the fence is gone, but the complete roster is
not verified exhibitable from any single-clock read-only surface; promotion
turns on a live/probe question (does a single-clock roster read-back enumerate
empty sections?), not on any fence ruling.* **Verdict: `WITHHELD-PENDING` —
reachable, not say-able.** The next hop is a probe, not a reading (§4, §6).

### 3.3 `honest_contract_complete` — explicit disposition (exit criterion 3)

**`is_honest_complete()` returns True iff no section is FAILED, and True
VACUOUSLY for an empty manifest** — confirmed own-hands, verbatim
(`dataframes/section_persistence.py:270-271`: `if not manifest.sections: return
True`; docstring `:267`: *"An empty manifest (no sections) returns True (vacuously
complete)."*). A section never *attempted* is **absent, not FAILED**. So the field
is a **failure-absence receipt**, not a **correspondence receipt**: `True` means
*"no section I know about failed,"* never *"all expected sections are present and
processed."*

**Does the vacuous-True propagate into item 1a? — Traced. Yes, into 1a's
DISCLOSURE; no, not into 1a's GATES.**

- **Not into the gates.** 1a's G2 denominator is *"of the N sections holding offer
  rows,"* **computed consumer-side from the `/rows` payload** (base `:1010-1018`),
  **not** from `honest_contract_complete`. On an empty manifest N=0 — still
  exhibitable. G1/G3/G4′ do not read the field either (§2.1 branches 1-6). **The
  vacuous-True flips none of 1a's four say-ability gates. Item 1a remains
  `SAY-ABLE`.**
- **Into the disclosure.** R-4:60 lets 1a's render *"read `honest_contract_complete`
  … off `meta`."* If the render presents `True` as *"the section contract is
  satisfied / the roster is complete,"* that is **false on an empty or never-built
  manifest** — the alias-defect the freshness contract exists to close
  (`CONTRACT…:368,:816-818`: *"an alias is how one quantity acquires another's
  guarantee without earning it"*). The failure-absence quantity silently acquires
  the completeness guarantee via the vacuous branch.

**Disposition — a new disclosure clause, bounded to 1a's render:**

> **DR-9 (NON-ALIASING OF `honest_contract_complete`, BINDING on any readout that
> reads it).** `honest_contract_complete=True` may be disclosed **only** as
> *"no section is in a FAILED state"* — a failure-absence receipt. It MUST NOT be
> rendered, glossed, or coalesced as a completeness / correspondence claim
> (*"all sections present," "roster complete," "genuinely quiet"*). A reader that
> wants a completeness attestation MUST co-check manifest **non-vacuity**
> (`manifest.sections` non-empty) in a separately-named path; absent that check,
> `True` is treated as **completeness-unknown**, never completeness-confirmed.

**Referenced, NOT absorbed (routed to the operator).** The same vacuous-True feeds
the shipped **`honest_empty` 200-vs-503 control path**:
`honest_empty = honest_contract_complete and prefilter_row_count == 0`
(`query/engine.py:280`), consumed at `api/routes/query.py:513-519` as the
`S7_CAUSE_HONEST_REFUSAL` *"attested honest-empty serve."* An **empty / never-built
manifest** (vacuous-True) with zero rows would be attested a **genuine empty-200**
rather than a still-building 503 — a directional false-freshness hazard in shipped
code. This is **product correctness, not say-ability** — parallel in kind to
`DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`. **Not this artifact's
to rule; not absorbed; routed to §6.** I verified the derivation and the consumer
own-hands; I did **not** probe whether an empty manifest actually reaches the
served boundary in production (a live question, unprobed this dispatch) — that
reachability sub-claim is carried as a UV-P, inferred in neither direction.

---

## §4 NR-2 refuter sweep (exit criterion 4; §A.2 / §A.3 reporting)

**The negative under test:** *"item 1b stays withheld — no shipped surface renders
its week-by-week edit series."* (Note the negative is **restated** from the base's
*"event-class mismatch not dissolvable"*: refuter (a) already narrowed that name;
§3.1.) All four §A.2 refuters swept own-hands this dispatch, **including the two
the record did not show swept (b, d)**. Nulls reported.

| refuter | swept? | what it returned | hop one past where the argument stops |
|---|---|---|---|
| **(a)** `DEFAULT_STORY_TYPES` beyond `section_changed` — NOW fully swept? | **YES** | **FIRED, and is fully swept.** 9 subtypes, **6 edit-class** (`assignee_changed, due_date_changed, marked_complete, marked_incomplete, enum_custom_field_changed, number_custom_field_changed`); fetcher applies no subtype filter; cache written unnarrowed on miss. The substrate **retains** edit history. **Effect:** it kills the *"not constructible"* name (§3.1) — but **does not promote 1b**, because retention-in-cache ≠ exposure-on-a-shipped-field. | `cache/integration/stories.py:23-33` (types) → `:141-146` (unnarrowed write) → **stops at** the one read-time narrowing consumer `services/section_timeline_service.py:341` (`resource_subtype == "section_changed"`); one hop past = there is **no second consumer** that surfaces the other 6 subtypes |
| **(b)** retained frame snapshots (`dataframe_cache_put`) — record does NOT show swept | **YES (swept this dispatch)** | **NULL.** Both cache tiers key on **`entity_type:project_gid`** and **overwrite**: `MemoryTier.put` pops any existing entry before adding (single current entry, LRU-evicted); `ProgressiveTier` keys identically; no date/time partition in the key. **No series of historical frame snapshots is retained** — you cannot reconstruct a week-by-week edit-time history from the DataFrame cache. Confirms the negative; does not refute it. | `cache/dataframe/tiers/memory.py:133-160` (`put` overwrites; key `entity_type:project_gid`) → `tiers/progressive.py:279` (`put_async` same key) → one hop past = `created_at` is per-entry **metadata for staleness/eviction**, not a partition key; there is no snapshot log to walk |
| **(c)** any OTHER shipped response field carrying **edit-class** rather than move-class semantics? | **YES** | **NULL.** `OfferTimelineEntry` = 7 scalars, all **move/dwell/current-state** (`active_section_days, billable_section_days, current_section, current_classification` + 3 ids), `extra="forbid"`, **no transitions**. No shipped route returns raw stories as a series (`receipts.py` **writes** comment stories — CR-1; `section_timelines.py` computes move-class scalars only). The **only** shipped edit-class datum is `last_modified` on `/rows` — a **current snapshot**, not a series. | `models/business/section_timeline.py:158-215` (the 7 scalars) → one hop past = the offer `/rows` payload's `last_modified`, which is `max`-reducible to **current state** (item 1a) but carries **no prior values** to form a series |
| **(d)** `honest_contract_complete` vacuous-True — does the absence propagate into item 1a? | **YES** | **FIRED into 1a's disclosure, NULL into 1a's gates.** Vacuous-True confirmed verbatim (`section_persistence.py:270-271`). Propagates into 1a's **render** (R-4:60) and into the shipped **`honest_empty` 200/503 path** (`engine.py:280` → `query.py:513-519`); does **not** flip any of 1a's four gates (§3.3). **Effect:** 1a stays `SAY-ABLE`; a new DR-9 clause is required; a shipped-code hazard is referenced-not-absorbed. | `section_persistence.py:270-271` (`if not manifest.sections: return True`) → `query/engine.py:280` (`honest_empty = … and prefilter_row_count == 0`) → one hop past = `api/routes/query.py:517` (`S7_CAUSE_HONEST_REFUSAL`) — the served boundary; whether an empty manifest **reaches** it in production is the unprobed UV-P |

**Verdict on the negative (§A.3): STANDS, with NARROWED scope.** *"Item 1b stays
withheld"* **STANDS**. The **ground narrows**: not *"the event-class mismatch is
undissolvable"* (refuter (a) dissolved that name — edit history **is** retained)
but *"no shipped response field carries the retained edit series, and R-4's read
grant does not reach the story cache"* (refuters (b), (c) both NULL — no snapshot
history, no other edit-class shipped field). No refuter promoted 1b. **A promotion
without a completed branch table would be reverted (PT-04); no promotion is made.**

---

## §5 SVR ledger (own-hands, this dispatch — all file-read at working-tree `main`)

| id | claim | method | anchor + marker |
|---|---|---|---|
| SVR-R6-1 | `DEFAULT_STORY_TYPES` = 9 subtypes, 6 edit-class | file-read | `src/autom8_asana/cache/integration/stories.py:23-33` — marker: `"enum_custom_field_changed",` / `"number_custom_field_changed",` |
| SVR-R6-2 | cache-miss writes the fetched stream **unnarrowed** | file-read | `cache/integration/stories.py:141-146` — marker: `stories = await fetcher(task_gid, None)` … `cache.set_versioned(task_gid, entry)` |
| SVR-R6-3 | DataFrame cache overwrites per `entity_type:project_gid`; no snapshot history | file-read | `cache/dataframe/tiers/memory.py:133-160` — marker: `if key in self._cache:` / `old_entry = self._cache.pop(key)` |
| SVR-R6-4 | `is_honest_complete` returns True **vacuously** on empty manifest | file-read | `dataframes/section_persistence.py:270-271` — marker: `if not manifest.sections:` / `return True` |
| SVR-R6-5 | `honest_contract_complete` spread into `RowsMeta`; `honest_empty` derived from it | file-read | `query/engine.py:280` (`honest_empty = honest_contract_complete and prefilter_row_count == 0`), `:292` (`honest_contract_complete=honest_contract_complete,`) |
| SVR-R6-6 | vacuous-True feeds the shipped `honest_empty` 200-serve branch | file-read | `api/routes/query.py:513-519` — marker: `S7_CAUSE_HONEST_REFUSAL` / `getattr(result.meta, "honest_empty", False)` |
| SVR-R6-7 | `OfferTimelineEntry` = 7 move/dwell scalars, `extra="forbid"`, no transitions | file-read | `models/business/section_timeline.py:158-215` — marker: `active_section_days` … `current_classification` … `"extra": "forbid",` |
| SVR-R6-8 | a shipped section-roster read exists (live Asana proxy; two-clock) | file-read | `api/routes/sections.py:50-86` (`GET /api/v1/sections/{gid}`; docstring names `GET /api/v1/projects/{gid}/sections` for the full list) |
| SVR-R6-9 | `last_modified` is a non-nullable snapshot copied from Asana `modified_at` | file-read | `dataframes/schemas/base.py:76-82` (cited from base SVR-S1-10; not re-opened) |

**UV-P carry (Gate-C DEFER-tag pattern):**

- `[UV-P: whether a single-clock read-back of the complete section roster (incl. zero-task sections) exists on any shipped read-only surface | METHOD: deferred-to-live-probe or S4 | REASON: §2.7 row 3's sole remaining barrier post-R-4; the manifest read-back and the section-entity empties-enumeration are both undeterminable by static read, and the live proxy is two-clock]`
- `[UV-P: whether the story cache is populated for OFFER tasks at all | METHOD: deferred-to-live-probe (R-2 authorized) or EX-1/eunomia | REASON: inherited open link from base :1739; the same probe closes option (g) warmth; not this dispatch's lane]`
- `[UV-P: whether an empty/never-built manifest actually reaches the served boundary as an attested honest-empty 200 in production | METHOD: deferred-to-live-probe | REASON: the §3.3 shipped-code hazard's reachability; verified the derivation own-hands, did not execute the round-trip]`

---

## §6 §OPERATOR-RESERVED — surfaced, not resolved

**Q-3 (surfaced, NOT resolved).** *Is G4′ the operator's intended say-ability
gate?* G4′ was adopted **inside** the base artifact **by its author** and is
**not operator-ruled** (`RULING…:202`, standing item 8). This entire revision — the
1a branch table, the localisation of 1b/§2.7-row-3 to G2-not-G4′ — **operates under
G4′ as written**. If the operator intends a different gate, the branch tables in §2
re-run under it; the §3 dispositions (which turn on **carrier-existence and
roster-exhibitability**, not on G4′'s sign test) are **robust to that change** —
1b and §2.7 row 3 fail at G2 regardless of the error-direction gate's form. **The
question is surfaced; the answer is not assumed and this artifact does not wait
for it** (shape EX-2 entry criteria: *"not gated on Q-3"*).

**Routed, not decided (C-9 — silence is not absorption):**

1. **The `honest_empty` 200/503 shipped-code hazard** (§3.3): vacuous-True →
   an empty/never-built manifest attested as a genuine empty-200. Product
   correctness; parallel to `DEFECT-temporal-filter-imputed-false-move`.
   **Operator-routed; not absorbed.**
2. **DR-9** (§3.3): proposed disclosure clause. It binds any readout that reads
   `honest_contract_complete` — including item 1a's render. **Proposed here;
   ratification is the operator's / the disclosure-contract owner's.**
3. **§2.7 row 3's roster probe** (§3.2 + UV-P): the single question whose
   resolution would move §2.7 row 3 from *reachable* to a verdict. **A probe, not
   a reading.**
4. **Enumeration addition for S4** (§3.2): the live-proxy roster source S1's slate
   did not enumerate. Evaluated-and-rejected here (two-clock); flagged so S4's
   option-enumeration exit criterion can dispose it explicitly.

---

## §7 Evidence grades & handoff

| claim | grade | basis |
|---|---|---|
| refuters (a)-(d) sweep results incl. nulls | **MODERATE** | four direct code-reads own-hands this dispatch (SVR-R6-1..8); capped MODERATE per self-attestation ceiling — `audit-lead` is the rite-disjoint corroborator who re-sweeps §A.2 independently |
| 1b `WITHHELD-PENDING`, ground = carrier gap | **MODERATE** | code-read decisive (no shipped edit-series carrier; refuters (b)(c) NULL); live populate-link unprobed (UV-P) |
| §2.7 row 3 `WITHHELD-PENDING`, reachable | **MODERATE** | fence-removal mechanical from R-4; roster-exhibitability UV-P by construction (static-unverifiable) |
| item 1a `SAY-ABLE` stands; DR-9 required | **MODERATE** | vacuous-True verbatim (SVR-R6-4); gate-independence traced (§3.3); disclosure defect is the novel finding, neither S1 nor its critic flagged it |

**Handoff.** To `hygiene` / `audit-lead` (MANDATORY, rite-disjoint): sweep the §A.2
refuters independently, check this record's nulls against your own, and return
**CONCUR / DISSENT** at
`.ledge/reviews/CRITIQUE-sayable-rederivation-2026-08-13.md`. **G4′ compels
enumeration, not completeness — the second reader is the actual detector** (base
`:830`). This artifact does not self-certify.
