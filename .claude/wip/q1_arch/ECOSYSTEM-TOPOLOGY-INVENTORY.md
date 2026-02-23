# Ecosystem Topology Inventory

**Date**: 2026-02-23
**Scope**: Full autom8y platform ecosystem (8 repos, 11 SDKs, 6+ services)
**Analysis Unit Type**: Multi-repo ecosystem
**Analyst**: topology-cartographer

---

## 1. Service Catalog

### 1.1 autom8y (Platform Workspace Monorepo)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8y` |
| **Classification** | Platform monorepo (workspace orchestrator + SDK host + service host + IaC) |
| **Confidence** | High -- explicit `pyproject.toml` workspace config, `services.yaml` manifest |
| **Package Manager** | uv (workspace mode) |
| **Python Version** | >=3.11 |
| **Build Backend** | N/A (workspace root is `package = false`) |
| **Contains** | 11 SDK packages, 8 services (6 platform-native + 2 infrastructure-only), Terraform IaC, CI/CD workflows |

**Workspace Members**:
- **SDKs** (in `sdks/python/autom8y-*/`): autom8y-auth, autom8y-cache, autom8y-claude, autom8y-config, autom8y-core, autom8y-http, autom8y-log, autom8y-meta, autom8y-slack, autom8y-stripe, autom8y-telemetry
- **Services** (in `services/`): auth, auth-mysql-sync, pull-payments, reconcile-spend, slack-alert, sms-performance-report
- **Service Template**: `services/_template` (scaffold for new services)

**Infrastructure Components**:
- Docker Compose: PostgreSQL 15, MySQL 8, Redis 7, LocalStack (S3 + Secrets Manager)
- Terraform: per-service directories under `terraform/services/`, platform stack, modules
- CI/CD: GitHub Actions workflows in `.github/`
- `services.yaml`: declarative service manifest (schema v1) -- single source of truth for all CI/deploy routing

---

### 1.2 autom8y-asana (Asana SDK + API Service)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8y-asana` |
| **Classification** | API service + SDK (satellite service) |
| **Confidence** | High -- extensive prior analysis (ARCH-REVIEW-1), explicit build manifests |
| **Package Manager** | uv |
| **Python Version** | >=3.11 |
| **Build Backend** | hatchling |
| **Deployment** | ECS Fargate (API server via uvicorn) + Lambda (cache warming) -- dual-mode single Docker image |
| **Archetype** | `ecs-fargate-hybrid` |

**Prior Analysis Reference**: See `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ARCH-REVIEW-1-INDEX.md` for comprehensive single-repo analysis (~111K LOC, 383 Python files, 27 packages).

**Key Characteristics**:
- Async-first Python SDK mediating Asana REST API
- FastAPI API with dual auth (S2S JWT + PAT)
- Entity modeling: 17 entity types in 4 categories
- Multi-tier caching: Redis (hot) + S3 (cold) for entities; Memory LRU + S3 Parquet for DataFrames
- Query engine: Composable predicate AST with Polars DataFrames
- Webhook inbound endpoint for Asana event processing
- DataServiceClient for cross-service calls to autom8y-data

---

### 1.3 autom8y-data (Data Platform Service)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8y-data` |
| **Classification** | API service + analytics engine (satellite service) |
| **Confidence** | High -- explicit build manifests, rich API surface, database migrations |
| **Package Manager** | uv |
| **Python Version** | >=3.11 (builds targeting 3.12) |
| **Build Backend** | hatchling |
| **Deployment** | ECS Fargate (API server via uvicorn on port 8000) |
| **Archetype** | `ecs-fargate-stateless` (per services.yaml; though it uses MySQL + Redis + DuckDB) |
| **Database** | MySQL (via asyncmy for async, SQLAlchemy/SQLModel ORM), DuckDB (analytics), Redis (L2 cache) |

**Description**: 4-layer database platform for the autom8 ecosystem. Serves as the central data store and analytics engine. Provides REST API, gRPC API, CLI interface, and an analytics/insights engine.

**Protocols**:
- **REST API**: FastAPI on port 8000 (primary)
- **gRPC**: grpclib on port 50051 (dual-protocol, same process)
- **CLI**: Typer CLI via `autom8` command entry point

**Key Modules**:
- `api/` -- FastAPI application factory, routes, auth middleware
- `analytics/` -- AnalyticsEngine, insights, dimensions, metrics, query execution
- `grpc/` -- gRPC server with CRUD handlers (Lead, Address, Business, Appointment, Payment, Vertical, Health)
- `services/` -- Business logic services with MySQL CRUD
- `cli/` -- Typer CLI entry point
- `core/` -- Configuration, logging, infrastructure
- `clients/` -- Client libraries for external service communication
- `proto/` -- Protocol Buffer definitions (buf-managed)

---

### 1.4 autom8y-ads (Ad Lifecycle Management Service)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8y-ads` |
| **Classification** | API service (satellite service) |
| **Confidence** | High -- explicit build manifests, FastAPI app factory |
| **Package Manager** | uv |
| **Python Version** | >=3.11 (builds targeting 3.12) |
| **Build Backend** | hatchling |
| **Deployment** | ECS Fargate (API server via uvicorn on port 8000) |
| **Archetype** | `ecs-fargate-stateless` |
| **External APIs** | Meta (Facebook) Ads API via autom8y-meta SDK |

**Description**: Ad lifecycle management service. Handles ad campaign launching (campaign + adset + creative + ad hierarchy creation) on Meta/Facebook. Currently in MVP phase with stub clients for Asana and Data services.

**Key Modules**:
- `api/` -- FastAPI routes (health, launch)
- `clients/` -- Stub clients for asana and data services
- `launch/` -- Launch orchestration, idempotency cache
- `lifecycle/` -- Budget, campaign lock/match/search, strategies
- `platforms/` -- Platform-specific adapters (Meta)
- `routing/` -- Account routing
- `models/` -- Domain models

