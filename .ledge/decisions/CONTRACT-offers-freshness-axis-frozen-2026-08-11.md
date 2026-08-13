---
type: spec
station: S2-0
gate: SPEC-FREEZE (T4)
crusade: offers-false-staleness-cure
sprint: sprint-20260811-offers-false-staleness-cure-wave1
session: session-20260811-115247-a1ccd942
rite: 10x-dev
role: architect
date: 2026-08-11
status: FROZEN
mode: TRANSCRIPTION-ONLY — no clause authored at this station; zero writes outside this path; no src/ touched, nothing warmed, no ari commands
source: .sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md
source_line_range: 143-639
verbatim_core: §C, between the extraction-fence markers — byte-for-byte identical to the source range AS OF THE [A-2026-08-12] AMENDMENT. The unqualified pre-amendment guarantee ("byte-for-byte identical to the source range") held from 2026-08-11 until 2026-08-13, when §1.2 was amended in place by operator ruling. §B carries both baselines and the re-baseline rationale.
ratified: 2026-08-11 (operator ratification of the composition)
amended: 2026-08-13 (ADR-007 §3 applied in place per operator ruling — RULING-operator-morning-set-2026-08-13 R-3 plus the four ambiguity rulings of the same sitting; the amendment block is tagged [A-2026-08-12] after its ratifying ruling, RULING-operator-adr007-ratification-2026-08-12 R-i; superseded §1.2 text struck and left standing per precedent [A-2026-08-03] — CHARTER-substrate-v2-epoch-2026-07-27.md, PR #298, merge 9797579c; §E.2 roster twelve → fifteen per ADR-007 §3.1; status FROZEN deliberately unchanged, per the same precedent)
adjudication_lineage: pythia round 1 (FORK-A..D + QUARANTINE) -> round 2 (FORK-A re-plead) -> round 3 (rite-disjoint audit; INCOMPLETE ruling on the v1 slate; lanes I/J/K; CAP-SIG requirement; D-1 RATIFIED; D-5 RULED; D-5b framed) -> operator ratification 2026-08-11
signatories_required: K-ASR, K-SDK, FIX-N-B, FIX-N-C1
open_nonblocking: D-5b (freshness-axis authority — framed, not decided; decide post-K)
w2_f5_flags: none (intra-fence; see §D.7)
w2_f1b: UNRESOLVED — AXIS-ABSENT token carries two referents with opposite dispositions (fence §1.5b consumer rule = never-a-refusal; source §3.7 H-1 / Lane-K binding caveat = loud refusal). Adjudication rides the W2-F1 pythia dispatch at gate G1. BOTH K LIMBS ARE FORBIDDEN TO IMPLEMENT EITHER DISPOSITION UNTIL RULED. See §D.8.
evidence_ceiling: inherited from source §5 — SPLIT (AUDITED for round-3-confirmed claims; MODERATE for lanes J/K and FINDING-3). This artifact adds no evidence and lifts no ceiling.
---

> ## 📍 CANONICAL LOCATION — promoted 2026-08-13 by operator ruling
>
> This file was authored at `.sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md`.
> `.sos/*` is gitignored (`.gitignore:90`), so **the contract of record had no
> durable home** — it could not be PR'd, and a fresh clone would not have it.
> `FINDING-k0c-contract-has-no-durable-home-2026-08-12.md` established that K-0c
> therefore could not follow its own precedent, which operated on a **tracked**
> `.ledge/decisions/` file.
>
> **Operator ruling `RULING-operator-morning-set-2026-08-13.md` R-3: promote.**
> **This path is now canonical.** The `.sos/wip/` copy is retained as a working
> mirror carrying a pointer here; cite THIS path.
>
> Content is byte-identical to the `.sos/wip/` original at promotion time. The
> `verbatim_core` transcription fence and the FROZEN status are unaffected — this
> ruling moved the file, it did not touch a clause.
>
> **K-0c is NOT discharged by this promotion.** It additionally requires the
> ratified §3 amendment applied in place, superseded text struck and standing,
> in one PR. That is the next step, not this one.

# CONTRACT — offers freshness axis (FROZEN)

> **Nothing in this artifact is authored.** §C is a byte-for-byte transcription of
> DESIGN v2 §1 — the frozen watermark contract — as ratified by the operator on
> 2026-08-11. The framing sections (§A, §B, §D, §E, §F) are thin scaffold:
> provenance, fidelity receipt, status ledger, build-prompt quote block, and
> signature slots. **On ANY divergence between framing and fence, THE FENCE IS
> AUTHORITATIVE.** No field was added, renamed, reordered, or "improved" at this
> station.

This is the ONE artifact both K limbs and both FIX-N legs sign. It exists so that
four independently-built legs speak one vocabulary. Cross-limb skew is the failure
mode this station exists to prevent; §E is the structural defense.

> **⚠ READ §D.8 BEFORE BUILDING ANY K LEG — COLLISION NOTE W2-F1b, UNRESOLVED.**
> The token **AXIS-ABSENT** carries **two referents with opposite dispositions**
> (never-a-refusal vs loud-refusal). Adjudication rides the W2-F1 pythia dispatch
> at gate G1. **Both K limbs are FORBIDDEN to implement either disposition until
> it is ruled.** This freeze records the discrepancy; it does not resolve it, and
> nothing in this artifact should be read as picking a side.

---

## §A PROVENANCE

| Field | Value |
|---|---|
| **Source file** | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md` |
| **Source line range** | **143–639** (inclusive) |
| **Range derivation** | starts at the line `## §1 THE FROZEN WATERMARK CONTRACT` (L143); ends at the last line before `## §2 OPTION SLATE` (L640) — so the trailing `---` separator at L638 and the blank at L639 are inside the fence, as authored |
| **Source revision** | v2 — re-issued over lanes A–K per the round-3 INCOMPLETE ruling |
| **Source code basis** | asana `origin/main @cc20772e80a34b750e0dcab3e9639e8cb1ac7a20` (all reads via `git show origin/main:<path>`); consumer claims from the autom8y monorepo `origin/main` |
| **Ratified** | **2026-08-11** — operator ratification of the composition |
| **Adjudication lineage** | pythia **round 1** (FORK-A HOLD-P6 + narrow FIX-2 door; FORK-B three-axis mandate, content-only advancement, null→decay; FORK-C co-sourcing; FORK-D decay-only/all-tiers-stale-aborts-loud; QUARANTINE of `is_fresh_by_watermark`) → **round 2** (FORK-A re-plead: `tiers/progressive.py:187-189` admissible as FIX-N) → **round 3** (rite-disjoint audit: INCOMPLETE ruling on the v1 slate; lanes I/J/K supplied; the CAP-SIG requirement; the K-GATE resolution; **D-1 RATIFIED**; **D-5 RULED**; the **D-5b** framing) → **operator ratification 2026-08-11** |
| **This station** | S2-0 SPEC-FREEZE (T4) — BLOCKING and SEQUENTIAL. Transcription only. |

**What this artifact is.** The single frozen contract surface. The wire-field
names, the advancement law, the null semantics, the co-sourcing invariant, the
capability signal, the consumption rule, the alarm re-homing rule, the
non-aliasing clause, and the explicit non-promises — exactly as ratified.

**What this artifact is NOT.** It is not the option slate (source §2), not the
hazard register (source §3), not the operator card list (source §4), and not the
evidence-and-fences section (source §5). Those remain in the source and are cited
here only where §D needs their dispositions.

---

## §B TRANSCRIPTION FIDELITY & NORMALIZATION LEDGER

> **⚠ THIS SECTION CARRIES TWO BASELINES.** BASELINE-1 is the original
> 2026-08-11 transcription receipt and is preserved verbatim as the historical
> record. BASELINE-2 is the **re-baselined** receipt taken after the
> [A-2026-08-12] amendment was applied in place on 2026-08-13 by operator
> ruling. **A reader running BASELINE-1's command today will get a NON-EMPTY
> diff. That is intentional and is not corruption** — BASELINE-2 states exactly
> what the delta is and why.
>
> **The fence's guarantee has changed** from *"byte-identical to source"* to
> ***"byte-identical as of the [A-2026-08-12] amendment."*** The frontmatter
> `verbatim_core` field carries the same qualification.

### §B.1 BASELINE-1 — original transcription receipt (2026-08-11, pre-amendment)

**Normalization ledger: EMPTY.** No character was substituted, no line wrapped or
reflowed, no bold label promoted to a heading, no blank line added or removed, no
whitespace altered. The em-dashes (U+2014), section signs (U+00A7), prime (U+2032),
warning sign (U+26A0), less-than-or-equal (U+2264), multiplication sign (U+00D7),
rightward arrows (U+2192), and the source's straight ASCII quotes and apostrophes
are carried verbatim into §C.

**Mechanical check.** The check extracts the lines lying strictly between the two
extraction-fence markers of §C and diffs them against `sed -n '143,639p'` of the
source. Exact commands:

```sh
SRC=".sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md"
OUT=".sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md"

# extract the fenced region from THIS artifact, diff against the source range
diff <(sed -n '143,639p' "$SRC") \
     <(awk '/^<!-- BEGIN VERBATIM CORE /{f=1;next} /^<!-- END VERBATIM CORE -->$/{f=0} f' "$OUT")
echo "exit=$?"
```

**Result: EMPTY DIFF — zero byte-deltas, exit 0.** The command produced no output
other than `exit=0`. Line counts agree at **497** lines on both sides.

The extraction-fence markers and this record's `§A`–`§F` headings are framing
scaffold: they lie outside the diff target and are therefore **not** byte-deltas
against the core. The framing deliberately uses letter section numbers so it can
never be confused with the fence's own `§1.x` numbering.

**This receipt held unconditionally from 2026-08-11 until 2026-08-13.** It is
superseded as the current-state receipt by §B.2 and retained as the record of
what the fence guaranteed before the amendment.

### §B.2 BASELINE-2 — re-baselined receipt (2026-08-13, post-amendment)

**Why this changed.** ADR-007 §3's ratified amendment targets **§1.2, which lies
inside the extraction fence** (fence line 39 onward). ADR-007 nowhere addresses
the transcription fence — the words `verbatim_core`, `extraction-fence` and
`byte-for-byte` appear nowhere in it — so applying the amendment necessarily
falsified BASELINE-1. **The operator ruled on 2026-08-13: amend in-fence and
re-baseline this receipt, recording why it changed**, so that a future reader
running BASELINE-1's command sees an intentional re-baseline rather than
corruption. The alternative — sealing the fence and carrying the amendment
elsewhere — was considered and not chosen.

**Mechanical check (canonical path).** Same extraction, run against the promoted
`.ledge/decisions/` location rather than the `.sos/wip/` original:

```sh
SRC=".sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md"
OUT=".ledge/decisions/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md"

diff <(sed -n '143,639p' "$SRC") \
     <(awk '/^<!-- BEGIN VERBATIM CORE /{f=1;next} /^<!-- END VERBATIM CORE -->$/{f=0} f' "$OUT")
echo "exit=$?"
```

**Result: NON-EMPTY DIFF — exit 1. Expected.** Measured 2026-08-13:

| quantity | value |
|---|---|
| hunks | **2**, both inside §1.2 |
| hunk 1 | `41,45c41,70` — the struck advancement law (5 source lines → 30) |
| hunk 2 | `47,50c72,190` — the struck FORK-B paragraph (4 source lines → 119) |
| source lines superseded | **9** |
| replacement lines | **149** |
| fenced line count | **497 → 637** |

**The delta is CONFINED to §1.2.** Two hunks, no others. Fence lines 41–45 and
47–50 correspond exactly to the two struck blocks; every other line of the
497-line core is byte-identical to `sed -n '143,639p'` of the source, including
**all of §1.2b**, which this amendment explicitly preserves. Any future run
producing a hunk outside those two ranges is **not** this amendment and should
be treated as corruption.

**Normalization ledger: ONE ENTRY** (BASELINE-1's ledger was EMPTY).

| # | normalization | rationale |
|---|---|---|
| N-1 | **One blockquote level removed.** ADR-007 §3 presents the amendment nested one `>` deep (it is quoting the contract). Transcribed here at the contract's own nesting, so the law renders as a `>` blockquote exactly as the superseded law did. | Formatting only. No character of the amendment's own text was substituted, wrapped, reflowed, or reordered. Not clause work. |

**⚠ KNOWN GAP, DISCLOSED NOT FIXED — this receipt is not reproducible from a
fresh clone.** `$SRC` is `.sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md`,
and `.sos/*` is gitignored (`.gitignore:90`; `git ls-files` returns no match).
**This was already true of BASELINE-1** — the promotion ruling
(`RULING-operator-morning-set-2026-08-13.md` R-3) moved the *contract*, and that
ruling explicitly leaves the wider `.sos/wip` corpus unruled (§2 item 10). The
source is therefore **not** promoted here: doing so would act on a ruling that
does not exist. Consequence to carry: **both baselines are verifiable only from
a working tree that still holds the untracked source.** This is the
`ratified ≠ durable` shape named in
`FINDING-k0c-contract-has-no-durable-home-2026-08-12.md`, surviving one level
down in the fence's own provenance.

---

## §C OPERATIVE CORE (VERBATIM) — DESIGN v2 §1

The block between the extraction-fence markers below is **byte-for-byte** identical
to `.sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md:143-639`.

<!-- BEGIN VERBATIM CORE DESIGN-s1-arch-watermark-contract-2026-08-11.md:143-639 -->
## §1 THE FROZEN WATERMARK CONTRACT

> **The keystone.** One canonical answer, consumed by all surfaces: asana emits,
> ASR reads, alarms alarm. This section is the thing that must not have two
> versions.

### §1.1 The three axes — names, types, grain, provenance

Grain for all three: **(project_gid × entity_type)** — the existing cache-key
grain, `f"{entity_type}:{project_gid}"` (`dataframe_cache.py:1189-1191`).

| # | Axis | Field (wire name) | Type | Derivation | Source of raw material | May advance freshness? |
|---|------|-------------------|------|------------|------------------------|------------------------|
| **1** | **CONTENT** (primary) | `content_digest` | `str` (sha256 hex) \| `null` | `substrate.freshness.canonical_digest` over pinned value columns | `substrate/freshness.py:145-281`; pins `("cost","mrr","offer_id","weekly_ad_spend")` at `:154` | **NO** — identity, not recency. Detects change; cannot date it. |
| **1b** | **CONTENT — frame-scoped** (producer-only) | `content_watermark` | ISO-8601 UTC `str` \| `null` | `max(last_modified)` over the **whole served frame**, before filter/limit | column: `dataframes/schemas/base.py:76-82` (nullable=False, `source="modified_at"`); model: `models/task_row.py:50`; capture: `builders/progressive.py:1877` | **YES — an axis that may.** |
| **1b′** | **CONTENT — result-scoped** (consumer-derivable) | `content_watermark_returned` | ISO-8601 UTC `str` \| `null` | `max(last_modified)` over the **rows in THIS response**, after filter + limit | same column; derivable by producer OR consumer (Lanes J/K) from `data[]` | **YES — an axis that may**, under the §1.2b truncation guard |
| **1c** | derived | `content_age_seconds` | `float` \| `null` | `(now_utc - {the gating watermark}).total_seconds()` | — | derived; carries its source's null |
| **1d** | **CAPABILITY** (frozen requirement, §1.5b) | `axes_present` | `list[str]` | the axis field names this producer actually speaks | producer-declared | **NO** — it disambiguates AXIS-ABSENT from AXIS-NULL |
| **2** | **BUILD** | `frame_built_at` **(NOT `built_from_live_at`, see §1.8)** | ISO-8601 UTC `str` | the existing unconditional `datetime.now(UTC)` at build | `builders/progressive.py:1130` (`watermark = datetime.now(UTC)`) | **NO — never readable as freshness.** |
| **2b** | **BUILD** | `served_entry_stamped_at` | ISO-8601 UTC `str` | the serving entry's `created_at` | `dataframe_cache.py:891` (memory put) / `cache/dataframe/tiers/progressive.py:207` (S3 hydration) | **NO — process-local. This is today's `data_age_seconds` anchor.** |
| **3** | **FETCH-LIVENESS** | `fetched_rows` | `int` \| `null` | `BuildResult.fetched_rows` | `builders/build_result.py:193-196` (SUCCESS sections only, excludes resumed) | **NO — liveness, not recency.** |
| **3b** | **FETCH-LIVENESS** | `sections_fetched` | `int` \| `null` | `BuildQuality.sections_succeeded` | `builders/build_result.py:316-323` | **NO** |
| **3c** | **FETCH-LIVENESS** | `sections_total` | `int` \| `null` | `BuildQuality.sections_total` | `builders/build_result.py:317` | **NO** |

**Why three axes and not one.** Each answers a different question and no two are
substitutable:

- **Content** answers *"how old is the newest fact in these bytes?"* — the only
  question a freshness gate has any business asking.
- **Build** answers *"when did this artifact get assembled?"* — a deployment and
  cadence observable. `frame_built_at` tracks the build clock to within ~0.5s of
  build start **even when `fetched_rows=0` and `sections_delta_updated=0`**
  (three live builds, DIAG-S1 F1.6). It is a tautology dressed as freshness;
  re-pointing a gate at it is the failure mode DIAG-S1 explicitly names.
- **Fetch-liveness** answers *"did anything actually come back from Asana?"* —
  the axis that distinguishes "the frame was rebuilt" from "the frame's data is
  current" (DIAG-S1 F1.7 constraint: two numbers, not one).

### §1.2 The advancement law (frozen)

> ~~**Only a CONTENT axis may advance freshness — `content_watermark`
> (frame-scoped) or `content_watermark_returned` (result-scoped).
> `frame_built_at`, `served_entry_stamped_at`, `fetched_rows`,
> `sections_fetched`, `sections_total` and `axes_present` are DISCLOSURE
> fields. No consumer may gate freshness on them, and no emitter may
> substitute one for a content axis.**~~
>
> ~~This is FORK-B as adjudicated (2026-08-11), and it is the same law the v2 seam
> already encodes: *"freshness is content-derived truth, never a write-time stamp"*
> (`substrate/freshness.py:10-11`) and *"no API on this S2 surface advances an
> instant without a content fetch"* (`:13-14`).~~
>
> **— SUPERSEDED IN PLACE by [A-2026-08-12]. Text retained per precedent
> [A-2026-08-03] (charter amendment #298): a superseded clause is struck and
> left standing, never deleted, so the record shows what was believed and when
> it stopped being believed.**
>
> **Scope of the strike — operator-ruled 2026-08-13.** The FORK-B paragraph is
> struck **with the law it restates**: it asserts the content-only advancement
> rule that [A-2026-08-12] supersedes, so leaving it standing un-struck would
> leave the superseded law asserted in prose directly beneath its own
> replacement. **The strike removes a superseded *assertion*; it does not
> discard *evidence*.** The two code citations that paragraph carries are
> preserved here for that reason —
> `substrate/freshness.py:10-11` (*"freshness is content-derived truth, never a
> write-time stamp"*) and `substrate/freshness.py:13-14` (*"no API on this S2
> surface advances an instant without a content fetch"*). Those observations may
> still be true of the v2 seam on their own terms; what is superseded is the
> inference that they exhaust the set of axes permitted to advance freshness,
> not the reading of what the seam encodes.

> **[A-2026-08-12 — AMENDED IN PLACE, operator-ruled]**
>
> **Exactly two axis families may advance freshness: CONTENT and VERIFICATION.**
>
> - **CONTENT** — `content_watermark` (frame-scoped) or
>   `content_watermark_returned` (result-scoped). Answers *"how old is the
>   newest fact in these bytes?"* **Unchanged in every respect by this
>   amendment**, including §1.2b's frame/result distinction, T-GUARD, and the
>   §1.2b corollary refusing monotonicity enforcement on content.
> - **VERIFICATION** — `verified_at` and its derived
>   `verification_age_seconds`. Answers *"how long since the rows in these bytes
>   were last confirmed against the live source?"* A verification axis advances
>   **only** through a per-section probe or fetch that (a) reached the live
>   source, (b) returned a verdict other than `PROBE_FAILED`, and (c) where the
>   verdict required a delta, had that delta successfully applied. It **never**
>   advances on assembly, on a build clock, on a cache write, on a fetch that
>   returned nothing, or on the passage of time.
>
> `frame_built_at`, `served_entry_stamped_at`, `data_age_seconds`,
> `staleness_ratio`, `freshness`, `stale_served`, `fetched_rows`,
> `sections_fetched`, `sections_total`, `served_tier`, `axes_present` and
> `content_digest` remain **DISCLOSURE** fields. No consumer may gate freshness
> on them; no emitter may substitute one for an advancing axis.
>
> **Which axis gates is a per-source ruling, not a per-emitter choice.** An
> emitter emits every axis it can derive; the *consumer's* ruling selects the
> gating one.
>
> **For the `offers` source that ruling is:** `PASS` iff
> `verification_age_seconds ≤ V` **AND** completeness proven per constituent.
> `content_age_seconds` is retained as DISCLOSURE and as the anomaly input for
> this source, and does **not** gate it.
>
> **VERIFICATION GRAIN (binding).** `verified_at` is the `min` over the
> **complete classification-scoped section-name set** for the request — every
> section the producer's classifier assigns to the requested classification(s),
> **including sections that carry zero rows**. A verified-empty section is
> verified and MUST be included. A classification-scoped section whose stamp is
> absent or null makes the axis **underivable for that response**: the emitter
> emits `null` and declares the axis in `axes_present` (AXIS-NULL). It is
> **never** dropped from the denominator, **never** skipped, **never**
> substituted.
>
> > **⚖ QUALIFICATION ON THE CLAUSE ABOVE — read before implementing it.** The
> > word `(binding)` in the VERIFICATION GRAIN clause is transcribed verbatim
> > from the draft as ADR-007 §3 instructs, but the ratifying ruling
> > **softened it from binding to advisory**:
> > `RULING-operator-adr007-ratification-2026-08-12.md` **R-i**. No limb may
> > reach the word `(binding)` without reaching this qualification.
> >
> > What the softening does and does not do:
> > - **P-5 remains the OPERATIVE RULING.** All classified sections — row-bearing
> >   and zero-row alike — are the population. The grain requirement still governs
> >   the build.
> > - **The advisory character spares contract-fence ceremony only. It does NOT
> >   open the denominator.**
> > - **Denominator changes follow R-alt: escalate only at the wall.** The build
> >   MUST attempt all-classified first; only a demonstrated impossibility
> >   **with receipts** may return to the operator. **No pre-emptive narrowing.**
>
> **MONOTONICITY (binding, and deliberately asymmetric with §1.2b).** A
> persisted verification instant MUST NOT move backward. §1.2b's corollary
> refuses monotonicity on the **content** watermark because a content watermark
> can legitimately decrease when rows are deleted, so a ratchet there would
> manufacture a false-fresh generator. **A verification instant cannot
> legitimately move backward, because time does not.** Monotonicity is a
> false-fresh generator on content and a truth-preserving invariant on
> verification. The asymmetry is intentional and is not an inconsistency.
>
> **NON-ALIASING (BINDING — inherits the §1.8 form and is binding for the same
> reason).**
>
> 1. `verified_at` and `verification_age_seconds` are emitted **only** as the
>    verification axis. No emitter may populate either from a build clock, a
>    cache-entry `created_at`, an S3 `LastModified`, a `written_at`, or a
>    `watermark`. An emitter that cannot derive the axis emits `null` and
>    declares it in `axes_present` (AXIS-NULL), or omits it entirely and does
>    **not** declare it (AXIS-ABSENT). Those are different states and §1.5b
>    governs both.
> 2. **No consumer may coalesce** `verification_age_seconds` with
>    `content_age_seconds` or `data_age_seconds` — no `or`, no fallback, no
>    "whichever is present" helper, no shared parse branch. A consumer that
>    wants more than one handles each in a separately-named code path. This is
>    §1.8 clause 3 applied to the new pair, binding for the identical reason: an
>    alias is how one quantity acquires another's guarantee without earning it.
> 3. **No field is ever polymorphic.** `content_age_seconds` keeps its exact
>    current meaning — result-scoped content age — permanently. It is never
>    re-pointed at another axis, never widened, never given a companion field
>    declaring "which axis this is". A field carries one axis for its whole life
>    or it is a new field.
> 4. `verified_at` is **NOT** `built_from_live_at`. The Seam-1 token remains
>    reserved exclusively for the frozen Seam-1 value object (D-1 RATIFIED,
>    §1.8). `verified_at` is a v1 quantity: a fold over per-section **probe or
>    fetch** instants, not the Seam-1 content-fetch fold. It must never carry the
>    Seam-1 name and the two must never be coalesced.
> 5. **`verification_backfill_used` is a REQUIRED companion field.** A
>    verification axis emitted without its backfill flag is unreadable and MUST
>    be treated by the consumer as AXIS-NULL.
>
> > **⚖ SPELLING PINNED BY RULING, DELEGATION STATUS FLAGGED.** The spelling
> > `verification_backfill_used` in clause 5 is **pinned by operator ruling of
> > 2026-08-13**, transcribed as the amendment writes it.
> >
> > **Flagged and unruled:** this pin stands in tension with
> > `RULING-operator-adr007-ratification-2026-08-12.md` **R-O3**, which
> > **DELEGATED** the `backfill_used` vs `verification_backfill_used` choice to
> > the architect at the producer-leg PR, with the inscription requirement that
> > the choice be recorded in that PR's body and the naming fence amended in the
> > same PR. The operator ruled the pin; the operator did **not** rule on what
> > happens to R-O3. **R-O3's delegation status is therefore FLAGGED and
> > UNRULED — nothing here discharges it**, and no limb may read this pin as
> > having discharged it.
>
> 6. **Spelling is load-bearing**, per §E.2. The forbidden near-misses are named
>    here so they are refused rather than debated: `verification_seconds`,
>    `verif_age`, `v_age`, `verified_age_seconds`, `last_verified_at` (that token
>    names the **manifest-tier** field and is already collided once inside the
>    producer repo — see the standing NOTE at `section_persistence.py:106-113`),
>    `verification_watermark`, `verified_watermark`.

### §1.2b Which content axis gates — and the truncation guard (frozen)

The two content watermarks are **not interchangeable** (FINDING-3):

- `content_watermark` (frame-scoped) answers *"how old is the newest fact in the
  artifact?"* Only a producer can compute it — the consumer never sees the frame.
- `content_watermark_returned` (result-scoped) answers *"how old is the newest
  fact in the rows I am about to act on?"* Either side can compute it.

For a gate deciding whether to reconcile **these rows**, the result-scoped
quantity is arguably the more relevant one. But it is systematically **≤** the
frame-scoped one, so it fails toward *stale* — the alarm-fatigue direction the
charter names as the original wound. It is therefore admissible **only** under:

> **T-GUARD (binding).** A consumer gating on `content_watermark_returned` MUST
> first establish that the result was **not truncated**. If
> `returned_count < total_available` for any constituent query, the result-scoped
> watermark is computed over an arbitrary window and MUST NOT be used to advance
> freshness — the source is refused as UNPROVABLE, exactly as for a null axis
> (C-NULL). ASR already carries this signal: `CompletenessCheck(returned_count,
> total_available)` at `readiness.py:133-143`, fed from `active_returned_count` /
> `active_total_available` (`fetcher.py:344-347`). T-GUARD reuses it rather than
> minting a new check.

Note the live exposure this guard covers: ASR requests `limit=1000` twice
(`fetcher.py:314,321`) against a 4192-row frame. Truncation is not hypothetical
here; it is a routine possibility that the completeness check already watches.

**Second scoping effect, named so it is not discovered later:**
`content_watermark_returned` is **classification-scoped** — ASR fetches only
`active` and `activating` (`fetcher.py:312,319`). A frame in which only
non-active offers were recently edited yields an old result-scoped watermark and
a fresh frame-scoped one. Under the "rows I act on" semantics that is *correct*,
not a bug. It is a genuine semantic difference and must never be presented as an
approximation of the frame-scoped number.

Corollary (mine): **both content watermarks are monotone non-decreasing per
(project_gid, entity_type) under honest operation, but the contract does NOT
enforce monotonicity.** A section refetch that drops rows can legitimately lower
the max. Enforcing monotonicity would manufacture a ratchet that survives data
deletion — a false-fresh generator. Instead, a **decrease** is an observability
signal (§1.7), never a rejection.

### §1.3 Null semantics — decay, and the consumer-side fail-open that breaks it

**Emit side (asana).** `content_watermark` is `null` when — and only when — it
cannot be derived from the served bytes: an empty frame (0 rows), or a frame
whose `last_modified` column is absent/all-null. It is **NEVER synthesized**.
The precedent to avoid is live in the code: `cache/dataframe/tiers/progressive.py:187-189`
sets `watermark = datetime.now(UTC)` when S3 metadata carries none, and
`:202-209` then uses that synthetic value as `created_at` — a frame of arbitrary
true age reads as **age 0 / FRESH**. That is a synthetic-fresh GENERATOR and it
is the FIX-N leg pythia ruled admissible (Lane B).

**Null → DECAY.** A null content axis means *unprovable*, and unprovable is
**stale**, never fresh. Ratified by pythia (FORK-B).

**⚠ CONSUMER-SIDE FINDING — the decay law does not hold on the wire today, and
would not hold after an emit-only change.** ASR's readiness gate fails OPEN on a
null:

```
Decision logic:
  - staleness_seconds is None -> PASS (assume fresh, no metadata)
```
— `sdks/python/autom8y-reconciliation/src/autom8y_reconciliation/gate.py:48`
(and restated at `gate.py:114`, `:175` "EC-1: None staleness -> PASS").

So if asana honestly emits `content_age_seconds: null`, ASR **passes the gate**.
Emitting the truth would, on today's consumer, make the system *less* safe than
emitting the lie. The contract therefore has a **mandatory consumer clause**:

> **C-NULL (binding, both sides).** A `null` content axis MUST NOT reach
> `StalenessCheck` as `staleness_seconds=None`. The consumer maps
> `content_age_seconds is None` → an explicit refusal for the `offers` source.
>
> **C-NULL IS NOT IMPLEMENTABLE WITHOUT §1.5b.** Under the SDK's `extra="ignore"`,
> a producer that does not yet speak the axis and a producer that says "unknown"
> both parse to `None`. Refusing on `None` alone would refuse *every* readiness
> check for the entire cutover horizon; not refusing is not C-NULL. The producer
> capability signal is the precondition, not a detail. See §1.5b.
> The refusal is expressed **consumer-side** — ASR's `readiness.py` selects the
> disposition — so the shared `autom8y-reconciliation` SDK gate (used by other
> consumers) is not mutated and its blast radius is not incurred.

Two admissible expressions of C-NULL, both consumer-local:

- **C-NULL-a (recommended):** in `readiness.py`, when the offers meta lacks a
  usable content axis, append the source with a `PopulationFloorCheck`-style
  hard failure or a `StalenessCheck` fed a sentinel that is deterministically
  > `threshold * warn_multiplier`. **Do not use `inf`** — `gate.py:29-32`
  `_to_minutes` maps non-finite to `-1`, which would corrupt the message and the
  `max_staleness_seconds` roll-up.
- **C-NULL-b:** add an explicit `provable: bool` dimension to `SourceMetadata`.
  Cleaner, but mutates the shared SDK — larger blast radius, and the SDK is
  consumed beyond ASR. Enumerated, not recommended.

[UV-P: the exhaustive set of `autom8y-reconciliation` gate consumers beyond ASR | METHOD: cross-repo dependency scan of `autom8y_reconciliation.gate` imports across the fleet | REASON: outside this station's declared read surface (asana + the ASR service + the two SDK model files); the blast-radius claim for C-NULL-b is therefore stated as a risk, not a count]

### §1.4 Co-sourcing — the invariant, and why it is nearly free

> **CO-SOURCING (frozen, FORK-C).** The freshness signal in the response meta
> describes the **bytes in that same response**. A signal derived from one tier
> may never accompany bytes served from another. There is no such thing as a
> "substrate watermark" attached to a serve-path body.

**Today this already holds for `data_age_seconds`** — and it is worth saying so
precisely, because it tells us the mechanism to reuse rather than invent.
`query/engine.py:517-542` `_get_freshness_meta` reads
`self.provider.last_freshness_info`, which `services/universal_strategy.py:805-807`
populates from `cache.get_freshness_info(...)` immediately after the
`get_async` that produced the bytes; the cache writes that side-channel inside
`_build_freshness_info` (`dataframe_cache.py:1126-1162`) for the tier that
actually answered. Signal and bytes are already same-tier.

**Lane G makes co-sourcing structural rather than disciplinary.** If
`content_watermark = max(frame["last_modified"])` is computed **from the served
frame at emit time**, co-sourcing is not a rule anyone can violate — the signal
is a pure function of the bytes. That is a stronger guarantee than any
side-channel discipline can offer, and it is the single best argument for
Lane G over Lane E's persistence-based variants.

**What co-sourcing forbids, concretely (each of these is a real path in code):**
- attaching `s3_watermark` to bytes served from the memory tier
  (`api/preload/progressive.py:641-647` does exactly this shape today, in the
  opposite direction — see §1.9 / Lane C);
- attaching a warmer-side `watermark.json` value to a serve-path body (the
  DP-1F residual; this is why L3-as-written was invalidated);
- attaching the Seam-5 sweep's provability verdict to a Seam-4 read
  (forbidden independently by `[H22]` query-independence,
  `TDD-substrate-v2.md:490-491`).

### §1.5 Response-meta schema addition (additive, backward-compatible)

**Emit side — asana.** Both meta models are `extra="forbid"` —
`AggregateMeta` at `query/models.py:228`, `RowsMeta` at `query/models.py:390` —
so fields must be declared; all additions are optional with defaults, so no
existing producer or test breaks.

```python
# ADDITIVE to BOTH query/models.py::RowsMeta and ::AggregateMeta
# (they share the engine._get_freshness_meta side-channel, spread at
#  engine.py execute_rows / execute_aggregate — a field added to one and not
#  the other raises on the extra="forbid" model. Precedent: the stale_served
#  mirror comment at query/models.py:249-252.)

content_watermark: str | None = None       # ISO-8601 UTC; max(last_modified) of THESE bytes; null = unprovable
content_age_seconds: float | None = None   # now - content_watermark; null iff content_watermark is null
content_digest: str | None = None          # sv2 canonical digest of THESE bytes; null when not computed
frame_built_at: str | None = None          # ISO-8601 UTC; build-clock stamp. DISCLOSURE ONLY.
served_entry_stamped_at: str | None = None # ISO-8601 UTC; serving entry created_at. DISCLOSURE ONLY.
served_tier: str | None = None             # "memory" | "s3" — the tier that produced these bytes (co-sourcing witness)
fetched_rows: int | None = None            # DISCLOSURE ONLY
sections_fetched: int | None = None        # DISCLOSURE ONLY
sections_total: int | None = None          # DISCLOSURE ONLY
freshness_axis: str = "content"            # the axis the consumer MUST gate on. Frozen literal.
```

`data_age_seconds`, `staleness_ratio`, `freshness`, `stale_served` are
**retained unchanged** — this is purely additive. They are re-declared as
DISCLOSURE fields in the contract's prose; no consumer may gate freshness on
`data_age_seconds` once `content_age_seconds` is available.

**Wire compatibility is verified, not assumed.** The consuming SDK model is
`extra="ignore"`:

```yaml
structural_verification_receipt:
  claim: "adding fields to asana's RowsMeta cannot break the ASR consumer at the wire, because the SDK model that parses it ignores unknown fields"
  verification_method: file-read
  verification_anchor:
    source: "sdks/python/autom8y-core/src/autom8y_core/models/asana_service.py (autom8y monorepo origin/main)"
    line_range: "L336"
    marker_token: "model_config = ConfigDict(extra=\"ignore\")"
    claim: "QueryMeta silently drops fields it does not declare, so emit-side additions are non-breaking; the corollary is that consumption requires a THIRD leg (the SDK model must declare the field before ASR can read it)"
```

**Three-leg chain, and the precedent proving it is real.** asana already emits
`stale_served` (`query/models.py:436-445`, landed under
ADR-serve-stale-within-bound) and `QueryMeta` does **not** declare it
(`asana_service.py:338-345`) — so it has been silently dropped on the floor for
its entire life. Any lane that ends at "asana emits it" has shipped a field
nobody can read. The chain is:

1. **asana** — `query/models.py` + `query/engine.py::_get_freshness_meta`
2. **SDK** — `sdks/python/autom8y-core/.../asana_service.py::QueryMeta` declares the fields
3. **ASR** — `services/account-status-recon/src/account_status_recon/fetcher.py:339-347`
   lifts them into `FetchResult.meta`, and `readiness.py:123-154` gates on them

Legs 2 and 3 are monorepo changes and are **outside asana's P6 boundary
entirely** — they are new code in a live consumer, not v1 hardening.

### §1.5b PRODUCER-CAPABILITY SIGNAL — frozen contract requirement (round-3)

> **THE AMBIGUITY.** The SDK model is `extra="ignore"`
> (`asana_service.py:336`). That property is what makes additive emission safe
> (§1.5) — and it is exactly what makes absence unreadable. Two structurally
> different producer states collapse to the same parsed value:
>
> | Producer state | Wire | Parsed by consumer |
> |---|---|---|
> | **AXIS-ABSENT** — producer does not speak the axis (pre-contract asana, or v2 pre-flip) | field not emitted | `None` |
> | **AXIS-NULL** — producer speaks the axis and says "I cannot derive it" | `content_watermark: null` | `None` |
>
> A consumer cannot distinguish "not yet implemented" from "implemented and
> unprovable." **C-NULL therefore cannot be written correctly against `None`.**
> Refusing on `None` fails every check until the emit leg lands; not refusing
> means the null-decay law does not exist on the wire. Both are unacceptable.

> **CAP-SIG (FROZEN — a contract field, not a consumer detail).** The producer
> MUST emit an explicit capability declaration. Admissible forms, in preference
> order:
>
> 1. **`axes_present: list[str]`** (recommended) — the axis field names this
>    producer speaks, e.g. `["content_watermark", "content_watermark_returned",
>    "frame_built_at"]`. Self-describing, forward-compatible, additive, and it
>    degrades correctly: an old producer omits it → parses to `None`/`[]` →
>    consumer reads AXIS-ABSENT, not AXIS-NULL.
> 2. **`contract_version: str`** — coarser; requires a version→axes table
>    maintained in two repos. Enumerated; second choice.
> 3. **Non-null unknown-sentinel** (e.g. `content_watermark: "unknown"`) —
>    works, but puts a magic string in a datetime-typed field and invites a
>    parse crash in any consumer that does not know it. Enumerated; not recommended.
>
> **Consumer rule.** `axis in axes_present` AND `value is None` → **AXIS-NULL** →
> refuse (C-NULL). `axis not in axes_present` → **AXIS-ABSENT** → fall back to
> today's `data_age_seconds` behavior and emit a *disclosure* log, never a
> refusal. This is what makes step-3-before-step-4 (§2.9) safe: the consumer leg
> can land ahead of the producer leg and simply stay dormant.

**Lane-K note.** Under Lane K the capability signal is *partially* derivable —
the SDK can observe whether `last_modified` is present in the returned row dicts.
But `engine.py:236-238` **silently drops** a selected column absent from the
served frame, so absence is ambiguous between *producer-did-not-project* and
*frame-lacks-column*. The derived signal is therefore a fallback, not a
substitute. **Keep CAP-SIG explicit even under K.**

```yaml
structural_verification_receipt:
  claim: "asana's query engine silently omits a client-selected column when that column is absent from the served frame — no error, no warning, no signal to the consumer"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/query/engine.py (origin/main @cc20772e)"
    line_range: "L236-L238"
    marker_token: "valid_columns = [c for c in columns if c in available]"
    claim: "the filter at :237 discards any requested column not in the frame's actual columns and :238 projects only the survivors, so a consumer that requested last_modified and received rows without it cannot tell whether the producer declined to project it or the frame never carried it — which is why the capability signal cannot be inferred from row shape alone"
```

### §1.6 ASR-side consumption rule

**The gate.** For the `offers` source, `readiness.py:145-154` MUST construct its
`StalenessCheck` from a **CONTENT** axis, not `data_age_seconds`
(`readiness.py:127` today). One-line semantic change, but it is the whole point:

```
staleness_seconds = meta["content_age_seconds"]   # was: meta["data_age_seconds"]
```

**Which content axis, and where it comes from, depends on the lane:**

| Lane | Axis consumed | Derived by | Guards that MUST be wired |
|---|---|---|---|
| **K (recommended)** | `content_watermark_returned` | the SDK, from `data[]` of that response | **AXIS-ABSENT tooth** (§1.5b) + **T-GUARD** (§1.2b) + **C-NULL** (§1.3) |
| J (fallback) | `content_watermark_returned` | ASR itself, from `data[]` | same three, re-implemented in ASR |
| G / E (producer) | `content_watermark` (frame-scoped) | asana, from the served frame | **C-NULL** + **CAP-SIG** (§1.5b) |
| H (post-cutover) | the Seam-1 `FreshnessProof` | the v2 seam, per-read | `Provable \| Refused` handling + DP-3 424/`Retry-After` |

All four paths gate on a content axis and none may fall back to
`data_age_seconds` silently. Under K, note that `content_age_seconds` is
**result-scoped** (§1.2b) — a deliberate and arguably more relevant semantics,
never an approximation of the frame-scoped number.

**The fresh-task acceptance case (mandatory, from DIAG-S1 F3.1).** A newly
started ECS worker MUST report the same freshness as a long-lived one for the
same underlying substrate. Today it does not: the 2026-08-10T20:00Z abort's
10083.3s anchored to a **task-startup preload put** at 17:12:43.30Z on worker
`595b17c49d5c`, while a task started minutes before a tick reports near-zero
regardless of substrate age (the 2026-08-11T00:01:01Z PASS at 1022.9s). Under
the content axis both workers derive `max(last_modified)` from the same bytes and
report the same number. **This is the acceptance test that discriminates the cure
from a re-anchoring accident**, and it is why "the 12:00Z tick passed" can never
be evidence of a fix.

**The 2.25× collision — resolved as an AXIS CONFLATION, not a threshold dispute.**
This is the point at which I depart from the framing the charge inherited, and I
want the departure legible.

| Quantity | Value | Axis | Anchor |
|---|---|---|---|
| asana governed freshness SLA (offer) | **3600 s** | freshness | `core/entity_registry.py:548` (`freshness_sla_seconds=3600`, C8/C17 operator-ratified 2026-07-30) |
| ASR readiness threshold (offer) | **3600 s** | freshness | `services/account-status-recon/src/account_status_recon/config.py:86-90` |
| ASR abort threshold | **7200 s** | freshness | **DERIVED**: `threshold × warn_multiplier`, `gate.py:50-51,58-59` (default 2.0) — NOT independently configured |
| asana LKG serve ceiling (offer) | **16200 s** | *availability tolerance* | `config.py:305` |

**The two sides already agree at 3600 s on the freshness axis.** The 16200 s
number is not a competing freshness threshold — it is the availability-first
read-tolerance bound governing whether to serve LKG bytes at all
(`config.py:284-294`). The collision is not "asana tolerates 2.25× more
staleness"; it is **"one wire field (`data_age_seconds`) carries an availability-
axis quantity into a freshness-axis gate."** Once the gate reads
`content_age_seconds` against the governed 3600 s, the axes separate and the
2.25× disappears without either number moving.

> **Threshold-alignment decision — stated explicitly for the operator, per the
> charge.** Recommendation: **change no threshold.** 3600 s (asana governed) ==
> 3600 s (ASR) is already alignment. Raising ASR's threshold to accommodate a
> producer measuring the wrong quantity would loosen a correctness gate to fit a
> measurement error — the charter's "never confidently wrong" (§2) points the
> other way. If, after the content axis is live, the *content* age genuinely
> exceeds 3600 s at tick time, that is a real warm-cadence finding to be fixed at
> the warmer, not absorbed by a threshold. **Note the coupling:** because the
> abort threshold is derived (`× warn_multiplier`), touching
> `offer_staleness_threshold_seconds` moves warn AND abort together; there is no
> knob that moves one alone. Operator card D-3.

### §1.7 AL-5 / L6c re-homing rule

**What AL-5 is today, precisely.** The metric filter
`asana-AL5-offer-frame-age-1143843662099250` keys on the log event
`dataframe_cache_memory_lkg_serve` and lifts `$.extra.age_seconds`
(CARD-l6 §5.B, byte-for-byte live/authored match). That event is emitted at
`dataframe_cache.py:767-776`, on the LKG serve path. DIAG-S1 F1.3 measured that
**every** offer read is an LKG serve (offer TTL 180 s ×
`SWR_GRACE_MULTIPLIER` 3.0 = 540 s grace; observed healthy-period ages
700–2074 s). So:

> **AL-5 is a read counter that carries an age field. Its firing rate is
> traffic, not health. It is not a staleness detector and must not be treated as
> one.**

**The re-homing rule (frozen).**

> **AL-5-HOME.** The offer-freshness alarm MUST read a **warmer-side /
> traffic-independent** emission whose cadence is set by a schedule, never by a
> consumer's read. It MUST NOT key on any serve-path log event. This is Seam-5
> query-independence `[H22]`: *"scheduled (EventBridge→Lambda / warmer
> post-step); NEVER called from `read`"* (`TDD-substrate-v2.md:490-491`).

**Concrete target — already built, already emitting.** `substrate/observe.py`
is the scheduled provability evaluator; its metric constants are frozen at
`observe.py:404-431`:
`SUBSTRATE_PROVABILITY_NAMESPACE = "Autom8y/SubstrateProvability"` (`:404`),
`METRIC_MAX_STALENESS_AGE_SECONDS` (`:421`), `METRIC_UNPROVABLE_COUNT` (`:419`),
`METRIC_EVALUATOR_HEARTBEAT` (`:423`), `METRIC_EVALUATED_COUNT` /
`METRIC_EXPECTED_COUNT` (`:425-426`), `METRIC_EXPECTED_SET_MISMATCH_COUNT`
(`:424`), `METRIC_FUTURE_DATED_PROOF_COUNT` (`:431`). The PROV-1..6 alarms in
`terraform/services/asana/substrate_v2_provability_alarms.tf` are the alarm
family already bound to these. **AL-5's honest successor is a PROV-family alarm
on `MaxStalenessAgeSeconds` dimensioned to the offer artifact — not a re-tuned
metric filter on the serve path.**

**Interim rule while AL-5 still exists.** Until the PROV successor covers offer,
AL-5 keeps its teeth (the L6 binding card) but its *semantics* are demoted in
writing: its alarm description must say what it measures. A green AL-5 is not
evidence of freshness, and CARD-l6 §4.4 already warns that the pending apply may
flip it ALARM→OK purely because the evaluation window narrows.

**One additional emission the contract asks for (Lane G-adjacent, cheap):**
a warmer-post-step emission of `content_watermark` age per (project_gid,
entity_type). It is traffic-independent by construction, it is the *same*
quantity the serve path emits (so a divergence between the two is itself a
detector), and a **decrease** in `content_watermark` (§1.2 corollary) is the
data-deletion signal nothing watches today.

### §1.8 ⚠ NAMING COLLISION — do not call the v1 build stamp `built_from_live_at`

Pythia's FORK-B names the build axis `built_from_live_at`, "the existing
`now(UTC)` at `builders/progressive.py:1130`, honestly renamed." I must surface a
conflict pythia did not have in front of it, because adopting the name literally
would import a guarantee the v1 quantity does not satisfy.

`built_from_live_at` is **already taken, and frozen, with a strictly stronger
meaning**:

- `substrate/freshness.py:72-73` — *"tz-aware UTC; = MIN over constituent
  sections' last REAL content-fetch instants (C1)"*
- `substrate/freshness.py:115-120` `fold_built_from_live_at` — *"THE LAW (no
  probe-stamp path on the S2 surface): this fold's ONLY input is content-fetch
  instants — there is no `probe_instant` parameter"*
- FROZEN v1.0-frozen-2026-07-29 per `TDD-substrate-v2.md` §4 Seam 1.

The v1 quantity at `builders/progressive.py:1130` is `datetime.now(UTC)`, set
unconditionally after section merge with no reference to any fetch instant — it
is stamped identically whether 4192 rows were fetched or zero (DIAG-S1 F1.6,
three live builds with `fetched_rows=0`). Giving it the v2 name would make a
build-clock stamp wear the badge of a content-fetch fold. That is the
false-fresh direction the epoch exists to end, achieved through nomenclature.

> **RULING — RATIFIED at round-3 (2026-08-11).** The v1 build-axis field is
> **`frame_built_at`**. `built_from_live_at` is reserved exclusively for the
> frozen Seam-1 value object. FORK-B's *substance* — rename the misleading
> `watermark`, make it never readable as freshness — is fully honored; only the
> token differs, and it differs specifically to protect the frozen seam. Card D-1
> is CLOSED.

> **NON-ALIASING CLAUSE (BINDING, added at round-3).**
>
> 1. `frame_built_at` is emitted **ONLY by v1**. The v2 seam never emits it.
> 2. `built_from_live_at` is emitted **ONLY by v2**. v1 never emits it.
> 3. **No consumer may treat them as the same field** — no `or` fallback, no
>    coalesce, no shared parse branch, no "whichever is present" helper. A
>    consumer that wants both must handle them in separate, separately-named
>    code paths.
> 4. **No field survives the flip under both names.** There is no transition
>    window in which one artifact carries both tokens.
> 5. **Strongest form (RECOMMENDED):** v1's emission uses **no token from the
>    Seam-1 vocabulary at all** — not `built_from_live_at`, not `content_digest`
>    as a Seam-1-semantics claim, not `sla_seconds`, not `provable`. If v1 must
>    emit a digest, it is named distinctly (e.g. `v1_value_digest`) unless it is
>    literally computed by `substrate.freshness.canonical_digest`, in which case
>    it may carry the Seam-1 name because it *is* the Seam-1 quantity.
>
> **Why this is binding and not stylistic.** An alias is how a v1 quantity
> acquires a v2 guarantee without earning it. The whole defect class this crusade
> exists to close is a number that means one thing being read as though it meant
> another. Permitting `frame_built_at || built_from_live_at` in any consumer
> would reconstruct that class at the vocabulary layer, one cutover later, where
> nobody is looking for it.

Second, smaller collision, same family: the entry field
`DataFrameCacheEntry.watermark` (`dataframe_cache.py:890`) is a build stamp, and
`is_fresh_by_watermark`'s parameter is documented as *"Current max(modified_at)
from source"* (`dataframe_cache.py:147`). One word, two referents, one comparison
operator between them — which is exactly the quarantined socket (§3.1).

### §1.9 What the contract does NOT promise (stated so nobody infers it)

- It does **not** promise the data is current — only that its newest fact is
  provably ≤ SLA old, or that it is loudly unprovable. This is the same bound
  the v2 F2-1 ruling accepted: *"provably <= SLA-old, else refused"*
  (`ADR-substrate-v2-fork-register.md` §F2, Option F2-1 disadvantage).
- It does **not** detect within-SLA change. A row edited 10 minutes into a
  60-minute SLA raises `content_watermark`, so the axis moves — but only after a
  rebuild observes it. Catching it sooner needs the F2-3 decay probe or F2-4
  webhook decay, both enumerated-and-deferred in the fork register.
- It does **not** make LKG serving dishonest or honest. LKG remains an
  availability decision on its own axis; the contract only stops that decision's
  byproduct from being read as freshness.
- It does **not** cover the v2 `Refused` path. On the v2 seam, an all-tiers-stale
  read aborts LOUD as DP-3 424 + `Retry-After`
  (`DP-3-consumer-contracts.md` §Ratification row 1), and the consumer-side
  `map_http_error` learning must land **with or before** the server flip
  (`DP-3-consumer-contracts.md`, binding sequencing). FORK-D, unchanged.

---

<!-- END VERBATIM CORE -->

---

## §D STATUS LEDGER

Every clause of the fence, its locus in the source, and its adjudicated status.
Loci are source line numbers (identical to fence content by §B).

### §D.1 Clause status — all RULED / RATIFIED

| # | Clause | Locus | Status | Basis |
|---|---|---|---|---|
| 1 | **§1.1 — the three axes.** Wire names, types, grain, derivation, provenance, and the per-axis "may advance freshness?" column. Grain for all three: **(project_gid × entity_type)**. | 149–180 | **RULED** | pythia FORK-B three-axis mandate |
| 2 | **§1.2 — THE ADVANCEMENT LAW (frozen).** Only a CONTENT axis may advance freshness; `frame_built_at`, `served_entry_stamped_at`, `fetched_rows`, `sections_fetched`, `sections_total`, `axes_present` are DISCLOSURE. | 181–193 | **RATIFIED** | FORK-B as adjudicated 2026-08-11; same law the v2 seam already encodes |
| 3 | **§1.2b — which content axis gates + T-GUARD (binding).** Frame-scoped vs result-scoped are not interchangeable; the truncation guard; the classification-scoping effect; the monotonicity corollary (a decrease is an observability signal, never a rejection). | 194–236 | **RULED** (T-GUARD binding; FINDING-3 carries the source's MODERATE ceiling per source §5) | FINDING-3 + reuse of `CompletenessCheck` |
| 4 | **§1.3 — null semantics + C-NULL (binding, both sides).** Null → DECAY; NEVER synthesized; the consumer-side fail-open finding; C-NULL-a recommended, C-NULL-b enumerated-not-recommended; the `inf` refusal. | 237–292 | **RULED** | FORK-B (null→decay ratified) |
| 5 | **§1.4 — CO-SOURCING (frozen, FORK-C).** The freshness signal describes the bytes in that same response; the three concretely-forbidden paths. | 293–325 | **RATIFIED** | FORK-C |
| 6 | **§1.5 — response-meta schema addition (additive, backward-compatible).** Both meta models are `extra="forbid"`; legacy fields retained unchanged; the three-leg chain (asana → SDK → ASR) and the `stale_served` precedent proving it is real. | 326–385 | **RULED** | carries an SVR at 360–369 (`verification_method: file-read`, SDK `extra="ignore"`) |
| 7 | **§1.5b — CAP-SIG (FROZEN).** Producer-capability signal; AXIS-ABSENT vs AXIS-NULL; the binding consumer rule; the Lane-K note (keep CAP-SIG explicit even under K). | 386–441 | **RULED** — the *requirement* is AUDITED (round-3 critic supplied it); the *resolution shape* carries the source's MODERATE ceiling per source §5 | carries an SVR at 432–441 (silent column drop at `engine.py:236-238`) |
| 8 | **§1.6 — ASR-side consumption rule.** The gate change; the per-lane axis table (K/J/G-E/H) with required guards; the **fresh-task acceptance case** (mandatory, DIAG-S1 F3.1); the **2.25× resolved as AXIS CONFLATION, not a threshold dispute**; the threshold-alignment decision. | 442–508 | **RATIFIED** — the axis-conflation reframe is **AUDITED, self-ref ceiling LIFTED** (source §5) | round-3 rite-disjoint audit; **D-3 recorded refusal** |
| 9 | **§1.7 — AL-5-HOME (frozen).** The alarm MUST read a warmer-side / traffic-independent emission and MUST NOT key on any serve-path log event ([H22] query-independence). PROV-family successor named; interim demotion-in-writing; the warmer-post-step emission the contract asks for. | 509–557 | **RULED** | Seam-5 `[H22]`, `TDD-substrate-v2.md:490-491` |
| 10 | **§1.8 — NAMING COLLISION + the D-1 RULING + the NON-ALIASING CLAUSE (BINDING, 5 numbered clauses).** v1's build axis is **`frame_built_at`**; `built_from_live_at` is reserved exclusively for the frozen Seam-1 value object. | 558–618 | **RATIFIED — D-1 CLOSED** | round-3 ruling, 2026-08-11 |
| 11 | **§1.9 — what the contract does NOT promise.** Four explicit non-promises, including that the v2 `Refused` path is out of scope (FORK-D, unchanged). | 619–639 | **RULED** | FORK-D unchanged |

**No clause is HELD for want of a ruling.** Every clause above was found ruled in
the source. See §D.3 for two *sub-clause* items that are not ruled and are
therefore inscribed HELD rather than defaulted.

### §D.2 Operator cards bearing on the fence

| Card | Question | Disposition |
|---|---|---|
| **D-1** | v1 build-axis naming | **CLOSED — RATIFIED at round-3.** `frame_built_at` for v1; `built_from_live_at` reserved for the frozen Seam-1 object. The binding NON-ALIASING clause (§1.8) rides with it. Locus: fence 558–618. |
| **D-3** | threshold alignment (the "2.25×") | **RECORDED REFUSAL — CHANGE NOTHING.** The two sides already agree at 3600 s on the freshness axis; 16200 s is an availability-tolerance bound on a different axis. Recorded as a refusal to act, per the source. Coupling noted: the abort threshold is DERIVED (`× warn_multiplier`), so warn and abort move together — there is no knob that moves one alone. Locus: fence 487–508. |
| **D-5** | FIX-N admissibility for the preload stamp | **CLOSED — RULED at round-3.** **C1 ADMISSIBLE as FIX-N under a BINDING CONDITION:** the `put_async` signature change must be **default-preserving** — `created_at: datetime \| None = None`, with `None → datetime.now(UTC)` — so every existing caller is byte-identical in behavior. **If the implementer makes the parameter required, or changes the default, C1 leaves the class and returns for re-adjudication.** **C2 CONFIRMED not-in-class.** Discriminator: *"does the change alter WHICH CODE PATH executes, or only WHAT VALUE a stamp records?"* Locus: source §4 row D-5 (outside the fence; governs the FIX-N-C1 signature). |
| **D-5b** | **freshness-axis authority once the content axis lands** | **OPEN — NON-BLOCKING. FRAMED, NOT DECIDED.** Two numbers will occupy the freshness axis: asana's **governed** `freshness_sla_seconds = 3600` and ASR's **deployed** threshold. Ruled a governance question, not an architectural one. **Decide AFTER K lands** — nothing in the composition depends on it. **The ASR deployed-threshold-location [UV-P] rides with it** (see §D.4). Locus: source §4 row D-5b (outside the fence). |

**This is the ONE open item.** Every other card bearing on the fence is closed or
is a recorded refusal.

### §D.3 HELD — found unruled in the source, inscribed HELD, never defaulted

Two sub-clause items are not ruled anywhere in the fence. Per station rule they
are inscribed HELD. **No limb may default them; a limb that needs one escalates.**

- **HELD-1 — the absent-representation of `axes_present`.** §1.5b form 1 states
  that an old producer "omits it → parses to `None`/`[]`", while the binding
  consumer rule is written as membership (`axis in axes_present` /
  `axis not in axes_present`) — well-defined on a list, undefined on `None`.
  **No clause rules which of `None` or `[]` the consumer normalizes to.**
  *Scope of the hold:* the AXIS-ABSENT / AXIS-NULL **semantics** are RULED and
  are not held — only the absent-representation is. *Does not block:* K-ASR,
  FIX-N-B, FIX-N-C1. *Must be settled before:* K-SDK and K-ASR assert AXIS-ABSENT
  against the same value. Both K limbs MUST use one normalization, whichever the
  operator rules.
- **HELD-2 — which value occupies `content_age_seconds` once both derivation
  legs are live.** §1.1 row 1c defines the field as parameterized —
  `(now_utc - {the gating watermark})` — and §1.6 fixes the gating watermark
  *per lane* (K → result-scoped, G/E → frame-scoped). **No clause rules which
  value occupies the single field name when the Lane G producer follow-on lands
  behind the Lane K bridge.** *Does not block:* K-ASR, K-SDK, FIX-N-B, FIX-N-C1
  — at K time only one referent exists. *Must be settled before:* the Lane G
  producer follow-on emits a frame-scoped `content_age_seconds`. Note the
  structural kinship with §1.8's own warning ("one word, two referents"); the
  fence's §1.2b already forbids presenting either scope as an approximation of
  the other.

### §D.4 UV-P carried

**Inside the fence:**

- **§1.3, locus 291** — the exhaustive set of `autom8y-reconciliation` gate
  consumers beyond ASR. METHOD and REASON as authored. It scopes the C-NULL-b
  blast-radius claim as a **risk, not a count** — which is why C-NULL-a
  (consumer-local, no shared-SDK mutation) is the recommended expression.

**Riding with D-5b (outside the fence, source §4 rows D-5b and D-10(f)):**

- the **ASR deployed-threshold location** UV-P — whether
  `offer_staleness_threshold_seconds` is overridden from its 3600 default in the
  deployed environment, and where (env var / SSM / task definition). METHOD:
  read the ASR Lambda's environment configuration + its terraform/SSM source.
  REASON: requires deployment-config reads outside the S1 station's declared read
  surface. Routed as a separate card; does not block this freeze.

### §D.5 CONDITIONS — ruled, but conditional; carried so no limb misses them

| # | Condition | Fence locus |
|---|---|---|
| **COND-1** | `content_digest` may carry the Seam-1 name **only while it is literally computed by `substrate.freshness.canonical_digest`** — the §1.8 non-aliasing clause-5 carve-out. A digest computed by any other means MUST be named distinctly (the source's example: `v1_value_digest`). | §1.8 cl. 5 |
| **COND-2** | `content_watermark_returned` is admissible as a gating axis **only under T-GUARD**: if `returned_count < total_available` for any constituent query, the result-scoped watermark MUST NOT advance freshness — refuse as UNPROVABLE, exactly as for a null axis (C-NULL). | §1.2b |
| **COND-3** | **C-NULL is NOT implementable without §1.5b.** The producer capability signal is the precondition, not a detail. A limb that implements C-NULL against bare `None` has not implemented C-NULL. | §1.3, §1.5b |
| **COND-4** | C-NULL-a MUST NOT use `inf` — `gate.py:29-32` `_to_minutes` maps non-finite to `-1`, corrupting the message and the `max_staleness_seconds` roll-up. | §1.3 |
| **COND-5** | **NON-ALIASING (BINDING, 5 clauses).** `frame_built_at` is v1-only; `built_from_live_at` is v2-only; no consumer may coalesce them (no `or`, no fallback, no shared parse branch, no "whichever is present" helper); no field survives the flip under both names; strongest recommended form is that v1 emit no Seam-1 token at all. | §1.8 |
| **COND-6** | **FIX-N-C1 default-preserving condition (D-5).** `created_at: datetime \| None = None`, `None → datetime.now(UTC)`. A required parameter or a changed default takes C1 out of the FIX-N class and back to re-adjudication. | source §4 D-5 |

### §D.6 NOTES — transcription observations (representation, not contradiction)

- **NOTE-1 — the §1.5 python block is NOT the exhaustive frozen field roster.**
  It omits `axes_present` (frozen at §1.5b; carried as a wire field in §1.1
  row 1d) and `content_watermark_returned` (§1.1 row 1b′; consumer-derivable
  under Lanes J/K). **§1.1's axes table is the roster; §1.5's block is the
  producer-side additive schema.** This is precisely why §E quotes the code block
  **and** the twelve field names — quoting the block alone would under-specify
  the contract by two fields.
- **NOTE-2 — `served_tier`** appears in the §1.5 block only. It is not a row in
  §1.1 and is not enumerated in §1.2's DISCLOSURE list. Its non-advancement
  follows from §1.2's **closed positive form** ("only a CONTENT axis may advance
  freshness"), which covers every non-content field whether enumerated or not.
- **NOTE-3 — CAP-SIG form.** §1.5b enumerates three admissible forms in
  preference order and recommends form 1. §1.1 row 1d and §1.2's disclosure
  enumeration both inscribe **`axes_present`** as the wire name, and §1.5b's
  binding consumer rule is written only for form 1. **Operative wire name for
  both limbs: `axes_present`.** Forms 2 (`contract_version`) and 3
  (non-null unknown-sentinel) are enumerated-not-selected and carry no written
  consumer rule; a limb wanting either escalates, it does not choose.
- **NOTE-4 — `content_watermark_returned` is not a producer wire field under the
  recommended lane.** Under Lane K the SDK derives it from `data[]`. §1.1 row 1b′
  keeps producer-side derivation admissible; the recommended composition does not
  use it.

### §D.7 W2-F5 flags

**NONE.** No §1 clause was found falsified by another §1 clause during
transcription. Two sub-clause items were found **unruled** and are inscribed HELD
at §D.3 rather than defaulted; four notes at §D.6 record representation gaps that
are dispositioned by the fence's own text and are therefore not contradictions.

**This is NOT a clean bill of health.** W2-F5 is scoped to *intra-fence*
falsification. A separate, **fence-crossing** collision is recorded at **§D.8
(W2-F1b, UNRESOLVED)** and is BLOCKING for both K limbs. Read §D.7 and §D.8
together or not at all.

### §D.8 COLLISION NOTE — **W2-F1b · UNRESOLVED · PENDING PYTHIA**

> **STATUS: UNRESOLVED.** Adjudication rides the **W2-F1 pythia dispatch at gate
> G1**. **Both K limbs (K-ASR, K-SDK) are FORBIDDEN to implement either
> disposition until it is ruled.**
>
> **This note RECORDS a discrepancy. It does not resolve one.** No side is
> picked here, no precedence is asserted, no default is taken. Nothing below
> amends the fence.

**The collision.** The token **`AXIS-ABSENT`** carries **two referents with
opposite dispositions** across the source document.

#### Referent (A) — fence §1.5b consumer rule → **never a refusal**

Locus: fence §1.5b, source 418–422 (inside §C). Quoted verbatim
(**EXTRACTED-FROM-FENCE** — the fence is authoritative on any divergence):

> **Consumer rule.** `axis in axes_present` AND `value is None` → **AXIS-NULL** →
> refuse (C-NULL). `axis not in axes_present` → **AXIS-ABSENT** → fall back to
> today's `data_age_seconds` behavior and emit a *disclosure* log, never a
> refusal. This is what makes step-3-before-step-4 (§2.9) safe: the consumer leg
> can land ahead of the producer leg and simply stay dormant.

#### Referent (B) — source §3.7 H-1 + the Lane-K BINDING CAVEAT → **loud refusal**

Locus: source §3.7 hazard table row H-1, line 1561 (**outside** the fence).
Quoted verbatim:

> **AXIS-ABSENT tooth** — missing column ⇒ loud refusal, never null-that-passes.
> This is the single most important test in Lane K.

Same disposition, bound into K's spec at source 1256–1263 (**outside** the fence).
Quoted verbatim:

> **BINDING CAVEAT (bound into K's spec, from round-3).** `engine.py:236-238`
> **silently drops** a selected column absent from the served frame (receipt in
> §1.5b). K MUST therefore treat a missing `last_modified` in the returned rows
> as **AXIS-ABSENT and refuse loudly** — never silent-pass, never fall back to
> `data_age_seconds` without an explicit disclosure, never synthesize. A
> derivation that silently degrades to "no rows carried the column, so max is
> null, so PASS" reconstructs the exact fail-open (§1.3) this contract exists to
> close, one layer further from anyone watching.

**(A) and (B) are directly opposed on the same token.** (A) says AXIS-ABSENT
falls back to `data_age_seconds` with a disclosure log and **never** refuses.
(B) says AXIS-ABSENT is a **loud refusal** and explicitly names "fall back to
`data_age_seconds` without an explicit disclosure" among the things K MUST NOT
do. A limb reading only one of them builds the opposite of a limb reading only
the other — the exact cross-limb skew this station exists to prevent.

#### The mis-pointed citation (recorded, not adjudicated)

Fence §1.6's Lane-K guard row (source 456, inside §C) reads:

> | **K (recommended)** | `content_watermark_returned` | the SDK, from `data[]` of that response | **AXIS-ABSENT tooth** (§1.5b) + **T-GUARD** (§1.2b) + **C-NULL** (§1.3) |

It names the **tooth** — referent (B)'s construct — and points it at **§1.5b**,
the section carrying referent (A)'s opposite disposition. The pointer and the
pointee do not agree. **Recorded as-is; not repaired here.**

#### The ordering tension (recorded, not adjudicated)

- `axes_present` is **producer-exclusive by construction** and is scheduled at
  source §2.9 **step 7** — "Producer-exclusive residue: frame-scoped watermark +
  fetch-liveness pairing + `axes_present`", lane **G (re-scoped)**, timing
  **post-window, post-K**.
- The K bridge is source §2.9 **step 3** — "**now**, fully independent of P5".
- Therefore **at step 3, `axes_present` is universally absent on every response.**
- Under disposition **(A)**, `axis not in axes_present` is true for every
  response, so every response falls back to `data_age_seconds` with a disclosure
  log and **never** refuses — **K is inert until step 7**. (A)'s own rationale
  says as much in its final sentence: the consumer leg "can land ahead of the
  producer leg and simply stay dormant."
- Under disposition **(B)**, the tooth governs at step 3 and K bites immediately
  on the actual hazard (`engine.py:236-238`'s silent drop).
- **So the two dispositions do not merely differ in strictness — they differ on
  whether the recommended bridge delivers a cure at step 3 at all.** Whether (B)
  governs at step 3, whether (A) governs only the `axes_present`-declared regime
  from step 7, or whether the token must be split into two distinct names, is
  **the pythia question** — not this station's.

#### Consequences held at this station

| | |
|---|---|
| **Blocked** | K-ASR and K-SDK — **forbidden to implement either disposition** until ruled. Not merely "choose carefully": neither branch may be built. |
| **Not blocked** | FIX-N-B and FIX-N-C1 — neither leg consumes the AXIS-ABSENT token. They proceed on the fence as frozen, subject to their own conditions (COND-6 / D-5, and source §4 D-6 timing). |
| **Adjudicator** | pythia, via the **W2-F1 dispatch at gate G1**. |
| **Not done here** | no side picked; no precedence rule asserted between fence and non-fence text; no rename proposed; no default taken; the fence is untouched (§B diff re-verified after this note was added). |
| **Interaction with HELD-1** | HELD-1 (§D.3) holds the *absent-representation* of `axes_present` (`None` vs `[]`). W2-F1b holds the *disposition* that fires on absence. They are distinct holds on the same surface and must be ruled together or in a stated order. |

---

## §E BUILD-PROMPT QUOTE BLOCK — **EXTRACTED-FROM-FENCE**

> **EVERY S2 BUILD PROMPT MUST QUOTE THIS BLOCK VERBATIM.** It is the only
> structural defense against cross-limb skew: four legs, one vocabulary.
>
> **This block duplicates fence content by design.** It is an extract, not a
> restatement. **On any divergence, the fence (§C) is authoritative** and this
> block is the error.
>
> **⚠ Quoting this block does NOT unblock the K limbs.** The vocabulary is frozen;
> the **AXIS-ABSENT disposition is not** (§D.8, W2-F1b, UNRESOLVED). Every S2
> build prompt for a K leg MUST carry §D.8 alongside this block.

### §E.1 The frozen schema addition — extracted from fence §1.5 (source 333–350)

```python
# ADDITIVE to BOTH query/models.py::RowsMeta and ::AggregateMeta
# (they share the engine._get_freshness_meta side-channel, spread at
#  engine.py execute_rows / execute_aggregate — a field added to one and not
#  the other raises on the extra="forbid" model. Precedent: the stale_served
#  mirror comment at query/models.py:249-252.)

content_watermark: str | None = None       # ISO-8601 UTC; max(last_modified) of THESE bytes; null = unprovable
content_age_seconds: float | None = None   # now - content_watermark; null iff content_watermark is null
content_digest: str | None = None          # sv2 canonical digest of THESE bytes; null when not computed
frame_built_at: str | None = None          # ISO-8601 UTC; build-clock stamp. DISCLOSURE ONLY.
served_entry_stamped_at: str | None = None # ISO-8601 UTC; serving entry created_at. DISCLOSURE ONLY.
served_tier: str | None = None             # "memory" | "s3" — the tier that produced these bytes (co-sourcing witness)
fetched_rows: int | None = None            # DISCLOSURE ONLY
sections_fetched: int | None = None        # DISCLOSURE ONLY
sections_total: int | None = None          # DISCLOSURE ONLY
freshness_axis: str = "content"            # the axis the consumer MUST gate on. Frozen literal.
```

### §E.2 The frozen wire-field names — the complete roster (~~twelve~~ **fifteen**)

Ten are inscribed in fence §1.1 (the axes table); `served_tier` and
`freshness_axis` are inscribed in fence §1.5. Per §D.6 NOTE-1, the §E.1 block
alone under-specifies the roster by two fields — quote **both** halves of §E.

**[A-2026-08-12] — roster additions, twelve → fifteen** (ADR-007 §3.1). The
three verification-axis names below are inscribed in fence **§1.2 as amended by
[A-2026-08-12]**, not in §1.1 or §1.5. They land in the same PR as the §1.2
amendment, so this block does not diverge from the fence — §E's precedence rule
(*"on any divergence, the fence (§C) is authoritative and this block is the
error"*) is satisfied rather than tripped.

```
content_watermark
content_watermark_returned
content_age_seconds
content_digest
frame_built_at
served_entry_stamped_at
served_tier
fetched_rows
sections_fetched
sections_total
freshness_axis
axes_present
verified_at
verification_age_seconds
verification_backfill_used
```

**⚖ `verification_backfill_used` carries a flag.** The spelling is pinned by
operator ruling of 2026-08-13; **R-O3's delegation of that choice to the
architect at the producer-leg PR is FLAGGED and UNRULED** and is not discharged
by the pin. See the qualification block under fence §1.2 NON-ALIASING clause 5
before treating this name as settled.

**Spelling is load-bearing.** No abbreviation, no pluralization change, no
re-casing, no `_ts`/`_at` substitution, no synonym. A limb that needs a name not
on this list does not rename — it escalates.

**The two names most easily got wrong:**

- **`frame_built_at`** — NOT `built_from_live_at` (D-1 RATIFIED; the latter is
  reserved exclusively for the frozen Seam-1 value object) and NOT `watermark`.
  See COND-5 (NON-ALIASING, binding).
- **`content_watermark_returned`** — NOT `content_watermark`. The two are **not
  interchangeable** (§1.2b); result-scoped is systematically ≤ frame-scoped and
  fails toward *stale*. It is admissible only under T-GUARD (COND-2).

---

## §F SIGNATURES

Four limbs sign this contract. **A signature is a claim of implementation against
a frozen vocabulary, so it must carry the vocabulary back verbatim.**

**A signature is complete when and only when it carries BOTH:**

1. the limb's **PR link** (merged or open, with the head SHA), and
2. a **verbatim quote of the §1.1 wire-field names it implements** — copied from
   §E.2, not retyped, with any name it does NOT implement omitted rather than
   altered.

A limb that cannot quote a name verbatim has found either a skew or a HELD item
(§D.3), and MUST escalate before signing.

**The K limbs cannot complete their signatures at this gate.** §D.8 (W2-F1b) is
UNRESOLVED and BLOCKING for both. Their slots below carry the block explicitly so
a partial build cannot be mistaken for a signed one.

### K-ASR

- **Branch:** `fix/asr-offers-watermark-repoint`
- **PR link:** https://github.com/autom8y/autom8y/pull/1539 (drawn post-SDK-merge;
  diff scoped to `services/account-status-recon/` only, zero `sdks/**` content —
  verified via `git diff origin/main...HEAD -- sdks/` empty at draw time)
- **Head SHA:** `fdef8bd6` (branch head; K-ASR commits `c730bc5a` part-1 + `2910fc24` part-2
  + `7d634c1a` FINDING-QA-1 refusal-attribution fix + `fdef8bd6` R-6 capability tolerance)
  — **post-merge branch head (merge of `origin/main` for the clean-diff PR draw):**
  `eeb773233c234e053dc3d10502086df1b3924397`
- **R-6 amendment (operator ruling, 2026-08-11):** the hard `>=4.14.0` build floor is
  REPLACED by honest quiet tolerance — `fetch_offers` feature-probes the installed SDK and,
  when the content-axis surface is absent, gates on the legacy age and emits
  `offers_content_axis_unavailable`; deployment against an older library degrades DISCLOSED,
  not dark, and the SDK→publish→ASR order stays preferred but is no longer build-enforced.
- **SDK integration (local, not for the PR diff):** `--no-ff` merge `bad54bea` (K-SDK
  `6fa3636b`) **superseded by** `4511f1a4` (K-SDK **`552e6c6e`**, incl. SURFACE §9 DELTA-1)
  — the K-SDK head this contract records; every count and mutation proof below was re-run
  against it, and DELTA-1 was measured observably inert for this limb
- **§1.1 wire-field names implemented (verbatim from §E.2):**

```
content_watermark_returned
content_age_seconds
```

  Two of the twelve. The other ten are **omitted, not altered** — this limb does
  not consume them. `content_watermark` (frame-scoped) is deliberately NOT read:
  under Lane K the result-scoped quantity is derived from `data[]`, and reading
  the frame-scoped field as a fallback is exactly the coalesce §1.2b forbids.
  `axes_present` is not read either — per the G1 disposition it governs nothing
  this limb reads at step 3; the `[]` normalization is bound, not re-derived,
  by not being re-implemented here.

- **SDK surface consumed** (K-SDK `SURFACE-k-sdk-2026-08-11.md`; NOT §E.2 wire
  names — listed separately so the two vocabularies are never conflated):
  `include_content_axis` · `derive_response_freshness` · `ResponseFreshness`
  (`disposition`, `axis_verdict`, `truncation_verdict`,
  `content_watermark_returned`, `content_age_seconds`, `returned_count`,
  `total_count`, `future_dated`, `disclosure`) · `FreshnessDisposition`
  (GATE / REFUSE / DORMANT) · `AxisVerdict` (OK / AXIS-UNDECLARED /
  AXIS-DROPPED / AXIS-NULL / AXIS-UNPARSEABLE) · `TruncationVerdict`
  (OK / TRUNCATED). `require_content_age_seconds()` is **not** used: this limb
  branches on `disposition` because it needs the DORMANT arm.

- **Guards wired (§1.6 Lane K row):** T-GUARD (§1.2b) ☑ · C-NULL (§1.3) ☑
  (C-NULL-a, consumer-local; deterministic sentinel = `threshold ×
  warn_multiplier + 1.0`, finite per COND-4 — `inf` refused)
- **AXIS-DROPPED tooth — ☑ IMPLEMENTED.** W2-F1b (§D.8) was **RULED at G1
  (2026-08-11)**: the overloaded `AXIS-ABSENT` token is split into
  **AXIS-UNDECLARED** (referent (A), dormant, never a refusal) and
  **AXIS-DROPPED** (referent (B), the tooth, loud refusal). Both dispositions
  now exist under distinct names, so neither branch was built against the
  unresolved token.
- **F-GUARD (DET-5, ruled 2026-08-11) — ☑ IMPLEMENTED** as a peer of T-GUARD,
  not a fifth axis token: `age < -allowance` → loud refusal;
  `-allowance ≤ age < 0` → clamp to 0.0, `future_dated` retained, disclosure
  logged. Per-constituent; any breach refuses the combined axis. Allowance is a
  new ASR-side env-overridable setting `offer_axis_future_skew_allowance_seconds`
  (default 60s, **PROVISIONAL**, carries a UV-P — no skew measurement exists yet
  and the clamp-band disclosure log is the re-baselining channel).
- **HELD items acknowledged:** HELD-1 ☑ (discharged at G1 → `axes_present`
  normalizes to `[]` at the SDK parse boundary; bound, not re-derived) ·
  HELD-2 ☑ (discharged by construction — the consumed `content_age_seconds` is
  result-scoped and travels adjacent to the watermark it was derived from, so
  its referent is readable off the object carrying it) ·
  **W2-F1b (§D.8) ☑ RULED at G1 — no longer blocking**
- **Non-promises re-affirmed:** no threshold moved (D-3 stands as a recorded
  refusal); nothing under `sdks/**` was written by this limb; the shared
  `autom8y-reconciliation` gate is unmutated (C-NULL-b remains
  enumerated-not-recommended); D-5b untouched.
- **Signed:** K-ASR (10x-dev principal-engineer seat) — date: 2026-08-11
  — **COMPLETE as of 2026-08-11** (PR link + verbatim wire-field quote both now
  present per §F's two-condition rule). Completing the signature attests the
  implementation-against-vocabulary claim only — it is NOT a landing or
  activation receipt; GATE-1 (CERT §2) and the REALIZE predicate (CERT §3d)
  remain separately gated downstream.

### K-SDK

- **Branch:** `feat/sdk-offers-content-axis` (monorepo `autom8y/autom8y`, base `origin/main` @ `dec8a513`)
- **PR link:** https://github.com/autom8y/autom8y/pull/1506
- **Head SHA:** `73fdb253` (build `6fa3636b` + scope-note amend `552e6c6e` + S3-AUDIT amend `7ca58a81` + CI-mypy test-only repair `f55b4afb` + merge of main @`98eaca2a`/4.13.1 `73fdb253`)
- **Typed surface (published pre-implementation, quotable verbatim by K-ASR):** `.sos/wip/SURFACE-k-sdk-2026-08-11.md` — see **§9 DELTA-1**
- **Post-ruling scope-note verification (pythia, 2026-08-11):** DET-1 (`AXIS_UNPARSEABLE`)
  **BLESSED**; DET-5 **RULED** — F-GUARD lands ASR-side, this limb's unclamped
  disclosure + `future_dated` flag stand as built. Three binding scope notes verified:
  - **Note 1 (all-or-nothing per response) — COMPLIANT AS-BUILT.** The parse loop
    returns on the first unreadable value; there is no skip-and-continue path.
    Proof: `TestAllOrNothingPerResponse` (bad-first / bad-last / bad-middle /
    bad-among-nulls) + `test_the_parseable_subset_max_is_never_returned`.
  - **Note 2 (NULL/UNPARSEABLE boundary) — COMPLIANT AS-BUILT.** `null` →
    `AXIS-NULL`; `""`, `"   "`, `0`, `0.0`, `False` → `AXIS-UNPARSEABLE`. The
    empty-string trap was already closed (`if not text: return None` precedes
    `fromisoformat`). Proof: `TestNullUnparseableBoundary`, including
    `test_empty_string_and_null_are_distinguished_side_by_side`.
  - **Note 3 (CAP-SIG malformation → dormancy) — VIOLATED AS-BUILT, AMENDED at
    `552e6c6e`.** The validator normalized `None → []` but let every other
    malformed roster reach the `list[str]` check, raising `ValidationError` out
    of the whole response parse — worse than a refusal, an uncaught exception on
    the query path. Now any non-well-formed roster (non-list, or a list with a
    non-string element) normalizes to `[]` → `AXIS-UNDECLARED` / `DORMANT`.
    A partial roster is normalized **whole**, not filtered to its string subset:
    salvaging one good element would let a malformed signal still *declare* an
    axis. Proof: `TestMalformedCapabilitySignal` (9 shapes) +
    `test_a_malformed_axes_present_never_raises_on_the_query_path` (wire-level,
    6 shapes), two-sided against `test_a_well_formed_roster_still_works`.
- **§1.1 wire-field names implemented (verbatim from §E.2):**

```
content_watermark
content_watermark_returned
content_age_seconds
content_digest
frame_built_at
served_entry_stamped_at
served_tier
fetched_rows
sections_fetched
sections_total
freshness_axis
axes_present
```

All twelve, declared on `QueryMeta` as optional-with-defaults. Copied from §E.2,
not retyped; none omitted, none altered. Rationale for declaring the full roster
at leg 2 rather than only the K-consumed subset: the `stale_served` precedent
(§1.5) — an undeclared field is dropped on the floor for its entire life — plus
the census §5 finding that the publish pipeline is red, so a second SDK release
to declare the Lane-G producer residue is not a cheap operation.

- **Guards wired (§1.6 Lane K row):** T-GUARD (§1.2b) ☑ · C-NULL (§1.3) ☑
  - **T-GUARD** — per-response `TruncationVerdict`, `returned_count < total_count`
    (`total_count` is the wire name of the fence's `total_available`; ASR already
    maps it so at `fetcher.py:344`). A truncated result refuses; it never advances
    freshness. Reported independently of the axis verdict so the caller can see
    *which* guard fired.
  - **C-NULL** — both null states refuse: zero rows, and an all-null column.
    Per the G1 disposition, under K these states are directly observable in the
    payload, so C-NULL is implementable here without CAP-SIG. `AXIS-UNPARSEABLE`
    carries the same disposition for a value that is present but unreadable
    (named separately so "the producer said null" and "the producer sent garbage"
    do not share one token — see SURFACE §6 DET-1).
- **AXIS-ABSENT tooth — ☑ IMPLEMENTED per the G1 adjudication (2026-08-11), which
  RESOLVED §D.8 / W2-F1b by splitting the token into two names with the two
  opposite dispositions:**
  - **`AXIS-UNDECLARED`** (referent A) — dormant, fall back with a *disclosure*
    log, **never a refusal**. Scoped to producer-emitted meta axes and, at this
    limb, to the no-opt-in case. `FreshnessDisposition.DORMANT`.
  - **`AXIS-DROPPED`** (referent B) — **the tooth. Loud refusal.** Fires only on
    all three of: the caller selected `last_modified`; the select passed
    `engine.py:213-219` schema validation (established by the `200` itself, since
    an unknown column raises `UnknownFieldError` before any projection); and the
    returned rows do not carry the column (`engine.py:236-238`'s silent drop).
    Never silent-pass, never fall back without explicit disclosure, never
    synthesize. `FreshnessDisposition.REFUSE`, with no derived watermark or age
    on the object for a caller to gate on by mistake.
  - **Skew** (G1 #6) is checked **first and unconditionally**: no opt-in ⇒
    `AXIS-UNDECLARED`, never `AXIS-DROPPED`. A skewed fleet does not start refusing.
- **Three-leg chain position (§1.5):** leg 2 — `QueryMeta` declares the fields (the `stale_served` precedent: an undeclared field is dropped on the floor for its entire life) ☑
- **HELD items acknowledged:** HELD-1 ☑ · HELD-2 ☑ · **W2-F1b (§D.8) ☑**
  - **HELD-1 (absent-representation of `axes_present`) — DISCHARGED to `[]`** per
    G1 #4: normalized to `list[str]`, default `[]`, **at the SDK parse boundary**,
    via a `mode="before"` validator that also maps an explicit wire `null` to `[]`.
    Without that validator a producer's honest `"axes_present": null` would fail
    validation against the non-optional `list[str]` and crash the whole response
    parse. `None` can never reach the membership test. **K-ASR: bind to `[]`; do
    not re-derive.**
  - **HELD-2 (which value occupies `content_age_seconds`) — held open on the
    producer half; discharged on this surface** per G1 #8. `content_age_seconds`
    on `ResponseFreshness` is result-scoped **by construction** — derived from
    `content_watermark_returned`, which is carried **adjacent on the same
    object** — so the field is never polymorphic: its referent is readable off
    the object that carries it. `QueryMeta.content_age_seconds` is a distinct
    field on a distinct object carrying whatever a producer sends; the two are
    never coalesced, preferred, or merged (SURFACE §2.6 NO-COALESCE). The Lane-G
    producer-half question remains for the follow-on.
  - **W2-F1b — consumed as RULED at G1**, not defaulted. Both dispositions are
    implemented, under the two distinct names the ruling assigned them.
- **Mandatory Lane-K mitigations (G1 #9), all three, unconditionally:** additive/
  read-only at the wire ☑ · opt-in **and** non-throwing ☑ · skew-degrades-to-
  UNDECLARED ☑. G1 #7 (never mutate a caller's explicit `select`) is satisfied
  structurally: the projection is appended to a **new list**, only at an opt-in
  call site.
- **Deviations from the G1 disposition text (#1-#9):** **NONE.** Five
  implementation determinations on points the disposition and the fence leave
  open are named at SURFACE §6 (DET-1 `AXIS-UNPARSEABLE` as a fourth *reason*
  within the refusal family; DET-2 opt-in-with-no-select degrades to dormant
  rather than false-refusing or fabricating a select; DET-3 naive timestamps read
  as UTC per the declared wire type; DET-4 a partially-carried column refuses;
  DET-5 a future-dated watermark is disclosed unclamped, **operator/architect
  card**, not refused). None contradicts #1-#9.
- **Delivery status:** merge-cleared by the D-10(e) census; **deployed delivery
  awaits publish convergence** — CodeArtifact tops at 4.12.0 and 4.13.0 has been
  merged-unpublished for six days (census §5). Recorded in the PR body as an
  operator card. Version 4.13.0 -> **4.14.0** (additive MINOR).
- **Signed:** principal-engineer, K-SDK seat (session-20260811-115247-a1ccd942) — date: 2026-08-11

### FIX-N-B

- **Branch:** `fix/null-watermark-decay`
- **PR link:** https://github.com/autom8y/autom8y-asana/pull/338 — **OPEN, MERGE-HELD**
- **Head SHA:** `f9e605936181e845a08499c9d3410bcbe4798d0a`
- **§1.1 wire-field names implemented (verbatim from §E.2):**

```
(none)
```

  **NONE — and this is a scope statement, not a skew or a HELD item.** This leg
  emits no wire field: it repairs the *entry stamp* (`DataFrameCacheEntry.created_at`
  on the S3 hydration path) that today's `data_age_seconds` anchors on — the
  referent §1.1 row 2b names `served_entry_stamped_at`. No name from §E.2 was
  needed, so none was retyped, abbreviated, or altered. Emitting the axes is the
  Lane-G producer follow-on, not this micro-packet.
- **§1.3 clause implemented:** the synthetic-fresh GENERATOR at
  `cache/dataframe/tiers/progressive.py:187-189` / `:202-209` — `content_watermark`
  is **NEVER synthesized** ☑
  *Narrowed ground (pythia, 2026-08-11):* the original ground "cures a live
  false-fresh emission" is **FALSIFIED and superseded on the record** — the
  blast-radius UV-P (`UVP-null-watermark-frequency-2026-08-11.md`) measured ZERO
  occurrences (594/594 loads, 118/118 sidecars) and the trap is structurally
  unreachable under the sole storage implementation. The surviving ground is a
  **latent-trap guard**: the state is legal by Protocol signature
  (`dataframes/storage.py:65`, return types `:1080`/`:1103`, duck-typed dispatch
  at `progressive.py:151`) and disarmed only by that implementation's
  sidecar-first read ordering. **ADMITTED** on the replaced ground.
- **Timing (source §4 D-6):** authored now, applied **after** the P5 window closes ☑
  (gates on the PR: P5 window ≥2026-08-12T09:19:45Z · C-NULL landed consumer-side)
- **HELD items acknowledged:** HELD-1 ☑ · HELD-2 ☑ · **W2-F1b (§D.8) ☑**
  (this leg consumes no `AXIS-ABSENT` token; §D.8 lists it as *not blocked*)
- **Signed:** principal-engineer (10x-dev, FIX-N seat) — date: 2026-08-11

### FIX-N-C1

- **Branch:** `fix/preload-stamp-honesty`
- **PR link:** https://github.com/autom8y/autom8y-asana/pull/339 — **OPEN, MERGE-HELD**
- **Head SHA:** `79c0078c3a640200bcfb812c0870a2351ac6706f`
- **§1.1 wire-field names implemented (verbatim from §E.2):**

```
(none)
```

  **NONE — scope statement, not a skew.** This leg emits no wire field. It
  repairs the *serving entry's* `created_at` on the startup-preload put — the
  quantity §1.1 row 2b names `served_entry_stamped_at` and marks **DISCLOSURE
  ONLY / process-local**, and which is today's `data_age_seconds` anchor. No
  §E.2 name was needed, so none was retyped or altered.
- **Clauses implemented:** **§1.4 CO-SOURCING** — the stamp describes the bytes
  in the same put (`s3_watermark` and `s3_df` come back from the same
  `load_dataframe`; the cascade self-heal re-persists any corrected frame under
  that same watermark) ☑ · **§1.6 fresh-task acceptance case** — a newly started
  worker reports the same freshness as a long-lived one for the same substrate
  (DIAG-S1 F3.1) ☑
- **COND-6 / D-5 BINDING CONDITION attested:** `created_at: datetime | None = None`,
  `None → datetime.now(UTC)`; every existing caller byte-identical in behavior ☑
  — *a required parameter or a changed default takes C1 out of the FIX-N class and
  back to re-adjudication.* **Attested mechanically**: the parameter is
  `KEYWORD_ONLY` (positional surface unchanged), annotation `datetime | None`,
  default `None`; `test_signature_is_default_preserving` is the standing tripwire,
  and an AST census over `src/` proves exactly one call site opts in.
- **Timing (source §4 D-6):** authored now, applied **after** the P5 window closes ☑
  (gates on the PR: P5 window ≥2026-08-12T09:19:45Z · C-NULL landed consumer-side)
- **HELD items acknowledged:** HELD-1 ☑ · HELD-2 ☑ · **W2-F1b (§D.8) ☑**
  (this leg consumes no `AXIS-ABSENT` token; §D.8 lists it as *not blocked*)
- **Signed:** principal-engineer (10x-dev, FIX-N seat) — date: 2026-08-11

---

## §G FENCES HONOURED AT THIS STATION

- **Transcription only.** No clause authored, no field added, renamed, reordered,
  or "improved". Everything outside the fence is provenance, fidelity receipt,
  ledger, extract, or signature slot.
- **Zero writes outside this artifact path.** Nothing under `src/` was read-modified,
  written, edited, or applied. No warm fired. No ASR tick triggered. No serve-path
  request issued. No `ari` command run.
- **Byte-fidelity is mechanical, not asserted** — §B records the exact commands and
  their empty output (exit 0), reproducible against this file and the source.
- **Nothing unruled was defaulted.** Two unruled sub-clause items are inscribed
  HELD (§D.3) and surfaced, not resolved.
- **No internal inconsistency was fixed silently.** §D.7 records the W2-F5 result
  (none); §D.6 records the four representation notes rather than editing the fence;
  **§D.8 records the W2-F1b AXIS-ABSENT collision as UNRESOLVED** — both referents
  quoted verbatim, both dispositions left standing, no side picked, no default
  taken. Adjudication rides the W2-F1 pythia dispatch at gate G1.
- **This artifact adds no evidence and lifts no ceiling.** The source's SPLIT
  evidence posture (source §5) carries through unchanged.
