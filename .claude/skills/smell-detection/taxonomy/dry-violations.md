# DRY Violations (DRY-*)

> Duplicated logic that should be consolidated.

## Smell Types

| Smell Type | ID Pattern | Description | Example |
|------------|------------|-------------|---------|
| Copy-Paste Code | DRY-COPY | Near-identical code blocks | Same validation in 3 files |
| Repeated Constants | DRY-CONST | Magic values duplicated | `timeout: 30000` in multiple places |
| Parallel Implementations | DRY-PARA | Different implementations of same concept | Two email validators |
| Config Drift | DRY-CFG | Same setting in multiple configs | `port: 3000` in dev/staging/prod |
| Test Duplication | DRY-TEST | Identical test setup/teardown | Same beforeEach in 10 test files |

## Detection Heuristics

### DRY-COPY: Copy-Paste Code

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | `jscpd` (copy-paste detector), `simian` | Set threshold to 6+ lines, 85%+ similarity |
| **Semi-Automated** | Diff similarity scoring | Compare file pairs; review borderline cases |
| **Manual** | Semantic duplication (same logic, different syntax) | Identify conceptually identical code with different names |

### DRY-CONST: Repeated Constants

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Grep for repeated literals: `grep -rn "30000"` | Focus on magic numbers, URLs, timeout values |
| **Semi-Automated** | Config file analysis | Extract constants; identify duplication candidates |
| **Manual** | Intentional vs. accidental duplication | Verify if values should actually be independent |

### DRY-PARA: Parallel Implementations

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Symbol search for similar names: `grep -rn "validate.*[Ee]mail"` | Find functions with similar naming patterns |
| **Semi-Automated** | Interface comparison | Compare function signatures and return types |
| **Manual** | Business rule alignment | Verify if implementations should be unified |

### DRY-CFG: Config Drift

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Diff config files: `diff -y dev.json prod.json` | Highlight common settings that differ |
| **Semi-Automated** | Config schema analysis | Identify fields that should be environment-independent |
| **Manual** | Environment-specific vs. duplicated | Distinguish intended differences from drift |

### DRY-TEST: Test Duplication

| Detection Type | Method | Notes |
|----------------|--------|-------|
| **Automated** | Test file structure analysis | Count identical beforeEach/afterEach blocks |
| **Semi-Automated** | Fixture comparison | Identify shared test data and setup patterns |
| **Manual** | Intentional isolation vs. duplication | Assess if tests should share setup or remain independent |

## Usage Guidance

### Detection Order

1. Run automated duplication detection tools (jscpd, simian)
2. Analyze config files and test suites for repeated patterns
3. Manually review semantic duplication that tools miss

### Common False Positives

| Smell | False Positive | How to Identify |
|-------|----------------|-----------------|
| DRY-COPY | Boilerplate code | Check if duplication is unavoidable (e.g., interface implementations) |
| DRY-CONST | Coincidental values | Verify values represent same concept vs. coincidentally equal |
| DRY-PARA | Intentional alternatives | Confirm if multiple implementations serve different use cases |
| DRY-CFG | Environment-specific settings | Distinguish configuration from drift |
| DRY-TEST | Test isolation | Ensure test independence isn't compromised by consolidation |

### Consolidation Strategies

| Smell | Refactoring Approach |
|-------|---------------------|
| DRY-COPY | Extract to shared function/module |
| DRY-CONST | Define constants in shared config or constants file |
| DRY-PARA | Unify implementations or document intentional differences |
| DRY-CFG | Use environment variables or shared base config |
| DRY-TEST | Extract test fixtures, setup helpers, or custom matchers |

### Integration with Severity

DRY violations typically have **medium-to-high** severity because:
- **High impact**: Bugs in duplicated code multiply across instances
- **High frequency**: Duplication increases maintenance burden
- **Medium-high blast radius**: Changes require coordinating multiple files
- **Low-medium fix complexity**: Refactoring is usually straightforward

See [severity/defaults.md](../severity/defaults.md) for specific default severity factors per smell type.

## Related Patterns

- **AR-MISSING**: Missing abstraction may indicate DRY violation opportunities
- **AR-SHOT**: Shotgun surgery often results from DRY violations
- **CX-GOD**: God objects may contain duplicated logic from consolidation gone wrong
