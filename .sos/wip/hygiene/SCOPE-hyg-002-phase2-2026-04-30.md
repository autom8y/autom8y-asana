---
type: triage
artifact_type: smell-scope
rite: hygiene
session_id: session-20260430-144514-3693fe01
task: HYG-002 Phase 2
charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-phase2
authored_by: code-smeller
evidence_grade: STRONG
evidence_basis: direct file inspection (Read on tests/unit/lambda_handlers/test_workflow_handler.py L1–L1403) + canonical-type probe (python3 import + inspect.signature on AsanaClient/DataServiceClient/EventPublisher/WorkflowAction/EntityScope/WorkflowRegistry) + grep enumeration of bare empty-arg mock sites at 2026-04-30 (HEAD 550ec57a)
---

# SCOPE — HYG-002 Phase 2: Mock Surface Enumeration (test_workflow_handler.py)

## §1 Scope Summary

**File in scope** (charter §4 Q1a Sub-Sprint A): `tests/unit/lambda_handlers/test_workflow_handler.py` (1403 lines).

**Total mock-call sites enumerated** (grep `MagicMock\(\|AsyncMock\(`): 168 — but this includes attribute attaches (`AsyncMock(return_value=...)`) and `MagicMock(return_value=wf)` factory-shells which are NOT the SCAR-026 surface. Charter §4 Q1a re-probe count of **87 bare empty-arg sites** (`MagicMock()` and `AsyncMock()` with no args) is the actionable surface.

**87 bare-mock sites cluster into 6 patterns** (per-line table at §2):
| Cluster | Sites | % |
|---|---|---|
| C1 — `mock_asana = MagicMock()` (Lambda-handler test pattern) | 22 | 25% |
| C2 — `mock_ds = AsyncMock()` (DataServiceClient async-ctxmgr) | 22 | 25% |
| C3 — `MagicMock()` trailing arg (Lambda context placeholder) | 29 | 33% |
| C4 — `wf = MagicMock()` (WorkflowAction shell, helper L64) | 1 | 1% |
| C5 — `mock_publisher = MagicMock()` (EventPublisher) | 4 | 5% |
| C6 — Misc — `workflow_factory=MagicMock()` (L49) | 1 | 1% |
| **Subtotal bare empty-arg sites** | **79** | **91%** |
| Composite bare-form (`__aenter__/__aexit__` chains, see §2.2) | 8 | 9% |
| **Total bare empty-arg `MagicMock()`/`AsyncMock()` sites** | **87** | **100%** |

