---
type: audit
---

# TYPE_CHECKING Smell Report

**Spike**: SPIKE-TYPE-CHECKING Phase 1 (Code Smeller)
**Date**: 2026-02-24
**Scope**: All `if TYPE_CHECKING:` blocks in `src/autom8_asana/`
**Mode**: READ-ONLY classification. No fixes proposed.

---

## Summary

| Category | Code | Files | Imports | Meaning |
|----------|------|------:|--------:|---------|
| Cycle Guard | A | 36 | 48 | Protects against a known structural cycle (KEEP) |
| Type-Only | B | 112 | 334 | Purely for type hints, no cycle involved (KEEP) |
| Removable | C | 3 | 6 | Guarded a cycle that was cut (CANDIDATE for removal) |
| Defensive | D | 83 | 165 | No current cycle, cautionary guard (JUDGMENT CALL) |
| **Total** | | **234** | **553** | |

**Key finding**: 112 files (48%) are standard type-only usage (B). Only 3 files (1.3%)
are confirmed removable (C). 83 files (35%) are defensive guards (D) requiring
architect-enforcer judgment. 36 files (15%) guard known structural cycles (A).

### Category D Breakdown

By target:
- **22** files guard imports from root modules (`client.py`, `config.py`) -- see D-Root section
- **61** files guard cross-package imports with no known cycle -- see D-Cross section

By composition:
- **5** files have only D-category imports, all targeting root -- lowest-risk removals
- **20** files have only D-category imports, targeting non-root packages -- needs review
- **58** files mix D imports with other categories (A/B) -- partial review needed

---

## Top 10 Hotspot Files

Files with the most TYPE_CHECKING imports (complexity indicators).

| Rank | File | Imports | Category | Key Targets |
|-----:|------|--------:|----------|-------------|
| 1 | `client.py` | 8 | D | automation, cache, protocols, search |
| 2 | `models/business/business.py` | 8 | D | (root), clients, models, protocols |
| 3 | `cache/integration/dataframe_cache.py` | 7 | B | cache, polars, protocols |
| 4 | `clients/data/client.py` | 7 | D | cache, clients, protocols |
| 5 | `dataframes/builders/base.py` | 7 | A | (root), dataframes, models |
| 6 | `dataframes/builders/progressive.py` | 7 | A | (root), dataframes, models |
| 7 | `models/business/resolution.py` | 7 | D | (root), models |
| 8 | `models/business/seeder.py` | 7 | D | (root), models, search |
| 9 | `persistence/session.py` | 7 | A | (root), models, persistence |
| 10 | `resolution/context.py` | 7 | D | (root), models, resolution |

---

## Category A: Cycle Guards (36 files, 48 imports)

These TYPE_CHECKING blocks protect against known structural cycles that remain
in the codebase. Removing them would reintroduce circular import errors.

### Structural Cycles Guarded

| Cycle | Direction in TC | Files | Imports |
|-------|-----------------|------:|--------:|
| cache <-> dataframes | both | 5 | 5 |
| models <-> dataframes | both | 15 | 20 |
| models <-> persistence | persistence -> models | 14 | 19 |
| models <-> core | core -> models | 1 | 1 |
| api <-> auth | auth -> api | 1 | 1 |
| services <-> core | services -> core | 2 | 2 |
| clients <-> persistence | (none -- uses deferred imports) | 0 | 0 |

### Per-File Detail

