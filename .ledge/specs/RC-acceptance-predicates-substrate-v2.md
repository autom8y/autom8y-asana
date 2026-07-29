---
type: spec
artifact_type: acceptance-predicates
artifact_id: RC-acceptance-predicates-substrate-v2
title: "RC-A..F Testable Acceptance Predicates — Substrate-v2 Epoch"
created_at: "2026-07-28T00:00:00Z"
author: requirements-analyst
complexity: PLATFORM
status: proposed
schema_version: "1.0"
consumes:
  - .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
  - .ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md
feeds:
  - phase-3-reconciliation (architect TDD conformance)
  - PT-01 cutover gate (qa-adversary adversarial fixture replay + live-parity window)
# --- Impact Assessment (routes workflow) ---
impact: high
impact_categories: [data_model, api_contract, cross_service]
# data_model     — v2 storage key schema, plane layout, freshness model (RC-A/RC-B/RC-C/RC-D)
# api_contract   — MCP query_rows/query_aggregate consumer contract; CLI/service consumers (RC-C/RC-E)
# cross_service  — warmer Lambda topology, plane-divergence alarms, fleet-wide entity-typed metrics (RC-E/RC-F)
success_criteria:
  - id: SC-A
    description: "RC-A (single source of truth): every predicate RC-A-1..4 passes — no two disagreeing row-copies for a (project, entity) can be silently served; divergence is detected AND explained."
    testable: true
    priority: must-have
    verification: "See §RC-A predicate table; adversarial fixture replay at PT-01."
  - id: SC-B
    description: "RC-B (content-derived freshness): every predicate RC-B-1..4 passes — a GID-set-preserving content edit is DIRTY-or-refused, never silently CLEAN-and-stamped; write-time metadata (mtime/bulk-stamp) is never treated as proof of freshness."
    testable: true
    priority: must-have
    verification: "See §RC-B predicate table; null-watermark and mtime-fresh/content-stale fixtures."
  - id: SC-C
    description: "RC-C (plane-correctness by construction): every predicate RC-C-1..3 passes — a plane-blind read/write is a compile/type error on EVERY enumerated consumer path, not a runtime lint; the guarantee is construction-level, not an enumerated call-site inventory."
    testable: true
    priority: must-have
    verification: "See §RC-C predicate table + Consumer-Path Inventory; type-check + per-path serve tests."
  - id: SC-D
    description: "RC-D (migration forcing function): every predicate RC-D-1..3 passes — a transitional/bridge surface carries a machine-enforced sunset that fails loud past expiry; no immortal dual-plane state."
    testable: true
    priority: must-have
    verification: "See §RC-D predicate table; expiry-past-due CI fixture."
  - id: SC-E
    description: "RC-E (atomic + side-effect-explicit + rate-safe rebuild): every predicate RC-E-1..4 passes — a partial/failed build cannot corrupt prod; a read-typed path is provably side-effect-free (DEFECT :76 becomes a passing test); rebuild is paced/budgeted."
    testable: true
    priority: must-have
    verification: "See §RC-E predicate table; mid-build-kill + read-path-zero-writes fixtures."
  - id: SC-F
    description: "RC-F (two-sided observability): every predicate RC-F-1..4 passes — an alarm FIRES on unprovability and does NOT fire on a provable number; provability signal is emitted independent of query traffic; dead-man watches a proven-live metric."
    testable: true
    priority: must-have
    verification: "See §RC-F predicate table; two-sided (broken/healthy) alarm fixtures."
related_adrs:
  - ADR-seam1-entity-identity-key
  - ADR-006-freshness-equals-verification-recency
---

# RC-A..F Testable Acceptance Predicates — Substrate-v2 Epoch

> The acceptance surface for substrate-v2. The charter (`CHARTER-substrate-v2-epoch-2026-07-27.md`)
> declares six broken invariants (RC-A..F) and requires that v2 render each one
> **impossible-by-construction OR fail-loud** (charter :36-38, :116). This document
> renders each invariant as a set of **falsifiable acceptance predicates**: a concrete
> input/state paired with the exact pass-or-loud-refuse the system must exhibit.
>
> A predicate is *satisfied* only when the falsifying input produces the stated
> behavior. If the falsifying input can produce a silent wrong-serve, the predicate
> is FALSIFIED and v2 is not done.

