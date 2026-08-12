---
type: review
status: draft
artifact_id: CRITIQUE-s4-mission-a-source-of-record-2026-08-12
initiative: asana-native-insight-delivery
sprint: S4-critique
rite: eunomia
critic_of: ADR-mission-a-source-of-record-2026-08-12
date: 2026-08-12
verdict: BLOCK
---

# CRITIQUE — S4 Mission-A source-of-record (rite-disjoint, eunomia)

> Critic seat: **eunomia**. Artifacts under critique authored by a
> **dependency-analyst** seat in **arch**. Disjointness is the point of this
> seat and it did work: the finding that blocks is one an arch seat sharing the
> author's option-frame would plausibly have inherited rather than found.

---

## 1. VERDICT

> ## **BLOCK**

**One-sentence reason**: S4's bounded negative result — "no contractable source
exists at acceptable cost" for the retrospective half — is **refuted by a
published, schema-covered, K-lane-free, retention-independent endpoint in this
same repo, on this same project GID** (`GET /api/v1/offers/section-timelines`,
`docs/api-reference/openapi.json:3859`, `src/autom8_asana/api/routes/section_timelines.py:75-100`),
which S4 did not enumerate; consequently exit criterion 1 (options ENUMERATED
before recommendation) is self-attested **MET** when it is **NOT MET**, and §11's
one-sentence GATE-FORK input is a **false biconditional** feeding a live,
operator-reserved, date-bounded decision.

**BLOCK is not "start over."** §4 (UV-P-5), §8 (contract statement), §9 (K-lane
attestation) and §10 (NF-2 hazard) survive my attacks substantially intact, and
the §7.1 recommendation of option (b) for the forward-looking readout is
**CONFIRMED and should stand unchanged**. The remediation is bounded: enumerate
option (g), re-derive §7.2/§11, and correct one misdescribed observable. I
estimate that as a single revision pass, not a re-run.

---

## 2. THE NEGATIVE-RESULT ADJUDICATION (charge A)

S4's §7.2 rests the negative result on three legs. I tested each at source.

### 2.1 Leg 1 — "`last_modified` is last-move-only, so a snapshot cannot reconstruct cohort spread" → **REFUTED IN ITS PREMISE, CONFIRMED IN ITS CONCLUSION**

The conclusion (a snapshot carries no history) is trivially true and I do not
contest it. **The premise is wrong, and the error is load-bearing.**

`last_modified` is not a *move* tracker. Its declared source is `modified_at`
(`src/autom8_asana/dataframes/schemas/base.py:76-82`), Asana's task-modification
timestamp, description *"Last modification timestamp"* (`:81`). It advances on
**any** edit, not on section movement. S4 calls it "time-since-last-move"
(§5 option (b) table), *"`last_modified` records the **most recent** move only"*
(Weakness 4), and *"An offer that moved three times in 14 days is one row with
one timestamp"* (§7.2). All three sentences conflate **modification** with
**movement**.

That conflation is the mechanical cause of the miss in §2.4: because S4 believed
`last_modified` *was* the move record, it never asked where the move record
actually lives. It lives in Asana stories, and this repo already reads them
(§2.4).

**Materiality: HIGH.** It does not change leg 1's conclusion; it removes the
reasoning that concealed option (g).

### 2.2 Leg 2 — "options (a)/(e) cap at 30 days on an uncontracted schema" → **CONFIRMED** (with the receipt-precision caveat at §5.2)

I could not re-run the live AWS probes (§7 — no Bash in this seat). The
*structural* half of the claim I did verify: `query_rows_complete` is a
`logger.info` (`src/autom8_asana/api/routes/query.py:548-560`) with no schema
version, no consumer registry entry, and no test that fails on a field rename. I
found nothing that contradicts the 30-day retention chain and one thing that
independently corroborates its *mechanism* (§5.2).

### 2.3 Leg 3 — "decisively: brief #1's spine was `SectionInfo.watermark`, and reproducing it in a recurring product breaches this sprint's own K-lane fence" → **REFUTED AS DECISIVE**

This is the leg S4 stakes the word "decisively" on and grades **STRONG** (§15).
It fails on three independent grounds.

**(i) The watermark is `max(last_modified)` — derivable from the very columns
option (b) already returns. Four in-code receipts, none of them cited by S4:**

| receipt | text |
|---|---|
| `src/autom8_asana/dataframes/builders/freshness.py:536-540` | `new_watermark` ← `merged_df["last_modified"].max()` (delta-apply path) |
| `src/autom8_asana/dataframes/builders/freshness.py:646-648` | `max_val = section_df["last_modified"].max()` (second write path) |
| `src/autom8_asana/dataframes/builders/progressive.py:1729-1731` | `max_val = section_df["last_modified"].max()` (build path) |
| `src/autom8_asana/dataframes/builders/progressive.py:657-681` | `_heal_null_watermark` — docstring: *"Derive a watermark for a null-watermark section from its cached parquet's `last_modified` column"*; `:680` `max_val = df["last_modified"].max()` |

And the module S4 cites for `SectionInfo` says it in its own docstring:
`src/autom8_asana/dataframes/section_persistence.py:521` —
`watermark: Max modified_at timestamp (for complete status)`.

**(ii) ADR-007 itself says this class of value is consumer-derivable, in the
section S4 read.** `ADR-007:1198-1205`:

> *"The content axis shipped consumer-side with **zero** producer work because
> `content_watermark_returned` is derivable from the returned rows.
> **Verification recency is not consumer-derivable**…"*

The K-lane is about **verification** recency. The watermark is the **content**
axis. ADR-007's blast-radius table classes `SectionInfo` / manifest JSON as
**`+0 fields` … two-way — semantics only** (`ADR-007:1219`); the one-way door is
`RowsMeta`/`AggregateMeta` alone (`:1223`, `:1228-1239`). S4 imported the
one-way-door gravity of `RowsMeta` onto a field the K-lane does not change.

