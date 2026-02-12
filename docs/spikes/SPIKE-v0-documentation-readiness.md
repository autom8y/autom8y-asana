# SPIKE: v0 Documentation Readiness

**Date**: 2026-02-12
**Timebox**: 1 session
**Status**: Complete

## Question

What documentation gaps remain for v0 dogfooding, and what's the priority order for closing them?

## Decision This Informs

Scope and sequencing of the next docs sprint to achieve v0 dogfooding readiness.

---

## 1. Stakeholder Interview Summary

### Audience & Context
- **Dogfooders**: Mixed internal engineers + external partner developers
- **Usage pattern**: Both REST API integrators (S2S JWT) and Python SDK consumers equally
- **Deployment**: Central service — dogfooders consume a deployed instance, no infra docs needed
- **Timeline**: 1–2 weeks to close blocking gaps
- **Quality bar**: Functional with rough edges OK (80/20) — covers happy paths, devs ask for edge cases

### Pain Points (Recurring Questions)
1. **Query patterns**: "How do I query for X?" / "What filters are supported?" — query API is the primary read path
2. **Environment/config setup**: "What env vars do I need?" — config surface is large (~70 variables)

### Scope Exclusions
- No deployment/infrastructure documentation (central service)
- No Asana API fundamentals (assume familiarity)
- Python SDK only — no other language bindings

### Feedback Mechanism
- Direct to stakeholder (you triage and file issues based on conversations)

---

## 2. Current State

### What Exists (commit 579e634)

| Category | Count | Status |
|----------|-------|--------|
| Getting Started | 3 docs | Complete |
| Topical Guides | 21 docs | Complete |
| SDK Reference | 8 module docs | Complete |
| API Reference | 2 endpoint docs + OpenAPI | 2 of 10 planned |
| Examples | 10 runnable scripts | Complete |
| Runbooks | 7 + README | Complete |
| Reference Data | 20+ REF-* docs + Glossary | Complete |
| INDEX.md | 1 navigation hub | Complete |

**IA Spec planned 10 endpoint docs. Only 2 delivered**: `entity-write.md`, `resolver.md`.

### Actual API Surface (Verified from Source)

| Router | Prefix | Endpoints | Auth | Doc Status |
|--------|--------|-----------|------|------------|
| query | /v1/query | 2 | S2S JWT | **Missing** |
| query_v2 | /v1/query | 2 | S2S JWT | **Missing** |
| tasks | /api/v1/tasks | 14 | PAT/JWT | **Missing** |
| projects | /api/v1/projects | 8 | PAT/JWT | **Missing** |
| sections | /api/v1/sections | 6 | PAT/JWT | **Missing** |
| dataframes | /api/v1/dataframes | 2 | PAT/JWT | **Missing** |
| admin | /v1/admin | 1 | S2S JWT | **Missing** |
| webhooks | /api/v1/webhooks | 1 | Token | **Missing** |
| health | /health | 3 | None | **Missing** |
| users | /api/v1/users | 3 | PAT/JWT | **Missing** |
| workspaces | /api/v1/workspaces | 2 | PAT/JWT | **Missing** |
| entity_write | /api/v1/entity | 1 | S2S JWT | Done |
| resolver | /v1/resolve | 1 | S2S JWT | Done |

**Total: 13 routers, 46 endpoints, 2 documented.**

---

## 3. Gap Inventory with Priority Scores

Scoring: **Impact** (1–5, how many v0 users need it) × **Urgency** (1–5, blocks first usage?) = **Score**. Effort estimated in content-brief units.

### P0 — Blocks v0 Dogfooding

| # | Gap | Impact | Urgency | Score | Effort | Notes |
|---|-----|--------|---------|-------|--------|-------|
| G-01 | **Query endpoint reference** (query + query_v2) | 5 | 5 | 25 | L | Primary read path. 4 endpoints: legacy query, rows, rows-v2, aggregate. Full PredicateNode docs, JoinSpec, AggSpec. Directly addresses "query patterns" pain point. |
| G-02 | **Tasks endpoint reference** | 5 | 5 | 25 | XL | 14 endpoints (CRUD + subtasks + tags + section + assignee + project membership). Core interaction surface for SDK and API users. |
| G-03 | **Environment variable reference** | 5 | 5 | 25 | M | ~70 env vars across 12 prefixes. Directly addresses "what env vars do I need?" pain point. Stakeholder-confirmed blocker. |

