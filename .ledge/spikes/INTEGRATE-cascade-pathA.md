---
type: spike
status: accepted
initiative: project-asana-pipeline-extraction
station: S2a
specialist: integration-researcher
related_spike: cascade-vs-join
path: A-cascade-extension
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
phase: 0
verdict_authority: S5 (tech-transfer)
this_artifact_authority: dependency-cartography (NOT verdict)
frame: .sos/wip/frames/project-asana-pipeline-extraction.md
shape: .sos/wip/frames/project-asana-pipeline-extraction.shape.md
workflow: .sos/wip/frames/project-asana-pipeline-extraction.workflow.md
---

# INTEGRATE — Path A (Cascade-Extension) Dependency Cartography

## §1 Telos Echo

**Throughline (verbatim, workflow §1.1):** "Vince (and every future PAT or S2S
caller) can produce a parameterized account-grain export of any business
entity via a dual-mount endpoint without custom scripting; Phase 1 verifies
against Vince's original Reactivation+Outreach CSV ask by 2026-05-11; Phase 2
cross-entity adjudication is deferred behind a spike-bounded architectural
commitment."

**This station's contribution.** Inside-view file:line dependency map for
Path A (cascade-extension) ONLY. Verdict authority pinned to S5; this
artifact widens evidence, not options. Path B + C5 mapped in S2b.

## §2 Files-Touched Map

```yaml
files_touched:
  # ── Schema authoring (per cascade field added; recurring per-field cost) ──
  - path: src/autom8_asana/dataframes/schemas/contact.py:73-89
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      New ColumnDef per added cascade field (e.g. `offer.section`,
      `offer.status` cascaded to contact). schema.version bump per change.
      Affects tests/unit/dataframes/test_contact_schema.py and any fixture
      asserting column count.
  - path: src/autom8_asana/dataframes/schemas/process.py:14-42
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      Same shape as contact: per-field ColumnDef + version bump. Process
      schema is the Vince inception-anchor target — every cascade column
      added here flows through pipeline-export rows.
  - path: src/autom8_asana/dataframes/schemas/offer.py:8-90
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      Cascade-source schema for any offer→contact/process cascade. New
      cascade fields here are NOT added to offer; they are added to the
      consumer schema (contact/process) with `source="cascade:Offer Foo"`.
      Offer schema is provider only.
  - path: src/autom8_asana/dataframes/schemas/unit.py:8-74
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      Same provider-only role as offer.py. Already cascades MRR / Weekly
      Ad Spend. Adding `unit.section` style cascades requires the field
      already exist on unit schema as `cf:` source.

  # ── Cascade registry (single point of truth for Asana field names) ──
  - path: src/autom8_asana/models/business/fields.py:1-200
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      New CascadingFieldDef per added cascade field; registered into
      CASCADING_FIELD_REGISTRY via the per-class `__init_subclass__` /
      provider class declaration. Critical: target_types and allow_override
      defaults gate runtime behavior; misdeclared = silent overwrite of
      descendant values (ADR-0054 design constraint).

  # ── Cascade resolver (no signature change for pure cascade-field extension) ──
  - path: src/autom8_asana/dataframes/resolver/cascading.py:199-275
    modification_type: refactor
    loc_delta_order: 10s
    test_surface_impact: |
      `resolve_async` already generic over field_name; new fields require
      no resolver code changes IF field is registered. `_traverse_parent_chain`
      L277-405 unchanged for new fields. ROOT-fallback at L348-366 is
      EntityType.BUSINESS-only — adding cascade from non-Business owner
      that needs ROOT fallback would require this branch extended.
  - path: src/autom8_asana/dataframes/extractors/base.py:262-326
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      `_extract_column_async` L321-325 already routes `cascade:` prefix
      through the resolver. NO change required for new cascade fields.
      Sync path L262-267 still raises ValueError on cascade — preserved.

  # ── Validator (cascade null audit + correction) ──
  - path: src/autom8_asana/dataframes/builders/cascade_validator.py:46-176
    modification_type: refactor
    loc_delta_order: 10s
    test_surface_impact: |
      `validate_cascade_fields_async` derives cascade columns from
      `schema.get_cascade_columns()` (L85) — NEW fields automatically
      validated. BUT `_CASCADE_SOURCE_MAP` at L185-191 is a HARDCODED
      dict mapping field name → source entity. Any new cascade field
      MUST be added here or audit reports "unknown" source entity.
      Tests/unit/dataframes/builders/test_cascade_validator.py:649-668
      regression-asserts thresholds; new field exercises must extend.
  - path: src/autom8_asana/dataframes/builders/cascade_validator.py:185-191
    modification_type: extension
    loc_delta_order: 10s
    test_surface_impact: |
      _CASCADE_SOURCE_MAP REQUIRED edit per added cascade field. This is
      the single largest hidden-coupling site for Path A — see §3 HC-01.

  # ── Cascade ordering / topological warm-graph (auto-derives) ──
  - path: src/autom8_asana/dataframes/cascade_utils.py:51-131
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      `cascade_provider_field_mapping` derives mapping from schema columns
      with `source="cf:..."`; new cascades that REUSE existing provider
      fields require NO change here. NEW provider fields require addition
      to provider schema (e.g., adding `cf:Offer Status` to offer.py),
      which auto-flows through.
  - path: src/autom8_asana/dataframes/cascade_utils.py:134-225
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      `cascade_warm_phases` topo-sort auto-detects new providers/consumers
      from schema columns + registry. Tests at
      tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106
      regression-pass IF warm_priority on EntityDescriptor remains
      consistent with new dependency edges.

  # ── Preload pipeline (cache warm orchestration) ──
  - path: src/autom8_asana/api/preload/progressive.py:315-321
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      shared_store creation is field-agnostic. NO change for added
      cascade fields IF the new cascade resolves through existing store.
  - path: src/autom8_asana/api/preload/progressive.py:468-502
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      `validate_cascade_fields_async` invocation is schema-driven; new
      fields auto-included. Self-heal re-persistence at L505-540 also
      schema-driven.
  - path: src/autom8_asana/api/preload/progressive.py:696-699
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      WarmupOrderingError re-raise barrier. UNCHANGED but: a new cascade
      from a non-warmable provider entity would surface here as an
      ordering violation. Defensive contract preserved.

  # ── Views / DynamicIndex / aggregator surface ──
  - path: src/autom8_asana/dataframes/views/cascade_view.py:340-380
    modification_type: refactor
    loc_delta_order: 0s
    test_surface_impact: |
      `_resolve_parent_chain_async` is field-agnostic (delegates by
      field_name). New cascade fields automatically resolved via plugin
      delegation path.
```

