# Common Pitfalls

> Lessons learned from .atrb file generation

## Format Errors

### Adding `content` to script/var blocks

**Wrong**:
```yaml
- id: "script-1"
  type: script
  props:
    interpreter: bash
    code: "echo hello"
  content: []  # WRONG - script blocks don't have content
```

**Right**:
```yaml
- id: "script-1"
  type: script
  props:
    interpreter: bash
    name: "my-script"
    code: |-
      echo hello
    outputVariable: null
    outputVisible: true
    dependency: null
```

### Wrong list indentation

**Wrong**:
```yaml
content:
  - id: "block-1"  # Indented too far
```

**Right**:
```yaml
content:
- id: "block-1"  # Same level as parent key
```

### Missing trailing paragraph

**Wrong**:
```yaml
content:
- id: "last-heading"
  type: heading
  # Document ends here - missing trailing paragraph
```

**Right**:
```yaml
content:
- id: "last-heading"
  type: heading
  # ...
- id: "trailing"
  type: paragraph
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
  content: []
```

---

## Property Errors

### Adding textAlignment to quote blocks

**Wrong**:
```yaml
- type: quote
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left  # WRONG - quote doesn't support this
```

**Right**:
```yaml
- type: quote
  props:
    backgroundColor: default
    textColor: default
```

### Wrong props order

**Wrong**:
```yaml
props:
  level: 2
  backgroundColor: default  # Should come first
  textColor: default
```

**Right**:
```yaml
props:
  backgroundColor: default
  textColor: default
  textAlignment: left
  level: 2
  isToggleable: false
```

---

## String Errors

### Inline multi-line code

**Wrong**:
```yaml
code: "echo hello
echo world"
```

**Right**:
```yaml
code: |-
  echo hello
  echo world
```

### Unquoted template variables

**Wrong**:
```yaml
url: {{var.base_url}}/path  # Unquoted
```

**Right**:
```yaml
url: "{{var.base_url}}/path"
```

---

## Semantic Errors

### Using variable before definition

**Wrong**:
```yaml
content:
- id: "use-var"
  type: script
  props:
    code: "echo {{var.my_var}}"  # Used here
- id: "define-var"
  type: var
  props:
    name: my_var  # Defined after use
    value: "hello"
```

**Right**:
```yaml
content:
- id: "define-var"
  type: var
  props:
    name: my_var  # Define first
    value: "hello"
- id: "use-var"
  type: script
  props:
    code: "echo {{var.my_var}}"  # Then use
```

### Invalid dependency reference

**Wrong**:
```yaml
- id: "script-2"
  type: script
  props:
    dependency: "nonexistent-block"  # Block doesn't exist
```

---

## Markdown Conversion Errors

### Converting code blocks to paragraph

When converting markdown, code blocks should become `script` blocks, not paragraphs:

**Source Markdown**:
```markdown
```bash
echo "hello"
```
```

**Wrong**:
```yaml
- type: paragraph
  content:
    - type: text
      text: "echo \"hello\""
```

**Right**:
```yaml
- type: script
  props:
    interpreter: bash
    name: "script-1"
    code: |-
      echo "hello"
```

### Losing heading levels

Preserve heading hierarchy from markdown:

- `# Title` -> `level: 1`
- `## Section` -> `level: 2`
- `### Subsection` -> `level: 3`