### P1 — Important for Productive Dogfooding

| # | Gap | Impact | Urgency | Score | Effort | Notes |
|---|-----|--------|---------|-------|--------|-------|
| G-04 | **Projects endpoint reference** | 4 | 3 | 12 | M | 8 endpoints. Needed for workspace management workflows. |
| G-05 | **Dataframes endpoint reference** | 4 | 3 | 12 | S | 2 endpoints. Key for data export/analysis workflows. |
| G-06 | **Sections endpoint reference** | 3 | 3 | 9 | M | 6 endpoints. Supporting resource for task organization. |
| G-07 | **Health endpoint reference** | 3 | 3 | 9 | S | 3 endpoints. Needed by operators integrating health probes. |

### P2 — Nice to Have for v0

| # | Gap | Impact | Urgency | Score | Effort | Notes |
|---|-----|--------|---------|-------|--------|-------|
| G-08 | **Users endpoint reference** | 2 | 2 | 4 | S | 3 endpoints. Lookup operations. |
| G-09 | **Workspaces endpoint reference** | 2 | 2 | 4 | S | 2 endpoints. Rarely called directly. |
| G-10 | **Webhooks endpoint reference** | 2 | 2 | 4 | S | 1 endpoint. Specialized integration. |
| G-11 | **Admin endpoint reference** | 2 | 2 | 4 | S | 1 endpoint. Internal operations only. |

### Deferred — Out of Scope for v0

| # | Gap | Reason |
|---|-----|--------|
| D-01 | Migration guides (S3→Redis, legacy SDK→current) | No active migration in progress |
| D-02 | Deployment/infrastructure docs | Central service; dogfooders don't deploy |
| D-03 | Lambda handler docs (cache_warmer, etc.) | Internal ops, not consumer-facing |
| D-04 | Integration testing guide for consumers | Can follow examples; ask for edge cases |
| D-05 | Changelog / release notes | v0 is first release; no prior versions to diff |
| D-06 | Developer onboarding checklist | Guides + env var ref cover this |
| D-07 | Error handling cookbook | Guides + patterns.md sufficient for 80/20 |

---

## 4. Recommended Execution Plan

### Effort Key
- **S** = Small (1 content brief, ~30 min write time)
- **M** = Medium (1 content brief, ~1 hr write time)
- **L** = Large (1 content brief, ~2 hr write time, complex models/examples)
- **XL** = Extra Large (may split into 2 briefs, ~3 hr write time)

### Phase 1: P0 Blockers (Days 1–3)

Execute in parallel where possible:

| Batch | Items | Effort | Parallelizable |
|-------|-------|--------|----------------|
| 1A | G-01: Query endpoint reference | L | Yes |
| 1B | G-02: Tasks endpoint reference | XL | Yes |
| 1C | G-03: Env var reference | M | Yes |

**Gate**: All 3 complete before proceeding. These unblock first v0 dogfooders.

### Phase 2: P1 Polish (Days 4–7)

| Batch | Items | Effort | Format |
|-------|-------|--------|--------|
| 2A | G-04: Projects endpoint ref | M | Full reference |
| 2B | G-05: Dataframes endpoint ref | S | Full reference |
| 2C | G-06: Sections endpoint ref | M | Lightweight summary |
| 2D | G-07: Health endpoint ref | S | Lightweight summary |

**Gate**: P1 complete = "v0 docs complete" milestone.

### Phase 3: P2 Backfill (Post-launch, as feedback warrants)

| Items | Format | Trigger |
|-------|--------|---------|
| G-08 through G-11 | Lightweight summaries | Dogfooder requests |

---

## 5. Content Briefs for New Docs

### CB-NEW-01: Query Endpoint Reference (`api-reference/endpoints/query.md`)

