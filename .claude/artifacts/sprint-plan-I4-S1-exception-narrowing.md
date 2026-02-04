# Sprint Plan: I4-S1 Exception Narrowing - Mechanical Fixes

**Initiative**: I4-S1 (Wave 1, parallel with I1)
**Session**: session-20260204-195700-0f38ebf6
**Rite**: hygiene (mechanical narrowing)
**Design Reference**: `docs/design/TDD-exception-hierarchy.md`
**Findings Catalog**: `.claude/artifacts/hygiene-findings-error-handling.md`
**Exception Definitions**: `src/autom8_asana/core/exceptions.py`

---

## Summary

Replace `except Exception` with specific exception types at 45 mechanical sites where the replacement type is obvious from operation context. This is Phase 1 of the TDD-exception-hierarchy migration pattern.

**Selection Criteria** (mechanical = all must be true):
1. Try block wraps a single operation with a known error domain
2. Replacement type is clear from context without judgment calls
3. No behavioral change needed (same return value, same logging)

---

## Group 1: Cache Backend Operations (21 sites)

Sites wrapping direct S3/Redis cache calls. Replace with `CACHE_TRANSIENT_ERRORS` or `S3_TRANSPORT_ERRORS`.

| ID | File | Line | Current | Target Type |
|----|------|------|---------|-------------|
| BE-049 | cache/providers/unified.py | 286 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-050 | cache/providers/unified.py | 377 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-051 | cache/providers/unified.py | 601 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-052 | cache/policies/lightweight_checker.py | 128 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-047 | cache/policies/coalescer.py | 208 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-053 | cache/dataframe/tiers/progressive.py | 162 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-055 | cache/dataframe/tiers/progressive.py | 265 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-056 | cache/integration/upgrader.py | 144 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-057 | cache/integration/hierarchy_warmer.py | 94 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-058 | cache/dataframe/warmer.py | 246 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-059 | cache/dataframe/warmer.py | 382 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-060 | cache/dataframe/warmer.py | 473 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-061 | cache/dataframe/decorator.py | 224 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-048 | cache/dataframe/build_coordinator.py | 345 | `except Exception as exc` | `except CACHE_TRANSIENT_ERRORS as exc` |
| BE-063 | cache/integration/freshness_coordinator.py | 248 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-064 | cache/integration/freshness_coordinator.py | 479 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-065 | cache/integration/autom8_adapter.py | 301 | `except Exception` | `except CACHE_TRANSIENT_ERRORS` |
| BE-066 | cache/integration/autom8_adapter.py | 438 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-075 | cache/connections/registry.py | 85 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-076 | cache/connections/registry.py | 127 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |
| BE-077 | cache/connections/registry.py | 144 | `except Exception as e` | `except CACHE_TRANSIENT_ERRORS as e` |

**Import**: `from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS, S3_TRANSPORT_ERRORS`
**Commit**: `fix(cache): narrow 21 bare-except to CACHE_TRANSIENT_ERRORS/S3_TRANSPORT_ERRORS`

---

## Group 2: Persistence & Storage (9 sites)

Sites wrapping S3 persistence operations in the dataframes subsystem.

| ID | File | Line | Current | Target Type |
|----|------|------|---------|-------------|
| BE-091 | dataframes/watermark.py | 219 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-092 | dataframes/watermark.py | 287 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-105 | dataframes/section_persistence.py | 435 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-106 | dataframes/section_persistence.py | 659 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-107 | dataframes/section_persistence.py | 748 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-095 | dataframes/builders/progressive.py | 306 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-102 | dataframes/resolver/cascading.py | 95 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-103 | dataframes/resolver/cascading.py | 515 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |
| BE-104 | dataframes/resolver/cascading.py | 536 | `except Exception as e` | `except S3_TRANSPORT_ERRORS as e` |

**Import**: `from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS`
**Commit**: `fix(dataframes): narrow 9 bare-except to S3_TRANSPORT_ERRORS`

---

## Group 3: Network/API Client Operations (7 sites)

Sites wrapping Asana API HTTP calls.

