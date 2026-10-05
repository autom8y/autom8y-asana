---
domain: db
generated_at: "2026-10-05T03:28:55Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./pyproject.toml"
  - "./docker-compose.yml"
  - "./docker-compose.override.yml"
generator: theoros
source_hash: "b996e4c52711b504b482c9ad51367187aa4db620b209e0987840f52a7f8f752b"
confidence: 0.78
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
---

# Codebase Database Schema

> Fresh full-observation pass at `origin/main` `c29f58f4` (detached worktree; all cites are relative to the worktree root; a bare `x/y.py:N` means `src/autom8_asana/x/y.py:N`). **Production oracle: NOT consulted** (no DuckDB MCP in this pass) — every claim is code-derived or corroborated from `.ledge/` receipts of stated date; anything that would need a production schema read is labelled `[UV-P: …]` with the exact query in the Canonical Production Queries appendix. Grade is therefore capped (see the metadata): this is a code-inferred knowledge reference, which the domain rubric itself says cannot exceed C-band on completeness.

## Status: No relational database layer in THIS service — but a persistent-store layer with real keys, grains and join chains

**Detection result (negative for relational).** `autom8y-asana` declares no ORM, no migrations and no SQL driver:

| Signal | Result | Evidence |
|---|---|---|
| ORM / driver imports (`sqlalchemy sqlmodel alembic duckdb pymysql aiomysql asyncpg psycopg sqlite3 aiosqlite`) in any `*.py` in the worktree | **0 files** | whole-tree `grep -rlE "^(import\|from) (…)"` → empty |
| Driver/ORM dependencies | **absent** — only `polars`, `boto3`, `pyyaml`, `openpyxl`, `phonenumbers`, optional `redis`/`hiredis` | `pyproject.toml:17,42,57-60` |
| Migration dirs / `*.sql` / `schema.prisma` / `*.db` | **0** | `find` over worktree (excl. `.git`) → empty |
| docker-compose DB service | **none** — `docker-compose.yml` runs LocalStack (`SERVICES=s3,secretsmanager`) only; `docker-compose.override.yml` *points at* an external `redis` host (`REDIS_HOST: redis`, `REDIS_DB: "2"`) and `AUTOM8Y_DATA_URL: http://data:8000` but defines no DB container | `docker-compose.yml:6-17`, `docker-compose.override.yml:28-36` |
| Terraform RDS / DynamoDB / ElastiCache / S3-bucket resources | **none in this repo** — `terraform/services/asana/` holds only alarms + the generated namespace JSON; infra for the data stores lives in the `autom8y` monorepo | `grep -rniE "aws_db_instance\|aws_rds\|dynamodb_table\|aws_elasticache\|aws_s3_bucket" terraform` → empty |

**What the pre-check misses (and the prior version understated).** The service nonetheless **reads and writes five persistent stores** and **traverses a multi-hop key chain** that ends in a MySQL schema it never connects to:

1. **S3 bucket `autom8-s3`** (default, `settings.py:426-429`) — parquet frames, JSON sidecars, versioned immutable artifacts, durable per-task copies. **Primary analytic store.**
2. **Redis** (optional extra; used in production when `REDIS_HOST` is set) — task-level cache.
3. **DynamoDB** table `autom8-idempotency-keys` — HTTP idempotency store.
4. **Local filesystem** (`~/.autom8/**`) — parquet + YAML for CLI/offline lanes.
5. **Asana itself** — the system of record for every entity; the service writes custom fields / tasks / comments back through `persistence/`.

…and it **pushes snapshots into / reads from the `autom8y-data` service** (HTTP only), whose backing store is **MySQL on RDS `nhc-db`, schema `dtenuta`** (engine family from the ledger; the "8.0" minor version is operator-memory only, not in any repo artifact) `[UV-P-1]` — corroborated by `.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md:124-133,348` (engine = MySQL, `ON DUPLICATE KEY UPDATE`, PostgreSQL dialect 0 hits) and `.ledge/spikes/SPIKE-asset-linkage-coverage-measurement-2026-07-08.md:15,114-119` (`nhc-db`, schema `dtenuta`, DuckDB `mysql_query('dtenuta_raw', …)` pushdown). **autom8y-asana never opens a connection to it.** The authoritative DDL knowledge belongs to the `autom8y-data` repo's own `.know/db.md` (cited by the SD-02 spike at `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:30-31`); this document records only the *contact surface* and the keys asana puts on the wire.

> **Engine correction relevant to any reader:** the downstream engine is **MySQL**, not Postgres — so `GET_LOCK` not `pg_advisory`, UNIQUE-key semantics treat multiple NULLs as distinct, and FK enforcement can be switched off at deploy (see Constraints).

## 1. Schema Inventory — the persistent stores, enumerated

### 1.1 S3 namespace registry (`autom8-s3`) — 12 registered namespaces

SSOT: `storage_namespace.py` — `REGISTRY` (`:520`), pinned count `REGISTRY_NAMESPACE_COUNT = 12` (`:540`), import-time `_validate_registry()` (unique names/prefixes; only two declared parent prefixes — `cache-warmer/checkpoints/` and `asana-cache`), generated TF JSON `terraform/services/asana/namespaces.gen.json` (449 lines; "DO NOT EDIT BY HAND"), alignment tests `tests/arch/test_namespace_contract.py` (t1–t5) and `tests/arch/test_namespace_gen.py`. Lifecycle enum `LIVE/FOSSIL/QUARANTINED/PHANTOM` (`:76`ff); zero PHANTOM rows (t4).

| # | Registry name (`storage_namespace.py`) | Prefix | Lifecycle | Writer | Semantic plane |
|---|---|---|---|---|---|
| 1 | `TASK_CACHE` (`:226`) | `asana-cache` → effective keyspace `asana-cache/tasks/{gid}/task.json[.gz]` (+ `stories.json`, `modified_at.json`) | **LIVE, write-durable / explicit-read** | **EXTERNAL** — the autom8 monolith (`apis/aws_api/services/s3/models/asana_cache/tasks/main.py:447-448` per `storage_namespace.py:233-244`); *not this repo* | durable per-task copy; read only via `DurableTaskCacheReader` (`cache/durable_task_cache.py:126`, `task_cache_key` `:98-106`) |
| 2 | `DATAFRAMES_V2` (`:282`) | `dataframes/` | **LIVE** | this repo — `dataframes/storage.py:347` | v2 GID-keyed project/entity frames ("coherent=561 plane", ~1,025 keys at registry authorship) |
| 3 | `CHECKPOINTS` (`:315`) | `cache-warmer/checkpoints/` | LIVE | `lambda_handlers/checkpoint.py:31` | warmer resume checkpoint (`latest.json`) |
| 4 | `CHECKPOINTS_BULK` (`:332`) | `cache-warmer/checkpoints/bulk/` | LIVE | `lambda_handlers/checkpoint.py:39` | per-lane disjoint checkpoint |
| 5 | `CHECKPOINTS_SECTION_FAST` (`:349`) | `cache-warmer/checkpoints/section-fast/` | LIVE | `lambda_handlers/checkpoint.py:39` | per-lane disjoint checkpoint |
| 6 | `E2E_TEST_DATAFRAMES` (`:367`) | `e2e-test-dataframes/` | LIVE (non-prod) | external e2e harness | test frames |
| 7 | `PROJECT_FRAMES_FOSSIL` (`:385`) | `asana-cache/project-frames/` | **FOSSIL** (last write 2025-10-02 per registry) | monolith v1 | v1 name-keyed frames; **also the live value of the overloaded `ASANA_CACHE_S3_PREFIX` in prod** (`namespaces.gen.json` `env_blocks.PROJECT_FRAMES_FOSSIL`) |
| 8 | `TASK_CACHE_LEGACY_FOSSIL` (`:412`) | `asana-cache/task-cache/` | FOSSIL | monolith (pickle) | legacy task pickle |
| 9 | `TASK_DATA_CACHE_V3_FOSSIL` (`:435`) | `asana-cache/task-data-cache-v3/` | FOSSIL | monolith | expensive-attrs v3 |
| 10 | `INSIGHTS_FRAMES_FOSSIL` (`:453`) | `asana-cache/insights-frames/` | FOSSIL | insights-export lambda (probable) | insights frames |
| 11 | `NAME_GID_MAPPINGS_FOSSIL` (`:475`) | `asana-cache/name-gid-mappings/` | FOSSIL | monolith | name→gid mappings |
| 12 | `ASANA_CACHE_DATAFRAMES_FOSSIL` (`:493`) | `asana-cache/dataframes/` | FOSSIL | monolith legacy | flat entity-gid frames (distinct from top-level `dataframes/`) |

