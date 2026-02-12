# Automated Detection Tooling

> Reference guide for automated smell detection tools and commands.

## Overview

This document catalogs automated and semi-automated tools for detecting code smells, organized by smell category. Use this as a quick reference when implementing detection heuristics from the taxonomy.

## Tool Categories

| Detection Type | Confidence | When to Use |
|----------------|------------|-------------|
| **Automated** | High | First pass; clear signatures |
| **Semi-Automated** | Medium | Requires human judgment on tool output |
| **Manual** | Low-Medium | No reliable tooling; context-dependent |

## Dead Code Detection Tools

### DC-FN, DC-VAR: Unused Code

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'no-unused-vars: error'` | Configure in .eslintrc |
| TypeScript | TypeScript | `tsc --noUnusedLocals --noUnusedParameters` | Compiler flags |
| Pylint | Python | `pylint --enable=unused-variable,unused-argument` | Python linting |
| Go compiler | Go | `go build` | Reports unused variables/imports |
| RuboCop | Ruby | `rubocop --only Lint/UselessAssignment` | Ruby linting |

### DC-UNREACH: Unreachable Code

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'no-unreachable: error'` | Detects code after return/throw |
| TypeScript | TypeScript | `tsc --allowUnreachableCode=false` | Compiler flag |
| Pylint | Python | `pylint --enable=unreachable` | Python linting |

### DC-MOD: Orphaned Modules

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| madge | JavaScript/TypeScript | `madge --orphans src/` | Finds modules with no incoming edges |
| webpack-bundle-analyzer | JavaScript/TypeScript | `webpack-bundle-analyzer stats.json` | Check what's included in bundles |
| depcheck | JavaScript/TypeScript | `depcheck --ignore-dirs=build,dist` | Finds unused dependencies |

### DC-IMP: Zombie Imports

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule '@typescript-eslint/no-unused-vars: error'` | Includes imports |
| TypeScript | TypeScript | Compiler errors | Unused imports flagged |
| organize-imports | TypeScript | `organize-imports-cli src/**/*.ts` | Auto-remove unused |

### DC-COMMENT: Commented Code

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| grep | All | `grep -rn "^\s*//.*{" src/` | Find commented blocks |
| ESLint | JavaScript/TypeScript | Custom rule or plugin | `eslint-plugin-comment` |

## DRY Violation Detection Tools

### DRY-COPY: Copy-Paste Code

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| jscpd | All | `jscpd src/ --min-lines 6 --min-tokens 50` | Copy-paste detector |
| simian | Java, C#, others | `simian -threshold=6 src/**/*.java` | Similarity analyzer |
| PMD CPD | Java, others | `pmd cpd --minimum-tokens 50 --files src/` | Copy-paste detection |
| duplo | C, C++ | `duplo src/ -ml 6` | Duplicate code blocks |

### DRY-CONST: Repeated Constants

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| grep | All | `grep -rn "30000" src/` | Find magic numbers |
| ESLint | JavaScript/TypeScript | `eslint --rule 'no-magic-numbers: warn'` | Flag hardcoded values |
| Pylint | Python | `pylint --enable=duplicate-code` | Python duplication |

### DRY-CFG: Config Drift

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| diff | All | `diff -y config/dev.json config/prod.json` | Side-by-side comparison |
| jq | JSON configs | `diff <(jq -S . dev.json) <(jq -S . prod.json)` | Normalized JSON diff |

## Complexity Detection Tools

### CX-CYCLO: High Cyclomatic Complexity

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'complexity: [error, 10]'` | Threshold configurable |
| eslint-plugin-complexity | JavaScript/TypeScript | Plugin with detailed metrics | More granular than base ESLint |
| lizard | Multiple | `lizard -l javascript src/` | Cross-language complexity |
| SonarQube | Multiple | Web-based analysis | Full platform |
| Pylint | Python | `pylint --max-complexity=10` | Python complexity |
| gocyclo | Go | `gocyclo -over 10 .` | Go complexity |

### CX-NEST: Deep Nesting

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'max-depth: [error, 4]'` | Nesting depth limit |
| Pylint | Python | `pylint --max-nested-blocks=5` | Python nesting |

### CX-GOD: God Object

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| wc | All | `wc -l src/**/*.ts \| sort -rn \| head -20` | Lines of code per file |
| cloc | All | `cloc src/ --by-file` | Count lines by file |
| SonarQube | Multiple | Cohesion and LOC metrics | Full analysis |

### CX-PARAM: Long Parameter List

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'max-params: [error, 4]'` | Parameter count limit |
| Pylint | Python | `pylint --max-args=5` | Python parameter count |

## Naming Detection Tools

### NM-INCONSIST: Inconsistent Naming

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| grep + clustering | All | Extract identifiers, cluster by similarity | Semi-automated |
| CodeScene | Multiple | Hotspot and naming analysis | Commercial tool |

