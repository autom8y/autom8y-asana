---
type: decision
artifact_type: ADR
adr_id: ADR-007-verification-axis-gate
artifact_id: ADR-007-verification-axis-gate-2026-08-12
title: "The offers readiness gate gates on VERIFICATION RECENCY; content age rides as first-class disclosure"
status: ratified-provisional  # see RATIFICATION RECORD; was draft
phase: design
authored_by: architect
authored_on: 2026-08-12
crusade: offers-freshness-axis-contract
initiative: option4-verification-axis-gate
session: session-20260811-115247-a1ccd942
rite: 10x-dev
charter: RULING-operator-option4-interview-2026-08-12.md (12 rulings; "Nothing not explicitly ruled here may be recorded as decided.")
supersedes: ADR-006-freshness-equals-verification-recency.md
amends: CONTRACT-offers-freshness-axis-frozen-2026-08-11.md §1.2 (in place, per [A-2026-08-03] precedent)
producer_code_basis: "autom8y-asana working tree == origin/main @4129ae7e (verified clean for src/ at authoring time)"
consumer_code_basis: "autom8y @origin/main = 6fc556d8 (ALL consumer reads via `git show origin/main:<path>`)"
evidence_ceiling: MODERATE (self-referential design authorship per self-ref-evidence-grade-rule); the empirical legs carry their own grades inline
ratification_pending:
  - "§3 — the CONTRACT §1.2 amendment TEXT (operator signature item i)"
  - "§4 — V = 14 400 s and its derived abort line 28 800 s (operator signature item ii)"
decides_nothing_beyond_the_rulings: >-
  Every construction here traces to a numbered operator ruling (P-1..P-12) or is
  explicitly flagged OPEN at §8. Where this ADR extends a ruling into a design
  consequence the ruling did not spell out, the extension is marked
  [DESIGN CONSEQUENCE] and stated as a recommendation the operator may reject
  without reopening the ruling.
scope: DESIGN AND GOVERNANCE ONLY — no production code authored, no infra mutation, no deploy, no threshold moved, no Asana call, no S3 read, no AWS call.
---

# ADR-007 — The offers gate gates on verification recency

> **How to read this.** §1 is the situation. §2 is the decision. §3 and §4 are
> the two blocks the operator signs. §5 disposes of ADR-006 decision by
> decision. §6 is the kill-switch register. §7 is the build plan. §8 is
> everything still open — including two items I found unruled and one
> ambiguity in a ruling's own wording.
>
> **Two corrections to inherited premises, surfaced rather than absorbed**, both
> found by direct read at authoring time and both material:
>
> - **[CORRECTION-1]** The design annex's §3.5 "one path that must be closed"
>   — the synthetic-`now()` hydration fallback — **is already closed at producer
>   HEAD.** `#338` (`2601c8c5`, "fix(cache): decay null watermarks instead of
>   now()") landed after the annex's `cc20772e` basis. The named refusal it asked
>   this ADR to carry is now a *preservation* obligation, not a new fix. §2.6.
> - **[CORRECTION-2]** The annex's consumer citations (`combine_offer_axis`,
>   `asana_freshness`, `autom8y-core 4.14.0`, `QueryMeta` axis fields) **do not
>   resolve in the autom8y working tree as checked out**, which sits on branch
>   `fix/wss-wildcard-scope-bypass-closure` @ `1bb00c3c` — *not* an ancestor of
>   `origin/main`. Every one of them **does** resolve at `origin/main` =
>   `6fc556d8`. All consumer anchors in this ADR were re-verified via
>   `git show origin/main:<path>`. Anyone re-checking this ADR against a local
>   checkout will get false negatives unless they pin `origin/main`. §8 O-7.

---

## §1 — Context

### 1.1 The gate that was falsified

The deployed `offers` readiness gate asks *"how old is the newest fact I hold?"*
and refuses when the answer exceeds `3 600 s` (abort `7 200 s`). W-1 measured
that question over **29 days and 175 organic ticks** and found the deployed
threshold passed **0/175**. Recovering a 95 % not-ABORT rate on that axis
demands an abort line of **47.6 h** — **6.0×** the consumer contract's own 8 h
tolerance.

> **W-1 pointer (the falsification of record):**
> `.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md`
> — 10 239 probe records, 29 days, three live ticks reconstructed to ±0.000000 s.
> **[STRONG]**, rite-disjoint (eunomia/verification-auditor).

The falsification is structural, not a tuning miss. The content axis's governing
quantity is *"how long may a human go without editing an offer?"* — p90 **48.4 h**,
max **88.3 h** in 29 days with no holiday in the window. The platform neither
owns nor forecasts that quantity, so **no threshold on it is both honest and
usable.**

### 1.2 The wave close

`RULING-operator-wave-close-realized-mechanism-2026-08-12.md` closed the
offers-freshness-axis-contract wave at the terminal rung **`REALIZED-MECHANISM`**
— the content-axis mechanism is realized at STRONG on two consecutive qualifying
organic ticks, cross-corroborated to the microsecond
(`.ledge/reviews/ATTEST-rel6-realize-offers-content-axis-2026-08-12.md` §7).
**`PASS-REALIZED` was not claimed**; the substrate-stale finding stands. The
ruling explicitly severed the *gate-quantity* question from the wave and opened
it as this initiative, with its full decision stack reserved to the operator
interview.

That severance is why this ADR exists: the K-lane content axis is **built,
correct, and on the wire** — and it still cannot gate, because the quantity it
measures is unthresholdable. Nothing here retracts the K lane. It re-points the
*gate* while leaving the content axis standing as the source-attested
cross-check (P-1).

### 1.3 The twelve rulings that are this ADR's charter

`RULING-operator-option4-interview-2026-08-12.md`, three AskUserQuestion batches,
2026-08-12 ~10:30–11:05Z. Binding note carried verbatim: *"Nothing not explicitly
ruled here may be recorded as decided."*

| # | Ruling | Where it lands in this ADR |
|---|---|---|
| **P-1** | Gate quantity: **both, disclosed separately** — gate on verification recency; content age rides as first-class disclosure, never conflated | §2.1, §2.7, §3 |
| **P-2** | Build appetite: **full chain, one initiative** — producer → SDK → consumer, K-lane sequenced, B-block preconditions gated inside | §7 |
| **P-3** | Interim posture: **accept until replaced** — honest aborts continue with NO clock; the successor's landing is the only exit | §7.0, §8 O-5 |
| **P-4** | "Done" bar: **observability truthful first** — stage 1 truth; stage 2 statistical bar (≥95 % healthy-pass / ≤8 h detection over a soak window) | §7.1, §7.6 |
| **P-5** | `min()` scope: **all classified sections** — verified-empty is still verified; zero-row sections must be stamped and included. **Stamp-eligibility producer fix is a HARD PRECONDITION of gate-live** | §2.3 (the load-bearing section), §7.2 |
| **P-6** | Backfill: **close at source, then refuse** — fetch-completion stamps honestly; thereafter unstamped = unknown = refuse | §2.4, §5 Decision-6 |
| **P-7** | Stage-1 authorizations (all four) — AL-5 description, AL-5 flapping, latency-truth + P9-FIX-4, stray-publish routing | §7.1 |
| **P-8** | ADR-006: **supersede into new ADR** — one principle, both surfaces | §5 (this document) |
| **P-9** | Falsification register: **3 kill-switches**; "eligibility unfixable" explicitly NOT registered | §6 |
| **P-10** | D-5b content-threshold afterlife: **HOLD (parked)**, revisit trigger = gate-live | §8 O-1, O-2 |
| **P-11** | DEFECT-1/2: **G-1 in design; defects parallel** | §2.5, §7.4 |
| **P-12** | Naming fence: **RATIFIED as proposed**; `content_age_seconds` immutable; no polymorphism; no coalescing. **HELD-2 CLOSES** | §2.7, §3 clause NON-ALIASING |

**Divergences from the architect's recommendations, recorded once and not
re-argued** (per the interview's own protocol note): P-3 (operator chose no
time-box), P-9 (operator registered three of four), P-10 (operator parked rather
than retired). This ADR implements the operator's rulings, not the
recommendations they diverged from.

---

## §2 — Decision

### 2.1 The gate predicate (P-1)

For the `offers` source, per tick, per constituent:

```
PASS   iff   verification_age_seconds ≤ V
       AND   returned_count == total_available                  # completeness proven
       AND   verification_age_seconds is not null               # axis provable
       AND   verification_backfill_used is False                # §2.4

WARN   iff   PASS's completeness and provability conjuncts hold
       AND   V < verification_age_seconds ≤ V × warn_multiplier # warn_multiplier = 2.0

ABORT  iff   verification_age_seconds > V × warn_multiplier
       OR    completeness is unproven or truncated
       OR    the verification axis is AXIS-NULL (declared, underivable)

DORMANT (fall back, never refuse)
       iff   the verification axis is AXIS-ABSENT
             (producer does not declare it in axes_present)
```

`content_age_seconds` **does not appear in the predicate.** Per P-1 it rides the
wire as first-class disclosure and feeds two non-gating channels: the per-tick
log line, and the anomaly rules at §2.7.

**The WARN band is inherited, not chosen.** A ruling on `V` is simultaneously and
unavoidably a ruling on the abort line at `2V`; there is no knob that moves one
without the other.

```yaml
structural_verification_receipt:
  claim: "the SDK's staleness dimension derives its FAIL boundary from threshold × warn_multiplier with warn_multiplier defaulting to 2.0, so ratifying V also ratifies an abort line at 2V"
  verification_method: file-read
  verification_anchor:
    source: "sdks/python/autom8y-reconciliation/src/autom8y_reconciliation/gate.py (autom8y @origin/main 6fc556d8)"
    line_range: "L44-L58"
    marker_token: "threshold < staleness_seconds <= threshold * warn_multiplier -> WARN"
    claim: "the abort line is not independently configurable, which is why §4 sizes both numbers together rather than picking V and discovering the abort line afterwards"
```

### 2.2 What `verification_age_seconds` means, stated honestly

> **`verification_age_seconds` = seconds since the rows in *these served bytes*
> were last confirmed to match live Asana by a successful per-section probe.**

Three things it is **not**, each of which has burned this crusade before and each
of which §3's NON-ALIASING clause forbids by name:

