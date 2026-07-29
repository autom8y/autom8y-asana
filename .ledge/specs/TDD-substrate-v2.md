---
type: spec
artifact_id: TDD-substrate-v2
title: "Substrate-v2 — whole design from RC-A..F as constructive invariants"
created_at: "2026-07-27T23:21:07Z"
finalized_at: "2026-07-29T08:52:09Z"
author: architect
prd_ref: PRD-substrate-v2-epoch
status: accepted            # PT-01 HARD gate PASS 2026-07-29 (fresh-instance potnia, de novo, receipts per-question)
lifecycle_status: ratified   # corridor-ratified at PT-01; doors DP-2/DP-3 OPERATOR-RATIFIED 2026-07-29 — the design is FULLY ratified
schema_version: "1.0"
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
phase: "FINALIZED (Phase-3 of the S1 three-phase DAG) — adversary PASS-WITH-CONDITIONS + PE BUILDABLE folded; PT-01 flips status to ratified"
seams_frozen: "v1.0-frozen-2026-07-29 (Seams 1-5; the S2-S7 build contract)"
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored corridor design; caps at MODERATE per self-ref-evidence-grade-rule.
  Phase-2 rite-disjoint arch-adversary rendered PASS-WITH-CONDITIONS (no fork reversed)
  and principal-engineer rendered BUILDABLE-AS-DRAWN; both folded here. STRONG is the
  eunomia attestation at epoch exit (S12).
prd_note: >
  No standalone PRD artifact exists. The requirements source is the CHARTER
  (RC-A..F acceptance invariants + P1-P12) + frame + shape, rendered into 22 testable
  predicates at RC-acceptance-predicates-substrate-v2.md. prd_ref is a logical handle
  satisfying the schema; the RC invariants + predicates ARE the acceptance criteria.
components:
  - name: substrate.identity
    type: module
    description: "Typed ArtifactId(project_gid, entity_type) value object; entity_type REQUIRED, non-defaultable; __post_init__ rejects non-servable members (registry-derived). Pure core. RC-C substrate."
    dependencies: []
  - name: substrate.freshness
    type: module
    description: "FreshnessProof (built_from_live_at=MIN over section fetch-instants, content_digest, sla_seconds) + is_provable + canonical_digest. The sole freshness law. Pure core. RC-B."
    dependencies: []
  - name: substrate.serve
    type: module
    description: "SubstrateReader choke-point + ServedNumber (Provable|Refused); the single public read path; freshness gate bound per-read; no result-caching above the gate. RC-C(serving) / P2."
    dependencies:
      - name: substrate.identity
        type: internal
      - name: substrate.freshness
        type: internal
      - name: substrate.store
        type: internal
  - name: substrate.store
    type: module
    description: "Versioned immutable artifact store + atomic current-pointer (CAS via If-Match; collision-free version-IDs); single-source; policy-free; read_current raises ArtifactMissing. Infra (S3). RC-A / RC-E storage half."
    dependencies:
      - name: substrate.identity
        type: internal
      - name: substrate.freshness
        type: internal
  - name: substrate.rebuild
    type: module
    description: "Stage-validate-swap rebuilder; paced live fetch; per-section provenance MIN-fold; produces a new version + FreshnessProof; atomic swap LAST. Infra (Asana + store). RC-E."
    dependencies:
      - name: substrate.store
        type: internal
      - name: substrate.freshness
        type: internal
      - name: substrate.identity
        type: internal
  - name: substrate.observe
    type: module
    description: "Query-independent scheduled provability evaluator; two-sided expected-set (registry ∪ store enumeration); completeness + heartbeat. Infra (CloudWatch). RC-F."
    dependencies:
      - name: substrate.store
        type: internal
      - name: substrate.freshness
        type: internal
related_adrs:
  - ADR-substrate-v2-fork-register
  - DP-2-v2-storage-shape
  - DP-3-consumer-contracts
  - DP-1F-v1-live-path-p6-boundary
related_artifacts:
  - CHARTER-substrate-v2-epoch-2026-07-27
  - DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27
  - RC-acceptance-predicates-substrate-v2
  - ADVERSARY-substrate-v2-design-s1
  - FEASIBILITY-substrate-v2-seams-s1
  - ADR-seam1-entity-identity-key
  - ADR-006-freshness-equals-verification-recency
---

# TDD — Substrate-v2 (whole design from RC-A..F as constructive invariants)

> **FINALIZED — Phase-3 of the S1 three-phase DAG.** Phase-2 is in: the rite-disjoint
> **arch-adversary** rendered **PASS-WITH-CONDITIONS** (no fork reversed; 7 MUST-FIX-PHASE-3,
> 4 CARRY-TO-BUILD) and the **principal-engineer** rendered **BUILDABLE-AS-DRAWN** (5 hardened
> seam contracts [H1]-[H23]; no re-enter). This finalize folds every accepted condition into
> the RC constructions and the five FROZEN seams, and adds the §10 disposition ledger and §11
> build-notes. The two operator doors (DP-2: F1+F3 storage-shape; DP-3: F5 consumer contracts)
> ride to the operator as compact packets WITH the adversary dissent verbatim. PT-01 flips
> `status: challenge-passed` → `ratified`.

## 0. What this design is (and the acid test)

Substrate-v2 is **one small store of one thing**: for each `(project, entity)` there is exactly
one addressable artifact, it carries its own proof of freshness, and the only way to read it is
through one gate that returns either a provable number or a loud refusal. Six modules, five frozen
seams, ~one dependency arrow (everything points inward to two pure core types). The mission's
acid test — *"will this look obviously right in 18 months?"* — is answered by subtraction: v2 has
no second layout, no dual-read bridge, no probe-that-stamps-fresh, no per-call-site guard, no
query-gated alarm, no result-cache above the freshness gate. Each of those absences is a broken v1
invariant made **unconstructable**, not guarded.

The design is **whole** (P4): v2 is built dark beside v1 as a coherent unit and lands in one
cutover — there is no strangler half-state, because the transitional half-state (the dual-plane
bridge) is the disease this epoch exists to cure (RC-D).

## 1. Premise ledger (SVR — re-anchored FRESH at HEAD `b9438e83`, discipline #8)

Every platform-behavior claim the design rests on, verified by direct inspection (ADR line anchors
are stale and deliberately not cited; these are fresh reads/greps, cross-confirmed by the PE §0
grounding ledger G1-G13):

