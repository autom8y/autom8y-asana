# Spike S0-002: Exception Audit

**Date**: 2026-02-04
**Author**: Principal Engineer (Claude)
**Status**: Complete
**Scope**: All `except Exception` blocks in `src/autom8_asana/`

---

## 1. Summary Statistics

### Total Count: 229 occurrences across 70 files

**No `except BaseException` or bare `except:` blocks found.** All broad catches use `except Exception`.

### By Subsystem

| Subsystem | File Count | Catch Count | Notes |
|-----------|-----------|-------------|-------|
| **cache/backends** (redis, s3) | 2 | 26 | Highest density; degraded-mode pattern |
| **cache** (tiered, unified, staleness, freshness, coalescer, etc.) | 11 | 28 | Graceful degradation throughout |
| **cache/dataframe** (warmer, decorator, tiers) | 4 | 7 | S3/parquet operations |
| **dataframes/persistence** | 1 | 19 | S3 CRUD for DataFrames |
| **dataframes/builders** (progressive, parallel_fetch, freshness, task_cache) | 4 | 15 | Build pipeline resilience |
| **dataframes** (async_s3, section_persistence, cache_integration, etc.) | 5 | 17 | S3 transport + integration |
| **api** (main, routes/*) | 6 | 23 | Request handlers, startup |
| **automation** (pipeline, seeding, engine, polling) | 5 | 18 | Workflow orchestration |
| **services** (resolver, universal_strategy) | 2 | 9 | Entity resolution |
| **persistence** (session, cascade, events, healing, etc.) | 6 | 10 | Save orchestration |
| **clients** (base, stories, sections, data/client) | 4 | 13 | Asana API + data service |
| **models/business** (detection, hydration, resolution, seeder, etc.) | 7 | 16 | Business model operations |
| **lambda_handlers** (cache_warmer, cache_invalidate, checkpoint) | 3 | 11 | Lambda entry points |
| **other** (core/schema, _defaults/auth, observability, search) | 4 | 4 | Misc |

### By Risk Level of Change

| Risk | Count | Description |
|------|-------|-------------|
| **Low** | ~95 | Clear specific exception; no behavioral change expected |
| **Medium** | ~100 | Requires verifying all possible exceptions from called code |
| **High** | ~34 | Catches at boundaries (Lambda handlers, API endpoints, event hooks) where broadness may be intentional |

### By Pattern Category

| Pattern | Count | Description |
|---------|-------|-------------|
| **Graceful degradation** (log + continue) | ~120 | Cache/S3 failures that shouldn't crash the system |
| **Return default** (return None/False/[]) | ~45 | Fallback to safe defaults |
| **Error wrapping** (catch + re-raise typed) | ~15 | Transform to domain exception |
| **Silent swallow** (catch + pass/no log) | ~12 | Most concerning -- no visibility |
| **Boundary catch-all** (Lambda/API top-level) | ~20 | Intentional top-level safety nets |
| **Schema fallback** (catch + use base) | ~6 | SchemaRegistry.get_schema fallback |
| **Retry with backoff** | ~5 | S3 retryable errors |

---

## 2. Full Audit Table

### 2.1 cache/backends/s3.py (13 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 186 | `except Exception as e` | boto3 S3 client creation | `botocore.exceptions.BotoCoreError`, `botocore.exceptions.ClientError`, `ImportError` | `except (BotoCoreError, ClientError) as e` | Low |
| 227 | `except Exception as e` | S3 reconnect (head_bucket) | `BotoCoreError`, `ClientError`, `ConnectionError` | `except (BotoCoreError, ClientError) as e` | Low |
| 390 | `except Exception as e` | S3 get_object (cache read) | `ClientError` (NoSuchKey, AccessDenied), `BotoCoreError`, `json.JSONDecodeError`, `gzip.BadGzipFile` | `except (BotoCoreError, ClientError, JSONDecodeError, BadGzipFile) as e` | Medium |
| 438 | `except Exception as e` | S3 put_object (cache write) | `ClientError`, `BotoCoreError`, `json.JSONEncodeError` | `except (BotoCoreError, ClientError) as e` | Low |
| 461 | `except Exception as e` | S3 delete_object | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 515 | `except Exception:` | Delete expired entry (TTL) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError):` | Low |
| 524 | `except Exception as e` | S3 get_object (versioned read) | `ClientError`, `BotoCoreError`, `JSONDecodeError` | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Medium |
| 576 | `except Exception as e` | S3 put_object (versioned write) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 699 | `except Exception as e` | S3 head_object (version check) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 733 | `except Exception:` | S3 delete in invalidate loop | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError):` | Low |
| 737 | `except Exception as e` | Outer invalidate catch | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 754 | `except Exception:` | S3 head_bucket (health check) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError):` | Low |
| 889 | `except Exception as e` | S3 batch delete (clear_all) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |

### 2.2 cache/backends/redis.py (13 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 167 | `except Exception as e` | Redis ConnectionPool creation | `redis.ConnectionError`, `redis.RedisError`, `ImportError` | `except (RedisError, ImportError) as e` | Low |
| 209 | `except Exception as e` | Redis reconnect (ping) | `redis.ConnectionError`, `redis.TimeoutError`, `RedisError` | `except RedisError as e` | Low |
| 340 | `except Exception as e` | Redis GET (cache read) | `RedisError`, `json.JSONDecodeError` | `except (RedisError, JSONDecodeError) as e` | Medium |
| 371 | `except Exception as e` | Redis SET/SETEX (cache write) | `RedisError`, `json.JSONEncodeError` | `except RedisError as e` | Low |
| 391 | `except Exception as e` | Redis DELETE | `RedisError` | `except RedisError as e` | Low |
| 458 | `except Exception as e` | Redis HGETALL (versioned read) | `RedisError`, `JSONDecodeError` | `except (RedisError, JSONDecodeError) as e` | Medium |
| 508 | `except Exception as e` | Redis HSET pipeline (versioned write) | `RedisError` | `except RedisError as e` | Low |
| 561 | `except Exception as e` | Redis pipeline GET batch | `RedisError`, `JSONDecodeError` | `except (RedisError, JSONDecodeError) as e` | Medium |
| 604 | `except Exception as e` | Redis pipeline SET batch | `RedisError` | `except RedisError as e` | Low |
| 665 | `except Exception as e` | Redis HGET (version check) | `RedisError` | `except RedisError as e` | Low |
| 705 | `except Exception as e` | Redis pipeline DELETE (invalidate) | `RedisError` | `except RedisError as e` | Low |
| 724 | `except Exception:` | Redis PING (health check) | `RedisError` | `except RedisError:` | Low |
| 811 | `except Exception as e` | Redis SCAN + DELETE (clear_all) | `RedisError` | `except RedisError as e` | Low |

### 2.3 cache/tiered.py (10 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 168 | `except Exception as e` | Cold tier delete | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 214 | `except Exception as e` | Cold tier get_versioned | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 232 | `except Exception as e` | Hot tier promotion write | Redis errors | `except RedisError as e` | Low |
| 264 | `except Exception as e` | Cold tier set_versioned (write-through) | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 306 | `except Exception as e` | Cold tier get_batch | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 330 | `except Exception as e` | Hot tier batch promotion | Redis errors | `except RedisError as e` | Low |
| 360 | `except Exception as e` | Cold tier set_batch (write-through) | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 426 | `except Exception as e` | Cold tier invalidate | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |
| 478 | `except Exception as e` | Hot tier clear_all | Redis errors | `except RedisError as e` | Low |
| 488 | `except Exception as e` | Cold tier clear_all | S3 backend errors | `except (BotoCoreError, ClientError) as e` | Low |

### 2.4 dataframes/persistence.py (19 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 238 | `except Exception as e` | boto3 S3 client creation | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 277 | `except Exception as e` | S3 reconnect | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 330 | `except Exception:` | S3 head_bucket (health check) | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError):` | Low |
| 422 | `except Exception as e` | S3 put_object (save DataFrame) | `BotoCoreError`, `ClientError`, polars errors | `except (BotoCoreError, ClientError, pl.ComputeError) as e` | Medium |
| 471 | `except Exception as e` | S3 get_object (load watermark) | `ClientError`, `BotoCoreError`, `JSONDecodeError` | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Medium |
| 487 | `except Exception as e` | S3 get_object (load DataFrame) | `ClientError`, `BotoCoreError`, polars errors | `except (BotoCoreError, ClientError, pl.ComputeError) as e` | Medium |
| 504 | `except Exception as e` | Outer load_dataframe catch | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 540 | `except Exception as e` | S3 delete_object in loop | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 547 | `except Exception as e` | Outer delete_dataframe catch | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 584 | `except Exception as e` | S3 get_object (watermark only) | `ClientError`, `BotoCoreError`, `JSONDecodeError` | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Low |
| 629 | `except Exception as e` | S3 paginate (list projects) | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 779 | `except Exception as e` | S3 put_object (save watermark) | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 816 | `except Exception as e` | Individual watermark load in loop | `BotoCoreError`, `ClientError`, `JSONDecodeError` | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Low |
| 827 | `except Exception as e` | Outer load_all_watermarks | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 887 | `except Exception as e` | S3 put_object (save index) | `BotoCoreError`, `ClientError`, `JSONDecodeError` | `except (BotoCoreError, ClientError) as e` | Low |
| 930 | `except Exception as e` | S3 get_object (load index) | `ClientError`, `BotoCoreError`, `JSONDecodeError` | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Medium |
| 948 | `except Exception as e` | Outer load_index catch | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 982 | `except Exception as e` | S3 delete_object (delete index) | `ClientError`, `BotoCoreError` | `except (BotoCoreError, ClientError) as e` | Low |
| 989 | `except Exception as e` | Outer delete_index catch | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |

### 2.5 dataframes/async_s3.py (7 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 249 | `except Exception as e` | boto3 S3 client creation (async) | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 354 | `except Exception as e` | S3 put_object with retry | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 433 | `except Exception as e` | S3 get_object with retry | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 501 | `except Exception as e` | S3 head_object | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 527 | `except Exception as e` | S3 delete_object | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 570 | `except Exception as e` | S3 list_objects | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 589 | `except Exception as e` | S3 head_bucket | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |

### 2.6 dataframes/builders/progressive.py (6 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 300 | `except Exception as e` | Freshness probe (API + cache) | `AsanaError`, `BotoCoreError`, `ClientError` | `except (AsanaError, BotoCoreError, ClientError) as e` | Medium |
| 612 | `except Exception as e` | Section fetch + persist pipeline | `AsanaError`, S3 errors, `DataFrameError` | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 671 | `except Exception as e` | Checkpoint resume | S3 errors, `JSONDecodeError`, polars errors | `except (BotoCoreError, ClientError, JSONDecodeError) as e` | Medium |
| 917 | `except Exception as e` | Checkpoint write | S3 errors | `except (BotoCoreError, ClientError) as e` | Low |
| 1011 | `except Exception as e` | Store populate batch | `AsanaError`, cache errors | `except (AsanaError, RedisError) as e` | Medium |
| 1032 | `except Exception as e` | GidLookupIndex build | `ImportError`, `ValueError`, polars errors | `except (ValueError, pl.ComputeError) as e` | Low |

### 2.7 dataframes/builders/parallel_fetch.py (4 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 286 | `except Exception as e` | Section list cache lookup | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 332 | `except Exception as e` | Section list cache populate | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 454 | `except Exception as e` | GID enumeration cache lookup | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 509 | `except Exception as e` | GID enumeration cache populate | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |

### 2.8 api/main.py (10 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 182 | `except Exception as e` | Entity resolver discovery at startup | `AsanaError`, `ConfigurationError`, `ImportError` | `except (AsanaError, ConfigurationError) as e` | Medium |
| 239 | `except Exception as e` | Cancel background cache warming | Any (task cleanup) | `except Exception as e` -- **KEEP** (task cancel safety) | High |
| 436 | `except Exception as e` | Index recovery during preload | `DataFrameError`, S3 errors | `except (DataFrameError, BotoCoreError, ClientError) as e` | Medium |
| 602 | `except Exception as e` | Per-project preload failure | `AsanaError`, S3 errors, `DataFrameError` | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 613 | `except Exception as e` | Overall preload failure | Any -- top-level safety net | `except Exception as e` -- **KEEP** (startup resilience) | High |
| 737 | `except Exception as e` | Incremental catchup failure | `AsanaError`, S3 errors | `except (AsanaError, BotoCoreError, ClientError) as e` | Medium |
| 823 | `except Exception as e` | Full rebuild failure | `AsanaError`, S3 errors, `DataFrameError` | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 877 | `except Exception as e` | Lambda invoke for preload | `BotoCoreError`, `ClientError` | `except (BotoCoreError, ClientError) as e` | Low |
| 1190 | `except Exception as e` | Per-project progressive preload | `AsanaError`, S3 errors, `DataFrameError` | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 1253 | `except Exception as e` | Overall progressive preload | Any -- top-level safety net | `except Exception as e` -- **KEEP** (startup resilience) | High |

### 2.9 automation/pipeline.py (9 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 473 | `except Exception as e` | Full rule execution catch-all | Any (top-level rule boundary) | `except Exception as e` -- **KEEP** (rule isolation) | High |
| 611 | `except Exception as e` | Fetch process holder on-demand | `AsanaError`, `AttributeError` | `except (AsanaError, AttributeError) as e` | Low |
| 652 | `except Exception as e` | Hierarchy placement | `AsanaError` | `except AsanaError as e` | Low |
| 723 | `except Exception as e` | Move task to section | `AsanaError` | `except AsanaError as e` | Low |
| 770 | `except Exception as e` | Set due date on task | `AsanaError` | `except AsanaError as e` | Low |
| 826 | `except Exception as e` | Access unit.rep list | `AttributeError`, `TypeError`, `IndexError` | `except (AttributeError, TypeError, IndexError) as e` | Low |
| 837 | `except Exception as e` | Access business.rep list | `AttributeError`, `TypeError`, `IndexError` | `except (AttributeError, TypeError, IndexError) as e` | Low |
| 854 | `except Exception as e` | Set assignee via API | `AsanaError` | `except AsanaError as e` | Low |
| 907 | `except Exception as e` | Create comment via API | `AsanaError` | `except AsanaError as e` | Low |

### 2.10 automation/seeding.py (4 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 548 | `except Exception as e` | Write seeded fields to Asana | `AsanaError` | `except AsanaError as e` | Low |
| 606 | `except Exception as e` | Descriptor field access | `AttributeError`, `KeyError`, `TypeError` | `except (AttributeError, KeyError, TypeError) as e` | Low |
| 624 | `except Exception as e` | CustomFieldsEditor access | `AttributeError`, `KeyError`, `TypeError` | `except (AttributeError, KeyError, TypeError) as e` | Low |
| 641 | `except Exception as e` | Direct attribute access | `AttributeError`, `TypeError` | `except (AttributeError, TypeError) as e` | Low |

### 2.11 services/resolver.py (3 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 405 | `except Exception:` | SchemaRegistry.get_schema | `SchemaNotFoundError`, `KeyError` | `except (SchemaNotFoundError, KeyError):` | Low |
| 541 | `except Exception:` | SchemaRegistry.get_schema | `SchemaNotFoundError`, `KeyError` | `except (SchemaNotFoundError, KeyError):` | Low |
| 633 | `except Exception:` | SchemaRegistry.get_schema | `SchemaNotFoundError`, `KeyError` | `except (SchemaNotFoundError, KeyError):` | Low |

### 2.12 services/universal_strategy.py (6 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 180 | `except Exception as e` | Resolution lookup via DataFrame | `DataFrameError`, polars errors | `except (DataFrameError, pl.ComputeError) as e` | Medium |
| 363 | `except Exception as e` | Enrichment from DataFrame | polars errors, `KeyError` | `except (pl.ComputeError, KeyError) as e` | Medium |
| 419 | `except Exception as e` | DataFrame cache fetch | Cache errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 450 | `except Exception as e` | Legacy strategy build fallback | `AsanaError`, `DataFrameError` | `except (AsanaError, DataFrameError) as e` | Medium |
| 548 | `except Exception as e` | Entity DataFrame build | `AsanaError`, `DataFrameError` | `except (AsanaError, DataFrameError) as e` | Medium |
| 573 | `except Exception:` | SchemaRegistry.get_schema | `SchemaNotFoundError`, `KeyError` | `except (SchemaNotFoundError, KeyError):` | Low |

### 2.13 clients/base.py (3 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 113 | `except Exception as exc` | Cache get_versioned | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 173 | `except Exception as exc` | Cache set_versioned | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 205 | `except Exception as exc` | Cache invalidate | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |

### 2.14 clients/data/client.py (7 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 394 | `except Exception as e` | Auth provider get_secret | `AuthenticationError`, `BotoCoreError` | `except (AuthenticationError, BotoCoreError, ClientError) as e` | Low |
| 527 | `except Exception as e` | Metrics hook emission | Any (callback) | `except Exception as e` -- **KEEP** (metrics isolation) | High |
| 586 | `except Exception as e` | Cache set (response caching) | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 671 | `except Exception as e` | Cache get (stale fallback) | Cache backend errors, `JSONDecodeError` | `except (RedisError, BotoCoreError, ClientError, JSONDecodeError) as e` | Medium |
| 1392 | `except Exception:` | Parse error response JSON | `JSONDecodeError`, `ValueError` | `except (JSONDecodeError, ValueError):` | Low |
| 1500 | `except Exception as e` | Parse response JSON body | `JSONDecodeError`, `ValueError` | Convert to `except (JSONDecodeError, ValueError) as e` (re-raises as InsightsServiceError) | Low |
| 1546 | `except Exception as e` | Parse response structure | `KeyError`, `ValueError`, `TypeError` | `except (KeyError, ValueError, TypeError) as e` (re-raises as InsightsServiceError) | Low |

### 2.15 clients/stories.py (2 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 570 | `except Exception as exc` | Cache get for stories | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 754 | `except Exception as exc` | Cache set for stories | Cache backend errors | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |

### 2.16 persistence/events.py (3 catches)

| Line | Current | Operation | Possible Exceptions | Recommended | Risk |
|------|---------|-----------|-------------------|-------------|------|
| 190 | `except Exception:` | Post-save hook execution | Any (user hooks) | `except Exception:` -- **KEEP** (hook isolation, but add logging) | High |
| 215 | `except Exception:` | Error hook execution | Any (user hooks) | `except Exception:` -- **KEEP** (hook isolation, but add logging) | High |
| 269 | `except Exception:` | Post-commit hook execution | Any (user hooks) | `except Exception:` -- **KEEP** (hook isolation, but add logging) | High |

### 2.17 persistence/other (cascade, action_executor, cache_invalidator, session, healing) (7 catches)

| Line | File | Operation | Recommended | Risk |
|------|------|-----------|-------------|------|
| 181 | cascade.py | Custom field update on entity | `except (AsanaError, AttributeError, KeyError) as e` | Medium |
| 115 | action_executor.py | API request execution | `except AsanaError as e` | Medium |
| 147 | cache_invalidator.py | Cache invalidate per GID | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 184 | cache_invalidator.py | DataFrame cache invalidation | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 871 | session.py | Automation evaluation | `except Exception as e` -- **KEEP** (NFR-003: automation must not fail commit) | High |
| 245 | healing.py | Individual entity healing | `except (AsanaError, DataFrameError) as e` | Medium |
| 369 | healing.py | Single entity heal operation | `except (AsanaError, DataFrameError) as e` | Medium |

### 2.18 models/business/* (16 catches)

| Line | File | Operation | Recommended | Risk |
|------|------|-----------|-------------|------|
| 108 | detection/facade.py | Cache deserialization | `except (KeyError, ValueError, TypeError):` | Low |
| 167 | detection/facade.py | Cache write for detection | `except (RedisError, BotoCoreError, ClientError):` | Low |
| 204 | detection/facade.py | Cache delete for detection | `except (RedisError, BotoCoreError, ClientError):` | Low |
| 509 | detection/facade.py | Warm detection cache | `except (AsanaError, DataFrameError) as exc` | Medium |
| 538 | detection/facade.py | Entity detection via strategies | `except (AsanaError, DataFrameError) as exc` | Medium |
| 179 | mixins.py | Custom field access | `except (AttributeError, KeyError, TypeError) as e` | Low |
| 490 | asset_edit.py | Custom field update | `except (AsanaError, AttributeError, KeyError) as e` | Medium |
| 149 | resolution.py | Entity resolution via strategy | `except (AsanaError, DataFrameError, ResolutionError) as e` | Medium |
| 215 | resolution.py | Strategy resolution | `except (AsanaError, DataFrameError) as e` | Medium |
| 289 | resolution.py | Resolution with fallback | `except (AsanaError, DataFrameError) as e` | Medium |
| 290 | hydration.py | Entity hydration | `except (AsanaError, HydrationError) as e` | Medium |
| 330 | hydration.py | Field hydration | `except (AsanaError, HydrationError) as e` | Medium |
| 348 | hydration.py | Nested hydration | `except (AsanaError, HydrationError) as e` | Medium |
| 384 | hydration.py | Relationship hydration | `except (AsanaError, HydrationError) as e` | Medium |
| 399 | hydration.py | Batch hydration | `except (AsanaError, HydrationError) as e` | Medium |
| 225 | business.py | Business model field access | `except (AttributeError, KeyError, TypeError) as e` | Low |
| 75 | matching/normalizers.py | String normalization | `except (TypeError, ValueError):` | Low |
| 390 | seeder.py | Seed value retrieval | `except (AsanaError, AttributeError, KeyError) as e` | Medium |
| 496 | seeder.py | Seed value application | `except (AsanaError, AttributeError) as e` | Medium |
| 541 | seeder.py | Seed batch application | `except AsanaError as e` | Medium |
| 585 | seeder.py | Seed validation | `except (ValueError, TypeError) as e` | Low |

### 2.19 lambda_handlers/* (11 catches)

| Line | File | Operation | Recommended | Risk |
|------|------|-----------|-------------|------|
| 235 | cache_warmer.py | CloudWatch metric emit | `except (BotoCoreError, ClientError) as e` | Low |
| 294 | cache_warmer.py | Lambda self-invoke continuation | `except (BotoCoreError, ClientError) as e` | Low |
| 372 | cache_warmer.py | Entity project discovery | `except (AsanaError, ImportError) as e` | Medium |
| 634 | cache_warmer.py | Per-entity warm in loop | `except Exception as e` -- **KEEP** (per-entity isolation in Lambda) | High |
| 706 | cache_warmer.py | Top-level async handler | `except Exception as e` -- **KEEP** (Lambda boundary) | High |
| 810 | cache_warmer.py | Top-level sync handler (asyncio.run) | `except Exception as e` -- **KEEP** (Lambda entry point) | High |
| 153 | cache_invalidate.py | Per-entity invalidation in loop | `except Exception as e` -- consider narrowing after audit of invalidation errors | Medium |
| 236 | cache_invalidate.py | Top-level invalidation handler | `except Exception as e` -- **KEEP** (Lambda boundary) | High |
| 229 | checkpoint.py | S3 checkpoint load | `except (BotoCoreError, ClientError) as e` | Low |
| 296 | checkpoint.py | S3 checkpoint save | `except (BotoCoreError, ClientError) as e` | Low |
| 329 | checkpoint.py | S3 checkpoint clear | `except (BotoCoreError, ClientError) as e` | Low |

### 2.20 api/routes/* (13 catches)

| Line | File | Operation | Recommended | Risk |
|------|------|-----------|-------------|------|
| 275 | resolver.py | Schema-based entity discovery | `except (SchemaNotFoundError, KeyError, ImportError) as e` | Low |
| 289 | resolver.py | Registry entity type check | `except (SchemaNotFoundError, KeyError) as e` | Low |
| 527 | resolver.py | Entity resolution (after re-raising HTTPException) | `except Exception as e` -- **KEEP** (API boundary, converts to 500) | High |
| 155 | query.py | SchemaRegistry.get_schema | `except (SchemaNotFoundError, KeyError):` | Low |
| 445 | query.py | Manifest-based section resolution | `except (BotoCoreError, ClientError, DataFrameError):` | Low |
| 219 | health.py | JWKS health check (after specific catches) | `except Exception:` -- **KEEP** (health endpoint resilience) | High |
| 147 | internal.py | S2S JWT validation | `except Exception as e` -- consider `except (JWTError, AuthenticationError) as e` | Medium |
| 142 | admin.py | Memory cache invalidation | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 165 | admin.py | S3 purge for cache refresh | `except (BotoCoreError, ClientError) as e` | Low |
| 175 | admin.py | Per-entity refresh failure | `except Exception as e` -- **KEEP** (per-entity isolation) | High |
| 263 | admin.py | Memory cache invalidation | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 313 | admin.py | Per-entity refresh failure | `except Exception as e` -- **KEEP** (per-entity isolation) | High |
| 361 | admin.py | Lambda invoke for warming | `except (BotoCoreError, ClientError) as e` | Low |

### 2.21 Remaining files (misc)

| Line | File | Operation | Recommended | Risk |
|------|------|-----------|-------------|------|
| 32 | core/schema.py | Schema version lookup | `except (SchemaNotFoundError, KeyError, ImportError) as e` | Low |
| 243 | _defaults/auth.py | boto3 SecretsManager call | `except (BotoCoreError, ClientError) as e` (already re-raises AuthenticationError above) | Low |
| 88 | observability/decorators.py | Decorated function execution | `except Exception as e` -- **KEEP** (re-raises after enrichment) | High |
| 215 | search/service.py | Search index query | `except (DataFrameError, pl.ComputeError, KeyError) as e` | Medium |
| 891 | client.py | Unknown internal operation | Needs context review | Medium |
| 336 | clients/sections.py | Section name parsing | `except (TypeError, ValueError, KeyError):` | Low |
| 268 | clients/data/models.py | Data model field parsing | `except (TypeError, ValueError, KeyError):` | Low |
| 95 | dataframes/resolver/cascading.py | Cascade resolution step | `except (AsanaError, DataFrameError) as e` | Medium |
| 515 | dataframes/resolver/cascading.py | Cascade enrichment | `except (DataFrameError, pl.ComputeError) as e` | Medium |
| 536 | dataframes/resolver/cascading.py | Cascade fallback | `except (AsanaError, DataFrameError) as e` | Medium |
| 251 | dataframes/cache_integration.py | Cache read | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 345 | dataframes/cache_integration.py | Cache write | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 407 | dataframes/cache_integration.py | Batch cache write | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 440 | dataframes/cache_integration.py | Cache warm | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 479 | dataframes/cache_integration.py | Cache invalidate | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 306 | dataframes/views/dataframe_view.py | DataFrame view query | `except (DataFrameError, pl.ComputeError) as e` | Medium |
| 218 | dataframes/builders/freshness.py | Freshness check | `except (BotoCoreError, ClientError) as e` | Low |
| 260 | dataframes/builders/freshness.py | Batch freshness | `except (BotoCoreError, ClientError) as e` | Low |
| 345 | dataframes/builders/freshness.py | Individual freshness in loop | `except (BotoCoreError, ClientError) as e` | Low |
| 214 | dataframes/builders/task_cache.py | Task cache read | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 302 | dataframes/builders/task_cache.py | Task cache write | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 435 | dataframes/section_persistence.py | Section manifest load | `except (BotoCoreError, ClientError) as e` | Low |
| 659 | dataframes/section_persistence.py | Section file save | `except (BotoCoreError, ClientError) as e` | Low |
| 748 | dataframes/section_persistence.py | Section file delete | `except (BotoCoreError, ClientError) as e` | Low |
| 219 | dataframes/watermark.py | Watermark S3 load | `except (BotoCoreError, ClientError) as e` | Low |
| 287 | dataframes/watermark.py | Watermark S3 save | `except (BotoCoreError, ClientError) as e` | Low |
| 155 | dataframes/extractors/base.py | Field extraction | `except (ExtractionError, KeyError, TypeError) as e` | Low |
| 191 | dataframes/extractors/base.py | Batch extraction | `except (ExtractionError, KeyError, TypeError) as e` | Low |
| 144 | cache/upgrader.py | Cache upgrade operation | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 94 | cache/hierarchy_warmer.py | Hierarchy warm operation | `except (AsanaError, RedisError) as e` | Medium |
| 286 | cache/unified.py | Cache upgrade | `except (AsanaError, RedisError, BotoCoreError, ClientError) as e` | Medium |
| 377 | cache/unified.py | Batch upgrade | `except (AsanaError, RedisError) as e` | Medium |
| 601 | cache/unified.py | Warm immediate parent | `except (AsanaError, RedisError) as e` | Medium |
| 132 | cache/staleness_coordinator.py | Staleness check | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 172 | cache/staleness_coordinator.py | Staleness invalidate | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 194 | cache/staleness_coordinator.py | Staleness TTL extend | `except (RedisError, BotoCoreError, ClientError) as exc` | Low |
| 248 | cache/freshness_coordinator.py | Batch freshness check | `except (AsanaError, RedisError) as e` | Medium |
| 479 | cache/freshness_coordinator.py | Hierarchy freshness check | `except (AsanaError, RedisError) as e` | Medium |
| 301 | cache/autom8_adapter.py | Adapter config read | `except (ConfigurationError, KeyError):` | Low |
| 438 | cache/autom8_adapter.py | Adapter initialization | `except (BotoCoreError, ClientError, RedisError) as e` | Medium |
| 208 | cache/coalescer.py | Coalesced batch flush | `except (RedisError, BotoCoreError, ClientError) as e` | Medium |
| 572 | cache/metrics.py | Metrics emission | `except Exception:` -- **KEEP** (metrics must never fail operations) | High |
| 128 | cache/lightweight_checker.py | Lightweight cache check | `except (RedisError, BotoCoreError, ClientError) as e` | Low |
| 847 | cache/dataframe_cache.py | DataFrame cache fallback | `except (RedisError, BotoCoreError, ClientError):` | Low |
| 82 | automation/polling/cli.py | Poll CLI startup | `except Exception as e` -- **KEEP** (CLI entry point) | High |
| 137 | automation/polling/cli.py | Poll CLI run | `except Exception as e` -- **KEEP** (CLI entry point) | High |
| 217 | automation/polling/cli.py | Poll CLI stop | `except Exception as e` -- **KEEP** (CLI entry point) | High |
| 181 | automation/polling/action_executor.py | Polling action execution | `except AsanaError as exc` | Medium |
| 423 | automation/polling/polling_scheduler.py | Polling cycle | `except Exception as exc` -- **KEEP** (scheduler resilience) | High |
| 226 | automation/engine.py | Automation rule evaluation | `except Exception as e` -- **KEEP** (per-rule isolation) | High |
| 184 | api/dependencies.py | Dependency injection | `except (ConfigurationError, ImportError) as e` | Medium |
| 162 | cache/dataframe/tiers/progressive.py | Parquet parse | `except (pl.ComputeError, pl.SchemaError, OSError) as e` | Low |
| 179 | cache/dataframe/tiers/progressive.py | Watermark JSON parse | `except (JSONDecodeError, ValueError, KeyError):` | Low |
| 265 | cache/dataframe/tiers/progressive.py | S3 put DataFrame | `except (BotoCoreError, ClientError) as e` | Low |
| 246 | cache/dataframe/warmer.py | Per-entity warm | `except Exception as e` -- **KEEP** (re-raises in strict mode, per-entity isolation) | High |
| 382 | cache/dataframe/warmer.py | Entity warm pipeline | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 473 | cache/dataframe/warmer.py | Progressive warm | `except (AsanaError, BotoCoreError, ClientError, DataFrameError) as e` | Medium |
| 224 | cache/dataframe/decorator.py | Decorated resolve (after re-raising HTTPException) | `except Exception as e` -- **KEEP** (releases build lock, then re-raises) | High |

---

## 3. Priority Ordering for Sprint 1

### Phase 1: Low-Hanging Fruit (Low Risk, High Impact) -- ~95 sites

**Start here.** These are pure infrastructure catches where the exception types are well-defined.

1. **cache/backends/s3.py** (13 sites) -- Replace with `BotoCoreError | ClientError`. All S3 operations have predictable error types. Single file, high test coverage expected.

2. **cache/backends/redis.py** (13 sites) -- Replace with `RedisError`. Same pattern as S3. Single file.

3. **dataframes/persistence.py** (19 sites) -- Replace with `BotoCoreError | ClientError`. Mirror of cache backend patterns.

4. **dataframes/async_s3.py** (7 sites) -- Replace with `BotoCoreError | ClientError`. Same infrastructure layer.

5. **cache/tiered.py** (10 sites) -- These delegate to backends. Replace with the same types used in backends.

6. **services/resolver.py** + **api/routes/query.py** SchemaRegistry fallbacks (5 sites) -- Replace `except Exception` with `except (SchemaNotFoundError, KeyError)`.

7. **clients/base.py** (3 sites) -- Cache operation wrappers. Replace with `RedisError | BotoCoreError | ClientError`.

8. **dataframes/builders/parallel_fetch.py** (4 sites) -- Cache wrappers. Same types.

9. **dataframes/cache_integration.py** (5 sites) -- Cache wrappers. Same types.

10. **clients/stories.py** (2 sites), **dataframes/builders/task_cache.py** (2 sites), **dataframes/builders/freshness.py** (3 sites) -- Cache/S3 wrappers.

### Phase 2: Medium Risk, Clear Improvements -- ~55 sites

These require verifying the full call chain but are still well-understood.

11. **automation/pipeline.py** API call catches (6 sites: lines 652, 723, 770, 854, 907, 611) -- Replace with `AsanaError`.

12. **automation/seeding.py** (4 sites) -- Mix of `AsanaError` and attribute access errors.

13. **services/universal_strategy.py** (5 non-schema sites) -- DataFrame/cache/API errors.

14. **models/business/hydration.py** (5 sites) -- `AsanaError | HydrationError`.

15. **models/business/resolution.py** (3 sites) -- `AsanaError | DataFrameError | ResolutionError`.

16. **clients/data/client.py** (5 narrowable sites) -- Various JSON/cache/auth errors.

17. **lambda_handlers/checkpoint.py** (3 sites) -- `BotoCoreError | ClientError`.

### Phase 3: Keep As-Is (High Risk / Intentional) -- ~34 sites

These catches serve as **intentional safety nets** and should be marked with explicit comments. Do NOT narrow them, but add `# BROAD-CATCH: <justification>` comments.

- Lambda handler top-level catches (cache_warmer.py lines 706, 810; cache_invalidate.py line 236)
- API startup resilience (api/main.py lines 613, 1253)
- Rule/entity isolation loops (pipeline.py:473, engine.py:226, cache_warmer.py:634, admin.py:175/313)
- Hook isolation (events.py:190/215/269) -- add logging
- Task cancel cleanup (api/main.py:239)
- Observability decorator (decorators.py:88) -- re-raises after enrichment
- Cache decorator (decorator.py:224) -- releases lock then re-raises
- Metrics emission (metrics.py:572, data/client.py:527)
- CLI entry points (polling/cli.py:82/137/217)
- Scheduler resilience (polling_scheduler.py:423)
- Session commit isolation (session.py:871)
- Health endpoint (health.py:219)
- API resolver boundary (resolver.py:527)
- Strict-mode warmer (warmer.py:246)

---

## 4. asyncio.CancelledError Analysis

**Python version**: 3.11+ (per `pyproject.toml`)

In Python 3.9+, `asyncio.CancelledError` is a subclass of `BaseException`, NOT `Exception`. Therefore, **none of the `except Exception` blocks in this codebase can catch `CancelledError`**. Graceful shutdown is not impacted.

The codebase already handles `CancelledError` correctly in 4 locations:
- `cache/coalescer.py:135` -- Timer cancel cleanup
- `cache/coalescer.py:160` -- Timer cancel passthrough
- `cache/coalescer.py:261` -- Shutdown cleanup
- `api/main.py:237` -- Background task cancel

**Verdict: No critical CancelledError issues.** This is a non-concern for Sprint 1.

---

## 5. Exception Hierarchy Recommendation

### Current State

The codebase has a solid hierarchy rooted in `AsanaError` for API errors and `DataFrameError` for dataframe operations. Missing are:

1. **No `CacheError` base class** -- Cache operations catch raw `RedisError` and `BotoCoreError/ClientError` separately, with no common ancestor.
2. **No `TransportError` base class** -- S3 transport failures (persistence, async_s3) have no domain abstraction.
3. **No `AutomationError` base class** -- Pipeline/seeding failures are caught as raw `Exception`.

### Proposed Hierarchy

```
AsanaError (existing)
├── AuthenticationError (existing)
├── ForbiddenError (existing)
├── NotFoundError (existing)
├── RateLimitError (existing)
├── ServerError (existing)
├── TimeoutError (existing)
├── ConfigurationError (existing)
├── HydrationError (existing)
├── ResolutionError (existing)
└── CircuitBreakerOpenError (existing)

TransportError (NEW) -- base for all I/O transport failures
├── S3TransportError (NEW) -- wraps BotoCoreError/ClientError for S3
└── RedisTransportError (NEW) -- wraps RedisError

CacheError (NEW) -- base for cache subsystem
├── CacheReadError (NEW)
├── CacheWriteError (NEW)
└── CacheConnectionError (NEW)

AutomationError (NEW) -- base for automation subsystem
├── RuleExecutionError (NEW)
├── SeedingError (NEW)
└── PipelineActionError (NEW)

DataFrameError (existing)
├── SchemaNotFoundError (existing)
├── ExtractionError (existing)
├── TypeCoercionError (existing)
└── SchemaVersionError (existing)
```

### Implementation Strategy

1. **Phase 1**: Create `TransportError`, `S3TransportError`, `RedisTransportError`. Wrap at the backend boundary (cache/backends/s3.py, cache/backends/redis.py). This lets all upstream code catch `TransportError` instead of vendor-specific types.

2. **Phase 2**: Create `CacheError` hierarchy. Wrap in `clients/base.py` and `cache/tiered.py` so higher-level code catches `CacheError` instead of transport details.

3. **Phase 3**: Create `AutomationError` hierarchy for `automation/pipeline.py` and `automation/seeding.py`.

4. **Phase 4**: Update all `except Exception` blocks to use domain exceptions.

### Benefits

- **Vendor isolation**: Upstream code never imports `botocore` or `redis` exception types
- **Consistent catch patterns**: `except CacheError` instead of `except (RedisError, BotoCoreError, ClientError)`
- **Monitoring**: Domain exceptions carry structured metadata (GID, operation, subsystem)
- **Testing**: Can assert on domain exception types without mocking vendor internals

---

## 6. Silent Swallow Concerns

The following catches swallow exceptions with no logging -- these should be addressed even if kept broad:

| File | Line | Current Behavior | Recommendation |
|------|------|-----------------|----------------|
| persistence/events.py | 190 | `except Exception: pass` | Add `logger.debug("post_save_hook_failed", exc_info=True)` |
| persistence/events.py | 215 | `except Exception: pass` | Add `logger.debug("error_hook_failed", exc_info=True)` |
| persistence/events.py | 269 | `except Exception: pass` | Add `logger.debug("post_commit_hook_failed", exc_info=True)` |
| cache/backends/s3.py | 515 | `except Exception: pass` | Add `logger.debug("s3_expired_entry_delete_failed", exc_info=True)` |
| cache/backends/s3.py | 733 | `except Exception: pass` | Add `logger.debug("s3_invalidate_entry_delete_failed", exc_info=True)` |
| api/routes/query.py | 445 | `except Exception: pass` | Add `logger.debug("manifest_resolution_failed", exc_info=True)` |

---

## 7. Key Observations

1. **The codebase has a consistent degraded-mode pattern.** Most catches follow: `except Exception as e: logger.warning(...); return safe_default`. This is architecturally sound but over-broad.

2. **Cache subsystem is the largest contributor** (61 catches across all cache-related files). A `CacheError` hierarchy would clean up ~40% of all sites with a single abstraction.

3. **S3/boto3 operations account for ~70 catches.** Wrapping with `S3TransportError` at the boundary would simplify all upstream catches.

4. **No catches swallow `CancelledError`** (Python 3.11+). Graceful shutdown is safe.

5. **~34 sites should remain broad** (`except Exception`) as intentional safety nets at system boundaries (Lambda handlers, API endpoints, rule isolation loops, hook dispatchers). These should be annotated with `# BROAD-CATCH:` comments.

6. **6 sites silently swallow exceptions** without any logging. These are the highest-priority fixes regardless of exception type narrowing.
