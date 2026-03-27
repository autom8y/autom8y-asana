# Architect Agent Memory

## Resolution Subsystem Architecture

- `HierarchyTraversalStrategy._traverse_to_business_async()` uses `Business.model_validate()` as entity type discriminator -- this is WRONG because Pydantic `extra="allow"` means ANY task validates as Business
- The fix is to gate `model_validate` behind `detect_entity_type()` which uses `ProjectTypeRegistry` for O(1) project membership lookup
- `tasks.get_async()` (default, no opt_fields) uses `STANDARD_TASK_OPT_FIELDS` which includes `memberships.project.gid` -- so fetched tasks already have detection data available
- Detection system has bootstrap guard in `_detect_tier1_project_membership` that calls `register_all_models()` if needed
- Deferred imports inside methods (not module-level) are the standard pattern in strategies.py to avoid circular imports

## Entity Hierarchy Depths

- ContactHolder.parent IS Business (1 level to Business)
- Unit.parent is UnitHolder, UnitHolder.parent IS Business (2 levels to Business)
- Offer.parent is OfferHolder, OfferHolder.parent is Unit, Unit.parent is UnitHolder, UnitHolder.parent IS Business (4 levels to Business)
- Process follows similar pattern to Offer (4 levels via ProcessHolder -> Unit -> UnitHolder -> Business)

## Key Design Pattern: model_validate is NOT a Type Discriminator

- Pydantic model_validate with `extra="allow"` accepts any superset of required fields
- BusinessEntity and all subclasses have NO required discriminating fields
- Always use `detect_entity_type()` -> `ProjectTypeRegistry` for entity type identification
- This is a systemic issue: `DependencyShortcutStrategy._try_cast()` has the same vulnerability

## File Locations (Resolution)

- Resolution strategies: `src/autom8_asana/resolution/strategies.py`
- Resolution context: `src/autom8_asana/resolution/context.py`
- Detection system: `src/autom8_asana/models/business/detection/`
- Entity registry: `src/autom8_asana/models/business/registry.py`
- Bootstrap: `src/autom8_asana/models/business/_bootstrap.py`
- Spike: `docs/spikes/SPIKE-resolution-traversal-design.md`

## API Surface Architecture

- Auth boundary: S2S-only (`require_service_claims`) vs dual-mode (`AsanaClientDualMode`) is intentional security design, NOT accidental divergence
- Query router S2S restriction prevents privilege escalation: DataFrame cache built from bot PAT may contain data exceeding individual PAT permissions
- Section-timelines already accepts JWT through dual-mode chain -- no auth change needed for S2S consumers
- URL prefix split: `/v1/{verb}/` (internal S2S) vs `/api/v1/{resource}/` (gateway-fronted) -- do not unify
- `SectionClassifier.sections_for()` exists but is disconnected from both query engine and timeline endpoint
- Query engine `section` param filters by single name, NOT by classification group -- classification sugar needed
- Derived timeline cache: single entry per (project_gid, classifier_name), 5min TTL -- filter post-cache, do NOT create per-classification keys
- Analysis: `.claude/wip/ANALYSIS-classification-api-surface.md`

## File Locations (API Surface)

- Query router: `src/autom8_asana/api/routes/query.py`
- Section-timelines: `src/autom8_asana/api/routes/section_timelines.py`
- Auth dependencies: `src/autom8_asana/api/dependencies.py`
- S2S auth guard: `src/autom8_asana/api/routes/internal.py` (require_service_claims)
- Dual-mode detection: `src/autom8_asana/auth/dual_mode.py`
- Classifiers: `src/autom8_asana/models/business/activity.py` (CLASSIFIERS dict, line 264)
- Timeline service: `src/autom8_asana/services/section_timeline_service.py`
- Query engine: `src/autom8_asana/query/engine.py`
- Derived cache: `src/autom8_asana/cache/integration/derived.py`

## N8N-CASCADE-INTEGRITY Initiative (2026-03-03)

### Key Architectural Finding: Cache Population Lacks Cascade Invariant

- 6 paths populate DataFrame cache; only 1 (progressive builder) runs cascade validation
- Fast-path (S3 parquet load), legacy preload, SWR refresh, admin rebuild, and @dataframe_cache decorator all bypass cascade
- Lambda cache_warmer processes "unit" BEFORE "business" -- opposite of cascade dependency ordering
- SWR and admin rebuild create per-client UnifiedTaskStore that lacks cross-project Business data
- CascadeViewPlugin._detect_entity_type_from_dict uses weak 2-heuristic (parent=None -> Business, else UNKNOWN); proper 4-tier detection at facade.py -- weak heuristic is LOW risk, only affects runtime, not preload
- Pydantic extra="ignore" audit: EntityWriteRequest, WorkflowInvokeRequest, CacheRefreshRequest all missing extra="forbid"
- Frame: `.claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md` (includes first-principles reframe)
- 8 workstreams total (5 original + 3 new: Lambda ordering, parquet provenance, SWR/admin cross-entity cascade)

## Cascade Warming API Path (2026-03-25)

- [Cascade Warming Design](project_cascade_warming_api_path.md) -- TDD for warming cascade store on DataFrame API endpoint

## Project Omniscience Sprint 4 (2026-03-27)

- [Sprint 4 ADRs](project_omniscience_sprint4_adrs.md) -- Registry unification (TENSION-013) + descriptor-driven resolver (TENSION-016)

## Project Omniscience Sprint 8 (2026-03-27)

- [Sprint 8 Lifecycle Observation](project_omniscience_sprint8_lifecycle_observation.md) -- StageTransitionRecord, MetricExpr median/quantile, GAP-03 webhook dispatcher, LoopDetector

## Project Omniscience Sprint 11 (2026-03-27)

- [Sprint 11 Semantic Introspection](project_omniscience_sprint11_semantic_introspection.md) -- YAML-in-description enrichment, centralized annotation registry, endpoint enhancements, contract tests

## Project Omniscience Sprint 12 (2026-03-27)

- [Sprint 12 Composite Reasoning](project_omniscience_sprint12_composite_reasoning.md) -- Composition over monolith: agents orchestrate existing endpoints via GID-set passing, no new composite endpoints
