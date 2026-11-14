---
domain: db
generated_at: "2026-11-14T18:12:12Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "gitidx-v1:5a15438a45d829aa10eb9e8b5c92b387fa17dfd228b999cba199073a9191b1e9"
source_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d"
evidence_hash: "gitidx-v1:863b98372591ec46e903681a93cdb41fed491f992fbaa2a11d8416fa39983b05"
anchor_source: "stamp-pin"
stamp: {pin_id: "d55b30ac3e8e8159", pin_commit: "584c8f79b5f7d0087a28a982a3ed4290cb98647d", body_sha256: "1c52ef785310efafa91532cdacc77ecbf2a137b9f3a6f71e6eee6a9d60b5b295"}
confidence: 0.78
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@584c8f79"
---

# Codebase Database Schema

> Fresh full-observation pass at `origin/main@584c8f79` (detached worktree; every cite is relative to the repo root, full `src/autom8_asana/...` form). Covered: all 628 `src/**/*.py`, 50 `mcp/**/*.py`, 845 `tests/**/*.py` and the 8 `terraform/**` files in the pre-filtered manifest, by (a) an AST import walk of 1,556 parseable Python files for ORM, SQL-driver, cache and AWS-client imports, (b) an AST walk of every `ColumnDef` and `DataFrameSchema` call under `src/autom8_asana/dataframes/schemas/` and of every `EntityDescriptor` call in `src/autom8_asana/core/entity_registry.py`, (c) a regex search over the manifest for every `boto3.client`, `put_object`, `Key=`/`Prefix=`, lock and conditional-write site, and (d) direct reads of each store module. **Nothing was validated against a live store.** This run had no database, DuckDB, MCP, AWS or HTTP access, so every schema below is the schema the repo declares, never a verified production schema. Where a claim rests on a dated `.ledge/` receipt rather than on code, it is tagged `[EXPERIENTIAL]` (ledger-sourced, not re-observed). Anything that needs a live read is named in `## Knowledge Gaps`.

## Schema Inventory

### 1.0 Database-layer detection (the pre-check), with evidence

| Signal | Result | Method and cite |
|---|---|---|
| ORM or SQL-driver imports (`sqlalchemy`, `sqlmodel`, `alembic`, `duckdb`, `pymysql`, `aiomysql`, `asyncpg`, `psycopg`, `psycopg2`, `sqlite3`, `aiosqlite`, `django`, `peewee`, `tortoise`) in `src/`, `mcp/`, `tests/`, `scripts/`, `prototypes/` | **0 files** | AST import walk of 1,556 parseable files; only `mysql` matched, twice, both in `scripts/certification/landing_receipt.py:211,1058` (a standalone certification script, see 1.10) |
| SQL driver dependencies in the project manifest | **absent** | `pyproject.toml` lists `polars`, `boto3`, optional `redis`/`hiredis`, `slowapi`; the import-linter comment states the SQL drivers are "none used today" (`pyproject.toml:337`) |
| Migration directories, `*.sql`, `schema.prisma` | **0** | no such path in the 3,056-file manifest (control: `pyproject.toml` and `queries/active_offers.yaml` are present in the same manifest) |
| Relational or key-value infrastructure in this repo's Terraform | **none** | regex for `aws_dynamodb`, `aws_db_instance`, `aws_rds`, `aws_elasticache`, `aws_s3_bucket`, `aws_sqs` over `terraform/` returned 0 hits; positive control `aws_cloudwatch_metric_alarm` returned 33 hits in 5 files. Terraform here holds alarms plus a generated namespace JSON only (`terraform/services/asana/observability_alarms.tf:226`) |
| docker-compose database service | **none** | `docker-compose.yml:6-17` runs LocalStack with `SERVICES=s3,secretsmanager` (no DynamoDB emulation); `docker-compose.override.yml` points at an external `redis` host and an external `data` service URL and defines no database container |

**Verdict.** autom8y-asana has **no relational schema of its own**: no tables, no DDL, no migrations, no connection to a relational database at runtime. The five criteria are therefore applied to the *persistence layer it actually has*: object-store keyspaces and sidecar schemas (S3), Polars frame schemas, a key-value cache (Redis or in-process), DynamoDB items, local parquet/YAML files, and the key chains it puts on the wire to the `autom8y-data` service. Asana itself is the system of record for every business entity.

### 1.1 Which criteria apply and which do not

| Criterion element | Applies? | Reason |
|---|---|---|
| BASE TABLE count, per-table PK and column count | **Analog only** | there are no tables; the analogs are the 12 registered S3 namespaces, 30 entity descriptors with 11 distinct frame schemas, and 3 key-value shapes (1.2-1.8, including 1.6a). A table count in the downstream MySQL schema is not observable from this repo `[UV-P]` |
| Tenant-key column, DIRECT/CHAIN/GLOBAL | **Yes, on frame schemas** | the tenant key is a column on Polars frames (`office_phone`), not a database column |
| FK chains | **Yes, as parent-graph and join-key chains** | there are zero declared FKs; chains are Asana parent links and denormalized key columns (section 3) |
| Production-oracle validation queries | **Partially** | the repo holds one real SQL surface (`scripts/certification/landing_receipt.py`) and four YAML query templates (`queries/*.yaml`, not SQL); canonical information-schema queries are criteria-supplied, never executed here |
| NOT NULL / UNIQUE / CHECK / FK ON DELETE | **Analog only** | analogs are: S3 `If-None-Match`/`If-Match` conditionals, DynamoDB `ConditionExpression`, Pydantic validators, Polars `nullable` flags (section 5) |

### 1.2 Store census (every persistent or shared-state store the code reads or writes)

Method: a search for `boto3.client(` and `put_object(` across `src/` and `mcp/` (36 matches for a client construction in 27 files, including a few docstring mentions; 12 matches for `put_object` in 4 files: the unused S3 cache backend, `S3DataFrameStorage` with its `_put_object` helper and callers, the checkpoint manager and the tripwire; plus the `asyncio.to_thread`-wrapped puts in `src/autom8_asana/substrate/store.py`), an AST import scan, and reads of each module.

| # | Store | What lives there | Write owner | Read owners | Declared in |
|---|---|---|---|---|---|
| 1 | **S3 bucket** (default name from `S3Settings.bucket`) | parquet frames, JSON sidecars, manifests, checkpoints, substrate artifacts, one baseline JSON | `S3DataFrameStorage`, `CheckpointManager`, `S3ArtifactStore`, the divergence tripwire; the Go monolith for `asana-cache/*` | API preload, warmers, metrics CLI, substrate, bridges | `src/autom8_asana/settings.py:404-433`, section 1.3-1.5 |
| 2 | **Redis** (optional extra) | task-level cache entries | `RedisCacheProvider` | same | `src/autom8_asana/cache/backends/redis.py:72-135`, section 1.6a |
| 3 | **In-process memory** | `InMemoryCacheProvider`, `MemoryTier` frame cache, `DynamicIndexCache`, `WatermarkRepository` singleton, per-process rate-limit counters | each class | each class | sections 1.6a, 5.3 |
| 4 | **DynamoDB, idempotency table** (opt-in) | request replay records | `DynamoDBIdempotencyStore` | same | section 1.7 |
| 5 | **DynamoDB, hook registry table** (D6, dark) | webhook registration state, project-to-hook pointer, reconciler lease | `HookRegistry` | same | section 1.7 |
| 6 | **Secrets Manager prefix** (D6, dark) | one write-once secret per webhook handle | `HookStore` | not read by this repo's code | section 1.7 |
| 7 | **SQS queue** (event publish, default off) | event envelopes | `SQSTransport` | external | `src/autom8_asana/automation/events/transport.py:97-99` |
| 8 | **Local filesystem** `~/.autom8/**` | stage-transition parquet, section-timeline parquet, saved-query YAML | `StageTransitionStore`, `TimelineStore`, `save_query` | CLI lanes | section 1.8 |
| 9 | **Asana** | every business entity, comments used as dedupe markers | `persistence/` (`SaveSession`), service routes | everything | section 1.9 |
| 10 | **autom8y-data service** (HTTP only; MySQL behind it) | sync targets and insight sources | this repo pushes four snapshots | this repo reads six endpoints | section 1.10 |

CloudWatch metrics and Logs, Lambda invoke and Secrets Manager credential reads also appear as `boto3.client(...)` sites (`src/autom8_asana/metrics/cloudwatch_emit.py:117`, `src/autom8_asana/automation/forwarding_stage_backfill/evidence_source.py:166`, `src/autom8_asana/api/routes/admin.py:384`, `src/autom8_asana/_defaults/auth.py:175`); they carry no entity data and are not inventoried as stores.

### 1.3 S3 namespace registry: 12 registered namespaces

SSOT: `src/autom8_asana/storage_namespace.py` (`REGISTRY` at `:520`, pinned `REGISTRY_NAMESPACE_COUNT = 12` at `:540`, import-time `_validate_registry()` at `:569-630` enforcing count, unique names, unique prefixes, and two declared parent prefixes). The count, the six LIVE and six FOSSIL split, and the single `KNOWN_DRIFTS` entry (`:548-559`) are unchanged since the prior pass. Alignment tests: `tests/arch/test_namespace_contract.py` (t1-t5).

| Registry name | Prefix | Lifecycle | Writer (per registry) | Plane | Line in `src/autom8_asana/storage_namespace.py` |
|---|---|---|---|---|---|
| `TASK_CACHE` | `asana-cache` (effective keyspace `asana-cache/tasks/{gid}/task.json[.gz]`) | LIVE | **external** Go monolith (no writer in this repo) | durable per-task copy, explicit read only | `:226-279`; reader key builder `src/autom8_asana/cache/durable_task_cache.py:98-106` |
| `DATAFRAMES_V2` | `dataframes/` | LIVE | `src/autom8_asana/dataframes/storage.py` (default prefix `:347`) | GID-keyed project/entity frames | `:282-308` |
| `CHECKPOINTS` | `cache-warmer/checkpoints/` | LIVE | `src/autom8_asana/lambda_handlers/checkpoint.py:31` | warmer resume checkpoint | `:315-330` |
| `CHECKPOINTS_BULK` | `cache-warmer/checkpoints/bulk/` | LIVE | same module, env-selected lane | per-lane disjoint checkpoint | `:332-347` |
| `CHECKPOINTS_SECTION_FAST` | `cache-warmer/checkpoints/section-fast/` | LIVE | same | per-lane disjoint checkpoint | `:349-364` |
| `E2E_TEST_DATAFRAMES` | `e2e-test-dataframes/` | LIVE (non-prod) | e2e harness, no IAM row | test frames | `:367-382` |
| `PROJECT_FRAMES_FOSSIL` | `asana-cache/project-frames/` | FOSSIL | monolith v1, last write 2025-10-02 (per registry text) | v1 name-keyed frames; also the live value of the overloaded `ASANA_CACHE_S3_PREFIX` | `:385-409` |
| `TASK_CACHE_LEGACY_FOSSIL` | `asana-cache/task-cache/` | FOSSIL | monolith (pickle) | legacy task pickle | `:412-432` |
| `TASK_DATA_CACHE_V3_FOSSIL` | `asana-cache/task-data-cache-v3/` | FOSSIL | monolith | expensive-attr v3 | `:435-450` |
| `INSIGHTS_FRAMES_FOSSIL` | `asana-cache/insights-frames/` | FOSSIL | insights-export lambda (probable) | insights frames | `:453-472` |
| `NAME_GID_MAPPINGS_FOSSIL` | `asana-cache/name-gid-mappings/` | FOSSIL | monolith | name-to-gid pickles | `:475-490` |
| `ASANA_CACHE_DATAFRAMES_FOSSIL` | `asana-cache/dataframes/` | FOSSIL | monolith legacy | flat entity-gid frames | `:493-511` |