---

### 1.5 autom8-core (Legacy Shared Library)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8-core` |
| **Classification** | Shared library (legacy, pre-platform-SDK era) |
| **Confidence** | High -- Poetry build, explicit library packaging |
| **Package Manager** | Poetry |
| **Python Version** | >=3.10,<4.0 |
| **Build Backend** | poetry-core |
| **Distribution** | PyPI/CodeArtifact wheel |

**Description**: Original shared core utilities for the autom8 platform, predating the autom8y SDK family. Provides primitives consumed primarily by the `autom8` legacy monolith. Uses Poetry (not uv), targets Python 3.10+ (older than the >=3.11 standard of modern repos).

**Exports**:
- `autom8_core.audit` -- Base audit utilities
- `autom8_core.auth` -- Token handling (python-jose)
- `autom8_core.concurrency` -- Thread pool, decorators
- `autom8_core.config` -- Admin, environment, secrets config
- `autom8_core.http` -- HTTP session, instrumentation
- `autom8_core.logging` -- Logging config
- `autom8_core.models` -- API, base, status models (pydantic)
- `autom8_core.pandas` -- DataFrame utilities
- `autom8_core.resilience` -- Circuit breaker
- `autom8_core.utils` -- Collections, datetime, dicts, hashing, numeric, phone, random, strings, uuid, validation

**Relationship to autom8y SDKs**: This is the **predecessor**. The autom8y SDK family (autom8y-core, autom8y-config, autom8y-log, etc.) is the modern replacement. The `autom8` legacy monolith still consumes `autom8y-core>=0.2.0,<1.0.0` (CodeArtifact version) rather than `autom8-core`, suggesting partial migration.

---

### 1.6 autom8 (Legacy Monolith Application)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8` |
| **Classification** | Monolith application (legacy, active) |
| **Confidence** | High -- massive dependency list, 70K+ dependency pinning, FastAPI app with 1921-line main.py |
| **Package Manager** | uv (migrated from pip) |
| **Python Version** | >=3.10,<3.12 (constrained upper bound) |
| **Build Backend** | hatchling |
| **Deployment** | AWS Lambda (Docker container image, multi-stage Dockerfile with optional ffmpeg/Chrome) |
| **Database** | MySQL (via PyMySQL + SQLAlchemy, AWS Secrets Manager for credentials) |
| **Terraform** | Own terraform/ directory with ALB, VPC peering, security groups |

**Description**: The original autom8 application -- a large monolith handling content automation integrations across 25+ external APIs. Contains FastAPI API endpoints for auth, employee management, and system utilities. Runs as Lambda behind ALB.

**Key Characteristics**:
- **`app/main.py`**: 1921-line FastAPI application with embedded auth, health, employee, and system endpoints
- **`adapters/asana_adapter.py`**: 1861-line Asana adapter (predecessor to autom8y-asana)
- **`apis/`**: 30+ API client directories (asana, meta, twilio, stripe, openai, slack, google, etc.)
- **`entry_points/`**: Job runners, handlers, routers, slack bots, debug tools
- **`sql/`**: Direct MySQL access via SQLAlchemy/PyMySQL with session management
- **`utils/`**: Shared utilities (formatting, logging, threading, etc.)
- **~80 direct dependencies** spanning Asana, Stripe, Twilio, Meta, Google, OpenAI, AWS, Slack, data science (pandas, scipy, scikit-learn), video (yt-dlp, ffmpeg)
- **HS256 JWT auth** with local secret key (not delegated to auth service)
- Consumes `autom8y-core>=0.2.0,<1.0.0` and `autom8y-log>=0.3.3,<1.0.0` from CodeArtifact

---

### 1.7 autom8-client-lead-sms (SMS Conversation Microservice)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8-client-lead-sms` |
| **Classification** | Lambda microservice (satellite service) |
| **Confidence** | High -- explicit Lambda container Dockerfile, EventBridge handler |
| **Package Manager** | uv |
| **Python Version** | >=3.11 (builds targeting 3.12) |
| **Build Backend** | hatchling |
| **Deployment** | Lambda container (EventBridge scheduled trigger) |
| **Archetype** | `lambda-scheduled` |

**Description**: SMS conversation service for client leads, replacing a prior Zapier-based workflow. Uses Claude (via autom8y-claude SDK) for AI-driven conversation orchestration and Twilio for SMS transport. Fetches lead data from autom8y-data, sends SMS via Twilio.

**Key Modules**:
- `handlers/scheduled.py` -- Lambda entry point (`lambda_handler`)
- `clients/data_service.py` -- DataServiceClient for lead data
- `clients/twilio.py` -- Twilio SMS client
- `services/orchestrator.py` -- Conversation orchestration
- `prompts/` -- Claude prompt templates (scheduled, SDR)
- `models/` -- Conversation and Twilio models

---

### 1.8 autom8-s2s-demo (S2S Auth Demo)

| Attribute | Value |
|-----------|-------|
| **Path** | `/Users/tomtenuta/Code/autom8-s2s-demo` |
| **Classification** | Demo/educational scaffold |
| **Confidence** | High -- explicit "demo" in name and pyproject description |
| **Package Manager** | uv |
| **Python Version** | >=3.11 |
| **Build Backend** | hatchling |
| **Deployment** | Local-only (no Dockerfile, no infrastructure) |

**Description**: Educational reference implementation demonstrating service-to-service authentication using autom8y-auth and autom8y-core SDKs. Contains example typed service clients (DataServiceClient, AsanaServiceClient) showing the BaseClient pattern. Not production code.

---

## 2. Tech Stack Inventory