## Scope and discipline boundary

**This document specifies OBSERVABLES, not mechanisms.** The charter expressly
delegates the design space to `/architect` (charter :128-135): canonical artifact
shape, freshness model (hash vs watermark vs hybrid), storage layout & key schema,
atomic rebuild mechanism, consumer contracts, observability design. These predicates
are **mechanism-agnostic** by construction — each states what must be OBSERVABLE at
the acceptance boundary, never how the substrate achieves it. The architect's TDD
is checked FOR conformance against these predicates in Phase-3 reconciliation; the
predicates do not pre-answer any open design question.

**Predicates are CHARTER-DERIVED, not design-derived.** They are produced in parallel
with the architecture and do not wait on it (RC-A..F are fixed by the charter and the
DEFECT). Where a predicate names a current v1 primitive (e.g. `storage.py` key-builder,
`from_s3_resolved`), it does so only to anchor the *class* of failure the predicate must
catch — v2 may realize the observable through an entirely different surface.

**Guarantee mode.** Each predicate declares its target mode, honoring charter P3
(prevention by construction beats guards, charter :58-62):

- **BY-CONSTRUCTION** — the failing state is unconstructable (a compile/type error).
  Preferred wherever construction can reach (charter P3).
- **FAIL-LOUD** — the failing state is constructable but is detected and refused
  loudly at runtime (charter P2: refuse > wrong, :54-56).
- **BOTH** — construction-level prevention with a fail-loud backstop (defense in depth
  at exactly the two high-rigor loci: the cutover gate and one-way doors, charter P7 :83-84).

## Two acceptance modes, one posture

The charter's north star (charter :41-46): *a number served is a number the system can
prove; a number it cannot prove is refused loudly.* Every predicate below is an instance
of this posture. "Loud refuse" means a distinct, non-zero, operator-visible failure
(e.g. a `DATA-INTEGRITY` non-zero exit on the CLI, an HTTP 5xx/409 with a machine-readable
reason on the service, an alarm transition) — **never** a WARNING beside a `0` exit, and
**never** a confidence-labelled stale number (charter Non-goals :125).

---

## Parity Exemplar (the first fixture) — the `$84,385`-vs-`$79,585` divergence

The DEFECT's headline scenario (DEFECT :16, :22, :64-72) is the canonical fixture that
RC-A, RC-B, and RC-F must each catch. It is reproduced here as a single seeded state so
QA can build one fixture that exercises three invariants:

**Seeded state** (from DEFECT :20-23, :64-71, verified directly against S3, project
`1143843662099250`):

- v2/offer plane frozen at 2026-07-13, consolidating to `active_mrr = $79,585`.
- A fresher reality (obtained by a full live re-warm at 15:27 UTC): `active_mrr = $84,385`
  (64 dedup combos, 4,179 rows) — a **`+$4,800` / +6%** divergence.
- The divergence is a **coherent composition shift, not noise**: `ACTIVE` `-$4,000`
  (51r/`$65,585` -> 48r/`$61,585`), `OPTIMIZE-Human-Review` `+$4,800` (2r/`$3,100` -> 5r/`$7,900`),
  `STAGED` `+$4,000` (5r/`$6,000` -> 7r/`$10,000`).
- The stale plane carried a false-fresh signal: `verification age: 1m` while
  `newest parquet = 2026-07-13` (14 days old), and `--strict` still exited 0 (DEFECT :16).

**The three catches this fixture must produce in v2:**

| Invariant | What must happen on this fixture | Predicate |
|-----------|----------------------------------|-----------|
| RC-A | The two materializations (`$79,585` vs `$84,385`) are recognized as copies of the same (project, entity); their disagreement is DETECTED and REFUSED, with an **explanation** rendered (which plane, absolute age, magnitude, per-section composition delta) — never a silent serve of either. | RC-A-2 |
| RC-B | The underlying content change (offers moving section + value growth) is derived from CONTENT, not from the fresh mtime of a re-consolidated artifact; the frozen plane reads STALE/unprovable. | RC-B-1, RC-B-2 |
| RC-F | While the substrate is in this divergent/stale state, an alarm FIRES (independent of whether anyone queried it), and it would NOT have fired on the coherent post-warm state. | RC-F-1, RC-F-3 |

