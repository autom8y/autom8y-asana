---
name: standards
description: "Code conventions, tech stack, repository structure, tool selection. Use when: writing code, choosing libraries, organizing files, checking naming, selecting tools. Triggers: code conventions, tech stack, repository structure, where does code go, naming conventions, import order, test structure, which tool, native vs shell, Grep vs rg, file operations, tool selection."
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

**Preferred**: Use `just` for task automation. See [justfile skill](../justfile/SKILL.md) for patterns.

```bash
just test              # Run tests
just test:unit         # Run unit tests only
just dev               # Start development
just lint              # Run linter
just ci                # Run full CI pipeline locally
```

**Legacy/Alternative**: Some projects use `make`:

```bash
make test              # Run tests
make test FILE=path    # Run specific test
make dev               # Start development
make lint              # Run linter
make coverage          # Generate coverage
```

### Task Runner Selection

| Runner | When to Use |
|--------|-------------|
| `just` | New projects, complex workflows, multi-file organization |
| `make` | Existing projects with Makefile, simple needs |
| `npm scripts` | JavaScript/Node.js projects |
| Shell scripts | One-off automation, complex logic (> 10 lines) |

**Decision**: For new Python/Go projects, prefer `just` with modular organization. See [justfile skill](../justfile/SKILL.md).

## Shell Tools Availability

The shell environment follows a three-tier tool availability model:

### Tier 1: Integrated Tools (Aliased in .zshrc)

These are available via short commands, used daily:
- **eza** (`ls`, `ll`, `tree`) - Modern ls replacement with git integration
- **bat** (`cat`) - Syntax-highlighted file viewer
- **fd** - Fast find alternative (used by fzf)
- **zoxide** (`z`, `zi`) - Smart directory jumping
- **fzf** (`Ctrl+R`, `Ctrl+T`, `Alt+C`) - Fuzzy finder

### Tier 2: Available Tools (Installed, Not Aliased)

These are available via full command name, used occasionally:
- **jq** - JSON query and transformation (`jq '.field' file.json`)
- **yq** - YAML query and transformation (`yq '.field' file.yaml`)
- **ripgrep** (`rg`) - Fast text search
- **mise** - Polyglot version manager
- **direnv** - Auto-load project environments
- **gh** - GitHub CLI

Use the full command name when needed. No aliases to avoid cluttering the shell namespace.

### Tier 3: On-Demand Tools (Install When Needed)

These can be installed quickly via `mise` or `brew` when specific need arises:
- **httpie/curlie** - Modern HTTP clients for API exploration
- **tokei** - Code statistics and language breakdown
- **difftastic** - Syntax-aware diffs
- **hyperfine** - Command benchmarking

### Decision Framework

**Add to Tier 1 if:**
- Used daily
- Improves core workflow
- Worth muscle memory investment

**Add to Tier 2 if:**
- Used weekly or occasionally
- Fills capability gap
- Low integration cost
- Single-purpose utility

**Keep in Tier 3 if:**
- Used rarely
- Solves specific problem
- Can install quickly when needed

### Using Tier 2 Tools

```bash
# jq - JSON processing
curl -s api.example.com/data | jq '.results[]'
jq '.dependencies | keys' package.json

# yq - YAML processing
yq '.services.*.image' docker-compose.yml
yq -r '.jobs | keys[]' .github/workflows/ci.yml

# rg - Fast search
rg "TODO" --type py
rg -i "error" logs/

# gh - GitHub operations
gh pr list
gh issue create
```

See [Shell Configuration Guide](../../../docs/SHELL.md) for complete tool reference.

## Tool Selection

**Default**: Use Claude Code native tools for file operations. Use shell CLI for git, GitHub, and project commands.

### Decision Tree

```
File operation (read/write/search/find)?
├─ YES: Use native tool (Read, Write, Edit, Grep, Glob)
└─ NO: Git/GitHub operation?
       ├─ GitHub (PRs, issues): Use `gh` CLI via Bash
       └─ Git (status, diff, commit): Use git commands via Bash

Directory structure visualization?
├─ YES: Use `eza --tree --git-ignore` via Bash
└─ NO: Project command (test, build, dev)?
       ├─ YES: Use `just` or `make` via Bash (prefer `just`)
       └─ NO: Default to native tool if available
```

### Quick Reference

| Task | Use This | NOT This |
|------|----------|----------|
| Search file contents | `Grep` tool | `rg`, `grep` commands |
| Find files by pattern | `Glob` tool | `fd`, `find` commands |
| Read file contents | `Read` tool | `cat`, `bat`, `head`, `tail` |
| Edit files | `Edit` tool | `sed`, `awk` |
| Write files | `Write` tool | `echo >`, heredocs |
| Directory tree | `eza --tree` via Bash | `tree` command |
| Git operations | `git` via Bash | (no native equivalent) |
| GitHub operations | `gh` via Bash | (no native equivalent) |
| Run tests | `make test` via Bash | (no native equivalent) |

### Hard Rules

1. **Never use interactive tools** - `fzf` picker, `zi` directory picker cannot receive agent input
2. **Always use Read for files** - handles text, images, PDFs; context-optimized
3. **Always use Grep for search** - structured output, respects sandboxing
4. **Always use Glob for finding** - faster than shell, integrated results
5. **Always use Edit/Write for changes** - atomic, integrated, safer

### Shell Tools Worth Using

| Tool | When | Example |
|------|------|---------|
| `eza --tree` | Visualize directory structure | `eza --tree --level=3 --git-ignore` |
| `gh` | GitHub PR/issue operations | `gh pr list`, `gh pr create` |
| `git` | All version control | `git status`, `git diff`, `git commit` |
| `just` | Project commands (preferred) | `just test`, `just dev`, `just lint` |
| `make` | Project commands (legacy) | `make test`, `make dev`, `make lint` |

For complete shell environment documentation, see [SHELL.md](../../../docs/SHELL.md).

## Cross-Skill Integration

- [prompting](../prompting/SKILL.md) - Implementation prompts reference these
- [10x-workflow](../10x-workflow/SKILL.md) - Principal Engineer enforces these
- [justfile](../justfile/SKILL.md) - Task automation patterns and recipes
- [claude-md-architecture](../claude-md-architecture/SKILL.md) - Content placement for CLAUDE.md (what belongs where)