### 2.1 Languages and Runtimes

| Repo | Language | Runtime | Notes |
|------|----------|---------|-------|
| autom8y | Python | 3.11+ | Workspace constraint |
| autom8y-asana | Python | 3.11+ | |
| autom8y-data | Python | 3.11+, deploys 3.12 | |
| autom8y-ads | Python | 3.11+, deploys 3.12 | |
| autom8-core | Python | 3.10+ | Legacy, wider compat |
| autom8 | Python | 3.10-3.11 | Constrained upper bound |
| autom8-client-lead-sms | Python | 3.11+, deploys 3.12 | |
| autom8-s2s-demo | Python | 3.11+ | |

### 2.2 Frameworks

| Framework | Used By | Version |
|-----------|---------|---------|
| FastAPI | autom8y-data, autom8y-ads, auth (autom8y), autom8 | >=0.100-0.115 |
| SQLAlchemy/SQLModel | autom8y-data, auth (autom8y), autom8 | >=2.0 |
| Polars | autom8y-asana, autom8y-data | >=0.20/1.35 |
| Pydantic/pydantic-settings | All repos | >=2.0 |
| grpclib (+ betterproto) | autom8y-data | 0.4.7 |
| Typer | autom8y-data | >=0.9.0 |
| Ibis (DuckDB backend) | autom8y-data (analytics extra) | >=11.0 |
| Flask | autom8 (legacy) | ~=3.0 |
| aws-lambda-powertools | autom8-client-lead-sms | >=2.0 |
| mangum | autom8-client-lead-sms | >=0.17 |

### 2.3 Databases and Data Stores

| Store | Used By | Role |
|-------|---------|------|
| **PostgreSQL 15** | auth (autom8y) | User accounts, RBAC, API keys |
| **MySQL 8** | autom8y-data, autom8 (legacy), auth-mysql-sync | Business data, CRUD entities, legacy data |
| **Redis 7** | autom8y-asana (hot cache), autom8y-data (L2 cache, vertical cache), auth (sessions/rate limiting) | Caching and session management |
| **DuckDB** | autom8y-data (analytics) | In-process analytical queries |
| **S3** | autom8y-asana (cold cache, Parquet DataFrames), autom8 (data storage) | Object storage |
| **LocalStack** | dev environment | S3 + Secrets Manager emulation |

### 2.4 External API Integrations

| API | Consuming Repo(s) | Purpose |
|-----|-------------------|---------|
| Asana REST API | autom8y-asana, autom8 (legacy) | Project/task management, webhooks |
| Meta/Facebook Ads API | autom8y-ads (via autom8y-meta SDK), autom8 (legacy via facebook-business SDK) | Ad campaign management |
| Twilio | autom8-client-lead-sms, autom8 (legacy) | SMS messaging |
| Stripe | pull-payments (via autom8y-stripe SDK), autom8 (legacy) | Payment processing |
| Slack | slack-alert (via autom8y-slack SDK), autom8 (legacy via slack-sdk) | Notifications, reports |
| OpenAI | autom8 (legacy) | AI/LLM features |
| Anthropic/Claude | autom8-client-lead-sms (via autom8y-claude SDK) | AI conversation orchestration |
| Google APIs | autom8 (legacy) | Calendar, search, maps |
| AWS (SES, SQS, S3, Secrets Manager) | autom8y-asana, autom8y-data, auth, autom8 | Cloud infrastructure |

### 2.5 Build Tools and CI

| Tool | Role | Used By |
|------|------|---------|
| **uv** | Package manager, workspace orchestrator | All modern repos |
| **Poetry** | Package manager (legacy) | autom8-core only |
| **hatchling** | Build backend | All repos except autom8-core (poetry-core) and autom8y workspace root |
| **Ruff** | Linter + formatter | All repos |
| **mypy** | Type checker | All repos |
| **pytest** | Test framework | All repos |
| **just (Justfile)** | Task runner | autom8y, autom8y-data, autom8y-ads, autom8-client-lead-sms, autom8y-asana |
| **Make (Makefile)** | Task runner (legacy) | autom8 (131K-line Makefile) |
| **Alembic** | DB migrations | autom8y-data, auth (autom8y) |
| **buf** | Proto management | autom8y-data |
| **Docker** | Container builds | All services (multi-stage builds) |
| **GitHub Actions** | CI/CD | autom8y, autom8y-data, autom8y-ads, autom8-client-lead-sms, autom8 |
| **Terraform** | Infrastructure as Code | autom8y (per-service), autom8 (legacy ALB/VPC) |
| **CodeArtifact** | Private Python package registry | All repos (AWS CodeArtifact at `autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com`) |
| **nox** | Multi-Python testing | autom8y workspace (dev dependency) |
| **python-semantic-release** | Automated versioning | autom8y workspace (dev dependency) |

---

## 3. API Surface Map

### 3.1 autom8y-asana REST API

**Base URL**: `https://asana.api.autom8y.io`
**Auth**: S2S JWT (via autom8y-auth SDK) + PAT dual-mode
**Protocol**: REST (FastAPI/uvicorn)
**Confidence**: High

