# Pattern Gap Analysis: autom8y Ecosystem vs Industry Practice

**Date**: 2026-02-23
**Scope**: 5 architectural gaps, reality-scoped (production patterns only, ≤6mo runway)
**Method**: Technology Scout (5 parallel assessments) → Integration Researcher (codebase fit analysis)
**Foundation**: ARCH-REVIEW-1 (10 documents), ECOSYSTEM-TOPOLOGY-INVENTORY (8 repos)

---

## Executive Summary

Five known architectural gaps were evaluated against proven industry patterns and then mapped against the actual codebase. Of 16 approaches evaluated, **6 received Adopt verdicts** and **1 received Trial**. These 7 items were prioritized by leverage-to-effort ratio and fit within a 40 developer-day budget (excluding one deferred item).

### Verdict Matrix

| Gap | Approach | Verdict | Effort | Leverage/Effort |
|-----|----------|---------|--------|-----------------|
| Pkg Distribution | CI Cache Hardening | **Adopt** | 0.25 days | **3.0** |
| Cache Simplification | Freshness Collapse Spike | **Trial** | 2 days | **2.0** |
| JWT Auth | Dual-Validation Middleware | **Adopt** | 7-10 days | **2.0** |
| Import Side Effects | Explicit Bootstrap + Deferred Resolution | **Adopt** | 8-11 days | **1.5** |
| Shared Database | Schema-per-Service (Phase 0) | **Adopt** | 4-7 days | **1.0** |
| Cache Simplification | Concept Consolidation (31→~25) | **Adopt** | 14-18 days | **1.0** |
| Shared Database | Strangler Fig (full migration) | **Adopt** | 39-68 days | **0.8** (DEFERRED) |

**Total budget-fit items**: P1-P5 = 21.25-30.25 days. P6 conditional on P2 spike result. P7 deferred.

---

## Gap 1: Shared Database (MySQL between autom8y-data + legacy monolith)

### Problem
autom8y-data (SQLAlchemy async/asyncmy) and the legacy monolith (SQLAlchemy sync/pymysql) share a MySQL 8 instance. 119 SQL query files in the legacy monolith access 30+ entity domains. Dual-write risk, no schema boundary, import-time database connection in legacy `sql/session.py`.

### Approaches Evaluated

| Approach | Verdict | Rationale |
|----------|---------|-----------|
| **Strangler Fig (API-mediated)** | Adopt (DEFERRED) | Correct end-state but 39-68 days; 8+ entity domains lack API coverage |
| **Schema-per-Service** | Adopt (Phase 0) | 4-7 days, creates measurable boundaries, zero new infrastructure |
| CDC (Debezium/DMS) | Hold | Infrastructure overhead (Kafka) exceeds team capacity |
| Database View Layer | Hold | Manages symptom, not root cause |
| Read Replica + Write Routing | Hold | Addresses write contention only, not schema coupling |

### Recommended Path
1. **Phase 0** (P5): Schema-per-Service — separate logical schemas, same MySQL instance
2. **Phase 1** (P7, deferred): Strangler Fig for the 10 entities with existing API coverage
3. **Prerequisite**: JWT Dual-Validation (P3) must complete first — legacy needs S2S auth to call autom8y-data

### Hidden Dependency Surfaced
Legacy `sql/session.py` connects to MySQL at **import time** (retry loop at lines 27-40). The strangler fig must replace import-time behavior, not just the query layer.

---

## Gap 2: Cache Abstraction Simplification (31 concepts → target ≤15)

### Problem
31 distinct caching concepts across two cache systems. 4 freshness enums with overlapping semantics (`Freshness`, `FreshnessMode`, `FreshnessClassification`, `FreshnessStatus`). 262 total references (113 source + 149 test).

### Key Finding
**The 31-to-15 target is unrealistic.** ADR-0067's 14-dimension analysis proved 12 of 14 divergences between entity and DataFrame caches are intentional (different data shapes, access patterns, operational requirements). The achievable target is **31→~25** through vocabulary unification.

### Approaches Evaluated