Key counts quoted in the registry text (385k durable task keys, 1,025 v2 frame keys, 2,243 v1 keys, 128,583 legacy pickle keys) are census figures from 2026-06-10 `[EXPERIENTIAL]`; they were not re-measured. The IAM matrix (principal and verb per namespace) is declared as data in the registry; it contains two role/user ARNs with an account identifier, deliberately not reproduced here. Redis is intentionally absent from the registry (`:513-517`).

**t3 is exact-match only.** `tests/arch/test_namespace_contract.py:210-231` flags a string `Constant` only when it equals a registry prefix exactly, and allowlists the registry's own anchor files (`:185-207`). Any key built from a prefix that differs by even one character is invisible to it. That is how the unregistered keyspaces in 1.4 coexist with a green t3.

### 1.4 Unregistered S3 keyspaces the code reads or writes (inventory gaps versus the registry)

| Keyspace | Writer / reader | Cite |
|---|---|---|
| `dataframes-v2/{project_gid}/{entity_type}/current.json` and `.../versions/{sha256}/frame` | **write:** `S3ArtifactStore` (`stage_version`, `swap_pointer`, `gc_versions`); **read:** `S3ArtifactStore.read_current`, `src/autom8_asana/lambda_handlers/prov_sweep.py` enumerator (bucket env `SUBSTRATE_V2_S3_BUCKET`, default is the shared bucket, `:21-22,87,180`) | key builder `src/autom8_asana/substrate/identity.py:68-75`; store `src/autom8_asana/substrate/store.py` |
| `soak-sentinel/r7-divergence-baseline.json` | read and write by the divergence tripwire; bucket env `TRAFFIC_OFFER_DIVERGENCE_BASELINE_BUCKET` | `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:317-319,1044,1078` |
| `dataframes/{project_gid}/cache-freshness-ttl.json` | SLA sidecar template, inside the registered `dataframes/` plane | `src/autom8_asana/metrics/sla_profile.py:86,483` |
| `dataframes/{project_gid}/offer/{dataframe.parquet,watermark.json}` read through a hand-pinned `_prefix = "dataframes"` (no trailing slash, so it never equals the registry value) | `S3OfferPlaneReader` | `src/autom8_asana/substrate/live.py:440-461` |
| frames read by key through `DATAFRAMES_V2.prefix` | enrollment bridge, divergence tripwire | `src/autom8_asana/enrollment/intent_projection.py:178-191`; `.../traffic_offer_divergence_tripwire.py:212` (these derive from the registry, so they are legal) |

**Substrate-v2 wiring status.** The only production consumer of the `substrate` package outside its own tests is the provability-sweep Lambda handler (search for imports of `autom8_asana.substrate` under `api/`, `lambda_handlers/`, `services/`, `cache/`, `dataframes/` and `mcp/` found only `src/autom8_asana/lambda_handlers/prov_sweep.py:55-75`). `SubstrateRebuilder` (the stage-validate-swap writer, `src/autom8_asana/substrate/rebuild.py:508`) is constructed only inside the package. The registered target set is pinned to exactly one artifact, the offer plane (`src/autom8_asana/lambda_handlers/prov_sweep.py:29-31`). Whether any pointer object actually exists in the bucket is unobserved `[UV-P]`.

### 1.5 The `dataframes/` plane: object layout and sidecar schemas

`S3DataFrameStorage` (`src/autom8_asana/dataframes/storage.py:308`, default prefix `:347`) keeps **two layouts side by side** (SEAM-1 dual-read; docstring `:320-335`):

```
legacy (entity-agnostic; read fallback only, legacy_fallback_enabled defaults True, :352, gate at :1010)
  {prefix}{project_gid}/{dataframe.parquet | watermark.json | gid_lookup_index.json | manifest.json | sections/{section_gid}.parquet}
v2 (write target whenever entity_type is supplied)
  {prefix}{project_gid}/{entity_type}/{same five object kinds}
```

Key builders: `_entity_segment` `:405-412`, `_df_key` `:414`, `_watermark_key` `:418`, `_index_key` `:422`, `_section_key` `:426`, `_manifest_key` `:432`. Every write goes through `_put_object` (`:498-536`), a plain `put_object` with `ContentType` and optional user metadata; there is no conditional header (section 5.3).

| Object | Schema (declared in code, no DDL) | Cite |
|---|---|---|
| `dataframe.parquet` | Polars frame; user metadata `project-gid`, `row-count`, `watermark` | `src/autom8_asana/dataframes/storage.py:931-941` |
| `watermark.json` | `{project_gid, watermark (ISO), saved_at, [row_count, columns, entity_type, population_degraded, population_min_rate]}`; the last two are additive carry-forward flags, a legacy sidecar lacking them reads back healthy | `:840-873` |
| `manifest.json` | `SectionManifest`: `project_gid, entity_type, started_at, sections{gid -> SectionInfo}, total_sections, completed_sections, version=1, schema_version`; `SectionInfo`: `status in {pending, in_progress, complete, failed}`, `rows, written_at, error, watermark, gid_hash, name, in_progress_since, last_fetched_offset, rows_fetched, chunks_checkpointed, last_verified_at`; empty `schema_version` means legacy and forces a rebuild | `src/autom8_asana/dataframes/section_persistence.py:76-149` |
| `gid_lookup_index.json` | serialized `GidLookupIndex`: `{version: "1.0", created_at, entry_count, lookup}`; keys `pv1:{office_phone}:{vertical}` mapped to a task gid | `src/autom8_asana/services/gid_lookup.py:151-177` (serialize/deserialize), `:292-293` (key build) |
| checkpoint `latest.json` | `CheckpointRecord`: `invocation_id, completed_entities, pending_entities, entity_results, created_at, expires_at`; staleness default 1 h | `src/autom8_asana/lambda_handlers/checkpoint.py:64-93,311-319`, `DEFAULT_STALENESS_HOURS` at `:32` |
| substrate `current.json` | `{version_id, proof}`; proof is `FreshnessProof{built_from_live_at, content_digest, sla_seconds}` | `src/autom8_asana/substrate/store.py:525-530`; `src/autom8_asana/substrate/freshness.py:62-82` |
| substrate frame object | `versions/{sha256(frame_bytes)}/frame`; content-digest addressed; written with `IfNoneMatch="*"` | `src/autom8_asana/substrate/store.py:18-20,340-350` |

Two distinct 64-hex digests exist in the substrate and must not be conflated: `version_id` is the address digest over stored bytes, `FreshnessProof.content_digest` is the parquet-independent freshness digest (`src/autom8_asana/substrate/store.py:24-31`).

### 1.6 Frame schemas (the analog of tables): 30 entity descriptors, 11 schema modules

SSOT: `ENTITY_DESCRIPTORS` (`src/autom8_asana/core/entity_registry.py:460`). AST walk of the file: **30 descriptors**: 1 ROOT (`business`), 1 COMPOSITE (`unit`), 9 HOLDER, 18 LEAF, 1 OBSERVATION (`stage_transition`); **16 are `warmable`** (business, unit, contact, offer, asset_edit, unit_holder, asset_edit_holder, nine `process_*`). Counts match the prior pass.

All frame schemas inherit `BASE_SCHEMA`, 13 columns (`gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags, parent_gid`; `src/autom8_asana/dataframes/schemas/base.py:12-112`, version 1.1.0). Of those 13, exactly 8 are `nullable=False` (`gid, name, type, created, is_completed, url, last_modified, tags`). **Every entity-specific extra column is `nullable=True`** (AST walk: zero `nullable=False` in any non-base schema file). `ColumnDef` is defined at `src/autom8_asana/dataframes/models/schema.py:19-43` with fields `name, dtype, nullable, source, extractor, description`. The `source` grammar: a plain Asana attribute, `cf:<Custom Field Name>` (own custom field), `cascade:<Field Name>` (ancestor-derived), or `None` (derived in an extractor).

Declared widths are the static count of `ColumnDef` names (13 base plus extras, de-duplicated against base). They are declared schema, not measured production frame width `[UV-P]`.

| Entity (descriptor) | Warm priority | Declared columns / schema version | Key columns | Line in `src/autom8_asana/core/entity_registry.py` | Schema cite |
|---|---|---|---|---|---|
| `business` (ROOT) | 1 | 18 / 1.2.0 | `office_phone` | `:464` | `src/autom8_asana/dataframes/schemas/business.py:54` |
| `unit` (COMPOSITE) | 2 | 22 / 1.5.0 | `office_phone, vertical` | `:492` | `src/autom8_asana/dataframes/schemas/unit.py:77` |
| `unit_holder` (HOLDER, parent business) | 3 | 23 / 1.1.0 | none | `:785` | `src/autom8_asana/dataframes/schemas/unit_holder.py:147` |
| `offer` (LEAF) | 4 | 33 / 1.6.0 | `office_phone, vertical, offer_id` | `:539` | `src/autom8_asana/dataframes/schemas/offer.py:209` |
| `contact` (LEAF) | 5 | 25 / 1.4.0 | `office_phone, contact_phone, contact_email` | `:519` | `src/autom8_asana/dataframes/schemas/contact.py:99` |
| `asset_edit` (LEAF) | 6 | 34 / 1.3.0 | `office_phone, vertical, asset_id, offer_id` | `:567` | `src/autom8_asana/dataframes/schemas/asset_edit.py:189` |
| `asset_edit_holder` (HOLDER) | 7 | 14 / 1.2.0 | `office_phone` | `:872` | `src/autom8_asana/dataframes/schemas/asset_edit_holder.py:28` |
| nine `process_*` (LEAF) | 10-18 | 16 / 1.0.0, one shared `PROCESS_SCHEMA` | `office_phone, vertical` | `:606-731` | `src/autom8_asana/dataframes/schemas/process.py:44` |
| `process` (LEAF, dynamic project) | none | no explicit schema path and no primary project; `PROCESS_SCHEMA` declares `task_type="Process"`, so it probably matches by name (not verified) | none | `:587` | `src/autom8_asana/dataframes/schemas/process.py:44` |
| `project`, `section` (LEAF, `body_parameterized=True`) | not warmed | 16 / 1.1.0 each (3 extras: `status, office_phone, vertical`) | none | `:964`, `:1004` | `src/autom8_asana/dataframes/schemas/project.py:46`, `src/autom8_asana/dataframes/schemas/section.py:49` |
| `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder`, `offer_holder`, `process_holder` (HOLDER) | not warmed | no frame schema | none | `:771-925` | none |
| `location`, `hours`, `calendar_integration` (LEAF) | not warmed | no frame schema | none | `:732-770` | none |
| `stage_transition` (OBSERVATION, virtual) | none | local parquet, 11 columns (1.8) | none | `:942` | `src/autom8_asana/lifecycle/observation_store.py:24-37` |

