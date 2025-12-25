# YAML Formatting Rules

> Critical formatting requirements for valid .atrb files

## Document Structure

### No Document Markers

Do NOT include YAML document markers:

```yaml
# WRONG - has document marker
---
id: "uuid"
name: "My Runbook"

# CORRECT - no marker
id: "uuid"
name: "My Runbook"
```

### Required Root Fields

All four fields required, in this order:

```yaml
id: "uuid"
name: "Document Title"
version: 1
forkedFrom: null
content: []
```

---

## List Formatting

### List Item Alignment

List items align at the same indentation level as the parent key:

```yaml
# CORRECT
content:
- id: "block-1"
  type: paragraph
- id: "block-2"
  type: heading

# WRONG - extra indentation
content:
  - id: "block-1"
    type: paragraph
```

This applies to all lists: `content`, inline content arrays, headers objects.

---

## String Formatting

### Multi-line Strings

Use block scalar literal style (`|-`) for multi-line content:

```yaml
code: |-
  echo "Line 1"
  echo "Line 2"
  echo "Line 3"
```

The `|-` indicator means:
- `|` = literal block (preserve newlines)
- `-` = strip final newline

### Quoted Strings

Use quotes for strings containing special characters:

```yaml
# Safe - no special characters
name: my-script

# Required - contains template syntax
url: "https://api.com/{{var.path}}"

# Required - contains colon
title: "Setup: Initial Configuration"
```

---

## Property Ordering

### Props Object

When multiple props are present, use this order:

1. `backgroundColor`
2. `textColor`
3. `textAlignment`
4. `level`
5. `isToggleable`
6. (then type-specific props)

```yaml
props:
  backgroundColor: default
  textColor: default
  textAlignment: left
  level: 2
  isToggleable: false
```

### Block Structure

Always: `id` -> `type` -> `props` -> `content` (if applicable)

```yaml
- id: "uuid"
  type: heading
  props:
    level: 1
  content:
    - type: text
      text: "Title"
      styles: {}
```

---

## Trailing Empty Paragraph

All documents must end with an empty paragraph block:

```yaml
content:
- id: "main-content"
  type: paragraph
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
  content:
    - type: text
      text: "Main content here"
      styles: {}
- id: "trailing-para"
  type: paragraph
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
  content: []
```

This is required for Atuin Desktop compatibility.

---

## UUID Format

Use standard UUID v4 format:

```yaml
id: "550e8400-e29b-41d4-a716-446655440000"
```

Or generate with:
- Python: `str(uuid.uuid4())`
- Node: `crypto.randomUUID()`
- Shell: `uuidgen`