## §3 Hidden Coupling Map

```yaml
hidden_coupling:
  - id: HC-01
    site: src/autom8_asana/dataframes/builders/cascade_validator.py:185-191
    coupling_type: null-audit-denominator
    impact_brief: |
      `_CASCADE_SOURCE_MAP` is a hardcoded dict mapping cascade field
      name → source entity, used to annotate the cascade_key_null_audit
      log event (L249-251). Every new cascade field MUST be added here
      or the audit reports `source_entity: "unknown"`. This is silent
      observability degradation, not an error — production alarms keyed
      on `source_entity` will miss the new field. Telos consequence:
      identity_complete flag transparency for Phase 1's CSV export
      depends on this audit firing correctly per added cascade column.
    evidence_grade: STRONG
  - id: HC-02
    site: src/autom8_asana/dataframes/builders/cascade_validator.py:31-32
    coupling_type: null-audit-denominator
    impact_brief: |
      CASCADE_NULL_WARN_THRESHOLD=0.05 / CASCADE_NULL_ERROR_THRESHOLD=0.20
      were calibrated against SCAR-005's 30% production incident on the
      EXISTING cascade columns (Office Phone, Vertical, Business Name,
      MRR, Weekly Ad Spend). Adding 2-N new cascade fields without
      re-calibration assumes the new fields' baseline null rate fits the
      same distribution. A new cascade like `offer.status` may have
      structural nulls (offers without a status section) that exceed
      20% by design — would auto-error the validator.
    evidence_grade: MODERATE
  - id: HC-03
    site: src/autom8_asana/dataframes/cascade_utils.py:281-328 + EntityDescriptor.warm_priority
    coupling_type: schema-validation
    impact_brief: |
      `validate_cascade_ordering` (L281+) is L1 startup check that compares
      EntityDescriptor.warm_priority against the cascade dependency graph
      derived from schemas + registry. Adding a cascade from a NEW
      provider entity (e.g., promoting a non-provider entity to
      cascading_field_provider=True) requires both schema + descriptor +
      warm_priority changes in lockstep. A mismatch surfaces as
      ValueError at startup — fail-fast, but the required edits are
      scattered across core/entity_registry.py + schemas/{provider}.py +
      models/business/fields.py.
    evidence_grade: STRONG
  - id: HC-04
    site: src/autom8_asana/dataframes/resolver/cascading.py:348-366
    coupling_type: scope-claims
    impact_brief: |
      The ROOT-fallback branch is hardcoded to EntityType.BUSINESS only:
      "if owner_type == EntityType.BUSINESS:" extracts the field at the
      project-root task even when project isn't registered in
      ProjectTypeRegistry. A new Path-A cascade from a non-Business
      owner (e.g., cascading an Offer field down to a child Process
      where the project type is unregistered) will silently return None
      instead of falling back to ROOT. This is a scope claim baked into
      the resolver that the schema/registry does not surface.
    evidence_grade: STRONG
  - id: HC-05
    site: src/autom8_asana/dataframes/views/cf_utils.py + get_field_value
    coupling_type: schema-validation
    impact_brief: |
      `get_field_value(parent_data, field_def)` is the cascade-aware
      extractor used in BOTH the live resolver path (cascading.py:331)
      and the post-build validator (cascade_validator.py:124). It
      checks `field_def.source_field` first (e.g. "name" → Task.name)
      then falls back to `get_custom_field_value`. A new cascade with
      source_field set to a non-existent attribute will silently return
      None at extract-time AND at validator-correct-time, producing
      structural nulls that look like upstream data quality issues
      rather than misdeclared schema.
    evidence_grade: MODERATE
  - id: HC-06
    site: src/autom8_asana/dataframes/views/cascade_view.py:330-400 + UnifiedTaskStore.get_parent_chain_async
    coupling_type: cache-invalidation
    impact_brief: |
      The unified-cache CascadeViewPlugin path (cascading.py:228-234)
      delegates to `cascade_plugin.resolve_async`, which fetches parent
      chains via `_store.get_with_upgrade_async` at CompletenessLevel
      .STANDARD. A new cascade field whose source attribute requires
      FULL completeness (e.g. enum field metadata not on STANDARD
      payload) will return None from cache but resolve correctly via
      direct API. The plugin path and the direct path diverge silently.
      Tests covering cache-warmed cascade may pass while production
      cold-cache cascade returns nulls.
    evidence_grade: MODERATE
  - id: HC-07
    site: src/autom8_asana/dataframes/builders/progressive.py + section persistence S3 keys
    coupling_type: cache-invalidation
    impact_brief: |
      `s3_df` corrected by `validate_cascade_fields_async` is re-persisted
      to S3 (progressive.py L505-540). Schema version bump (e.g.
      contact 1.4.0 → 1.5.0 when adding a cascade column) MUST coincide
      with cache-key versioning OR cold-start L2 reads stale rows that
      lack the new cascade column. The schema version field exists on
      DataFrameSchema but no automated check ties it to S3 cache key
      versioning — this is a manual discipline that PR review must catch.
    evidence_grade: MODERATE
  - id: HC-08
    site: src/autom8_asana/services/dataframe_service.py + SchemaRegistry warmed cache
    coupling_type: DI
    impact_brief: |
      SchemaRegistry exposes 8 named warmed dataframes consumed by
      `api/routes/dataframes.py:400`. New cascade columns flow through
      automatically AT SCHEMA REGISTRATION TIME, but any consumer that
      asserts a specific column-set via Pydantic response model (e.g.
      ContactRow / ProcessRow at dataframes/models/) must extend in
      lockstep with the schema. TaskRow subclasses are positional
      contract holders — drift here causes runtime serialization
      failures only at the consumer boundary, not at schema build time.
    evidence_grade: STRONG
  - id: HC-09
    site: src/autom8_asana/persistence/* SavePipeline (cascading writeback)
    coupling_type: scope-claims
    impact_brief: |
      Path A only touches READ-side cascade. Persistence write-side
      `SavePipeline` does not consume the new cascade columns directly —
      but any new cascading field declared with allow_override=False
      (the DEFAULT per ADR-0054) will, on save-cycle, OVERWRITE
      descendant local values from parent. If a new Phase-2 cascade is
      added without explicitly setting allow_override=True, existing
      descendant data may be silently mutated on the next save cycle.
      This is an ADR-0054 contract pitfall, not a code bug.
    evidence_grade: MODERATE
```