| # | Premise | Method | Receipt (fresh) | Status |
|---|---------|--------|-----------------|--------|
| P1 | v1 key-builders admit a plane-blind key: entity segment defaults to None with a live legacy fallback | file-read | `dataframes/storage.py` `_entity_segment(project_gid, entity_type: str \| None)`, `_df_key(..., entity_type: str \| None = None)`; ctor `legacy_fallback_enabled: bool = True` (PE G5) | VERIFIED |
| P2 | v1 freshness derives from a STRUCTURAL proxy, not content; the D8 null-watermark false-CLEAN hole is live | file-read | `builders/freshness.py` `compute_gid_hash`; probe docstring step 5: hash-only CLEAN when watermark is None; GID-set-preserving edits invisible | VERIFIED |
| P3 | freshness is a re-stampable manifest field, not a content-derived value | file-read | `section_persistence.py` `SectionInfo.last_verified_at/watermark/gid_hash`; carried-forward in `mark_section_complete` | VERIFIED |
| P4 | the "read-only" rebuild path writes prod mid-fetch | file-read | `builders/progressive.py` loop dispatches `_fetch_and_persist_section*` → `write_section_async` (persist DURING fetch) | VERIFIED |
| P5 | refuse-loud (PlaneDivergenceError) protects ONLY the CLI path | bash-probe | defined `offline.py:54`, called only `offline.py:168`, caught only `metrics/__main__.py:787`; zero call sites in services/query/api | VERIFIED |
| P6 | the service/MCP query path reads dataframes WITHOUT the guard | file-read | `universal_strategy.py:802` + `matching.py:145` `cache.get_async` → `DataFrameCache` → `storage.load_dataframe`; no guard | VERIFIED |
| P7 | the freshness reader used for the CLI signal is mtime-based and does NOT refuse on divergence | file-read | `metrics/freshness.py from_s3_resolved` → `from_s3_listing` (parquet LastModified); no divergence refusal | VERIFIED |
| P8 | the v1 divergence guard is write-time metadata AND bridge-coupled (goes blind once legacy is gone) | file-read | `offline._guard_plane_divergence` compares mtimes; returns early when no legacy plane → v2 stands unchecked | VERIFIED |
| P9 | the second split (consolidated vs per-section) is a real two-writer/two-layout divergence | file-read | DEFECT addendum: consolidated-warm writes `dataframe.parquet`, `sections_fresh=0/33`, reader reads per-section | VERIFIED |
| P10 | there is NO content-value hash anywhere — only structural GID hashing | bash-probe | `compute_gid_hash` (GIDs) only; no value-column digest in the substrate | VERIFIED |
| P11 | `EntityType` is a real closed Enum with an `UNKNOWN = "unknown"` member; mypy `strict = true` is repo-wide; runtime floor 3.12 | file-read | PE G1 (`core/types.py`), G2 (`pyproject.toml:144`), G3 (`requires-python >=3.12`) | VERIFIED (via PE) |
| P12 | S3 object replacement is atomic at the object level — no torn reads; a failed multipart is never visible; a failed PUT leaves the prior object intact (strong read-after-write) | docs-cite (DOMAIN-PRIOR) | AWS S3 documented strong read-after-write consistency + atomic object-level replacement. **CORRECTS the draft's false "overwrite is non-atomic" premise (adversary AV-4/C4).** | DOMAIN-PRIOR — S2 receipts before DP-2 build locks |

**UV-P (deferred, discharge at build-sprint entry):**

