---
type: review
status: closed
kit: bd9e0cdcc830
profile: a8867c41c39b
clerk_start_row: 19713
---

# A1b-check v2 receipt: STOPPED at the import gate (kit defect)

- Stamped 2026-11-01T21:07:05Z (date -u). Run 21:06:28Z to 21:06:41Z, once, on the clerk heavy START row 19713.
- Venue: sparse job-tmp clone at 3b17c1989e04. Box Toms-MacBook-Pro. Census SET (DIRENV_DIR, DIRENV_FILE presence only). Hook: defined, not wired.
- Kit exit 3 (STOP).

## Kit output (verbatim, minus three import-time log lines)

```
head=3b17c1989e04
env_census=0
ruff_check rc=0 errors=0
ruff_format rc=0 would_reformat=0
ruff_script(excluded-by-config, forced) rc=1 errors=0
mypy rc=1 errors=3
under_W=<captured log lines plus "yes"; see finding 1>
yes
STOP import_not_under_W
```

## Findings

1. **Kit defect, import gate.** `autom8_asana` emits three structured warnings to stdout at import time. The kit captured them with the boolean, so `U` was not exactly `yes` and the gate stopped. The last captured line was `yes`, so the import does resolve under the clone. The stop is the kit's, not the code's. Cure for v3: compare the last line only, or send import logging to stderr.
2. **mypy: src clean; 3 errors in the new test file.** The two src files show 0 errors (the two A1 errors are cured). All three errors are `no-untyped-def` in `tests/unit/enrollment/test_r03_phone_field_contract.py` at lines 25, 30 and 35 (parametrized test functions without annotations). Cure: annotate those three signatures (a test-only edit).
3. **Kit defect, ruff count.** The forced `scripts/` ruff check printed `Found 49 errors.` (rc 1), but the kit's line regex counted 0, because ruff's output format does not match it. 49 equals the A1 base (the A1 record read 49 at the base and 50 after A1; cure (ii) removed the extra one). Cure for v3: parse the `Found N errors` line.
4. **Not reached because of the stop:** pytest, both guard modes and the digit scan.
