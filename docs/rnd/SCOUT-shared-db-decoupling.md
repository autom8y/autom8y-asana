# SCOUT-shared-db-decoupling

**Date**: 2026-02-23
**Scout**: technology-scout
**Scope**: Shared MySQL 8 database decoupling between autom8y-data and autom8 (legacy monolith)
**Constraint**: Reality-scoped -- production-proven patterns only, max 6-month runway

---

## Executive Summary

The shared MySQL 8 database between `autom8y-data` (async, SQLAlchemy/asyncmy) and `autom8` (sync, SQLAlchemy/pymysql) is a coupling risk documented in the ecosystem topology inventory. Five proven decoupling approaches were evaluated against the constraints of a 2-3 engineer team, Python-async stack, and 6-month runway. **Verdict: Adopt Strangler Fig Pattern (API-mediated) as the primary strategy, with Schema-per-Service as the immediate tactical step.** CDC (Debezium/DMS) is rated Hold -- powerful but infrastructure-heavy for the team size. Database Views and Read Replica routing are rated Hold -- they manage symptoms rather than address root cause.

The key insight: the existing `auth-mysql-sync` Lambda already demonstrates a data projection pattern in this ecosystem. The natural progression is to route legacy MySQL reads through `autom8y-data`'s REST/gRPC API (which already exposes full CRUD for businesses, offers, leads, appointments, payments) rather than introducing new infrastructure. The strangler fig is already partially grown -- the question is how to accelerate it.

---

## Technology Overview

This assessment evaluates five approaches to the same problem: decoupling two services that share MySQL 8 tables.

| Approach | Category | Maturity | License | Backing |
|----------|----------|----------|---------|---------|
| Strangler Fig (API-mediated) | Architecture Pattern | Mature | N/A (pattern) | Fowler, AWS, Microsoft, industry consensus |
| Database View Layer | Database Pattern | Mature | N/A (MySQL native) | MySQL/Oracle |
| Change Data Capture (CDC) | Infrastructure Tool | Growing | Apache 2.0 (Debezium) / Managed (DMS) | Red Hat (Debezium), AWS (DMS) |
| Schema-per-Service | Database Pattern | Mature | N/A (MySQL native) | Industry standard |
| Read Replica + Write Routing | Database Pattern | Mature | N/A (MySQL/RDS native) | AWS RDS |

---

## Approach-by-Approach Evaluation

### 1. Strangler Fig Pattern (API-Mediated)

**Maturity**: Mature
**Core Idea**: Incrementally route legacy direct-DB reads/writes through autom8y-data's API, leaving legacy as passthrough until migration complete.

#### Production Reference Users
- **Shopify**: Refactored 3,000-line Shop "God Object" using Strangler Fig, cutting CI time 60% with zero downtime
- **Allianz**: Used Strangler Fig with Kafka event backbone to migrate from legacy mainframes to cloud microservices
- **AWS**: Documented as a prescriptive guidance pattern for cloud migrations
- **Microsoft**: Documented in Azure Architecture Center patterns

#### Python Ecosystem Fit
- **Excellent**. No new libraries required. `autom8y-data` already exposes REST + gRPC CRUD APIs for all shared entities (businesses, offers, leads, appointments, payments, campaigns, ads, adsets, verticals, addresses)
- `autom8y-core` BaseClient pattern already used by satellite services (pull-payments, reconcile-spend, client-lead-sms)
- S2S JWT auth flow already operational between services
- httpx (async) and requests (sync) both available for client implementation

#### MySQL 8 Applicability
- Not MySQL-specific -- works at application layer. The fact that both services use SQLAlchemy (async and sync variants) is irrelevant to the pattern.

#### Risk Profile (2-3 Engineers)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dual-write inconsistency during transition | Medium | High | Implement writes through API first; reads can tolerate eventual consistency |
| Performance regression (API call vs direct DB) | Low | Medium | autom8y-data is on same VPC/ALB; latency <5ms for internal calls |
| Legacy monolith code churn | Medium | Medium | Thin client wrapper in autom8, minimal code changes per entity migration |
| Auth integration gap (HS256 vs RS256) | Medium | High | Legacy autom8 uses independent HS256 auth; needs S2S token acquisition from auth service |