- [UV-P: prod cache-warmer Lambda image carries the #276 entity-aware prober fix | METHOD: deploy-dispatch receipt + ECR digest probe | REASON: downstream deploy state not probed at design time; inherited from frame UV-P-1]
- [UV-P: canonical value-digest column set (offer: mrr/offer_id/cost/weekly_ad_spend) is stable across a warm | METHOD: DuckDB MCP prod probe at S2 entry (premise-validation-discipline) | REASON: [H1] digest domain must be confirmed against prod before locking]
- [UV-P: the incremental-rebuild API budget under per-section-provenance (re-fetch only sections older than SLA−cadence) fits the P10 per-day budget | METHOD: budget model quantified at S2 with real section counts/cadence | REASON: C1's RK1 re-derivation needs live numbers; the mechanism is fixed, the numbers are S2's]
- [UV-P: S3 object-level atomic replacement + strong read-after-write (P12) holds for this bucket | METHOD: SVR bash-probe/docs-cite at S2 before DP-2 build | REASON: adversary marked the S3-atomicity claim DOMAIN-PRIOR; receipt it before the key/schema locks]

Gate A.1 (provenance-root): the origin is internal — the DEFECT report + charter, live-read. No
external origin-signal asserted.

## 2. Module decomposition (6 modules, 5 seams, one inward dependency direction)

The design applies the **Clean Architecture Dependency Rule** [DP:SRC-003] and **DIP**
[DP:SRC-002]: the two pure-core modules (`identity`, `freshness`) depend on nothing; the three
infrastructure modules (`store`, `rebuild`, `observe`) depend INWARD on the core; `serve` is core
policy + thin per-consumer adapters. No core module imports an infrastructure module.

```
                    CORE (pure, no I/O — the policy)
              ┌───────────────────┐   ┌────────────────────┐
              │ substrate.identity│   │ substrate.freshness│
              │  ArtifactId       │   │  FreshnessProof    │
              │  (entity REQUIRED)│   │  is_provable       │
              │  servable guard   │   │  canonical_digest  │
              └─────────▲─────────┘   └─────────▲──────────┘
                        │        ┌──────────────┤
        ┌───────────────┼────────┼──────────────┼───────────────┐
        │ INFRASTRUCTURE│(depends inward on core types only)     │
        │  ┌────────────┴───┐ ┌──┴───────────┐ ┌────────────────┐│
        │  │ substrate.store│ │substrate.    │ │substrate.      ││
        │  │ versioned +    │ │  rebuild     │ │  observe       ││
        │  │ CAS pointer    │ │ stage-val-   │ │ scheduled +    ││
        │  │ (RC-A/RC-E)    │ │ swap (RC-E)  │ │ 2-sided (RC-F) ││
        │  └────────▲───────┘ └──────┬───────┘ └───────┬────────┘│
        └───────────┼────────────────┼─────────────────┼─────────┘
                    │                 writes staging     reads proof
             ┌──────┴───────────────────────────────────┐
             │ substrate.serve  (core policy + adapters) │
             │  SubstrateReader.read -> Provable|Refused │
             │  gate bound per-read; no result-cache     │
             └───────────────────────────────────────────┘
   consumers: CLI · service(query) · MCP/fleet · matching · force-warm
   ALL read through substrate.serve; NONE reach storage.load_dataframe directly (import-tooth, PE [H17]/G13)
```

Placement: `src/autom8_asana/substrate/` (new package, dark beside v1's `dataframes/`). v1 is
untouched and frozen (P6). At cutover consumers repoint to `substrate.serve`; at extinction (S11)
v1's planes/bridges/flags delete to zero.

## 3. The six RC invariants as constructions (impossible-by-construction OR fail-loud)

Each RC is a CONSTRUCTION. Where Python cannot make a thing compile-time impossible, the honest
floor is stated: **deleted capability + mypy-strict CI tooth + construction-time guard** (P11 — CI
teeth sparingly where construction cannot reach). Phase-2 conditions folded inline.

### RC-A — single source of truth per (project, entity)

**Impossible-by-construction.** ONE artifact per `ArtifactId`, ONE writer (the `Rebuilder`), ONE
authority (the versioned pointer). The consolidated-vs-per-section duality (P9) is SUBTRACTED — v2
has a single materialized shape (DP-2). No re-consolidation step; no second writer (the entity-blind
prober and the consolidated-warm both delete with v1). The "4 row-copies / 3 writers / nothing
asserts agreement" state cannot be built — there is no second copy to disagree with.
- **Fail-loud backstop (C3 folded):** the pointer swap is a true CAS (S3 conditional write,
  `If-Match` ETag) and version-IDs are collision-free (UUID/timestamp/digest-addressed), so two
  concurrent rebuilders cannot silently clobber — the loser's swap is rejected, not overwritten. An
  absent pointer/object raises `ArtifactMissing` (PE [H5]) — never a silent `(None, None)`.

### RC-B — freshness is content-derived truth, not write-time metadata

**Impossible-by-construction (D8 class subtracted) + fail-loud (refuse past SLA / on digest
mismatch).** Freshness is a pure function of two artifact fields: `built_from_live_at` and
`content_digest` (over the value-bytes, canonicalized — not GIDs, not parquet bytes; P10). The
`last_verified_at` re-stamp and the watermark/gid-hash probe-to-stamp bridge (P2, P3) are DELETED —
no CLEAN-stamps-fresh path exists, so the null-watermark false-CLEAN class is unconstructable.

**C1 folded (the sharpest Phase-2 finding, AV-1 — closes D8-resurrection in the incremental
rebuild):** an incremental rebuild that reuses cached sections must NOT stamp the whole artifact
`built_from_live_at = now`. Instead:
- **the artifact's `built_from_live_at` = MIN over its constituent sections' last real
  content-fetch instants.** A reused section keeps its old instant; the artifact ages by its
  STALEST section.
- **only a real content fetch (value-bytes pulled from live Asana) advances a section's instant.** A
  cheap structural probe (GID-set / modified_since) may DECIDE whether to re-fetch a section (a
  scheduling optimization) but NEVER advances its instant — a probe cannot freshen. This is v1's
  probe-refreshes-freshness pattern made unconstructable at the section altitude, not just the
  artifact altitude.
- **RK1 budget answer (numbers → S2 UV-P):** the rebuild re-fetches only sections whose age exceeds
  `SLA − warm_cadence` and reuses fresher ones; the artifact refuses once its oldest constituent
  exceeds SLA. Incremental savings are real (skip fresh sections) AND honest (skipped sections keep
  their true age). This is the RK1 mitigation re-derived without a freshness lie.
- **Fail-loud:** serving computes `now − built_from_live_at`; `> SLA` → `Refused(STALE)`. Serving
  re-canonicalizes the parsed frame and re-hashes; `≠ content_digest` → `Refused(CORRUPT)`. (C2
  wording fix: the digest arm re-canonicalizes the PARSED FRAME per [H1], not the parquet bytes.)

### RC-C — plane-correctness by construction (keys that cannot be built plane-blind)

**Impossible-by-construction for the omission wound + fail-loud-at-construction for an explicit
non-servable member (C6/OQ-2 honest disclosure — no silent BY-CONSTRUCTION on a runtime guard).**
`ArtifactId` is a frozen value object whose `entity_type: EntityType` is REQUIRED (no `None`
default; no legacy key-builder to fall through to — contrast P1). Two distinct guarantees, honestly
separated:
- **The wound (entity_type OMITTED → defaults to legacy plane) is BY-CONSTRUCTION prevented:** there
  is no default argument and no `str | None` path; mypy-strict (P11) makes an omitted/mistyped
  discriminator a static type error. A writer with `grep -c entity_type == 0` cannot construct an
  `ArtifactId`. This is the actual DEFECT class, genuinely unconstructable.
- **An explicitly non-servable member (`EntityType.UNKNOWN`, structural PROJECT/SECTION) is
  FAIL-LOUD-at-construction:** `__post_init__` raises at object birth. Per **OQ-2**, this branch is
  disclosed as FAIL-LOUD (runtime `__post_init__`), NOT labeled BY-CONSTRUCTION — mypy is satisfied
  by any enum member. The servable set is **DERIVED from the entity registry** (single source,
  data-driven), NOT a hand-maintained second enum — a subset enum was considered and rejected
  because it re-introduces a drift-prone duality (the RC-A/P3 disease). The str→EntityType coercion
  at HTTP/CLI boundaries (PE G12: `matching.py "business"`, MCP `entity_type: str`) lives in the
  Seam-4 adapters and MUST coerce-or-refuse (unknown string → `Refused`, never silent legacy).
- Serving-side: refuse-loud is a property of the single read choke-point (§Seam 4), not a
  per-call-site guard (P5/P6 prove that drifts).

### RC-D — migrations have a forcing function; no immortal bridges

**Impossible-by-construction (no bridge exists) + fail-loud (any temporary bridge self-expires).**
v2 has NO dual-read fallback: `legacy_fallback_enabled` (P1) does not exist in `substrate/`. The
migration is the CUTOVER EVENT (S8 gate → cutover → S11 extinction), a scheduled sprint with an
operator door (DP-1), not a lever left open. Any bounded bridge (e.g. the parity harness reading
both planes) lives ONLY in the S7 harness (test scope, deleted with it) and carries a `SUNSET_AFTER`
date that fails CI past expiry.
- **C11 (CARRY-TO-BUILD, §11):** `SUNSET_AFTER` extensions require an operator-visible ruling — a
  serial date-bump is itself the immortal bridge re-entering with receipts.

### RC-E — atomic, side-effect-explicit, rate-safe rebuild

**Impossible-by-construction (staging-only writes + capability-typed reader) + fail-loud (partial
build leaves live untouched).** The `Rebuilder` writes ONLY to a staging version, validates it, then
performs ONE atomic pointer swap (LAST — PE [H10]). Reads go through `SubstrateReader`, whose type
has NO write method — a "read-only recompute" cannot persist (P4 becomes a passing test:
`RC-E-2`/`RC-E-3`). Rate-safety: every live Asana fetch routes the S4 paced primitive (PE G6 — it
exists; the rebuilder delegates, never re-implements). Single-flight per `ArtifactId` via the
existing coalescer (PE G7).
- **Fail-loud:** a partial/failed build leaves the live pointer unmoved and discards staging —
  partial ≠ corrupt. Side effects are EXPLICIT: staged version + one pointer swap, nothing in-place.
- **C9 (CARRY-TO-BUILD, §11):** gate `swap_pointer` on a `ValidationReceipt` minted only by
  `AcceptancePredicates.validate()` (construction-enforces validate-before-swap), OR lock the
  ordering with a discriminating swap-before-validate test if the capability change is declined.

### RC-F — observability that cannot read green while broken

**Impossible-by-construction (query-independent, shared predicate, two-sided expected-set,
absence=alarm) + fail-loud (self-heartbeat + completeness).** A scheduled evaluator (independent of
serve AND warm) reads each artifact's freshness proof via the SAME `is_provable` predicate serving
uses (PE [H19]) and emits `provable=1/0`.
- **C7 folded (AV-6 — the DMS-orphan class one level up):** the evaluator's expected-set is
  **two-sided: registry (catches should-exist-but-missing) ∪ store enumeration under
  `dataframes-v2/` (catches exists-but-unregistered)**; a member of either set absent from the other
  fires. This closes the "built-and-served but unregistered → evaluator never expects it → green
  while it rots" construction. Extends PE [H20]'s completeness metric (`evaluated_count <
  len(expected)` fires).
- Fires on `provable=0`, on ABSENCE (`ArtifactMissing` → `provable=0`, never silence), on
  incompleteness, and via its run-count heartbeat when the evaluator itself stops. v1's query-gated
  AL-5 and the DMS-24h dead-man-on-a-dead-metric are subtracted.
- **Division of labor (adversary advisory, folded):** the evaluator asserts DATA provability; a
  serve-path defect (adapter bug → 5xx on provable data) is caught by a distinct receiver
  refusal/health SLI (Seam-4 emission). BOTH together are "cannot read green while broken"; neither
  is retired believing the other covers it.
- **C10 (CARRY-TO-BUILD, §11):** the cutover gate's evidence must include ONE observed end-to-end
  fired alarm (synthetic unprovability → operator-visible notification) — closes the alarm-action
  void (SNS-gap precedent on record).

### RC scoreboard (post-Phase-2)

| RC | Mode | One-line construction (conditions folded) |
|----|------|-------------------------------------------|
| RC-A | impossible-by-construction + CAS backstop | one ArtifactId → one artifact → one CAS pointer; collision-free version-IDs; ArtifactMissing on absence (C3, [H5]) |
| RC-B | construction + fail-loud | freshness = MIN-over-section-fetch-instants + value-digest; probe cannot freshen; refuse past SLA / on mismatch (C1, C2) |
| RC-C | construction (omission) + fail-loud-at-construction (member) | entity_type required + registry-derived servable guard; omission unconstructable, explicit-UNKNOWN raises (C6/OQ-2) |
| RC-D | construction + CI sunset (+ operator ruling on extension) | no dual-read bridge; harness bridges fail CI past SUNSET_AFTER (C11) |
| RC-E | construction + fail-loud | staging-only writes; reader has no write method; validate-then-swap-LAST; partial ≠ corrupt (C9) |
| RC-F | construction + fail-loud | scheduled evaluator on the shared predicate; two-sided expected-set; absence + incompleteness + heartbeat fire (C7, C10) |

## 4. The five FROZEN seams (v1.0-frozen-2026-07-29 — the S2-S7 build contract)

**FROZEN.** These interfaces are the build contract; the vocabulary is fixed and five independent
builders converge on them. A DP ruling changes a SHAPE (the physical version layout, the wire
status class), NOT a seam. Contracts below are the architect's drawn signatures HARDENED with the
PE's [H1]-[H23] deltas and the adversary's C1-C7. Internal implementation is emergent within them.

### Seam 1 — FRESHNESS (`substrate.freshness`, pure core) — RC-B — FROZEN v1.0

```python
@dataclass(frozen=True, slots=True)
class FreshnessProof:
    built_from_live_at: datetime   # tz-aware UTC; = MIN over constituent sections' last REAL content-fetch instants (C1)
    content_digest: str            # sha256 hex over canonical_digest() form — never GIDs, never parquet bytes
    sla_seconds: int               # freshness contract for this (project, entity) class; sourced from the entity registry

class Provability(Enum):           # CLOSED — shared verbatim with Seam 5; no builder adds a member
    PROVABLE = "provable"; STALE = "stale"; CORRUPT = "corrupt"

def is_provable(proof: FreshnessProof, served_frame_digest: str, now: datetime) -> Provability:
    """PROVABLE iff (now - built_from_live_at) <= sla_seconds AND served_frame_digest == content_digest.
    Else STALE (age) or CORRUPT (digest mismatch). Pure; deterministic in its 3 args; no I/O, no now()."""

def canonical_digest(frame) -> str:  # [H1] the ONE digest function; every producer/consumer calls it
    ...
```
- **[H1] digest canonicalization FROZEN here (closes RK2/C2 — top divergence risk):** pin all five —
  (a) column set = registry-declared value-columns (UV-P confirms offer set at S2); (b) row order =
  ascending sort on declared `row_key`; (c) serialization = parquet-INDEPENDENT canonical encoding
  (UTF-8 JSON of sorted-key records), explicitly NOT `write_parquet()` bytes; (d) null = one pinned
  sentinel; (e) float = one pinned fixed-precision format. Same-bytes-twice reproducibility test at S2.
- **[H2] tz invariant:** `__post_init__` rejects naive `built_from_live_at`; `is_provable` rejects
  naive `now`. Monotonic decay holds only in UTC.
- **[H3]/C1** `is_provable` is the SOLE freshness definition — no parallel staleness check anywhere.
  `built_from_live_at` is a MIN-fold; **no probe advances it — only a content fetch does** (C1).
- **Frozen invariant:** only a content-bearing rebuild constructs a new `FreshnessProof`; a section's
  fetch-instant advances only on a real content fetch; `is_provable` is consumed identically by
  serving (Seam 4) and observability (Seam 5).

### Seam 2 — STORAGE+KEYS (`substrate.identity` + `substrate.store`) — RC-A/RC-E — FROZEN v1.0

```python
@dataclass(frozen=True, slots=True)
class ArtifactId:
    project_gid: str
    entity_type: EntityType         # REQUIRED — no default, no None
    def __post_init__(self) -> None:                      # [H4] guard content FROZEN
        if not self.project_gid: raise ValueError("empty project_gid")
        if not is_servable(self.entity_type):             # servable set DERIVED from the entity registry (C6 — no drift enum)
            raise ValueError(f"non-servable entity_type: {self.entity_type}")

def artifact_key(aid: ArtifactId) -> str:  # pure; the ONLY key-builder; no None branch, no legacy segment
    return f"dataframes-v2/{aid.project_gid}/{aid.entity_type.value}"

class ArtifactStore(Protocol):
    async def read_current(self, aid: ArtifactId) -> tuple[bytes, FreshnessProof]: ...   # [H5] raises ArtifactMissing on absence — NEVER (None, None)
    async def stage_version(self, aid: ArtifactId, frame_bytes: bytes, proof: FreshnessProof) -> VersionId: ...  # never touches the pointer; collision-free VersionId (C3)
    async def swap_pointer(self, aid: ArtifactId, to: VersionId, *, if_match: ETag) -> None: ...  # [H6]/C3 true CAS (If-Match); sole, atomic, monotonic mutation
    async def list_versions(self, aid: ArtifactId) -> list[VersionId]: ...
    async def gc_versions(self, aid: ArtifactId, keep_after: datetime) -> int: ...       # never deletes current/current-1; age > SLA+grace only
```
- **[H4]/C6** guard is registry-derived (single source, no drift); the non-servable set ⊇ `{UNKNOWN}`.
- **[H5] `read_current` HARD v1 break:** resolves pointer → named immutable version in ONE logical
  read and returns `(bytes, proof)`, or **raises `ArtifactMissing`** (contrast v1 `(None, None)`).
- **[H6]/C3** `swap_pointer` is the ONLY writer of the pointer, a **true CAS** (`If-Match` ETag — not
  read-check-PUT), monotonic (reject a swap to a version older than current unless via an explicit
  rollback capability). **VersionId is collision-free** (UUID/timestamp/digest-addressed — not
  `max+1`; digest-addressing also makes identical rebuilds idempotent).
- **[H7]** `stage_version` NEVER touches the pointer and never overwrites a pointed-to version.
- **[H8] the store is POLICY-FREE** — returns bytes+proof, does not apply the SLA/refuse gate (that
  is Seam 4; preserves the rebuilder + parity-harness raw-read need). This is the F5-3 rejection made
  structural.
- **Frozen invariant:** `entity_type` required + registry-servable; exactly one key-builder, no
  legacy path; `stage_version` never mutates the pointer; `swap_pointer` is the sole atomic monotonic
  CAS mutation; reads resolve current → named immutable version or raise.

> **DP-2 (operator door #2):** the PHYSICAL version layout (app-level `v{N}/` + pointer vs S3-native
> versioning vs single-object + proof-in-metadata) is the operator's ruling. The seam is
> layout-stable: `stage_version`/`swap_pointer`/`read_current` semantics hold under any ratified
> shape. See DP-2-v2-storage-shape.md.

### Seam 3 — REBUILD (`substrate.rebuild`, infra) — RC-E — FROZEN v1.0

```python
class RebuildOutcome(Enum):  # CLOSED
    SWAPPED = "swapped"; STAGED_REJECTED = "staged_rejected"; FETCH_REFUSED = "fetch_refused"

class Rebuilder(Protocol):
    async def rebuild(self, aid: ArtifactId, fetch: PacedAsanaFetcher, validate: AcceptancePredicates) -> RebuildResult:
        """ORDERED, swap LAST:
        1. read prior version's per-section provenance (each section's last real content-fetch instant).
        2. for each section: a cheap structural probe MAY decide re-fetch; a section older than (SLA - cadence) MUST re-fetch.
           a re-fetch pulls value-bytes from LIVE Asana (paced) and advances THAT section's instant to now. reused sections keep their instant. (C1)
        3. materialize the WHOLE version; content_digest = canonical_digest(frame); built_from_live_at = MIN over section instants. (C1)
        4. store.stage_version(...)  — staging only, never the pointer.
        5. validate(staged) — population floor + digest self-consistency + proof well-formedness ([H13]).
        6. on PASS: store.swap_pointer(aid, staged, if_match=...)  — the single atomic CAS swap.  on FAIL: discard staging, live untouched."""
```
- **[H9] capability separation is THE frozen invariant:** `Rebuilder` and `SubstrateReader` are
  DISTINCT types; `Rebuilder` exposes no serve-read, `SubstrateReader` exposes no write; never the
  same object. P4/RC-E-2 becomes a passing test — the serve capability has no `put`.
- **[H10] swap LAST + conditional:** validate on STAGED bytes; swap ONLY on PASS; on FAIL discard,
  pointer untouched. Never swap-then-validate (C9 hardens this at build).
- **[H11] paced-fetch delegation MANDATORY:** all live Asana I/O routes the injected
  `PacedAsanaFetcher` (PE G6); no direct `AsanaClient`, no un-paced path (RC-E-4).
- **[H12] single-flight per ArtifactId** via the existing coalescer (PE G7; RK7).
- **C1 per-section provenance is a REBUILD-seam obligation:** the rebuild maintains per-section
  last-content-fetch instants, MIN-folds them into the artifact proof, and never advances an instant
  without a real content fetch. This is the D8-resurrection closure and rides into the S2/S4 build.
- **Frozen invariant:** writes are staging-only until one atomic monotonic CAS swap after validation;
  all live fetches route the paced primitive; a section's fetch-instant advances only on a real
  content fetch; a failed rebuild cannot corrupt the live artifact.

### Seam 4 — SERVING (`substrate.serve`, core policy + thin adapters) — RC-C(serve)/P2 — FROZEN v1.0

```python
@dataclass(frozen=True, slots=True)
class Provable:  frame: bytes; proof: FreshnessProof
@dataclass(frozen=True, slots=True)
class Refused:   reason: RefuseReason; detail: RefusePayload   # RefuseReason CLOSED: {STALE, CORRUPT, MISSING, DIVERGENT}

type ServedNumber = Provable | Refused      # PEP 695 alias — valid on 3.12 (PE G3)

class SubstrateReader(Protocol):
    async def read(self, aid: ArtifactId) -> ServedNumber: ...
    # postcondition: store.read_current -> is_provable(proof, canonical_digest(parsed frame), now) -> Provable | Refused; NEVER a bare value
```
- **[H14]/OQ-1 sum-member payloads FROZEN** so CLI/HTTP/MCP adapters serialize identical fields.
  `RefuseReason` CLOSED {STALE, CORRUPT, MISSING, DIVERGENT}. `RefusePayload` carries the RC-A-2
  explanation observable (OQ-1, **do NOT narrow**): which copy/plane, absolute age of each, divergence
  magnitude, per-section composition delta. The wire FORMAT is DP-3; the FIELDS are the seam.
- **[H15] exhaustiveness tooth (net-new pattern):** every `ServedNumber` consumer matches both arms
  with `typing.assert_never`; a bare attribute access is a mypy error. Zero `assert_never` uses exist
  today (PE grep) — the contract mandates it as the RC-C-serving honest floor.
- **[H16]/C2 the gate lives INSIDE `read`, bound per-read:** `read` resolves `store.read_current`,
  computes `canonical_digest` of the PARSED FRAME (not parquet bytes), applies `is_provable`, returns
  `Refused` on failure — never `Provable` for an unprovable number. **C2 freeze: the age arm executes
  on EVERY logical read; the digest arm binds at bytes-ingress from store; caching of
  `ServedNumber`/`Provable` results above the gate is FORBIDDEN — only proof-validated bytes may be
  tiered.** (The memory→S3 tier caches BYTES that pass the gate, never a `Provable` result.)
- **[H17] raw-read privacy enforceable + bounded (PE G13):** `store.read_current`/`load_dataframe`
  are module-private to `substrate.{serve,rebuild}`; an import-layer mypy/lint tooth forbids importing
  them elsewhere. Today's raw `load_dataframe` importers are all v1 write/warm/preload (delete at S11),
  none are consumer serve paths. Rebuilder + parity harness reach raw bytes via a DISTINCT non-serving
  capability.
- **[H18] adapters are THIN:** CLI, service route, MCP route, matching, force-warm translate
  `ServedNumber` to their surface and contain NO freshness logic (§Consumer map below).
- **Frozen invariant:** exactly one public read path; it returns `Provable | Refused`; a bare value is
  unobtainable without handling `Refused`; the gate binds per-read with no result-cache above it; raw
  bytes reachable only by rebuilder + parity harness via a distinct non-serving capability.

> **DP-3 (operator door #3):** the cross-process WIRE contract (STALE→status class, refusal-body
> schema, the mandated-client-SDK question, and the explicit supersession of
> ADR-serve-stale-within-bound) is the operator's ruling. The seam is wire-stable: the `Refused`
> FIELDS and the "no `Refused` is a 200" invariant hold under any ratified status class. See
> DP-3-consumer-contracts.md.

Consumer map (all forced through the choke-point; PE §4d): CP-1 offline/CLI → non-zero
`DATA-INTEGRITY` exit; CP-2 force-warm recheck → `is_provable` not mtime; CP-3/4 MCP
rows/aggregate → str→EntityType coerce-or-refuse + `Refused`→non-2xx; CP-5 shared `DataFrameCache` →
key derived from `ArtifactId`; CP-6 persistence-wrapper surface → subtracted with v1; matching →
`ArtifactId(gid, EntityType.BUSINESS)`.

### Seam 5 — OBSERVABILITY (`substrate.observe`, infra) — RC-F — FROZEN v1.0

```python
class ProvabilityEvaluator(Protocol):
    async def evaluate_all(self, now: datetime) -> EvaluationRun: ...
    # expected-set = registry-warm-targets ∪ store-enumeration(dataframes-v2/)  (C7 two-sided)
    # per-aid: read_current + is_provable -> emit provable=1/0; ArtifactMissing -> provable=0 (never silence)
    # run-level: emit heartbeat(run_count) AND evaluated_count; evaluated_count < len(expected) FIRES; either-set-only member FIRES
```
- **[H19] shared-predicate invariant:** calls the SAME `is_provable` + `Provability` (Seam-1) that
  Seam-4 serving calls — the mechanical basis of "cannot read green while serving refuses."
- **[H20]+C7 completeness ≠ heartbeat, expected-set two-sided:** heartbeat proves the evaluator RAN;
  completeness proves it COVERED every artifact. Expected-set = **registry warm-targets ∪ store
  enumeration under `dataframes-v2/`** (C7); a member present in one set and absent from the other
  FIRES (closes AV-6 unregistered-but-served rot). `evaluated_count < len(expected)` fires.
- **[H21] absence = alarm:** `ArtifactMissing` → `provable=0`, never silence.
- **[H22] query-independence:** scheduled (EventBridge→Lambda / warmer post-step); NEVER called from
  `read`.
- **[H23] emission reuses `cloudwatch_emit` EMF/`put_metric_data`** (PE G8). The terraform
  alarm-provisioning limb is the EXISTING Door #4 — out of this seam's CODE scope.
- **Frozen invariant:** provability is evaluated on a schedule independent of serve and warm; it
  consumes the identical `is_provable`; absence fires; incompleteness (two-sided) fires; the
  evaluator's own silence fires (heartbeat + CloudWatch native no-data).

### Seam dependency legality (Dependency Rule check)

`freshness` + `identity` import nothing from the substrate. `store`, `rebuild`, `serve`, `observe`
import the two core types; the core imports none of them. No outward (core → infra) edge — a
violation is a mypy import-layer error (the sparing CI tooth). DIP direction: infrastructure
satisfies ports the core defines.

## 5. Fork rulings (final states — full slates in the companion ADR + packets)

| Fork | Final state | Ruling | Routing |
|------|-------------|--------|---------|
| **F1+F3** | **STAGED-FOR-OPERATOR** | versioned-immutable + atomic CAS pointer (draft C), on CORRECTED S3 premise; A-prime/C-prime/E added | **DP-2** (Door #2) |
| **F2** | **RATIFIED-AUTO** (challenge passed; C1 folded) | content-digest + MIN-over-section build-from-live age; probe cannot freshen; no re-stamp | auto |
| **F4** | **RATIFIED-AUTO** (challenge passed; C3/C9 folded) | stage-validate-swap; capability-typed reader; CAS swap; collision-free version-IDs | auto |
| **F5** | **STAGED-FOR-OPERATOR** | one typed choke-point → `Provable\|Refused`; F5-5 SDK added; status-class + supersession to operator | **DP-3** (Door #3) |
| **F6** | **RATIFIED-AUTO** (challenge passed; C7/C10 folded) | scheduled evaluator; two-sided expected-set; completeness + heartbeat | auto; terraform = Door #4 |

The rulings COMPOSE: F1/F3's pointer carries F2's proof; F4's swap IS that pointer-flip; F5's
choke-point reads it through F2's law; F6's evaluator reads the SAME proof F5 reads. Seams (§4), not
shapes, are frozen — a door ruling changes a shape and the composition re-derives.

## 6. Data model (the artifact and its proof)

```
dataframes-v2/{project_gid}/{entity_type}/    # key: artifact_key(ArtifactId) — entity_type REQUIRED, servable
  <current pointer>       # names the live immutable version + carries the FreshnessProof (built_from_live_at=MIN, content_digest, sla_seconds); atomic CAS swap target
  <version N>            # immutable materialized frame + per-section provenance (each section's last content-fetch instant, for C1 MIN-fold)
  <version N-1>          # retained for rollback until GC (older than SLA+grace; never current/current-1)
```
(Physical realization of `<current pointer>` and `<version N>` = DP-2 operator ruling.)

| Model | Type | Fields | Constraint |
|-------|------|--------|-----------|
| `ArtifactId` | value_object | project_gid, entity_type | entity_type REQUIRED + registry-servable (RC-C) |
| `FreshnessProof` | value_object | built_from_live_at (=MIN), content_digest, sla_seconds | advanced only by content-fetch; probe cannot freshen (RC-B/C1) |
| per-section provenance | value_object | {section_gid: last_content_fetch_at} | rebuild-internal; MIN-folds into the proof (C1) |
| `ServedNumber` | value_object (sum) | Provable(frame, proof) \| Refused(reason, payload) | bare value unobtainable without handling Refused; RefusePayload = OQ-1 observable (RC-C serving) |

## 7. Risks + adversarial resolution (post-Phase-2)

| # | Risk | Sev | Resolution |
|---|------|-----|-----------|
| RK1 | Whole-frame-per-version rebuild blows the P10 API budget | HIGH | **Resolved via C1:** per-section provenance — re-fetch only sections older than SLA−cadence, reuse fresher; artifact ages by its stalest section. Budget numbers quantified at S2 (UV-P). Shape (F1/F3) stays orthogonal to fetch. |
| RK2 | `content_digest` non-reproducible across serialization | HIGH | **Resolved via [H1]:** canonicalization frozen in `substrate.freshness`; parquet-independent encoding; same-bytes-twice test at S2. |
| AV-1 | Incremental rebuild resurrects D8 (stamps reused sections live-fresh) | **was BLOCK-class** | **Resolved via C1:** a probe cannot advance a section's fetch-instant; only a content fetch does; artifact `built_from_live_at`=MIN. This was the sharpest Phase-2 finding; Seam 3 does NOT freeze without it (coordinator HARD). |
| AV-2 | Result-cache above the gate re-creates false-fresh from memory | **was MUST-FIX** | **Resolved via C2:** age arm per-read; digest at ingress; caching `Provable`/`ServedNumber` above the gate FORBIDDEN. |
| RK5 | Cross-process MCP consumer can ignore `Refused` bytes | HIGH (door) | **DP-3:** `Refused`→non-2xx (PE G9) + consumer raises on every non-200 (PE G10); shape-hostile bodies (C5); F5-5 mandated SDK enumerated. Operator rules the status class. |
| AV-6 | Evaluator expected-set drift (unregistered-but-served rots green) | MUST-FIX | **Resolved via C7:** two-sided expected-set (registry ∪ store enumeration). |
| RK4/RK7 | GC reaps a held version; two rebuilders race the pointer | MED | GC never touches current/current-1 (age>SLA+grace); swap is CAS + collision-free version-IDs (C3); single-flight coalescer (PE G7). |

**Adversarial pass outcome:** the arch-adversary attempted a silent-wrong-serve construction under
every RC and found ZERO that survive the design-as-intended; the two that survived the
design-as-DRAWN (AV-1, AV-2) are closed by C1/C2 above. No fork choice was reversed. The design
holds.

## 8. Reversibility assessment (one-way doors flagged, P8)

| Decision | Door | Reversibility |
|----------|------|---------------|
| F1/F3 key/schema shape (DP-2) | **one-way post-cutover** | TWO-WAY during dark-build/parity; ONE-WAY once v1 deleted. Operator ratifies (packet carries corrected S3 premise + dissent). |
| F5 consumer contract (DP-3) | **one-way (cross-service)** | ONE-WAY once external MCP/fleet consumers depend on the wire contract. Operator ratifies. |
| F2 / F4 / F6 | two-way | value-object / internal / emission contracts; RATIFIED-AUTO (challenge passed). |
| v1-live-path P6 boundary (DP-1F) | — | RATIFIED-BY-OPERATOR (c-i HOLD P6); residual logged as extinction-urgency accelerant. |
| v1 deletion (S11) | one-way | Door #1, operator — out of S1 scope. |

No code-level one-way door is crossed in S1 (design only). DP-2/DP-3 staged for the operator with
the arch-adversary dissent attached verbatim.

## 9. Handoff status (S1 exit criteria — FINALIZED)

- [x] TDD covers all six RC invariants as constructions (§3) — each impossible-by-construction or fail-loud; Phase-2 conditions folded.
- [x] Six forks F1-F6 with final states (§5): F2/F4/F6 RATIFIED-AUTO; F1+F3, F5 STAGED-FOR-OPERATOR.
- [x] Five inter-module seams FROZEN (v1.0-frozen-2026-07-29, §4) with the PE [H1]-[H23] hardened contracts + C1-C7.
- [x] Disposition ledger (§10): every C1-C11 + [H1]/[H5]/[H20] + OQ-1/OQ-2 ACCEPT/REBUT recorded.
- [x] Build-notes (§11): C8-C11 routed to wave-2 sprints (NOT designed in).
- [x] Three operator decision-packets authored (DP-2, DP-3, DP-1F) with dissent verbatim.
- [x] Premise ledger re-anchored fresh (§1); the false S3-atomicity premise CORRECTED (P12).
- [x] **PT-01 hard gate (Potnia): PASS 2026-07-29** — all 5 structural checks + 4 supplementary duties YES (de novo, per-question receipts); adversary BLOCK-triggers verified cleared; status flipped to `ratified`.
- [x] DP-2 / DP-3 operator ratification — **RATIFIED 2026-07-29** (DP-2: shape C · entity-after-project, S3-atomicity SVR discharged; DP-3: 424+refusal-SLI · F5-5 P11 law · stale-200 ADR superseded-executed). S3 UNBLOCKED; S5 door satisfied (awaits {S2, S3}).

This finalize does NOT gold-plate (P7): it stops at whole-design + frozen seams + folded conditions
+ operator packets. Rigor concentrates at the cutover gate (S8) and the doors (DP-2/DP-3).

## 10. Phase-2 disposition ledger

Every adversary condition (C1-C7 MUST-FIX; C8-C11 CARRY), PE hardening ([H1]/[H5]/[H20]), and RA
open question (OQ-1/OQ-2). ACCEPT = folded into the design (§ ref); door-scoped rebuttals ride into
the packet for the operator.

| Item | Disposition | One line |
|------|-------------|----------|
| **C1** [AV-1, Seam 3] | **ACCEPT** | Per-section live-fetch provenance; artifact `built_from_live_at`=MIN over sections; a probe cannot advance a section instant — only a content fetch does (§3 RC-B, Seam 3). Chosen over forbid-reuse because it answers RK1 honestly. |
| **C2** [AV-2, Seam 4] | **ACCEPT** | Age arm per-read; digest at bytes-ingress; result-caching above the gate FORBIDDEN; TDD "re-hashes served bytes"→"re-canonicalizes parsed frame" (§3 RC-B, Seam 4 [H16]). |
| **C3** [RC-A/E, Seam 2] | **ACCEPT** | `swap_pointer` is true CAS (If-Match ETag); collision-free version-IDs (UUID/timestamp/digest) (Seam 2 [H6]). |
| **C4** [F1/F3, DP-2] | **ACCEPT (rides DP-2)** | Corrected the false S3-atomicity premise (P12); added A-prime/C-prime/E; genuinely re-evaluated (recommendation HELD at C on corrected grounds, A-prime named strongest simpler alt); dissent verbatim in DP-2. |
| **C5** [F5, DP-3] | **ACCEPT (rides DP-3)** | F5-5 SDK enumerated; explicit SUPERSEDED of ADR-serve-stale-within-bound; status-class two-sided (rec 424+refusal-SLI); shape-hostile bodies; dissent verbatim in DP-3. |
| **C6** [RC-C, OQ-2] | **ACCEPT** | Omission BY-CONSTRUCTION; explicit-UNKNOWN FAIL-LOUD-at-construction (honest OQ-2 disclosure); servable set registry-DERIVED (no drift enum) (§3 RC-C, Seam 2 [H4]). |
| **C7** [AV-6, Seam 5] | **ACCEPT** | Two-sided expected-set: registry ∪ store enumeration; either-side mismatch fires (§3 RC-F, Seam 5 [H20]). |
| **[H1]** digest canon | **ACCEPT** | Frozen in `substrate.freshness`; `canonical_digest()` helper; 5 pins (Seam 1). |
| **[H5]** read_current raises | **ACCEPT** | `ArtifactMissing` on absent pointer/object; never `(None, None)` (Seam 2). |
| **[H20]** completeness metric | **ACCEPT (extended by C7)** | Completeness ≠ heartbeat; two-sided expected-set (Seam 5). |
| **OQ-1** refusal payload | **ACCEPT** | RefusePayload FROZEN as the RC-A-2 observable (plane, absolute age, magnitude, per-section delta); wire format = DP-3, fields = seam; NOT narrowed (Seam 4 [H14]). |
| **OQ-2** RC-C degrade | **ACCEPT** | Disclosed: RC-C is BY-CONSTRUCTION for omission, FAIL-LOUD-at-construction for explicit-UNKNOWN (§3 RC-C). |
| **C8** SLA governance | **ACCEPT → CARRY (§11)** | Where `sla_seconds` lives + who changes it + operator-visible current-vs-SLA-old delta → S2 / DP-3 note. |
| **C9** ValidationReceipt swap | **ACCEPT → CARRY (§11)** | Gate swap on a receipt minted by `validate()`, or a discriminating swap-before-validate test → S4. |
| **C10** fired-alarm evidence | **ACCEPT → CARRY (§11)** | One observed end-to-end fired alarm at the cutover gate → S6/S8. |
| **C11** SUNSET_AFTER ruling | **ACCEPT → CARRY (§11)** | SUNSET_AFTER extension requires an operator-visible ruling → S3/S11. |

No REBUT. Every condition is accepted; door-scoped items (C4, C5) ride into their packets where the
operator holds the ruling. The adversary's falsification hooks are addressed: AV-1's "reuse means
per-section verification" is answered by C1's "only a content FETCH advances the instant; a probe
decides scheduling only" (a reused section is NOT re-verified — it honestly keeps its old instant and
the artifact ages); the S3-atomicity claim is corrected (P12) and receipted at S2 before DP-2 locks.

## 11. Build-notes (C8-C11 — routed to wave-2 sprints; NOT designed in here)

Per the coordinator's instruction, the four CARRY-TO-BUILD conditions are recorded for their owning
sprint and deliberately NOT designed into the S1 frozen contract (P7 — do not gold-plate the corridor):

- **C8 → S2 (freshness) + DP-3 note.** SLA governance: declare where `sla_seconds` per (project,
  entity) lives (entity registry per [H1]), who may change it, and surface the values + the "provably
  ≤ SLA-old (not 'current')" semantic delta to the operator no later than the cutover gate — cheapest
  as a DP-3 packet line. Quantify the F2-3 decay-probe rot-trigger threshold at S8. **Watch:** AV-3's
  construction (an unreviewed 14-day SLA re-serves the wound with a green proof) — SLA governance is
  the whole truth-content of RC-B.
- **C9 → S4 (rebuild).** Gate `swap_pointer` on a `ValidationReceipt` minted only by
  `AcceptancePredicates.validate()` (construction-enforces validate-before-swap), OR lock the ordering
  with a discriminating swap-before-validate RED test if the capability change is declined.
- **C10 → S6 (observe) / S8 (gate).** Cutover-gate evidence includes ONE observed end-to-end fired
  alarm: synthetic unprovability → CloudWatch alarm → operator-visible SNS notification (closes the
  alarm-action void; SNS-gap precedent on record in this fleet).
- **C11 → S3 / S11 (extinction).** One doctrine line at S9/S11: a `SUNSET_AFTER` extension requires an
  operator-visible ruling — a serial date-bump is the immortal bridge re-entering with receipts.

---

*Authored by architect (10x-dev), S1. Draft 2026-07-27; FINALIZED 2026-07-29 folding the Phase-2
arch-adversary (PASS-WITH-CONDITIONS) + principal-engineer (BUILDABLE-AS-DRAWN). Five seams FROZEN
v1.0-frozen-2026-07-29 (the S2-S7 build contract). Two operator doors staged (DP-2, DP-3). PT-01
flips status to ratified. No fork reversed (P8). Evidence grade MODERATE (self-authored; self-ref
ceiling — STRONG is eunomia at epoch exit).*
