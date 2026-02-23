# Janitor Agent Memory

## Project: autom8y-asana

### Test Command Pattern
Always prefix pytest commands with `AUTOM8_DATA_URL=` to avoid env config errors:
```
AUTOM8_DATA_URL= uv run pytest tests/unit/cache/ -q --timeout=60
```

### RF-009 Adversarial Triage Patterns (cache module, completed 2026-02-23)

**LOW VALUE (DELETE):**
- Tests that only construct model objects with edge-case data (empty dict, None, Unicode)
  -- these test Python/Pydantic behavior, not the module under test
- Tests that duplicate non-adversarial counterparts with trivially different inputs
- Partition/staleness edge cases that exist verbatim in non-adversarial files

**HIGH VALUE (KEEP):**
- Threading race conditions (concurrent set/get/clear with multiple threads)
- Concurrent metric updates + snapshot-during-update tests
- `asyncio.gather` with 100+ concurrent requests (deduplication/coalescing tests)
- Source inspection guards for dead code removal (`inspect.getsource` pattern)
- `@pytest.mark.slow` tests -- always preserve marker when moving

**MERGE TARGET FILES for cache module:**
- CacheEntry TTL boundaries -> `test_entry.py`
- Version comparison edge cases -> `test_versioning.py`
- In-memory provider error paths + thrashing -> `test_memory_backend.py`
- fetch_task_modifications variants -> `test_batch.py`
- RequestCoalescer race conditions -> `test_coalescer.py`
- LightweightChecker chunking + malformed responses -> `test_lightweight_checker.py`
- StalenessCheckCoordinator TTL ceiling/404/degradation -> `test_staleness_coordinator.py`
- warm_ancestors + dead code guards + 429 logging -> `test_hierarchy_warmer.py`
- Pacing boundary/batch/error/concurrency/config -> `test_hierarchy_pacing.py`

### Import Additions for Merges
When merging adversarial tests into canonical files, commonly needed imports to add:
- `from unittest.mock import AsyncMock, MagicMock` (often only MagicMock present)
- `from autom8_asana.batch.models import BatchResult`
- `from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider`
- `from autom8_asana.core.exceptions import RedisTransportError`
- `from autom8_asana.cache.models.entry import _parse_datetime` (private helper)
- `import asyncio` and `import inspect` for warmer source inspection tests

### Commit Convention for Triage
```
test(cleanup): triage <module>/<filename>.py [RF-XXX]

DELETE/MERGE/KEEP summary with class names and counts
RF-XXX: -NNN LOC adversarial file, description
```
