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

## Say-able predicate under the refusing verdict axis — S1 (2026-08-12)

- [Say-able Predicate](project_sayable_predicate_refusing_axis.md) -- CLOSED at rev-5: ONE say-able readout (1a via `/rows`); 2 and 5a both withdrawn on imputation defects; G4' branch-enumeration; method-finding = only a second reader catches this class

## Option-4 verification-axis gate — ADR-007 (2026-08-12)

- [ADR-007 Verification Axis Gate](project_option4_verification_axis_gate_adr.md) -- founding ADR draft; P-5's min()-over-all-classified supersedes the annex's rows-present reduction (pass rate is set by stamp eligibility, not warm cadence); two ratification-pending blocks; the autom8y-checkout-is-not-origin/main hazard

## Option-4 verification-recency axis (2026-08-12)

- [Option 4 Verification Axis](project_option4_verification_axis.md) -- design annex for the operator interview: content axis is measurement-dead (0/175); verification recency relocates the gate quantity into the platform's own control loop; `max()` shields / `min()` exposes; five inherited premises corrected on direct read

## Offers freshness-axis contract (2026-08-11)

- [Offers Freshness Axis Contract](project_offers_freshness_axis_contract.md) -- S1-ARCH v2 + S2-0 FROZEN contract: 2.25x is axis conflation; ceiling knob inert; content watermark derivable CONSUMER-side in the SDK (no P6 door); never alias v1/v2 tokens; W2-F1b AXIS-ABSENT double-referent UNRESOLVED (K limbs blocked)

## Floor-locus ENDSTATE adjudication (2026-08-12)

- [Floor Locus Endstate](project_floor_locus_endstate.md) -- three divergent value-column floors ALREADY exist; FM-5 ARM-B is the ratified per-consumer contract with `population_expectation` declared-but-inert; A6 falsified at Seam 4 / true at the query One-Gate; `_VALUE_COLUMNS` narrowing = digest-scheme version event (pre-refused)

## Insight-delivery S2 residue triage (2026-08-12)

- [Insight-Delivery S2 Residues](project_insight_delivery_s2_residues.md) -- seven ASR-brief residues dispositioned; the 100-campaign cap (monorepo/ADS) and the 1000-row cap (asana/offers) must never merge; item-4 residual is the missing LEADING indicator only; FP-1's "unconditionally" is false on direct read

## REC-002(b) arm-the-instrument (2026-08-14)

- [REC-002 ASR Content Hash](project_rec002_asr_content_hash.md) -- the tautology trap (recompute, never thread), three `_safe_slack_post` call sites not one, and H-1: `bool("false")` sinks E2 on any Logs-Insights-projection ingestion

## S-15 Domain-B design — EBI email intake (2026-08-18)

- [S-15 Domain-B Design](project_s15_domainb_design.md) -- OR-4 corroboration can't see a wrong booking (extracted value IS the join key); extractor temperature UNSET at default 1.0; primary fixture 7-of-13 fields on a doc-example boundary; "two real captures swept" is N=1 and both were form-data not `.eml`

## S-09 email-intake-cutover disposition slate (2026-08-23)

- [S-09 Cutover Disposition Slate + RULING](project_s09_cutover_disposition_slate.md) -- PR autom8y#1696; RULED "D-B ⊗ W-2 then W-3"; **`ari agora telos` is armed but READ-ONLY** (measured, never recorded); the effective-at-instant zero-act record construction

## provably-landed S-01 doctrine-law card (2026-08-23)

- [Provably-Landed Doctrine Card](project_provably_landed_doctrine_card.md) -- the five WAVE-1 doctrines (D-1..D-5) with origin/main anchors + BITEs, autom8y PR #1697; frame naming line and the HTTP-200 mint locus are both UNLANDED

## Working conventions

- [Commit Attribution Guard](feedback_commit_attribution_guard.md) -- NO AI co-author trailer in a8 commits; the guard is harness-level so git-hook probes cannot detect it

## S-13 monolith COV-0 charter-prep (2026-08-23)

- [S-13 Monolith COV-0 Charter-Prep](project_s13_monolith_cov0_charter_prep.md) -- autom8y PR #1699; receipt (iii) BLOCKED at OWN-08 (packet is the ceiling); the RETRO is UNTRACKED; BLOCKER-2 = off-disk Heroku writer falsifies "WS-1 Dependencies: none"; the RETRO's analysis held, its decomposition did not

## Substrate-v2 Epoch S1 whole-design (2026-07-27)

- [Substrate-v2 S1 Design](project_substrate_v2_epoch_s1_design.md) -- S1 FINALIZED (all 3 phases): adversary PASS-WITH-CONDITIONS, 5 seams FROZEN, C1-C11 dispositioned, 3 packets staged (DP-2/DP-3 await operator, DP-1F ratified); RC-A..F as constructions
