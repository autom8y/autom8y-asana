---
domain: feat/vertical-backfill
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/services/vertical_backfill.py"
  - "./tests/unit/services/test_vertical_backfill.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
---

# Feature Knowledge: Vertical Backfill Service

## Purpose

The Vertical Backfill Service repairs a data-quality gap: unit tasks in Asana that were created
before the `cf:Vertical` custom field was reliably populated arrive in the cache with a null or
empty `vertical` column. The service extracts the vertical value from an older, human-authored
source of truth — the plain-text `notes` field — and writes it back to the structured custom
field via the Asana API.

**Why this feature exists**: During the `remediation-vertical-investigation-spike`, two remediation
paths were evaluated (documented in service and handler docstrings as "Option A+C"). Option A is
the cache-warmer passthrough: run the backfill as a post-warm step against the already-warmed
DataFrame so that no extra API fetch of the full task list is required. Option C adds the "notes
parsing" heuristic. This combination was chosen over a DB-side migration or a full re-sync because
it is non-blocking, self-contained, and can be rolled out behind a feature flag without touching
any intake path.

**Distinguished from adjacent features**:
- `entity-resolution` (`services/universal_strategy.py`, `resolution/`) — resolves phone + vertical
  → GID for new intake; vertical-backfill does not resolve entities, it patches an existing field
  value on a known GID.
- `entity-write-api` (`api/routes/entity_write*`, `resolution/write_registry.py`) — handles
  structured field coercion at intake time; vertical-backfill operates post-warm against a cache
  snapshot, not at write-request time.
- `intake-pipeline` (`services/intake_create_service.py`) — writes `cf:Vertical` during unit
  creation via `_write_vertical_custom_field`; vertical-backfill reuses the same enum-resolution
  logic but operates in bulk against the warmed DataFrame, not on a single new task.

---

## Conceptual Model

### Core Abstractions

| Abstraction | Type | Role |
|---|---|---|
| `VerticalBackfillService` | Class (`services/vertical_backfill.py`) | Entry point; owns the backfill loop and delegates to `_backfill_single_task` |
| `BackfillResult` | Dataclass (`services/vertical_backfill.py`) | Aggregated counters: `attempted`, `succeeded`, `skipped`, `failed`, `errors` |
| `parse_vertical_from_notes` | Module-level function | Pure parser: regex scan of task notes for `"Vertical: <value>"` |
| `_VERTICAL_NOTES_RE` | Compiled regex | `(?:^|\n)\s*Vertical:\s*(.+?)(?:\n|$)`, IGNORECASE — matches first occurrence |

### Processing Lifecycle

```
DataFrame of unit tasks (from cache warmer)
  → filter: rows where vertical is null or empty AND gid is present
  → for each candidate:
      fetch task notes + custom field metadata via tasks.get_async
      parse_vertical_from_notes(notes)
        → None → skipped (logged: vertical_backfill_no_vertical_in_notes)
      locate "Vertical" CF by name (case-insensitive)
        → not found → skipped (logged: vertical_backfill_cf_not_found)
      match enum option by name (case-insensitive)
        → no match → skipped (logged: vertical_backfill_enum_option_not_found)
      tasks.update_async(gid, data={"custom_fields": {cf_gid: {"gid": enum_option_gid}}})
        → success → BackfillResult.succeeded++
        → exception → BackfillResult.failed++, error recorded
  → log vertical_backfill_complete (attempted/succeeded/skipped/failed)
```

### Task Outcomes (mutually exclusive per task)

| Outcome | Counter | Trigger |
|---|---|---|
| Not a candidate | (not counted in `attempted`) | `vertical` already non-empty, or `gid` missing |
| Succeeded | `succeeded` | CF written successfully |
| Skipped | `skipped` | No vertical in notes, CF not found on task, or enum option not matched |
| Failed | `failed` | Any exception raised during `_backfill_single_task` |

`BackfillResult.errors` accumulates `(task_gid, error_message)` tuples for failed tasks; skipped
tasks do not produce error entries.

### Enum Resolution Pattern (shared with intake-pipeline)

Both `VerticalBackfillService._backfill_single_task` and
`IntakeCreateService._write_vertical_custom_field` (line 300) follow the same three-step pattern:
1. Fetch task with `opt_fields` for custom field metadata.
2. Locate the CF named `"vertical"` (`.lower()` comparison).
3. Match the parsed value against `enum_options` by name (`.lower()` comparison) to get the
   enum option GID, then write `{cf_gid: {"gid": enum_option_gid}}`.

This is the canonical pattern for writing Asana enum custom fields in this codebase.

