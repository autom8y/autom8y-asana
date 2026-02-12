# Refactoring Plan -- Phase 3 WS-6: Conftest Hierarchy & Fixture Consolidation

**Initiative**: Deep Code Hygiene -- autom8_asana
**Session**: session-20260210-230114-3c7097ab
**Agent**: architect-enforcer
**Date**: 2026-02-11
**Input**: `.claude/artifacts/smell-report-phase3.md` (WS-6: SM-201 through SM-214)
**Test Baseline**: 9,138 tests passed (post WS-7)

---

## Architectural Assessment

The test infrastructure suffers from a systemic DRY violation: ~1,900 lines of duplicated mock classes and fixture definitions across 14 findings. This is not an architectural boundary problem -- it is a test infrastructure maturity problem. The production code boundaries are sound; the test support code simply grew organically without consolidation.

**Root cause**: Each test file was written independently, copy-pasting the mock classes and fixtures it needed. No shared test infrastructure layer was established early. The project does have `tests/_shared/mocks.py` (containing `MockTask`), proving the pattern is viable -- it was just never extended to the core mock classes.

**Boundary health**: Good. The mock classes model production protocols correctly (HTTP client, auth provider, logger, cache provider). The fixture naming is mostly consistent within groups. The root conftest already handles singleton reset correctly.

---

## Architectural Decisions

### Decision 1: Conftest Hierarchy

```
tests/
  conftest.py (ROOT -- exists)
    - MockHTTPClient class (superset)
    - MockAuthProvider class
    - MockLogger class (superset)
    - mock_http fixture
    - config fixture
    - auth_provider fixture
    - logger fixture
    - reset_settings_singleton (exists, autouse)
    - reset_registries (exists, autouse)
    - MockClientBuilder (exists)
    - mock_client_builder (exists)

  _shared/
    mocks.py (exists -- MockTask; NO CHANGES)

  unit/
    clients/
      conftest.py (NEW)
        - MockCacheProvider class
        - FailingCacheProvider class
        - cache_provider fixture

  unit/
    cache/
      conftest.py (NEW)
        - mock_batch_client fixture

  api/
    conftest.py (exists -- NO WS-6 CHANGES, already has its own fixtures)

  integration/
    conftest.py (exists -- REMOVE duplicate mock classes/fixtures after root conftest has them)
```

**Rationale**: Mock classes and their fixtures belong at the root conftest level because they are used by both unit AND integration tests. The `tests/_shared/mocks.py` module exists but is reserved for domain mock objects (MockTask), not pytest fixtures. Putting mock classes in conftest.py makes them automatically available to all tests via pytest's fixture discovery -- no explicit imports needed. MockCacheProvider is scoped to `tests/unit/clients/` because only the 6 client cache test files use it, and it has a domain-specific protocol tied to CacheEntry/EntryType. The `mock_batch_client` is scoped to `tests/unit/cache/` because 4 of 5 module-level definitions are in cache tests.

### Decision 2: Mock Class Placement

**Decision**: Option A -- In conftest files alongside fixtures.

**Rationale**: Conftest files are the idiomatic pytest location for test infrastructure. Classes defined in conftest are importable if needed (via `from tests.conftest import MockHTTPClient`) but the primary consumption path is through fixtures, which pytest discovers automatically from conftest. This avoids the need for explicit imports in test files.

### Decision 3: Variant Handling

**Decision**: Single superset class for both MockHTTPClient and MockLogger.

- **MockHTTPClient**: The Extended variant (7 methods: get, post, put, delete, get_paginated, post_multipart, get_stream_url) is a strict superset of Basic (5 methods). Unused AsyncMock methods on the instance do nothing and cause zero test interference -- they are never called by tests that don't need them, so no assertion failures.
- **MockLogger**: The Extended variant (5 methods: debug, info, warning, error, exception) is a strict superset of Basic (4 methods). The `exception` method simply appends to `self.messages` like the others. Tests that never call `logger.exception()` are unaffected.

**Risk assessment**: Zero. AsyncMock/MagicMock attributes that are never accessed cause no side effects. The mock objects have no validation or enforcement of "only these methods exist." This is a strictly additive change.

### Decision 4: SM-210 (clean_registries) -- Partially Redundant

**Decision**: The per-file `clean_registries` fixtures are PARTIALLY redundant but CANNOT be blindly deleted.