**Audience**: API integrators using S2S JWT
**Scope**:
- 4 endpoints across query.py and query_v2.py
- `POST /v1/query/{entity_type}` (deprecated, with sunset date)
- `POST /v1/query/{entity_type}/rows` (v1 and v2 implementations)
- `POST /v1/query/{entity_type}/aggregate` (v2 only)
- Full `PredicateNode` tree documentation (Comparison, AndGroup, OrGroup, NotGroup)
- `JoinSpec` cross-entity join documentation
- `AggSpec` aggregation specification (sum, count, mean, min, max, count_distinct)
- `RowsResponse` and `AggregateResponse` schemas with meta fields (freshness, query_ms, staleness_ratio)
- Error codes: QueryTooComplexError (400), UnknownFieldError/InvalidOperatorError/CoercionError (422), CacheNotWarmError (503)
- Migration note: v1 → v2 differences

**Template**: Match entity-write.md format (path params, request/response bodies, examples, error codes)

### CB-NEW-02: Tasks Endpoint Reference (`api-reference/endpoints/tasks.md`)

**Audience**: SDK consumers and API integrators
**Scope**:
- 14 endpoints: CRUD (5) + subtasks (1) + dependents (1) + duplicate (1) + tags (2) + section (1) + assignee (1) + project membership (2)
- Dual-mode auth: JWT (bot PAT) and PAT (pass-through)
- Request models: CreateTaskRequest, UpdateTaskRequest, DuplicateTaskRequest, AddTagRequest, MoveSectionRequest, SetAssigneeRequest, AddToProjectRequest
- Standard response envelope with pagination (SuccessResponse)
- Error handling via ServiceError → get_status_for_error()

**Template**: Match entity-write.md format. Group endpoints by category (CRUD, Related, Membership).

### CB-NEW-03: Environment Variable Reference (`reference/env-vars.md`)

**Audience**: All dogfooders (SDK and API consumers)
**Scope**:
- ~70 environment variables organized by prefix/category
- Categories: Core Asana (5), Cache (17), S3 Backend (4), Redis Backend (6), Pacing (6), S3 Retry/CB (9), Webhooks (2), Events (3), Data Service (3), Workflow Features (1), DataFrame (3), AWS (4), API Server (2), CloudWatch (2), Lambda (1), Dynamic Projects (pattern)
- For each: name, type, default, required/optional, description
- "Quick start" section: minimal env vars needed for first API call
- "Full reference" section: complete table grouped by category

**Template**: New format — table-based reference with quick-start callout box.

### CB-NEW-04: Projects Endpoint Reference (`api-reference/endpoints/projects.md`)

**Audience**: SDK consumers and API integrators
**Scope**:
- 8 endpoints: CRUD (5) + sections listing (1) + member management (2)
- Bearer token auth (dual-mode)
- Request models for create, update, add/remove members

**Template**: Match entity-write.md format.

### CB-NEW-05: Dataframes Endpoint Reference (`api-reference/endpoints/dataframes.md`)

**Audience**: Data analysis workflows
**Scope**:
- 2 endpoints: project dataframe, section dataframe
- JSON and Polars output formats
- Bearer token auth

**Template**: Lightweight — path params, query params, response format, one example each.

### CB-NEW-06: Sections Endpoint Reference (`api-reference/endpoints/sections.md`)

**Audience**: Task organization workflows
**Scope**: 6 endpoints (CRUD + add task + reorder)
**Template**: Lightweight summary with endpoint table and key request/response schemas.

### CB-NEW-07: Health Endpoint Reference (`api-reference/endpoints/health.md`)

**Audience**: Operators, monitoring integrations
**Scope**: 3 endpoints (liveness, readiness, S2S check)
**Template**: Lightweight — response codes and when each returns 503 vs 200.

---

## 6. Exit Criteria: "v0 Docs Complete"

v0 documentation readiness is achieved when ALL of:

- [ ] G-01: Query endpoint reference published
- [ ] G-02: Tasks endpoint reference published
- [ ] G-03: Environment variable reference published
- [ ] G-04: Projects endpoint reference published
- [ ] G-05: Dataframes endpoint reference published
- [ ] G-06: Sections endpoint reference published (lightweight)
- [ ] G-07: Health endpoint reference published (lightweight)
- [ ] INDEX.md updated with links to new docs
- [ ] Existing guides cross-link to new endpoint refs where relevant

