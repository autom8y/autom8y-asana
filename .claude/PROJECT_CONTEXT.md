# Project Context

> This document orients agents to the project. Update it as the project evolves.

## What Is This?

**autom8_asana** is a standalone Python SDK wrapper for the Asana API, extracted from the monolithic autom8 platform. It provides a clean, type-safe, and ergonomic interface for interacting with Asana workspaces, projects, sections, tasks, custom fields, webhooks, and related resources. The project aims to decouple Asana API operations from domain-specific business logic, enabling reuse across multiple services while following industry best practices for SDK design (dependency injection, clean abstractions, proper error handling, and comprehensive typing).

## Current State

**Stage**: Prototype

**Health**:

- Test coverage: 0% (greenfield extraction)
- Known tech debt: Source module has ~798 files with 119 SQL imports, 256 business-logic imports, and 24 AWS cache imports that need separation
- Last major refactor: N/A - Initial extraction from autom8 `apis/asana_api/` module

## Tech Stack

| Layer          | Technology             | Notes                                              |
| -------------- | ---------------------- | -------------------------------------------------- |
| Language       | Python 3.10+           | Type-first with Pydantic models                    |
| SDK Base       | asana 5.0.3            | Official Asana Python SDK                          |
| HTTP Client    | httpx                  | Async-capable HTTP for custom endpoints            |
| Models         | Pydantic v2            | Request/response validation, serialization         |
| Caching        | Protocol-based         | Pluggable cache interface (default: in-memory)     |
| Async          | asyncio                | Optional async variants for all operations         |
| Queue          | N/A                    | SDK is stateless; consumers handle queueing        |
| Infrastructure | PyPI (CodeArtifact)    | Published to private autom8 artifact repository    |

## Architecture Overview

The SDK follows a layered architecture separating transport, resource management, and domain models. Business logic is explicitly excluded—this is a pure API wrapper.

```txt
┌─────────────────────────────────────────────────────────────────────┐
│                         Consumer Application                        │
│  (autom8 handlers, jobs, other microservices)                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        autom8_asana SDK                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  High-Level Resources (Task, Project, Section, CustomField) │   │
│  │  - Lazy loading, caching, batch operations                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Low-Level Clients (TasksApi, ProjectsApi, WebhooksApi)     │   │
│  │  - Direct API mapping, pagination, error handling           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Transport Layer (AsanaClient, connection pooling, retries) │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          ┌─────────────────┐
                          │   Asana API     │
                          │   api.asana.com │
                          └─────────────────┘
```

## Key Integrations

| System              | Purpose                          | Owner       | Docs                                          |
| ------------------- | -------------------------------- | ----------- | --------------------------------------------- |
| Asana API           | Core task/project management     | Asana       | https://developers.asana.com/docs             |
| autom8 (consumer)   | Primary consumer of this SDK     | autom8 team | Internal                                      |
| CodeArtifact        | Private package distribution     | autom8 team | AWS CodeArtifact console                      |

## Current Priorities

1. **Extract core Asana API wrapper** - Pure API operations without business logic (clients, models, error handling)
2. **Define clean interfaces** - Protocol-based abstractions for caching, logging, and auth that consumers can implement
3. **Establish testing infrastructure** - Unit tests with mocked Asana responses, integration test harness

## Known Constraints

- **Asana API Rate Limits**: 1,500 requests/minute per PAT; SDK must provide backoff/retry and batch API support
- **Backward Compatibility**: autom8 monolith depends heavily on current patterns; extraction must not break existing workflows during migration
- **No Business Logic**: SDK must remain domain-agnostic; business rules (e.g., "Offer", "Business", "Unit" models) stay in autom8
- **Python Version**: Must support Python 3.10-3.11 to match autom8 runtime constraints

## What Success Looks Like

| Metric                          | Target                                          |
| ------------------------------- | ----------------------------------------------- |
| Import footprint                | Zero imports from sql/, contente_api/, aws_api/ |
| Test coverage                   | ≥80% on core modules                            |
| API parity                      | All current asana_api operations supported      |
| Migration path                  | autom8 can adopt incrementally without rewrites |
| Documentation                   | Full API reference + migration guide            |
| Package size                    | <5MB wheel (no heavy dependencies)              |
| Cold import time                | <500ms                                          |

---

## Extraction Scope Reference

### What Moves to autom8_asana (Pure SDK)

- `clients/` - API client wrappers (tasks, projects, sections, webhooks, etc.)
- `asana_utils/` - Auth, error handling, converters (cleaned of business logic)
- `objects/generics/` - Base classes for Asana resources
- Core resource classes (Task, Project, Section, CustomField base)
- Batch API support
- Connection pooling and retry logic

### What Stays in autom8 (Business Logic)

- `objects/task/models/` - Domain-specific task types (Offer, Business, Unit, Contact, etc.)
- `objects/task/managers/` - Ad managers, insights exporters, process managers
- `objects/project/models/` - Project-specific business logic
- `objects/custom_field/models/` - Custom field mappings to business concepts
- All SQL integrations and AWS caching integrations
- Slack/OpenAI/Meta integrations triggered by Asana events
