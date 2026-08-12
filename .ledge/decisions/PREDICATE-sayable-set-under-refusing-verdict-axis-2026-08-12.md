---
type: decision
status: draft
artifact_id: PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12
revision: 5
final: true
remediates: CRITIQUE-s1-sayable-predicate-2026-08-12 (BLOCK, rev-2) + delta pass 2 (UPHELD-WITH-CONDITIONS, rev-3 — C-1/C-2) + PT-02 fork-surface gate (rev-4 — HARD C-6/C-7, both WITHDRAWALS) + delta pass 3 (rev-5 — 5a WITHDRAW; G4 replaced by G4′)
references: DEFECT-temporal-filter-imputed-false-move-2026-08-12.md (live product defect surfaced by the 5a refutation; operator-routed, NOT absorbed here)
initiative: asana-native-insight-delivery
sprint: S1 (WS-B — the say-able set under a refusing verdict axis)
rite: 10x-dev
author_seat: architect
external_critic: audit-lead (hygiene — rite-disjoint) — pass 1 RETURNED 2026-08-12 verdict BLOCK; delta pass 2 RETURNED 2026-08-12 verdict UPHELD-WITH-CONDITIONS (BLOCK DISCHARGED; item 1a cleared on five attacks; both rev-2 rejections CONCEDED)
date: 2026-08-12
evidence_grade: MODERATE (self-attestation cap). R-1 is corroborated at STRONG by the rite-disjoint critique (CRITIQUE §7) — that grade is the critic's, not this seat's.
supersedes: none
binding_inheritance:
  - CHARTER-decision-space-of-record-2026-07-30.md:52 (hard floor)
  - CHARTER-decision-space-of-record-2026-07-30.md:54 (priority domains)
  - CHARTER-decision-space-of-record-2026-07-30.md:55 (the two gates)
  - RULING-operator-option4-interview-2026-08-12.md:19 (P-1, verbatim)
  - RULING-operator-option4-interview-2026-08-12.md:22 (P-4, verbatim)
  - RULING-operator-option4-interview-2026-08-12.md:30 (P-12, verbatim)
---

# PREDICATE — the say-able set under a refusing verdict axis

**Sprint S1 exit artifact.** Mission, verbatim from
`.sos/wip/frames/asana-native-insight-delivery.shape.md:592-596`: *"Write the
completeness-vs-freshness discriminator as a PREDICATE a downstream author can
apply without re-litigating P-3, and classify the five REPORT §6 candidates
against it. State the disclosure rule any published number must carry so it can
never read as fresher than it is."*

---

## REVISION 5 — the last

Delta pass 3 returned **`5a WITHDRAW`**. This revision closes the artifact.

### The final count — ONE say-able readout

> **`SAY-ABLE`: item 1a only.** *"At the {t} observation, these sections' most
> recent observed offer edit was {t_s}"* — read via **`POST /v1/query/offer/rows`**
> (§3.0.1), subject to **DR-2** (as-of is the `min` floor over constituents).
>
> Everything else in this artifact is withheld: **1b, 2, 2′, 5a, 5b**
> `WITHHELD-PENDING`; **3, 4** `WITHHELD-AXIS`.

### 5a — WITHDRAWN. My structural argument was refuted at source.

I argued 5a survives as an **occurrence set**: imputation fires only on zero
surviving stories, so an imputed offer contributes no move events and cannot
contaminate a reported value — omission only, single-signed.

**Both load-bearing sentences are false.** I stopped at
`section_timeline_service.py:356-358`. One hop past is **`query/temporal.py`** —
the module that actually implements an occurrence set, imported and applied by a
shipped consumer (`query/__main__.py:875` import, `:893-895` construct, `:920`
`temporal_filter.matches(tl)`), iterating the very `tl.intervals` I cited. **I
never read it.** Verified own-hands, verbatim:

- `matches()` (`temporal.py:44-46`) — `return any(self._interval_matches(interval, timeline) for interval in timeline.intervals)`. Conjunctive over **specified** fields only.
- `moved_to` (`:51-58`) — compares `interval.section_name` and `interval.classification`, i.e. the interval's **own** identity. **No predecessor consulted.**
- `since`/`until` (`:61-64`) — test `interval.entered_at.date()`.
- `moved_from` (`:67-78`) — the **only** predecessor-consulting criterion; its `idx == 0` guard (`:69-70`) sits **inside** `if self.moved_from is not None:` and is therefore reached **only if `moved_from` is specified**.

An imputed interval carries `entered_at = task_created_at` and the offer's
**current** classification. A natural weekend query specifies `moved_to` +
`since`/`until` and **no** `moved_from`, so the guard never runs.

> **An offer merely created over the weekend, which never moved, is returned as
> having moved.**

Not a corner case: the population most likely to be imputed — zero surviving
stories — is disproportionately the **newly created**, whose `created_at` is
exactly what lands in recent windows.

**And the workaround inverts the sign.** `_build_intervals_from_stories`
(`section_timeline_service.py:231-267`) synthesises **no** pre-first interval —
it closes the previous interval and appends a new one per story (`:249-267`) — so
`intervals[0]` is a **genuine first move**. Specifying `moved_from` therefore
hits the `idx == 0` guard and **drops it**. **False positives without it, false
negatives with it. No formulation is single-signed.** G4 FAIL, on the same rule
that took item 2.

**Two further concessions, both correct:**

1. **My "omission only" claim was about the wrong object.** It is true of
   `SectionTimeline.intervals` — **which no HTTP consumer receives**.
   `OfferTimelineEntry` is seven scalars under `extra="forbid"`
   (`section_timeline.py:158-212`) and carries **no transitions for any offer**.
   The claim never transferred to a consumable surface.
2. **G2 bites 5a identically to 2′.** Exhibit `N of M` → you have published
   `M − N`, which **is** 5b — the item I withhold. Don't exhibit → G2 FAIL.
   **The 5a/5b split does not survive its own G2 requirement.** I built the split
   and did not test it against the gate I had just repaired.

### G4′ — ADOPTED, with one clarification and one stated limit

The critic convicted **its own gate**, not me: G4 as it repaired it asks *"is the
direction **known**?"*, which is answerable by assertion and never compels branch
enumeration. Items 2 and 5a both passed that way. It names this *"the same defect
class I convicted G3 of at pass 1 and left standing in G4."* **The routed
question I raised at rev-4 — gate defect or author defect — is answered: gate
defect, and the critic owns it.**

**G4′ replaces G4 in §2.4.** Verified mechanically against all three items before
adopting: **2 fails, 5a fails, 1a passes** (§2.4).

**Clarification (needed for 1a to pass, and offered as refinement not
disagreement):** *"all branches share one sign"* governs the **non-neutral**
branches. A branch that is exact — introduces no error — does not break the
conjunction. Most of 1a's path is exact; without this clause G4′ would fail
everything.

**Stated limit, which is the honest one:** G4′ compels enumeration; it **cannot
compel the enumeration to be complete.** An author who has not read
`temporal.py` will enumerate the branches they know and stop. The closing clause
— *an unenumerated branch is an undeclared direction* — makes that a **defect
rather than a pass**, which is the most a written gate can do. It is not what
caught anything tonight.

### The live defect — referenced, not absorbed

The 5a refutation surfaced a **shipped-code correctness defect**, filed
separately at
`.ledge/decisions/DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`. It is
product correctness, not say-ability; **operator-routed, not this artifact's to
rule, and deliberately not absorbed.**

Worth carrying here (and folded into §3.2): **three different consumers of one
imputation produce three different wrong answers** — sign-flip by sub-population
(item 2), indistinguishable payload (item 2′), false positives (item 5a / the
defect) — **and the remedy is one thing**: an imputed-vs-observed discriminator
must reach the consumable surface.

---

## REVISION 4 — two withdrawals

PT-02 (the fork-surface gate) ruled on revision 3 and issued two **HARD**
conditions. Both are **withdrawals**. Neither is annotated: PT-02 attached a
tripwire — *"if the briefing annotates item 2's SAY-ABLE rather than withdrawing
it, this gate becomes FORK SURFACE COMPROMISED."* Annotation was therefore not
available, and on the receipts below it would not have been defensible anyway.

| condition | disposition | outcome |
|---|---|---|
| **C-6 (HARD)** — item 2's G4 justification is refuted; the imputation error is **population-dependent in sign** | **ACCEPTED — `SAY-ABLE` WITHDRAWN** | Item 2 → **`WITHHELD-PENDING`**. The narrowed form (2′) is derived separately per PT-02's invitation and is **also withheld — on G2, not G4.** |
| **C-7 (HARD)** — tier (iii) *"edit history genuinely absent and not constructible"* is refuted | **ACCEPTED — tier (iii) WITHDRAWN and RESTATED** | The substrate does **not** exclude edit history. **One consumer discards it, at read time.** One link genuinely remains open and is carried, not closed. |
| **item 5a re-tested against C-6** (PT-02 instruction) | **SURVIVES — and the reason is structural** | 5a reports an **occurrence set**, not a derived difference. Imputation contributes **no** move events, so it cannot contaminate a reported value; its only effect is omission, which is single-signed. |

### C-6 — what I got wrong, and it is worse than a wrong sign

Revision 3 §3.0.2 asserted the imputation error was *"bounded and
one-directional: dwell is OVERSTATED, never understated."* **That is refuted on
the code.** Verified own-hands at `origin/main`:

`_build_imputed_interval` (`services/section_timeline_service.py:272-300`)
returns **exactly one** interval, carrying the offer's **current**
classification (`:296` `classification=account_activity`; docstring `:280` —
*"Use the offer's current account_activity for classification"*) and
`exited_at=None` (`:298`), which per `section_timeline.py:70,89` — *"Open
intervals extend to period_end"* — spans the whole window. The two counts are
classification-**set filters**: `active_days_in_period` → `frozenset({ACTIVE})`
(`section_timeline.py:81`); `billable_days_in_period` →
`frozenset({ACTIVE, ACTIVATING})` (`:100-102`).

| imputed offer's current classification | `active` | `billable` | `billable − active` | truth | sign |
|---|---|---|---|---|---|
| **ACTIVE** | full window | full window | **0** | ACTIVATING dwell may be > 0 | **UNDERSTATEMENT** |
| **ACTIVATING** | 0 | full window | **full window** | actual dwell ≤ window | **OVERSTATEMENT** |

**Same mechanism, opposite signs, partitioned by each offer's present
classification.** G4 requires the error direction to be *known*. Across the
cohort it is not merely unknown — **it is not single-signed**, so there is no
direction to declare. I derived the ACTIVATING branch, stopped, and generalised
from it. The ACTIVE branch was one filter-set away.

**Why annotation could not have rescued it.** The consumer cannot measure the
contaminated fraction from the response. `story_count` exists internally on
`SectionTimeline` (`models/business/section_timeline.py:62`; docstring `:54` —
*"Number of section_changed stories after filtering"*) and is **dropped at the
response boundary**: `OfferTimelineEntry` (`:158-209`) carries seven fields —
`offer_gid`, `office_phone`, `offer_id`, `active_section_days`,
`billable_section_days`, `current_section`, `current_classification` — and
`story_count` is not among them, under `extra="forbid"` (`:212`). A payload with
100 % imputed rows is byte-indistinguishable from one with 0 %.

### C-7 — tier (iii) is refuted, not merely unproven

Revision 3's `:1196-1199` declared edit history *"genuinely absent and not
constructible"* — the **only** remaining "actually expensive" cost tier at the
fork. Three receipts, ascending:

1. **`DEFAULT_STORY_TYPES` admits nine subtypes** (`cache/integration/stories.py:23-33`),
   of which **six are edit-class or custom-field-edit**: `assignee_changed`,
   `due_date_changed`, `marked_complete`, `marked_incomplete`,
   `enum_custom_field_changed`, `number_custom_field_changed`. Revision 3's
   entire edit-history argument used **one** (`section_changed`).
2. **`filter_relevant_stories` is a READ-time filter** — a pure list
   comprehension over an already-fetched in-memory list
   (`cache/integration/stories.py:266-294`, `:294`
   `return [s for s in stories if s.get("resource_subtype") in include_types]`).
   `load_stories_incremental` does **no** narrowing at cache-write: on a cache
   miss it calls `await fetcher(task_gid, None)` and writes the result whole
   (`:141-146`).
3. **Decisive — the fetcher applies no subtype filter at all.**
   `clients/stories.py:482-505` builds `params` from `_build_opt_fields(opt_fields)`
   plus `limit`, optional `since`, optional `offset`, and calls
   `/tasks/{task_gid}/stories`. There is **no `resource_subtype` parameter
   anywhere in the fetch**. Docstring `:483`, verbatim: *"Fetch all stories for a
   task, optionally since a timestamp."*

**The only narrowing in the entire chain is at READ time, by one consumer** —
`section_timeline_service.py:341`, `s.resource_subtype == "section_changed"`.

> **Restated tier (iii): the substrate does not exclude edit history. One
> consumer discards it.** Edit history is **not contracted** and its
> *availability* is unverified — but *"absent and not constructible"* is
> **false**, and it was the load-bearing sentence under this artifact's only
> remaining expensive cost tier.

This is the identical correction S4 was forced into on its own negative result,
reached here one sprint later — which is itself evidence the error is
structural to the approach, not incidental to one seat.

---

## REVISION 3 — the two conditions

Delta pass 2 of `CRITIQUE-s1-sayable-predicate-2026-08-12` returned
**UPHELD-WITH-CONDITIONS**. The **BLOCK is DISCHARGED**. Item 1a was attacked
five ways and held on all five. **Both of revision 2's rejections were conceded
outright** — the critic recorded that on F-3 it *"asserted a source was usable
without checking whether this initiative may use it"* and that on F-6 it had
authored *"the F-1 error class"* itself.

**This revision is narrow. Two conditions, nothing else re-opened.**

| condition | disposition | what moved | classification change |
|---|---|---|---|
| **C-1** — revision 2 routed item 1a's author to `/aggregate`, which carries **neither** receipt its render needs | **ACCEPTED — and the repair is larger than a swap** | §3.0 re-routes 1a to **`/rows`**, verified against both metas before committing. Verification found the age problem is **not** fixed by the swap — *neither* endpoint carries a content as-of — and that the platform's own content axis is **derived from the row payload**, which is why `/rows` is the answer. | none directly; makes 1a's `SAY-ABLE` renderable |
| **C-2** — `section-timelines` is an unfenced, retrospective, Asana-observed surface that reopens three grounds | **ACCEPTED in full** | §3.1 re-derived for 1b, 2 and 5. | **YES — item 2 → `SAY-ABLE`; item 5 splits, 5a → `SAY-ABLE`** |

### C-1 — what revision 2 would have caused, stated plainly

A downstream author follows revision 2's §3.0 to `POST /{entity_type}/aggregate`,
needs an age to render, and finds **exactly one age-shaped field**:
`AggregateMeta.data_age_seconds` (`query/models.py:241-244`). That field is, by
name, the one the ASR readiness gate abandoned on honesty grounds —
`readiness.py:84-87`, verbatim:

> `# The gate reads a CONTENT axis: max(last_modified) over the rows actually`
> `# returned, derived per response by the SDK. It does not read the serving cache`
> `# entry's age (`data_age_seconds`), which advances on a rebuild whether or not`
> `# one byte of upstream data moved -- a build clock wearing a freshness badge.`

**Revision 2 would have routed an author into the founding defect of this entire
crusade, using the field this artifact pointed them at.** A predicate whose whole
purpose is refusing unsound renders must not itself hand an author the unsound
field. And it could not have been patched at the endpoint: `AggregateMeta` is
`extra="forbid"` (`models.py:228`) **and** `AggregateMeta` is on the shape
`:1502-1503` fence list, so the missing receipts cannot be added.

Recorded as a **third** instance of one error class, now named:

> **This seat's recurring failure is asserting a surface's fitness from a
> partial read of it.** Rev-1 read one log line and generalised to "the
> substrate." Rev-2 read the aggregate *compiler* (`aggregator.py:49` — legal,
> dtype-compatible, true) and never read the aggregate *envelope*
> (`models.py:225-262` — receipt-barren). Legality is not fitness. The gates
> ask what a render *can* carry; verifying that requires reading the **response
> contract**, not only the request contract.

### C-2 — the surface, and what it does not do

`section-timelines` is mounted unconditionally (`api/main.py:488`), replays each
offer's Asana section history over a caller-chosen window
(`section_timelines.py:103-106`), and filters Asana's own story stream to
`resource_subtype == "section_changed"` (`section_timeline_service.py:341`) via a
fetch-through cached client bounded at 2 h
(`section_timeline_service.py:334-338`). An independent grep of all three files
for `SectionInfo`, `section_persistence`, `mark_section_complete`, `manifest`,
`RowsMeta` and `AggregateMeta` returns **zero matches** — it is **unfenced**.

**The observer is Asana's own event log, read at request time.** That is the
property that moves three verdicts, and it is the same property that cleared
item 1a: *the datum is the observed system's own assertion, not an inference
from our observation cadence.*