"Explained" is a charter requirement, not a nicety: the cutover gate admits the flip only
when *every divergence is explained before the flip* (charter P5 :69-73). RC-A-2's refusal
payload IS that explanation.

---

## RC-A — Single source of truth per (project, entity)

**Broken invariant** (charter :29): no single source of truth — 4 row-copies, 3 writers,
2+ readers, nothing asserts agreement ("double-write cache location"). Compounded by a
SECOND split (DEFECT :74): the consolidated `offer/dataframe.parquet` write path and the
per-section `offer/sections/*` read path are cross-wired — a successful full warm does not
refresh what the reader reads.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-A-1** | For a given (project, entity) there is exactly ONE canonical artifact a consumer resolves to. | Two distinct artifacts exist that any consumer could read as the answer for the same (project, entity) — e.g. a per-section layout AND a consolidated layout both readable and both claiming to answer `active_mrr`. | v2 exposes ONE read target per (project, entity); a second readable copy is either unconstructable, or the read resolves deterministically to the single canonical artifact. Two live disagreeing read targets = FALSIFIED. | BOTH |
| **RC-A-2** | Two materializations of the same (project, entity) that DISAGREE on a served number are detected and refused, with the divergence explained. | Seed the Parity Exemplar: v2 plane summing to `$79,585` (14d stale) and a fresher reality of `$84,385`. | Loud refuse (`DATA-INTEGRITY`-class) carrying the explanation: which copy, absolute age of each, magnitude (`+$4,800`/+6%), per-section composition delta. Serving either number silently = FALSIFIED. | FAIL-LOUD |
| **RC-A-3** | Writer target and reader target are the SAME artifact: a successful full rebuild refreshes exactly what the consumer reads. | The DEFECT :74 layout split — a full entity warm rewrites `dataframe.parquet` (+ watermark + index) but leaves per-section `sections/*` and the manifest untouched (`sections_fresh=0/33`, `manifest_present=0`), while the reader reads the per-section layout. | A rebuild-then-read fixture: warm the (project, entity), then read via each consumer — the read MUST reflect the warm's output. A warm that does not move the number the consumer reports = FALSIFIED. | BOTH |
| **RC-A-4** | The set of writers to a (project, entity) canonical artifact is bounded and asserted; no second, unasserted writer can produce a divergent copy. | The DEFECT root cause: an entity-blind prober (Writer B) writes to a legacy plane while the full builder (Writer A) writes v2, and nothing asserts the two agree. | A second writer to the same (project, entity) is either unconstructable (single-writer discipline) or its writes land on the SAME canonical artifact such that divergence is impossible. An independent second writer producing a shadow copy = FALSIFIED. | BY-CONSTRUCTION |

---

## RC-B — Freshness is content-derived, not write-time metadata

**Broken invariant** (charter :30): freshness is write-time metadata (stamps, mtimes),
not content-derived truth. The DEFECT documents three layers of false-fresh (DEFECT :22):
one bulk `last_verified_at` for 34 sections; 20/34 `watermark=NULL` -> hash-only CLEAN ->
stamped anyway; a re-consolidated artifact with fresh mtime over stale content.

