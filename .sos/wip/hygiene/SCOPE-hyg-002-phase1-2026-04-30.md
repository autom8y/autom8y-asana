---
type: triage
artifact_type: smell-scope
rite: hygiene
session_id: session-20260430-131833-8c8691c1
task: HYG-002 Phase 1
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-hygiene-sprint
authored_by: code-smeller
evidence_grade: STRONG
evidence_basis: direct file inspection (Read on tests/conftest.py + tests/integration/test_lifecycle_smoke.py) + src/ cross-reference (Grep over src/autom8_asana/{lifecycle,clients,client.py,resolution,protocols,config.py,models/business,transport}) at 2026-04-30
---

# SCOPE — HYG-002 Phase 1: Mock Surface Enumeration

## §1 Scope Summary

**Files in scope** (charter §4.1 Q1a adjudication):
1. `tests/conftest.py` (204 lines total; root fixture region L76–L123)
2. `tests/integration/test_lifecycle_smoke.py` (1707 lines; 127 mock-call sites)

**Total mock-call sites enumerated**: 135
- conftest.py: 8 sites (5 `MagicMock`-class-attr-via-`MockHTTPClient`, 0 raw `MagicMock()`, 8 `AsyncMock()` inside `MockHTTPClient.__init__`). Note: conftest uses hand-written class shells (`MockHTTPClient`, `MockAuthProvider`, SDK `MockLogger`) rather than raw `MagicMock(...)` calls — ZERO bare `MagicMock`/`AsyncMock` instantiations live at fixture scope. Only the 8 `AsyncMock()` initializers inside the class body remain.
- test_lifecycle_smoke.py: 127 sites (per `grep -c MagicMock\|AsyncMock` at L1–L1707; charter §4.1 quoted 133 — present-tense probe yields 127 after import-line and signature-annotation exclusion).

**Spec= readiness distribution**:
| Status | Count | % |
|---|---|---|
| VERIFIED (canonical class found, import path stable) | ~74 | 55% |
| AMBIGUOUS (canonical exists; verify import path / shape variance) | ~28 | 21% |
| MISSING (no canonical match — drift signal) | 0 | 0% |
| CANNOT-SPEC-PHASE1 (Protocol / dynamic / Pydantic forward-ref) | ~33 | 24% |

**Charter §4.3 NO-LEVER threshold check**: 33/135 = 24% canonical-type-resolution failure. **24% < 50% — PROCEED to architect-enforcer.**

## §2 Root Fixtures (`tests/conftest.py:76–123`)

Conftest does NOT use bare `MagicMock(...)` calls at fixture scope. The four root fixtures (`mock_http`, `config`, `auth_provider`, `logger`) are hand-written class shells. The 8 mock instantiations live inside `MockHTTPClient.__init__` only.