#### Estimated Time to First Production Value
**2-4 weeks** for the first entity migration (e.g., route legacy business reads through autom8y-data REST API). Incremental thereafter -- each entity ~1-2 weeks.

#### Key Advantage
The infrastructure already exists. autom8y-data already has CRUD endpoints for every shared entity. The work is routing, not building.

---

### 2. Database View Layer / API Gateway Pattern

**Maturity**: Mature
**Core Idea**: Create MySQL views over the canonical tables. Legacy reads through views while modern service owns the underlying tables.

#### Production Reference Users
- **Percona**: Documented MySQL views as a microservices data sharing mechanism
- **Materialize**: Advocates materialized views for cross-service data access
- Common in enterprise Oracle/PostgreSQL environments; less documented for MySQL specifically

#### Python Ecosystem Fit
- Transparent to SQLAlchemy -- views appear as tables. No code changes needed in ORM queries.
- View definitions managed via Alembic migrations in autom8y-data.

#### MySQL 8 Applicability
- MySQL 8 supports updatable views with restrictions (no aggregation, no UNION, single table for updates). This is a significant limitation -- many cross-entity queries will produce non-updatable views.
- MySQL views are not materialized (unlike PostgreSQL). Every view query re-executes the underlying SQL. Performance impact for complex joins.

#### Risk Profile (2-3 Engineers)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Non-updatable views block writes | High | High | Legacy writes still go direct to tables; views only for reads |
| Schema evolution requires view updates | Medium | Medium | Alembic migrations manage view DDL alongside table DDL |
| View performance on complex joins | Medium | Medium | MySQL lacks materialized views; monitor query plans |
| False sense of decoupling (still shared DB) | High | Medium | Views are a stepping stone, not an end state |

#### Estimated Time to First Production Value
**1-2 weeks** for first view-based read isolation.

#### Key Limitation
This manages the symptom (shared table access) without addressing the root cause (shared database instance). Both services still depend on the same MySQL availability. It is a tactical holding pattern, not a strategy.

---

### 3. Change Data Capture (CDC)

**Maturity**: Growing (Debezium 2.5+), Mature (AWS DMS for one-time migration)
**Core Idea**: Stream MySQL binlog changes to keep separate databases in sync. Each service owns its own database, CDC ensures eventual consistency.

#### Sub-Options Evaluated

| Tool | Type | Infrastructure Required | Python Fit |
|------|------|------------------------|------------|
| **Debezium** | Open source, Kafka Connect | Kafka cluster + ZooKeeper/KRaft + Connect workers | Java runtime; Python consumes from Kafka via confluent-kafka or aiokafka |
| **AWS DMS** | Managed service | DMS replication instance | boto3 for management; transparent data flow |
| **Maxwell** | Open source, MySQL-specific | Kafka or Kinesis + Maxwell daemon | Java runtime; Python consumes from stream |
| **python-mysql-replication** | Pure Python library | None (direct binlog reading) | Native Python; production-tested at medium scale |

#### Production Reference Users
- **Debezium**: Used at WePay (Chase), Trivago, Walmart; 45% adoption surge in fintech/IoT in 2025
- **AWS DMS**: Standard AWS migration tool; significant production experience but known sync lag issues
- **Maxwell**: Used at Nord Security for MySQL CDC
- **python-mysql-replication**: "Used in production for critical stuff in some medium internet corporations" per project README; 1500+ changes/sec documented

#### Python Ecosystem Fit
- **Debezium**: Requires Kafka infrastructure. Python consumes via `confluent-kafka` (C extension, production-grade) or `aiokafka` (pure Python async). No direct Python SDK for Debezium itself.
- **AWS DMS**: Managed via `boto3`. CDC data flows through DMS without application code. Good for one-time migration; poor for ongoing sync (documented sync lag issues).
- **python-mysql-replication**: Pure Python (`pip install mysql-replication`). Built on PyMySQL. Parses binlog directly. Lightweight but you own checkpointing, schema evolution, and delivery guarantees.

