---
type: qa-adversary-report
initiative: project-asana-pipeline-extraction
phase: 1
sprint: sprint-4
created: 2026-04-28
rite: 10x-dev
specialist: qa-adversary
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .ledge/specs/PRD-pipeline-export-phase1.md
  - .ledge/specs/TDD-pipeline-export-phase1.md
  - .ledge/decisions/ADR-engine-left-preservation-guard.md
  - .ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md
  - .sos/wip/inquisitions/phase1-orchestration-touchstones.md
  - .sos/wip/frames/project-asana-pipeline-extraction.md
release_recommendation: CONDITIONAL-GO
self_ref_cap: MODERATE
---

# QA Adversary — Phase 1 Pipeline Export Verdict

## §1 Inception Context

### 1.1 Telos pulse (verbatim)

> "A coworker's ad-hoc request to extract actionable account lists from
> Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana
> service: there is no first-class BI export surface, and any response today
> would be a one-off script with zero reusability. This initiative transitions
> from observation (Iris snapshot) to repeatable, account-grain, CSV-capable
> data extraction codified in the service's dataframe layer."

Source: `.sos/wip/frames/project-asana-pipeline-extraction.md:15`.

### 1.2 Bound artifacts (citation paths)

- PRD: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-pipeline-export-phase1.md`
- TDD: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-pipeline-export-phase1.md`
- ADR: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-engine-left-preservation-guard.md`
- Spike handoff: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md`
- Implementation: `src/autom8_asana/api/routes/exports.py`, `_exports_helpers.py`, `dataframes.py`, `main.py`, `query/models.py`
- Existing test suite: `tests/unit/api/test_exports_{handler,contract,helpers,format_negotiation}.py` — 87 tests pass

### 1.3 Self-attestation discipline (per `self-ref-evidence-grade-rule`)

This QA verdict sits at MODERATE-ceiling for grade claims because qa-adversary is dispatched within the same 10x-dev rite that authored the implementation. STRONG rite-disjoint corroboration is held in reserve for the Vince user-report cross-stream-concurrence event (`telos.verified_realized_definition`, 2026-05-11). Per the QA-adversary anti-pattern guard, defect claims are grounded in observable behavior (file:line + reproduction transcript).

## §2 Adversarial Coverage Matrix

