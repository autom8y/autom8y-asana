---
name: atuin-desktop
description: "Atuin Desktop .atrb runbook format and validation. Use when: generating runbooks for Atuin Desktop, validating .atrb file structure, converting workflows to runbook format. Triggers: atrb, runbook, Atuin Desktop, .atrb format, runbook generation, runbook validation."
---

# Atuin Desktop Runbooks (.atrb)

> YAML-based runbook format for Atuin Desktop application

## Format Overview

**Extension**: `.atrb` (Atuin RunBook)
**Encoding**: UTF-8, YAML 1.1
**No document markers**: Omit `---` at start

### Root Schema

```yaml
id: <uuid>              # Required: Unique document identifier
name: <string>          # Required: Document title
version: 1              # Required: Always 1
forkedFrom: null        # Required: null or source document ID
content: []             # Required: Array of blocks
```

## Block Types Quick Reference

| Type | Purpose | Has Content? | Key Props |
|------|---------|--------------|-----------|
| `heading` | Section headers | Yes | `level` (1-6), `isToggleable` |
| `paragraph` | Text content | Yes | textAlignment |
| `quote` | Blockquotes | Yes | (no textAlignment) |
| `var` | Define variables | **No** | `name`, `value` |
| `var_display` | Show variable | No | `name` |
| `script` | Execute code | **No** | `interpreter`, `code`, `outputVariable` |
| `http` | HTTP requests | No | `request` object |
| `run` | Terminal command | No | `code`, `pty`, `terminalRows` |

**Critical**: `script` and `var` blocks have NO `content` field.

## Critical Formatting Rules

1. **No YAML document markers** - Don't start with `---`
2. **List item alignment** - Items at same indent as parent key
3. **Multi-line strings** - Use block scalar `|-`
4. **Trailing paragraph** - All documents end with empty paragraph
5. **Props before content** - Always in this order
6. **No content on script/var** - These blocks store data in props only

## Agent Workflow

| Agent | Uses This Skill For |
|-------|---------------------|
| Requirements Analyst | Capturing runbook requirements in PRD |
| Architect | Designing runbook structure in TDD |
| Principal Engineer | Generating valid .atrb files |
| QA/Adversary | Validating .atrb structure and content |

## Sub-Files

**Specifications**:
- [spec/block-types.md](spec/block-types.md) - Complete block type specifications with examples
- [spec/formatting-rules.md](spec/formatting-rules.md) - YAML formatting requirements
- [spec/template-variables.md](spec/template-variables.md) - Variable interpolation and usage

**Validation**:
- [validation/checklist.md](validation/checklist.md) - QA validation checklist
- [validation/common-pitfalls.md](validation/common-pitfalls.md) - Known issues and fixes

**Agent Integration**:
- [agent-guidance.md](agent-guidance.md) - Agent-specific workflows

## Cross-Skill Integration

- [standards](../../guidance/standards/INDEX.lego.md) - YAML conventions, file organization
- [documentation](../documentation/INDEX.lego.md) - PRD/TDD when runbooks are the deliverable