#### MySQL 8 Applicability
- MySQL 8 has binary logging enabled by default -- prerequisite is met.
- `GTID` mode recommended for Debezium (must verify RDS configuration).
- `binlog_format=ROW` required (standard for RDS MySQL 8).

#### Risk Profile (2-3 Engineers)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Kafka cluster operational burden | High | High | Team has no Kafka experience; MSK adds $200+/mo minimum |
| Schema evolution breaks CDC pipeline | Medium | High | Debezium handles some schema changes; custom code for others |
| Exactly-once delivery complexity | Medium | High | Debezium + Kafka provides at-least-once; idempotent consumers required |
| DMS sync lag for ongoing replication | High | Medium | AWS docs warn DMS is not suited for ongoing real-time CDC |
| Monitoring and alerting overhead | High | Medium | New operational domain for the team |

#### Estimated Time to First Production Value
- **Debezium + Kafka**: 6-8 weeks (includes Kafka setup, connector config, consumer implementation, monitoring)
- **AWS DMS**: 2-4 weeks for one-time migration; unreliable for ongoing sync
- **python-mysql-replication**: 3-4 weeks (direct implementation, but you own all reliability guarantees)

#### Key Limitation
CDC solves the "separate databases" problem but introduces significant infrastructure complexity. For a 2-3 person team, operating a Kafka cluster (or MSK) is a major operational commitment. The ecosystem has no existing Kafka usage to amortize this cost against.

---

### 4. Schema-per-Service

**Maturity**: Mature
**Core Idea**: Same MySQL 8 instance, but each service gets its own schema (database) with explicit cross-schema contracts via `GRANT` permissions.

#### Production Reference Users
- **Percona**: Documented as MySQL microservices pattern
- **AWS**: Listed in Prescriptive Guidance as "shared-database-per-service" pattern
- Common in enterprise environments as pragmatic first step

#### Python Ecosystem Fit
- SQLAlchemy handles schema routing natively via `schema` parameter on `Table`/`MetaData` or connection URL database component
- Alembic supports multi-schema migrations
- asyncmy and pymysql both support schema selection in connection string

#### MySQL 8 Applicability
- Native support. `CREATE DATABASE autom8_data_schema; CREATE DATABASE autom8_legacy_schema;`
- Cross-schema queries work via fully-qualified names (`autom8_data_schema.businesses`)
- User-level `GRANT` restricts each service to its own schema
- MySQL 8 supports cross-schema foreign keys (though not recommended for decoupling)

#### Risk Profile (2-3 Engineers)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data migration between schemas | Medium | High | Migrate one table at a time; dual-write during transition |
| Cross-schema query performance | Low | Low | Same MySQL instance; negligible overhead |
| Single point of failure (shared instance) | Existing | Medium | Same risk as today; not worse |
| False boundary (easy to cross-query) | Medium | Low | Enforce via GRANT permissions; code review |

#### Estimated Time to First Production Value
**1-2 weeks** for first schema separation.

#### Key Advantage
Lowest-effort first step. Creates logical ownership boundaries without new infrastructure. Can be done incrementally -- migrate one table at a time. Does not preclude any future approach (Strangler Fig, CDC, or full database separation).

---

### 5. Read Replica + Write Routing

**Maturity**: Mature
**Core Idea**: Legacy service reads from a MySQL read replica. Modern service owns all writes to the primary. Eliminates write contention.

#### Production Reference Users
- **AWS RDS**: Standard read replica configuration; used by thousands of production systems
- **Shopify**: Historically used read replicas at massive scale
- SQLAlchemy community: `flask-replicated`, SQLAlchemy `get_bind()` routing pattern

#### Python Ecosystem Fit
- SQLAlchemy 2.0 supports `Session.get_bind()` override for read/write routing
- `flask-replicated` extension for Flask (autom8 legacy uses Flask for some endpoints)
- asyncmy and pymysql both support separate connection strings for primary/replica
- AWS RDS Proxy can handle routing transparently

