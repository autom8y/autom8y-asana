---
type: review  # arch topology-inventory (sprint-1 cartography artifact)
artifact_subtype: arch-topology-inventory
initiative: dyn-enum-contract
rite: arch
sprint: 1-of-5 (topology -> dependency -> structure -> remediation -> adversary)
generated_by: topology-cartographer
created: 2026-06-30
status: draft  # WIP-uncommitted per operator no-auto-commit discipline
rung: cataloged  # G-RUNG: topology reaches "cataloged" ONLY — never "validated"/"proven"
producer_truth_anchor: "autom8y-asana origin/main (ca28251d) — NOT cwd chore/bump-core-4.6.0 (f4f924d2)"
consumer_truth_anchor: "autom8y-data HEAD (92d3606d, branch main)"
legacy_source_anchor: "autom8 monorepo main (5c749c11) — NON-CANONICAL frozen-legacy"
ec1_status: "SETTLED = MySQL (cited, NOT re-resolved); authoritative receipt taken by dependency-analyst"
downstream: dependency-analyst (sprint-2)
---

# Topology Inventory — dyn-enum-contract sync seam

The canonical structural baseline for the `dyn-enum-contract` telos: *one typed, additive,
FK-safe sync contract carrying an Asana enum-option-set change into `autom8y-data.verticals`*.
Every entry carries a `{path}:{line}` receipt at the stated anchor and a confidence rating.
**Rung discipline (G-RUNG): this artifact CATALOGS what IS — it does not validate, score, or
classify health.** Coupling = sprint-2; anti-patterns = sprint-3.

Anchor conventions used in every receipt below:
- **[P]** = producer `autom8y-asana` at `origin/main` (ca28251d) — verified via `git grep -n … origin/main`
- **[C]** = consumer `autom8y-data` at `HEAD` (92d3606d) — verified via `git grep -n … HEAD`
- **[L]** = legacy `autom8` monorepo at `main` (5c749c11), path-root `/Users/tomtenuta/Code/autom8`
- Absolute repo roots: producer `/Users/tomtenuta/Code/a8/repos/autom8y-asana`, consumer
  `/Users/tomtenuta/Code/a8/repos/autom8y-data`.

---

## 1 · Service Catalog — REAL repo roster, IN/OUT of the vertical option-set seam

**Denominator gate (G-DENOM):** positive selection of REAL services only. 66 `*-wt-*`
worktrees EXCLUDED (verified: `ls -1d …/*-wt-*/ | wc -l` = 66; total dirs = 76).
The roster below is the 10 real `autom8y-*`/`tools` service repos + the `autom8` legacy monorepo.

A unit is **IN** the seam iff it materializes, consumes, or FK-references the vertical
option-set / `verticals` dimension. Deciding `{path}:{line}` cited for every IN/OUT call.

