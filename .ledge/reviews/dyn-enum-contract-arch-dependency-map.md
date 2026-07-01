---
type: review  # arch dependency-map (sprint-2 coupling/integration artifact)
artifact_subtype: arch-dependency-map
initiative: dyn-enum-contract
rite: arch
sprint: 2-of-5 (topology -> DEPENDENCY -> structure -> remediation -> adversary)
generated_by: dependency-analyst
created: 2026-06-30
status: draft  # WIP-uncommitted per operator no-auto-commit discipline
rung: mapped  # G-RUNG: dependency-map reaches "MAPPED" only — coupling SURFACES mapped, anti-patterns NOT classified (sprint-3)
producer_truth_anchor: "autom8y-asana origin/main (ca28251d) — NOT cwd chore/bump-core-4.6.0 (f4f924d2, 25 behind, OFF-ANCHOR)"
consumer_truth_anchor: "autom8y-data HEAD (92d3606d, branch main)"
legacy_source_anchor: "autom8 monorepo main (5c749c11) — NON-CANONICAL frozen-legacy"
ec1_status: "CONFIRMED = MySQL (authoritative receipt taken; NOT re-litigated)"
ghalt_verdict: "NO new structural RED; consumer-store branch proceeds (U-3 DuckDB-write NEGATIVE)"
upstream: topology-cartographer (sprint-1)
downstream: structure-evaluator (sprint-3)
---

# Dependency Map — dyn-enum-contract sync seam

Cross-repo dependency, coupling, and integration topology for the `dyn-enum-contract` telos:
*one typed, additive, FK-safe sync contract carrying an Asana enum-option-set change into
`autom8y-data.verticals`*. Every edge carries a LIVE `{path}:{line}` receipt (G-PROVE) and a
confidence rating. **Rung discipline (G-RUNG): this artifact MAPS coupling surfaces — it does
NOT classify anti-patterns, score architectural health, or judge coupling acceptability
(sprint-3 / structure-evaluator territory).**

Anchor conventions (re-confirmed live this pass; SHAs verified):
- **[P]** producer `autom8y-asana` @ `origin/main` (ca28251d) — `git -C … grep -n … origin/main`
- **[C]** consumer `autom8y-data` @ `HEAD` (92d3606d) — `git -C … grep -n … HEAD`
- **[L]** legacy `autom8` @ `main` (5c749c11), root `/Users/tomtenuta/Code/autom8`
- **[SDK]** SDK host `autom8y` @ HEAD (abec0b08), `sdks/python/autom8y-core`
- Downstream Python consumers (ads/sms/scheduling) read at on-disk HEAD (each on `chore/bump-core-4.6.0`)

Confidence rubric: **High** = explicit declaration (manifest/import/typed contract/FK string);
**Medium** = pattern-match + structural corroboration; **Low** = grep text-match only.

---

## 1 · Cross-Repo Edge Graph

### 1.0 Directed graph (ASCII)

```
                         Asana SaaS (enum_options; field GID 1182735041547604)
                                    │  [source-of-record READ]
                                    v
   ┌──────────────────────────── autom8y-asana [P] ───────────────────────────┐
   │  custom_field.py:113 enum_options  ──>  annotations.py:50 values_source   │
   │  door {hardcoded, asana_configured, mixed}  (vertical = asana_configured) │
   │                                    │                                      │
   │              _push_to_data_service (gid_push.py:163)                      │
   │              flag GID_PUSH_ENABLED :62/:95 · base-URL AUTOM8Y_DATA_URL:144│
   │            ┌──────────────┴───────────────┐                              │
   │   path A :338                       path B :563                          │
   │   /gid-mappings/sync :339           /account-status/sync :564            │
   │   "vertical": parts[2] :123         "vertical": str(...) :490 (UNTYPED)  │
   └───────────────────┬───────────────────────┬──────────────────────────────┘
                       │  HTTP POST (REST, async, flag-gated)
                       v                        v
   ┌──────────────────────── autom8y-data [C]  (CONSUMER / STORE) ─────────────┐
   │  models_comparison.py:62  vertical: str   (UNTYPED consumer side)         │
   │  [[ PROPOSED /api/v1/vocabularies/sync — 0 bindings — design-under-val ]] │
   │                                    │  upsert (shape-B: ON DUPLICATE KEY)  │
   │                                    v                                      │
   │            ┌──────── verticals dimension (_platform.py:131/:142) ───────┐ │
   │            │ key UNIQUE :146  ·  name UNIQUE :147  (dual-unique surface) │ │
   │            │ sole writer: VerticalService.create services/vertical.py:212│ │
   │            └───┬───────────────────────────────────────────────────┬────┘ │
   │   inbound FK fan-in (≥7, §2)                       DuckDB analytics READ   │
   │   Campaign/AssetVertical/Offer/Business/Question/Payment   enrichment_views │
   │                                                            .py:152 (mysql_scanner)
   └────────────────────────────────────────────────────────────────────────────┘
         ^             ^                ^                         ^
         │ SDK GET     │ FK (shared-   │ local VerticalNormalizer│ local model fields
         │ /verticals  │ schema)       │ (own canonical list)    │ vertical_id/key
   autom8y-core[SDK]  autom8y-scheduling   autom8y-ads            autom8y-sms
   (typed)            (shared-DB)          (ad-hoc)               (ad-hoc)

   autom8y-admin-ui / autom8y-fe-skeleton ──> /api/v1/asset-verticals (JUNCTION CRUD only; EXCLUDED)
   autom8 [L] contente_api vertical sources ──// ISOLATED (no import edge into canonical tree)
```