| Endpoint Group | Route Prefix | Key Endpoints |
|---------------|--------------|---------------|
| Health | `/` | GET /health, GET /ready, GET /health/deps |
| Projects | `/api/v1/projects` | GET (list), GET /{gid}, POST, PUT /{gid}, DELETE /{gid}, GET /{gid}/sections, POST /{gid}/sections, DELETE /{gid}/sections/{section_gid} |
| Tasks | `/api/v1/tasks` | GET (list), GET /{gid}, POST, PUT /{gid}, DELETE /{gid}, GET /{gid}/stories, GET /{gid}/subtasks, POST /{gid}/subtasks, POST /{gid}/addFollowers, DELETE /{gid}/removeFollowers, POST /{gid}/addProject, PUT /{gid}/section, POST /{gid}/setParent, DELETE /{gid}/setParent |
| Sections | `/api/v1/sections` | GET /{gid}/tasks, POST, PUT /{gid}, DELETE /{gid}, POST /{gid}/addTask, POST /{gid}/insertInSection |
| Users | `/api/v1/users` | GET /{gid}, GET (list), GET /me |
| Workspaces | `/api/v1/workspaces` | GET (list), GET /{gid} |
| DataFrames | `/api/v1/dataframes` | GET /project/{gid}, GET /section/{gid} |
| Query | `/api/v1/query` | POST /{entity_type}, POST /{entity_type}/rows, POST /{entity_type}/aggregate |
| Resolver | `/api/v1/resolve` | POST /{entity_type} |
| Entity Write | `/api/v1/entities` | PATCH /{entity_type}/{gid} |
| Section Timelines | `/api/v1/section-timelines` | GET /{section_gid} |
| Webhooks | `/api/v1/webhooks` | POST /inbound |
| Workflows | `/api/v1/workflows` | POST |
| Admin | `/api/v1/admin` | POST (cache warm, etc.) |

---

### 3.2 autom8y-data REST + gRPC API

**Base URL**: `https://data.api.autom8y.io`
**Auth**: JWT (via autom8y-auth SDK)
**Protocol**: REST (FastAPI port 8000) + gRPC (grpclib port 50051, same process)
**Confidence**: High

#### REST Endpoints

| Endpoint Group | Route Prefix | Key Endpoints |
|---------------|--------------|---------------|
| Health | `/` | GET /health, GET /ready, GET /health/deps, GET /health/materialization, GET /health/pool, GET /health/auth-config, GET /health/jwks-test |
| Data Service | `/api/v1` | POST /write (upsert), POST /write/batch, GET /read, GET /schema |
| Query | `/api/v1` | POST /query |
| Schema | `/api/v1/schema` | GET /metrics, GET /dimensions, GET /periods |
| Insights | `/api/v1` | GET /insights, GET /insights/{name}, POST /insights/{name}/execute, POST /insights/{name}/execute/batch, POST /insights/{name}/batch |
| Intelligence | `/api/v1/intelligence` | POST /market-efficiency, POST /budget-optimization, POST /anomalies, POST /peer-ranking, POST /creative |
| Analytics Health | `/api/v1/analytics` | POST /health |
| CRUD: Businesses | `/api/v1/businesses` | GET (list + factory CRUD: POST, GET/{id}, PATCH/{id}, DELETE/{id}, POST/batch) |
| CRUD: Offers | `/api/v1/offers` | GET (list), GET /{id} |
| CRUD: Business Offers | `/api/v1/business-offers` | GET /lookup, GET (list) |
| CRUD: Leads | `/api/v1/leads` | GET /{phone} |
| CRUD: Appointments | `/api/v1/appointments` | (factory CRUD) |
| CRUD: Payments | `/api/v1/payments` | POST (create), POST /batch |
| CRUD: Campaigns | `/api/v1/campaigns` | GET (list), GET /{id} |
| CRUD: Ads | `/api/v1/ads` | GET (list), GET /{id} |
| CRUD: Adsets | `/api/v1/adsets` | GET (list), GET /{id} |
| CRUD: Ad Insights | `/api/v1/ad-insights` | GET (list) |
| CRUD: Verticals | `/api/v1/verticals` | GET (list), GET /{id}, GET /key/{key} |
| CRUD: Addresses | `/api/v1/addresses` | GET (list) |
| Messages | `/api/v1` | GET /messages/pending, GET /messages/{id}/history, GET /messages/conversations, GET /messages/export, GET /messages, POST /messages |
| GID Mappings | `/api/v1/gid-mappings` | POST (sync Asana GIDs to data service) |
| Admin | `/api/v1/admin` | POST (refresh, jobs), GET (status, reports) |

#### gRPC Services (port 50051)

| Service | Package | Methods |
|---------|---------|---------|
| LeadService | autom8.data.v1 | CRUD operations |
| AddressService | autom8.data.v1 | CRUD operations |
| BusinessService | autom8.data.v1 | CRUD operations |
| AppointmentService | autom8.data.v1 | CRUD operations |
| PaymentService | autom8.data.v1 | CRUD operations |
| VerticalService | autom8.data.v1 | CRUD operations |
| Health | grpc.health.v1 | Standard health check |

#### CLI Interface

| Command | Entry Point |
|---------|-------------|
| `autom8` | `autom8_data.cli.main:app` (Typer) |

---

### 3.3 autom8y-ads REST API

**Base URL**: `https://ads.api.autom8y.io` (inferred; ALB priority pending)
**Auth**: JWT (via autom8y-auth SDK, disable-able for local dev)
**Protocol**: REST (FastAPI/uvicorn port 8000)
**Confidence**: High

| Endpoint Group | Route Prefix | Key Endpoints |
|---------------|--------------|---------------|
| Health | `/` | GET /health, GET /ready, GET /health/deps |
| Launch | `/api/v1` | POST /offers/{offer_id}/launch |
| Metrics | `/metrics` | (autom8y-telemetry Prometheus endpoint) |

---

### 3.4 Auth Service REST API

**Base URL**: `https://auth.api.autom8y.io`
**Auth**: Mixed (some endpoints public, some JWT-protected, some internal-only)
**Protocol**: REST (FastAPI/uvicorn)
**Confidence**: High
**JWT Issuer**: `auth.api.autom8y.io`