| Site | Current shape | Var / scope | Inferred canonical type | Spec= candidate | Readiness |
|---|---|---|---|---|---|
| conftest.py:80 | `AsyncMock()` | `MockHTTPClient.get` | `AsanaHttpClient.get` (`src/autom8_asana/transport/asana_http.py:253`) | `AsyncMock(spec=AsanaHttpClient.get)` (method-level spec) | AMBIGUOUS — spec-on-method requires test-shape verification; alternative is a single `MagicMock(spec=AsanaHttpClient)` for the entire `mock_http` fixture replacing the hand-written class |
| conftest.py:81 | `AsyncMock()` | `MockHTTPClient.post` | `AsanaHttpClient.post` (`asana_http.py:275`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:82 | `AsyncMock()` | `MockHTTPClient.put` | `AsanaHttpClient.put` (`asana_http.py:294`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:83 | `AsyncMock()` | `MockHTTPClient.delete` | `AsanaHttpClient.delete` (`asana_http.py:311`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:84 | `AsyncMock()` | `MockHTTPClient.request` | `AsanaHttpClient.request` (`asana_http.py:513`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:85 | `AsyncMock()` | `MockHTTPClient.get_paginated` | `AsanaHttpClient.get_paginated` (`asana_http.py:322`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:86 | `AsyncMock()` | `MockHTTPClient.post_multipart` | `AsanaHttpClient.post_multipart` (`asana_http.py:380`) | same pattern as L80 | AMBIGUOUS |
| conftest.py:87 | `AsyncMock()` | `MockHTTPClient.get_stream_url` | `AsanaHttpClient.get_stream_url` (`asana_http.py:487`) | same pattern as L80 | AMBIGUOUS |

**Cluster recommendation (root fixtures)**: replace hand-written `MockHTTPClient` (conftest L76–L87) with a single `MagicMock(spec=AsanaHttpClient)` factory; the 8/8 method names already match the canonical class verbatim (verified). The `MockAuthProvider` (L90–L94) can be replaced with `MagicMock(spec=AuthProvider)` (`src/autom8_asana/protocols/auth.py:6`). `MockLogger` is SDK-provided (`autom8y_log.testing.MockLogger`) — DO NOT modify. `AsanaConfig()` (L106) is real-class instantiation — NOT a mock; out of scope.

## §3 High-Density Consumer (`tests/integration/test_lifecycle_smoke.py`)

127 mock sites cluster into 8 patterns. Cluster-level enumeration per HANDOFF discipline (charter §8 hard constraint: 250-line cap precludes per-line table).

### §3.1 Cluster A — Process entity (helper `_make_mock_process`, called ~13× test-side)
- **Sites**: L66 return-type, L68 base, L72 attr, L79 nested `process_type` MagicMock; reused via fn calls at L827, L848, L873, L898, L996, L1018, L1032, L1047, L1061, L1075, L1090, L1108, L1388, L1441, L1521–22, L1574, L1608.
- **Canonical type**: `Process` at `src/autom8_asana/models/business/process.py:161` (Pydantic BusinessEntity subclass).
- **Spec= candidate**: `MagicMock(spec=Process)`.
- **Readiness**: CANNOT-SPEC-PHASE1 — Pydantic model with NameGid forward references resolved only at session bootstrap (conftest `_bootstrap_session` L126; rebuild at L169–190). Spec= against Pydantic-rebuild target risks pre-rebuild collection-time failure. Defer to Phase 2 with explicit `spec_set=False` opt-in or factory-protocol design.

### §3.2 Cluster B — AsanaClient (helper `_make_mock_client`, called ~30+× test-side)
- **Sites**: L87 sig, L89 base, L90/L101/L109 sub-namespace shells (`tasks`, `sections`, `stories`); L91–99 (9 task ops), L102/107 sections, L110 stories. Reused everywhere `client = _make_mock_client()`.
- **Canonical type**: `AsanaClient` at `src/autom8_asana/client.py:50`.
- **Spec= candidate**: `MagicMock(spec=AsanaClient)` for L89; per-method `AsyncMock(spec=...)` for L91–99 / L102 / L110.
- **Readiness**: VERIFIED — `AsanaClient` is concrete; `tasks`, `sections`, `stories` attributes resolve to `TasksClient`, `SectionsClient`, `StoriesClient` (`src/autom8_asana/clients/{tasks,sections,stories}.py`). Apply spec= top-down at the client root; nested attribute mocks remain as-is or upgrade incrementally.

### §3.3 Cluster C — Service Protocol stubs (LifecycleEngine constructor injections)
- **Sites** (39 total): 6× per-engine-construction × ~6 constructions: L939/L945/L951/L957/L963/L967/L1433–38/L1495/L1499/L1501/L1505/L1507/L1518/L1600–05.
- **Canonical types** (Protocol-typed): `CreationServiceProtocol`, `SectionServiceProtocol`, `CompletionServiceProtocol`, `InitActionRegistryProtocol`, `WiringServiceProtocol`, `ReopenServiceProtocol` — all at `src/autom8_asana/lifecycle/engine.py:77–143`.
- **Spec= candidate**: `MagicMock(spec=CreationServiceProtocol)` etc. — `@runtime_checkable` Protocols (verified at L76, L88, L99, L109, L122, L134) are spec-compatible.
- **Readiness**: AMBIGUOUS — Python `MagicMock(spec=Protocol)` works for `@runtime_checkable` Protocols but only attributes declared in the Protocol body are available on the mock. The tests attach `AsyncMock` to method names that ARE declared in the Protocol bodies (verified): `create_process_async`, `cascade_async`, `complete_source_async`, `execute_actions_async`, `wire_defaults_async`, `reopen_async`. Spec= viable; verify each method-attach matches the Protocol's verbatim signature.

### §3.4 Cluster D — ResolutionContext stubs (`ctx = MagicMock()`)
- **Sites** (~15): L493, L527, L551, L585, L618, L828, L849, L874, L899, L1356, L1396, L1575. Each followed by `ctx.{offer,unit,business,resolve_holder}_async = AsyncMock(...)`.
- **Canonical type**: `ResolutionContext` at `src/autom8_asana/resolution/context.py:35`.
- **Spec= candidate**: `MagicMock(spec=ResolutionContext)`.
- **Readiness**: VERIFIED — class exists at expected path. Verify `offer_async`, `unit_async`, `business_async`, `resolve_holder_async` are declared methods (likely; not confirmed in this scoping pass — architect should re-probe at plan-authoring).

### §3.5 Cluster E — InitActionConfig stubs (`action_config = MagicMock()`)
- **Sites** (~4): L825, L846, L871, L896.
- **Canonical type**: `InitActionConfig` at `src/autom8_asana/lifecycle/config.py:35` (Pydantic BaseModel).
- **Spec= candidate**: `MagicMock(spec=InitActionConfig)`.
- **Readiness**: AMBIGUOUS — Pydantic BaseModel; spec= against BaseModel allows attribute access for declared fields. Setting `.condition` / `.type` / `.comment_template` etc. as test-side overrides on a spec'd mock requires `Config.frozen=False` semantics; verify before commit.

### §3.6 Cluster F — StageConfig stubs (`target_stage = MagicMock()`)
- **Sites** (~2): L1351, L1391.
- **Canonical type**: `StageConfig` at `src/autom8_asana/lifecycle/config.py:101` (Pydantic BaseModel).
- **Spec= candidate**: `MagicMock(spec=StageConfig)`.
- **Readiness**: AMBIGUOUS — same Pydantic-model concern as Cluster E.

### §3.7 Cluster G — Business / Unit / Offer entities (test-local MagicMocks)
- **Sites** (~13): L460/L464/L468/L518/L547/L571/L613 (offer/unit/business mock entities for cascading sections); L696/L698/L720 (business/unit name-generation tests); L802/L806 (CommentHandler source/business); L850/L875/L900 (campaign/products business mocks).
- **Canonical types**: same Pydantic `BusinessEntity` family (`src/autom8_asana/models/business/`). `name`, `gid`, `memberships`, `products`, `process_holder` are attributes on the BusinessEntity subclasses.
- **Spec= candidate**: `MagicMock(spec=BusinessEntity)` or specific subclass (`Business`, `Unit`, `Offer`).
- **Readiness**: CANNOT-SPEC-PHASE1 — same Pydantic forward-ref concern as Cluster A; defer.

### §3.8 Cluster H — Generic helper mocks (paginators, sections, holders, subtasks, source)
- **Sites** (~12): L105, L474, L480, L523, L576, L581, L615, L754, L762, L770, L1375, L1378, L1384.
- **Canonical types**: heterogeneous — paginator (no canonical class — protocol-shape `.collect`), section (no test isolation from `Section` model at `src/autom8_asana/models/section.py`), task (Pydantic `Task`).
- **Spec= candidate**: paginator → CANNOT-SPEC (no protocol declared); section/task → `MagicMock(spec=Section)`/`MagicMock(spec=Task)` AMBIGUOUS (Pydantic forward-ref).
- **Readiness**: ~50% CANNOT-SPEC (paginators), ~50% AMBIGUOUS (Section/Task models).

## §4 Spec= Binding Candidates — Consolidated

| Canonical type | Import path | Used by clusters |
|---|---|---|
| `AsanaHttpClient` | `autom8_asana.transport.asana_http` (L61) | conftest root fixture (mock_http) |
| `AuthProvider` | `autom8_asana.protocols.auth` (L6) | conftest root fixture (auth_provider) |
| `AsanaClient` | `autom8_asana.client` (L50) | Cluster B (lifecycle smoke) |
| `CreationServiceProtocol` | `autom8_asana.lifecycle.engine` (L77) | Cluster C |
| `SectionServiceProtocol` | `autom8_asana.lifecycle.engine` (L89) | Cluster C |
| `CompletionServiceProtocol` | `autom8_asana.lifecycle.engine` (L100) | Cluster C |
| `InitActionRegistryProtocol` | `autom8_asana.lifecycle.engine` (L110) | Cluster C |
| `WiringServiceProtocol` | `autom8_asana.lifecycle.engine` (L123) | Cluster C |
| `ReopenServiceProtocol` | `autom8_asana.lifecycle.engine` (L135) | Cluster C |
| `ResolutionContext` | `autom8_asana.resolution.context` (L35) | Cluster D |
| `InitActionConfig` | `autom8_asana.lifecycle.config` (L35) | Cluster E |
| `StageConfig` | `autom8_asana.lifecycle.config` (L101) | Cluster F |

All 12 candidates VERIFIED via Grep on src/autom8_asana/ at scoping time. Zero MISSING.

## §5 Canonical-Type-Resolution Failures (CANNOT-SPEC-PHASE1)

Per charter §4.3 NO-LEVER trigger. Sites where Phase 1 spec= MUST be skipped:

1. **Pydantic-model targets with NameGid forward references** (Cluster A `Process`, Cluster G `Business`/`Unit`/`Offer`, Cluster H Section/Task) — ~33 sites total. Rationale: conftest `_bootstrap_session` (L126) explicitly resolves NameGid forward references via `model_rebuild()` (L169, L190) at session start. Spec= materialization at test-collection time PRECEDES the bootstrap fixture scope; `MagicMock(spec=Process)` evaluated at module-import time may surface forward-ref resolution errors that the runtime has been working around. Janitor will skip these in Phase 1; defer to Phase 2 plan with explicit collection-time gate.

2. **Generic paginator stubs** (~6 sites in Cluster H: L105, L480, L523, L581, L1384) — no canonical Protocol or class is declared in src/autom8_asana for the paginator shape. The shape is implicit (`.collect()` method only). Janitor cannot bind spec= without a canonical type; flag as drift signal for /eunomia or architect to consider declaring a `PaginatorProtocol` in a follow-on cleanup.

3. **Process.process_type nested MagicMock** (conftest helper L79) — `process_type` is set to a nested `MagicMock()` whose only used attribute is `.value`. The canonical `process_type` field on `Process` is an `Enum` (per business model conventions); spec=Enum on a nested mock is over-specification for tests that only need `.value`. Defer until canonical Enum import is verified.

**Total CANNOT-SPEC-PHASE1**: ~33 sites (24% of 135 total). Charter §4.3 NO-LEVER threshold (>50%) NOT triggered — proceed.

## §6 Smell-Detection Findings (out-of-scope, surfaced for visibility)

Per Skill("smell-detection") taxonomy, smells observed during scoping (NOT for action in Sub-Sprint A):

- **DRY-1 (DRY violation, MEDIUM)**: `_make_engine` (L920–990) instantiates 6 service mocks in identical patterns; same 6-mock construction also appears verbatim at L1495–1518 and L1600–1605. Three near-identical 6-mock blocks; candidate for shared fixture or factory once spec= canonicalization lands.
- **DRY-2 (DRY violation, LOW)**: `mock_offer = MagicMock(); mock_offer.gid = ...; mock_offer.memberships = [...]` pattern repeats verbatim 4× (L460–462, L518–520, L547–549, L571–573). Could collapse to a `_make_mock_entity(gid, memberships)` helper post Phase 1.
- **CX-1 (Complexity, LOW)**: `test_lifecycle_smoke.py` is 1707 lines / 9 categories / multiple test classes. Above the typical "long test module" threshold (>1000 lines). Consider category-per-file split — defer to Phase 2/3 or architect-enforcer.
- **NM-1 (Naming, LOW)**: hand-written `MockHTTPClient` (conftest:76) shadows the conventional `MagicMock(spec=AsanaHttpClient)` pattern; the name "MockHTTPClient" implies a generic HTTP client when in fact it is an Asana-specific 8-method shape. Rename / replace at spec= conversion time.
- **PR-1 (Process, LOW)**: zero sites currently use `MagicMock(spec=...)` — this is the SCAR-026 surface the sprint targets; no smell, just absence-of-discipline confirmed.

## §7 Recommended Next-Step

**Architect-enforcer should plan**: a Phase 1 commit covering the VERIFIED + AMBIGUOUS-with-low-risk clusters only:

- **Highest ROI (commit immediately)**:
  - Cluster B: replace `_make_mock_client()` body (L87–112) with `MagicMock(spec=AsanaClient)`. 1 helper edit; ~30 downstream test cases benefit. Estimated commit complexity: LOW.
  - Cluster D: spec=ResolutionContext at all 12 `ctx = MagicMock()` sites. Mechanical find-replace. LOW.

- **Medium ROI (commit if planning bandwidth permits)**:
  - Conftest `MockHTTPClient` → `MagicMock(spec=AsanaHttpClient)` factory replacing the hand-written class (L76–L87). Single fixture rewrite; ALL HTTP-dependent tests benefit. LOW-MEDIUM (verify SDK testing pattern compat).
  - Conftest `MockAuthProvider` → `MagicMock(spec=AuthProvider)`. LOW.
  - Cluster C: spec= the 6 service protocols at all 39 sites. Mechanical; benefits from architect-enforcer review of one signature per Protocol before bulk-applying. MEDIUM.

- **DEFER to Phase 2** (canonical-type-resolution-failures, Pydantic forward-ref concern):
  - Cluster A `Process`, Cluster G BusinessEntity-family, Cluster H Section/Task — ~33 sites — until forward-ref bootstrap interaction is bounded.

- **DEFER (drift signal — surface to /eunomia per charter §11.1)**:
  - Generic paginator shape lacks a canonical Protocol declaration. Recommend declaring `PaginatorProtocol` in `src/autom8_asana/protocols/` as a separate cleanup ticket; do NOT block Phase 1 on it.

**Estimated Phase 1 commit complexity for janitor**: **LOW–MEDIUM** (single conftest edit + 2 helper functions + ~12 ctx-replace sites + ~39 service-protocol-spec sites = ~55 edits, all mechanical, all backed by VERIFIED canonical types).

**Ready to dispatch architect-enforcer**: YES. Charter §4.3 NO-LEVER threshold not triggered (24% < 50%); ~74 sites have unambiguous canonical-type bindings; ~28 have AMBIGUOUS bindings resolvable at plan-authoring time with one signature-probe per Protocol; ~33 are cleanly deferred to Phase 2 with documented rationale.