**Analysis**:
- The root conftest `reset_registries` (autouse) resets 4 registries (ProjectTypeRegistry, WorkspaceProjectRegistry, SchemaRegistry, EntityProjectRegistry) before AND after every test.
- Per-file `clean_registries` resets 2 registries (ProjectTypeRegistry, WorkspaceProjectRegistry) before and after.
- Per-file `clean_registry` (singular) resets 1 registry (ProjectTypeRegistry) before and after.

The teardown half is fully redundant (root conftest already does it). The setup half is also handled by root conftest. HOWEVER, these fixtures serve as **explicit dependency markers** -- tests declare `clean_registries: None` as a fixture parameter to indicate "this test configures registries during setup." For example, `business_task(clean_registries: None)` ensures the registry is reset before configuring it with business project data.

Since root conftest's `reset_registries` is autouse and runs before every test, the `clean_registries` fixture is doing redundant work. But tests that use it as a dependency parameter need a migration path.

**Action**: Delete the per-file `clean_registries`/`clean_registry` definitions. Tests that referenced them as parameters can simply remove the parameter -- the root conftest autouse fixture already guarantees clean state. For fixtures that chain through clean_registries (e.g., `business_task(clean_registries: None)`), remove the parameter.

### Decision 5: Naming Convention

**Decision**: Use `mock_` prefix for all mock-returning fixtures.

| Current Name | New Name | Rationale |
|---|---|---|
| `mock_http` | `mock_http` | Already uses prefix. Keep as-is. |
| `config` | `config` | Returns real `AsanaConfig()`, not a mock. No prefix needed. |
| `auth_provider` | `auth_provider` | Returns `MockAuthProvider()` but is typed as the protocol. Convention: name after what it provides, not what it is. Keep as-is. |
| `logger` | `logger` | Same reasoning as auth_provider. Keep as-is. |
| `mock_auth` (integration/conftest) | REMOVE | Integration conftest defines `mock_auth` returning `MockAuthProvider()`. This duplicates `auth_provider`. Consolidate to `auth_provider` in root conftest. |
| `mock_logger` (integration/conftest) | REMOVE | Integration conftest defines `mock_logger` returning `MockLogger()`. Consolidate to `logger` in root conftest. |

**Rationale**: Renaming fixtures would break every test that references them. The current names (`auth_provider`, `logger`, `config`) are fine -- they describe what the fixture provides, not its implementation. The 2 outlier names (`mock_auth`, `mock_logger`) are only in `tests/integration/conftest.py` and can be aliased during migration, but the integration conftest's own `client_fixture` references `mock_auth` and `mock_logger`, so those references must be updated.

### Decision 6: Low-ROI Findings (SM-211 through SM-214)

**Threshold**: Consolidate if 4+ files AND fixtures are identical. Defer if <4 files or if fixtures differ.

| ID | Finding | Files | Identical? | Decision |
|---|---|---|---|---|
| SM-211 | `mock_invalidator` | 4 | **No** -- API tests use `spec=MutationInvalidator` with `fire_and_forget`; service tests return plain `MagicMock()` | **DEFER** -- variants are semantically different |
| SM-212 | `mock_batch_client` | 5 module + 3 class | **Partially** -- 4 cache tests identical (MagicMock + execute_async=AsyncMock); integration test is different; 3 class-scoped are different | **CONSOLIDATE** the 4 identical cache tests to `tests/unit/cache/conftest.py` |
| SM-213 | `reset_cache_ready` | 3 | Yes, all `set_cache_ready(True) / yield / set_cache_ready(True)` but different parent directories (api/ and unit/api/) | **DEFER** -- only 3 files, cross-directory, autouse semantics |
| SM-214 | `mock_service_claims` | 3 | **No** -- API tests use `sub="service-123"`, integration test uses `sub="service:test_service"` | **DEFER** -- different test data |

### Decision 7: Fixture Scope

**Decision**: All consolidated fixtures remain `function`-scoped (the pytest default).

Every single per-file fixture being consolidated is function-scoped (no `scope=` parameter). The consolidated versions must also be function-scoped. Changing scope to `session` or `module` would cause mock state to leak between tests (e.g., `MockHTTPClient` instances have `AsyncMock` attributes that record call history -- sharing them across tests would cause false positives/negatives).

---

## Refactoring Tasks

### Phase 1: Consolidate Mock Classes + Core Fixtures to Root Conftest (LOW RISK)

#### RF-201: Add MockHTTPClient, MockAuthProvider, MockLogger to root conftest