#### MySQL 8 Applicability
- RDS MySQL 8 supports up to 15 read replicas
- Replication lag typically <1 second for standard workloads
- Read replicas are read-only by default -- no accidental writes

#### Risk Profile (2-3 Engineers)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Replication lag causes stale reads | Medium | Medium | Accept eventual consistency for reads; write-after-read patterns need primary |
| Write routing complexity in legacy code | Medium | Medium | Requires code audit of all write paths in autom8 |
| Additional RDS cost | Low | Low | Read replica ~50% of primary instance cost |
| Does not address schema coupling | High | Medium | Both services still share the same schema; only write contention is resolved |

#### Estimated Time to First Production Value
**2-3 weeks** (RDS replica provisioning + connection routing changes).

#### Key Limitation
This only addresses write contention, not schema coupling. Both services still read the same tables. If the primary concern is data ownership and independent schema evolution, read replicas do not help.

---

## Comparison Matrix

| Criteria | Status Quo (Shared DB) | Strangler Fig (API) | Database Views | CDC (Debezium) | Schema-per-Service | Read Replica |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Decoupling Effectiveness** | -- | +++ | + | +++ | ++ | + |
| **Implementation Effort** | None | Medium | Low | High | Low | Medium |
| **New Infrastructure Required** | None | None (APIs exist) | None | Kafka/MSK | None | RDS replica |
| **Operational Overhead** | Low | Low | Low | High | Low | Low-Medium |
| **Team Skill Match** | N/A | High (Python, REST) | Medium (DBA skills) | Low (Kafka, Java) | Medium (DBA skills) | Medium (DBA skills) |
| **Independent Schema Evolution** | No | Yes | Partial | Yes | Partial | No |
| **Write Ownership** | Neither | Clear | Partial | Clear | Clear | Partial |
| **Reversibility** | N/A | High | High | Low | Medium | High |
| **6-Month Runway Fit** | N/A | Yes | Yes | Risky | Yes | Yes |
| **Addresses Root Cause** | No | Yes | No | Yes | Partially | No |
| **Leverages Existing Investment** | N/A | autom8y-data API, S2S auth | Alembic | None | Alembic | RDS |
| **Monthly Cost Delta** | $0 | $0 | $0 | $200-500+ (MSK) | $0 | $50-150 (replica) |

**Scoring**: -- (actively harmful), - (worse), 0 (neutral), + (marginal), ++ (good), +++ (excellent)

---

## Fit Assessment

### Philosophy Alignment

The autom8y ecosystem is already on a strangler fig trajectory. The platform architecture shows:
- `autom8y-data` already owns CRUD for all core business entities via REST + gRPC
- Lambda services (pull-payments, reconcile-spend, client-lead-sms) already access data exclusively through `autom8y-data` REST API with S2S JWT auth
- `auth-mysql-sync` demonstrates a data projection pattern (MySQL -> PostgreSQL)
- The legacy monolith has its own HS256 auth -- a clear trust boundary that will eventually migrate to the platform RS256 auth

The strangler fig is the natural continuation of decisions already made.

### Stack Compatibility

- **autom8y-data**: Already has full CRUD API surface. No changes needed for read routing.
- **autom8 (legacy)**: Needs a thin `DataServiceClient` (using `autom8y-core` BaseClient pattern, which it already depends on). Migration complexity is in the legacy codebase's direct SQL usage (`sql/` directory with SQLAlchemy/PyMySQL sessions).
- **auth-mysql-sync**: May eventually become unnecessary if legacy monolith migrates to platform auth.

### Team Readiness

- Team already builds and operates `autom8y-data` REST API and S2S auth flows
- No new infrastructure skills required for Strangler Fig or Schema-per-Service
- CDC (Debezium) would require learning Kafka operations -- a significant skill gap
- Schema separation is standard DBA work compatible with existing Alembic migration skills

---