## §4 Migration Phases

```yaml
phases:
  - name: phase-1a-baseline-instrumentation
    goal: |
      Pre-flight: capture baseline null rates for ALL existing cascade
      columns + planned new cascade columns BEFORE any schema change,
      and extend _CASCADE_SOURCE_MAP placeholders.
    files:
      - src/autom8_asana/dataframes/builders/cascade_validator.py:185-191
      - tests/unit/dataframes/builders/test_cascade_validator.py:649-668
    reversibility_cost: LOW
    rationale: |
      Instrumentation-only edit; no schema bump, no runtime behavior
      change. Trivial revert via git.
    verification_at_exit: |
      `cascade_key_null_audit` log event reports source_entity for every
      currently-cascaded field; no `unknown` entries in production logs.

  - name: phase-1b-provider-schema-extension
    goal: |
      Add the new field on the PROVIDER schema (e.g., `cf:Offer Status`
      on offer.py) WITHOUT yet adding the cascade consumer column.
    files:
      - src/autom8_asana/dataframes/schemas/offer.py:8-90
      - src/autom8_asana/dataframes/schemas/unit.py:8-74
      - src/autom8_asana/models/business/fields.py
    reversibility_cost: MED
    rationale: |
      Provider schema bump is forward-only at S3 cache key altitude.
      Reverting requires either cache key roll-forward or cold-start
      cache rebuild. HC-07 applies.
    verification_at_exit: |
      Provider entity dataframe contains the new cf: column; validator
      reports new column at WARN/ERROR thresholds within calibrated
      range; no warmup ordering errors.

  - name: phase-1c-consumer-cascade-declaration
    goal: |
      Add `source="cascade:Offer Status"` ColumnDef to consumer schemas
      (contact.py, process.py); register CascadingFieldDef with explicit
      target_types and allow_override.
    files:
      - src/autom8_asana/dataframes/schemas/contact.py:73-89
      - src/autom8_asana/dataframes/schemas/process.py:14-42
      - src/autom8_asana/models/business/fields.py
      - src/autom8_asana/dataframes/builders/cascade_validator.py:185-191
    reversibility_cost: MED
    rationale: |
      Consumer schema bump triggers HC-07 cache-key concern AND HC-09
      persistence-write contract. Revert requires schema-version
      rollback + cache key bump again.
    verification_at_exit: |
      validate_cascade_ordering passes at startup; warm_phases include
      new dep edge if applicable; consumer dataframe carries the new
      column with non-null rate within HC-02 thresholds; identity_
      complete-flag-equivalent test fixture passes for null cases.

  - name: phase-1d-vince-fixture-revalidation
    goal: |
      Re-run the Reactivation+Outreach inception-anchor fixture against
      the cascade-extended schemas; verify no regression on existing
      cascade columns; verify new column appears.
    files:
      - tests/integration/* (Vince fixture)
      - tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106
    reversibility_cost: LOW
    rationale: |
      Verification phase — no production code change. Failure → re-run
      phase-1c with corrected target_types or allow_override settings.
    verification_at_exit: |
      Vince inception-anchor fixture reproduces with new cascade column
      visible; SCAR-005/006 null-flag invariant intact (new column
      surfaces nulls explicitly, not silently dropped).

  - name: phase-2-deferred (NOT IN PATH A SCOPE)
    goal: NOT THIS ARTIFACT
    files: []
    reversibility_cost: N/A
    verification_at_exit: |
      Defer to spike-handoff verdict. Path A's per-field cost recurs at
      Phase 2 if Phase 2 commits to cascade altitude.
```