**Before State:**
- `tests/conftest.py`: Has MockClientBuilder, reset_settings_singleton, reset_registries
- MockHTTPClient defined in 18 files (SM-201)
- MockAuthProvider defined in 26 files (SM-202)
- MockLogger defined in 10 files (SM-203)

**After State:**
- `tests/conftest.py`: Gains 3 mock classes (superset variants)
  ```python
  class MockHTTPClient:
      def __init__(self) -> None:
          self.get = AsyncMock()
          self.post = AsyncMock()
          self.put = AsyncMock()
          self.delete = AsyncMock()
          self.get_paginated = AsyncMock()
          self.post_multipart = AsyncMock()
          self.get_stream_url = AsyncMock()

  class MockAuthProvider:
      def get_secret(self, key: str) -> str:
          return "test-token"

  class MockLogger:
      def __init__(self) -> None:
          self.messages: list[tuple[str, str]] = []
      def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
          self.messages.append(("debug", msg))
      def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
          self.messages.append(("info", msg))
      def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
          self.messages.append(("warning", msg))
      def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
          self.messages.append(("error", msg))
      def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
          self.messages.append(("exception", msg))
  ```

**Invariants:**
- MockHTTPClient is the 7-method superset (Extended variant)
- MockAuthProvider returns `"test-token"` from `get_secret()`
- MockLogger is the 5-method superset (Extended variant)
- All method signatures identical to current implementations

**Verification:**
1. Run: `.venv/bin/pytest tests/ -x -q --timeout=60`
2. Result: 9,138 tests pass
3. No test file should fail due to missing class

**Rollback**: Revert single commit

---

#### RF-202: Add mock_http, config, auth_provider, logger fixtures to root conftest

**Before State:**
- `mock_http` defined in 18 files (Pattern A from SM-204)
- `config` defined in 19 files (SM-205)
- `auth_provider` defined in 18 files (SM-206)
- `logger` defined in 9 files (SM-207)

**After State:**
- `tests/conftest.py` gains 4 fixtures:
  ```python
  @pytest.fixture
  def mock_http() -> MockHTTPClient:
      return MockHTTPClient()

  @pytest.fixture
  def config() -> AsanaConfig:
      return AsanaConfig()

  @pytest.fixture
  def auth_provider() -> MockAuthProvider:
      return MockAuthProvider()

  @pytest.fixture
  def logger() -> MockLogger:
      return MockLogger()
  ```

**Invariants:**
- `mock_http` returns `MockHTTPClient()` (function scope, new instance per test)
- `config` returns `AsanaConfig()` (no-arg construction)
- `auth_provider` returns `MockAuthProvider()` (function scope)
- `logger` returns `MockLogger()` (function scope)
- None are autouse
- `AsanaConfig` import added to root conftest

**Verification:**
1. Run: `.venv/bin/pytest tests/ -x -q --timeout=60`
2. Result: 9,138 tests pass
3. Fixtures are discoverable from any test directory

**Rollback**: Revert single commit

---

**ROLLBACK POINT A**: After RF-201 + RF-202, run full test suite. If green, proceed. If red, revert and investigate. These two tasks form one commit.

---

### Phase 2: Remove Per-File Duplicates (MEDIUM RISK -- many file edits)

#### RF-203: Remove MockHTTPClient + mock_http from 17 unit test files

**Before State:**
Per SM-201/SM-204, the following files define both `class MockHTTPClient` and `def mock_http()`:
1. `tests/unit/test_tasks_client.py`
2. `tests/unit/test_batch.py`
3. `tests/unit/test_batch_adversarial.py`
4. `tests/unit/test_tier1_clients.py`
5. `tests/unit/test_tier1_adversarial.py`
6. `tests/unit/test_tier2_clients.py`
7. `tests/unit/test_tier2_adversarial.py`
8. `tests/unit/test_coverage_gap.py`
9. `tests/unit/clients/test_tasks_cache.py`
10. `tests/unit/clients/test_custom_fields_cache.py`
11. `tests/unit/clients/test_projects_cache.py`
12. `tests/unit/clients/test_sections_cache.py`
13. `tests/unit/clients/test_stories_cache.py`
14. `tests/unit/clients/test_users_cache.py`
15. `tests/unit/clients/test_tasks_duplicate.py`
16. `tests/unit/clients/test_tasks_dependents.py`
17. `tests/unit/test_client.py` (MockAuthProvider only, no MockHTTPClient -- verify)

