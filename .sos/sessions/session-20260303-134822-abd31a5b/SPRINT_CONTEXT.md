---
sprint_id: sprint-20260303-n8n-cascade-fix
session_id: session-20260303-134822-abd31a5b
status: ACTIVE
created_at: "2026-03-03T12:48:22Z"
goal: "Resolve P0 cascade resolution failure on S3 fast-path and P1 EntityWriteRequest contract gap that caused Damian's n8n integration bugs"
frame: ".claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md"
spike: "docs/spikes/SPIKE-n8n-consumer-bugs.md"
---

# Sprint: N8N-CASCADE-FIX

## Goal

Resolve two consumer-facing bugs surfaced by Damian's n8n form-questions workflow:

- **B1 (P0):** `POST /v1/resolve/unit` returns NOT_FOUND for 9/10 accounts because the S3 parquet fast-path loads stale DataFrames without cascade validation. `office_phone` is null for cascade-dependent rows.
- **B2 (P1):** `list_remove` field silently dropped on PATCH because `EntityWriteRequest` lacks `extra="forbid"`.

Bottom-up execution order: fix data corruption first, then structural gap, then API boundary, then detection.

---

## Workstreams

| WS | Name | Severity | Est. | Phase | Status | Depends On |
|----|------|----------|------|-------|--------|------------|
| WS-2 | Shared Store Population for Fast-Path | P0 | ~1h | A | pending | — |
| WS-1 | Cascade Validation on S3 Fast-Path | P0 | ~2h | A | pending | WS-2 |
| WS-3 | EntityWriteRequest extra=forbid | P1 | ~15min | B | pending | — |
| WS-4 | Cascade Null-Rate Alerting | P2 | ~1h | C | pending | WS-1 |
| WS-5 | PhoneNormalizer in Resolver Index | P2 | ~1.5h | D | pending | — |

---

## Phase A — P0 Critical Path (WS-2 + WS-1, ~3h)

**Goal:** After Business loads via S3 fast-path, populate shared_store so downstream cascade validation can resolve. Then run cascade validator on all entity fast-path loads.

### WS-2: Shared Store Population for Fast-Path

**Files:** `src/autom8_asana/api/preload/progressive.py`

After loading Business DataFrame from S3 fast-path, adapt rows into minimal task dicts (`gid` + `custom_fields` keys) and call `store.put_batch_async()` without hierarchy warming. This unblocks WS-1 validation for Unit/Contact/Offer entities.

**Tests:**
- Store populated after Business fast-path load
- Downstream entity cascade validation finds Business data in store

### WS-1: Cascade Validation on S3 Fast-Path

**Files:**
- `src/autom8_asana/api/preload/progressive.py` — add validation call in fast-path
- `src/autom8_asana/dataframes/builders/cascade_validator.py` — make cascade_plugin optional or provide factory

After loading `s3_df` from S3, invoke `validate_cascade_fields_async()` when `shared_store` is available and entity type has cascade fields. If validation corrects rows, re-persist to S3 (self-healing). Log `progressive_preload_cascade_validated` event with correction counts.

**Key constraint:** Business entity skips cascade validation (it is the cascade source, not consumer).

**Tests:**
- Mock S3 load with null cascade fields — verify validation runs and corrects
- Business entity skips cascade validation
- Self-healing write-back when corrections applied

---

## Phase B — P1 API Contract (WS-3, ~15min)

**Goal:** Unknown fields on EntityWriteRequest produce 422 instead of silent drop.

### WS-3: EntityWriteRequest extra=forbid

**File:** `src/autom8_asana/api/routes/entity_write.py`

Add `model_config = ConfigDict(extra="forbid")` at line 62. Import `ConfigDict`.

**Tests:**
- Unknown fields produce 422
- Valid payloads still pass

---

## Phase C — P2 Detection (WS-4, ~1h)

**Goal:** Future cascade regressions are detectable before consumers hit them.

### WS-4: Cascade Null-Rate Alerting

**Files:**
- `src/autom8_asana/dataframes/builders/cascade_validator.py` — add `check_cascade_null_rate()` function
- `src/autom8_asana/api/preload/progressive.py` — call after cache put

Emit `cascade_null_rate_elevated` warning log when null rate exceeds 50% for cascade-critical fields. Non-blocking — DataFrame still loads.

**Tests:**
- Warning emitted when null rate exceeds threshold
- No warning when null rate is normal

---

## Phase D — P2 Defense in Depth (WS-5, ~1.5h)

**Goal:** Resolution is format-tolerant for phone numbers.

### WS-5: PhoneNormalizer in Resolver Index

**Files:**
- `src/autom8_asana/services/dynamic_index.py` — normalize phone values during index construction
- `src/autom8_asana/services/resolver.py` — normalize phone values in criterion before lookup

Wire existing `PhoneNormalizer` (`models/business/matching/normalizers.py`) into DynamicIndex and resolver criterion normalization.

**Tests:**
- Index built with normalized phone values
- Format-variant queries resolve to same entry

---

## Verification Strategy

After Phase A:
1. `pytest tests/unit/dataframes/builders/test_cascade_validator.py`
2. Run new fast-path integration tests
3. Full preload-related test suite
4. Post-deploy: check ECS logs for `progressive_preload_cascade_validated` with non-zero correction counts
5. Post-deploy: re-run Damian's n8n workflow against the 9 failing phone numbers

After Phase B:
1. Entity write test suite
2. Verify 422 on unknown fields

---

## Operational Pre-Requisite (Outside Code Scope)

Force Unit DataFrame rebuild to unblock Damian before code ships:
```
POST /admin/rebuild?entity_type=unit&force=true
```

---

## Completed Tasks

_(none yet)_
