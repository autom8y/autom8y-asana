---
name: standards
description: "Code conventions, tech stack, repository structure. Use when: writing code, choosing libraries, organizing files, checking naming. Triggers: code conventions, tech stack, repository structure, where does code go, naming conventions, import order, test structure."
---

# Standards & Conventions

> Implementation-time reference for code quality

## Decision Tree

**Before writing code**:
1. `repository-map.md` - Where does this file go?
2. `code-conventions.md` - How should I structure it?
3. `tech-stack.md` - What libraries should I use?

**Before choosing library**:
1. Check `tech-stack.md` - Preferred tool exists?
2. If deviating - Create ADR

## Quick Reference

### File Naming (Python)

- Service: `{name}_service.py`
- Repository: `{name}_repository.py`
- Router: `{name}_router.py`
- Test: `test_{name}.py`

### Import Order

1. Standard library
2. Third-party
3. Local (absolute)

### Test Naming

`test_{function}_{scenario}_{expected}()`

### Test Structure (AAA)

```python
def test_create_user_succeeds():
    # Arrange
    user_data = UserFactory.build()
    # Act
    result = service.create_user(user_data)
    # Assert
    assert result.id is not None
```

### Directory Quick Lookup

- Business logic: `/src/domain/services/`
- API routes: `/src/api/routes/`
- Database: `/src/infrastructure/database/`
- Tests: `/tests/unit/` (mirrors src)

## Progressive Standards

### Code & Structure
- **Code Conventions**: [code-conventions.md](code-conventions.md) - File org, naming, patterns, error handling, testing
- **Repository Map**: [repository-map.md](repository-map.md) - Directory structure, file placement, dependencies

### Tech Stack (Domain-Specific)
- **Core Policies**: [tech-stack-core.md](tech-stack-core.md) - Universal technology governance, version strategy
- **Python Stack**: [tech-stack-python.md](tech-stack-python.md) - Python runtime, frameworks, tooling
- **Go Stack**: [tech-stack-go.md](tech-stack-go.md) - Go project structure, tooling, testing
- **Infrastructure**: [tech-stack-infrastructure.md](tech-stack-infrastructure.md) - Databases, Docker, CI/CD, cloud
- **API Design**: [tech-stack-api.md](tech-stack-api.md) - REST standards, OpenAPI, versioning

## Common Tasks

| I want to... | Check File | Section |
|--------------|-----------|---------|
| Add API endpoint | repository-map.md | Where to Put New Code |
| Choose database | tech-stack-infrastructure.md | Database |
| Choose Python library | tech-stack-python.md | Python Stack |
| Choose Go library | tech-stack-go.md | Go Stack |
| Structure test | code-conventions.md | Testing Conventions |
| Name service | code-conventions.md | Naming Conventions |
| Handle errors | code-conventions.md | Error Handling |
| Set up Docker | tech-stack-infrastructure.md | Containerization |
| Design REST API | tech-stack-api.md | REST APIs |

## Development Commands

```bash
make test              # Run tests
make test FILE=path    # Run specific test
make dev               # Start development
make lint              # Run linter
make coverage          # Generate coverage
```

## Cross-Skill Integration

- [prompting](../prompting/SKILL.md) - Implementation prompts reference these
- [10x-workflow](../10x-workflow/SKILL.md) - Principal Engineer enforces these
