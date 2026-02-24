---
type: audit
---

# Hallucination Hunter Detection Report

**Phase**: 1 — Detection
**Agent**: hallucination-hunter
**Produced**: 2026-02-24
**Scope**: tests/integration/, tests/validation/, tests/benchmarks/, tests/_shared/
**Mode**: interactive

---

## Executive Summary

**Gate impact: PASS**

Zero CRITICAL or HIGH severity findings. All imports in the target test directories resolve cleanly against the source tree at `src/autom8_asana/`. No phantom dependencies were found. No invalid `@patch()` targets were found in the scanned directories. No dead API references were detected.

---

## Scan Scope

### Files Scanned

| Directory | File Count |
|-----------|------------|
| `tests/integration/` | 43 Python files |
| `tests/validation/persistence/` | 6 Python files |
| `tests/benchmarks/` | 3 Python files |
| `tests/_shared/` | 2 Python files |

**Total**: 54 Python files

### Dependency Manifest

`pyproject.toml` (project root). Key dev dependencies verified present:

- `pytest>=7.0.0`, `pytest-asyncio>=0.23.0`, `pytest-mock>=3.12.0`
- `respx>=0.20.0` (httpx mocking)
- `fakeredis>=2.20.0`, `moto>=5.0.0`, `boto3>=1.34.0`
- `autom8y-log[testing]`, `autom8y-cache[testing]`, `autom8y-http[testing]`, `autom8y-config[testing]`, `autom8y-core[testing]`, `autom8y-auth[testing]`

Private packages (`autom8y-*`) are sourced from a CodeArtifact registry configured in `pyproject.toml`. They are treated as externally verified.

---

## Check 1: Phantom Imports — `from autom8_asana.X import Y`

All `from autom8_asana.*` imports in every file were traced against the source tree. Every module path and every imported name was individually verified.

### Resolution Results

