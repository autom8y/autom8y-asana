# Infrastructure & DevOps Tech Stack

> Databases, containerization, cloud, CI/CD, developer tooling

**Core Policies**: See [tech-stack-core.md](tech-stack-core.md) for universal technology governance

---

## Database

### Primary Database

| Choice | Tool | Why |
|--------|------|-----|
| OLTP Database | **PostgreSQL 16+** | Reliability, features, JSON support |
| Connection Pool | **PgBouncer** (production) | Connection management at scale |

### Migrations

| Choice | Tool | Why |
|--------|------|-----|
| Python | **alembic** | SQLAlchemy integration |
| Go | **goose** | Simple SQL migrations |
| Standalone | **dbmate** | Language-agnostic |

### Caching

| Choice | Tool | Why |
|--------|------|-----|
| Cache | **Redis** or **Valkey** | Fast, versatile, pub/sub |
| Client (Python) | **redis-py** with async | Native async support |

### Search (When Needed)

| Choice | Tool | Why |
|--------|------|-----|
| Full-text | **PostgreSQL FTS** | Good enough for most cases |
| Heavy Search | **Meilisearch** or **Typesense** | When Postgres FTS isn't enough |

---

## Infrastructure & DevOps

### Containerization

| Choice | Tool | Why |
|--------|------|-----|
| Containers | **Docker** | Industry standard |
| Local Dev | **Docker Compose** | Multi-service development |
| Build | **Multi-stage Dockerfiles** | Small, secure images |

```dockerfile
# Python example
FROM python:3.12-slim as builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "src.main"]
```

### Cloud

| Choice | Tool | Why |
|--------|------|-----|
| Cloud Provider | **AWS** (primary) | Mature, comprehensive |
| Auth | **AWS SSO / IAM Identity Center** | Centralized access |
| IaC | **Terraform** or **Pulumi** | Reproducible infrastructure |
| Secrets | **AWS Secrets Manager** or **1Password** | Never in code |

### CI/CD

| Choice | Tool | Why |
|--------|------|-----|
| CI/CD | **GitHub Actions** | Integrated, good free tier |
| Alternative | **GitLab CI** | If using GitLab |

### Local Development

| Choice | Tool | Why |
|--------|------|-----|
| Version Manager | **mise** | Manages Python, Go, Node, etc. in one tool |
| Env Files | **.env** (gitignored) | Local-only secrets |
| Secrets (dev) | **direnv** | Auto-load env per directory |

---

## CLI Tools

### Building CLIs

| Choice | Tool | Why |
|--------|------|-----|
| Python CLI | **Typer** | FastAPI-like DX for CLIs |
| Go CLI | **cobra** | Industry standard |
| Rich Output | **Rich** (Python) | Beautiful terminal output |

### Developer Tools We Use

```bash
# Essential
brew install mise           # Version management for everything
brew install direnv         # Auto-load env vars
brew install jq             # JSON processing
brew install httpie         # Better curl

# Database
brew install pgcli          # Better psql

# Containers
brew install docker
brew install lazydocker     # TUI for Docker

# Git
brew install gh             # GitHub CLI
brew install lazygit        # TUI for Git
```
