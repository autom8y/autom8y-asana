---
type: decision
decision_subtype: adr
id: ADR-SEAM1
artifact_id: ADR-seam1-entity-identity-key
schema_version: "1.0"
status: draft
lifecycle_status: draft
date: "2026-06-08"
rite: 10x-dev
initiative: "CR-3 dataframe-resolution defect class — SEAM-1 entity-identity key contract + FM-4 value-population receipt + FM-2 status extraction"
session_id: cr3-dfr-seam1
deciders:
  - architect (10x-dev rite)
consulted:
  - principal-engineer (10x-dev rite, downstream implementer)
  - qa-adversary (10x-dev rite, broken-fixture-RED proof)
evidence_grade: MODERATE
evidence_grade_rationale: >
  Self-authored design within the 10x-dev rite; caps at MODERATE per
  self-ref-evidence-grade-rule. STRONG certification is the eunomia
  rite-disjoint critic's at campaign exit (per G-CRITIC).
supersedes: []
related:
  - ADR-G2RECV-002 (offer-domain cache-only serving contract — hard non-regression)
  - ADR-1 honest-empty-200 (final-artifact persist gate)
  - ADR-006 (verification-recency stamp; manifest re-seed)
  - TDD-UNIFIED-DF-PERSISTENCE-001 (storage protocol consolidation)
---

# ADR-SEAM1: Entity-Identity in the DataFrame S3 Key Contract

## Status

DRAFT — pending principal-engineer implementation + qa-adversary broken-fixture-RED proof + eunomia STRONG certification.

## Context

### The defect class (one sentence)

The DataFrame S3 cache key is **entity-agnostic** — `dataframes/{project_gid}/dataframe.parquet`
and `dataframes/{project_gid}/sections/{section_gid}.parquet` carry NO entity_type
discriminator (`storage.py:336`, `storage.py:348`) — so two distinct entity views
of the **same Asana project GID** collide on the same key. Project `1143843662099250`
is BOTH the `offer` warm target (`entity_registry.py:517`, `warmable=True`,
`warm_priority=3`) AND a body-parameterized `section` query target. The next
`section` warm of that project clobbers the healthy `offer` frame.

### The telos at risk (G-DENOM)

At HEAD a fresh `offer` warm produced **62 active-classified offer combos /
$79,485 active_mrr** — proving the cascade/cf extraction at `schemas/offer.py:41-89`
(`mrr` = `cascade:MRR`, `offer_id` = `cf:Offer ID`, `cost` = `cf:Cost`,
`weekly_ad_spend` = `cascade:Weekly Ad Spend`) WORKS. But that 62 lives at the
entity-AGNOSTIC key `dataframes/1143843662099250/dataframe.parquet`. The next
`section` warm of project `1143843662099250` writes a section-shaped frame to the
**same key**, clobbering the offer frame back to ~7 rows (the cross-entity
collision artifact). The fix makes 62 DURABLE against that collision.

### The exact discard mechanism (SEAM-1, proven at HEAD)

The entity_type is **present at the boundary and thrown away one call later**:

1. `dataframe_cache.py:948-950` `_build_key(project_gid, entity_type)` →
   `"{entity_type}:{project_gid}"` (entity-AWARE, e.g. `offer:1143843662099250`).
2. `dataframe_cache.py:~306` passes that key to `progressive_tier.get_async(cache_key)`.
3. `cache/dataframe/tiers/progressive.py:127` `_parse_key` splits it back into
   `(entity_type, project_gid)` — entity_type IS in scope here.
4. `cache/dataframe/tiers/progressive.py:144`/`:146` calls
   `storage.load_dataframe(project_gid)` — **entity_type discarded**.
5. `storage.py:334` `_df_key(project_gid)` builds the key from `project_gid` ALONE.