## Risk Analysis (Aggregate)

| Risk | Likelihood | Impact | Mitigation | Applies To |
|------|------------|--------|------------|------------|
| Legacy HS256 -> RS256 auth gap | High | High | Implement S2S token acquisition in autom8 monolith as prerequisite | Strangler Fig |
| Dual-write window data inconsistency | Medium | High | Migrate writes first (through API), then reads; minimize dual-write period | Strangler Fig |
| Kafka operational burden on small team | High | High | Avoid CDC approach entirely until team grows or platform needs justify it | CDC |
| Schema migration data loss | Low | Critical | Dry-run migrations on staging; dual-write + validation scripts | Schema-per-Service |
| Performance regression from API indirection | Low | Medium | Same VPC; benchmark first entity migration; circuit breaker in client | Strangler Fig |
| Legacy monolith unknown write paths | Medium | Medium | Audit `autom8/sql/` directory before starting migration | All |

---

## Recommendation

### Primary Verdict: **Adopt** -- Strangler Fig Pattern (API-Mediated)

**Rationale**:
1. **The infrastructure already exists.** autom8y-data has REST + gRPC CRUD for all shared entities. S2S JWT auth is operational. The BaseClient pattern is proven across 3+ services.
2. **Incremental and reversible.** Each entity can be migrated independently. If a migration causes issues, the direct-DB fallback remains available.
3. **Zero new infrastructure cost.** No Kafka, no new databases, no replicas. The work is routing changes in the legacy monolith.
4. **Natural trajectory.** The ecosystem is already moving this direction. This assessment accelerates an existing architectural intention.
5. **Team skill match.** Python REST clients, S2S auth, and httpx/requests are daily tools for this team.

### Tactical Step: **Adopt** -- Schema-per-Service as Phase 0

Before beginning API routing, separate the MySQL schemas:
1. Create `autom8_data` and `autom8_legacy` schemas on the shared MySQL 8 instance
2. Migrate table ownership: tables consumed primarily by autom8y-data move to `autom8_data` schema
3. Grant cross-schema read access temporarily (with expiration date)
4. This creates visible ownership boundaries and makes the strangler fig migration measurable

### Hold: CDC (Debezium/DMS/Maxwell)

**Rationale**: CDC is the right tool when you need real-time database synchronization across separate database instances at scale. For a 2-3 person team with no Kafka infrastructure and no existing CDC operational experience, the infrastructure overhead exceeds the benefit. Revisit when: (a) the legacy monolith is decommissioned and you need real-time sync between autom8y-data and a new service, or (b) the team grows to 5+ engineers with dedicated infrastructure support.

### Hold: Database Views and Read Replicas

**Rationale**: Both manage symptoms without addressing root cause. Views create a false sense of decoupling (still shared DB, still shared availability). Read replicas only address write contention, which is not the primary problem (the primary problem is schema coupling and independent evolution). Neither moves toward the goal of service independence.

---

## Recommended Execution Sequence

```
Phase 0 (Weeks 1-2):    Schema-per-Service
                         Create logical schema boundaries on shared MySQL 8
                         Establish ownership via GRANT permissions

Phase 1 (Weeks 3-4):    Auth Bridge
                         Implement S2S token acquisition in autom8 legacy
                         (prerequisite for all API-mediated routing)

Phase 2 (Weeks 5-8):    First Entity Migration (Strangler Fig)
                         Route legacy reads for one entity (e.g., businesses)
                         through autom8y-data REST API
                         Validate performance, correctness, error handling

Phase 3 (Weeks 9-16):   Entity-by-Entity Migration
                         Migrate remaining entities: offers, leads,
                         appointments, payments, campaigns, ads
                         ~1-2 weeks per entity

Phase 4 (Weeks 17-20):  Write Migration
                         Route legacy writes through autom8y-data API
                         Remove direct MySQL write access from autom8

Phase 5 (Weeks 21-24):  Cleanup
                         Remove cross-schema GRANTs
                         Remove legacy schema (or archive)
                         Decommission auth-mysql-sync Lambda
                         (if legacy auth migrated to platform auth)
```