**The D8 null-watermark class** (DEFECT :43): a content edit that PRESERVES the section's
GID set is invisible to a GID-set-only check; the content-derived signal that would catch
it (the watermark, in v1) is NULL, so only the GID-set hash runs, and the value edit slips
through as CLEAN — then is stamped `verified`.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-B-1** | A content edit that PRESERVES the GID set is detected. | Take a section; edit a task's content-bearing value (e.g. an offer's MRR `$1,000 -> $1,200`) with NO change to the GID set (same task GIDs, same membership). In v1's null-watermark path this stamps CLEAN. | Verdict is DIRTY (or the derived number is refused as unprovable). A GID-set-preserving value edit that yields silent CLEAN = FALSIFIED. This is the core RC-B predicate. | FAIL-LOUD |
| **RC-B-2** | Write-time metadata (mtime / stamp) is never treated as proof of content freshness. | The DEFECT :22c artifact: a re-consolidation touches `dataframe.parquet` mtime (fresh, today 13:01) over stale content (a re-sum of frozen 07-13 per-section parquets); a freshness check keyed on mtime reads FRESH. | Freshness derives from content -> reads STALE -> refuse. Any path where a fresh mtime alone yields a FRESH/served verdict over 14-day-stale content = FALSIFIED. | FAIL-LOUD |
| **RC-B-3** | N sections cannot share ONE freshness proof unless N genuine per-section verification events occurred. | The DEFECT :22a bulk stamp: 34 sections carry one identical `last_verified_at` (`2026-07-27T13:00:30.232451Z`) written by a single per-warm bulk operation. | Each section's provability stands alone; a single bulk write cannot mark N sections proven. A shared stamp accepted as N verification events = FALSIFIED. | BOTH |
| **RC-B-4** | A section whose content-currency CANNOT be established is reported unprovable (refused), never stamped verified. | The DEFECT :22b / :43 case: content baseline absent (v1: `watermark=NULL`) -> only a membership check is possible -> in v1 stamped `verified` with `last_verified_at=now`. | Cannot-establish-currency surfaces as UNVERIFIED/refused; its verification age climbs off written-at and is never reset to now. Stamping an unestablishable section as verified = FALSIFIED. | FAIL-LOUD |

---

## RC-C — Plane-correctness by construction

**Broken invariant** (charter :31): plane-correctness is per-call-site manual discipline;
the enumerated guard drifted and missed a whole layer. **Root cause** (DEFECT :27): the
freshness prober had zero `entity_type`, so every read/write defaulted to the legacy
entity-agnostic plane. **Why the guard missed it** (DEFECT :37-38): the call-site inventory
enumerated only storage-layer methods; the prober used the persistence-layer wrappers
(`write_section_async`, `read_section_async`, `update_manifest_section_async`), which were
NOT in the inventory — so the entity-blind calls were invisible and the guard passed green.

The construction-level defect, anchored fresh (see Verification Anchors §V-1): every
`storage.py` key-builder takes `entity_type: str | None = None`, and when `None` it emits
the legacy plane. **An optional plane discriminator that defaults to legacy makes
plane-blindness the constructable default.** RC-C requires that this be a compile/type
error instead.

> **CRITICAL — consumer-exhaustive.** RC-C is FALSIFIED if a plane-blind serve/write is
> possible on ANY single consumer path. v1's guard drifted precisely because it was
> per-call-site and missed a layer. The predicate below is checked against the full
> Consumer-Path Inventory; a passing green on a subset is not acceptance.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-C-1** | A read/write/key-build cannot be constructed without a non-optional plane discriminator. | Attempt to construct a storage key, or issue a read/write, omitting the plane/entity discriminator — i.e. any surface with signature shape `entity_type: str \| None = None` that emits a legacy path when omitted. | Compile/type error (type-check failure or unconstructable API) — NOT a runtime lint, NOT a silent default-to-legacy. A call that omits the discriminator and still resolves to a plane = FALSIFIED. | BY-CONSTRUCTION |
| **RC-C-2** | EVERY consumer path resolves through the plane-correct-by-construction primitive; none can serve plane-blind. | For EACH path in the Consumer-Path Inventory below, drive a read/serve and inspect the resolved plane. | Every path resolves to the plane-correct target by construction. A plane-blind serve on ANY one path (offline/CLI, force-warm recheck, MCP `query_rows`, MCP `query_aggregate`, `DataFrameCache`, persistence-wrapper surface) = FALSIFIED. | BY-CONSTRUCTION |
| **RC-C-3** | The guarantee is construction-level, not an enumerated call-site inventory that a new consumer can bypass. | Add a BRAND-NEW consumer function that reads/writes the substrate WITHOUT referencing any existing guard list or inventory (simulating the persistence-wrapper layer that `test_seam1_callsite_inventory.py` missed). | The new consumer cannot compile a plane-blind call (the discriminator is required by the type). A green guard while the new consumer serves plane-blind = FALSIFIED. The guard must not be a maintained list of method names. | BY-CONSTRUCTION |