The same discard happens on the write path: `progressive.py:239`
`write_final_artifacts_async(project_gid=..., entity_type=entity_type)` →
`section_persistence.py:790` `save_dataframe(project_gid, df, watermark, entity_type=...)`
— but `entity_type` is only stamped into **watermark metadata** (`storage.py:713-714`),
NOT into the **key** (`storage.py:763` writes `_df_key(project_gid)`).

### Two companion defects in the same defect class

- **FM-2 (status 100% null)**: `schemas/section.py:23` + `schemas/project.py:23`
  declare `status` with `source=None` and the comment "Derived from custom fields;
  S-07: minimal extraction" — but **ZERO `_extract_status` implementations exist**
  (`grep -rn 'def _extract_status\b' src/` → empty). Section/project bind
  `SchemaExtractor` (`entity_registry.py` section/project descriptors), a generic
  extractor with NO derived-field methods. The `source=None` dispatch at
  `extractors/base.py:251-260` looks for `_extract_status`, finds none, and
  `return None` (line 260) — 100% null by construction. The only `_extract_status_code`
  (`patterns/error_classification.py:160`) is unrelated HTTP-error classification.

- **FM-4 (value-population receipt absent)**: there is NO post-warm assertion that
  the active-classified subset's `mrr`/`offer_id` non-null rate clears a floor. A
  present-but-null economics frame (62 rows, all-null mrr) would pass every existing
  gate silently — there is no receipt to fire RED.

### Constraints (from the standing grant + PV)

- PV-4: ORTHOGONAL to CR-3 GATE-2 soak. PV-5: section warm-lane is PAUSED (Trap-4) —
  the section-arm clobber is currently dormant but the key collision is live the
  instant it un-pauses; the fix must land while it is safe.
- ADR-G2RECV-002 hard non-regression: offer-domain entities (`body_parameterized=False`)
  are cache-only; a miss returns `None`. The key change must NOT alter that.
- Operator levers (NOT in code scope): live S3 migration, merge, warm. The code
  must SUPPORT the transition (build-on-miss, dual-read), not EXECUTE it.
- Receipt ships WARN/alarm-first, NOT hard-fail (must not 503 a healthy-but-degraded
  warm).

### NFRs (measurable)

| NFR | Metric | Target | Method | Environment |
|-----|--------|--------|--------|-------------|
| NFR-1 Collision-immunity | offer active_mrr combos after a section-warm of the same project GID | stays == 62 (was: clobbered to ~7) | broken-fixture-RED test injecting a cross-entity write to the same project_gid | local CI `uv run pytest -n0` |
| NFR-2 Read-correctness | every reader resolves the entity-keyed path; 0 readers resolve the old entity-agnostic path post-cutover (except offline CLI per Decision-3) | 0 mis-keyed reads | call-site inventory test asserting `_df_key`/`_section_key` receive entity_type | local CI |
| NFR-3 Population-floor | non-null rate of `mrr` AND `offer_id` over the active-classified offer subset | >= 0.80 (WARN floor); RED if a present frame is all-null | FM-4 receipt unit test with a present-but-null fixture | local CI |
| NFR-4 Status-population | non-null rate of `status` over section/project rows with a resolvable status custom field | > 0.0 (was: exactly 0.0) | FM-2 extractor unit test on a fixture task with a Status cf | local CI |
| NFR-5 No-503-regression | offer-domain cache miss still returns None (ADR-G2RECV-002) | unchanged | existing `_get_dataframe` non-regression test | local CI |

## Decision

### Decision 1 — New key shape (entity-segmented)

**CHOSEN: `dataframes/{project_gid}/{entity_type}/dataframe.parquet`** and
`dataframes/{project_gid}/{entity_type}/sections/{section_gid}.parquet`,
with the manifest, watermark, and index co-located under the same entity segment:
`dataframes/{project_gid}/{entity_type}/{manifest.json,watermark.json,gid_lookup_index.json}`.

#### Options enumerated