| # | Unit | On-disk path | Role | IN/OUT (option-set seam) | Deciding receipt | Confidence |
|---|------|--------------|------|--------------------------|------------------|------------|
| 1 | **autom8y-asana** | `/Users/tomtenuta/Code/a8/repos/autom8y-asana` | **PRODUCER** (source-of-record reader) | **IN — primary** | [P] `custom_field.py:113` reads Asana `enum_options`; [P] `gid_push.py:163` push helper | High |
| 2 | **autom8y-data** | `/Users/tomtenuta/Code/a8/repos/autom8y-data` | **CONSUMER / STORE** (upsert target) | **IN — primary** | [C] `core/models/_platform.py:142` `__tablename__ = "verticals"` | High |
| 3 | **autom8y** (monorepo) | `/Users/tomtenuta/Code/a8/repos/autom8y` | Orchestrator + **shared SDK host** (`autom8y-core`) | **IN — downstream consumer** | `sdks/python/autom8y-core/src/autom8y_core/clients/data_intake.py:473` `def list_verticals(self) -> VerticalsListResponse`; `docker/dev/seed/mysql-seed.sql:23` "Verticals (dimension table)" | High |
| 4 | **autom8y-ads** | `/Users/tomtenuta/Code/a8/repos/autom8y-ads` | Ads service w/ vertical-keyed policy | **IN — downstream consumer** | `src/autom8_ads/api/creative_performance.py:90` `VerticalNormalizer.normalize(body.vertical_key)`; `src/autom8_ads/api/policy_override.py:42` `"/policies/verticals/{vertical_key}/override"` | High |
| 5 | **autom8y-sms** | `/Users/tomtenuta/Code/a8/repos/autom8y-sms` | SMS service carrying vertical key | **IN — downstream consumer** | `src/autom8_sms/models/conversation.py:169` `default_vertical_key: str` (+ `:92 vertical_id: int`) | High |
| 6 | **autom8y-scheduling** | `/Users/tomtenuta/Code/a8/repos/autom8y-scheduling` | Scheduling service w/ verticals FK | **IN — downstream consumer (FK)** | `src/autom8_scheduling/models/shared.py:48` `foreign_key="verticals.id"` (on `default_vertical_id`) | High |
| 7 | **autom8y-admin-ui** | `/Users/tomtenuta/Code/a8/repos/autom8y-admin-ui` | TS/JS admin frontend | **OUT (border) — junction-CRUD binding only** | `src/lib/api/_generated/openapi.d.ts:785` `"/api/v1/asset-verticals"` (generated client types only; no vocabulary materialization) | Medium |
| 8 | **autom8y-fe-skeleton** | `/Users/tomtenuta/Code/a8/repos/autom8y-fe-skeleton` | TS/JS frontend template | **OUT (border) — junction-CRUD binding only** | `src/lib/api/_generated/openapi.d.ts:857` `"/api/v1/asset-verticals"` (generated, skeleton template) | Medium |
| 9 | **autom8y-contente-tokens** | `/Users/tomtenuta/Code/a8/repos/autom8y-contente-tokens` | Token service | **OUT — no touch** | 0 vertical hits across `*.py/*.go/*.ts/*.sql` (grep-zero) | High |
| 10 | **tools** (symlink → `/Users/tomtenuta/Code/a8/tools`) | `/Users/tomtenuta/Code/a8/tools` (`semantic-score/`) | Dev tooling | **OUT — no touch** | 0 vertical hits (grep-zero) | High |
| 11 | **autom8** (legacy monorepo) | `/Users/tomtenuta/Code/autom8` | Legacy contente_api host | **OUT of CANONICAL seam — frozen-legacy source** | [L] `apis/contente_api/models/vertical/main.py:19` `class Vertical(Enum)` — NON-CANONICAL per telos (sources #1/#2/#3, see §5) | High |

### DEFER-1 consumer denominator (seed for sprint-2)

Downstream consumers of the vertical vocabulary / `verticals` dimension, EXCLUDING the
producer (asana) and the store (data):

- **Solid downstream consumers (4):** autom8y (via `autom8y-core` SDK), autom8y-ads,
  autom8y-sms, autom8y-scheduling.
- **Border consumers (2):** autom8y-admin-ui, autom8y-fe-skeleton — bind only the
  `/api/v1/asset-verticals` *junction* CRUD via generated client types; no vocabulary
  materialization. Recorded for completeness; sprint-2 decides whether the junction-CRUD
  binding counts toward the DEFER-1 denominator.
- **Store / target (1):** autom8y-data is the **1st vocab consumer** of a `/vocabularies/sync`
  contract (per PV PREMISE-5). The PV pre-flight established the DEFER-1 trigger as **NOT
  FIRED (N<3)**: the proposed vocab contract would be the 2nd `field_key`-class binding and
  data the 1st vocab consumer — neither the 2nd-field_key nor 3rd-consumer threshold is met.
  This inventory does not re-adjudicate DEFER-1; it supplies the structural denominator.

> **Scope note (G-RUNG / anti-pattern guard):** the IN/OUT calls above record *structural
> touch of the seam surface*, NOT consumer→producer dependency arrows. Who-calls-whom is
> sprint-2 (dependency-analyst) territory.

---

## 2 · Producer Surface — autom8y-asana @ origin/main (LIVE anchors)

All anchors re-verified at `origin/main` (ca28251d). The cwd branch `chore/bump-core-4.6.0`
(f4f924d2) is OFF-ANCHOR (~25 commits behind, lacks the gfr substrate) — NOT used.

| Surface | Receipt [P] | Verbatim marker | Confidence |
|---------|-------------|-----------------|------------|
| Asana enum-option-set read (source-of-record) | `models/custom_field.py:113` | `enum_options: list[CustomFieldEnumOption] \| None = Field(` | High |
| Push helper (single conduit, two call paths) | `services/gid_push.py:163` | `async def _push_to_data_service(` | High |
| — call path A (gid-mappings) | `services/gid_push.py:338` | `return await _push_to_data_service(` | High |
| — call path B (account-status) | `services/gid_push.py:563` | `return await _push_to_data_service(` | High |
| Leaf empty-guard (path A) | `services/gid_push.py:328` | `return True  # Nothing to push is not a failure` | High |
| Leaf empty-guard (path B) | `services/gid_push.py:554` | `return True  # Nothing to push is not a failure` | High |
| Account-status response envelope | `services/gid_push.py:375` | `"""POST /api/v1/account-status/sync response envelope."""` | High |
| Account-status endpoint path | `services/gid_push.py:564` | `endpoint_path="/api/v1/account-status/sync",` | High |
| **Producer-push FEATURE FLAG** | `services/gid_push.py:62` | `GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"` (gate read at `:95`) | High |
| Seam target base-URL resolver | `services/gid_push.py:144` | `return os.environ.get("AUTOM8Y_DATA_URL")` | High |
| `values_source` enum door (schema) | `api/routes/resolver_schema.py:366` | `values_source: str \| None = Field(` | High |
| — door description | `api/routes/resolver_schema.py:368` | `…(e.g., 'hardcoded', 'asana_configured').` | High |
| — door population | `api/routes/resolver_schema.py:473` | `values_source=annotation.get("values_source"),` | High |
| Insights READ kill-switch (distinct path) | `clients/data/client.py:117` | `FEATURE_FLAG_ENV_VAR = "AUTOM8Y_DATA_INSIGHTS_ENABLED"` | High |

**API surface (HTTP, producer-side):** asana is a FastAPI service (`api/main.py`) whose
`_push_to_data_service` conduit POSTs to the consumer's REST endpoints. The ONLY existing
typed push contract today is `POST /api/v1/account-status/sync` (envelope `:375`, endpoint
`:564`). There is **no `/vocabularies/sync` producer binding** (see §4).

---

## 3 · Consumer Surface — autom8y-data @ HEAD (LIVE anchors)

| Surface | Receipt [C] | Verbatim marker | Confidence |
|---------|-------------|-----------------|------------|
| `verticals` FK-parent table | `core/models/_platform.py:131` | `class Vertical(SQLModel, table=True):` | High |
| — tablename | `core/models/_platform.py:142` | `__tablename__ = "verticals"` | High |
| — upsert key (unique) | `core/models/_platform.py:146` | `vertical_key: str = Field(unique=True, sa_column_kwargs={"name": "key"})` | High |
| — name (unique — UPDATE collision hazard) | `core/models/_platform.py:147` | `vertical_name: str = Field(unique=True, sa_column_kwargs={"name": "name"})` | High |
| Inbound FK: offers.category STRING FK | `core/models/_platform.py:162` | `vertical_key: str = Field(sa_column_kwargs={"name": "category"}, foreign_key="verticals.key")` | High |
| Inbound FK: asset_verticals junction | `core/models/_advertising.py:322` | `__tablename__ = "asset_verticals"` (+ `:326` `vertical_id … foreign_key="verticals.id", primary_key=True`) | High |
| Inbound FK: Campaign.vertical_id (PRIMARY lead path) | `core/models/_advertising.py:80` | `vertical_id: int = Field(foreign_key="verticals.id")` | High |
| Enrichment join: campaign → vertical (PRIMARY) | `core/repositories/dimension_enrichment.py:144` | `.join(Vertical, Campaign.vertical_id == Vertical.vertical_id)` | High |
| Enrichment join: business → vertical (FALLBACK / organic) | `core/repositories/dimension_enrichment.py:166` | `.join(Vertical, Business.default_vertical_id == Vertical.vertical_id)` | High |
| **ADDITIONAL** inbound verticals.id FK (pre-table) | `core/models/_platform.py:72` | `foreign_key="verticals.id"` (owning model unresolved this pass) | Medium |
| **ADDITIONAL** inbound verticals.id FK ("5 NULLs") | `core/models/_platform.py:451` | `vertical_id: int \| None = Field(default=None, foreign_key="verticals.id")  # 5 NULLs` | High |
| No-delete service surface | `services/vertical.py:9` | `- No Delete operation (verticals are permanent)` (+ `:28` `class VerticalService(BaseService[Vertical])`) | High |
| gRPC create handler (NO delete handler) | `grpc/handlers/vertical.py:128` | `async def create_vertical(self, create_vertical_request: CreateVerticalRequest) -> Vertical:` | High |
| Proto permanence invariant | `proto/autom8/data/v1/__init__.py:667` | `Verticals are permanent reference data - no delete operation is provided.` | High |
| Snapshot-replace `source`-scoped pattern (account_status) | `core/models/_platform.py:497-498` | `Snapshot replace protocol [SD-05]: DELETE FROM account_status WHERE source = 'section_classifier',` | High |
| `verticals` ABSENCE of a `source` column | `core/models/_platform.py:131-162` | table fields = id/key/name/… ; **no `source` column present** (structural absence → source-scoped snapshot-replace is impossible on verticals) | Medium |
| Existing typed-sync precedent (request) | `api/data_service_models/_account_status_sync.py:70` | `class AccountStatusSyncRequest(BaseModel):` (`:6` "Mirrors the gid-mappings sync pattern") | High |
| Existing typed-sync precedent (response) | `api/data_service_models/_account_status_sync.py:113` | `class AccountStatusSyncResponse(BaseModel):` | High |

**API surface (consumer-side, dual):** data exposes the Vertical surface on BOTH transports —
REST (FastAPI `api/main.py`) and **gRPC** (`grpc/server.py`, handler `grpc/handlers/vertical.py:128`).
The proto contract (`proto/autom8/data/v1/__init__.py:667`) is **Create / Get-by-key / List, NO Delete**.

### Second read-consumer of `verticals` — the DuckDB analytics path (topology surface)

The analytics subsystem is a **second, read-only consumer** of the `verticals` dimension,
reached over `mysql_scanner` (DuckDB reads the MySQL operational store):

- `src/autom8_data/analytics/core/infra/enrichment_views.py:152` — `f"LEFT JOIN {raw_prefix}.verticals v\n"` (enrichment view builder; multiple joins at `:152/:216/:218/:274`)
- `enrichment_views.py:139` — `vertical_key: Direct 1-hop join via payments.vertical_id -> verticals.id.`
- 45 analytics files reference `verticals` (grep count, `analytics/**`).
- Dockerfile confirms the extension: `Dockerfile:40` `mysql_scanner.duckdb_extension`, `:66` `MYSQL_SCANNER_VENDOR_DIR=/opt/duckdb-extensions/v1.4.4/linux_amd64`.

> **Recorded as a structural surface (read-side).** No analytics *write*-path to `verticals`
> was found this pass; whether any analytics path is a SECOND WRITE-consumer is flagged for
> sprint-2/3 (Unknown U-3). Confidence: High (read surface), Medium (write-absence).

---

## 4 · Sync Seam `/api/v1/vocabularies/sync` — PROPOSED / NOT-YET-EXISTING

The contract under validation has **ZERO bindings** at both truth anchors:

- **Producer (asana origin/main):** `git grep -nE "vocabularies/sync|/vocabularies|field_key"`
  matched only `persistence/tracker.py:230-234` — a generic `for field_key in all_field_keys:`
  loop variable, **NOT** a `/vocabularies` route binding. Effective `/vocabularies` bindings: **0**.
- **Consumer (data HEAD):** `git grep -nE "vocabularies/sync|/vocabularies"` → **0 files**.

**Verdict (cataloged, not validated):** `/api/v1/vocabularies/sync` is **PROPOSED / non-existent**
— it is the design under validation, correctly absent from both real trees. The nearest extant
analogue it would mirror is the typed `POST /api/v1/account-status/sync` precedent (§2 producer
`gid_push.py:564`; §3 consumer `_account_status_sync.py:70/:113`). Confidence: High.

---

## 5 · Six Vertical Materialization Sources

| # | Source | Anchor | Canonical? | Confidence |
|---|--------|--------|------------|------------|
| 1 | `Vertical(Enum)` (legacy enum) | [L] `apis/contente_api/models/vertical/main.py:19` `class Vertical(Enum):` | **NON-CANONICAL** (frozen-legacy, OUT) | High |
| 2 | `VERTICAL_NAMES` (legacy name map) | [L] `apis/contente_api/models/vertical/main.py:261` `VERTICAL_NAMES: dict[Vertical, str] = {` (used `:232/:236`) | **NON-CANONICAL** (frozen-legacy, OUT) | High |
| 3 | contente `db_verticals()` SQL reader | [L] `apis/contente_api/models/vertical/main.py:12` `def db_verticals() -> dict[str, dict[str, Any]]:` (called `:201/:222/:321`) | **NON-CANONICAL** (frozen-legacy, OUT) | High |
| 4 | **Asana live `enum_options`** (AUTHORITATIVE source-of-record) | [P] `models/custom_field.py:113`; Asana Vertical custom-field **GID `1182735041547604`**, "50+ enabled enum options" per [P] `dataframes/annotations.py:224-225` | **AUTHORITATIVE** | High |
| 5 | asana `SEMANTIC_ANNOTATIONS.valid_values` | [P] `dataframes/annotations.py:71` `SEMANTIC_ANNOTATIONS: dict[str, dict[str, Any]] = {` ; vertical entries at `:214`/`:246` set `valid_values: "dynamic"` (`:222/:252`) + `values_source: "asana_configured"` (`:232`) | Asana-deferring (NOT hardcoded for vertical) | High |
| 6 | **autom8y-data `verticals`** (upsert TARGET) | [C] `core/models/_platform.py:131` / `:142` | **CANONICAL store / sync target** | High |

**Refinement on source #5 (drift-relevant):** for the `vertical` field specifically, asana does
**not** hardcode the value list — `dataframes/annotations.py:222/:252` set `valid_values: "dynamic"`
and `:232` sets `values_source: "asana_configured"`, i.e. asana structurally defers the vertical
vocabulary to source #4 (Asana live `enum_options`). The canonical authority enum lives at
[P] `dataframes/annotations.py:50` — `VALID_VALUES_SOURCES: frozenset[str] = frozenset({"hardcoded", "asana_configured", "mixed"})` — which carries a **THIRD value, `"mixed"`**, beyond the brief's two.

---

## 6 · Tech-Stack Inventory + Entry Points + Structure Profiles

### Per-unit tech stack (build-manifest grade)

| Unit | Lang | Build/dep mgr | Framework markers | IaC | Confidence |
|------|------|---------------|-------------------|-----|------------|
| autom8y-asana [P] | Python | `pyproject.toml` (uv; `uv.lock` present) | `fastapi>=0.115`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, **`asana>=5.0.3`** (Asana SDK), `autom8y-telemetry`, **`autom8y-core>=4.2.0,<5.0.0`** (index "autom8y" CodeArtifact) | `Dockerfile`, `Dockerfile.dev`, `terraform/` | High |
| autom8y-data [C] | Python | `pyproject.toml` (uv; `uv.lock`) | `sqlmodel>=0.0.14`, `fastapi>=0.115`, **`betterproto>=2.0.0b7`** (gRPC/proto), **`duckdb==1.4.4`**, **`asyncmy>=0.2.11,<0.3.0`** (async MySQL), `pymysql>=1.1.0`, `types-PyMySQL` | `Dockerfile`, `Dockerfile.dev`, `docker-compose.override.yml` | High |
| autom8y (monorepo) | Python | `pyproject.toml`; hosts `sdks/python/autom8y-core` (**v4.6.0**) | shared SDK `DataServiceClient` + `PhoneVerticalPair` + `VerticalsListResponse` | `terraform/`; `docker/dev/seed/mysql-seed.sql` | High |
| autom8y-ads | Python | `pyproject.toml` | (FastAPI-family; `VerticalNormalizer` domain class) | `Dockerfile`, `Dockerfile.dev` | Medium |
| autom8y-sms | Python | `pyproject.toml` | (Field/model layer; `vertical_id`/`default_vertical_key`) | `Dockerfile` | Medium |
| autom8y-scheduling | Python | `pyproject.toml` | (SQLModel-family; `foreign_key="verticals.id"`) | `Dockerfile` | Medium |
| autom8y-admin-ui | TS/JS | `package.json` | generated OpenAPI client (`_generated/openapi.d.ts`) | — | Medium |
| autom8y-fe-skeleton | TS/JS | `package.json` | generated OpenAPI client | — | Medium |
| autom8 (legacy) [L] | Python | `pyproject.toml` | `contente_api` (vertical enum/SQL host) | — | Medium |

### EC-1 DB-engine — SETTLED = MySQL (CITED, NOT re-resolved)

Per the binding brief, EC-1 is **settled** and the topology-cartographer CONFIRMS the
config location without re-adjudicating; the dependency-analyst takes the authoritative
receipt in sprint-2:

- [C] `core/config.py:217` — `MySQL URL in format: mysql+asyncmy://user:pass@host:port/database`
- [C] `core/config.py:222` — `return self.mysql_url.replace("mysql://", "mysql+asyncmy://")`

**Polyglot persistence (topology fact):** MySQL operational store (`asyncmy`/`pymysql`,
SQLModel `table=True`) + DuckDB analytics (`duckdb==1.4.4` + `mysql_scanner` reading MySQL,
§3) + sqlite test fixtures. The `verticals` transactional write-path is MySQL. The DuckDB
path is a confirmed **read**-consumer (§3); write-consumer status is Unknown U-3.

### Entry-point catalog

| Unit | Entry points |
|------|--------------|
| autom8y-asana [P] | FastAPI app `src/autom8_asana/api/main.py` (+ `api/lifespan.py`); console script `autom8-query = autom8_query_cli:main` (`pyproject.toml:106`); CLIs `automation/polling/cli.py`, `metrics/__main__.py` |
| autom8y-data [C] | FastAPI app `src/autom8_data/api/main.py`; **gRPC server `src/autom8_data/grpc/server.py`**; canary `api/canary/__main__.py`; console script `autom8y-analytics = autom8_data.analytics.cli:app` (`pyproject.toml:116`); `src/autom8_data/materialization_runner.py` |
| autom8y (SDK host) | library exports via `sdks/python/autom8y-core/src/autom8y_core/__init__.py` (`DataServiceClient`, `PhoneVerticalPair`, `VerticalsListResponse`) |

### Structure profiles (top-level, observational)

- **autom8y-asana [P]:** `src/autom8_asana/{api, automation, cache, clients, core, dataframes,
  metrics, models, persistence, services, …}`; supporting `config/ docker/ docs/ examples/
  prototypes/ queries/ runbooks/ scripts/ terraform/ tests/`. FastAPI service + Asana polling
  automation + several CLIs.
- **autom8y-data [C]:** `src/autom8_data/{analytics, api, clients, core, grpc, proto, services,
  utils}` + `materialization_runner.py`; supporting `alembic/ migrations/ proto/ config/ docker/
  docs/ examples/ fixtures/ packages/ prototypes/ runbooks/ scripts/ tests/`. Dual REST+gRPC,
  DuckDB analytics subsystem, alembic-migrated MySQL.
- **autom8y (SDK host):** vertical vocabulary lives under `sdks/python/autom8y-core` (v4.6.0,
  CodeArtifact-distributed) and the generated `autom8y-client-sdk`.

---

## 7 · Premise-Drift Findings (G-PREMISE — re-verified at stated anchors)

Producer LIVE-anchor confirmations matched the brief's corrected numbers exactly
(`custom_field.py:113`, `gid_push.py:163/:328/:554/:375/:564`, `resolver_schema.py:366/:368/:473`).
**New / additional drift surfaced this pass:**

| # | Drift | Spike/frame said | LIVE truth | Severity |
|---|-------|------------------|------------|----------|
| D-1 | **Feature-flag surface mislocated** | resolver_schema.py `:351/:491` | resolver_schema.py is **475 lines** (`:491` is past EOF; `:351` is now a `Field` close-paren). The REAL producer-push flag is [P] `gid_push.py:62` `GID_PUSH_ENABLED` (gate `:95`). No env-flag gating exists inside the resolver route. | Material — corrects the gating surface |
| D-2 | **`values_source` machinery location** | implied resolver_schema only | the authority enum lives at [P] `dataframes/annotations.py:50` `VALID_VALUES_SOURCES = frozenset({"hardcoded","asana_configured","mixed"})` — **a third value `"mixed"`** not in the brief | Minor — enriches the door model |
| D-3 | **Two producer push call-sites** | one push path | `_push_to_data_service` is invoked at [P] `gid_push.py:338` (gid-mappings) AND `:563` (account-status) — TWO call paths through ONE helper | Minor — confirms brief's "TWO push paths" |
| D-4 | **Consumer tablename line** | `_platform.py:140` (PV said :12/:140) | `__tablename__ = "verticals"` is at [C] `_platform.py:142` | Trivial |
| D-5 | **Key field API form** | `name="key"` / `name="name"` | LIVE uses `sa_column_kwargs={"name": "key"}` / `{"name": "name"}` ([C] `_platform.py:146/:147`) — same intent, different SQLModel API | Trivial |
| D-6 | **Additional inbound verticals.id FK edges** | 3 inbound edges enumerated | LIVE shows MORE: [C] `_platform.py:72` and `_platform.py:451` (`# 5 NULLs`) are additional `foreign_key="verticals.id"` references beyond the brief's set | Material — widens the fan-in surface |

All downstream stations MUST continue to ground producer on `origin/main` and consumer on
`HEAD`, and use the LIVE numbers above.

---

## 8 · Explicit Unknowns for the dependency-analyst (sprint-2)

Per EXIT-7: zero "unknown topology" markers silently passed forward.

### Unknown: U-1 — asset_verticals (and full inbound FK) row counts not live-queried
- **Question**: actual row counts on `asset_verticals` (~43K asserted by spike) and the other inbound verticals FK tables.
- **Why it matters**: sizes the blast-radius of a mis-keyed/orphaned vertical row; sprint-2 coupling weighting.
- **Evidence**: structural FK edges confirmed ([C] `_advertising.py:326`, `_platform.py:72/:162/:451`); no DB creds in env to run `SELECT COUNT(*)`.
- **Suggested source**: live MySQL query by operator / dependency-analyst with creds.

### Unknown: U-2 — feature-flag completeness (resolver/dynamic-vocab gate)
- **Question**: was there ever a *resolver-level / dynamic-vocab* feature flag (per the spike's stale `resolver_schema.py:351/:491`), now removed — or did the spike conflate the `values_source` door with a feature flag?
- **Why it matters**: determines whether dynamic-vocab resolution is independently gateable from the producer push (`GID_PUSH_ENABLED`).
- **Evidence**: `resolver_schema.py` (475 lines) has no env-flag gating; producer-push gate is `gid_push.py:62 GID_PUSH_ENABLED`; door is `annotations.py:50`.
- **Suggested source**: git history of `resolver_schema.py` / `annotations.py`; sprint-2 dependency trace of the dynamic-resolution path.

### Unknown: U-3 — DuckDB analytics: read-only, or a SECOND write-consumer of verticals?
- **Question**: does any `analytics/**` path WRITE the `verticals` table, or is it strictly read (via `mysql_scanner` joins / enrichment views)?
- **Why it matters**: a second write-path would change the additive-upsert contract's exclusivity assumptions.
- **Evidence**: 45 analytics files reference verticals; confirmed READ surface ([C] `enrichment_views.py:152` `LEFT JOIN … verticals`); no write-path found this pass.
- **Suggested source**: sprint-2 dependency trace of `analytics/core/{joins,infra,dimensions}` against the MySQL write surface.

### Unknown: U-4 — autom8y-core SDK version-pin matrix across consumers
- **Question**: which exact `autom8y-core` version does each IN consumer pin (asana origin/main pins `>=4.2.0,<5.0.0`; cwd branch bumps to `4.6.0`; SDK head is `4.6.0`)?
- **Why it matters**: the SDK is the shared vertical-vocabulary conduit (`list_verticals → VerticalsListResponse`); pin skew = vocabulary-shape skew across the fleet.
- **Evidence**: [P] `pyproject.toml` `autom8y-core>=4.2.0,<5.0.0` (index "autom8y"); SDK `clients/data_intake.py:473`.
- **Suggested source**: sprint-2 cross-repo dependency-manifest graph (the SDK pin matrix is dependency-analyst's core deliverable).

### Unknown: U-5 — owning models of the additional verticals.id FK edges
- **Question**: which models own the `foreign_key="verticals.id"` references at [C] `_platform.py:72` and `:451`?
- **Why it matters**: completes the inbound FK fan-in set that defines the verticals dimension's coupling surface.
- **Evidence**: FK lines confirmed; owning-class identification deferred (breadth-first discipline).
- **Suggested source**: sprint-2 model-graph resolution within `_platform.py`.

### Unknown: U-6 — autom8y-scheduling verticals: local table or shared store reference?
- **Question**: is scheduling's `foreign_key="verticals.id"` ([scheduling] `models/shared.py:48`) pointing at a LOCAL verticals table or a reference to the shared `autom8y-data` verticals dimension?
- **Why it matters**: distinguishes an independent materialization from a cross-service FK into the canonical store.
- **Evidence**: FK string confirmed; cross-DB resolution not in topology scope.
- **Suggested source**: sprint-2 cross-repo dependency / schema-ownership trace.

### Unknown: U-7 — `VALID_VALUES_SOURCES` "mixed" semantics
- **Question**: when is a field's `values_source` `"mixed"` vs `"asana_configured"` (the third frozenset value at [P] `annotations.py:50`)?
- **Why it matters**: the vocab-sync contract must handle every `values_source` mode; `"mixed"` is undocumented in the brief.
- **Evidence**: vertical field is `asana_configured`/`dynamic`; `"mixed"` exists in the enum but its consumers were not traced this pass.
- **Suggested source**: sprint-2 trace of `values_source` consumers in `resolver_schema.py` / `annotations.py`.

---

## Handoff Status

- topology-inventory artifact: **complete** with all required sections (service catalog, tech-stack
  inventory, API surface map, entry-point catalog, structure profiles, six sources, drift, unknowns).
- Every target unit (10 real services + tools + autom8 legacy) scanned and classified IN/OUT with a
  deciding `{path}:{line}`; no unit skipped.
- Confidence ratings on every classification and surface entry.
- API surfaces carry endpoint paths / protocols / interface signatures sufficient for sprint-2
  consumer-matching (account-status REST endpoint, gRPC Create handler, SDK `list_verticals`,
  ads `/policies/verticals/{vertical_key}/override`, junction `/api/v1/asset-verticals`).
- EC-1 cited (MySQL `config.py:217/:222`), NOT re-resolved.
- `/vocabularies/sync` flagged PROPOSED / 0-bindings at both anchors.
- 7 explicit unknowns handed forward; 6 drift findings (D-1..D-6) recorded.

**Acid test:** the dependency-analyst can trace cross-unit relationships from this inventory
(every API surface carries path + protocol + signature) without re-scanning any unit for basic
structure. Rung: **CATALOGED** (never validated/proven).