**Declared target-vs-live drift:** `KNOWN_DRIFTS` (`:548`) — the warmer-lane roles still hold PUT/DELETE/HEAD on `asana-cache/project-frames/*` although the namespace is FOSSIL. IAM matrix: warmer role `…:role/autom8-asana-cache-warmer-lambda-role` covers 6 namespaces; monolith user `…:user/autom8` covers the 5 task/insights/name fossils (`terraform/services/asana/namespaces.gen.json`, `iam_resources`). `E2E_TEST_DATAFRAMES` has **no** IAM row.

**Unregistered S3 keyspaces the code uses (inventory gap vs the registry — NEW since prior):**

| Prefix / key | Writer / reader | Why it escapes the registry | Cite |
|---|---|---|---|
| **`dataframes-v2/{project_gid}/{entity_type}/current.json` + `…/versions/{sha256}/frame`** — substrate-v2 immutable artifacts + CAS pointer | `substrate/store.py` `S3ArtifactStore` (writer), `lambda_handlers/prov_sweep.py` (enumerator) | t3 is an AST scan for string `Constant`s that are *exactly equal* to a registry prefix (`tests/arch/test_namespace_contract.py:210-231`); `"dataframes-v2/"` (and f-string-built keys) never equal `"dataframes/"`, so the plane is neither registered nor in the TF IAM gen JSON. Bucket env `SUBSTRATE_V2_S3_BUCKET` (default `autom8-s3`). | `substrate/identity.py:68-77` (`artifact_key`), `substrate/store.py:11-14,103-104`, `lambda_handlers/prov_sweep.py:21-22,87`; absent from `terraform/services/asana/namespaces.gen.json` |
| `soak-sentinel/r7-divergence-baseline.json` | `lambda_handlers/traffic_offer_divergence_tripwire.py` (reads at `:1044`, writes at `:1078`); bucket env `TRAFFIC_OFFER_DIVERGENCE_BASELINE_BUCKET` default `autom8-s3` | literal key, not a prefix namespace | `lambda_handlers/traffic_offer_divergence_tripwire.py:317-319` |
| `dataframes/{project_gid}/cache-freshness-ttl.json` | `metrics/sla_profile.py` sidecar writer | sits *inside* the registered `dataframes/` plane (so legal) but is a hard-coded template | `metrics/sla_profile.py:86,483` |
| `dataframes` (no trailing slash) as `_prefix` default | `substrate/live.py` `S3OfferPlaneReader` reads `dataframes/{project}/offer/{dataframe.parquet,watermark.json}` | hand-pinned literal; `"dataframes"` ≠ the registry's `"dataframes/"` so t3's exact-equality scan cannot see it | `substrate/live.py:446-461` |

### 1.2 The `dataframes/` plane — object layout (per project, per entity)

`dataframes/storage.py:308-332` (`S3DataFrameStorage`, default prefix `:347`). **Two layouts coexist (dual-read, SEAM-1 / ADR-SEAM1):**

```
LEGACY (entity-agnostic; read fallback only, gated by legacy_fallback_enabled=True, :352,1010,1195)
  dataframes/{project_gid}/{dataframe.parquet | watermark.json | gid_lookup_index.json | manifest.json | sections/{section_gid}.parquet}
v2 (write target when entity_type is supplied; collision-free per entity view of the same project)
  dataframes/{project_gid}/{entity_type}/{dataframe.parquet | watermark.json | gid_lookup_index.json | manifest.json | sections/{section_gid}.parquet}
```

Key builders: `_entity_segment` `:405-412`, `_df_key` `:414`, `_watermark_key` `:418`, `_index_key` `:422`, `_section_key` `:426`, `_manifest_key` `:432`. The project GID stays the first segment so `list_projects()` is unchanged (`:392-403`). Progressive tier keys are `"{entity_type}:{project_gid}"` (`cache/dataframe/tiers/progressive.py:112-128`).

**Sidecar schemas (JSON, app-defined — no DDL):**
- `watermark.json` — `{project_gid, watermark(ISO), saved_at, [row_count, columns, entity_type, population_degraded, population_min_rate]}` (`dataframes/storage.py:840-873`); the last two are additive carry-forward flags for the stateless Lambda warm.
- `manifest.json` = `SectionManifest` (`dataframes/section_persistence.py:119-132`): `project_gid, entity_type, started_at, sections{gid→SectionInfo}, total_sections, completed_sections, version=1, schema_version`. `SectionInfo` (`:85-117`) carries `status ∈ {pending,in_progress,complete,failed}` (`:76`), `rows, written_at, watermark, gid_hash, name, last_fetched_offset, rows_fetched, chunks_checkpointed, last_verified_at`. An empty `schema_version` is "legacy manifest → force rebuild" (`:136-149`).
- `gid_lookup_index.json` = serialized `GidLookupIndex`: canonical key `pv1:{office_phone}:{vertical}` (lower-cased strings) → task gid (`services/gid_lookup.py:262-293`).

### 1.3 Frame schemas (the "tables") — 30 entity descriptors, 16 warmable

SSOT: `ENTITY_DESCRIPTORS` (`core/entity_registry.py:460`); getter `get_registry()` (`:1262`). Category census: 1 ROOT (business), 1 COMPOSITE (unit), 9 HOLDER, 18 LEAF, 1 OBSERVATION (`stage_transition`) = 30 (`core/entity_registry.py:85-92`, descriptors list). Column counts below are **static** `ColumnDef(name=…)` counts (BASE 13 + entity extras, de-duplicated against BASE) from `dataframes/schemas/*.py`; they are *declared* schema, not production frame width `[UV-P-2]`.

| Entity (descriptor) | Asana project GID (`core/project_registry.py`) | Warm prio | Declared cols / schema ver | Key columns (`key_columns`) | Cite |
|---|---|---|---|---|---|
| `business` (ROOT) | `1200653012566782` (`:23`) | 1 | 18 / 1.2.0 | `office_phone` | `core/entity_registry.py:464-490`; `dataframes/schemas/business.py:54-62` |
| `unit` (COMPOSITE) | `1201081073731555` (`:26`) | 2 | 22 / 1.5.0 | `office_phone, vertical` | `:492-517`; `schemas/unit.py:77-85` |
| `unit_holder` (HOLDER→business) | `1204433992667196` (`:27`) | 3 | 23 / 1.1.0 | `()` | `:785`ff; `schemas/unit_holder.py:147-155` |
| `offer` (LEAF) | `1143843662099250` (`:30`) | 4 | 33 / 1.6.0 | `office_phone, vertical, offer_id` | `:539-565`; `schemas/offer.py:209-217` |
| `contact` (LEAF) | `1200775689604552` (`:34`) | 5 | 25 / 1.4.0 | `office_phone, contact_phone, contact_email` | `:519-537`; `schemas/contact.py:99-107` |
| `asset_edit` (LEAF) | `1202204184560785` (`:38`) | 6 | 34 / 1.3.0 | `office_phone, vertical, asset_id, offer_id` | `:567-585`; `schemas/asset_edit.py:189-197` |
| `asset_edit_holder` (HOLDER→business) | `1203992664400125` (`:39`) | 7 | 14 / 1.2.0 | `office_phone` | `:872`ff; `schemas/asset_edit_holder.py:28-36` |
| `process_{sales,outreach,onboarding,implementation,month1,retention,reactivation,account_error,expansion}` (9 LEAF) | one pipeline project each (`core/project_registry.py:68-76`) | 10-18 | 16 / 1.0.0 (shared `PROCESS_SCHEMA`) | `office_phone, vertical` | `:606-731`; `schemas/process.py:44-52` |
| `process` (LEAF, dynamic project) | `None` (workspace discovery) | – | – | – | `:587-604` |
| `location`, `hours`, `calendar_integration` (LEAF) | `1200836133305610`, `1201614578074026`, `1209442849265632` | not warmed | no frame schema (calendar descriptor has "deliberately NO dataframe schema") | – | `:732-770` |
| `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder` (HOLDER→business); `offer_holder`, `process_holder` (HOLDER→unit) | per `project_registry.py:35,48,51,54` (`location_holder`, `process_holder` have none) | not warmed | – | – | `:771-925` |
| `project`, `section` (LEAF, `body_parameterized=True`) | per-request (`project_gid` in query body) | not warmed | 16 / 1.1.0 each (3 extras: `status`, `office_phone`, `vertical`) | – | `:964-1050`; `schemas/project.py:46-54` |
| `stage_transition` (OBSERVATION, virtual) | none | – | local parquet, not S3 (§1.5) | – | `:942-960` |

