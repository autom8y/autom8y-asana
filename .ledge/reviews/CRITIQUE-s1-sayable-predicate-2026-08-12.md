---
type: review
status: draft
artifact_id: CRITIQUE-s1-sayable-predicate-2026-08-12
initiative: asana-native-insight-delivery
sprint: S1-critique
rite: hygiene
critic_of: PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12
date: 2026-08-12
verdict: BLOCK
delta_pass_2_verdict: UPHELD-WITH-CONDITIONS
delta_pass_2_scope: item 1a; F-3 disposition; F-6 sub-claim; the two refinements; section-timelines
critic_seat: audit-lead (hygiene — rite-disjoint from the 10x-dev architect seat that authored the artifact)
---

# CRITIQUE — S1 say-able predicate, rite-disjoint

## 1. VERDICT

**BLOCK.**

The artifact's flagship refinement (R-1: the discriminator is referent, not
property) is **CONFIRMED and understated** — it survives every attack I could
mount and the code supports a *stronger* version than the artifact claims. But
the artifact's second load-bearing claim, the **FALSIFICATION** at §3.1
(*"for three of the five candidates the source does not carry the measurand at
all"*), is **REFUTED on shipped code and by the artifact's own primary evidence
file**. That claim is not decorative: §5 O-6 forwards it as *"decision-grade
input to S4 and, through it, to GATE-FORK: Mission A's cost is higher than the
frame's framing implies."* Feeding an operator-reserved fork a cost signal that
is wrong in the expensive direction is the charter `:52` floor
(**NEVER CONFIDENTLY WRONG**) firing against the artifact that invokes it.

BLOCK, not REVISION-REQUIRED, because §3, §3.1 and §5 O-6 must be **re-derived**,
not edited — the premise under them is false, and two of five classifications
change. The predicate machinery in §2 and the disclosure rule in §4 are largely
salvageable; §2.1/§2.2/§2.4 need structural repair (Findings F-5, F-6, F-7).

---

## 2. THE R-1 ADJUDICATION — S1 is right; pythia is the one I am contradicting

### 2.1 The finding

**S1's R-1 is CONFIRMED.** `total_count` is computed post-filter and
pre-pagination; `returned_count` is computed post-pagination. The pair is a
**truncation predicate over the served frame**. It carries **zero** board
correspondence — structurally, not merely epistemically.

Receipt chain, `autom8y-asana` @ `origin/main` (`4129ae7e`):

| step | receipt | what it establishes |
|---|---|---|
| the frame is loaded from the provider (cache), not Asana | `src/autom8_asana/query/engine.py:130-134` | the population is the **served frame**, not the board |
| filters applied | `src/autom8_asana/query/engine.py:168-170` (`df = df.filter(filter_expr)`) | `total_count` is **post-predicate** |
| **`total_count` taken** | `src/autom8_asana/query/engine.py:189-190` — `# 8. Total count (before pagination)` / `total_count = len(df)` | it is the pre-slice length of the *filtered* frame |
| limit clamped, then sliced | `engine.py:192-196` — `effective_limit = self.limits.clamp_limit(request.limit)` / `df = df.slice(request.offset, effective_limit)` | the only thing standing between the two numbers is **pagination** |
| `returned_count` taken | `engine.py:243` (`data = df.to_dicts()`) → `engine.py:286` (`returned_count=len(data)`) | post-slice |

Therefore `total_count == returned_count` **iff the filtered set fit inside one
page**. That is the whole semantic content of `68/68`.

The engine says so itself, unprompted, in a comment written for an unrelated
purpose — `src/autom8_asana/query/engine.py:136-141`:

> `# The post-filter total_count (step 8) conflates the two -- a zero-matching where on a 1480-row project would otherwise be mis-attested as honest_empty.`

An in-repo, author-independent statement that post-filter `total_count` **cannot
be read as a frame-level completeness fact**. This is the strongest single
receipt in the adjudication and S1 did not find it.

The **consumer side** corroborates independently, rite-disjoint from both seats.
`autom8y` monorepo @ `origin/main` (`7bbb418e`) — read via `git show`, never the
working tree, which is on `fix/wss-wildcard-scope-bypass-closure` @ `cd24d61f`:

- `services/account-status-recon/src/account_status_recon/fetcher.py:409-410` maps
  `"returned_count": meta.returned_count` and `"total_available": meta.total_count`
  — the exact pair S1 names.
- `fetcher.py:390` calls it, verbatim, *"the truncation pair"*.
- `readiness.py:96-97`: *"T-GUARD -- returned_count < total_available. A watermark
  over a truncated result is a watermark over an arbitrary window."*

The only consumer of `68/68` in production **already treats it as a truncation
guard**. Nothing anywhere reads it as board correspondence.

### 2.2 The `1,000` figure — verified, and it is the caller's, not the engine's

S1 and `REPORT…:100-102` both say "1,000-row limit per status group." True, but
the cap is **not** a platform constant: `guards.py:50` sets
`max_result_rows: int = 10_000` and `guards.py:67-72` clamps by
`min(requested, max_result_rows)`. The 1,000 is the ASR's own request:
`fetcher.py:504-514` — `classification="active", limit=1000` and
`classification="activating", limit=1000`. So the receipt is
"non-truncation against a **caller-chosen** 1,000-row page, itself 10× under the
engine ceiling." Immaterial to the verdict; material to any downstream author who
reads "1,000-row cap" as a platform invariant it can rely on. **REFINED.**

### 2.3 Whom I am contradicting, plainly

**I am contradicting pythia, not S1.**

The characterization of `68/68` as *"completeness receipted on every tick"* is
carried in two durable artifacts:

- `.know/telos/asana-native-insight-delivery.md:73-75` — *"completeness is
  receipted on every tick of the pause (68/68 active, 48/48 activating …) while
  recency is refused."*
- `.know/telos/asana-native-insight-delivery.md:157` — *"completeness receipted on
  every tick — **the fact that makes the class-B readout say-able under P-3**."*
- `.sos/wip/frames/asana-native-insight-delivery.md:71-79` — the same spine.

Adjudicated against the code:

- **What survives**: the receipt is real, it is per-tick, and it did hold
  continuously through the dark period. *Serve*-non-truncation is proven
  continuously. That much of pythia's claim stands.
- **What does not survive**: the load-bearing word. `68/68` is **not** a
  completeness receipt in any sense that licenses a claim about the board. It
  proves the page was not truncated. It cannot detect a frame that silently lost
  thirty active offers — such a frame reports `38/38` and passes every guard in
  the chain. A value argument that rests on "completeness proven continuously
  through the dark period" is therefore resting on **pagination hygiene**, and is
  weaker than stated.

`.know/telos/…:157` is the sentence that must change: `68/68` is not "the fact
that makes the class-B readout say-able." What makes a class-B readout say-able
is the **referent**, exactly as S1 argues.

### 2.4 Where S1 is imprecise in its own favour — REFINED, materiality: prose

S1's §1.3 blockquote glosses the receipt as *"we returned every row we had."*
That is one notch too generous, because `total_count` is post-filter
(`engine.py:168-190`). The exact gloss is:

> *"we returned every row we had **that matched this predicate**."*

The difference matters precisely at the boundary S1 is defending: "every row we
had" still sounds like a statement about the frame's contents. It is not. Same
correction applies to S1's §2.7 row-2 SAY-ABLE exemplar — *"the active cohort held
68 rows"* — where "the active cohort" is under-specified and re-imports the
ambiguity DR-1 exists to kill. The honest form is *"the served frame held 68 rows
whose classification matched `active`."*

Citation drift, immaterial: §7 cites `query.py:551-552` for a claim §1.3 correctly
anchors at `:552-553`. Line 551 is `"entity_type": entity_type,`.

---

## 3. FINDINGS

### F-1 — The FALSIFICATION premise is REFUTED. Materiality: **changes classifications and changes the GATE-FORK input.**

**Claim as written** (§3.1): *"items 1, 2 and 5 each require **per-section or
per-offer observation that does not exist today**. This sharpens NF-2 … to
'**for three of the five candidates the source does not carry the measurand at
all**.'"* Supported solely by the field list of one log line,
`query_rows_complete` (`query.py:548-560`).

**What I did**: took the instruction to look beyond `query.py` literally. Read the
row model, the queryable schema, the aggregate compiler's dtype matrix, the
section-persistence emissions, the freshness-delta emissions, and the appendix of
S1's own primary evidence file.

**Receipts** — `autom8y-asana` @ `origin/main`:

**(a) The per-offer edit-time measurand is a first-class, non-nullable column.**
- `src/autom8_asana/dataframes/models/task_row.py:50-51` — `last_modified: dt.datetime`, `section: str | None`; `OfferRow(TaskRow)` at `:158`.
- `src/autom8_asana/dataframes/schemas/base.py:76-89` — `ColumnDef(name="last_modified", dtype="Datetime", nullable=False, source="modified_at", …)` and `ColumnDef(name="section", …)`.
- `src/autom8_asana/dataframes/schemas/offer.py:213` — `OFFER_SCHEMA` is built from `*BASE_COLUMNS`, so both columns are on every offer row.

**(b) The per-section quiet-time readout is a legal query against a shipped
endpoint, today.**
- `src/autom8_asana/api/routes/query.py:565-572` — the `/{entity_type}/aggregate` route exists.
- `src/autom8_asana/query/models.py:197-206` — `group_by` (1–5 columns) + `aggregations` (1–10 `AggSpec`).
- `src/autom8_asana/query/aggregator.py:36` — `_ORDERABLE_AGGS = frozenset({AggFunction.MIN, AggFunction.MAX})`.
- `src/autom8_asana/query/aggregator.py:49` — `"Datetime": _ORDERABLE_AGGS | _UNIVERSAL_AGGS`.

  `MAX` over a `Datetime` column is an **explicitly enumerated compatibility
  entry**. `group_by: ["section"], aggregations: [{column: "last_modified",
  agg: "max"}]` is a request the service accepts now. That *is* candidate 1's
  measurand — `now − max(last_modified) per section` — with no new emission, no
  new retention, and no history.

**(c) A per-section observation series is already emitted, already retained, and
was already queried by this initiative.** From S1's own primary evidence file,
`.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md`:
- `:633-640` — *"per-section persisted watermark series (5 chunks, 10 239 records; 7 227 on the 8 constituent sections; no truncation)"*, driven by the `modified_since=` emission at `src/autom8_asana/dataframes/builders/freshness.py:298-306`.
- `:645-646` — *"per-section content-change events (168 records, 16 d)"* — `freshness_delta_section_updated`, emitted at `src/autom8_asana/dataframes/builders/freshness.py:563-574` with `section_gid`, `verdict`, `added`, `removed`, `delta_tasks`, `final_rows`.
- `:642-643` — *"offers section census + row counts (34 sections, 8 311 records matched)"* — `section_status_updated`, `src/autom8_asana/dataframes/section_persistence.py:551-560`.
- `:613` — *"7 227 direct watermark observations; 15-day segment"*, graded **STRONG**.
- Per-section watermark is also persisted durably: `section_persistence.py:90` (`watermark: datetime | None`) and `:537-540` (`mark_section_complete(section_gid, rows, watermark=watermark, …)`).

**Verdict: REFUTED.** The measurand exists in **three** independent places — a
queryable column, a durable per-section manifest field, and a retained
per-section event stream that this initiative has already mined to STRONG grade.
S1 inspected exactly one log line and generalised to "the substrate."

**What S1 could defensibly have written** (and what the re-derivation should say):
*"no **contracted source-of-record** carries the measurand — it is reachable
today only via a CloudWatch Logs Insights query and an uncontracted aggregate
call."* That is true, it preserves NF-2's force, and it prices Mission A far
lower than §3.1/O-6 currently do. The distinction between *absent* and
*uncontracted* is the entire cost delta the operator is about to rule on.

### F-2 — G2's masking argument is a property of the ASR gate, not the substrate. Materiality: **changes item 1's stated grounds.**

**Claim as written** (§2.2 shape 2): *"the observed board-behaviour series is a
per-cohort watermark, `max` over the sections in the cohort … only the argmax
section is ever visible; every quieter section is masked by construction."*

**Receipt**: `EVIDENCE-w1:198-200` does say the advance series is `max over
sections in cohort` — but that is the **cohort roll-up** the ASR gate consumes.
Underneath it, `EVIDENCE-w1:146-151` names per-section watermarks by GID with
microsecond values, and `:633-640` shows the 10,239-record **per-section** series
they came from. A new readout is not obliged to consume the ASR's reduction.

**Verdict: REFUTED as a substrate claim; CONFIRMED only as a claim about the ASR
gate's emission.** "Masked by construction" is false; "masked by *this
consumer's* construction" is true and is a different disposition — it is fixed by
querying differently, not by a source decision.

### F-3 — G2's zero-row-invisibility argument is inverted. Materiality: **changes item 1's and §2.7-row-3's grounds.**

**Claim as written** (§2.2 shape 3): *"A row-derived observation cannot see a
section with no rows."*

**Receipt**: true of a row-derived observation, and irrelevant, because the
census is **section**-derived: `section_status_updated`
(`section_persistence.py:551-560`) emits one record per section with `rows`, and
`EVIDENCE-w1:642-643` matched **8 311 records across all 34 sections** — which is
exactly how S1's own cited `:128` figure ("21 sections are 0-row") was obtained.
The zero-row sections are not the invisible set; they are the *only* set that
census makes visible, and they are enumerable **with names** by GID.

Consequence for the gate as written: G2 says *"PASS iff the denominator is
exhibitable and exhibited."* For a per-section leaderboard the denominator **is**
exhibitable — `"13 of 34 sections report a last-edit; 21 hold no rows and cannot"`
— which is precisely the DR-5 `k of n` form. G2 should PASS with exhibition.

S1's §2.7 row 3 is doubly affected: *"Which sections currently hold zero offers"*
is marked **G2 FAIL — zero-row sections are the invisible set**, when the census
answers that question directly and is the artifact's own source for the number.

**Verdict: REFUTED.**

### F-4 — Item 2 (dwell): the negative is asserted where a UV-P was warranted. Materiality: **prose + one honest gap.**

**Claim as written** (§3 row 2): *"the substrate carries cohort-level counts and
watermarks, **not per-offer transitions**."*

**Receipt**: `src/autom8_asana/cache/integration/stories.py:20-31` —
`DEFAULT_STORY_TYPES`, described at `:21` as *"track task state changes that
affect dataframe rows"*, includes **`"section_changed"`**, alongside
`added_to_project` / `removed_from_project`. The incremental loader is live
infrastructure (`stories.py:3-4`; wired at `src/autom8_asana/clients/stories.py:406-416`
and `src/autom8_asana/lambda_handlers/cache_invalidate.py:139`).

A `section_changed` story **is** a per-offer transition with a timestamp. That is
the dwell measurand.

**What I could not close**: whether `section_changed` stories are actually fetched
and retained for offer-project tasks in production, and with what horizon. I did
not probe live story cache contents (read-only fence + no AWS mutations).

**Verdict: REFUTED as written** — the flat negative "the substrate carries … not
per-offer transitions" is false; a per-offer transition capture path exists in
the substrate. The honest form is a UV-P on population, not an assertion of
absence. Item 2's `WITHHELD-PENDING` verdict may well survive; its *reason* does
not. Note S1 already carries two UV-Ps on adjacent questions (§6) — it knew how to
do this and did not do it here.

### F-5 — G1 conflates a render defect with a value defect, and contradicts §2.1 using S1's own example. Materiality: **structural; affects the terminating rule.**

**Claim as written** (§2.1): *"VERDICT-CLASS terminates the predicate:
`WITHHELD-AXIS`. **No disclosure rescues it, because the failure is in the value,
not in the render.**"*

**Test**: apply it to S1's own §1.3 table. *"The board has 68 active offers"* and
*"at the last observed frame build, the served active cohort held 68 rows"* carry
**the same integer** and differ **only in render**. S1 says so explicitly:
*"Both sentences carry the same integer. One is say-able and one is not."* So for
that pair, disclosure (DR-1) **does** rescue it — the failure is *entirely* in
the render.

This means G1 is doing two different jobs under one name:
- **G1-tense**: is the claim worded world-now? → rescuable by DR-1 restatement.
- **G1-two-clock**: does the value join a second, independently-drifting system of
  record? → **not** rescuable by any wording, because a stale board field against
  live spend produces a **wrong number**, not a mistimed one.

Only the second matches §2.1's stated rationale. The "fast screen" S1 demotes to
*"the cheap path"* is in fact the only part of G1 that terminates for the reason
§2.1 gives.

**Second-order defect**: the artifact never says whether G1 is applied **before**
or **after** DR-1 normalisation. §1.3 says *"the predicate operates on the claim"*
(→ before), but §2.7 row 3 accepts *"which sections **currently** hold zero
offers"* as COMPLETENESS-class (→ after; as literally worded, "currently" is a
world-now assertion that becomes **false**, not lagged, the moment a row lands).
Applied "before," candidate 1's *"have gone longest without an edit"* is also
world-now and should be VERDICT-class. Applied "after," G1 collapses into the
two-clock screen. The artifact uses both readings within five pages.