**After State:**
- Each file above: Remove `class MockHTTPClient` definition and `def mock_http()` fixture
- Tests in these files use the root conftest's `mock_http` fixture via pytest discovery
- Remove any now-unused imports (e.g., `AsyncMock` if only used by the removed class)

**Invariants:**
- No test references `MockHTTPClient` by class name directly (they use the `mock_http` fixture)
- Fixture name `mock_http` unchanged
- Return type unchanged (MockHTTPClient instance)
- Function scope unchanged

**Verification:**
1. Run: `.venv/bin/pytest tests/unit/ -x -q --timeout=60`
2. All unit tests pass
3. No `class MockHTTPClient` remains in any file under `tests/unit/`

**Rollback**: Revert single commit

---

#### RF-204: Remove MockHTTPClient + mock_http from integration test files

**Before State:**
- `tests/integration/conftest.py`: Defines MockHTTPClient, MockAuthProvider, MockLogger, mock_http (fixture named `mock_http`), mock_auth, mock_logger
- `tests/integration/test_stories_cache_integration.py`: Defines MockHTTPClient, MockAuthProvider, mock_http, auth_provider

**After State:**
- `tests/integration/conftest.py`: Remove MockHTTPClient, MockAuthProvider, MockLogger class definitions. Remove `mock_http` (renamed `mock_auth`), `mock_auth`, and `mock_logger` fixture definitions. Update `client_fixture` to use `auth_provider` and `logger` parameter names instead of `mock_auth` and `mock_logger`.
- `tests/integration/test_stories_cache_integration.py`: Remove MockHTTPClient, MockAuthProvider, mock_http, auth_provider definitions.
- `tests/integration/conftest.py` retains: `reset_registries_after_test`, `client_fixture` (updated to use renamed params), `task_fixture`.

**Critical note**: The integration conftest's `client_fixture` fixture takes parameters `mock_http`, `mock_auth`, `mock_logger`. After consolidation:
  - `mock_http` -- matches root conftest fixture name. Works automatically.
  - `mock_auth` -- must be renamed to `auth_provider` to match root conftest. Update `client_fixture` parameter and body.
  - `mock_logger` -- must be renamed to `logger` to match root conftest. Update `client_fixture` parameter and body.

**Invariants:**
- `client_fixture` still constructs the same mock AsanaClient with same components
- Integration tests still get MockHTTPClient, MockAuthProvider, MockLogger instances
- `reset_registries_after_test` unchanged

**Verification:**
1. Run: `.venv/bin/pytest tests/integration/ -x -q --timeout=60`
2. All integration tests pass

**Rollback**: Revert single commit

---

#### RF-205: Remove MockAuthProvider from remaining unit test files

**Before State:**
Per SM-202, MockAuthProvider is defined in these additional unit files (beyond those already covered by RF-203):
1. `tests/unit/test_client.py`
2. `tests/unit/transport/test_asana_http.py`
3. `tests/unit/transport/test_aimd_integration.py`

Note: `tests/unit/test_phase2a_adversarial.py` has 4 class-scoped `MockAuthProvider` definitions inside fixture methods. These are NOT removed -- they are class-scoped and local to their test classes.

**After State:**
- Remove `class MockAuthProvider` from the 3 files listed above
- Tests use root conftest's MockAuthProvider via `auth_provider` fixture

**Invariants:**
- `auth_provider` fixture name unchanged
- `get_secret()` returns `"test-token"`
- Class-scoped definitions in test_phase2a_adversarial.py preserved

**Verification:**
1. Run: `.venv/bin/pytest tests/unit/test_client.py tests/unit/transport/ -x -q --timeout=60`
2. All tests pass

**Rollback**: Revert single commit

---

#### RF-206: Remove config and auth_provider fixtures from unit test files

**Before State:**
Per SM-205/SM-206, `config` and `auth_provider` fixtures defined in these files (not yet covered by RF-203):
- Files that have ONLY config/auth_provider (not MockHTTPClient): check each file

Note: Most files have all 4 fixtures together (MockHTTPClient, MockAuthProvider, config, auth_provider), so RF-203 should handle them. This task covers any stragglers.

**After State:**
- All per-file `def config()` and `def auth_provider()` definitions removed from unit test files
- Root conftest provides them

**Invariants:**
- `config` returns `AsanaConfig()` (no-arg)
- `auth_provider` returns `MockAuthProvider()`
- No scope changes