All frame schemas inherit `BASE_SCHEMA` (13 cols: `gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags, parent_gid`; `dataframes/schemas/base.py:13-111`, version 1.1.0 — `parent_gid` was added "for hierarchy reconstruction on resume"). Column `source` grammar: `gid`/Asana attr, `cf:<Custom Field Name>` (own custom field), `cascade:<Field Name>` (ancestor-derived), or `None` (derived in extractor). Declared cascade-sourced column counts: offer 15, unit 2, contact 2, asset_edit 2, process 2, project 2, section 2, asset_edit_holder 1, business 0, unit_holder 0 (`grep -c 'source="cascade:'` per schema file).

**Freshness governance on every warmable entity:** `freshness_sla_seconds=3600` for business/unit/contact/offer/asset_edit/process (`core/entity_registry.py:468,497,524,544,572,592`); `default_ttl_seconds` differs (business 3600, unit 900, contact 900, offer 180, asset_edit 300, process 60) and is only the SLA *fallback* post-C17 (`:131-138` docstring).

### 1.4 Redis keyspace (task-level cache; schema-free)

Provider selection: `ASANA_CACHE_PROVIDER ∈ {memory,redis,tiered,none}` explicit, else auto-detect — production + `REDIS_HOST` → Redis; otherwise in-memory (`cache/integration/factory.py:80-185`). `TieredCacheProvider` is now an **honest Redis-only passthrough** (S3 cold tier retired; `cache/providers/tiered.py:1-31`). Redis is installed via the `redis` extra (`pyproject.toml:57-60`); a "redis package not installed" degraded mode has its own alarm (`terraform/services/asana/warmer_cache_degraded_alarm.tf:5-20`).

| Key | Type | Content | Cite |
|---|---|---|---|
| `asana:tasks:{gid}:{entry_type}` | HASH (versioned path) / JSON string (simple path) | one `CacheEntry` per (task gid, `EntryType`) | `cache/backends/redis.py:98,322-335` |
| `asana:struc:{key}` | HASH | `EntryType.DATAFRAME` entries ("struc" data; key already embeds project gid) | `cache/backends/redis.py:99,331-334` |
| `asana:tasks:{gid}:_meta` | HASH `entry_type → version string` | per-task version map; expires with the entry TTL | `cache/backends/redis.py:337-346,536-544` |
| `asana:config:*` | – | prefix constant `CONFIG_PREFIX` declared; no other reference in `src/` (`grep -rn CONFIG_PREFIX src` → only `redis.py:100`) — dead constant | `cache/backends/redis.py:100` |

