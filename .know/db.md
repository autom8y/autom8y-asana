---
domain: db
generated_at: "2026-04-28T21:55:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "8c58f930"
confidence: 0.95
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Database Schema

**Status**: No database layer detected.

This project does not manage a relational schema. The `autom8y-asana` service is an async-first Asana API client (Python/FastAPI) that interfaces with the Asana REST API over HTTP and uses Redis as its caching backend. All data persistence is handled at the Asana API layer (remote) or via S3-backed Parquet files for lifecycle observation records. No ORM framework, no relational migration directory, and no database driver dependency is present.

If this finding is incorrect, check for:
- ORM model files (SQLModel, SQLAlchemy, Django ORM, GORM)
- Migration directories (`alembic/versions/`, `migrations/`, `schema/*.sql`)
- Driver dependencies (`psycopg`, `asyncpg`, `pymysql`, `duckdb`)
- Production database connection artifacts (AWS Secrets Manager secrets with `postgresql://` scheme, Terraform RDS resources, docker-compose `image: postgres` service)

**Evidence collected**:
- `pyproject.toml` — production dependencies include `httpx`, `pydantic`, `polars`, `redis`, `boto3`, `asana`; no SQLModel/SQLAlchemy/Alembic/psycopg/asyncpg/duckdb listed
- `src/autom8_asana/models/base.py` — base class is `pydantic.BaseModel` (`AsanaResource`), not an ORM entity
- `src/autom8_asana/persistence/` — 20 files; all implement Asana API write-path logic (actions, cascade, executor, graph, tracker), none contain DB connection code
- `docker-compose.override.yml` — declares Redis service only; no PostgreSQL/MySQL container
- No files matching `**/alembic/versions/*.py`, `**/migrations/*.sql`, `**/schema/*.sql` found anywhere in project root (excluding `.venv`)
- `grep` across all `src/` Python files for `sqlmodel`, `sqlalchemy`, `alembic`, `psycopg`, `asyncpg`, `pymysql`, `duckdb`, `postgresql://`, `mysql://`, `CREATE TABLE` returned zero hits

**Persistence classification**:
- **Remote API persistence**: All entity mutations go through the Asana REST API (HTTP). The `persistence/` package is an abstraction over Asana API write operations — not a local database.
- **Cache persistence**: Redis (in-memory key-value store via `autom8y-cache`) for performance caching; not a relational schema.
- **Parquet persistence**: S3-backed Parquet via `polars` and `boto3` for lifecycle stage-transition observation records (`src/autom8_asana/lifecycle/observation_store.py`). This is append-only columnar file storage, not a relational database.

## Knowledge Gaps

None — the negative finding is high confidence. All detection signals were checked exhaustively against the project root source tree (excluding `.venv`, `.worktrees`, `.mypy_cache` subdirectories).