**What it does NOT do — the distinction that keeps 1b withheld:**

> ***Edit* history cannot be manufactured backward. *Movement* history can.**

A `section_changed` story records a **move**. `last_modified` records an
**edit** — bumped by a custom-field change, a description edit, a comment, none
of which emit a `section_changed` story. The story log is therefore a **strict
subset** of the edit stream. Candidate 1 is a *quiet-time* readout keyed on
edits; candidate 2 and candidate 5's first limb are keyed on *movement*. The
surface serves the second class and not the first.

---

## REVISION 2 — what changed under BLOCK

`CRITIQUE-s1-sayable-predicate-2026-08-12` (audit-lead, hygiene, rite-disjoint)
returned **BLOCK** on revision 1. Every finding is dispositioned below. Every
receipt the critic offered was **re-verified own-hands at `origin/main`** before
acceptance — none is taken on the critic's word.

**The BLOCK is upheld.** The FALSIFICATION premise in revision 1's §3.1 was
**wrong**, it was wrong **in the expensive direction**, and §5 O-6 forwarded it to
an operator-reserved fork. That is charter `:52` (`NEVER CONFIDENTLY WRONG`)
firing against the artifact that invokes it. The correct claim is
**uncontracted-and-partly-fenced, not absent** — and the distinction is the whole
cost delta at GATE-FORK.

### Disposition table

| finding | disposition | what moved | classification change |
|---|---|---|---|
| **F-1** — FALSIFICATION premise REFUTED; the measurand exists | **ACCEPTED-WITH-NARROWING** | §3.1 re-derived from the ground up; §3 items 1/2/5 re-run; §5 O-6 rewritten. **Narrowing**: of the critic's three paths only **one** is available to this initiative — the other two are `SectionInfo`-derived and fall inside the shape `:1502-1504` zero-K-lane fence the critic did not read. **Addition the critic missed**: `last_modified` is last-move-only, so the surviving path serves the *current-state* limb and **cannot** serve the *week-by-week* limb. | **YES — item 1 splits; 1a becomes `SAY-ABLE`** |
| **F-2** — masking is the ASR gate's reduction, not the substrate's | **ACCEPTED** | §2.2 shape 2 rewritten. `group_by:["section"]` applies no cohort `max`; the masking is a property of one consumer's reduction and is fixed by querying differently. | contributes to item 1a |
| **F-3** — zero-row sections are enumerable, not invisible | **ACCEPTED-WITH-NARROWING** / **disposition REJECTED-WITH-RECEIPT** | §2.2 shape 3 rewritten. The *fact* is accepted: `section_status_updated` enumerates all 34 sections with names and row counts. The *disposition* ("G2 should PASS with exhibition") is **rejected**: that emission is the K-lane manifest write path (`section_persistence.py:537-560`), fenced by shape `:1502-1504`. The sections are **fenced, not invisible** — a different and more closable defect. | changes §2.7 row 3's **grounds**, not its verdict |
| **F-4** — item 2's flat negative on per-offer transitions is false | **ACCEPTED** | §3 item 2's justification replaced. `"section_changed"` is in `DEFAULT_STORY_TYPES` (`stories.py:26`) — a per-offer transition with a timestamp. Reason replaced by a UV-P on population/horizon, per the critic's own point that revision 1 knew how to carry UV-Ps and did not here. | verdict unchanged, **grounds replaced** |
| **F-5** — §2.1 contradicts §1.3; normalisation order undeclared | **ACCEPTED** | §2.1 split into **G1-tense** (rescuable by DR-1) and **G1-two-clock** (not rescuable by anything). The *"no disclosure rescues it"* rule is narrowed to the two-clock limb only. Normalisation order **declared**: G1 runs **after** DR-1. | resolves the §2.7-row-3 inconsistency |
| **F-6** — G3 clause (c) is under-strict, not over-strict | **ACCEPTED** | §2.3 rewritten: (c) is **subordinated to (b)**, never an alternative to it. The repaired gate is re-run on items 1 and 5. It does **real work in both directions** — item 1a passes on a genuine point-observation receipt; item 5 now **correctly fails** where clause (c) would have rescued it by rewording. | **YES — the repaired gate changes both** |
| **F-6 sub-claim** — the content-change event stream is a genuine (b) receipt | **REJECTED-WITH-RECEIPT** | `builders/freshness.py:294-297` states verbatim that null-watermark sections (**~21/34 offer**) *"bypass this branch entirely."* The stream is structurally blind to exactly the sections item 1 exists to surface. It is a coverage receipt for the watermark-bearing subset **only**. | narrows the (b) options |
| **F-7** — render conditions evaluated where no render exists | **ACCEPTED** | Resolved in the direction the critic named: **the predicate classifies CLAIMS.** §2 gates test **capability** (is the denominator *exhibitable*? is the bound *known*?); §4 tests **performance** (is it *exhibited*? *stated*?). "and exhibited" struck from G2; "stated in the render" struck from G4. `SAY-ABLE` is now reachable and §2.7 row 2 is consistent. | **YES — unblocks item 1a** |
| **F-8** — UV-P-5 is manufactured | **ACCEPTED-WITH-NARROWING** | UV-P-5 **DISCHARGED** at §6 with the value **30 days** (`EVIDENCE-w1:624`, live `describe-log-groups`). The stated REASON was **doubly false**: `terraform/services/asana/` exists at *this* repo's `origin/main` (6 tracked files) **and** at the autom8y monorepo's `origin/main` (`main.tf:101`). **Restated, not struck**: the honest residual is the **declaration site**, not the value — per S4, the 30 is a module default in a *third* repo at pinned `ref=0fb9527b`, consumed without declaration, mutable with zero diff in either repo. | strengthens the contracted-vs-reachable distinction |
| **F-9** — SVR ledger sound (9/9 spot-checks) | **ACCEPTED (no change required)** | Recorded. The defect was scope, not accuracy — exactly as the critic diagnosed. | none |
| **F-10** — DR-4's exemplar is half a counter-example | **ACCEPTED — gift taken** | DR-4 rewritten. `freshness.py:617-627` emits `"max_age_seconds": 0` and `"stale": False` in the `available: False` branch — **null-meaning-fresh in the code DR-4 cites as the pattern to inherit.** DR-4 is now grounded on a shipped surface that does *not* satisfy it. | none; strengthens DR-4 |
| **F-11** — REPORT 67-vs-68 wobble | **ACCEPTED (advisory)** | Noted at §1.3 and routed. | none |
| **critique §2.2** — the 1,000 is the caller's, not the platform's | **ACCEPTED** | §1.3 corrected: ceiling is `10_000` (`guards.py:50,67-72`); the 1,000 is the ASR's own request. | none |
| **critique §2.4** — §1.3 gloss and §2.7 row-2 wording | **ACCEPTED** | Both corrected to name the predicate and the served frame. | none |
| **critique §6.8** — §7 citation `:551-552` | **ACCEPTED** | Corrected to `:552-553`. `:551` is `"entity_type": entity_type,`. | none |

### Verdict-relevant deltas

> **READ AS HISTORY, NOT AS LIVE STATE.** Items 1, 2 and 5 below were **superseded
> at revision 3** under critique conditions C-1 and C-2. Specifically: item 1b's
> *"forward-accrual"* ground and item 5's *"forward accrual + `REPORT…:172`
> watchdog"* grounds are both **WITHDRAWN**, and items 2 and 5a are now
> `SAY-ABLE`. The live classifications are in **§3.1**; this block records what
> rev-2 changed and why, per charter `:57`.

1. **Item 1 SPLITS.** `1a` (current-state per-section quiet-time) is **`SAY-ABLE`**
   today. `1b` (the *"week by week"* limb) is `WITHHELD-PENDING` on a
   **forward-accrual**, not an absence. Revision 1 said neither.
2. **§3.1's headline is replaced.** *"the source does not carry the measurand at
   all"* → *"one contracted, K-lane-free path carries the current-state measurand
   today; no unfenced path carries its history, and history cannot be
   manufactured backward."*
3. **§5 O-6 is reversed in direction.** It told the operator Mission A costs
   **more** than the frame implies. On the corrected premise the current-state
   half costs **less** — it is reachable on declared schema with no new emission —
   and only the retrospective half costs more, for a reason revision 1 never
   named.
4. **Items 2 and 5 keep `WITHHELD-PENDING` and change grounds.** Item 5's new
   grounds are *narrower and better* — the repaired G3 fails it for the reason G3
   exists, which the unrepaired G3 could not do.
5. **Items 3 and 4 are untouched.** The critic attacked both and could not dent
   them; F-5's narrowing leaves them on the limb that survives.

### What revision 1 got wrong, structurally

It inspected **one** `logger.info` call and let the conclusion inherit the scope
of the phrase *"the substrate."* The SVR ledger was accurate at every anchor and
the reasoning above it was sound; the defect was **denominator**, in an artifact
whose own G2 exists to catch exactly that. Recorded, not papered.

---

## 0. Scope fence — what this artifact decides, and what it does not

**It decides:** whether an arbitrary candidate readout may be *said* honestly
today, and what disclosure any published number must carry.

**It does NOT decide:** whether a readout may be *built* (source-of-record —
S4), whether a *rail* exists to carry it (S3), whether anyone *wants* it (WS-A,
UV-P-2 open), or whether it may be *delivered* to a surface the charter reserves
(CR-1 / CR-2 / OS-6).

> **SAY-ABLE IS NECESSARY, NEVER SUFFICIENT.** A downstream author who reads a
> `SAY-ABLE` verdict here as a build authorization has misread this artifact.
> Publication requires `SAY-ABLE` **AND** a contracted source **AND** a verified
> rail **AND** clearance of the charter gates at §2.5.

**Binding fences carried, not re-litigated:**

- **P-3 is RULED** (`RULING-operator-option4-interview-2026-08-12.md:21`) —
  *"Accept until replaced" — honest aborts continue with NO clock; the
  successor's landing is the only exit.* This artifact does not argue with it,
  route around it, or attach a clock to it. §1.2 shows how the predicate is
  applied **without reading it**.
- **CR-1 is BINDING** (`.sos/wip/frames/asana-native-insight-delivery.shape.md:414-424`)
  — all three Asana write classes are operator-reserved; the initiative is
  READ-ONLY with respect to the board. **No Asana-native rail is proposed
  anywhere in this artifact.**
- **Zero K-lane dependency** (shape `:1502-1505`). Nothing here requires a number
  that exists only on the K-lane. Where a candidate would need one, it WAITS and
  is recorded as waiting.

---

## 1. The ground the predicate stands on

### 1.1 The floor, not the pause

The predicate is grounded in the charter's hard floor, **not** in the interim
posture. Verbatim, `CHARTER-decision-space-of-record-2026-07-30.md:52`:

> Hard floor under everything: **NEVER CONFIDENTLY WRONG.** If a thing can't be
> made trustworthy simply, refuse or surface it — never ship it dressed up.

and `:54`:

> **"Done" for priority domains requires a real-world check.** Anything touching
> **money, customers, or data people act on** is not done until checked against
> reality at least once — not merely against its own tests.

and the stage-1 bar the operator set for this very arc,
`RULING-operator-option4-interview-2026-08-12.md:22` (P-4, verbatim):

> "Observability truthful first" — stage 1: every alarm/description tells the
> truth; stage 2: gate closes under the statistical bar.

**Consequence:** the question this predicate answers is *"can this readout be
stated in a form that is not confidently wrong?"* — a question with an answer
whether or not the verification axis is refusing. That is what makes it
durable across the axis flip and applicable without re-reading P-3.

### 1.2 P-3 enters as one input variable, never as an argument

The predicate reads **one** state variable off a single line and does not
interrogate it:

```
AXIS_STATE ∈ { REFUSING, LIVE }
AXIS_STATE = REFUSING   # as of 2026-08-12; source: RULING-...:21 (P-3)
                        # flips to LIVE at ADR-007 gate-live; nothing else flips it
```

A downstream author reads `AXIS_STATE` and proceeds. When the successor lands,
the **same predicate re-runs unchanged** and every `WITHHELD-AXIS` item becomes
say-able without re-authoring anything. This is the mechanism that discharges
the mission's *"without re-litigating P-3"* requirement:
**P-3 is a value, not a premise.**

### 1.3 REFINEMENT R-1 — the discriminator is REFERENT, not property

The frame states the spine as *"Completeness and freshness are different
properties, and only one of them is in doubt"*
(`.sos/wip/frames/asana-native-insight-delivery.md:71-80`). **The conclusion
holds. The stated reason is imprecise, and the imprecision would mislead a
downstream author.** Surfaced, not papered (charter `:57`).

**What is actually receipted.** `REPORT-asr-team-brief-2026-08-12.md:138` reads
*"the full offer lists are coming through intact (68 of 68 active, 48 of 48
activating, on every run)"*. Direct inspection of the emitter shows those two
numbers are `total_count` and `returned_count` from the query result meta
(`src/autom8_asana/api/routes/query.py:552-553`).

**R-1 was corroborated at STRONG by the rite-disjoint critique, on receipts
stronger than revision 1 held** (`CRITIQUE…§2.1`). Re-verified own-hands at
`origin/main` (`4129ae7e`, this repo; `0c2fc6a5`, the autom8y monorepo — note the
critique pinned `7bbb418e`, which has since moved; the receipts hold at both):

| step | receipt | what it establishes |
|---|---|---|
| the frame is loaded from the provider (cache), not Asana | `src/autom8_asana/query/engine.py:130-134` | the population is the **served frame** |
| filters applied | `engine.py:168-170` — `df = df.filter(filter_expr)` | `total_count` is **post-predicate** |
| `total_count` taken | `engine.py:189-190` — `# 8. Total count (before pagination)` / `total_count = len(df)` | pre-slice length of the **filtered** frame |
| limit clamped, then sliced | `engine.py:192-196` | the only thing between the two numbers is **pagination** |
| `returned_count` taken | `engine.py:243` → `engine.py:286` (`returned_count=len(data)`) | post-slice |

The engine states the consequence itself, unprompted, in a comment written for an
unrelated purpose — `engine.py:136-141`:

> `# The post-filter total_count (step 8) conflates the two -- a zero-matching where on a 1480-row project would otherwise be mis-attested as honest_empty.`

An in-repo, author-independent statement that post-filter `total_count` **cannot
be read as a frame-level completeness fact**. The **only production consumer**
agrees, rite-disjoint from both seats: `autom8y@origin/main`
`services/account-status-recon/src/account_status_recon/fetcher.py:409-410` maps
the pair, `:390` calls it verbatim *"the truncation pair"*, and `readiness.py:96-97`
reads it as *"T-GUARD -- returned_count < total_available. A watermark over a
truncated result is a watermark over an arbitrary window."* Nothing anywhere
reads `68/68` as board correspondence.

> **`68/68` is a NON-TRUNCATION receipt against a row cap. It is not a
> correspondence receipt against the Asana board.** It says *"we returned every
> row we had **that matched this predicate**"*, not *"we had every row that
> exists."*

**Two corrections to revision 1's own gloss, both adopted from the critique:**

- The qualifier *"that matched this predicate"* is load-bearing. `total_count` is
  taken **after** `df.filter()` (`engine.py:168-190`). *"Every row we had"* still
  sounds like a statement about the frame's contents; it is not.
- The **1,000 is the caller's, not the platform's.** `guards.py:50` sets
  `max_result_rows: int = 10_000` and `:67-72` clamps by `min(requested,
  max_result_rows)`. The 1,000 in `REPORT…:100-104` is the ASR's own request
  (`fetcher.py:504-514`, `limit=1000` per classification) — **10× under the engine
  ceiling.** Immaterial to the verdict; material to any downstream author who
  would read "1,000-row cap" as a platform invariant to rely on.

**Advisory, recorded not reconciled** (critique F-11): `REPORT…:101-102` says
*"about 67 active and 48 activating"* while `:138` says *"68 of 68 active."*
Almost certainly one row moving between the capacity note and the check-in — but
it is precisely the class of thing DR-5 exists to surface, occurring inside the
founding artifact this disclosure rule governs.

Correspondence-to-the-board is precisely what the verification axis was built to
certify, and it is refused. So "wholeness" and "recency" are **not** independent
properties — wholeness-relative-to-the-board inherits the recency doubt at the
frame boundary. Stated as the frame states it, an author could conclude that
*"the board has 68 active offers"* is say-able. **It is not.**

**The correct discriminator is the readout's REFERENT:**

| referent | example claim | status |
|---|---|---|
| **the observation series** | "at the last observed frame build, the served active cohort held 68 rows, none truncated" | say-able — the series *is* the thing observed |
| **the world now** | "the board has 68 active offers" | needs the refused axis — the claim is about Asana, and the frame's correspondence to Asana is unvouched |

Both sentences carry the *same integer*. One is say-able and one is not. **The
predicate operates on the claim, never on the number.**