---

## Implementation Map

### Files

| File | Purpose | LOC |
|---|---|---|
| `src/autom8_asana/services/vertical_backfill.py` | Full feature implementation | 290 |
| `src/autom8_asana/lambda_handlers/cache_warmer.py` | Caller: `_run_vertical_backfill` function (lines 108–180); invoked at line 645 | ~750 total |
| `tests/unit/services/test_vertical_backfill.py` | Dedicated unit test cluster | ~397 |

### Key Entry Points

**`VerticalBackfillService.backfill_from_dataframe(unit_df: pl.DataFrame) -> BackfillResult`**
(line 67) — Primary public API. Accepts a Polars DataFrame of unit tasks (must contain `gid` and
`vertical` columns). Returns `BackfillResult`. Async.

**`parse_vertical_from_notes(notes: str) -> str | None`** (line 270) — Module-level pure
function. Also imported and tested independently. The only public symbol at module scope
besides the classes.

### Caller: `cache_warmer._run_vertical_backfill`

The sole production caller lives in `lambda_handlers/cache_warmer.py` at lines 108–180. It:
- Guards on `ASANA_VERTICAL_BACKFILL_ENABLED` env var (values `"1"`, `"true"`, `"yes"`; default
  disabled)
- Guards on `"unit"` being in `completed_entities` (only runs after unit DataFrame is warmed)
- Fetches the warmed DataFrame from `DataFrameCache`
- Instantiates `VerticalBackfillService(client=client)` with a lazy import to avoid circular
  load at cold-start
- Wraps the entire call in a broad `except Exception` so backfill failures never fail the
  Lambda invocation (BROAD-CATCH isolation pattern)

**No HTTP routes expose this service** — it is Lambda-internal only.

### Data Flow

```
cache_warmer Lambda invocation
  → warm all entity types (cache_warmer main loop)
  → Phase 5a complete: completed_entities includes "unit"
  → _run_vertical_backfill() [lines 638–651 in cache_warmer.py]
      → DataFrameCache.get_async(project_gid, "unit") → CacheEntry.dataframe
      → VerticalBackfillService.backfill_from_dataframe(entry.dataframe)
          → tasks.get_async(gid, opt_fields=[notes, custom_fields.*])  [per candidate]
          → tasks.update_async(gid, data={...})  [on success]
      → log vertical_backfill_result
```

### Test Coverage

`tests/unit/services/test_vertical_backfill.py` covers three test classes:

| Class | Tests | Coverage |
|---|---|---|
| `TestParseVerticalFromNotes` | 9 | Regex matching: Dental, Chiro, case-insensitive, leading text, empty, None, no-prefix, whitespace-strip, first-occurrence |
| `TestBackfillResult` | 1 | Dataclass defaults |
| `TestBackfillFromDataframe` | 11 | Main loop: candidate identification, existing-vertical skip, null-gid skip, notes→CF write, no-vertical-prefix skip, count correctness, batch-continues-on-failure, missing-gid-column, missing-vertical-column, no-CF-on-task skip, no-enum-match skip, case-insensitive enum match |

All tests use `AsyncMock` / `MagicMock` for the Asana client. No integration tests exist against
a live Asana API.

---

## Boundaries and Failure Modes

### Explicit Scope Boundaries

- **Notes field only**: Parses `cf:Vertical` from the `notes` field exclusively. Does not examine
  task name, description sub-sections, attachments, comments/stories, or any other field.
- **Unit tasks only**: Designed for the `unit` entity type DataFrame. The `backfill_from_dataframe`
  contract requires `gid` and `vertical` columns; other schemas are silently returned as empty
  `BackfillResult`.
- **Empty-vertical rows only**: Rows where `vertical` is already non-empty are never touched. The
  service is additive, not corrective for existing values.
- **Enum custom field only**: Only writes `cf:Vertical` via the enum resolution pattern. Does not
  write free-text custom fields or any other custom field type.
- **No HTTP surface**: There is no REST route that triggers backfill on demand. The only trigger
  is the cache warmer Lambda post-warm hook.
- **Feature-flagged**: Disabled by default (`ASANA_VERTICAL_BACKFILL_ENABLED` unset). Must be
  explicitly enabled in Lambda environment config.

### Error Paths