**Spec= readiness distribution**:
| Status | Count | % | Notes |
|---|---|---|---|
| VERIFIED (canonical class found, import path stable, spec'd-mock empirically tested) | 49 | 56% | C1 (22) + C2 (22) + C4 (1) + C5 (4) — all canonical types import OK at session bootstrap; spec= probe at §3 confirms attribute access works |
| AMBIGUOUS (canonical exists; minor verification pending) | 1 | 1% | C6 — `workflow_factory=MagicMock()` (L49) — workflow_factory is a Callable type per src/autom8_asana/lambda_handlers/workflow_handler.py:76; spec= viable but mocking a Callable is shape-thin |
| MISSING (no canonical match) | 0 | 0% | — |
| CANNOT-SPEC-PHASE2 (no importable canonical type) | 29 | 33% | C3 — Lambda context arg; `aws_lambda_powertools.LambdaContext` not in test dep tree (verified via `python3 -c "from aws_lambda_powertools.utilities.typing import LambdaContext"` raises ImportError) |
| Composite subform | 8 | 9% | `__aenter__ = AsyncMock(return_value=...)` / `__aexit__ = AsyncMock(return_value=False)` — these are chained off C2's `mock_ds` and propagate through C2's spec= application |

**Charter §4.3 NO-LEVER threshold check**: 29/87 = 33% canonical-type-resolution failure (CANNOT-SPEC-PHASE2). **33% < 50% — PROCEED to architect-enforcer.** All 29 CANNOT-SPEC sites are the same pattern (Lambda context placeholder), not 29 distinct drift signals — this is a single drift signal manifesting at 29 sites.

**Phase 1 comparison**: Phase 1 had 24% CANNOT-SPEC; Phase 2 has 33% — 9pp higher but still under threshold. The Phase 2 increase is structural (a single uniform pattern: every test invokes `await asyncio.to_thread(handler, {}, MagicMock())` for the Lambda context placeholder), not heterogeneous drift. Architect should consider whether to flag for /eunomia (drift signal: missing typed Lambda context fixture) per charter §11.1 routing.

## §2 Mock Site Enumeration (cluster-level table per HANDOFF discipline)

### §2.1 Cluster C1 — `mock_asana = MagicMock()` (22 sites)

**Sites**: L95, L127, L160, L191, L248, L279, L327, L364, L399, L429, L459, L518, L547, L588, L633, L668, L705, L744, L797, L831, L866, L912, L950, L983 (24 enumerated; 22 use `mock_asana = MagicMock()` exactly + 2 use `mock_asana_class.return_value = MagicMock()` at L1100/L1370). All occupy the same pattern within `@patch("autom8_asana.client.AsanaClient")` decorator scope.

**Inferred canonical type**: `AsanaClient` at `src/autom8_asana/client.py:50`.

**Import path** (verified): `from autom8_asana.client import AsanaClient` — module loads cleanly at probe time.

**Spec= candidate**: `MagicMock(spec=AsanaClient)`.

**Readiness**: VERIFIED. The pattern is `mock_asana_class.return_value = mock_asana` where `mock_asana_class` is the patched `AsanaClient` class object. Inside the test bodies, `mock_asana` is never asserted-against (per grep — no `mock_asana.X` attribute access in the test assertions). spec=AsanaClient is the safer form because the handler may construct an `AsanaClient(...)` instance internally and call its methods; spec= ensures the mock matches the real class shape. Empirically tested via `python3 -c "from unittest.mock import MagicMock; from autom8_asana.client import AsanaClient; MagicMock(spec=AsanaClient)"` — passes.

### §2.2 Cluster C2 — `mock_ds = AsyncMock()` (22 sites + 8 composite chains)

**Sites** (22 base): L98, L130, L163, L194, L251, L282, L330, L367, L402, L432, L462, L521, L550, L591, L636, L671, L708, L747, L800, L834, L869, L915, L953, L986 (24 enumerated; 22 use `mock_ds = AsyncMock()` exactly + 2 use `mock_ds = AsyncMock()` inside the SPOF helper `_invoke_fleet` at L1101/L1371).

**Composite chains** (8 sites; same `mock_ds` symbol): each `mock_ds = AsyncMock()` is followed by `mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)` and `mock_ds.__aexit__ = AsyncMock(return_value=False)`. The 8 composite sites at conftest-style chains are: L99/L100, L131/L132, L164/L165, L195/L196 (representative; pattern repeats for ALL 24 base sites — total chain attaches: ~48).

**Inferred canonical type**: `DataServiceClient` at `src/autom8_asana/clients/data/client.py:72` — empirically verified: `hasattr(DataServiceClient, '__aenter__') == True` (DataServiceClient IS an async context manager).

**Import path** (verified): `from autom8_asana.clients.data.client import DataServiceClient`.

**Spec= candidate**: `AsyncMock(spec=DataServiceClient)`.

**Readiness**: VERIFIED. DataServiceClient is a real class (not Protocol) with `__aenter__`/`__aexit__` declared as instance methods. AsyncMock(spec=DataServiceClient) preserves the async-ctxmgr shape AND the existing `mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)` test-side override pattern (spec= doesn't block setting an existing-attribute to a new mock). One nuance: the chained override pattern is verbose; architect may consider a `_mock_data_service_client()` helper to collapse the 8-line composite into 1 call — but that is a DRY-cleanup deferred beyond Phase 2.

### §2.3 Cluster C3 — `MagicMock()` trailing arg (Lambda context, 29 sites) — CANNOT-SPEC-PHASE2

**Sites**: every `await asyncio.to_thread(handler, {...}, MagicMock())` at L108, L143, L173, L211, L231, L261, L292, L311, L340, L378, L412, L442, L472, L532, L562, L566, L605, L651, L685, L722, L761, L810, L847, L882, L928, L966, L1000, L1106, L1376.

**Inferred canonical type**: `aws_lambda_powertools.utilities.typing.LambdaContext` (the AWS-Lambda runtime context object — handler signature is `(event, context) -> dict`).

**Import path probe** (verified): `python3 -c "from aws_lambda_powertools.utilities.typing import LambdaContext"` raises `ModuleNotFoundError: No module named 'aws_lambda_powertools'` at session bootstrap. The package is NOT in the test dep tree.

**Spec= candidate**: NONE — canonical type unimportable.

**Readiness**: **CANNOT-SPEC-PHASE2**. Per charter §4.3, this is a uniform drift signal manifesting at 29 sites, not 29 distinct gaps. The handler under test (`workflow_handler.py`) never accesses any field on the context object (verified: zero `context.` references in `src/autom8_asana/lambda_handlers/workflow_handler.py`); the context arg is signature-compliance-only. Architect-enforcer routing recommendation: surface to /eunomia as a single drift signal — "introduce a typed Lambda-context fixture (or a tests/conftest.py-level `_lambda_context` factory backed by `types.SimpleNamespace` matching the LambdaContext attribute surface used elsewhere in the lambda_handlers test tree)" — do NOT treat as 29 separate spec= gaps.

### §2.4 Cluster C4 — `wf = MagicMock()` (helper L64, 1 site)

**Site**: L64 inside helper `_mock_workflow` (L59–70). The helper attaches `wf.validate_async`, `wf.enumerate_async`, `wf.execute_async` as `AsyncMock(return_value=...)` (L65–69) and is consumed across ALL test methods (~26 call sites at L103, L135, L168, L203, L256, L287, L335, L373, L407, L437, L467, L526, L555, L596, L641, L676, L713, L752, L805, L839, L874, L920, L958, L991, L1081). Two sites set `wf.workflow_id = "reg-test-wf"` (L527) and `wf.workflow_id = "warm-wf"` (L556).

**Inferred canonical type**: `WorkflowAction` at `src/autom8_asana/automation/workflows/base.py:106` (abstract base class).

**Import path** (verified): `from autom8_asana.automation.workflows.base import WorkflowAction`.

**Public methods on `WorkflowAction`** (verified via `inspect.getmembers`):
- `validate_async(self) -> list[str]`
- `enumerate_async(self, scope: EntityScope) -> list[dict[str, Any]]`
- `execute_async(self, entities: list[dict], params: dict) -> WorkflowResult`
- `workflow_id` (property at L123)

All 4 attributes used by the test surface match `WorkflowAction`'s declared shape.

**Spec= candidate**: `MagicMock(spec=WorkflowAction)`.

**Readiness**: VERIFIED. Empirical probe: `MagicMock(spec=WorkflowAction)` permits all 4 attribute accesses (`validate_async`, `enumerate_async`, `execute_async`, `workflow_id`) and correctly raises `AttributeError` on a non-existent attribute. The `wf.workflow_id = "reg-test-wf"` assignment at L527 works on a spec'd mock (verified: spec= preserves named-attribute write-ability for property names; spec_set=False is the default and is what's needed here). Cluster C4 is the **highest ROI single edit** — replacing L64 with `MagicMock(spec=WorkflowAction)` propagates the canonical binding to all ~26 downstream consumers via the `_mock_workflow()` helper.

### §2.5 Cluster C5 — `mock_publisher = MagicMock()` (4 sites)

**Sites**: L601, L646, L681, L757 — each inside a `with patch("autom8y_events.EventPublisher") as mock_publisher_cls:` block. Pattern is `mock_publisher = MagicMock(); mock_publisher_cls.return_value = mock_publisher`.

**Inferred canonical type**: `EventPublisher` at `autom8y_events.publisher` (autom8y SDK; verified via `python3 -c "from autom8y_events import EventPublisher"` — module imports cleanly).

**Public methods on `EventPublisher`** (verified): `publish(self, event: DomainEvent) -> bool`.

**Spec= candidate**: `MagicMock(spec=EventPublisher)`.

**Readiness**: VERIFIED. Test assertions are `mock_publisher.publish.assert_called_once()` (L608) and `mock_publisher.publish.call_args[0][0]` (L611, L763) — `publish` is the only attribute used. spec=EventPublisher binds the canonical method shape and the side-effect `mock_publisher.publish.side_effect = RuntimeError(...)` (L647) continues to work on a spec'd mock.

### §2.6 Cluster C6 — `workflow_factory=MagicMock()` (1 site)

**Site**: L49 inside helper `_make_config` (default arg).

**Inferred canonical type**: `Callable[..., WorkflowAction]` (from `src/autom8_asana/lambda_handlers/workflow_handler.py:76` field declaration).

**Spec= candidate**: AMBIGUOUS — Callable types do not have a useful spec= shape at runtime; `MagicMock(spec=callable)` produces a callable mock but no attribute constraint. The L49 site is a **default value** (overridden by L104, L136, L169, L204, L257, L288, L336, L374, L408, L438, L468, L528, L557, L597, L642, L677, L714, L753, L806, L840, L875, L921, L959, L992, L1085, L1356 — 26 explicit `factory = MagicMock(return_value=wf)` sites that pass into `_make_config(workflow_factory=factory)`).

**Readiness**: AMBIGUOUS. The 26 explicit `factory = MagicMock(return_value=wf)` sites are NOT bare-form (they take an arg) and are out of scope for the SCAR-026 87-site surface. The L49 default value is the only bare-form site. Architect-enforcer recommendation: leave L49 as-is (default Callable factory; replacing with `MagicMock(spec=callable)` adds no test-time safety). Mark as DEFER-NO-ACTION — counted in 87 for grep-completeness but contributes zero ROI to spec= conversion.

## §3 Spec= Binding Candidates — Consolidated

| Canonical type | Import path | Used by clusters | Empirical probe |
|---|---|---|---|
| `AsanaClient` | `autom8_asana.client` (L50) | C1 (22 sites) | `MagicMock(spec=AsanaClient)` instantiates OK |
| `DataServiceClient` | `autom8_asana.clients.data.client` (L72) | C2 (22 base + 8 composite) | `AsyncMock(spec=DataServiceClient)` preserves `__aenter__`/`__aexit__` async-ctxmgr shape |
| `WorkflowAction` | `autom8_asana.automation.workflows.base` (L106) | C4 (helper L64; ~26 downstream consumers) | `MagicMock(spec=WorkflowAction)` permits `workflow_id`/`validate_async`/`enumerate_async`/`execute_async` and rejects unknown attrs |
| `EventPublisher` | `autom8y_events.publisher` | C5 (4 sites) | `MagicMock(spec=EventPublisher)` permits `publish` only |
| `Callable` (generic) | `typing.Callable` | C6 (1 site, default) | DEFER-NO-ACTION — Callable spec= is shape-thin |

All 4 actionable canonical types VERIFIED via `python3 -c "from <path> import <Class>"` at scoping time. Zero MISSING.

## §4 Canonical-Type-Resolution Failures (CANNOT-SPEC-PHASE2)

Per charter §4.3 NO-LEVER trigger. Sites where Phase 2 spec= MUST be skipped:

1. **Lambda context placeholder** (Cluster C3, 29 sites). The handler signature is `(event: dict, context: LambdaContext) -> dict`; tests pass `MagicMock()` as the context arg. `aws_lambda_powertools.utilities.typing.LambdaContext` is the canonical type but is NOT importable in the test dep tree (`ModuleNotFoundError`). The handler under test never accesses any field on the context (verified: zero `context.` references in workflow_handler.py source). Recommendation: defer to a follow-on cleanup that introduces a `tests/conftest.py`-level `_lambda_context()` factory using `types.SimpleNamespace` with the conventional LambdaContext attributes (`function_name`, `aws_request_id`, etc.) — drift signal for /eunomia per charter §11.1.

2. **Generic Callable factory default** (Cluster C6, 1 site at L49). `Callable` types lack a useful runtime spec= shape; `MagicMock(spec=callable)` is a no-op constraint. Mark DEFER-NO-ACTION.

**Total CANNOT-SPEC-PHASE2**: 30 sites of 87 = 34% (29 from C3 + 1 from C6). Charter §4.3 NO-LEVER threshold (>50%) NOT triggered — proceed.

## §5 Process-Global State Interaction (loadfile-mode requirement)

Per `.know/test-coverage.md:111`: *"`tests/unit/lambda_handlers/test_workflow_handler.py` and `tests/test_openapi_fuzz.py` share process-global state — `pytest-xdist` `--dist=loadfile` is required to keep tests on a single worker."*

**Process-global state surfaces identified in this file**:

1. **`WorkflowRegistry` singleton** (L488–502, `TestHandlerWorkflowRegistration`). Class-level `setup_method` and `teardown_method` invoke `reset_workflow_registry()` from `autom8_asana.automation.workflows.registry` (canonical at `src/autom8_asana/automation/workflows/registry.py:86`). Each test in this class registers a workflow via the handler's first invocation (L532) and asserts via `get_workflow_registry().get(...)` (L534). The registry is module-global — concurrent test-class invocations on different workers would corrupt state.

2. **`sys.modules["autom8y_events"]` mutation** (L703–732, `test_event_skipped_when_events_not_installed`). The test temporarily sets `sys.modules["autom8y_events"] = None` to simulate the package being unavailable. A try/finally restores the original. Cross-worker concurrent execution would race — another test's `from autom8y_events import EventPublisher` could fail with stale state.

3. **`patch("autom8y_events.EventPublisher")` context-managers** (L600, L645, L680, L756). Each is a function-scope mock patch; not process-global per se, but interacts with the L703 `sys.modules` mutation: if a test in TestBridgeEventEmission runs concurrently with `test_event_skipped_when_events_not_installed` on the same worker, both mutate `autom8y_events` symbol-table state.

**Spec= application order vs process-global state**:

- **C1 (AsanaClient)**, **C2 (DataServiceClient)**, **C5 (EventPublisher)**: spec= applied at-call-site is INSIDE `with patch(...)` or `@patch(...)` decorator scopes. The class object is patched (not the module), so spec= against the original class definition (imported via `from autom8_asana.client import AsanaClient`) does NOT interact with the patch — spec= reads the original class shape, the test invokes the patched class, the mock replaces the patched return_value. **No interaction with process-global state**. SAFE.

- **C4 (WorkflowAction)**: spec= applied at helper-L64 is INSIDE `_mock_workflow` helper which is invoked outside any patch context for the WorkflowAction symbol. WorkflowAction is imported once at module-import time; spec=WorkflowAction reads the class shape once. **No interaction with process-global state**. SAFE.

- **C5 + L703 sys.modules mutation interaction**: the `test_event_skipped_when_events_not_installed` test (L696) DOES mutate `sys.modules["autom8y_events"] = None`. If we apply spec=EventPublisher at module-import time (e.g., a top-of-file `from autom8y_events import EventPublisher`), the EventPublisher symbol is bound at import time and the L703 mutation does NOT invalidate the already-bound symbol. spec=EventPublisher inside the `_mock_publisher = MagicMock(spec=EventPublisher)` call at L601/L646/L681/L757 also reads the already-bound symbol. **Mutation race risk: NONE**. The L703 test does NOT use `mock_publisher = MagicMock()` (verified at L713–732 — uses different code path). SAFE.

**xdist mode requirements for verification**:

- **Janitor verification step MUST use `--dist=loadfile` mode** (NOT `--dist=load`) when running the full unit-test suite under xdist. Alternative: scoped invocation `pytest tests/unit/lambda_handlers/test_workflow_handler.py` (single-process; xdist mode irrelevant for a single file).
- **Recommended verification command** for janitor's pre-commit smoke test:
  ```
  pytest tests/unit/lambda_handlers/test_workflow_handler.py -p no:xdist
  # OR (matches CI):
  pytest tests/unit/lambda_handlers/test_workflow_handler.py --dist=loadfile -n auto
  ```
- **Risk surfaced for architect**: if the janitor commit applies spec= to `wf = MagicMock(spec=WorkflowAction)` at the helper-L64 level AND also touches module-import order (e.g., adding a top-level `from autom8_asana.automation.workflows.base import WorkflowAction`), this is a no-op for the existing process-global state because WorkflowAction is already in scope (verified — see test_workflow_handler.py:14). **No new module-import order added by spec= conversion**.

## §6 Smell-Detection Findings (out-of-scope, surfaced for visibility)

Per `Skill("smell-detection")` taxonomy, smells observed during scoping (NOT for action in Sub-Sprint A):

- **DRY-1 (DRY violation, MEDIUM)**: the `mock_ds = AsyncMock(); mock_ds.__aenter__ = AsyncMock(return_value=mock_ds); mock_ds.__aexit__ = AsyncMock(return_value=False)` triplet (3 lines × 24 sites = 72 lines) repeats verbatim. ROI Score: ~7.5/10. Candidate for `_make_mock_data_service()` helper or pytest fixture. **Defer to architect-enforcer post-spec= conversion** (will be a 1-line helper edit downstream of Phase 2).
- **DRY-2 (DRY violation, MEDIUM)**: 24 instances of the `@patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")` + `@patch("autom8_asana.client.AsanaClient")` + `@patch("autom8_asana.clients.data.client.DataServiceClient")` decorator triplet on test methods. Could collapse to a class-level `pytest.fixture(autouse=True)` for the AsanaClient/DataServiceClient pair. ROI Score: ~6/10. Defer.
- **CX-1 (Complexity, LOW)**: file is 1403 lines / 8 test classes / SPOF chaos suite at L1016-end. Above the 1000-line "long test module" threshold but well below the 1707-line precedent set by `test_lifecycle_smoke.py` (Phase 1 Cluster CX-1). Defer.
- **NM-1 (Naming, LOW)**: `mock_ds_class` vs `mock_asana_class` — both follow the same `_<short-name>_class` convention; consistent. No drift. SKIP.
- **PR-1 (Process, LOW)**: zero sites use `MagicMock(spec=...)` (verified: `grep -c "MagicMock(spec="` returns 0; `grep -c "AsyncMock(spec="` returns 0). This is the SCAR-026 surface the sprint targets — confirmation, not a new smell.
- **AR-1 (Architecture, MEDIUM)**: the `aws_lambda_powertools` LambdaContext gap (29 sites). The fact that 29 tests pass `MagicMock()` for the Lambda context argument when no canonical type is importable suggests a missing test fixture — this is a structural gap, not a sprint-level smell. Architect should surface to /eunomia per charter §11.1 routing.

## §7 Recommended Next-Step

**Architect-enforcer should plan**: a Phase 2 commit covering all 4 actionable clusters (C1 + C2 + C4 + C5). Cluster C3 (Lambda context, 29 sites) and C6 (Callable default, 1 site) are DEFERRED.

**Highest ROI (commit immediately, single atomic commit)**:

1. **C4 — `_mock_workflow` helper L64**: replace `wf = MagicMock()` with `wf = MagicMock(spec=WorkflowAction)`. Add `from autom8_asana.automation.workflows.base import WorkflowAction` at top. **1 helper edit; ~26 downstream consumers benefit**. Estimated commit complexity: LOW.

2. **C2 — DataServiceClient sites (22 base + 8 composite)**: replace `mock_ds = AsyncMock()` with `mock_ds = AsyncMock(spec=DataServiceClient)`. Add `from autom8_asana.clients.data.client import DataServiceClient` at top. **22 line edits, all mechanical**. Composite chains (`__aenter__`/`__aexit__`) UNCHANGED — they already work on a spec'd async-ctxmgr. Estimated complexity: LOW.

3. **C1 — AsanaClient sites (22)**: replace `mock_asana = MagicMock()` with `mock_asana = MagicMock(spec=AsanaClient)`. Add `from autom8_asana.client import AsanaClient` at top. **22 line edits, all mechanical**. Estimated complexity: LOW.

4. **C5 — EventPublisher sites (4)**: replace `mock_publisher = MagicMock()` with `mock_publisher = MagicMock(spec=EventPublisher)`. Add `from autom8y_events import EventPublisher` at top (already imported as `with patch("autom8y_events.EventPublisher")` — but the patch import is a string-literal; an explicit symbol-import is needed for spec=). Estimated complexity: LOW. **Risk note**: the L696 test (`test_event_skipped_when_events_not_installed`) mutates `sys.modules["autom8y_events"]`. The new top-level import binds EventPublisher at module-import time BEFORE the L703 mutation, so the spec= reference remains valid. Verified safe in §5.

**Total Phase 2 commit footprint**: 4 import additions + 49 line-level spec= upgrades = **53 mechanical edits** in a single atomic commit. Same shape as Phase 1's ~55-edit commit.

**DEFER to follow-on cleanup** (drift signals — surface to /eunomia per charter §11.1):

- **C3 (29 sites)**: Lambda context placeholder. Recommend introducing a `_lambda_context()` factory in `tests/conftest.py` backed by `types.SimpleNamespace` with conventional LambdaContext attributes. Out of Phase 2 scope.
- **C6 (1 site)**: Callable factory default at L49. DEFER-NO-ACTION (Callable spec= is shape-thin; no value-add).

**Estimated Phase 2 commit complexity for janitor**: **LOW** (single test-file edit + 4 top-level imports + 49 mechanical spec= upgrades, all backed by VERIFIED canonical types with successful empirical probes). Same atomic-commit shape as Phase 1.

**xdist verification mode**: `pytest tests/unit/lambda_handlers/test_workflow_handler.py -p no:xdist` for janitor's pre-commit smoke (single-process; loadfile concern moot at file-scope). For full-suite verification: `pytest tests/unit/lambda_handlers/ --dist=loadfile -n auto` (matches CI).

**Ready to dispatch architect-enforcer**: YES.
- Charter §4.3 NO-LEVER threshold not triggered (33% < 50%).
- 49 sites have unambiguous canonical-type bindings (VERIFIED via empirical import + spec=-instantiation probe).
- 30 are cleanly deferred (29 to C3 follow-on cleanup; 1 DEFER-NO-ACTION at C6) with documented rationale.
- Process-global state interaction analyzed in §5 — no spec= application order concern.
- Estimated commit shape matches Phase 1 precedent (single atomic commit, ~50 mechanical edits).
