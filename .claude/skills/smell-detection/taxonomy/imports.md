# Import Hygiene (IM-*)

> Dependency management issues and import organization problems.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Circular Dependencies | IM-CIRC | A imports B imports A | Module A <-> Module B |
| Wildcard Imports | IM-WILD | Importing everything | `import * from 'utils'` |
| Deep Imports | IM-DEEP | Importing from internal paths | `import { x } from 'lib/internal/private'` |
| Barrel Bloat | IM-BARREL | Index files re-exporting too much | `index.ts` with 50+ exports |
| Version Skew | IM-VERSION | Same dependency at multiple versions | `lodash@4.17.0` and `lodash@4.17.21` |
| Unused Dependencies | IM-UNUSED | Package.json deps not imported | `"axios": "^1.0.0"` never used |

## Detection Heuristics

### IM-CIRC: Circular Dependencies

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `madge --circular`, `dpdm` | Generate dependency graph; detect cycles |
| **Semi-Automated** | Cycle-breaking analysis | Identify which module should be extracted to break cycle |
| **Manual** | Intentional cycles (rare) | Verify if circular dependency is architectural requirement |

### IM-WILD: Wildcard Imports

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | ESLint `no-import-all`, grep `import \*` | Flag all wildcard imports for review |
| **Semi-Automated** | Tree-shaking impact | Measure bundle size impact of wildcard imports |
| **Manual** | Performance measurement | Assess if wildcard significantly affects load time |

### IM-DEEP: Deep Imports

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Path depth analysis, internal path patterns | Grep for imports with `/internal/`, `/private/`, 3+ path segments |
| **Semi-Automated** | API boundary definition | Identify intended public API surface |
| **Manual** | Intended exposure | Verify if deep import is accessing intentionally exposed API |

### IM-BARREL: Barrel Bloat

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Export count per index file | `grep -c "export" index.ts` |
| **Semi-Automated** | Bundle impact analysis | Measure if barrel file causes unnecessary bundling |
| **Manual** | Monorepo patterns | Assess if barrel is appropriate for package structure |

### IM-VERSION: Version Skew

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `npm ls`, `yarn why`, lockfile analysis | Identify duplicate dependencies at different versions |
| **Semi-Automated** | Deduplication feasibility | Check if versions can be unified |
| **Manual** | Compatibility constraints | Verify if version differences are required |

### IM-UNUSED: Unused Dependencies

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `depcheck`, `npm-check` | Scan for dependencies not imported anywhere |
| **Semi-Automated** | Test/build dependency separation | Distinguish dev vs. production dependencies |
| **Manual** | Dynamic requires | Check for runtime-only dependencies (e.g., plugins) |

## Usage Guidance

### Detection Order

1. Run automated dependency analyzers (madge, depcheck)
2. Review import patterns and barrel file structure
3. Manually assess architectural implications

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| IM-CIRC | Type-only cycles | TypeScript type imports may create cycles without runtime issues |
| IM-WILD | Namespace imports | Some libraries designed for wildcard import (e.g., React as `import * as React`) |
| IM-DEEP | Monorepo internal paths | Deep imports may be acceptable within monorepo boundaries |
| IM-BARREL | Framework conventions | Some frameworks expect barrel files (e.g., Angular) |
| IM-VERSION | Peer dependency conflicts | Version skew may be necessary for compatibility |
| IM-UNUSED | Build tools, test runners | Dependencies used only in scripts or config files |

### Refactoring Strategies

| Smell | Refactoring Approach |
|-------|---------------------|
| IM-CIRC | Extract shared module, invert dependency direction, use dependency injection |
| IM-WILD | Replace with named imports, use namespace import only when appropriate |
| IM-DEEP | Define public API via barrel files, document public vs. private modules |
| IM-BARREL | Split into smaller barrels by domain, use lazy loading |
| IM-VERSION | Deduplicate with `npm dedupe`, update dependencies to compatible versions |
| IM-UNUSED | Remove from package.json, verify with CI that removal doesn't break builds |

### Import Best Practices

| Practice | Rationale | Example |
|----------|-----------|---------|
| **Named imports** | Explicit dependencies, better tree-shaking | `import { useState } from 'react'` |
| **Public API surface** | Clear contract, encapsulation | Export via `index.ts`, keep internals private |
| **Dependency deduplication** | Smaller bundles, consistent behavior | Single version of each dependency |
| **Import ordering** | Readability, merge conflict reduction | Standard library, external, internal (top to bottom) |
| **Absolute paths** | Refactoring-friendly | `import { User } from '@/models/user'` vs. `../../models/user` |

### Integration with Severity

Import hygiene issues typically have **medium-to-high** severity because:
- **Medium-high impact**: Circular dependencies can cause runtime errors, large bundles affect performance
- **Low-medium frequency**: Import issues accumulate slowly
- **Medium-high blast radius**: Dependency changes affect many files
- **Medium-high fix complexity**: Breaking circular dependencies can be complex

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **AR-COUPLE**: Tight coupling often manifests as import smells
- **DC-MOD**: Orphaned modules are extreme case of unused dependencies
- **DC-IMP**: Zombie imports are file-level version of unused dependencies
