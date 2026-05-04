---
domain: db
generated_at: "2026-05-04T12:48Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
  - "./docker-compose*.yml"
generator: theoros
source_hash: "20ef7952"
confidence: 0.95
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Database Schema

**Status**: No database layer detected.

This project does not manage a relational schema. `autom8y-asana` is an
async-first Asana API client (Python 3.12, FastAPI) that interfaces with the
Asana REST API over HTTP. All data persistence is handled at three tiers:
remote API, Redis cache, and S3-backed Parquet. No ORM framework, no
relational migration directory, and no database driver dependency is present.

## Detection Evidence (as of `20ef7952`, 2026-05-04)

| Signal | Checked Against | Result |
|--------|----------------|--------|
| ORM imports (`sqlmodel`, `sqlalchemy`, `alembic`) | all `src/**/*.py` | **0 hits** |
| DB driver imports (`psycopg`, `asyncpg`, `pymysql`, `aiomysql`, `duckdb`, `sqlite3`) | all `src/**/*.py` | **0 hits** |
| Migration directories (`alembic/`, `migrations/`, `schema/`) | project root | **0 directories** |
| SQL files (`*.sql`) | project root (excl. `.venv`, `.worktrees`) | **0 files** |
| `pyproject.toml` DB dependencies | `[project.dependencies]` + all extras | **Absent** |
| Docker-compose DB services | `docker-compose.yml`, `docker-compose.override.yml` | **Redis only; no Postgres/MySQL** |
| Terraform RDS resources | `find *.tf` | **0 files** |
| New-code DB patterns (diff `8c58f930`→`20ef7952`) | 34 changed Python files | **0 DB imports** |

If this finding is ever incorrect, check for:
- ORM model files (SQLModel, SQLAlchemy, Django ORM)
- Migration directories (`alembic/versions/`, `migrations/`, `schema/*.sql`)
- Driver dependencies (`psycopg`, `asyncpg`, `pymysql`, `duckdb`)
- Production DB artifacts (AWS Secrets Manager secrets with `postgresql://` scheme,
  Terraform RDS resources, docker-compose `image: postgres` service)

## Persistence Topology

### Tier 1 — Remote API Persistence (Asana REST)

All entity mutations flow through the Asana REST API (HTTP/HTTPS). The
`src/autom8_asana/persistence/` package (20 files) abstracts Asana write
operations: actions, cascade, executor, graph, tracker. This is not a local
database; it is an HTTP client abstraction layer.

**Tenant scoping**: Tenant identity is carried as Asana workspace/project GIDs
passed at request time. No tenant-key column exists because there is no local
schema.

### Tier 2 — Redis Cache

- **Library**: `autom8y-cache>=0.4.0` (wraps `redis>=5.0.0`, `hiredis>=2.0.0`)
- **Connection config**: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` env vars;
  local dev: `REDIS_DB: "2"` per `docker-compose.override.yml`
- **Provider**: `autom8y-cache` tiered provider (memory → Redis fallback);
  selectable via `ASANA_CACHE_PROVIDER` env var (`memory`, `redis`, `tiered`, `none`)
- **Schema**: None. Key-value store; no schema, no migrations, no constraints.
- **Tenant isolation**: Cache keys are scoped by project GID; not a relational
  tenant-key column.

### Tier 3 — S3 Parquet (DataFrame Persistence)

- **Library**: `polars>=0.20.0` + `boto3>=1.42.19`
- **Abstraction**: `src/autom8_asana/dataframes/storage.py` →
  `S3DataFrameStorage` (canonical S3 write abstraction as of `20ef7952`)
- **Secondary**: `src/autom8_asana/lifecycle/observation_store.py` (parquet
  append path for lifecycle observation records)
- **S3 prefix pattern**: `s3://{ASANA_CACHE_S3_BUCKET}/dataframes/{project_gid}/`
- **Default bucket**: `autom8-s3` per `settings.py` `S3Settings`
- **Sidecar**: `s3://{bucket}/dataframes/{project_gid}/cache-freshness-ttl.json`
  (per `sla_profile.py`, introduced at `20ef7952`)
- **Freshness monitoring**: `src/autom8_asana/metrics/freshness.py` — lists
  `.parquet` keys via `s3.get_paginator("list_objects_v2")` and emits
  `FreshnessReport` with `parquet_count`, `oldest_mtime`, `newest_mtime`
- **Schema**: Schema-free columnar files. No DDL constraints. `polars` enforces
  column types at write time via Python type annotations only.
- **Tenant isolation**: Partitioned by `project_gid` in the S3 key path.

### Application-Layer Invariants (Not DB-Enforced)

These constraints exist in Python application code but have no DDL backing:

| Invariant | Location | Type |
|-----------|----------|------|
| `AsanaResource` fields validation | `src/autom8_asana/models/base.py:10` | Pydantic `BaseModel`, `extra="ignore"` |
| Business model field constraints | `src/autom8_asana/models/business/fields.py` | Pydantic validators |
| Cache entry versioning/schema | `src/autom8_asana/cache/models/versioning.py` | Python dataclass |
| SLA profile YAML validation | `src/autom8_asana/metrics/sla_profile.py` | YAML schema + Pydantic |

These are application-only invariants. None are mirrored at a DDL level because
no DDL exists.

## Schema Inventory, Tenant Resolution Model, FK Chain Catalog, Validation Queries, Constraint Posture

**Not applicable.** All five schema-knowledge criteria evaluate to N/A because
no relational schema exists. See persistence topology above for the actual data
layer model.

## Incremental Verification Protocol

Because this project has no database layer, the verification cadence is:

1. **On each `.know/db.md` refresh** (7-day cadence or source_hash drift):
   Re-run ORM/driver grep across `src/` and check `pyproject.toml` dependencies.
2. **Trigger for escalation**: any commit that adds `duckdb`, `sqlmodel`,
   `sqlalchemy`, `asyncpg`, or `psycopg` to `pyproject.toml` should trigger
   a full db-domain re-audit (criteria 1–5 become applicable).
3. **Production-oracle rule**: not applicable while no relational DB exists.
   If a DB is introduced, production schema (not ORM inference) becomes
   authoritative per premise-integrity throughline.

## Knowledge Gaps

None. The negative finding is high-confidence (0.95). All detection signals
checked exhaustively against project root source tree. The 34-file diff since
`8c58f930` introduces no new persistence patterns. Parquet/S3 tier expanded
with `freshness.py`, `sla_profile.py`, and `cloudwatch_emit.py` — all use
`boto3` for S3/CloudWatch only, no relational DB.
