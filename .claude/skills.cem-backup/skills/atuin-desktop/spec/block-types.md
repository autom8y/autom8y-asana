# Block Types Reference

> Complete specification for all .atrb block types

## Common Properties

All blocks share these optional props:

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `backgroundColor` | string | `"default"` | Block background |
| `textColor` | string | `"default"` | Text color |

---

## Content Blocks

These blocks have a `content` array for inline text.

### paragraph

Basic text content.

**Props**:
- `backgroundColor`: string
- `textColor`: string
- `textAlignment`: `"left"` | `"center"` | `"right"` | `"justify"`

**Content**: Array of inline elements

```yaml
- id: "uuid"
  type: paragraph
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
  content:
    - type: text
      text: "Paragraph text"
      styles: {}
```

### heading

Section headers with levels 1-6.

**Props**:
- `backgroundColor`: string
- `textColor`: string
- `textAlignment`: `"left"` | `"center"` | `"right"` | `"justify"`
- `level`: 1 | 2 | 3 | 4 | 5 | 6
- `isToggleable`: boolean

**Content**: Array of inline elements

```yaml
- id: "uuid"
  type: heading
  props:
    backgroundColor: default
    textColor: default
    textAlignment: left
    level: 1
    isToggleable: false
  content:
    - type: text
      text: "Main Title"
      styles: {}
```

### quote

Blockquote content. Note: NO `textAlignment` property.

**Props**:
- `backgroundColor`: string
- `textColor`: string

**Content**: Array of inline elements

```yaml
- id: "uuid"
  type: quote
  props:
    backgroundColor: default
    textColor: default
  content:
    - type: text
      text: "Important note"
      styles: {}
```

---

## Variable Blocks

### var

Defines a variable. **No content field**.

**Props**:
- `name`: string (variable identifier)
- `value`: string (variable value)

```yaml
- id: "uuid"
  type: var
  props:
    name: api_endpoint
    value: "https://api.example.com"
```

### var_display

Displays a variable's value inline.

**Props**:
- `name`: string (variable to display)

```yaml
- id: "uuid"
  type: var_display
  props:
    name: api_endpoint
```

---

## Executable Blocks

### script

Executes code in specified interpreter. **No content field**.

**Props**:
- `interpreter`: `"zsh"` | `"bash"` | `"sh"` | `"fish"` | `"python"` | `"node"` | `"ruby"` | `"perl"`
- `name`: string (display name)
- `code`: string (block scalar, the code to run)
- `outputVariable`: string | null (capture output to variable)
- `outputVisible`: boolean (show output in UI)
- `dependency`: string | null (block ID that must complete first)

```yaml
- id: "uuid"
  type: script
  props:
    interpreter: python
    name: "fetch-data"
    code: |-
      import requests
      resp = requests.get("{{var.api_endpoint}}")
      print(resp.json())
    outputVariable: api_response
    outputVisible: true
    dependency: null
```

### run

Interactive terminal session. **No content field**.

**Props**:
- `type`: `"terminal"` (always this value)
- `name`: string (terminal name)
- `code`: string (command to run)
- `pty`: boolean (allocate pseudo-terminal)
- `global`: boolean (persist terminal across sessions)
- `outputVisible`: boolean
- `dependency`: string | null
- `terminalRows`: number (terminal height)

```yaml
- id: "uuid"
  type: run
  props:
    type: terminal
    name: "dev-server"
    code: |-
      npm run dev
    pty: true
    global: false
    outputVisible: true
    dependency: null
    terminalRows: 15
```

### http

HTTP request block.

**Props**:
- `name`: string
- `request`: object
  - `method`: `"GET"` | `"POST"` | `"PUT"` | `"DELETE"` | `"PATCH"`
  - `url`: string (supports template variables)
  - `headers`: object (key-value pairs)
  - `body`: string (for POST/PUT/PATCH)

```yaml
- id: "uuid"
  type: http
  props:
    name: "create-resource"
    request:
      method: POST
      url: "{{var.api_endpoint}}/resources"
      headers:
        Content-Type: application/json
        Authorization: "Bearer {{var.token}}"
      body: |-
        {
          "name": "{{var.resource_name}}"
        }
```

---

## Inline Content Elements

Inside `content` arrays, these element types are supported:

### text

Basic text element.

```yaml
- type: text
  text: "Plain text content"
  styles: {}
```

### Styled text

Apply formatting via styles object:

```yaml
- type: text
  text: "Bold and italic"
  styles:
    bold: true
    italic: true
```

Available styles: `bold`, `italic`, `underline`, `strikethrough`, `code`

### link

Hyperlink element:

```yaml
- type: link
  href: "https://example.com"
  content:
    - type: text
      text: "Click here"
      styles: {}
```
