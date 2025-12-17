# API Design Standards

> REST API conventions, OpenAPI documentation, versioning

**Core Policies**: See [tech-stack-core.md](tech-stack-core.md) for universal technology governance

---

## API Design

### REST APIs

| Preference | Standard |
|------------|----------|
| Naming | `snake_case` for JSON fields |
| Versioning | URL-based: `/v1/`, `/v2/` |
| Pagination | Cursor-based for large sets, offset for small |
| Errors | RFC 7807 Problem Details |

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Email format is invalid",
  "instance": "/users/123"
}
```

### Documentation

| Choice | Tool | Why |
|--------|------|-----|
| API Docs | **OpenAPI 3.1** | Auto-generated from FastAPI |
| Interactive | **Swagger UI** (built into FastAPI) | Try endpoints in browser |
