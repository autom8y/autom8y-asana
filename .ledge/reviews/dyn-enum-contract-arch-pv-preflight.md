---
type: review  # arch PV-preflight receipt (validation/audit artifact)
artifact_subtype: arch-pv-preflight-receipt
initiative: dyn-enum-contract
rite: arch
generated_by: main-thread (PV pre-flight entry gate; G-PROVE / G-PREMISE / G-DENOM)
created: 2026-06-30
status: draft  # WIP-uncommitted per operator no-auto-commit discipline
gate_verdict: PASS  # no HALT; EC-1 settled by inspection, all 6 premises confirmed
producer_truth_anchor: "autom8y-asana origin/main (NOT cwd chore/bump-core-4.6.0 f4f924d2, ~25 behind)"
consumer_truth_anchor: "autom8y-data HEAD 92d3606d (branch main)"
---

# PV Pre-Flight Receipt — dyn-enum-contract arch validation

Live re-assertion of the 6 load-bearing premises at each repo's HEAD (NOT the spike's stale read).
Every verdict carries a `{path}:{line}` receipt. **Gate: PASS** — no structural RED; EC-1 settled.

## PREMISE-2 · EC-1 DB-ENGINE — **SETTLED = MySQL** (the load-bearing fork)

Priors DISAGREED (INTEGRATE MySQL / PROTO PostgreSQL). Settled by inspecting the REAL engine. **MySQL, decisively:**

- `autom8y-data/src/autom8_data/core/config.py:217,222` — `MySQL URL ... mysql+asyncmy://user:pass@host:port/db`
- `autom8y-data/src/autom8_data/api/routes/read_only_deps.py:75` — `url = f"mysql+asyncmy://..."` + `:77 create_async_engine`
- `autom8y-data/src/autom8_data/api/routes/deps.py:129` — `_async_engine = create_async_engine(...)`
- `autom8y-data/src/autom8_data/services/base.py:387` — `("mysql+asyncmy://", "mysql+aiomysql://", "mysql://")`
- `autom8y-data/alembic/env.py:88,144,178` — `mysql+asyncmy://` connectable
- `autom8y-data/pyproject.toml:99` — `"pymysql>=1.1.0"  # Direct MySQL driver`
- `autom8y-data/docker-compose.override.yml:3,29,65` — `Dependencies: mysql` / `DB_HOST: mysql`
- `autom8y-data/docker/dev/entrypoint.sh:13,28,52` — `dev_wait_for_mysql` / `DB_PORT 3306` / `mysql-seed.sql`
- `autom8y-data/src/autom8_data/core/models/_advertising.py:16` — `from sqlalchemy.dialects import mysql`

**Consumer-store shape B (MySQL):** upsert = `INSERT ... ON DUPLICATE KEY UPDATE`; lock = `GET_LOCK()/RELEASE_LOCK()`.
**NOT** PostgreSQL `ON CONFLICT(key) DO UPDATE` / `pg_advisory_xact_lock`. **→ PROTO canary-1 (PostgreSQL `ON CONFLICT`) must be re-derived for MySQL by the 10x-dev build.**
POLYGLOT NOTE (for dependency-analyst): DuckDB analytics (`Dockerfile` `mysql_scanner.duckdb_extension`, reads MySQL) + sqlite test fixtures (`analytics/fixtures/schema.py:18`) COEXIST — but the `verticals` transactional write-path is MySQL (SQLModel `table=True`). Confirm no DuckDB-analytics second write-consumer of verticals.

## PREMISE-1 · FK-PARENT REALITY — **CONFIRMED (richer than the spike's 3)**

`verticals` (`_platform.py:131 class Vertical(SQLModel, table=True)`, `:12/:140 __tablename__="verticals"`) is an FK-parent dimension AND the lead-enrichment join hub. Inbound edges (≥5):

