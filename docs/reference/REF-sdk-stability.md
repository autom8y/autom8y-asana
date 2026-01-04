# REF-sdk-stability

> Platform SDK stability classifications and version requirements

## Overview

This document clarifies the stability status of autom8y platform SDKs used in autom8_asana and reconciles the difference between formal classifiers and usage maturity.

## Official Stability Classifiers

All autom8y platform SDKs are currently **Beta** according to their official PyPI classifiers:

| SDK | Version Floor | PyPI Classifier |
|-----|---------------|-----------------|
| autom8y-auth | 0.1.0 | Beta (0.x) |
| autom8y-cache | (implicit) | Beta (0.x) |
| autom8y-config | 0.1.0 | Beta (0.x) |
| autom8y-http | 0.3.0 | Beta (0.x) |
| autom8y-log | 0.3.2 | Beta (0.x) |

**Beta means:**
- Public APIs may change between minor versions
- Semantic versioning is not guaranteed until 1.0.0
- Production use is acceptable but with version pinning
- Breaking changes follow platform deprecation policy

## Usage Maturity in autom8_asana

While officially Beta, these SDKs have different levels of **usage maturity** within autom8_asana:

### Production-Ready Usage
These SDKs are battle-tested in autom8_asana with stable integration patterns:

- **autom8y-http**: Core HTTP transport layer, fully integrated
  - 67 files depend on it (direct and indirect)
  - Wraps httpx with retry, observability, and error handling
  - Version: 0.3.0+ required

- **autom8y-log**: Logging infrastructure with stdlib interception
  - 58 files use logging (intercepted via `intercept_stdlib=True`)
  - Auto-format detection (JSON in CI, colored console in dev)
  - Version: 0.3.2+ required for auto-format

- **autom8y-config**: Settings management via Pydantic
  - Used in all configuration classes
  - Stable environment variable parsing
  - Version: 0.1.0+ required

### Limited Usage
These SDKs are used but with narrower scope:

- **autom8y-cache**: Cache abstraction layer
  - Used in 4 files (cache/manager.py, cache/redis.py, etc.)
  - Provides Redis/memory cache implementations
  - Version: Not explicitly pinned (follows platform)

- **autom8y-auth**: Authentication and JWT validation
  - Optional dependency (`extras = ["auth"]`)
  - Used only in API authentication layer
  - Version: 0.1.0+ required

## Dependency Declaration

All platform SDKs must be declared in **two places** in `pyproject.toml`:

1. **dependencies** (or optional-dependencies): Declares package dependency
2. **tool.uv.sources**: Declares CodeArtifact registry location

Example:
```toml
[project]
dependencies = [
    "autom8y-http>=0.3.0",
]

[tool.uv.sources]
autom8y-http = { index = "autom8y" }
```

**Why both?**
- `dependencies`: What packages are needed
- `tool.uv.sources`: Where to find them (private CodeArtifact registry)

Missing `uv.sources` entry will cause resolution failure even if dependency is declared.

## Version Floor Requirements

Version floors enforce minimum feature requirements:

| SDK | Floor | Reason |
|-----|-------|--------|
| autom8y-log | 0.3.2 | Auto-format detection (TTY → console, no TTY → JSON) |
| autom8y-http | 0.3.0 | HTTPX 0.25+ compatibility, retry configuration |
| autom8y-config | 0.1.0 | Initial stable Pydantic Settings integration |
| autom8y-auth | 0.1.0 | JWT validation with JWKS caching |

**No upper bounds**: SDKs follow platform compatibility policy. Upper bounds (e.g., `<0.4.0`) should be avoided unless breaking changes are known.

## Stability vs. Readiness

**Stability** (PyPI classifier): Official semantic versioning commitment
**Readiness** (usage maturity): Battle-tested integration patterns in this project

All autom8y SDKs are:
- **Officially Beta**: 0.x versions, API may change
- **Production-ready for autom8_asana**: Stable integration patterns, version floors ensure compatibility

When integrating new SDK versions:
1. Review CHANGELOG for breaking changes
2. Test against version floor requirements
3. Update integration if APIs changed
4. Document new patterns if behavior differs

## Related Documents

- `src/autom8_asana/core/logging.py`: Stdlib logging interception configuration
- `pyproject.toml`: Dependency and source declarations
- Platform SDK CHANGELOGs: Breaking change announcements