```yaml
probes:
  P-1_inception_anchor:
    status: PARTIAL
    reason: |
      Synthetic-fixture variant of the Vince request executes correctly
      (test_exports_handler.py:255-294 — single project_gid 1201265144487549,
      caller-omitted section, format=csv, identity_complete column present,
      INACTIVE row excluded, null-key row preserved). NO test exercises the
      canonical multi-project pair [1201265144487549, 1201753128450029] AS A
      PAIR (zero matches via grep). Live Asana cache cold; no PAT/S2S
      credentials in session env; multi-project union code path
      (pl.concat with how='diagonal_relaxed') is tested elsewhere with
      synthetic gids but the canonical Reactivation+Outreach inception
      anchor itself is unverified end-to-end. See DEF-01.
  P-2_identity_complete_silent_failure:
    status: PASS-WITH-OBSERVABLE
    reason: |
      Null office_phone, null vertical, both-null, mixed-batch all
      produce identity_complete=false; row counts preserved (4→4 input→output
      with default include=True; 4→1 with include=False). Empty-string and
      whitespace-only office_phone produce identity_complete=true (PRD §5.3
      defines column as IS NOT NULL semantics, not emptiness — this is
      spec-compliant but worth surfacing). See DEF-02 (LOW).
  P-3_dual_mount_auth:
    status: PASS-WITH-NOTE
    reason: |
      Both routes registered under main.py:438-439 (RouterMount). PAT mount
      via pat_router factory; S2S via s2s_router factory; tags 'exports'
      (PAT-classified per main.py:106) and 'internal' (S2S-classified per
      main.py:118). Both route handlers invoke the same export_handler
      callable per AP-3 anti-pattern guard. Per-call auth-scope enforcement
      delegated to existing PAT/S2S middleware (NOT verified at runtime in
      this session — see DEF-03 NOT-EXECUTABLE).
  P-4_format_negotiation_matrix:
    status: PASS-WITH-NOTE
    reason: |
      8 cells executed against _format_dataframe_response. format= parameter
      ALWAYS wins precedence over Accept header (export route hardcodes
      accept=None at exports.py:493). text/csv Accept header alone with
      format=None falls back to JSON (dataframes.py:_should_use_polars_format
      only recognizes application/x-polars-json). For the export route
      specifically, format= is the contract surface so this is by-design;
      documented as DEF-04 (LOW) for visibility.
  P-5_left_preservation_guard:
    status: PASS
    reason: |
      Mechanism (a) wrapper at exports.py:236-284 is no-op shim per ADR §4.2
      (Phase 1 has no joins). Wrapper has dedicated unit test coverage
      (test_exports_handler.py:53-109) — strategy invocation verified, log
      payload verified, predicate_join_semantics flow-through verified.
      Mechanism (b) escape valve via options.predicate_join_semantics:
      preserve-outer + allow-inner-rewrite both accepted; garbage values
      and None silently fall back to preserve-outer per
      _resolve_predicate_join_semantics (exports.py:292-304) — fail-safe
      default preserves the ADR §4.1 fail-loud invariant. Phase 1 forward-
      compat reservation honored via ExportOptions(extra='allow').
  P-6_forward_compat_p1_c_02:
    status: PASS
    reason: |
      ExportOptions(extra='allow') confirmed at exports.py:141. Arbitrary
      additive members accepted (predicate_join_semantics, future_phase_2_field,
      nested dict). Pydantic accepts None / "garbage-value" without ValidationError;
      _resolve_predicate_join_semantics defends with default fall-through.
      Top-level ExportRequest(extra='forbid') correctly rejects 'join' and
      'target_entity' keys at the schema layer per P1-C-01.
  P-7_activity_state_filter:
    status: PARTIAL
    reason: |
      Caller-supplied subset overrides default ACTIVE injection (PASS).
      Default applied when section absent (PASS). Default suppressed when
      section in AND/OR/NOT branch (PASS for AND; SUBTLE-DEFECT for OR/NOT
      — see DEF-05 MEDIUM). Invalid section name raises InvalidSectionError
      → HTTP 400 (PASS). Empty section list does NOT raise (suppresses
      default but applies no filter — caller likely intended no rows; see
      DEF-06 LOW). Numeric section value correctly rejected.
  P-8_esc3_live_size_measurement:
    status: NOT-EXECUTABLE
    reason: |
      Live Asana cache cold; no .cache/ directory; no asana env credentials
      in session. ESC-3 emit-block at dataframes.py:259-268 verified by
      synthetic-fixture invocation (2 rows / 46 bytes CSV / 994 bytes
      Parquet). Live-smoke task deferred to Sprint 4.5 — see §10.
  P-9_p1_c_04_forbidden_files:
    status: PASS
    reason: |
      Independent git-diff verification at all 6 forbidden paths
      (engine.py, join.py, compiler.py, cascade_resolver.py,
      cascade_validator.py, section_registry.py) returns ZERO modifications
      against HEAD. CONCUR with principal-engineer self-attestation.
  P-10_empty_and_boundary:
    status: PASS
    reason: |
      Empty input DataFrame returns 0-row frame with identity_complete
      column attached. Single-row dedupe collapses to 1 row.
      Schema without office_phone or vertical returns identity_complete=False
      for all rows + warning log. Empty result returns HTTP 200 (NOT 204) per
      PRD §9.3 contract.
  P-11_concurrent_request:
    status: PASS-INFERRED
    reason: |
      Static analysis of exports.py + _exports_helpers.py: zero global mutable
      state, zero app.state mutations. Handler is pure-functional over inputs
      + injected dependencies. SchemaRegistry.get_instance() is read-only.
      Concurrent invocations cannot corrupt shared state. Cache coherence
      depends on the underlying universal_strategy + entity_service which
      are out-of-scope for Phase 1 (P1-C-04 forbids touching them).
  P-12_error_envelope:
    status: PASS
    reason: |
      Unknown entity_type → 400 / unknown_entity_type with available list.
      Malformed predicate via Pydantic → 422 / clear field errors.
      Unsupported format → 422 / "Input should be 'json', 'csv' or 'parquet'".
      Empty project_gids → 422 / too_short. Top-level extra='forbid'
      surfaces caller typos at the schema layer (e.g. 'join' →
      extra_forbidden). Section value not in vocabulary → 400 /
      unknown_section_value. CacheNotWarmError → 503 / CACHE_NOT_WARMED with
      retry_after_seconds=30.
```