**Verification:**
1. Run: `.venv/bin/pytest tests/unit/ -x -q --timeout=60`
2. All unit tests pass
3. `grep -r "def config()" tests/unit/` returns zero matches
4. `grep -r "def auth_provider()" tests/unit/` returns zero matches

**Rollback**: Revert single commit

---

#### RF-207: Remove MockLogger and logger fixture from unit test files

**Before State:**
Per SM-203/SM-207, MockLogger class + `logger` fixture defined in:
1. `tests/unit/test_tasks_client.py`
2. `tests/unit/test_batch.py`
3. `tests/unit/test_batch_adversarial.py`
4. `tests/unit/test_tier1_clients.py`
5. `tests/unit/test_tier1_adversarial.py`
6. `tests/unit/test_tier2_clients.py`
7. `tests/unit/test_tier2_adversarial.py`
8. `tests/unit/test_coverage_gap.py`
9. `tests/integration/test_savesession_partial_failures.py` (also has MockAuthProvider + auth_provider + config)

**After State:**
- Remove `class MockLogger` and `def logger()` from all listed files
- `tests/integration/test_savesession_partial_failures.py`: Also remove MockAuthProvider, auth_provider, config fixtures

**Invariants:**
- `logger` fixture name unchanged
- Returns MockLogger with 5 methods (superset)
- `self.messages` list for recording calls

**Verification:**
1. Run: `.venv/bin/pytest tests/ -x -q --timeout=60`
2. All tests pass
3. `grep -r "class MockLogger" tests/` returns only `tests/conftest.py`

**Rollback**: Revert single commit

---

**ROLLBACK POINT B**: After RF-203 through RF-207, run full test suite. Expected: 9,138 tests pass. If fewer, investigate which test files broke.

---

### Phase 3: Client Cache Fixtures (LOW RISK)

#### RF-208: Create tests/unit/clients/conftest.py with MockCacheProvider

**Before State:**
Per SM-208/SM-209, identical `MockCacheProvider` + `cache_provider` fixture in 6 files:
1. `tests/unit/clients/test_tasks_cache.py`
2. `tests/unit/clients/test_custom_fields_cache.py`
3. `tests/unit/clients/test_projects_cache.py`
4. `tests/unit/clients/test_sections_cache.py`
5. `tests/unit/clients/test_stories_cache.py`
6. `tests/unit/clients/test_users_cache.py`

Also: `FailingCacheProvider` in `test_tasks_cache.py` (keep local -- only used in that file).

**After State:**
- New file `tests/unit/clients/conftest.py` with:
  ```python
  """Shared fixtures for client cache tests."""
  from __future__ import annotations
  from autom8_asana.cache.models.entry import CacheEntry, EntryType
  import pytest

  class MockCacheProvider:
      """Mock cache provider for testing."""
      def __init__(self) -> None:
          self._cache: dict[str, CacheEntry] = {}
          self.get_versioned_calls: list[tuple[str, EntryType]] = []
          self.set_versioned_calls: list[tuple[str, CacheEntry]] = []
          self.invalidate_calls: list[tuple[str, list[EntryType] | None]] = []

      def get_versioned(self, key: str, entry_type: EntryType) -> CacheEntry | None:
          self.get_versioned_calls.append((key, entry_type))
          return self._cache.get(f"{key}:{entry_type.value}")

      def set_versioned(self, key: str, entry: CacheEntry) -> None:
          self.set_versioned_calls.append((key, entry))
          self._cache[f"{key}:{entry.entry_type.value}"] = entry

      def invalidate(self, key: str, entry_types: list[EntryType] | None = None) -> None:
          self.invalidate_calls.append((key, entry_types))
          if entry_types:
              for entry_type in entry_types:
                  self._cache.pop(f"{key}:{entry_type.value}", None)
          else:
              keys_to_remove = [k for k in self._cache if k.startswith(f"{key}:")]
              for k in keys_to_remove:
                  del self._cache[k]

  @pytest.fixture
  def cache_provider() -> MockCacheProvider:
      return MockCacheProvider()
  ```
- Remove MockCacheProvider + cache_provider from the 6 files listed above
- `FailingCacheProvider` remains in `test_tasks_cache.py`

**Invariants:**
- `cache_provider` fixture returns `MockCacheProvider()` (function scope)
- MockCacheProvider has identical API: `get_versioned`, `set_versioned`, `invalidate`
- Internal tracking lists (`get_versioned_calls`, etc.) preserved
- `FailingCacheProvider` unchanged (local to test_tasks_cache.py)