**Why the frame's conclusion nonetheless survives.** A series-referent readout is
not made *wrong* by frame lag; it is made *lagged*, by a **measured, bounded
amount in a known direction**. `EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:188`
measures it: *"inter-build gap: median 2 361 s (39 min) p90 13 008 s (3.6 h) max
14 394 s (4.0 h)"*, and `:182,191` state the direction — the served frame is
*"an optimistic upper bound"*, the reality *"strictly worse"*. The series trails
the board and never leads it, corroborated independently by
`ATTEST-rel6-realize-offers-content-axis-2026-08-12.md:752` — *"every observed
reading errs stale."*

**A bounded error in a declared direction is not confident wrongness.** That is
the whole of why board-behaviour readouts survive the pause, and it is a
different sentence from "completeness is receipted."

---

## 2. THE PREDICATE

Apply the gates **in order**. The **first failure decides**; do not average, do
not weigh. Each gate is answerable from the candidate's own wording plus the
named receipts. No gate requires reading P-3.

### 2.0 What the predicate classifies, and when it runs — DECLARED (rev-2, F-7)

Revision 1 left this implicit and paid for it: G2 required a denominator to be
*"exhibited"* and G4 required a bound *"stated in the render"*, both evaluated at
a moment when **no render exists**. Applied literally that made `SAY-ABLE`
unreachable, and revision 1 awarded it anyway. Resolved explicitly:

> **The predicate classifies CLAIMS, not renders.**
>
> - **§2 gates test CAPABILITY.** Is the denominator *exhibitable*? Is the bound
>   *known*? Is a coverage receipt *available*? A gate never asks whether
>   something was typed into a line.
> - **§4 disclosure rules test PERFORMANCE.** Is it *exhibited*? Is it *stated*?
>   These are obligations on the author of a render, binding on every published
>   number including every `SAY-ABLE` one.
>
> A `SAY-ABLE` verdict therefore means: *"a truthful render of this claim is
> constructible today."* It does **not** mean any particular render is truthful.
> §0's fence stands unchanged and is now load-bearing twice over.

**Normalisation order — DECLARED (F-5).** The gates run **on the DR-1-normalised
claim**, not on the candidate's colloquial wording.

Rationale: DR-1 is a *mandatory* transform on every published number (§4.2). A
predicate that ran before it would fail nearly every candidate on tense alone —
including candidates whose only defect is that a human wrote them in a hurry —
and would collapse the `WITHHELD-AXIS` / `WITHHELD-PENDING` split that is the
artifact's most load-bearing distinction. Running after DR-1 asks the honest
question: *"once stated as honestly as the disclosure rule permits, is this claim
still un-say-able?"*

**Consequence, stated plainly**: the tense limb of G1 can never terminate the
predicate on its own, because DR-1 always fixes tense. Only the **two-clock** limb
terminates. §2.1 is rewritten accordingly.

**Two duplications removed** (F-7): G4 was `≡ DR-6` and G2's exhibition limb was
`≡ DR-5`. Both now live in §4 only. Two of five gates were disclosure rules
wearing gate costumes, and that — not the substrate — is the mechanical reason
revision 1 landed three of five candidates on `WITHHELD-PENDING`.

### 2.1 G1 — REFERENT (the discriminator)

> **Ask:** *If the served frame were N hours older than the readout believes,
> would the readout's assertion become **false**, or merely **lagged**?*

| answer | class |
|---|---|
| **lagged** — the assertion is about the observation series, and age shifts *when* it describes, not *whether* it is true | **COMPLETENESS-CLASS** |
| **false** — the assertion is about the world now, and age produces a difference indistinguishable from the real-world difference being reported | **VERDICT-CLASS** |

**Fast screen (apply first; it decides most candidates in one line):**

> **The two-clock test.** Does the readout's value require joining board state to
> a **non-Asana system of record** (campaign spend, billing, payments) whose
> clock runs independently of the board's?
> **YES → VERDICT-CLASS.** Two independent clocks can drift apart, and the drift
> is arithmetically indistinguishable from the finding the readout exists to
> report.
> **NO → continue to G2.** A readout computed from board observations alone, or
> from board observations against *themselves over time*, has one clock; a single
> clock cannot disagree with itself.

**G1 has two limbs, and only one of them terminates (rev-2, F-5).**

Revision 1 stated one terminating rule — *"no disclosure rescues it, because the
failure is in the value, not in the render"* — and then, four paragraphs earlier
at §1.3, offered a pair of sentences carrying **the same integer** that differ
**only** in render, one say-able and one not. Those two statements cannot both be
right. The repair is to name the limbs:

| limb | question | rescuable? |
|---|---|---|
| **G1-tense** | is the claim *worded* world-now? | **YES** — by DR-1 restatement. Because §2.0 declares the gates run **after** DR-1, this limb is already discharged when G1 is reached and can never terminate. |
| **G1-two-clock** | does the value **join board state to a non-Asana system of record** (campaign spend, billing, payments) whose clock runs independently? | **NO** — no wording rescues it. A stale board field against live external spend produces a **wrong number**, not a mistimed one, and the error is arithmetically indistinguishable from the finding the readout exists to report. |

**Only G1-two-clock terminates the predicate: `WITHHELD-AXIS`.** *"No disclosure
rescues it, because the failure is in the value, not in the render"* is **true of
the two-clock limb and false of the tense limb**, and is hereby narrowed to the
limb it is true of.

The screen revision 1 demoted to *"the cheap path"* is therefore not cheap: it is
**the whole of the terminating gate**. Applied to §1.3's own pair, this comes out
right — *"the board has 68 active offers"* is single-clock and is rescued by DR-1
into a say-able series claim, which is exactly what §1.3 asserts.

**YES → `WITHHELD-AXIS`. NO → continue to G2.** A readout computed from board
observations alone, or from board observations against *themselves over time*,
has one clock; a single clock cannot disagree with itself.

### 2.2 G2 — DENOMINATOR

> **Ask:** *Over what population is the readout computed, is that population one
> the platform observes through a source this initiative may use, and **can** the
> readout exhibit the difference?*

Three failure shapes. **Two of the three were mis-stated in revision 1 and are
corrected here on receipts the critique supplied and this seat re-verified.**

1. **Population substitution.** *(unchanged — survived critique.)* The receipted
   population is **offers** (68/68, 48/48 — `REPORT…:138`). A readout whose
   population is **sections** has not inherited that receipt and must be able to
   exhibit its own.

2. **Reduction masking — CORRECTED (F-2).** Revision 1 wrote that the quieter
   sections are *"masked by construction."* **That is false as a claim about the
   substrate.** The `max`-over-cohort reduction (`EVIDENCE-w1:198-200`, argmax
   named per tick at `:146-151`) is the **ASR readiness gate's own roll-up**, and
   a new readout is under no obligation to consume it. Underneath it,
   `EVIDENCE-w1:146-151` names per-section watermarks by GID at microsecond
   resolution.

   The honest form: *"masked by **this consumer's** construction."* The remedy is
   to **query differently**, not to wait for a source decision. Concretely, a
   `group_by:["section"]` aggregate applies **no** cohort reduction — each section
   carries its own value. The `max()`-shields / `min()`-exposes asymmetry (P-5,
   `RULING…:23`) is still the right lens; it just indicts a *reduction choice*,
   which is the reader's to make.

3. **Zero-row invisibility — CORRECTED, then RE-FAILED ON DIFFERENT GROUNDS
   (F-3).** Revision 1 wrote that a row-derived observation cannot see a section
   with no rows, and inferred that zero-row sections are *"the invisible set."*
   The first clause is true; **the inference is false.** The critique is right:
   the census is *section*-derived, not row-derived — `section_status_updated`
   emits one record per section with `rows` and `name`
   (`section_persistence.py:551-560`), and `EVIDENCE-w1:642-643` matched
   **8 311 records across all 34 sections**. That emission is *how revision 1's own
   cited `:128` figure ("21 sections are 0-row") was obtained.* Revision 1 cited a
   number as evidence that the thing producing it could not be seen.

   **Where this seat departs from the critique.** The critique concludes *"G2
   should PASS with exhibition."* **Rejected, with receipt.** That emission is
   produced inside the **K-lane manifest write path**: `section_status_updated` is
   logged from `update_section_status_async` immediately after
   `manifest.mark_section_complete(...)` and `_save_manifest_async(manifest)`
   (`section_persistence.py:537-560`), over `SectionInfo` (`:83-93`). Shape
   `:1502-1504` binds this initiative verbatim:

   > **Zero K-lane dependency**: no touch on the offer-axis combiner, the
   > freshness-meta reducer, `RowsMeta` / `AggregateMeta`, **the manifest write
   > path, or `SectionInfo`**. **If a readout wants a number that only exists on
   > the K-lane, it WAITS.**

   So the correct disposition is **fenced, not invisible** — a materially
   different and far more closable defect, and one whose closing condition is an
   *operator/initiative-boundary* event rather than a source build.

   The unfenced candidate for a full section roster is the **`section` entity
   type**, which is registered and body-parameterized with its own schema
   (`core/entity_registry.py:1004-1020`; `dataframes/schemas/section.py`) and is
   reachable at `POST /v1/query/section/rows`. **Whether the section frame
   enumerates sections holding zero tasks is not determinable by static read** and
   is carried as a UV-P at §6 rather than assumed in either direction.

**PASS** iff the denominator is **exhibitable** from a source this initiative may
use. **FAIL → `WITHHELD-PENDING`**, with the missing observation named.

> **Note the change (F-7):** the *"and exhibited"* limb is **struck**. Exhibiting
> the denominator is DR-5's duty, in §4, binding on every published number. G2
> asks only whether it *can* be done.

### 2.3 G3 — POLARITY (the negative-claim gate)

> **Ask:** *Does the readout assert an **absence** — "has not been edited",
> "nothing moved", "no X occurred"?*

An absence claim over a window is true only if the **observer was demonstrably
live across the whole window**. Without a per-window coverage receipt,
*absence of observation* is indistinguishable from *absence of event* — the
canonical confidently-wrong shape.

This is not hypothetical here. `REPORT-asr-team-brief-2026-08-12.md:172` records
it as a live, twice-realised gap: *"a silently stopped job produces no error, so
today nothing pages; this has bitten us twice, including the checker itself
skipping runs unnoticed."* The watchdog that would close it is improvement #1 —
**named as coming, not shipped**.

**REPAIRED (rev-2, F-6).** Revision 1's PASS condition offered three *alternative*
clauses, the third of which — *"restate positively"* — is unconditionally
available to every absence claim and adds **zero epistemic content**. If the
observer was dead across the window, *"last observed edit: 2026-08-07"* is exactly
as misleading as *"has not been edited since 2026-08-07"*; the reader reconstructs
the forbidden inference in one step. Clause (c) was a **tense** fix offered as an
equal to (b), an **evidence** fix, while the gate's own rationale demands (b).

The critique's diagnosis is accepted in full and is worth restating because it
inverts revision 1's self-assessment: **G3 was not over-strict. It was
under-strict, and internally inconsistent** — as written it refused nothing,
because (c) always applies. Judgment leaked past the gate at exactly the point
this seat was charged to check.

**Repaired PASS condition. (c) is subordinated to (b), never an alternative:**

> **PASS** iff **either**
> **(a)** the claim is positive — it asserts an observed value, not the
> non-occurrence of an event; **or**
> **(b)** the readout carries an **observation-coverage receipt for its window**
> *and* is restated positively. Both, conjunctively. The receipt is
> `k of n expected observations present` for a window claim, or the frame's own
> as-of plus lag bound for a **point** claim (a claim about an observed maximum at
> a single observation is not corrupted by observer death across any prior
> window — it is only made stale, which DR-2 and DR-6 already govern).
>
> **FAIL → `WITHHELD-PENDING`.**

**What the repair costs, honestly.** It is two-sided. It **rescues** item 1a,
whose point-observation receipt is genuine and available. It **fails** item 5,
which the unrepaired gate would have let through on a one-line rewording. A gate
that only ever loosened would not be a repair.

**A (b) receipt this seat will NOT accept, contra the critique.** The critique
offers the per-section content-change stream (`freshness_delta_section_updated`,
`builders/freshness.py:563-574`; 168 records/16 d at `EVIDENCE-w1:645-646`) as an
observation-coverage series. **Rejected on the emitter's own documentation.**
`builders/freshness.py:294-297` states verbatim:

> `# Residual (documented, NOT a regression): null-watermark`
> `# sections (~21/34 offer, ~4/17 unit per QA 2026-05-27)`
> `# bypass this branch entirely and retain the pre-existing`
> `# hash-only detection.`

The emission is gated behind `if section_info.watermark is not None:` (`:298`).
It is structurally blind to **approximately the same 21-of-34 sections that a
quiet-corner readout exists to surface** — and it is `SectionInfo`-derived, so it
is K-lane-fenced besides. It is a coverage receipt for the **watermark-bearing
subset only**, and must be exhibited as such if used at all.

### 2.4 G4 — ERROR DIRECTION

> **Ask:** *Where the readout is imprecise, is the imprecision **bounded** and in
> a **declared direction**?*

A bound that errs in a stated direction is honest (charter `:52` — refuse or
**surface**). An unbounded or undeclared-direction error is not. The platform
already supplies the two board-behaviour bounds: frame lag ≤ 4.0 h
(`EVIDENCE-w1…:188`), direction stale-never-fresh (`ATTEST-rel6…:752`).

**REPAIRED (rev-2, F-7).** Revision 1's PASS condition was *"bound and direction
are **stated in the render**"* — a condition on a rendering, evaluated before any
render exists. Applied literally it failed every candidate including revision 1's
own `SAY-ABLE` exemplar, whose G4 cell was then filled with a statement of what
*could* be disclosed. That is judgment leaking past a gate in the opposite
direction from F-6, and it made `SAY-ABLE` structurally unreachable.

**~~PASS iff a bound is known and its direction is known.~~ SUPERSEDED AT REV-5
BY G4′.** The rev-2 repair asked *"is the direction **known**?"* — a question
answerable **by assertion**. It never compelled enumeration, and **items 2 and 5a
both passed it while carrying errors that were not single-signed**. The critic
convicted its own repair: *"the same defect class I convicted G3 of at pass 1 and
left standing in G4."*

> ### G4′ — ERROR DIRECTION (branch-enumerating)
>
> **Enumerate every imputation, default, filter and clipping branch on the path
> from source event to rendered figure. State the sign on each. PASS iff all
> branches share one sign. An unenumerated branch is an undeclared direction.**
>
> **FAIL → `WITHHELD-PENDING`.**

**Clarification (rev-5).** *"Share one sign"* governs the **non-neutral**
branches. A branch that introduces no error is neutral and does not break the
conjunction. Without this, G4′ would fail every readout, since most steps on any
path are exact.

**Worked mechanically against all three contested items:**

| item | branches on the path | signs | G4′ |
|---|---|---|---|
| **2** — `billable − active` | imputation × currently-ACTIVE; imputation × currently-ACTIVATING | **understate**; **overstate** | **FAIL** |
| **5a** — weekend moved-set | imputed interval matched by `moved_to`+`since`/`until` with no `moved_from` (`temporal.py:51-64`); `idx == 0` guard drops genuine first move when `moved_from` **is** given (`:69-70`); cross-project noise filter drops stories (`section_timeline_service.py:343-346`); 2 h cache staleness (`:337`) | **overstate**; **understate**; understate; understate | **FAIL** |
| **1a** — `now − max(last_modified)` per section | imputation: **none**; default: none (`last_modified` is `nullable=False`, `base.py:76-82`); filters narrow *which rows*, not the value; clipping: none; frame staleness → value ages | only non-neutral branch is frame staleness → **overstate**; remainder exact | **PASS** |

**The honest limit.** G4′ compels enumeration; it **cannot compel completeness of
enumeration**. An author who has not read `query/temporal.py` enumerates what
they know and stops — which is precisely what happened at rev-3 and rev-4. The
closing clause converts that silence into a **defect** rather than a pass, which
is the most a written gate can achieve. What actually caught it, in every
instance, was **a second reader going one hop further** (§3.2).

> **Stating** the bound remains DR-6's duty, in §4, on every published
> board-behaviour number. G4 `≡ DR-6` under revision 1's wording; that
> duplication stays removed — G4′ is a capability test (**can** one sign be
> declared?), not a render test.

### 2.5 G5 — PUBLICATION AUTHORITY (not a say-ability gate)

Runs **independently** of G1–G4 and can reserve a fully say-able readout.

- **Charter `:55`(a) irreversibility** — can the publication be cheaply taken
  back? A Slack post's *record* is deletable; its *broadcast* is not (shape
  `:352-360`). Recurrence multiplies this.
- **Charter `:55`(b) sensitive list, regardless of reversibility** — anything a
  customer sees, anything touching security/credentials, anything that spends
  money or makes an external commitment. **Not statically decidable** where the
  audience is a mutable runtime property (shape `:373-379`).
- **Charter `:54` priority domains** — money / customers / data people act on:
  requires a real-world check before "done."
- **CR-1** — any Asana-native delivery is operator-reserved (shape `:414-424`).

**FAIL → `OPERATOR-RESERVED`**, which is orthogonal to and does not override the
G1–G4 verdict.

