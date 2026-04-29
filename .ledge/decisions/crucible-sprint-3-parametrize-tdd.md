---
type: design
initiative: project-crucible
sprint: 3
rite: 10x-dev
created: 2026-04-15
author: architect
consumes:
  - .ledge/spikes/crucible-hygiene-to-10xdev-handoff.md
  - .sos/wip/frames/project-crucible-17-second-frontier.md
  - .sos/wip/frames/project-crucible-17-second-frontier.shape.md
  - .sos/wip/crucible/sprint-2-behavior-audit-report.md
  - .sos/wip/crucible/sprint-1-audit-report.md
produces:
  - parametrize conversions in tests/unit/clients/ and tests/unit/models/
downstream_agent: principal-engineer
baseline_head: 8a0bab6a
status: APPROVED-FOR-EXECUTION
---

# TDD: Crucible Sprint-3 Parametrize Campaign (Clients + Models)

## Overview

Sprint-3 converts copy-paste test families in `tests/unit/clients/` (880 functions) and `tests/unit/models/` (~1,350 functions post-sprint-2) into parametrized matrices. The target state is ~200-250 functions in `clients/` (>=50% reduction) plus proportional reduction in `models/`, with Category B boundary-inversion refactoring merged into the same pass for single-pass efficiency. Coverage floor is 80%; all 33 scar-tissue regression tests are sacred; production source code is out of scope.

This TDD is the execution contract for principal-engineer. It specifies five parametrize patterns (A-E), five phases with concrete file-scope and commit boundaries, a scar-tissue preservation matrix, a coverage-verification protocol, conversion-semantics rules, and an inline ADR selecting the parametrize ID convention.

## Context

### Upstream Inputs

| Source | Load-Bearing Content |
|--------|----------------------|
| Hygiene-to-10xdev handoff | Baseline state at HEAD `8a0bab6a`; fixture map; sacred constraints; Category B catalog (~114 high-priority + ~256 broader) |
| Sprint-2 behavior audit | Per-file Category A/B/C classification; high-confidence boundary inversions |
| Sprint-1 audit | `client_factory` fixture landed in `tests/unit/clients/conftest.py` at RF-006 (`5b4565d3`) |
| Frame throughline | Suite to 4,500-5,500 functions; parametrize rate >=8%; CI under 60s; scars preserved |
| Shape sprint-3 exit criteria | clients/ >=50% reduction; models/ >=30% reduction; parametrize rate >=15% across converted files; raw=True + sync/async splits consolidated |

### Sacred Constraints (Non-Negotiable)

1. 33 scar-tissue regression tests pass after every commit (SCAR-001 through SCAR-030 + SCAR-S3-LOOP + SCAR-IDEM-001 + SCAR-REG-001)
2. Coverage >=80% at phase boundaries (baseline 87.61%)
3. No `src/autom8_asana/` changes -- tests-only
4. Independent revertibility per commit
5. `tests/unit/events/test_events.py` MockCacheProvider PRESERVED
6. `tests/unit/clients/data/` subtree OFF-LIMITS (TENSION-001 pending clearance)
7. SCAR-026 `spec=` enforcement is a PARALLEL track (add, do not remove; separate `chore(tests): SCAR-026 -- ...` commits, not `CRU-S3-NNN`)
8. SCAR-001 territory (`test_registry.py`, `test_registry_consolidation.py`) requires explicit review before refactor
9. SCAR-025 (`PRIMARY_PROJECT_GID`, `NAME_CONVENTION` class-attribute tests) preserved even when shaped like framework waste
10. SCAR-027 (`test_creation.py`, 12 cases) -- already parametrize-like; verify scar intent before restructuring

### Out of Scope

- `tests/unit/clients/data/` (20 files, TENSION-001)
- `tests/unit/clients/test_batch.py` (Category C; batch orchestration is application behavior)
- `tests/unit/events/` (MockCacheProvider scar-sensitive)
- `tests/unit/automation/`, `persistence/`, `dataframes/`, `cache/`, `core/` (sprint-4 scope)
- 47 xfail-masked OpenAPI violations (S10) -- separate rite
- RF-007 local fixture promotion (deferred; AST remeasurement required)

## System Design

### Architecture Diagram

```
                    ┌────────────────────────────────────────────┐
                    │        Sprint-3 Parametrize Pipeline       │
                    └──────────────────┬─────────────────────────┘
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         │                                                           │
  ┌──────▼─────────┐                                         ┌───────▼─────────┐
  │  Pre-conversion│                                         │ Post-conversion │
  │   Inventory    │                                         │   Verification  │
  │ (per-file AST  │                                         │ (scar sweep +   │
  │  function cnt) │                                         │  coverage gate) │
  └──────┬─────────┘                                         └───────▲─────────┘
         │                                                           │
         ▼                                                           │
  ┌──────────────────────────────────────────────────────────────────┴─┐
  │               Pattern Selection Matrix (A through E)               │
  │                                                                    │
  │  A: cross-client (WorkspacesClient..CustomFieldsClient) via        │
  │     client_factory                                                 │
  │  B: sync/async method-name parametrize                             │
  │  C: raw=True return-type parametrize                               │
  │  D: field-assertion parametrize (models/)                          │
  │  E: boundary-inversion refactor (mock.assert -> behavior assert)   │
  └───────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │                 Phased Execution (atomic commits)                   │
  │                                                                     │
  │  P1: test_tier1_clients.py    51 ->  12-15  fns                     │
  │  P2: test_tier2_clients.py    71 ->  15-20  fns                     │
  │  P3: test_tasks_client.py     +Category B boundary fuse             │
  │  P4: residual clients/ files  (pattern-driven)                      │
  │  P5: unit/models/ parametrize (post-inventory)                      │
  └─────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Responsibility | Location |
|-----------|----------------|----------|
| `client_factory` fixture | Constructs any Asana client type from shared mocks | `tests/unit/clients/conftest.py:101-133` |
| `MockCacheProvider` (shared) | SDK-backed mock cache with `key:type` composite keys | `tests/unit/clients/conftest.py:22-92` |
| Scar-tissue sweep | Verifies 33 scars pass after each phase | `.know/scar-tissue.md` + verification script |
| Coverage gate | Enforces >=80% at phase boundary | `uv run pytest --cov=src --cov-report=term` |
| Commit protocol | `refactor(tests): CRU-S3-NNN -- <desc>` | Conventions skill |

### Data Model

This is a test-structural refactor. There is no new data model. Parametrize parameters are tuples describing test inputs, reference outputs, or method names. The transformation preserves the test-collection contract: every original test function maps to exactly one parametrize case with a deterministic test-id.

### API Contracts

Not applicable (test-code refactor). The parametrize-id convention (ADR below) is the only "contract" produced by this work -- it governs debuggability and CI failure-attribution.

## Pattern Catalog

Five patterns drive the campaign. Each pattern has: applicability criteria, a concrete before/after code sample, and a consolidation-ratio expectation. Every parametrize conversion MUST match one (or a composition) of these patterns; conversions that do not fit pattern A-E require architect consultation before committing.

---

### Pattern A: Cross-Client Parametrize via `client_factory`

**Applicability**: Test functions that exercise the SAME method semantic across 2+ client types and differ only in (client class, endpoint URL, response model). Canonical site: `test_tier1_clients.py` `TestWorkspacesClientGetAsync::test_get_async_returns_workspace_model` + `TestUsersClientGetAsync::test_get_async_returns_user_model` + 3 more copies across Projects/Sections/CustomFields.

**Expected consolidation**: 5 functions -> 1 parametrized function (5:1).

**Before** (excerpt, `test_tier1_clients.py:57-73`):

```python
class TestWorkspacesClientGetAsync:
    async def test_get_async_returns_workspace_model(
        self, workspaces_client, mock_http
    ) -> None:
        mock_http.get.return_value = {"gid": "ws123", "name": "My Workspace", "is_organization": True}
        result = await workspaces_client.get_async("ws123")
        assert isinstance(result, Workspace)
        assert result.gid == "ws123"
        assert result.name == "My Workspace"
        mock_http.get.assert_called_once_with("/workspaces/ws123", params={})

