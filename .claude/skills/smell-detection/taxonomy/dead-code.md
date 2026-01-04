# Dead Code Smells (DC-*)

> Code that is not executed, not reachable, or serves no purpose.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Unused Functions | DC-FN | Functions with zero call sites | `function formatPhone() {}` never called |
| Unused Variables | DC-VAR | Variables declared but never read | `const temp = x;` never used |
| Unreachable Code | DC-UNREACH | Code after unconditional return/throw | Code after `return` statement |
| Orphaned Modules | DC-MOD | Files with no imports | `legacy-utils.ts` imported nowhere |
| Zombie Imports | DC-IMP | Imports whose symbols are unused | `import { foo } from 'bar'` where `foo` unused |
| Dead Branches | DC-BRANCH | Conditional branches that can never execute | `if (false) { ... }` |
| Commented Code | DC-COMMENT | Commented-out code blocks | `// function oldImplementation() { ... }` |

## Detection Heuristics

### DC-FN: Unused Functions

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `grep -rn "function_name" --include='*.ts'` counts < 2 (declaration only) | Works for simple cases; may miss dynamic calls |
| **Semi-Automated** | AST analysis with tree-sitter | Parse call graph; handle cross-module references |
| **Manual** | Review exported functions across module boundaries | Check if exports are actually consumed externally |

### DC-VAR: Unused Variables

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint `no-unused-vars`, TypeScript compiler warnings | High confidence for local variables |
| **Semi-Automated** | Variable shadowing analysis | Identify cases where inner scope shadows unused outer variable |
| **Manual** | Dynamic property access patterns | Check for `obj[varName]` patterns that compilers miss |

### DC-UNREACH: Unreachable Code

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | TypeScript `--noUnusedLocals`, ESLint `no-unreachable` | Detects code after return/throw |
| **Semi-Automated** | Control flow analysis | Identify unreachable branches in switch/if statements |
| **Manual** | Exception-based flow patterns | Review error handling paths that might hide unreachable code |

### DC-MOD: Orphaned Modules

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Build dependency graph, find zero-incoming-edge nodes | Use `madge --orphans` or similar tools |
| **Semi-Automated** | Bundle analyzer output | Check what's included in production builds |
| **Manual** | Test-only modules, conditional imports | Review modules that may be loaded conditionally |

### DC-IMP: Zombie Imports

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint `no-unused-imports`, TypeScript errors | High confidence for named imports |
| **Semi-Automated** | Re-export chains | Trace through barrel files to find unused chains |
| **Manual** | Dynamic imports, type-only imports | Check for side-effect imports or type-only usage |

### DC-BRANCH: Dead Branches

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Static analysis: constant conditions | Look for `if (false)`, `if (true)` patterns |
| **Semi-Automated** | Feature flag analysis | Identify permanently disabled feature flags |
| **Manual** | A/B test remnants | Review experiment branches that are no longer active |

### DC-COMMENT: Commented Code

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Grep for multi-line comment blocks with code patterns | `grep -E "^\s*//.*\{" file.ts` |
| **Semi-Automated** | Diff against recent commits | Check if commented code was recently active |
| **Manual** | Documentation vs. dead code | Distinguish explanatory comments from disabled code |

## Usage Guidance

### Detection Order

1. Run automated checks first (ESLint, TypeScript, grep patterns)
2. Review semi-automated output for false positives
3. Manually inspect edge cases flagged by tools

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| DC-FN | Exported API functions | Check package.json exports or index.ts |
| DC-VAR | Function parameters | Verify if parameter is required by interface |
| DC-MOD | Entry point modules | Check package.json main/bin fields |
| DC-IMP | Side-effect imports | Look for module initialization side effects |
| DC-COMMENT | Commented examples | Check for "Example:" or "Usage:" prefix |

### Integration with Severity

Dead code typically has **low-to-medium** severity because:
- **Low impact**: Doesn't affect runtime behavior
- **Medium frequency**: Can accumulate over time
- **Low blast radius**: Usually isolated to single file
- **Low fix complexity**: Safe to delete after verification

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **DRY-TEST**: Test duplication may indicate dead test code
- **AR-DIVERGE**: Frequently changed files may accumulate dead branches
- **PR-SKIP**: Disabled tests are similar to commented code
