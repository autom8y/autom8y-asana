# Complexity Hotspots (CX-*)

> Code that is excessively complex or difficult to understand.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| High Cyclomatic | CX-CYCLO | Functions with many decision points | Function with 15+ branches |
| Deep Nesting | CX-NEST | Excessive indentation levels | 5+ levels of nesting |
| God Object | CX-GOD | Classes/modules with too many responsibilities | 2000+ line file |
| Long Parameter List | CX-PARAM | Functions with many parameters | `function foo(a, b, c, d, e, f, g)` |
| Boolean Blindness | CX-BOOL | Multiple boolean parameters | `createUser(true, false, true)` |
| Primitive Obsession | CX-PRIM | Using primitives instead of domain types | Passing `string` for email everywhere |
| Feature Envy | CX-ENVY | Method using more of another class's data | Function mostly accessing external state |

## Detection Heuristics

### CX-CYCLO: High Cyclomatic Complexity

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `eslint-plugin-complexity`, `lizard` | Set threshold: 10+ for warning, 15+ for error |
| **Semi-Automated** | Threshold adjustment per codebase | Review complexity distribution; adjust for domain |
| **Manual** | Acceptable vs. excessive for domain | Business logic complexity may be inherent |

### CX-NEST: Deep Nesting

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint `max-depth`, AST depth analysis | Typical threshold: 4-5 levels |
| **Semi-Automated** | Context-dependent thresholds | Some domains need deeper nesting |
| **Manual** | Callback hell vs. necessary logic | Distinguish architectural issue from domain complexity |

### CX-GOD: God Object

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `wc -l *.ts \| sort -rn`, LOC analysis | Flag files >500 lines; investigate >1000 lines |
| **Semi-Automated** | Cohesion metrics | Measure how related methods are to each other |
| **Manual** | Single responsibility assessment | Evaluate if class/module has one clear purpose |

### CX-PARAM: Long Parameter List

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint `max-params`, function signature scan | Typical threshold: 4-5 parameters |
| **Semi-Automated** | Parameter object candidates | Identify groups of related parameters |
| **Manual** | API stability concerns | Consider backward compatibility before refactoring |

### CX-BOOL: Boolean Blindness

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Grep for multiple `true`/`false` args | `grep -rn "function.*true.*false"` |
| **Semi-Automated** | Enum refactoring candidates | Identify boolean combinations that could be enums |
| **Manual** | Intentional flags vs. poor design | Assess if flags represent distinct modes |

### CX-PRIM: Primitive Obsession

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Type analysis: primitive frequency | Count `string`, `number` in type signatures |
| **Semi-Automated** | Domain model review | Identify candidates for value objects (Email, Money, etc.) |
| **Manual** | Type safety vs. over-engineering | Balance abstraction with pragmatism |

### CX-ENVY: Feature Envy

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Dependency analysis: external references | Count method calls to external objects vs. internal |
| **Semi-Automated** | Cohesion metrics | Measure coupling between methods and data |
| **Manual** | Method placement review | Assess if method belongs in different class/module |

## Usage Guidance

### Detection Order

1. Run automated complexity analyzers (ESLint, lizard, SonarQube)
2. Review flagged hotspots for context-specific thresholds
3. Manually assess architectural appropriateness

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| CX-CYCLO | Complex business rules | Verify if complexity is domain-inherent vs. poor structure |
| CX-NEST | Parser/interpreter code | Deep nesting may be appropriate for AST traversal |
| CX-GOD | Framework entry points | Main files, routers may legitimately coordinate many concerns |
| CX-PARAM | Builder patterns | Intentional parameter lists for configuration |
| CX-BOOL | Feature toggles | Flags may represent independent feature switches |
| CX-PRIM | Data transfer objects | DTOs often use primitives for serialization |
| CX-ENVY | Visitor pattern | Intentional external data access |

### Refactoring Strategies

| Smell | Refactoring Approach |
|-------|---------------------|
| CX-CYCLO | Extract method, replace conditionals with polymorphism |
| CX-NEST | Early returns, extract functions, flatten with guard clauses |
| CX-GOD | Split into smaller modules, apply single responsibility principle |
| CX-PARAM | Introduce parameter object, use builder pattern |
| CX-BOOL | Replace booleans with enums or strategy pattern |
| CX-PRIM | Introduce value objects, create domain types |
| CX-ENVY | Move method to appropriate class, extract new class |

### Integration with Severity

Complexity hotspots typically have **medium-to-high** severity because:
- **High impact**: Complex code is error-prone and hard to maintain
- **Medium-high frequency**: Complexity compounds over time
- **Low-medium blast radius**: Usually localized to specific functions/modules
- **Medium-high fix complexity**: Refactoring complex code requires care and testing

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **AR-MISSING**: Missing abstractions often manifest as complexity smells
- **DRY-COPY**: Duplicated complex logic doubles the maintenance burden
- **CX-GOD** often contains **CX-CYCLO** and **CX-PARAM** smells
