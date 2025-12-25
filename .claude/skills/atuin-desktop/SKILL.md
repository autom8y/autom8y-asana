---
name: atuin-desktop
description: "Atuin Desktop .atrb runbook file format, generation, and validation. Use when: creating runbooks, editing .atrb files, converting markdown to runbook format, validating runbook YAML structure. Triggers: atrb, runbook, Atuin Desktop, runbook file, .atrb format, runbook generation, runbook validation, markdown to runbook, script block, terminal block, var block."
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

---

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

---

## Block Structure Pattern

Every block follows this structure:

```yaml
- id: <uuid>
  type: <block-type>
  props:
    # Type-specific properties (order matters for some)
  content:  # Only if block type supports content
    - type: text
      text: "Content here"
      styles: {}
```

### Props Order (when present)

`backgroundColor` -> `textColor` -> `textAlignment` -> `level` -> `isToggleable`

---

## Content Blocks (with inline content)

### Paragraph

```yaml
- id: "block-uuid"
  type: paragraph
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
  content:
    - type: text
      text: "Your text here"
      styles: {}
```

### Heading

```yaml
- id: "block-uuid"
  type: heading
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
    level: 2
    isToggleable: false
  content:
    - type: text
      text: "Section Title"
      styles: {}
```

### Quote

```yaml
- id: "block-uuid"
  type: quote
  props:
    backgroundColor: default
    textColor: default
  content:
    - type: text
      text: "Quoted text"
      styles: {}
```

---

## Executable Blocks (no content field)

### Script Block

```yaml
- id: "block-uuid"
  type: script
  props:
    interpreter: zsh
    name: "my-script"
    code: |-
      echo "Hello"
      echo "World"
    outputVariable: result_var
    outputVisible: true
    dependency: null
```

**Interpreters**: `zsh`, `bash`, `sh`, `fish`, `python`, `node`, `ruby`, `perl`

### Run Block (Terminal)

```yaml
- id: "block-uuid"
  type: run
  props:
    type: terminal
    name: "terminal-name"
    code: |-
      ./start-server.sh
    pty: true
    global: false
    outputVisible: true
    dependency: null
    terminalRows: 10
```

### HTTP Block

```yaml
- id: "block-uuid"
  type: http
  props:
    name: "api-call"
    request:
      method: GET
      url: "https://api.example.com/data"
      headers:
        Authorization: "Bearer {{var.token}}"
```

---

## Variable System

### Define Variable

```yaml
- id: "block-uuid"
  type: var
  props:
    name: api_key
    value: "sk-xxxxx"
```

### Display Variable

```yaml
- id: "block-uuid"
  type: var_display
  props:
    name: api_key
```

### Use in Templates

Reference with double braces: `{{var.variable_name}}`

---

## Critical Formatting Rules

1. **No YAML document markers** - Don't start with `---`
2. **List item alignment** - Items at same indent as parent key
3. **Multi-line strings** - Use block scalar `|-`
4. **Trailing paragraph** - All documents end with empty paragraph
5. **Props before content** - Always in this order
6. **No content on script/var** - These blocks store data in props only

---

## Agent Workflow

| Agent | Uses This Skill For |
|-------|---------------------|
| Requirements Analyst | Capturing runbook requirements in PRD |
| Architect | Designing runbook structure in TDD |
| Principal Engineer | Generating valid .atrb files |
| QA/Adversary | Validating .atrb structure and content |

---

## Progressive Disclosure

**Detailed References**:
- [spec/block-types.md](spec/block-types.md) - Complete block type specifications
- [spec/formatting-rules.md](spec/formatting-rules.md) - YAML formatting requirements
- [spec/template-variables.md](spec/template-variables.md) - Variable interpolation

**Examples**:
- [examples/minimal.atrb](examples/minimal.atrb) - Simplest valid document
- [examples/comprehensive.atrb](examples/comprehensive.atrb) - All features demonstrated

**Validation**:
- [validation/checklist.md](validation/checklist.md) - QA validation checklist
- [validation/common-pitfalls.md](validation/common-pitfalls.md) - Known issues and fixes

**Agent Integration**:
- [agent-guidance.md](agent-guidance.md) - Agent-specific workflows

---

## Cross-Skill Integration

- [standards](../standards/SKILL.md) - YAML conventions, file organization
- [documentation](../documentation/SKILL.md) - PRD/TDD when runbooks are the deliverable