**Verification:**
1. Run: `.venv/bin/pytest tests/unit/clients/ -x -q --timeout=60`
2. All client cache tests pass
3. `grep -r "class MockCacheProvider" tests/unit/clients/` returns only `conftest.py`

**Rollback**: Revert single commit

---

### Phase 4: Cache Test Fixtures (LOW RISK)

#### RF-209: Create tests/unit/cache/conftest.py with mock_batch_client

**Before State:**
Per SM-212, identical `mock_batch_client` fixture in 4 cache test files:
1. `tests/unit/cache/test_freshness_coordinator.py`
2. `tests/unit/cache/test_staleness_coordinator.py`
3. `tests/unit/cache/test_unified.py`
4. `tests/unit/cache/test_lightweight_checker.py`

All return `MagicMock()` with `client.execute_async = AsyncMock(return_value=[])`.

Note: `tests/integration/test_unified_cache_success_criteria.py` has a DIFFERENT `mock_batch_client` (tracks `_call_count`). `tests/unit/persistence/test_action_executor.py` has 3 class-scoped variants using `AsyncMock()` instead of `MagicMock()`. Both are excluded.

**After State:**
- New file `tests/unit/cache/conftest.py`:
  ```python
  """Shared fixtures for cache module tests."""
  from __future__ import annotations
  from unittest.mock import AsyncMock, MagicMock
  import pytest

  @pytest.fixture
  def mock_batch_client() -> MagicMock:
      """Create a mock BatchClient."""
      client = MagicMock()
      client.execute_async = AsyncMock(return_value=[])
      return client
  ```
- Remove `def mock_batch_client()` from the 4 files listed above

**Invariants:**
- `mock_batch_client` returns `MagicMock()` with `execute_async = AsyncMock(return_value=[])`
- Function scope
- Non-autouse

**Verification:**
1. Run: `.venv/bin/pytest tests/unit/cache/ -x -q --timeout=60`
2. All cache unit tests pass

**Rollback**: Revert single commit

---

### Phase 5: Clean Up Redundant Registry Fixtures (LOW RISK)

#### RF-210: Remove redundant clean_registries/clean_registry fixtures

**Before State:**
Per SM-210, `clean_registries` defined in 5 files, `clean_registry` in 4 files. Root conftest's `reset_registries` (autouse) already resets all 4 registries before every test.

Files with `clean_registries`:
1. `tests/integration/test_detection.py:49`
2. `tests/integration/test_workspace_registry.py:40`
3. `tests/integration/test_hydration_cache_integration.py:48`
4. `tests/integration/test_hydration.py:53`
5. `tests/unit/models/business/test_detection.py:69`

Files with `clean_registry`:
1. `tests/unit/models/business/test_detection.py:61`
2. `tests/unit/detection/test_detection_cache.py:47`
3. `tests/unit/models/business/test_registry.py:37`
4. `tests/unit/models/business/test_patterns.py:38`

**After State:**
- Remove the fixture definitions from all 9 files
- For each test/fixture that declares `clean_registries: None` or `clean_registry: None` as a parameter, remove that parameter
- Root conftest's autouse `reset_registries` provides the guarantee

**Important**: Some fixtures chain through `clean_registries`. For example:
```python
@pytest.fixture
def business_task(clean_registries: None) -> Task:
    registry = get_registry()
    registry.register(project_gid, EntityType.BUSINESS)
    ...
```
After removing `clean_registries`, this becomes:
```python
@pytest.fixture
def business_task() -> Task:
    registry = get_registry()
    registry.register(project_gid, EntityType.BUSINESS)
    ...
```
This is safe because root conftest's autouse `reset_registries` runs before any fixture in any test.

**Note on integration conftest**: `tests/integration/conftest.py` has its own `reset_registries_after_test` autouse fixture that resets 2 registries (ProjectTypeRegistry, WorkspaceProjectRegistry) after yield. This is redundant with root conftest but serves as a defense-in-depth pattern. Leave it in place -- removing autouse fixtures from conftest files is higher risk than removing per-test fixtures.

**Invariants:**
- All registries still reset before every test (via root conftest autouse)
- No test relies on clean_registries for anything beyond reset
- Tests that configure registries in fixtures still work (autouse runs first)