| It is NOT | Because |
|---|---|
| when the frame was **assembled** (`frame_built_at`) | assembly advances unconditionally — measured advancing with `fetched_rows=0` on three live builds (DIAG-S1 F1.6) |
| when a **cache entry was written** (`served_entry_stamped_at` / today's `data_age_seconds`) | process-local; a fresh ECS task reports near-zero for the substrate a long-lived task reports at 10 083 s (DIAG-S1 F3.1, CONTRACT §1.6) |
| when a row was last **edited** (`content_watermark`) | that is the content axis — the one W-1 proved unthresholdable |

The distinction that makes the referent honest is **probe-verdict gating**, not
naming discipline. The stamp advances only through a code path that required a
live Asana round-trip and a non-failure verdict.

```yaml
structural_verification_receipt:
  claim: "the verification stamp has exactly one assignment site in the build path, reachable only downstream of the PROBE_FAILED continue, the applied_gids membership test, and the null-watermark hash-only-CLEAN continue"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/builders/progressive.py"
    line_range: "L573"
    marker_token: "stamp_info.last_verified_at = now"
    claim: "a build in which no section successfully probed writes zero stamps and the axis ages — which is exactly the discrimination frame_built_at's unconditional clock read cannot make, and is the mechanical answer to 'verification recency is just BUILD-axis with extra steps'"
```

### 2.3 The reduction denominator: `min()` over ALL classified sections (P-5)

**This is the section that changed most under operator ruling, and it is the one
that most changes the design's risk profile. It should be read twice.**

P-5 ruled: *"All classified sections — verified-empty is still verified; zero-row
sections must be stamped and included."*

**[DESIGN CONSEQUENCE — the annex's reduction is superseded by this ruling.]**
The design annex §3.4 Hop-4 proposed reducing over `served_sections` = *the
section names present in the rows THIS response returns*. Under P-5 that is
**wrong by construction**: a classified section with **zero rows** contributes no
rows, therefore never appears in `served_sections`, therefore can never enter the
`min()` — which is precisely the population P-5 rules must be included.

The corrected reduction:

```
classified   = CLASSIFIERS[entity_type].sections_for(<the classifications in THIS request>)
verified_at  = min(verified_by_section[s] for s in classified)
backfill     = any(s in verification_backfill_sections for s in classified)
```

Three consequences, each stated so nobody discovers them later:

**(a) The producer must consult its own classifier at emit time.** The annex
claimed *"No `billable_sections()` filter is needed on the producer side at all —
the classification filter in the request performs the scoping."* Under P-5 that
claim no longer holds: row-filtering scopes the **rows**, but the `min()`
denominator is a **name set**, and a zero-row name is invisible to a row filter.
The producer resolves the name set from `CLASSIFIERS[entity_type]`, which it
already owns and already uses. **This is producer policy, not consumer policy** —
the §3.2 denominator correction (`active_sections()` excludes ACTIVATING) is
satisfied because the request's classification is the input, not a hardcoded
group.

```yaml
structural_verification_receipt:
  claim: "the metrics-CLI reader scopes to the classifier's ACTIVE group alone, which excludes the ACTIVATING cohort that is binding for the offers gate — so the serve-path reduction must NOT reuse that denominator"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/metrics/freshness.py"
    line_range: "L785"
    marker_token: "active_names = classifier.active_sections()"
    claim: "reusing this reader unchanged would compute recency over a section set omitting ACTIVATING entirely — the cohort whose watermark advanced 26 times in 29 days against ACTIVE's 92 — producing a signal that reads healthy while the binding cohort is stalled"
```

```yaml
structural_verification_receipt:
  claim: "a correctly-named ACTIVE+ACTIVATING accessor already exists on the classifier, so the P-5 denominator requires no new vocabulary"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/models/business/activity.py"
    line_range: "L92-L94"
    marker_token: "Section names that represent billable state (ACTIVE + ACTIVATING)."
    claim: "the producer already carries the ACTIVE+ACTIVATING name set under a name that matches the offers gate's constituents, so the P-5 denominator is a call site, not a new concept"
```

**(b) An unstamped classified name is AXIS-NULL, and AXIS-NULL aborts.** This
follows from P-5 conjoined with P-6 (*unstamped = unknown = refuse*). A
classification-scoped section carrying a null or absent stamp makes the `min()`
underivable for that response; the axis is emitted `null`, declared present in
`axes_present`, and the consumer aborts. It is **never** substituted, never
skipped, never silently dropped from the denominator.

**(c) The gate's realised pass rate is determined by stamp eligibility, not by
warm cadence.** This is the honest headline and it must not be softened. The
V-sizing evidence measures a **frame-level** quantity and reports **100 % PASS**
at `V = 14 400` over 29 days. The same corpus contains a **6.7-day window
(2026-07-28 → 2026-08-03T15:52Z)** in which 18–19 of 34 offers sections were not
stamped on any pass. Under the P-5 reduction the gate in that window would have
read up to **7.00 days** of verification age — **0/37 PASS, 0/37 not-ABORT, 21×
the abort line** — while every frame-level figure over the same window reads
100 %.

> **Both numbers are true of the same corpus.** Which one the built gate reads is
> decided entirely by whether zero-row classified sections carry stamps. That is
> why P-5's consequence clause reads *"the stamp-eligibility producer fix is a
> HARD PRECONDITION of gate-live (else permanent 0 %)"* — and this ADR treats it
> as a **blocking** precondition at §7.2, not a risk note.

**Status of that precondition at producer HEAD `4129ae7e`** — partially
discharged, and the residue is nameable:

| Eligibility hole | Status at HEAD | Disposition |
|---|---|---|
| Empty sections denied a stamp on hash-CLEAN (the 18–19 population) | **CLOSED** — FIX-1, `5d62d0b8` / PR #299, with the qa coherence premise (`rows==0 AND gid_hash==hash(∅)`) | verified in code; carried forward as §5 Decision-5d |
| `mark_section_failed` rebuilds `SectionInfo` carrying neither `name` nor `last_verified_at` — one transient failure destroys the stamp permanently | **OPEN at HEAD** | **IN this design** (§2.4); a healthy fleet reaches the unstamped state through this door, not only legacy data |
| A section fetched-but-never-probed has no stamp at all | **OPEN at HEAD** | **IN this design** — P-6 source-close (§2.4) |
| Do all 27 classified names carry stamps on prod today? | **UNMEASURED** | **B3-a**, re-scoped under P-5 at §7.2 — blocks everything |

```yaml
structural_verification_receipt:
  claim: "FIX-1's coherently-empty stamp exemption is live at producer HEAD, with the qa coherence premise requiring BOTH rows==0 and the empty-GID hash before an empty section may stamp"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/builders/progressive.py"
    line_range: "L566-L570"
    marker_token: "stamp_info.rows == 0 and stamp_info.gid_hash == _EMPTY_GID_HASH"
    claim: "the largest single stamp-eligibility hole named in the V-sizing evidence is closed in code at HEAD, which converts the 6.7-day pinned-floor scenario from a live defect into a regression the gate must be protected against rather than cured by this initiative"
```

```yaml
structural_verification_receipt:
  claim: "mark_section_failed rebuilds SectionInfo from scratch carrying neither name nor last_verified_at, so a single transient section failure destroys that section's verification stamp permanently"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/section_persistence.py"
    line_range: "L225-L228"
    marker_token: "self.sections[section_gid] = SectionInfo( status=SectionStatus.FAILED, error=error, )"
    claim: "the sibling mark_section_complete carries both fields forward (L205-L207) while this path does not, so the stamp-destruction channel is asymmetric and reachable from a healthy fleet — this is why the P-6 source-close must include stamp preservation on the failure path, not only stamping on the fetch path"
```

### 2.4 Backfill: close at source, then refuse (P-6)

P-6 ruled annex option **(iv)**. Two halves, both producer-tier:

**Half 1 — close the conflation at the source.** `written_at` conflates two
states, and one of them is honest:

| state | what `written_at` means | honest as a verification instant? |
|---|---|---|
| **(i)** section fetched in this build, never probed (cold build; recovered FAILED section; new section) | *"I fetched these rows from live Asana at this instant"* | **YES** — arguably stronger than a probe stamp |
| **(ii)** legacy manifest; written before the stamp shipped and not probed since | mutation-recency of unknown provenance | **NO** |

The fix: **a fetch IS a verification.** `mark_section_complete` sets
`last_verified_at = now` when the section was actually fetched in this build, and
carries forward only when it was not. `mark_section_failed` preserves the prior
`last_verified_at` (and `name`) instead of destroying it. After this, state (i)
is a real stamp and `backfill_used=True` means **only** state (ii).

**Half 2 — then refuse.** Thereafter, `verification_backfill_used=True` refuses
the source. Unstamped = unknown = refuse. **No `written_at` value is ever
emitted as, coalesced into, or substituted for a verification instant.**

**Accepted failure mode, stated plainly:** a section never probed since the stamp
shipped, and not fetched in the current build, refuses the offers source until
its next warm probes it. Given median warm cadence of **39 min**, that window is
short and bounded, and ADR-006 §Decision-7a already ruled that **the warm cadence
is the backfill** and no backfill job is warranted (§5 carries that ruling).

**[DESIGN CONSEQUENCE] G-3 rides.** The annex conditioned the
`VerificationSource` provenance enum (`PROBE` / `FETCH` / `BACKFILL_WRITTEN_AT`)
on option (iv) being ruled — *"it is the same edit, and an enum is strictly more
useful than the boolean."* (iv) **is** ruled, so **G-3 is IN**. The wire field
remains the boolean (§3 roster, P-12 fence); the enum is the manifest-tier
representation the boolean is derived from. It makes §2.4's conflation
self-describing rather than inferable.

### 2.5 G-1: the monotone envelope, in design (P-11)

P-11 ruled: *"G-1 in design; defects parallel."*

**G-1 — the persisted `last_verified_at` never moves backward.** A regression
event is absorbed at the producer rather than propagated to the gate.

**Why this is needed and why it is not symmetric with the content axis.** The
content axis aggregates with `max()` and is therefore *shielded* from one bad
section. The verification axis aggregates with `min()` and is therefore
*maximally exposed* to one. DEFECT-2 (a 70.9-day backward watermark jump) did not
bind under `max()`; under `min()` it is not merely unshielded, it is **attracted
to** — one regressed stamp pins the axis outright.

**The argument that must be inscribed, because a future reader will cite CONTRACT
§1.2b against it.** §1.2b's corollary explicitly **refuses** to enforce
monotonicity on the content watermark: *"enforcing monotonicity would manufacture
a ratchet that survives data deletion — a false-fresh generator."* That reasoning
does **not** transfer. A content watermark can legitimately decrease (rows
deleted). **A verification instant cannot legitimately move backward, because
time does not.** Monotonicity is a false-fresh generator on content and a
truth-preserving invariant on verification. The two are not the same rule applied
inconsistently; they are two different quantities with two different honest
treatments.

**Not in this design, per P-11 — parallel tracks:**

| track | what | why parallel |
|---|---|---|
| **DEFECT-1 root cause** (G-2: optimistic concurrency on the manifest write) | `version` compare-and-set or an S3 conditional PUT | wider blast radius than this gate (metrics CLI, resume path, checkpointing). Bundling it makes the gate change unattributable — the exact discipline the sequencing ruling protects: *never bundle the disclosure patch with a threshold move; attribution loss is permanent* |
| **DEFECT-2 root cause** | the write path that permitted a backward stamp | G-1 neutralises its *effect* on this axis; the *cause* is producer correctness |
| **ECS task-id dimension on the probe log line** | one log field | the falsifier for the DEFECT-1 mechanism diagnosis (below), which is MODERATE and inferred, not proven |

**Residual risk, named rather than discovered post-ship:** DEFECT-1's direction is
fail-STALE (a lost update discards a stamp; `min()` reads older), so it does not
block shipping — but **it caps the achievable pass rate by an unmeasured amount,
and that cap is invisible until the axis is live.** The V evidence corroborates
the mechanism directly: 15 of 684 adjacent stamp passes are <120 s apart with
**different** trace_ids, which is the read-modify-write window in which a stamp is
lost. **A logged stamp pass is therefore not proof of a persisted stamp.**

```yaml
structural_verification_receipt:
  claim: "the manifest read-modify-write cycle is serialized only by a process-local asyncio.Lock, is answered from a process-local cache that never expires, and terminates in an unconditional whole-object PUT with no precondition — so lost updates are structurally available across concurrent ECS tasks"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/dataframes/section_persistence.py"
    line_range: "L352, L453, L489, L129"
    marker_token: "self._manifest_locks[project_gid] = asyncio.Lock()"
    claim: "an asyncio.Lock is intra-event-loop; the model carries a `version: int = 1` slot at L129 that is never incremented and never compared, and the save at L489 is an unconditional save_json — so the object model has the slot for optimistic concurrency and the write path does not use it. Grade MODERATE: this is a sufficient mechanism read from code, not a proven cause of the specific alternation W-1 measured"
```

### 2.6 The named non-inheritance — now a preservation obligation

**[CORRECTION-1, restated as a decision.]** The annex asked this ADR to carry a
named refusal: the verification stamp must never inherit the S3-hydration
`watermark = datetime.now(UTC)` fallback — *"a missing `verified_at` key in the
sidecar is AXIS-NULL, never `now()`"* — because the adjacent line did exactly the
forbidden thing and the next engineer would pattern-match on it.

**That fallback is gone at producer HEAD.** `#338` replaced it with an explicit
decay anchor and a disclosure log. The refusal therefore inverts in form: it is no
longer *"do not copy the adjacent line"* but *"do not regress the adjacent line,
and apply its discipline to the new key."*

**Decision:** a missing `verified_at` key in the sidecar is **AXIS-NULL**, never
`now()`, never a decay anchor that reads as fresh, never omitted from
`axes_present` once the producer declares the axis.

```yaml
structural_verification_receipt:
  claim: "the S3 hydration path no longer substitutes now() for an absent watermark; it decays to an explicit anchor and emits a disclosure warning, and the code comment records that the pre-fix path was a synthetic-fresh generator wired into the seam's type signature"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/cache/dataframe/tiers/progressive.py"
    line_range: "L215-L228"
    marker_token: "watermark = NULL_WATERMARK_DECAY_ANCHOR"
    claim: "the annex's §3.5 'one path that must be closed' is closed at HEAD by #338, so this ADR's obligation is to preserve the discipline and extend it to the verification key rather than to introduce it — recorded because inheriting the annex's wording unchanged would have inscribed a fixed defect as an open one"
```

### 2.7 The naming fence (P-12) — verbatim, and its consequences

P-12 is **RATIFIED as proposed**, and **HELD-2 CLOSES**. The ruling's own text:

> `content_age_seconds` keeps its exact current meaning forever (result-scoped
> content age); the new axis ships as `verification_age_seconds` + `verified_at`
> + `backfill_used`; NO field ever polymorphic; NO consumer coalescing
> ("whichever is present" is forbidden). Non-aliasing clause extends to the
> verification family.

Four binding consequences:

1. **`content_age_seconds` is immutable in meaning.** It is not re-pointed, not
   widened, not made polymorphic across axes, not given a "which axis is this"
   companion. Its current referent is its permanent referent.
2. **No field is ever polymorphic.** A field carries one axis for its whole life
   or it is a new field.
3. **No consumer coalescing.** No `or`, no fallback, no "whichever is present"
   helper, no shared parse branch. A consumer that wants both handles each in a
   separately-named code path. This is CONTRACT §1.8 clause 3 applied to the new
   pair, binding for the identical reason: **an alias is how one quantity acquires
   another's guarantee without earning it.**
4. **Spelling is load-bearing.** The forbidden near-misses are enumerated in §3
   so they are refused rather than debated.

> **⚠ ONE AMBIGUITY IN THE RULING'S OWN WORDING — flagged, not resolved.** P-12
> names the third field **`backfill_used`**; the proposal it ratifies ("as
> proposed") names it **`verification_backfill_used`**. Under a fence whose first
> principle is *spelling is load-bearing*, this ADR will not silently pick one.
> This draft uses `verification_backfill_used` throughout with the architect's
> recommendation at §8 O-3, and the one-word confirmation is an operator item.

**Content age's non-gating job (P-1).** Content age earns its place on the wire by
detecting one thing the verification axis structurally cannot: **a producer that
stamps without fetching.** Two rules:

- **HARD REFUSAL (not an alarm):** `verification_age_seconds` small **AND**
  `sections_fetched < sections_total`. The producer claims recent verification
  while admitting incomplete coverage — a contradictory record, not a degraded
  read. This is the same class the consumer already refuses as a broken record.
- **DISCLOSURE + ALARM CANDIDATE:** `verification_age_seconds` small **AND**
  `content_age_seconds` at an extreme percentile of its own history. Usually
  legitimate quiescence — which is exactly why it must **not** gate — but also the
  signature of a stamp-without-fetch defect. Per-cohort disclosure line and an
  operator-visible counter.

```yaml
structural_verification_receipt:
  claim: "the consumer's offer-axis combiner already refuses a self-contradictory record — a GATE verdict carrying no age — rather than inventing the missing quantity, so the §2.7 hard-refusal rule extends an existing refusal shape rather than minting one"
  verification_method: file-read
  verification_anchor:
    source: "services/account-status-recon/src/account_status_recon/readiness.py (autom8y @origin/main 6fc556d8)"
    line_range: "L290-L296"
    marker_token: "A GATE verdict carrying no age is a BROKEN RECORD -- the verdict contradicts itself."
    claim: "combine_offer_axis (defined at L190) already carries a malformed-record disposition distinct from breach and clamp, so the verification conjunct lands in a function that already knows how to refuse an incoherent record instead of judging one"
```

### 2.8 Capture: §1.4-compliant by construction

The capture shape is ratified from the annex §3.4 with the P-5 correction at
§2.3(a) applied to Hop 4. **Four hops, each riding an existing carrier. No new
storage object, no new S3 read, no new query-time I/O.**

| hop | what | why this site and not another |
|---|---|---|
| **1 · capture** | per-section stamp map captured at build **inside `_finalize_artifacts_write_async`** (the converged write primitive that owns the fail-closed decision), *not* at the build step | its `PRESERVE_PRIOR_GOOD` branch **skips the write** — so a degraded warm that preserves the prior frame also preserves that frame's verification stamp, **for free and structurally**. Capturing at the build step would advance the stamp on a build whose bytes were discarded: a false-fresh generator of exactly the class this design removes |
| **2 · durability** | two additive keys on the existing `watermark.json` sidecar | precedented: `population_degraded` / `population_min_rate` were added there for the identical reason (stateless Lambda warm; the sidecar is the carry-forward channel), with legacy sidecars reading back as documented defaults |
| **3 · cache tiers** | +2 fields on `DataFrameCacheEntry`; S3 hydration reads them out of the **already-loaded** sidecar dict | **no extra round-trip** — the hydration path already loads the full sidecar in one GET and already reaches into it for `schema_version` |
| **4 · emission** | `FreshnessInfo` gains the map + flag; the query engine's freshness-meta reducer performs the **§2.3 classifier-scoped reduction** | the emitted signal is a reduction of a map that **travelled with the bytes**. No live read, no side-channel to skew, no tier the signal could have come from other than the tier that answered |

**This is what makes the design §1.4-*structural* rather than §1.4-*disciplinary*.**
CO-SOURCING stops being a rule anyone can violate and becomes a property of the
data — the same argument the contract makes for Lane G over Lane E.

**The join is GID→GID, and that matters.** At build time the builder already holds
a live `{gid: name}` map from the warm-entry section listing, independent of the
manifest. So the capture joins GID→GID against the manifest and takes its *names*
from the live listing. `SectionInfo.name` is **never consulted on the serve path**.
Consequence: **the name-join defect (B3-b) does not block this gate** — it remains
fully load-bearing for the metrics CLI (§5 Decision-7). The two surfaces **share
the stamp and diverge on the join**, which is the fact that drives the whole
supersession at §5.

**On LKG serves the stamp ages with the frame, and that is the design's
stuck-pipeline detector, not a bug in it.** Because the stamp is captured into the
frame at build and reduced from the frame at emit, an LKG serve of a five-hour-old
frame emits ~18 000 s of verification age. There is no live read to supply a
fresher number. This also makes the LKG ceiling and the gate ceiling interact
intelligibly for the first time: asana stops serving LKG at 16 200 s; the gate
warns at 14 400 s and aborts at 28 800 s. **A frame asana refuses to serve can
never satisfy the gate** — the correct nesting.

### 2.9 The emission chain is five legs, and every leg has killed a field

```
1. builder captures  → BuildResult
2. cache put         → DataFrameCacheEntry
3. serve             → FreshnessInfo
4. emit              → freshness-meta dict → RowsMeta / AggregateMeta  (both extra="forbid")
5. SDK               → QueryMeta declares it                            (extra="ignore")
6. consumer          → fetcher lifts it → readiness gates on it
```

Legs 3→4 is where `build_status` and `sections_failed` died — populated on
`FreshnessInfo`, never included in the emitted dict. Leg 4→5 is where
`stale_served` died. The V-sizing evidence independently confirms the first:
**`build_status` was null on all 495 offer records**, so build quality could not
be filtered on.

> **Therefore the acceptance test for this work is not "asana emits it."** It is
> **a live consumer log line showing the number.** That is written into §7.6's
> exit criteria, not left to diligence.

`RowsMeta` and `AggregateMeta` are both `extra="forbid"` and share the
freshness-meta side-channel, so **a field added to one and not the other raises**.
This turns a one-line omission into a 500.

```yaml
structural_verification_receipt:
  claim: "both response-meta models are extra=forbid and share one freshness-meta side-channel, so the three new fields must be added to both in the same change or the serve path raises"
  verification_method: file-read
  verification_anchor:
    source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/src/autom8_asana/query/models.py"
    line_range: "L228, L250-L252, L390"
    marker_token: "AggregateMeta is extra=\"forbid\" and shares the engine._get_freshness_meta"
    claim: "the codebase already carries a standing mirror comment recording this coupling as a live hazard, so the both-models requirement is an inscribed precedent rather than a new caution"
```

---

## §3 — The CONTRACT §1.2 amendment text

> ## ⚖ SIGNATURE ITEM (i) — **AMENDED-RATIFIED 2026-08-12** (RULING-operator-adr007-ratification-2026-08-12 R-i)
> **VERIFICATION GRAIN clause softened binding → advisory by the ruling; P-5 remains the operative ruling; denominator change process = R-alt (escalate only at the wall, receipts required). MONOTONICITY + non-aliasing extension ratified as written. Draft block below preserved verbatim per the struck-and-standing tradition:**
>
> **Direction ratified at P-1** (assumption (iv) was on the table when chosen).
> **The wording is drafted here and ratified here.** Process per precedent
> **[A-2026-08-03]** (charter amendment #298): amended **in place**, superseded
> text left standing and struck, one PR, ruled by the operator personally.
>
> **Why no third textual form exists.** A "refusal-only conjunct" — content age
> still advances freshness, verification recency may only subtract — leaves the
> predicate `content_age ≤ 3600 ∧ verification_age ≤ V`. The first conjunct passed
> **0/175 ticks**; adding a term to a conjunction can never raise its pass rate,
> so the conjunction passes **0/175**. The amendment must let verification recency
> **replace** content age as the advancing quantity for this source, or be refused
> honestly. **If REFUSED, say so in those words** and record that the offers gate
> is thereby ruled to remain on an axis measured at 0/175 — because that is what
> refusal means, and it should be a decision rather than a residue.

The following replaces `CONTRACT-offers-freshness-axis-frozen-2026-08-11.md` §1.2
(fence line 150). **The struck block is left standing verbatim.**

---

> ### §1.2 The advancement law (frozen)
>
> > ~~**Only a CONTENT axis may advance freshness — `content_watermark`
> > (frame-scoped) or `content_watermark_returned` (result-scoped).
> > `frame_built_at`, `served_entry_stamped_at`, `fetched_rows`,
> > `sections_fetched`, `sections_total` and `axes_present` are DISCLOSURE
> > fields. No consumer may gate freshness on them, and no emitter may
> > substitute one for a content axis.**~~
> >
> > **— SUPERSEDED IN PLACE by [A-2026-08-12]. Text retained per precedent
> > [A-2026-08-03] (charter amendment #298): a superseded clause is struck and
> > left standing, never deleted, so the record shows what was believed and when
> > it stopped being believed.**
>
> > **[A-2026-08-12 — AMENDED IN PLACE, operator-ruled]**
> >
> > **Exactly two axis families may advance freshness: CONTENT and VERIFICATION.**
> >
> > - **CONTENT** — `content_watermark` (frame-scoped) or
> >   `content_watermark_returned` (result-scoped). Answers *"how old is the
> >   newest fact in these bytes?"* **Unchanged in every respect by this
> >   amendment**, including §1.2b's frame/result distinction, T-GUARD, and the
> >   §1.2b corollary refusing monotonicity enforcement on content.
> > - **VERIFICATION** — `verified_at` and its derived
> >   `verification_age_seconds`. Answers *"how long since the rows in these bytes
> >   were last confirmed against the live source?"* A verification axis advances
> >   **only** through a per-section probe or fetch that (a) reached the live
> >   source, (b) returned a verdict other than `PROBE_FAILED`, and (c) where the
> >   verdict required a delta, had that delta successfully applied. It **never**
> >   advances on assembly, on a build clock, on a cache write, on a fetch that
> >   returned nothing, or on the passage of time.
> >
> > `frame_built_at`, `served_entry_stamped_at`, `data_age_seconds`,
> > `staleness_ratio`, `freshness`, `stale_served`, `fetched_rows`,
> > `sections_fetched`, `sections_total`, `served_tier`, `axes_present` and
> > `content_digest` remain **DISCLOSURE** fields. No consumer may gate freshness
> > on them; no emitter may substitute one for an advancing axis.
> >
> > **Which axis gates is a per-source ruling, not a per-emitter choice.** An
> > emitter emits every axis it can derive; the *consumer's* ruling selects the
> > gating one.
> >
> > **For the `offers` source that ruling is:** `PASS` iff
> > `verification_age_seconds ≤ V` **AND** completeness proven per constituent.
> > `content_age_seconds` is retained as DISCLOSURE and as the anomaly input for
> > this source, and does **not** gate it.
> >
> > **VERIFICATION GRAIN (binding).** `verified_at` is the `min` over the
> > **complete classification-scoped section-name set** for the request — every
> > section the producer's classifier assigns to the requested classification(s),
> > **including sections that carry zero rows**. A verified-empty section is
> > verified and MUST be included. A classification-scoped section whose stamp is
> > absent or null makes the axis **underivable for that response**: the emitter
> > emits `null` and declares the axis in `axes_present` (AXIS-NULL). It is
> > **never** dropped from the denominator, **never** skipped, **never**
> > substituted.
> >
> > **MONOTONICITY (binding, and deliberately asymmetric with §1.2b).** A
> > persisted verification instant MUST NOT move backward. §1.2b's corollary
> > refuses monotonicity on the **content** watermark because a content watermark
> > can legitimately decrease when rows are deleted, so a ratchet there would
> > manufacture a false-fresh generator. **A verification instant cannot
> > legitimately move backward, because time does not.** Monotonicity is a
> > false-fresh generator on content and a truth-preserving invariant on
> > verification. The asymmetry is intentional and is not an inconsistency.
> >
> > **NON-ALIASING (BINDING — inherits the §1.8 form and is binding for the same
> > reason).**
> >
> > 1. `verified_at` and `verification_age_seconds` are emitted **only** as the
> >    verification axis. No emitter may populate either from a build clock, a
> >    cache-entry `created_at`, an S3 `LastModified`, a `written_at`, or a
> >    `watermark`. An emitter that cannot derive the axis emits `null` and
> >    declares it in `axes_present` (AXIS-NULL), or omits it entirely and does
> >    **not** declare it (AXIS-ABSENT). Those are different states and §1.5b
> >    governs both.
> > 2. **No consumer may coalesce** `verification_age_seconds` with
> >    `content_age_seconds` or `data_age_seconds` — no `or`, no fallback, no
> >    "whichever is present" helper, no shared parse branch. A consumer that
> >    wants more than one handles each in a separately-named code path. This is
> >    §1.8 clause 3 applied to the new pair, binding for the identical reason: an
> >    alias is how one quantity acquires another's guarantee without earning it.
> > 3. **No field is ever polymorphic.** `content_age_seconds` keeps its exact
> >    current meaning — result-scoped content age — permanently. It is never
> >    re-pointed at another axis, never widened, never given a companion field
> >    declaring "which axis this is". A field carries one axis for its whole life
> >    or it is a new field.
> > 4. `verified_at` is **NOT** `built_from_live_at`. The Seam-1 token remains
> >    reserved exclusively for the frozen Seam-1 value object (D-1 RATIFIED,
> >    §1.8). `verified_at` is a v1 quantity: a fold over per-section **probe or
> >    fetch** instants, not the Seam-1 content-fetch fold. It must never carry the
> >    Seam-1 name and the two must never be coalesced.
> > 5. **`verification_backfill_used` is a REQUIRED companion field.** A
> >    verification axis emitted without its backfill flag is unreadable and MUST
> >    be treated by the consumer as AXIS-NULL.
> > 6. **Spelling is load-bearing**, per §E.2. The forbidden near-misses are named
> >    here so they are refused rather than debated: `verification_seconds`,
> >    `verif_age`, `v_age`, `verified_age_seconds`, `last_verified_at` (that token
> >    names the **manifest-tier** field and is already collided once inside the
> >    producer repo — see the standing NOTE at `section_persistence.py:106-113`),
> >    `verification_watermark`, `verified_watermark`.

---

### 3.1 Roster additions — §E.2 goes from twelve names to fifteen

| field | type | meaning |
|---|---|---|
| `verified_at` | ISO-8601 UTC `str` \| `null` | `min` over the **complete classification-scoped section-name set** for this response, zero-row sections included. `null` = unprovable. Never synthesized. |
| `verification_age_seconds` | `float` \| `null` | `now − verified_at`. `null` iff `verified_at` is `null`. |
| `verification_backfill_used` | `bool` | `True` iff any classification-scoped section's stamp was substituted from `written_at` rather than a real probe-or-fetch stamp. **[spelling pending — §8 O-3]** |

**`axes_present` (CAP-SIG, §1.5b) MUST gain `"verified_at"` and
`"verification_age_seconds"` when the producer speaks them.** This is not
optional plumbing. It is the **only** thing that lets a consumer distinguish
*"this producer has not shipped the axis yet"* (AXIS-ABSENT → dormant, fall back,
never refuse) from *"this producer shipped it and cannot derive it"* (AXIS-NULL →
refuse). **Without it the consumer leg cannot land before the producer leg and
the staged rollout at §7 collapses.**

---

## §4 — V

> ## ⚖ SIGNATURE ITEM (ii) — **RATIFIED-PROVISIONAL 2026-08-12** (RULING R-ii)
> **V=14,400 / abort 28,800 live as PROVISIONAL; auto-confirm-or-reopen executes at the 14-day soak close, no separate sitting. Riders carried unsoftened. Draft block below preserved verbatim:**
>
> `V = 14 400 s` **was NOT ratified at the interview.** The ruling records it as
> assumption 1 among those explicitly not decided: *"the annex proposes it and the
> age-at-tick evidence supports it, but the number goes to ratification at the new
> ADR's draft, alongside the evidence's two riders."* Both riders are attached
> below, unsoftened.

### 4.1 The proposal

| quantity | value |
|---|---|
| **V (PASS line)** | **14 400 s = 4.0 h** |
| **derived abort line (2V, not independently settable)** | **28 800 s = 8.0 h** |
| deployed content gate, for comparison | 3 600 s / 7 200 s — passed **0/175** |

**The argument is the ratio, not the pass rate.** Option 1's least-bad abort line
was **47.6 h = 6.0× the consumer contract**. This lands the abort line at
**8.0 h = 1.0× the consumer contract's 8 h horizon** rather than six times it.
*(On what that horizon actually bounds, read the block immediately below before
citing this ratio anywhere.)*

> **⚠ REFERENT PRECISION on "the consumer contract's 8 h" — stated because this
> ADR will not repeat the crusade's founding error at its own ratification.**
>
> The 8 h is verified and real, but its referent is **the published verdict
> surface's staleness rule**, not a stated tolerance for input-data age:
>
> ```yaml
> structural_verification_receipt:
>   claim: "the consumer contract's 8h is the staleness rule for the PUBLISHED VERDICT surface — 'two missed runs' of the 4-hourly cadence — not a declared tolerance for the age of the data behind a verdict"
>   verification_method: file-read
>   verification_anchor:
>     source: "services/account-status-recon/docs/contracts/S5-INGESTION-CONTRACT-verdict-surface.md (autom8y @origin/main 6fc556d8)"
>     line_range: "§5, L175-L177"
>     marker_token: "now - latest.verdict_at > 8h` (two missed runs; mirrors ASR's dead-man threshold)"
>     claim: "the quantity bounded is now-minus-verdict_at, i.e. how old a published verdict may be before the surface displays it as stale — so treating 8h as a data-age tolerance is an inference from it, not a quotation of it"
> ```
>
> **The two compose coherently, and that is the honest argument to make.** If the
> gate aborts, no verdict is published; after 8 h of continuous aborting, the
> surface reads stale. **The gate's abort line and the surface's staleness rule
> therefore fire at the same horizon** — the surface goes stale exactly when the
> gate has been refusing for the full window. That is a *correct nesting*, the same
> shape as the LKG-ceiling nesting at §2.8, and it is a genuine argument for
> 28 800 s.
>
> **What it is not** is the sentence *"8 h is the consumer's stated tolerance for
> data age."* No artifact states that. The operator is being asked to ratify an
> abort line that **aligns the gate's refusal horizon with the surface's staleness
> horizon** — which is defensible on its own terms and should be ratified on those
> terms rather than on a borrowed one. See §8 O-14.

Candidates enumerated and dispositioned, so the choice is visibly a choice:

| V | abort (2V) | disposition |
|---|---|---|
| 3 600 s | 7 200 s (2 h) | **REJECT as deployed cadence stands** — the abort line sits *below* the measured p90 inter-build gap (13 008 s). A healthy pipeline would abort routinely. Admissible only **after** warm cadence is engineered to a p99 under 2 h — a legitimate future goal, and exactly the kind of goal the content axis could never generate |
| 7 200 s | 14 400 s (4 h) | **REJECT on margin** — max observed inter-build gap (15 d) was 14 394 s, **6 seconds** under the abort line. Zero margin against one slow warm |
| **14 400 s** | **28 800 s (8 h)** | **PROPOSED** — the abort line lands **exactly** on the consumer contract's 8 h horizon (§4.1 referent note); abort-line margin against every measured maximum is **1.72×–2.20×** |
| 16 200 s | 32 400 s (9 h) | enumerate, do not adopt — elegant in making V equal the LKG serve ceiling, but the abort line then **exceeds** the consumer contract, and aligning a freshness knob to an availability constant is the exact axis-conflation this crusade exists to end |

### 4.2 The measurement

`.sos/wip/EVIDENCE-age-at-tick-v-sizing-2026-08-12.md` — eunomia /
verification-auditor, rite-disjoint, read-only, **[STRONG]**. It discharged the
annex's own UV-P and returned a stronger answer than the annex expected.

| V | PASS (`age ≤ V`) | not-ABORT (`age ≤ 2V`) |
|---|---|---|
| 7 200 s | 88.1 % stamp / 63.5 % build | 100.0 % / 100.0 % |
| **14 400 s** | **100.0 % / 100.0 %** | **100.0 % / 100.0 %** |

126 organic ticks over 29 days; invariant across **five perturbations** (organic /
optimistic causality / warmer-only counterfactual / synthetic uniform grid ×2),
two event families, three grids. **The abort line is never crossed anywhere:**
0 of 42 241 continuous one-minute samples, 0 of 126 ticks, 0 of 177 grid ticks.
The warmer-only stress case's own maximum is 16 774 s — **1.72× inside 2V**.

**The annex's length-bias worry is refuted, and the refutation is a property of
platform ownership rather than luck.** The gap distribution is hard-capped by a
scheduled ~4 h warm, so it is **under-dispersed** (CV = 0.89 build / 0.94 stamp).
The closed-form length-bias prediction matches the measured mean age to **0–2
seconds (0.06 %)**. Age-at-tick is **6–10 % shorter** than the mean gap, not
longer. A business-driven interval is over-dispersed and length-bias inflates it;
a scheduled interval is under-dispersed and length-bias deflates it.

**Weekend behaviour is strongest exactly where the content axis was worst.** The
warmer does not sleep: weekend age-at-tick equals or beats weekday on both series,
100 % PASS at V = 14 400 on both partitions. W-1's content axis on the same
weekends: **0/24 not-ABORT at the deployed threshold.**

**The tail is platform-engineerable, unlike W-1's sawtooth.** Every named cause
has an owner and a knob — the 4 h scheduled warm ceiling (warm schedule / entity
TTL / concurrency), the overnight request drought (synthetic keep-warm), one
`_list_sections` failure (a code defect with a stack trace), per-section stamp
pinning (already fixed). W-1's tail was generated by *"how long may a human go
without editing an offer?"* — **no knob at all**.

### 4.3 RIDER 1 — size the confidence on the ABORT line, not on V

> **The annex's stated *ground* for V does not survive a 30-day window.** The
> annex argued *"PASS line covers the measured maximum inter-build interval"*
> (max gap 14 394 s over 15 days). **Over 30 days that claim is false:**
> `max(gap) = 14 568 s`.
>
> The conclusion survives; the reasoning must be replaced. The correct statement:
>
> > V = 14 400 s passes **100 % of measured ticks over 29 days because the tick
> > grid does not land inside the over-4h gaps**, not because 14 400 s bounds the
> > gap. **The margin at the observed tick maximum is 76 seconds.** The
> > load-bearing quantity is the **abort line**, whose margin against every
> > measured maximum — including the one build failure — is **1.72×–2.20×**.
>
> This is a **stronger** argument than the annex's, not a weaker one, because it
> does not depend on a bound a wider window falsifies. **The operator is being
> asked to place confidence on the abort line (2.00× at the observed max, 1.72×
> under the warmer-only stress case), not on the PASS line (76 s).**
>
> **Operational consequence, stated so it is not read as degradation:** at
> V = 14 400, **WARN will be a routine overnight reading.** The 14-day build-series
> p75 is already 12 779 s. WARN does not gate — only `> 2V` aborts — but an
> operator watching the readout will see WARN more often than today, and that is
> the design working, not failing.

### 4.4 RIDER 2 — the nine inter-build gaps over 14 400 s in 30 days

> **Nine gaps exceed 14 400 s in the 30-day window**, with `max(gap) = 14 568 s`.
>
> **All nine fall in segment A (2026-07-14 → 07-27, pre-re-seed).** Zero fall in
> segments B, C or D. Segment D — the current regime since 2026-08-05T09:15Z — is
> the **best** on the stamp series: tick max **5 419 s**, which would clear
> **100 % PASS even at V = 7 200**.
>
> **Two ways to read that, and the operator should hold both.** (i) The regime has
> genuinely improved, so V = 14 400 is conservative against today's cadence. (ii)
> Segment D is only **7 days / 43 organic ticks**, and **the cadence changed inside
> the measurement window** (`bc620e18`, 2026-08-05, offer-frame priority). The
> evidence grades segment D **[MODERATE]** for that reason and 30-day log retention
> is a hard ceiling on doing better today.
>
> **Therefore: V's re-baseline trigger is booked now, not later.** V is a function
> of warm cadence. Any change to warm scheduling, entity TTL, or Lambda
> concurrency invalidates it. The re-derivation is a one-line CloudWatch query on
> a log group with 30-day retention. **This trigger is already live, not
> hypothetical** — the cadence changed once inside the very window that sized V.

### 4.5 The counter-weight the operator must hold alongside the 100 %

**The V evidence measures a frame-level quantity. The gate under P-5 reads a
per-section `min()`. These can diverge by 21× the abort line, and the corpus
contains a 6.7-day instance.**

| | frame-level (what §4.2 measured) | per-section `min()` (what the gate will read) |
|---|---|---|
| 2026-07-28 → 08-03, 37 organic ticks | **100 % PASS** at V = 14 400 | **0/37 PASS, 0/37 not-ABORT**; median 96.0 h, max **7.00 days** |

The evidence states this in its own words: *"This is invisible to every instrument
in this artifact."* The class is closed at HEAD by FIX-1, and §2.3's table
inventories the residue. But **the 100 % figure is a ceiling conditional on stamp
eligibility, and it should be ratified as such** — which is precisely why P-5's
consequence makes the stamp-eligibility fix a hard gate-live precondition rather
than a nice-to-have.

### 4.6 What §4 does not establish

- It does **not** establish what the *built* gate reads. It measures the
  producer-side verification instant; the serve-path stamp identity is **UV-P-1**,
  dischargeable only post-implementation. **The direction of error is known and
  one-sided: the built gate reads OLDER, never younger.**
- It does **not** validate `min()` over constituents (**UV-P-3**, the same question
  as B3-a).
- It does **not** cover a public holiday (**UV-P-6**, inherited) — though exposure
  is far smaller here, because the axis is not driven by human presence.
- **A logged stamp pass is not proof of a persisted stamp** (DEFECT-1, §2.5). Every
  figure is a **floor** on the age for this third, independent reason.

> **[UV-P: the pass rate the built gate will realise under the P-5 per-section
> reduction | METHOD: the first 14-day soak after K-4 lands, reading
> `verification_age_seconds` off live consumer log lines | REASON: the field does
> not exist in production; §4.2's 100 % is a frame-level ceiling and §4.5's 0/37
> is the same corpus read at the gate's actual grain. This is the P-9 kill-switch-3
> measurement and it cannot be run before the axis is live.]**

---

## §5 — Supersession of ADR-006 (P-8)

**P-8 ruled: supersede into a new ADR — one principle covering both surfaces
(metrics CLI + query wire).**

### 5.1 The situation being resolved

ADR-006 is `status: proposed-revised`, revision 3, dated 2026-05-27. **Never
accepted.** Its code shipped anyway and is live and load-bearing: the
`SectionInfo.last_verified_at` field, the stamp pass, `compute_verification_age`,
and the FIX-1 empty-section coherence clause merged as recently as PR #299. This
is not a discharged governance debt; it is a second one.

This initiative would otherwise build a **second** consumer of the same stamp, on
a **different surface**, with a **different denominator** and a **different join
key**, under an ADR that is not in force and whose §D1 contains a *rejection* of
GID-based joining that a careless reader would cite against the new design.

Three options were enumerated; two are visibly rejected:

| # | option | verdict |
|---|---|---|
| a | Accept ADR-006 as-is, then amend it | **Rejected** — ratifies revision 3's denominator and join ruling as in force and then immediately departs from both. Ratifying a document in order to amend it in the same sprint is governance theatre, and it leaves the D1-vs-GID tension live rather than resolved |
| **b** | **Supersede into one ADR covering both surfaces** | **RULED (P-8)** — lets the stamp-eligibility rules be **ratified once and inherited twice**, and resolves the D1 tension by **scoping** it rather than reversing it |
| c | Retire ADR-006 | **Not available** — the code is live. Retirement would leave `last_verified_at`, the stamp pass, and FIX-1 standing with **no** decision record at all: strictly worse than the current limbo. Enumerated so it is visibly rejected rather than silently skipped |

**At ratification, ADR-006's status line becomes
`superseded-by: ADR-007-verification-axis-gate-2026-08-12`, its text left
standing** per the same discipline §3 applies to the contract clause. *This ADR
does not modify ADR-006; the status edit executes at ratification.*

### 5.2 Decision-by-decision disposition

Every ADR-006 decision is **carried**, **carried-as-scoped**, **amended**, or
**overruled** — none is left to inference.

| ADR-006 | Substance | Disposition here |
|---|---|---|
| **Decision-1** — persist per-section `last_verified_at` on the manifest, stamped at the probe site on every verdict ≠ `PROBE_FAILED` | the stamp itself | **CARRIED VERBATIM.** This is the quantity both surfaces share. Finally ratified. |
| **Decision-2** — reader re-point: `verification_age = now − min(last_verified_at)`, not `now − min(parquet mtime)` | the CLI's reader | **CARRIED, CLI-scoped.** The serve path derives the same quantity from a map captured into the frame (§2.8), never from a live manifest read — CONTRACT §1.4 forbids the latter on a serve path. |
| **Decision-3** — scope to `active_sections()` | the CLI's denominator | **CARRIED FOR THE CLI; DELIBERATELY DIVERGENT ON THE SERVE PATH.** The offers gate's constituents are `active` **and** `activating`, and under **P-5** the serve-path denominator is the complete classification-scoped **name set** including zero-row sections (§2.3). Stated as a deliberate divergence, not a discrepancy. |
| **Decision-4** — two signals; `verification_age` is the FULL alarmable `--strict` SLI; `mutation_age` context-only | the CLI's exposure | **CARRIED UNCHANGED for the CLI.** No serve-path analogue: the serve path emits an axis, not an SLI. |
| **Decision-5 (5a/5b/5c)** — the stamp invariant: `PROBE_FAILED` never stamps; a `CLEAN` stamps only because the prober's `CLEAN` is trustworthy; a delta-requiring verdict stamps only on **delta-apply success** | the load-bearing rule set | **CARRIED VERBATIM AND RATIFIED ONCE, INHERITED TWICE.** This is the substance that makes the "not just build-axis with extra steps" answer mechanical rather than definitional. |
| **Decision-5d** *(new — records what shipped after ADR-006 rev-3)* | FIX-1: a hash-CLEAN on a **coherently-empty** section (`rows==0` **AND** `gid_hash==hash(∅)`) **does** stamp; an **incoherent** `rows==0` stays on the no-stamp path | **INSCRIBED HERE.** `5d62d0b8` / PR #299 post-dates ADR-006 rev-3 and is unrecorded in it. Under **P-5** this clause is not a nicety — it is the mechanism by which zero-row classified sections become stampable at all. Its coherence premise is preserved verbatim: stamping a poisoned `rows=0` would silence the exact channel that detects the poison. |
| **Decision-6** — backward-compat: missing `last_verified_at` is "never verified" and **on read falls back to the section's `written_at`**; a wholly-unstamped manifest **degrades to the ADR-001 mutation-axis signal** rather than erroring | the `written_at` fallback | **⛔ OVERRULED BY P-6.** *Stated in those words, because this is the single reversal in the supersession.* P-6 ruled **close at source, then refuse**: a fetch **is** a verification and stamps honestly at completion; thereafter **unstamped = unknown = refuse**. `written_at` is a **mutation-recency** channel and may never be read as, coalesced into, or substituted for a verification instant on **either** surface (P-8: one principle, both surfaces). The serve path ABORTs; the CLI reports the axis unprovable rather than silently degrading to `mutation_age`. **The graceful-degrade path is retired** — it is the mechanism by which the cured defect would re-enter one layer up. *(The CLI's precise exit-code / alarm expression of "unprovable" is an implementation item for the CLI leg — §8 O-4.)* |
| **Decision-7** — named sections are a FUNCTIONAL REQUIREMENT; the `name` wipe healed at source; re-seed from `Section.name` at warm entry; loud error on ≥2 sections with a null name | the CLI's join key | **CARRIED, CLI-SCOPED.** The **serve path joins GID→GID** and takes names from the live warm-entry listing (§2.8), so `SectionInfo.name` is **not** a precondition for this gate. **B3-b blocks the CLI only.** *The carry-forward half is verified live in code at `mark_section_complete` (L205-L207).* |
| **Decision-7a** — re-seed-window alarm suppression; **no backfill job; the warm cadence IS the backfill** | the rollout posture | **CARRIED, AND IT IS LOAD-BEARING HERE.** It is the ruling that makes P-6's refusal window **short and bounded** (median warm cadence 39 min) rather than open-ended. Without it, "refuse the unstamped" would have no stated exit. |
| **Decision-8** — sync→async bridge for the CLI reader | plumbing | **CARRIED UNCHANGED, CLI-only.** No serve-path analogue. |
| **Decision-9** — stamp-phase failures are observable (`section_last_verified_stamp_failed`) | observability | **CARRIED AND ELEVATED.** Under P-5's `min()` over all classified sections, **silent stamp starvation is the dominant failure mode**, so this metric moves from diagnostic to **gate-critical**. It is the P-4 stage-1 instrument for kill-switch 2. |
| **§D1** — the GID-based resolver alternative is **REJECTED** | the join ruling | **CARRIED AS SCOPED, NOT REVERSED.** D1's rationale is explicitly the CLI's: a human-interpretable named manifest is a stated **functional requirement** there, and a GID resolver would **mask** the name wipe. **Neither concern applies** to a serve-path reduction that never surfaces a section name to a human and whose names come from the live listing. **This scoping statement is inscribed here so nobody later reads §2.8 as a quiet reversal of D1.** |
| **Alternatives a/b/c/d** | project-level heartbeat rejected; parquet-touch rejected; per-section manifest chosen; two-signal exposure accepted | **CARRIED.** Alternative (a) — the project-level heartbeat — is **strengthened** by P-5: a project scalar cannot express a per-section `min()` at all, so it cannot detect the dropped-coverage case that P-5 makes central. |
| **Threshold re-grounding** — the 6 h default "should track the warm cadence" | an unfinished sentence in ADR-006 | **DISCHARGED BY §4.** V is sized on warm cadence, measured (§4.2), and carries a booked re-baseline trigger (§4.4). This is the ADR-006 intent, finally given a number and an instrument. |

### 5.3 What the superseding ADR carries that lived nowhere before

1. **The stamp** and its 5a/5b/5c/5d eligibility rules — ratified once, inherited twice.
2. **Two surfaces, two denominators, one quantity** — stated as a deliberate divergence.
3. **The D1 scoping statement** — why the GID-join rejection binds the CLI and not the serve path.
4. **G-1 monotonicity** with the explicit argument for why it is correct on verification and forbidden on content (§2.5, §3).
5. **The P-6 backfill disposition**, including the `mark_section_failed` stamp-destruction channel (§2.4).
6. **The named non-inheritance** of synthetic-fresh hydration, restated as a preservation obligation after `#338` (§2.6).

---

## §6 — Falsifier register (P-9)

**Three kill-switches, registered verbatim from the ruling. Any seat observing one
HALTS and escalates, never argues.**

> ### KS-1 — wrong-verdict case
> **A verified-complete-and-recent snapshot produces a materially wrong published
> verdict traceable to data age.**
>
> *What it kills:* the pillar. If the gate says GO on data that was recent and
> complete by its own measure, and the published verdict is materially wrong
> *because of data age*, then verification recency is not the quantity that
> governs verdict correctness and this gate is measuring the wrong thing.
> *Owner of the observation:* any seat. *Escalation:* HALT.

> ### KS-2 — stamp-integrity failure
> **Verification errs FRESH against demonstrable Asana truth.**
>
> *What it kills:* the pillar. This is the design's deepest accepted cost made
> real. `verification_age_seconds` is **producer-attested** — the producer
> asserting *"I called Asana and it answered"* — where `content_watermark` is
> **source-attested** and can only ever be wrong in the *stale* direction. A single
> observed instance of a stamp advancing on a section whose content was
> demonstrably not confirmed falsifies the mitigations at §6.1.
> *Owner:* any seat. *Escalation:* HALT.

> ### KS-3 — soak bar missed
> **The 14-day soak fails the ≥95 % / ≤8 h bar.**
>
> *What it kills:* the P-4 stage-2 "done" bar, and with it the gate's live status.
> *Owner:* the soak. *Escalation:* HALT.

### 6.0 The fourth case — explicitly NOT registered

> **"Eligibility unfixable" was explicitly NOT registered.** The operator diverged
> from the recommendation (which proposed all four) and ruled it a **redesign
> trigger for P-5, not a pillar kill.**
>
> **Disposition, stated so the boundary is unambiguous:** if the stamp-eligibility
> precondition (§2.3, §7.2) proves unachievable — zero-row classified sections
> cannot be made to carry honest stamps — the response is **to re-open P-5's
> `min()` scope**, not to abandon the verification axis. The design space that
> re-opens includes narrowing the denominator to row-bearing sections plus an
> independent zero-row coverage check, or moving the zero-row question out of the
> recency axis entirely into the completeness conjunct.
>
> **A seat that observes eligibility failure must NOT treat it as KS-1/2/3, must
> NOT halt the initiative, and must route it to the operator as a P-5 redesign
> item.** Conflating it with a kill-switch would discard a working axis over a
> denominator question.

### 6.1 The mitigations KS-2 tests, and what would falsify them

The producer-attestation cost is real and is ruled on knowingly. Four parts —
**the first three are mitigations, not refutations:**

1. **The stamp is gated on independent success predicates** (§2.2) — the failure
   requires a *specific* broken-probe defect, not mere inattention. The probe
   issues an HTTP request to Asana per section, per warm; W-1's entire instrument
   is built on 7 227 of those requests read off the wire. A stamp advancing without
   a probe would require those requests not to have happened, and they demonstrably
   did.
2. **The content axis stays on the wire** (P-1) as the source-attested cross-check;
   §2.7's anomaly rules exist precisely to consume it. The design does not discard
   the humbler quantity — it stops letting it *gate*.
3. **The hard refusal at §2.7** closes the cheapest version of the failure: a
   producer that stamps while admitting incomplete coverage.
4. **The trust increase is real but not new in kind.** The consumer already trusts
   this producer to project `last_modified` honestly, to report
   `returned_count`/`total_count` honestly, and not to serve one project's frame
   under another's key — and the query engine already **silently drops** a
   requested column absent from the frame, a producer-attested behaviour the
   consumer cannot detect. Option 4 increases the **degree** of trust, not its
   **category**.

**The concession, made rather than withheld:** the stamp confirms *the section*,
not *the frame*. The stamp lives on the manifest; the served bytes are a merged
parquet. §2.8's capture-inside-the-write-gate closes the gap that matters, but the
two artifacts are distinct and a defect decoupling them would decouple the axis
from the bytes. **That is a design invariant to test (§7.6), not a proof to
assume.**

**The class is constructible in this codebase.** The FIX-1 /
`DEFECT-delta-path-empty-poison` history exists because a poisoned `rows=0` beside
a non-empty `gid_hash` could produce a false CLEAN. That defect was contained; the
class was not eliminated. **KS-2 is registered because this is a live class, not a
theoretical one.**

### 6.2 The genuine alternative, enumerated so it is visibly rejected

> **Option 5 — completeness-only gate + cadence alarm.** `PASS` iff completeness
> proven. Stuck-pipeline detection moves entirely to the existing
> `completion_event_deadman`. No contract amendment, no wire fields, no five-leg
> chain. **Cost: ~zero.**

It is a serious option — every offers field the consumer reads is a join key or a
static attribute, none is time-sensitive, and the population was proved complete
(68/68, 48/48) at both refused ticks.

**It has one fatal flaw and it is decisive: the deadman measures *consumer*
liveness, not *producer* liveness.** A stuck producer with a healthy consumer under
a completeness-only gate: the producer serves a frozen but complete frame, so
`returned_count == total_count` every tick (a frozen frame is perfectly
self-consistent); the consumer passes, reconciles, and publishes every tick; the
deadman sees a publish every window and stays **GREEN**; the readout is confidently
wrong, indefinitely, with **no signal anywhere.** The deadman's alarm condition is
"no completion in the window" — and a completeness-only gate *guarantees*
completion. **Option 5 converts a loud, fail-safe failure into a silent,
confidently-wrong one.** The charter's hard floor — **NEVER CONFIDENTLY WRONG** —
points directly away from it.

That argument also *strengthens* this design: the verification conjunct is the only
proposed mechanism that carries **producer liveness** onto the consumer's decision
path, and it is not redundant with the deadman because the deadman cannot see it.

> **[UV-P: whether `source-coverage-3of3-deadman` would catch the frozen-frame
> scenario | METHOD: read that alarm's metric expression and dimensions and
> determine whether its input can distinguish a served-but-frozen source from a
> served-and-current one | REASON: the completion deadman's parameters were read
> directly; this one's were not. If it **does** catch the frozen-frame case,
> Option 5's flaw is smaller than argued and the option deserves re-weighing.
> This is the single cheapest falsifier of §6.2 and it survives unrun from the
> annex.]**

### 6.3 The honest cost, in the operator's units

- **Detection latency triples on paper.** Under the deployed content gate a stuck
  producer aborts at 2 h; under V = 14 400 it aborts at 8 h. **The defence is that
  8 h is the consumer contract's own horizon (§4.1) and 2 h was never actually
  achieved** — 0/175 ticks reached the gate at all, so the comparison is between a
  **theoretical 2 h** and a **real 8 h**. An operator who believes the 2 h number
  is real is losing something in this trade and should be told the number rather
  than the ratio.
- **The gate becomes a platform-health check wearing a data-quality name.**
  Completeness is a data question; verification recency is a pipeline question.
  Given that no offers field the consumer reads is time-sensitive, that is
  arguably the correct division of labour — but the gate's inherited name
  (*freshness*) will drift from its content again, which is the naming failure this
  crusade has now corrected twice. **The mitigation is nominative and is taken
  here:** call the quantity what it is in logs, dashboards, and this ADR —
  **verification recency** — and do not let "freshness" become the umbrella term
  for both axes a third time.

---

## §7 — Build plan skeleton (P-2)

**P-2 ruled: full chain, one initiative — producer capture → SDK → consumer,
K-lane sequenced, B-block preconditions gated inside.**

### 7.0 Interim posture (P-3)

> **"Accept until replaced" — honest aborts continue with NO clock. The
> successor's landing is the only exit.**

No time-box, no review horizon, no escalation on elapsed time. The offers gate
continues to abort honestly on the falsified content axis until **K-4 lands**.
*(Recorded as ruled; this diverged from the recommendation and is not re-argued.)*

### 7.1 Stage boundaries (P-4)

| stage | bar | status |
|---|---|---|
| **Stage 1 — observability truthful first** | every alarm and description tells the truth | **EXECUTING.** All four P-7 items authored and planned, **nothing applied, nothing committed** — `.sos/wip/STAGE1-observability-truth-2026-08-12.md`. Awaiting operator apply on (a)+(b) *(one apply — same resource, same file)*, operator apply on (c) *(monorepo)*, and operator routing on (d) |
| **Stage 2 — the gate closes under the statistical bar** | **≥95 % healthy-pass / ≤8 h detection over a soak window**; KS-3 names **14 days** | **BLOCKED on K-4.** The instrument does not exist: `verification_age_seconds` is not on the wire, so the soak cannot begin before the axis is live and observed |

**Stage 1 is not a prerequisite of building; it is a prerequisite of trusting the
readout the build will be judged on.** A soak measured against alarms that lie is
not a soak.

### 7.2 K-0 — preconditions, gated inside the initiative (P-2)

| id | precondition | blocks | owner |
|---|---|---|---|
| **K-0a** | **B3-a — the manifest observation, RE-SCOPED UNDER P-5** | **everything** | rite-disjoint (eunomia / verification-auditor) |
| **K-0b** | This ADR ratified (§3 amendment text + §4 V) | K-1 onward | operator |
| **K-0c** | The §3 amendment landed in the contract, one PR, superseded text struck and standing | K-1 onward | 10x-dev |

> **⚠ B3-a's pass criteria are REWRITTEN by P-5 and the annex's version must not
> be used.** The annex scoped B3-a to *"every section that contributes rows to an
> `active` or `activating` classification."* Under P-5 that is the wrong
> population — it is exactly the ~19 zero-row sections that the annex's criteria
> would have excluded and P-5 rules must be included.
>
> **B3-a PASS (P-5 scoping) iff:**
> 1. **every** section name in `OFFER_CLASSIFIER.sections_for(ACTIVE, ACTIVATING)`
>    — all 27, **row-bearing and zero-row alike** — resolves to a manifest section;
> 2. **every** one of those sections carries a non-null `last_verified_at`;
> 3. `now − oldest_stamp` **over that full set** is within the same order of
>    magnitude as the measured build cadence (**hours, not days**).
>
> A stamp set whose oldest entry over the full classified population is days or
> weeks old means the stamp pass is not reaching some section. **That is a
> successful detection and a blocker** — route it as a producer defect, not as an
> Option-4 cost. It is also the pre-registered check for the §4.5 pinned-floor
> scenario.
>
> **B3-b** (`SectionInfo.name` populated) is **split off and blocks the metrics CLI
> only** (§5 Decision-7). Both questions are answered by reading **one** S3 object.
>
> *Owner rationale:* this is a read-only prod state observation whose whole value
> is that it is performed by someone who did not design the thing being checked.
> Scope deliberately narrow: read the object, answer against the stated criteria,
> report the unstamped list verbatim, take no view on the design.

> **[UV-P: the live prod state of `last_verified_at` across the full classified
> section population for the offers project | METHOD: one S3 GET of the offer
> manifest plus a `jq` reduction, against the three P-5 criteria above | REASON:
> this ADR's fence is design-only — no S3 read, no AWS call. No artifact in this
> crusade has read that object; every statement here about prod stamp state is a
> claim about **code**, not about **data**.]**

### 7.3 K-1 … K-5 — the lane

**Steps K-1 through K-3 are all DARK. The single behaviour-changing merge is K-4,
and it is one predicate in one function.** That is the atomic-commit property
worth protecting: if the gate misbehaves, **exactly one merge is a candidate.**

| step | leg | repo | lands | gated on |
|---|---|---|---|---|
| **K-1** | producer capture (§2.8, four hops) + **G-1** monotone envelope + **G-3** provenance enum + **P-6 source-close** (fetch-is-verification stamping + `mark_section_failed` stamp preservation) | asana | **dark** — nothing reads it | K-0a PASS, K-0b, K-0c |
| **K-2** | SDK: `QueryMeta` declares the three fields + the `axes_present` tokens | autom8y-core | **dark** — SDK parses, nobody gates | K-1 deployed **and observed on the wire** (§2.9 acceptance test) |
| **K-3** | ASR: the constituent-signal builder carries the new keys, **absence-preserving** | autom8y ASR | **dark** — carried, not gated | K-2 published |
| **K-4** | the offer-axis combiner gains the verification conjunct; the axis switch selects it | autom8y ASR | **⚠ BEHAVIOUR CHANGE** | K-1..K-3 live, **one observed tick showing the number** |
| **K-5** | content age demoted to disclosure + §2.7 anomaly rules | autom8y ASR | disclosure only | K-4 |

**Never bundle K-4 with anything.**

**Four K-lane properties adopted verbatim as rollout discipline** — these are why
the previous lane worked, and each maps to a specific hazard here:

| property | how it applies |
|---|---|
| **key ABSENCE ≠ key NULL** — the consumer omits axis keys entirely when it could not derive them, so "never derived" (dormant) and "derived and null" (refuse) stay distinguishable | the producer omits `verified_at` and does **not** list it in `axes_present` when it cannot derive it. AXIS-ABSENT → dormant; AXIS-NULL → refuse |
| **capability-tolerant, skew-safe** — a wheel landing ahead of its call sites stays inert; a version-skewed fleet does not start refusing | K-2/K-3 can land before K-1 is fully rolled and stay dormant. **CAP-SIG is what makes this true and is therefore not optional** (§3.1) |
| **NO-COALESCE, structurally** | §3 NON-ALIASING clause 2, same words, new pair |
| **non-throwing derivation, one deliberate raising surface** | the reduction must never raise on a malformed map; a malformed map is AXIS-NULL |

> **Do not attempt the previous lane's *shape*.** The content axis shipped
> consumer-side with **zero** producer work because
> `content_watermark_returned` is derivable from the returned rows. **Verification
> recency is not consumer-derivable** — there is no per-row "confirmed at" datum
> and there cannot be one, because the fact being reported is about a *fetch
> event*, not about a row. A design that pretended otherwise would be deriving it
> from something else, which is exactly how a build stamp became a freshness axis
> in the first place.

### 7.4 Parallel tracks (P-11)

| track | scope | why not in the lane |
|---|---|---|
| **DEFECT-1 / G-2** — optimistic concurrency on the manifest write | own PR, own attribution, producer correctness | blast radius wider than this gate (metrics CLI, resume path, checkpointing). Its absence **caps this gate's pass rate by an unknown amount** — named as a known-unknown in the telos rather than discovered post-ship |
| **DEFECT-2 root cause** — the write path permitting a backward stamp | own PR | G-1 neutralises the *effect* on this axis; the *cause* is producer correctness |
| **ECS task-id dimension on the probe log line** | one log field | the falsifier for §2.5's **MODERATE** mechanism diagnosis. Should land **before or with** G-2 so the mechanism is confirmed rather than inferred |

### 7.5 Blast radius and reversibility

| surface | change | radius | reversibility |
|---|---|---|---|
| `SectionInfo` / manifest JSON | +0 fields (P-6 changes **when** an existing field is set; G-3 adds a provenance value) | all manifest readers | **two-way** — semantics only |
| `watermark.json` sidecar | +2 optional keys | all sidecar readers; legacy objects read as absent | **two-way** — additive, precedented |
| `DataFrameCacheEntry` | +2 fields | in-process only | **two-way** |
| `FreshnessInfo` | +2 fields | in-process only | **two-way** |
| **`RowsMeta` + `AggregateMeta`** | **+3 fields on BOTH** (`extra="forbid"`) | **every `/rows` and `/aggregate` consumer** | **⚠ ONE-WAY DOOR — see below** |
| `QueryMeta` (autom8y-core) | +3 declared fields | every SDK consumer, fleet-wide | **two-way** — `extra="ignore"`, additive |
| ASR offer-axis combiner | new conjunct | **the offers gate's behaviour** | **two-way** — one predicate, revertible in one PR |
| the query engine's freshness-meta reducer | + the §2.3 classifier-scoped reduction | **every** query response, both endpoints | **two-way**, but it is the **hot serve path** — the reduction must be **O(sections), not O(rows)**, and must **never raise** |

> ### ⚠ THE ONE-WAY DOOR — requires explicit stakeholder acknowledgment at ratification
>
> **Adding fields to the public `RowsMeta` / `AggregateMeta` contract.**
>
> Additive **emission** is safe and reversible. What is **irreversible** is that
> **once any consumer gates on `verification_age_seconds`, withdrawing the field is
> a breaking change to that consumer.** The public meta contract is fleet-visible,
> and this crusade's whole history is of consumers acquiring dependencies on
> fields whose meaning nobody re-checked.
>
> Every other row above is a two-way door. **This one is not, and the ratification
> should acknowledge it explicitly rather than absorb it.**

### 7.6 Exit criteria — what "built" means

1. **A live consumer log line showing `verification_age_seconds`** (§2.9). Not
   "asana emits it." Not a unit test. A consumer log line. Legs 3→4 and 4→5 have
   each killed a field already.
2. **Both meta models carry all three fields**, verified together — a field on one
   and not the other raises (§2.9).
3. **The reduction denominator is observed to include zero-row classified
   sections** — the P-5 invariant, tested against the §4.5 pinned-floor scenario as
   a regression fixture.
4. **`PRESERVE_PRIOR_GOOD` is observed not to advance the stamp** — the §2.8 Hop-1
   invariant, tested.
5. **A missing sidecar key reads AXIS-NULL, never `now()`, never a fresh-reading
   decay anchor** (§2.6), tested.
6. **The stamp-and-bytes coupling invariant is tested, not assumed** (§6.1
   concession).
7. **Then, and only then:** the 14-day soak against the P-4 stage-2 bar
   (≥95 % healthy-pass / ≤8 h detection), which is also KS-3's measurement.

---

## §8 — Open items

### Carried from the ruling

| id | item | status |
|---|---|---|
| **O-1** | **D-5b — the content threshold's afterlife.** **HOLD (parked)** per P-10. *"The threshold's afterlife is unruled until the verification gate is LIVE."* **Revisit trigger: gate-live.** *(Diverged from the recommendation [retire; keep 3600 as an anomaly line]; recorded as ruled, not re-argued.)* | **PARKED** |
| **O-2** | **F-GUARD 60 s future-skew allowance.** Formally **bound to the parked D-5b card**; carries with the park, unresolved. Verified live at consumer `origin/main`: `offer_axis_future_skew_allowance_seconds: float = 60.0`, carrying its own in-code UV-P (*"60s is a judgement, not a measurement"*) and its own re-baselining channel (the clamp-band disclosure logs). **Deliberately its own quantity** — not derived from the staleness threshold, because one number serving two axes is how an availability bound ends up gating freshness. **Note for the gate-live revisit:** F-GUARD is a **content-axis** guard. Whether the verification axis needs its own future-skew allowance is **unruled and unasked** — a verification instant dated in the future is as much a false-fresh generator as a content watermark dated in the future, and `min()` does not shield it. **Recommend adding this to the D-5b card at its revisit rather than deciding it here.** | **PARKED WITH D-5b; one sub-question newly surfaced** |
| **O-5** | **P-3's no-clock posture.** Honest aborts continue indefinitely; the successor's landing is the only exit. There is deliberately **no** review horizon. Recorded so a later seat does not mistake the absence of a clock for an oversight. | **RULED, no action** |
| **O-6** | **Stage-1 items awaiting operator action** (P-7): apply (a)+(b) *(one apply)*; apply (c) *(monorepo)*; route (d). Plus the stage-1 artifact's own open question — dropping `ok_actions` on AL-5 was **outside the authorized lever set and NOT authored**, though it is named as the single biggest remaining noise lever. | **AWAITING OPERATOR** |

### The re-baseline gate

| id | item | status |
|---|---|---|
| **O-7a** | **The AL-5 threshold re-baseline: ≥48 h of post-rollout data, i.e. from ~2026-08-14T11:04Z.** Boundary receipted: PR #339 merged `2026-08-12T10:24:13Z`; ECS task definition `:762` reached `rolloutState COMPLETED` at `2026-08-12T11:04:18Z`. **Only after that window may the AL-5 threshold be set**, and only from the serve contract — never from the dead consumer alignment. It carries a **falsifiable prediction**: alarm duty at threshold 7200 will **RISE**, not fall. **If duty instead collapses toward 0 %, the regime assumption is wrong and the tuning must be re-opened.** | **GATED, date-certain** |
| **O-7b** | **V's own re-baseline trigger** (§4.4) is a *different* gate on a *different* quantity, and the two must not be conflated. O-7a re-baselines an **alarm threshold** against the post-#339 serve regime; V re-baselines a **gate threshold** against **warm cadence**. They share a repo and nothing else. V's trigger fires on any change to warm scheduling, entity TTL, or Lambda concurrency — and it **has already fired once** inside the measurement window (`bc620e18`, 2026-08-05). | **BOOKED, trigger-driven** |

### Found unruled or ambiguous by this ADR

| id | item | recommendation |
|---|---|---|
| **O-3** | **The `backfill_used` spelling.** P-12 names the field **`backfill_used`**; the proposal it ratifies "as proposed" names it **`verification_backfill_used`**. Under a fence whose first principle is *spelling is load-bearing*, this cannot be resolved silently. | **RECOMMEND `verification_backfill_used`** — it is what "as proposed" points at; it is prefix-consistent with the family, which is what makes the §3 NON-ALIASING near-miss list enforceable; and a bare `backfill_used` would collide with any future non-verification backfill flag. **One-word operator confirmation.** |
| **O-4** | **How the metrics CLI expresses "unprovable" after Decision-6 is overruled.** P-8 rules one principle across both surfaces and P-6 retires the `written_at` fallback, so the CLI must stop degrading to `mutation_age`. **What it does instead** — non-zero exit under `--strict`, a distinct unprovable state in the `--json` envelope, or an alarm-only disposition — **is unruled.** | **RECOMMEND** it be settled inside the CLI leg against ADR-001's retained exit-code matrix, **not decided here**. It is a surface-local expression of a ruled principle, not a new principle. Flagged because silently choosing it would inscribe an unruled decision. |
| **O-8** | **A classified section name that resolves to no manifest section at all.** §2.3(b) rules an absent stamp → AXIS-NULL → ABORT, which closes the hole. But it means a **classifier-vocabulary drift** (a name in the classifier that Asana no longer has) would refuse the source **permanently and silently-as-to-cause**. | **RECOMMEND** the strict form as drafted (refuse — a vocabulary drift is a genuine defect worth refusing on), **plus a distinct disclosure counter** that names *which* classified section is unresolvable, so the abort is diagnosable in one log line rather than by inference. **K-0a measures whether this is a live risk today** (criterion 1: all 27 names resolve). |
| **O-14** | **The "1.0× the consumer contract" framing rests on a referent inference, not a quotation** (§4.1 receipt). The verified 8 h bounds `now − verdict_at` on the **published verdict surface** ("two missed runs"), not the age of the data behind a verdict. The two horizons compose coherently — the surface goes stale exactly when the gate has been refusing for the full window — but no artifact states an input-data-age tolerance. | **RECOMMEND** ratifying 28 800 s on the **horizon-alignment** argument as stated at §4.1 (the gate's refusal horizon equals the surface's staleness horizon), **not** on the phrase "the consumer's own stated tolerance", and **RECOMMEND** the ADR's own §4.1 wording be treated as the canonical framing wherever this number is later cited. If the operator wants an actual declared input-data-age tolerance, that is a **new ruling** on the consumer contract and is not available from the current record. |
| **O-9** | **ADR number collision.** Two `ADR-007-*` files already exist in `.ledge/decisions/` (`ADR-007-cw-namespace-tri-partition.md`, `ADR-007-verify-denominator-congruence.md`). This artifact is at the path the charge specifies and is disambiguated by its dated filename and `artifact_id`, but the **bare number `ADR-007` is now triple-booked** and any future citation of "ADR-007" is ambiguous. | **RECOMMEND** citing this record **only** by its full `artifact_id` (`ADR-007-verification-axis-gate-2026-08-12`), never by the bare number; and **RECOMMEND** a separate renumbering hygiene item rather than renumbering inside this initiative. |

### Premise corrections and basis drift found at authoring time

| id | item | status |
|---|---|---|
| **O-10** | **[CORRECTION-1]** The annex's §3.5 synthetic-`now()` hydration fallback **is closed at producer HEAD** by `#338` (`2601c8c5`), which post-dates the annex's `cc20772e` basis. §2.6 restates the obligation as **preservation**, not introduction. **Inheriting the annex's wording unchanged would have inscribed a fixed defect as an open one.** | **CORRECTED, no action** |
| **O-11** | **[CORRECTION-2]** The autom8y working tree as checked out sits on `fix/wss-wildcard-scope-bypass-closure` @ `1bb00c3c`, which is **NOT an ancestor of `origin/main`**. Against that branch, `combine_offer_axis`, `asana_freshness`, `autom8y-core 4.14.0` and the `QueryMeta` axis fields **do not exist** — the offers readiness block there still reads `data_age_seconds` (the build axis) and there is no axis-selection layer at all. **Every one of them resolves at `origin/main` = `6fc556d8`,** and all consumer anchors in this ADR were re-verified there. | **RECORDED — a re-checking hazard.** Any seat verifying this ADR **must pin `origin/main`**; a local checkout will produce false negatives that read like a falsification of the K lane |
| **O-12** | **Consumer basis drift.** The annex pinned `c21cab9d` and recorded `8589b4be` as "today's `origin/main`"; `origin/main` is now `6fc556d8`. The drift is **recorded rather than absorbed**, per the annex's own precedent. `fetcher.py:504,512` and `fetcher.py:413-427` both still resolve; the contract's own `fetcher.py:312,321` citation predates the cure and no longer resolves. **Three artifacts cite three different line numbers for the same two calls** — which is the ordinary cost of line-anchored citation across a moving tree, and the reason each of this ADR's receipts names its basis SHA. | **RECORDED** |
| **O-13** | **The unrun cheapest falsifier.** The `source-coverage-3of3-deadman` UV-P (§6.2) came from the annex, was never run, and is carried forward unrun. It is the single cheapest falsifier of the argument that rejects Option 5. | **CARRIED, unrun** |

---

## §9 — Evidence ledger and grading

| claim | grade | basis |
|---|---|---|
| No content-age threshold works (0/175 at deployed 3600 s; 47.6 h for 95 % not-ABORT) | **STRONG** | W-1: 10 239 probe records, 29 d, 3/3 ticks reconstructed to ±0.000000 s; rite-disjoint |
| V = 14 400 → 100 % PASS on every tick grid; 2V never crossed | **STRONG** | age-at-tick evidence: invariant across 5 perturbations, 2 event families, 3 grids, 2 causality treatments; rite-disjoint |
| Length-bias refutation (CV < 1; closed-form matches measurement to 0.06 %) | **STRONG** | `E[G²]/(2E[G])` matches on both series independently |
| Nine inter-build gaps exceed 14 400 s over 30 d; `max(gap)` = 14 568 s; margin at observed tick max = 76 s | **STRONG** | direct measurement; **falsifies the annex's stated ground for V** (§4.3) |
| Weekend non-degradation | **STRONG** | 4 weekends, 2 series, 2 grids, consistent direction |
| The abort line at 2V is 28 800 s = 8 h | **STRONG** | arithmetic: 14 400 × 2.0 = 28 800 |
| The consumer contract's 8 h exists and is verified | **STRONG** | direct read at consumer `origin/main`, SVR §4.1 |
| That 8 h is a **data-age** tolerance | **REFUTED AS STATED** | the verified referent is `now − verdict_at` on the published verdict surface ("two missed runs"), not input-data age. The horizon-alignment argument survives; the borrowed phrasing does not. §4.1, §8 O-14 |
| The WARN/FAIL boundary is not independently settable | **STRONG** | direct code read at consumer `origin/main`, SVR §2.1 |
| The verification stamp requires a live Asana round-trip | **STRONG** | single assignment site downstream of three guards, SVR §2.2; corroborated by W-1's 7 227 wire observations |
| The CLI reader's denominator is ACTIVE-only and wrong for this gate | **STRONG** | direct code read, SVR §2.3 |
| An ACTIVE+ACTIVATING accessor already exists on the classifier | **STRONG** | direct code read, SVR §2.3 |
| FIX-1's coherently-empty stamp exemption is live at producer HEAD | **STRONG** | direct code read, SVR §2.3 |
| `mark_section_failed` destroys the stamp; `mark_section_complete` carries it forward | **STRONG** | direct code read of both, SVR §2.3 |
| The synthetic-`now()` hydration fallback is closed at producer HEAD | **STRONG** | direct code read, SVR §2.6 |
| Both meta models are `extra="forbid"` and share one side-channel | **STRONG** | direct code read + a standing in-code mirror comment, SVR §2.9 |
| `min()` exposes the verification axis where `max()` shielded content | **STRONG** | arithmetic on the stated aggregations |
| Under P-5, the same 6.7-day corpus window reads 100 % frame-level and 0/37 per-section | **MODERATE** | arithmetically exact **given** UV-P-3, which is unresolved by construction; per-section stamp identity was inferred from pass-level counts, not read |
| DEFECT-1's mechanism (process-local lock + never-expiring cache + unconditional PUT) | **MODERATE** | three code anchors give a **sufficient** mechanism; not proven to be the observed cause. Falsifier: the ECS task-id log dimension (§7.4). Corroborated by 15 sub-120 s adjacent stamp passes with different trace_ids |
| `written_at` is a genuine verification instant on the just-fetched path | **MODERATE** | code read; the *inference* that a completion always follows a live fetch is a code read, not a measurement |
| Option 5's deadman is blind to the frozen-frame case | **MODERATE** | the completion deadman was read directly; the source-coverage deadman was **not** (§6.2 UV-P) |
| V = 14 400's pass rate **at the gate's actual grain** | **UNMEASURED** | UV-P at §4.6 — the field does not exist in production |
| Prod state of `last_verified_at` across the full classified population | **UNMEASURED** | UV-P at §7.2 (K-0a / B3-a) — no artifact in this crusade has read that object |
| Segment D (the current, best regime) | **MODERATE** | 7 days / 43 organic ticks only; the cadence changed inside the window; 30-day retention is a hard ceiling |

**Document evidence ceiling: MODERATE.** Self-referential design authorship — the
architect proposing the design is grading it, per `self-ref-evidence-grade-rule`.
The empirical legs (W-1; the age-at-tick evidence) carry **STRONG** independently
and are **rite-disjoint**; the *design* claims do not inherit that. **STRONG on
the design would require K-0a to run and an adversarial read by a rite-disjoint
seat.**

**All SVR receipts in this document were verified by direct read at authoring
time** against producer `4129ae7e` (working tree clean for `src/`) and consumer
`origin/main` `6fc556d8` — not inherited from the annex. Two inherited premises
failed that read and are recorded as O-10 and O-11 rather than propagated.

---

## §10 — Fence compliance

Design and governance only. **No production code authored or modified. No
infrastructure mutation. No deploy. No threshold moved. No Lambda invoked. No
request to the serve path. No Asana API call. No S3 object read. No AWS call of
any kind.** No frozen artifact modified: `CONTRACT-offers-freshness-axis-frozen-2026-08-11.md`,
`ADR-006-freshness-equals-verification-recency.md`, and every `RULING-*` record
were **read only** — this ADR **quotes** them; ratification executes the edits
later.

**Reads:** `git` (producer working tree at `4129ae7e`, verified clean for every
cited `src/` path; consumer via `git show origin/main:<path>` at `6fc556d8`) and
the six artifacts named in the charge.

**Status: `draft`.** It goes to the operator for ratification. The two signature
items are §3 (the amendment TEXT) and §4 (V = 14 400). Nothing in this document is
in force until those are ruled.


---

## RATIFICATION RECORD (appended 2026-08-12)

The binding record of this ADR's ratification sitting is
`RULING-operator-adr007-ratification-2026-08-12.md` (7 rulings). Summary:
R-i AMENDED-RATIFIED (grain advisory; P-5 operative; R-alt governs change) ·
R-ii RATIFIED-PROVISIONAL (soak-close auto-disposition) · R-O3
DELEGATED-WITH-INSCRIPTION (spelling decided at producer-leg PR, fence amended
same PR) · R-O14 REFUSED-AS-POSED (no citation-framing constraint) · R-O4
DELEGATED (CLI leg vs ADR-001 exit-code matrix) · R-O8 HOLD (trigger: K-0a).
Status advances draft → **ratified-provisional**; the build plan (§7) is
unblocked in full.