**(iii) S4 elevated an attestation requirement into a prohibition.** The sprint
block states the K-lane item as an *exit criterion*, not a fence:
`shape:696` — *"EXPLICIT statement that no ADR-007 K-lane surface is depended
on (RowsMeta / AggregateMeta / SectionInfo / freshness-meta reducer / manifest
write path)"*. The S4 block (`shape:672-703`) declares no `fences:` key at all;
its only stated boundaries are `pr_boundary` (`:679`) and
`producer_deploy: false` (`:680`). S4's ADR frontmatter (`:20`) restates this as
a binding fence — *"No dependency on any ADR-007 K-lane surface"* — and §7.2
then reads it as forbidding the **observable**, not the **dependency**. The
correct reading: do not *depend on* `SectionInfo`; a quantity independently
derivable from declared columns is not a dependency on it.

S4 is also internally inconsistent here. §7.3 retains option (a) for *"a one-off,
human-run, explicitly-labelled retrospective"* — which is precisely mining the
`modified_since=` lines whose values are `SectionInfo.watermark`. If the fence
bars the value, it bars the one-off. If the one-off is fine, the operative
distinction is **standing dependency vs. one-off read**, not K-lane provenance —
and §7.2 should say so.

**Materiality: HIGH.** Leg 3 is not decisive; it is redundant on the
retrospective half (legs 1 and 2 already carry it) and, as written, it risks
foreclosing the forward half.

### 2.4 The finding that blocks — option (g), not enumerated

**`GET /api/v1/offers/section-timelines`** is a live, mounted, published endpoint
that reconstructs offer section history from Asana's own story feed.

| property | receipt |
|---|---|
| Route declared with a Pydantic `response_model`, `summary`, `response_description` | `src/autom8_asana/api/routes/section_timelines.py:75-82` |
| Takes an arbitrary **retrospective window** `period_start` / `period_end` | `section_timelines.py:86-93` |
| *"Computes `active_section_days` and `billable_section_days` for each offer by **replaying its Asana section history within the specified date range**"* | `section_timelines.py:103-106` |
| Unconditionally mounted — no feature flag, no gate | `src/autom8_asana/api/main.py:488`; `src/autom8_asana/api/routes/__init__.py:50` |
| **In the published OpenAPI contract** — therefore covered by the CI spec-drift check that option (b)'s hidden `/rows` route is NOT | `docs/api-reference/openapi.json:3859`; schemas at `:1106` (`OfferTimelineEntry`), `:1907`, `:2061`; gate at `.github/workflows/test.yml:77-79` |
| **Same board** as `OFFER_CLASSIFIER` | `section_timeline_service.py:84` `BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"` == `models/business/activity.py:183` |
| Classification already applied via `OFFER_CLASSIFIER` | `section_timeline_service.py:232-233` |
| Intervals built from `section_changed` stories with real `entered_at`/`exited_at` | `section_timeline_service.py:197-269`; `models/business/section_timeline.py:20-39` |
| Day-counting clamps to the requested (past) period | `models/business/section_timeline.py:145-153` |
| **No CloudWatch retention dependency** — Asana is the store | `section_timeline_service.py:87-93` story `opt_fields` |
| **No K-lane contact** — reads `AsanaClient` stories + `CacheProvider`; no `SectionInfo`, no `RowsMeta`, no manifest | `section_timeline_service.py:414-421`, `:478-481`, `:496` |
| **No producer deploy** — already built and deployed | `main.py:488` |

**S4 had this file open.** It counted the six `/v1/query/*` path objects in
`openapi.json` and asserted the absence of a `/rows` path (SVR-4, §5 option (b)
Weakness 1) — I confirmed both counts (`openapi.json:8641, 8731, 8832, 8922,
9023, 9124`). `/api/v1/offers/section-timelines` sits at `:3859` in the same
file. This is a hard miss inside a read S4 performed, not an unlucky one.

**Honest calibration — what option (g) is NOT.** I attacked my own finding:

1. **It is not brief #1's statistic.** The HTTP response model
   (`models/business/section_timeline.py:158-226`, `extra: "forbid"` at `:212`)
   exposes only `offer_gid`, `office_phone`, `offer_id`, `active_section_days`,
   `billable_section_days`, `current_section`, `current_classification`. The raw
   `SectionInterval` list stays in the in-process `SectionTimeline` dataclass
   (`:42-62`) and is **not returned**. A readout wanting per-move intervals needs
   an additive field on an already-published model — option-(c)-class work, but
   an order of magnitude smaller than a new emission, and *covered* by the
   spec-drift gate rather than uncovered.
