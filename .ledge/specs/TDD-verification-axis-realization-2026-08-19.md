---
type: spec
status: draft
title: TDD — verification-axis realization (verification_age_seconds, end-to-end)
initiative: asr-verification-axis-landing
sprint: SPR-V0
rite: 10x-dev
author: architect
created: 2026-08-19
evidence_grade: MODERATE
grade_ceiling_reason: >-
  Single-attester, self-authored design. ADVISORY §C.5 is binding on this
  initiative: STRONG is not available at all, disjoint METHODS are not disjoint
  ATTESTERS, and ambiguity rounds toward the weaker grade. SPR-VC (dre /
  change-warden, dispatched from the monorepo root) is the disjoint attester.
pins:
  autom8y_asana_origin_main: e3aab8d4
  autom8y_origin_main: 3a066a5a
  probed_at_utc: "2026-08-19T14:46Z – 15:06Z"
production_change: NONE
readiness_py_touched: false
---

# TDD — Verification-Axis Realization

> **SPR-V0 design lock.** Zero production change. `readiness.py` byte-unchanged.
> This artifact rules FORK-1 and FORK-3, discharges UV-P-7 and R-O3, returns the
> R-1 verdict, fixes the grain, and specifies V1 / V2 / V3 as atomic per-repo PRs.

---

## §0 Scope, provenance, and the divergences this artifact declares

### §0.1 What this locks

Realizing `verification_age_seconds` end-to-end so the `offers` readiness gate
measures **"how long since these rows were confirmed against the live source"**
instead of **"how long since a human last touched a task in the quieter of two
Asana pipeline pools."** The second quantity is construct-invalid at every
cut-score (DIAG §2.4); the first is the axis of record per CONTRACT §1.2
[A-2026-08-12].

### §0.2 Consumed, not re-derived

| Artifact | Consumed for |
|---|---|
| `.sos/wip/frames/asr-verification-axis-landing.md` (autom8y) | §3 problem, §7 predicate, §8 constraints, §9 scars |
| `.sos/wip/frames/asr-verification-axis-landing.shape.md` (autom8y) | SPR-V0 block, FORK-1/FORK-3 slates, §5 critical path, §11 substrate |
| `.ledge/reviews/DIAG-offers-watermark-advance-2026-08-17.md` (asana) | §2 mechanism, §2.4 two-sided bar, §3 grain finding, §5 rank-1 lever, §4 R-1/R-2/R-5 |
| `.ledge/decisions/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md` (asana) | §1.2 [A-2026-08-12], §1.2b, §1.3, §1.4, §1.5, §1.5b, §1.6, §E.2 |
| `.ledge/reviews/CRITIC-wsa-watermark-cure-2026-08-18.md` (asana) | C-1, C-3, C-7, C-8, C-9 |

### §0.3 Divergences this artifact declares up front

Four. Each is a place where a downstream reader following the shape or the
frame literally would build the wrong thing. All four are grounded in §14
receipts.

| # | Source claim | This TDD's finding | Consequence |
|---|---|---|---|
| **D-1** | Shape SPR-V0 exit artifact path: `autom8y-asana/.ledge/decisions/DESIGN-verification-axis-realization-2026-08-19.md` | The dispatch (potnia, PT-00) directed `.ledge/specs/TDD-verification-axis-realization-2026-08-19.md`, `type: spec`. This artifact is at the dispatch path. | SPR-VC and PT-01 look **here**. No DESIGN-*.md exists and none will be authored. |
| **D-2** | Shape SPR-V3 + dispatch: floor pin at `services/account-status-recon/pyproject.toml:26` | The pin is at **`:35`** — and was `:35` at the shape's own pin `d9b9c92c` too. Line 26 is a `#` comment line inside the R-6 rationale block. There is also a **third** pin nobody named: `:79` `autom8y-core[testing]>=4.6.0,<5.0.0`. | **THREE pins, not two.** §8. |
| **D-3** | Shape SPR-V3: "Moving only one is a false-green: the workspace source makes DEV resolve editable while the deployed image resolves the published floor." | The *mechanism* is right, the *attribution* is inverted. The root `pyproject.toml` **never enters the ASR image build context** (Dockerfile `:58` copies only the service pyproject; no `uv sync`, no `uv.lock`, no parent-dir copy). The root pin cannot influence the image at all. | The **service** pin is the only image-governing pin. The root pin is SSOT hygiene. §8. |
| **D-4** | DIAG §3 + shape SPR-V0 exit #3: grain from `billable_sections()` (`activity.py:92-94`) | `billable_sections()` hardcoded in the producer **violates frozen CONTRACT §1.4 CO-SOURCING** on a single-classification request. The correct primitive is the request-resolved set the engine already computes at `query/engine.py:124`. The billable grain is reconstituted by ASR's `max(ages)` combination, not by a producer hardcode. | §4. |

### §0.4 What is NOT resolvable

`[UV-P: the "§Q3.1 seam table from the DIAG's companion analysis" named in the
SPR-V0 dispatch | METHOD: repo-wide grep for `§Q3`/`Q3.1` across
autom8y-asana and autom8y at origin/main | REASON: returns only
`COVERAGE-DISCLOSURE-render.md` and the DIAG itself; no companion artifact
carrying a §Q3.1 seam table exists as a file at either origin/main. The seam
table is therefore DERIVED FIRST-HAND in §5.1 of this artifact from code, not
inherited. If the operator holds that table out-of-band, §5.1 should be diffed
against it before PT-01.]`

---

## §1 The quantity, and the live proof that it is reachable

### §1.1 What the axis is (CONTRACT §1.2 [A-2026-08-12], binding)

> A verification axis advances **only** through a per-section probe or fetch that
> (a) reached the live source, (b) returned a verdict other than `PROBE_FAILED`,
> and (c) where the verdict required a delta, had that delta successfully
> applied. It **never** advances on assembly, on a build clock, on a cache
> write, on a fetch that returned nothing, or on the passage of time.

That law is already implemented on the write side, and the implementation is
faithful to it — `dataframes/builders/progressive.py:514-574`:

- `:515-516` — `PROBE_FAILED` → `continue`. Never stamps. **(a)+(b)**
- `:517-520` — delta verdict whose `section_gid ∉ applied_gids` → `continue`. **(c)**
- `:561-572` — `CLEAN` on a null-watermark, non-coherently-empty section →
  heal the watermark, **do not stamp**. (The D8 hash-only-clean guard.)
- `:573` — `stamp_info.last_verified_at = now`, reached only past all three gates.

**This is the RED tooth, and it is structural.** No code path stamps without a
live probe. The DIAG's two-sided table (§2.4) is correct: verification is the
only one of the three axes that separates "quiet business, healthy warmer"
(GREEN) from "halted warmer" (RED).

### §1.2 The live GREEN-arm feasibility receipt

Read from production at 2026-08-19T15:05:24Z (manifest `LastModified`
2026-08-19T14:46:33Z), pool-level only per critic C-3:

| Pool | Sections in manifest | Sections **without** `last_verified_at` | `min(last_verified_at)` | Implied `verification_age_seconds` |
|---|---|---|---|---|
| `active` | 22 | **0** | 2026-08-19T14:46:32.232624Z | **1132.4 s** |
| `activating` | 5 | **0** | 2026-08-19T14:46:32.232624Z | **1132.4 s** |
| billable (∪) | 27 | **0** | 2026-08-19T14:46:32.232624Z | **1132.4 s** |

Manifest totals: `total_sections=34`, `completed_sections=34`, all `complete`,
**0 null names**, `schema_version=1.6.0`. Seven manifest sections fall in
neither requested classification.

Against the same day's gate reading:

| Axis | Value | Bar (3600 s) | Verdict |
|---|---|---|---|
| `content_age_seconds` @ 2026-08-19T12:01:05Z, trace `8b6db8eea70febbc…` | **52 566.7 s** | 14.6× over | **FAIL** (as it has 47 consecutive ticks) |
| `verification_age_seconds` @ 2026-08-19T15:05:24Z | **1 132.4 s** | 0.31× | **PASS** |

Three things this receipt establishes, and one it does not:

1. **Clause (iii) — the GREEN arm is achievable on real data.** Not argued;
   measured, on the live manifest, before a line of code is written.
2. **The strict no-backfill rule (§5.3) is satisfiable in production TODAY.**
   Zero in-scope sections lack a real stamp. The design does not have to
   tolerate a state that does not exist.
3. **The C-1 standing invariant is GREEN.** In `active`, null-watermark count
   (17) equals zero-row count (17); in `activating`, 2 equals 2. Every
   null-watermark section is exactly a zero-row section, so FIX-1's
   coherently-empty exemption covers all of them and all 34 stamp.
   `non-empty AND null-watermark == 0` holds live.
4. **It does NOT establish that the grain is observable.** All 34 stamps carry
   the *identical* instant (`14:46:32.232624Z` — the single `now` taken at
   `progressive.py:494` and applied at `:573`). `min` over any subset returns
   the same number. **A wrong grain is numerically invisible in production
   today** and would stay invisible until a partial warm failure. This is a
   named trap: see §11 TRAP-3.

---

## §2 R-1 verdict — three freshness modules, one derivation, no fourth

**Exit criterion.** "The design must state which one owns the verification
quantity and why the other two do not, OR justify a fourth. A silent fourth
derivation is a PT-01 FAIL."

### §2.1 The three modules at `e3aab8d4`