# ... 4 more near-identical classes for Users, Projects, Sections, CustomFields
```

**After**:

```python
@pytest.mark.parametrize(
    "client_cls, gid, payload, expected_model, url_template",
    [
        (WorkspacesClient, "ws123",
         {"gid": "ws123", "name": "My Workspace", "is_organization": True},
         Workspace, "/workspaces/{gid}"),
        (UsersClient, "1234567890123",
         {"gid": "1234567890123", "name": "Alice Smith", "email": "alice@example.com"},
         User, "/users/{gid}"),
        (ProjectsClient, "1234567890123",
         {"gid": "1234567890123", "name": "My Project", "archived": False, "public": True},
         Project, "/projects/{gid}"),
        (SectionsClient, "sec123",
         {"gid": "sec123", "name": "Section A"},
         Section, "/sections/{gid}"),
        (CustomFieldsClient, "cf123",
         {"gid": "cf123", "name": "Priority", "type": "enum"},
         CustomField, "/custom_fields/{gid}"),
    ],
    ids=["workspaces_get", "users_get", "projects_get", "sections_get", "custom_fields_get"],
)
async def test_get_async_returns_model(
    client_factory, mock_http, client_cls, gid, payload, expected_model, url_template
) -> None:
    client = client_factory(client_cls, use_cache=False)
    mock_http.get.return_value = payload

    result = await client.get_async(gid)

    assert isinstance(result, expected_model)
    assert result.gid == payload["gid"]
    assert result.name == payload["name"]
    mock_http.get.assert_called_once_with(url_template.format(gid=gid), params={})
```

**Gotchas**:

- `client_factory` injects `cache_provider` by default; pass `use_cache=False` for clients that don't take one in the original test (WorkspacesClient, UsersClient were built without cache in the originals).
- Asymmetric field assertions (e.g., `is_organization` on Workspace, `email` on User) stay in the per-case tuple, not in the shared body. If the shared body needs to assert case-specific fields, promote those into the parametrize tuple as an `extra_assertions: dict[str, Any]` field.
- Do NOT parametrize across client types that have genuinely different call signatures (e.g., `UsersClient.list_for_workspace_async(ws_gid)` vs `ProjectsClient.list_async(workspace=)`) -- those belong in Pattern B, not A.

---

### Pattern B: Sync/Async Method-Name Parametrize

**Applicability**: Every client method has `*_async` and sync-wrapper variants whose test bodies differ only by `await` and method name. Canonical site: `test_tier1_clients.py::TestWorkspacesClientGetAsync::test_get_async_returns_workspace_model` vs `TestWorkspacesClientGetSync::test_get_sync_returns_workspace_model` (mirrored in every client class).

**Expected consolidation**: 2 functions -> 1 parametrized function per method (2:1). Composable with Pattern A for (sync/async) x (5 clients) = 10:1.

**Before** (`test_tier1_clients.py:90-116` compressed):

```python
class TestWorkspacesClientGetSync:
    def test_get_sync_returns_workspace_model(self, mock_http, config, auth_provider) -> None:
        client = WorkspacesClient(http=mock_http, config=config, auth_provider=auth_provider)
        mock_http.get.return_value = {"gid": "ws456", "name": "Sync Workspace"}
        result = client.get("ws456")
        assert isinstance(result, Workspace)
        assert result.gid == "ws456"

class TestWorkspacesClientGetAsync:
    async def test_get_async_returns_workspace_model(self, workspaces_client, mock_http) -> None:
        mock_http.get.return_value = {"gid": "ws123", "name": "My Workspace", ...}
        result = await workspaces_client.get_async("ws123")
        assert isinstance(result, Workspace)
        # ...
```

**After** (use a helper to unify async/sync call-sites):

```python
import asyncio
import inspect