## §5 Risk Surface

```yaml
risks:
  - id: PA-R-01
    desc: |
      _CASCADE_SOURCE_MAP omission causes silent observability gap on
      newly-cascaded fields (HC-01).
    likelihood: HIGH
    likelihood_rationale: |
      The map is a hardcoded dict in the validator module. The schema
      authoring path does not import or reference it. Reviewers must
      catch the cross-file edit manually. PR drift is the default mode.
    impact: MED
    impact_rationale: |
      Production alarms keyed on `source_entity` will miss new fields;
      SCAR-005-class incidents on the new column will be detected late.
      Throughline impact: identity_complete flag transparency degrades
      silently for the new column.
    mitigation: |
      Phase 1a adds the entry as instrumentation-only edit BEFORE
      schema change. Add unit test asserting every cascade field in
      the registry has a _CASCADE_SOURCE_MAP entry.
    phase: 1
  - id: PA-R-02
    desc: |
      Cascade-null thresholds (5% WARN / 20% ERROR) calibrated against
      existing fields may not fit new fields' distribution (HC-02).
    likelihood: MED
    likelihood_rationale: |
      Thresholds calibrated against Office Phone/Vertical/MRR/etc.
      where structural null rate is low. New cascade like
      `offer.section` or `offer.status` may have structural nulls per
      lifecycle stage. Distribution shift is unmeasured.
    impact: HIGH
    impact_rationale: |
      Auto-error at startup blocks warm; cold-start cache rebuild
      stalls; entire dataframe service degrades to legacy-fallback.
    mitigation: |
      Phase 1a baseline measurement; per-field threshold override
      pathway (currently absent — requires cascade_validator extension)
      OR documented field selection criterion that excludes
      structurally-null fields from cascade altitude.
    phase: 1
  - id: PA-R-03
    desc: |
      Non-Business owner cascades fail silently due to ROOT-fallback
      hardcode (HC-04).
    likelihood: MED
    likelihood_rationale: |
      Existing cascade providers are Business + Unit. Adding cascades
      from Offer or Process as new providers — plausible Phase-2 scope
      — hits the EntityType.BUSINESS-only fallback branch.
    impact: MED
    impact_rationale: |
      Silent null at extract; appears as data-quality issue; difficult
      to root-cause because the resolver itself returns None without
      logging the scope-claim mismatch.
    mitigation: |
      Generalize ROOT-fallback to any cascading_field_provider entity,
      OR document the constraint and gate Path-A field selection to
      Business/Unit-owned cascades only.
    phase: 1
  - id: PA-R-04
    desc: |
      Schema version bump without S3 cache-key version coordination
      causes cold-start cache to read stale rows (HC-07).
    likelihood: MED
    likelihood_rationale: |
      Manual discipline; no automated cache-key invalidation tied to
      schema version. Has been hit before (SCAR-013 family) per
      .know/scar-tissue.md.
    impact: HIGH
    impact_rationale: |
      Stale rows lack new cascade column; downstream queries silently
      return null on the new field; identity_complete flag becomes
      meaningless for cached rows.
    mitigation: |
      PR-checklist item: "schema.version bump → confirm S3 cache-key
      bump or cache cold-flush plan." Automated check is out-of-scope
      for Path A.
    phase: 1
  - id: PA-R-05
    desc: |
      ADR-0054 allow_override=False default may silently overwrite
      descendant values on save cycle (HC-09).
    likelihood: LOW
    likelihood_rationale: |
      Save-cycle is rare in extract-only Vince flow; primary risk is
      Phase-2 if write-side surfaces the new field. Default is
      well-documented in fields.py L29-30, but mistakes are common
      enough that ADR-0054 explicitly flags this as DESIGN CONSTRAINT.
    impact: HIGH
    impact_rationale: |
      Silent data mutation across the entity hierarchy; not caught by
      validator (which only audits NULLs, not overwrites).
    mitigation: |
      Path-A schema authoring discipline: every new CascadingFieldDef
      explicitly sets allow_override; treat default as code smell;
      add lint check.
    phase: 2
```