| Endpoint Group | Route Prefix | Key Endpoints |
|---------------|--------------|---------------|
| Health | `/` | GET /health, GET /ready, GET /health/deps |
| Auth | `/auth` | POST /register, POST /login, POST /refresh, POST /logout, POST /password-reset, GET /users, POST /verify, PUT /users/{id}, GET /profile |
| RBAC | `/auth/rbac` | POST /roles, GET /roles, GET /roles/{id}, PUT /roles/{id}, DELETE /roles/{id}, POST /assign, GET /permissions, POST /permissions, DELETE /permissions, POST /user-permissions, DELETE /user-permissions |
| API Keys | `/auth/api-keys` | POST, GET, DELETE /{id}, POST /validate |
| Well-Known | `/.well-known` | GET /jwks.json |
| Internal | `/internal` | POST /s2s/token, POST /s2s/validate, POST /bootstrap, POST /rotate-keys, GET /users |
| Admin | `/admin` | POST /users, GET /users, POST /system, DELETE /users/{id} |
| OAuth (mothballed) | `/auth/oauth` | (disabled per ADR-VAULT-001) |
| Charter (mothballed) | `/auth/charter` | (disabled) |

---

### 3.5 autom8 (Legacy) REST API

**Base URL**: (ALB-routed, legacy infrastructure)
**Auth**: HS256 JWT with local secret key
**Protocol**: REST (FastAPI/uvicorn, deployed as Lambda)
**Confidence**: Medium -- large monolithic main.py, auth pattern differs from platform standard

| Endpoint Group | Route Prefix | Key Endpoints |
|---------------|--------------|---------------|
| System | `/` | GET /, GET /health, GET /health/detailed, GET /health/circuit-breakers |
| Auth | `/auth` | POST /login, POST /logout, GET /me, POST /employees/authenticate, GET /employees/me, POST /tokens, POST /employees/tokens, POST /admin/tokens, POST /organizations/tokens |
| Employees | `/employees` | GET (list), GET /{id}, PATCH /{id} |
| System | `/system` | GET /organizations |

---

### 3.6 Lambda Services (No External API Surface)

These services are Lambda functions triggered by EventBridge schedules or SNS events. They do not expose HTTP endpoints but make outbound calls.

| Service | Trigger | Outbound Calls |
|---------|---------|---------------|
| **pull-payments** | EventBridge schedule | Stripe (via autom8y-stripe), autom8y-data REST API, auth S2S token |
| **reconcile-spend** | EventBridge schedule | autom8y-data REST API, autom8y-asana REST API, Slack, auth S2S token |
| **sms-performance-report** | EventBridge schedule | autom8y-data REST API, Slack, auth S2S token |
| **slack-alert** | SNS event (CloudWatch alarms) | Slack (via autom8y-slack SDK) |
| **auth-mysql-sync** | EventBridge schedule | MySQL (source), PostgreSQL (target) |
| **client-lead-sms** | EventBridge schedule | autom8y-data REST API (lead data), Twilio (SMS), Claude (AI conversation) |

---

## 4. Integration Pattern Map

### 4.1 Service-to-Service Communication

```
                                  +-----------+
                                  | Asana API |
                                  | (external)|
                                  +-----+-----+
                                        |
                          REST (PAT)    |
                                        v
+------------+   S2S JWT    +------------------+   REST (S2S JWT)    +-----------------+
|   autom8   |<----------->| autom8y-asana    |<------------------->| autom8y-data    |
|  (legacy)  |  (partial)  | (ECS + Lambda)   |  GID push, writes  | (ECS)           |
+-----+------+             +--------+---------+                    +--------+--------+
      |                             |                                       |
      | MySQL                       | S3                                    | MySQL
      | (direct)                    | (cache)                               | (primary DB)
      v                             v                                       | DuckDB
  +-------+                    +---------+                                  | Redis (L2)
  | MySQL |                    | S3/Redis|                                  v
  +-------+                    +---------+                           +------------+
                                                                     | MySQL/DuckDB|
                                                                     | Redis       |
                                                                     +------------+

+------------------+   REST (S2S JWT)    +-----------------+
| autom8y-ads      |<------------------->| autom8y-data    |
| (ECS)            |     (stub MVP)      |                 |
+------------------+                     +-----------------+
        |
        | REST (S2S JWT, stub)
        v
+------------------+
| autom8y-asana    |
+------------------+

+------------------+     S2S JWT         +------------------+
| pull-payments    |<------------------->| auth service     |
| (Lambda)         |     token acquire   | (ECS + Postgres) |
+--------+---------+                     +------------------+
         |                                       ^
         | Stripe API                             |
         v                                        |
    +---------+                    JWKS fetch      |
    | Stripe  |        +---> /.well-known/jwks.json+
    +---------+        |
                  All satellite services validate JWTs
                  by fetching JWKS from auth service

+------------------+   REST (S2S JWT)    +-----------------+
| reconcile-spend  |<------------------->| autom8y-data    |
| (Lambda)         |                     | autom8y-asana   |
+------------------+                     +-----------------+
         |
         | Slack API
         v
    +---------+
    |  Slack  |
    +---------+

+----------------------+  REST     +------------------+
| autom8-client-lead-  |---------->| autom8y-data     |
| sms (Lambda)         |           +------------------+
+----------+-----------+
           |
           | Twilio SMS + Claude AI
           v
     +-----------+   +---------+
     |  Twilio   |   |  Claude |
     +-----------+   +---------+
```

### 4.2 Authentication Topology

| Component | Role | Mechanism |
|-----------|------|-----------|
| **auth service** (autom8y) | Token issuer, JWKS provider, user/RBAC management | RS256 JWT (asymmetric), JWKS endpoint at `/.well-known/jwks.json` |
| **autom8y-auth SDK** | JWT validation library | Fetches JWKS from auth service, validates RS256 tokens |
| **S2S Token Flow** | Service-to-service auth | Service obtains S2S JWT from auth `/internal/s2s/token` using SERVICE_API_KEY, presents to target service |
| **autom8 (legacy)** | Independent auth | HS256 JWT with local secret key -- NOT integrated with auth service |