| Module | LOC | Role | Owns the quantity? |
|---|---|---|---|
| `src/autom8_asana/dataframes/builders/freshness.py` | 672 | **The prober.** `ProbeVerdict` (`:109`), `SectionProbeResult` (`:119`), `SectionFreshnessProber` (`:137`). Produces the *evidence* (`verdict != PROBE_FAILED`) that authorizes a stamp. Computes no age. | **NO** — it is upstream of the quantity, not a derivation of it. |
| `src/autom8_asana/metrics/freshness.py` | 855 | **The reader.** `VerificationAge` (`:70`), `compute_verification_age` (`:735`). The ONLY existing code that computes `now − min(last_verified_at)`. | **YES.** |
| `src/autom8_asana/substrate/freshness.py` | 317 | **Seam-1 v2 pure core.** `fold_built_from_live_at` (`:115`) = MIN over sections' last **content-fetch** instants. FROZEN `v1.0-frozen-2026-07-29`. R-1: zero importers in `src/` — built and UNWIRED. | **NO**, and it must not. |

### §2.2 Why `substrate/freshness.py` is not a duplicate

R-1 warns that a frozen v2 lane computing "exactly the axis the operator just
ruled as the axis of record" is a partial duplicate. **It is not the same
quantity, and CONTRACT §1.2 NON-ALIASING clause 4 says so in terms:**

> `verified_at` is **NOT** `built_from_live_at`. […] `verified_at` is a v1
> quantity: a fold over per-section **probe or fetch** instants, not the Seam-1
> content-fetch fold. It must never carry the Seam-1 name and the two must
> never be coalesced.

`fold_built_from_live_at` folds **content-fetch** instants — strictly narrower.
A `CLEAN` probe advances `verified_at` and does **not** advance
`built_from_live_at`. Collapsing them would either (a) import Seam-1's stronger
guarantee onto a weaker quantity, or (b) destroy the whole GREEN arm (a healthy
pipeline that fetches nothing because nothing changed would read as unverified).

**R-1 is RECONCILED, not deferred:** the two quantities are contract-distinct by
frozen clause; the v2 lane's frozen-and-unwired state is a separate defect
(SPR-R1) that this initiative neither depends on nor worsens. **This design
adds no importer of `substrate/`.**

### §2.3 The owning module, and the shape of the reuse

`metrics/freshness.py` owns it. But `compute_verification_age` as written is
**not** contract-conformant for the serve path — three defects:

| # | Defect | Site | Contract clause violated |
|---|---|---|---|
| G-1 | Grain hardcoded to `classifier.active_sections()` (22 sections) | `:785` | §1.2 VERIFICATION GRAIN ("the requested classification(s)") — and §1.4 CO-SOURCING under the fix (see §4) |
| G-2 | `last_verified_at is None` → falls back to `info.written_at` | `:804-813` | §1.2 NON-ALIASING clause 1 — **`written_at` is named verbatim in the forbidden-source list.** `mark_section_complete` sets `written_at=datetime.now(UTC)` (`section_persistence.py:211`); it is a write clock. |
| G-3 | `VerificationAge.unavailable()` returns `max_age_seconds=0` and `stale=False` | `:102-116` | §1.3 null-decay ("unprovable is stale, never fresh"). Any consumer that reads the number without first reading `available` gets **maximally fresh**. |

G-1/G-2/G-3 are all correct *for the module's existing purpose* — a metrics-CLI
warning line whose ruled degrade path is "fall back to the mutation-axis
signal" (ADR-006 §Decision-6). They are wrong for a **gate**.

**RULING — one fold, two policies, zero fourth derivations.**

Extract the join-and-fold into ONE private helper in `metrics/freshness.py`,
consumed by exactly two public callers in the same file:

```python
def _fold_oldest_verified(
    manifest: Any,
    section_names: frozenset[str],      # already lower-cased
    *,
    allow_written_at_backfill: bool,
) -> _Fold:                              # (oldest, in_scope, missing, backfill_used)
    ...
```

| Caller | Scope argument | `allow_written_at_backfill` | Purpose |
|---|---|---|---|
| `compute_verification_age(...)` — **UNCHANGED public behavior** | `classifier.active_sections()` | `True` | metrics CLI SLI (ADR-006). Not touched by this initiative beyond the internal extraction. |
| `compute_serve_verification(...)` — **NEW** | caller-supplied, request-resolved | `False` | the wire axis |

The quantity is derived in exactly **one** place. The two callers differ only
by two explicit parameters. A silent fourth derivation is structurally
impossible: the fold is private, and both call sites are in the same file and
the same diff.

**Equivalence obligation for SPR-V1:** the extraction must be proven
behavior-preserving for `compute_verification_age` — the existing
`tests/unit/metrics/test_freshness.py` and `test_freshness_adversarial.py` pass
**unmodified**. If a test has to change, the extraction was not an extraction.

---

## §3 FORK-1 RULED — the hot-path manifest read

### §3.1 Enumeration audit first (option-enumeration-discipline §4 Step 2)

The shape's slate is OPT-1…OPT-6 and carries the discipline's own instruction:
*"NO recommendation is attached here by design."* Applying §3's mechanical
check —

> *"For each option, ask: what existing platform feature already handles this?
> If the design is silent on a relevant existing feature → likely gap."*

— surfaces a gap option. **Every option on the slate is priced against an S3
round-trip that the serve path is already paying.**

`query/engine.py:248-256`, inside `execute_rows`, unconditionally:

```
# 12.5 Derive honest_contract_complete from SectionPersistence manifest.
honest_contract_complete = await self._derive_honest_contract_complete(
```

and inside that method, at `:588`:

```
manifest = await section_persistence.get_manifest_async(
```

`get_manifest_async` (`section_persistence.py:433-478`) misses its in-process
`_manifest_cache` and calls `self._storage.load_json(...)`, which is
`return await self._get_object(key)` (`storage.py:1426`) — an uncached S3 GET.
The manifest object is then used for exactly one boolean
(`is_honest_complete(manifest)`, `:598`) and **discarded**.

**The stamp is already in an object the serve path already fetched, already
holds, and already throws away.** OPT-1's sole `against` — "adds an S3
round-trip to the hot path" — was written on an unverified premise and is
FALSE. OPT-2 / OPT-3 / OPT-4 / OPT-5 exist to avoid a cost that is not there.

This is the option-enumeration-discipline outcome the skill predicts: the gap
option is not a marginal improvement, it changes the recommendation.

### §3.2 The complete slate — SEVEN options, evaluated symmetrically

| ID | Mechanism | For | Against | Clause (iv)? | Horizon vs 3600 s bar | Disposition |
|---|---|---|---|---|---|---|
| **OPT-1** | Add an S3 manifest read per request on the serve path | Always current; no horizon | Would add I/O and a new serve-path failure mode — **except the read already exists**, which makes this option a description of the status quo plus a redundant second GET | YES | 0 s | **SUBSUMED by OPT-7.** Correct in intent; its cost column is falsified and its mechanism is redundant. |
| **OPT-2** | Carry `last_verified_at` on the cache entry, unbounded | Zero hot-path I/O | Stamp ages with the entry; axis inherits the cache's horizon; reproduces the frozen-anchor class the predecessor spent five days diagnosing | **NO** | unbounded | **PRE-REFUSED** (shape, binding). Re-refused here on evidence. |
| **OPT-3** | Cache-entry carry with TTL strictly < 3600 s | Zero I/O common case; bounded horizon | Correctness depends on a TTL invariant living far from the gate; needs an asserted coupling, not a comment; adds a knob whose independent movement silently breaks the guarantee | YES, conditionally | < 3600 s by construction | **REFUSED** — buys nothing OPT-7 does not give free, and costs a cross-module invariant. |
| **OPT-4** | Conditional GET / `If-None-Match` on the manifest object, decoupled from the dataframe cache | Near-zero cost on the unchanged path; always-current; independent lifecycle | A second cache; 304 + clock-skew semantics to specify; a distinct failure mode; `S3DataFrameStorage` has no conditional-GET surface today (`load_json → _get_object`), so this is net-new machinery | YES | 0 s | **REFUSED** — strictly more machinery than OPT-7 for identical semantics. |
| **OPT-5** | Producer stamps the value into the serve payload at build time | No consumer-side I/O; producer owns the stamp | Collapses to OPT-2 on a warm-cache hit; relocates the horizon rather than removing it. **Falsified empirically:** the build clock has already been proved tooth-less — a warm with `fetched_rows=0`, `sections_delta_updated=0`, 34/34 CLEAN, 5.8 min wall time still stamped a fresh watermark (DIAG §5 rank-3) | **NO** | = cache TTL/grace | **REFUSED.** |
| **OPT-6** | Emit `verification_age` as a separate CloudWatch metric stream ASR reads instead of the query response | Fully decouples the axis from the serve path | **Fails the same-trace conjunct.** Frame §7 conjunct 3 requires axis, `content_hash`, and `SourceCoverage3of3` on the **same `trace_id`**; a metric stream is not derivable from the response it gated. Adds a metric-pipeline delay between fact and gate. Also inverts §1.4 CO-SOURCING: the signal would no longer describe the bytes it accompanies — it would describe no bytes at all | **NO** (co-sourcing broken) | metric-pipeline lag, unbounded | **REFUSED — the same-trace conjunct is NOT cleared.** The shape required OPT-6 to clear it or be refused. It does not clear it. |
| **OPT-7** ★ | **Reuse the manifest the serve path already fetches** — a sibling derivation alongside `_derive_honest_contract_complete`, hitting the per-request `_manifest_cache` memo, costing **zero additional S3 GETs** | Always current by construction; **zero** added I/O; no new cache, no new TTL, no new failure mode; no coupling to `honest_contract_complete`'s value | Rests on an invariant that must be **asserted, not assumed**: `EntityQueryService` is per-request. If it is ever hoisted to a singleton the memo becomes unbounded and this silently degrades to OPT-2 | **YES** | **0 s** | **RULED.** |

