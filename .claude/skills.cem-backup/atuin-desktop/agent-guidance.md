# Agent-Specific Guidance

> How each agent uses this skill

## Requirements Analyst

When runbooks are part of requirements:

### In PRD

Capture runbook requirements as functional requirements:

```markdown
| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-010 | Runbook includes setup section | Must | Has heading level 1 "Setup" |
| FR-011 | Runbook defines environment variables | Must | Var blocks for API_KEY, BASE_URL |
| FR-012 | Runbook includes health check | Should | Script block that curls /health |
```

### Questions to Clarify

- What interpreters are available in target environment?
- Are there sensitive values that need secure handling?
- What's the expected execution order / dependencies?
- Will runbook be forked from existing document?

---

## Architect

When designing runbook structure:

### In TDD

Define runbook architecture:

```markdown
## Runbook Structure

### Sections
1. **Header** - Title, version info
2. **Variables** - Environment configuration
3. **Setup** - Prerequisites and installation
4. **Main Process** - Core workflow steps
5. **Validation** - Health checks and verification

### Dependencies
- `install-deps` script must complete before `run-tests`
- `get-token` script captures `auth_token` variable for subsequent HTTP calls

### Block Types Used
- `var`: Configuration values
- `script` (bash): System commands
- `script` (python): Data processing
- `http`: API calls
- `run`: Interactive terminal for debugging
```

### ADR Considerations

Document decisions about:
- Interpreter choice (bash vs zsh vs python)
- Variable vs script for sensitive values
- Monolithic vs modular runbook structure
- Dependency chain design

---

## Principal Engineer

When implementing runbooks:

### Generation Workflow

1. Read full spec: `spec/block-types.md`
2. Review examples: `examples/comprehensive.atrb`
3. Generate structure following formatting rules
4. Validate against checklist

### Code Generation Pattern

```python
def generate_atrb(name: str, blocks: list[dict]) -> str:
    """Generate valid .atrb content."""
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "version": 1,
        "forkedFrom": None,
        "content": blocks + [empty_paragraph()]
    }
    return yaml.dump(doc, default_flow_style=False, sort_keys=False)

def empty_paragraph() -> dict:
    """Required trailing paragraph."""
    return {
        "id": str(uuid.uuid4()),
        "type": "paragraph",
        "props": {
            "backgroundColor": "default",
            "textColor": "default",
            "textAlignment": "left"
        },
        "content": []
    }
```

### Markdown-to-ATRB Conversion

| Markdown | ATRB Block |
|----------|------------|
| `# Heading` | `heading` level 1 |
| `## Heading` | `heading` level 2 |
| Paragraph text | `paragraph` |
| `> Quote` | `quote` |
| ` ```lang code``` ` | `script` with interpreter |
| None | `var` (from metadata/frontmatter) |

---

## QA/Adversary

When validating runbooks:

### Test Plan Approach

1. **Structural Tests**
   - Parse YAML successfully
   - All required fields present
   - Block IDs unique

2. **Format Tests**
   - List indentation correct
   - Multi-line strings properly formatted
   - Props in correct order

3. **Semantic Tests**
   - Variables defined before use
   - Dependencies reference valid blocks
   - Interpreter strings valid

4. **Behavioral Tests** (if Atuin Desktop available)
   - File loads without error
   - Scripts execute successfully
   - Variables interpolate correctly

### Validation Script

```bash
# Quick structural validation
yq eval '.content | length' runbook.atrb  # Has content
yq eval '.content[-1].type' runbook.atrb  # Ends with paragraph
yq eval '.content[-1].content | length' runbook.atrb  # Empty content
```

### Common Defects to Check

See `validation/common-pitfalls.md` for known issues:
- `content` field on script/var blocks
- Missing trailing paragraph
- Wrong list indentation
- `textAlignment` on quote blocks