**Trust Boundaries**:
1. **Platform trust zone**: auth service issues RS256 JWTs; all modern satellites (autom8y-asana, autom8y-data, autom8y-ads) validate via autom8y-auth SDK + JWKS
2. **Legacy trust zone**: autom8 monolith uses independent HS256 JWT auth with hardcoded secret keys -- separate trust domain
3. **S2S trust**: Lambda services (pull-payments, reconcile-spend, sms-performance-report) acquire S2S tokens from auth service before calling satellite services

---

## 5. Deployment Topology

### 5.1 Service Deployment Map

| Service | Runtime | Deploy Method | ALB Priority | ECR Repo |
|---------|---------|--------------|--------------|----------|
| auth | ECS Fargate + RDS | ecs-deploy | 5 | autom8y/auth |
| autom8y-data | ECS Fargate | ecs-deploy | 110 | autom8y/data |
| autom8y-asana | ECS Fargate + Lambda | ecs-deploy | 120 | autom8y/asana |
| autom8y-ads | ECS Fargate | ecs-deploy | (pending) | autom8y/ads |
| autom8 (legacy) | Lambda (container) | (legacy deploy) | (legacy ALB) | (legacy ECR) |
| pull-payments | Lambda (container) | lambda-container | N/A | autom8y/pull-payments |
| reconcile-spend | Lambda (container) | lambda-container | N/A | autom8y/reconcile-spend |
| sms-performance-report | Lambda (container) | lambda-container | N/A | (pending) |
| slack-alert | Lambda (container) | lambda-container | N/A | autom8y/slack-alert |
| auth-mysql-sync | Lambda (zip) | lambda-zip | N/A | N/A |
| client-lead-sms | Lambda (container) | lambda-container | N/A | autom8y/client-lead-sms |
| codeartifact | Terraform-only | terraform-only | N/A | N/A |
| grafana | Terraform-only | terraform-only | N/A | N/A |
| observability | Terraform-only | terraform-only | N/A | N/A |

### 5.2 Satellite Service Pattern

Services whose application code lives in a separate repository from `autom8y` are "satellite services". Their Terraform and CI/CD live in `autom8y`, but their application code is in an external repo. Builds are triggered via `satellite-receiver.yml` GitHub Actions workflow.

| Satellite Repo | Platform Service Name |
|---------------|----------------------|
| autom8y-asana | asana |
| autom8y-data | data |
| autom8y-ads | ads |
| autom8y-client-lead-sms (inferred) | client-lead-sms |

### 5.3 Shared Infrastructure

| Infrastructure | Provider | Terraform Path | Consuming Services |
|---------------|----------|---------------|-------------------|
| PostgreSQL | AWS RDS | terraform/services/auth | auth |
| MySQL | AWS RDS | (legacy terraform) | autom8y-data, autom8 (legacy), auth-mysql-sync |
| Redis (auth) | ElastiCache | terraform/modules/auth-redis | auth |
| Redis (data) | ElastiCache | terraform/modules/data-redis | autom8y-data |
| Redis (asana) | ElastiCache | (via cache config) | autom8y-asana |
| S3 | AWS S3 | terraform/services/asana/s3.tf | autom8y-asana (cache + DataFrames) |
| ECR | AWS ECR | terraform/modules/ecr-repo | All containerized services |
| ALB | AWS ALB | terraform/services/* + autom8/terraform | All ECS services |
| CodeArtifact | AWS CodeArtifact | terraform/services/codeartifact | All repos (SDK distribution) |
| Cloudflare | Cloudflare | terraform/environments/production | DNS, CDN |
| LocalStack | Local Docker | docker-compose.platform.yml | Dev environment (S3, Secrets Manager emulation) |

---

## 6. Platform Library Graph

### 6.1 SDK Source and Distribution

All platform SDKs are developed in the **autom8y** workspace monorepo at `sdks/python/autom8y-*/` and distributed via **AWS CodeArtifact** at `autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/`.

In workspace development mode, SDKs resolve as editable workspace members. In CI and satellite repos, they resolve from CodeArtifact.

### 6.2 SDK Dependency Graph

```
autom8y-config (0.4.0) -- pydantic, pydantic-settings
    ^
    |
autom8y-log (0.5.5) -- autom8y-config, structlog
    ^
    |
autom8y-http (0.4.0) -- autom8y-log, httpx
    ^       ^
    |       |
    |   autom8y-core (1.1.0) -- httpx, pydantic
    |       ^
    |       |
autom8y-auth (1.1.0) -- autom8y-core, python-jose, tenacity
    |
autom8y-telemetry (0.3.1) -- autom8y-config, autom8y-log, opentelemetry-*
    |
autom8y-cache (0.4.0) -- (no required deps; optional: redis, boto3, autom8y-config)
    |
autom8y-meta (0.1.0) -- autom8y-http, autom8y-config, autom8y-log, httpx, pydantic
    |
autom8y-claude (0.2.0) -- autom8y-http, autom8y-log, pydantic
    |
autom8y-slack (0.2.0) -- httpx, autom8y-config, pydantic
    |