**Null-mechanism option** (discipline §5 item 2): OPT-2/OPT-5 are the
"do not add mechanism" arms — both are refused on *correctness*, not on cost.
**Delegation option** (§5 item 4): OPT-6 is the delegate-to-an-existing-substrate
arm — refused on the same-trace conjunct. Both were evaluated at the same depth
as OPT-7 rather than dismissed.

### §3.3 The OPT-7 ruling, and why it does not re-create the staleness being cured

Required by the shape's exit criterion, stated directly:

The staleness being cured is an **anchor frozen in the past that then climbs
+14 400 s/tick**. Three independent properties prevent OPT-7 from re-creating it:

1. **The read is per-request and uncached across requests.**
   `api/routes/query.py:468` constructs `EntityQueryService()` **inside** the
   `query_rows` handler (`async def` at `:334`, `@router.post` at `:321`).
   `SectionPersistence` is lazily created per service instance
   (`query_service.py:318-332`) and its `_manifest_cache` starts empty. Within
   a request it is a memo (two call sites, one GET); across requests it cannot
   exist. **The only `_manifest_cache` eviction in the module is inside
   `delete_manifest_async` (`:1193`)** — there is no TTL and no read-path
   invalidation, which would be a fatal staleness trap on a long-lived object
   and is harmless on a per-request one. This is exactly why the invariant must
   be asserted (TRAP-1, §11).
2. **The value is not time-derived on the consumer side of a cache.** It is
   `min(last_verified_at)` over section records read fresh from S3 on this
   request. There is no entry age, no `created_at`, no build clock anywhere in
   the derivation.
3. **The horizon is 0 s.** The bound the shape asked for — "must not introduce
   a staleness horizon longer than the gate's PASS bar (3600 s)" — is satisfied
   with the entire budget unspent. In production today the axis reads
   ~1 132 s against a 3 600 s bar, and that number is set by the *hourly warm
   cadence*, not by any cache in the read path.

**Clause (iv) construct validity, demonstrated rather than asserted.** The
state "warm loop healthy + business quiet + quantity GREEN" is not hypothetical:
§1.2's live read IS that state. The stamp advanced at 14:46:32Z on a warm cycle;
the content axis was simultaneously 52 566.7 s stale because no human had edited
a task in the quieter pool since 2026-08-12. **Quiet business, healthy warmer,
GREEN.** That is the state the old axis could never produce.

---

## §4 The grain — RULED, and it is a correction to the DIAG and the shape

### §4.1 The correction

DIAG §3 and shape SPR-V0 exit #3 both say: grain from `billable_sections()`
(`models/business/activity.py:92-94`), not `active_sections()`.

`active_sections()` is unambiguously wrong — that half is right. But
**`billable_sections()` is also wrong, and it is wrong against a FROZEN clause.**

ASR issues **two separate single-classification requests**
(`fetcher.py:502-517`): `classification="active"` and
`classification="activating"`. A producer hardcoding `billable_sections()`
would answer the `active` request with a `verified_at` folded over sections
that are **not in that response's bytes**. CONTRACT §1.4, FROZEN:

> **CO-SOURCING (frozen, FORK-C).** The freshness signal in the response meta
> describes the **bytes in that same response**. A signal derived from one tier
> may never accompany bytes served from another.

`billable_sections()` returns the right *number* for this caller only by
coincidence — ASR's two calls happen to union to exactly billable, and
`max(ages)` of two identical values is that value. It would be right-answer,
wrong-mechanism, and it would break the moment any caller queries one
classification alone. ASR literally does that, twice, on every tick.

### §4.2 The ruled primitive

**Grain = the request's resolved classification section set**, which the engine
already computes and already holds in scope at the exact line where the
manifest is read:

```
query/engine.py:124   classification_sections = self._resolve_classification(request.classification, entity_type)
```

`_resolve_classification` (`:438-490`) returns `frozenset[str] | None` of
**lower-cased section names** (`:449`), via `classifier.sections_for(activity)`
(`:480`) — the same primitive `active_sections()` and `billable_sections()` are
both thin wrappers over (`activity.py:86, :88-90, :92-94`). The join in
`_fold_oldest_verified` is name-based and case-normalized, identical to the
existing `compute_verification_age` join at `:801`.

**The billable grain §1.2 requires is reconstituted at ASR, not at the
producer:**

```
producer(active)     -> verified_at_A = min(last_verified_at | 22 ACTIVE sections)
producer(activating) -> verified_at_G = min(last_verified_at | 5 ACTIVATING sections)
ASR combine          -> verification_age = max(age_A, age_G) = now - min(verified_at_A, verified_at_G)
                      = now - min(last_verified_at | ACTIVE u ACTIVATING)
                      = now - min(last_verified_at | billable_sections())   [identical, by construction]
```

Co-sourcing holds on each leg. The ruled grain holds on the combination. No
hardcode anywhere. **`billable_sections()` is not called by this design.**

### §4.3 `classification is None`