- **Option 1A — entity AFTER project_gid (CHOSEN)**:
  `dataframes/{project_gid}/{entity_type}/dataframe.parquet`.
  - Advantage: preserves the existing top-level `dataframes/{project_gid}/` prefix
    that `list_projects()` (`storage.py:1143-1164`) and the offline reader
    (`offline.py:83` prefix `dataframes/{project_gid}/sections/`) already scan;
    the project-GID stays the primary partition. `list_projects` keeps returning
    project GIDs (it scans `CommonPrefixes` under `dataframes/` and the first
    segment is still the project GID — verified: `storage.py:1158-1162` strips
    `self._prefix` and takes the segment before the first `/`).
  - Advantage: one project's multiple entity views are siblings under one prefix —
    natural for per-project enumeration and debugging.
- **Option 1B — entity BEFORE project_gid**:
  `dataframes/{entity_type}/{project_gid}/dataframe.parquet`.
  - Advantage: clean per-entity enumeration (`list all offer projects`).
  - Disadvantage: breaks `list_projects()` semantics (first segment becomes
    entity_type, not project GID) — forces a rewrite of enumeration + the offline
    reader prefix. Larger blast radius for no telos benefit.
- **Option 1C — entity as a key SUFFIX on the filename**:
  `dataframes/{project_gid}/dataframe.{entity_type}.parquet`.
  - Advantage: minimal path change; sections dir unchanged.
  - Disadvantage: sections still collide (`sections/{section_gid}.parquet` shared
    across entities for the same project — the section-arm clobber is NOT fixed).
    REJECTED: does not close the section-arm of the defect (the live clobber path).
- **Option 1D — hash/composite key** `dataframes/{sha(project_gid+entity_type)}/...`.
  - Disadvantage: opaque, un-debuggable, breaks the offline reader's
    human-navigable prefix. REJECTED.

**Justification for 1A**: it is the only option that fixes BOTH the dataframe-arm
AND the section-arm of the collision (1C fails the section arm) while preserving
`list_projects()` and the offline-reader prefix semantics (1B breaks them). The
project GID remains the primary partition, so all existing project-level tooling
keeps working; entity_type becomes a sub-partition. This is the dependency-correct
direction: the key now encodes the full identity tuple `(project_gid, entity_type)`
that the cache layer already carries (`dataframe_cache.py:948`).

### Decision 2 — Migration / back-compat: DUAL-READ FALLBACK (RECOMMENDED)

**CHOSEN: dual-read fallback — read the new entity-keyed path first; on miss fall
back to the legacy entity-agnostic path. Always WRITE the new path only. The live
S3 migration is the OPERATOR lever; the code supports the transition without
executing it.**

#### Options enumerated

- **Option 2A — clean cutover (write+read new key only)**:
  - Advantage: simplest code; no fallback branch; orphaned old keys self-expire by
    being ignored.
  - Disadvantage: **temporarily loses the live 62** until the next `offer` warm
    re-populates the new key — the cold-cache window violates G-DENOM's "62 stays
    62" until a warm runs. The receiver would cold-miss offer reads (offer-domain
    is cache-only → returns None → empty denominator) until the operator triggers
    an offer warm. UNACCEPTABLE against the telos which requires the 62 to be
    DURABLE, not "durable after the next warm."
- **Option 2B — dual-read fallback (CHOSEN)**:
  - Mechanism: `load_dataframe(project_gid, entity_type)` and
    `load_section(project_gid, section_gid, entity_type)` try
    `_df_key_v2(project_gid, entity_type)` first; on `None` they retry
    `_df_key_legacy(project_gid)` (the current entity-agnostic key). Writes go to
    v2 ONLY.
  - Advantage: **preserves the live 62 immediately** — the existing entity-agnostic
    `dataframes/1143843662099250/dataframe.parquet` (the current home of the 62) is
    read via fallback until the next offer warm writes the v2 key, after which the
    v2 key is authoritative. No cold window. G-DENOM holds across the transition.
  - Advantage: orphans the old keys harmlessly (they are read-only fallback;
    never written again; operator deletes them out-of-band post-migration).
  - Advantage: the section-arm collision is closed immediately — section writes go
    to `dataframes/{gid}/section/...` (v2), offer reads fall back to the legacy
    offer frame, so a section warm can no longer clobber the offer denominator
    (they no longer share a write key).
  - Disadvantage: one extra S3 GET on the fallback path (only on v2-miss; warm
    cache hits never fall back). Bounded, transient (ends when all entities are
    re-warmed), and gated behind a `legacy_fallback_enabled` flag the operator
    flips off post-migration.