### 2.6 Verdict vocabulary (closed — do not extend or alias)

| verdict | meaning | exit condition |
|---|---|---|
| `SAY-ABLE` | passes G1–G4; may be stated today in the §4 disclosure form | — |
| `WITHHELD-AXIS` | fails G1 — needs the axis that is refusing | `AXIS_STATE = LIVE` (ADR-007 gate-live). **Nothing else.** |
| `WITHHELD-PENDING` | passes G1, fails G2/G3/G4 — blocked by **our own** disclosure or observation hygiene, **not by the pause** | the named receipt is carried |
| `OPERATOR-RESERVED` | fails G5 — say-ability is irrelevant until the operator rules | an operator ruling |

The `WITHHELD-AXIS` / `WITHHELD-PENDING` split is the load-bearing one:
`WITHHELD-PENDING` items are **actionable now** and are wrongly narrated as
"blocked by the pause."

**The vocabulary is unchanged in rev-2 — no value added, none aliased, none
retired.** What changed is that `SAY-ABLE` is now **reachable**. Under revision
1's wording it was not: G2 required a denominator to be *"exhibited"* and G4
required a bound *"stated in the render"*, both evaluated before any render
exists, so every candidate failed and the entry was dead (`CRITIQUE…F-7`). A
closed vocabulary with an unreachable member is a four-value vocabulary
pretending to be five. §2.0 fixes that without touching the enum.

**And the split now does work in both directions.** Revision 1 landed three of
five on `WITHHELD-PENDING` and narrated that as a substrate finding; the
mechanical cause was two disclosure rules wearing gate costumes. With the costumes
removed, one candidate reaches `SAY-ABLE` and the rest fail on named,
initiative-scoped conditions — which is exactly what `WITHHELD-PENDING` was
defined to mean.

### 2.7 Worked application to an arbitrary candidate (generality proof)

Three candidates **not** on the REPORT §6 list, to show the predicate decides
outside its calibration set. **Re-derived under the repaired gates (rev-2).** Each
row is stated in its DR-1-normalised form, per §2.0.

| candidate (DR-1-normalised) | G1 | G2 (capability) | G3 | G4 (capability) | verdict |
|---|---|---|---|---|---|
| *"Which accounts were overbilled in the week to {t}"* | **two-clock** (board ↔ billing) → VERDICT | — | — | — | `WITHHELD-AXIS` |
| *"At the {t} frame build, the served frame held 68 rows whose classification matched `active`, untruncated"* | single-clock, series referent → COMPLETENESS | population = offers, exhibitable; receipted `REPORT…:138` | **positive** (an observed count) | bound **known**: ≤4.0 h, stale-never-fresh | **`SAY-ABLE`** |
| *"At the {t} observation, these sections held zero offer rows"* | single-clock, series referent → COMPLETENESS | **FAIL** — the full section roster is enumerable only from `section_status_updated`, which is K-lane-fenced (§2.2.3); the unfenced `section`-entity path is **UV-P** | positive as normalised (**PASS** — G3 no longer decides this row) | bound known | `WITHHELD-PENDING` |

**Two corrections carried into this table from the critique:**

- Row 2's wording is fixed. Revision 1 wrote *"the active cohort held 68 rows"*,
  where *"the active cohort"* is under-specified and re-imports the very ambiguity
  DR-1 exists to kill. The honest form names the **served frame** and the
  **predicate**.
- Row 3's **grounds** change and its **verdict** does not. Revision 1 failed it on
  G2 *"zero-row sections are the invisible set"* **and** on G3 *"absence claim."*
  Both were wrong: they are enumerable (F-3), and once DR-1-normalised the claim
  is positive, not an absence claim (§2.0 order). It fails on a **fence** — a
  clean, named, initiative-boundary condition — which is a far better answer than
  revision 1's, and it is still the instructive row: a readout that looks
  trivially say-able is not, on the very property it purports to report.

---

## 3. The five REPORT §6 candidates, classified

> **Note on the count (rev-2):** there are still **five** REPORT §6 candidates.
> Candidate 1 as written at `REPORT…:185` bundles two limbs with **different
> verdicts** — *"which sections have gone longest without an edit"* (current state)
> and *"week by week"* (history) — so the classification table has **six rows**.
> Splitting it is not a scope change; it is the predicate refusing to average two
> answers into one, per §2's *first-failure-decides, do not average* rule.

The frame's first pass — *"items 1, 2 and 5 need completeness only; items 3 and 4
are verdict-class and are gate-starved. Three of five are buildable under P-3"*
(`.sos/wip/frames/asana-native-insight-delivery.md:81-85`) — was treated as a
**hypothesis and tested**, per the S1 charge.

**Result (rev-2, re-derived under BLOCK): the CLASS assignment is CONFIRMED.
The implied disposition ("three of five are buildable under P-3") is
CONFIRMED-IN-PART and FALSIFIED-IN-PART — and revision 1's re-derivation of it
was itself wrong.** Item 1 splits: its current-state half **is** say-able today,
on a contracted, K-lane-free path. Its historical half and items 2 and 5 are not
— on gates that name closable conditions, not on a source that does not exist.

### 3.0 The measurand, established before the gates run (rev-2)

Revision 1 asserted that items 1, 2 and 5 *"require per-section or per-offer
observation that does not exist today,"* generalising from the field list of one
`logger.info` call. **That is refuted.** Own-hands verification at `origin/main`
(`4129ae7e`), each anchor read directly:

**Path (a) — the per-offer edit-time measurand is a declared, non-nullable
schema column, and a per-section reduction over it is a legal request against a
shipped endpoint today.**

- `dataframes/schemas/base.py:76-82` — `ColumnDef(name="last_modified",
  dtype="Datetime", nullable=False, source="modified_at", …)`; `section` at
  `:83-89` (`Utf8`, nullable).
- `dataframes/schemas/offer.py:209-215` — `OFFER_SCHEMA` is built from
  `*BASE_COLUMNS`, so both columns are on **every offer row**. Mirrored in the row
  model at `dataframes/models/task_row.py:50-51`, `OfferRow(TaskRow)` at `:158`.
- `api/routes/query.py:565-572` — the `POST /{entity_type}/aggregate` route
  exists.
- `query/models.py:197-206` — `group_by` (1–5 columns) + `aggregations` (1–10).
- `query/aggregator.py:36` — `_ORDERABLE_AGGS = frozenset({AggFunction.MIN,
  AggFunction.MAX})`; `:49` — `"Datetime": _ORDERABLE_AGGS | _UNIVERSAL_AGGS`.
  An **explicitly enumerated** `Datetime × MAX` compatibility entry.
- Both validators resolve against the same schema object:
  `query/guards.py:96-102` (`check_group_by` → `schema.get_column`) and
  `query/aggregator.py:104-119` (`_compile_one` → `schema.get_column`, then the
  dtype matrix).

  Therefore `group_by:["section"], aggregations:[{column:"last_modified",
  agg:"max"}]` is **schema-legal and dtype-compatible against shipped code**.
  That is candidate 1's measurand — `now − max(last_modified)` per section — with
  **no new emission, no new retention, and no history required.**

#### 3.0.1 The receipt-bearing surface is `/rows`, NOT `/aggregate` (rev-3, C-1)

Revision 2 established that the aggregate *request* is legal and stopped there.
Legality is not fitness. Reading the aggregate **response contract** — which
revision 2 never did — shows the endpoint cannot carry a compliant render.

**Verified own-hands, both metas, before committing to the swap:**

| receipt the render needs | `/rows` (`RowsMeta`) | `/aggregate` (`AggregateMeta`) |
|---|---|---|
| section completeness — `honest_contract_complete` | **YES** — `models.py:451-459`, spread at `engine.py:292` | **NO** — absent from `models.py:225-262`; not spread at `engine.py:427-435` |
| `honest_empty` (attested empty vs still-building) | **YES** — `engine.py:293` | **NO** |
| FM-5 column contract — `contract_complete`, `unservable_required_columns`, `column_manifest` | **YES** — `models.py:489-520`, spread at `engine.py:294-296` | **NO** |
| truncation pair — `total_count` / `returned_count` | **YES** — `engine.py:285-286` | **NO** — `group_count` only (`models.py:230`) |
| freshness side-channel — `freshness`, `data_age_seconds`, `staleness_ratio`, `stale_served` | YES — `engine.py:298` | YES — `engine.py:434` (**identical**; same `_get_freshness_meta()` source) |
| **content as-of** | **NO** | **NO** |

**Two conclusions, and the second is the one that matters.**

1. `/aggregate` is **receipt-barren** on four counts and **cannot be fixed**:
   `AggregateMeta` is `extra="forbid"` (`models.py:228`) and is named on the
   shape `:1502-1503` K-lane fence. The missing receipts can be neither added nor
   spread.

2. **The swap does not fix the age axis, because there was never a meta field to
   swap to.** Neither envelope carries a content as-of; both carry only the build
   clock. The platform's content axis is **derived from the row payload** —
   `readiness.py:84-87` verbatim: *"max(last_modified) over the rows actually
   returned, derived per response"*, explicitly **not** `data_age_seconds`,
   *"a build clock wearing a freshness badge."*

   So `/rows` is the answer for a reason stronger than its meta: **it returns the
   payload the content axis is derived from.** Item 1a's measurand and item 1a's
   as-of are the same read.

**Named path for item 1a, rev-3:**

> `POST /v1/query/offer/rows` — read the row payload (`section`,
> `last_modified`), group and reduce **consumer-side**. Take the content as-of
> from the payload per `readiness.py:84-87`, never from `data_age_seconds`. Read
> `honest_contract_complete` and the truncation pair off `meta`. At **68 + 48
> rows against a 10 000-row ceiling** (`guards.py:50`) there is no aggregation
> pressure — the only reason to have preferred `/aggregate` was never
> load-bearing.