### Consumer-Path Inventory (the RC-C-2 exhaustive surface)

Every path a served number can flow through today, verified fresh by direct inspection
at authoring time (2026-07-28; anchors in §V). RC-C-2 requires a per-path serve test for
each row. This list is the acceptance surface, NOT a design; v2 may collapse these paths,
but if a path exists it must be plane-correct-by-construction.

| # | Consumer path | Entry point (anchored) | Plane-blind risk today |
|---|---------------|------------------------|------------------------|
| CP-1 | Offline / CLI read | `metrics/__main__.py` -> `offline.load_project_dataframe` (per-section layout) | Reads per-section layout; guarded only by runtime `_guard_plane_divergence` (offline.py:183). |
| CP-2 | Force-warm recheck | `metrics/__main__.py:476` & `:883` -> `FreshnessReport.from_s3_resolved` (metrics/freshness.py:219) | Recompute path; must resolve the SAME plane as CP-1. |
| CP-3 | MCP `query_rows` | `POST /v1/query/{entity_type}/rows` -> `api/routes/query.py:334` -> `resolve_section_index` -> `DataFrameCache` | `entity_type` is a runtime URL param (`str`); downstream storage default `None` -> legacy is constructable. |
| CP-4 | MCP `query_aggregate` | `POST /v1/query/{entity_type}/aggregate` -> `api/routes/query.py:573` | Same as CP-3. |
| CP-5 | Shared `DataFrameCache` | `api/dependencies.py:365` `get_dataframe_cache` / `:513` `DataFrameCacheDep` (app.state, ADR-0067) | The cache both MCP paths resolve through; a plane-blind cache key poisons CP-3/CP-4. |
| CP-6 | Persistence-wrapper surface (the MISSED layer) | `write_section_async` / `read_section_async` / `update_manifest_section_async` (used by the prober, freshness.py:425/:553/:606/:653) | THIS is the layer v1's inventory missed (DEFECT :38). Any writer here defaults to legacy when `entity_type` is omitted. |

---

## RC-D — Migrations have a forcing function; bridges have an enforced sunset

**Broken invariant** (charter :32): migrations defer with no forcing function; "temporary"
bridges are immortal (dual-plane since 2026-06-09, discovered 2026-07-27 — ~7 weeks
immortal). The bridge in flight is `legacy_fallback_enabled` (default `True`, storage.py:352,
anchored §V-3). Charter P11 (:104-112) states enforcement is primarily by construction,
with **CI teeth used sparingly where construction cannot reach — e.g. bridge-sunset expiry**.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-D-1** | Any transitional/bridge/dual-read surface carries a declared sunset date; past it the bridge FAILS, not silently persists. | A bridge flag (e.g. a `legacy_fallback_enabled` successor) exists with no declared expiry, or with an expiry that is not read by any check. | A bridge without an enforced expiry is a construction-time / CI failure. A dual-read surface that can exist with no sunset = FALSIFIED. | BOTH |
| **RC-D-2** | The sunset is machine-enforced (teeth), not a comment or ADR note. | The sunset is documented only in prose/ADR; nothing goes red when the date passes. | A CI check (or build refusal) goes RED once the sunset date is in the past. A past-due bridge that leaves CI green = FALSIFIED. | FAIL-LOUD |
| **RC-D-3** | The dual-plane state has a terminal deletion and cannot outlive its window; post-cutover the legacy plane is DELETED, not disabled. | The 2026-06-09 -> 2026-07-27 immortality: two planes both live, indefinitely, with the bridge flag defaulting to on. | Post-cutover, legacy planes/bridges/flags are DELETED (charter P12 :114-119); continued existence of a superseded plane past cutover is a detectable violation. A disabled-but-present legacy plane after cutover = FALSIFIED. | BOTH |

