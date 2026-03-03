# Repository Map

> Where things live. Consult this before creating new files or looking for existing code.

## Directory Structure

```
/
├── .claude/                    # Claude Code configuration
│   └── CLAUDE.md              # Main entry point (this references other docs)
│
├── .ledge/                    # Documentation root
│   ├── specs/                 # PRDs, TDDs, and Test Plans
│   └── decisions/             # ADRs
│
├── /src                       # Application source code
│   ├── /api                   # HTTP layer
│   │   ├── /routes            # Route handlers by domain
│   │   ├── /middleware        # Request/response middleware
│   │   ├── /models            # Request/response Pydantic models
│   │   └── dependencies.py    # FastAPI dependency injection
│   │
│   ├── /domain                # Business logic (no I/O dependencies)
│   │   ├── /entities          # Domain objects
│   │   ├── /services          # Business operations
│   │   ├── /rules             # Business rules and validation
│   │   └── /events            # Domain events
│   │
│   ├── /infrastructure        # External concerns
│   │   ├── /database          # DB connection, repositories, migrations
│   │   ├── /cache             # Redis/cache implementations
│   │   ├── /external          # Third-party API clients
│   │   └── /messaging         # Queue/pub-sub implementations
│   │
│   ├── /shared                # Cross-cutting concerns
│   │   ├── /types             # Shared type definitions
│   │   ├── /errors            # Error hierarchy
│   │   ├── /utils             # Pure utility functions
│   │   └── /constants         # Application constants
│   │
│   └── main.py                # Application entry point
│
├── /tests                     # Test suite
│   ├── /unit                  # Pure logic tests
│   ├── /integration           # Tests with real dependencies
│   ├── /e2e                   # End-to-end tests
│   ├── /fixtures              # Test data factories
│   └── conftest.py            # Shared pytest configuration
│
├── /scripts                   # Development and operational scripts
│   ├── dev_setup.sh           # Local development setup
│   ├── run_migrations.py      # Database migration runner
│   └── seed_data.py           # Test data seeding
│
├── /config                    # Configuration files
│   ├── settings.py            # Application settings class
│   └── logging.py             # Logging configuration
│
├── pyproject.toml             # Project dependencies and metadata
├── Makefile                   # Common commands
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Local development stack
└── README.md                  # Project overview
```

## Key Files

| File                      | Purpose                            | When to Modify                            |
| ------------------------- | ---------------------------------- | ----------------------------------------- |
| `src/main.py`             | App entry, middleware registration | Adding middleware, startup/shutdown hooks |
| `src/api/dependencies.py` | Dependency injection setup         | Adding new injectable services            |
| `src/shared/errors.py`    | Error class hierarchy              | Adding new error types                    |
| `config/settings.py`      | Environment configuration          | Adding new config values                  |
| `tests/conftest.py`       | Test fixtures and setup            | Adding shared test utilities              |

## Where to Put New Code

| I'm creating...     | Put it in...                                                     | Notes                   |
| ------------------- | ---------------------------------------------------------------- | ----------------------- |
| New API endpoint    | `/src/api/routes/{domain}.py`                                    | One router per domain   |
| Business logic      | `/src/domain/services/{name}_service.py`                         | No I/O imports allowed  |
| Database query      | `/src/infrastructure/database/repositories/{name}_repository.py` | Returns domain entities |
| External API client | `/src/infrastructure/external/{service}_client.py`               | Wrap with interface     |
| Shared type         | `/src/shared/types/{domain}_types.py`                            | Used across layers      |
| Utility function    | `/src/shared/utils/{purpose}.py`                                 | Must be pure (no I/O)   |
| New error type      | `/src/shared/errors.py`                                          | Add to hierarchy        |
| Unit test           | `/tests/unit/test_{module}.py`                                   | Mirror source structure |
| Integration test    | `/tests/integration/test_{feature}.py`                           | Group by feature        |
| Test factory        | `/tests/fixtures/{domain}_factory.py`                            | One factory per entity  |

## Module Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                          /api                                │
│                     (HTTP layer)                             │
└─────────────────────────┬───────────────────────────────────┘
                          │ imports
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        /domain                               │
│                   (Business logic)                           │
└─────────────────────────┬───────────────────────────────────┘
                          │ defines interfaces for
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    /infrastructure                           │
│                  (External concerns)                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        /shared                               │
│              (Can be imported by any layer)                  │
└─────────────────────────────────────────────────────────────┘
```

**Rules**:
- `/api` -> can import from `/domain`, `/shared`
- `/domain` -> can import from `/shared` only (defines interfaces, doesn't import implementations)
- `/infrastructure` -> can import from `/domain`, `/shared` (implements domain interfaces)
- `/shared` -> imports nothing from other src directories

## Naming Patterns

| Type              | Pattern                  | Example              |
| ----------------- | ------------------------ | -------------------- |
| Router            | `{domain}_router.py`     | `user_router.py`     |
| Service           | `{domain}_service.py`    | `user_service.py`    |
| Repository        | `{domain}_repository.py` | `user_repository.py` |
| Entity            | `{name}.py`              | `user.py`            |
| Factory (test)    | `{domain}_factory.py`    | `user_factory.py`    |
| Client (external) | `{service}_client.py`    | `stripe_client.py`   |

## Documentation Locations

| Document Type | Location          | Naming                 |
| ------------- | ----------------- | ---------------------- |
| PRD           | `.ledge/specs/`   | `PRD-{NNNN}-{slug}.md` |
| TDD           | `.ledge/specs/`   | `TDD-{NNNN}-{slug}.md` |
| ADR           | `.ledge/decisions/` | `ADR-{NNNN}-{slug}.md` |
| Test Plan     | `.ledge/specs/`   | `TP-{NNNN}-{slug}.md`  |