`EntryType` enum (16 members: task, subtasks, dependencies, dependents, stories, attachments, dataframe, project, section, user, custom_field, detection, project_sections, gid_enumeration, insights, derived_timeline) at `cache/models/entry.py:20-52`; default entry TTL 300 s (`:105`). The S3 `CacheBackendBase` sibling uses `{prefix}/tasks/{gid}/{entry_type}.json[.gz]`, `{prefix}/dataframe/{key}.json`, `{prefix}/simple/{key}.json` (`cache/backends/s3.py:258-282`) — **but no live factory path constructs it as a read tier** (mask #1 retired; `cache/providers/tiered.py:5-18`), so that keyspace is *code-present, namespace-orphaned* `[UV-P-3]`.

The insights client also caches `insights:{factory}:pv1:{phone}:{vertical}` entries through whichever `CacheProvider` is configured (`clients/data/_cache.py:30-42`; `EntryType.INSIGHTS` TTL 300 s default `cache/models/entry.py:51`).

### 1.5 DynamoDB, local filesystem, and secrets

| Store | Shape | Cite |
|---|---|---|
| **DynamoDB `autom8-idempotency-keys`** (region `us-east-1`; envs `IDEMPOTENCY_TABLE_NAME`, `IDEMPOTENCY_TABLE_REGION`, `IDEMPOTENCY_STORE_BACKEND` default `dynamodb`; construct-failure → `NoopIdempotencyStore`) | `pk = "{service_name}#{idempotency_key}"`, `sk = "{METHOD}#{path_template}"`, `ttl` epoch seconds (DynamoDB TTL auto-expiry, default 86400 s), response body base64 | `api/middleware/idempotency.py:92,242-253,625-630`; `api/main.py:393-440` |
| **Local parquet** `~/.autom8/stage_transitions/{entity_type}.parquet` — `StageTransitionStore` (**NOT S3**; the prior version mis-described it as an S3 path) | 11 cols: `entity_gid, entity_type, business_gid, from_stage, to_stage, pipeline_stage_num(Int64), transition_type, entered_at, exited_at (Datetime us UTC), automation_result_id, duration_ms` | `lifecycle/observation_store.py:5,24-37,58-60,75-80` |
| **Local parquet** `~/.autom8/timelines/{project_gid}.parquet` — `TimelineStore` (derived section timelines) | one denormalized file per project | `query/timeline_provider.py:31,48-50,105-106` |
| **Local YAML** `~/.autom8/queries/{name}.yaml`, `./queries/*.yaml` (4 saved queries), `config/lifecycle_stages.yaml`, `config/rules/conversation-audit.yaml` | saved query templates / pipeline DAG config | `query/saved.py:115-158`; `queries/*.yaml`; `config/lifecycle_stages.yaml:1-30` |
| **Secrets Manager** (credential reads, not data) | – | `_defaults/auth.py` (`boto3.client("secretsmanager")`) |
| **SQS** (event publish transport; no schema) | envelope to queue URL | `automation/events/transport.py:73-99` |

### 1.6 Cross-service tables this service puts keys on (owned by other repos)

| Surface (HTTP, never SQL) | Direction | Wire grain / key | Downstream table (per ledger, `[UV-P]`) | Cite |
|---|---|---|---|---|
| `POST /api/v1/gid-mappings/sync` | asana → data | `{project_gid, mappings[(phone,vertical)→task_gid], source_timestamp, entry_count}` | gid-mapping store | `services/gid_push.py:770-795` |
| `POST /api/v1/account-status/sync` | asana → data (snapshot-**replace**) | entries `{phone, vertical, pipeline_type, account_activity, pipeline_section, stage_entered_at}`; grain `(phone, vertical, pipeline_type)` | `account_status` (PK + `uq_phone_vertical_pipeline` UNIQUE; **no FK in prod**, 2026-07-08) | `services/gid_push.py:446-554` region, `:975-1050`, `:1156`; spike `…SD02….md:21-34` |
| `POST /api/v1/vocabularies/sync` | asana → data | enum option sets keyed by field | vocabulary tables (MySQL, idempotent upsert) | `services/gid_push.py:1467-1572` |
| `POST /api/v1/scheduling-stratum/sync` | asana → data (default-dark) | `{guid, stratum, custom_ghl_id, ghl_calendar_id, resolved_at[, served_calendar_id]}`, source `"asana"` | scheduling-stratum table (data PR #218) | `services/scheduling_stratum_push.py:65,116-141,242` |
| `POST /api/v1/data-service/insights` | asana → data (read) | `{frame_type, phone_vertical_pairs[{phone, vertical}], period, …}` | insights frames over ads/leads/appointments | `clients/data/_endpoints/insights.py:182-205` |
| `GET /api/v1/appointments`, `GET /api/v1/leads` | read | query param `office_phone` (+`days`, `limit`) | `appointments`, `leads` | `clients/data/_endpoints/simple.py:143-148,248-253` |
| `GET /api/v1/messages/export` | read | conversation export | messages | `clients/data/_endpoints/export.py:158-207` |
| `POST /api/v1/insights/operator/execute-batch` | read, operator-minted token | batch over operator's owned office set `O` (server-internal) | insights | `clients/data/_endpoints/operator.py:47` |
| `POST /api/v1/insights/reconciliation/execute` | read | reconciliation insights | – | `clients/data/_endpoints/reconciliation.py:156` |
| `POST …/tokens/exchange-business` (auth service) | asana → auth | `{external_business_id, requested_scopes}` → single-tenant JWT | auth org/business tables | `auth/business_token.py:182-210` |
| EBI DynamoDB `forwarding\|verified` keyspace (read as the *first* operand of a tripwire; asana supplies the stage-of-record count) | cross-source | – | `ebi-forwarding-idempotency` | `services/forwarding_stage_census.py:9-13` |

### 1.7 Inventory snapshot (as of `c29f58f4`)

12 registered S3 namespaces (6 LIVE incl. 1 non-prod, 6 FOSSIL) + 3 unregistered keyspaces/templates; 30 entity descriptors / 16 warmable → 16 distinct `dataframes/{project}/{entity}/` frame families (+ the `dataframes-v2/` substrate store, today pinned to exactly the offer artifact, `lambda_handlers/prov_sweep.py:29-31`); 1 Redis keyspace family (3 live key shapes); 1 DynamoDB table; 2 local parquet stores; 0 relational tables in-repo. **BASE TABLE count in the downstream `dtenuta` schema: not observed** `[UV-P-1]` (Q-a).

## 2. Tenant Resolution Model

### 2.1 What "tenant" is, and the three keys that name it

There is **no `tenant_id` column, no schema-per-tenant, no row-level-security** anywhere in this repo. A tenant is a **Business** (one clinic/office) and it is addressed by three different keys at three different altitudes, which are **not interchangeable**:

| Key | Where it lives | Role | Cite |
|---|---|---|---|
| **Business task GID** (Asana, decimal string `^[0-9]{10,20}$`-class) | `business.gid`; `parent_gid` on every child frame row | **Identity.** GID-exact, never a join, never a display string | `resolution/gfr/engine.py:1-35` (INVARIANT GFR-IDENTITY-1); `models/business/identity_supply.py:47-52` (W-7 STRICT) |
| **`office_phone`** (E.164 text; Asana custom field "Office Phone", `PhoneTextField(cascading=True)`) | own field on Business; **cascaded down** to Unit/Offer/Process/Contact (and asset_edit/holders by schema) | **Operational join key & scheduling-gate key**; with `vertical` forms the PhoneVerticalPair the data plane filters on | `models/business/business.py:261-272,305-309`; `core/entity_registry.py:486`; `models/contracts/phone_vertical.py:1-45` |
| **`company_id`** (custom field "Company ID", `TextField`) == downstream **`chiropractors.guid`** | own field on Business; `target_types=None` ⇒ cascades to *all* descendants | **Cross-plane identity** → `normalize_chiropractor_guid` → `ebid` → single-tenant JWT | `models/business/business.py:263,311-315`; `automation/workflows/leads_ebid.py:1-17,62`; `.ledge/decisions/ADR-grain-bridge-leads-consumer-2026-06-26.md:59-86` |

The tenant-root entity is therefore **`business`** (`EntityCategory.ROOT`, `core/entity_registry.py:464-490`, project `1200653012566782`). It is a **multi-tenant project**: every clinic is a row in one frame (`resolution/gfr/engine.py:73-75`). Storage partitions by *project/entity* (`dataframes/{project_gid}/{entity_type}/`), **not by tenant** — tenant isolation is a **query-time predicate**, never a storage boundary.

### 2.2 DIRECT / CHAIN / GLOBAL classification (all 30 descriptors)

| Class | Count | Entities | Basis |
|---|---|---|---|
| **DIRECT** (frame schema carries `office_phone`) | **18** | `business` (own cf), `unit`, `offer`, `contact`, `asset_edit`, `asset_edit_holder`, `process` + 9 `process_*`, `project`, `section` (all `cascade:Office Phone`) | `dataframes/schemas/{business:24-27, unit:54-57, offer:19-22, contact:77-80, asset_edit:80-83, asset_edit_holder:19-22, process:18-21, project:31, section:34}.py` |
| **CHAIN** (no `office_phone` column; reach Business via `parent_gid` / holder hierarchy) | **12** | `unit_holder` (schema has 0 cascade cols; joins via `unit_holder.parent_gid == business.gid`), `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder`, `offer_holder`, `process_holder`, `location`, `hours`, `calendar_integration`, `stage_transition` (carries `business_gid`, nullable) | `schemas/unit_holder.py:52-57`; `enrollment/intent_projection.py:41-42`; `core/entity_registry.py:771-925`; `lifecycle/observation.py:38,51` |
| **GLOBAL** (declared tenant-free) | **0 declared** | – — `project`/`section` are `body_parameterized` (project GID arrives per request) but still carry `office_phone`/`vertical` cascade columns; no descriptor is declared GLOBAL | `core/entity_registry.py:964-1050` |

**Ambiguity flagged:** the `asset_edit` descriptor's `aliases=("process",)` (`core/entity_registry.py:579`) collides with the separate `process` descriptor name — an alias-resolution ambiguity at the registry level, not a tenant-key ambiguity.

### 2.3 Hierarchy that carries the chain (Asana parent graph)

```
Business (ROOT)                      project 1200653012566782
 ├─ UnitHolder   (HOLDER→business)   project 1204433992667196   (cf: custom_cal_status + 9 posture/provider fields)
 │   └─ Unit     (COMPOSITE)         project 1201081073731555
 │       ├─ OfferHolder (HOLDER→unit)   project 1210679066066870
 │       │   └─ Offer (LEAF)             project 1143843662099250
 │       └─ ProcessHolder (HOLDER→unit) no project
 │           └─ Process / process_* (LEAF, pipeline projects)
 ├─ ContactHolder → Contact (LEAF)
 ├─ AssetEditHolder → AssetEdit (LEAF)
 ├─ LocationHolder → Location; DnaHolder; ReconciliationHolder; VideographyHolder
```
(`core/entity_registry.py` `parent_entity`/`holder_for` fields at `:771-925`; model classes `models/business/{business,unit,offer,contact,asset_edit}.py`.) Offer is **4 hops** below Business (Offer→OfferHolder→Unit→UnitHolder→Business); the cascade walker's default `max_depth=5` (`dataframes/views/cascade_view.py:112`) leaves exactly one hop of slack, while the identity-supply walk uses `max_depth=10` (`models/business/identity_supply.py:637,706`). The in-memory `HierarchyIndex` (wrapping `autom8y_cache.HierarchyTracker`, extractors `task.gid` / `task.parent.gid`) holds the parent graph (`cache/policies/hierarchy.py:57-260`).

### 2.4 Cascade (denormalized tenant-key propagation)

Tenant keys are **denormalized down the tree** two ways: (1) **read-time** — frame columns with `source="cascade:<Name>"` are resolved by `CascadeViewPlugin` walking `UnifiedTaskStore.get_parent_chain_async` (`dataframes/views/cascade_view.py:1-60,184-234`); (2) **write-time** — `persistence/cascade.py` `CascadeOperation` batch-stamps fields onto descendants in Asana itself (`persistence/cascade.py:1-30`; `models/business/business.py:295-338`). Declared cascades:

| Source | Field | `target_types` | `allow_override` | Cite |
|---|---|---|---|---|
| Business | Office Phone | Unit, Offer, Process, Contact | False | `models/business/business.py:305-309` |
| Business | Company ID | `None` (all descendants) | False | `:311-315` |
| Business | Business Name (`source_field="name"`) | Unit, Offer | False | `:317-322` |
| Business | Primary Contact Phone | Unit, Offer, Process | False | `:324-328` |
| Unit | Platforms | Offer | **True** (only opt-in) | `models/business/unit.py:166-170` |
| Unit | Vertical | Offer, Process | False | `:172-176` |
| Unit | Booking Type / MRR / Weekly Ad Spend | Offer | False | `models/business/unit.py:178-204` |
| UnitHolder | Custom Cal Status + 8 CASCADE_PRIORITY provider fields | all descendants | False | `models/business/unit.py:476-503`; `normalizer/scheduling_stratum.py:71` |

**Vertical has two different sources:** `unit.vertical` is `cf:Vertical` ("vertical waterfalls down, no cascade", `schemas/unit.py:61-65`) while `offer.vertical`, `contact.vertical`, `process.vertical`, `asset_edit.vertical` are `cascade:Vertical` (`schemas/offer.py:28-31`, `contact.py:84-87`, `process.py:25-28`, `asset_edit.py:71-74`) — the join key `(office_phone, vertical)` is thus sourced differently on its two sides.

### 2.5 Resolver flow — inbound claim → tenant key → filter injection point

| Lane | Inbound | Resolution | Filter / injection point | Cite |
|---|---|---|---|---|
| **PAT routes** (`/api/v1/{tasks,projects,sections,workspaces,dataframes,offers,exports,tags}/*`) | Asana PAT in request; JWT-excluded | tenant = whatever the PAT can see; project GID in path/body | none at app layer; Asana permissions are the isolation | `api/main.py:465-485` |
| **S2S routes** (`s2s_router`: query, resolver, receipts, identity-supply, forwarding-stage census, matching…) | JWT with `ServiceClaims` (`sub`, `permissions`; `scope` for logging only) | caller supplies `project_gid`/entity/criteria in the body; **`require_business_scope=True`** is set on `JWTAuthConfig`, but **no `src/` code consumes the `business_id` claim as a query filter** (grep of `api auth query services` finds only the config line and the per-business token mint) | request-body predicates in `query/engine.py`; multi-tenant frame is filtered by `where`/`classification` | `api/main.py:475-478`; `api/routes/internal.py:33-130`; `[UV-P-5]` whether the platform middleware enforces `business_id` upstream |
| **GFR** (`resolve_async(gid, fields)`) | any Asana gid (offer/unit/business) | **entry:** the *only* Asana read — hydrate, detect type, walk parents to Business gid; **identity read:** `RowsRequest where gid == business_gid`, `join=None`; **post-guard:** `assert_rows_tenant_identity` raises if any returned row's `gid != business_gid` | Vector-A cross-tenant guard (fail-closed, missing `gid` is a violation) | `resolution/gfr/engine.py:1-35,60-77,144`; `resolution/gfr/guard.py:183-233` |
| **Identity-supply** (`GET /v1/identity-supply/{offer_gid}`) | offer gid, digits-only `^[0-9]{1,64}$`, scope `query:read` | upward walk to Business candidates; **publishes identity from Tier 1 (project membership) only**; >1 candidate ⇒ SET with `match_count`, no value ("SET, never PICK") | allow-list on tier, not a confidence threshold | `api/routes/identity_supply.py:94-111`; `models/business/identity_supply.py:94-137,354` |
| **Leads / per-business data read** (grain-bridge) | Offer gid | Offer→Business walk → `company_id` → `compute_ebid` (`normalize_chiropractor_guid`, 3-state: absent/null/ok) → `POST /tokens/exchange-business` → **single-tenant JWT** → `PerBusinessTokenProvider` → data `GET /api/v1/leads?office_phone=…` | **served tenant = JWT `business_id`, which DOMINATES the `office_phone` query param (anti-IDOR)** | `automation/workflows/leads_ebid.py:62-95`; `auth/business_token.py:182-250`; `auth/per_business_provider.py:1-24` |
| **Scheduling-gate bridge** | three S3 frames (unit_holder, business, offer) | INTENT×IDENTITY joined on `unit_holder.parent_gid == business.gid`; ×ROSTER as a **set intersection on `office_phone` (strip-only)** | `business.office_phone` is the write key; `offer.office_phone` is roster-join only | `enrollment/intent_projection.py:14-80,175-188` |

### 2.6 Phone-key normalization is NOT uniform (a standing join hazard)

| Site | Normalization | Cite |
|---|---|---|
| Frame join `execute_join` | exact string equality (no trim/case/E.164) | `query/join.py:131-185` |
| `DynamicIndexKey` / `GidLookupIndex` | `str.lower()` on string values; canonical `idx1:`/`pv1:` prefixes | `services/dynamic_index.py:51-92,236-241`; `services/gid_lookup.py:285-293` |
| Enrollment bridge | **strip-only** by design ("do NOT introduce E.164 canonicalization … would silently merge distinct offices") | `enrollment/intent_projection.py:84-100,517-529` |
| Account-status push | E.164 regex `E164_PHONE_PATTERN` (shared with the receiver's `OfficePhoneField`); invalid ⇒ row skipped | `services/gid_push.py:1015-1045` |
| `PhoneVerticalPair` | owned by `autom8y_core.models.data_service` (validation lives in the SDK) | `models/contracts/phone_vertical.py:1-8` |

### 2.7 NULL posture of the tenant key

`office_phone` is **nullable by construction** on every DIRECT entity except Business-own: cascade-sourced, so a failed ancestor walk yields null and the schemas carry the comment "**null cascade = silent NOT_FOUND (FIND-005)**" (`schemas/unit.py:52`; same on offer/contact/process/asset_edit/asset_edit_holder). Guardrails: `CASCADE_NULL_WARN_THRESHOLD=0.05`, `CASCADE_NULL_ERROR_THRESHOLD=0.20` (calibrated to "SCAR-005's 30% production incident"), and a post-build re-resolution pass (`dataframes/builders/cascade_validator.py:40-41,420-422`). The ERROR threshold's slack is documented: on the observed 8,846-row contact frame it tolerates 1,769 null joinable rows vs a projected true fault population of ~273 (`:30-36`).

Ledger-sourced observations (dated; NOT production reads by this pass; `[UV-P-4]`):
- Business tier `office_phone`: "2400/2572 = 93.3%" (`enrollment/intent_projection.py:30-32`; TDD 2026-08-05) — read as the non-null share on Business rows.
- `unit_holder.parent_gid == business.gid`: 2082/2082 = 100.0% (`:41-42`).
- Offer frame `custom_cal_status`: 2/4191 = 0.05% populated on a *fresh* frame (pre-1.6.0 mis-sourcing; fixed by sourcing `cascade:` off UnitHolder) (`:25-27`; `schemas/offer.py:209-217`).
- Active offices whose Business ancestor lacks `Company ID` exist (CARD WS-B/3): the guid-keyed producer cannot see them while a phone-keyed writer can (`enrollment/intent_projection.py:52-66`); phones mapping to >1 distinct guid are counted `guid_ambiguous_phones` (`:62`).
- Reserved canary tenant: `CANARY_SENTINEL_PHONE = "+15550000000"`, excluded from account-status and the R7 numerator (`lambda_handlers/traffic_offer_divergence_tripwire.py:271`; `services/gid_push.py` `extract_status_from_dataframe`).

## 3. FK Chain Catalog (join / parent chains the code actually traverses)

There are **no declared foreign keys in this repo**. Referential structure is carried by (a) the Asana **parent graph** (`parent_gid` / `task.parent.gid`), (b) **denormalized cascade columns** (`office_phone`, `vertical`, `company_id`), (c) **registry-declared join keys** (`EntityDescriptor.join_keys`), and (d) a **cross-service key chain** ending in MySQL. Referential integrity is therefore *application-asserted*, and every join below is a *left join on a text key with no engine to refuse an orphan*.

### 3.1 Parent-chain to the tenant root (Business), per entity

| Entity | Chain (child → … → Business) | Depth | Pseudo-SQL skeleton (frame-level) | Notes |
|---|---|---|---|---|
| `unit_holder` | `parent_gid → business.gid` | **1** | `unit_holder JOIN business ON unit_holder.parent_gid = business.gid` | measured 2082/2082 = 100% in the TDD (`enrollment/intent_projection.py:41-42`); the "intact office spine" |
| `contact_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `videography_holder`, `asset_edit_holder` | `parent_gid → business.gid` | 1 | same | `parent_entity="business"` (`core/entity_registry.py:771-905`) |
| `contact` | Contact → ContactHolder → Business | 2 | `contact JOIN contact_holder ON … JOIN business …` or **by key**: `contact.office_phone = business.office_phone` | registry `join_keys=(("business","office_phone"),)` (`:519-537`) |
| `asset_edit` | AssetEdit → AssetEditHolder → Business | 2 | by key: `office_phone` (no `join_keys` declared — chain is cascade-only) | `core/entity_registry.py:567-585` |
| `unit` | Unit → UnitHolder → Business | 2 | by key: `unit.office_phone = business.office_phone` | `join_keys` business/offer on `office_phone` (`:492-517`) |
| `offer_holder`, `process_holder` | → Unit → UnitHolder → Business | 3 | – | `parent_entity="unit"` (`:910,924`) |
| **`offer`** | Offer → OfferHolder → Unit → UnitHolder → Business | **4** (>3 ⇒ design-review candidate) | by key: `offer.office_phone = unit.office_phone` (**phone only, not vertical**) and `= business.office_phone` | `join_keys` unit/business on `office_phone` (`:539-565`); mitigated by cascade denormalization + cascade `max_depth=5` |
| **`process` / `process_*`** | Process → ProcessHolder → Unit → UnitHolder → Business | **4** | by key `(office_phone, vertical)` (`key_columns`) | pipeline projects are separate Asana projects: the same Process task can be a member of a pipeline project while its *ancestry* lives under the Unit tree |
| `location`, `hours`, `calendar_integration` | → LocationHolder → Business (location); `hours` parent not verified | 2+ | – | no frame schema (`:732-770`) `[UV-P-6]` |
| `stage_transition` | `business_gid` (nullable) | 1 (denormalized) | `stage_transition.business_gid = business.gid` | `lifecycle/observation.py:38,51`; local parquet only |

The in-process `ENTITY_RELATIONSHIPS` list is **auto-derived** from `join_keys` (`query/hierarchy.py:64-101`): business→{unit, contact, offer} `office_phone`; unit→{business, offer}; offer→{unit, business}; contact→business. Cardinality labels come from category pairs only (`_derive_cardinality`, `query/hierarchy.py:42-61`: root/composite→leaf = `1:N`, leaf→root/composite = `N:1`, else `"unknown"` — so `business↔unit` is **`unknown`**). `find_relationship` returns the first match in either direction (`:104-125`). Saved-query YAMLs exercise two: `queries/offers_with_business.yaml` (offer⟕business on default `office_phone`, selecting `booking_type`) and `queries/offers_with_spend.yaml` (offer ⟕ `data-service` spend factory `T30`, `"on": office_phone`).

### 3.2 Multi-source reachability and the canonical choice

| Entity pair | Two ways to reach | Canonical (as coded) | Hazard |
|---|---|---|---|
| Offer → Business | (1) **parent chain by GID** (4 hops); (2) **`office_phone` equality** | **Identity: parent chain, GID-exact** (GFR `join=None`, INVARIANT I2) — never `office_phone` (`resolution/gfr/engine.py:11-17`). **Roster/aggregate: `office_phone`.** | `office_phone` is not unique per Business tier consumer: a phone can map to >1 guid (`guid_ambiguous_phones`, `enrollment/intent_projection.py:62`); a Business with no phone is invisible to phone joins |
| Offer → Unit | parent chain; `office_phone` | parent chain for hierarchy; `office_phone` join for frames | **`unit` has one row per (phone, vertical)** (`key_columns=("office_phone","vertical")`), so a phone-only join fans out and `execute_join` **silently de-duplicates `keep="first"`** (`query/join.py:157`) — the offer inherits an arbitrary vertical's unit columns. The ratification states the same fact: "one phone holds many rows. Nobody holds the join" (`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md:64-65`) |
| Business ↔ guid | `company_id` custom field on Business; downstream `chiropractors.guid`; `office_phone` UNIQUE on `chiropractors` | `company_id` (normalized → ebid) | the **GUID ↔ `office_phone` join does not exist as a standalone store** (`…ADR-ws-join-office-naming-path-2026-09-08.md:65-66`) — the only place both live on one row is the Asana **Business frame row** (`schemas/business.py`: `company_id` + `office_phone`) |
| Unit-level `vertical` | `cf:Vertical` on Unit vs `cascade:Vertical` on Offer/Contact/Process/AssetEdit | – (not reconciled) | two sourcing mechanisms for one join-key member (§2.4) |

### 3.3 Frame-key types that do not agree

- `offer.offer_id` is **`Utf8`** (`schemas/offer.py:42-45`, `cf:Offer ID`) while `asset_edit.offer_id` is **`Int64`** (`schemas/asset_edit.py:127-130`, `cf:Offer ID`) — a cross-frame equality on `offer_id` is a dtype mismatch in polars unless cast. The downstream table carries a *third* representation (`business_offers.offer_id` `String(45)` as FK to an Integer PK, MySQL coerces — `.ledge/spikes/SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md` D3) `[UV-P-7]`.
- `asset_edit.asset_id` is `Utf8` holding a list rendered as text (`"[1,2,3]"` or `"1,2,3"`, read by `ast.literal_eval` + comma-split fallback) per the same spike (D11); the schema column is `schemas/asset_edit.py:106-109`.
- `GidLookupIndex.from_dataframe` is **last-write-wins** on duplicate `(phone, vertical)` keys (`services/gid_lookup.py:285-293`), `DynamicIndex` is **multi-valued** (`defaultdict(list)`, `services/dynamic_index.py:224-247`), and the status push is **first-wins** (`services/gid_push.py:1038-1041`). Three different duplicate policies on the same grain.

### 3.4 Cross-service key chain (asana → data → MySQL)

```
Asana Offer gid
  └─ upward walk (identity_supply, max_depth=10)  ─→ Business gid  (Tier-1 project membership only publishes identity)
       ├─ Business.company_id ── normalize_chiropractor_guid ──→ ebid ──POST /tokens/exchange-business──→ single-tenant JWT {business_id}
       │      └─ downstream: chiropractors.guid (String(36) PK) ── office_phone (UNIQUE)            [UV-P-1, ledger 2026-07-08]
       └─ Business.office_phone ── (phone, vertical) ──→ account_status / gid-mappings / insights / leads / appointments
              └─ downstream chain (legacy-monolith decomposition D6/D12, [UV-P-8]):
                   leads.office_phone → chiropractors ; appointments.phone → leads.phone (soft UNIQUE) ;
                   assets.chiropractor_id → chiropractors.guid ; assets.offer_id → offers.offer_id → offers.category → verticals.key ;
                   asset_verticals(asset_id, vertical_id) ; ads_insights(ad_id, date, platform) → ads → ad_creatives(creative_id) → assets_ad_creatives → assets
```
Walk implementation: `models/business/identity_supply.py:633-724` (`walk_business_candidates_async`, `supply_identity_evidence_async`); the walk's `observed_at` is **`datetime.now(UTC)` at call time** (`:722`) — i.e. a **fetch clock**, not a source (Asana `modified_at`) clock, so any downstream "disagreement" check across two writers that both stamp their own fetch time is blind by construction `[corroborates operator memory; UV-P-9 for the fold]`. Evidence grains: `G-0, G-1, G-2, G-2a, G-3`; families published by this seat: `asana_business` (G-1), `business_display_name` (G-1), `offer` (G-3) (`models/business/identity_supply.py:1-18,141-250`).

### 3.5 Orphans

No entity is both un-keyed and un-chained. Residual orphan *risks*: (a) `stage_transition.business_gid` may be `None` ("None if not applicable", `lifecycle/observation.py:38`); (b) `location_holder` and `process_holder` have `primary_project_gid=None` so they have no frame to join; (c) Business rows with null `office_phone` (~6.7% per the dated ledger figure) drop out of every phone-keyed join silently; (d) ancestor fetch failures are *typed permanent faults* (`ForbiddenError/GoneError/NotFoundError` on a parent) rather than silent nulls (`cache/providers/unified.py:36-45`), but the resulting null cascade value is still "silent NOT_FOUND" at lookup.

## 4. Constraints and Null Posture

### 4.1 Engine-level constraints present in the stores THIS repo operates

| Store | Engine-enforced invariant | Cite |
|---|---|---|
| S3 `dataframes-v2/` | **write-once** staged versions: `PutObject … IfNoneMatch="*"` (412 ⇒ already staged, idempotent); **true CAS pointer**: `If-Match` ETag conditional PUT, `If-None-Match:*` to create; blank `if_match` is *rejected in code* because it would degrade to unconditional overwrite | `substrate/store.py:336-350,351-399` |
| DynamoDB idempotency | `ConditionExpression="attribute_not_exists(pk)"` claim (single winner); DynamoDB TTL on `ttl` | `api/middleware/idempotency.py:313,335-338` |
| Redis | per-key `EXPIRE`/`SETEX` TTL only; no constraints | `cache/backends/redis.py:451-454,540-544` |
| S3 `dataframes/`, `cache-warmer/checkpoints/` | **none** (last-writer-wins `PutObject`; atomicity of parquet + watermark is "best-effort") | `dataframes/storage.py:95-100` ("Persist DataFrame and watermark atomically (best-effort)") |

### 4.2 Application-only invariants (not mirrored in any DDL — there is no DDL)

| Invariant | Where asserted | Cite |
|---|---|---|
| Frozen, slotted `EntityDescriptor`; registry never mutated after load | dataclass | `core/entity_registry.py:95-101` |
| `ArtifactId`: digits-only `project_gid`, servable `entity_type` (derived from warmable descriptors) — refused **at construction** | `__post_init__` [H4] | `substrate/identity.py:34-66,99-107` |
| `FreshnessProof` tz-aware (`[H2]` reject naive), PROVABLE iff age ≤ SLA and digest matches | `__post_init__` / `is_provable` | `substrate/freshness.py:62-117` |
| Asana GID shape: `^\d{10,20}$` (reconciliation), `^[0-9]{1,64}$` (identity-supply, unconditional), `^\d{1,64}$` **only when `AUTOM8Y_ENV` ∉ {test, local}** (`GidStr`, conditional) | regex | `reconciliation/section_registry.py:37`; `api/routes/identity_supply.py:94-111`; `api/models.py:46-54` |
| Section manifest compatible iff `schema_version` equals the current schema's version; empty ⇒ legacy ⇒ rebuild | method | `dataframes/section_persistence.py:136-149`; `dataframes/builders/progressive.py:298-326` |
| `honest_contract_complete` ⇔ zero FAILED sections in the manifest | function | `dataframes/section_persistence.py:324-343` |
| Per-row E.164 + `(phone, vertical, pipeline_type)` dup-grain guards **mirroring a remote UNIQUE** (`uq_phone_vertical_pipeline`) | `_sanitize_status_entries` | `services/gid_push.py:975-1045` |
| Cascade null-rate thresholds 5%/20% | validator | `dataframes/builders/cascade_validator.py:40-41` |
| `Evidence` has **no** `confidence/refuted/shared` attributes — the seat boundary is enforced by type | dataclass | `models/business/identity_supply.py:56-70,251` |
| Pydantic `extra="ignore"` on response envelopes (`GidPushResponse`, `AccountStatusPushResponse`) — **a changed server contract is silently tolerated**; HTTP 200 does not prove persistence (see scar `SCAR-CFWRITE-001` in `.know/scar-tissue.md`) | model_config | `services/gid_push.py:98-106,823-830` |

### 4.3 Downstream DDL posture (ledger-sourced; **stale-dated 2026-07-08**; `[UV-P-1]`)

| Table (autom8y-data, MySQL `dtenuta`) | Constraint finding | Cite |
|---|---|---|
| `account_status` | `PRIMARY KEY` + `uq_phone_vertical_pipeline` (UNIQUE) **only — NO FOREIGN KEY in prod**; migration 013 *declared* an FK (`autom8y-data/alembic/versions/013_add_account_status_table.py:67-72`) that did not land because "deploy entrypoint strips `FOREIGN KEY` clauses and sets `FOREIGN_KEY_CHECKS=0` before Alembic runs" | `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:21-34` |
| `account_status` receiver | transactional snapshot-**replace**; entries `extra="forbid"` | same spike §1 H2/H4 |
| `chiropractors` | `guid` String(36) PK, `office_phone` UNIQUE (operable business key); 1402 rows on 2026-07-08 | `…SPIKE-legacy-monolith-truth-decomposition-2026-07-08.md` D1; sd02 spike `:21-34` |
| `business_offers` | composite PK `(office_phone, offer_id)` + UniqueConstraint; `offer_id String(45)` FK → Integer PK (MySQL coerces) | same, D3 |
| `offers.category` ↔ `verticals.key` | collation mismatch (`utf8mb4_unicode_ci` vs `utf8mb4_0900_ai_ci`) forces explicit `collate()` in joins (MySQL error 1267) | same, D12 |
| `leads` / `appointments` | `leads.phone` UNIQUE (soft); `appointments.phone` FK → `leads.phone`; status vocabularies are raw `String(N)` — **not enum-constrained** | same, D5/D6 |
| vocabulary sync | MySQL idempotent upsert (`ON DUPLICATE KEY UPDATE`); named locks are connection-scoped on MySQL, so the design rejected `GET_LOCK` | `.ledge/decisions/ADR-dyn-enum-contract-shared-contract.md:124-186` |

> **MySQL consequence for this service's pushes:** with `FOREIGN_KEY_CHECKS=0` at deploy and UNIQUE-only enforcement, *referential* correctness of everything asana pushes is entirely the sender's job — which is why the sender pre-sanitizes (E.164, dup-grain) and why the "empty snapshot ⇒ skip POST (return True)" short-circuit made a never-populated table look healthy (`SPIKE-sd02…:29-34`).

### 4.4 NULL posture summary

| Column | Nullability evidence | Cite |
|---|---|---|
| `business.office_phone` | own custom field; ~93.3% populated per dated ledger figure | `enrollment/intent_projection.py:30-32` `[UV-P-4]` |
| `{unit,offer,contact,process,asset_edit,…}.office_phone` | cascade ⇒ nullable by construction; thresholds 5/20% | §2.7 |
| `*.vertical` | `unit`: own cf; others cascade | §2.4 |
| `business.company_id` | nullable; absent for some active offices (CARD WS-B/3) | `enrollment/intent_projection.py:52-66` |
| `offer.custom_cal_status` etc. | was 0.05% (mis-sourced) before schema 1.6.0 | `enrollment/intent_projection.py:25-27` |
| `watermark.population_degraded` | additive; **legacy sidecar lacking the key reads back healthy** (default False / 1.0) | `dataframes/storage.py:840-873` |
| `Evidence.value` | `None` is a *typed absence* with `absent_reason`; ratified reasons enumerated | `models/business/identity_supply.py:183-200` |

## 5. Canonical Production Queries (appendix) and oracle access path

**Scope-cap note.** The domain rule is "extract verbatim, do not compose." Three provenance classes are used and labelled per row: **[VERBATIM-LEDGER]** copied from a `.ledge/` receipt; **[VERBATIM-CRITERIA]** copied from the `radar-schema-drift` criteria (these are the queries that pass will run); **[COMPOSED-UV-P]** composed in this pass *only* because the invoking brief required an exact query for an unverifiable surface — no result is claimed, and the ledger records the result of the first two (below) but not their SQL text.

### 5.1 Oracle access path

- **Downstream MySQL (`nhc-db`, schema `dtenuta`)**: from the `autom8y-data` repo — `direnv exec . python` → `QueryConnection.from_settings()` ATTACHes the RDS as `{attach_as}_raw` (`attach_as` default `"dtenuta"`, `core/config.py:302` of autom8y-data) and aggregation is pushed down with `SELECT * FROM mysql_query('dtenuta_raw', '<sql>')` "so aggregation runs on RDS, not through the no-pushdown scanner (SCAR-027 avoidance)". Source: `.ledge/spikes/SPIKE-asset-linkage-coverage-measurement-2026-07-08.md:15,114-122`; `.ledge/spikes/SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:21,144-146`. **Not exercised in this pass** (no DuckDB MCP attach was available; the MCP configured in this session is a *local* DuckDB file — whether it attaches `nhc-db` is `[UV-P-1]`).
- **This service's own stores** (S3 / Redis / DynamoDB): AWS CLI / boto3 with the warmer-role or an operator profile; DuckDB `read_parquet('s3://…')` with `httpfs` if configured. No in-repo production oracle script exists for these; the closest are `metrics/freshness.py` (S3 list + `FreshnessReport`) and `substrate/observe.py` / `lambda_handlers/prov_sweep.py` (provability sweep over `dataframes-v2/`).

### 5.2 Query catalog

Derivation date / source_hash for every row below: **2026-10-04 / `c29f58f4`** (this pass). Re-run triggers: `schema_snapshot_hash` drift in `.know/db.md` frontmatter, any change to `dataframes/schemas/*.py`, `core/entity_registry.py`, or `storage_namespace.py`, or a new `*/sync` push endpoint. Cadence: with every `.know/db.md` refresh.

| ID | Intent (criterion tag) | Provenance | Use when |
|---|---|---|---|
| **Q-a** | BASE TABLE enumeration of the downstream schema (Crit-1 anchor) | VERBATIM-CRITERIA | before trusting any statement about which tables asana's pushes land in |
| **Q-b** | Tenant-key column presence + NOT NULL/NULLABLE split (Crit-2 anchor) | COMPOSED-UV-P | before relying on `office_phone`/`guid` being present on a table |
| **Q-c** | NULL-rate on a NULLABLE tenant-key column (Crit-2/5 anchor) | VERBATIM-CRITERIA | before sizing a denominator over `office_phone` |
| **Q-d** | FK enumeration via INFORMATION_SCHEMA (Crit-3 anchor) | VERBATIM-CRITERIA | before assuming a declared FK is enforced |
| **Q-e** | Constraint inventory on one table (shows "PK + UNIQUE only, FK stripped") | COMPOSED-UV-P (result recorded at `SPIKE-sd02…:27`) | before relying on `account_status` referential integrity |
| **Q-f** | Liveness of a pushed table | VERBATIM-LEDGER (`SPIKE-sd02…:25-26`) | after enabling/changing a push lane |
| **Q-g** | Asset→creative→spend linkage coverage by quarter (FK-chain health, multi-hop) | VERBATIM-LEDGER (`SPIKE-asset-linkage…:124-152`) | before any spend→offer attribution claim |
| **Q-h** | Frame schema/NULL probe on the S3 business frame | COMPOSED-UV-P | to settle `[UV-P-2]`/`[UV-P-4]` |
| **Q-i** | Substrate pointer enumeration | COMPOSED-UV-P | to settle the `dataframes-v2/` expected-set |

```sql
-- Q-a [VERBATIM-CRITERIA]  (radar-schema-drift Criterion 2).  {database_name} = 'dtenuta' via mysql_query('dtenuta_raw', …) or prod.information_schema
SELECT table_name FROM prod.information_schema.tables
WHERE table_schema = '{database_name}' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Q-b [COMPOSED-UV-P]  tenant-key columns and nullability
SELECT table_name, column_name, is_nullable, column_type
FROM information_schema.columns
WHERE table_schema = 'dtenuta' AND column_name IN ('office_phone','phone','guid','chiropractor_guid','chiropractor_id','business_id')
ORDER BY column_name, table_name;

-- Q-c [VERBATIM-CRITERIA]  (radar-schema-drift Criterion 4); run for chiropractors.office_phone, business_offers.office_phone, account_status.phone, leads.office_phone
SELECT COUNT(*) total, COUNT({col}) non_null,
       ROUND(100.0 * COUNT({col}) / NULLIF(COUNT(*),0), 2) pct_populated
FROM prod.{table};

-- Q-d [VERBATIM-CRITERIA]  (radar-schema-drift Criterion 3)
SELECT table_name, column_name, referenced_table_name, referenced_column_name
FROM prod.information_schema.key_column_usage
WHERE referenced_table_name IS NOT NULL
ORDER BY table_name, column_name;

-- Q-e [COMPOSED-UV-P]  (ledger records only the RESULT: "PRIMARY KEY + uq_phone_vertical_pipeline (UNIQUE) ONLY — NO FOREIGN KEY")
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'dtenuta' AND table_name = 'account_status';

-- Q-f [VERBATIM-LEDGER]  SPIKE-sd02-empty-registry-diagnosis-2026-07-08.md:25-26
SELECT COUNT(*), MAX(synced_at) FROM account_status;
SELECT COUNT(*) FROM chiropractors;
```

```sql
-- Q-g [VERBATIM-LEDGER]  .ledge/spikes/SPIKE-asset-linkage-coverage-measurement-2026-07-08.md:122-148  (MySQL dialect, read-only, pushed down)
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
Ledger note on Q-g: DISTINCT sub-joins prevent junction many:many fan-out from multiplying spend; `jp` applies the canonical platform-match; the in-code "18.7%" direct-FK claim was measured by the same spike as 5.8% (2,589/44,523) — i.e. documented drift between a code comment and the oracle (`SPIKE-asset-linkage…:104-108`).

```sql
-- Q-h [COMPOSED-UV-P]  business-frame tenant-key probe against the S3 oracle (DuckDB + httpfs).  Settles UV-P-2 (declared 18 cols) and UV-P-4 (office_phone/company_id fill)
SELECT COUNT(*) AS total,
       COUNT(office_phone) AS office_phone_non_null,
       COUNT(company_id)  AS company_id_non_null,
       COUNT(DISTINCT office_phone) AS distinct_phones
FROM read_parquet('s3://autom8-s3/dataframes/1200653012566782/business/dataframe.parquet');
DESCRIBE SELECT * FROM read_parquet('s3://autom8-s3/dataframes/1200653012566782/business/dataframe.parquet');
-- watermark sidecar:  aws s3 cp s3://autom8-s3/dataframes/1200653012566782/business/watermark.json -

-- Q-i [COMPOSED-UV-P]  substrate pointer enumeration (expected-set cross-check; must equal registry targets ∪ store enumeration)
-- aws s3api list-objects-v2 --bucket autom8-s3 --prefix dataframes-v2/ --query "Contents[?ends_with(Key,'current.json')].Key"
```

### 5.3 UV-P register (every item needs the oracle; none were settled here)

| ID | Claim held unverified | Exact query / method | Why it matters |
|---|---|---|---|
| UV-P-1 | Downstream engine = MySQL (8.0 per operator memory only) on RDS `nhc-db`, schema `dtenuta`; table count; constraint set | Q-a, Q-d, Q-e + `SELECT VERSION();` via `mysql_query` | engine semantics (NULL in UNIQUE, FK off at deploy); ledger figures date 2026-07-08 / 2026-06-30 |
| UV-P-2 | Declared frame widths (business 18, unit 22, unit_holder 23, offer 33, contact 25, asset_edit 34, asset_edit_holder 14, process 16) equal production parquet widths | Q-h `DESCRIBE …` per `dataframes/{project}/{entity}/dataframe.parquet` | schema-version skew between warm lanes (SEAM-1 dual layout) |
| UV-P-3 | `asana-cache/tasks/…` keyspace is monolith-written only; asana's S3 CacheBackend keyspace is unused | `aws s3api list-objects-v2 --bucket autom8-s3 --prefix asana-cache/ --delimiter /` + object key shapes | registry says 385k keys (2026-06-10) |
| UV-P-4 | NULL rates of `office_phone`/`company_id` on the current Business frame (ledger: 93.3%) | Q-c on the S3 frame via Q-h | gate-key coverage; denominators for any phone-keyed bridge |
| UV-P-5 | Platform middleware enforces JWT `business_id` before handlers run | exercise an S2S route with a single-tenant token vs another tenant's `project_gid`/criteria | tenant isolation at the API boundary |
| UV-P-6 | `hours` parent chain; `calendar_integration` linkage | Asana API read of one task's `parent` | FK catalog completeness |
| UV-P-7 | `offer_id` dtype on both frames and downstream | Q-h `DESCRIBE` on offer and asset_edit frames | cross-frame join correctness |
| UV-P-8 | Downstream FK chains listed in §3.4 still hold | Q-d + `SHOW CREATE TABLE` per table | ledger date 2026-07-08 |
| UV-P-9 | identity-substrate fold's dispute check cannot see disagreement because both writers stamp `observed_at` = their own fetch time | inspect the `[data]` fold + sample two observations of one family | operator memory ↔ code agree on the supply half (`models/business/identity_supply.py:722`) |
| UV-P-10 | Production object counts per S3 prefix (registry cites 385k / 1,025 / 561 on 2026-06-10) | `aws s3 ls --summarize --recursive` per prefix | inventory snapshot freshness |

## 6. Knowledge Gaps

1. **No production oracle was available.** All "tables" are declared/code-derived; every downstream-DB statement is ledger-sourced and ≥ 2 months old (2026-07-08 / 2026-06-30 / 2026-09-08). Criterion grades are capped accordingly.
2. **autom8y-data's own `.know/db.md` was not read** (outside the permitted scope); it is the authority for DDL and would supersede §4.3 and the downstream half of §3.4.
3. **Redis in production**: usage is implied (`warmer_cache_degraded_alarm.tf`, factory auto-detect) but the live `ASANA_CACHE_PROVIDER`/`REDIS_HOST` values were not observed; key volume and TTL distribution unknown.
4. **`dataframes-v2/` live contents**: code pins the registered target to exactly the offer artifact (`lambda_handlers/prov_sweep.py:29-31`); whether any other pointer exists in S3 is unobserved (`Q-i`).
5. **`mcp/**` (asana-mcp sidecar)** was not re-read for stores; the whole-tree relational-import grep (§Status) covers `mcp/`, but a `boto3.client(` / file-store grep was run over `src/` only — `mcp/` stores were not traced.
6. **Not traced to leaf:** `automation/polling/*` state, `automation/forwarding_stage_backfill/evidence_source.py` (reads CloudWatch Logs, `boto3.client("logs")`), `lambda_handlers/{insights_export,payment_reconciliation,conversation_audit,onboarding_walkthrough}` output sinks (no `put_object` found; outputs appear to go to Asana attachments / email), `clients/data/_endpoints/*` response schemas beyond headers.

### Changes since prior version (2026-05-08, `8980bcd7`; ~5 months, ~89+ commits)

- **CORRECTED — headline:** prior said "no database layer … Schema Inventory … N/A" and stopped. The negative *relational* finding stands (re-verified: 0 ORM/driver imports, 0 SQL/migration files, no DB deps, no RDS in terraform), but the five criteria are **not** N/A — the service has real persistent stores, a tenant-key model and join chains; this version documents them.
- **CORRECTED — S3 layout:** prior documented `s3://{bucket}/dataframes/{project_gid}/` only. Now **two coexisting layouts** — legacy and v2 entity-segmented `dataframes/{project_gid}/{entity_type}/…` — with a dual-read fallback (`dataframes/storage.py:308-332,352`).
- **CORRECTED — `lifecycle/observation_store.py`:** prior called it a "parquet append path" under the S3 tier. It is a **local filesystem** store at `~/.autom8/stage_transitions/` (`lifecycle/observation_store.py:5,58-60`), not S3.
- **CORRECTED — docker-compose:** prior said "Redis only". `docker-compose.yml` now runs **LocalStack only**; Redis is referenced as an external service by the override (`docker-compose.yml:6-17`, `docker-compose.override.yml:28-36`).
- **NEW:** `storage_namespace.py` registry (12 namespaces, 6 fossils, KNOWN_DRIFT) and the generated TF/IAM JSON; **unregistered** `dataframes-v2/` substrate store (with CAS pointer), `soak-sentinel/` baseline key, `dataframes` hand-pinned reader prefix.
- **NEW:** DynamoDB idempotency table (`autom8-idempotency-keys`; pk/sk/ttl schema); Redis key shapes; `TieredCacheProvider` is Redis-only (S3 cold tier retired).
- **NEW:** 30-descriptor entity registry (16 warmable; `freshness_sla_seconds=3600` governed), per-entity schema versions/widths, cascade registry, DIRECT/CHAIN/GLOBAL classification, join-key relationship graph and its `keep="first"` hazard.
- **NEW:** cross-service surfaces — account-status / gid-mapping / vocabulary / scheduling-stratum pushes, insights/leads/appointments reads, operator batch, `exchange-business` token mint — each with the key it puts on the wire; downstream engine **MySQL (`nhc-db`, `dtenuta`; 8.0 per operator memory)** from the ledger, with `account_status` = PK + UNIQUE only (FK stripped at deploy).
- **NEW:** identity-supply route/supply (`/v1/identity-supply/{offer_gid}`; `observed_at` = fetch clock), and the three duplicate-key policies (last/first/multi) on the `(phone, vertical)` grain.
- **Confidence:** prior 0.95 (for a negative finding). This version is lower (see metadata) because it makes positive claims that were not cross-checked against a production oracle.