| ID | File | Line | Current | Target Type |
|----|------|------|---------|-------------|
| BE-029 | clients/data/client.py | 394 | `except Exception as e` | `except (AsanaError, ConnectionError, TimeoutError) as e` |
| BE-031 | clients/data/client.py | 586 | `except Exception as e` | `except (AsanaError, ConnectionError, TimeoutError) as e` |
| BE-032 | clients/data/client.py | 671 | `except Exception as e` | `except (AsanaError, ConnectionError, TimeoutError) as e` |
| BE-034 | clients/data/client.py | 1500 | `except Exception as e` | `except (AsanaError, ConnectionError, TimeoutError) as e` |
| BE-035 | clients/data/client.py | 1546 | `except Exception as e` | `except (AsanaError, ConnectionError, TimeoutError) as e` |
| BE-150 | client.py | 891 | `except Exception` | `except (AsanaError, ConnectionError, TimeoutError)` |
| BE-154 | clients/sections.py | 336 | `except Exception` | `except (AsanaError, ConnectionError, TimeoutError)` |

**Import**: `from autom8_asana.exceptions import AsanaError`
**Commit**: `fix(clients): narrow 7 bare-except to (AsanaError, ConnectionError, TimeoutError)`

---

## Group 4: Serialization/Validation (6 sites)

Sites wrapping JSON parsing, data type conversion, or schema validation.

| ID | File | Line | Current | Target Type |
|----|------|------|---------|-------------|
| BE-033 | clients/data/client.py | 1392 | `except Exception` | `except (ValueError, KeyError, json.JSONDecodeError)` |
| BE-054 | cache/dataframe/tiers/progressive.py | 179 | `except Exception` | `except (ValueError, TypeError)` |
| BE-155 | clients/data/models.py | 268 | `except Exception` | `except (ValueError, TypeError)` |
| BE-151 | core/schema.py | 32 | `except Exception as e` | `except (ValueError, KeyError, TypeError) as e` |
| BE-159 | models/custom_field_accessor.py | 356 | `except (KeyError, AttributeError, Exception)` | `except (KeyError, AttributeError, TypeError, ValueError)` |
| BE-108 | dataframes/views/dataframe_view.py | 306 | `except Exception as e` | `except (KeyError, ValueError, TypeError) as e` |

**Import**: `import json` (if not already imported)
**Commit**: `fix(serialization): narrow 6 bare-except to specific ValueError/TypeError/KeyError`

---

## Group 5: Swallowed Exception Logging (2 standalone sites)

Sites where `except Exception: pass` gains logging. Sites already in Groups 3/4 get logging added as part of their group.

| ID | File | Line | Current | Fix |
|----|------|------|---------|-----|
| SW-003 | cache/models/metrics.py | 572 | `except Exception: pass` | Add `logger.debug("callback_error", exc_info=True)` |
| Overlaps | Groups 3/4 sites | -- | Already narrowed above | Add `logger.debug` where currently silent |

**Commit**: `fix(logging): add logging to silently-swallowed exception sites`

---

## Execution Order

1. **Group 1** (cache backend, 21 sites) - largest group, lowest risk, well-tested
2. **Group 2** (persistence/storage, 9 sites) - S3 operations, clear transport boundary
3. **Group 4** (serialization, 6 sites) - small group, simple type narrowing
4. **Group 5** (swallowed logging, 2 sites) - do after Groups 3/4 overlaps
5. **Group 3** (network/API, 7 sites) - API client layer, test most carefully

**Total: 45 sites across 5 commits**

---

## Test Verification Strategy

After EACH group commit:
1. `uv run python -m pytest tests/unit/cache/ -x -q` (Groups 1, 2)
2. `uv run python -m pytest tests/unit/clients/ -x -q` (Groups 3, 4)
3. `uv run python -m pytest tests/unit/dataframes/ -x -q` (Group 2)
4. `uv run python -m pytest tests/ -x -q --timeout=120` (full suite after all groups)

Verify bare-except count decreased:
```bash
grep -rn "except Exception" src/autom8_asana/ | wc -l
```

---

## Safety Rules (from TDD Section 6.2)

Every narrowed catch MUST preserve existing behavior exactly:
1. Same return value on error (None, False, [], etc.)
2. Same logging (warning level, same log key)
3. Same degraded-mode transition (if applicable)
4. The ONLY change is the `except` clause type list

---

## Out of Scope for I4-S1

- Lambda handler boundary catches (BE-040..BE-046) - intentional broad catches
- api/main.py sites (BE-001..BE-011) - read-only zone until I5
- automation/ sites (BE-109..BE-127) - need AutomationError wiring (I4-S2)
- models/business/ sites (BE-128..BE-148) - mixed domains, case-by-case (I4-S2)
- persistence/ sites (BE-078..BE-087) - mixed API+cache, case-by-case (I4-S2)
- Mutation invalidator sites (BE-068..BE-074) - fire-and-forget pattern (I4-S2)
