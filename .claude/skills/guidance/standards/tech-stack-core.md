# Tech Stack Core Policies

> Universal technology decisions and governance policies that apply to all tech choices.

## Related Tech Stack Guides

- [Python Stack](tech-stack-python.md) - Python ecosystem choices
- [Go Stack](tech-stack-go.md) - Go ecosystem choices
- [Infrastructure](tech-stack-infrastructure.md) - DevOps, databases, deployment
- [API Design](tech-stack-api.md) - REST API standards

---

# Tech Stack & Tooling Preferences

> Opinionated defaults for technology choices. These are strongly held preferences, loosely held—override when requirements demand it, but document why in an ADR.

---

## Philosophy

**Boring technology for infrastructure, modern tools for productivity.** We don't chase shiny things, but we don't cling to legacy tools when better options exist. The goal is fast iteration with production stability.

**Explicit dependencies, reproducible builds.** Anyone should be able to clone the repo and run the project with minimal setup. Lock files are committed. Versions are pinned.

**Type safety is not optional.** Static analysis catches bugs before runtime. Types are documentation that doesn't go stale.

---

## When to Deviate

These are defaults, not mandates. Override when:

| Situation | Example | Action |
|-----------|---------|--------|
| Client requirement | "Must use MySQL" | Use MySQL, document in ADR |
| Legacy integration | Existing pandas pipeline | Keep pandas for that module |
| Performance critical | Need every microsecond | Drop to lower-level tools |
| Team expertise | Team knows Django well | Consider Django over FastAPI |
| Ecosystem constraint | Library requires X | Use X, isolate the dependency |

**Always**: Document deviations in an ADR explaining why.

---

## Version Pinning Strategy

### Lock Everything

```toml
# pyproject.toml - specify minimum versions
dependencies = [
    "fastapi>=0.109.0",
    "pydantic>=2.5.0",
]

# uv.lock - exact versions (committed)
# This file is auto-generated, always commit it
```

### Update Strategy

- **Weekly**: Run `uv lock --upgrade` and test
- **Monthly**: Review and update major versions
- **Quarterly**: Audit for security vulnerabilities

```bash
# Check for updates
uv pip list --outdated

# Update all
uv lock --upgrade

# Update specific package
uv add package@latest
```

---

## ADR Triggers

Create an ADR when deviating from this stack:

- Using a database other than PostgreSQL
- Using an ORM other than SQLModel
- Using pandas instead of Polars for new code
- Using a different web framework
- Adding significant new infrastructure
- Choosing a different cloud provider
- Using synchronous I/O in an async context (even if justified)