- **Option 2C — dual-WRITE (write both keys)**:
  - Disadvantage: doubles write I/O permanently and re-introduces the collision on
    the legacy key (two entities still write the same legacy key). REJECTED — does
    not fix the defect.

**Justification for 2B**: only dual-read preserves the live 62 with ZERO cold
window (G-DENOM: "62 must stay 62"), while still routing ALL writes to the
collision-free v2 key (G-PROPAGATE). The fallback is read-only, flag-gated, and
self-retiring. The live S3 migration (copy legacy → v2, then delete legacy) stays
the OPERATOR lever; the code merely tolerates both layouts during the window.

#### Fossil-valve interaction (PV-1)

The empty-branch fossil valve at `builders/progressive.py:1007-1020` (a section
with no first-page tasks marks COMPLETE with 0 rows and does NOT overwrite the
merged frame) is PRESERVED — it operates on the manifest/section layer, which moves
wholesale under the entity segment with no logic change. The diagonal-relaxed metric
union at `offline.py:95` / `section_persistence.py:741` is unchanged (it concatenates
sections WITHIN one entity's segment — never across entities, because cross-entity
sections no longer share a prefix).

### Decision 3 — Complete call-site inventory (G-PROPAGATE)

ONE fix on the entity-identity substrate (the two key-builders + the load/save
methods that call them), threaded through ALL call-sites. Every reader/writer below
MUST thread `entity_type`. A missed reader = reads the wrong/old key.

#### Substrate (the single fix site — add `entity_type` param + v2/legacy key-builders)

| # | File:line | Symbol | Change |
|---|-----------|--------|--------|
| S1 | `dataframes/storage.py:334` | `_df_key(project_gid)` | add `entity_type`; emit v2 path. Add `_df_key_legacy` for fallback. |
| S2 | `dataframes/storage.py:346` | `_section_key(project_gid, section_gid)` | add `entity_type`; emit v2 path. Add legacy variant. |
| S3 | `dataframes/storage.py:338` | `_watermark_key` | add `entity_type` (co-locate under entity segment). Legacy fallback. |
| S4 | `dataframes/storage.py:342` | `_index_key` | add `entity_type`. Legacy fallback. |
| S5 | `dataframes/storage.py:350` | `_manifest_key` | add `entity_type`. Legacy fallback. |
| S6 | `dataframes/storage.py:725` | `save_dataframe(...)` | thread `entity_type` into `_df_key` (already accepts `entity_type` kwarg at :731 — currently only used for watermark metadata at :776; now also keys the parquet). |
| S7 | `dataframes/storage.py:792` | `_load_dataframe_impl` | add `entity_type` param; v2-first then legacy fallback on the df+watermark GETs (:813/:821). |
| S8 | `dataframes/storage.py:839` | `load_dataframe(project_gid)` | add `entity_type` param. |
| S9 | `dataframes/storage.py:857` | `load_dataframe_with_metadata` | add `entity_type` param. |
| S10 | `dataframes/storage.py:876` | `delete_dataframe` | add `entity_type`; delete v2 (+ optionally legacy under operator flag). |
| S11 | `dataframes/storage.py:1038` | `save_section(...)` | thread `entity_type` into `_section_key` (:1062). |
| S12 | `dataframes/storage.py:1068` | `load_section(...)` | add `entity_type`; v2-first then legacy fallback (:1082). |
| S13 | `dataframes/storage.py:1087` | `delete_section` | add `entity_type`. |
| S14 | `dataframes/storage.py:135`/`:139` | `save_watermark`/`get_watermark` | add `entity_type`. |
| S15 | `dataframes/storage.py:149`/`:153`/`:157` | `save_index`/`load_index`/`delete_index` | add `entity_type`. |
| S16 | `dataframes/storage.py:1143` | `list_projects` | UNCHANGED — first segment is still project GID under Option 1A (verified :1158-1162). |
| S17 | `dataframes/storage.py:64` | `DataFrameStorage` Protocol | mirror every signature change in the Protocol so the contract is explicit. |

