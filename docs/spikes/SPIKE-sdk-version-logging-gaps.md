# SPIKE: SDK Version Pinning & Logging Convention Gaps

**Date**: 2026-02-13
**Status**: Complete
**Timebox**: 30 minutes
**Decision Informed**: Whether to upgrade SDK dependencies, add Ruff rules, and migrate remaining stdlib logger files

---

## Question

What is the current state of autom8_asana's SDK dependency versions, mypy type visibility, Ruff logging rules, and stdlib logger holdouts — and what actions are safe to take vs. require design decisions?

## Context

Cross-pollination analysis from autom8_data's adapter hardening work (autom8y-log v0.4.0, autom8y-auth v1.0.1) identified potential gaps in autom8_asana. The key tension: autom8_asana deliberately uses `%s` lazy formatting (FR-LOG-005), while autom8_data mandates f-strings. Tooling rules must respect this difference.

---

## Findings

### Gap 1: SDK Version Pinning (CRITICAL)

| Package | pyproject.toml spec | Locked version | Target |
|---------|-------------------|----------------|--------|
| autom8y-auth | `>=1.0.0` | **1.0.0** | >=1.0.1 |
| autom8y-log | `>=0.3.2` | **0.3.2** | >=0.4.0 |
| autom8y-telemetry | `>=0.2.0` | 0.2.0 | (check if update needed) |

**Risk**: autom8y-auth 1.0.0 has a TypeError crash in JWT validation. autom8y-log 0.3.2 lacks the adapter hardening that safely handles `*args` positional formatting.

**Action**: `uv lock --upgrade-package autom8y-auth --upgrade-package autom8y-log` to pull latest. No pyproject.toml changes needed — floor specs already allow newer versions.

### Gap 2: mypy SDK Visibility

All three SDKs ship `py.typed` markers:

| Package | py.typed | ignore_missing_imports | Action |
|---------|----------|----------------------|--------|
| autom8y_auth | Yes | **Not ignored** (good) | None |
| autom8y_log | Yes | **Not ignored** (good) | None |
| autom8y_telemetry | Yes | **Ignored** (line 118-119) | **Remove override** |

**Finding**: `autom8y_telemetry.*` is unnecessarily in `ignore_missing_imports` at `pyproject.toml:118-119`. Since it ships `py.typed`, mypy can resolve its types. Removing this will surface any type errors that are currently hidden.

**Action**: Remove the `autom8y_telemetry.*` override from `[[tool.mypy.overrides]]`. Run `mypy` to verify no new errors surface.

### Gap 3: Ruff Logging Rules

Current select: `["E", "F", "I", "UP", "B"]`

Missing rule groups:

| Rule Group | Purpose | Recommendation |
|-----------|---------|---------------|
| `G` (flake8-logging-format) | Logging format string checks | Add with exceptions |
| `LOG` (flake8-logging) | Logging best practices | Add |

**Key nuance for `G` rules**:
- `G001` (logging-string-concat): **Enable** — catches `logger.info("msg" + var)` which is always wrong
- `G002` (logging-percent-format): **SKIP** — this IS the intended pattern per FR-LOG-005
- `G003` (logging-string-format): **Enable** — catches `logger.info("msg {}".format(var))`
- `G004` (logging-f-string): **SKIP** — autom8_asana's lazy formatting philosophy means `%s` is preferred over f-strings

**Action**: Add to ruff select, ignore G002 and G004:
```toml
select = ["E", "F", "I", "UP", "B", "G", "LOG"]
ignore = [
    ...existing...
    "G002",   # %-format in logging is intentional (FR-LOG-005 lazy formatting)
    "G004",   # f-string in logging - we prefer lazy %s formatting
]
```

### Gap 4: Semgrep

**Finding**: No Semgrep configuration exists in this repo. This is correct.

**Recommendation**: Do NOT port autom8_data's `no-logger-positional-args` Semgrep rule. It prohibits the `%s` pattern that autom8_asana intentionally uses.

If Semgrep is added later, target stdlib logger misuse instead:
- Flag `logging.getLogger()` in non-infrastructure code (should use `from autom8_asana.core.logging import get_logger`)
- Flag direct `import logging` in production modules (should go through SDK)

### Gap 5: Stdlib Logger Files

**7 files** reference stdlib `logging` (not 5 as initially estimated):

| File | Usage Pattern | Migrate? |
|------|--------------|----------|
| `core/logging.py` | SDK wrapper module (re-exports autom8y_log) | No — this IS the SDK entry point |
| `_defaults/log.py` | Intentional stdlib fallback provider | No — fallback by design |
| `cache/models/events.py` | Docstring example only (`>>> import logging`) | No — not runtime code |
| `api/middleware.py` | Uses `logging.Logger` type hint + structlog | **Yes** — should use SDK logger |
| `automation/polling/cli.py` | `logging.basicConfig()` for CLI startup | **Yes** — cohesive module |
| `automation/polling/structured_logger.py` | `logging.basicConfig()`, `logging.getLogger()` | **Yes** — cohesive module |
| `automation/polling/polling_scheduler.py` | `logging.basicConfig()` in `__main__` | **Yes** — cohesive module |

**4 files to migrate**, of which 3 are in the same `automation/polling/` module and should be migrated together.

**Note**: `middleware.py` is borderline — it imports both `structlog` (for actual logging) and `logging` (for the `Logger` type hint in `_logger: logging.Logger`). The structlog usage may be intercepted by autom8y-log's `intercept_stdlib=True` already.

### SDK Logger Adoption

| Metric | Count |
|--------|-------|
| Files using SDK logger (`core.logging` or `autom8y_log`) | **147** |
| Files referencing stdlib `logging` | **7** (4 genuine, 2 infra, 1 docstring) |
| SDK adoption rate | **~97%** |

---

## Recommendation

### Immediate (no design decision needed)

1. **Upgrade SDK lockfile**: `uv lock --upgrade-package autom8y-auth --upgrade-package autom8y-log`
2. **Remove mypy override**: Delete `autom8y_telemetry.*` from `ignore_missing_imports`

### Short-term (low risk, clear action)

3. **Add Ruff G/LOG rules**: Add `"G"` and `"LOG"` to select, ignore `G002` and `G004`
4. **Migrate middleware.py**: Replace `logging.Logger` type with SDK logger

### Medium-term (cohesive unit of work)

5. **Migrate polling module**: Convert `cli.py`, `structured_logger.py`, `polling_scheduler.py` as a single PR

### Do NOT do

6. **Do NOT port Semgrep rules** from autom8_data — they conflict with FR-LOG-005
7. **Do NOT migrate `_defaults/log.py`** — intentional stdlib fallback

---

## Follow-up Actions

- [ ] Verify autom8y-auth v1.0.1 and autom8y-log v0.4.0 are published to CodeArtifact
- [ ] After lockfile upgrade, run full test suite to verify no regressions
- [ ] After removing mypy override, run `mypy` to surface any hidden type errors
- [ ] After adding Ruff G/LOG rules, run `ruff check` to see violations (expect 0 for G002/G004 since ignored)
- [ ] Create ticket for polling module stdlib migration (WS-LOG-001)