Primary Asana project identifiers for the entity types are the constants in `src/autom8_asana/core/project_registry.py` (for example the business, unit, unit-holder, offer, offer-holder and contact project constants at `:23-34`); they are not reproduced here. Entity-specific extra columns by schema: asset_edit 21 `ColumnDef`s (`schemas/asset_edit.py:19-172`), offer 21 (`src/autom8_asana/dataframes/schemas/offer.py`), unit_holder 10, contact 12, unit 9, business 6 (`company_id, name, office_phone, stripe_id, booking_type, facebook_page_id`), process 3, project 3, section 3, asset_edit_holder 1.

**Cache-governance fields on each descriptor** (`EntityDescriptor` dataclass, `:96-209`): `default_ttl_seconds` (business 3600, unit 900, contact 900, offer 180, asset_edit 300, process 60, location 3600, hours 3600, all others default 300), `freshness_sla_seconds` (3600 on business, unit, contact, offer, asset_edit, process), `warmable`, `warm_priority`, `join_keys`, `key_columns`, `cascading_field_provider`, `body_parameterized`. `DEFAULT_ENTITY_TTLS` is derived from the registry, filtering out the default (`src/autom8_asana/config.py:312-316`); fallback `DEFAULT_TTL = 300` (`:133`), stale-while-revalidate grace multiplier 3.0 (`:138`), last-known-good staleness multiplier 10.0 (`:157`), per-entity absolute ceilings in `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` for project, section and offer (`:295-310`).

### 1.6a Redis and in-process caches (schema-free key-value)

Provider selection: `ASANA_CACHE_PROVIDER` in `{memory, redis, tiered, none}`; with no explicit value, production plus `REDIS_HOST` selects Redis, anything else selects the in-process provider (`src/autom8_asana/cache/integration/factory.py:48-182`; Redis settings at `src/autom8_asana/settings.py:355-389`, `ssl` defaults to `True`, `host` defaults to `None`). The `tiered` value resolves to a plain Redis provider; the S3 cold tier was retired (`src/autom8_asana/cache/integration/factory.py:204-222`). `S3CacheProvider` is declared (`src/autom8_asana/cache/backends/s3.py:63`) but no factory path and no source constructor selects it (search for `S3CacheProvider(` finds only docstrings), so its keyspace is code-present and namespace-orphaned.

| Key | Type | Content | Line in `src/autom8_asana/cache/backends/redis.py` unless a path is given |
|---|---|---|---|
| `asana:tasks:{gid}:{entry_type}` | HASH (versioned path) or string (simple path) | one `CacheEntry` per task gid and `EntryType` | `src/autom8_asana/cache/backends/redis.py:98,322-335` |
| `asana:struc:{key}` | HASH | `EntryType.DATAFRAME` entries; the key already embeds the project gid | `:99,331-334` |
| `asana:tasks:{gid}:_meta` | HASH `entry_type -> version string` | per-task version map, expires with the entry TTL | `:337-346,536-544` |
| `asana:config` | none | prefix constant only; the search found its single occurrence at its definition, so it is an unused constant (control: `STRUC_PREFIX` found at its definition and its use) | `:100` |

`CacheEntry` fields (`src/autom8_asana/cache/models/entry.py:100-108`): `key, data, entry_type, version, cached_at, ttl (default 300), project_gid, metadata, freshness_stamp`. Redis serialization writes `data, entry_type, version, cached_at, ttl, project_gid, metadata, key, freshness_stamp` as hash fields (`src/autom8_asana/cache/backends/redis.py:354-372`). `EntryType` has 16 members: task, subtasks, dependencies, dependents, stories, attachments, dataframe, project, section, user, custom_field, detection, project_sections, gid_enumeration, insights, derived_timeline (`src/autom8_asana/cache/models/entry.py:20-55`; per-type TTL notes in the comments: project_sections 1800 s, gid_enumeration 300 s, insights 300 s, derived_timeline 300 s). Expiry is a per-key `EXPIRE`/`SETEX` (`redis.py:451-454,540-544`). Default in-process cache size is `memory_max_size = 10000` (`src/autom8_asana/settings.py:149`).

Frame cache: `DataFrameCache` keys are `"{entity_type}:{project_gid}"` (`src/autom8_asana/cache/dataframe/tiers/progressive.py:112-131`); the memory tier is an LRU bounded by `max_heap_percent` (default 0.3) and `max_entries` (default 100) (`src/autom8_asana/cache/dataframe/tiers/memory.py:81-82,104`); the progressive tier persists through `SectionPersistence.write_final_artifacts_async` (`progressive.py:306-318`), which is the S3 write path in 1.5.

### 1.7 DynamoDB and Secrets Manager (three items: one live-but-off-by-default, two dark)