#### SectionPersistence layer (its own key-builders + delegations)

| # | File:line | Symbol | Change |
|---|-----------|--------|--------|
| P1 | `section_persistence.py:367` | `_make_section_key` | add `entity_type` (or delete — it duplicates storage's; see Decision 3a). |
| P2 | `section_persistence.py:371` | `_make_dataframe_key` | add `entity_type` / delete. |
| P3 | `section_persistence.py:375` | `_make_watermark_key` | add `entity_type` / delete. |
| P4 | `section_persistence.py:379` | `_make_index_key` | add `entity_type` / delete. |
| P5 | `section_persistence.py:363` | `_make_manifest_key` | add `entity_type` — manifest moves under entity segment. NOTE: `SectionManifest.entity_type` (`:124`) already carries it; thread that value. |
| P6 | `section_persistence.py:582` | `write_section_async` → `save_section` | thread `entity_type` (read from manifest or new param). |
| P7 | `section_persistence.py:645` | `read_section_async` → `load_section` | thread `entity_type`. |
| P8 | `section_persistence.py:790` | `write_final_artifacts_async` → `save_dataframe` | already has `entity_type` param (:766); thread it into the key (currently only metadata). |
| P9 | `section_persistence.py:443`/`:459` | `get_manifest_async`/`_save_manifest_async` → `_make_manifest_key` | thread `entity_type`. |
| P10 | `section_persistence.py:855` (write_checkpoint) | `save_section` | thread `entity_type`. |
| P11 | `section_persistence.py:934` (delete_section_files) | `delete_section` | thread `entity_type`. |

##### Decision 3a — collapse SectionPersistence's duplicate key-builders

`section_persistence.py:363-381` re-declares `_make_*_key` builders that duplicate
storage's `_*_key`. To honor G-PROPAGATE (ONE substrate fix, not N orphans),
**delete P1-P4** and route ALL key construction through the storage layer
(`SectionPersistence` already delegates I/O to `self._storage`). Only the manifest
key (P5) is built in SectionPersistence today (storage has `_manifest_key` too at
:350 but SectionPersistence builds its own at :363) — consolidate to one. This
removes a duplicate-substrate orphan risk.

#### Cache-tier readers/writers (entity_type already in scope — thread it down)

| # | File:line | Symbol | entity_type source | Change |
|---|-----------|--------|--------------------|--------|
| C1 | `cache/dataframe/tiers/progressive.py:144` | `get_async` → `load_dataframe_with_metadata(project_gid)` | `_parse_key` (:127) already yields `entity_type` | pass `entity_type`. |
| C2 | `cache/dataframe/tiers/progressive.py:146` | `get_async` → `load_dataframe(project_gid)` | same | pass `entity_type`. |
| C3 | `cache/dataframe/tiers/progressive.py:239` | `put_async` → `write_final_artifacts_async(entity_type=...)` | `_parse_key` (:226) | already passes `entity_type` — verify it now keys the parquet (via P8). |
| C4 | `cache/dataframe/tiers/progressive.py:292` | `exists_async` → `load_dataframe(project_gid)` | `_parse_key` (:286) | pass `entity_type`. |
| C5 | `cache/dataframe/tiers/progressive.py:319` | `delete_async` → `delete_dataframe(project_gid)` | `_parse_key` (:309) | pass `entity_type`. |

#### Preload readers/writers (entity_type in scope at the loop)

| # | File:line | Symbol | entity_type source | Change |
|---|-----------|--------|--------------------|--------|
| PR1 | `api/preload/legacy.py:182` | `persistence.load_dataframe(project_gid)` | loop var `entity_type` (:166) | pass `entity_type`. |
| PR2 | `api/preload/legacy.py:283` | `persistence.save_dataframe(project_gid, ...)` | same | pass `entity_type`. |
| PR3 | `api/preload/legacy.py:175`/`:206`/`:284` | `load_index`/`save_index` | same | pass `entity_type`. |
| PR4 | `api/preload/progressive.py:409` | `df_storage.load_dataframe(project_gid)` | loop var `entity_type` (:382) | pass `entity_type`. |
| PR5 | `api/preload/progressive.py:513` | `df_storage.save_dataframe(project_gid, s3_df, s3_watermark)` | same | pass `entity_type` (self-heal write must key v2). |

#### Builder writers (entity_type is `self._entity_type`)

| # | File:line | Symbol | Change |
|---|-----------|--------|--------|
| B1 | `builders/progressive.py:661` | `write_final_artifacts_async(..., entity_type=self._entity_type)` | already passes; verify P8 keys parquet. |
| B2 | `builders/progressive.py:814` | `write_final_artifacts_async(..., entity_type=self._entity_type)` | same. |
| B3 | `builders/progressive.py` (no-sections empty persist, ~:661 block) | `write_final_artifacts_async(..., entity_type=self._entity_type)` | same. |

#### Offline path (THE ONE READER WITHOUT entity_type — special handling)

| # | File:line | Symbol | Problem | Change |
|---|-----------|--------|---------|--------|
| O1 | `dataframes/offline.py:83` | `load_project_dataframe_with_meta` prefix `dataframes/{project_gid}/sections/` | NO entity_type in scope (sync CLI) | add OPTIONAL `entity_type` param. When provided: scan `dataframes/{project_gid}/{entity_type}/sections/` (v2) then fall back to legacy prefix. When omitted: scan BOTH layouts (legacy `dataframes/{project_gid}/sections/` AND any `dataframes/{project_gid}/*/sections/`) and concat — preserves the CLI's "load everything for this project" semantics. |
| O2 | `query/offline_provider.py:120` | `load_project_dataframe_with_meta(project_gid)` | HAS `entity_type` (:93) but discards it | pass `entity_type` through. |
| O3 | `metrics/__main__.py:748` | `load_project_dataframe(project_gid)` | NO entity_type (CLI) | accept optional `--entity-type` flag; default = scan-all (O1 omitted-param semantics). The live re-derived offer count is produced by passing `offer`. |

**Inventory completeness check**: this enumerates EVERY hit of
`load_dataframe`/`save_dataframe`/`load_section`/`save_section`/`write_final_artifacts`/
`load_project_dataframe` from the repo-wide grep, plus the two key-builders and
their Protocol mirror. No reader is left resolving a `project_gid`-only key except
the offline CLI, which is handled by scan-all fallback (O1).

### Decision 4 — Value-population RECEIPT (FM-4)

**CHOSEN: a new `post_build_population_receipt(...)` sibling to
`post_build_validate_and_audit` (`builders/post_build_validation.py:28`), invoked at
the warm SUCCESS attestation immediately after Step 5.5 validation
(`builders/progressive.py:785`) and before/at the final write (`:814`). WARN-first
(structured `logger.warning` + an EMF/alarm-shaped metric), NEVER hard-fail.**

#### Mechanism

- Signature mirrors the existing validator:
  `post_build_population_receipt(merged_df, schema, entity_type, project_gid) -> PopulationReceipt`.
- Sibling threshold constant pattern: `POPULATION_WARN_THRESHOLD = 0.80`
  (mirrors `cascade_validator.py:31` `CASCADE_NULL_WARN_THRESHOLD = 0.05`).
- Assertion: over the **active-classified subset** (filter rows whose `section`
  classifies to ACTIVE/ACTIVATING via the same `get_classifier(entity_type)` path
  used at `universal_strategy.py:361,460`), compute non-null rate of the entity's
  **value columns** declared in the schema (for `offer`: `mrr`, `offer_id`; derived
  from `OFFER_SCHEMA` cf/cascade columns at `schemas/offer.py:42,77`). If the subset
  is non-empty AND the non-null rate < threshold → emit `population_receipt_below_floor`
  WARNING + alarm metric. If the subset is non-empty AND the rate is exactly 0.0
  (present-but-null frame) → the receipt is the RED signal the broken-fixture test
  asserts.
- WARN-first justification: a degraded-but-present warm must still serve (the 62 is
  better than nothing); the receipt makes the degradation OBSERVABLE and alarmable
  without 503ing. Matches the operator-gated philosophy (receipt ships WARN/alarm-first
  per the standing grant).
- Entity-scoped: only fires for entities whose schema declares value columns
  (offer-domain). Section/project (no economic value columns) skip via an empty
  value-column set — same safe-degradation shape as `post_build_validation.py:94`
  (`if total_rows > 0 and schema is not None`).

#### Options enumerated

- **Option 4A — sibling validator module, WARN-first (CHOSEN)**: minimal new surface,
  reuses the proven validator shape + threshold-constant convention + WARN discipline.
- **Option 4B — extend `post_build_validate_and_audit` in place**: conflates
  cascade-correction (which mutates the frame) with a read-only population assertion;
  muddies the single-responsibility boundary. REJECTED.
- **Option 4C — hard-fail the warm on below-floor**: would 503 a healthy-but-degraded
  warm and could empty the denominator on a transient cascade lag. REJECTED — violates
  WARN-first.

### Decision 5 — FM-2 `_extract_status` design

**CHOSEN: change `status` source from `None` to a real `cf:` source (Option 5B) —
`source="cf:Status"` — falling back to implementing a derived extractor only if no
canonical Status custom field exists.**

#### Options enumerated

- **Option 5A — implement `_extract_status` on a hand-coded Section/Project extractor**:
  Section/project currently bind the GENERIC `SchemaExtractor` (`entity_registry.py`
  section/project descriptors). Adding `_extract_status` would require EITHER (a) a
  hand-coded `SectionExtractor`/`ProjectExtractor` subclass (new classes, new
  descriptor wiring) OR (b) a `_extract_status` method ON `SchemaExtractor` — but
  `SchemaExtractor` is generic-by-design (`extractors/schema.py` docstring: "entities
  with custom derived field logic still require hand-coded extractors"). Putting a
  status-specific method on the generic extractor pollutes it. The derived path also
  requires knowing WHERE status comes from (a custom field, a section name, a tag) —
  which is exactly what a `source` declaration encodes.
- **Option 5B — change `source=None` → `source="cf:Status"` (CHOSEN)**: the status
  IS a custom field on Asana tasks (the schema comment literally says "Derived from
  custom fields"). The `cf:` extraction path is already fully implemented
  (`extractors/base.py:269-274,327-332` → `resolver.get_value(task, "cf:Status")`),
  works under the generic `SchemaExtractor`, and requires ZERO new extractor classes.
  This is the dependency-correct fix: the `source` field is the declared contract for
  WHERE a column's value comes from; the bug is that it was left `None` (= "derived,
  call `_extract_status`") when it should have been `cf:Status` (= "resolve the Status
  custom field"). The implementer MUST verify the canonical custom-field NAME against
  production (DuckDB MCP / a live offer/section task) before locking the literal —
  per premise-validation-discipline. If the field is named differently (e.g.
  "Account Status", "Stage"), use that exact name.
- **Option 5C — derive status from the section name via the classifier**: section
  classification (ACTIVE/ACTIVATING/...) already exists (`get_classifier`). Status
  could be `source=None` + a `_extract_status` that runs the classifier on the
  section. Disadvantage: status would then DUPLICATE the classification axis and
  couple the column to the classifier; it also still needs a hand-coded extractor
  (5A's cost). Viable as a FALLBACK if no Status cf exists, but inferior to 5B when
  a real cf is present.

**Justification for 5B**: it fixes the 100%-null at the declaration layer with no new
classes, uses the already-working `cf:` path, and restores the schema's stated intent
("derived from custom fields"). The implementer's gate: confirm the production custom
field name first (premise-validation-discipline). If — and only if — no Status custom
field exists on these tasks, fall back to 5C (classifier-derived, with a hand-coded
extractor). The TDD records 5B as primary with 5C as the documented fallback.

## Consequences

### Positive

- G-DENOM: the 62/$79,485 offer denominator becomes DURABLE — a section warm of
  project `1143843662099250` can no longer clobber it (different write key); dual-read
  preserves it with zero cold window during migration.
- G-PROPAGATE: ONE substrate fix (two key-builders + the load/save methods + their
  Protocol mirror), threaded through ALL ~40 call-sites enumerated; the duplicate
  SectionPersistence key-builders are collapsed (no orphan substrate).
- FM-2: status column populates from `cf:Status` (was 100% null).
- FM-4: a present-but-null economics frame fires a RED receipt (was: silent pass).

### Negative / risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| A reader is missed and keeps reading the legacy key | HIGH | Dual-read fallback makes a missed reader still RESOLVE (degraded, not broken) during the window; the call-site inventory test (NFR-2) asserts every storage method receives `entity_type`. |
| Live S3 has data only at legacy keys at cutover | MED | Dual-read (Decision 2B) reads legacy on v2-miss — no data loss; operator migrates out-of-band. |
| `cf:Status` field name wrong → still null | MED | premise-validation-discipline gate: confirm field name against production before locking the literal; FM-2 unit test on a real fixture catches a wrong name. |
| Receipt false-WARN during transient cascade lag | LOW | WARN-first (never 503); alarm tuned to sustained below-floor, not a single warm. |
| Offline CLI scan-all concats cross-entity frames | LOW | Documented O1 semantics; `--entity-type offer` produces the clean re-derived count; scan-all is diagonal-relaxed and only used for "everything for this project" debugging. |

### Reversibility assessment

- **Key shape (Decision 1)**: TWO-WAY DOOR during the dual-read window — writes go to
  v2 but legacy is still readable; reverting = flip writes back to legacy. Becomes a
  ONE-WAY DOOR only after the operator deletes legacy keys (operator-gated, explicit).
- **Migration (Decision 2)**: TWO-WAY DOOR — `legacy_fallback_enabled` flag; the live
  S3 copy/delete is the operator lever, reversible until delete.
- **FM-2 source change (Decision 5)**: TWO-WAY DOOR — revert the one `source=` literal.
- **Receipt (Decision 4)**: TWO-WAY DOOR — additive WARN-only module; remove to revert.

No code-level one-way doors. The only one-way door (deleting legacy S3 keys) is an
explicit OPERATOR action outside this change's scope.

## Proof obligations (G-THEATER / G-PROVE — for qa-adversary)

1. **Cross-entity collision RED**: a fixture that writes a `section`-shaped frame to
   project `1143843662099250` then reads `offer` MUST show 62 preserved (v2 key) —
   and a deliberately-broken variant that writes to the entity-AGNOSTIC key MUST show
   the offer frame clobbered to ~7 (proving the entity-key is what prevents it).
2. **Present-but-null receipt RED**: a fixture offer frame with 62 rows but all-null
   `mrr` MUST fire `population_receipt_below_floor` RED.
3. **FM-2 RED→GREEN**: a section/project fixture task with a Status custom field MUST
   produce a non-null `status` (was: null).
4. Each proven via `uv run pytest -n0` with exit codes + before/after counts, plus a
   live re-derived offer count (`metrics/__main__.py --entity-type offer`).