| Import | Module File Verified | Names Verified |
|--------|---------------------|----------------|
| `from autom8_asana import AsanaClient` | `src/autom8_asana/__init__.py` | AsanaClient confirmed |
| `from autom8_asana.client import AsanaClient` | `src/autom8_asana/client.py` | class confirmed |
| `from autom8_asana.config import AsanaConfig, RetryConfig` | `src/autom8_asana/config.py` | both confirmed |
| `from autom8_asana.exceptions import HydrationError, ExportError, NameNotFoundError` | `src/autom8_asana/exceptions.py` | all confirmed |
| `from autom8_asana.models import Task, Project, Workspace` | `src/autom8_asana/models/__init__.py` | all confirmed |
| `from autom8_asana.models.task import Task` | `src/autom8_asana/models/task.py` | confirmed |
| `from autom8_asana.models.common import NameGid` | `src/autom8_asana/models/common.py` | confirmed |
| `from autom8_asana.models.story import Story` | `src/autom8_asana/models/story.py` | confirmed |
| `from autom8_asana.models.contracts import PhoneVerticalPair` | `src/autom8_asana/models/contracts/__init__.py` | re-exports from `autom8y_core.models.data_service`; `autom8y-core>=1.1.0` declared in `pyproject.toml` |
| `from autom8_asana.models.custom_field_accessor import CustomFieldAccessor` | `src/autom8_asana/models/custom_field_accessor.py` | confirmed |
| `from autom8_asana.models.business.activity import AccountActivity` | `src/autom8_asana/models/business/activity.py` | confirmed |
| `from autom8_asana.models.business.business import Business` | `src/autom8_asana/models/business/business.py` | confirmed |
| `from autom8_asana.models.business.contact import Contact, ContactHolder` | `src/autom8_asana/models/business/contact.py` | confirmed |
| `from autom8_asana.models.business.detection import EntityType, DetectionResult, CONFIDENCE_TIER_1/2/3, detect_by_parent, detect_entity_type, detect_entity_type_async` | `src/autom8_asana/models/business/detection/__init__.py` + `types.py` | all confirmed |
| `from autom8_asana.models.business.fields import get_cascading_field, DETECTION_OPT_FIELDS, STANDARD_TASK_OPT_FIELDS` | `src/autom8_asana/models/business/fields.py` | all confirmed |
| `from autom8_asana.models.business.hydration import HydrationBranch, HydrationFailure, HydrationResult, _convert_to_typed_entity, _is_recoverable, _traverse_upward_async, hydrate_from_gid_async, _BUSINESS_FULL_OPT_FIELDS` | `src/autom8_asana/models/business/hydration.py` | all confirmed |
| `from autom8_asana.models.business.offer import Offer` | `src/autom8_asana/models/business/offer.py` | confirmed |
| `from autom8_asana.models.business.process import Process, ProcessType` | `src/autom8_asana/models/business/process.py` | confirmed |
| `from autom8_asana.models.business.registry import ProjectTypeRegistry, WorkspaceProjectRegistry, get_registry, get_workspace_registry` | `src/autom8_asana/models/business/registry.py` | all confirmed |
| `from autom8_asana.models.business.unit import Unit, UnitHolder` | `src/autom8_asana/models/business/unit.py` | confirmed |
| `from autom8_asana.batch.models import BatchResult, BatchRequest` | `src/autom8_asana/batch/models.py` | both confirmed |
| `from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider` | `src/autom8_asana/cache/backends/memory.py` | confirmed |
| `from autom8_asana.cache.integration.batch import ModificationCheckCache, fetch_task_modifications, reset_modification_cache` | `src/autom8_asana/cache/integration/batch.py` | all confirmed |
| `from autom8_asana.cache.integration.staleness_coordinator import StalenessCheckCoordinator` | `src/autom8_asana/cache/integration/staleness_coordinator.py` | confirmed |
| `from autom8_asana.cache.models.entry import CacheEntry, EntryType` | `src/autom8_asana/cache/models/entry.py` | both confirmed |
| `from autom8_asana.cache.models.freshness_unified import FreshnessIntent` | `src/autom8_asana/cache/models/freshness_unified.py` | confirmed |
| `from autom8_asana.cache.models.staleness_settings import StalenessCheckSettings` | `src/autom8_asana/cache/models/staleness_settings.py` | confirmed |
| `from autom8_asana.cache.policies.hierarchy import HierarchyIndex` | `src/autom8_asana/cache/policies/hierarchy.py` | confirmed |
| `from autom8_asana.cache.policies.staleness import check_batch_staleness` | `src/autom8_asana/cache/policies/staleness.py` | confirmed |
| `from autom8_asana.cache.providers.unified import UnifiedTaskStore` | `src/autom8_asana/cache/providers/unified.py` | confirmed |
| `from autom8_asana.clients.data.client import DataServiceClient` | `src/autom8_asana/clients/data/client.py` | confirmed |
| `from autom8_asana.clients.data.config import DataServiceConfig` | `src/autom8_asana/clients/data/config.py` | confirmed |
| `from autom8_asana.clients.data.models import ColumnInfo, InsightsMetadata, InsightsResponse, ExportResult` | `src/autom8_asana/clients/data/models.py` | all confirmed |
| `from autom8_asana.clients.stories import StoriesClient` | `src/autom8_asana/clients/stories.py` | confirmed |
| `from autom8_asana.clients.tasks import TasksClient` | `src/autom8_asana/clients/tasks.py` | confirmed |
| `from autom8_asana.core.entity_registry import get_registry` | `src/autom8_asana/core/entity_registry.py` | confirmed |
| `from autom8_asana.core.scope import EntityScope` | `src/autom8_asana/core/scope.py` | confirmed |
| `from autom8_asana.dataframes.builders.task_cache import TaskCacheCoordinator, TaskCacheResult` | `src/autom8_asana/dataframes/builders/task_cache.py` | both confirmed |
| `from autom8_asana.dataframes.extractors.base import BaseExtractor` | `src/autom8_asana/dataframes/extractors/base.py` | confirmed |
| `from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema` | `src/autom8_asana/dataframes/models/schema.py` | both confirmed |
| `from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver, TaskParentFetcher` | `src/autom8_asana/dataframes/resolver/cascading.py` | both confirmed |
| `from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA` | `src/autom8_asana/dataframes/schemas/unit.py` | confirmed |
| `from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin` | `src/autom8_asana/dataframes/views/cascade_view.py` | confirmed |
| `from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin` | `src/autom8_asana/dataframes/views/dataframe_view.py` | confirmed |
| `from autom8_asana.api.dependencies import AuthContext, AuthContextDep, get_auth_context` | `src/autom8_asana/api/dependencies.py` | all confirmed |
| `from autom8_asana.api.main import create_app` | `src/autom8_asana/api/main.py` | confirmed |
| `from autom8_asana.api.preload.progressive import _preload_dataframe_cache_progressive` | `src/autom8_asana/api/preload/progressive.py` | confirmed |
| `from autom8_asana.api.routes.health import set_cache_ready` | `src/autom8_asana/api/routes/health.py` | confirmed |
| `from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims` | `src/autom8_asana/api/routes/internal.py` | both confirmed |
| `from autom8_asana.auth.bot_pat import clear_bot_pat_cache` | `src/autom8_asana/auth/bot_pat.py` | confirmed |
| `from autom8_asana.auth.dual_mode import AuthMode` | `src/autom8_asana/auth/dual_mode.py` | confirmed |
| `from autom8_asana.auth.jwt_validator import reset_auth_client` | `src/autom8_asana/auth/jwt_validator.py` | confirmed |
| `from autom8_asana.automation.events.envelope import EventEnvelope` | `src/autom8_asana/automation/events/envelope.py` | confirmed |
| `from autom8_asana.automation.events.transport import SQSTransport` | `src/autom8_asana/automation/events/transport.py` | confirmed |
| `from autom8_asana.automation.events.types import EventType` | `src/autom8_asana/automation/events/types.py` | confirmed |
| `from autom8_asana.automation.polling import ActionConfig, ActionExecutor, PollingScheduler, Rule, RuleCondition, TriggerAgeConfig, TriggerDeadlineConfig, TriggerEvaluator, TriggerStaleConfig` | `src/autom8_asana/automation/polling/__init__.py` | all confirmed in `__all__` |
| `from autom8_asana.automation.workflows.conversation_audit import AUDIT_ENABLED_ENV_VAR, ConversationAuditWorkflow` | `src/autom8_asana/automation/workflows/conversation_audit.py` | both confirmed |
| `from autom8_asana.persistence import EntityState, OperationType, PlannedOperation, SaveResult, SaveSession` | `src/autom8_asana/persistence/__init__.py` | all confirmed in `__all__` |
| `from autom8_asana.persistence.exceptions import CyclicDependencyError, DependencyResolutionError, GidValidationError, PartialSaveError, SaveOrchestrationError, SaveSessionError, SessionClosedError` | `src/autom8_asana/persistence/exceptions.py` | all confirmed |
| `from autom8_asana.persistence.graph import DependencyGraph` | `src/autom8_asana/persistence/graph.py` | confirmed |
| `from autom8_asana.persistence.models import SaveError` | `src/autom8_asana/persistence/models.py` | confirmed |
| `from autom8_asana.persistence.session import SaveSession` | `src/autom8_asana/persistence/session.py` | confirmed |
| `from autom8_asana.persistence.tracker import ChangeTracker` | `src/autom8_asana/persistence/tracker.py` | confirmed |
| `from autom8_asana.persistence.validation import validate_gid` | `src/autom8_asana/persistence/validation.py` | confirmed |
| `from autom8_asana.resolution.field_resolver import FieldResolver` | `src/autom8_asana/resolution/field_resolver.py` | confirmed |
| `from autom8_asana.resolution.write_registry import CORE_FIELD_NAMES, EntityWriteRegistry` | `src/autom8_asana/resolution/write_registry.py` | both confirmed |
| `from autom8_asana.services.dynamic_index import DynamicIndex` | `src/autom8_asana/services/dynamic_index.py` | confirmed |
| `from autom8_asana.services.errors import EntityTypeMismatchError, NoValidFieldsError, TaskNotFoundError` | `src/autom8_asana/services/errors.py` | all confirmed |
| `from autom8_asana.services.field_write_service import FieldWriteService` | `src/autom8_asana/services/field_write_service.py` | confirmed |
| `from autom8_asana.services.gid_lookup import GidLookupIndex` | `src/autom8_asana/services/gid_lookup.py` | confirmed |
| `from autom8_asana.services.resolution_result import ResolutionResult` | `src/autom8_asana/services/resolution_result.py` | confirmed |
| `from autom8_asana.services.resolver import EntityProjectRegistry, _apply_legacy_mapping` | `src/autom8_asana/services/resolver.py` | both confirmed |
| `from autom8_asana._defaults.cache import InMemoryCacheProvider` | `src/autom8_asana/_defaults/cache.py` | confirmed |