**(a) Idempotency table, opt-in.** Item schema (`src/autom8_asana/api/middleware/idempotency.py:249-253,324-335`): partition key `pk = "{service_name}#{idempotency_key}"` (S), sort key `sk = "{METHOD}#{path_template}"` (S), attributes `status` (`processing` | `complete`), `request_fingerprint` (sha256 of the request body), `response_status` (N), `response_body` (base64 string), `response_headers` (JSON string, `content-type` only), `created_at` (ISO), `ttl` (N, epoch seconds; default `DEFAULT_TTL_SECONDS = 86400`, `:92`). Eligible endpoints (`:62-69`): `POST /v1/intake/business`, `POST /v1/intake/route`, `POST /v1/tasks/{task_gid}/custom-fields`, `PATCH /api/v1/entity/{entity_type}/{gid}`. Key rules: 8-256 characters of `[a-zA-Z0-9\-_.]` (`:51-53`). **Writer/reader:** only `DynamoDBIdempotencyStore` (`:242-411`), selected by `IDEMPOTENCY_STORE_BACKEND`.
**Since the prior pass this store is opt-in** (PR #535): `DEFAULT_IDEMPOTENCY_BACKEND = "noop"` (`src/autom8_asana/api/main.py:91`); `dynamodb` and `memory` must be named explicitly (`:403-442`); the table name defaults to `autom8-idempotency-keys` and the region to `us-east-1` via `IDEMPOTENCY_TABLE_NAME` and `IDEMPOTENCY_TABLE_REGION` (`:410-411`); a construction failure falls back to the no-op store (`:425-430`); an unknown backend value falls back to no-op (`:437-442`). The code comment gives the reason: the middleware runs before request authentication in this stack, so store-and-replay stays off until it runs after authentication (`:403-406`). The CI synthetic-coverage workflow pins `noop` (`.github/workflows/aegis-synthetic-coverage.yml:76`). The DynamoDB table is not declared in this repo's Terraform, and LocalStack in `docker-compose.yml` does not enable DynamoDB, so `memory` is the only local replay backend.

**(b) Hook-registry table (D6, new in PR #541, dark).** Writer: `HookRegistry` (`src/autom8_asana/trigger/hook_registry.py:119-422`), table name from env `ASANA_HOOK_REGISTRY_TABLE` (`:36,133-141`; the docstring names the table `autom8y-asana-hook-registry`, `:1`). All keys are strings `pk`/`sk` (declared a one-way door, `:4`):

| Item | `pk` / `sk` | Attributes | Line in `src/autom8_asana/trigger/hook_registry.py` |
|---|---|---|---|
| hook row | `HOOK#{handle}` / `META` | `state`, `resource_gid`, `webhook_gid`, `expires_at`, `created_at`, `updated_at`, `handshaken_at`, `ttl` | `:80-82,204-227` |
| active pointer | `PROJECT#{gid}` / `ACTIVE` | `handle`, `updated_at` | `:84-86,339-347` |
| lease | `LEASE#reconciler` / `-` | `owner`, `until` | `:88-90,392-409` |

`HookState` has 7 members: pending, handshaken, active, create_unknown, failed, compromised, removed (`:44-51`). TTLs: pending row `expires_at + 86,400 s` grace, closed rows (failed, removed) retained 30 days, compromised rows keep no TTL for forensics (`:38-40,216,283,290-296`). Delivery, decision-key and liveness rows are explicitly deferred to later receiver PRs (`:14`).

**(c) Hook-value secret prefix (D6, new, dark).** `HookStore` (`src/autom8_asana/trigger/hook_store.py:142-270`) is the one writer for the Secrets Manager prefix `autom8y/asana/webhook-hook/` (`:46`), one secret per 32-hex handle (`:47,92-96`), body `{hook_value, resource_gid, registered_at}` (`:199-201`), tags `service`, `purpose`, `handle`, later `webhook_gid` (`:206-211,234`). Write-once by construction: `create_secret` only, a second write raises `HookValueAlreadyStored` (`:220-223`); delete uses a 7-day recovery window (`:48,255`). It refuses unless `ASANA_HOOK_ENVIRONMENT` is exactly `production` and the credentials are the ECS task role (`:166-186`; marker logic `src/autom8_asana/trigger/hook_environment.py:92-133`). No value is read or logged.

**Wiring status of the whole `trigger/` package.** A search for `autom8_asana.trigger` over `src/` and `mcp/` finds only the package's own modules; nothing in production constructs these objects, and registration is gated on `ASANA_HOOK_SHADOW_ENABLED` being exactly `"1"` (`src/autom8_asana/trigger/__init__.py:13-15`; `src/autom8_asana/trigger/registration.py:291-292`). The shipped trigger map is empty (`src/autom8_asana/trigger/watched_projects.py:47`), so even with the flag on, zero webhooks register. The watched entity types are `asset_edit` and `offer` (`:44`); their project gids come from `ProjectTypeRegistry.get_primary_gid` and an unresolved gid refuses loudly (`:74-96`). Import-linter contracts confine boto3 to the two store modules (`pyproject.toml:245-270`).

### 1.8 Local filesystem stores (CLI and offline lanes; not S3)

| Path | Shape | Cite |
|---|---|---|
| `~/.autom8/stage_transitions/{entity_type}.parquet` (`StageTransitionStore`, append-only read-concat-write) | 11 columns: `entity_gid, entity_type, business_gid, from_stage, to_stage` (Utf8), `pipeline_stage_num` (Int64), `transition_type` (Utf8), `entered_at, exited_at` (Datetime us UTC), `automation_result_id` (Utf8), `duration_ms` (Float64) | `src/autom8_asana/lifecycle/observation_store.py:24-37,40,62-86` |
| `~/.autom8/timelines/{project_gid}.parquet` (`TimelineStore`) | 9 columns: `offer_gid, office_phone, offer_id, section_name, classification, entered_at, exited_at, task_created_at, story_count` | `src/autom8_asana/query/timeline_provider.py:31,65-106` |
| `~/.autom8/queries/{name}.yaml` and `./queries/*.yaml` (saved query templates) | query DSL, not SQL | `src/autom8_asana/query/saved.py:115-158`; `queries/*.yaml` (4 files, section 4.2) |

### 1.9 Asana as a store

Writes go through `SaveSession`, a Unit of Work with snapshot-comparison change tracking (`src/autom8_asana/persistence/session.py:1-9`, `src/autom8_asana/persistence/tracker.py:1-25`) and `CascadeOperation` batch stamping of descendant custom fields (`src/autom8_asana/persistence/cascade.py:1-30`). Idempotency for comment-based writes is an application convention: comments carry a marker string and the writer scans existing stories before posting (`src/autom8_asana/services/receipts_service.py:21-23`; marker prefixes `RCPT` at `:77`, `autom8y:contact-card` at `src/autom8_asana/automation/workflows/onboarding_walkthrough/contact_synthesis.py:77`). Neither Asana nor this code provides a compare-and-set (section 5.3).

### 1.10 Cross-service surfaces (HTTP only; downstream engine is MySQL)

| Endpoint | Direction | Wire grain | Cite |
|---|---|---|---|
| `POST /api/v1/gid-mappings/sync` | push | `{project_gid, mappings[{phone, vertical, task_gid}], source_timestamp, entry_count}` | `src/autom8_asana/services/gid_push.py:126-160,781-795` |
| `POST /api/v1/account-status/sync` | push, snapshot-replace | entries with grain `(phone, vertical, pipeline_type)`, source `section_classifier` | `:1140-1160`; sanitizer `:989-1062` |
| `POST /api/v1/vocabularies/sync` | push | enum option sets keyed by field (`field_key="vertical"` today) | `:1458-1482,1572` |
| `POST /api/v1/scheduling-stratum/sync` | push (default off) | per-office stratum | `src/autom8_asana/services/scheduling_stratum_push.py:65,242` |
| `POST /api/v1/data-service/insights` | read | `phone_vertical_pairs`, frame type, period | `src/autom8_asana/clients/data/_endpoints/insights.py:182`; virtual join targets in `src/autom8_asana/query/data_service_entities.py:25-80` |
| `GET /api/v1/appointments`, `GET /api/v1/leads` | read | query parameter `office_phone` | `src/autom8_asana/clients/data/_endpoints/simple.py:143,248` |
| `GET /api/v1/messages/export`, `POST /api/v1/insights/operator/execute-batch`, `POST /api/v1/insights/reconciliation/execute` | read | as named | `src/autom8_asana/clients/data/_endpoints/export.py:192`, `src/autom8_asana/clients/data/_endpoints/operator.py:47`, `src/autom8_asana/clients/data/_endpoints/reconciliation.py:156` |
| `POST /tokens/exchange-business` (auth service) | token mint | `{external_business_id, requested_scopes}` returning a single-tenant token; scope pinned to `data:read` | `src/autom8_asana/auth/business_token.py:182-210` |

**The downstream engine is MySQL, not PostgreSQL** `[EXPERIENTIAL]`: the ledger decision `.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md:124-135` records the confirm receipts (a MySQL URL scheme, an asyncmy normalizer, `INSERT ... ON DUPLICATE KEY UPDATE` call sites) and the probe notes in `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:15-40` give the schema name and the attach method. autom8y-asana never opens a connection to it from `src/`.

**The one relational client in the repo is a script, not the service.** `scripts/certification/landing_receipt.py` imports `mysql.connector` lazily (`:211`), opens a **read-only** session (`SET SESSION TRANSACTION READ ONLY`, `:232-233`), gates every statement to begin with `SELECT` and refuses statements touching the retired `ad_accounts` table (module docstring `:15-27`; selftest `:268-300`). It reads connection settings from a dotenv-style file outside the repo by variable name (`DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, `:52`); the file was not opened. The driver is not a project dependency (`:211-217` tells the operator to supply it at run time). Its SQL is the only SQL in the repo and is cataloged verbatim in section 4.

### 1.11 What changed since the prior pass (`c29f58f4` to `584c8f79`) in the persistence layer

1. **Idempotency store became opt-in (PR #535).** Default backend `noop` (1.7a). The prior pass recorded the default as `dynamodb`.
2. **Rate-limiter storage is pinned (PR #537).** `LIMITER_STORAGE_URI = "memory://"` (`src/autom8_asana/api/rate_limit.py:342`) is passed explicitly as `storage_uri` (`:357`) so `RATELIMIT_*` environment settings cannot redirect storage (`:356`); `LIMITER_CONFIG_FILENAME` points at a path that never exists so a working-directory dotenv file is never loaded (`:335-339`, PR #534). Counters live per ECS task in process memory, and the PAT bucket key is an HMAC under a per-process random key (`:104,209-218`), so PAT buckets are not comparable across tasks and would need a shared key if storage ever moves to Redis (docstring `:212-216`). Health probes are exempt from the limiter (PR #538, `exempt_from_rate_limit` at `:376-390`). Bucket keys now come only from verified identity (PR #533): `sa:asana-dataframe-resolver`, `jwt:{identity}[:{business_id}]`, `pat:{hmac}`, `ip:{addr}` (`:221-267`). The default limit is 100 per minute (`src/autom8_asana/core/api_settings.py:56-60`) and the resolver service account gets 600 per minute (`rate_limit.py:84,98`).
3. **New `src/autom8_asana/trigger/` package (PRs #539-#541).** Adds a DynamoDB table schema, a write-once Secrets Manager prefix, and an environment marker; all dark (1.7b-c).
4. **Substrate-v2 and registry are unchanged** in shape (1.3, 1.4); the 12-namespace count, 30 descriptors and 16 warmable are re-verified.

### 1.12 Inventory snapshot (as of `584c8f79`, repo-declared)

12 registered S3 namespaces (6 LIVE incl. 1 non-prod, 6 FOSSIL) plus 4 unregistered S3 keyspace families; 30 entity descriptors, 16 warmable, 11 frame-schema modules; Redis 3 live key shapes; 2 DynamoDB item families (idempotency, hook registry) and 1 Secrets Manager prefix; 2 local parquet stores; 0 relational tables in this repo; **BASE TABLE count of the downstream MySQL schema: not observable here `[UV-P]`**. Grading note: because no production oracle was consulted, this section is a code-inferred inventory.

## Tenant Resolution Model

### 2.1 What a tenant is, and the three keys that name it

There is **no `tenant_id` column, no schema-per-tenant and no row-level security** anywhere in this repo. A tenant is a **Business** (one clinic or office) and it is addressed by three different keys at three different altitudes; they are not interchangeable.

| Key | Where it lives | Role | Cite |
|---|---|---|---|
| **Business task GID** (Asana decimal string) | `business.gid`; `parent_gid` on every child frame row | **Identity.** GID-exact, never a join on a phone, never a display string | `src/autom8_asana/resolution/gfr/guard.py:1-40`; `src/autom8_asana/models/business/identity_supply.py:1-50` |
| **`office_phone`** (E.164 text; custom field "Office Phone", `PhoneTextField(cascading=True)`) | own field on Business, cascaded to Unit, Offer, Process, Contact; present as a column on 9 frame schemas | **Operational join key**; with `vertical` it forms the `PhoneVerticalPair` the data service filters on | `src/autom8_asana/models/business/business.py:267`; `src/autom8_asana/models/contracts/phone_vertical.py:1-17`; `src/autom8_asana/core/entity_registry.py:464-490` |
| **`company_id`** (custom field "Company ID") | own field on Business, cascades to all descendants | **Cross-plane identity** that maps to the downstream clinic guid and then to a single-tenant token | `src/autom8_asana/models/business/business.py:311-315`; `src/autom8_asana/auth/business_token.py:182-210` |

The tenant-root entity is **`business`** (`EntityCategory.ROOT`, `src/autom8_asana/core/entity_registry.py:464`). It is a **multi-tenant project**: every clinic is a row in one Business frame, and the frame is partitioned by project and entity (`dataframes/{project_gid}/{entity_type}/`), **not by tenant**. Tenant isolation is therefore a query-time predicate and a post-query assertion, never a storage boundary.

**Identity versus join, enforced in code.** The GFR guard states that no plan element may reach the tenant-identity field `company_id` through an `office_phone` value-join; the identity reach is the parent chain plus a gid-exact row only (`src/autom8_asana/resolution/gfr/guard.py:19-27`, forbidden key constant `:62`). The reason is in the join code: `execute_join` de-duplicates the target on the join key with `unique(..., keep="first")` (`src/autom8_asana/query/join.py:154-157`), so a phone shared by several rows silently resolves to an arbitrary one. After the read, `assert_rows_tenant_identity` raises if any returned row's `gid` differs from the anchored business gid, as defense in depth over the query engine's own filter (`src/autom8_asana/resolution/gfr/guard.py:28-40`).

### 2.2 DIRECT / CHAIN / GLOBAL classification (30 descriptors)

Method: the set of schema modules that declare an `office_phone` `ColumnDef` (AST walk: `asset_edit`, `asset_edit_holder`, `business`, `contact`, `offer`, `process`, `project`, `section`, `unit`) joined against the 30 descriptors.

| Class | Count | Entities | Basis |
|---|---|---|---|
| **DIRECT** (frame schema carries `office_phone`) | **17** | `business` (own custom field), `unit`, `offer`, `contact`, `asset_edit`, `asset_edit_holder`, nine `process_*` (shared `PROCESS_SCHEMA`), `project`, `section` | `ColumnDef(name="office_phone")` at `src/autom8_asana/dataframes/schemas/business.py:24`, `src/autom8_asana/dataframes/schemas/unit.py:54`, `src/autom8_asana/dataframes/schemas/offer.py:19`, `src/autom8_asana/dataframes/schemas/contact.py:77`, `src/autom8_asana/dataframes/schemas/asset_edit.py:80`, `src/autom8_asana/dataframes/schemas/asset_edit_holder.py:19`, `src/autom8_asana/dataframes/schemas/process.py:18`, `src/autom8_asana/dataframes/schemas/project.py:31`, `src/autom8_asana/dataframes/schemas/section.py:34` |
| **CHAIN** (no `office_phone` column; reach Business through `parent_gid` or the holder hierarchy) | **13** | `process` (no explicit schema path; resolution of its schema not verified), `unit_holder`, `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder`, `offer_holder`, `process_holder`, `location`, `hours`, `calendar_integration`, `stage_transition` | `src/autom8_asana/core/entity_registry.py:587,732-960`; `unit_holder` joins by `parent_gid` (`src/autom8_asana/enrollment/intent_projection.py:40-42`) |
| **GLOBAL** (declared tenant-free) | **0 declared** | none; `project` and `section` receive the project gid per request (`body_parameterized=True`) yet still carry `office_phone`/`vertical` columns | `:964-1050` |

Count check: 17 + 13 = 30. (The prior pass counted 18 DIRECT and 12 CHAIN by classing `process` as DIRECT; `process` has no explicit schema binding in its descriptor, so this pass keeps it in CHAIN until a schema resolution is observed `[INFERRED]`.)

### 2.3 The hierarchy that carries the chain (Asana parent graph)

```
Business (ROOT)
 |- UnitHolder (HOLDER -> business)
 |   `- Unit (COMPOSITE)
 |       |- OfferHolder (HOLDER -> unit)  -> Offer (LEAF)
 |       `- ProcessHolder (HOLDER -> unit) -> Process / process_* (LEAF)
 |- ContactHolder -> Contact
 |- AssetEditHolder -> AssetEdit
 `- LocationHolder -> Location; DnaHolder; ReconciliationHolder; VideographyHolder
```

Source: `parent_entity`, `holder_for`, `holder_attr` fields on the descriptors (`src/autom8_asana/core/entity_registry.py:771-925`; `offer_holder` and `process_holder` declare `parent_entity='unit'` at `:910,924`). Offer sits **four hops** below Business (Offer, OfferHolder, Unit, UnitHolder, Business). The cascade walker defaults to `max_depth=5` (`src/autom8_asana/dataframes/resolver/cascading.py:203`), one hop of slack. Upward traversal from any task gid to the Business root is `_traverse_upward_async` (`src/autom8_asana/models/business/hydration.py:768`) and the strategy chain `SessionCacheStrategy`, `NavigationRefStrategy`, `DependencyShortcutStrategy`, `HierarchyTraversalStrategy` (`src/autom8_asana/resolution/strategies.py:63-193`).

### 2.4 Cascade (denormalized tenant-key propagation)

Tenant keys are denormalized down the tree two ways: **read-time** (`cascade:` frame columns resolved by walking parents) and **write-time** (`CascadeOperation` stamping custom fields on descendants in Asana, `src/autom8_asana/persistence/cascade.py:1-30`). The authoritative declarations are the nested `CascadingFields` classes; the example in `src/autom8_asana/models/business/fields.py:40-58` is a docstring, not a registry.

| Source | Field | `target_types` | `allow_override` | Cite |
|---|---|---|---|---|
| Business | Office Phone | Unit, Offer, Process, Contact | False | `src/autom8_asana/models/business/business.py:305-309` |
| Business | Company ID | `None` (all descendants) | False | `:311-315` |
| Business | Business Name (`source_field="name"`) | Unit, Offer | False | `:317-322` |
| Business | Primary Contact Phone | Unit, Offer, Process | False | `:324-328` |
| Unit | Platforms, Vertical, Booking Type, MRR, Weekly Ad Spend | defined per field | Platforms opts in to override | `src/autom8_asana/models/business/unit.py:157-195` |
| UnitHolder | Custom Cal Status plus 9 provider and id fields | all descendants | False | `src/autom8_asana/models/business/unit.py:476-518` |

**`vertical` has two sources.** `unit.vertical` is `cf:Vertical` (`src/autom8_asana/dataframes/schemas/unit.py:61-64`), while the offer frame declares scheduling-posture columns as `cascade:` off the UnitHolder (`src/autom8_asana/dataframes/schemas/offer.py:84-205`; the 1.6.0 comment documents that the earlier `cf:` sourcing resolved null on every row). The `(office_phone, vertical)` key is therefore sourced differently on its two sides. Matching modes also differ: `cf:` resolves through a normalizer that strips non-alphanumerics, `cascade:` compares lower-cased trimmed names only (comment in `src/autom8_asana/dataframes/schemas/offer.py:84-136`), so a field-name spelling that works for one fails for the other.

### 2.5 Resolver flow: inbound identity to tenant key to filter point

| Lane | Inbound | Resolution | Filter or injection point | Cite |
|---|---|---|---|---|
| **PAT routes** (`/api/v1/{tasks,projects,sections,users,workspaces,dataframes,offers,exports,tags}/*`) | Asana PAT | tenant is whatever the PAT can see; project gid in path or body | none at the application layer; Asana permissions are the isolation | JWT exclusion list `src/autom8_asana/api/main.py:457-481` |
| **S2S routes** (resolver, query, receipts, intake, identity-supply and others) | service JWT | caller supplies criteria in the body | `JWTAuthConfig(require_business_scope=True)` is set (`main.py:481`); a search of `src/autom8_asana/api/` and `auth/` for `business_id` finds it only in that comment, in rate-limit keying (`rate_limit.py:203-205`) and in the per-business token code, so **no application code uses the `business_id` claim as a data filter** `[UV-P]` whether the upstream auth middleware enforces it | `src/autom8_asana/api/main.py:457-481` |
| **Resolver** `POST /v1/resolve/{entity_type}` (S2S only, PAT refused) | criteria list: `phone` (E.164, pattern `^\+[1-9]\d{6,14}$`), `vertical`, `offer_id`, `offer_name`, `contact_email`, `contact_phone`, plus any schema column (`extra="allow"`) | `GidLookupIndex` and `DynamicIndex` lookup to task gid | frames are filtered by criteria values; ambiguity returns a match count | `src/autom8_asana/api/routes/resolver.py:90,154-190`; `src/autom8_asana/api/routes/resolver_models.py:31-107` |
| **GFR** (resolve fields from any gid) | any Asana gid | hydrate, detect type, walk parents to the Business gid; identity read is `where gid == business_gid` with no join | post-read tenant assertion (2.1) | `src/autom8_asana/resolution/gfr/guard.py:1-40` |
| **Identity supply** | offer gid | upward walk to Business candidates; identity published from Tier 1 (project membership) only; more than one candidate returns the set with `match_count` and no value | allow-list on tier, never on confidence | `src/autom8_asana/models/business/identity_supply.py:1-50` |
| **Per-business data read** (grain bridge) | Business `company_id` | normalize to an external business id, `POST /tokens/exchange-business`, then a provider wrapping exactly one single-tenant token; the served tenant is the token's `business_id`, which **dominates** a client `office_phone` parameter (anti-IDOR) | one provider per tenant, never reused | `src/autom8_asana/auth/business_token.py:182-210`; `src/autom8_asana/auth/per_business_provider.py:1-24` |
| **Scheduling-gate bridge** | three warmed S3 frames (unit_holder, business, offer) | intent x identity joined on `unit_holder.parent_gid == business.gid`; roster intersected on `office_phone` (strip-only, no E.164 canonicalization) | `business.office_phone` is the write key | `src/autom8_asana/enrollment/intent_projection.py:14-70,178-191` |

**Workspace resolution.** There is a single configured Asana workspace: `ASANA_WORKSPACE_GID` through `get_workspace_gid()` (`src/autom8_asana/config.py:117-123`). API preload, admin and warmer paths refuse to run when it is absent (`src/autom8_asana/api/preload/progressive.py:349-357`, `src/autom8_asana/lambda_handlers/cache_warmer.py:452-458`). All service-side Asana reads use one bot credential (`src/autom8_asana/api/preload/legacy.py:482`). The workspace gid is never a key in S3, Redis or DynamoDB, so there is no cross-workspace partitioning: the service assumes one workspace.

**Caller-identity namespaces (not tenant data).** Rate-limit buckets and idempotency partition keys are both keyed by verified caller identity (service account id, then client id, then subject), `jwt:{identity}[:{business_id}]` and `{service_name}#{key}` respectively (`src/autom8_asana/api/rate_limit.py:168-206`; `src/autom8_asana/api/middleware/idempotency.py:474-530,629`).

### 2.6 Phone-key normalization is not uniform (a standing join hazard)

| Site | Normalization | Cite |
|---|---|---|
| Frame join `execute_join` | exact string equality; null keys dropped | `src/autom8_asana/query/join.py:142-160` |
| `GidLookupIndex` | canonical key `pv1:{col1}:{col2}`, null key or gid rows skipped | `src/autom8_asana/services/gid_lookup.py:235-293` |
| `DynamicIndexKey` | `idx1:col1=val1:col2=val2`; values lower-cased per the docstring | `src/autom8_asana/services/dynamic_index.py:29-67` |
| Enrollment bridge | strip-only by design | `src/autom8_asana/enrollment/intent_projection.py:14-70` |
| Account-status push | regex `E164_PHONE_PATTERN` imported from the shared schema package; invalid rows skipped | `src/autom8_asana/services/gid_push.py:1008-1045` |
| `PhoneVerticalPair` | owned by `autom8y_core`; validation lives in that SDK | `src/autom8_asana/models/contracts/phone_vertical.py:1-12` |

### 2.7 NULL posture of the tenant key

`office_phone` is **nullable by construction on every DIRECT entity except Business**: the extra-column definitions are all `nullable=True` (1.6), and cascade-sourced columns resolve null when the ancestor walk fails. The schema comments call it "null cascade = silent NOT_FOUND (FIND-005)" (`src/autom8_asana/dataframes/schemas/offer.py:15-16`). Guardrails: `CASCADE_NULL_WARN_THRESHOLD = 0.05` and `CASCADE_NULL_ERROR_THRESHOLD = 0.20` (`src/autom8_asana/dataframes/builders/cascade_validator.py:40-41`), and a population-floor flag that rides in `watermark.json` (1.5).

Dated figures found in code comments, **not re-measured** `[EXPERIENTIAL]`: Business-tier `office_phone` populated 2400 of 2572 (93.3%), `unit_holder.parent_gid == business.gid` 2082 of 2082 (`src/autom8_asana/enrollment/intent_projection.py:30-31,41-42`); offer-frame `custom_cal_status` populated 2 of 4191 on a fresh frame before the 1.6.0 re-sourcing (`:25-27`). Some active offices lack a `Company ID` on the Business ancestor, so a guid-keyed producer cannot see them while a phone-keyed writer can (`:52-66`). No production NULL-rate query was run.

### 2.8 Ambiguities flagged

1. `asset_edit` declares `aliases=("process",)` (`src/autom8_asana/core/entity_registry.py:579`), colliding with the separate `process` descriptor name: a registry alias ambiguity, not a tenant-key ambiguity.
2. `(office_phone, vertical)` is the unit grain, so a phone-only join to `unit` fans out and `keep="first"` picks arbitrarily (2.1). The ratification record states the same fact for the identity join (`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md:60-66`, quoting that "one phone holds many rows").
3. The webhook trigger map is empty by default (1.7), so no project is yet wired to a trigger.

## FK Chain Catalog

There are **no declared foreign keys in this repo** (no DDL). Referential structure is carried by (a) the Asana parent graph (`parent_gid`), (b) denormalized key columns (`office_phone`, `vertical`, `company_id`), (c) registry-declared join keys (`EntityDescriptor.join_keys`), and (d) a cross-service key chain that ends in MySQL. Referential integrity is application-asserted, and every frame join is a left join on a text key with no engine to refuse an orphan.

### 3.1 Chain to the tenant root, per entity

Sources: `parent_entity` and `join_keys` on descriptors (`src/autom8_asana/core/entity_registry.py:464-925`); the derived `ENTITY_RELATIONSHIPS` list (`src/autom8_asana/query/hierarchy.py:42-101`).

| Entity | Chain (child to Business) | Depth | Pseudo-SQL skeleton | Notes |
|---|---|---|---|---|
| `unit_holder`, `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder`, `asset_edit_holder` | `parent_gid -> business.gid` | 1 | `X JOIN business ON X.parent_gid = business.gid` | `parent_entity="business"` at `:771-905`; unit_holder measured 2082 of 2082 in a dated comment (`src/autom8_asana/enrollment/intent_projection.py:41-42`) `[EXPERIENTIAL]` |
| `contact` | Contact, ContactHolder, Business | 2 | by key: `contact.office_phone = business.office_phone` | `join_keys=(("business","office_phone"),)` at `:519-537` |
| `asset_edit` | AssetEdit, AssetEditHolder, Business | 2 | by key: `office_phone` (no `join_keys` declared, chain is cascade-only) | `:567-585` |
| `unit` | Unit, UnitHolder, Business | 2 | by key: `unit.office_phone = business.office_phone` | `join_keys` business and offer at `:492-517` |
| `offer_holder`, `process_holder` | holder, Unit, UnitHolder, Business | 3 | n/a | `parent_entity="unit"` at `:910,924` |
| **`offer`** | Offer, OfferHolder, Unit, UnitHolder, Business | **4** (more than 3 hops, a design-review candidate) | by key: `offer.office_phone = unit.office_phone` (phone only, not vertical) and `= business.office_phone` | `join_keys` unit and business at `:539-565`; mitigated by cascade denormalization and `max_depth=5` |
| **`process`, `process_*`** | Process, ProcessHolder, Unit, UnitHolder, Business | **4** | by key `(office_phone, vertical)` | pipeline projects are separate Asana projects while ancestry lives under the Unit tree |
| `location`, `hours`, `calendar_integration` | Location to LocationHolder to Business; the others unverified | 2 or more | none | no frame schema `[UV-P]` for the `hours` and `calendar_integration` parents |
| `stage_transition` | `business_gid` column on the local parquet | 1 (denormalized) | `stage_transition.business_gid = business.gid` | column present in the store schema (`src/autom8_asana/lifecycle/observation_store.py:27`); nullability of the source not re-verified |

Cardinality labels derive from category pairs only: root or composite to leaf is `1:N`, leaf to root or composite is `N:1`, anything else `unknown`, so `business` to `unit` is `unknown` (`src/autom8_asana/query/hierarchy.py:42-61`). Saved queries exercise two joins: offer to business on `office_phone` selecting `booking_type` (`queries/offers_with_business.yaml:7-9`) and offer to the data-service `spend` factory over period `T30` on `office_phone` (`queries/offers_with_spend.yaml:7-13`).

### 3.2 Multi-source reachability and the canonical choice

| Pair | Two ways to reach | Canonical (as coded) | Hazard |
|---|---|---|---|
| Offer to Business | parent chain by gid (4 hops) or `office_phone` equality | **identity: parent chain, gid-exact** (GFR); roster and aggregates use `office_phone` | a phone can map to more than one guid (counted as `guid_ambiguous_phones`, `src/autom8_asana/enrollment/intent_projection.py:62`); a Business with no phone is invisible to phone joins |
| Offer to Unit | parent chain or `office_phone` | parent chain for hierarchy, phone for frames | `unit` has one row per `(phone, vertical)`, so a phone-only join fans out and `keep="first"` takes an arbitrary vertical (`src/autom8_asana/query/join.py:157`) |
| Business to guid | `company_id` custom field | `company_id` | the guid-to-`office_phone` join has no standalone store; the ratification states "Nobody holds the join" `[EXPERIENTIAL]` (`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md:60-66`) |

### 3.3 Frame-key type disagreements and duplicate-key policies

- `offer.offer_id` is `Utf8` (`src/autom8_asana/dataframes/schemas/offer.py:41`) while `asset_edit.offer_id` is `Int64` (`src/autom8_asana/dataframes/schemas/asset_edit.py:126`); a cross-frame equality needs a cast. Downstream the ledger records a third representation, a string foreign key to an integer primary key, which MySQL coerces `[EXPERIENTIAL]` (`.ledge/spikes/SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md:211`).
- Three different duplicate policies on the same `(phone, vertical)` grain: `GidLookupIndex.from_dataframe` is **last-write-wins** (`src/autom8_asana/services/gid_lookup.py:293`), `DynamicIndex` is **multi-valued** (`defaultdict(list)`, `src/autom8_asana/services/dynamic_index.py:228,245`), the account-status push is **first-wins** (`src/autom8_asana/services/gid_push.py:1037-1041`).

### 3.4 Cross-service key chains

**(A) The chain the code itself walks in SQL** (`scripts/certification/landing_receipt.py`, staged lookups that carry identifiers through Python because a server-side join across mismatched collations "grinds", `:54-58,480-485`):

```
appointments(id, office_phone, phone, ...)      -- :431-438
  -> leads(phone, id, office_phone, source_id, ...)   -- :454-455   (join on phone)
  -> ads(ad_id, adset_id)                             -- :472       (leads.source_id = ads.ad_id)
  -> adsets(adset_id, campaign_id)                    -- :475
  -> campaigns(campaign_id, chiropractor_id)          -- :479
  -> chiropractors(guid, office_phone)                -- :487       (campaigns.chiropractor_id = chiropractors.guid)
```

The script names the collation clash explicitly: `campaigns.chiropractor_id` is `latin1_swedish_ci` while `chiropractors.guid` is `utf8mb3_general_ci` (`:54-58,480-485`). The tenant terminus is `chiropractors.office_phone`; clinic resolution reads `office_phone, guid, office, status` from `chiropractors` (`:501-502`).

**(B) Ledger-sourced chains** `[EXPERIENTIAL]` (dated 2026-07-08, not re-observed): `assets.chiropractor_id -> chiropractors.guid`; `assets.offer_id -> offers.offer_id -> offers.category -> verticals.key`; an asset-to-vertical bridge; `ads_insights -> ads -> ad_creatives -> assets_ad_creatives -> assets` (`.ledge/spikes/SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md:121`; join structure in the asset-linkage spike, section 4.3). The tenant root downstream is `chiropractors`, dual-keyed by a string guid primary key and a unique `office_phone` (`:95`).

**(C) Asana to data to token chain:** Offer gid, upward walk to Business gid, `company_id`, external business id, `POST /tokens/exchange-business`, single-tenant token, then per-tenant data reads (2.5; `src/autom8_asana/auth/business_token.py:182-250`).

### 3.5 Orphans

No entity is both un-keyed and un-chained. Residual risks: `location_holder` and `process_holder` have `primary_project_gid=None` and therefore no frame (`src/autom8_asana/core/entity_registry.py:828,924`); `process` has `primary_project_gid=None` and no explicit schema path (`:587-597`); Business rows with a null `office_phone` (about 6.7% in the dated figure) drop out of every phone-keyed join silently (2.7). The prior pass's claim that ancestor fetch failures are typed permanent faults was not re-verified.

## Validation Query Catalog

**Scope cap honored.** Queries below are extracted verbatim from a repo file or from a cited ledger record. None was composed in this pass. **No query was executed**; there is no oracle access in this run. Derivation date: 2026-11-14. Source hash at derivation: `584c8f79`.

### 4.1 Oracle access paths (as documented, not exercised)

- **Downstream MySQL, schema `dtenuta`.** From the `autom8y-data` repo, `QueryConnection.from_settings()` attaches the RDS instance as `{attach_as}_raw` (`attach_as` default `"dtenuta"`), and aggregation is pushed down with `SELECT * FROM mysql_query('dtenuta_raw', '<sql>')` so it runs on the server (`.ledge/spikes/SPIKE-asset-linkage-coverage-measurement-2026-07-08.md:108-113`; `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:15-17,142-146`) `[EXPERIENTIAL]`. A second documented path is the read-only certification script, which uses a direct driver session (1.10).
- **This service's own stores (S3, Redis, DynamoDB).** No in-repo oracle script reads production. The nearest are the freshness report (`src/autom8_asana/metrics/freshness.py:281-362`, an S3 listing) and the substrate provability sweep (`src/autom8_asana/lambda_handlers/prov_sweep.py`, an enumeration of `dataframes-v2/` pointer keys). Reading a frame schema needs a parquet read of the warmed object; no repo query does this.
- **The local MCP.** This session's DuckDB MCP is a local file; whether any session attaches the production schema is unknown here.

### 4.2 Repo-resident query surfaces

| ID | File | Kind | Use when |
|---|---|---|---|
| V-1 | `scripts/certification/landing_receipt.py` (8 distinct SELECT forms) | real SQL, MySQL dialect, read-only | tracing the appointment-to-clinic chain before trusting an attribution claim |
| V-2 | `queries/active_offers.yaml`, `queries/mrr_by_vertical.yaml`, `queries/offers_with_business.yaml`, `queries/offers_with_spend.yaml` | **saved-query YAML for the in-repo query engine, not SQL** (`command`, `entity_type`, `classification`, `select`, `join`, `group_by`, `aggregations`) | frame-level aggregation over the warmed offer and business frames |

V-2 shapes: `active_offers` is `rows` over `offer` with `classification: active`, selecting `gid, name, mrr, office_phone, vertical, section`, ordered by `mrr` desc, limit 500; `mrr_by_vertical` is `aggregate` grouped by `vertical` with `sum(mrr)` and `count(gid)`; the two join files are summarized in 3.1.

### 4.3 Verbatim SQL

**V-1, from `scripts/certification/landing_receipt.py` (line numbers in the file):**

```sql
-- :431   (f-string; {cols} = "id, created, office_phone, phone, start_datetime, status, source, type", defined at :428)
SELECT {cols} FROM appointments WHERE id IN ({ph})
-- :434-436
SELECT {cols} FROM appointments WHERE office_phone = %s AND type = 'appt' AND created >= %s ORDER BY created
-- :438-439
SELECT {cols} FROM appointments WHERE type = 'appt' AND created >= %s ORDER BY created
-- :454-455
SELECT phone, id, office_phone, email, source_id, full_name, platform FROM leads WHERE phone IN ({ph})
-- :472
SELECT ad_id, adset_id FROM ads WHERE ad_id IN ({ph})
-- :475
SELECT adset_id, campaign_id FROM adsets WHERE adset_id IN ({ph})
-- :479
SELECT campaign_id, chiropractor_id FROM campaigns WHERE campaign_id IN ({ph})
-- :487
SELECT guid, office_phone FROM chiropractors WHERE guid IN ({ph})
-- :501-502
SELECT office_phone, guid, office, status FROM chiropractors WHERE office_phone IN ({ph})
```

The harness also pins the session read-only with `SET SESSION TRANSACTION READ ONLY` and `START TRANSACTION READ ONLY` (`:232-233`).

**V-3, verbatim from the asset-linkage spike** `[EXPERIENTIAL]` (`.ledge/spikes/SPIKE-asset-linkage-coverage-measurement-2026-07-08.md`, the "Leg 2" block after line 114; MySQL dialect; run through the `mysql_query` push-down):

```sql
SELECT
  CONCAT(SUBSTRING(ai.`date`,1,4), '-Q', QUARTER(ai.`date`)) AS qtr,
  COUNT(*)                                               AS n_rows,
  ROUND(SUM(COALESCE(ai.spend,0)),2)                     AS spend_total,
  ROUND(SUM(CASE WHEN a.ad_id IS NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_no_ad_row,
  ROUND(SUM(CASE WHEN a.ad_id IS NOT NULL AND ac.creative_id IS NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_no_creative,
  ROUND(SUM(CASE WHEN j.ad_creative_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_junction_any,
  ROUND(SUM(CASE WHEN jp.ad_creative_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_junction_platform_matched,
  ROUND(SUM(CASE WHEN ac.asset_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_direct_column,
  ROUND(SUM(CASE WHEN j.ad_creative_id IS NOT NULL OR ac.asset_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_either,
  SUM(j.ad_creative_id IS NOT NULL)                      AS rows_junction_any,
  SUM(ac.asset_id IS NOT NULL)                           AS rows_direct_column,
  SUM(j.ad_creative_id IS NOT NULL OR ac.asset_id IS NOT NULL) AS rows_either
FROM ads_insights ai
LEFT JOIN ads a  ON a.ad_id = ai.ad_id
LEFT JOIN ad_creatives ac ON ac.creative_id = a.creative_id
LEFT JOIN (SELECT DISTINCT ad_creative_id FROM assets_ad_creatives) j
       ON j.ad_creative_id = a.creative_id
LEFT JOIN (SELECT DISTINCT ad_creative_id, platform_id FROM assets_ad_creatives) jp
       ON jp.ad_creative_id = a.creative_id AND jp.platform_id = ai.platform
GROUP BY qtr
ORDER BY qtr;
```

**V-4, the SD-02 liveness probes** `[EXPERIENTIAL]` (`.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:21-27`): `SELECT COUNT(*), MAX(synced_at) FROM account_status` returned `(0, NULL)` and `SELECT COUNT(*) FROM chiropractors` returned 1402 on 2026-07-08; a third probe read `information_schema.table_constraints` for `account_status` and found `PRIMARY KEY` and `uq_phone_vertical_pipeline` (UNIQUE) only, no foreign key. The spike records that result but not the third statement's text, so no SQL is reproduced for it here.

**V-5, criteria-supplied canonical information-schema queries** (verbatim from the schema-drift criteria file, **not repo-derived**; these are the queries a drift pass runs against the production oracle; `{database_name}` is the downstream schema):

```sql
-- Q-a  BASE TABLE enumeration
SELECT table_name FROM prod.information_schema.tables
WHERE table_schema = '{database_name}' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Q-d  FK enumeration
SELECT table_name, column_name, referenced_table_name, referenced_column_name
FROM prod.information_schema.key_column_usage
WHERE referenced_table_name IS NOT NULL
ORDER BY table_name, column_name;

-- Q-c  NULL-rate on a nullable tenant-key column (run for each suspect column)
SELECT COUNT(*) total, COUNT({col}) non_null,
       ROUND(100.0 * COUNT({col}) / NULLIF(COUNT(*),0), 2) pct_populated
FROM prod.{table};
```

### 4.4 Coverage of the four required query roles

| Role | Held in this catalog | Gap |
|---|---|---|
| Q-a BASE TABLE enumeration | V-5 (criteria-supplied) | no repo or ledger statement for the downstream schema |
| Q-b tenant-key column presence, NOT NULL versus NULLABLE | **none** | no repo or ledger query exists, and composing one is out of scope; recorded as a gap |
| Q-c NULL-rate on a nullable tenant-key column | V-5 template | no run result in this pass |
| Q-d FK enumeration | V-5 | no run result in this pass |

**Re-run triggers and cadence.** Re-run Q-a, Q-c, Q-d when any of these change: a file under `src/autom8_asana/dataframes/schemas/`, the descriptor list in `src/autom8_asana/core/entity_registry.py`, `src/autom8_asana/storage_namespace.py`, a new `*/sync` push endpoint in `src/autom8_asana/services/gid_push.py`, or the DynamoDB item schemas in 1.7. Cadence: with every refresh of this file (the expiry is 7 days). There is no `schema_snapshot_hash` field in this file's frontmatter, so a drift pass cannot compare a hash.

## Constraints and Null Posture

There is no DDL, so there are no NOT NULL, UNIQUE, CHECK or ON DELETE constraints to catalog from this repo. The analogs are the conditional-write conditions each store supports, the application validators that stand in for constraints, and, for the downstream MySQL, what the ledger records. Each store is classified as engine-enforced or application-only below.

### 5.1 Engine-enforced invariants in the stores this repo operates

| Store | Enforced by the engine | Cite |
|---|---|---|
| S3 `dataframes-v2/` | **staged versions are write-once** (`PutObject` with `IfNoneMatch="*"`); **the pointer swap is a true compare-and-swap** (`If-Match` with the observed ETag; `CREATE_IF_ABSENT` becomes `If-None-Match: *`); outcomes 412 lost race, 404 pointer gone, 409 concurrent delete, each mapped to a typed exception; a blank `if_match` is refused in code because `IfMatch=""` would degrade to an unconditional overwrite | `src/autom8_asana/substrate/store.py:343,351-399,371-372` |
| DynamoDB idempotency | `ConditionExpression="attribute_not_exists(pk)"` on claim (single winner); DynamoDB TTL on `ttl` | `src/autom8_asana/api/middleware/idempotency.py:310-346` |
| DynamoDB hook registry | every state transition is a conditional write, a lost condition raises `HookRegistryConflict`; first handshake wins (`#state = :pending AND expires_at > :now`); **one active hook per project** (`attribute_not_exists(pk) OR #handle = :old` in a `transact_write_items` with the state move); lease acquired conditional on absence, expiry or same owner; consistent reads by default; no `Scan` anywhere (the task role holds none) | `src/autom8_asana/trigger/hook_registry.py:16-19,204-227,245-252,311-373,392-409` |
| Secrets Manager hook prefix | `CreateSecret` only, so a second write is refused by the service (`ResourceExistsException`) and by IAM (no `PutSecretValue`, per the module docstring) | `src/autom8_asana/trigger/hook_store.py:7-11,220-223` |
| Redis | per-key TTL only | `src/autom8_asana/cache/backends/redis.py:451-454,540-544` |
| S3 `dataframes/`, `cache-warmer/checkpoints/`, `soak-sentinel/` | **none**: unconditional `put_object`, last writer wins | `src/autom8_asana/dataframes/storage.py:524-536`; `src/autom8_asana/lambda_handlers/checkpoint.py:313-318` |

### 5.2 Application-only invariants (no database mirror)

| Invariant | Where asserted | Cite |
|---|---|---|
| `ArtifactId`: digits-only `project_gid`, servable `entity_type` derived from warmable descriptors, refused at construction | `__post_init__` | `src/autom8_asana/substrate/identity.py:30,56-66,91-107` |
| `FreshnessProof` must carry a timezone-aware instant | `__post_init__` | `src/autom8_asana/substrate/freshness.py:62-82` |
| Asana GID shape: `^\d{10,20}$` (reconciliation), `^[0-9]{1,64}$` (identity-supply path, unconditional), `^\d{1,64}$` for `GidStr` **only when `AUTOM8Y_ENV` is not test, local or LOCAL** (the default env value counts as production) | regex | `src/autom8_asana/reconciliation/section_registry.py:37`; `src/autom8_asana/api/routes/identity_supply.py:111`; `src/autom8_asana/api/models.py:46-54` |
| Idempotency key: 8-256 characters of `[a-zA-Z0-9\-_.]`; same key with a different body returns 422 | validator and fingerprint compare | `src/autom8_asana/api/middleware/idempotency.py:51-53,447-460,686-700` |
| Hook handle: 32 lowercase hex characters; hook header 16-256 printable non-space ASCII | regex | `src/autom8_asana/trigger/hook_store.py:47`; `src/autom8_asana/trigger/registration.py:72-75` |
| Section manifest compatible only when `schema_version` equals the current version (empty means legacy and forces rebuild); `honest_contract_complete` is true only when zero sections failed | method and function | `src/autom8_asana/dataframes/section_persistence.py:136-149,324-343` |
| **Converged write gate**: a final-frame write honors a fail-closed `WriteDecision`; `PRESERVE_PRIOR_GOOD` skips the save and keeps the prior frame; a below-floor frame with no decision is refused | `write_final_artifacts_async` | `src/autom8_asana/dataframes/section_persistence.py:962-1060` |
| Per-row E.164 and `(phone, vertical, pipeline_type)` duplicate-grain guards, mirroring a remote UNIQUE `uq_phone_vertical_pipeline` and an `extra="forbid"` receiver | `_sanitize_status_entries` | `src/autom8_asana/services/gid_push.py:989-1062` |
| Cascade null-rate thresholds 5% warn, 20% error | validator | `src/autom8_asana/dataframes/builders/cascade_validator.py:40-41` |
| Write-class authorization: deny-by-default per-write-class allowlists from `ASANA_WRITERS_*` env variables; mode unset or malformed resolves to ENFORCE, only the literal `observe` relaxes it; the `scope` axis is refused | `write_authz` | `src/autom8_asana/api/write_authz.py:1-60,122-175` |
| Response envelopes parse with `extra="ignore"`, so a changed server contract is tolerated silently; an HTTP 2xx does not prove persistence | `model_config` | `src/autom8_asana/services/gid_push.py:98-106` |

### 5.3 Where the code relies on a constraint the store does not enforce

1. **S3 frame writes are last-writer-wins and two-object.** `save_dataframe` writes `dataframe.parquet` then `watermark.json` as two separate puts; the docstring says consumers "must tolerate inconsistent state" on partial failure (`src/autom8_asana/dataframes/storage.py:893-897,931-960`). No `IfMatch` is sent, and no code under `src/autom8_asana/dataframes/` or `src/autom8_asana/cache/` sends one (search for `IfMatch`/`IfNoneMatch` across `src/` finds only the substrate store). The compensating control is the application-level write gate in 5.2, not the store.
2. **Manifest read-modify-write is serialized per process only.** `SectionPersistence` holds one `asyncio.Lock` per project in process memory (`src/autom8_asana/dataframes/section_persistence.py:418-426`); two Lambda or ECS processes can interleave a manifest update on the same key.
3. **Checkpoint single-writer is an infrastructure assumption.** Safety of `latest.json` depends on each warmer function's reserved concurrency of 1, and only when each function uses a distinct prefix (`src/autom8_asana/lambda_handlers/checkpoint.py:33-39,160-166`).
4. **Asana writes carry no concurrency token.** `SaveSession` tracks changes by snapshot comparison (`src/autom8_asana/persistence/tracker.py:1-25`); a search of `src/autom8_asana/persistence/` and `src/autom8_asana/transport/` for `etag`, `if-match`, `optimistic`, `precondition` and `conflict` found only unrelated hits (positioning-conflict errors in `persistence/errors.py`; control: `class ChangeTracker` found at `tracker.py:17`). Comment-marker dedupe is check-then-post, so it is not atomic (`src/autom8_asana/services/receipts_service.py:21-23`).
5. **Idempotency protects nothing by default.** With the no-op store, `claim` returns True and `get` returns None for every call (`src/autom8_asana/api/middleware/idempotency.py:414-439`); store-and-replay only exists when `IDEMPOTENCY_STORE_BACKEND` is set. When the DynamoDB store is on, **any non-conditional claim error returns False** (`:340-346`), the follow-up `get` then returns None on failure, and the middleware "falls through to execute the handler" (`:666-669`), so a DynamoDB outage degrades to passthrough (and adds the `X-Idempotent-Degraded` header on the paths where the store call raises, `:644-647,661-664`). A finalize failure for a service-identity caller returns 500 `IDEMPOTENCY_KEY_NOT_PERSISTED` with the processing sentinel left in place until TTL (`:782-833`).
6. **Rate limits are per process.** In-memory storage means N ECS tasks give N times the configured limit (`src/autom8_asana/api/rate_limit.py:341-358`).
7. **Duplicate `(phone, vertical)` keys resolve three different ways** (3.3), and `execute_join` keeps the first row, so the result depends on iteration order.
8. **Webhook delivery has no dedupe store yet.** The inbound route invalidates caches conditional on `modified_at` and has no delivery table (`src/autom8_asana/api/routes/webhooks.py:360`); delivery and decision rows are deferred to later trigger PRs (`src/autom8_asana/trigger/hook_registry.py:14`).

### 5.4 Downstream DDL posture `[EXPERIENTIAL]` (ledger-sourced, dated 2026-07-08, not re-observed)

| Table (autom8y-data, MySQL schema `dtenuta`) | Constraint finding | Source |
|---|---|---|
| `account_status` | `PRIMARY KEY` plus `uq_phone_vertical_pipeline` (UNIQUE) **only; no foreign key in production**. The migration declared a foreign key that did not land because the deploy entrypoint strips `FOREIGN KEY` clauses and sets `FOREIGN_KEY_CHECKS=0` before the migration tool runs | `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:21-32` |
| `account_status` receiver | transactional snapshot-replace; the sender skips the POST when entries are empty, so a never-populated table looks healthy | same, `:34-38` |
| `chiropractors` | `guid` String(36) primary key, `office_phone` UNIQUE; 1402 rows on 2026-07-08 | `.ledge/spikes/SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md:95`; sd02 spike `:21-27` |
| `business_offers` | composite primary key `(office_phone, offer_id)` plus a unique constraint; `offer_id` String(45) as a foreign key to an Integer primary key | legacy-monolith spike `:99,211` |
| `leads` and `appointments` | `leads.phone` UNIQUE (soft), `appointments.phone` foreign key to `leads.phone`; status vocabularies are raw strings, not enum-constrained | legacy-monolith spike `:103-105` |
| MySQL semantics that follow | UNIQUE treats several NULLs as distinct; foreign-key enforcement can be off at deploy; vocabulary sync is an idempotent upsert (`ON DUPLICATE KEY UPDATE`) | `.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md:124-135` |

Consequence: with only UNIQUE enforced downstream, referential correctness of everything this repo pushes is the sender's job, which is why the sender pre-sanitizes rows (5.2).

### 5.5 NULL posture summary

| Column or field | Nullability evidence | Cite |
|---|---|---|
| `business.office_phone` | custom field on the root; 93.3% populated per a dated comment `[EXPERIENTIAL]` | `src/autom8_asana/enrollment/intent_projection.py:30-31` |
| `office_phone` on unit, offer, contact, process, asset_edit, holders, project, section | `nullable=True`, cascade-sourced, null means silent not-found | 2.7; `src/autom8_asana/dataframes/schemas/offer.py:15-22` |
| `company_id` | nullable; absent for some active offices | `src/autom8_asana/enrollment/intent_projection.py:52-66` |
| BASE columns | 8 of 13 are `nullable=False`; `date`, `due_on`, `completed_at`, `section`, `parent_gid` are nullable | `src/autom8_asana/dataframes/schemas/base.py:12-104` |
| `watermark.population_degraded` | additive; a legacy sidecar lacking the key reads as healthy | `src/autom8_asana/dataframes/storage.py:861-871` |
| substrate pointer | absence is loud: `ArtifactMissing`, `PointerCorrupt`, never `(None, None)` | `src/autom8_asana/substrate/store.py:107-128` |

## Knowledge Gaps

1. **No production or live read of any kind.** No database, DuckDB, MCP, AWS or HTTP access was used. Every schema above is repo-declared. Not verified against production: declared frame widths versus warmed parquet widths; S3 key counts per prefix (registry figures are from 2026-06-10); whether `dataframes-v2/` holds any pointer; the live `ASANA_CACHE_PROVIDER`, `REDIS_HOST` and `IDEMPOTENCY_STORE_BACKEND` values; whether the idempotency table and the hook-registry table exist; the downstream MySQL table inventory, constraints and NULL rates.
2. **Q-b (tenant-key column presence) has no source** in the repo or the ledger; it was not composed (scope cap). Q-a, Q-c, Q-d are criteria-supplied templates with no run result.
3. **The downstream authority is `autom8y-data`'s own knowledge file**, which was not read. Section 5.4 and 3.4(B) rest on dated ledger receipts (2026-07-08) and would be superseded by it.
4. **`business_id` enforcement upstream** (the platform auth middleware with `require_business_scope=True`) is unverified; this repo contains no code that filters data by that claim (2.5).
5. **`process` descriptor schema binding** (no explicit schema path) was not traced to the schema registry; its DIRECT versus CHAIN class is `[INFERRED]`.
6. **Not traced to leaf:** the automation polling state; the `mcp/**` package (the AST import walk found no storage-client imports there, but non-import persistence such as local files was not searched); response schemas of `src/autom8_asana/clients/data/_endpoints/*` beyond endpoint paths; the in-memory parent-index module under the cache policies package and the unified task-store provider (typed ancestor-fetch faults) were not re-read this pass.
7. **Floored or unread names (operator's act):** the generated Terraform namespace JSON was not re-read (its content is described only through the registry module); the repo-root credentials manifest, the secretspec file, the env directory and env file at the repo root, and the env, secret and credential audit records under the ledger and scripts directories were not opened (names only). One ledger decision file with a PII-flagged suffix was not read.
8. **The mise tool-version config at the repo root is a symlink and was not followed.**

### Corrections to the prior pass (c29f58f4 to 584c8f79)

| Prior claim | Finding at `584c8f79` | Evidence |
|---|---|---|
| `IDEMPOTENCY_STORE_BACKEND` default is `dynamodb` (construct failure falls back to no-op) | **Default is `noop`.** `dynamodb` and `memory` are opt-in; the unknown-backend fallback is also no-op | `src/autom8_asana/api/main.py:91,403-442` |
| Rate limiter storage described only as "in-memory by default" in docstrings | **Pinned** to `memory://` with an explicit `storage_uri`; settings file path disabled; verified-identity bucket keys; health probes exempt | `src/autom8_asana/api/rate_limit.py:335-358,209-267,376-390` |
| No `trigger/` package | **New**: D6 trigger package adds a DynamoDB registry schema, a write-once Secrets Manager prefix and an environment marker, all dark; zero production importers | `src/autom8_asana/trigger/*.py`; section 1.7 |
| DIRECT 18 / CHAIN 12 | **17 / 13**: `process` has no explicit schema path in its descriptor, so it is CHAIN pending a schema-resolution check | `src/autom8_asana/core/entity_registry.py:587-597` |
| Q-b, Q-e, Q-h, Q-i were composed queries marked UV-P | **Removed**: the domain scope cap forbids composing queries; only verbatim repo, ledger and criteria-supplied queries are kept | section 4 |
| Offer-schema line anchors (`:209-217`) and other line numbers | **Re-derived**; every cite in this file was re-checked at `584c8f79` | throughout |
| 16 `EntryType` members; 30 descriptors; 12 namespaces; 16 warmable; unused `CONFIG_PREFIX`; `soak-sentinel` key; `dataframes-v2/` unregistered | **Re-verified, unchanged** | 1.3, 1.4, 1.6, 1.6a |
| `ConsistentRead`, conditional writes and lease for the registry | **New in this pass** (the table did not exist at `c29f58f4`) | 5.1 |
| Pydantic `extra="ignore"` on `AccountStatusPushResponse` | **Not re-verified**; only `GidPushResponse` at `gid_push.py:98-106` was re-read | `src/autom8_asana/services/gid_push.py:98-106` |
| Claims citing `identity_supply.py` walk depth (`max_depth=10`), `cascade_view.py:112` default depth, the `HierarchyIndex`, and `lifecycle/observation.py` nullability | **Dropped**: not re-verified this pass | not cited above |