**Verdict: REFINED (structural).** Not fatal to items 3/4 — they are two-clock and
stay `WITHHELD-AXIS` on the surviving limb — but §2.1's terminating rule is
over-broad as stated, and the normalisation order must be declared.

### F-6 — G3's escape clause (c) does not satisfy G3's own rationale. Materiality: **items 1 and 5 are not decided by the gate text.**

**Claim as written** (§2.3): rationale — *"absence of observation is
indistinguishable from absence of event."* PASS condition — *"(a) the claim is
positive, or (b) … observation-coverage receipt …, or (c) the claim is restated
positively (**"last observed edit: {t}"** instead of "has not been edited since
{t}")."*

**Test**: clause (c) is unconditionally available to every absence claim, and it
adds **no** epistemic content. If the observer was dead across the window,
*"last observed edit: 2026-08-07"* is exactly as misleading as *"has not been
edited since 2026-08-07"* — the reader reconstructs the forbidden inference in one
step. (c) is a **tense** fix offered as an equal alternative to (b), which is an
**evidence** fix. The gate's rationale demands (b); its PASS condition accepts (c).

**Consequence, and this is the material part**: S1 fails **items 1 and 5** on G3
(*"absence claim with no observer-liveness receipt"*). Under G3(c) as written,
both are rescued by a one-line rewording. **The gate text does not produce the
verdicts claimed** — judgment leaked in at exactly the point the task asked me to
check. And a genuine (b) receipt is also available: the per-section content-change
event stream (F-1(c)) is an observation-coverage series.

To answer the question posed directly: **G3 is not over-strict — it is
under-strict, and it is internally inconsistent.** An over-strict G3 would refuse
claims the initiative must make; the G3 actually written refuses nothing, because
(c) always applies. Either delete (c), or gate it behind (b) ("restate positively
**and** carry the coverage receipt").

### F-7 — G2's "exhibited" limb and G4 are render conditions evaluated at classification time, which makes `SAY-ABLE` structurally unreachable. Materiality: **structural; explains why 3/5 landed on `WITHHELD-PENDING`.**

**Claim as written**: G2 — *"PASS iff the denominator is **exhibitable and
exhibited**."* G4 — *"PASS iff bound and direction are **stated in the render**."*

**Test**: at classification time no render exists. Applied literally, **every**
candidate fails G4, including S1's own §2.7 row-2 exemplar — which S1 nonetheless
awards **`SAY-ABLE`**, filling the G4 cell with *"lag ≤4.0h, stale-never-fresh"*
(a statement of what *could* be disclosed, not of what *is* rendered). Applied
consistently, `SAY-ABLE` is unreachable and the verdict vocabulary has a dead
entry.

There is also straightforward duplication: **G4 ≡ DR-6** and **G2's exhibition
limb ≡ DR-5**, restated as gates. §4 already binds both on *"every published
number, in every readout, at every rung."* Two of the five gates are disclosure
rules wearing gate costumes — which is the mechanical reason all three
completeness-class candidates landed on `WITHHELD-PENDING`.

**Fix**: gates test **capability** (is the denominator *exhibitable*? is the bound
*known*?); the disclosure rule tests **performance** (is it *exhibited*? is it
*stated*?). Move "exhibited" and "stated in the render" out of §2 and leave them
in §4 where they already are. Under that split, and with F-1..F-3 applied, item 1
plausibly reaches `SAY-ABLE`.

I am **not** ruling that item 1 is say-able — that is the author's re-derivation
to make, and it needs the operator's O-3 answer on `k of n`. I am ruling that
**the grounds given do not produce the verdict given**.

### F-8 — UV-P-5 is a manufactured gap; it is answered in the artifact's own primary evidence file. Materiality: **honesty of the UV-P ledger.**

**Claim as written** (§6): `[UV-P-5 … the asana service's CloudWatch log retention
| METHOD: deferred-to-S4 | REASON: terraform/services/asana/ does not exist at
autom8y origin/main]`

**Receipts**:
1. `EVIDENCE-w1:624` — *"**Log groups** (both `retentionInDays: 30`, confirmed via
   `describe-log-groups`): `/ecs/autom8y-asana-service` … `/aws/lambda/autom8y-account-status-recon`."*
   S1 cites this file nine times. The answer is **live-probed and recorded** in it.
2. The stated REASON is also mis-scoped. `terraform/services/asana/` **does** exist
   — in *this* repo, at `origin/main`, six tracked files including
   `observability_alarms.tf` and `substrate_v2_provability_alarms.tf`
   (`git ls-tree -r --name-only origin/main terraform/services/asana/`). It is
   absent from the *autom8y* monorepo, which is the tree S1 checked.

**Verdict: REFUTED.** Retention is **30 days**, on a live `describe-log-groups`
probe. Discharge UV-P-5 and carry the number — it is load-bearing for any
candidate whose measurand lives in logs, which after F-1 is most of them.

Partial credit where due: the retention answer *sharpens* rather than dissolves
the concern. A 30-day rolling window is not a source-of-record, and "week by week"
trending (item 1) and any multi-month series die at day 31. That is the honest
NF-2 sharpening §3.1 was reaching for.

### F-9 — Receipt spot-checks: SVR ledger is sound. Materiality: **none — recorded as evidence the artifact was not sampled but checked.**

Every SVR in §6 that I could reach was verified at `origin/main`:

| SVR | verdict | note |
|---|---|---|
| SVR-S1-1 `query.py:548-560` | **CONFIRMED** | marker `"total_count": result.meta.total_count,` at `:552` |
| SVR-S1-2 `metrics/freshness.py:746` | **CONFIRMED** | verbatim: ``computes ``now - min(last_verified_at)`` over the in-scope set`` |
| SVR-S1-3 `metrics/freshness.py:632-638` | **CONFIRMED** | one `mutation_block` under `"freshness"` `:635` and `"mutation_age"` `:637`; marker at `:634` |
| SVR-S1-4 `metrics/freshness.py:602-605` | **CONFIRMED** | verbatim at `:602-604` |
| SVR-S1-5 `metrics/freshness.py:675-679` | **CONFIRMED** | both axes + `in_scope_count` on one line |
| SVR-S1-6 `metrics/__main__.py:1000-1002` + `freshness.py:650-655` | **CONFIRMED** | the marker is at `:652` (docstring); the live `return` is `:656`, one line outside the cited range |
| SVR-S1-7/8/9 (EVIDENCE-w1) | **CONFIRMED** | `:198-200`, `:188`, `:128` all read as quoted |
| O-4 `metrics/freshness.py:606-614` | **CONFIRMED** | `oldest_verified_at` / `max_age_seconds` / `backfill_used` present as described |

The SVR ledger is the strongest part of the artifact. Its defect is **scope, not
accuracy**: every receipt is true, and §3.1 generalises from one of them to a
claim about the whole substrate.

### F-10 — DR-4's cited positive exemplar is half a counter-example. Materiality: **strengthens DR-4; the operator should see it.**

**Claim as written** (DR-4): *"The platform already holds the correct pattern: the
verification block is 'always present so operators can detect the unavailable
state explicitly rather than via field absence' (`metrics/freshness.py:602-605`)."*

**Receipt**: the `available: False` branch at
`src/autom8_asana/metrics/freshness.py:617-627` emits
`"max_age_seconds": 0` and `"stale": False` alongside `"available": False`.

The **flag** is explicit; the **number beside it reads perfectly fresh**. A
consumer that reads `verification_age.max_age_seconds` without first branching on
`available` gets `0` — "verified this instant." That is null-meaning-fresh
wearing a boolean seatbelt, in the exact code DR-4 cites as the pattern to
inherit.

**Verdict: REFINED, and it is a gift to DR-4** — the rule is *more* necessary than
S1 argues, and there is a shipped surface that does not satisfy it. Route
alongside O-2/O-5 into the P-8 successor ADR. I am **not** ruling on that ADR.

### F-11 — Denominator wobble in the founding artifact. Materiality: **advisory.**

`REPORT-asr-team-brief-2026-08-12.md:101-102` says *"about **67** active and 48
activating"*; `:138` says *"**68** of 68 active"*. S1 quotes both passages (§1.3)
without reconciling them. Almost certainly one row moving between the capacity
note and the check-in — but it is precisely the class of thing DR-5 exists to
surface, occurring inside the artifact that S1's disclosure rule governs.
Advisory; not blocking.

---

## 4. WHAT I COULD NOT TEST

Named honestly. I did not manufacture findings to fill these.

- `[UV-P: whether `section_changed` stories are actually fetched and retained for offer-project tasks in production, and over what horizon | METHOD: deferred-to-live-probe or S4 source-of-record enumeration | REASON: F-4 establishes the capture path exists in code (`cache/integration/stories.py:20-31`); population and retention require a live cache/API probe, outside this seat's read-only fence]`
- `[UV-P: whether `POST /v1/query/offer/aggregate` with `group_by:["section"], aggregations:[{column:"last_modified",agg:"max"}]` returns the expected shape against live data | METHOD: deferred-to-S4 | REASON: F-1(b) proves the request is schema-legal and dtype-compatible by code-read (`aggregator.py:49`); I did not execute it — no live API calls made]`
- `[UV-P: whether the retained frame snapshots (`dataframe_cache_put`, 267 builds / 15 d) are individually addressable such that per-offer section transitions could be reconstructed by frame-diff | METHOD: deferred-to-S4 | REASON: S3 backend object retention/versioning not probed; this is the second candidate dwell path after stories]`
- `[UV-P: whether the 30-day log retention (F-8) is declared in IaC anywhere in the fleet | METHOD: deferred | REASON: no `retention_in_days` appears anywhere under `terraform/` at this repo's origin/main; the 30 days is an observed runtime fact (`describe-log-groups`), not a contracted one — which is itself relevant to the contracted-vs-reachable distinction in F-1]`
- `[UV-P: S1's own UV-P on the ASR verdict-surface starvation (`orchestrator.py:242` / `:440`) | METHOD: not re-probed | REASON: out of scope for this critique; S1's UV-P is correctly formed and correctly scoped to the monorepo]`
- **Not tested by design**: P-1..P-12 and the seven ADR-007 rulings (ratified — I checked S1's *application* of P-3/P-5/P-12 and found no misapplication); GATE-FORK; the gate-(b) scope question; O-1..O-6 dispositions. Where my findings bear on an operator item I say so and route it (F-8 → discharge in-place; F-10 → P-8 successor ADR; F-1 → **O-6 must be re-authored before the operator reads it**).

---

## 5. WHAT I TRIED THAT FAILED TO BREAK THE ARTIFACT

Recorded because a critique that only lists hits is not calibrated.

1. **Attacked R-1 from the code, expecting to find board correspondence hiding in
   `total_count`.** Failed — it is post-filter/pre-slice and the engine's own
   comment says so. R-1 came out **stronger**, not weaker.
2. **Attacked the two-clock screen as over-broad.** It holds. Items 3 and 4 join
   `weekly_ad_spend` (board) to campaign spend (external), and stale-vs-live there
   produces a *wrong number*, not a *lagged* one. Independently, item 4's second
   refusal (the unbackfilled hole, `REPORT…:144-145`) is a genuine REFINEMENT the
   frame missed and S1 caught. Item 4's `WITHHELD-AXIS` ×2 is **correct and
   well-argued** and I could not dent either limb.
3. **Attacked the P-1/P-12 verbatim inheritance for smuggling.** Checked
   `RULING…:19` and `:30` character-by-character against §4.1. Verbatim, no
   paraphrase, no third number invented, no polymorphism. DR-8 is a genuine and
   non-obvious consequence of the O-2 alias pair.
4. **Attacked DR-2's `min`-floor as invented.** It is not:
   `metrics/freshness.py:746` computes `now - min(last_verified_at)` and `:79-80`
   names `oldest_verified_at` the floor. Correctly grounded.
5. **Attacked the SVR ledger for vacuity/paraphrase (AP-2/AP-3).** All nine
   receipts survive the substring and orthogonality predicates. Clean.
6. **Attacked §0's scope fence for over-claiming.** It is the most disciplined part
   of the artifact — `SAY-ABLE IS NECESSARY, NEVER SUFFICIENT` is exactly right,
   and §1.2's `AXIS_STATE`-as-value mechanism genuinely discharges the mission's
   *"without re-litigating P-3"* requirement. Exit criterion 1 is **satisfied**.

The artifact is not sloppy. It is **precise about the wrong-sized object**: it
proved a sharp thing about one log line and let the conclusion inherit the scope
of "the substrate."

---

## 6. REMEDIATION — what must change before re-review

Blocking:

1. **§3.1 FALSIFIED / CONSEQUENCE and §5 O-6 — re-derive.** Replace *"the source
   does not carry the measurand at all"* with the defensible claim (**no
   contracted source-of-record carries it; three uncontracted reaches exist:
   `last_modified` via `/aggregate`, the per-section manifest watermark, and a
   30-day-retained per-section event stream**). Re-price Mission A accordingly.
   This is the GATE-FORK input; it must be right before the operator reads it.
2. **§3 items 1, 2, 5 — re-run the gates** against the per-section series
   (F-1..F-4). Verdicts may change; if item 1 lands `SAY-ABLE`, the §3.1 headline
   changes with it.
3. **§2.3 G3 — delete clause (c) or subordinate it to (b)** (F-6). Then re-decide
   items 1 and 5 on the repaired gate.
4. **§2.2 / §2.4 — move "exhibited" and "stated in the render" from the gates into
   §4** (F-7), so `SAY-ABLE` is reachable and the gates test capability.
5. **§2.1 — declare the normalisation order** (G1 before or after DR-1) and narrow
   the *"no disclosure rescues it"* rule to the two-clock limb (F-5).
6. **§6 — discharge UV-P-5** with the 30-day figure and correct the mis-scoped
   REASON (F-8).

Advisory (do not block re-review):

7. §1.3 gloss → *"every row we had **that matched this predicate**"* (§2.4 above).
8. §7 citation `:551-552` → `:552-553`.
9. Add F-10 (the `max_age_seconds: 0` unavailable branch) to O-2/O-5's routing
   into the P-8 successor ADR.
10. Note the `REPORT` 67-vs-68 wobble (F-11).

Route: **back to the 10x-dev architect seat** (author). No janitor or enforcer
routing — nothing here is a commit-hygiene or plan-structure defect. The frame
and `.know/telos/…:73-75,157` also carry the superseded "completeness receipted"
sentence; whether to amend in place is **O-1, the operator's**, and my §2.3
finding is input to it, not a ruling on it.

---

## 7. GRADE — self-attestation

| claim class | grade | ceiling and why |
|---|---|---|
| R-1 adjudication (§2) | **STRONG** | five independent receipts across **two repositories and two seats' code** — producer (`engine.py:136-141,168-196,286`), consumer (`fetcher.py:390,409-410`; `readiness.py:96-97`), and the wire (`EVIDENCE-w1:112-113`). Rite-disjoint from both the authoring seat and the pythia seat. Not self-referential. |
| F-1 (measurand exists) | **STRONG** | three structurally independent paths, each with a direct code anchor; one of them (`aggregator.py:49`) is an explicit `Datetime`×`MAX` compatibility entry, which is as close to a decisive receipt as a static read gets. |
| F-8 (retention = 30 d) | **STRONG** | live `describe-log-groups` result recorded in `EVIDENCE-w1:624`; corroborated by the absence of any `retention_in_days` in this repo's `terraform/`. |
| F-2, F-3, F-9, F-10, F-11 | **MODERATE** | single-reader code inspection at a pinned SHA; no execution, no live probe. |
| F-4 (stories / dwell) | **MODERATE** | capture path proven by code-read; **population unproven** — carried as a UV-P rather than asserted. |
| F-5, F-6, F-7 (gate structure) | **MODERATE** | analytic findings about the artifact's internal consistency, demonstrated against the artifact's own worked examples. Structural reasoning, not empirical measurement; no external corroboration. |
| overall verdict (BLOCK) | **MODERATE** | rests on F-1 (STRONG) plus a **judgement** that a mispriced GATE-FORK input is blocking rather than advisory. The judgement is mine and is contestable by the operator; the fact under it is not. |

**Ceiling: no STRONG claim about the *predicate's own fitness* is made here** —
that would require a second rite-disjoint reader, and per
`self-ref-evidence-grade-rule` a single critique cannot lift a design artifact's
grade beyond corroborating or falsifying its individual claims. What this
critique **does** discharge is the artifact's own §7 conditional: R-1 was graded
MODERATE pending *"the rite-disjoint critique."* That critique has now run.
**R-1 is corroborated at STRONG on rite-disjoint code receipts.** The predicate's
gate structure remains MODERATE and is now **contested** on the three structural
findings above.

**Exit criterion 4 (shape `:606`) — "audit-lead critique returned and
dispositioned": RETURNED. NOT YET DISPOSITIONED.** The artifact stays
`status: draft`.

---

# DELTA PASS 2

**Scope, declared and held**: item 1a (the only candidate that moved to
`SAY-ABLE`); the two findings the author rejected with receipts (F-3's
disposition, F-6's sub-claim); the two refinements in item (3); and the
`GET /api/v1/offers/section-timelines` surface supplied by the coordinator.
**Nothing cleared in pass 1 is re-audited.** Items 3 and 4, the SVR ledger, the
P-1/P-12 verbatim inheritance, DR-2's `min`-floor grounding, and §0's scope fence
are untouched here and remain as dispositioned above.

Repo state at this pass: `autom8y-asana` `origin/main` `4129ae7e`. Monorepo read
**only** via `git show origin/main:` — it has moved to `a5c98f9c` and its working
tree is on a divergent branch a sibling session is actively committing to. No git
mutations.

## D1. VERDICT — UPHELD-WITH-CONDITIONS

**Item 1a's `SAY-ABLE` is sound.** I attacked it five ways and it held on all
five, including the one I expected to break it. The author cannot clear its own
move; this is the record that clears it. It is cleared.

**Both rejections are CONCEDED.** The author is right on F-3's disposition and
right on the F-6 sub-claim. On the second I was wrong in the most instructive way
available — I offered as a coverage receipt a stream that is structurally blind
to precisely the sections the readout exists to surface, which is the same
denominator error I convicted revision 1 of, committed by me, one gate over.

**Both refinements against pass 1 are CONFIRMED**, on own-hands receipts.

The two conditions are **C-1** (1a's named path is the weaker of the two
available surfaces, and the receipt it needs is not on it) and **C-2** (the
`section-timelines` surface refutes the *generality* of "history cannot be
manufactured backward" and reopens three grounds). Neither touches 1a's verdict.
Both are one-paragraph corrections plus one routed item.

## D2. ITEM 1a — five attacks, five holds

Claim under test, DR-1-normalised per the rev-2 §2.0 declaration (`:296-305`):
*"At the {t} observation, of the N sections holding offer rows, section X carried
the oldest last-edit: {t_x}."*

| # | attack | outcome |
|---|---|---|
| A-1 | **Two-clock smuggling.** Does the readout join a non-Asana system of record? | **HELD.** Board observations only. `max(last_modified) group_by section` reads one frame, one clock. A single clock cannot disagree with itself. G1 → COMPLETENESS is correct. |
| A-2 | **Denominator exhibitable only "in principle".** G2 as repaired asks whether the denominator *can* be exhibited; I expected this to be hand-wave. | **HELD, and better than the artifact claims.** `AggregateMeta.group_count` (`query/models.py:230`) puts N **on the wire**. The denominator is not a promise; it is a response field. |
| A-3 | **G3 laundering by clause (a).** This was my best shot: "gone longest without an edit" reads to a human as *"section X has not been edited for nine days"* — an absence claim. Is clause (a) doing what clause (c) used to do, under a new name? | **HELD.** The distinction is real and load-bearing. `last_modified` is **the board's own assertion, copied into the row** (`schemas/base.py:76-82`, `source="modified_at"`), not an inference from our observation cadence. If our pipeline died for five days, `last_modified` is not *falsified* — it is carried forward at whatever value the last frame build captured, so the computed quiet-time is **overstated, never understated**, by at most the frame age. G3 exists to stop "we saw nothing, therefore nothing happened." That failure cannot occur when the datum is the observed system's own timestamp. The author's point-claim carve-out (`:474-479`) is sound, and it is **not** clause (c) renamed: clause (c) rescued a claim by rewording it; this rescues a claim because its referent is a value the observer copied rather than a non-event the observer failed to see. |
| A-4 | **The ≤4.0 h bound is not enforced.** `EVIDENCE-w1:188`'s 4.0 h is an *observed 15-day maximum*, not a ceiling. If the build pipeline silently stops, frame age is unbounded — and the detector that would catch that is improvement #1, **named as coming, not shipped** (`REPORT…:172`). The very gap G3 names bites 1a through G4. | **HELD, conditionally, and the condition is already binding.** DR-2 (`§4.2`) requires the as-of to be a real floor on the face of the render, not a historical bound. A stalled pipeline then shows up **as an old as-of on the readout itself**. 1a's justification cites both receipts — *"the frame's own as-of plus the ≤4.0 h bound"* — and it is the first that carries the weight. Sound, but see **C-1**: the as-of the author's named endpoint actually returns is the wrong axis. |
| A-5 | **Receipt location.** Does the endpoint §3.0 path (a) names actually carry what 1a's render needs? | **LANDS — as a condition, not a failure.** See C-1. |

**Ruling on 1a: the gates as literally written produce `SAY-ABLE`, and they
produce it for the right reasons.** The split survives, and the history limb is
not doing load-bearing work the current-state limb inherits: 1a's measurand is
`now − max(last_modified)` evaluated at **one** observation, and it needs no
prior observation to be well-defined. That is the structural fact that makes the
split legitimate rather than convenient.

One product observation, explicitly **not** a gate finding: 1a's denominator is
*"sections holding offer rows"*, which under `EVIDENCE-w1:128` excludes 21 of 34
sections — and a zero-offer section is the most forgotten corner a
"forgotten corners" leaderboard could report. That is honest-and-incomplete, not
confidently wrong, so G2 correctly passes and DR-5 correctly carries the
exhibition duty. It belongs in the render and in S4's option enumeration, not in
the predicate. The capability/performance split introduced at §2.0 is working
exactly as designed here, which is itself evidence the F-7 repair was correct.

## D3. F-3 disposition — **CONCEDED. The author is right; I did not read the fence.**

Fence text, read own-hands at `.sos/wip/frames/asana-native-insight-delivery.shape.md:1502-1504`:

> **Zero K-lane dependency**: no touch on the offer-axis combiner, the
> freshness-meta reducer, `RowsMeta` / `AggregateMeta`, the manifest write path,
> or `SectionInfo`. **If a readout wants a number that only exists on the K-lane,
> it WAITS.**

`SectionInfo` and the manifest write path are named **verbatim**. The
`section_status_updated` emission sits at `section_persistence.py:551-560`,
immediately after `manifest.mark_section_complete(...)` (`:537-540`) and
`_save_manifest_async(manifest)` (`:549`), and its payload (`status`, `rows`,
`completed`) is manifest state over `SectionInfo` (`:83-93`). My "G2 should PASS
with exhibition" asserted a source was usable without checking whether this
initiative may use it.

**"Fenced, not invisible" is the correct disposition and is materially better
than mine** — it names a closable initiative-boundary condition rather than a
source absence, and it is reinforced by P-5's ratified consequence
(`RULING…:23`): the zero-row section population is a set whose *membership and
stamping semantics are mid-change on the K-lane*. A readout that took its
denominator from there would acquire exactly the dependency the fence forbids.

The rev-2 replacement candidate is sound and correctly hedged: the `section`
entity type is registered, `body_parameterized=True`, `warmable=False`, with its
own schema module (`core/entity_registry.py:1004-1020` — verified verbatim), and
whether its frame enumerates sections holding zero tasks is carried as a UV-P
rather than assumed. That is the right shape.

**One coherence note, routed not ruled.** The fence does not draw the line
between *touching* a K-lane surface and *reading a field off an already-shipped
response that was derived from one*. Applied as the author applies it to
`section_status_updated`, the same reasoning reaches `RowsMeta.honest_contract_complete`
— which is derived by reading the live `SectionManifest`
(`query/engine.py:519-543` region, `_derive_honest_contract_complete`) and is the
attestation C-1 says 1a needs. `RowsMeta` is **on** the fence list; so is
`AggregateMeta`. Either 1a's best attestation is fenced too, or reading a shipped
response field is not "touching" — and the artifact needs to say which, because
1a's soundness depends on the answer. **Operator/S4 boundary question. Not ruled
here.**

## D4. F-6 sub-claim — **CONCEDED without reservation.**

`builders/freshness.py:294-297`, read own-hands, verbatim:

> `# Residual (documented, NOT a regression): null-watermark`
> `# sections (~21/34 offer, ~4/17 unit per QA 2026-05-27)`
> `# bypass this branch entirely and retain the pre-existing`
> `# hash-only detection. ADR-006 §Revision-2-correction (D8).`

and the gate itself at `:298` — `if section_info.watermark is not None:`.

The `modified_since=` probe (`:301-306`) and therefore the whole content-change
detection path is entered **only** for watermark-bearing sections. My pass-1 offer
of `freshness_delta_section_updated` as a genuine G3(b) observation-coverage
receipt is **refuted on the emitter's own documentation**: the stream is blind to
approximately the same ~21/34 sections a quiet-corner readout exists to surface.
It is a coverage receipt for the watermark-bearing subset only, and it is
`SectionInfo`-gated besides — fenced on the same grounds as D3.

This is the sharper of the two concessions and I record it plainly: I cited a
coverage stream without checking its coverage. That is the F-1 error class,
authored by me. The author caught it with a receipt I could have read and did not.

## D5. The two refinements — both CONFIRMED

**Against me — two of three paths are fenced, so only one is usable.**
**CONFIRMED.** Path (b) is `SectionInfo.watermark` (`section_persistence.py:90`,
written at `:537-540`) — fenced by name. Path (c)'s value in the `modified_since=`
emission is `section_info.watermark` (`builders/freshness.py:298-303`) and its
census is the manifest write path — fenced on both limbs. Only path (a) — declared
`ColumnDef`s on a versioned schema — is available. The author's own note that
this does not rescue revision 1's claim is correct and honestly stated: path (a)
was the strongest of the three, so the refutation stands at full force with one
path instead of three. My "three places" framing overstated the *available*
surface even where it correctly refuted the *absence* claim.

**In its favour — `last_modified` is last-move-only.** **CONFIRMED.**
`schemas/base.py:76-82` declares one `Datetime` column sourced from `modified_at`;
a row carries one timestamp regardless of how many times the task moved.
S4 corroborates independently and verbatim at
`ADR-mission-a-source-of-record-2026-08-12.md:287-290` — *"⚠ Weakness 4 —
snapshot-only history: `last_modified` records the most recent move only. A
14-day retrospective series is not reconstructible from a snapshot"* — and
reaches the same recommendation by a different route at `:255-268` (the
`section` / `last_modified` / `created` column table with `base.py` anchors).

**My pass-1 sentence *"that IS candidate 1's measurand"* was therefore true of
the leaderboard and false of the trend.** I accept the correction as stated. It is
the same over-scoping I convicted revision 1 of, at one-tenth the magnitude, and
it is right that it is on the record.

## D6. `section-timelines` — it changes three grounds, and not 1a

Verified own-hands, all at `autom8y-asana` `origin/main`:

- `api/main.py:488` — `RouterMount(router=section_timelines_router)`, in the
  unconditional mount list, no guard.
- `api/routes/section_timelines.py:41` — `pat_router(prefix="/api/v1/offers")`;
  `:75-99` — `GET /section-timelines` taking `period_start`, `period_end`
  (inclusive dates) and an optional `classification`.
- `:103-106` — computes `active_section_days` and `billable_section_days` per
  offer *"by replaying its Asana section history within the specified date
  range"*; `:111-112` — *"computes on demand from cached task stories."*
- `services/section_timeline_service.py:334-337` —
  `client.stories.list_for_task_cached_async(..., max_cache_age_seconds=7200)`;
  `:341` — `[s for s in stories if s.resource_subtype == "section_changed"]`;
  `:352-354` → intervals; `:357-363` — imputation for never-moved tasks.
- `models/business/section_timeline.py:36-39` — `SectionInterval` carries
  `section_name`, `entered_at`, `exited_at`.
- **K-lane clean**: a grep of `section_timeline_service.py` for
  `SectionInfo|section_persistence|RowsMeta|AggregateMeta|manifest` returns
  **0 matches**. Nothing on the shape `:1502-1504` list is touched.

**The load-bearing property**: the observer for this surface is **Asana's own
story log, replayed at request time over a caller-chosen window** — not a
scheduled job of ours, and not a 30-day CloudWatch window. Movement history is
therefore reachable *backward*, today, with no accrual.

**The load-bearing limit, which cuts the other way**: the response contract
(`OfferTimelineEntry`, `:158-207`) exposes only `offer_gid`, `office_phone`,
`offer_id`, `active_section_days`, `billable_section_days` (*"Days in ACTIVE or
ACTIVATING sections"*, `:197`), `current_section`, `current_classification`.
**The intervals are computed internally and are not serialised.** And
`section_changed` ⊊ *edits*: a section move is an edit, an edit is not a section
move.

What that changes:

| target | ruling |
|---|---|
| **item 1a** | **NOTHING.** 1a is a current-state edit-recency claim on `last_modified`. `section-timelines` neither helps nor threatens it. My clearance of 1a stands independently. |
| **1b — verdict UPHELD, reason NARROWED** | `WITHHELD-PENDING` is right: 1b as worded needs *edit* history, and edit history genuinely cannot be manufactured backward. But the artifact's stated reason — *"history cannot be manufactured backward"* — is **too general**. **Movement** history is replayable backward today, over an arbitrary window, from a shipped mounted endpoint. The honest sentence is *"**edit** history cannot be manufactured backward; movement history can."* That distinction is decision-grade for S4. |
| **item 5 — verdict UPHELD, one limb's reason REFUTED** | The *"what moved"* limb does **not** *"inherit 1b's forward accrual"* (rev-2 `:3.1` row 5). Movement over a past weekend is replayable today. And for that limb the repaired-G3 observer-liveness objection **does not apply at all** — the silently-stopped-job hazard (`REPORT…:172`) is a property of *our* scheduled observer, and this surface reads the board's own event log retrospectively. Item 5's G3 FAIL is correct **only** under the edit-semantics reading of "moved". The artifact must say which reading it applies, because `REPORT…:189` is ambiguous and the two readings give different verdicts. |
| **item 2 — grounds must be re-derived; verdict now genuinely OPEN** | `billable_section_days − active_section_days` = days in ACTIVATING per offer over the window, and `current_classification` **exhibits the right-censoring split** (still-activating = in flight; now-active = completed) — i.e. the denominator the author calls "exhibitable" is exhibitable *from named response fields*, not merely in principle. The UV-P — *"whether these stories are actually fetched and retained for offer-project tasks"* — is substantially answered by the existence and construction of an endpoint whose entire purpose is to fetch exactly those stories for `BUSINESS_OFFERS_PROJECT_GID`. The residual is **operational** (story-history completeness from Asana, pagination, `_is_cross_project_noise` distortion, cold-path latency at 68+48 offers, PAT/JWT reachability), not substrate. |

**Routed, not ruled — the option-enumeration defect recurs one altitude up.**
S4's `ADR-mission-a…:415-424` declares *"OPTION (d) FIRES. NEGATIVE RESULT.
There is no contractable source for a 14-day retrospective board-behaviour
series, at any acceptable cost."* That negative is authored over an option slate
that does not contain `section-timelines`. For the **movement** measurand the
negative is contradicted by a shipped, mounted, OpenAPI-published route. For the
**edit** measurand it survives. **This is S4's to re-derive, and through S4 it is
GATE-FORK input — the retrospective half may be cheaper than the negative
implies, in exactly the way the current-state half turned out cheaper than
revision 1 implied.** Same error class, same direction, one sprint later. I
route it; I do not rule it.

## D7. CONDITIONS

**C-1 — 1a's named path carries neither receipt 1a's render needs. Re-anchor §3.0
path (a) on `/rows`.** *(Materiality: prose + one anchor swap. Does not change
1a's verdict; does prevent a downstream author from building the wrong thing.)*

`AggregateMeta` (`query/models.py:225-262`) carries `group_count` (`:230` — good,
that is 1a's denominator on the wire) and four **cache-clock** fields:
`freshness`, `data_age_seconds`, `staleness_ratio` (`:237-248`), `stale_served`
(`:253-262`). `query/engine.py:425-435` builds it with `**freshness_meta` only,
and `_get_freshness_meta` (`engine.py:517-543`) returns **exactly** those four
keys. So on `/aggregate`:

1. **There is no content as-of.** The only age is `data_age_seconds` — the
   *build* clock. That is the axis the ASR gate abandoned on honesty grounds:
   autom8y `origin/main` `readiness.py:84-87` — *"It does not read the serving
   cache entry's age (`data_age_seconds`), which advances on a rebuild whether or
   not one byte of upstream data moved -- a build clock wearing a freshness
   badge."* A downstream author who renders it as 1a's as-of commits the DR-4 /
   P-12 substitution the artifact forbids **using the field the artifact's own
   §3.0 points them at**.
2. **There is no `honest_contract_complete`.** It is spread into `RowsMeta`
   (`engine.py:292`) and **not** into `AggregateMeta`. A section whose build
   FAILED contributes zero rows, forms no group, and `group_count` silently
   absorbs it. The denominator is *exhibitable* but **not attestable**.
3. **Neither can be added by this initiative.** `AggregateMeta` is
   `extra="forbid"` (`models.py:228`) **and** is named on the shape `:1502-1504`
   fence.

The fix is already available and is what S4 recommends: read `/rows` with
`select:["gid","section","last_modified"]` and reduce client-side. At 68 + 48
rows there is no aggregation pressure, and `RowsMeta` carries
`honest_contract_complete` (`:292`), `honest_empty` (`:293`), and the
`total_count`/`returned_count` non-truncation pair (`:285-286`). **§3.0 path (a)
should name `/rows` as the receipt-bearing surface and `/aggregate` as an
optional convenience that loses two attestations.** As written it does the
reverse.

**C-2 — narrow the retrospective claim and re-derive three grounds.** Per D6:
1b's reason to *edit*-history specifically; item 5's *"what moved"* limb off the
forward-accrual ground; item 2's grounds onto the shipped surface with the
residual restated as operational. And route the S4 slate gap.

Neither condition requires a third full pass. Both are verifiable by re-reading
the amended sections against the anchors above.

## D8. WHAT I COULD NOT TEST — DELTA PASS 2

- `[UV-P: whether GET /api/v1/offers/section-timelines returns complete and accurate section history for offer tasks over a multi-week window in production | METHOD: deferred-to-live-probe (S4) | REASON: story-log completeness from Asana, pagination behaviour, `_is_cross_project_noise` filtering effects, cold-path latency at 68+48 offers, and PAT/JWT reachability for the initiative's consumer are all runtime facts; I read the route, the service, and the models, and executed nothing — read-only fence, no live API calls]`
- `[UV-P: whether the `section` entity frame enumerates sections holding zero tasks | METHOD: deferred-to-S4 | REASON: not determinable by static read; the author already carries this UV-P and I concur with its framing]`
- `[UV-P: whether the shape :1502-1504 fence extends to reading fields off already-shipped responses derived from SectionInfo (D3 coherence note) | METHOD: operator or S4 boundary ruling | REASON: operator-reserved initiative-boundary question; 1a's best attestation sits on the undrawn line]`
- **Not tested by design**: everything cleared in pass 1; the ratified rulings; GATE-FORK; the operator items.

## D9. GRADE — DELTA PASS 2

| claim class | grade | ceiling and why |
|---|---|---|
| 1a clearance (D2, five attacks) | **MODERATE** | Analytic testing of a claim against a written predicate, plus code anchors for each gate's substrate. Structural reasoning by a single reader; no execution. A-3's resolution is the load-bearing step and rests on a semantic distinction (copied-datum vs non-observation) that is sound but not externally corroborated. |
| C-1 (`AggregateMeta` lacks the as-of and the completeness attestation) | **STRONG** | Direct field-list read of `query/models.py:225-262`, the construction site `engine.py:425-435`, the exhaustive `_get_freshness_meta` return `engine.py:517-543`, the `RowsMeta` contrast `engine.py:285-298`, and a cross-repo corroboration that `data_age_seconds` is the abandoned axis (`readiness.py:84-87`). Five anchors, two repositories, no inference gaps. |
| D3 and D4 concessions | **STRONG** | Both rest on verbatim source the author cited and I re-read: the fence at shape `:1502-1504` and the bypass comment at `builders/freshness.py:294-298`. Conceding on a receipt is the least uncertain act available to a critic. |
| D5 refinements confirmed | **STRONG** | `schemas/base.py:76-82` plus rite-disjoint corroboration from the S4 arch seat at `ADR-mission-a…:287-290`, reached by a different route. |
| D6 (`section-timelines` changes three grounds) | **MODERATE** | Route, service, and response model read directly and the K-lane-clean grep is exhaustive; but every consequence I draw depends on runtime behaviour I did not exercise (D8 UV-P 1). I state what the contract *permits*, not what the endpoint *does*. |
| overall verdict (UPHELD-WITH-CONDITIONS) | **MODERATE** | Rests on the 1a clearance (MODERATE) and on a judgement that C-1 is a receipt-location defect rather than a verdict defect. That judgement is mine and is contestable; the field lists under it are not. |

**Calibration note, recorded against myself.** Pass 1 convicted revision 1 of
generalising from one `logger.info` to "the substrate." In pass 2 I conceded two
findings: one where I asserted a source was usable without reading the fence that
forbade it (D3), and one where I offered a coverage stream without reading its
coverage (D4). Both are the same error class I named. The author caught both with
receipts available to me at pass 1. That is the external-critique gate working in
the direction it is supposed to work in, and the grade above is set accordingly —
**no STRONG claim is made for any pass-2 analytic judgement, only for the
document reads.**

**Disposition of the pass-1 BLOCK: DISCHARGED.** The remediation is accepted.
Exit criterion 4 (shape `:606`) is **SATISFIED at pass 2** for the critique-
returned-and-dispositioned limb, subject to C-1 and C-2 being carried. The
artifact's own `status: draft` and rung `PENDING` are the author's and the
operator's to move, not mine.