**Result: 0 phantom imports found.**

---

## Check 2: Invalid Patch Targets — `@patch("autom8_asana.foo.bar")`

`@patch()` decorators in the target directories (integration/, validation/, benchmarks/, _shared/) were scanned. No `@patch("autom8_asana.*")` decorator-form patches exist in these directories. Decorator-form patches of this type are confined to `tests/unit/` which is outside the declared scan scope.

The file `tests/integration/automation/workflows/test_conversation_audit_e2e.py` uses `unittest.mock.patch` as a context manager (not a decorator). The patched name targets `autom8_asana.models.business.business.Business`, which is confirmed to exist.

**Result: 0 invalid patch targets found in scope.**

---

## Check 3: Dead API References — Method/Class Calls Against Source

Methods called on objects sourced from `autom8_asana` were cross-referenced against actual source definitions.

| Call Site | Method / Usage | Source Verification |
|-----------|---------------|---------------------|
| `tests/benchmarks/bench_batch_operations.py` | `EnhancedInMemoryCacheProvider.set_versioned`, `.get_batch`, `.set_batch`, `.get_versioned`, `.clear`, `.invalidate` | All methods confirmed in `src/autom8_asana/cache/backends/memory.py` |
| `tests/benchmarks/bench_batch_operations.py` | `ModificationCheckCache.set`, `.get_many` | Confirmed in `src/autom8_asana/cache/integration/batch.py` |
| `tests/benchmarks/bench_batch_operations.py` | `check_batch_staleness(cache, gids, EntryType, versions)` | Function confirmed at line 69 of `staleness.py`; argument pattern matches signature |
| `tests/benchmarks/test_insights_benchmark.py` | `DataServiceClient.get_insights_async`, `.get_insights_batch_async` | Both confirmed in `src/autom8_asana/clients/data/client.py` (lines 670, 850) |
| `tests/benchmarks/test_insights_benchmark.py` | `InsightsResponse.to_dataframe`, `BatchInsightsResponse.to_dataframe` | Confirmed in `src/autom8_asana/clients/data/models.py` |
| `tests/integration/persistence/test_action_batch_integration.py` | `SaveSession.track`, `.add_tag`, `.commit_async` | `track` at line 375, `add_tag` as `ActionBuilder("add_tag")` descriptor at line 1249, `commit_async` at line 724 in `session.py` |
| `tests/integration/automation/polling/test_end_to_end.py` | `PollingScheduler.from_config_file`, `._evaluate_rules`, `.config` | All confirmed in `src/autom8_asana/automation/polling/polling_scheduler.py` (lines 150, 302) |
| `tests/integration/automation/workflows/test_conversation_audit_e2e.py` | `ConversationAuditWorkflow._activity_map`, `.enumerate_async` | `_activity_map` is an instance dict; `enumerate_async` is inherited from `WorkflowAction` base class |
| `tests/validation/persistence/test_functional.py` | `SaveSession` as context manager, `.track`, `.commit_async` | All confirmed |
| `tests/integration/test_entity_write_smoke.py` | `EntityWriteRegistry(get_registry())` | Constructor confirmed; `get_registry()` at line 853 of `entity_registry.py` returns expected type |

