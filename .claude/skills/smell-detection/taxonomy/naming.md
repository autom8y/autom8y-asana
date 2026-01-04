# Naming Inconsistencies (NM-*)

> Terminology drift, misleading identifiers, and convention violations.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Inconsistent Naming | NM-INCONSIST | Same concept with different names | `user`, `account`, `member` for same entity |
| Misleading Names | NM-MISLEAD | Names that don't match behavior | `getUser()` that modifies state |
| Convention Violations | NM-CONV | Breaks project naming rules | `camelCase` in `snake_case` codebase |
| Abbreviation Soup | NM-ABBREV | Excessive or inconsistent abbreviations | `usr`, `usrAcct`, `userAccount` |
| Type-Name Mismatch | NM-TYPE | Variable name doesn't match type | `const user: Account = ...` |

## Detection Heuristics

### NM-INCONSIST: Inconsistent Naming

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Symbol extraction + clustering | Extract all identifiers; cluster by semantic similarity |
| **Semi-Automated** | Synonym detection | Use NLP or word similarity to find synonyms |
| **Manual** | Domain expert review | Validate that concepts truly represent same entity |

### NM-MISLEAD: Misleading Names

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Static analysis: side effects in getters | Flag methods named `get*` that mutate state |
| **Semi-Automated** | Behavior analysis | Compare function name with operations performed |
| **Manual** | Code review patterns | Look for verbs that don't match actions (e.g., `calculate` that doesn't compute) |

### NM-CONV: Convention Violations

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint naming rules, custom regex | Enforce camelCase, PascalCase, UPPER_CASE conventions |
| **Semi-Automated** | Convention documentation | Document project conventions; scan for violations |
| **Manual** | Project-specific rules | Review context-specific naming patterns |

### NM-ABBREV: Abbreviation Soup

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Abbreviation dictionary check | Flag identifiers with inconsistent abbreviations |
| **Semi-Automated** | Consistency analysis | Group similar abbreviations; identify outliers |
| **Manual** | Team glossary alignment | Verify abbreviations match team's shared vocabulary |

### NM-TYPE: Type-Name Mismatch

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | TypeScript: type vs. name comparison | Compare variable name with type annotation |
| **Semi-Automated** | Semantic analysis | Check if name suggests different type than declared |
| **Manual** | Intent verification | Confirm whether mismatch is intentional or error |

## Usage Guidance

### Detection Order

1. Run automated naming convention checks (ESLint, TypeScript)
2. Analyze identifier patterns for inconsistencies
3. Manually review domain terminology alignment

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| NM-INCONSIST | Domain-driven design bounded contexts | Different contexts may intentionally use different terms |
| NM-MISLEAD | Historical naming | Legacy APIs may have misleading names for compatibility |
| NM-CONV | Third-party integrations | External APIs may dictate naming conventions |
| NM-ABBREV | Established domain abbreviations | Industry-standard abbreviations (e.g., URL, HTTP) are acceptable |
| NM-TYPE | Polymorphism | Variable may hold subtype of declared type |

### Refactoring Strategies

| Smell | Refactoring Approach |
|-------|---------------------|
| NM-INCONSIST | Establish ubiquitous language; rename consistently across codebase |
| NM-MISLEAD | Rename to match behavior (e.g., `getUser` -> `fetchUser`, `getUserOrCreate`) |
| NM-CONV | Apply automated refactoring to align with conventions |
| NM-ABBREV | Define abbreviation standards; expand or standardize abbreviations |
| NM-TYPE | Rename variable to match type or adjust type to match intent |

### Naming Convention Examples

| Convention | When to Use | Example |
|------------|-------------|---------|
| **camelCase** | Variables, functions (JS/TS) | `getUserById`, `currentUser` |
| **PascalCase** | Classes, types, interfaces | `UserAccount`, `EmailValidator` |
| **snake_case** | Variables, functions (Python, Ruby) | `get_user_by_id`, `current_user` |
| **UPPER_SNAKE_CASE** | Constants | `MAX_RETRY_COUNT`, `API_BASE_URL` |
| **kebab-case** | File names, CSS classes | `user-account.ts`, `btn-primary` |

### Integration with Severity

Naming inconsistencies typically have **low-to-medium** severity because:
- **Medium impact**: Poor names reduce code comprehension
- **Medium-high frequency**: Naming issues accumulate over time
- **Medium-high blast radius**: Names used across multiple files
- **Low-medium fix complexity**: Renaming is safe with modern IDEs

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **AR-MISSING**: Missing abstractions often result in generic names (e.g., `data`, `info`)
- **CX-GOD**: God objects often have vague names (e.g., `Manager`, `Helper`, `Utils`)
- **DRY-PARA**: Parallel implementations may have inconsistent naming