> Note: RC-D-3 is the temporal complement of RC-A. RC-A forbids two disagreeing copies at
> any instant; RC-D-3 forbids the transitional dual-state from becoming permanent. The
> v1-deletion event itself (charter one-way door #1, :139) is operator-gated (P9 :94-96);
> RC-D-3 asserts the *detectability* of a surviving legacy plane, not that the agent deletes it.

---

## RC-E — Rebuild is atomic + side-effect-explicit + rate-safe

**Broken invariant** (charter :33): no atomic, side-effect-explicit, rate-safe rebuild
primitive — building mutates prod; partial = corrupt; rebuilds 429-storm. The DEFECT :76
counterexample is load-bearing and MUST become a passing test: a local `strategy._build_dataframe`
run *intended as read-only* partially rewrote prod `offer/sections/*`, because the
progressive builder persists sections mid-fetch — so that path is NOT side-effect-free.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-E-1** | A partial/failed build cannot corrupt prod: prod only ever transitions last-good -> next-good atomically. | Kill the rebuild mid-flight (e.g. after section 15 of 34). | Prod canonical artifact is UNCHANGED (still last-good), or the new build was staged and never swapped in. A mid-build failure that leaves prod in a mixed-vintage/partial state = FALSIFIED. | BOTH |
| **RC-E-2** | A read-typed path is provably side-effect-free: invoking it against prod produces ZERO prod writes. | The DEFECT :76 counterexample: invoke the read/recompute path a consumer (or an ad-hoc validation) would call, against prod, and count S3 PUTs. | Observed prod mutation count = 0. Any read/recompute path that writes prod (as `strategy._build_dataframe` did, persisting sections mid-fetch) = FALSIFIED. **This exact counterexample must become a passing test.** | FAIL-LOUD |
| **RC-E-3** | Write capability is explicit: a path typed/named as read or compute cannot silently persist. | A helper named/typed as a build/read (e.g. `_build_dataframe`) writes prod as a side effect, with no explicit write-capability in its signature. | Read/compute-typed paths are unconstructable-with-writes (write requires an explicit capability token/param). A read-typed path that can persist = FALSIFIED. | BY-CONSTRUCTION |
| **RC-E-4** | A full rebuild is rate-safe: it routes through paced primitives and respects the API budget. | Trigger a full rebuild that issues unpaced concurrent fetches (the 2026-07-27 ad-hoc 429-storm, charter :99-102). | Rebuild routes through paced primitives (AIMD / 429-banking, bounded concurrency, per-day budget, off-peak for heavy pulls) and leaves a receipt (charter P10 :98-102). An unpaced burst / 429-storm from a rebuild = FALSIFIED. | FAIL-LOUD |

> RC-E-2 (behavioral: zero writes observed) and RC-E-3 (constructional: read-typed cannot
> write) are complementary — the behavioral test is the fixture, the construction guarantee
> is what makes the fixture pass by design rather than by vigilance (charter P3).

---

## RC-F — Observability cannot read green while broken (two-sided)

**Broken invariant** (charter :34): observability can read green while broken — query-gated
alarms, dead-man on a dead metric. The DEFECT names two mechanisms (DEFECT :57): the
staleness alarm (AL-5) *only emits on query*, so absolute plane age is invisible when no
one queries; and an orphaned dead-man (`autom8-asana-cache-warmer-DMS-24h`) watches a
retired warmer — a dead-man on a dead metric can never fire. Charter P2 (:54-57): **alarms
assert provability, not liveness.**

The **two-sided** requirement is explicit: an alarm FIRES on unprovability AND does NOT fire
on a provable number. A one-sided alarm (fires always, or never) carries no information.

| Predicate | Observable condition | Falsifying input / state | Pass vs loud-refuse expectation | Mode |
|-----------|----------------------|--------------------------|----------------------------------|------|
| **RC-F-1** | Fires on unprovability (true-positive side). | Put the substrate in an unprovable state: 14-day-stale plane, or plane divergence (Parity Exemplar), or a refused number. | The alarm FIRES. A stale/divergent/refused substrate with a silent alarm (the DEFECT headline: 14-day-stale served under "verified 1m ago", no alarm) = FALSIFIED. | FAIL-LOUD |
| **RC-F-2** | Does NOT fire on a provable number (false-positive side / two-sidedness). | Put the substrate in a healthy, provable state: fresh, single-source, plane-correct (the coherent post-warm `$84,385`). | The alarm does NOT fire. An alarm that fires on a healthy state (noise that trains operators to ignore it) = FALSIFIED. RC-F-1 and RC-F-2 together = two-sided discrimination. | FAIL-LOUD |
| **RC-F-3** | The provability signal is emitted independent of query traffic. | No consumer queries the (project, entity) for 14 days (the AL-5 query-gating, DEFECT :57): the alarm's input metric is only produced on query, so absence-of-query looks identical to health. | Absolute provability/age is emitted on a heartbeat/schedule independent of query traffic; a plane going stale with zero queries still fires. A signal that only exists when queried = FALSIFIED. | BOTH |
| **RC-F-4** | The dead-man watches a proven-live metric, and fires when that metric goes absent. | The orphaned `DMS-24h` case (DEFECT :57): the dead-man is keyed on a metric from a retired/renamed source, so the metric is permanently absent and the dead-man is inert. | The watched metric is confirmed to be the live one, AND the dead-man fires when it goes absent. A dead-man whose watched metric is orphaned (can never fire) = FALSIFIED. | BOTH |

---

## How QA consumes these at PT-01 (cutover gate)

The cutover gate (charter P5 :69-73) is the single validation event: full adversarial
fixture replay PLUS a time-boxed live-parity window. These predicates are the fixture
catalogue:

1. **Adversarial fixture replay** — each RC-*-N falsifying input becomes a discriminating
   test. A test PASSES when the falsifying input produces the stated loud-refuse or is
   unconstructable; it FAILS (RED) when the input can produce a silent wrong-serve. Per the
   discriminating-canary posture, the no-defect variant of each fixture must also pass GREEN
   (two-sided teeth) — most sharply for RC-F (F-1 fires / F-2 silent) and RC-A-2 (divergent
   refuses / coherent serves).
2. **Live-parity window** — v2 computes the real numbers beside v1 against live prod; **every
   divergence is explained before the flip** (charter :71). RC-A-2's refusal payload is the
   explanation format; the Parity Exemplar is the worked example.
3. **Rate-safety of the parity window itself** — all prod touches during the window route
   through paced primitives (RC-E-4 / charter P10); ad-hoc unpaced pulls are banned, agents
   included (charter :101-102).

**Acceptance is consumer-exhaustive and two-sided.** A predicate is not accepted on a
subset of consumer paths (RC-C-2) nor on the true-positive side alone (RC-F). Green on a
subset is the exact drift that produced the wound.

## Out of scope (explicitly)

- **Mechanism selection** — freshness model, key schema, artifact shape, rebuild mechanism,
  observability design (charter :128-135). Owned by `/architect`; these predicates constrain
  the acceptance surface, not the design.
- **The v1-deletion action** — operator-gated one-way door (charter :139, P9). RC-D-3 asserts
  *detectability* of a surviving legacy plane, not the deletion act.
- **Cross-repo terraform applies** (warmer topology, alarm provisioning) — operator-gated
  one-way door (charter :142); RC-F predicates specify alarm BEHAVIOR, not its provisioning.
- **Fleet-wide reconstruction** (Stream 2) — begins from extracted doctrine post-Asana
  (charter P1 :50-52); these predicates are the Asana proving-ground acceptance surface.

## Open questions

None blocking. These predicates are charter-derived and fixed. Two items are flagged for
Phase-3 reconciliation with the architect (they do not gate this artifact):

- **OQ-1** — The refusal-payload SCHEMA for RC-A-2 ("explained divergence") is an acceptance
  observable here (which plane / age / magnitude / per-section delta) but its wire format
  (CLI text, HTTP body, structured log) tracks the architect's consumer-contract decision.
  Reconcile the observable list against the chosen contract; do not narrow the observable.
- **OQ-2** — RC-C-1's "compile/type error" presumes a type-checked construction surface
  (mypy-gated). If the architect selects a construction surface where the discriminator
  cannot be made a static type error, RC-C degrades to FAIL-LOUD for that surface and the
  degradation must be disclosed (it weakens charter P3 for that path).

---

## Verification Anchors (SVR) — platform-behavior claims, receipted

Per structural-verification-receipt discipline, the platform-behavior claims this document
makes about named primitives (file paths, signatures, entry points — SVR trigger rows 1/3/4)
are verified by direct inspection at authoring time (2026-07-28). These anchor the
Consumer-Path Inventory and the RC-C root-cause claim; they are the substrate for the RC-C-2
exhaustiveness assertion. Re-runnable probes:

- **V-1 (RC-C root: constructable plane-blindness).** `storage.py` key-builders take
  `entity_type: str | None = None`; `None` emits the legacy plane. Probe:
  `rg -n "entity_type: str \| None = None|When \`None\` it emits" src/autom8_asana/dataframes/storage.py`
  -> signatures at lines 91, 117, 128; legacy-emit documented at 395-398; v2 layout at 327-332.
- **V-2 (persistence-wrapper surface — the missed layer).** The prober uses
  `write_section_async` / `read_section_async` / `update_manifest_section_async`. Probe:
  `rg -n "write_section_async|read_section_async|update_manifest_section_async" src/autom8_asana/dataframes/builders/freshness.py`
  -> lines 425, 553, 606, 653. Cross-check: the SEAM-1 call-site inventory test enumerated
  storage-layer methods only (`tests/unit/dataframes/test_seam1_callsite_inventory.py` exists).
- **V-3 (RC-D bridge flag).** `legacy_fallback_enabled: bool = True` default. Probe:
  `rg -n "legacy_fallback_enabled" src/autom8_asana/dataframes/storage.py` -> default at 352,
  dual-read semantics documented at 334/364.
- **V-4 (MCP consumer surface).** `POST /v1/query/{entity_type}/rows` and `/aggregate`. Probe:
  `rg -n "query_rows|query_aggregate|/{entity_type}/rows" src/autom8_asana/api/routes/query.py`
  -> `query_rows` def at 334, `query_aggregate` def at 573, route docstring at 7-8.
- **V-5 (MCP cache resolution).** MCP paths resolve through the shared `DataFrameCache`. Probe:
  `rg -n "get_dataframe_cache|DataFrameCacheDep" src/autom8_asana/api/dependencies.py`
  -> `get_dataframe_cache` at 365, `DataFrameCacheDep` at 513 (app.state, per ADR-0067).
- **V-6 (offline/force-warm recheck).** `from_s3_resolved` is the recompute recheck. Probe:
  `rg -n "from_s3_resolved" src/autom8_asana/metrics/freshness.py src/autom8_asana/metrics/__main__.py`
  -> def at `metrics/freshness.py:219`; called at `metrics/__main__.py:476` and `:883`.
- **V-7 (RC-E-2 side-effect counterexample).** The read-intended path that wrote prod is
  documented in the DEFECT operational note. Anchor: `DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md:76`
  ("a local `strategy._build_dataframe` run (intended as read-only) partially rewrote prod
  `offer/sections/*` ... that path is NOT side-effect-free").

Charter/DEFECT anchors re-read fresh at authoring (no stale line numbers carried forward):
charter RC-table :27-38, P1-P12 :48-119, open questions :128-135, one-way doors :137-142;
DEFECT symptom :16, evidence :20-23, root cause :27-38, compounding :42-44, addendum
divergence :64-72, second split :74, side-effect note :76.

---

## Attestation

| Artifact | Absolute path | Status |
|----------|---------------|--------|
| RC acceptance predicates (this document) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/RC-acceptance-predicates-substrate-v2.md` | authored 2026-07-28, status: review |
| Consumed — charter | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md` | read fresh |
| Consumed — DEFECT | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md` | read fresh |

**Coverage self-check:** 6 invariants (RC-A..F) -> 22 predicates (A:4, B:4, C:3, D:3, E:4,
F:4). Every predicate carries a concrete falsifying input and a pass-vs-loud-refuse
expectation. Consumer-Path Inventory: 6 paths (CP-1..6), each anchored. Parity Exemplar
maps to RC-A-2 / RC-B-1,2 / RC-F-1,3. `prod_touch: NONE` (read-only source inspection only).
Evidence grade for the predicate set: derived directly from ratified charter invariants +
directly-inspected code anchors; self-authored acceptance surface, subject to architect
Phase-3 reconciliation and qa-adversary PT-01 replay (rite-disjoint corroboration).