**The honest cost of the swap, recorded not buried.** `AggregateMeta.group_count`
(`models.py:230`) puts the group denominator **on the wire**; `/rows` requires
the consumer to count sections itself. G2 still passes — the denominator remains
exhibitable — but its provenance weakens from *read* to *computed*. S4 records
the identical trade for the same reason
(`ADR-mission-a-source-of-record-2026-08-12.md:540` — the readout *"**counts rows
itself** rather than reading `meta.total_count` / `meta.returned_count`"*). A
wire-borne denominator on a receipt-barren envelope is worth less than a computed
denominator beside four attestations.

**Path (b) — a durable per-section watermark.** `SectionInfo.watermark`
(`section_persistence.py:83,90`), written at `:537-540`. **FENCED** — shape
`:1502-1504` names `SectionInfo` and the manifest write path explicitly.

**Path (c) — a retained per-section observation series, already mined to STRONG
by this initiative.** `EVIDENCE-w1:633-640` (per-section persisted watermark
series, 5 chunks, **10 239 records**, 7 227 on the 8 constituent sections, no
truncation), `:613` (*"7 227 direct watermark observations"*, graded **STRONG**),
`:645-646` (168 per-section content-change events, 16 d), `:642-643` (census, 34
sections, 8 311 records). **FENCED** — the value in the `modified_since=`
emission is `section_info.watermark` (`builders/freshness.py:298-303`), i.e.
`SectionInfo`; and the census is the manifest write path (§2.2.3).

**Two things follow, and they point in opposite directions.**

1. **Revision 1's claim is refuted.** The measurand exists in three independent
   places, one of which — path (a) — is on **declared, versioned schema**, carries
   **no retention dependency**, and touches **no K-lane surface**. It is not merely
   present; it is the *best* of the three. Independently corroborated by the S4
   arch seat, which reached the same conclusion by a different route and
   **recommends** reading the offers frame per-row on exactly `section`,
   `last_modified`, `created`
   (`ADR-mission-a-source-of-record-2026-08-12.md:255-268,401-413`). This seat's
   negative was the outlier.

2. **A constraint the critique did not name, which this seat verifies and
   carries.** `last_modified` records the **most recent** move only. A snapshot
   cannot reconstruct history: an offer that moved three times in fourteen days is
   one row with one timestamp. Path (a) therefore serves the **current-state**
   limb of any readout and **cannot** serve a retrospective series. Corroborated
   at `ADR-mission-a…:288-290` (*"⚠ Weakness 4 — snapshot-only history"*) and
   `:420-422`. The critique's *"that IS candidate 1's measurand"* is true of the
   leaderboard and **false of the "week by week" limb**.

#### 3.0.2 A fourth path, unfenced and retrospective — `section-timelines` (rev-3, C-2)

Neither revision 1 nor revision 2 found this. It is a shipped, mounted,
**unfenced** surface whose observer is **Asana's own event log**.

- `api/main.py:488` — `RouterMount(router=section_timelines_router)`, mounted
  unconditionally alongside the other production routers.
- `api/routes/section_timelines.py:103-106` — *"Computes `active_section_days`
  and `billable_section_days` for each offer by **replaying its Asana section
  history** within the specified date range. Each entry also reports the offer's
  `current_section` and `current_classification`."*
- `services/section_timeline_service.py:334-338` — stories fetched through
  `client.stories.list_for_task_cached_async(..., max_cache_age_seconds=7200)`, a
  **fetch-through** read bounded at 2 h.
- `services/section_timeline_service.py:341` — filtered to
  `s.resource_subtype == "section_changed"`.
- `models/business/section_timeline.py:188-209` — `active_section_days` (*"Days
  in ACTIVE sections"*), `billable_section_days` (*"Days in ACTIVE **or
  ACTIVATING** sections"*), `current_section`, `current_classification`.
- **Fence probe**: grep of all three files for `SectionInfo`,
  `section_persistence`, `mark_section_complete`, `manifest`, `RowsMeta`,
  `AggregateMeta` → **0 matches**. Unfenced.

**Why this moved verdicts at rev-3 — and why it no longer does (rev-5).** It is
a *retrospective replay*, not an accrual: it reads what Asana already recorded,
so the observation-coverage receipt repaired-G3(b) demands is supplied by the
observed system itself. **That much still holds, and it is why G3 is not the
gate that refuses items 2 and 5a.** What does refuse them is downstream of the
replay, in how this surface's output is *reduced and filtered*:

> **⚠ Every verdict this surface carried has since been withdrawn (rev-4: item
> 2; rev-5: item 5a).** The defect is not in the replay — it is in
> `_build_imputed_interval` (`section_timeline_service.py:272-300`) and in
> `TemporalFilter` (`query/temporal.py`), which consume it. **An unfenced,
> honestly-observed source is not the same as a say-able readout**, and this
> section is the artifact's clearest demonstration of the difference.

**The boundary of what it serves — `movement`, not `edit`.**

> ***Edit* history cannot be manufactured backward. *Movement* history can.**

A `section_changed` story records a **move**. `last_modified` records an
**edit** — bumped by a custom-field change, a description edit, or a comment,
none of which emit a `section_changed` story. The story stream is a **strict
subset** of the edit stream. This is the precise reason item 1b stays withheld
while items 2 and 5a move: candidate 1 is keyed on *edits*; candidates 2 and 5's
first limb are keyed on *movement*.

**An inference this seat found and then MIS-SIGNED — corrected at rev-4 under
PT-02 C-6.** `_build_imputed_interval` (`section_timeline_service.py:272-300`,
applied at `:358`, `:586`, `:608`) imputes `[task.created_at, None]` for a
never-moved task. Revision 3 concluded from this that *"dwell is OVERSTATED,
never understated"* and passed item 2 on G4.

> **~~Overstated, never understated.~~ WITHDRAWN — the sign is
> population-dependent.** The imputed interval carries the offer's **current**
> classification (`:296`, docstring `:280`) and is open-ended (`:298` →
> `section_timeline.py:70,89`, *"Open intervals extend to period_end"*). Against
> the two classification-**set** filters (`section_timeline.py:81` `{ACTIVE}`;
> `:100-102` `{ACTIVE, ACTIVATING}`), a currently-**ACTIVE** imputed offer yields
> `billable − active = 0` (**understatement**) and a currently-**ACTIVATING** one
> yields the full window (**overstatement**). See the REVISION 4 table.

**The surviving general rule, adopted from PT-02 and superseding the
duration/occurrence split in `FINDING-option-g-imputation-indistinguishable-2026-08-12.md`
§RECONCILIATION rather than supplementing it** (the old split was too coarse —
item 2 is duration-shaped and passed straight through it):

> **Option (g) is SOUND for durations measured IN the offer's current
> classification, and SIGN-AMBIGUOUS for durations derived as DIFFERENCES ACROSS
> classifications.**

Two consequences carried in §3.1: item 2 fails G4 as a cross-classification
difference; item 2′ passes G4 in-classification but fails **G2**, because the
imputed subset is not exhibitable — `story_count` is dropped at the response
boundary (`section_timeline.py:158-209`, `extra="forbid"` `:212`). DR-7 still
binds on any surviving use, but DR-7 was never sufficient here: **a label cannot
disclose a fraction the payload does not carry.**

**Net (rev-3): `uncontracted, partly fenced, and partly served by an unfenced
retrospective surface`.**

- **Current-state edit measurand** — contracted, unfenced, K-lane-free: the row
  payload via `/rows` (§3.0.1).
- **Movement history** — unfenced and retrospective: `section-timelines`, bounded
  at 2 h, Asana-observed.
- **Edit history** — ~~**no unfenced source, and none constructible**~~
  **WITHDRAWN at rev-4 under PT-02 C-7.** The clause *"the story stream is
  movement-only"* is **false**. The fetch applies **no** subtype filter
  (`clients/stories.py:482-505`), `load_stories_incremental` writes the result
  **unnarrowed** on a cache miss (`cache/integration/stories.py:141-146`), and
  `DEFAULT_STORY_TYPES` admits **nine** subtypes of which **six are edit-class**
  (`:23-33`). The **only** narrowing is at read time, in one consumer
  (`section_timeline_service.py:341`). Restated:

  > **The substrate does not exclude edit history — one consumer discards it.**
  > Edit history is **not contracted**, and its *availability* turns on one open
  > link (below). *"Absent and not constructible"* is refuted.

  `last_modified` remains last-move-only (`base.py:76-82`) — that part stands.
  What falls is the inference from it to the whole substrate.

  **The one link that genuinely remains open, carried and NOT closed:** whether
  anything actually fetches stories for **offer** tasks in production — i.e.
  whether the story cache is populated for offers at all. The same unknown gates
  option (g)'s cache warmth, so **one probe closes both**. Carried as a UV-P at
  §6, inferred in neither direction.

  **[INFERRED | MODERATE] — one refinement offered, clearly marked as mine and
  not load-bearing on any verdict:** for this path **cold ≠ empty**.
  `list_for_task_cached` falls back to `_fetch_all_stories_uncached` when no
  cache provider is present (`clients/stories.py:392-403`), and
  `load_stories_incremental:141-146` performs a **full fetch** on a cache miss.
  So a never-invoked endpoint implies a cold cache, **not** an empty result — the
  first invocation would fetch live. **I could not verify** whether the endpoint
  has in fact been invoked, or the current cache state: no log query and no API
  call were made this dispatch.

### 3.1 The five candidates

| # | candidate (`REPORT…:185-189`) | class (G1) | verdict | one-line justification |
|---|---|---|---|---|
| **1a** | Per-section quiet-time leaderboard — *current state* (`:185`, first limb) | COMPLETENESS | **`SAY-ABLE`** *(changed at rev-2; **CLEARED by the critic at delta pass 2 on five attacks**)* | Single-clock, series referent (G1). Measurand is `max(last_modified)` grouped by `section` on declared schema, K-lane-free (§3.0 path (a)), read via **`/rows`** per §3.0.1. Per-section grouping applies **no** cohort reduction, so F-2's masking does not arise; the denominator ("of the N sections holding offer rows") is exhibitable from the same read (G2). G3 passes via clause **(a)**, not (b) — see the note below, which is the critic's strongest attack and the reason 1a holds. Bound and direction known (G4). **§0's fence: a say-ability verdict, not a build authorization.** |
| **1b** | Per-section quiet-time leaderboard — *"week by week"* (`:185`, second limb) | COMPLETENESS | **`WITHHELD-PENDING`** *(verdict unchanged; ground SHARPENED at rev-3)* | G1/G3/G4 as 1a. **G2 FAIL**, and revision 2's ground was **too general**. It is not that history is unreachable — `section-timelines` reaches **movement** history retrospectively and unfenced (§3.0.2). It is that ***edit* history cannot be manufactured backward while *movement* history can**, and candidate 1 is keyed on edits: `last_modified` is last-move-only (`base.py:76-82`) and a `section_changed` story (`section_timeline_service.py:341`) is a strict subset of the edit stream. The K-lane fence is **no longer load-bearing** here — the binding constraint is the event-class mismatch, which no fence ruling can dissolve. |
| **2** | Launch-pipeline dwell time (`:186`) | COMPLETENESS | **`WITHHELD-PENDING`** *(rev-3's `SAY-ABLE` **WITHDRAWN** at rev-4 under PT-02 C-6)* | G1 PASS. **G4 FAIL** — and this is the withdrawal. `billable_section_days − active_section_days` is a **difference across classifications**, and for an imputed offer the single `[created_at, None]` interval carries the offer's **current** classification (`section_timeline_service.py:272-300`), so the two `frozenset` filters (`section_timeline.py:81`, `:100-102`) yield **0 for a currently-ACTIVE offer (understatement)** and **the full window for a currently-ACTIVATING one (overstatement)**. The error is **not single-signed across the cohort**, so no direction can be declared. **Not annotatable**: `story_count` is dropped at the response boundary (`section_timeline.py:158-209`, `extra="forbid"` `:212`), so the contaminated fraction is unmeasurable from the payload. The pending condition is now a **named, closable, code-level** one: an imputed-vs-observed discriminator must reach `OfferTimelineEntry`. |
| **2′** | Dwell measured **IN** the offer's current classification (derived separately per PT-02, **NOT** a rescue of item 2) | COMPLETENESS | **`WITHHELD-PENDING`** — but **on G2, not G4** | PT-02's formulation is **adopted and holds**: measured *in* the current classification the imputation error **is** single-signed, because imputation always back-dates entry to `created_at` (`:297`) — the value can only be **overstated**. So **G4 PASSES** here where it fails for item 2. **G2 FAILS instead**: the served population is *"offers, an unknown subset of which have inferred rather than observed histories,"* and the readout **cannot exhibit its own population split** — same `story_count` boundary drop. That is §2.2 shape-1 population substitution, not an error-direction problem. **This is a refinement of PT-02, not a disagreement**: option (g) is sign-sound in-classification exactly as PT-02 states; sign-soundness is simply not sufficient, because a second gate bites. Same closing condition as item 2. |
| 3 | Budget expected-vs-actual roll-up (`:187`) | **VERDICT** | **`WITHHELD-AXIS`** + `OPERATOR-RESERVED` *(unchanged)* | Two-clock by construction — task `weekly_ad_spend` joined to campaign spend is exactly the budget-drift/mismatch grading (`REPORT…:56-58`); a stale board field against live spend yields a difference indistinguishable from real drift. This is the limb that **survives** F-5's narrowing: no wording rescues it. Additionally charter `:54` money limb, and *"one number"* is the shape that reads most authoritative. |
| 4 | Ghost / missing-campaign trendline (`:188`) | **VERDICT** | **`WITHHELD-AXIS`** ×2 *(unchanged)* | Two-clock (board vs campaign — `REPORT…:53-54`), **and** independently the trend axis is punctured: the pause takes no snapshots and *"those windows are not backfilled"* (`REPORT…:144-145`), so a weekly series would render an observation hole as a data point. Two sufficient grounds; the critique attacked both limbs and dented neither. |
| **5a** | Monday-morning weekend digest — *"what moved"* (`:189`, first limb) | COMPLETENESS | **`WITHHELD-PENDING`** *(rev-3's `SAY-ABLE`, re-affirmed at rev-4, **WITHDRAWN at rev-5** — delta pass 3)* | G1 PASS. **G4′ FAIL** and **G2 FAIL**, independently. **G4′**: the occurrence set is computed by `TemporalFilter` (`query/temporal.py`, shipped consumer at `query/__main__.py:875,893-895,920`), whose `moved_to` compares the interval's **own** identity with **no predecessor consulted** (`:51-58`) and whose `since`/`until` test `entered_at` (`:61-64`). An imputed interval carries `entered_at = created_at` and the current classification, and the `idx == 0` guard (`:69-70`) is reached **only if `moved_from` is specified** — so a natural weekend query returns **an offer that was merely created and never moved**, as having moved. Specifying `moved_from` inverts the sign: `_build_intervals_from_stories:231-267` synthesises no pre-first interval, so the guard **drops genuine first moves**. **Overstate without it, understate with it — not single-signed.** **G2**: exhibiting `N of M` publishes `M − N`, which **is** item 5b, withheld; not exhibiting fails G2. **The 5a/5b split does not survive its own G2 requirement.** My rev-4 "omission only" defence was about `SectionTimeline.intervals` — **an object no HTTP consumer receives** (`OfferTimelineEntry` is seven scalars, `extra="forbid"`, `section_timeline.py:158-212`, carrying **no transitions**). *(This refutation also surfaced a live product defect — filed at `DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`, operator-routed, not absorbed here.)* |
| **5b** | Monday-morning weekend digest — *"what didn't move"* (`:189`, second limb) | COMPLETENESS | **`WITHHELD-PENDING`** *(verdict unchanged; ground REPLACED and much narrowed)* | G1 PASS. **G3 FAIL**, but **not** on `REPORT…:172` — that ground is **withdrawn**. An absence-of-movement claim rests on the completeness of Asana's story stream **as replayed through this path**, and that path deliberately narrows it twice: a 2 h staleness window (`section_timeline_service.py:337`) and a cross-project noise filter that **drops** stories (`:344-346`). Absence-of-retained-record is therefore not yet equal to absence-of-event. Carried as a **UV-P** on replay completeness (§6), not asserted. Item 1's masking ground remains **withdrawn** (F-2). The Monday maximum-divergence context (3.7-day spread, `REPORT…:92`) is **not** a gate failure — DR-6a render obligation per §2.0's capability/performance split. |

#### 3.1.1 Why item 1a survives G3 under clause (a), not clause (b) (rev-3)

The critic's strongest attack at delta pass 2 was **G3-laundering by clause (a)**:
if *"gone longest without an edit"* reads as an absence claim, then routing it
through (a) makes (a) do exactly the illegitimate work clause (c) used to do, and
the F-6 repair is defeated from the other side. Recorded because the answer is
load-bearing and was not obvious.

**It holds, and the reason is provenance, not wording.** `last_modified` is the
**board's own timestamp copied into the row** — `ColumnDef(name="last_modified",
… source="modified_at")` (`schemas/base.py:76-82`). It is Asana asserting when
the task last changed. It is **not** an inference from our observation cadence.

The consequence is the discriminator:

> If the pipeline dies for five days, `max(last_modified)` is **not falsified**.
> The quiet-time it yields is **overstated, never understated**, bounded by frame
> age. G3 exists to stop *"we saw nothing, therefore nothing happened."* That
> inference **cannot occur** when the datum is the observed system's own
> assertion about itself.

This is the same structure that carries item 5a (§3.0.2): where the observer
**is** the observed system, an absence-shaped sentence is a positive claim about
a recorded value, and clause (a) is honestly available. Where the observer is
**us** — item 5b, whose claim rests on our *retained* replay being complete — it
is not. *(Item 2 was carried by this structure at rev-3 and is **withdrawn** at
rev-4 on an unrelated G4 defect; its removal does not disturb the G3 reasoning
here.)*

**C-6 SIGN RE-TEST, applied to 1a's own single-signed claim (rev-4).** C-6
falsified a *"single-signed"* assertion this seat made without enumerating both
branches. The same assertion shape appears above — *"overstated, never
understated"* — so it is re-tested rather than left standing:

- **Overstatement branch**: pipeline stalls, the frame's `max(last_modified)`
  per section freezes, real edits are not ingested, `now − max(last_modified)`
  grows. Quiet-time reads **longer** than truth. ✓
- **Understatement branch**: would require the served `last_modified` to be
  **newer** than the board's actual value. **Structurally impossible** — the
  column is copied from Asana's own `modified_at`
  (`schemas/base.py:76-82`, `source="modified_at"`), so it cannot lead the source
  it is copied from. ✗

**Both branches enumerated; the sign holds.** The contrast with item 2 is exact
and is the generalisable lesson: item 2's sign was set by a **filter-set
membership test** that *partitions* the population (`section_timeline.py:81` vs
`:100-102`), so it admits two branches; 1a's sign is set by a **copy
relationship** that admits only one.

### 3.2 What the test changed — REVISED under BLOCK

- **CONFIRMED:** the 1/2/5 ÷ 3/4 class split. Items 3 and 4 are verdict-class;
  items 1, 2 and 5 are not. Unchanged from revision 1 and unchallenged by the
  critique.
- **REFINED:** item 4 carries a **second, independent** refusal (the unbackfilled
  hole, `REPORT…:144-145`) that the frame did not name. It would remain refused
  for its historical window even after `AXIS_STATE = LIVE`.
- **CONFIRMED-IN-PART / FALSIFIED-IN-PART, and the ratio moved again at rev-3:**
  *"three of five are buildable under P-3."* On the corrected substrate the frame's
  disposition is **substantially right and revision 1 was substantially wrong**.
  Say-able today: **item 1a, item 2, item 5a** — i.e. the say-able core of all
  three of the frame's 1/2/5 set. Withheld: **1b** (edit-history, no unfenced
  source and none constructible) and **5b** (replay-completeness UV-P). Revision
  1's flat *"all three FALSIFIED"* was wrong in the expensive direction; revision
  2 corrected one third of it; revision 3 corrects the rest.
- **The correction ran entirely one way — until rev-4, when the fourth movement
  turned out to be WRONG.** This is the most useful entry in the artifact and it
  is extended, not replaced.

  | rev | movement | direction | caused by | verdict on the movement |
  |---|---|---|---|---|
  | 1 | — | — | read **one `logger.info` field list**, generalised to *"the substrate"* | the founding false negative |
  | 2 | item **1a** → `SAY-ABLE` | withheld → say-able | read the **row schema** | **correct** — critic-cleared on five attacks |
  | 3 | item **2** → `SAY-ABLE` | withheld → say-able | found **`section-timelines`**, read the *request* side | **WRONG** — withdrawn at rev-4 (C-6) |
  | 3 | item **5a** → `SAY-ABLE` | withheld → say-able | same surface | survives the C-6 re-test; still un-critiqued |
  | 4 | item **2** → `WITHHELD-PENDING`; tier (iii) withdrawn | **say-able → withheld**, and **absent → uncontracted** | PT-02 read the **imputation branch I stopped short of**, and the **fetcher** | first movement toward withheld |

  | 5 | item **5a** → `WITHHELD-PENDING`; G4 → **G4′** | say-able → withheld | delta pass 3 read **`query/temporal.py`**, one hop past where I stopped | second correct withdrawal |

- **The mechanism, stated precisely.** Every error in the table has the same
  shape: **reading stopped at the first branch that confirmed the sentence
  already being written**, and the missing read was **adjacent** to the read
  performed. Rev-1 stopped at one log line. Rev-2 stopped at the aggregate
  *request* contract. Rev-3 stopped at the imputation's ACTIVATING branch — **one
  `frozenset` away** from the ACTIVE branch (`section_timeline.py:81` vs
  `:100-102`) — and at `section_timeline_service.py:341`, never following the
  chain to the fetcher (`clients/stories.py:482-505`). Rev-4 stopped at
  `section_timeline_service.py:356-358`, never reaching `query/temporal.py`, the
  module that actually implements the occurrence set it was reasoning about.

- **THE FINDING IS ABOUT THE METHOD, NOT THE SEAT.** Three passes produced three
  findings against this seat — and **three concessions by the critic**, plus **one
  gate defect the critic convicted itself of** (G4, §2.4). PT-01 predicted the
  rev-3 error class *because this section was already in the artifact*, and then
  the same exercise produced two more errors of the same class in the critic's
  own work. The critic's closing line, carried verbatim because it is the
  deepest finding of the arc:

  > *"The pattern S1 diagnosed in itself is not a property of that seat; it is
  > the failure mode of the whole exercise, and the only thing that has caught it
  > — in every instance including mine — is a second reader going one hop
  > further."*

  **The operative consequence is a process claim, not a character claim:** no
  gate, no self-flag, and no calibration note has ever caught this class. **A
  second reader going one hop further has caught it every time — five for five.**
  G4′ (§2.4) is the strongest written expression of that discipline available,
  and §2.4 records why it is still not sufficient: enumeration can be compelled;
  *completeness* of enumeration cannot.

- **One imputation, three consumers, three different wrong answers** — and one
  remedy. Sign-flip by sub-population (item 2), payload indistinguishable from
  clean (item 2′), false positives on a shipped filter (item 5a, and the live
  defect at `DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`). **The
  remedy is a single thing: an imputed-vs-observed discriminator must reach the
  consumable surface.** That one change closes both withheld dwell items and the
  filed defect.
- **SELF-CORRECTION, recorded per charter `:57`:** revision 1 wrote *"for three of
  the five candidates the source does not carry the measurand at all."* **This
  seat withdraws that sentence.** It was supported solely by the field list of
  `query_rows_complete` (`api/routes/query.py:548-560`) — a request-shaped
  emission with no edit-time field, which remains **true of that log line** and
  says nothing about the row schema, the aggregate compiler, the section manifest,
  or the retained event streams. SVR-S1-1 was accurate; the inference above it
  over-scoped by an order of magnitude, in an artifact whose own G2 exists to
  catch exactly that class of error.
- **CONSEQUENCE — routed, not absorbed (charter `:57`):** the honest sharpening of
  NF-2 (shape `:160-206`) is **not** *"the source does not carry the measurand."*
  It is:

  > **For the current-state measurand, a contracted and K-lane-free source
  > exists** — declared `ColumnDef`s on a versioned schema, reachable through a
  > shipped endpoint, with no retention dependency. **For the retrospective
  > measurand, no unfenced source exists, and none can be manufactured backward**;
  > the reaches that do exist are `SectionInfo`-derived (fenced) or live in a
  > 30-day log window whose retention is declared in a third repo at a pinned
  > `ref=` (§6, UV-P-5 discharged).

  **Routed to S4** as a named option-enumeration input; **not decided here.** S4
  has since reached the same two-halves conclusion independently
  (`ADR-mission-a…:396-397` for the current half; `:415-430` — *"OPTION (d) FIRES.
  NEGATIVE RESULT"* — for the retrospective half).

---

## 4. THE DISCLOSURE RULE

Binding on **every** published number, in **every** readout, at **every** rung —
including numbers whose verdict is `SAY-ABLE`.

### 4.1 Verbatim inheritance

**P-1** (`RULING-operator-option4-interview-2026-08-12.md:19`), verbatim:

> "Both, disclosed separately" — gate on verification recency; content age rides
> the wire as first-class disclosure, never conflated.

**P-12** (`RULING-operator-option4-interview-2026-08-12.md:30`), verbatim:

> `content_age_seconds` keeps its exact current meaning forever (result-scoped
> content age); the new axis ships as `verification_age_seconds` + `verified_at`
> + `backfill_used`; NO field ever polymorphic; NO consumer coalescing
> ("whichever is present" is forbidden). Non-aliasing clause extends to the
> verification family.

**No third number is invented below. No field is polymorphic. No coalescing is
permitted.** Shape `:1506-1507` binds this identically.

### 4.2 The rules

**DR-1 — OBSERVATION-RELATIVE TENSE (the never-fresher rule).**
Every published number is stated relative to its observation, never in the
world-present tense. *"At the {t} observation, the served active cohort held 68
rows"* — never *"the board has 68 active offers."* Per R-1 (§1.3), present tense
is the single most common way a number reads fresher than it is: it silently
promotes a series-referent claim to a world-now claim, which is the
`WITHHELD-AXIS` class.

**DR-2 — AS-OF IS THE FLOOR, BY `min`.**
A readout's as-of is `min` over the observation times of **all** its
constituents. Not the newest constituent. Not the render time. This is not a new
invention: the platform already reduces this way — `oldest_verified_at` is
*"the floor used to derive `max_age_seconds`"*
(`src/autom8_asana/metrics/freshness.py:79-80`) and is computed as
`now - min(last_verified_at)` over the in-scope set (`:746`). It is the same
`min()`-exposes direction the operator ratified at P-5 (`RULING…:23`).
A roll-up may never carry an as-of newer than its oldest input.
Render time, if shown at all, is **labelled as render time** and is never the
as-of.

**DR-3 — BOTH AXES, SEPARATELY, ON THE FACE OF THE RENDER.**
P-1 requires both numbers disclosed separately in the envelope. This rule
extends the obligation to the **rendered line**, because a readout is consumed as
a line, not as an envelope. The positive exemplar already exists in this repo —
`format_verification_warning` (`src/autom8_asana/metrics/freshness.py:675-679`)
renders *"verification age {v} exceeds {threshold} ({N} in-scope sections;
mutation age {m})"*: **both axes named, with the denominator, on one line.**
Every readout render inherits that shape.
**A rendered number that does not name its own axis is forbidden**, even where
the envelope behind it is compliant.

**DR-4 — ABSENT MEANS ABSENT.**
While `AXIS_STATE = REFUSING`, the verification-recency figure is **absent**. It
must be rendered as explicitly absent — *"verification recency: not yet
available (gate not live)"* — and never as null-meaning-fresh, never silently
omitted, and **never substituted from the content/mutation axis**. That
substitution is precisely the *"whichever is present"* coalescing P-12 forbids.

The platform holds **half** the correct pattern, and the other half is a live
counter-example. Revision 1 cited only the half that flatters the rule; the
critique supplied the rest (F-10), and this seat verified it verbatim.

- **The half that is right.** The verification block is *"[a]lways present so
  operators can detect the unavailable state explicitly rather than via field
  absence"* (`metrics/freshness.py:602-605`). The `available` flag is explicit, and
  `oldest_verified_at` is correctly `None` in the unavailable branch (`:619`).
- **The half that is wrong, in the same `else` block.** `metrics/freshness.py:617-627`
  emits, alongside `"available": False`:

  ```
  "max_age_seconds": 0,     # :620
  "stale": False,           # :624
  "in_scope_count": 0,      # :625
  ```

  A consumer that reads `verification_age.max_age_seconds` **without first
  branching on `available`** gets `0` — *"verified this instant"* — and `stale:
  False` beside it. **That is null-meaning-fresh wearing a boolean seatbelt, in
  the exact code DR-4 cites as the pattern to inherit.** The numeric fields carry
  the most reassuring possible value in the least reassuring possible state.

**DR-4 is therefore stated more strongly than revision 1 stated it:** an
`available: False` block must not carry a *value-shaped* number beside the flag.
Absence is rendered as absence in **every** field of the block, not only in the
flag guarding them. `oldest_verified_at: None` is the correct shape; `0` and
`False` are not.

Routed to the P-8 successor ADR alongside O-2 and O-5 (§5). **This artifact does
not rule on that ADR, and does not touch the shipped surface.**

**DR-5 — DENOMINATOR ON THE FACE.**
Every published count or rate states its population as `k of n`, in the same
form the platform already receipts (`68 of 68`, `REPORT…:138`; `{N} in-scope
sections`, `freshness.py:677`). **This is not a third number on the age axis** —
it is a completeness statement, it is already the shipped render shape, and it
is never arithmetically combined with either age. (Ratification item — §5, O-3.)

**DR-6 — BOUND AND DIRECTION.**
Every board-behaviour number carries its lag bound and the direction of its
error: *"series trails the board by up to 4.0 h; readings err stale, never
fresh"* (`EVIDENCE-w1…:188`; `ATTEST-rel6…:752`).

**DR-6a — PERIODIC-NORMALITY CONTEXT (rev-2).** A readout delivered at a
recurring instant of **known maximum divergence** states that normality on its
face. The measured case in hand: the Monday-morning cohort spread reaches
**3.7 days** (`REPORT…:92`), so a weekend digest without that context reads as
breakage rather than rhythm. Moved here from G4 under §2.0's capability /
performance split — it was never a say-ability failure; it is a render duty.

**DR-7 — INFERENCE IS LABELLED AS INFERENCE.**
Any derived, modelled, or trended quantity is published as the inference it is,
with its window and its assumptions — the precedent the frame already set for
residue 7 (`.sos/wip/frames/asana-native-insight-delivery.md:438`).

**DR-8 — ONE NAME PER AXIS, DECLARED, NEVER A FALLBACK.**
A readout binds to exactly one field name per axis and states which. It must not
fall back to a second name for the same quantity, and must not treat two names
for one block as interchangeable. (See §5, O-2 — the substrate currently offers
exactly such a pair.)

### 4.3 Composite worked render

```
Launch-pipeline observation — week of 2026-08-04
  as-of            2026-08-11 19:29 UTC   (floor: oldest constituent observation)
  rendered         2026-08-12 09:14 UTC   (render time — NOT the as-of)
  population       48 of 48 activating rows, untruncated   (1 000-row cap)
  observation      k of n expected ticks observed in window
  content age      {value}                (result-scoped; P-12 meaning, unchanged)
  verification     not yet available — gate not live   (explicitly absent; never
                                                        substituted from content age)
  bound            series trails the board by up to 4.0 h; errs stale, never fresh
```

Two ages, separately, both named. No third age. No polymorphic field. No
fallback. The as-of is a floor. Nothing is in the present tense.

---

## 5. Routed to the OPERATOR — surfaced, not decided here

Per charter `:57` (*scope changes are surfaced as findings, not absorbed*) and
shape `:1515-1517`. **None of these is ruled by this artifact.**

- **O-1 — the frame's spine sentence is imprecise (R-1, §1.3).** "Completeness is
  receipted" is true of *serve*-completeness (non-truncation against a 1 000-row
  cap) and not of *board*-completeness. The initiative's conclusion survives on
  the corrected referent ground. **Does the operator want the frame's §1 spine
  text amended in place, or the correction carried only here?**
- **O-2 — a shipped alias pair on the age axis.** `build_envelope`
  (`src/autom8_asana/metrics/freshness.py:632-638`) emits **one** block object
  under **two** keys — `"freshness"` and `"mutation_age"` — self-described in the
  docstring as *"alias for the existing `freshness` block"* (`:570-572`), for v1
  back-compat. Same meaning, two names: not polymorphism and not coalescing, but
  the exact substrate on which a consumer writes *"whichever is present."*
  **P-8 (`RULING…:26`) supersedes ADR-006 into a new ADR covering both surfaces —
  this belongs in that draft, and it is why DR-8 exists.**
- **O-3 — is a `k of n` denominator a "third number"?** Shape `:1507` says *never
  a third number*. DR-5 holds that a denominator is a completeness statement, not
  an age, and cites the already-shipped `{N} in-scope sections`
  (`freshness.py:678`) as precedent. **Confirm or refuse at the new ADR.**
- **O-4 — a naming delta between P-12 and the shipped code.** P-12 names the new
  axis `verification_age_seconds` + `verified_at` + `backfill_used`; the shipped
  envelope carries `verification_age.max_age_seconds` +
  `verification_age.oldest_verified_at` + `verification_age.backfill_used`
  (`freshness.py:606-614`). `backfill_used` matches exactly; the other two differ
  in name (`oldest_verified_at` is *more* informative — it declares the `min`
  reduction). **Block-scoping or an aliasing breach? The new ADR's call.**
- **O-5 — the metrics-CLI fallback line does not name its axis.** When
  verification is unavailable the CLI prints `format_warning`
  (`src/autom8_asana/metrics/__main__.py:1000-1002`), whose text is *"WARNING:
  data older than {threshold} (max_age={observed})"* (`freshness.py:650-655`) —
  a single unlabelled age, on precisely the path where the other axis is
  missing. The envelope remains compliant; **the rendered line is where DR-3
  came from.** Adjacent surface, governed by the superseded ADR-006; **routed,
  not touched.**
- **O-6 — REWRITTEN UNDER BLOCK. Revision 1's version of this item was wrong, and
  wrong in the expensive direction.** It told the operator: *"three of five
  candidates need a measurand the substrate does not carry … Mission A's cost is
  higher than the frame's framing implies."* On the corrected premise (§3.0) that
  sentence would have **talked the operator out of something they can in fact
  do**, at an operator-reserved fork, on a premise this seat had not tested. It is
  withdrawn. The honest input to **S4** and, through it, to **GATE-FORK**:

  > **Mission A has two halves with opposite cost profiles, and revision 1
  > priced both at the expensive one.**
  >
  > - **The current-state half is CHEAPER than the frame's framing implies.** The
  >   measurand is a declared, non-nullable `ColumnDef` on a versioned schema
  >   (`base.py:76-82`), present on every offer row (`offer.py:209-215`), and a
  >   per-section reduction over it is schema-legal and dtype-compatible against a
  >   shipped endpoint **today** (`aggregator.py:36,49`; `guards.py:96-102`;
  >   `query.py:565-572`). No new emission. No new retention. No K-lane contact.
  >   Item **1a is `SAY-ABLE`** (§3.1).
  > - **The retrospective half is EXPENSIVE, for a reason revision 1 never
  >   named.** `last_modified` is last-move-only (`base.py:76-82`), so history is
  >   **not reconstructible from a snapshot** and cannot be manufactured backward.
  >   The reaches that do carry history are `SectionInfo`-derived and fall inside
  >   this initiative's own zero-K-lane fence (shape `:1502-1504`), or live in a
  >   30-day log window whose retention value is real but whose **declaration
  >   site** is a module default in a third repo at a pinned `ref=` (§6).
  > - **The distinction the fork turns on is `uncontracted` vs `absent`**, not
  >   `present` vs `absent`. Revision 1 collapsed it. That collapse is the entire
  >   cost delta.

  **AMENDED AGAIN AT REV-3 — the cheap half is larger than revision 2 said.**
  Revision 2 priced one of five candidates as say-able. On the corrected substrate
  it is **three**: item 1a, item 2 and item 5a. The addition is
  **`section-timelines`** (§3.0.2) — a shipped, unconditionally-mounted, **unfenced**
  surface whose observer is Asana's own event log, which revision 2 did not find
  and which requires **no build at all** for the movement class. Restated for the
  operator:

  > **Three distinct cost tiers, not two.**
  > **(i) Already reachable, zero build** — movement-class readouts (dwell, weekend
  > moved-set) via `section-timelines`, `api/main.py:488`, bounded 2 h.
  > **(ii) Reachable on declared schema, no new emission** — current-state
  > edit-class readouts via `/rows` (§3.0.1).
  > **(iii) ~~Genuinely absent and not constructible~~ — WITHDRAWN AT REV-4
  > (PT-02 C-7). RESTATED: uncontracted and one-consumer-discarded, with one
  > open link.** The substrate does **not** exclude edit history: the fetch
  > applies no subtype filter (`clients/stories.py:482-505`), the cache is
  > written unnarrowed (`cache/integration/stories.py:141-146`), and six of the
  > nine admitted subtypes are edit-class (`:23-33`). The only narrowing is at
  > **read** time in one consumer (`section_timeline_service.py:341`). **The one
  > genuinely open link — carried, not closed — is whether the story cache is
  > populated for offer tasks at all** (§6 UV-P; one probe also closes option
  > (g)'s warmth).

  **Net effect on the fork input at rev-4 — and it cuts BOTH ways.** The
  say-able set **shrinks** (item 2 withdrawn; only **1a and 5a** stand, both
  un-critiqued). The **expensive tier also shrinks** — this artifact no longer
  asserts that anything is *absent*. What it now says is narrower and weaker in
  both directions: **two readouts appear say-able, one measurand class is
  uncontracted-but-not-excluded, and one probe would move more of this than any
  further reading of code.** **The operator should weight this artifact's cost
  signal accordingly — it has been wrong at every prior revision.**

  **Still not a recommendation on the fork.** S4 enumerated the options and
  recommended independently (`ADR-mission-a-source-of-record-2026-08-12.md` §7.1 /
  §7.2). **The operator should know that S4's slate and this artifact's rev-3
  substrate may now differ**: S4's enumeration was authored before
  `section-timelines` surfaced in this arc, and this seat has not checked whether
  its option slate includes that surface. Flagged as a possible enumeration gap
  for S4 to close — **not asserted, and not this seat's to rule.**
  `[UV-P: whether ADR-mission-a-source-of-record-2026-08-12's option slate enumerates the section-timelines surface | METHOD: deferred-to-S4 re-read or operator | REASON: rev-3 surfaced it after S4's authorship; this seat verified the surface but did not audit S4's slate against it, and option-enumeration completeness is S4's exit criterion, not S1's]`

- **O-7 (new, rev-2) — is the K-lane fence load-bearing on item 1b and §2.7 row
  3?** Both are `WITHHELD-PENDING` **solely** because their only history/roster
  source is `SectionInfo`-derived and shape `:1502-1504` binds *"if a readout
  wants a number that only exists on the K-lane, it WAITS."* The data exists, is
  retained, and has already been mined to STRONG by this initiative
  (`EVIDENCE-w1:613,633-640,642-643`). **This seat applies the fence as written
  and does not route around it.** Whether the fence is intended to bar a
  *read-only, downstream* consumption of a K-lane-derived value — as distinct from
  a *touch* on the K-lane surface — is not this seat's to decide. **Operator or
  potnia call.** If read-only consumption is permitted, item 1b and §2.7 row 3
  both move, and S4's option slate gains a candidate it currently rejects.

- **O-8 (new, rev-2) — the `available: False` block carries value-shaped numbers**
  (DR-4, F-10). `metrics/freshness.py:617-627` emits `"max_age_seconds": 0` and
  `"stale": False` beside `"available": False`. A consumer that does not branch on
  the flag reads *"verified this instant."* Routed **alongside O-2 and O-5 into
  the P-8 successor ADR** (`RULING…:26`), which already covers both surfaces.
  Surfaced, not touched.

---

## 6. SVR ledger (own-hands, this dispatch)

| # | claim | method | anchor |
|---|---|---|---|
| SVR-S1-1 | `query_rows_complete` emits request-shaped count fields and **no edit-time field** | file-read | `src/autom8_asana/api/routes/query.py:548-560` — marker: `"total_count": result.meta.total_count,` |
| SVR-S1-2 | the verification family is already implemented, with `oldest_verified_at` as the `min`-reduced floor | file-read | `src/autom8_asana/metrics/freshness.py:746` — marker: `computes ``now - min(last_verified_at)`` over the in-scope set` |
| SVR-S1-3 | the envelope emits one block under two names (`freshness`, `mutation_age`) | file-read | `src/autom8_asana/metrics/freshness.py:632-638` — marker: `# v1 'freshness' block retained byte-for-byte for back-compat.` |
| SVR-S1-4 | verification block is always present so absence is explicit, never field-absence | file-read | `src/autom8_asana/metrics/freshness.py:602-605` — marker: `Always present so operators can detect the unavailable state explicitly` |
| SVR-S1-5 | the axis-naming exemplar renders both axes plus denominator on one line | file-read | `src/autom8_asana/metrics/freshness.py:675-679` — marker: `f"WARNING: verification age {verification_human} exceeds "` |
| SVR-S1-6 | the CLI fallback line does not name its axis | file-read | `src/autom8_asana/metrics/__main__.py:1000-1002` + `freshness.py:650-655` — marker: `WARNING: data older than {threshold_human} (max_age={observed_human})` |
| SVR-S1-7 | board behaviour is observed as a per-cohort `max`-reduced watermark | file-read | `EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:198-200` — marker: `the cohort's binding watermark` / `max over sections in cohort` |
| SVR-S1-8 | frame lag is bounded at 4.0 h and errs stale | file-read | `EVIDENCE-w1…:188` + `ATTEST-rel6…:752` — marker: `every observed reading errs stale.` |
| SVR-S1-9 | 21 of 34 sections are 0-row | file-read | `EVIDENCE-w1…:128` — marker: `(21 sections are 0-row)` |

**Revision-2 additions — every receipt below re-verified own-hands at
`origin/main` (`4129ae7e`), none taken on the critique's word:**

| # | claim | method | anchor |
|---|---|---|---|
| SVR-S1-10 | the per-offer edit-time measurand is a **declared, non-nullable** schema column | file-read | `src/autom8_asana/dataframes/schemas/base.py:76-82` — marker: `name="last_modified",` / `dtype="Datetime",` / `nullable=False,` / `source="modified_at",` |
| SVR-S1-11 | that column is on **every** offer row | file-read | `src/autom8_asana/dataframes/schemas/offer.py:209-215` — marker: `columns=[` / `*BASE_COLUMNS,` |
| SVR-S1-12 | `MAX` over a `Datetime` column is an **explicitly enumerated** compatibility entry | file-read | `src/autom8_asana/query/aggregator.py:36,49` — marker: `"Datetime": _ORDERABLE_AGGS \| _UNIVERSAL_AGGS,` |
| SVR-S1-13 | both `group_by` and `aggregations` validate against the same schema object, so the request is legal end-to-end | file-read | `src/autom8_asana/query/guards.py:96-102` (`col_def = schema.get_column(col_name)`) + `src/autom8_asana/query/aggregator.py:104-119` (`col_def = schema.get_column(spec.column)` → `AGG_COMPATIBILITY.get(col_def.dtype, …)`) |
| SVR-S1-14 | the aggregate route is shipped | file-read | `src/autom8_asana/api/routes/query.py:565-572` — marker: `"/{entity_type}/aggregate",` |
| SVR-S1-15 | `total_count` is post-filter / pre-slice — the engine says so itself | file-read | `src/autom8_asana/query/engine.py:136-141` — marker: `The post-filter total_count (step 8) conflates the two` |
| SVR-S1-16 | the platform row ceiling is `10_000`; the 1 000 is the caller's | file-read | `src/autom8_asana/query/guards.py:50,67-72` — marker: `max_result_rows: int = 10_000` |
| SVR-S1-17 | a **per-offer transition** capture path exists in the substrate | file-read | `src/autom8_asana/cache/integration/stories.py:23-33` — marker: `"section_changed",` |
| SVR-S1-18 | the per-section census is emitted from the **K-lane manifest write path** | file-read | `src/autom8_asana/dataframes/section_persistence.py:537-560` — marker: `manifest.mark_section_complete(` … `"section_status_updated",` |
| SVR-S1-19 | the per-section watermark log series carries a `SectionInfo` value | file-read | `src/autom8_asana/dataframes/builders/freshness.py:298-306` — marker: `if section_info.watermark is not None:` / `modified_since=watermark_iso,` |
| SVR-S1-20 | the content-change event stream is structurally blind to ~21/34 offer sections | file-read | `src/autom8_asana/dataframes/builders/freshness.py:294-297` — marker: `sections (~21/34 offer, ~4/17 unit per QA 2026-05-27)` / `bypass this branch entirely` |
| SVR-S1-21 | the `available: False` verification block carries value-shaped numbers | file-read | `src/autom8_asana/metrics/freshness.py:617-627` — marker: `"max_age_seconds": 0,` … `"stale": False,` |
| SVR-S1-22 | `terraform/services/asana/` exists at **this** repo's `origin/main` (6 tracked files) — falsifying UV-P-5's stated reason | git-ls-files | `git ls-tree -r --name-only origin/main terraform/services/asana/` → 6 paths incl. `observability_alarms.tf`, `substrate_v2_provability_alarms.tf` |
| SVR-S1-23 | it exists at the **autom8y monorepo's** `origin/main` too, pinned to a third repo | file-read | `autom8y@origin/main:terraform/services/asana/main.tf:101` — marker: `?ref=0fb9527b` |
| SVR-S1-24 | no `retention_in_days` is declared anywhere under this repo's `terraform/` | bash-probe | `git grep -c retention_in_days origin/main -- terraform/` → exit **1**, zero matches |
| SVR-S1-25 | the `section` entity type is registered with its own schema and default projection | file-read | `src/autom8_asana/core/entity_registry.py:1004-1020` — marker: `schema_module_path="autom8_asana.dataframes.schemas.section.SECTION_SCHEMA",` |

**Revision-3 additions — C-1 and C-2. Every anchor re-verified own-hands at
`origin/main` (`4129ae7e`, this repo; `a5c98f9c`, the autom8y monorepo via
`git show origin/main:` only — the monorepo working tree is on a divergent branch
with a sibling session actively committing):**

| # | claim | method | anchor |
|---|---|---|---|
| SVR-S1-26 | `AggregateMeta` carries **no** completeness attestation and **no** content as-of; its only age field is the build clock | file-read | `src/autom8_asana/query/models.py:225-262` — marker: `data_age_seconds: float \| None = Field(` / `description="Age of the cached data in seconds since last refresh.",` |
| SVR-S1-27 | `AggregateMeta` cannot be extended to carry them | file-read | `src/autom8_asana/query/models.py:228` — marker: `model_config = ConfigDict(extra="forbid")` |
| SVR-S1-28 | `honest_contract_complete` is spread into `RowsMeta` **only** | file-read | `src/autom8_asana/query/engine.py:292` (`honest_contract_complete=honest_contract_complete,`) vs `engine.py:427-435` (`AggregateMeta(` … `**freshness_meta,`) — the field is absent from the second |
| SVR-S1-29 | `RowsMeta` additionally carries `honest_empty`, the FM-5 column contract, and the truncation pair | file-read | `src/autom8_asana/query/engine.py:285-296` — marker: `honest_empty=honest_empty,` / `contract_complete=contract_complete,` |
| SVR-S1-30 | **the platform's content axis is derived from the ROW PAYLOAD, explicitly not from `data_age_seconds`** | file-read | `autom8y@origin/main:services/account-status-recon/src/account_status_recon/readiness.py:84-87` — marker: `max(last_modified) over the rows actually returned, derived per response by the SDK` |
| SVR-S1-31 | the `section-timelines` router is mounted unconditionally | file-read | `src/autom8_asana/api/main.py:488` — marker: `RouterMount(router=section_timelines_router),` |
| SVR-S1-32 | it replays Asana section history over a caller-chosen window | file-read | `src/autom8_asana/api/routes/section_timelines.py:103-106` — marker: `each offer by replaying its Asana section history within the specified` |
| SVR-S1-33 | the observed event class is `section_changed`, read through a 2 h fetch-through cache | file-read | `src/autom8_asana/services/section_timeline_service.py:334-341` — marker: `max_cache_age_seconds=7200,` / `s.resource_subtype == "section_changed"` |
| SVR-S1-34 | dwell in ACTIVATING is `billable_section_days − active_section_days`, and the right-censoring split is on the wire | file-read | `src/autom8_asana/models/business/section_timeline.py:188-209` — marker: `description="Days in ACTIVE or ACTIVATING sections",` / `current_classification: str \| None = Field(` |
| SVR-S1-35 | the day counts are **window-clipped**, so left-censoring is not exhibited | file-read | `src/autom8_asana/models/business/section_timeline.py:167-169` — marker: `active_section_days: Calendar days in ACTIVE sections during period.` |
| SVR-S1-36 | a never-moved task's interval is **imputed from creation**, so dwell errs long | file-read | `src/autom8_asana/services/section_timeline_service.py:272-279` — marker: `Per AC-3.1: If zero stories remain, impute [task.created_at, None].` |
| SVR-S1-37 | the replay path narrows the retained story set a second time, by dropping cross-project noise | file-read | `src/autom8_asana/services/section_timeline_service.py:343-346` — marker: `if not _is_cross_project_noise(s, OFFER_CLASSIFIER)` |
| SVR-S1-38 | the `section-timelines` surface touches **no** K-lane-fenced surface | bash-probe | `git show origin/main:{section_timelines.py,section_timeline_service.py,section_timeline.py} \| grep -n "SectionInfo\|section_persistence\|mark_section_complete\|manifest\|RowsMeta\|AggregateMeta"` → **0 matches** across all three files |

**Revision-4 additions — PT-02 C-6 and C-7. Every anchor re-verified own-hands at
`origin/main` (`4129ae7e`); nothing accepted on PT-02's word:**

| # | claim | method | anchor |
|---|---|---|---|
| SVR-S1-39 | the imputed interval carries the offer's **current** classification and is open-ended | file-read | `src/autom8_asana/services/section_timeline_service.py:293-300` — marker: `classification=account_activity,` / `exited_at=None,` |
| SVR-S1-40 | an open interval extends to `period_end`, so an imputed offer spans the whole window | file-read | `src/autom8_asana/models/business/section_timeline.py:70` and `:89` — marker: `Per AC-4.5: Open intervals extend to period_end.` |
| SVR-S1-41 | the two day-counts are classification-**set** filters differing by `ACTIVATING` — the mechanism that makes the sign population-dependent | file-read | `src/autom8_asana/models/business/section_timeline.py:81` (`frozenset({AccountActivity.ACTIVE})`) vs `:100-102` (`frozenset({AccountActivity.ACTIVE, AccountActivity.ACTIVATING})`) |
| SVR-S1-42 | `story_count` exists internally but is **dropped at the response boundary**, so the imputed fraction is unmeasurable by a consumer | file-read | `src/autom8_asana/models/business/section_timeline.py:62` (`story_count: int` on `SectionTimeline`) vs `:158-209` (`OfferTimelineEntry`, seven fields, no `story_count`) + `:212` (`"extra": "forbid"`) |
| SVR-S1-43 | imputation fires **only** when zero stories survive filtering — why item 5a's occurrence set cannot be contaminated | file-read | `src/autom8_asana/services/section_timeline_service.py:356-358` — marker: `intervals = _build_imputed_interval(` |
| SVR-S1-44 | **the story fetch applies NO `resource_subtype` filter** — the decisive C-7 receipt | file-read | `src/autom8_asana/clients/stories.py:482-502` — marker: `"""Fetch all stories for a task, optionally since a timestamp."""` / `f"/tasks/{task_gid}/stories",` |
| SVR-S1-45 | the cache is written **unnarrowed** on a miss — no narrowing at cache-write | file-read | `src/autom8_asana/cache/integration/stories.py:141-146` — marker: `# No cache - full fetch` / `stories = await fetcher(task_gid, None)` |
| SVR-S1-46 | `filter_relevant_stories` is a **read-time** in-memory filter, not a fetch constraint | file-read | `src/autom8_asana/cache/integration/stories.py:294` — marker: `return [s for s in stories if s.get("resource_subtype") in include_types]` |
| SVR-S1-47 | six of the nine admitted subtypes are edit-class, not movement-class | file-read | `src/autom8_asana/cache/integration/stories.py:23-33` — marker: `"assignee_changed",` / `"enum_custom_field_changed",` / `"number_custom_field_changed",` |

**Revision-5 additions — delta pass 3. Every anchor re-verified own-hands at
`origin/main` (`4129ae7e`); the `temporal.py` module was read in full, having
never been read in revisions 1–4:**

| # | claim | method | anchor |
|---|---|---|---|
| SVR-S1-48 | `matches()` is satisfied by **any** interval meeting **all specified** criteria | file-read | `src/autom8_asana/query/temporal.py:44-46` — marker: `return any(self._interval_matches(interval, timeline) for interval in timeline.intervals)` |
| SVR-S1-49 | `moved_to` compares the interval's **own** section/classification — **no predecessor consulted** | file-read | `src/autom8_asana/query/temporal.py:51-58` — marker: `section_match = interval.section_name.lower() == self.moved_to.lower()` |
| SVR-S1-50 | `since`/`until` test `entered_at`, which for an imputed interval is `task_created_at` | file-read | `src/autom8_asana/query/temporal.py:61-64` — marker: `if self.since is not None and interval.entered_at.date() < self.since:` |
| SVR-S1-51 | the `idx == 0` guard is reached **only when `moved_from` is specified** — the false-positive mechanism | file-read | `src/autom8_asana/query/temporal.py:67-70` — marker: `if self.moved_from is not None:` / `return False  # No previous interval` |
| SVR-S1-52 | no pre-first interval is synthesised, so `intervals[0]` is a genuine first move — the sign-inversion mechanism | file-read | `src/autom8_asana/services/section_timeline_service.py:249-267` — marker: `# Open new interval (AC-2.6: last one stays open)` |
| SVR-S1-53 | `TemporalFilter` is applied by a **shipped consumer**, not a hypothetical one | file-read | `src/autom8_asana/query/__main__.py:875` (`from autom8_asana.query.temporal import TemporalFilter, parse_date_or_relative`) + `:893-895` + `:920` (`matched = [tl for tl in timelines if temporal_filter.matches(tl)]`) |
| SVR-S1-54 | `OfferTimelineEntry` carries **no transitions**, so any intervals-level argument does not transfer to an HTTP consumer | file-read | `src/autom8_asana/models/business/section_timeline.py:158-212` — seven scalar fields; marker: `"extra": "forbid",` |

**UV-P carry (Gate-C DEFER-tag pattern):**

- `[UV-P: the ASR verdict surface is starved during the pause because the readiness-FAIL abort returns 198 lines before _emit_verdict_surface | METHOD: deferred-to-monorepo-read | REASON: orchestrator.py:242 / :440 live in the autom8y monorepo, out of this repo's tree; inherited from frame :62-67 and not re-probed own-hands this dispatch]`
- ~~`[UV-P: whether any per-section or per-offer observation series can be reconstructed from an existing emission | …]`~~ — **DISCHARGED at §3.0.** Three exist (SVR-S1-10..14, 17, 18, 19); one is unfenced. Revision 1 carried this as an open question **while simultaneously asserting the answer was no** in §3.1 — the two were incoherent, and the assertion was the wrong one.
- `[UV-P: whether mean dwell is derivable from cohort counts via a queueing identity | METHOD: deferred-to-S4-option-enumeration | REASON: the identity needs gross transition flow, and counts yield only net change; feasibility unassessed and deliberately not asserted]`
- ~~`[UV-P-5 … | REASON: terraform/services/asana/ does not exist at autom8y origin/main]`~~ — **DISCHARGED, and its stated reason FALSIFIED twice over.** See below.

**UV-P-5 — DISCHARGED (rev-2, F-8).**

- **Value: 30 days.** Live-probed and recorded in this artifact's own primary
  evidence file, cited nine times by revision 1: `EVIDENCE-w1:624` —
  *"**Log groups** (both `retentionInDays: 30`, confirmed via
  `describe-log-groups`): `/ecs/autom8y-asana-service` …
  `/aws/lambda/autom8y-account-status-recon`."* The answer was inside the artifact
  revision 1 was reading.
- **The stated REASON was false in both repos.** `terraform/services/asana/`
  exists at **this** repo's `origin/main` — 6 tracked files (SVR-S1-22) — **and**
  at the **autom8y monorepo's** `origin/main`, where `main.tf:101` pins the
  stateless-service stack at `?ref=0fb9527b` (SVR-S1-23).
- **RESTATED, not struck — the honest residual is the declaration site, not the
  value.** Independently established by S4
  (`ADR-mission-a-source-of-record-2026-08-12.md:145-191,636-644`): the 30 is a
  **module default in a third repo** (`autom8y/a8`,
  `stacks/service-stateless/variables.tf:422-426` →
  `primitives/ecs-fargate-service/main.tf:111-113`), consumed at the pinned `ref=`
  **without declaration** at either consuming site, and `retention_in_days` appears
  **nowhere** under this repo's `terraform/` (SVR-S1-24, exit 1). It is therefore
  changeable by a `ref=` bump that produces **zero diff in either repo's
  retention posture**. Carried forward:

  `[UV-P-5' (restated): the effective 30-day retention of /ecs/autom8y-asana-service is an OBSERVED RUNTIME FACT, not a contracted one — its declaration site is an externally-defaulted module variable in a third repo at a pinned ref, mutable with no diff in either consuming repo | METHOD: deferred-to-SRE-lane (S4 §11 routes an explicit log_retention_days declaration + a retention-delta check on the a8 ref-bump procedure) | REASON: this is exactly the contracted-vs-reachable distinction §3.0 turns on, and it is the reason a 30-day log window is not a source-of-record even where its current value is known]`

- **Partial credit to the concern revision 1 was reaching for.** The retention
  answer **sharpens** rather than dissolves it: a 30-day rolling window is not a
  source-of-record, so *"week by week"* trending (item 1b) and any multi-month
  series die at day 31 regardless. That is the honest NF-2 sharpening — and it is
  a much smaller claim than *"the source does not carry the measurand at all."*

**UV-P carry — new this revision:**

- ~~`[UV-P: whether "section_changed" stories are actually fetched and retained for offer-project tasks in production … ]`~~ — **DISCHARGED at rev-3 (§3.0.2).** They are fetched per offer through `client.stories.list_for_task_cached_async(..., max_cache_age_seconds=7200)` and filtered to `resource_subtype == "section_changed"` (`section_timeline_service.py:334-341`), on a **shipped, unconditionally-mounted** route (`api/main.py:488`). This was item 2's whole remaining question and it is answered.

**Rev-3 UV-P carry:**

- `[UV-P: whether Asana's story stream, AS REPLAYED through this path, is complete enough that absence-of-retained-record equals absence-of-movement | METHOD: deferred-to-live-probe or S4 | REASON: item 5b's ONLY remaining ground. The path narrows the stream twice — a 2h staleness window (section_timeline_service.py:337) and a cross-project noise filter that DROPS stories (:343-346) — and neither narrowing is exhibited in the response. Not probed live: read-only fence, no API calls made this dispatch]`
- `[UV-P: whether a section-timelines request over a multi-day window returns the expected shape and completes within its stated budget against live data | METHOD: deferred-to-S4 | REASON: SVR-S1-31/32/33 prove the route is mounted and the computation is specified by code-read; section_timelines.py:110-112 states a <5s cold-path budget, which is a claim about a live surface this seat did NOT execute. Items 2 and 5a are SAY-ABLE verdicts, which are claims about say-ability and NOT about a verified round-trip — §0's fence governs]`
- `[UV-P: whether the left-censoring in section-timelines day counts is closable by widening the requested window | METHOD: deferred-to-S4 | REASON: SVR-S1-35 proves the counts are period-clipped; whether a window predating the project makes the clip vacuous is an operational question this seat did not test. Subsumed in practice by item 2's withdrawal at rev-4, but recorded because it survives any future re-adjudication]`

**Rev-4 UV-P carry — the one genuinely open link (PT-02 C-7):**

- `[UV-P: whether anything actually fetches stories for OFFER tasks in production — i.e. whether the story cache is populated for offers at all | METHOD: deferred-to-live-probe (CloudWatch on stories_fetch_started / stories_fetch_completed_no_cache, or a cache inspection) | REASON: THE load-bearing open link under restated tier (iii). SVR-S1-44/45/46/47 prove the substrate does NOT exclude edit history — the fetch is unnarrowed and the only narrowing is one consumer at read time — but availability turns on whether the fetch has ever run for offers. The SAME probe closes option (g)'s cache-warmth question, so one probe closes both. NOT inferred in either direction: I could not verify the endpoint's invocation history or current cache state, and no log query or API call was made this dispatch]`
- `[UV-P: whether an imputed-vs-observed discriminator can be added to OfferTimelineEntry | METHOD: deferred-to-S4 or a producer change | REASON: this is the exact closing condition for BOTH item 2 and item 2'. story_count already exists upstream on SectionTimeline (section_timeline.py:62) and is dropped at the boundary; whether surfacing it is a bounded additive change or carries contract consequences is not this seat's call and was not assessed]`
- `[UV-P: whether the section entity frame (POST /v1/query/section/rows) enumerates sections holding ZERO tasks | METHOD: deferred-to-S4 or live-probe | REASON: SVR-S1-25 proves the entity is registered with its own schema; whether the frame's construction path includes empty sections is not determinable by static read. This is the unfenced denominator candidate for item 1's roster and for §2.7 row 3, and it is deliberately not asserted in either direction]`
- `[UV-P: whether POST /v1/query/offer/aggregate with group_by:["section"], aggregations:[{column:"last_modified",agg:"max"}] returns the expected shape against live data | METHOD: deferred-to-S4 | REASON: SVR-S1-12/13/14 prove the request is schema-legal and dtype-compatible by code-read; it was NOT executed — no live API calls made this dispatch. Item 1a's SAY-ABLE verdict is a claim about say-ability, not about a verified round-trip; §0's fence governs]`
- `[UV-P: whether the shape :1502-1504 zero-K-lane fence bars READ-ONLY downstream consumption of a SectionInfo-derived value, as distinct from a TOUCH on the K-lane surface | METHOD: deferred-to-operator/potnia (routed as O-7) | REASON: item 1b and §2.7 row 3 are WITHHELD-PENDING solely on this reading; this seat applies the fence as written rather than construing it in its own favour]`

---

## 7. Evidence grades

| claim | grade | basis |
|---|---|---|
| the predicate's gate structure and verdict vocabulary | **MODERATE, and now CONTESTED** | self-attestation cap (shape `:1512`); authored by the seat it governs. The rite-disjoint critique **did not lift this** — it found three structural defects (F-5, F-6, F-7), all accepted and repaired here. **A repair authored by the same seat cannot lift its own grade**; the repaired structure has not been externally read. |
| **R-1 (referent, not property) and the `68/68` non-truncation correction** | **STRONG — but the grade is the critic's, not this seat's** | `CRITIQUE…§7` grades it STRONG on five receipts across **two repositories and two seats' code**: producer (`engine.py:136-141,168-196,286`), consumer (`fetcher.py:390,409-410`; `readiness.py:96-97`), and the wire (`EVIDENCE-w1:112-113`). Rite-disjoint from both the authoring seat and the pythia seat. This seat re-verified every anchor (§1.3) and **records the grade as inherited corroboration, not as self-attestation.** Revision 1's own §7 made this conditional on *"the rite-disjoint critique"*; that critique has run. |
| §3.0 — the measurand exists on a contracted, K-lane-free path | **MODERATE** | five direct-read anchors this dispatch (SVR-S1-10..14), each individually re-verified at `origin/main`; **corroborated independently and rite-disjointly twice** — by the hygiene critique (F-1, graded STRONG there) and by the S4 arch seat reaching the same conclusion by a different route (`ADR-mission-a…:255-268,401-413`). Held at MODERATE here **only** because the round-trip was not executed (UV-P) — the code-read is decisive, the live behaviour is not probed. |
| §3.0 — `last_modified` is last-move-only, so history is not reconstructible backward | **MODERATE** | `base.py:76-82` by direct read; corroborated at `ADR-mission-a…:288-290,420-422`. This is the one substantive finding revision 1 was *reaching for* and mis-stated, and the one point where this seat **refines the critique** rather than accepting it. |
| **item 1a** (`SAY-ABLE`) | **MODERATE, externally CORROBORATED** | re-derived at rev-2; **attacked five ways at delta pass 2 and held on all five**, including the G3-laundering-by-clause-(a) attack the critic expected to break it (§3.1.1). Rite-disjoint corroboration of a *verdict*, which is the strongest standing any classification in this artifact has. Still MODERATE: the round-trip is un-executed (UV-P) and the endpoint routing under it **changed at rev-3**, after the clearance. |
| items 3 and 4 (`WITHHELD-AXIS`) | **MODERATE, externally attacked and undented** | two-clock; `CRITIQUE…§5.2` attacked both limbs of item 4 and dented neither. Unchanged across all three revisions. |
| ~~**item 2** (`SAY-ABLE`) — NEW at rev-3~~ | **WITHDRAWN at rev-4** | The rev-3 grade line invited attack on *"whether a 2 h story-cache bound is a `bound` in G4's sense."* **The actual defect was one layer beneath that and in the same gate**: the imputation sign is population-dependent (C-6). The invitation was pointed at roughly the right gate and still missed the mechanism — recorded because a self-flagged uncertainty that names the wrong mechanism is **not** a substitute for the read. |
| ~~**item 5a** (`SAY-ABLE`)~~ | **WITHDRAWN at rev-5** | The rev-4 grade line invited attack on *"whether `N observed to move of M offers` is genuinely exhibitable"* — **and that invitation was correct**: G2 is one of the two gates that took it. But the invitation was authored **while the seat's own C-6 re-test was recorded as PASSED**, and that re-test was performed against `SectionTimeline.intervals` — an object no HTTP consumer receives. **A self-re-test conducted at the wrong layer produced a false PASS, and the correctly-aimed doubt beside it did not outweigh it.** This is the strongest single argument in the artifact for a second reader over a self-check. |
| **item 2′** (`WITHHELD-PENDING` on G2) — NEW at rev-4 | **MODERATE — un-critiqued, and it is a NEGATIVE** | Derived per PT-02's explicit invitation. It is the first thing this seat has authored that moves **toward** withheld, which by §3.2's own pattern makes it the *least* likely of this artifact's claims to be an error of the characteristic kind — and therefore the one whose reasoning deserves the least deference on that basis alone. |
| items 1b and 5b (`WITHHELD-PENDING`) | **MODERATE** | verdicts unchanged across rev-2 and rev-3; **grounds replaced twice**. 1b's ground is now the edit-vs-movement event-class mismatch (§3.0.2), which no fence ruling dissolves. 5b's is a replay-completeness UV-P. Both are narrower and more falsifiable than what they replaced, and neither has been externally read. |
| **§3.0.1 endpoint routing** (`/rows`, not `/aggregate`) | **MODERATE** | six direct-read anchors across both response models and both construction sites (SVR-S1-26..30). The C-1 finding is the critic's; the **verification that the swap does not fix the age axis — and that the content as-of is derived from the payload rather than read from meta — is this seat's** and is un-critiqued. |
| the disclosure rule DR-1..DR-8, DR-6a | **MODERATE** | P-1/P-12 inherited verbatim; DR-2/DR-3/DR-4 each instantiate a pattern already shipped in this repo rather than an invention. DR-4 is **strengthened by a rite-disjoint counter-example** (F-10, `freshness.py:617-627`) that this seat verified verbatim. |
| §5 operator items | **MODERATE** | each carries a file:line receipt; none is ruled here. O-6 is **rewritten** and its revision-1 form is withdrawn on the record. |

**One STRONG claim appears in this artifact (R-1), and it is inherited from the
rite-disjoint critique rather than asserted by this seat.** Everything this
revision authors is MODERATE or below, per `self-ref-evidence-grade-rule`.

**Ceiling declared, rev-5 — FINAL.** The `SAY-ABLE` set is **item 1a alone**, and
it is the **only** verdict in this artifact that has been attacked by a
rite-disjoint reader and held (five attacks, delta pass 2, §3.1.1). Every other
`SAY-ABLE` this seat ever asserted has been withdrawn: **item 2 at rev-4, item 5a
at rev-5.**

> **Two of the three `SAY-ABLE` verdicts this seat authored were wrong.** The one
> that survived is the one a critic tried hardest to break. That ratio is the
> artifact's most reliable output and should govern how its remaining claims are
> weighted.

**Grades on this revision's own work.** The 5a withdrawal, the G4′ adoption, and
the §3.2 method-finding are **MODERATE**: each rests on direct-read anchors
(SVR-S1-48..54, `temporal.py` read in full) and each **concedes** rather than
asserts, which is the disposition least exposed to this seat's characteristic
error — but the G4′ **clarification** (neutral branches) and its **stated limit**
are this seat's own additions and are un-critiqued.

Tier (iii)'s withdrawal has a second-order consequence worth stating: **this
artifact no longer asserts that anything is absent.** Every negative it now
carries is *uncontracted*, *fenced*, *unexhibitable*, or *unprobed* — each with a
named closing condition. That is a weaker artifact and a truer one.

**Ceiling declared, rev-3 (retained).** Two things remain true and must not be
collapsed:

1. **The gate structure has still never been externally read in its repaired
   form.** Delta pass 2 cleared a *verdict* (1a), not the *machinery*. F-5/F-6/F-7
   remain this seat's own repairs.
2. **Revision 3 moves two more candidates to `SAY-ABLE` on grounds no critic has
   seen** (items 2 and 5a), and re-routes the one candidate that *was* cleared
   (1a) to a different endpoint **after** its clearance. The clearance was of
   1a's gate reasoning, which is unchanged; the surface under it changed.

Across three revisions this seat has erred **only in one direction** — asserting
a surface's limits from a partial read of it, three times, each time resolved by
reading further (§3.0.1 records the pattern). The correction has therefore run
one way as well, withheld → say-able, five times. **A reader should treat that
asymmetry as a reason for suspicion of revision 3, not as a track record.**

---

## 8. Exit-criteria satisfaction (shape `:602-606`)

| # | exit criterion | where satisfied |
|---|---|---|
| 1 | a written predicate, applicable without re-reading P-3, deciding say-able vs withheld for an **arbitrary** candidate | §2 (five gates, ordered, first-failure-decides); **§2.0 declares what is classified (claims, not renders) and when the gates run (after DR-1)** — both undeclared in revision 1 and both defects the critique found; §1.2 (P-3 enters as `AXIS_STATE`, a value — `CRITIQUE…§5.6` confirms this discharges the *"without re-litigating P-3"* requirement and marks **exit criterion 1 satisfied**); §2.7 (three off-list candidates decided, re-derived under the repaired gates) |
| 2 | all five candidates classified, one-line justification each; the frame's pass treated as hypothesis | §3.1 table (**six rows — item 1 splits into 1a/1b**); §3.0 establishes the measurand *before* the gates run, which revision 1 did not do; §3.2 records CONFIRMED class split, REFINED item 4, **CONFIRMED-IN-PART/FALSIFIED-IN-PART** on *"buildable under P-3"*, and the withdrawal of revision 1's over-scoped sentence |
| 3 | disclosure rule inherits P-1 and P-12 **verbatim** — no third number, no polymorphic field, no coalescing | §4.1 (both quoted verbatim; `CRITIQUE…§5.3` checked them character-by-character and found no smuggling); §4.2 DR-1..DR-8 **+ DR-6a**; §4.3 worked render; the one candidate third-number question routed to the operator at §5 O-3 rather than assumed |
| 4 | audit-lead critique returned and dispositioned | **SATISFIED.** Pass 1 RETURNED 2026-08-12 verdict **BLOCK**; all eleven findings dispositioned in the REVISION 2 table (eight accepted or accepted-with-narrowing, two REJECTED-WITH-RECEIPT, one no-change). Delta pass 2 RETURNED verdict **UPHELD-WITH-CONDITIONS**: the **BLOCK is DISCHARGED**, item 1a **cleared on five attacks**, and **both rev-2 rejections CONCEDED** by the critic. Its two conditions C-1 and C-2 are dispositioned in the REVISION 3 table. `status: draft` **held** — the record clears the artifact, not the author. |

**Rung: PENDING. Artifact CLOSED at revision 5.** A file authored is not a
predicate adopted (shape `:889-896`). What is true at close:

- **All conditions met**: the critique's C-1/C-2, PT-02's C-6/C-7 (by withdrawal,
  per the tripwire), and delta pass 3's `5a WITHDRAW` + G4′ adoption.
- **The `SAY-ABLE` set is item 1a alone** — read via `/rows` (§3.0.1), subject to
  DR-2. Withheld: 1b, 2, 2′, 5a, 5b `WITHHELD-PENDING`; 3, 4 `WITHHELD-AXIS`.
- **This artifact asserts no absences.** Tier (iii) is
  uncontracted-and-one-consumer-discarded, with **one open link** (§6 UV-P) that
  a single live probe closes, along with option (g)'s warmth question.
- **The gate machinery is now partly externally read, and one gate was found
  defective by its own author.** G4 passed two items whose errors were not
  single-signed; **G4′ replaces it** (§2.4) and decides all three mechanically.
  The rev-4 routed question is **answered — gate defect, critic-owned.**
  F-5/F-6/F-7 remain externally unread.
- **One live product defect** was surfaced and is **referenced, not absorbed**:
  `DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`. Operator-routed.
- **Operator-reserved and untouched**: O-1, O-3, O-7, O-8, GATE-FORK, the
  gate-(b) scope question.
- **Nothing here authorizes a build.** §0's fence holds: one `SAY-ABLE` verdict
  sits upstream of an un-executed round-trip (§6), an un-ruled K-lane question
  (O-7), a possible S4 enumeration gap (§5 O-6), and the open story-cache probe.

> **The single most useful thing in this document is §3.2**, and it is a finding
> about the **method**: five errors of one class across two seats, and in every
> instance the only thing that caught it was **a second reader going one hop
> further**. No gate, no self-flag, and no calibration note ever did.