**Result: 0 dead API references found.**

---

## Check 4: Hallucinated Dependencies — Third-Party Packages Not in pyproject.toml

All third-party imports found in the target test files were cross-referenced against `pyproject.toml`.

| Package | Import Found In | In pyproject.toml? |
|---------|----------------|---------------------|
| `pytest` | All test files | Yes (`pytest>=7.0.0` dev dep) |
| `pytest_mock` (TYPE_CHECKING only) | `test_cache_optimization_e2e.py` | Yes (`pytest-mock>=3.12.0`) |
| `respx` | `tests/benchmarks/test_insights_benchmark.py` | Yes (`respx>=0.20.0`) |
| `pydantic` | `test_trigger_evaluator_integration.py` | Yes (`pydantic>=2.0.0` core dep) |
| `polars` | `test_cascading_field_resolution.py` | Yes (`polars>=0.20.0` core dep) |
| `boto3` | `test_sqs_integration.py` | Yes (`boto3>=1.34.0` dev dep) |
| `httpx` (local import inside function) | `test_insights_benchmark.py:163` | Yes (`httpx>=0.25.0` core dep) |
| `statistics`, `time`, `asyncio`, `os`, `json`, `uuid`, `tempfile`, `textwrap`, `dataclasses`, `datetime`, `collections.abc`, `typing`, `unittest.mock` | Various | Python stdlib — no manifest entry required |

