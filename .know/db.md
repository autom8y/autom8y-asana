---
domain: db
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.95
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Database

**Status**: No database layer detected.

This project does not manage a relational schema. If incorrect, check for:
ORM model files, migration directories, or driver dependencies.

---

## Pre-Check Evidence

All five detection signals were evaluated:

**ORM imports**: `rg -l "from sqlmodel|from sqlalchemy|from django.db.models|gorm.io|@prisma" src/` returned zero results.

**Migration directories**: `find . -maxdepth 4 -name "alembic" -o -name "migrations" -o -name "schema.prisma"` returned zero results.

**Driver dependencies** in `pyproject.toml`: No `psycopg`, `asyncpg`, `sqlmodel`, `sqlalchemy`, `duckdb`, `pymysql`, or `aiomysql` entries. Declared dependencies are `httpx`, `pydantic`, `pydantic-settings`, `asana`, `polars`, `phonenumbers`, `fastapi`, `redis`.

**Connection strings** in env files and source: No `postgresql://`, `mysql://`, `DATABASE_URL`, `POSTGRES`, or `MYSQL` references found in `.env`, `.envrc`, or source.

**Docker-compose db services**: `docker-compose.yml` declares only `localstack` (S3/SecretsManager). `docker-compose.override.yml` declares `asana`, `redis` — no Postgres/MySQL/SQLite image.

## Disambiguation of Potentially Misleading Directories

- `/src/autom8_asana/persistence/` — This is the **Save Orchestration Layer** (per `TDD-0010` docstring in `persistence/models.py`). It is a unit-of-work pattern over the **Asana REST API** using Python `dataclass` objects. No ORM. No DDL. No relational tables.
- `/src/autom8_asana/models/` — Pydantic `BaseModel` subclasses representing Asana API resource shapes (tasks, projects, sections, etc.). Not SQLModel, not `__tablename__` — pure API DTO layer.
- `/src/autom8_asana/core/connections.py` — Manages Redis/S3 cache backend connection lifecycle. Not a database connection pool.
- `BaseModel` import is from `pydantic`, not `sqlalchemy.orm`.

## Conclusion

`autom8y-asana` is an async-first Asana API client SDK with Redis/S3 caching, not a service that owns a relational schema. No schema-inventory, tenant-resolution-model, FK-chain-catalog, validation-query-catalog, or constraint-posture work applies to this service.

---

### Grade Derivation

All criteria grade F because no database layer exists. This is a true-negative finding, not a documentation gap. The F grades reflect the absence of a subject domain, not inadequate knowledge capture. Confidence 0.95 per criteria spec for confirmed-negative findings.

| Criterion | Grade | Weight |
|---|---|---|
| Schema Inventory | F | 30% |
| Tenant Resolution Model | F | 25% |
| FK Chain Catalog | F | 20% |
| Validation Query Catalog | F | 15% |
| Constraints and Null Posture | F | 10% |
| **Overall** | **F (0%)** | |