**Stretch (not blocking)**:
- [ ] G-08 through G-11 (users, workspaces, webhooks, admin) — backfill post-launch

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| query_v2 router overlaps with query router on same prefix | Confusing docs | Document both with clear "v1 (deprecated) vs v2 (preferred)" callouts |
| Env var reference goes stale quickly | Misleading docs | Generate from settings.py source; add "last verified" date |
| 14-endpoint tasks doc is too long | Poor UX | Split into categories with anchor links; add summary table at top |
| External devs lack S2S JWT setup context | Blocked at auth | Ensure authentication guide covers token provisioning for both PAT and JWT |

---

## Appendix: Endpoint Inventory Detail

### Query Router (query.py) — 2 endpoints
| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/query/{entity_type}` | Deprecated (sunset 2026-06-01) |
| POST | `/v1/query/{entity_type}/rows` | Active |

### Query V2 Router (query_v2.py) — 2 endpoints
| Method | Path | Status |
|--------|------|--------|
| POST | `/v1/query/{entity_type}/rows` | Active (preferred) |
| POST | `/v1/query/{entity_type}/aggregate` | Active |

### Tasks Router — 14 endpoints
| Method | Path | Category |
|--------|------|----------|
| GET | `/api/v1/tasks` | CRUD |
| GET | `/api/v1/tasks/{gid}` | CRUD |
| POST | `/api/v1/tasks` | CRUD |
| PUT | `/api/v1/tasks/{gid}` | CRUD |
| DELETE | `/api/v1/tasks/{gid}` | CRUD |
| GET | `/api/v1/tasks/{gid}/subtasks` | Related |
| GET | `/api/v1/tasks/{gid}/dependents` | Related |
| POST | `/api/v1/tasks/{gid}/duplicate` | Related |
| POST | `/api/v1/tasks/{gid}/tags` | Tags |
| DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | Tags |
| POST | `/api/v1/tasks/{gid}/section` | Membership |
| PUT | `/api/v1/tasks/{gid}/assignee` | Membership |
| POST | `/api/v1/tasks/{gid}/projects` | Membership |
| DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | Membership |

### Projects Router — 8 endpoints
| Method | Path |
|--------|------|
| GET | `/api/v1/projects` |
| GET | `/api/v1/projects/{gid}` |
| POST | `/api/v1/projects` |
| PUT | `/api/v1/projects/{gid}` |
| DELETE | `/api/v1/projects/{gid}` |
| GET | `/api/v1/projects/{gid}/sections` |
| POST | `/api/v1/projects/{gid}/members` |
| DELETE | `/api/v1/projects/{gid}/members` |

### Sections Router — 6 endpoints
| Method | Path |
|--------|------|
| GET | `/api/v1/sections/{gid}` |
| POST | `/api/v1/sections` |
| PUT | `/api/v1/sections/{gid}` |
| DELETE | `/api/v1/sections/{gid}` |
| POST | `/api/v1/sections/{gid}/tasks` |
| POST | `/api/v1/sections/{gid}/reorder` |

### Dataframes Router — 2 endpoints
| Method | Path |
|--------|------|
| GET | `/api/v1/dataframes/project/{gid}` |
| GET | `/api/v1/dataframes/section/{gid}` |

### Health Router — 3 endpoints
| Method | Path |
|--------|------|
| GET | `/health` |
| GET | `/health/ready` |
| GET | `/health/s2s` |

### Remaining (P2)
- **Admin**: 1 endpoint (`POST /v1/admin/cache/refresh`)
- **Users**: 3 endpoints (`GET /api/v1/users/me`, `GET /api/v1/users/{gid}`, `GET /api/v1/users`)
- **Workspaces**: 2 endpoints (`GET /api/v1/workspaces`, `GET /api/v1/workspaces/{gid}`)
- **Webhooks**: 1 endpoint (`POST /api/v1/webhooks/inbound`)