### NM-CONV: Convention Violations

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule '@typescript-eslint/naming-convention'` | Configurable rules |
| Pylint | Python | `pylint --naming-style=snake_case` | Python conventions |
| RuboCop | Ruby | `rubocop --only Naming` | Ruby conventions |
| checkstyle | Java | `checkstyle -c google_checks.xml` | Java style checker |

## Import Hygiene Detection Tools

### IM-CIRC: Circular Dependencies

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| madge | JavaScript/TypeScript | `madge --circular src/` | Visualize/detect cycles |
| dpdm | JavaScript/TypeScript | `dpdm src/index.ts` | Circular dependency detection |
| Pylint | Python | `pylint --enable=cyclic-import` | Python circular imports |

### IM-WILD: Wildcard Imports

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| ESLint | JavaScript/TypeScript | `eslint --rule 'no-restricted-imports: [error, "*"]'` | Flag wildcard imports |
| grep | All | `grep -rn "import \*" src/` | Find all wildcard imports |

### IM-VERSION: Version Skew

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| npm | JavaScript/TypeScript | `npm ls` | Show dependency tree with duplicates |
| yarn | JavaScript/TypeScript | `yarn why <package>` | Explain why package is installed |
| pip | Python | `pip list --outdated` | Python package versions |

### IM-UNUSED: Unused Dependencies

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| depcheck | JavaScript/TypeScript | `depcheck` | Find unused dependencies |
| npm-check | JavaScript/TypeScript | `npm-check` | Interactive dependency checker |
| go mod tidy | Go | `go mod tidy` | Remove unused Go dependencies |

## Architecture Detection Tools

### AR-CIRC, AR-COUPLE: Coupling Analysis

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| madge | JavaScript/TypeScript | `madge --image graph.svg src/` | Visualize dependencies |
| dependency-cruiser | JavaScript/TypeScript | `depcruise src/` | Validate architecture rules |
| jdepend | Java | `jdepend src/` | Java dependency analysis |
| SonarQube | Multiple | Coupling metrics (CBO) | Full platform |

### AR-LAYER: Layer Violation

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| dependency-cruiser | JavaScript/TypeScript | Define layer rules in config | Enforces layering |
| ArchUnit | Java | Unit tests for architecture | Java architecture testing |

## Process Detection Tools

### PR-TEST: Missing Tests

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| Jest | JavaScript/TypeScript | `jest --coverage --coverageThreshold='{"global":{"lines":80}}'` | Coverage enforcement |
| pytest | Python | `pytest --cov=src --cov-report=html --cov-fail-under=80` | Python coverage |
| go test | Go | `go test -cover -coverprofile=coverage.out` | Go coverage |

### PR-FLAKY: Flaky Tests

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| Jest | JavaScript/TypeScript | `jest --detectLeaks --maxWorkers=1` | Detect test issues |
| pytest-flakefinder | Python | `pytest --flake-finder` | Python flaky test detection |
| CI log analysis | All | Parse CI logs for intermittent failures | Semi-automated |

### PR-SLOW: Slow Tests

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| Jest | JavaScript/TypeScript | `jest --verbose` (shows timing) | Review slowest tests |
| pytest | Python | `pytest --durations=10` | Show 10 slowest tests |
| go test | Go | `go test -v -timeout 30s` | Timeout enforcement |

### PR-TODO: TODO Accumulation

| Tool | Language | Command | Notes |
|------|----------|---------|-------|
| grep | All | `grep -rn "TODO\|FIXME\|HACK\|XXX" src/` | Find all TODOs |
| leasot | JavaScript | `leasot src/**/*.js` | TODO extraction tool |
| todo-or-die | Ruby | Gem that enforces TODO deadlines | Ruby TODO enforcement |

## Cross-Language Tools

| Tool | Languages | Use Case | Command |
|------|-----------|----------|---------|
| SonarQube | 25+ languages | Comprehensive quality analysis | Web platform |
| lizard | 15+ languages | Complexity metrics | `lizard src/` |
| cloc | All | Lines of code counting | `cloc src/` |
| grep/ripgrep | All | Text pattern matching | `grep -rn "pattern" src/` |
| git blame | All | Code age analysis | `git blame file.ts` |

## Tool Installation

### JavaScript/TypeScript Ecosystem

```bash
npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install -g jscpd madge depcheck dpdm
```

### Python Ecosystem

```bash
pip install pylint pytest pytest-cov
```

### Go Ecosystem

```bash
go install github.com/fzipp/gocyclo/cmd/gocyclo@latest
```

### Cross-Language

```bash
# lizard (Python-based, works for many languages)
pip install lizard

# SonarQube (requires Docker or installation)
docker run -d --name sonarqube -p 9000:9000 sonarqube
```

## Integration with Detection Heuristics

For each smell type in the taxonomy, use the corresponding tool from this reference:

1. **Automated detection**: Run tool, parse output
2. **Semi-automated**: Review tool output, apply human judgment
3. **Manual**: Use patterns from taxonomy files

Example workflow for DRY-COPY:
```bash
# Automated: Run jscpd
jscpd src/ --min-lines 6 --min-tokens 50 --format json > duplication.json

# Semi-automated: Review jscpd output, filter false positives
jq '.duplicates[] | select(.percent > 85)' duplication.json

# Manual: Verify semantic duplication that differs syntactically
```

## Related Documentation

- [../taxonomy/](../taxonomy/) - Smell types and detection heuristics
- [smell-report.md](smell-report.md) - Documenting detection results
- [debt-ledger.md](debt-ledger.md) - Mapping smells to debt