### 1.a Primary seam — asana → data (producer → consumer/store)

| Attribute | Finding | Receipt | Confidence |
|-----------|---------|---------|------------|
| Conduit (single helper) | `_push_to_data_service` | [P] `services/gid_push.py:163` | High |
| Call path A (gid-mappings) | targets `/api/v1/gid-mappings/sync` | [P] `gid_push.py:338` → endpoint `:339` | High |
| Call path B (account-status) | targets `/api/v1/account-status/sync` | [P] `gid_push.py:563` → endpoint `:564` | High |
| Base-URL resolver | `AUTOM8Y_DATA_URL` env | [P] `gid_push.py:144` | High |
| Producer-push feature flag | `GID_PUSH_ENABLED` (gate read `:95`) | [P] `gid_push.py:62` | High |
| Transport | synchronous HTTP **POST**, async, flag-gated | [P] `gid_push.py:163/:564` | High |
| Direction | **unidirectional** producer → consumer | derived from above | High |
| **Untyped `str` leak (producer)** | `"vertical": str(vertical)` (path B payload) | [P] `gid_push.py:490` | High |
| Untyped parse (path A) | `"vertical": parts[2]` (from `pv1:{phone}:{vertical}`) | [P] `gid_push.py:123` | High |
| **Untyped `str` leak (consumer)** | `vertical: str = Field(...)` | [C] `api/models_comparison.py:62` | High |
| Contract under validation | `/api/v1/vocabularies/sync` — **0 bindings** at both anchors | topology §4 (re-confirmed) | High |
| Nearest extant precedent | typed account-status sync (req/resp) | [C] `data_service_models/_account_status_sync.py:70/:113`; route `routes/account_status.py:4` | High |

**Typed-vs-untyped verdict:** the vertical option-set crosses the CURRENT asana→data seam as an
**untyped `str`** with no enum-option-set validation on either end ([P]`:490` → [C]`:62`). The
proposed `/vocabularies/sync` is the design that would replace this with a typed contract; it
correctly has zero bindings today (design-under-validation, not a live edge).

### 1.a.bis Source-of-record edge (Asana → producer)

| Attribute | Finding | Receipt | Confidence |
|-----------|---------|---------|------------|
| Live option-set read | `enum_options: list[CustomFieldEnumOption]` | [P] `models/custom_field.py:113` (class `:19/:45`) | High |
| Asana field identity | Vertical custom-field **GID 1182735041547604** | [P] `dataframes/annotations.py:225/:255/:284/:463` | High |
| `values_source` door (authority enum) | `frozenset({"hardcoded","asana_configured","mixed"})` | [P] `annotations.py:50` | High |
| Vertical field mode | `valid_values:"dynamic"` + `values_source:"asana_configured"` | [P] `annotations.py:222/:232` (also :252/:262, :281/:291, :460/:470) | High |
| Resolver-schema surfacing | `values_source: str \| None = Field(` / population | [P] `api/routes/resolver_schema.py:366` / `:473` | High |

### 1.b The four downstream vocab consumers

Each consumes the **same vertical vocabulary via a DIFFERENT mechanism** — four distinct conduits,
four distinct shapes. (Fragmentation evidence assembled for sprint-3 per G-DEFER; NOT collapsed
to SHIP, NOT counted toward N≥3.)

| # | Consumer | Vocabulary shape consumed | Conduit | Typed? | Receipt | Confidence |
|---|----------|---------------------------|---------|--------|---------|------------|
| 1 | **autom8y** (autom8y-core SDK) | `VerticalsListResponse` (typed list) | **SDK-pin + REST GET** `/api/v1/verticals` | **TYPED** | [SDK] `clients/data_intake.py:473` `def list_verticals(self) -> VerticalsListResponse`; URL `:497`; `model_validate` `:515`; data-side route `verticals_crud` [C]`routes/__init__.py:17/:70` | High |
| 2 | **autom8y-ads** | `vertical_key` (str), validated vs **ads-LOCAL** canonical list | **local materialization** + own REST | ad-hoc | [ads] `api/creative_performance.py:90` `VerticalNormalizer.normalize(body.vertical_key)` (import `:24` `from autom8_ads.intelligence.vertical_scoring`); route `api/policy_override.py:42` `/policies/verticals/{vertical_key}/override` | High |
| 3 | **autom8y-sms** | `default_vertical_key: str` + `vertical_id: int` (local fields) | **local model** (denormalized) | ad-hoc | [sms] `models/conversation.py:169` (`:92` vertical_id:int, `:166` default_vertical_id:int) | High |
| 4 | **autom8y-scheduling** | `vertical_id: int` FK → verticals.id | **FK (shared-schema)** | FK (no local table) | [sched] `models/shared.py:48` `foreign_key="verticals.id"` on `Business.default_vertical_id` `:46` | High |

