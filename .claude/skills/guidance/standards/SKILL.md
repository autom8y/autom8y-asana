---
name: standards
description: "Code conventions, tech stack, and tool selection. Use when: writing implementation code, choosing libraries, deciding between native and shell tools. Triggers: code conventions, tech stack, naming conventions, tool selection, file operations."
---

# Standards & Conventions

> Implementation-time reference for code quality

## Decision Tree

**Before writing code**:
1. `repository-map.md` - Where does this file go?
2. `code-conventions.md` - How should I structure it?
3. `tech-stack-*.md` - What libraries should I use?

**Before choosing a tool**:
1. Check [tool-selection.md](tool-selection.md) - Native vs shell?
2. If deviating from conventions - Create ADR

## Sub-Files

### Code & Structure
- **Code Conventions**: [code-conventions.md](code-conventions.md) - File org, naming, patterns, error handling, testing
- **Repository Map**: [repository-map.md](repository-map.md) - Directory structure, file placement, dependencies

### Tech Stack (Domain-Specific)
- **Core Policies**: [tech-stack-core.md](tech-stack-core.md) - Universal technology governance, version strategy
- **Python Stack**: [tech-stack-python.md](tech-stack-python.md) - Python runtime, frameworks, tooling
- **Go Stack**: [tech-stack-go.md](tech-stack-go.md) - Go project structure, tooling, testing
- **Infrastructure**: [tech-stack-infrastructure.md](tech-stack-infrastructure.md) - Databases, Docker, CI/CD, cloud
- **API Design**: [tech-stack-api.md](tech-stack-api.md) - REST standards, OpenAPI, versioning

### Tool & Shell Guidance
- **Tool Selection**: [tool-selection.md](tool-selection.md) - Native tools vs shell, decision tree, hard rules, shell tools, task runners

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
| Choose tool (native vs shell) | tool-selection.md | Decision Tree |

## Cross-Skill Integration

- [prompting](../prompting/INDEX.lego.md) - Implementation prompts reference these
- [justfile](../../templates/justfile/INDEX.lego.md) - Task automation patterns and recipes
- `claude-md-architecture` - Content placement for CLAUDE.md (available with ecosystem)
- Team workflows - Principal Engineer role enforces these standards during implementation