| Approach | Verdict | Rationale |
|----------|---------|-----------|
| **Concept Consolidation** (no tech change) | Adopt | Freshness vocabulary collapse + DataFrameCacheProtocol + shared observability. 31→~25 concepts in 5 weeks |
| **Freshness Collapse Spike** | Trial | 2-day validation of FreshnessIntent/FreshnessState/FreshnessCheck design |
| Unified abstractions (dogpile/aiocache) | Hold | None support S3 backends, Polars DataFrames, or completeness tracking |
| Redis Modules/Valkey | Avoid | SSPL licensing risk; increases operational complexity |
| Sidecar caching | Avoid | Wrong layer — caching is between app and Asana API, not client and app |

### Recommended Path
1. **P2** (2 days): Freshness Collapse Spike — define unified enums with type aliases, validate tests pass
2. **P6** (14-18 days, conditional on P2): Full consolidation — freshness vocabulary, DataFrameCacheProtocol + DI, shared observability, EntryType cleanup

---

## Gap 3: JWT Auth Consolidation (HS256 legacy → RS256 platform)

### Problem
Split trust domains: modern platform uses RS256 JWTs via auth service JWKS; legacy monolith uses independent HS256 with local secret key (`AUTOM8_SECRET_KEY`). The auth service is the single trust root for all modern services but has no authority over the legacy monolith.

### Approaches Evaluated

| Approach | Verdict | Rationale |
|----------|---------|-----------|
| **Dual-Validation Middleware** | Adopt | Pattern already proven in autom8y-asana (`detect_token_type()`). ~200 LOC change in legacy monolith |
| Token Exchange (RFC 8693) | Assess | Only solves outbound calls, not inbound. 2-day spike to evaluate |
| ALB JWT Verification | Hold (Phase 2) | AWS ALB doesn't support HS256; useful as hardening overlay after RS256 migration |
| Big-Bang Cutover | Avoid | High risk for 1921-line main.py with ~80 dependencies |
| OIDC Standard Adoption | Hold | Over-engineered for current needs; auth service already works |

### Critical Security Note
During dual-validation, the **algorithm confusion attack** must be explicitly defended against. Route validation by JWT `kid` header presence (RS256 tokens have `kid`; HS256 tokens do not), never by the `alg` header alone.

### Recommended Path
1. **P3** (7-10 days): Add RS256 path to legacy `app/auth.py` with JWKS client, feature flag, deprecation counter
2. **60-90 day window**: Callers migrate from HS256 to RS256 tokens
3. **Cleanup** (1-2 days): Remove HS256 path, rotate/invalidate secret key

### Hidden Dependency Surfaced
- Legacy auth uses **both SSM and Secrets Manager** for different secrets; JWKS fetch introduces a third config source
- **python-jose is unmaintained** since 2021 — both `autom8y-auth` SDK and legacy `autom8-core` depend on it. Migration should be time-boxed to avoid extended exposure
- Caller inventory for the legacy monolith is unknown — need audit of what sends tokens TO the monolith

---

## Gap 4: Private Python Package Distribution Resilience

### Problem
11 SDKs distributed via single AWS CodeArtifact repository. All builds depend on it. 7 `setup-uv` calls across repos are missing `enable-cache: true`. Every CI run re-downloads all 109 packages. All packages (including standard PyPI) resolve through CodeArtifact's proxy.

### Key Finding
uv's multi-index fallback is **not a true failover**. The `first-index` strategy only falls back on HTTP 404. Connection timeouts and 401/403 are hard failures. Multi-registry provides less resilience than it appears.

### Approaches Evaluated

| Approach | Verdict | Rationale |
|----------|---------|-----------|
| **CI Cache Hardening** | Adopt | 2-3 hours, eliminates ~95% of registry dependency for routine CI |
| Multi-Registry Fallback | Assess | uv's fallback semantics limit actual resilience |
| Git-Based Distribution | Assess | Viable as break-glass procedure, too slow for primary |
| Vendored Wheels | Hold | Maximum resilience but unsustainable maintenance |
| Path Dependencies (subtree) | Hold | Breaks producer/consumer separation |
| Registry Mirroring (devpi) | Avoid | Running infrastructure to protect infrastructure |

### Recommended Path
1. **P1** (0.25 days): Enable `enable-cache: true` + upgrade to `@v4` across 7 workflow sites
2. **Short-term**: Investigate why all 109 packages resolve via CodeArtifact proxy instead of PyPI directly
3. **Short-term**: Write 1-page break-glass runbook for git-based SDK resolution during extended outages