**Verification:**
1. Run: `.venv/bin/pytest tests/ -x -q --timeout=60`
2. All 9,138 tests pass
3. `grep -r "def clean_registr" tests/` returns zero matches

**Rollback**: Revert single commit

---

**ROLLBACK POINT C**: After all phases, run full test suite. Expected: 9,138 tests pass.

---

## Deferred Items

| ID | Finding | Reason for Deferral |
|---|---|---|
| SM-211 | `mock_invalidator` (4 files) | Variants are semantically different (spec vs plain MagicMock). Consolidating would require choosing one pattern and potentially breaking tests that rely on spec validation. Only 4 files. |
| SM-213 | `reset_cache_ready` (3 files) | Only 3 files across different directories. Autouse semantics make conftest placement tricky (would need separate conftest for each directory). Low ROI. |
| SM-214 | `mock_service_claims` (3 files) | Different test data (`sub` values differ). Only 3 files. Would need parameterized fixture or factory pattern, adding complexity for minimal gain. |
| SM-204-B | `mock_http` Pattern B (2 files) | `MagicMock()` with explicit methods -- different pattern from `MockHTTPClient()`. Test-specific. |
| SM-204-C | `mock_http` Pattern C (1 file) | Class-scoped `AsyncMock` in `test_phase2a_adversarial.py` -- intentionally class-scoped. |
| SM-202-C | MockAuthProvider in test_phase2a_adversarial.py (4x) | Class-scoped, defined inside fixture methods. Intentionally local. |

---

## Risk Matrix

| Phase | Tasks | Files Changed | Blast Radius | Failure Detection | Rollback Cost |
|---|---|---|---|---|---|
| 1 | RF-201, RF-202 | 1 (root conftest) | Low -- additive only, no removal | Full test suite | 1 commit revert |
| 2 | RF-203 through RF-207 | ~25 files | Medium -- removing definitions | Per-directory test runs, then full suite | 1 commit per task |
| 3 | RF-208 | 7 files (1 new + 6 modified) | Low -- scoped to clients/ | `tests/unit/clients/` test run | 1 commit revert |
| 4 | RF-209 | 5 files (1 new + 4 modified) | Low -- scoped to cache/ | `tests/unit/cache/` test run | 1 commit revert |
| 5 | RF-210 | 9 files | Low -- removing no-ops | Full test suite | 1 commit revert |

---

## Janitor Notes

### Commit Conventions
- One commit per RF-task (except RF-201 + RF-202 which should be a single commit since adding classes and fixtures together is atomic)
- Commit message format: `refactor(tests): RF-2XX <description>`
- Example: `refactor(tests): RF-201+RF-202 add shared mock classes and fixtures to root conftest`

### File Editing Order (Critical)
1. **Always add before removing.** RF-201/RF-202 (add to root conftest) MUST be committed and verified before RF-203-RF-207 (remove from test files). If you remove before adding, tests will fail because the fixtures don't exist yet.
2. **Remove in batches by directory.** Process all files in `tests/unit/clients/` together, then `tests/unit/`, then `tests/integration/`. This makes it easier to verify with directory-scoped test runs.
3. **Update integration conftest carefully.** RF-204 must update `client_fixture` parameter names (`mock_auth` -> `auth_provider`, `mock_logger` -> `logger`) AND update the fixture body references simultaneously.

### Test Requirements
- Run `.venv/bin/pytest tests/ -x -q --timeout=60` after each commit
- Expected result: 9,138 passed at every checkpoint
- If count drops, investigate immediately -- do NOT proceed to next task
- NOT `uv run` -- uv has dependency resolution issues with `autom8y-telemetry`

### Files to NOT Touch
- `tests/unit/test_phase2a_adversarial.py` -- class-scoped mocks, intentionally local
- `tests/integration/test_cache_optimization_e2e.py` -- uses MagicMock pattern, different from MockHTTPClient
- `tests/unit/persistence/test_action_executor.py` -- class-scoped mock_batch_client, different implementation
- `tests/unit/dataframes/test_cache_integration.py` -- uses MagicMock for mock_logger, not MockLogger
- `tests/unit/cache/test_dataframes.py` -- different MockCacheProvider implementation
- `tests/unit/cache/test_stories.py` -- different MockCacheProvider implementation
- `tests/unit/automation/events/test_rule.py` -- `config` returns `EventRoutingConfig`, NOT `AsanaConfig`
- `tests/api/conftest.py` -- has its own specialized fixtures for FastAPI testing, no overlap with WS-6 targets