async def _call(method, *args, **kwargs):
    """Unify sync/async invocation. async methods are awaited; sync methods are run in executor-free path."""
    result = method(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result

@pytest.mark.parametrize(
    "method_name",
    ["get_async", "get"],
    ids=["async", "sync"],
)
async def test_workspaces_get_returns_model(
    client_factory, mock_http, method_name
) -> None:
    # Use fresh client for sync variant to avoid shared event loop (preserves original test's fresh-construct pattern)
    client = client_factory(WorkspacesClient, use_cache=False)
    mock_http.get.return_value = {"gid": "ws123", "name": "My Workspace", "is_organization": True}

    method = getattr(client, method_name)
    result = await _call(method, "ws123")

    assert isinstance(result, Workspace)
    assert result.gid == "ws123"
    assert result.name == "My Workspace"
```

**Critical constraint**: The `test_get_sync_fails_in_async_context` test (which asserts `SyncInAsyncContextError` when the sync method is called from within an async test) MUST NOT be folded into Pattern B. It is a distinct behavioral assertion and remains a standalone function. This applies everywhere sync/async parity tests exist.

**Gotcha**: Original sync tests often construct a fresh client without `log_provider` or cache; preserve this by passing `use_cache=False` and NOT injecting `logger` when the original omitted it. If the sync test's semantic is "fresh client works standalone," that semantic is preserved by `client_factory(ClientCls, use_cache=False)`.

---

### Pattern C: `raw=True` Return-Type Parametrize

**Applicability**: Paired tests that differ only in `raw=False` vs `raw=True` expected return type (model vs dict). Canonical site: `test_tasks_duplicate.py:58-80` (`test_duplicate_async_returns_task_model` + `test_duplicate_async_returns_raw_dict_when_raw_true`). This pattern appears on nearly every client method per sprint-2 audit.

**Expected consolidation**: 2 functions -> 1 parametrized function (2:1). Composable with Pattern A and B.

**Before** (`test_tasks_duplicate.py:58-80`):

```python
async def test_duplicate_async_returns_task_model(self, tasks_client, mock_http) -> None:
    mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Duplicated Task")
    result = await tasks_client.duplicate_async(TEMPLATE_GID, name="Duplicated Task")
    assert isinstance(result, Task)
    assert result.gid == NEW_TASK_GID
    assert result.name == "Duplicated Task"

async def test_duplicate_async_returns_raw_dict_when_raw_true(self, tasks_client, mock_http) -> None:
    mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Duplicated Task")
    result = await tasks_client.duplicate_async(TEMPLATE_GID, name="Duplicated Task", raw=True)
    assert isinstance(result, dict)
    assert result["gid"] == NEW_TASK_GID
    assert result["name"] == "Duplicated Task"
```

**After**:

```python
@pytest.mark.parametrize(
    "raw, expected_type, accessor",
    [
        (False, Task, lambda r: (r.gid, r.name)),
        (True,  dict, lambda r: (r["gid"], r["name"])),
    ],
    ids=["typed_model", "raw_dict"],
)
async def test_duplicate_async_return_shape(
    tasks_client, mock_http, raw, expected_type, accessor
) -> None:
    mock_http.post.return_value = make_job_response(NEW_TASK_GID, "Duplicated Task")

    kwargs = {"name": "Duplicated Task"}
    if raw:
        kwargs["raw"] = True
    result = await tasks_client.duplicate_async(TEMPLATE_GID, **kwargs)

    assert isinstance(result, expected_type)
    gid, name = accessor(result)
    assert gid == NEW_TASK_GID
    assert name == "Duplicated Task"
```

**Gotcha**: The accessor lambda isolates the model-vs-dict attribute-access divergence. Do NOT use `getattr(r, "gid", r.get("gid"))` -- that hides type-semantic differences and risks masking a future bug where one path silently returns the wrong shape.

**Do NOT apply Pattern C** where the `raw=True` test checks additional fields not present on the model path (e.g., raw dict carries `resource_subtype` that the model discards). Keep those as separate tests; Pattern C assumes symmetric assertions.

---

### Pattern D: Field-Assertion Parametrize (`models/`)

**Applicability**: Single test function asserting many independent fields on a model constructed from a shared API response fixture. Canonical site: `tests/unit/models/test_models.py:162` `test_create_from_full_api_response` (38 discrete field assertions in one body). Prevalent across `test_models.py` nested-object handling, field-alias handling, and inheritance tests.

**Expected consolidation**: 1 monolithic function with N assertions -> 1 parametrized function with N cases. Function count: 1 -> 1 (no reduction in functions). Test-case count: N asserts -> N distinct test-ids. This IMPROVES debuggability (each field failure has its own reported test-id) even though it does not reduce function count. Apply this pattern only where it clarifies diagnosis; do not apply for the sake of count reduction.

**When to apply**:
- The function has >=10 independent field assertions
- The assertions are all of the form `assert task.<field> == <expected>` against a shared fixture
- A single field failure currently stops execution of the rest; parametrization surfaces all failures

**When NOT to apply**:
- Assertions have ordering dependencies (e.g., state mutation between asserts)
- The function body does non-trivial setup between asserts
- The test is named in scar-tissue (`SCAR-020 test_normalizers.py`, `SCAR-023 test_cascade_validator.py`) -- check first

**Before** (`test_models.py:162-208`, summarized):

```python
def test_create_from_full_api_response(self) -> None:
    task = Task.model_validate(TASK_FULL)
    assert task.gid == "1234567890"
    assert task.resource_type == "task"
    assert task.name == "Complete SDK Hardening"
    assert task.notes == "Implement comprehensive test coverage for models"
    # ... 34 more assertions
    assert task.actual_time_minutes == 120.5
```

**After**:

```python
@pytest.fixture
def full_task() -> Task:
    return Task.model_validate(TASK_FULL)

@pytest.mark.parametrize(
    "field_path, expected",
    [
        ("gid", "1234567890"),
        ("resource_type", "task"),
        ("name", "Complete SDK Hardening"),
        ("notes", "Implement comprehensive test coverage for models"),
        ("html_notes", "<body>Implement comprehensive test coverage for models</body>"),
        ("completed", False),
        ("completed_at", None),
        ("due_on", "2024-12-31"),
        # ... remaining simple fields
        ("num_subtasks", 3),
        ("actual_time_minutes", 120.5),
    ],
    ids=lambda p: p if isinstance(p, str) else None,  # use field_path as test-id
)
def test_full_api_response_field(full_task, field_path, expected) -> None:
    """Each field from TASK_FULL deserializes correctly."""
    assert _resolve(full_task, field_path) == expected


def _resolve(obj, path: str):
    """Resolve dotted path like 'assignee.gid' against a model."""
    current = obj
    for part in path.split("."):
        current = getattr(current, part)
    return current


# Nested-object fields whose expected value is itself a model (assignee, workspace, projects) stay
# in a SEPARATE test function because they have structural assertions (isinstance, len of list)
# that do not fit the simple equality matrix.
def test_full_api_response_nested_objects(full_task) -> None:
    assert isinstance(full_task.assignee, NameGid)
    assert full_task.assignee.gid == "987654321"
    assert full_task.assignee.name == "Test User"
    assert isinstance(full_task.workspace, NameGid)
    assert full_task.workspace.gid == "ws999"
    assert len(full_task.projects or []) == 2
    assert full_task.parent is None
```

**Gotcha**: `ids=lambda p: p if isinstance(p, str) else None` uses the field path as the test-id. pytest will then report `test_full_api_response_field[gid]`, `test_full_api_response_field[assignee.gid]`, etc. This is load-bearing for the ADR parametrize-id convention (below).

---

### Pattern E: Boundary-Inversion Refactoring (Category B Fuse)

**Applicability**: Tests that assert on mock-call state (`mock_http.get.assert_called_once_with(...)`) rather than on observable behavior of the system under test. Per sprint-2 audit: ~114 high-confidence + ~256 broader inversions in `tests/unit/clients/`. Pattern E is applied *during* Pattern A/B/C conversions -- each boundary-inversion encountered is refactored in-place, not deferred.

**Expected consolidation**: 0:1 function-count impact (pure refactoring). The goal is to reduce boundary-inversion density; parametrize reduction comes from A/B/C/D.

**Inversion decision tree**:

1. Does the mock-call assertion encode a CONTRACT with the Asana API (URL path, HTTP verb, request-body shape)? -> KEEP. Contract assertions are legitimate. Example: `mock_http.post.assert_called_once_with("/tasks/{gid}/duplicate", json={...})` verifies the Asana endpoint contract and must remain.
2. Is the mock-call assertion merely repeating what the fixture itself demonstrates (e.g., `mock_http.get.assert_called_once()` after already returning a fixture value)? -> REMOVE. The return value is the observable effect.
3. Is the mock-call assertion a proxy for behavior that can be asserted on the output model? -> REFACTOR to assert on output. Example: asserting `mock_http.get.call_args[1]["params"] == {"opt_fields": "name,notes"}` to verify `opt_fields` handling -- when the same thing can be verified by constructing an input with opt_fields and asserting the returned Task has the expected fields populated (behavior observable via Asana's response). If there is no behavior-side observation possible, keep the mock assertion but annotate it as a contract-assertion (category 1).

**Before** (generic Category B pattern, from `test_tier1_clients.py`):

```python
async def test_get_async_returns_workspace_model(self, workspaces_client, mock_http) -> None:
    mock_http.get.return_value = {"gid": "ws123", "name": "My Workspace", "is_organization": True}
    result = await workspaces_client.get_async("ws123")

    assert isinstance(result, Workspace)
    assert result.gid == "ws123"
    assert result.name == "My Workspace"
    assert result.is_organization is True
    mock_http.get.assert_called_once_with("/workspaces/ws123", params={})   # <-- Category B
```

**After (fused with Pattern A)**:

```python
# The isinstance + field checks are the behavioral assertions.
# The URL assertion is the Asana-contract assertion -- retained but narrowed to URL only.
# The fused test below keeps the URL assertion (contract) and drops redundant call-count.

@pytest.mark.parametrize(
    "client_cls, gid, payload, expected_model, url_template",
    # ... same table as Pattern A ...
)
async def test_get_async_returns_model(
    client_factory, mock_http, client_cls, gid, payload, expected_model, url_template
) -> None:
    client = client_factory(client_cls, use_cache=False)
    mock_http.get.return_value = payload

    result = await client.get_async(gid)

    # Behavioral assertions (output shape, field values)
    assert isinstance(result, expected_model)
    assert result.gid == payload["gid"]
    assert result.name == payload["name"]

    # Contract assertion (Asana endpoint URL) -- retained per decision tree category 1
    # Note: assert_called_once_with REPLACED with call_args inspection to decouple from mock semantics
    assert mock_http.get.call_args.args[0] == url_template.format(gid=gid)
    assert mock_http.get.call_args.kwargs == {"params": {}}
```

**Rationale for the replacement idiom** (`call_args.args[0]` instead of `assert_called_once_with(...)`):
- `assert_called_once_with` conflates "called exactly once" (behavioral) with "called with these exact args" (contract). Separating them exposes what is actually being tested.
- Under parametrize, `mock_http` may legitimately be called once per parametrize-case with different args; `assert_called_once` is still correct per-case because pytest re-constructs fixtures per test-id, but the idiom is less brittle under future refactoring.

**Do NOT apply Pattern E** to SCAR-026 territory (workflow mocks) without the parallel-track SCAR-026 `spec=` enforcement. Removing boundary assertions in a file that also lacks `spec=` can mask the exact SCAR-026 failure mode. If a target file has MagicMock without `spec=`, add `spec=` FIRST (separate commit), THEN apply Pattern E.

---

## Phased Execution Plan

Five phases, each with defined file-scope, commit boundaries, pattern application, revertibility, and verification. Every commit is independent: revert of CRU-S3-N does not force revert of CRU-S3-N+1.

### Phase 1: `test_tier1_clients.py` (51 -> 12-15 functions)

**Scope**: `tests/unit/clients/test_tier1_clients.py` only. 51 test functions across WorkspacesClient, UsersClient, ProjectsClient, SectionsClient, CustomFieldsClient (5 classes, 9 nested test classes per tier-1 client).

**Primary patterns**: A (cross-client) + B (sync/async) + C (raw=True). Pattern E applied wherever a Category B inversion is encountered during A/B/C conversion.

**Commit decomposition**:
- `CRU-S3-001`: Pattern A fuse of `get_async_returns_model` across 5 tier-1 clients (5 -> 1)
- `CRU-S3-002`: Pattern A fuse of `get_async_raw_returns_dict` across 5 tier-1 clients (5 -> 1) OR merge into CRU-S3-001 via Pattern C composition if that reduces to a single (client x raw) matrix
- `CRU-S3-003`: Pattern B sync/async fuse for `get` family across 5 tier-1 clients
- `CRU-S3-004`: Pattern A fuse of `list_async_returns_page_iterator` across 5 tier-1 clients
- `CRU-S3-005`: ProjectsClient create/update/delete family -> (sync/async) x (raw) matrix
- `CRU-S3-006`: SectionsClient task-movement family consolidation
- `CRU-S3-007`: CustomFieldsClient enum-options + project-settings family consolidation
- `CRU-S3-008`: Residual `TestModelImports` / `TestModelValidation` / `TestAsanaClientThreadSafety` pass (mostly Pattern E, minimal consolidation)

**Expected outcome**: 51 -> 12-15 functions. Consolidation ratio: 3.4:1 to 4.2:1.

**Risk**: MEDIUM. Cross-client Pattern A is the novel step. Hazard: asymmetric field assertions (e.g., Workspace.is_organization vs User.email) force per-case `extra_assertions` complication.

**Revertibility**: Each commit touches 5-10 functions within `test_tier1_clients.py`. Revert isolated to file.

**Scar intersections**: None direct. SCAR-026 (`spec=` enforcement) applies to ALL client tests but runs parallel-track.

**Verification**: After each commit -- full test suite green, file-scoped coverage within +/-0.1%, test count drops match expected delta.

---

### Phase 2: `test_tier2_clients.py` (71 -> 15-20 functions)

**Scope**: `tests/unit/clients/test_tier2_clients.py` only. 71 test functions across WebhooksClient, TeamsClient, AttachmentsClient, TagsClient, GoalsClient, PortfoliosClient, StoriesClient.

**Primary patterns**: A (cross-client where signatures align), B (sync/async), C (raw=True), E (inversion fuse). Tier-2 clients have less signature symmetry than tier-1 (Webhooks has signature-verification tests, Attachments has upload/download, Goals has subgoals/supporting-work) -- Pattern A applies narrowly to `get_async_returns_*_model` and `create_async_returns_*_model` only.

**Commit decomposition**:
- `CRU-S3-010`: Pattern A fuse for `get_async_returns_*_model` across 7 tier-2 clients (7 -> 1)
- `CRU-S3-011`: Pattern A fuse for `create_async_returns_*_model` across subset of tier-2 clients with symmetric create
- `CRU-S3-012`: WebhooksClient signature-verification Pattern B+C fuse (8 tests -> 3-4)
- `CRU-S3-013`: AttachmentsClient upload family parametrize (`test_upload_various_file_types` already parametrize-shape -- verify, do not regress)
- `CRU-S3-014`: AttachmentsClient download family parametrize (to_path vs to_file_object -> Pattern B-like parametrize)
- `CRU-S3-015`: GoalsClient subgoal/supporting-work/follower families
- `CRU-S3-016`: PortfoliosClient item/member/custom-field-setting families
- `CRU-S3-017`: StoriesClient consolidation (small)
- `CRU-S3-018`: `TestAsanaClientTier2Properties` + `TestTier2ModelExports` -- Pattern D or Pattern A across 7 property tests

**Expected outcome**: 71 -> 15-20 functions. Consolidation ratio: 3.5:1 to 4.7:1.

**Risk**: MEDIUM-HIGH. WebhooksClient signature tests encode HMAC correctness -- treat as contract (Pattern E decision tree category 1); do not remove HMAC digest assertions. AttachmentsClient upload has file-handle lifecycle tests that are behavioral and must survive.

**Revertibility**: Per-commit atomic within the file.

**Scar intersections**: None direct. Webhook signature tests overlap SCAR-029 (whitespace-only GID bypass) territory -- those specific adversarial tests are preserved unchanged.

**Verification**: Same as Phase 1.

---

### Phase 3: `test_tasks_client.py` Category B Boundary Fuse (~11 functions)

**Scope**: `tests/unit/clients/test_tasks_client.py`. 11 Category B high-priority functions identified in sprint-2 audit. This phase is primarily Pattern E (boundary refactor) with opportunistic Pattern C.

**Primary patterns**: E (primary) + C (where raw=True pairs surface).

**Commit decomposition**:
- `CRU-S3-020`: Pattern C fuse for `get_async_returns_task_model` + `get_async_raw_returns_dict` + sync equivalents
- `CRU-S3-021`: Pattern C fuse for `create_async` family (returns_task_model, raw_returns_dict, with_projects, with_parent)
- `CRU-S3-022`: Pattern E refactor of remaining Category B inversions; drop redundant `assert_called_once()` where behavior already verified by return-value assertion
- `CRU-S3-023`: Sync-wrapper coverage preserved via Pattern B fuse with freshly-constructed client

**Expected outcome**: ~11 Category B residue -> absorbed; total file function reduction dependent on Pattern C opportunities.

**Risk**: LOW. `test_tasks_client.py` is well-established; patterns are understood.

**Revertibility**: Per-commit atomic.

**Scar intersections**: `TasksClient` is referenced by SCAR-026 territory (workflows calling `tasks.list_for_project_async`). Before applying Pattern E here, verify that the test file uses `spec=` (or add it first under a parallel SCAR-026 commit). TasksClient.duplicate_async is referenced by SCAR-027 (`test_creation.py` is the actual scar test; `test_tasks_duplicate.py` is not the scar location).

**Verification**: Same as Phase 1 + explicit scar sweep on SCAR-026 workflow tests.

---

### Phase 4: Residual `clients/` Files (pattern-driven)

**Scope**: All remaining `tests/unit/clients/*.py` except `data/`, `test_batch.py`, and files already converted in Phases 1-3. Target files:
- `test_base_cache.py`
- `test_client.py`
- `test_client_warm_cache.py`
- `test_coverage_gap.py`
- `test_custom_fields_cache.py`
- `test_name_resolver.py`
- `test_projects_cache.py`
- `test_sections_cache.py`
- `test_stories_cache.py`
- `test_tasks_cache.py`
- `test_tasks_dependents.py`
- `test_tasks_duplicate.py`
- `test_users_cache.py`

**Primary patterns**: Per-file pattern selection. Pre-phase micro-audit required: run a function-count + parametrize-opportunity scan (AST-based or manual) before starting. Do NOT batch-convert -- each file gets its own commit or small commit cluster.

**Commit decomposition**: TBD per-file at phase-start micro-audit. Expected range: `CRU-S3-030` through `CRU-S3-055`. Each commit: one file's conversion OR one coherent pattern application across one file.

**Pre-phase micro-audit output**: Per-file table with columns (function count, estimated pattern mix, estimated post-count, scar intersections, risk tier). Principal-engineer produces this before first commit of Phase 4.

**Expected outcome**: Remaining clients/ to ~200-250 total. Combined with Phases 1-3 delivers the 880 -> 200-250 target.

**Risk**: VARIABLE. `*_cache.py` files are more likely to contain scar-sensitive behavior (SCAR-004 cache coherence; SCAR-005/006 cascade) -- higher risk. `test_name_resolver.py` touches resolver behavior (SCAR-020 adjacent but scar test is in `models/business/matching/test_normalizers.py`).

**Revertibility**: Per-commit atomic. Each file's commit independently revertible.

**Scar intersections**:
- `*_cache.py` files: SCAR-004 territory (shared CacheProvider contract). Do NOT refactor cache-coherence assertions; Pattern E decision tree category 1 applies.
- `test_name_resolver.py`: low-risk but verify no SCAR-020 assertions leak in.
- `test_tasks_dependents.py` and `test_tasks_duplicate.py`: Pattern C heavy opportunity.

**Verification**: Same as Phase 1 + per-file coverage delta reported in sprint-3 audit log.

---

### Phase 5: `unit/models/` Post-Cleanup Parametrize

**Scope**: `tests/unit/models/` excluding `business/matching/test_normalizers.py` (SCAR-020) and `contracts/` subdirectory.

**Primary patterns**: D (field-assertion) + A-like matrix parametrize across model classes where the same serialize-roundtrip pattern repeats.

**Commit decomposition**: Pre-phase micro-audit required before commit 1. `test_models.py` (1144 lines) is the largest target -- Pattern D applies to `TestTaskSerialization::test_create_from_full_api_response` and similar monoliths in `TestNestedObjectHandling`, `TestFieldAliasHandling`, `TestTaskInheritance`.

- `CRU-S3-060`: Pattern D fuse of `test_create_from_full_api_response` (38 assertions -> 38 parametrize cases; function count stays 1 but failure-granularity improves)
- `CRU-S3-061`: Cross-model Pattern A fuse where serialization roundtrip pattern repeats across Task/Project/User/Workspace
- `CRU-S3-062` onwards: `test_common_models.py`, `test_custom_field_accessor.py`, `test_section_timeline.py`, `test_task_custom_fields.py`, `business/*` files

**Pre-phase micro-audit output**: Models directory function-count inventory; identify which monolith tests benefit from Pattern D; identify cross-model parametrize opportunities.

**Expected outcome**: models/ >=30% function reduction per shape exit criteria. Because Pattern D does not reduce function count (only improves diagnosis granularity), the 30% reduction must come from Pattern A-style cross-model consolidation.

**Risk**: HIGH. `models/` contains scar-adjacent coverage (SCAR-005/006 cascade, SCAR-020 phone normalizer, SCAR-023 offer cascade). A false consolidation can eliminate sole-coverage lines.

**Revertibility**: Per-commit atomic.

**Scar intersections**:
- `models/business/matching/test_normalizers.py` (SCAR-020): PRESERVE entirely
- `models/business/test_*.py` (various SCARs): audit per-file before touching
- `models/contracts/`: out of scope

**Verification**: Same as Phase 1 + model-specific coverage delta + sole-coverage-line verification (each removed/consolidated test MUST NOT be the sole coverage provider for any source line).

---

## Scar-Tissue Preservation Matrix

Every phase is audited against the 33-scar catalog (`.know/scar-tissue.md`). The matrix below enumerates scar-phase intersections and the preservation strategy.

| Scar | Test Location | Phase Intersection | Preservation Strategy |
|------|---------------|--------------------|-----------------------|
| SCAR-001 | `tests/unit/core/test_project_registry.py:225-270` | None (core/ out of scope) | N/A |
| SCAR-001 (register consolidation) | `tests/unit/core/test_registry_consolidation.py` | None | N/A; do not touch in sprint-3 |
| SCAR-002 | `tests/unit/dataframes/test_section_persistence_storage.py` | None (dataframes/ sprint-4) | N/A |
| SCAR-003 | `tests/unit/api/routes/test_admin_force_rebuild.py` | None (api/ out of scope) | N/A |
| SCAR-004 | No dedicated test (known gap) | Phase 4 `*_cache.py` | Do NOT remove cache-coherence assertions; Pattern E decision tree category 1 |
| SCAR-005/006 | `tests/unit/dataframes/builders/test_cascade_validator.py`, `test_warmup_ordering_guard.py`, `test_cascade_ordering_assertion.py` | None (sprint-4) | N/A |
| SCAR-007 | `tests/unit/dataframes/builders/test_build_result.py` | None | N/A |
| SCAR-008 | No dedicated test | None | N/A |
| SCAR-009 | Various (test env setup) | Phase 1-4 indirectly | Preserve all `ASANA_WORKSPACE_GID` fixtures |
| SCAR-010/010b | `tests/unit/persistence/test_session_concurrency.py` | None (persistence/ sprint-4) | N/A |
| SCAR-011/011b | health tests | None | N/A |
| SCAR-012 | auth tests | None | N/A |
| SCAR-013 | import-fallback path (known gap) | None | N/A |
| SCAR-014 | lifecycle config tests | None | N/A |
| SCAR-015 | I/O heavy warm-up tests | None | N/A |
| SCAR-016/017/018/019 | automation/polling tests | None (sprint-4) | N/A |
| SCAR-020 | `tests/unit/models/business/matching/test_normalizers.py:65-67` | Phase 5 (models/) | EXCLUDE entirely; do not touch file |
| SCAR-020 also | `tests/unit/api/test_routes_resolver.py:565` | None | N/A |
| SCAR-021 | mypy gate | None | N/A |
| SCAR-022 | Dockerfile | None | N/A |
| SCAR-023 | `tests/unit/dataframes/builders/test_cascade_validator.py` | None (sprint-4) | N/A |
| SCAR-024 | `tests/unit/models/business/matching/test_normalizers.py:65` | Phase 5 | EXCLUDE |
| SCAR-025 | asset_edit behavior | None | N/A |
| SCAR-026 | Workflow mocks (no systematic test) | Phase 3 (`test_tasks_client.py`), Phase 4 (cache files using MagicMock) | Add `spec=` under PARALLEL `chore(tests): SCAR-026` commits BEFORE Pattern E; never fold into `CRU-S3-NNN` commits |
| SCAR-027 | `tests/unit/core/test_creation.py` (12 cases, already parametrize-shape) | None (core/ out of scope) | N/A; do NOT touch |
| SCAR-028 | `tests/unit/services/test_gid_push.py` | None | N/A |
| SCAR-029 | 45 webhook adversarial tests | Phase 2 (tier-2 webhooks) | PRESERVE all signature-and-GID-validation tests unchanged; Pattern E NOT applicable to security contract tests |
| SCAR-030 | `tests/unit/models/business/*` section-name tests | Phase 5 (models/business/) | AUDIT per-file before touching |
| SCAR-S3-LOOP | `tests/unit/core/test_retry.py` (86 tests), `tests/unit/dataframes/test_storage.py` (63 tests) | None (sprint-4) | N/A |
| Env Var Naming | settings.py tests | None | N/A |
| SCAR-IDEM-001 | idempotency middleware tests | None | N/A |
| SCAR-REG-001 | `reconciliation/section_registry.py` import-time validation | None | N/A |
| SCAR-WS8 | None (route precedence, no regression test) | None | N/A |

**Operational rule**: Before each commit, principal-engineer runs the scar sweep (section below). If any scar test fails, the commit is rolled back and the affected test is added to the preservation list for the next attempt.

---

## Coverage Verification Protocol

### Per-Commit (fast)

```bash
uv run pytest tests/ -x --timeout=120 -q -m 'not integration and not benchmark'
uv run ruff check src/ tests/
```

Assert: all pass. Commit message format: `refactor(tests): CRU-S3-NNN -- <description>`.

### Per-File (within a commit touching a single file)

```bash
# Before conversion:
uv run pytest tests/unit/clients/test_<file>.py --cov=src/autom8_asana --cov-report=term:skip-covered \
  --timeout=60 -q 2>&1 | tee /tmp/cov-before.txt

# After conversion:
uv run pytest tests/unit/clients/test_<file>.py --cov=src/autom8_asana --cov-report=term:skip-covered \
  --timeout=60 -q 2>&1 | tee /tmp/cov-after.txt

diff <(grep -E '^src/' /tmp/cov-before.txt | sort) <(grep -E '^src/' /tmp/cov-after.txt | sort)
```

**Acceptable delta**: +/-0.1% per module (as reported by cov-term per-file rows). Any module showing a >0.1% drop triggers STOP-AND-INVESTIGATE: the consolidation likely collapsed a behavioral assertion that was the sole coverage provider for a code path.

### Per-Phase (end of phase)

```bash
# Full suite coverage gate
uv run pytest tests/ --cov=src --cov-report=term --cov-fail-under=80 --timeout=120 \
  -m 'not integration and not benchmark' 2>&1 | tail -30
```

Assert: total coverage >= 80% (baseline 87.61%). If coverage falls below 80%, ROLLBACK the last commit and re-diagnose.

### Per-Phase Scar Sweep

```bash
uv run pytest \
  tests/unit/core/test_entity_registry.py \
  tests/unit/core/test_project_registry.py \
  tests/unit/core/test_registry_consolidation.py \
  tests/unit/core/test_creation.py \
  tests/unit/reconciliation/test_section_registry.py \
  tests/unit/dataframes/test_cascade_ordering_assertion.py \
  tests/unit/dataframes/test_warmup_ordering_guard.py \
  tests/unit/dataframes/test_storage.py \
  tests/unit/core/test_retry.py \
  tests/unit/models/business/matching/test_normalizers.py \
  tests/unit/dataframes/builders/test_cascade_validator.py \
  tests/unit/services/test_gid_push.py \
  tests/unit/api/test_routes_resolver.py \
  tests/unit/api/routes/test_admin_force_rebuild.py \
  tests/unit/automation/polling/test_config_schema.py \
  tests/unit/dataframes/builders/test_build_result.py \
  tests/unit/dataframes/test_section_persistence_storage.py \
  -q --timeout=60
```

Assert: 238+ passing (per hygiene handoff baseline established 2026-04-15). If any scar test fails, ROLLBACK and re-diagnose.

### Per-Sprint Final Verification

1. Full test suite green under xdist (4-shard parallel)
2. Coverage >=80% with `--cov-fail-under=80` passing
3. Function-count reduction matches target (880 -> 200-250 for clients/; >=30% for models/)
4. Sprint audit log produced at `.sos/wip/crucible/sprint-3-parametrize-campaign-log.md`
5. Return-handoff artifact produced at `.ledge/spikes/crucible-10xdev-to-hygiene-handoff.md`

---

## Conversion Semantics Rules

These rules are non-negotiable for every parametrize conversion.

1. **One-to-one case mapping**: every original test function maps to exactly one parametrize case OR is retained standalone. No function is silently dropped. If a removal is intentional (e.g., framework-testing waste missed in sprint-2), it goes in a separate commit under `refactor(tests): CRU-S3-NNN -- remove <description>`, NOT fused with a parametrize commit.

2. **Parametrize-id deterministic**: every parametrize case has an explicit `ids=[...]` or `ids=lambda p: ...` argument. No pytest-default auto-ids (`0`, `1`, `2`). See ADR below.

3. **Behavioral preservation**: every assertion from the original tests survives in some form in the consolidated test. If an assertion is dropped, the commit message MUST document it with rationale (e.g., "drop `assert_called_once` -- return value observation supersedes per Pattern E category 2").

4. **No shared mutable state across parametrize cases**: `mock_http.reset_mock()` or fresh fixtures per case. Violation = false-green test where case N's state leaks into case N+1. If a fixture is inherently stateful (e.g., counters), use `@pytest.fixture` (default function scope) or explicit reset.

5. **Scar tests NEVER fused**: any test file listed in the Scar-Tissue Preservation Matrix is excluded from the conversion. If a scar test is adjacent to a convert target in the same file, the scar test is left unchanged and the conversion skips it (document in commit message: "preserves SCAR-NNN at test_<name>").

6. **`spec=` preservation**: if a test uses `MagicMock(spec=X)` or `AsyncMock(spec=X)`, the `spec=` annotation is preserved in the converted test. If a test uses bare `MagicMock()`, the conversion MAY add `spec=` (follows SCAR-026 track) but MUST NOT remove it.

7. **Class hierarchy collapse allowed but explicit**: nested `TestWorkspacesClientGetAsync` classes with single tests may be replaced by a top-level parametrized function. However, if the class has a class-level `setup_method` or `@classmethod` setup, the conversion must replace that with an explicit fixture.

8. **Parametrize over BOTH axes if both axes are being tested**: do not serialize two parametrize decorators if they are orthogonal. Use `pytest.mark.parametrize` with a flat tuple OR stacked decorators for cartesian product. Choose the flat tuple when the (client, raw) cross is sparse; use stacked decorators when the product is fully populated.

9. **Preserve TDD-intentional structure**: adversarial test files (e.g., webhook signature verification, 45 GID-validation cases) have intentional test-case structure reflecting security properties. Flatten ONLY obviously redundant copies; preserve the adversarial topology.

10. **Commit message quality**: every CRU-S3-NNN commit message must include: (a) files changed, (b) pattern applied (A/B/C/D/E), (c) function-count before/after, (d) consolidation ratio, (e) scar intersection notes if any.

---

## ADR: Parametrize ID Convention

### Status

APPROVED (within this TDD)

### Context

Sprint-3 will produce ~150-200 parametrize blocks across clients/ and models/. Each block needs deterministic `ids=` to make pytest output debuggable. Three options considered:

**Option 1: Original function name suffix**
```python
ids=["returns_workspace_model", "raw_returns_dict", "fails_in_async_context"]
```
Pros: Preserves the string used to grep for specific tests; easy to map backwards from a failing CI run to the original test.
Cons: Verbose; duplicates the test function name prefix; breaks down when Pattern A fuses cases across client classes (each case has a different "original" name).

**Option 2: Descriptive test-case labels**
```python
ids=["Workspace with full fields", "User with email only", "Project archived"]
```
Pros: Human-readable; surfaces intent.
Cons: Subjective; inconsistent across authors; harder to grep; no mechanical mapping back to original test.

**Option 3: Structured naming `{subject}_{variant}`**
```python
ids=["workspaces_get", "users_get", "projects_get", "sections_get", "custom_fields_get"]  # Pattern A
ids=["async", "sync"]                                                                      # Pattern B
ids=["typed_model", "raw_dict"]                                                            # Pattern C
ids=lambda p: p                                                                            # Pattern D (field path as id)
```
Pros: Deterministic, greppable, short, per-pattern convention is predictable. Mechanical mapping back: `test_get_async_returns_model[workspaces_get]` clearly came from `TestWorkspacesClientGetAsync::test_get_async_returns_workspace_model`.
Cons: Author must choose a convention per pattern (governed by this ADR).

### Decision

**Option 3 (Structured naming)** with per-pattern conventions:

| Pattern | ID Convention | Example |
|---------|---------------|---------|
| A (cross-client) | `{client_short}_{method}` | `workspaces_get`, `users_list` |
| B (sync/async) | `async` / `sync` | `async`, `sync` |
| C (raw=True) | `typed_model` / `raw_dict` | `typed_model`, `raw_dict` |
| D (field-assertion) | field path string | `gid`, `assignee.gid`, `num_subtasks` |
| E (boundary refactor) | inherits Pattern applied | N/A standalone |
| Cartesian (A x C) | `{client_short}_{method}_{variant}` | `workspaces_get_typed`, `users_get_raw` |

Client short names: `workspaces`, `users`, `projects`, `sections`, `custom_fields`, `tasks`, `webhooks`, `teams`, `attachments`, `tags`, `goals`, `portfolios`, `stories`.

### Rationale

1. **Deterministic**: two authors converting the same code will produce the same ids.
2. **Greppable**: `pytest -k "workspaces_get"` selects exactly the Workspace-get case.
3. **Mechanical traceback**: a failing `test_xxx[workspaces_get]` maps to the original `TestWorkspacesClientGetAsync` by table lookup.
4. **Composable under cartesian**: stacked parametrize decorators produce `[workspaces_get-async-typed_model]` which remains readable.
5. **Pattern D special case**: field-path ids reuse the dotted attribute access expression (e.g., `assignee.gid`) which is self-documenting.

### Consequences

**Positive**:
- CI failure triage is fast; no mental translation from parametrize-index to original intent.
- Author guidance is reduced to five rules (one per pattern), lowering review burden.
- Backward mapping from the converted test to the commit-history original function is mechanical.

**Negative**:
- Requires a short-name table for clients (13 entries; documented above).
- Pattern D's `ids=lambda p: p` only works when the first parametrize value is a string; mixed-type tuples need `ids=lambda p: p if isinstance(p, str) else None` which has a documented fallback.

**Neutral**:
- Does not reduce function count; purely governs readability and diagnosis.

### Reversibility

Two-way door. If the convention proves awkward, a find/replace across `ids=[...]` strings can re-label without semantic change. Parametrize ids are not load-bearing for any scar test.

---

## Risk Register

| Risk | Phase | Likelihood | Impact | Mitigation |
|------|-------|------------|--------|-----------|
| Cross-client Pattern A produces asymmetric assertions forcing per-case complexity | 1, 2 | M | M | Accept per-case `extra_assertions: dict[str, Any]` tuple field; if 3+ cases need it, revert to pattern-B fuse instead |
| Pattern E over-removes assertions, eliminating Asana-contract verification | 3, 4 | M | H | Pattern E decision tree (category 1/2/3) is MANDATORY; treat URL/verb assertions as contract; remove only call-count redundancies |
| `client_factory` fixture asymmetry (some clients take `cache_provider`, some don't) creates test-construction failures | 1, 2 | M | L | `client_factory(cls, use_cache=False)` documented; verify per-client at conversion time |
| Scar test coverage loss via over-consolidation in Phase 5 | 5 | M | H | Per-file sole-coverage-line verification BEFORE any consolidation; scar preservation matrix enforced |
| `spec=` absence masks non-existent method calls post-Pattern-E | 3, 4 | M | M | Parallel SCAR-026 track: add `spec=` in separate `chore(tests)` commits BEFORE Pattern E on that file |
| xdist parallel interference from shared-state parametrize | all | L | M | Conversion Semantics Rule 4: no shared mutable state; fixture function-scope default; explicit `reset_mock()` when needed |
| Cumulative commit count triggers PR review fatigue, producing rubber-stamp review | all | H | M | Principal-engineer groups commits by file into logical PR clusters; each cluster <=8 commits; qa-adversary reviews per-cluster |
| Test-id collisions under cartesian parametrize producing ambiguous failures | all | L | L | ADR convention prevents collisions by construction; pytest will raise at collection if ids collide |
| `test_batch.py` accidentally drawn into scope due to prevalence heuristics | 4 | L | H | EXPLICIT exclusion list referenced by every Phase-4 commit |
| `tests/unit/clients/data/` accidentally touched (TENSION-001 violation) | 4 | L | H | EXPLICIT file path check in every Phase-4 commit; architect-enforcer escalation on any touch attempt |
| Consolidation ratio drops below 2:1 on average | 1-5 | M | M | Per-commit metric in commit message; if 3 consecutive commits are <2:1, STOP and reassess pattern mix |
| Principal-engineer runs Phase 5 before Phase 1-4 complete | 5 | L | M | Sequential phase gate: Phase N+1 does not start until Phase N scar sweep + coverage gate pass |

---

## Success Criteria

Phase-by-phase gate-based success criteria. A phase is "complete" only when all row-1 criteria are green.

| Criterion | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|-----------|---------|---------|---------|---------|---------|
| Function-count reduction | 51 -> 12-15 | 71 -> 15-20 | >=20% | To ~200-250 total clients/ | >=30% models/ |
| Consolidation ratio (avg across commits in phase) | >=3.4:1 | >=3.5:1 | >=2:1 | >=2:1 | >=2:1 (A-pattern) |
| Coverage delta (per-file, absolute) | within +/-0.1% | within +/-0.1% | within +/-0.1% | within +/-0.1% | within +/-0.1% |
| Total coverage | >=80% | >=80% | >=80% | >=80% | >=80% |
| Scar sweep passes | 238+ | 238+ | 238+ | 238+ | 238+ |
| Ruff clean | yes | yes | yes | yes | yes |
| Parametrize ID convention compliant | yes | yes | yes | yes | yes |
| Independent-revertibility (sample 3 commits, revert + re-verify) | pass | pass | pass | pass | pass |
| SCAR-026 `spec=` track advanced (or not regressed) | track | track | track | track | N/A |

### Sprint Success (all must be true)

- `tests/unit/clients/` function count: 880 -> 200-250 (>=50% reduction)
- `tests/unit/models/` function count: >=30% reduction
- Parametrize rate across converted files: >=15%
- `raw=True` split consolidated via Pattern C in all converted client files
- sync/async split consolidated via Pattern B in all converted client files
- `test_tier1_clients.py` + `test_tier2_clients.py`: 122 -> <=35 combined
- All 33 scar-tissue regression tests pass
- Coverage >=80%
- Each conversion independently revertible
- Sprint audit log at `.sos/wip/crucible/sprint-3-parametrize-campaign-log.md`
- Return-handoff to hygiene at `.ledge/spikes/crucible-10xdev-to-hygiene-handoff.md`

---

## Implementation Guidance

- **Start with Phase 1, commit 1 (`CRU-S3-001`)**: it is the canonical cross-client Pattern A. If it lands cleanly, the rest of Phase 1 follows mechanically. If it fails, the pattern needs refinement before scaling.
- **Use `pytest -k` for targeted re-runs during development**: `pytest tests/unit/clients/test_tier1_clients.py -k "get_async" -v` to see parametrize-id surfacing.
- **Before Phase 4 and Phase 5**: produce the micro-audit table (per-file function count, pattern-mix estimate, scar intersections, risk tier). Do NOT start first commit of these phases without the audit.
- **Defer ambiguity**: if a conversion looks like it fits Pattern A but asymmetric assertions produce a 4-entry `extra_assertions` dict, STOP. Reassess: Pattern B may be the better fit. It is better to have two medium-consolidation conversions than one over-stretched Pattern A that becomes unmaintainable.
- **Commit atomicity check**: after each commit, run `git diff HEAD^ --stat` and verify only expected files changed. A stray change to `src/` means the commit is NOT ready.

## Open Items

1. **Phase 4 pre-audit**: principal-engineer produces per-file function-count + pattern-mix estimate for residual `clients/` files before starting commit `CRU-S3-030`. Estimated output: a table in the sprint-3 audit log.
2. **Phase 5 pre-audit**: same, for `tests/unit/models/` excluding scar-sensitive files. Output: same location.
3. **SCAR-026 parallel track**: principal-engineer may run `chore(tests): SCAR-026 -- add spec= to <file>` commits concurrent with Phase 3/4, but these commits MUST NOT be interleaved into `CRU-S3-NNN` sequence. Separate PR recommended.
4. **Return-handoff drafting**: qa-adversary produces `crucible-10xdev-to-hygiene-handoff.md` at sprint-3 wrap, cataloging any boundary-inversions discovered beyond sprint-2 audit scope.

## ADRs (summary table)

| ID | Title | Status |
|----|-------|--------|
| ADR-PARAM-IDS (this TDD) | Parametrize ID convention (Option 3, structured naming) | APPROVED |

---

**End of TDD.**
