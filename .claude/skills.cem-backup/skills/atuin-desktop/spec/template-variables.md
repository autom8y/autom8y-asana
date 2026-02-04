# Template Variables

> Variable interpolation in .atrb runbooks

## Syntax

Template variables use double-brace syntax:

```
{{var.variable_name}}
```

## Defining Variables

Use a `var` block:

```yaml
- id: "var-api-key"
  type: var
  props:
    name: api_key
    value: "sk-abc123"
```

## Using Variables

Reference in any string value:

```yaml
# In script code
code: |-
  curl -H "Authorization: Bearer {{var.api_key}}" https://api.example.com

# In HTTP request
url: "{{var.base_url}}/users/{{var.user_id}}"

# In headers
headers:
  Authorization: "Bearer {{var.token}}"
```

## Capturing Script Output

Script blocks can capture output to variables:

```yaml
- id: "get-token"
  type: script
  props:
    interpreter: bash
    name: "get-auth-token"
    code: |-
      echo "$(curl -s https://auth.example.com/token)"
    outputVariable: auth_token
    outputVisible: false
    dependency: null
```

Then use: `{{var.auth_token}}`

## Variable Scope

- Variables are document-scoped
- Define before use (blocks execute top-to-bottom)
- Script output variables available after script completes

## Displaying Variables

Show variable value in document:

```yaml
- id: "show-token"
  type: var_display
  props:
    name: auth_token
```

## Best Practices

1. **Define early**: Put `var` blocks near document start
2. **Descriptive names**: `api_base_url` not `url`
3. **Sensitive values**: Use script blocks to fetch secrets at runtime
4. **Chain dependencies**: Use `dependency` prop for execution order