2. **`current_section` is current, not as-of-period-end** (`:200-203`, "from last
   interval"). Per-day occupancy is still reconstructible by sweeping single-day
   windows (`_count_days_for_classifications` clamps per call,
   `section_timeline.py:145-153`), at 14 calls for a 14-day window.
3. **It has a real silent-degradation defect.** `read_stories_batch` is
   pure-read (`section_timeline_service.py:495-496`). If more than
   `MAX_INLINE_STORY_FETCHES = 50` tasks miss the story cache, the gap is
   **logged and not filled** (`:502-541`), and those offers fall through to
   `_build_imputed_interval` (`:272-300`) — reported as if they had never moved.
   `cache_hits` / `cache_misses` are computed (`:545-546`) but **not returned**,
   so a consumer cannot distinguish a never-moved offer from a cache miss. A
   cache-provider-less client returns `[]` silently (`:434-443`).
4. **Coverage is current-membership-scoped**: it enumerates tasks currently in
   the project (`:478-481`). An offer removed from the board mid-window is absent.

Items 1 and 3 are exactly the disclosure-and-precondition class S4 handled well
for option (b) in §8.4. They make option (g) *conditioned*, not *unavailable*.

### 2.5 Explicit statement, as charged

> **YES. The operator is being told they cannot do something they in fact can.**

Two distinct instances:

1. **§7.2 / §11 tell the operator that no contractable retrospective source
   exists at any acceptable cost.** One exists, is already deployed, is *better*
   contracted than the source S4 recommends (in-schema vs. `include_in_schema=False`),
   carries no retention cap and no K-lane contact. §11's biconditional —
   *"Mission A is buildable as framed **if and only if** the operator rules that
   its readout may start its history at first run"* — is **false**. There is a
   third branch, and it is the cheapest of the three.

2. **§7.2's leg 3 risks foreclosing the forward half of the same metric.** A
   reader of *"the retrospective spine is K-lane-derived… building the recurring
   product on it would violate this sprint's own fence"* can reasonably conclude
   the cohort-spread *metric* is K-lane-tainted. It is not: per-section
   `max(last_modified)` is derivable from the row payload option (b) already
   returns (four receipts, §2.3(i)), with zero K-lane contact, warranted by
   ADR-007's own text (`:1198-1201`). S4 never connects `freshness.py:536-540` to
   `base.py:76-82` — and `freshness.py:536-541` sits in **EVIDENCE-w1's own code
   anchor list at `:666`**, inside the bounded context around the `:669` read S4
   was charged with and attests it performed
   (`HANDOFF-…:97`, `HANDOFF-…:146-148`).

**Corrected GATE-FORK input** (offered as sharpened input only — the fork is
operator-reserved and I do not touch it):

> The retrospective half is **reachable**. Three paths exist, not two: (1) begin
> the series at first run under option (b) — zero additional cost, and it
> reproduces brief #1's per-section watermark exactly, since that watermark *is*
> `max(last_modified)`; (2) consume `GET /api/v1/offers/section-timelines` for
> historical per-offer classification occupancy — already built, already in the
> published contract, no producer deploy, conditional on two additive disclosure
> fields (`cache_hits`/`cache_misses`) and on the day-sweep reconstruction; or
> (3) the 30-day-capped uncontracted log mine S4 correctly rejects. Mission A is
> **not** shown to be more expensive than framed on the retrospective half.

---

## 3. THE S1 CONVERGENCE CALL (charge E)

> **SHARED INHERITED CHAIN — not independent corroboration. The substance is
> nonetheless TRUE, and I verified it myself at source.**

**Reasoning, with receipts.** S1 is
`.ledge/decisions/PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md`.
At `:338-343` it states:

> *"`query_rows_complete` (`src/autom8_asana/api/routes/query.py:548-560`,
> verified by direct read at `4129ae7e`) emits `entity_type`, `total_count`,
> `returned_count`, `query_ms`, `caller_service`, `predicate_depth`, `section`,
> `classification` — **request-shaped, with no edit-time field**. A section
> appears in that stream iff some caller queried it. **Routed to S4** as a named
> option-enumeration input; not decided here."*

S1 did not converge with S4 from a different direction. **S1 derived the finding
and handed it to S4 by name.** S1 further carries the open question as an
explicit UV-P (`:516`): *"whether any per-section or per-offer observation series
can be reconstructed from an existing emission | METHOD: **deferred-to-S4-source-of-record**"*.
S4's ADR presents the same finding as its own discovery — *"⚠ Coverage
dependency the shape did not name"* (§5 option (a)) — and cites neither S1 nor
the routing. That is a provenance elision, and it is what makes the two readings
look like corroboration when they are one reading counted twice.