| File | Source Pkg | Target Pkg | Guarded Import |
|------|-----------|------------|----------------|
| `auth/audit.py` | auth | api | `from autom8_asana.api.dependencies import (` |
| `cache/dataframe/tiers/progressive.py` | cache | dataframes | `from autom8_asana.dataframes.section_persistence import SectionPersistence` |
| `core/creation.py` | core | models | `from autom8_asana.models.task import Task` |
| `dataframes/builders/base.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/builders/cascade_validator.py` | dataframes | cache | `from autom8_asana.cache.providers.unified import UnifiedTaskStore` |
| `dataframes/builders/parallel_fetch.py` | dataframes | models | `from autom8_asana.models.section import Section` |
| `dataframes/builders/parallel_fetch.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/builders/progressive.py` | dataframes | models | `from autom8_asana.models.section import Section` |
| `dataframes/builders/progressive.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/builders/section.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/builders/task_cache.py` | dataframes | cache | `from autom8_asana.cache.providers.unified import UnifiedTaskStore` |
| `dataframes/builders/task_cache.py` | dataframes | models | `from autom8_asana.models import Task` |
| `dataframes/extractors/base.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/extractors/contact.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/extractors/unit.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/resolver/cascading.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/resolver/default.py` | dataframes | models | `from autom8_asana.models.custom_field import CustomField` |
| `dataframes/resolver/default.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/resolver/mock.py` | dataframes | models | `from autom8_asana.models.custom_field import CustomField` |
| `dataframes/resolver/mock.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/resolver/protocol.py` | dataframes | models | `from autom8_asana.models.custom_field import CustomField` |
| `dataframes/resolver/protocol.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/views/cascade_view.py` | dataframes | cache | `from autom8_asana.cache.providers.unified import UnifiedTaskStore` |
| `dataframes/views/cascade_view.py` | dataframes | models | `from autom8_asana.models.task import Task` |
| `dataframes/views/cf_utils.py` | dataframes | models | `from autom8_asana.models.business.fields import CascadingFieldDef` |
| `dataframes/views/dataframe_view.py` | dataframes | cache | `from autom8_asana.cache.providers.unified import UnifiedTaskStore` |
| `models/custom_field_accessor.py` | models | dataframes | `from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver` |
| `persistence/actions.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/cascade.py` | persistence | models | `from autom8_asana.models.business.base import BusinessEntity` |
| `persistence/cascade.py` | persistence | models | `from autom8_asana.models.business.fields import CascadingFieldDef` |
| `persistence/cascade.py` | persistence | models | `from autom8_asana.models.task import Task` |
| `persistence/events.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/exceptions.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/executor.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/graph.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/healing.py` | persistence | models | `from autom8_asana.models.business.base import BusinessEntity` |
| `persistence/holder_construction.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/holder_ensurer.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/models.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/models.py` | persistence | models | `from autom8_asana.models.common import NameGid` |
| `persistence/pipeline.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/reorder.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/session.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `persistence/session.py` | persistence | models | `from autom8_asana.models.common import NameGid` |
| `persistence/session.py` | persistence | models | `from autom8_asana.models.user import User` |
| `persistence/tracker.py` | persistence | models | `from autom8_asana.models.base import AsanaResource` |
| `services/entity_context.py` | services | core | `from autom8_asana.core.entity_registry import EntityDescriptor` |
| `services/entity_service.py` | services | core | `from autom8_asana.core.entity_registry import EntityRegistry` |

---

## Category B: Type-Only (112 files, 334 imports)

Standard Python practice: imports used only in type annotations, guarded to avoid
runtime overhead. No cycle involved. These are all KEEP.

**Sub-breakdown**: 62 external/stdlib, 99 intra-package, 19 protocol imports.

### B Files Summary

| File | # Imports | Import Types |
|------|----------:|-------------|
| `_defaults/auth.py` | 1 | external |
| `_defaults/log.py` | 1 | protocol |
| `api/client_pool.py` | 1 | protocol |
| `api/preload/progressive.py` | 2 | external |
| `api/routes/dataframes.py` | 2 | external, intra-pkg |
| `api/routes/entity_write.py` | 1 | intra-pkg |
| `api/routes/query.py` | 1 | intra-pkg |
| `api/routes/resolver.py` | 1 | intra-pkg |
| `api/routes/resolver_schema.py` | 1 | intra-pkg |
| `api/routes/section_timelines.py` | 2 | external, intra-pkg |
| `auth/jwt_validator.py` | 1 | external |
| `automation/events/__init__.py` | 1 | intra-pkg |
| `automation/events/emitter.py` | 3 | intra-pkg |
| `automation/events/envelope.py` | 1 | intra-pkg |
| `automation/events/transport.py` | 1 | intra-pkg |
| `automation/polling/action_executor.py` | 1 | intra-pkg |
| `automation/polling/polling_scheduler.py` | 3 | external, intra-pkg |
| `automation/polling/trigger_evaluator.py` | 1 | intra-pkg |
| `automation/workflows/registry.py` | 1 | intra-pkg |
| `cache/backends/base.py` | 4 | external, intra-pkg, protocol |
| `cache/backends/memory.py` | 1 | external |
| `cache/backends/redis.py` | 2 | external, intra-pkg |
| `cache/backends/s3.py` | 2 | external, intra-pkg |
| `cache/dataframe/build_coordinator.py` | 2 | external |
| `cache/dataframe/decorator.py` | 3 | external, intra-pkg |
| `cache/dataframe/factory.py` | 1 | intra-pkg |
| `cache/dataframe/tiers/memory.py` | 1 | intra-pkg |
| `cache/integration/autom8_adapter.py` | 2 | external, intra-pkg |
| `cache/integration/batch.py` | 1 | external |
| `cache/integration/dataframe_cache.py` | 7 | external, intra-pkg, protocol |
| `cache/integration/dataframes.py` | 2 | external, protocol |
| `cache/integration/derived.py` | 1 | protocol |
| `cache/integration/loader.py` | 2 | external, protocol |
| `cache/integration/mutation_invalidator.py` | 2 | intra-pkg, protocol |
| `cache/integration/stories.py` | 2 | external, protocol |
| `cache/models/completeness.py` | 1 | intra-pkg |
| `cache/models/entry.py` | 1 | intra-pkg |
| `cache/models/events.py` | 4 | external, intra-pkg, protocol |
| `cache/models/metrics.py` | 1 | external |
| `cache/policies/coalescer.py` | 2 | intra-pkg |
| `cache/policies/freshness_policy.py` | 4 | external, intra-pkg |
| `cache/policies/staleness.py` | 2 | intra-pkg, protocol |
| `cache/providers/tiered.py` | 2 | intra-pkg, protocol |
| `clients/data/_endpoints/export.py` | 2 | external, intra-pkg |
| `clients/data/_endpoints/insights.py` | 3 | external, intra-pkg |
| `clients/data/_endpoints/reconciliation.py` | 3 | external, intra-pkg |
| `clients/data/_endpoints/simple.py` | 3 | external, intra-pkg |
| `clients/data/_metrics.py` | 1 | protocol |
| `clients/data/_policy.py` | 3 | external, intra-pkg |
| `clients/data/_response.py` | 3 | external, protocol |
| `clients/data/_retry.py` | 3 | external, protocol |
| `clients/data/models.py` | 2 | external |
| `clients/goal_followers.py` | 1 | intra-pkg |
| `clients/goal_relationships.py` | 1 | intra-pkg |
| `clients/goals.py` | 2 | intra-pkg |
| `clients/stories.py` | 1 | external |
| `core/retry.py` | 1 | external |
| `core/system_context.py` | 1 | external |
| `dataframes/builders/build_result.py` | 2 | external |
| `dataframes/builders/fields.py` | 2 | external, intra-pkg |
| `dataframes/cache_integration.py` | 2 | protocol |
| `dataframes/models/registry.py` | 2 | external, intra-pkg |
| `dataframes/models/schema.py` | 2 | external |
| `dataframes/section_persistence.py` | 2 | external, intra-pkg |
| `dataframes/watermark.py` | 2 | external, intra-pkg |
| `exceptions.py` | 1 | external |
| `lambda_handlers/checkpoint.py` | 1 | external |
| `metrics/compute.py` | 1 | intra-pkg |
| `metrics/expr.py` | 1 | external |
| `metrics/metric.py` | 2 | external, intra-pkg |
| `metrics/registry.py` | 1 | intra-pkg |
| `models/attachment.py` | 1 | intra-pkg |
| `models/business/contact.py` | 1 | intra-pkg |
| `models/business/detection/tier2.py` | 1 | intra-pkg |
| `models/business/detection/tier3.py` | 1 | intra-pkg |
| `models/business/dna.py` | 1 | intra-pkg |
| `models/business/fields.py` | 2 | external, intra-pkg |
| `models/business/holder_factory.py` | 1 | intra-pkg |
| `models/business/hours.py` | 2 | intra-pkg |
| `models/business/location.py` | 3 | intra-pkg |
| `models/business/matching/blocking.py` | 2 | intra-pkg |
| `models/business/matching/comparators.py` | 1 | intra-pkg |
| `models/business/matching/engine.py` | 1 | intra-pkg |
| `models/business/offer.py` | 3 | intra-pkg |
| `models/business/patterns.py` | 1 | intra-pkg |
| `models/business/process.py` | 2 | intra-pkg |
| `models/business/reconciliation.py` | 1 | intra-pkg |
| `models/business/section_timeline.py` | 1 | intra-pkg |
| `models/business/videography.py` | 1 | intra-pkg |
| `models/common.py` | 1 | external |
| `models/contracts/phone_vertical.py` | 1 | intra-pkg |
| `models/custom_field.py` | 1 | intra-pkg |
| `models/goal.py` | 1 | intra-pkg |
| `models/portfolio.py` | 1 | intra-pkg |
| `models/project.py` | 1 | intra-pkg |
| `models/section.py` | 1 | intra-pkg |
| `models/story.py` | 1 | intra-pkg |
| `models/tag.py` | 1 | intra-pkg |
| `models/task.py` | 1 | intra-pkg |
| `models/team.py` | 1 | intra-pkg |
| `models/user.py` | 1 | intra-pkg |
| `models/webhook.py` | 1 | intra-pkg |
| `observability/decorators.py` | 2 | external, protocol |
| `patterns/async_method.py` | 1 | external |
| `persistence/action_ordering.py` | 1 | external |
| `persistence/cache_invalidator.py` | 1 | intra-pkg |
| `services/dynamic_index.py` | 1 | external |
| `services/gid_push.py` | 1 | intra-pkg |
| `services/resolver.py` | 1 | intra-pkg |
| `transport/adaptive_semaphore.py` | 2 | external |
| `transport/response_handler.py` | 1 | external |
| `transport/sync.py` | 1 | external |

---

## Category C: Removable (3 files, 6 imports)

These TYPE_CHECKING blocks guarded cycles that were broken during REM-ASANA-ARCH.
The imports can potentially be moved to normal (non-guarded) imports.
Architect-enforcer should validate each before removal.

| File | Source Pkg | Target Pkg | Cut Cycle | Guarded Import |
|------|-----------|------------|-----------|----------------|
| `api/dependencies.py` | api | cache | api <-> cache | `from autom8_asana.cache.integration.dataframe_cache import DataFrameCache` |
| `automation/workflows/pipeline_transition.py` | automation | lifecycle | automation <-> lifecycle | `from autom8_asana.lifecycle.config import LifecycleConfig` |
| `automation/workflows/pipeline_transition.py` | automation | lifecycle | automation <-> lifecycle | `from autom8_asana.lifecycle.engine import LifecycleEngine` |
| `services/dataframe_service.py` | services | dataframes | services <-> dataframes | `from autom8_asana.dataframes.cache_integration import DataFrameCacheIntegration` |
| `services/dataframe_service.py` | services | dataframes | services <-> dataframes | `from autom8_asana.dataframes.models.schema import DataFrameSchema` |
| `services/dataframe_service.py` | services | dataframes | services <-> dataframes | `from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver` |

**Note**: These files also contain TYPE_CHECKING imports in other categories.
Only the imports matching cut cycles are candidates for removal.

- `api/dependencies.py` also has 5 non-C imports:
  - [D] `from autom8_asana.resolution.write_registry import EntityWriteRegistry`
  - [D] `from autom8_asana.services.dataframe_service import DataFrameService`
  - [D] `from autom8_asana.services.entity_service import EntityService`
  - [D] `from autom8_asana.services.section_service import SectionService`
  - [D] `from autom8_asana.services.task_service import TaskService`
- `automation/workflows/pipeline_transition.py` also has 2 non-C imports:
  - [D] `from autom8_asana.client import AsanaClient`
  - [D] `from autom8_asana.core.scope import EntityScope`
- `services/dataframe_service.py` also has 3 non-C imports:
  - [D] `from autom8_asana.client import AsanaClient`
  - [D] `from autom8_asana.models.project import Project`
  - [D] `from autom8_asana.models.section import Section`

---

## Category D: Defensive (83 files, 165 imports)

These TYPE_CHECKING blocks guard cross-package imports where no known cycle exists
(neither structural nor cut). They may be:
- Preventive guards against potential future cycles
- Leftover from earlier codebase states
- Standard practice applied uniformly regardless of cycle status

The architect-enforcer should render a keep/remove verdict for each.

### D-Root: Imports from root modules only (22 files)

These import from `client.py`, `config.py`, or other root-level modules.
Root modules are imported by most packages; these guards are likely
conventional rather than cycle-preventing.

| File | Source Pkg | Guarded Imports |
|------|-----------|-----------------|
| `automation/waiter.py` | automation | AsanaClient |
| `cache/dataframe/warmer.py` | cache | AsanaClient |
| `clients/name_resolver.py` | clients | AsanaClient |
| `clients/task_operations.py` | clients | AsanaClient |
| `clients/task_ttl.py` | clients | AsanaConfig |
| `clients/tasks.py` | clients | AsanaClient |
| `dataframes/builders/freshness.py` | dataframes | AsanaClient |
| `dataframes/storage.py` | dataframes | S3LocationConfig |
| `lifecycle/dispatch.py` | lifecycle | AsanaClient |
| `models/business/asset_edit.py` | models | AsanaClient |
| `models/business/base.py` | models | AsanaClient |
| `models/business/detection/facade.py` | models | AsanaClient |
| `models/business/detection/tier1.py` | models | AsanaClient |
| `models/business/detection/tier4.py` | models | AsanaClient |
| `models/business/hydration.py` | models | AsanaClient |
| `models/business/mixins.py` | models | AsanaClient |
| `models/business/registry.py` | models | AsanaClient |
| `models/business/resolution.py` | models | AsanaClient |
| `models/business/unit.py` | models | AsanaClient |
| `services/section_timeline_service.py` | services | AsanaClient |
| `transport/asana_http.py` | transport | AsanaConfig |
| `transport/config_translator.py` | transport | AsanaConfig |

### D-Cross: Cross-package imports (61 files)

These import across package boundaries where no known cycle exists.
Some may be guarding undocumented bidirectional dependencies.

#### Bidirectional TYPE_CHECKING Pairs (potential undocumented cycles)

These package pairs have TYPE_CHECKING imports in BOTH directions,
suggesting a bidirectional dependency that may warrant cycle documentation.

| Pair | A->B Files | B->A Files | Flag |
|------|--------:|---------:|------|
| cache <-> clients | 3 | 2 | Architect-enforcer review |
| clients <-> models | 2 | 1 | Architect-enforcer review |

#### D-Cross Per-File Detail

| File | Source Pkg | Target Pkgs | # D Imports | Other Cats |
|------|-----------|-------------|------------:|------------|
| `_defaults/cache.py` | _defaults | cache | 3 | B |
| `api/errors.py` | api | services | 1 | - |
| `api/preload/legacy.py` | api | dataframes, services | 3 | B |
| `api/routes/workflows.py` | api | lambda_handlers | 1 | B |
| `automation/base.py` | automation | models, persistence | 2 | B |
| `automation/context.py` | automation | (root), persistence | 2 | B |
| `automation/engine.py` | automation | (root), models, persistence | 3 | B |
| `automation/events/rule.py` | automation | models | 1 | B |
| `automation/pipeline.py` | automation | models | 1 | B |
| `automation/polling/structured_logger.py` | automation | persistence | 1 | B |
| `automation/seeding.py` | automation | (root), models | 2 | - |
| `automation/templates.py` | automation | (root), models | 3 | - |
| `automation/workflows/base.py` | automation | core | 1 | B |
| `automation/workflows/conversation_audit.py` | automation | clients, core, models | 3 | - |
| `automation/workflows/insights_export.py` | automation | clients, core | 2 | - |
| `automation/workflows/section_resolution.py` | automation | clients | 1 | - |
| `cache/integration/factory.py` | cache | (root), batch | 2 | B |
| `cache/integration/freshness_coordinator.py` | cache | batch | 1 | B |
| `cache/integration/hierarchy_warmer.py` | cache | clients | 1 | B |
| `cache/integration/staleness_coordinator.py` | cache | batch | 1 | B |
| `cache/integration/upgrader.py` | cache | clients | 1 | - |
| `cache/policies/lightweight_checker.py` | cache | batch | 1 | B |
| `cache/providers/unified.py` | cache | batch, clients | 2 | B |
| `client.py` | (root) | automation, cache, search | 4 | B |
| `clients/base.py` | clients | (root), cache, transport | 3 | B |
| `clients/data/_cache.py` | clients | models | 1 | B |
| `clients/data/_endpoints/batch.py` | clients | models | 1 | B |
| `clients/data/client.py` | clients | cache | 1 | B |
| `config.py` | (root) | cache | 2 | - |
| `lambda_handlers/workflow_handler.py` | lambda_handlers | automation | 1 | B |
| `lifecycle/completion.py` | lifecycle | (root), models | 2 | - |
| `lifecycle/creation.py` | lifecycle | (root), models, resolution | 3 | B |
| `lifecycle/engine.py` | lifecycle | (root), models | 2 | B |
| `lifecycle/init_actions.py` | lifecycle | (root), models, resolution | 3 | B |
| `lifecycle/reopen.py` | lifecycle | (root), models, resolution | 3 | B |
| `lifecycle/sections.py` | lifecycle | (root), resolution | 2 | B |
| `lifecycle/seeding.py` | lifecycle | (root), models | 4 | - |
| `lifecycle/wiring.py` | lifecycle | (root), resolution | 2 | B |
| `metrics/resolve.py` | metrics | dataframes | 1 | B |
| `models/business/business.py` | models | (root), clients | 2 | B |
| `models/business/seeder.py` | models | (root), search | 2 | B |
| `persistence/action_executor.py` | persistence | batch, transport | 2 | - |
| `protocols/cache.py` | protocols | cache | 4 | B |
| `protocols/dataframe_provider.py` | protocols | (root), cache | 2 | B |
| `protocols/insights.py` | protocols | clients | 1 | B |
| `protocols/item_loader.py` | protocols | models | 1 | - |
| `query/aggregator.py` | query | dataframes | 1 | - |
| `query/compiler.py` | query | dataframes | 1 | - |
| `query/engine.py` | query | (root), metrics | 2 | B |
| `query/guards.py` | query | dataframes | 1 | - |
| `resolution/context.py` | resolution | (root), models | 6 | B |
| `resolution/selection.py` | resolution | models | 2 | - |
| `resolution/strategies.py` | resolution | models | 1 | B |
| `resolution/write_registry.py` | resolution | core | 1 | - |
| `search/service.py` | search | dataframes | 1 | B |
| `services/field_write_service.py` | services | (root), cache | 2 | - |
| `services/gid_lookup.py` | services | models | 1 | B |
| `services/query_service.py` | services | (root), cache, metrics, query | 4 | B |
| `services/section_service.py` | services | (root), cache | 2 | - |
| `services/task_service.py` | services | (root), cache | 2 | - |
| `services/universal_strategy.py` | services | (root), cache | 2 | B |

---

## Cross-References and Flags

### For Architect Enforcer

1. **Category C (3 files)**: Validate that converting guarded imports to runtime imports
   will not reintroduce circular import errors. The cycles were cut in REM-ASANA-ARCH
   but no automated verification was done post-cut.

2. **Category D-Cross (61 files)**: Render keep/remove verdict. Key questions:
   - Do runtime imports exist in the reverse direction?
   - Would removing the guard create a new circular import?
   - Is the guard conventional (applied uniformly) or targeted?

3. **Bidirectional D pairs**: These may represent undocumented cycles that should
   be added to the structural cycle registry if confirmed:

   - `cache <-> clients` (3+2 guarded files)
   - `clients <-> models` (2+1 guarded files)

4. **`protocols <-> cache`**: protocols/cache.py imports 4 cache types under
   TYPE_CHECKING while 13 cache files import from protocols under TYPE_CHECKING.
   This is the highest-volume bidirectional pair not in any known cycle list.
   May indicate a missing entry in the structural cycles registry.

### Relationship to Known Architecture

| Known Cycle | Status | TYPE_CHECKING Guards | Category |
|-------------|--------|---------------------:|----------|
| clients <-> persistence | Structural | 0 (uses deferred imports) | A |
| cache <-> dataframes | Structural | 5 files, 5 imports | A |
| models <-> dataframes | Structural | 15 files, 20 imports | A |
| models <-> persistence | Structural | 14 files, 19 imports | A |
| models <-> core | Structural | 1 file, 1 import | A |
| api <-> auth | Structural | 1 file, 1 import | A |
| services <-> core | Structural | 2 files, 2 imports | A |
| cache -> api | Cut | 1 file, 1 import | C |
| automation <-> lifecycle | Cut | 1 file, 2 imports | C |
| dataframes <-> services | Cut | 1 file, 3 imports | C |
| cache <-> models | Cut | 0 | (no TC imports in this direction) |
| core <-> dataframes | Cut | 0 | (no TC imports in this direction) |
| core <-> models | Cut+Structural | 1 file, 1 import | A (structural takes precedence) |

---

## Methodology

1. Extracted all `if TYPE_CHECKING:` blocks from 234 files in `src/autom8_asana/`
2. Parsed each import statement to identify source package (file location) and target package
3. Normalized targets: root-level modules (`client.py`, `config.py`) mapped to `(root)`,
   external packages (stdlib, polars, autom8y_*) identified separately
4. Classified each import against known cycle lists from PROMPT_0-SPIKE-TC.md:
   - Structural cycle match -> A (cycle guard)
   - Cut cycle match -> C (removable)
   - Same-package or external/stdlib -> B (type-only)
   - Protocol target with no cycle -> B (type-only)
   - Cross-package with no known cycle -> D (defensive)
5. Per-file category = highest-priority import category (A > C > D > B)
6. No files were modified. No tests were run. No cycles were re-discovered.

## Attestation

| Check | Status |
|-------|--------|
| All 234 TYPE_CHECKING files scanned | PASS |
| Each import has category + rationale | PASS |
| Known cycle lists used without modification | PASS |
| No files modified (read-only) | PASS |
| No architecture evaluation performed | PASS |
| No fixes proposed | PASS |
| Boundary flags for architect-enforcer included | PASS |
