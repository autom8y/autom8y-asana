# .atrb Validation Checklist

> QA/Adversary validation criteria for runbook files

## Structural Validation

### Root Document

- [ ] Has `id` field with valid UUID
- [ ] Has `name` field with non-empty string
- [ ] Has `version` field set to `1`
- [ ] Has `forkedFrom` field (null or valid UUID)
- [ ] Has `content` field as array
- [ ] No YAML document marker (`---`) at start

### Block Structure

- [ ] Every block has unique `id`
- [ ] Every block has valid `type`
- [ ] Every block has `props` object
- [ ] Content blocks have `content` array
- [ ] Non-content blocks (var, script, run) have NO `content` field

### Trailing Paragraph

- [ ] Document ends with empty paragraph block
- [ ] Final block has `content: []`

---

## Type-Specific Validation

### heading

- [ ] `level` is 1-6
- [ ] `isToggleable` is boolean
- [ ] Has `textAlignment` prop

### paragraph

- [ ] Has `textAlignment` prop
- [ ] `content` array contains valid inline elements

### quote

- [ ] Does NOT have `textAlignment` prop
- [ ] Has `backgroundColor` and `textColor` only

### var

- [ ] Has `name` prop (valid identifier)
- [ ] Has `value` prop
- [ ] Does NOT have `content` field

### var_display

- [ ] Has `name` prop referencing defined variable

### script

- [ ] `interpreter` is valid: zsh, bash, sh, fish, python, node, ruby, perl
- [ ] Has `name` prop
- [ ] Has `code` prop with block scalar format
- [ ] Does NOT have `content` field
- [ ] `outputVariable` is null or valid identifier
- [ ] `dependency` is null or valid block ID

### run

- [ ] `type` prop is `"terminal"`
- [ ] Has `name` prop
- [ ] Has `code` prop
- [ ] `pty` is boolean
- [ ] `global` is boolean
- [ ] `terminalRows` is positive integer
- [ ] Does NOT have `content` field

### http

- [ ] Has `name` prop
- [ ] Has `request` object with `method` and `url`
- [ ] `method` is valid HTTP method

---

## Formatting Validation

- [ ] List items at same indent as parent key
- [ ] Multi-line strings use `|-` block scalar
- [ ] Props in correct order (backgroundColor, textColor, textAlignment, level, isToggleable)
- [ ] Template variables use `{{var.name}}` syntax
- [ ] Strings with special characters are quoted

---

## Semantic Validation

- [ ] Variables defined before use
- [ ] Script dependencies reference existing block IDs
- [ ] Variable names are valid identifiers (alphanumeric + underscore)
- [ ] No duplicate block IDs
- [ ] No duplicate variable names

---

## Exit Criteria

A runbook passes validation when:
1. All structural checks pass
2. All type-specific checks pass for each block
3. All formatting rules followed
4. All semantic relationships valid
5. File loads successfully in Atuin Desktop (if available for testing)
