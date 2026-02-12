---
name: pinakes-registry-format
description: "Format specification for Pinakes domain registration. Use when: adding new audit domains to the Pinakes, understanding criteria file structure. Triggers: add domain, registry format, domain criteria template, new audit domain."
---

# pinakes-registry-format

> Format specification for registering new theoria audit domains in the Pinakes.

## Purpose

Defines the canonical format for adding audit domains to the Pinakes. A domain is registered when it has a row in the INDEX domain registry table and a corresponding criteria file in `domains/`.

## Registration Process

### Step 1: Choose Domain Name

- **Format**: `[a-z][a-z0-9-]*` (lowercase, alphanumeric, hyphens)
- **Max Length**: 32 characters
- **Reserved**: `all`, `list`, `help`, `config`
- **Examples**: `dromena`, `legomena`, `git-hygiene`, `test-coverage`

### Step 2: Write Criteria File

Create `rites/shared/mena/pinakes/domains/{domain}.lego.md`:

```markdown
---
name: {domain}-criteria
description: "Evaluation criteria for {domain} audits. Use when: theoros is auditing {domain} domain. Triggers: {domain} audit criteria."
---

# {domain} Audit Criteria

## Scope

What files/patterns this domain covers.

## Criteria

### Criterion 1: {Name} (weight: {N}%)

**What to evaluate**: {description}

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90-100% | {what excellent looks like} |
| B | 80-89% | {what good looks like} |
| C | 70-79% | {what adequate looks like} |
| D | 60-69% | {what below standard looks like} |
| F | < 60% | {what failing looks like} |

### Criterion 2: {Name} (weight: {N}%)

{same structure}
```

### Step 3: Register in the Pinakes INDEX

Add a row to the Domain Registry table in `INDEX.lego.md`:

```markdown
| **{domain}** | `domains/{domain}.lego.md` | {scope} | {brief description} |
```

### Step 4: Validate

```bash
# Test the domain
/theoria {domain}
```

Check that:
- Criteria file loads without errors
- Grading rubric produces clear grades with evidence
- Report format follows the theoros output schema

## Criteria File Requirements

### Frontmatter (required)
- `name`: `{domain}-criteria`
- `description`: Must include "Use when:" and "Triggers:" for CC skill loading

### Body Structure
- **Scope section**: What files/patterns the domain covers (glob patterns preferred)
- **Criteria sections**: Each criterion needs name, weight, and grading rubric
- **Weights must sum to 100%** across all criteria
- **Grading rubric**: Use simple A-F letter grades aligned with the Pinakes grading scale

### Grading Scale (all domains)

| Grade | Meaning | Threshold |
|-------|---------|-----------|
| **A** | Excellent | 90-100% criteria met |
| **B** | Good | 80-89% criteria met |
| **C** | Adequate | 70-79% criteria met |
| **D** | Below Standard | 60-69% criteria met |
| **F** | Failing | Below 60% criteria met |

No +/- modifiers. Simple letter grades only.

### Scope Values

| Scope | Meaning |
|-------|---------|
| `framework` | Knossos infrastructure (agents, dromena, legomena) |
| `codebase` | Source code quality (Go, Python, shell scripts) |
| `process` | Development workflow (git, CI/CD, testing) |
| `culture` | Team practices (docs, naming, conventions) |

## Example: Complete Domain Registration

**Criteria file** (`domains/git-hygiene.lego.md`):

```markdown
---
name: git-hygiene-criteria
description: "Evaluation criteria for git hygiene audits. Use when: theoros is auditing git practices. Triggers: git hygiene audit criteria."
---

# git-hygiene Audit Criteria

## Scope

Git history, commit messages, branch structure. Evaluate via `git log`, branch naming, `.gitignore`.

## Criteria

### Criterion 1: Commit Message Quality (weight: 40%)

| Grade | Threshold | Evidence Required |
|-------|-----------|-------------------|
| A | 90%+ of commits follow convention | Sample of last 50 commits |
| B | 80-89% follow convention | Count of violations |
| C | 70-79% follow convention | List of common violations |
| D | 60-69% follow convention | Pattern analysis |
| F | < 60% follow convention | Representative failures |

### Criterion 2: Branch Hygiene (weight: 30%)
...

### Criterion 3: History Cleanliness (weight: 30%)
...
```

**INDEX registration** (add row to Domain Registry table):

```markdown
| **git-hygiene** | `domains/git-hygiene.lego.md` | process | Git practices: commit quality, branch hygiene, history |
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Criteria weights do not sum to 100% | Adjust weights to total exactly 100% |
| Using +/- grade modifiers | Use simple A-F only |
| Criteria too vague to grade | Add specific thresholds and evidence requirements |
| No glob patterns in scope | Specify exact file patterns the theoros should search |
| Missing INDEX registration | Add row to the Domain Registry table in INDEX.lego.md |

## Related

- [INDEX.lego.md](INDEX.lego.md) - The domain registry (where to register)
- [grading.lego.md](schemas/grading.lego.md) - Grading scale definitions
- [report-format.lego.md](schemas/report-format.lego.md) - Audit report structure