**Total runway: ~24 weeks (6 months)**, fitting the constraint exactly.

---

## The Acid Test

*"If we don't adopt this now, will we regret it in two years?"*

**Yes.** The shared database is a ticking clock. Every new feature in autom8y-data that requires a schema change (new column, index, migration) carries risk of breaking the legacy monolith. Every legacy monolith write that bypasses autom8y-data's validation creates data integrity risk. The coupling will only get worse as the ecosystem grows (autom8y-ads integration, new satellite services). The cost of decoupling grows with time; the cost of delay compounds.

The existing API surface in autom8y-data means the marginal effort to begin is low. The risk of not starting is high.

---

## Next Steps

1. **Audit legacy write paths**: Enumerate all direct MySQL write operations in `autom8/sql/` to scope Phase 4
2. **Validate Unknown**: Confirm whether autom8y-data and autom8 access the same MySQL schemas or already have partial separation (see Ecosystem Topology Inventory, Unknown: "Shared MySQL database boundaries")
3. **Route to Integration Researcher**: Hand off this assessment for dependency mapping of the autom8 -> autom8y-data API migration (entity-by-entity integration map)

---

## Sources

- [Strangler Fig Pattern - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html)
- [Strangler Fig Pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)
- [Refactoring Legacy Code with the Strangler Fig Pattern - Shopify Engineering](https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern)
- [Replacing Legacy Systems with Data Streaming: Strangler Fig Approach - Kai Waehner](https://www.kai-waehner.de/blog/2025/03/27/replacing-legacy-systems-one-step-at-a-time-with-data-streaming-the-strangler-fig-approach/)
- [MySQL CDC with Debezium in Production - Materialize](https://materialize.com/guides/mysql-cdc/)
- [Debezium for CDC in Production: Pain Points and Limitations - Estuary](https://estuary.dev/blog/debezium-cdc-pain-points/)
- [Real-time Data Replication with Debezium and Python](https://debezium.io/blog/2025/02/01/real-time-data-replication-with-debezium-and-python/)
- [AWS DMS: Challenges and Solutions Guide 2025](https://www.integrate.io/blog/aws-dms-challenges-solutions-guide/)
- [I Used AWS DMS to Migrate a Live Production Database](https://aws.plainenglish.io/i-used-aws-dms-to-migrate-a-live-production-database-heres-the-part-nobody-explains-clearly-b4b854310f1d)
- [python-mysql-replication - GitHub](https://github.com/julien-duponchelle/python-mysql-replication)
- [Change Data Capture using Maxwell for MySQL - Nord Security](https://nordsecurity.com/blog/decoupling-maxwell-cdc-mysql)
- [MySQL in Microservices Environments - Percona](https://www.percona.com/blog/mysql-in-microservices-environments/)
- [Database-per-service Pattern - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-data-persistence/database-per-service.html)
- [Shared Database per Service - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-data-persistence/shared-database.html)
- [Shared Database Anti-Pattern](https://microservices.io/patterns/data/shared-database.html)
- [Simplify Microservices with Shared Database and Materialized Views - Materialize](https://materialize.com/blog/simplify-microservices-shared-database-materialized-views/)
- [SQLAlchemy 2.0 Horizontal Sharding Extension](https://docs.sqlalchemy.org/en/20/orm/extensions/horizontal_shard.html)
- [SQLAlchemy Read Replica Routing Pattern](https://gist.github.com/jasonwalkeryung/5133383d66782461cdc3b4607ae35d98)
- [Asynchronous SQLAlchemy and Multiple Databases - Makimo](https://makimo.com/blog/asynchronous-sqlalchemy-and-multiple-databases/)

---

## Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| Tech Assessment | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-shared-db-decoupling.md` | Pending read-back |
| Ecosystem Topology (input) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ECOSYSTEM-TOPOLOGY-INVENTORY.md` | Read |
| Architecture Topology (input) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ARCH-REVIEW-1-TOPOLOGY.md` | Read |