---

## Gap 5: Import-Time Side Effect Elimination

### Problem
`register_all_models()` called at import time from `models/business/__init__.py:66`. 305 import sites across 75 files. 6+ mutable singletons. 20+ deferred imports managing 4 circular dependency chains. 100 `.reset()` calls in 25 test files.

### Approaches Evaluated

| Approach | Verdict | Rationale |
|----------|---------|-----------|
| **Explicit Bootstrap** | Adopt | Django-proven pattern. 8-11 days. Codebase already has building blocks |
| **Deferred Resolution** | Adopt | Complement to bootstrap. `SchemaRegistry._ensure_initialized()` already implements this |
| Import Graph Restructuring | Assess | Correct long-term but not urgent. 2-day assessment after bootstrap |
| DI Container | Hold | Overkill for 4 singletons. Pydantic v2 compatibility issues |
| Entry Point Discovery | Hold | Solves wrong problem; all 16 entities are in same package |
| PEP 562 Lazy Loading | Hold | Treats symptom, not disease. Does not improve test isolation |

### Recommended Path
1. **P4** (8-11 days): Create `bootstrap()` function, wire into 6 Lambda handlers + API lifespan + test conftest. Add `_ensure_bootstrapped()` guard to `ProjectTypeRegistry` (following existing `SchemaRegistry` pattern). Remove import-time call from `__init__.py:66`.
2. **Follow-up**: Assess which of the 20+ deferred imports are still needed post-bootstrap

---

## Prioritized Execution Plan (40 Developer-Day Budget)

| Week | Priority | Item | Days | Cumulative | Deliverable |
|------|----------|------|------|------------|-------------|
| 1 | **P1** | CI Cache Hardening | 0.25 | 0.25 | 7 workflows upgraded, all builds use cache |
| 1 | **P2** | Freshness Collapse Spike | 2 | 2.25 | Unified freshness enums validated or rejected |
| 2-3 | **P3** | JWT Dual-Validation | 7-10 | 9.25-12.25 | Legacy accepts RS256, 90-day caller migration window opens |
| 3-5 | **P4** | Explicit Bootstrap | 8-11 | 17.25-23.25 | Import-time side effects eliminated, Lambda cold starts improved |
| 5-6 | **P5** | Schema-per-Service | 4-7 | 21.25-30.25 | Logical DB boundaries established |
| 6-10 | **P6** | Cache Consolidation | 14-18 | 35.25-48.25 | 31→~25 caching concepts (conditional on P2 spike) |
| — | **P7** | Strangler Fig | 39-68 | — | **DEFERRED** — exceeds budget, 8+ API gaps |

**Rollback points**: Each priority is independently reversible. Failure at any stage does not block subsequent priorities (except P6 depends on P2 result, and P7 depends on P3 + P5).

---

## Deferred Items (with triggers)

| Item | Trigger | Effort |
|------|---------|--------|
| Strangler Fig full migration | Budget allocation for 8-14 weeks; 8 API gaps filled in autom8y-data | 39-68 days |
| python-jose → PyJWT migration | Security advisory or python-jose removal from PyPI | 3-5 days |
| uv multi-registry fallback | >2 CodeArtifact outages in 90 days | 2-3 days |
| Import graph restructuring | Post-bootstrap assessment reveals remaining circular deps | 2-3 days |
| Cache concept target ≤15 | Future architectural review post-consolidation | TBD |

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| This document | `.claude/wip/q1_arch/PATTERN-GAP-ANALYSIS.md` |
| Integration Fit Analysis | `.claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md` |
| Ecosystem Topology Inventory | `.claude/wip/q1_arch/ECOSYSTEM-TOPOLOGY-INVENTORY.md` |
| Scout: Shared DB Decoupling | `docs/rnd/SCOUT-shared-db-decoupling.md` |
| Scout: Cache Simplification | `docs/rnd/SCOUT-cache-abstraction-simplification.md` |
| Scout: JWT Auth Consolidation | `docs/rnd/SCOUT-jwt-auth-consolidation.md` |
| Scout: Package Distribution | `docs/rnd/SCOUT-pkg-distribution-resilience.md` |
| Scout: Import Side Effects | `docs/rnd/SCOUT-import-side-effect-elimination.md` |