autom8y-stripe (1.2.0) -- autom8y-http, autom8y-config, stripe, pydantic
```

### 6.3 SDK Consumption Matrix

| SDK | autom8y-asana | autom8y-data | autom8y-ads | autom8-client-lead-sms | pull-payments | reconcile-spend | sms-perf-report | slack-alert | autom8 (legacy) | autom8-s2s-demo |
|-----|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| autom8y-config | X | X | X | - | X | X | X | X | - | - |
| autom8y-log | X | X | X | X | X | X | X | X | X* | - |
| autom8y-core | X | X | - | X | X | X | X | - | X* | X |
| autom8y-http | X | X | - | X | X | X | X | - | - | - |
| autom8y-auth | X | X | - | - | X | X | X | - | - | X |
| autom8y-cache | X | X | - | - | - | - | - | - | - | - |
| autom8y-telemetry | X | X | X | X | - | - | - | - | - | - |
| autom8y-meta | - | - | X | - | - | - | - | - | - | - |
| autom8y-claude | - | - | - | X | - | - | - | - | - | - |
| autom8y-slack | - | - | - | - | - | - | X | X | - | - |
| autom8y-stripe | - | - | - | - | X | - | - | - | - | - |

*X* = legacy `autom8` uses CodeArtifact versions with constrained version ranges (`<1.0.0`)

---

## 7. Data Flow Map

### 7.1 Primary Data Flows

```
Asana REST API
    |
    | (PAT auth, REST)
    v
autom8y-asana -------> S3 (Parquet cold cache)
    |                  Redis (hot cache)
    |
    | (S2S JWT, REST)
    | GID mappings, entity writes
    v
autom8y-data -------> MySQL (primary data store)
    |                 DuckDB (analytics engine)
    |                 Redis (L2 cache, vertical cache)
    |
    | (S2S JWT, REST)
    v
pull-payments <------ Stripe API (invoices)
    |
    | (S2S JWT, REST)
    | payment records
    v
autom8y-data

reconcile-spend
    |
    | (S2S JWT, REST)
    | read offers, payments, spend
    v
autom8y-data + autom8y-asana
    |
    | Slack webhook
    v
Slack (anomaly alerts)

client-lead-sms
    |
    | (REST)
    | read lead data
    v
autom8y-data
    |
    | Twilio API + Claude API
    v
SMS to leads

autom8y-ads (future)
    |
    | Meta Graph API
    | (campaign creation)
    v
Meta Ads Platform
    |
    | (future: S2S JWT)
    v
autom8y-data (ad entity writes)
autom8y-asana (task updates)
```

### 7.2 Database Flow

```
                    +----------------+
                    |  PostgreSQL 15 |  (auth-only)
                    |  auth_service  |
                    +-------+--------+
                            ^
                            |
                    +-------+--------+
                    |  auth service  |
                    +-------+--------+
                            ^
                            | (sync projection)
                            |
                    +-------+--------+
                    | auth-mysql-sync| (Lambda)
                    +-------+--------+
                            |
                            v
+-------------------+     MySQL 8     +-------------------+
| autom8y-data      |<-------------->| autom8 (legacy)   |
| (SQLAlchemy async)|  (shared DB)   | (SQLAlchemy sync) |
+-------------------+                +-------------------+
```

**Critical Observation**: autom8y-data and the autom8 legacy monolith share the same MySQL database. The auth-mysql-sync Lambda projects entities from this MySQL into the auth service's PostgreSQL.

---

## 8. Unknowns Register

### Unknown: autom8y-ads ALB routing not configured

- **Question**: Is autom8y-ads deployed and routable via ALB in production, or is it still pre-production?
- **Why it matters**: `alb_priority: null` in services.yaml means no ALB listener rule. The service may not be reachable in production.
- **Evidence**: `services.yaml` line 109: `alb_priority: null  # TODO: set when ads ALB routing is configured`
- **Suggested source**: Platform engineer or deployment runbooks

### Unknown: Shared MySQL database boundaries

- **Question**: Do autom8y-data and autom8 (legacy) access the same MySQL tables, or do they have separate schemas within the same MySQL instance?
- **Why it matters**: Shared table access creates tight coupling and data race risk. Schema separation would be a different (lower) risk profile.
- **Evidence**: Both repos connect to MySQL. `auth-mysql-sync` exists to project data from MySQL to PostgreSQL. `autom8y-data` uses SQLAlchemy async (asyncmy), autom8 uses SQLAlchemy sync (pymysql). Both appear to reference similar entity types (businesses, offers, leads).
- **Suggested source**: DBA documentation, database schemas, or `autom8y-data` Alembic migrations vs `autom8` SQL scripts

### Unknown: autom8 legacy monolith production deployment method

- **Question**: How is the autom8 legacy monolith currently deployed? The Dockerfile builds a Lambda container image, but it also has its own terraform/ with ALB configuration.
- **Why it matters**: Understanding whether the legacy app runs as Lambda, ECS, or both determines the blast radius of changes and the migration path.
- **Evidence**: 13K-line Dockerfile with multi-stage Lambda build, terraform/ with ALB routing, Makefile references both Lambda and local execution, `services.yaml` in autom8y does not list autom8 as a service.
- **Suggested source**: Deployment runbooks, AWS console

### Unknown: autom8-core vs autom8y-core relationship

- **Question**: Is `autom8-core` (Poetry, Python 3.10+) still actively maintained, or has it been fully superseded by `autom8y-core` (hatchling, Python 3.11+)?
- **Why it matters**: Two different "core" packages could cause version conflicts or confusion. The autom8 legacy monolith uses `autom8y-core` (from CodeArtifact), not `autom8-core` -- suggesting autom8-core may be deprecated.
- **Evidence**: `autom8-core` uses Poetry (last modified Nov 2025), `autom8y-core` uses uv/hatchling (actively maintained in workspace). The legacy `autom8` pyproject.toml depends on `autom8y-core>=0.2.0,<1.0.0`, not `autom8-core`. No modern repo imports `autom8_core`.
- **Suggested source**: Engineering team, package registry (CodeArtifact) usage metrics

### Unknown: autom8y-ads integration completeness