**Result: 0 hallucinated dependencies found.**

---

## Ambiguities (Advisory Only — Not Blocking)

### AMB-001: `PhoneVerticalPair` re-exported from private registry package

**File**: `tests/benchmarks/test_insights_benchmark.py:32`
**Import**: `from autom8_asana.models.contracts import PhoneVerticalPair`
**Detail**: `PhoneVerticalPair` is not defined in the project source. It is re-exported through an explicit `__all__` from `autom8y_core.models.data_service` (a private CodeArtifact package). Chain:

```
tests -> autom8_asana.models.contracts.__init__ -> autom8y_core.models.data_service.PhoneVerticalPair
```

`autom8y-core>=1.1.0` is declared in `pyproject.toml` core dependencies. The re-export is intentional per inline documentation. Static verification of the `autom8y_core` source is not possible from this environment.
**Confidence that this is a problem**: LOW. The pattern is intentional and the dependency is declared.

### AMB-002: `_BUSINESS_FULL_OPT_FIELDS` is a private-prefixed name imported by a test

**File**: `tests/integration/test_hydration_cache_integration.py:32`
**Import**: `from autom8_asana.models.business.hydration import _BUSINESS_FULL_OPT_FIELDS as HYDRATION_FULL_OPT_FIELDS`
**Detail**: The name starts with `_`, indicating it is not part of the public API surface. It exists in source at `hydration.py:69`. The import resolves correctly; this is a test coupling to an internal implementation detail rather than a non-existent reference.
**Severity**: Not a hallucination finding. Advisory for logic-surgeon to assess test coupling depth.

### AMB-003: `tests/integration/spike_write_diagnosis.py` not collected by pytest

**File**: `tests/integration/spike_write_diagnosis.py`
**Detail**: Named `spike_write_diagnosis.py` — does not match pytest's default `test_*.py` discovery pattern. Not executed as a test. No imports from it were scanned because it is a spike/script artifact, not a test file.
**Severity**: Not a detection finding. Advisory for cruft-cutter to assess as potential temporal debt.

---

## Summary Table

| Check | Findings | CRITICAL | HIGH | MEDIUM |
|-------|----------|----------|------|--------|
| Phantom imports | 0 | 0 | 0 | 0 |
| Invalid `@patch` targets | 0 | 0 | 0 | 0 |
| Dead API references | 0 | 0 | 0 | 0 |
| Hallucinated dependencies | 0 | 0 | 0 | 0 |
| **Total** | **0** | **0** | **0** | **0** |

---

## Handoff Criteria

- [x] Every file in review scope scanned for import/dependency issues
- [x] Each finding includes file path, line number, resolution failure reason (no findings warranted)
- [x] Registry verification completed for all third-party imports (all resolved against pyproject.toml)
- [x] Severity assigned to all findings (no findings requiring severity classification)
- [x] No files skipped without documented reason (`spike_write_diagnosis.py` documented in AMB-003)

**Acid test satisfied**: Logic-surgeon can begin behavioral analysis without re-checking whether any import actually exists. Every reference in the scanned test suite points to something that verifiably exists in the source tree or declared dependency manifest.