### Import Cleanup
When removing a mock class from a file, check if any imports become unused:
- `AsyncMock` -- may still be used by other test code in the file
- `Any` from typing -- may still be used by remaining code
- Only remove imports that become truly unused after the mock class removal

### Handling the integration/conftest.py Transition (RF-204)
The `client_fixture` in `tests/integration/conftest.py` currently references `mock_auth` and `mock_logger`:
```python
@pytest.fixture
def client_fixture(mock_http, mock_auth, mock_logger):
    ...
    client._auth_provider = mock_auth
    client._log = mock_logger
    ...
```
After removing the local `mock_auth` and `mock_logger` fixtures, this must be updated to:
```python
@pytest.fixture
def client_fixture(mock_http, auth_provider, logger):
    ...
    client._auth_provider = auth_provider
    client._log = logger
    ...
```
This is a fixture parameter rename, not a behavior change.

---

## Summary Statistics

| Metric | Before | After |
|---|---|---|
| MockHTTPClient definitions | 18 | 1 (root conftest) |
| MockAuthProvider definitions | 26 (22 module + 4 class) | 5 (1 root conftest + 4 class-scoped in test_phase2a) |
| MockLogger definitions | 10 | 1 (root conftest) |
| MockCacheProvider definitions | 8 (6 identical + 2 different) | 3 (1 clients/conftest + 2 different) |
| mock_http fixture definitions | 24 (18 Pattern A + 6 other) | 7 (1 root conftest + 6 non-Pattern-A) |
| config fixture definitions | 19 + 1 different | 1 (root conftest) + 1 (EventRoutingConfig) |
| auth_provider fixture definitions | 18 + 2 mock_auth | 1 (root conftest) |
| logger fixture definitions | 9 + 2 mock_logger | 1 (root conftest) + 1 MagicMock variant |
| cache_provider fixture definitions | 6 + 2 different | 1 (clients/conftest) + 2 different |
| mock_batch_client definitions (module) | 5 + 3 class | 1 (cache/conftest) + 1 integration + 3 class |
| clean_registries/clean_registry definitions | 9 | 0 (root conftest autouse covers all) |
| **Total duplicate lines removed** | | **~1,400** |
| **New conftest files** | | **2** (clients/conftest.py, cache/conftest.py) |
| **Test count** | 9,138 | 9,138 (unchanged) |

---

## Attestation Table

| Item | Verified Via | Status |
|---|---|---|
| Root conftest current contents | `Read tests/conftest.py` | Verified |
| Existing conftest hierarchy (7 files) | `Glob tests/**/conftest.py` | Verified |
| `tests/_shared/mocks.py` exists with MockTask | `Read tests/_shared/mocks.py` | Verified |
| `tests/unit/conftest.py` does NOT exist | `ls` returned exit 2 | Verified |
| `tests/unit/clients/conftest.py` does NOT exist | `ls` returned exit 2 | Verified |
| `tests/unit/cache/conftest.py` does NOT exist | `ls` returned exit 2 | Verified |
| MockHTTPClient Extended variant (7 methods) | `Read tests/unit/test_tier2_clients.py:36-47` | Verified |
| MockHTTPClient Basic variant (5 methods) | `Read tests/unit/clients/test_tasks_cache.py:23-32` | Verified |
| MockAuthProvider identical across files | `Grep class MockAuthProvider` + sample reads | Verified |
| MockLogger Extended variant (5 methods) | `Read tests/unit/test_tier2_clients.py:56-75` | Verified |
| MockCacheProvider identical in 6 client files | `Read tests/unit/clients/test_tasks_cache.py:41-71` | Verified |
| mock_batch_client identical in 4 cache files | `Grep def mock_batch_client` with context | Verified |
| clean_registries redundant with root autouse | `Read tests/conftest.py:104-133` vs per-file fixtures | Verified |
| SM-211 variants differ (spec vs plain) | `Grep def mock_invalidator` with context | Verified |
| SM-214 variants differ (sub values) | `Grep def mock_service_claims` with context | Verified |
| Integration conftest client_fixture uses mock_auth/mock_logger | `Read tests/integration/conftest.py:88-116` | Verified |
| test_phase2a_adversarial class-scoped MockAuthProvider | `Grep class MockAuthProvider tests/unit/test_phase2a_adversarial.py` | Verified |
| Smell report WS-6 section | `Read .claude/artifacts/smell-report-phase3.md` | Verified |
