# Go Tech Stack

> Go ecosystem: runtime, project structure, tooling, testing

**Core Policies**: See [tech-stack-core.md](tech-stack-core.md) for universal technology governance

---

## Go Stack

### Version & Management

| Choice | Tool | Why |
|--------|------|-----|
| Go Version | **1.22+** | Range-over-func, better tooling |
| Version Management | **mise** or **goenv** | Multiple Go versions |

### Project Structure

```
/cmd
    /myapp          # Main applications
        main.go
/internal           # Private application code
    /domain         # Business logic
    /handlers       # HTTP/gRPC handlers
    /repository     # Data access
/pkg                # Public library code (if any)
/scripts            # Build/deploy scripts
go.mod
go.sum
```

### Web & API

| Choice | Tool | Why |
|--------|------|-----|
| HTTP Router | **chi** or **stdlib** | chi for features, stdlib (1.22+) for simplicity |
| Validation | **go-playground/validator** | Struct tag validation |
| Config | **envconfig** or **viper** | Environment-based config |

### Database Tooling

| Choice | Tool | Why |
|--------|------|-----|
| SQL Driver | **pgx** | Best PostgreSQL driver |
| Query Builder | **sqlc** | Generate type-safe code from SQL |
| Migrations | **goose** | Simple, SQL-based migrations |

### Testing

| Choice | Tool | Why |
|--------|------|-----|
| Testing | **stdlib testing** | Built-in is excellent |
| Assertions | **testify** (optional) | If you want assertions |
| Mocking | **mockery** | Generate mocks from interfaces |

### Tooling

| Choice | Tool | Why |
|--------|------|-----|
| Linting | **golangci-lint** | Aggregates all linters |
| Formatting | **gofmt** / **goimports** | Standard formatting |

---

## Quick Reference

### New Go Project

```bash
# Create project
mkdir my-service && cd my-service
go mod init github.com/org/my-service

# Add dependencies
go get github.com/go-chi/chi/v5
go get github.com/jackc/pgx/v5
go get github.com/rs/zerolog

# Setup linting
cat > .golangci.yml << 'EOF'
linters:
  enable:
    - gofmt
    - govet
    - errcheck
    - staticcheck
    - gosimple
    - ineffassign
    - unused
EOF
```