## §6 Evidence Trail

| Claim | File:Line Citation | Grade |
|-------|-------------------|-------|
| `resolve_async` is field-agnostic; new fields don't change resolver code | `src/autom8_asana/dataframes/resolver/cascading.py:199-275` | STRONG |
| ROOT-fallback is EntityType.BUSINESS-only (HC-04) | `src/autom8_asana/dataframes/resolver/cascading.py:351` | STRONG |
| Extractor `_extract_column_async` routes cascade prefix to resolver, no edit needed | `src/autom8_asana/dataframes/extractors/base.py:321-325` | STRONG |
| Sync path raises ValueError on cascade source (preserved invariant) | `src/autom8_asana/dataframes/extractors/base.py:262-267` | STRONG |
| Validator derives cascade columns from schema dynamically | `src/autom8_asana/dataframes/builders/cascade_validator.py:85-86` | STRONG |
| `_CASCADE_SOURCE_MAP` is hardcoded; new fields require manual entry (HC-01) | `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` | STRONG |
| Null thresholds calibrated against SCAR-005 30% incident (HC-02) | `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32` | STRONG |
| `validate_cascade_ordering` is L1 startup check (HC-03) | `src/autom8_asana/dataframes/cascade_utils.py:281-328` | STRONG |
| `cascade_provider_field_mapping` derives mapping from schema columns | `src/autom8_asana/dataframes/cascade_utils.py:51-131` | STRONG |
| `cascade_warm_phases` topo-sorts from schema + registry; auto-detects new edges | `src/autom8_asana/dataframes/cascade_utils.py:134-225` | STRONG |
| Progressive preload invokes validator on entities with cascade fields | `src/autom8_asana/api/preload/progressive.py:472-503` | STRONG |
| WarmupOrderingError re-raise barrier preserves SCAR-005/006 invariant | `src/autom8_asana/api/preload/progressive.py:696-699` | STRONG |
| Cascade plugin uses STANDARD completeness (HC-06) | `src/autom8_asana/dataframes/views/cascade_view.py:359-363` | STRONG |
| ADR-0054 allow_override=False default (HC-09) | `src/autom8_asana/models/business/fields.py:26-30` | STRONG |
| Process schema is Vince inception-anchor target | `src/autom8_asana/dataframes/schemas/process.py:1-52` | STRONG |
| Existing cascade columns: office_phone, vertical, business_name, mrr, weekly_ad_spend | `src/autom8_asana/dataframes/builders/cascade_validator.py:186-190` | STRONG |
| Threshold-vs-distribution claim for new fields (PA-R-02) | self-attestation; calibration evidence not yet collected | MODERATE |
| Cache-key/schema-version coordination is manual discipline (HC-07) | absent automated check; inferred from .know/scar-tissue.md SCAR-013 family | MODERATE |
| Save-cycle mutation risk on default allow_override (PA-R-05) | derived from ADR-0054 fields.py:26-30 + persistence/* surface | MODERATE |
| Phase 1 timing fits 2026-05-11 telos deadline | inferred from frame.md telos.verified_realized_definition; not validated against sprint capacity | MODERATE |

### §6.1 Self-attestation grade ceiling

Per `self-ref-evidence-grade-rule`: this artifact's claims about Path A's
cost cap at MODERATE. STRONG appears only for file:line citations
verified live. The MODERATE claims (PA-R-02, HC-07, PA-R-05) are flagged
for S3 (prototype-engineer) empirical validation OR S5 (tech-transfer)
verdict reconciliation against S2b's Path B/C5 cartography.

### §6.2 Anti-pattern guard self-check

- §3 hidden coupling list contains 9 entries (≥3 threshold per CKP-S2).
- No verdict synthesis — §5 risks are surfaced costs, not recommendations.
- No comparative analysis — Path B/C5 not mentioned in body except
  out-of-scope phase-2-deferred placeholder.
- All file:line anchors verified against live source by Read tool prior
  to authorship.

---

*Authored by integration-researcher (Station S2a) under
`project-asana-pipeline-extraction` Phase 0 spike,
session-20260427-232025-634f0913. MODERATE self-attestation ceiling.
Verdict authority pinned at S5. Phase 2 non-foreclosure invariant
respected — this artifact maps Path A costs only; Path B + C5 mapped
in S2b parallel station.*