- `_platform.py:146` — `vertical_key: str = Field(unique=True, name="key")` (portable upsert key)
- `_platform.py:147` — `vertical_name: str = Field(unique=True, name="name")` (**the UPDATE-path collision hazard — confirmed live**)
- `_platform.py:162` — `Offer.vertical_key ... foreign_key="verticals.key"` (**offers.category STRING FK — confirmed live**)
- `_advertising.py:322` — `asset_verticals` table; composite PK `(asset_id, vertical_id)` also FK (`factories.py:1063`)
- `core/repositories/dimension_enrichment.py:144` — `.join(Vertical, Campaign.vertical_id == Vertical.vertical_id)` (campaigns int FK; PRIMARY lead-vertical path, `:76`)
- `core/repositories/dimension_enrichment.py:166` — `Business.default_vertical_id == Vertical.vertical_id` (**business.default_vertical_id — ADDITIONAL inbound edge, organic-lead FALLBACK path `:77`; not in the spike's enumeration**)

BLAST-RADIUS SIGNAL (for structure-evaluator): a mis-keyed/orphaned vertical breaks lead dimensional enrichment (campaign PRIMARY + business FALLBACK both join through `verticals`). 
UV-P: `asset_verticals` ~43K ROW COUNT not live-queried (no DB creds in env) — structural edge confirmed; the count is deferred to a live MySQL query (operator / dependency-analyst with creds).

## PREMISE-3 · SIX SOURCES + UNTYPED LEAK — **CONFIRMED (refined)**

The vertical option-set crosses the asana→data seam as an **untyped `str`, with NO enum-option-set validation**:
- Producer: `autom8y-asana origin/main:src/autom8_asana/services/gid_push.py:490` — `"vertical": str(vertical)` (parsed from `pv1:{phone}:{vertical}`, `:104,:123`)
- Consumer: `autom8y-data:src/autom8_data/api/models_comparison.py:62` — `vertical: str = Field(...)` ("Vertical name, business term, e.g. 'dental'")

The existing typed sync (`/api/v1/account-status/sync`) is **snapshot-replace scoped by a `source` column**: `autom8y-data:_platform.py:497-498` — `Snapshot replace protocol [SD-05]: DELETE FROM account_status WHERE source='section_classifier'`. **`verticals` has NO `source` column** (`_platform.py:15-17` = id/key/name only) → source-scoped snapshot-replace is structurally impossible on verticals → **additive-upsert is mandatory** (live confirmation of the INTEGRATE FK-parent correction).

## PREMISE-4 · PRODUCER/CONSUMER SEAM — **CONFIRMED @ origin/main (⚠ PRODUCER LINE-DRIFT)**

- `custom_field.py:113` — `enum_options: list[CustomFieldEnumOption] | None = Field(` (live option-set read; `:19 class CustomFieldEnumOption`, `:45 class CustomField`) ✓ accurate
- `resolver_schema.py:366,368,473` — `values_source` (`'hardcoded'`/`'asana_configured'`) door ✓ accurate
- `gid_push.py:163` — `async def _push_to_data_service(` (**spike/frame said :131 — STALE**)
- `gid_push.py:328` AND `:554` — `return True  # Nothing to push is not a failure` (**leaf empty-guard; spike said :519 — STALE, and there are TWO push paths, not one**)
- `gid_push.py:375,564` — `/api/v1/account-status/sync` envelope + endpoint_path
- Consumer typed contract already exists: `autom8y-data:src/autom8_data/api/data_service_models/_account_status_sync.py:71,114` (request/response, "Mirrors the gid-mappings sync pattern")

**G-PREMISE FLAG: the producer `gid_push.py` line anchors in the spike/frame are STALE.** Live origin/main = :163 / :328+:554 / :375 / :564. All downstream stations MUST use live origin/main numbers. (Consumer `_platform.py` anchors :146/:147/:162 + `services/vertical.py:9` ARE accurate at HEAD.)

## PREMISE-5 · DEFER-1 TRIGGER STATE — **NOT FIRED (N<3)**

- `git grep -l '/vocabularies/sync|field_key'` (asana origin/main) → **ZERO files** — the vocab contract is PROPOSED/not-yet-existing (correctly; it is the design under validation).
- `/api/v1/account-status/sync` bound only by `gid_push.py` (the ONE existing typed snapshot contract).
- So: vocab would be the 2nd `field_key`-class binding; autom8y-data the 1st vocab consumer. **N≥3 (2nd field_key AND 3rd consumer) NOT met.** → per-instance contract is the correct scope; **DEFER-1 fleet registry stays watch-registered, escalate-only** (G-DEFER).

## PREMISE-6 · SERVICE DENOMINATOR — **CONFIRMED**

REAL service repos (10): `autom8y, autom8y-admin-ui, autom8y-ads, autom8y-asana, autom8y-contente-tokens, autom8y-data, autom8y-fe-skeleton, autom8y-scheduling, autom8y-sms, tools` + the `autom8` monorepo (PRESENT). **66 `*-wt-*` worktrees EXCLUDED** (G-DENOM positive selection).

## BONUS — load-bearing compose-with finding (for structure/remediation)

The consumer ALREADY models verticals as **permanent / create-only**, with a service layer + gRPC surface the vocab-sync should COMPOSE with, not reinvent:
- `autom8y-data:src/autom8_data/services/vertical.py:9` — "No Delete operation (verticals are permanent)"; `:28 class VerticalService(BaseService[Vertical])`
- `autom8y-data:src/autom8_data/grpc/handlers/vertical.py:128` — `async def create_vertical(...)` (Create handler; **NO delete_vertical handler**)
- `autom8y-data:src/autom8_data/proto/.../v1/__init__.py:667` — "Verticals are permanent reference data - no delete operation is provided" (CreateVertical / GetVerticalByKey / ListVerticals — no Delete in the proto)

→ Boundary-alignment signal: the additive-upsert DELETE-forbidden contract is **already the domain's stated invariant**. Leverage point: route `/vocabularies/sync` through `VerticalService` (create-if-absent / update-name) rather than a new bespoke store.

## Gate verdict

**PASS** — 6/6 premises confirmed at HEAD; EC-1 settled (MySQL); no structural RED → no G-HALT. Sprint-1 (topology-cartographer) cleared to dispatch. All stations ground producer on origin/main, consumer on autom8y-data HEAD, and use the LIVE (not spike) line numbers.