**Conduit divergence (mapped, not judged):** ONE typed conduit (SDK, #1), TWO ad-hoc local
materializations (#2 ads owns its own normalizer; #3 sms carries denormalized fields), ONE
shared-schema FK (#4). The proposed `/vocabularies/sync` would be the **1st typed vocab-contract
consumer**; these four bind by SCATTERED ad-hoc coupling, NOT the contract-class under validation.

### 1.c The two border consumers (DEFER-1 denominator: EXCLUDE)

| Consumer | Binding | Receipt | Adjudication | Confidence |
|----------|---------|---------|--------------|------------|
| autom8y-admin-ui | `/api/v1/asset-verticals` junction CRUD | [admin-ui] `src/lib/api/_generated/openapi.d.ts:785` (ops `list/create/search_junction_rows`) | **EXCLUDE** — binds JUNCTION, not vocabulary | Medium |
| autom8y-fe-skeleton | `/api/v1/asset-verticals` junction CRUD | [fe-skeleton] `src/lib/api/_generated/openapi.d.ts:857` (ops `*_junction_rows_*`) | **EXCLUDE** — binds JUNCTION, not vocabulary | Medium |

Data-side route confirms the junction is a SEPARATE surface (and is mutable/deletable, unlike the
permanent verticals dimension): [C] `routes/asset_verticals_crud.py:55` prefix `/api/v1/asset-verticals`
with `POST/GET/DELETE/search` (`:4-8`). The operation IDs (`*_junction_rows_*`) and the DELETE verb
confirm these consumers CRUD the asset↔vertical M:N link rows, not the vertical option-set.
**DEFER-1 denominator: the 2 border consumers are RECORDED and EXCLUDED.**

### 1.d The six sources → seam

| # | Source | Receipt | Canonical? | Edge to seam | Confidence |
|---|--------|---------|------------|--------------|------------|
| 1 | legacy `Vertical(Enum)` | [L] `apis/contente_api/models/vertical/main.py:19` | **NON-CANONICAL / frozen** | **NONE** (isolated, §3) | High |
| 2 | legacy `VERTICAL_NAMES` | [L] `…/main.py:261` | **NON-CANONICAL / frozen** | **NONE** (isolated) | High |
| 3 | legacy `db_verticals()` | [L] `…/main.py:12` | **NON-CANONICAL / frozen** | **NONE** (isolated) | High |
| 4 | Asana live `enum_options` | [P] `custom_field.py:113` (GID 1182735041547604) | **AUTHORITATIVE** source-of-record | source-of-record → producer | High |
| 5 | asana `SEMANTIC_ANNOTATIONS` | [P] `annotations.py:222/:232` | Asana-deferring (vertical=`asana_configured`/`dynamic`) | producer-internal door | High |
| 6 | data `verticals` | [C] `_platform.py:131/:142` | **CANONICAL store / upsert TARGET** | terminal sink | High |

---

## 2 · FK-Parent Coupling — the `verticals` dimension fan-in (≥7 edges)

`verticals` ([C] `_platform.py:131` `class Vertical(SQLModel, table=True)`, `:142`
`__tablename__="verticals"`) is a **pure FK-parent reference dimension** AND the lead-enrichment
join hub. **U-5 RESOLVED** (the two previously-unresolved owners identified inline below).

### 2.a Inbound FK / reference edges (owning model · key-type · join role)

| # | Owning model (table) | Edge | Key-type | Role | Receipt | Confidence |
|---|----------------------|------|----------|------|---------|------------|
| E1 | **Campaign** (`campaigns`) | `vertical_id → verticals.id` | int FK | **PRIMARY** lead-enrichment dimension | [C] `_advertising.py:80` | High |
| E2 | **AssetVertical** (`asset_verticals`) | `vertical_id → verticals.id` | int FK, **composite PK** `(asset_id, vertical_id)` | junction (M:N asset↔vertical) | [C] `_advertising.py:322/:326` | High |
| E3 | **Offer** (`offers`) | `vertical_key → verticals.key` (col `category`) | **STRING FK** | category linkage (the only key-based FK) | [C] `_platform.py:162` | High |
| E4 | **Business** (`chiropractors`) — *U-5 :72 owner* | `default_vertical_id → verticals.id` | int FK | **FALLBACK** organic-lead enrichment | [C] `_platform.py:72` (field `:70`, class `:9`) | High |
| E5 | **Question** (`questions`) — *U-5 :451 owner* | `vertical_id → verticals.id` | int FK, nullable (`# 5 NULLs`) | reference (questions↔vertical) | [C] `_platform.py:451` (class `:439`) | High |
| E6 | **Payment** (`payments`) | `vertical_id ⇢ verticals.id` | **str GENERATED, SOFT ref (NOT declared FK)** | analytics 1-hop (derived from `billing_reason`) | [C] `_platform.py:419` (`Computed("SUBSTRING_INDEX(billing_reason,'•',1)")` `:424`; INV-003 `:417`) | High |
| E7 | **Business** (cross-repo, `autom8y-scheduling`) | `default_vertical_id → verticals.id` | int FK | shared-schema FK (no local verticals table — U-6) | [sched] `models/shared.py:48` | High |

**Count: 7 model-level edges** (6 consumer-internal E1–E6 + 1 cross-repo E7), of which **5 are
DB-declared FKs** (E1–E5), **1 is a soft/generated reference** (E6, Payment), **1 is a cross-repo
shared-schema FK** (E7, scheduling).

### 2.b Repository-layer join consumers (read-coupling on the dimension)

| Edge | Join | Receipt | Confidence |
|------|------|---------|------------|
| J1 | `Campaign.vertical_id == Vertical.vertical_id` (PRIMARY) | [C] `core/repositories/dimension_enrichment.py:144` | High |
| J2 | `Business.default_vertical_id == Vertical.vertical_id` (FALLBACK) | [C] `dimension_enrichment.py:166` | High |
| J3 | `Vertical.vertical_id == Campaign.vertical_id` (reverse) | [C] `dimension_enrichment.py:328` | High |
| J4 | `Vertical.vertical_id == Business.default_vertical_id` (reverse) | [C] `dimension_enrichment.py:340` | High |

Blast-radius note (mapped, for sprint-3): the lead-dimension enrichment joins the vertical dimension
on BOTH the PRIMARY (campaign) and FALLBACK (business/organic) paths — a mis-keyed/orphaned vertical
row touches both lead-enrichment routes. (Magnitude only; acceptability = sprint-3.)

### 2.c Dual-unique coupling surface — rename → UPDATE-collision (MAP only)

| Constraint | Receipt | Role | Confidence |
|------------|---------|------|------------|
| `vertical_key` **UNIQUE** | [C] `_platform.py:146` `Field(unique=True, name="key")` | the **upsert key** (portable, stable) | High |
| `vertical_name` **UNIQUE** | [C] `_platform.py:147` `Field(unique=True, name="name")` | second unique → an UPDATE that renames a vertical can collide on `name` | High |

**Mapped surface (NOT classified as a hazard — sprint-3):** the dimension carries TWO unique
constraints. An additive upsert keyed on `vertical_key` that also writes `vertical_name` has a
structural collision surface on the `name` unique index when a rename occurs (two keys racing toward
one name, or a name already held by another key). This is recorded as a **coupling surface**; whether
it constitutes an anti-pattern / hazard is the structure-evaluator's call.

### 2.d Parent-side write/permanence surface (sole writer)

| Surface | Receipt | Confidence |
|---------|---------|------------|
| Sole canonical writer | [C] `services/vertical.py:212` `self._session.add(vertical)` (in `create()` `:149`) | High |
| Permanence invariant (no delete) | [C] `services/vertical.py:9` "No Delete operation (verticals are permanent)"; proto `proto/autom8/data/v1/__init__.py:667` | High |
| gRPC create handler (no delete handler) | [C] `grpc/handlers/vertical.py:128` `create_vertical(...)` | High |
| REST CRUD (list/get/get_by_key/create — no delete) | [C] `routes/__init__.py:17` | High |
| GLOBAL-entity scoping | [C] `routes/factory.py:354` "GLOBAL entities (verticals, …)" | Medium |

---

## 3 · Monorepo / Cross-Repo Import-Isolation (legacy autom8 contente_api)

**CONFIRMED ISOLATED — no leak edge.** Neither the producer nor the consumer canonical tree imports
the legacy `autom8` contente_api vertical sources (#1/#2/#3).

| Tree | Probe | Result | Confidence |
|------|-------|--------|------------|
| asana [P] @ origin/main | `git grep -nE "contente_api\|from autom8\.\|import autom8\b" origin/main -- src/**` | **0 hits** (empty) | High |
| data [C] @ HEAD | same probe `-- src/**` | **0 hits** (empty) | High |
| legacy [L] sources exist & frozen | [L] `…/vertical/main.py:12/:19/:261` present (e.g. `:305` "D-6: close the VERTICAL_NAMES gap (7 members)") | live-but-isolated | High |

The legacy enum / name-map / `db_verticals()` reader remain a self-contained vertical materialization
inside `autom8` with **zero inbound import edges from the canonical seam**. Frozen-legacy isolation
holds; sources #1–#3 are NON-CANONICAL and structurally severed from the dyn-enum-contract path.

---

## 4 · EC-1 Authoritative Receipt — MySQL (CONFIRMED, not re-litigated)

EC-1 was SETTLED upstream (= MySQL). This station takes the **authoritative receipt** and CONFIRMS
by direct inspection; it does NOT re-resolve and does NOT design the upsert.

| Receipt | Marker | Confidence |
|---------|--------|------------|
| [C] `core/config.py:217` | docstring `MySQL URL … mysql+asyncmy://user:pass@host:port/database` | High |
| [C] `core/config.py:222` | `return self.mysql_url.replace("mysql://", "mysql+asyncmy://")` | High |
| [C] `api/routes/read_only_deps.py:75` | `url = f"mysql+asyncmy://{db.username}:…"` | High |
| [C] `api/routes/read_only_deps.py:77` | `_read_only_engine = create_async_engine(` | High |
| [C] `api/routes/deps.py:129` | `_async_engine = create_async_engine(` (`:130` `settings.db.async_mysql_url`) | High |
| [C] `services/base.py:387` | `("mysql+asyncmy://", "mysql+aiomysql://", "mysql://")` | High |
| [C] `alembic/env.py:88` | `url = f"mysql+asyncmy://{username}:…"` (`:144` strips to `mysql://` for render) | High |

### Consumer-store SHAPE-B implication (recorded, NOT designed)

- **Upsert primitive = `INSERT … ON DUPLICATE KEY UPDATE`** — and this is **NOT hypothetical**: the
  consumer ALREADY uses this exact idiom as its idempotent-write pattern at
  [C] `api/services/forwarding_binding_store.py:155/:218/:252/:315` ("MySQL authoritative write via
  INSERT … ON DUPLICATE KEY UPDATE"). A `conflict_resolution: 'insert'|'upsert'` enum also exists in
  the data_service_models ([C] `_asset.py:365`, `_lead.py:308`, `_payment.py:321`). **Live exemplar present.**
- **Lock primitive = `GET_LOCK() / RELEASE_LOCK()`** — **PROSPECTIVE**: grep for `GET_LOCK|RELEASE_LOCK|advisory`
  across `src/autom8_data/**` @ HEAD returns **0 hits**. The named-lock is the recommended MySQL
  serialization primitive but is not yet used in the consumer; 10x-dev would introduce it.
- **NOT** PostgreSQL `ON CONFLICT(key) DO UPDATE` / `pg_advisory_xact_lock` — grep for `ON CONFLICT|pg_advisory`
  returns **0 hits** in the consumer tree. The PROTO PostgreSQL canary-1 is 10x-dev's to re-derive for MySQL.

**Confirm, do not design:** shape-B is the upsert SHAPE the consumer store dictates (MySQL). The
upsert IMPLEMENTATION belongs to 10x-dev beyond the seam.

---

## 5 · Coupling-Hotspot Scoring

**Methodology.** Coupling-context three-check (bounded-context / intentionality / directionality)
applied BEFORE severity input; package metrics (Ca afferent, Ce efferent, I = Ce/(Ce+Ca)) computed
structurally. **U-1 (FK row counts) has no DB creds in env → UV-P; scored on structural fan-in/fan-out
ONLY, row-count weighting DEFERRED. No counts fabricated.** Scores are MAGNITUDE inputs for sprint-3 —
NOT health judgments.

### 5.a Hub: the `verticals` dimension (consumer-internal)

| Metric | Value | Basis |
|--------|-------|-------|
| Afferent coupling (Ca) | **HIGH** | 6 inbound model edges (E1–E6) + 4 repo joins (J1–J4) + multi-join analytics surface (§6) + 1 cross-repo FK (E7) |
| Efferent coupling (Ce) | **~0** | `verticals` declares NO outbound FK — pure leaf parent / reference dimension |
| Instability I = Ce/(Ce+Ca) | **≈ 0.0** | maximally STABLE (correct posture for a shared reference dimension) |

**Coupling-context three-check on the high-Ca hub:**
1. **Bounded context** — `verticals` is an explicitly GLOBAL platform reference dimension
   ([C]`factory.py:354`); the fan-in is domain-cohesive (the lead-enrichment hub). Coupling reflects
   natural domain shape, NOT incidental sprawl.
2. **Intentionality** — DESIGNED: explicit FK declarations, typed SDK contract, stated permanence
   invariant ([C]`services/vertical.py:9`). Intentional reference-data sharing.
3. **Directionality** — UNIDIRECTIONAL inbound (everything → verticals; verticals → nothing).
   **No cycle.** ADP (Acyclic Dependencies Principle) not violated by the hub.

→ Per the coupling-context gate, the high afferent coupling on `verticals` is **intentional,
bounded-context-aligned, unidirectional** — MAPPED as a stable reference hub (I≈0), **NOT pre-flagged
as a hotspot**. (Final severity disposition is sprint-3's.)

### 5.b Edge-level coupling scores (connected pairs)

| Pair / edge | Coupling type (data>stamp>control>temporal) | Direction | Surface | Ctx-check | MAPPED magnitude |
|-------------|---------------------------------------------|-----------|---------|-----------|------------------|
| asana → data (vocab seam, current) | **data** (single `str` field) + **temporal** (flag-gated push) | unidir P→C | 1 untyped field (`vertical`) | incidental (untyped, no contract) | LOW surface / fragmented type-safety |
| autom8y-core SDK → data (`/verticals`) | **data** (typed list) | unidir consumer→store | typed `VerticalsListResponse` | designed, unidir | MED (typed, the "good" conduit) |
| ads → vocabulary (local normalizer) | **data** (vertical_key str) | self-local (no runtime read of data) | own canonical list | incidental (duplicated vocab) | MED-fragmentation |
| sms → vocabulary (local fields) | **stamp** (id+key carried on conversation) | self-local | 2 denormalized fields | incidental (duplicated shape) | MED-fragmentation |
| scheduling → data verticals (FK) | **data** (FK on id) | unidir → shared store | shared-schema FK | designed but shared-DB | HIGH (shared-DB tightest) |
| data.verticals ← FK children (E1–E7) | **data** (FK on id/key) | unidir inbound | 5 declared FK + 1 soft + 1 x-repo | intentional hub | HIGH Ca / STABLE (I≈0) |
| analytics → verticals (DuckDB read) | **data** (cross-engine read join) | unidir read | multi-LEFT-JOIN | intentional read | MED (read-only, §6) |

### 5.c Fragmentation hotspot (assembled for sprint-3; G-DEFER honored)

The SAME vertical vocabulary is consumed via **four divergent mechanisms** (§1.b): typed SDK (#1),
ads-local normalizer (#2), sms-local fields (#3), scheduling shared-schema FK (#4). This scattered
ad-hoc coupling is the **blast-radius multiplier** the proposed `/vocabularies/sync` contract would
unify — data would be the **1st** typed vocab-contract consumer. **Per G-DEFER: this is fragmentation
EVIDENCE, NOT a DEFER→SHIP collapse; the 4 are NOT contract-class bindings and do NOT count toward
N≥3. DEFER-1 stays watch-registered, escalate-only.**

---

## 6 · Deep-Dive Data-Flow Diagram (asana → data vocab seam, end-to-end)

```
[Asana SaaS]
  enum_options (custom_field.py:113) · field GID 1182735041547604
        │  source-of-record READ (Asana SDK asana>=5.0.3)
        v
[autom8y-asana — producer]
  values_source door (annotations.py:50) {hardcoded, asana_configured, mixed}
        │   vertical field RESOLVES to: valid_values="dynamic", values_source="asana_configured"
        │   (resolver_schema.py:366/:473 surfaces values_source)
        v
  push conduit _push_to_data_service (gid_push.py:163)
        │   flag GID_PUSH_ENABLED (:62/:95) · base-URL AUTOM8Y_DATA_URL (:144)
        │   TODAY: emits "vertical": str(...) UNTYPED (:490) on path B (/account-status/sync :564)
        v
  ╔══ PROPOSED /api/v1/vocabularies/sync ══╗   (0 bindings — design-under-validation)
  ║   mirrors the typed account-status/sync ║   precedent: _account_status_sync.py:70/:113
  ╚════════════════════════════════════════╝   data route: routes/account_status.py:4
        │   HTTP POST (REST, async)
        v
[autom8y-data — consumer / store]
  consumer-side vertical: str (models_comparison.py:62)  ← UNTYPED today
        │   upsert (shape-B MySQL): INSERT … ON DUPLICATE KEY UPDATE
        │   via VerticalService.create (services/vertical.py:149/:212) — sole writer, create-only
        v
  verticals dimension (_platform.py:131/:142) · key UNIQUE :146 · name UNIQUE :147
        │
        ├── FAN-OUT to FK children (transactional MySQL):
        │     Campaign:80 (PRIMARY) · AssetVertical:326 (junction) · Offer:162 (str FK)
        │     Business:72 (FALLBACK) · Question:451 · Payment:419 (soft/generated)
        │     + cross-repo scheduling shared.py:48
        │
        └── DuckDB analytics READ (mysql_scanner cross-engine, READ-ONLY):
              enrichment_views.py:152/:216/:218/:274/:512/:514/:585/:691 (LEFT JOIN verticals)
              canonical_paths.py:232/:246/:266 (JoinStep campaign/chiropractors → verticals)
              → propagates vertical key DOWNWARD onto fact tables (leads/calls/messages/payments),
                NEVER writes the verticals dimension (see §7 U-3)
```

**Transform summary:** the vocabulary travels Asana-typed (enum_options) → producer door
(`asana_configured`/`dynamic`) → **flattened to untyped `str`** at the current push → (proposed:
re-typed at `/vocabularies/sync`) → MySQL upsert into `verticals` → re-expanded into FK joins
(int `id` for most; str `key` for Offer/category) → read-denormalized by DuckDB analytics back onto
fact rows. The single type-fidelity loss point today is the producer→consumer `str` flattening
([P]`:490` → [C]`:62`).

---

## 7 · Unknown Triage (U-1 … U-7)

| U | Status | Resolution / blocked-fact | Receipt |
|---|--------|---------------------------|---------|
| **U-1** FK row counts | **UV-P** | No DB creds in env → cannot run `SELECT COUNT(*)`. Structural fan-in mapped (§2); row-count weighting deferred. **No counts fabricated.** | `[UV-P: asset_verticals + inbound-FK row counts | METHOD: bash-probe (live MySQL SELECT COUNT) | REASON: no DB creds in env at this altitude; operator/dependency-analyst-with-creds is the attester]` |
| **U-2** resolver-flag completeness | **RESOLVED (partial)** | No resolver-level / dynamic-vocab env-flag exists; the ONLY producer-push gate is `GID_PUSH_ENABLED`. `values_source` is a DATA door, not a feature flag → dynamic-vocab resolution is NOT independently gateable from the push. | [P] `gid_push.py:62`; `annotations.py:50`; `resolver_schema.py` (475 lines, no env-gate) |
| **U-3** DuckDB **WRITE**-consumer? (FORK-3 watch) | **RESOLVED — NEGATIVE** | NO analytics write to the canonical `verticals` dimension. The analytics writes are: (a) test-fixture DuckDB seeding `fixtures/builder.py:1670`; (b) derived TEMP tables `_lead/_call/_msg_verticals` `initialization.py:259/:288/:308`; (c) denormalization UPDATEs onto OTHER fact tables `UPDATE leads/calls/messages/payments SET vertical=…` `initialization.py:270/:296/:316/:324`. **Sole verticals-dimension writer = VerticalService.create** [C]`services/vertical.py:212`. Exclusivity HOLDS. | [C] `analytics/initialization.py:259-324`, `analytics/fixtures/builder.py:1670`, `services/vertical.py:212` |
| **U-4** SDK pin matrix | **RESOLVED** | Uniform: all 4 Python consumers pin `autom8y-core>=4.2.0,<5.0.0` from index `autom8y` (CodeArtifact); SDK self-version 4.6.0. No declared-pin skew at anchors (cwd-branch bumps asana to 4.6.0 but origin/main = the range). **Residual:** resolved lock versions (per-repo `uv.lock`) not diffed — range is uniform. | [P]`pyproject.toml:26`, [ads]`:21`, [sms]`:26`, [sched]`:31`; [SDK]`sdks/python/autom8y-core/pyproject.toml:7` |
| **U-5** owning models of `_platform.py:72`/`:451` | **RESOLVED** | `:72` = **Business.default_vertical_id** (table `chiropractors`, class `:9`) — the FALLBACK FK that `dimension_enrichment.py:166` joins (same logical edge, two layers). `:451` = **Question.vertical_id** (table `questions`, class `:439`). | [C] `_platform.py:9/:70/:72`, `:439/:451` |
| **U-6** scheduling local-vs-shared | **RESOLVED** | Scheduling defines `Business`/`chiropractors` (`shared.py:13/:21`) + `Lead`/`leads` (`:82/:90`) with FK `verticals.id` (`:48`) but **NO local `verticals` table** (grep empty) → it is a **shared-schema consumer** of the verticals dimension, not an independent materialization. (Whether the bound MySQL is literally data's store vs a replica is U-6-residual; the no-local-materialization fact is settled.) | [sched] `models/shared.py:48`; grep `class Vertical\|__tablename__="verticals"` → 0 |
| **U-7** "mixed" values_source semantics | **RESOLVED (partial)** | `"mixed"` appears ONLY at the frozenset definition `annotations.py:50` — zero dispatch/consumer logic in the producer annotation/resolver surface. The vertical field is `"asana_configured"`, so **"mixed" is OFF the vertical path** (vertical-seam impact: NONE). General semantics undefined in code. | [P] `annotations.py:50` (sole occurrence); `[UV-P: when values_source="mixed" applies vs "asana_configured" | METHOD: file-read of mixed-consumers | REASON: zero dispatch logic exists in traced producer surface; semantics are undefined-in-code, not blocking the vertical seam]` |

### Cross-rite observations (noted as unknowns for remediation-planner routing)

- The untyped `str` seam ([P]`:490`→[C]`:62`) is a type-safety surface that may interest a quality
  lens; recorded here as a coupling fact, routed onward (not classified).
- ads/sms maintaining LOCAL vertical vocabularies (own normalizer / denormalized fields) is a
  vocabulary-drift surface across the fleet; recorded as fragmentation evidence (§5.c).

---

## 8 · Integration Pattern Catalog

| Channel | Pattern | Sync/Async | Receipt | Confidence |
|---------|---------|------------|---------|------------|
| asana → data (current push) | **Synchronous REST POST**, flag-gated, snapshot-style | sync HTTP, async runtime | [P] `gid_push.py:163/:564` | High |
| asana → data (proposed vocab) | Synchronous REST POST (`/vocabularies/sync`) — **0 bindings** | n/a (proposed) | topology §4 | High |
| SDK → data (`/verticals`) | **Synchronous REST GET**, typed, cacheable | sync | [SDK] `data_intake.py:497/:515`; [C] `verticals_crud` | High |
| data dual transport | **REST + gRPC** (Create/Get-by-key/List, NO Delete) | sync | [C] `grpc/handlers/vertical.py:128`; proto `:667` | High |
| scheduling ↔ data verticals | **Shared database / shared-schema** (FK, no local table) | n/a (DB) | [sched] `shared.py:48` (U-6) | Medium |
| ads → vocabulary | **Local materialization** (own `VerticalNormalizer`) + own REST | sync | [ads] `creative_performance.py:24/:90` | High |
| sms → vocabulary | **Local model** (denormalized fields) | n/a | [sms] `conversation.py:169` | High |
| admin-ui / fe-skeleton → data | **Synchronous REST** (generated OpenAPI client) — junction CRUD only | sync | `openapi.d.ts:785/:857` | Medium |
| analytics → verticals | **Cross-engine READ** (DuckDB `mysql_scanner` → MySQL) | sync read | [C] `enrichment_views.py:152`; Dockerfile `mysql_scanner.duckdb_extension` | High |
| autom8 legacy → canonical seam | **NONE — isolated** (no import edge) | n/a | §3 (grep 0) | High |

---

## 9 · Shared Model Registry

| Model / type / schema | Where it appears | Shared-via | Status | Confidence |
|-----------------------|------------------|------------|--------|------------|
| `verticals` dimension (id/key/name) | [C] `_platform.py:131` (CANONICAL store) | — (the source) | **canonical** | High |
| `VerticalsListResponse` | [SDK] `data_intake.py:42/:473`; consumed by autom8y | **autom8y-core SDK** (typed) | **shared via library** | High |
| `vertical_key` (str business term) | [C]`:146/:162`; [P]`:490`; [ads]`vertical_key`; [sms]`:169` | scattered (no shared lib for the key str) | **duplicated / divergent** | High |
| `vertical_id` (int FK) | [C] E1/E2/E4/E5; [sched]`:48`; [sms]`:92/:166` | FK string convention | **duplicated FK convention** | High |
| `VerticalNormalizer` (canonical list) | [ads] `intelligence/vertical_scoring` | ads-LOCAL only | **diverged (ads owns a parallel vocab)** | High |
| `values_source` enum {hardcoded, asana_configured, mixed} | [P] `annotations.py:50` | producer-local | **producer-only authority enum** | High |
| account-status sync req/resp (precedent shape) | [C] `_account_status_sync.py:70/:113` | the contract `/vocabularies/sync` would MIRROR | **precedent (typed)** | High |
| legacy `Vertical(Enum)` / `VERTICAL_NAMES` | [L] `main.py:19/:261` | autom8-local | **diverged / frozen (isolated)** | High |

---

## 10 · G-HALT Verdict (FORK-3 watch)

**NO new structural RED surfaced. Consumer-store branch proceeds.**

Three RED-watch conditions checked:
1. **2nd verticals WRITE-consumer (U-3 DuckDB-write)?** → **NO.** Sole canonical writer is
   `VerticalService.create` ([C]`services/vertical.py:212`); all analytics writes target fixtures /
   temp tables / OTHER fact columns, never the `verticals` dimension. Additive-upsert exclusivity HOLDS.
2. **Legacy import leak?** → **NO.** asana and data canonical trees both grep-empty for
   `contente_api`/`autom8` imports (§3). Frozen-legacy isolation holds.
3. **An FK that breaks additive-upsert exclusivity?** → **NO.** All 7 fan-in edges (E1–E7) are
   INBOUND consumers of `verticals.id`/`.key`; none writes the parent. The dual-unique (key+name)
   collision surface (§2.c) is MAPPED as a coupling surface for sprint-3 classification — it is not a
   write-path conflict and does not break exclusivity at the mapping rung.

---

## 11 · Handoff Status

| Exit criterion | Status |
|----------------|--------|
| 1. Cross-repo edge graph (seam + 4 vocab + 2 border + 6 sources) | **RESOLVED** (§1) |
| 2. FK-parent coupling (≥7 edges, owners, dual-unique) | **RESOLVED** — 7 edges, U-5 owners identified (§2) |
| 3. Monorepo import-isolation (legacy contente_api) | **RESOLVED** — isolated, no leak (§3) |
| 4. EC-1 authoritative receipt + shape-B implication | **RESOLVED** — MySQL confirmed; ON DUPLICATE KEY UPDATE live-exemplified; GET_LOCK prospective (§4) |
| 5. Coupling-hotspot scoring (Ca/Ce/I; context-checked) | **RESOLVED** — structural; U-1 counts UV-P (§5) |
| 6. Deep-dive data-flow diagram (end-to-end) | **RESOLVED** (§6) |
| 7. Unknown triage U-1…U-7 | **RESOLVED** 5 (U-2/3/4/5/6) · **partial** 2 (U-2,U-7) · **UV-P** carried: U-1 (counts), U-7 ("mixed" semantics) (§7) |

**Acid-test line:** *Can the structure-evaluator assess boundary alignment + anti-patterns from
THIS dependency-map + the topology-inventory, WITHOUT independently re-tracing any cross-repo edge?*
→ **YES.** Every cross-repo communication channel carries a classified integration pattern (§8) and a
coupling score (§5); every FK edge carries owning model + key-type + join role (§2); the seam, the 4
vocab conduits, the 2 border bindings, and the 6 sources each carry a LIVE `{path}:{line}` + confidence.

**G-HALT verdict line:** **NO new structural RED; consumer-store branch proceeds.** (U-3 DuckDB-write
NEGATIVE; legacy isolation holds; no FK breaks additive-upsert exclusivity.)

**Rung:** MAPPED (coupling surfaces mapped; anti-pattern classification is sprint-3). **Status:** draft
(WIP-uncommitted; no auto-commit, dirty tree not staged).