| Error Condition | How Handled | Result |
|---|---|---|
| DataFrame missing `gid` column | Logs `vertical_backfill_no_gid_column`, returns empty result | `attempted=0` |
| DataFrame missing `vertical` column | Logs `vertical_backfill_no_vertical_column`, returns empty result | `attempted=0` |
| Row has null/empty GID | `continue` (silent skip) | Not counted |
| Notes lack `"Vertical: "` prefix | Logs `vertical_backfill_no_vertical_in_notes`, returns `False` | `skipped++` |
| Task has no "Vertical" CF | Logs `vertical_backfill_cf_not_found`, returns `False` | `skipped++` |
| Vertical value not in enum options | Logs `vertical_backfill_enum_option_not_found`, returns `False` | `skipped++` |
| Any exception in `_backfill_single_task` | Broad-catch (BLE001 suppressed), logs `vertical_backfill_task_error`, records `(gid, error)` | `failed++` |
| Any exception in entire backfill call | Outer broad-catch in `cache_warmer._run_vertical_backfill`, logs `vertical_backfill_error` | Lambda invocation unaffected |

**Double broad-catch isolation**: Task-level isolation (inside `backfill_from_dataframe`) ensures
one failing task never stops the batch. Service-level isolation (inside `_run_vertical_backfill`)
ensures the entire backfill never fails the Lambda invocation.

### Interaction Points and Boundaries with Adjacent Features

**`cache_warmer` Lambda**: Backfill is a post-warm side-effect. It consumes the already-warm
DataFrame from `DataFrameCache`; it does not re-warm or invalidate. The warmed DataFrame reflects
the state at cache-warm time — any tasks created between the warm and the backfill run will be
absent from the DataFrame and therefore missed.

**`intake_create_service.IntakeCreateService._write_vertical_custom_field`** (line 300): The enum
resolution pattern is duplicated, not shared. If enum-field write logic changes in intake, the
backfill service must be updated separately. This is a latent divergence risk.

**`DataFrameCache`**: Backfill reads from cache but does NOT write back. After a successful
backfill of N tasks, the cached DataFrame still shows `vertical=null` for those tasks until the
next warm cycle. The Asana-side custom field is the authoritative destination; the cache is stale
until the next warm.

**Enum option values**: The matching is case-insensitive against whatever enum options are
currently configured on the Asana task. If the enum is reconfigured (option added, renamed,
deleted) between backfill runs, previously-skipped tasks with `enum_option_not_found` may
become succeeding or vice versa.

### Configuration Boundaries

| Setting | Valid Values | Effect |
|---|---|---|
| `ASANA_VERTICAL_BACKFILL_ENABLED` | `"1"`, `"true"`, `"yes"` (any case) | Enables the backfill; anything else (including unset) disables it |
| `opt_fields` on `tasks.get_async` | Hardcoded: `notes`, `custom_fields.gid`, `custom_fields.name`, `custom_fields.enum_options.gid`, `custom_fields.enum_options.name` | Changing these breaks parsing or enum resolution |

---

```metadata
evidence_sources:
  - path: src/autom8_asana/services/vertical_backfill.py
    lines: 1-290
    role: primary implementation
  - path: src/autom8_asana/lambda_handlers/cache_warmer.py
    lines: 108-180, 638-651
    role: sole production caller; feature-flag guard; outer isolation
  - path: tests/unit/services/test_vertical_backfill.py
    lines: 1-397
    role: test coverage map; 21 test cases across 3 classes
  - path: src/autom8_asana/services/intake_create_service.py
    lines: 300-355
    role: enum resolution pattern reference (shared algorithm, not shared code)
  - path: .know/architecture.md
    section: "services/ package inventory"
    role: structural context; confirms services/ layer placement
  - path: .know/conventions.md
    lines: 209, 346
    role: confirms BackfillResult naming and log: Any | None constructor pattern

design_rationale_sources:
  - "Module docstring (vertical_backfill.py:1-9): 'Option A+C: Cache-warmer passthrough approach'"
  - "cache_warmer.py:638: 'Option A from P1-E spike'"
  - "cache_warmer._run_vertical_backfill docstring (line 116-131): feature flag, non-blocking contract"
  - "test_vertical_backfill.py module docstring (line 1-9): 'Per remediation-vertical-investigation-spike Option A'"

gaps:
  - No spike artifact found in .ledge/ — 'remediation-vertical-investigation-spike' referenced in
    code docstrings but not present as a discoverable .ledge/spikes/ document. Design rationale
    reconstructed from code comments.
  - No ADR or RFC documents this feature. Decision record exists only in docstrings.

confidence_rationale: >
  Full source and test file read; caller traced to cache_warmer with line-number evidence;
  enum-resolution pattern cross-referenced against intake_create_service. Design rationale
  reconstructed from inline docstrings (no external decision record found). Confidence 0.92
  reflects high code-read fidelity with minor uncertainty on the full spike context.
```
