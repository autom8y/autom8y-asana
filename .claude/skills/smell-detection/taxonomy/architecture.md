# Architecture Smells (AR-*)

> Structural issues that affect system design and maintainability.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Leaky Abstraction | AR-LEAK | Implementation details exposed | Internal errors bubbling to API |
| Tight Coupling | AR-COUPLE | Excessive dependencies between modules | Module A calls 15 functions from B |
| Layer Violation | AR-LAYER | Wrong-direction dependencies | Domain importing from UI |
| Missing Abstraction | AR-MISSING | Repeated patterns without encapsulation | Same try/catch in every handler |
| Shotgun Surgery | AR-SHOT | One change requires many file edits | Adding field touches 10 files |
| Divergent Change | AR-DIVERGE | One file changes for many reasons | `utils.ts` edited every sprint |

## Detection Heuristics

### AR-LEAK: Leaky Abstraction

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Error type analysis, API response schemas | Check if internal error types appear in public APIs |
| **Semi-Automated** | Boundary testing | Test API responses for implementation details |
| **Manual** | Design review | Assess if abstraction hides or exposes internals |

### AR-COUPLE: Tight Coupling

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Dependency graph: edge count analysis | Count import statements between modules |
| **Semi-Automated** | Coupling metrics (CBO - Coupling Between Objects) | Calculate coupling scores; flag high values |
| **Manual** | Architecture review | Assess if coupling is appropriate for domain |

### AR-LAYER: Layer Violation

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Import path rules, layer definitions | Define layer rules; grep for violations |
| **Semi-Automated** | Dependency direction analysis | Visualize dependency graph; check for upward dependencies |
| **Manual** | Architecture diagram comparison | Compare actual imports with intended architecture |

### AR-MISSING: Missing Abstraction

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Pattern detection: similar code structures | Use AST to find repeated patterns |
| **Semi-Automated** | Refactoring candidate identification | Identify code that could be extracted to shared utility |
| **Manual** | Design session | Discuss whether pattern represents reusable abstraction |

### AR-SHOT: Shotgun Surgery

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Git history: files changed together | `git log --pretty=format: --name-only \| sort \| uniq -c` |
| **Semi-Automated** | Change coupling analysis | Measure how often files change in same commit |
| **Manual** | Feature-level review | Assess if changes should be localized |

### AR-DIVERGE: Divergent Change

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Git history: change frequency per file | Count commits touching each file |
| **Semi-Automated** | Reason analysis | Categorize commits by reason (feature, bug, refactor) |
| **Manual** | Responsibility review | Assess if file has multiple unrelated responsibilities |

## Usage Guidance

### Detection Order

1. Run automated dependency and coupling analysis tools
2. Review git history for change patterns
3. Manually assess architectural alignment with design intent

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| AR-LEAK | Intentional transparency | Some abstractions intentionally expose internals (e.g., database ORMs) |
| AR-COUPLE | Domain cohesion | High coupling within a bounded context may be appropriate |
| AR-LAYER | Practical compromises | Strict layering may be relaxed for performance or pragmatism |
| AR-MISSING | Over-abstraction risk | Not every pattern needs extraction; YAGNI principle applies |
| AR-SHOT | Cross-cutting concerns | Logging, auth, error handling legitimately touch many files |
| AR-DIVERGE | Coordinator modules | Entry points, routers naturally change for multiple reasons |

### Refactoring Strategies

| Smell | Refactoring Approach |
|-------|---------------------|
| AR-LEAK | Introduce facade, map internal types to external DTOs |
| AR-COUPLE | Apply dependency inversion, use events/messaging for decoupling |
| AR-LAYER | Refactor imports, introduce anti-corruption layer |
| AR-MISSING | Extract to shared utility, introduce design pattern |
| AR-SHOT | Consolidate related changes, introduce central abstraction |
| AR-DIVERGE | Split file by responsibility, apply single responsibility principle |

### Architectural Patterns for Prevention

| Pattern | Prevents | How |
|---------|----------|-----|
| **Dependency Inversion** | AR-COUPLE, AR-LAYER | High-level modules don't depend on low-level modules |
| **Facade** | AR-LEAK | Hide complex subsystems behind simple interface |
| **Repository** | AR-LEAK | Isolate data access details from business logic |
| **Strategy** | AR-DIVERGE | Separate algorithms from context |
| **Observer** | AR-SHOT | Decouple change notification from change handling |
| **Bounded Context** | AR-COUPLE | Define clear boundaries between subsystems |

### Integration with Severity

Architecture smells typically have **high-to-critical** severity because:
- **High impact**: Architectural issues affect entire system
- **Medium-high frequency**: Poor architecture compounds over time
- **High blast radius**: Changes ripple across many modules
- **High fix complexity**: Architectural refactoring is risky and time-consuming

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **IM-CIRC**: Circular dependencies are often symptom of tight coupling
- **CX-GOD**: God objects violate single responsibility, leading to divergent change
- **DRY-COPY**: Duplication may indicate missing abstraction
- **AR-SHOT** and **AR-DIVERGE** are inverses: many files for one change vs. one file for many changes