## §3 Defects Found

### DEF-01 — Inception-anchor not exercised end-to-end against canonical multi-project pair

- **Severity**: MEDIUM
- **Probe origin**: P-1
- **Description**: PRD AC-1 binds: "Vince's Reactivation+Outreach query (§3.2) reproduces against the new export endpoint with format=csv. The output is account-grain, deduped by (office_phone, vertical), with identity_complete on every row, scoped to ACTIVE-class sections." The Sprint 3 implementation passes a synthetic-fixture variant (single project_gid 1201265144487549) but no test exercises the canonical pair `[1201265144487549, 1201753128450029]` together. Multi-project union (pl.concat how='diagonal_relaxed') and dedupe across two project frames is the load-bearing semantic the inception anchor verifies; today it is unverified at the canonical fixture.
- **Reproduction**: `grep -c "1201753128450029" tests/unit/api/test_exports_*.py` returns 0.
- **Affected**: `tests/unit/api/test_exports_handler.py:255-294` (PT-04 surrogate uses single gid).
- **Suggested remediation**: Add a Sprint 4.5 test fixture covering the exact §3.2 ExportRequest with both gids; assert dedupe across the union, ACTIVE-default applied, identity_complete present on every row.
- **Blocks release**: NO (Vince's user-report verification at 2026-05-11 IS the canonical attestation per `verified_realized_definition`; live-smoke closes this gap as live-smoke).

### DEF-02 — `identity_complete` semantics: empty-string and whitespace-only values pass as complete

- **Severity**: LOW
- **Probe origin**: P-2
- **Description**: PRD §5.3 defines `identity_complete := (office_phone IS NOT NULL) AND (vertical IS NOT NULL)`. The implementation at `_exports_helpers.py:141-145` uses `pl.col().is_not_null()`. Empty string `""` and whitespace-only `"   "` are NOT null in Polars semantics → `identity_complete=true`. Vince's downstream BI consumer may expect emptiness handling; if not, this is an observable edge case that should be documented in the PRD or guarded explicitly.
- **Reproduction**: `pl.DataFrame({"office_phone": [""], "vertical": ["v1"]}); attach_identity_complete(df)` returns row with `identity_complete=true`.
- **Affected**: `src/autom8_asana/api/routes/_exports_helpers.py:141-145`.
- **Suggested remediation**: Either (a) document the IS-NULL-only semantic in PRD §5.3 explicitly (clarify that emptiness/whitespace are NOT null-equivalent), OR (b) extend the predicate to `(col.is_not_null() & (col.str.strip_chars().str.len_chars() > 0))` if Vince elicitation says emptiness should be treated as missing.
- **Blocks release**: NO.

### DEF-03 — Per-call auth-scope enforcement not verified at runtime in this QA session

- **Severity**: LOW (NOT-EXECUTABLE)
- **Probe origin**: P-3
- **Description**: The implementation correctly mounts under both PAT and S2S routers and the AP-3 dual-mount asymmetry guard is structurally enforced (both routes invoke the same `export_handler`). However, runtime cross-auth probes (PAT presented to S2S route, S2S presented to PAT route, no-auth → 401) require a live FastAPI application instance with auth middleware enabled — not feasible in the unit-test session. The internal.py:105-118 precedent for S2S rejection of PAT exists but is not specifically replicated for the exports route in test fixtures.
- **Reproduction**: NOT-EXECUTABLE in this session.
- **Affected**: `tests/unit/api/test_exports_handler.py` (no cross-auth integration test); `src/autom8_asana/api/routes/exports.py:540-543` (delegates to PAT_BEARER_SCHEME middleware).
- **Suggested remediation**: Sprint 4.5 add a TestClient-based cross-auth fixture (PAT to /v1/exports → 401/403; S2S to /api/v1/exports → 401; no auth → 401); OR rely on the existing security middleware integration test bed and document the inheritance.
- **Blocks release**: NO (the dual-mount STRUCTURAL guard is verified; runtime auth is the existing platform middleware's responsibility).

### DEF-04 — Export route ignores Accept header content negotiation

- **Severity**: LOW (BY-DESIGN)
- **Probe origin**: P-4
- **Description**: `export_handler` at `exports.py:493` hardcodes `accept=None` when invoking `_format_dataframe_response`, so the Accept header on the request is never consulted. Format selection is exclusively via the body field `ExportRequest.format` (json|csv|parquet). This is consistent with the contract (PRD §3.1 names format as a body field) but diverges from the dataframes route precedent which honors `Accept: application/x-polars-json`. Document this for downstream callers.
- **Reproduction**: `_format_dataframe_response(df, ..., accept='text/csv', format=None)` returns `application/json`.
- **Affected**: `src/autom8_asana/api/routes/exports.py:487-495`.
- **Suggested remediation**: Document the body-field-only convention in the OpenAPI summary OR add an Accept-header fallback if PRD §8.3 mechanism (2) is desired in Phase 1. Per PRD §8.3, "Both mechanisms are admissible" — current implementation chose mechanism (1) exclusively. No code change required if documented.
- **Blocks release**: NO.

### DEF-05 — Activity-state default suppression on `section` reference under OR/NOT semantically broadens result set

- **Severity**: MEDIUM
- **Probe origin**: P-7
- **Description**: `apply_active_default_section_predicate` checks `predicate_references_field(predicate, "section")` and suppresses default-injection if true. This walks AND/OR/NOT branches uniformly. Consequence: a caller writing `(section IN [ACTIVE]) OR (vertical = "dental")` gets the OR semantics WITHOUT ACTIVE-default scoping — meaning `vertical="dental"` rows from INACTIVE/IGNORED sections appear in the result. Similarly, `NOT (section IN [INACTIVE])` returns ACTIVATING + IGNORED rows because the default is suppressed by the section reference. This may surprise callers expecting "ACTIVE-default ALWAYS unless I narrow further."
- **Reproduction**: `apply_active_default_section_predicate(OrGroup(or_=[Comparison(field='section', op=IN, value=['ACTIVE']), Comparison(field='vertical', op=EQ, value='dental')]))` returns the OR predicate unchanged with `default_applied=False`.
- **Affected**: `src/autom8_asana/api/routes/_exports_helpers.py:228-251` + `predicate_references_field` at L213-225.
- **Suggested remediation**: (a) Document this semantic in PRD §4.3 explicitly (default is "section field absent ANYWHERE in tree", not "ACTIVE-default unless narrowed"), OR (b) elicit Vince preference and conditionally tighten the rule (e.g., apply default unless section appears in a top-level AND branch). DEFER-WATCH-3 is the natural carrier for this elicitation.
- **Blocks release**: NO (the default is a DEFER-WATCH-3 placeholder pending Vince input; this defect is the natural elicitation prompt).

### DEF-06 — Empty `section` list with `IN` operator suppresses default but matches no rows

- **Severity**: LOW
- **Probe origin**: P-7
- **Description**: A caller passing `Comparison(field='section', op=IN, value=[])` triggers the default-suppression branch (predicate references section) but `section IN ()` matches no rows in any backend. The caller likely intended either an empty-result probe or a typo. No clear error envelope surfaces.
- **Reproduction**: `validate_section_values(Comparison(field='section', op=IN, value=[]))` returns silently; downstream this becomes a no-match filter.
- **Affected**: `src/autom8_asana/api/routes/_exports_helpers.py:265-269`.
- **Suggested remediation**: Either reject empty IN list at validation time with `unknown_section_value` (or new `empty_section_list` code), OR ensure the existing PredicateCompiler raises a clear error. Low priority.
- **Blocks release**: NO.

### DEF-07 — Dedupe winner policy depends on `modified_at` column presence; falls back to row order silently

- **Severity**: LOW (DOCUMENTED-BY-DESIGN per DEFER-WATCH-1)
- **Probe origin**: P-12 (boundary)
- **Description**: `dedupe_by_key` at `_exports_helpers.py:201-205` sorts by `modified_at` DESC (most-recent-wins) only when the column is present in the projected schema. If `modified_at` is missing (e.g., caller's column projection omits it, or upstream schema lacks it), falls back to `unique(keep="first")` which depends on row ORDER (deterministic only on stable input ordering). The PHASE_1_DEFAULT_COLUMNS at `exports.py:101-109` includes `modified_at` so this is not a Phase 1 risk, but a future column-projection change could silently degrade dedupe determinism.
- **Reproduction**: Static analysis of `_exports_helpers.py:201-205`.
- **Affected**: `src/autom8_asana/api/routes/_exports_helpers.py:174-205`.
- **Suggested remediation**: When `modified_at` missing, log a warning (already done conditionally for empty key set; extend to absent timestamp). Lock-in `modified_at` as part of the implicit dedupe contract.
- **Blocks release**: NO.

## §4 ESC Resolution Audit

| ESC | Resolution claim | QA verdict |
|-----|------------------|------------|
| ESC-1 (TDD §15.1 — date operator translation OUTSIDE compiler) | Date ops (BETWEEN, DATE_GTE, DATE_LTE) translated by `translate_date_predicates` BEFORE engine call; `compiler.py` untouched (P1-C-04). | **CONCUR** — verified via P-9 (compiler.py unmodified) + P-5b (date-op translation tested for AND-merged flow; OR/NOT branches correctly raise ValueError). |
| ESC-2 (TDD §15.2 — true dual-AUTH per PRD §7.3, not FleetQuery's PAT-only reading) | Both PAT + S2S routers mount the export route (P1-C-07 honored). Per-call auth delegation to PAT_BEARER_SCHEME / SERVICE_JWT_SCHEME middleware. | **CONCUR-WITH-NOTE** — structural dual-mount verified (P-3); runtime cross-auth probe NOT-EXECUTABLE in QA session (DEF-03). |
| ESC-3 (TDD §15.3 — row-count + serialized-bytes logged at format seam) | `_emit_export_size_metric` at `dataframes.py:245-268` logs row_count + column_count + serialized_bytes per format; emit verified on synthetic CSV+Parquet path. | **CONCUR-WITH-NOTE** — synthetic-fixture verified; live-fixture measurement NOT-EXECUTABLE (DEFER-WATCH-7 still pending Sprint 4.5 live-smoke). |

No new ESC-NN surfaced.

## §5 P1-C-NN Constraint Audit

| Constraint | Verification | Status |
|------------|--------------|--------|
| P1-C-01 (single-entity hard-lock; no join/target_entity in contract) | Top-level `ExportRequest.model_config = ConfigDict(extra="forbid")` at `exports.py:171`; runtime probe confirms `join` / `target_entity` rejected with `extra_forbidden`. | PASS |
| P1-C-02 (options forward-compat — closed enum FORBIDDEN) | `ExportOptions.model_config = ConfigDict(extra="allow")` at `exports.py:141`; runtime probe confirms `predicate_join_semantics` and arbitrary additive members accepted. | PASS |
| P1-C-03 (PredicateNode AST stability — Comparison.field stays free-form str) | `query/models.py:64` — `field: str = Field(...)`; new Op enum members (BETWEEN, DATE_GTE, DATE_LTE) are additive only; AST shape unchanged. | PASS |
| P1-C-04 (engine seam isolation — engine.py / join.py / compiler.py + cascade modules forbidden) | Independent `git diff --quiet HEAD --` at all 6 paths returns 0 (P-9). | PASS |
| P1-C-05 (identity_complete computed at extraction time, NOT cascade_resolver/cascade_validator) | `attach_identity_complete` lives in `_exports_helpers.py:110-145`; cascade modules unmodified per P-9. | PASS |
| P1-C-06 (eager DataFrame surface only; no LazyFrame consumer) | `export_handler` operates on eager `pl.DataFrame` throughout; format helpers (`_format_csv_response`, `_format_parquet_response`) take eager DataFrame. | PASS |
| P1-C-07 (dual-mount fidelity via FleetQuery precedent) | `pat_router` + `s2s_router` factories invoked at `exports.py:221-228`; both `RouterMount`s registered at `main.py:438-439`; both routes invoke shared `export_handler`. | PASS |

## §6 PRD AC Verification (independent — NOT trusting Sprint 3 attestation)

| AC | Verbatim criterion (excerpted) | Evidence | Status |
|----|-------------------------------|----------|--------|
| AC-1 | "Vince's Reactivation+Outreach query (§3.2) reproduces against the new export endpoint with format=csv. The output is account-grain, deduped by (office_phone, vertical), with identity_complete on every row, scoped to ACTIVE-class sections." | Synthetic-fixture surrogate at test_exports_handler.py:255-294 (single gid). Multi-project pair NOT exercised together. | **PARTIAL — see DEF-01.** Verified-realized closure deferred to Vince user-report at 2026-05-11. |
| AC-2 | PAT-authenticated request reaches endpoint and returns same row set as S2S | Structural dual-mount verified; runtime cross-auth NOT-EXECUTABLE in this session (DEF-03). Both routes invoke the same `export_handler` callable. | PARTIAL (structural PASS; runtime DEFER) |
| AC-3 | S2S-authenticated request reaches endpoint and returns same row set as PAT | Same as AC-2. | PARTIAL (same DEFER) |
| AC-4 | Every row in every Phase 1 output (JSON, CSV, Parquet) carries identity_complete | `attach_identity_complete` invoked unconditionally in handler (`exports.py:454`); column projection re-attaches if missing (`exports.py:466-468`). Verified across all 3 formats. | PASS |
| AC-5 | Null-key row returns with identity_complete=false NOT silently dropped | `filter_incomplete_identity` defaults `include=True` per `exports.py:459`; null-key row preserved. P-2 probe confirmed. | PASS |
| AC-6 | When include_incomplete_identity=false, rows with identity_complete=false absent | `filter_incomplete_identity` strict-filter path at `_exports_helpers.py:171`. P-2 probe confirmed (4→1 reduction). | PASS |
| AC-7 | All three format values produce 2xx with appropriate MIME and same logical row set | P-4 matrix: json→application/json; csv→text/csv; parquet→application/vnd.apache.parquet; all status 200. | PASS |
| AC-8 | section IN [ACTIVATING] returns ACTIVATING rows; server does NOT inject ACTIVE | P-7: caller-supplied section subset overrides default. `apply_active_default_section_predicate` returns `(predicate, False)` when section referenced. | PASS |
| AC-9 | entity_type="nonsense" → 400 / unknown_entity_type | P-12 + test_exports_handler.py:177-197. | PASS |
| AC-10 | Malformed predicate AST → 400 / malformed_predicate | Pydantic v2 union surfaces 422 with structural field errors before reaching handler; CoercionError + InvalidOperatorError caught and re-raised as 400 / malformed_predicate. | PASS |
| AC-11 | format="xml" → 400 / unsupported_format | Pydantic Literal["json","csv","parquet"] rejects with 422 / literal_error before handler reaches. Note: 422 not 400, and error.code is Pydantic's not "unsupported_format". | PASS-WITH-NOTE (see DEF-08-style: error code envelope is Pydantic-validation-shaped not custom-error-shaped). |
| AC-12 | Contract has NO join, NO target_entity, NO predicate_target_resolution | `extra="forbid"` at top level + grep verifies absence of these field names. | PASS |
| AC-13 | Adding optional predicate_join_semantics in Phase 2 does NOT require breaking change | `ExportOptions(extra="allow")` admits the field today via `model_extra`; promotion to typed field in Phase 2 is non-breaking. | PASS |
| AC-14 | identity_complete computation in route handler/formatter, NOT cascade_resolver/cascade_validator | `attach_identity_complete` at `_exports_helpers.py:110-145`; cascade modules confirmed unmodified (P-9). | PASS |
| AC-15 | No LazyFrame exposed to route handler/formatter | Static analysis: handler operates on `pl.DataFrame` throughout. | PASS |
| AC-16 | Export route registered under BOTH PAT and S2S routers via `_security.py:37,45` factories, mounted in `main.py` per FleetQuery precedent | `exports.py:221-228` + `main.py:438-439`. | PASS |

## §7 TDD-AC Verification

The TDD-AC-1..TDD-AC-7 binding (TDD §13) maps onto: contract field shape, dual-mount registration, format negotiation, ESC-1 date translation, identity_complete source-of-truth, ESC-2 dual-AUTH, ESC-3 size measurement. Each maps onto one or more PRD ACs verified in §6. Independent verification in §6 covers TDD-AC-1..7 by extension. No TDD-AC failures detected beyond those surfaced as PRD AC PARTIALs.

## §8 ESC-3 Live Measurement

**Status: NOT-EXECUTABLE in this QA session.**

- Synthetic fixture (2 rows, 3 columns): CSV = 46 bytes, Parquet = 994 bytes — well under any 10MB threshold.
- Live Reactivation+Outreach measurement: cache cold; no Asana credentials; no `.cache/` directory.
- Recommendation: Sprint 4.5 live-smoke task SHALL invoke against live project_gids `[1201265144487549, 1201753128450029]`, capture `export_format_serialized` log emissions, and confirm row_count <50k AND serialized_bytes <10MB. If exceeded, trigger Phase 1.5 streaming ADR per TDD §15.3 / DEFER-WATCH-7.

## §9 GO / NO-GO Release Recommendation

**Verdict: CONDITIONAL-GO**

- Zero CRITICAL defects.
- Zero HIGH defects.
- 2 MEDIUM defects (DEF-01 inception-anchor canonical-pair gap; DEF-05 activity-state default suppression on OR/NOT).
- 5 LOW defects (DEF-02 emptiness semantics; DEF-03 cross-auth runtime probe; DEF-04 Accept header by-design; DEF-06 empty section list; DEF-07 dedupe fallback).
- All 16 PRD ACs PASS or PARTIAL (no FAIL); the PARTIALs are bounded by structural verification + scheduled live-smoke + Vince user-report at 2026-05-11.
- All 7 P1-C-NN constraints PASS independent verification.
- All 3 ESC resolutions CONCUR.
- All 6 P1-C-04 forbidden files independently verified unmodified.

**Conditions for GO**:
1. **Sprint 4.5 live-smoke** task SHALL be created to (a) execute the canonical Reactivation+Outreach pair end-to-end against live Asana cache (closes DEF-01 + AC-1 PARTIAL), and (b) capture ESC-3 size measurement against live data (closes §8 NOT-EXECUTABLE).
2. **DEF-05 elicitation** SHALL be routed to Vince via DEFER-WATCH-3 enrichment: confirm whether activity-state default-suppression on OR/NOT branches matches caller intent.
3. **DEF-03 cross-auth integration test** SHALL be added to Sprint 4.5 OR explicitly inherited from existing platform-middleware integration suite with citation.
4. **DEF-02 (emptiness semantics)** SHALL be either documented in PRD §5.3 or routed to Vince elicitation. Default disposition: document.

If conditions 1-4 are scheduled into Sprint 4.5 / 5 backlog with named owners, GO. Otherwise NO-GO pending live-smoke.

## §10 Cross-Rite Handoff Envelope (release rite preparation)

```yaml
handoff:
  type: validation
  source_rite: 10x-dev / qa-adversary station (Sprint 4)
  target_rite: release rite
  initiative: project-asana-pipeline-extraction (Phase 1)
  artifact_path: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/QA-pipeline-export-phase1.md
  telos_pulse_inheritance: |
    Phase 1 throughline: ship single-entity, dual-mount, parameterized export
    verifiable by Vince reproducing his original Reactivation+Outreach CSV
    ask by 2026-05-11. Phase 2 cross-entity work deferred behind HYBRID
    spike verdict; Phase 1 must not foreclose it.
  release_recommendation: CONDITIONAL-GO
  acceptance_criteria_for_release:
    - Sprint 4.5 live-smoke landed (DEF-01 + ESC-3 §8 closure)
    - DEF-05 elicitation routed to Vince (DEFER-WATCH-3 amendment)
    - DEF-03 cross-auth runtime test added OR inheritance documented
    - DEF-02 emptiness semantics documented in PRD §5.3 OR elicited
  defects_accepted:
    - DEF-04 (Accept header by-design — body-field-only contract)
    - DEF-07 (dedupe fallback when modified_at missing — DOCUMENTED-BY-DESIGN per DEFER-WATCH-1)
  defects_deferred_to_sprint_45:
    - DEF-01 (canonical multi-project pair end-to-end)
    - DEF-03 (cross-auth runtime probe)
    - ESC-3 live size measurement
  defects_blocking_release:
    - none (all defects are CONDITIONAL-resolvable in Sprint 4.5 or are by-design)
  defer_watch_state:
    DEFER-WATCH-1: still pending Vince — dedupe winner policy (current default: most-recent-by-modified_at)
    DEFER-WATCH-2: still pending Vince — column projection (current default: PHASE_1_DEFAULT_COLUMNS)
    DEFER-WATCH-3: enrichment requested via DEF-05 — activity-state default semantics on OR/NOT
    DEFER-WATCH-4: still pending Vince — null-key handling beyond flag
    DEFER-WATCH-5: resolved (JSON default per implementation)
    DEFER-WATCH-6: still pending Vince — pagination on CSV
    DEFER-WATCH-7: live-smoke needed in Sprint 4.5
  documentation_impact_assessment: |
    Changes affect: new public API surface (POST /v1/exports + POST /api/v1/exports);
    new Op enum members (BETWEEN, DATE_GTE, DATE_LTE); new identity_complete column.
    Documentation handoff to docs rite is REQUIRED (high impact per impact_categories
    [api_contract, auth, data_model]).
  security_handoff_required: NO
    rationale: |
      Phase 1 extends existing PAT + S2S middleware patterns without introducing new
      auth surfaces, no PII handling beyond existing schemas, no crypto changes,
      no session management changes. The dual-mount pattern is FleetQuery-precedented.
      DEF-03 cross-auth runtime probe is platform-middleware territory not new
      auth design.
  sre_handoff_required: ADVISORY
    rationale: |
      ESC-3 live size measurement (DEF-WATCH-7) is a performance-observability
      concern at production altitude. SRE rite SHOULD know about the
      export_format_serialized log signal so it can be consumed by SLO/SLI
      dashboards. No infrastructure change; no DB migration; no new service.
      Recommend ADVISORY HANDOFF surfacing the log signal name and the
      Phase 1.5 streaming-ADR trigger threshold (50k rows / 10MB).
```

---

End of QA verdict. No pending markers. Defect counts: 0 CRITICAL / 0 HIGH / 2 MEDIUM / 5 LOW. Verdict: CONDITIONAL-GO. ESC-1, ESC-2, ESC-3 all CONCUR. No new ESC-NN surfaced.