- **Question**: The autom8y-ads service uses stub clients for autom8y-asana and autom8y-data. When will real integration be completed?
- **Why it matters**: Until real clients are wired, the ads service cannot create Asana tasks or persist ad entities to the data store. The launch flow is incomplete.
- **Evidence**: `app.py` lines 112-114: `app.state.data_client = StubDataServiceClient()` and `app.state.asana_client = StubAsanaServiceClient()`. Config has `data_writes_enabled: bool = Field(default=False)`.
- **Suggested source**: Product roadmap, ads service team

### Unknown: autom8 legacy monolith migration timeline

- **Question**: What is the planned decommissioning or migration path for the autom8 legacy monolith?
- **Why it matters**: The monolith duplicates functionality now in satellite services (Asana adapter vs autom8y-asana, auth vs auth service, ad management, etc.). Parallel operation increases maintenance burden and data consistency risk.
- **Evidence**: 30+ API integrations in monolith, many being extracted into dedicated services. `adapters/asana_adapter.py` (1861 lines) predates autom8y-asana. The monolith has its own HS256 auth, distinct from the RS256 auth service.
- **Suggested source**: Engineering leadership, migration planning documents

### Unknown: Redis instance topology

- **Question**: Are autom8y-asana, autom8y-data, and auth using the same Redis instance or separate instances?
- **Why it matters**: Shared Redis creates a coupling point and potential noisy-neighbor issues. Separate instances provide isolation but add infrastructure cost.
- **Evidence**: Terraform has `auth-redis` and `data-redis` modules, suggesting at least partial separation. autom8y-asana also uses Redis. Docker Compose provides a single Redis for local dev.
- **Suggested source**: Terraform configuration, AWS ElastiCache console

### Unknown: sms-performance-report deployment status

- **Question**: Is sms-performance-report fully deployed? It's listed in services.yaml as a service within the autom8y workspace but has no `ecr_name` or `build_config`.
- **Why it matters**: Incomplete deployment configuration means CI/CD may not build or deploy this service automatically.
- **Evidence**: `services.yaml` does not have an entry for sms-performance-report (it exists as source code in `services/sms-performance-report/` but is not in the services manifest).
- **Suggested source**: Platform engineer, CI/CD logs

---

## Appendix A: Confidence Rating Summary

| Item | Confidence | Basis |
|------|-----------|-------|
| autom8y workspace classification | High | Explicit pyproject.toml workspace config |
| autom8y-asana classification | High | Prior ARCH-REVIEW-1 + build manifests |
| autom8y-data classification | High | pyproject.toml, Dockerfile, API routes, Alembic |
| autom8y-ads classification | High | pyproject.toml, Dockerfile, FastAPI app factory |
| autom8-core classification | High | pyproject.toml (Poetry), library packaging |
| autom8 (legacy) classification | High | pyproject.toml, 1921-line main.py, Dockerfile |
| autom8-client-lead-sms classification | High | pyproject.toml, Lambda Dockerfile, handler |
| autom8-s2s-demo classification | High | Explicit "demo" designation |
| Auth service API surface | High | Route files + include_router calls |
| autom8y-data gRPC surface | High | server.py service list + proto directory |
| autom8y-ads API surface | High | Route files (only health + launch) |
| Shared MySQL database hypothesis | Medium | Both repos connect to MySQL, auth-mysql-sync exists, but schema overlap not confirmed |
| autom8-core deprecation status | Medium | No modern repo imports it, but no explicit deprecation marker |
| autom8 deployment method | Medium | Dockerfile is Lambda-based, but terraform has ALB config |

---

## Appendix B: Repository Cross-Reference

| Canonical Service Name | Repo (Application Code) | Repo (Terraform + CI) | Service Archetype |
|----------------------|------------------------|----------------------|-------------------|
| auth | autom8y (services/auth/) | autom8y (terraform/services/auth/) | ecs-fargate-rds |
| data | autom8y-data | autom8y (terraform/services/data/) | ecs-fargate-stateless |
| asana | autom8y-asana | autom8y (terraform/services/asana/) | ecs-fargate-hybrid |
| ads | autom8y-ads | autom8y (terraform/services/ads/) | ecs-fargate-stateless |
| client-lead-sms | autom8-client-lead-sms | autom8y (terraform/services/client-lead-sms/) | lambda-scheduled |
| pull-payments | autom8y (services/pull-payments/) | autom8y (terraform/services/pull-payments/) | lambda-scheduled |
| reconcile-spend | autom8y (services/reconcile-spend/) | autom8y (terraform/services/reconcile-spend/) | lambda-scheduled |
| slack-alert | autom8y (services/slack-alert/) | autom8y (terraform/services/slack-alert/) | lambda-event-driven |
| auth-mysql-sync | autom8y (services/auth-mysql-sync/) | autom8y (terraform/services/auth-mysql-sync/) | lambda-scheduled |
| sms-performance-report | autom8y (services/sms-performance-report/) | (not in services.yaml) | lambda-scheduled (inferred) |
| autom8 (legacy) | autom8 | autom8 (terraform/) | Lambda monolith (legacy) |
| codeartifact | N/A | autom8y (terraform/services/codeartifact/) | infrastructure |
| grafana | N/A | autom8y (terraform/services/grafana/) | infrastructure |
| observability | N/A | autom8y (terraform/services/observability/) | infrastructure |

---

## Appendix C: Service Domain URLs

| Service | Production URL |
|---------|---------------|
| auth | https://auth.api.autom8y.io |
| autom8y-data | https://data.api.autom8y.io |
| autom8y-asana | https://asana.api.autom8y.io |
| autom8y-ads | (pending ALB configuration) |
| Web app | https://app.autom8y.io |
| Docs | https://docs.autom8y.io |
| Root | https://autom8y.io |