The two seats also share a third inherited item: S1 carries the **same false
premise** about UV-P-5 verbatim (`:518` — *"REASON: terraform/services/asana/
does not exist at autom8y origin/main"*), sourced from `shape:694`. S4 falsified
it. Credit where due — but S4's §2 attributes the falsified premise to shape §2.3
alone, when S1 propagated it too.

**Why I nonetheless call the substance TRUE**: I read the emission myself.
`query.py:557-558` is `"section": request_body.section` and
`"classification": request_body.classification` — **request-filter echoes**, not
properties of the returned rows. So the claim is stronger than either seat
states: option (a)'s `classification` dimension is *authored by the caller*, and
a caller querying without a classification filter emits `classification: null`.
`RowsRequest` enforces `section` and `classification` mutually exclusive
(`query/models.py:379-384`), so a single call can never carry both.

**The consequence of the shared chain is the real damage.** S1 routed *two*
enumeration questions to S4 (`:516`, `:517` — the latter noting that a dwell
identity *"needs gross transition flow, and counts yield only net change;
feasibility unassessed"*). **Gross transition flow is exactly what Asana stories
carry** (`section_timeline_service.py:197-269`). Both routed UV-Ps are answered
YES by option (g), and S4 discharged neither. A genuinely independent second
seat would have had a second chance to find it. That is the concrete cost of
inheritance masquerading as convergence — and it is the reason this critic seat
was made rite-disjoint.

**Is S4's counter-finding-2 fatal to option (a), as S4 implies?** **REFINED —
fatal for a source-of-record, not fatal for the surface.** S4's §7.3 already
gives the correct disposition (one-off, human-run, explicitly labelled), so the
ADR's *practice* is right; its *rhetoric* ("REJECTED") overstates relative to its
own carve-out. Caller-hostage coverage is disqualifying for a recurring
denominator because the denominator is unknowable, not merely noisy. On the
current registry, no consumer is declared against `entity_type=offer` rows at all
(`dataframes/contracts/consumer_column_requirements.vendored.json:9-23` lists
`/v1/query/project/rows` and `/v1/query/section/rows` only) — which sharpens the
point, though that file is an FM-5 *seed*, not a caller census, and I do not
treat it as one.

---

## 4. FINDINGS

Each: claim as written → what I did → receipt → disposition → materiality.

### F-1 — Option space asserted complete at six · **REFUTED** · moves a recommendation

*Claim* (§5, §16 criterion 1 "MET"): six options enumerated, four charged plus
two found. *Test*: swept the repo's own published HTTP surface for an existing
per-offer/per-section observation series — the exact question S1 routed to S4
(`PREDICATE…:516`). *Receipts*: `api/routes/section_timelines.py:75-100`;
`api/main.py:488`; `openapi.json:3859`; `section_timeline_service.py:84, 197-269`.
*Disposition*: **REFUTED**. A seventh option exists, in-repo, in-contract, on the
same board. *Materiality*: **moves §7.2, §11, §15 and exit criterion 1.**

### F-2 — "The retrospective spine is `SectionInfo`-derived, decisively" · **REFUTED as decisive** · moves a recommendation

*Test*: traced the watermark's derivation across every write path. *Receipts*:
`freshness.py:536-540`, `:646-648`; `progressive.py:657-681`, `:1729-1731`;
`section_persistence.py:521`; `ADR-007:1198-1205`, `:1219`; `shape:696`.
*Disposition*: **REFUTED as decisive** (redundant on the retrospective half;
wrong as a bar on the forward half). *Materiality*: **high** — it is the ground
§15 grades STRONG.

### F-3 — "`last_modified` yields time-since-last-**move**" · **REFUTED** · prose, but causally upstream of F-1

*Receipt*: `base.py:76-82` — `source="modified_at"`, *"Last modification
timestamp"*. *Disposition*: **REFUTED**. `modified_at` advances on any edit.
*Materiality*: prose in itself; **causal** in that it concealed F-1.

### F-4 — "`classification` is derivable from `section`; `section` is sufficient" · **REFINED** · adds a precondition

*Test*: compared the two classification semantics live in this codebase.
*Receipts*: query-engine filter is **section-only** —
`query/engine.py:153-161` (`pl.col("section").str.to_lowercase().is_in(...)`),
`:438-486`. The resolution path applies an **`is_completed` terminal override →
INACTIVE before the section lookup** — `services/universal_strategy.py:510-513`
(SD-6); unrecognized section → `None` at `:521-524` (EC-9). *Disposition*:
**REFINED** — true against the query surface's own definition, false against the
service's resolution semantics. A `section`-only readout will classify completed
offers into their section's group while other surfaces call them INACTIVE.
*Materiality*: adds a **fourth precondition** to §8.4 — the readout must declare
which classification semantic it implements, and disclose the divergence.

### F-5 — `OFFER_CLASSIFIER` is a silent staleness hazard · **CONFIRMED and WORSE** · sharpens §8.5

*Test*: read the classifier and its unknown-section path. *Receipts*:
`activity.py:48-74` — `classify()` is `self._mapping.get(section_name.lower())`,
returning `None` for any unknown name, **case-insensitive, no error, no log at
this layer**. `activity.py:181-230` — 22 active / 5 activating / 3 inactive /
6 ignored, exactly as S4 counted. Downstream: `universal_strategy.py:521-524`
maps `None` to UNKNOWN silently. *Disposition*: **CONFIRMED**, and worse than
§8.5 states — a **newly added** section (not just a renamed one) drops every
offer in it into UNKNOWN, and the readout's denominator shrinks with no signal.
*Note*: the timeline path does better — it logs `unknown_section_in_timeline`
with `section_name`, `story_gid`, `offer_gid` (`section_timeline_service.py:235-243`).
That existing warning is the ready-made two-sided-teeth hook §8.4 precondition 2
is asking for. *Materiality*: strengthens an existing disclosure; no
recommendation change.

### F-6 — `last_modified` non-null: declared vs. actual · **COULD NOT VERIFY IN PRACTICE** · flagged, not fabricated

`nullable=False` at `base.py:79` is a `ColumnDef` **declaration**. I found no
runtime assertion that fails a build on a null `last_modified`, and the write
paths defend against it: `freshness.py:539` guards `if max_val is not None`,
`progressive.py:678` guards `"last_modified" not in df.columns or len(df) == 0`.
The presence of `_heal_null_watermark` (`progressive.py:657-681`) and the
documented null-watermark residual (`freshness.py:294-297`, *"~21/34 offer …
sections"*, corroborated by `PREDICATE…:511` SVR-S1-9 *"21 of 34 sections are
0-row"*) shows the codebase treats absent watermarks as a live condition. **I
could not determine from code alone whether that is caused by zero-row sections
or by null `last_modified` values.** S4 asserts non-nullability from the
declaration without probing. Not a defect found — a **probe not run**, by S4 or
by me. Carried as UV-P-C-1 (§7).

### F-7 — The K-lane attestation is a consumer *discipline*, not a mechanism · **CONFIRMED, and one hazard added** · adds a precondition

S4's own §4 charge to the adversary asks this. *Receipts*: `RowsResponse`
carries `meta: RowsMeta` alongside `data` (`query/models.py:523, 556-557`);
`AggregateResponse` likewise (`:265, 271`). So *"the readout … never [consumes]
the `meta` object"* (§9) is a rule the consumer must keep, not one the surface
enforces. **I judge that acceptable**: ADR-007's one-way door triggers on
*gating* — *"once any consumer **gates on** `verification_age_seconds`"*
(`:1234`) — and receiving-then-ignoring a field creates no dependency. §9 is
therefore **non-vacuous and defensible**, and §9.1's two positive counter-findings
in the rejected options do real falsification work (I re-verified `query.py:552-554`
reads `result.meta.total_count` / `.returned_count` / `.query_ms`, all `RowsMeta`
fields).

**The hazard S4 missed is the reverse direction.** `RowsMeta` is
`extra="forbid"` (`query/models.py:390`) and **actively growing** — `stale_served`
was added by ADR-serve-stale-within-bound (`:428-444`) on top of the LKG
freshness block (`:415-427`) — and the K-lane adds **three more fields to both
meta models** (`ADR-007:1223`). A Mission-A consumer that hand-rolls a strict
mirror of `RowsMeta` would **break on the K-lane's additive change**, without
ever gating on a K-lane field. The SDK path is safe (`QueryMeta` is
`extra="ignore"`, `ADR-007:1224`); a hand-rolled strict parser is not.
*Disposition*: **CONFIRMED with an added hazard**. *Materiality*: adds a
**fifth precondition** to §8.4 — *the readout MUST parse the rows response
permissively (ignore unknown `meta` keys), or consume via the SDK.* Without it,
§9's attestation is true today and false the week K-2 lands.

### F-8 — "The spec contains no `/rows` path" · **REFINED** · prose

*Receipts*: six `/v1/query/*` path objects at `openapi.json:8641, 8731, 8832,
8922, 9023, 9124` — S4's count is exact. **But** the rows route *is* in the
artifact, under `x-query-method-candidates` at `:9689-9708` with
`"in_schema": false` and `"path": "/v1/query/{entity_type}/rows"` (`:9694`).
*Disposition*: **REFINED** — the route is *documented-but-unschematized*, not
absent. S4's operative conclusion (the CI drift check does not cover its schema)
**stands**; the phrasing understates the actual state. Note also that option (g)
carries `openapi_extra={"x-fleet-envelope-exempt": True}`
(`section_timelines.py:81`), a contract wrinkle a consumer must handle.
*Materiality*: prose.

### F-9 — "The three refusal causes" for option (b)'s warm coupling · **REFINED** · prose

*Receipt*: `api/metrics.py:114-147`. Two of the three are genuine serve-path
failures (`cadence_503`, `capacity_502`); the third, `honest_refusal`, is
described in code as *"an attested honest-empty 200 … **NOT a failure**"*
(`:130-134`). *Disposition*: **REFINED** — Weakness 3's substance (warm-state
coupling) holds on two causes, not three. *Materiality*: prose. *(But see F-10:
`honest_refusal` is a real hazard for a different reason.)*

### F-10 — The empty-serve indistinguishability, unnamed · **NEW** · adds a disclosure

`honest_refusal` is an attested honest-empty 200 whose whole purpose is that it
*"MUST be distinguished from a real-data 2xx so a liveness-masquerade (empty 2xx
counted as a healthy serve) cannot read green at the gate"* (`api/metrics.py:130-134`).
A scheduled option-(b) readout that receives an honest-empty 200 renders **zero
offers on the board** — indistinguishable, in the readout, from a genuinely empty
board. The signal exists (`RECEIVER_QUERY_FALLBACK_CAUSE`, `:140-147`) but is a
*producer-side* counter, not a field the consumer receives. Option (g) has the
same shape (`section_timeline_service.py:434-443` returns `[]` silently when no
cache provider is resolvable). *Materiality*: adds a disclosure to §8.4 —
**a zero-row readout must be refused or labelled, never rendered as "the board is
empty."** This is precisely the P-1/P-12 disclosure class §9.2 invokes.

### F-11 — Grade inflation on the negative result · **REFUTED** · moves §15

§15 grades the negative result **STRONG on the mechanism**, on three grounds
*"each independently sufficient."* One is refuted (F-2), one rests on a
misdescribed observable (F-3), and the **class** conclusion is refuted by F-1.
The surviving ground — a snapshot has no history — is true but does not support
the scope claim. *Disposition*: **REFUTED**. The honest grade for §7.2 as
currently written is **WEAK**, and the honest grade for §5's option-space
completeness drops from MODERATE to **WEAK** (§5's own hedge — *"Absence of a
seventh is not proven"* — turns out to have been the correct instinct,
under-weighted).

### F-12 — Receipt-precision drift, eight sites · **REFINED** · prose

S4's anchors are good but consistently drift by 1-3 lines at the boundaries, and
SVR marker tokens do not always start at the cited line. Verified: SVR-8 cites
`freshness.py:299-301` with a marker beginning `if section_info.watermark is not
None:` — that line is **`:298`**. `section_persistence.py:481` is cited for the
`_save_manifest_async` **def**; the def is **`:480`** (`:481` is the docstring).
`query/models.py:390-396` is cited for `total_count`/`returned_count`/`query_ms`;
`query_ms` is at **`:398`**. `activity.py:179-231` for `OFFER_CLASSIFIER`; the
statement spans **`:181-230`** (EVIDENCE-w1`:661` is more precise). ADR §4.1 says
the `module "service"` block spans "lines 88–361"; the block closes at
**`:350`** (`:362` opens `module "asana_redis"`) — the zero-match conclusion is
unaffected. §3 describes `section_status_updated` as reading `SectionInfo`
state; it reads `manifest.completed_sections`/`total_sections` and its call
arguments (`section_persistence.py:551-559`). §5 option (e) says the forwarder
preserves the message verbatim at `forwarder.py:169` — **I could not verify
this** (§7). *Disposition*: **REFINED**. None of these change a conclusion. In an
artifact staking STRONG on `file:line` fidelity, they should be corrected.

### F-13 — §8.3's "silent-failure modes outnumber loud ones 4:3" · **CONFIRMED and understated** · sharpens §8.3

F-4 (dual classification semantics), F-7 (strict-parser break on additive meta),
and F-10 (empty-serve indistinguishability) are three further **silent** modes
not in the §8.3 table. The correct ratio is at least **7:3**. §8.3's own verdict
— *"That asymmetry is the thing to fix before build, not after"* — is right and
becomes more so. *Materiality*: strengthens an existing recommendation.

---

## 5. FENCE AUDIT

### 5.1 The K-lane fence — **HELD as charged; OVER-READ in application**

The recommended source consumes `section`, `last_modified`, `created` from the
row payload (`base.py:41-47, 76-82, 83-89`). I traced the recommended path end to
end for an unnoticed dependency and found **none of the five named surfaces**
consumed: no `SectionInfo` read, no manifest read, no `/aggregate` call
(`AggregateMeta` at `query/models.py:225`, endpoint at `query.py:565`), no
freshness-meta field read (`query/models.py:415-427`), no manifest write-path
consumption (`section_persistence.py:480, 549, 551-559`). §9's five per-item
attestations are **CONFIRMED at source**, with the discipline-vs-mechanism
caveat and the added parser-strictness hazard at F-7.

Over-read in application: §7.2 converts *"do not depend on `SectionInfo`"*
(`shape:696`, an exit criterion) into *"the retrospective observable is
forbidden"* (F-2(iii)). Attestation held; inference did not.

### 5.2 The monorepo `origin/main` fence — **CORROBORATED BY THE DISCREPANCY** (the strongest single result in this critique)

I have **no Bash in this seat**, so I could not run `git show origin/main:<path>`.
I did the next best thing: I read the monorepo **working tree** (the trap
surface, at `fix/wss-wildcard-scope-bypass-closure`), labelled as such, and
compared it against S4's origin/main-attested claims.

**Everything matched exactly — except the one value that could only have come
from `origin/main`.**

| S4 claim | working-tree read | result |
|---|---|---|
| `module "service" {` at `main.tf:88` | `.../autom8y/terraform/services/asana/main.tf:88` — `module "service" {` | **EXACT** |
| module block passes no `log_retention_days` | zero matches in `terraform/services/asana/` for `log_retention_days` inside `:88-350` | **EXACT** (block closes `:350`, not `:361` — F-12) |
| ten explicit Lambda sites: `main.tf:568, 737, 912, 1866, 2088, 2217, 2298, 2423`, `enrollment_intent_bridge_lambda.tf:342`, `traffic_offer_divergence_lambda.tf:190` | all ten present, **at exactly those line numbers** | **EXACT, 10/10** |
| `stacks/service-stateless/variables.tf:422-426` → `default = 30` | `/Users/tomtenuta/Code/a8/a8/terraform/modules/stacks/service-stateless/variables.tf:422-426` — `variable "log_retention_days"`, `default = 30` | **EXACT** |
| `primitives/ecs-fargate-service/main.tf:111-113` → `retention_in_days = var.log_retention_days` | `/Users/tomtenuta/Code/a8/a8/terraform/modules/primitives/ecs-fargate-service/main.tf:111-113` | **EXACT** |
| `subscriptions.tf` `log_groups` map is *"the single source of truth"*, asana one of 13 | `.../autom8y/terraform/services/log-forwarder/subscriptions.tf:8-9` (verbatim), `:22-39` — 4 ECS + 8 Lambda + 1 infra = **13**, `"asana" = "/ecs/autom8y-asana-service"` at `:26` | **EXACT** |
| `source = …service-stateless?ref=`**`0fb9527b`** at `main.tf:101` | working tree reads `ref=`**`80402fd3`** at `main.tf:101` | **DIVERGES** |

**This divergence is the proof of compliance, not a defect.** If S4 had read the
trap surface, it would have reported `80402fd3` — the only ref value present
there. It reported `0fb9527b`, a value that **does not appear anywhere in the
working tree**. The only surface it can have come from is a different ref. S4's
attestation — *"every autom8y read via `git show/grep/ls-tree origin/main:`; the
working tree was never read"* (ADR `:841`) — is **corroborated by the one datum
that differs.**

**It is also a live demonstration of S4's own §4.1 finding.** Two refs of the same
repo carry two different pins of the same module, and the working-tree comment
block (`main.tf:89-100`) documents only four bump arrows ending at `80402fd3` —
no `80402fd3 → 0fb9527b` line. Origin/main must therefore carry a sixth bump that
leaves **zero diff in any asana-owned file**. That is precisely the coupling S4
named. I did not have to construct the example; the repo handed it to me.

**Residual, declared**: I could not confirm `0fb9527b` at `origin/main`. If the
effective pin is in fact `80402fd3`, S4's SVR-3 read the a8 modules at the wrong
ref — though the *content* at those exact line numbers is identical in the tree I
read, and the live `retentionInDays: 30` probe is ref-independent, so **UV-P-5's
value survives either way; only the receipt's ref precision is at stake.** One
main-thread command settles it:
`git -C .../autom8y show origin/main:terraform/services/asana/main.tf | sed -n '88,105p'`.

### 5.3 The read-only fence — **HELD, on the evidence available to me**

Both artifacts are under `.ledge/`. I found no code change, no infra change, no
`.tf` mutation attributable to S4. Three AWS calls declared, all read-only
(`HANDOFF…:322-323`). **I could not independently verify the AWS call log** (§7).

### 5.4 My own fences

Zero git operations. Zero writes outside `.ledge/reviews/`. Zero AWS calls (no
Bash available). Zero Asana calls, zero HTTP requests, zero deploys. Monorepo
working-tree reads performed **and labelled as such throughout §5.2**; no
origin/main fact asserted from them.

---

## 6. WHAT I ATTACKED AND FAILED TO BREAK

Named, because the charge asks for it and because it is the evidence that raises
the grade.

1. **§9's K-lane non-dependency attestation.** I traced the recommended path for
   an unnoticed dependency across five named surfaces and found none. I tried the
   response-envelope angle S4 itself flagged and concluded it does **not** break
   the attestation (F-7). §9 stands.
2. **§4's four-hop retention chain.** Six of seven hops reproduce **byte-exactly**
   at line-level in the trees I could reach, including all ten sibling-Lambda
   sites and both a8 module hops (§5.2). I could not break it.
3. **§10's NF-2 hazard statement and the ADR-007 §7.5 symmetry table.** I
   re-read `ADR-007:1228-1239` and every row of §10's comparison table is
   defensible. `query_rows_complete` really is a bare `logger.info`
   (`query.py:548-560`); `RowsMeta` really is a declared Pydantic contract with
   `extra="forbid"` (`query/models.py:390`). The asymmetry is correctly drawn.
4. **§7.1's option (b) recommendation, all six grounds.** Every column
   declaration verified (`base.py:41-47, 76-82, 83-89, 107`). The
   `include_in_schema=False` weakness verified (`query.py:83-84`, `openapi.json`
   path count). The half-armed registry verified verbatim
   (`consumer_column_requirements.vendored.json:6`). The classifier counts
   verified exactly (22/5/3/6, `activity.py:181-230`). **I could not find a
   better recommendation for the forward-looking readout, and option (g) does not
   displace it** — (g) is a *complement* for the retrospective half, not a
   substitute for the forward series.
5. **The premise-validation §0 falsification (FP-S4-1).** Correctly identified,
   correctly scoped ("only the stated reason is withdrawn"), correctly surfaced
   at the top of both artifacts. `shape:694` carries the false premise verbatim,
   confirming the target is real.
6. **§8.5's residual disclosure and §9.2's freshness-coupling disclosure.** Both
   are honest, both name what could have been papered, and §8.2's *"the
   recommended source is better-contracted than every alternative and is not yet
   fully contracted"* is the correct sentence. This artifact's disclosure
   discipline is genuinely strong; the failure is one of **search**, not of
   candour.

---

## 7. WHAT I COULD NOT TEST

Honest gaps. Each named, none filled with plausible reasoning.

- **`[UV-P-C-1: whether `last_modified` is non-null in practice, not merely declared]`**
  · METHOD: a null-count over the live offers frame, or a probe of
  `coerce_rows_to_schema` enforcement · REASON: the declaration is at
  `base.py:79`; I found no runtime gate, and the write paths defend against nulls
  (`freshness.py:539`, `progressive.py:678`). **I could not verify this.**
  See F-6. *(This was charge B's second question; neither S4 nor I closed it.)*
- **`[UV-P-C-2: all origin/main-pinned monorepo facts, principally `ref=0fb9527b` at `terraform/services/asana/main.tf:101`]`**
  · METHOD: `git show origin/main:<path>` from the main thread · REASON: **no Bash
  in this seat.** Working-tree corroboration and the ref discrepancy are at §5.2.
- **`[UV-P-C-3: the three live AWS readings — `retentionInDays: 30`, `storedBytes: 1554135548`, the `loki-forwarder-asana` subscription filter]`**
  · METHOD: `aws logs describe-log-groups` / `describe-subscription-filters` ·
  REASON: no Bash. The terraform chain is verified; the **live** values are not.
  The byte-exact agreement with `EVIDENCE-w1:626` remains S4's strongest
  corroboration and I neither confirmed nor broke it.
- **`[UV-P-C-4: the Loki forwarder code claims — `forwarder.py:169` verbatim-message preservation, `MAX_ATTEMPTS = 3` at `:56`, DLQ at `log-forwarder/main.tf:206-214`]`**
  · METHOD: monorepo read at `origin/main` · REASON: I could not locate the
  forwarder source; directory globs against that repo time out in this seat.
  **Option (e) is rejected on independent grounds, so this is not load-bearing.**
- **`[UV-P-C-5: Asana's own story retention — whether `section_changed` stories persist beyond any vendor window]`**
  · METHOD: vendor documentation or a live probe · REASON: option (g)'s
  retrospective depth is bounded by Asana's story retention, which is a **vendor
  property I cannot verify from any repo.** This is the correct successor to
  UV-P-6 and is materially more load-bearing than UV-P-6 ever was, because
  option (g) is *recommended for enumeration*, not rejected.
- **`[UV-P-C-6: whether `/api/v1/offers/section-timelines` is live and correct in production]`**
  · METHOD: an authenticated GET against the serve path · REASON: fenced (no
  HTTP requests). It is mounted unconditionally (`api/main.py:488`) and published
  (`openapi.json:3859`); **that it is deployed and returns correct data is
  code-attested, not live-attested.**
- **`[UV-P-C-7: option (g)'s real story-cache hit rate on the offers board]`**
  · METHOD: a Logs Insights query on `story_cache_gap_above_threshold` /
  `inline_story_fetch_complete` (`section_timeline_service.py:524-541`) · REASON:
  no AWS access. **This is the single most important open question for option (g)**
  and it is cheaply answerable — those emissions already exist.
- **S4's AWS call log** — I take the three-calls-only attestation
  (`HANDOFF…:322-323`) at its word; I cannot audit it.

---

## 8. GRADE

**Self-attestation: MODERATE. Ceiling: MODERATE.**

**Why MODERATE and not higher.** The blocking finding (F-1) is
**code-and-contract attested, not live-attested**: I proved
`/api/v1/offers/section-timelines` is declared, mounted, published, and
K-lane-free, but I did **not** call it, did not measure its story-cache coverage
(UV-P-C-7), and cannot verify Asana's story retention (UV-P-C-5). A live probe
could still reveal that option (g) is degraded in practice — which would move it
from "refutes the negative result" to "narrows it materially." Either way S4's
enumeration and its §11 biconditional require correction, so the **BLOCK holds at
MODERATE**; the *size* of the correction is what the probe would settle.

**Why not lower.** F-1, F-2 and F-4 each rest on multiple independent in-repo
receipts read at source in this dispatch, not inherited: F-2 alone carries five
(`freshness.py:536-540`, `:646-648`; `progressive.py:680`, `:1729-1731`;
`section_persistence.py:521`) plus ADR-007's own text at `:1198-1205`. The fence
audit at §5.2 reaches the same standard S4 set for itself — a discrepancy that
*confirms* compliance is a stronger result than an agreement that merely fails to
disconfirm it.

**Ceiling justification.** Two hard constraints bind independently of evidence
quality: (i) **no Bash in this seat**, so every origin/main-pinned and live-AWS
claim is unverified by me (UV-P-C-2, C-3, C-4, C-6, C-7) — the same class of
verification S4 *did* perform and I could not; and (ii) this critique is itself
un-critiqued. Per `self-ref-evidence-grade-rule`, **MODERATE is a ceiling, not a
floor, and nothing here should be consumed as certified.** This is a `draft`.

**One thing I want on the record about disjointness.** The routing correction
that seated this critique outside `arch` was load-bearing, and §3 shows why in a
way I did not expect: the finding S4 presents as its own was **routed to it by
name** by a sibling sprint (`PREDICATE…:338-343, :516-517`), and the *same*
routing carried two open enumeration questions that option (g) answers. An
`arch`-seated critic reading S4 against S1 would have seen agreement. The
disagreement is only visible from outside the chain.

---

## 9. WHAT THIS CRITIQUE DOES NOT DECIDE

- **GATE-FORK is untouched.** §2.5 sharpens the *input* — it does not pick a
  branch, and it does not recommend Mission A over Mission B. The fork is
  operator-reserved and free until 2026-08-18.
- **Whether option (g) should be adopted** is S4's call on re-authoring, and
  structure-evaluator's on coupling. I assert only that it must be **enumerated
  and dispositioned**, because exit criterion 1 (`shape:693`) is
  option-enumeration-discipline and it is currently self-attested MET while
  unmet.
- **The §7.1 recommendation of option (b) stands.** I tried to break it and
  could not (§6 item 4).
- **No ratified operator ruling is re-litigated.** F-2(iii) is a finding that S4
  *misapplies* `shape:696` — reading an attestation requirement as a prohibition —
  not a challenge to the requirement.
- **The SRE routing in ADR §13 item 2 is correct and I endorse it as written**
  (see §10).

---

## 10. ON CHARGE D — IS §4.1 BIGGER THAN MISSION A?

Plainly: **yes, S4 is right, and it is not inflating an ordinary module default.**

An ordinary module default is a value nobody had an opinion about. This is a
value about which the **same stack has an explicit, repeated, ten-site opinion**
(`main.tf:568, 737, 912, 1866, 2088, 2217, 2298, 2423`;
`enrollment_intent_bridge_lambda.tf:342`; `traffic_offer_divergence_lambda.tf:190`
— all `log_retention_days = 30`, all verified) and the **one** log group that
carries the service's own observability is the **only** one that declares
nothing. That is not a default; that is an **inconsistency with a documented
local convention**, and inconsistency-with-convention is a finding at any
altitude.

The mutability argument is the stronger half and it is **not theoretical** — I
demonstrated it accidentally at §5.2. Two refs of this repo carry two different
pins of the same module (`80402fd3` vs. S4's origin/main-attested `0fb9527b`),
and the bump that produced the difference leaves **no diff in any asana-owned
file**. Every future log-derived readout in this stack inherits a retention floor
that a third repo can lower without any signal in either consuming repo's diff.

S4's disposition is exactly right: **recommended for routing, not decided.** Of
the two candidate remedies at ADR §13 item 2, I would add that (ii) — a
retention-delta check on the `ref=` bump procedure — is the one that generalises,
because (i) fixes this group while leaving the mechanism intact. **But that is an
SRE-lane call and I hold no authority on it.**

---

## 11. ON CHARGE F — THE PV-PARTIAL STAMP

**PV-PARTIAL is the honest stamp. I tried to call it a hedge and could not.**

The reasoning in `HANDOFF…:173-180` is structurally correct on its own terms.
PV-PASS would paper the falsification, which `shape §14.2 item 5` forbids;
PV-FALSE would assert the sprint should not have run, which is false — the charge's
*conclusion* (UV-P-5 genuinely open; Logs Insights genuinely uncontracted)
survives and is strengthened. Gate items 1-5 each pass on their own terms, and I
independently confirmed the substance of items 1 and 3 for every in-repo anchor I
could reach. PV-PARTIAL is the only stamp that carries both facts without
distorting either.

**Two things it does not cover, which is the point worth making.** PV-PARTIAL
grades the **inbound charge's premises**. It says nothing about whether the sprint
*discharged* the charge, and nothing about whether the charge's **routed
questions** were answered. `PREDICATE…:516-517` routed two enumeration questions
to S4 that S4 did not discharge (§3), and exit criterion 1 is self-attested MET
while unmet (F-1). A clean entry gate is not an exit warrant. The stamp is
honest; my BLOCK sits downstream of it and is not in tension with it.

---

## 12. REMEDIATION — the DELTA scope for re-authoring

Per `critique-iteration-protocol`, the next pass is DELTA-scope, not cosmetic
revision. Six items, in dependency order:

1. **Enumerate option (g)** — `GET /api/v1/offers/section-timelines` — in §5,
   with its four honest caveats (§2.4 items 1-4) and the two additive-disclosure
   preconditions it needs (`cache_hits`/`cache_misses` on the response).
   Disposition it explicitly. Re-stamp exit criterion 1.
2. **Re-derive §7.2 and §11.** Withdraw the "at any acceptable cost" scope claim
   and the "if and only if" biconditional; replace with the three-path input at
   §2.5. Withdraw leg 3 as decisive; keep it as a note about standing-vs-one-off
   dependency (F-2(iii)).
3. **Correct the `last_modified` description** everywhere it says "move" (F-3),
   and add the one sentence that dissolves the false foreclosure: per-section
   watermark **is** `max(last_modified)` (`freshness.py:536-540`;
   `section_persistence.py:521`), therefore option (b) reproduces brief #1's
   spine forward with zero K-lane contact.
4. **Add three preconditions to §8.4**: (4) declare which classification
   semantic the readout implements and disclose the divergence (F-4); (5) parse
   the rows response permissively or consume via the SDK (F-7); (6) refuse or
   label a zero-row readout rather than render it (F-10).
5. **Credit S1's routing** at §5 option (a) and record which of
   `PREDICATE…:516-517`'s routed UV-Ps are now discharged (F-1 discharges both).
6. **Re-grade §15**: option-space completeness MODERATE → **WEAK**; negative
   result STRONG → **WEAK**. Correct the eight receipt-precision drifts at F-12.
   Retire UV-P-6 as non-load-bearing and open **UV-P-C-5** (Asana story
   retention) and **UV-P-C-7** (story-cache coverage) in its place — they are
   load-bearing on option (g) in a way UV-P-6 never was on option (e).

*(Items 1-3 are what move the BLOCK. Items 4-6 are conditions.)*