`_resolve_classification` returns `None` when no classification was requested —
the whole-frame case. Ruling: the producer then scopes to **every section in the
manifest** (the frame's own section set), which is the co-sourcing-correct
answer for a whole-frame response. ASR never takes this path; it is specified so
the behavior is defined rather than accidental.

---

## §5 V1 — the producer leg (autom8y-asana, ONE atomic PR)

### §5.1 The seam table (derived first-hand; see §0.4)

| # | Seam | Site @ `e3aab8d4` | What it already does | V1 change |
|---|---|---|---|---|
| S-a | Classification resolution | `query/engine.py:124` | computes `classification_sections: frozenset[str] \| None`, lower-cased | **read only** — pass it down |
| S-b | Serve-path manifest read | `query/engine.py:254` → `:588` | fetches the manifest from S3, uses one boolean, discards the object | **read only** — a sibling method re-requests it and hits the per-request memo |
| S-c | Fold | `metrics/freshness.py:789-819` | joins classifier names to `SectionInfo.name`, folds `min` | **extract** to `_fold_oldest_verified`; add `compute_serve_verification` |
| S-d | Meta assembly | `query/engine.py:282-299` | builds `RowsMeta(...)` with `**freshness_meta` | **add** 4 explicit kwargs (NOT via `_get_freshness_meta` — it has no manifest access) |
| S-e | Wire models | `query/models.py:225` `AggregateMeta`, `:387` `RowsMeta`, both `extra="forbid"` | | **declare** 4 optional fields on **BOTH** (§1.5: a field on one and not the other raises on `extra="forbid"`) |
| S-f | Stamp write | `dataframes/builders/progressive.py:514-574` | the RED tooth | **UNTOUCHED** |
| S-g | `honest_contract_complete` | `query/engine.py:544-613` | drives the 503 path (`query/models.py:465`) | **UNTOUCHED — byte-identical value required** |

### §5.2 The four wire fields

Three are frozen in CONTRACT §E.2. The fourth (`axes_present`) is frozen in
§1.5b/§E.2 and is **the precondition, not a detail**.

```python
# ADDITIVE to BOTH query/models.py::RowsMeta and ::AggregateMeta.
verified_at: str | None = None                  # ISO-8601 UTC; min(last_verified_at) over the REQUEST's classification-scoped sections
verification_age_seconds: float | None = None   # now - verified_at; null iff verified_at is null
verification_backfill_used: bool | None = None  # REQUIRED companion (§1.2 clause 5)
axes_present: list[str] = []                    # CAP-SIG (§1.5b): the axis names this producer speaks
```

**Populated only on the rows path.** `execute_aggregate` (`engine.py:305`) does
**not** read the manifest (it calls `_get_freshness_meta` at `:423` but never
`_derive_honest_contract_complete`). `AggregateMeta` therefore **declares** the
fields (so `extra="forbid"` cannot raise) and leaves them `None` with
`axes_present=[]` → the consumer reads **AXIS-ABSENT** for aggregate, which is
true and is §1.5b's sanctioned state. Extending the axis to aggregate is
explicitly out of scope.

**Spelling is load-bearing** (§1.2 clause 6). Refused near-misses, named so they
are not debated: `verification_seconds`, `verif_age`, `v_age`,
`verified_age_seconds`, `last_verified_at` (that token names the **manifest-tier
field** and is already collided once inside the producer repo — standing NOTE at
`section_persistence.py:106-113`), `verification_watermark`,
`verified_watermark`.

### §5.3 Emission rule — RULED (this is the design's sharpest edge)

```
in_scope := the request's resolved classification section set (lower-cased)
missing  := { s in in_scope : manifest has no entry for s, or entry.last_verified_at is None }

if manifest read raised or returned None:
    verified_at = null ; verification_age_seconds = null ; verification_backfill_used = null
    axes_present = [the three verification names]              -> AXIS-NULL -> consumer REFUSES
elif in_scope is empty:
    verified_at = null ; verification_age_seconds = null ; verification_backfill_used = null
    axes_present = [the three verification names]              -> AXIS-NULL -> consumer REFUSES
elif missing is non-empty:
    verified_at = null ; verification_age_seconds = null ; verification_backfill_used = TRUE
    axes_present = [the three verification names]              -> AXIS-NULL -> consumer REFUSES
else:
    verified_at = min(last_verified_at).isoformat()
    verification_age_seconds = (now - min).total_seconds()      # UNCLAMPED; see §5.4
    verification_backfill_used = FALSE
    axes_present = [the three verification names]              -> AXIS present -> consumer GATES
```

**Why `missing` → null and never a `written_at` backfill.** CONTRACT §1.2
VERIFICATION GRAIN says it verbatim:

> A classification-scoped section whose stamp is absent or null makes the axis
> **underivable for that response**: the emitter emits `null` and declares the
> axis in `axes_present` (AXIS-NULL). It is **never** dropped from the
> denominator, **never** skipped, **never** substituted.

and NON-ALIASING clause 1 names `written_at` in the forbidden-source list
explicitly. **G-2 (`metrics/freshness.py:804-813`) is contract-conformant for
the CLI and contract-violating for the wire.** The serve caller passes
`allow_written_at_backfill=False`; the CLI keeps `True`. The two policies never
meet.

**What `verification_backfill_used` then means on the wire.** It is the
disclosure of *why* the axis is null: `true` = "at least one in-scope section
carried no verification stamp" (the state the CLI would have backfilled);
`false` = the axis is derived, fully stamped, no reach. It is never `true`
alongside a non-null `verified_at`. This gives clause 5's required companion a
real referent while honoring clause 1 — and the two clauses are otherwise in
tension.

**Why a manifest-read failure REFUSES rather than falls dormant.** §1.3
(ratified): *"Null → DECAY. A null content axis means unprovable, and
unprovable is stale, never fresh."* Silently *not declaring* the axis on an S3
error would make a transient failure indistinguishable from an old producer
image — the precise AXIS-ABSENT/AXIS-NULL conflation §1.5b exists to kill. Cost:
one aborted report per manifest-read failure, disclosed, self-healing on the
next tick. Named as RISK-2 (§11) with an observability obligation, not a
fallback.

### §5.4 Clock skew — UNCLAMPED, deliberately

`compute_verification_age:822-823` clamps a negative age to 0. **The serve
derivation does not clamp.** A clamp turns a future-dated stamp into "maximally
fresh," which passes every threshold trivially. The SDK's existing content-axis
precedent is explicit that this is the right call —
`asana_freshness.py:195-197`: *"The negative age is carried **unclamped**;
clamping would be synthesis. Disclosed, not refused."* ASR already carries an
F-GUARD for exactly this on the content axis (`readiness.py:325-332`,
`offer_axis_future_skew_allowance_seconds`); §7.3 reuses that shape.

### §5.5 Implementation shape

- New sibling on `QueryEngine`, **not** a modification of
  `_derive_honest_contract_complete`:
  `async def _derive_verification_axis(self, project_gid, *, entity_type, classification_sections) -> _VerificationMeta`.
  Same broad-catch discipline, same `getattr(self.provider, "section_persistence", None)` guard —
  but its failure disposition is **AXIS-NULL (declared + null)**, not `False`.
- It calls `get_manifest_async(project_gid, entity_type=entity_type)`, which
  **hits the memo populated by `_derive_honest_contract_complete` at `:588`** →
  zero additional S3 GETs.
- Call ordering in `execute_rows`: `_derive_honest_contract_complete` first
  (unchanged, `:254`), then `_derive_verification_axis`. The memo is warm by
  then. If the honest-contract read failed, the verification read fails the
  same way and emits AXIS-NULL. Consistent, and no second network attempt.
- `metrics/freshness.py` gains `_fold_oldest_verified` + `compute_serve_verification`;
  `compute_verification_age`'s public behavior is unchanged (§2.3).

### §5.6 V1 exit criteria (supersedes the shape's SPR-V1 list where they differ)

1. G-1 FIXED at the **request-resolved** grain (§4.2). `billable_sections()` is
   NOT called. `active_sections()` is NOT called on the serve path.
2. G-2 held off the wire: `allow_written_at_backfill=False` on the serve caller;
   a test asserts that a manifest with one in-scope section at
   `last_verified_at=None` and a *fresh* `written_at` emits
   `verified_at=null, verification_backfill_used=true` — **not** a fresh age.
3. G-3 held off the wire: no path emits `verification_age_seconds=0` for an
   underivable axis.
4. `honest_contract_complete` proven byte-identical (existing tests unmodified).
5. Extraction proven behavior-preserving for the CLI (existing metrics tests
   unmodified).
6. **Grain test with DIVERGENT stamps** — see TRAP-3. A fixture where the
   `active` pool's min and the `activating` pool's min differ, asserting each
   single-classification request returns its own pool's min. Production cannot
   prove this today (§1.4).
7. **PRODUCTION-OBSERVABLE:** after merge and auto-deploy, a live serve-path
   response carries `verified_at` with a real value and
   `axes_present` containing the three names, observed in production telemetry.
8. **UV-P-1 discharged**: the ~13 min post-merge asana auto-deploy is OBSERVED
   at this merge. Record the measured latency, whatever it is.
9. **R-O3 inscription** (§6.2) carried verbatim in the PR body, and the §1.2
   clause-5 qualification block amended in the same PR.
10. `readiness.py` untouched — trivially true (different repo); state it, do not
    prove it.

---

## §6 V2 — the SDK leg (autom8y monorepo, `sdks/python/autom8y-core`, ONE atomic PR)

### §6.1 SEPARATE value object — RULED, and this changes the shape's SPR-V2

The shape's SPR-V2 mission says: *"Add the separately-named verification field
to `ResponseFreshness` and parse it in `derive_response_freshness`."*

**REFUSED.** Not on doctrine — on a mechanism already carded as LATENT-HIGH.

`derive_response_freshness` (`asana_freshness.py:333-522`) is **row-derived end
to end** and returns a **single `disposition` for the whole object**. Riding the
verification axis on it couples the two axes at three places, each of which is
wrong:

| Coupling site | What it does to the content axis | What it would do to the verification axis |
|---|---|---|
| `:371-387` — `content_axis_requested` false → `DORMANT` | correct | verification would go dormant because nobody asked for a **row column** it does not use |
| `:392-401` — zero rows → `REFUSE` | correct (no rows, no watermark) | **inverts the cure.** Verification is precisely the axis that CAN prove an honestly-empty frame is verified — §1.2 GRAIN: *"A verified-empty section is verified and MUST be included."* Live today: 17 of 22 `active` sections carry zero rows |
| `:473-498` — T-GUARD → `REFUSE` | correct | **imports R-5's 1000-row cliff into the cure.** Both ASR queries use `limit=1000` (`fetcher.py:504-518`); either pool crossing 1000 rows flips the whole object to `REFUSE`, and the verification axis would die with it → permanent `7201.0` sentinel abort. A cliff, not a slope. |

Verification is **meta-derived**, not row-derived. It shares no input with the
content axis. Sharing a disposition IS a shared parse branch under §1.2
NON-ALIASING clause 2.

**RULED:** a separate module surface —

```python
# sdks/python/autom8y-core/src/autom8y_core/helpers/asana_verification.py   (NEW)
class VerificationDisposition(StrEnum):
    GATE = "GATE"        # axis declared, value present -> gate on verification_age_seconds
    REFUSE = "REFUSE"    # axis declared, value null (AXIS-NULL) -> refuse loudly
    DORMANT = "DORMANT"  # axis NOT declared (AXIS-ABSENT) -> caller keeps prior behavior + discloses

@dataclass(frozen=True, slots=True)
class ResponseVerification:
    disposition: VerificationDisposition
    verified_at: str | None
    verification_age_seconds: float | None
    backfill_used: bool | None
    future_dated: bool
    disclosure: str

def derive_response_verification(response, *, now=None) -> ResponseVerification: ...
```

`ResponseFreshness` is **not modified**. `derive_response_freshness` is **not
modified**. No shared branch exists to violate.

### §6.2 R-O3 DISCHARGED (architect's delegated ruling)

CONTRACT §E.2 records: *"R-O3's delegation of that choice to the architect at
the producer-leg PR is FLAGGED and UNRULED and is not discharged by the pin."*

**Ruling: adopt the operator's pinned spelling `verification_backfill_used` as
the WIRE name; keep `backfill_used` as the in-object field name.**

Rationale: (1) the operator's 2026-08-13 pin is the later act and §E.2 lists the
long form in the frozen fifteen; (2) `backfill_used` unqualified is ambiguous on
a wire that will carry other backfills, and clause 6 makes spelling load-bearing
precisely to pre-empt that; (3) inside a module named `asana_verification` /
`freshness`, the qualifier is redundant and the existing
`VerificationAge.backfill_used` (`metrics/freshness.py:98`) needs no rename —
avoiding churn in a module this PR is already touching. **The wire name and the
in-object name differ deliberately and are documented at both ends.**

Inscription requirement (R-O3's own condition): this ruling is carried verbatim
into the SPR-V1 PR body, and the §1.2 clause-5 qualification block is amended in
that same PR to record R-O3 as **DISCHARGED-BY-ARCHITECT, CONCURRING WITH THE PIN**.

### §6.3 `QueryMeta` — three declarations

`models/asana_service.py:322-435` already declares the full frozen roster
**including `axes_present` (`:398`) with its null-normalizing validator
(`:400-435`) and a `declares_axis()` helper (`:437`)**. The three verification
names are the only roster members missing:

```python
verified_at: str | None = None
verification_age_seconds: float | None = None
verification_backfill_used: bool | None = None
```

That is the whole model change. `extra="ignore"` (`:375`) makes it non-breaking.

**The `stale_served` precedent is why this leg cannot be skipped:** asana has
emitted `stale_served` since birth and `QueryMeta` never declared it, so it has
been silently dropped for its entire life. An undeclared field is unreadable
forever.

### §6.4 V2 exit criteria

1. NON-ALIASING **proven, not asserted**: a test constructs a response with
   `content_age_seconds` present and the verification fields absent, and asserts
   `derive_response_verification` returns `DORMANT` with
   `verification_age_seconds is None` — it does **not** read the content value.
   And the inverse.
2. **AXIS-DROPPED tooth preserved:** a response declaring the axis in
   `axes_present` with `verified_at: null` returns `REFUSE`, not `GATE`, and not
   a fresh-reading number.
3. **AXIS-ABSENT ≠ AXIS-NULL:** `axes_present=[]` returns `DORMANT`;
   `axes_present=[...three...]` with null value returns `REFUSE`. Two tests, two
   distinct verdicts. This is the discriminator the entire deploy-ordering
   safety rests on (§8.4).
4. Malformed `axes_present` degrades to `[]` → `DORMANT`, never a raise
   (inherited from the existing validator; assert it holds for the new path).
5. **PRODUCTION-OBSERVABLE:** the published version is **RESOLVABLE FROM
   CODEARTIFACT** — verified by resolution, not by a green publish job, and not
   by a green CI (§8.3 explains why CI cannot witness this).
6. Version bumped from the 4.15.0 baseline at `sdks/python/autom8y-core/pyproject.toml:7`.

---

## §7 V3 — the ASR consumption leg (autom8y monorepo, ONE atomic PR)

### §7.1 "Fourth disposition path" — the reading that is NOT a contract violation

The shape says "a fourth disposition path alongside GATE/REFUSE/DORMANT". Read
as *"add a fourth member to `FreshnessDisposition`"* that is a NON-ALIASING
clause-2 violation — one enum is one parse branch. **Ruled reading: a NEW
three-valued switch UPSTREAM of the existing one, whose DORMANT arm delegates to
today's code path unchanged.**

```
readiness.py :490  if offers and offers.success:
                       verification = combine_offer_verification(signals)     # NEW, upstream

                       if verification.disposition is VerificationDisposition.GATE:
                           offer_staleness = verification.verification_age_seconds   # THE AXIS OF RECORD
                           # content decision computed and LOGGED as disclosure only

                       elif verification.disposition is VerificationDisposition.REFUSE:
                           offer_staleness = refusal_staleness_seconds(staleness_check)   # :387, sentinel
                           log.error("offer_verification_axis_refused", ...)

                       else:  # DORMANT — producer does not declare the axis
                           log.info("offer_verification_axis_dormant", ...)
                           <<< today's exact block, readiness.py:517-557, UNCHANGED >>>
```

Properties this shape buys:

- **The DORMANT arm is byte-identical to today.** The verification leg cannot
  make anything worse than the current state; at worst it is inert.
- **`readiness.py:334-344` whole-source dormancy is UNTOUCHED.** The A5 refusal
  premise is structurally honored: this PR does not change which constituent
  routes what. Critic C-7 satisfied by non-action, provable by diff.
- **`combine_offer_axis` is not modified.** `content_age_seconds` keeps its exact
  current meaning permanently (NON-ALIASING clause 3).

### §7.2 The combination — whole-source semantics, mirroring the existing rule

`combine_offer_verification` over the two constituent records:

| Condition | Result |
|---|---|
| ANY constituent `REFUSE` | `REFUSE` (naming the refusing constituents) |
| ANY constituent `DORMANT` | `DORMANT` for the whole source (mirrors `readiness.py:334-344`'s whole-source rule — a mixed-image state must not half-gate) |
| a constituent reports `GATE` without an age | `REFUSE` — malformed record, mirrors `readiness.py:307-323` |
| all `GATE` | `GATE` with `verification_age_seconds = max(ages)` = `now − min(verified_at)` over both pools = **the billable grain** (§4.2) |

Refusal ordering: refusals are evaluated **before** dormancy, exactly as
`combine_offer_axis` does (`:307-344`) — a refusal must not be swallowed by a
sibling's dormancy.

### §7.3 F-GUARD

Future-dated verification (negative age) reuses the content axis's existing
guard shape: within `offer_axis_future_skew_allowance_seconds` → clamp and log
`offer_verification_axis_clamped`; beyond it → `REFUSE`. Rationale is unchanged
from `readiness.py:325-332`: *"a negative age passes every threshold trivially."*
Verification adds a reason of its own — §1.2 MONOTONICITY makes a backward
verification instant impossible under honest operation, so a future-dated stamp
is evidence of a defect, not of skew.

### §7.4 Capability tolerance — and why it is NOT the refused OPT-C

`fetch_offers` already carries operator ruling **R-6 HONEST QUIET TOLERANCE**
(`fetcher.py:444-461`, `pyproject.toml:27-34`): probe the installed SDK surface;
absent → legacy gate + a disclosure log naming version, fallback and impact;
*"Never silently dark, never a refusal, never a build failure."*

V3 adds the same probe for the verification surface. **This must not be confused
with FORK-3's refused OPT-C.** The distinction is sharp and it is the whole
safety story:

| | Refused OPT-C ("tolerant read") | Mandated §1.5b (AXIS-ABSENT) |
|---|---|---|
| Trigger | the axis field is **missing from a response that declares the axis** | the producer **does not declare the axis** (`axes_present`), or the installed SDK has no parse surface |
| Behavior | read something else *while still claiming verification gated* | the axis is not in play; the pre-existing content switch governs, disclosed |
| Verdict | **fallback on the axis — NON-ALIASING forbids it** | **the ruled semantics of an absent axis — the contract mandates it** |

The discriminator is `axes_present`. Without CAP-SIG the two states are
indistinguishable — which is exactly why §1.5b calls the capability signal *"the
precondition, not a detail."* **This is why §5.2 makes `axes_present` a V1
deliverable and not a nice-to-have.**

### §7.5 V3 exit criteria

1. The three floor pins moved (§8.2).
2. `readiness.py:334-344` present verbatim and unchanged; `combine_offer_axis`
   unchanged; the DORMANT arm's block byte-identical to the pre-PR block
   (diff-provable).
3. A test asserting AXIS-ABSENT → the pre-existing gate value, byte-for-byte.
4. A test asserting AXIS-NULL → `refusal_staleness_seconds(...)` = 7201.0, not a
   pass and not `None` (the SDK gate reads `None` as PASS —
   `autom8y_reconciliation/gate.py:48`, the C-NULL hazard).
5. **PRODUCTION-OBSERVABLE:** after merge (ASR merge = deploy), a live tick emits
   the verification axis on a real `trace_id`.
6. **The abort path is NOT edited here** — `orchestrator.py` abort rendering
   (`:248`, `:258`, `_build_readiness_abort_alert`) belongs to SPR-I1 and must
   not be entangled with the gate change.

---

## §8 FORK-3 RULED — the SDK/ASR PR boundary, and UV-P-7 discharged BY NAME

### §8.1 UV-P-7 — **CONFIRMED**, by direct build-config read

> `[UV-P: the deployed ASR Lambda image resolves autom8y-core from CodeArtifact
> rather than from the uv workspace | METHOD: inspect the Lambda build path |
> REASON: inferred at shape time … NOT observed end-to-end. This is UV-P-7 and
> it is RISK-1's premise — the most load-bearing unverified claim in this shape.]`

Discharged at `services/account-status-recon/Dockerfile`, current `origin/main`
`3a066a5a`:

| Line | Verbatim | Consequence |
|---|---|---|
| `:58` | `COPY --link pyproject.toml ./` | the build context is the **service directory**; only the **service** pyproject enters the image |
| `:69` / `:75` | `uv pip compile pyproject.toml \` | resolution is computed from the **service** pyproject alone — no workspace context |
| `:72` / `:84` | `--index-url "$EXTRA_INDEX_URL" \` | with `--extra-index-url https://pypi.org/simple/`; `:62-63` supply CodeArtifact auth for local builds |
| `:99` | `uv pip install --system --no-deps .` | the service package itself, no deps |

And a two-sided check: `grep -cE "COPY .*\.\./|WORKDIR /app|uv sync|uv\.lock"`
over the Dockerfile returns **0**. There is no `uv sync`, no `uv.lock`, no
parent-directory copy. The root `pyproject.toml` — which is where
`[tool.uv.workspace]` (`:42`) and `autom8y-core = { workspace = true }` (`:71`)
live — **is not in the build context and is never read by the image build.**

**VERDICT: UV-P-7 CONFIRMED. The deployed image resolves `autom8y-core` from
CodeArtifact.** And the corollary the shape did not draw: **the root pin cannot
influence the image.**

### §8.2 Three pins, with their actual functions named

| # | Pin | Verbatim @ `3a066a5a` | Governs | Move? |
|---|---|---|---|---|
| P-1 | `services/account-status-recon/pyproject.toml:35` | `"autom8y-core>=4.6.0,<5.0.0",` | **the deployed image** — the only pin `uv pip compile` sees | **YES — load-bearing** |
| P-2 | `pyproject.toml:21` (root) | `"autom8y-core>=3.2.0",` | the declared *"single source of truth for SDK minimums across all members"* (`:16`); dev/CI resolution, where `:71` workspace-source wins anyway | **YES — SSOT hygiene.** Leaving it at `>=3.2.0` while a member needs `>=4.16.x` makes the SSOT a lie for every other member. |
| P-3 | `services/account-status-recon/pyproject.toml:79` | `"autom8y-core[testing]>=4.6.0,<5.0.0",` | the `testing` extra — the environment the service's own tests resolve | **YES.** Unmoved, the test env may resolve a floor the runtime does not require. k1-ib1 scar: prove against the REAL emitter. |

**Correction to the shape (D-3):** moving only P-2 is the false-green. Moving
only P-1 ships a correct image with a stale SSOT and a divergent test env.
**Move all three, in the same PR, for the three distinct reasons above.**

### §8.3 Why a green CI is not evidence the image will resolve the field

Dev and CI resolve the workspace (`root pyproject.toml:71`
`autom8y-core = { workspace = true }`) → **editable, always carrying the new
field regardless of any floor**. The image resolves CodeArtifact against P-1.
**The two never disagree in CI's favor and always can in production's.** This is
the documented false-green class, and it is why PT-02's gate must be *resolution
from the index*, not a green pipeline. The gate is now mechanically justified
rather than asserted.

### §8.4 The ruling

**OPT-B — two PRs: SDK publish first (V2), then floor pins + ASR consumption
(V3).** With three amendments:

1. **OPT-A is refused** on §8.3: a single PR would ship ASR code consuming a
   field the *installed* SDK does not have, because the image resolves the
   published floor and the PR's own CI cannot witness that.
2. **OPT-C is refused** as the shape has it — a tolerant read IS a fallback and
   NON-ALIASING forbids it. §7.4 draws the line between OPT-C and the mandated
   AXIS-ABSENT semantics; nothing in this design crosses it.
3. **The R-6 capability probe is insurance, not a re-ordering license.** It
   makes deploy ORDER non-fatal (any out-of-order state fails to DORMANT, never
   to a wrong answer), but the sprints still run in OPT-B order. Fragmenting V3
   to buy schedule would add a production act; see §12 for the lever and its
   price.

### §8.5 Build-cache scar (both repos)

The asana build cache **skips new files**. V2 adds a new module
(`asana_verification.py`) and V1 adds no new file (all edits are to existing
modules) — so the scar bites V2, not V1. Bump the floor pin / bust the cache and
**verify by resolution**, never by a green build.

---

## §9 The monotonicity ratchet — ASSERTED, not assumed

CONTRACT §1.2: *"**MONOTONICITY (binding …)** A persisted verification instant
MUST NOT move backward."* The dispatch required this be asserted. It was.

| Path | Site | Carry-forward? | Verdict |
|---|---|---|---|
| `mark_section_complete` | `section_persistence.py:205-216` | **YES** — `:207` reads `prior.last_verified_at`, `:215` writes it back | conformant; forward-only |
| `mark_section_in_progress` | `:230-240` | **YES** when the gid exists (`:233-235` mutates status/`in_progress_since` in place); a fresh `SectionInfo` only for an unknown gid | conformant |
| `mark_section_failed` | `:219-228` | **NO** — constructs `SectionInfo(status=FAILED, error=error)`; `last_verified_at` defaults to `None` | **VIOLATION SITE.** A section that had a real stamp loses it on failure. |
| stamp pass | `builders/progressive.py:573` | writes `now`, only past the three gates | conformant |

**Finding.** The carry-forward is forward-only on the two paths the shape and
DIAG cite (`:207`, `:215`) — that half is confirmed. **`mark_section_failed`
does not carry forward, and it is the one path nobody named.** The stamp is then
permanently lost until a real probe re-stamps, because a subsequent
`mark_section_complete` carries forward from the FAILED record, which is `None`.

**Ruling — this is NOT fixed by this initiative, and the design is correct
without fixing it.**

1. Under §5.3, a missing stamp → `verified_at: null` → AXIS-NULL → **REFUSE**.
   A section that just FAILED genuinely is not verified. The wipe produces the
   *correct* gate outcome via the correct mechanism. It is conservative in the
   safe direction.
2. Where it would have been dangerous is under the `written_at` backfill (G-2):
   FAILED wipes the stamp, the next `mark_section_complete` sets
   `written_at=now` (`:211`), and the CLI's backfill would then read ≈0 s —
   **a false-GREEN**. §5.3's `allow_written_at_backfill=False` closes it on the
   wire. The CLI keeps its ruled behavior; the gate does not inherit it.
3. **Carded, not silently accepted.** `mark_section_failed`'s non-carry is a
   real monotonicity-clause defect. It belongs in SPR-R1's roster with a named
   disposition (it is adjacent to R-2/C-9 as a manifest-integrity item, not a
   freshness-axis item). Fixing it here would change the write path this design
   deliberately leaves untouched (`§5.1 S-f`).

`[UV-P: mark_section_failed's stamp wipe has occurred in production for the
offers manifest | METHOD: it has not — all 34 sections read `complete` at the
2026-08-19T14:46:33Z manifest, so no FAILED record is currently observable |
REASON: the code path is proven by read; its production incidence is not, and
this design does not depend on the incidence either way]`

---

## §10 Four-clause receipt grammar, bound to each leg

Critic C-8: gate changes are permitted ONLY under the full four clauses.
Clauses (i)+(ii) alone certify a stuck alarm (the `999999` reductio).

| Clause | Statement | Discharged where | Pre-build evidence in hand |
|---|---|---|---|
| **(i)** changes the measured QUANTITY | `offer_staleness` moves from `now − min(max(last_modified \| pool))` to `now − min(last_verified_at \| requested classification set)`. Different inputs, different write path, different tooth. | SPR-V4, at `readiness.py` disposition level, before/after on the same trace shape | §1.2's two rows: 52 566.7 s vs 1 132.4 s on the same day |
| **(ii)** still RED on a genuinely-halted warmer | No probe ⇒ no stamp (`progressive.py:515-516` skips `PROBE_FAILED`; `:517-520` withholds on unapplied deltas; `:561-572` withholds on hash-only-clean). `min` cannot advance. Age climbs → ABORT. | SPR-V4, **discriminating canary**: a deliberately-broken INPUT the live surface correctly refuses, paired with the real input passing GREEN. **Defect injection into working production code is G-THEATER and is FORBIDDEN.** | the three withhold gates, read at `e3aab8d4` |
| **(iii)** GREEN arm on REAL data | The running 12-tick window IS the receipt. Not a fixture. | SPR-V4 / SPR-Z1 | **§1.2 — already measured on the live manifest: 1 132.4 s, 0.31× the bar** |
| **(iv)** construct validity | There EXISTS an observable state: warm loop healthy + business quiet + quantity GREEN. | SPR-V4, named by `trace_id` and timestamp | **§1.2 IS that state** — stamp advanced 14:46:32Z while the content axis read 52 566.7 s because nobody had edited the quieter pool since 2026-08-12 |

Suggested clause-(ii) canary construction (input-broken, never code-broken):
point the derivation at a **manifest fixture whose in-scope set contains one
section with `last_verified_at=None` and a fresh `written_at`**. The correct
surface emits `verified_at: null, verification_backfill_used: true` → ASR
REFUSES → 7201.0. Two-sided: the same fixture with the stamp present passes
GREEN. That fixture bites on exactly the G-2 defect and on nothing else.

---

## §11 Named traps, tripwires, and risks

| ID | Trap | Why it bites | Guard (BUILD OBLIGATION) |
|---|---|---|---|
| **TRAP-1** | `EntityQueryService` hoisted from per-request to a module singleton | `SectionPersistence._manifest_cache` has **no TTL and no read-path invalidation** (only eviction is inside `delete_manifest_async:1193`). Per-request it is a memo; long-lived it is an unbounded staleness cache — **OPT-2-unbounded, the pre-refused option, arrived at silently.** | A test that asserts a **fresh** `SectionPersistence` (empty `_manifest_cache`) per `query_rows` invocation. Must FAIL if the lifetime changes. This is the "asserted coupling, not a comment" the shape demanded of OPT-3, applied to OPT-7. |
| **TRAP-2** | Reading the shape's SPR-V1 wording *"via the manifest read the engine already performs"* as "hold the manifest across requests" | Same landing point as TRAP-1, arrived at by prose | §5.5: a **sibling per-request call** that hits the per-request memo. Never a hoisted handle, never a module-level cache. |
| **TRAP-3** | The grain defect is **numerically invisible in production today** | All 34 stamps carry the identical instant (`progressive.py:494` takes one `now` for the whole pass). `min` over any subset is the same number. A wrong grain would look right until a partial warm failure — the worst kind of latent defect | §5.6 item 6: a grain test with **divergent** stamps per pool. Production observation cannot substitute. |
| **TRAP-4** | Adding a field to `RowsMeta` but not `AggregateMeta` | Both are `extra="forbid"` and share the `_get_freshness_meta` spread — a field on one and not the other **raises** (CONTRACT §1.5, and the `stale_served` mirror comment at `query/models.py:249-252`) | §5.2: declare on BOTH; populate only on rows. |
| **TRAP-5** | Emitting the verification fields **through** `_get_freshness_meta` | `_get_freshness_meta` (`engine.py:517-542`) has no manifest access and is shared with the aggregate path; routing through it would either force a manifest read into the aggregate path or emit nulls that look like AXIS-NULL | §5.1 S-d: explicit kwargs at the `RowsMeta(...)` construction, not the spread. |
| **TRAP-6** | Treating an absent field as AXIS-NULL | Under `extra="ignore"`, an old producer image and "I cannot derive it" both parse to `None`. Refusing on `None` alone would refuse **every** readiness check for the whole cutover horizon | `axes_present` is the discriminator and is a V1 deliverable (§5.2, §7.4). |
| **RISK-1** | A manifest-read failure now aborts the report (§5.3) | Trades a permanent RED for an intermittent RED | Distinct log event + a metric on manifest-read-failure at the derivation site, so the rate is observable **before** anyone debates a fallback. **No fallback.** |
| **RISK-2** | R-5's 1000-row T-GUARD cliff | Unrelated to this axis but still live on the content axis. The §6.1 separation ensures the cure does not inherit it. It remains a real latent-HIGH on the retained disclosure axis | SPR-R1. Named here only so the separation's motive is on the record. |
| **RISK-3** | R-2 `population_degraded` persisted hourly | A correct freshness signal over a below-floor frame is still a wrong answer | SPR-R1, HIGH. **This design does not fix it and must not be read as fixing it.** |

---

## §12 Schedule honesty (deadline tightened to 2026-08-28)

The shape's walk landed 2026-08-31 → 09-01 against a 09-02 deadline, i.e. 1-2
days of slack. **Against 2026-08-28 that walk has ~3-4 days of NEGATIVE slack.**
Stating it rather than absorbing it, per the dispatch.

Three findings in this TDD reduce the work without touching a receipt:

- **OPT-7 makes V1 small.** No new I/O, no new cache, no new failure mode; the
  grain comes from a variable already in scope at the read site.
- **V2 is bounded**: one new module (~1 value object + 1 pure function) plus
  three field declarations on a model that already carries the rest of the
  roster and the `declares_axis` helper.
- **Out-of-order deploys are non-fatal** (§7.4), so the publish→resolve→pin
  chain — the shape's named critical segment — is safe to run tight rather than
  padded.

Revised walk: design locked **today** → V1 ∥ V2 build ~2 d → publish + resolve +
V3 + deploy ~1 d → **48 h window (irreducible)** → SPR-V4 receipts ~1 d →
SPR-Z1 ~1 d. That is 2026-08-25 → 2026-08-28, **with zero slack.**

**The schedule tripwire, as a checkable date:** the deploy boundary must be
pinned and the 12-tick clock STARTED **by 2026-08-25T~12:00Z**. Past that, the
48 h window plus receipts plus a three-leg attestation cannot fit before
2026-08-28. If PT-04 has not fired by then, the honest act is to **move the date,
not the receipts.**

**Do not compress:** SPR-VC (the disjoint critique) and PT-02/PT-03 (the
observability gates). Their absence is precisely what produced the predecessor's
REFUSE-ADVISORY and its five-day dark substrate.

**The one available lever, with its price named:** split V3 into V3a
(capability-probing consumption, inert, no pin move — landable in parallel with
V1/V2) and V3b (three pin moves, after PT-02). This removes V3 from the
serialized segment entirely. **Price: one additional production act.** Not
recommended as the plan; recorded so it can be taken deliberately if PT-02 slips,
rather than invented under pressure.

---

## §13 What this TDD does NOT claim

1. It does **not** claim the cure is realized. Landed < deployed < REALIZED.
   Nothing here is a shipped-class claim.
2. It does **not** claim the 12-tick window will pass. §1.2 shows the axis reads
   1 132.4 s **at one instant**; it does not prove the warm loop's cadence holds
   for 48 h. That is what the window is for.
3. It does **not** fix R-2, R-5, C-9, R-1's frozen-lane defect, or
   `mark_section_failed`'s stamp wipe. Each is named and routed to SPR-R1.
4. It does **not** touch the abort rendering, the interim posture, or any
   threshold. `offer_staleness_threshold_seconds` stays 3600.
5. It does **not** self-grade above MODERATE, and it is not a disjoint
   attestation of anything. SPR-VC is the disjoint attester; SPR-Z1 is reserved
   and unspent.
6. Its **pool-level** claims stay pool-level (C-3). No section-level attribution
   appears anywhere in §1.2, and none may be inferred from it.

---

## §14 SVR / UV-P register

```yaml
structural_verification_receipt:
  claim: "the asana serve path already performs an S3 manifest read on every rows query and discards the object, which falsifies OPT-1's cost objection and makes OPT-7 available at zero added I/O"
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/query/engine.py | sed -n '248p;254p;588p'  (autom8y-asana @ e3aab8d4)"
    command_output_verbatim: "        # 12.5 Derive honest_contract_complete from SectionPersistence manifest.\n        honest_contract_complete = await self._derive_honest_contract_complete(\n            manifest = await section_persistence.get_manifest_async("
    exit_code: 0
    claim: "the manifest object is fetched inside execute_rows for a single boolean and then released; the verification stamp is already inside an object the hot path holds"
```

```yaml
structural_verification_receipt:
  claim: "the serve-path manifest read is genuinely fresh per request: EntityQueryService is constructed inside the request handler, so SectionPersistence._manifest_cache cannot outlive a request"
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/api/routes/query.py | sed -n '468p'  +  git show origin/main:src/autom8_asana/dataframes/storage.py | sed -n '1426p'  (autom8y-asana @ e3aab8d4)"
    command_output_verbatim: "    query_service = EntityQueryService()\n        return await self._get_object(key)"
    exit_code: 0
    claim: "construction at :468 sits inside `async def query_rows` (:334, decorated @router.post at :321), and load_json delegates straight to an uncached S3 GET, so each request pays exactly one manifest GET and holds no cross-request state"
```

```yaml
structural_verification_receipt:
  claim: "UV-P-7 CONFIRMED and the root floor pin cannot influence the deployed image: the ASR Lambda build context carries only the service pyproject and resolves from CodeArtifact, with no uv workspace, no uv.lock, and no parent-directory copy"
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:services/account-status-recon/Dockerfile | grep -nE '^COPY --link pyproject|uv pip compile pyproject|--index-url' ; and | grep -cE 'COPY .*\\.\\./|WORKDIR /app|uv sync|uv\\.lock'   (autom8y @ 3a066a5a)"
    command_output_verbatim: "58:COPY --link pyproject.toml ./\n69:      uv pip compile pyproject.toml \\\n72:        --index-url \"$EXTRA_INDEX_URL\" \\\n75:      uv pip compile pyproject.toml \\\n0"
    exit_code: 0
    claim: "the trailing 0 is the count of workspace/lockfile/parent-copy constructs in the image build; their absence is what makes services/account-status-recon/pyproject.toml the sole image-governing pin and demotes the root constraint block to SSOT hygiene"
```

```yaml
structural_verification_receipt:
  claim: "the verification axis would PASS on live production data at design time, at a grain-independent 1132.4s against a 3600s bar, while the content axis read 52566.7s on the same day"
  verification_method: bash-probe
  verification_anchor:
    source: "aws s3 cp s3://autom8-s3/dataframes/1143843662099250/offer/manifest.json - | python3 (pool-level fold, tzinfo=timezone.utc)  @ 2026-08-19T15:05:24Z"
    command_output_verbatim: "--- POOL active: 22 sections in manifest ---\n  sections WITHOUT last_verified_at: 0\n  min(last_verified_at) = 2026-08-19T14:46:32.232624+00:00  -> verification_age_seconds = 1132.4\n--- POOL activating: 5 sections in manifest ---\n  sections WITHOUT last_verified_at: 0\n  min(last_verified_at) = 2026-08-19T14:46:32.232624+00:00  -> verification_age_seconds = 1132.4"
    exit_code: 0
    claim: "clause (iii) GREEN-arm achievability and clause (iv) construct validity are both evidenced pre-build on production substrate; the strict no-backfill emission rule is satisfiable today because zero in-scope sections lack a real stamp"
```

```yaml
structural_verification_receipt:
  claim: "the ASR floor pin is at services/account-status-recon/pyproject.toml:35, not :26, and a third autom8y-core pin exists at :79 that neither the shape nor the dispatch names"
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:services/account-status-recon/pyproject.toml | grep -n autom8y-core   (autom8y @ 3a066a5a; identical at the shape's own pin d9b9c92c)"
    command_output_verbatim: "35:    \"autom8y-core>=4.6.0,<5.0.0\",\n79:    \"autom8y-core[testing]>=4.6.0,<5.0.0\","
    exit_code: 0
    claim: "line 26 falls inside the R-6 rationale comment block; a limb sent to edit :26 would edit a comment, and a limb told there are two pins would leave the testing extra resolving a different floor than the runtime"
```

```yaml
structural_verification_receipt:
  claim: "the verification stamp is wiped, not carried forward, on the section-failure path — a monotonicity-clause violation site that neither the shape nor the DIAG names"
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/dataframes/section_persistence.py | sed -n '219,228p'  (autom8y-asana @ e3aab8d4)"
    command_output_verbatim: "    def mark_section_failed(\n        self,\n        section_gid: str,\n        error: str,\n    ) -> None:\n        \"\"\"Mark a section as failed.\"\"\"\n        self.sections[section_gid] = SectionInfo(\n            status=SectionStatus.FAILED,\n            error=error,\n        )"
    exit_code: 0
    claim: "mark_section_complete carries last_verified_at forward from prior (:207, :215) and mark_section_in_progress mutates in place (:233-235), but this constructor passes only status and error, so the field falls to its None default and a real stamp is lost on failure — and is not recovered by the next completion, which carries forward from the wiped record"
```

```yaml
structural_verification_receipt:
  claim: "written_at is a write clock and is named verbatim in the contract's forbidden-source list, so compute_verification_age's Decision-6 backfill is contract-conformant for the CLI and contract-violating for the wire axis"
  verification_method: docs-cite-verbatim
  verification_anchor:
    source: ".ledge/decisions/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md (autom8y-asana), fence §1.2 [A-2026-08-12] NON-ALIASING clause 1"
    line_range: "L357"
    marker_token: "No emitter may populate either from a build clock, a"
    claim: "the serve-path derivation must pass allow_written_at_backfill=False and emit a null axis with the backfill flag set, rather than substituting the mutation-recency stamp the metrics CLI is ruled to substitute"
```

**Open UV-P carried out of SPR-V0** (RULE-1: consumed in-initiative by a
subsequent artifact's receipt; RULE-2: survivors ride the HANDOFF DEFER tag):

1. `[UV-P: the §Q3.1 seam table named in the SPR-V0 dispatch | METHOD: operator or main-thread produces the out-of-band artifact | REASON: not resolvable as a file at either origin/main; §5.1 is derived first-hand instead — diff the two before PT-01]`
2. `[UV-P: asana satellite auto-deploys ~13min post-merge | METHOD: observe the pipeline at the SPR-V1 merge | REASON: inherited UNDISCHARGED from two predecessor waves; no WS-A merge has ever occurred]`
3. `[UV-P: mark_section_failed's stamp wipe has ever fired on the offers manifest | METHOD: it has not at 2026-08-19T14:46:33Z (34/34 complete) | REASON: the code path is proven by read; production incidence is not, and this design is correct either way]`
4. `[UV-P: EXT-DEP-1 (#1644) and EXT-DEP-2 (#1643) merged between shape time and design time | METHOD: git log d9b9c92c..origin/main — 927571fd "feat(asr): deadman to named-actor wiring (SPR-D1) (#1644)" and 3a066a5a "feat(asana): AL-5 re-home to PROV MaxStalenessAgeSeconds (SPR-D2) (#1643)" | REASON: RESOLVED-BY-PROBE, recorded because the shape carries both as OPEN drafts and #1643 as DIRTY. Neither touches ASR source. The L6 alarm lane the DIAG wanted landed first has LANDED.]`

---

## §15 Rulings summary (the PT-01 checklist)

| Item | Ruling |
|---|---|
| **FORK-1** | **OPT-7** — reuse the manifest the serve path already fetches, via a per-request sibling derivation. Full 7-option slate at §3.2. OPT-2 refused (pre-refused, re-refused on evidence). **OPT-6 REFUSED — it does not clear the same-trace conjunct.** OPT-1 subsumed; its cost objection falsified. |
| **FORK-3** | **OPT-B** — SDK publish first, then pins + ASR consumption. OPT-A refused on §8.3; OPT-C refused on NON-ALIASING. |
| **UV-P-7** | **CONFIRMED** — CodeArtifact, not the workspace. Discharged by Dockerfile read; corollary: the root pin cannot govern the image. |
| **Floor pins** | **THREE**, not two: service `:35` (load-bearing), root `:21` (SSOT), service `:79` testing extra. `:26` is a comment line. |
| **R-1** | `metrics/freshness.py` OWNS the derivation. `builders/freshness.py` is the prober (upstream, not a derivation). `substrate/freshness.py` folds a contract-distinct quantity that NON-ALIASING clause 4 forbids collapsing. **No fourth derivation:** one private fold, two policy-parameterized callers in one file. |
| **Grain** | The **request-resolved classification set** (`engine.py:124`). NOT `active_sections()`, and NOT `billable_sections()` — the latter violates frozen §1.4 CO-SOURCING. The billable grain is reconstituted by ASR's `max(ages)`. |
| **Backfill** | `allow_written_at_backfill=False` on the wire. Missing stamp → `verified_at: null` + `verification_backfill_used: true` → AXIS-NULL → REFUSE. |
| **R-O3** | **DISCHARGED** — wire name `verification_backfill_used`; in-object name `backfill_used`. Inscription rides the SPR-V1 PR body + the §1.2 clause-5 amendment. |
| **SDK shape** | **Separate** `ResponseVerification` + `derive_response_verification` in a new module. `ResponseFreshness` and `derive_response_freshness` UNMODIFIED. Grounded in R-5's cliff and the zero-rows REFUSE, not in doctrine alone. |
| **Fourth disposition path** | A NEW three-valued switch UPSTREAM of the existing one, whose DORMANT arm delegates to today's block unchanged. NOT a fourth member of `FreshnessDisposition`. |
| **`axes_present`** | **A V1 DELIVERABLE.** Without CAP-SIG, AXIS-ABSENT and AXIS-NULL are indistinguishable and the ASR refusal becomes a deploy-order accident. |
| **Monotonicity** | Asserted. Forward-only on `mark_section_complete`/`_in_progress`; **`mark_section_failed` wipes**. Design is correct without fixing it (missing stamp → REFUSE); carded to SPR-R1. |
| **Schedule** | 2026-08-28 is reachable with **zero slack**. Tripwire: PT-04 must fire by **2026-08-25T~12:00Z**. Move the date, not the receipts. |

---

## §16 Reconciliation with the concurrent acceptance seat

SPR-V0 seats two agents. The requirements-analyst authored
`autom8y-asana/.ledge/specs/SPEC-verification-axis-acceptance-2026-08-19.md`
(`authored_at_utc: 2026-08-19T14:54:36Z`), concurrently and without access to
this artifact. Reconciled here because **PT-01 must not receive two artifacts
that disagree about an acceptance predicate.**

### §16.1 Independent concurrence — and its grade ceiling

Three findings were reached by both seats independently:

| Finding | Acceptance spec | This TDD |
|---|---|---|
| ASR floor pin is at `:35`; `:26` is comment prose | S-CORR-1, AD-3 | D-2, §8.2 |
| A **third** pin exists at `:79` (`autom8y-core[testing]`), unnamed in the shape | S-CORR-2, AD-3 | D-2, §8.2 P-3 |
| The `written_at` backfill must be refused on the gating path | AD-6, AR-14 | §2.3 G-2, §5.3 |

**This concurrence does NOT lift anything above MODERATE.** ADVISORY §C.5 is
binding: *disjoint methods are not disjoint attesters*, and same-rite
convergence caps at MODERATE. Both seats are 10x-dev, dispatched from the same
session root, consuming the same five artifacts of record. The convergence is
worth recording — it makes an inherited-premise error less likely — and it is
**not** external corroboration. **SPR-VC remains the disjoint attester.**

### §16.2 One divergence — R-V1-3, and its resolution

The acceptance spec's **R-V1-3** predicate reads:

> *"The in-scope set derives from the request's classification via
> `billable_sections()` (`activity.py:92-94`, `ACTIVE + ACTIVATING`), **not**
> `active_sections()`."*

That sentence contains two requirements that §4 shows are **not the same
requirement**, and the second falsifies the first on a single-classification
request:

- *"derives from the request's classification"* — **CORRECT**, and it is what
  this design implements (`query/engine.py:124`).
- *"via `billable_sections()`"* — **REFUSED.** `billable_sections()` is a fixed
  union that ignores the request. On ASR's `classification="active"` call it
  would fold over 5 sections absent from that response's bytes, violating
  **frozen** CONTRACT §1.4 CO-SOURCING.

**Resolution (architect's call, per the acceptance spec's own boundary — "this
spec states what a ruling must be able to PROVE, never which ruling to make"):**
R-V1-3's predicate is amended to its first clause alone —

> *The in-scope set is the request's resolved classification section set
> (`query/engine.py:124` `classification_sections`). `billable_sections()` is NOT
> called; `active_sections()` is NOT called on the serve path. Asserted at POOL
> level only (C-3).*

The billable grain §1.2 requires is still proven — at the ASR combination
(§4.2), where it is the correct locus, not at the producer where it breaks
co-sourcing.

**Note for the acceptance seat:** the amended predicate is *strictly harder* to
pass, and it exposes FG-V1-2's own blind spot. Because all 34 live stamps
currently carry an identical instant (§1.4), `billable`, `active∪activating`,
and `all-34` all yield the same number in production. A pool-level assertion
against live data **cannot discriminate** the grain today. The discriminating
check must be the divergent-stamp fixture (§5.6 item 6 / TRAP-3), not a live
observation.

### §16.3 AD-6's dependency edge is NOT created

AD-6 offers two arms: refuse the backfill on the gating path, **or** land
SPR-R1's L7 fix before the 12-tick window — the latter creating a
`SPR-R1 → PT-04` edge the shape does not carry. **This design takes the first
arm** (§5.3, `allow_written_at_backfill=False`). The edge is not created, and
SPR-R1 stays off the critical path. With zero schedule slack (§12) that is not a
cosmetic preference.

### §16.4 A live instance of the frame's §9 scar-2

Probed at design time, `2026-08-19T~15:06Z`:

| | |
|---|---|
| `autom8y` working tree | branch `fix/wss-wildcard-scope-bypass-closure` @ `7ddbd46c` |
| `readiness.py` in that tree | **129 lines** |
| `readiness.py` at `origin/main` (`3a066a5a`) | **574 lines** |
| `git diff origin/main -- …/readiness.py` | 18 insertions, **463 deletions** |

This is the exact stale tree that produced the predecessor frame's retracted
§4.4 (critic C-6). **It is stale right now, in the session root this wave
dispatches from.** Every code claim in this TDD was read via
`git show origin/main:{path}`; none came from a working tree.

**Binding on SPR-V1/V2/V3:** branch from `origin/main`, never from this tree,
and re-read before citing. A citation that resolves line-exact against this tree
is not evidence the tree is current — here it is positive evidence of the
opposite.
