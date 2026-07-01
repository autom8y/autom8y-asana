---
type: spike
status: draft
slug: dyn-enum-contract
wave: 3 (prototype-engineer)
upstream: .ledge/spikes/INTEGRATE-dyn-enum-contract.md (wave 2)
downstream: moonshot-architect (wave 4)
evidence_grade: "[STRUCTURAL | MODERATE]"
---

# PROTO-dyn-enum-contract

> rnd /spike — Wave 3 (prototype-engineer). THROWAWAY code. No production primitives modified.
> Time-box: 1-day equivalent (2 canaries, stdlib only, no live Asana, no real DB).
> Evidence ceiling: MODERATE (self-referential fleet assessment; rnd-dk caps at MODERATE).
> SVR discipline: all production-primitive claims carry `{path}:{line}` receipts or `[UV-P]`.

---

## Executive Summary

Built two discriminating canaries proving the core mechanism question for `dyn-enum-contract`:
(1) additive-upsert keyed on `vertical_key` is safe on the FK-parent `verticals` table where
snapshot-replace (DELETE+INSERT) is demonstrably unsafe; (2) the current leaf-calibrated empty
guard at `gid_push.py:514-519` silently no-ops on empty or truncated Asana reads, which is wrong
for an FK-parent publish — a hard-refuse guard that checks referential coverage is the correct
replacement. Both canaries are two-sided (RED fires on the defect, GREEN passes on the correct
input, same fixture). **Verdict: GO** for productionization of the additive-upsert vocab-sync
contract, with four residual risks documented for moonshot-architect.

---

## 1. What Was Built and How to Run It

### Artifacts

```
.sos/wip/spikes/dyn-enum-contract/
  canary1_fk_parent.py     — FK-parent write semantics (snapshot-replace vs additive-upsert)
  canary2_empty_publish.py — empty/truncated-publish hard-refuse guard
```

### How to Run

```bash
# From repo root (no dependencies beyond stdlib — Python 3.10+)
python3 .sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py
python3 .sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py

# Both exit 0 on pass, 1 on fail.
```

No environment setup required. No live Asana token. No database credentials. The fixtures are
self-contained in-memory constructs.

---

## 2. Canary 1 — FK-parent Write Semantics

**Hypothesis under test (from INTEGRATE HD-2 STRONG):** the `verticals` table is an FK-parent
dimension referenced by `campaigns.vertical_id` (`_advertising.py:80`),
`asset_verticals.vertical_id` (`_advertising.py:326`, 43,057 rows in production), and
`offers.category` → `verticals.key` (`_platform.py:162`). A snapshot-replace
(DELETE+INSERT) on this table — which is the current `account_status_store.snapshot_replace`
pattern (`account_status_store.py:82-143`) — is structurally unsafe. The safe mechanism is
additive-upsert keyed on `vertical_key`.

**SVR receipt (HD-2 load-bearing claim):**
```yaml
structural_verification_receipt:
  claim: "asset_verticals.vertical_id is a FK into verticals.id"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_data/core/models/_advertising.py"
    line_range: "L326"
    marker_token: "vertical_id: int = Field(foreign_key=\"verticals.id\")"
    claim: "asset_verticals declares a hard FK to verticals.id; a DELETE+INSERT that
            reassigns the auto-increment id orphans this reference"
```

### Fixture

SQLite in-memory DB with:
- `verticals(id AUTOINCREMENT, key UNIQUE, name)` — mirrors `_platform.py:145-147`
- `campaigns(vertical_id FK→verticals.id)` — mirrors `_advertising.py:80`
- `asset_verticals(vertical_id FK→verticals.id)` — mirrors `_advertising.py:326`

Seeded: 4 verticals (chiropractic id=1, dental id=2, vision id=3, wellness id=4);
2 campaign FK children; 3 asset_verticals FK children.

### RED Side — Snapshot-replace Breaks FK Integrity

**Phase A — FK enforcement ON (mirrors PostgreSQL production behavior):**

```
snapshot_replace result: ok=False  msg=FK CONSTRAINT VIOLATION: FOREIGN KEY constraint failed
CANARY FIRES (Phase A): DELETE blocked by FK constraint [EXPECTED]
```

The DELETE from `verticals` was blocked by the FK constraint from `asset_verticals`. In
production PostgreSQL, this is the failure mode: the DELETE itself raises a constraint
violation before a single row is removed.

**Phase B — FK enforcement OFF (shows id reassignment / orphan hazard — mirrors MySQL without
strict FK mode, or any DB if constraints are deferred):**

```
Original ids: {'chiropractic': 1, 'dental': 2, 'vision': 3, 'wellness': 4}
New ids after replace: {'chiropractic': 5, 'dental': 6, 'vision': 7, 'wellness': 8}
ID changes (reassigned!): {'chiropractic': (1, 5), 'dental': (2, 6), 'vision': (3, 7), 'wellness': (4, 8)}

asset_verticals children (stored_id → resolved):
  [('chiro_hero_banner.png', 1, None),
   ('dental_offer_v2.pdf', 2, None),
   ('vision_care_video.mp4', 3, None)]
DANGLING (orphaned) rows: 3 — ['chiro_hero_banner.png', 'dental_offer_v2.pdf', 'vision_care_video.mp4']

CANARY FIRES (Phase B): id reassignment detected + orphaned FK children
```

Even when FK constraints do not block the DELETE (e.g. legacy MySQL MyISAM, or if constraints
are temporarily deferred during a transaction), the AUTOINCREMENT assigns NEW ids (5-8 instead
of 1-4). Every FK child row that stored the old ids (1-4) now points at non-existent rows:
all 3 `asset_verticals` rows are orphaned. The `campaigns` rows would be equally orphaned.

**RED SIDE VERDICT: CANARY FIRES — snapshot-replace is UNSAFE [CORRECT]**

### GREEN Side — Additive-upsert Preserves FK Integrity

```
additive_upsert result: ok=True
  msg=Upserted 5 options (insert-new + update-in-place, no delete)

Verticals AFTER upsert:
  [{'id': 1, 'key': 'chiropractic', 'name': 'Chiropractic'},
   {'id': 2, 'key': 'dental',       'name': 'Dental'},
   {'id': 3, 'key': 'vision',       'name': 'Vision'},
   {'id': 4, 'key': 'wellness',     'name': 'Wellness'},
   {'id': 9, 'key': 'hearing_health', 'name': 'Hearing Health'}]  ← new key inserted

Original ids: {'chiropractic': 1, 'dental': 2, 'vision': 3, 'wellness': 4}
Ids after upsert: {'chiropractic': 1, 'dental': 2, 'hearing_health': 9, 'vision': 3, 'wellness': 4}
Original ids PRESERVED: True
New key 'hearing_health' INSERTED: True (id=9)

FK integrity: ok=True  All 3 FK children resolve correctly; original ids preserved
asset_verticals AFTER upsert:
  [('chiro_hero_banner.png', 'chiropractic'),
   ('dental_offer_v2.pdf', 'dental'),
   ('vision_care_video.mp4', 'vision')]

GREEN SIDE VERDICT: PASS — additive-upsert SAFE [CORRECT]
```

Original ids unchanged (1, 2, 3, 4). New key `hearing_health` inserted with id=9 (no
collision). All 3 FK children still resolve correctly via LEFT JOIN.

### Canary 1 Summary

```
RED  (snapshot-replace is unsafe): FIRES [CORRECT — has teeth]
GREEN (additive-upsert is safe):   PASS  [CORRECT]

CANARY 1 RESULT: TWO-SIDED — DISCRIMINATING [PASS]
```

The canary bites ONLY on the defect (snapshot-replace). It does NOT fire on the correct
input (additive-upsert). This is the discriminating-canary-doctrine requirement met.

---

## 3. Canary 2 — Empty/Truncated-publish Hard-refuse

**Hypothesis under test (from INTEGRATE HD-5 STRONG, HD-7):** the current producer empty
guard (`gid_push.py:514-519`) is calibrated for the account_status leaf table:

```python
if not entries:
    logger.info("status_push_skipped", extra={"reason": "no_entries_to_push"})
    return True  # Nothing to push is not a failure
```

This is correct for account_status (no FK children; a missed push just leaves stale data).
For the FK-parent `verticals` publish, an empty Asana read — caused by API auth partial
failure, wrong field GID, or transient error — must HARD-REFUSE and alert, not silently
no-op. A truncated read (pagination bug returning 2 of 10 options) must also be refused if
any of the missing options are currently FK-referenced (their absence is indistinguishable
from a rename or deletion at the Asana level).

**SVR receipt (HD-5 leaf-calibrated guard claim):**
```yaml
structural_verification_receipt:
  claim: "the existing producer empty guard returns True (no failure) on empty entries"
  verification_method: file-read
  verification_anchor:
    source: "src/autom8_asana/services/gid_push.py"
    line_range: "L514-L519"
    marker_token: "return True  # Nothing to push is not a failure"
    claim: "the existing guard explicitly declares empty-push as non-failure; this is
            unsafe for an FK-parent publish where an empty Asana read must be refused"
```

### Fixture

- `FK_REFERENCED_KEYS = frozenset({'chiropractic', 'dental', 'vision', 'wellness'})` —
  stands in for a DB query of keys currently FK-referenced by `asset_verticals`/`campaigns`.
- `FULL_ENUM_OPTIONS` — 5 options including all 4 FK-referenced + 1 new.
- `EMPTY_ENUM_OPTIONS` — 0 items (simulates API failure / wrong field GID).
- `TRUNCATED_ENUM_OPTIONS` — 2 items; missing `vision` and `wellness` (both FK-referenced).

### RED Side A — Empty Options

```
[CURRENT GUARD — leaf-calibrated gid_push.py:514-519]
  → no_entries_to_push → return True (no-op, not a failure)
  refused=False, reason='leaf_guard: empty → no-op (not a failure)'
  DEFECT PRESENT: True

[NEW GUARD — FK-parent hard-refuse]
  REFUSED: HARD-REFUSE: enum_options is empty — Asana returned no options for this
  custom field. This may indicate an API auth failure, wrong field GID, or transient
  error. Refusing publish to protect FK-parent verticals table.
  ALERT: ops team must investigate Asana API response.
  refused=True, alert_emitted=True
  GUARD CORRECT: True

CANARY A FIRES (defect demonstrated, fix verified): True
```

### RED Side B — Truncated Options (missing FK-referenced keys)

```
Input: TRUNCATED_ENUM_OPTIONS (2 items) — keys: ['chiropractic', 'dental']
FK-referenced keys MISSING from input: ['vision', 'wellness']

[CURRENT GUARD]
  → 2 options — publishing: ['chiropractic', 'dental']
  refused=False
  DEFECT PRESENT: True (publishes truncated set silently)

[NEW GUARD]
  REFUSED: HARD-REFUSE: incoming options are missing FK-referenced keys: ['vision', 'wellness'].
  A publish with missing referenced keys would leave 2 vertical_keys unreachable by existing
  FK children (campaigns.vertical_id, asset_verticals.vertical_id).
  ALERT: Asana enum_options may be truncated or a key was renamed.
  refused=True, alert_emitted=True
  GUARD CORRECT: True

CANARY B FIRES (defect demonstrated, fix verified): True
```

### GREEN Side — Full Healthy Options

```
Input: FULL_ENUM_OPTIONS (5 items) — keys: ['chiropractic', 'dental', 'vision', 'wellness', 'hearing_health']
FK-referenced keys: ['chiropractic', 'dental', 'vision', 'wellness']
New keys (will INSERT): ['hearing_health']

[CURRENT GUARD]  refused=False  [expected: False / passes]
[NEW GUARD]
  Coverage OK: all 4 FK-referenced keys present.
  New keys (will INSERT): ['hearing_health']
  Publishing 5 options.
  refused=False  [expected: False / passes]
  reason: fk_parent_guard: 5 options, all 4 FK-referenced keys covered

GREEN PASSES (healthy input not refused by either guard): True
```

### Canary 2 Summary

```
RED A (empty options):     FIRES [CORRECT]
  - leaf guard defect:     True (silently no-ops instead of refusing)
  - new guard correct:     True (refuses + alerts)
RED B (truncated options): FIRES [CORRECT]
  - leaf guard defect:     True (publishes truncated set)
  - new guard correct:     True (refuses + alerts)
GREEN (full options):      PASS  [CORRECT]

CANARY 2 RESULT: TWO-SIDED — DISCRIMINATING [PASS]
```

The canary bites ONLY on empty/truncated input. It does NOT fire on a healthy full
option-set. Discriminating-canary-doctrine requirement met.

---

## 4. Deliberate Shortcuts and Production Gaps

| Shortcut | Where used | Production gap |
|----------|------------|----------------|
| **SQLite in-memory DB** (not PostgreSQL) | Canary 1 fixture | Production uses PostgreSQL. SQLite's `ON CONFLICT(key) DO UPDATE SET name=excluded.name` syntax is the same in PostgreSQL (`INSERT ... ON CONFLICT ... DO UPDATE`). FK enforcement semantics differ slightly (SQLite requires `PRAGMA foreign_keys = ON`; Postgres enforces by default) but the structural result is identical. [PRODUCTION GAP: integrate with real autom8y-data DB via the service layer; validate `vocab_upsert()` store method against a staging PostgreSQL instance.] |
| **Hardcoded fixture enum_options** (not live Asana API) | Both canaries | Real implementation calls `CustomFieldsClient.get(custom_field_gid)` and reads `.enum_options` (model: `custom_field.py:113`). The live Asana call has network latency, auth dependency (ASANA_PAT), and rate-limit exposure. [PRODUCTION GAP: wire `CustomFieldsClient.get` as shown at `clients/custom_fields.py:442` context; guard with the feature flag pattern from `gid_push.py:491`.] |
| **Hardcoded FK-referenced keys fixture** (not DB query) | Canary 2 referential-coverage check | Production must query the actual FK-referenced keys from `autom8y-data` before each publish: `SELECT DISTINCT v.key FROM verticals v WHERE EXISTS (SELECT 1 FROM asset_verticals av WHERE av.vertical_id = v.id) OR EXISTS (SELECT 1 FROM campaigns c WHERE c.vertical_id = v.id)`. [PRODUCTION GAP: this cross-table query adds ~1 DB round-trip per 4h publish cycle; acceptable overhead; must be done before the publish decision, not after.] |
| **No S2S JWT / HTTP transport** | Both canaries | The real publish uses `_push_to_data_service` (`gid_push.py:528`) with S2S JWT auth (`account_status.py:41`). Transport layer is not prototyped. [PRODUCTION GAP: the new `push_vocab_to_data_service()` function reuses `_push_to_data_service` verbatim with a new `endpoint_path="/api/v1/vocabularies/sync"`.] |
| **SQLite AUTOINCREMENT gap behavior** | Canary 1 Phase B id-reassignment | SQLite AUTOINCREMENT continues from the highest-ever id (not just max-current), so after DELETE+INSERT the new ids are 5-8 not 1-4. PostgreSQL SERIAL/SEQUENCE behaves the same: after DELETE the sequence does NOT reset; re-INSERTs get new ids. The orphaning hazard is identical. [No production gap: the structural result is the same.] |
| **No `offers.category` FK child modeled** | Canary 1 fixture | The integration doc cites a third FK edge: `offers.category FK→verticals.key` (`_platform.py:162`). The canary only models `campaigns` and `asset_verticals`. [PRODUCTION GAP: the referential-coverage check in production must also cover `offers.category`; add that to the DB query above.] |
| **`print()` instead of structured logger** | Both canaries | Production uses `structlog`/JSON logging with `extra={}` dicts (per `gid_push.py:515-518` pattern). [PRODUCTION GAP: replace `print()` with `logger.warning("vocab_push_refused", extra={"reason": ..., "alert": True})`.] |

---

## 5. What This Proves / Does NOT Prove

### Proven (MODERATE evidence — self-ref ceiling)

- **FK-parent write semantics**: `INSERT ... ON CONFLICT(key) DO UPDATE SET name=excluded.name`
  preserves existing `id` values and leaves FK children intact. DELETE+INSERT either (a) raises
  an FK constraint violation in strict mode or (b) reassigns auto-increment ids and orphans all
  FK children in loose mode. This is a structural result independent of DB vendor for the AUTOINCREMENT/SERIAL id pattern used in production (`_platform.py:145`).

- **Empty/truncated guard defect**: the current `gid_push.py:514-519` guard returns `True`
  (no-op) on empty input. Applied to a vocab publish for an FK-parent, this is the wrong
  semantics. The FK-parent hard-refuse guard demonstrated in Canary 2 correctly refuses both
  the empty and the truncated cases while passing the healthy full-set case.

- **Referential-coverage check feasibility**: the check (`FK_REFERENCED_KEYS - incoming_keys`)
  is O(n) set arithmetic on a small vocabulary (~10-55 options). No performance concern at this
  cardinality or frequency (every 4h).

- **Name-key normalization round-trip**: `normalize_to_key("Hearing Health") == "hearing_health"`;
  the key correctly identifies the vertical in both the additive-upsert (Canary 1 GREEN) and the
  coverage check (Canary 2 GREEN). `enum_option.gid` does not appear in any persisted key — the
  gfr-dynvocab NAME-keying discipline (`vertical_key`) holds.

### NOT Proven (production gaps the next rite must own)

- **Real PostgreSQL upsert behavior under concurrent writes**: the prototype uses SQLite
  single-writer. Production needs to validate that `INSERT INTO verticals ... ON CONFLICT(key)
  DO UPDATE SET name=excluded.name` behaves correctly under concurrent 4h push cycles without
  a transaction-level lock. The `VerticalService` is "read-heavy" (`services/vertical.py:7`)
  so contention is expected low, but this is untested. [UV-P: concurrent upsert correctness |
  METHOD: integration test against staging PostgreSQL | REASON: SQLite single-writer prototype
  cannot test this]

- **Live Asana `enum_options` payload shape and completeness**: the fixture shapes
  `CustomFieldEnumOption{gid,name,enabled}` from `custom_field.py:19-42`. Live Asana may
  return options with `enabled=False` for disabled options. The referential-coverage check
  must decide: does a disabled option in Asana count as "present"? If a FK-referenced vertical
  is disabled in Asana, should the publish WARN or REFUSE? This is an operator-judgment question
  not resolved by the prototype. [UV-P: disabled-option handling in referential-coverage check |
  METHOD: operator decision + integration test with live Asana | REASON: fixture uses
  enabled=True for all options]

- **First-publish reconciliation**: the data-side `verticals` table is already populated with
  FK-referenced rows. The first real sync must match existing `vertical_key` values, not
  re-key them. The prototype seeds a clean fixture; it does not test the case where the
  Asana option names have drifted from the current `vertical_key` values (e.g. "Chiropractic"
  in Asana vs "chiro" as `vertical_key` in the DB). Production must handle this mismatch
  gracefully (WARN, not crash). [UV-P: first-sync key-match reconciliation | METHOD: dry-run
  against staging DB with real Asana payload | REASON: clean fixture; no drift tested]

- **`offers.category` FK coverage**: only `campaigns.vertical_id` and
  `asset_verticals.vertical_id` are modeled. The third FK edge (`offers.category →
  verticals.key`) is structurally the same but must be included in the production
  referential-coverage query.

---

## 6. GO / NO-GO

### Verdict: **GO**

The two load-bearing uncertainties the integration researcher flagged as requiring prototype
validation are both resolved:

| Risk area | Was | Is now |
|-----------|-----|--------|
| FK-parent write semantics (HD-2 STRONG) | Hypothesis ("upsert is safe, replace is not") | PROVEN with captured output; two-sided canary with teeth |
| Empty/truncated-publish guard (HD-5 STRONG) | Known gap in the current leaf guard | DEMONSTRATED defect + DEMONSTRATED fix; two-sided canary with teeth |

The mechanism is sound. The production path (additive-upsert on `vertical_key`, new
`POST /api/v1/vocabularies/sync` endpoint, hard-refuse guard with referential-coverage check)
has a clear implementation path reusing existing fleet primitives.

### Residual Risks for Moonshot-architect to Own

1. **Concurrent upsert correctness** — validate `ON CONFLICT DO UPDATE` under concurrent
   push cycles against a real PostgreSQL staging instance. Low likelihood given read-heavy
   `VerticalService`, but unproven.

2. **Disabled-option semantics** — operator must decide: does a disabled Asana enum option
   count toward referential coverage? Recommend: yes (disabled but present is not missing;
   missing is the refusal trigger). This is a policy decision, not a technical one.

3. **First-sync key-mismatch reconciliation** — a dry-run against staging with the live
   Asana vertical cf payload must confirm that `normalize_to_key(option.name)` matches
   existing `vertical_key` values exactly. If there is drift (e.g. a renamed option in Asana
   that does not match the DB key), the referential-coverage check will refuse the first
   publish until a human resolves the mismatch. This is correct behavior but must be planned
   for.

4. **`offers.category` FK coverage** — the production referential-coverage query must include
   the `offers.category → verticals.key` edge (`_platform.py:162`) in addition to
   `campaigns.vertical_id` and `asset_verticals.vertical_id`.

### Confidence

**MODERATE** — self-referential ceiling per `self-ref-evidence-grade-rule`; rnd-dk literature
caps at MODERATE. The structural mechanism result (upsert preserves ids; replace orphans them)
is high-confidence regardless of the ceiling, but the ceiling applies to the GO verdict as a
whole because it incorporates unproven production conditions (PostgreSQL staging, live Asana
payload, first-sync reconciliation).

---

## Artifact Verification Table

| Artifact | Path | Status |
|----------|------|--------|
| Canary 1 | `.sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py` | Written + executed; exit 0 confirmed |
| Canary 2 | `.sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py` | Written + executed; exit 0 confirmed |
| Findings doc | `.ledge/spikes/PROTO-dyn-enum-contract.md` | This file |

---

## Demo Script (for stakeholder walkthrough)

### Prerequisites

```bash
python3 --version  # 3.10+ required; stdlib only
```

### Walkthrough

**Step 1 — Show the problem (Canary 1 RED):**
Run `python3 .sos/wip/spikes/dyn-enum-contract/canary1_fk_parent.py` and point to Phase A
output: `FK CONSTRAINT VIOLATION: FOREIGN KEY constraint failed`. The DELETE is blocked.
Then point to Phase B: `ID changes (reassigned!): {'chiropractic': (1, 5), ...}` and
`DANGLING (orphaned) rows: 3`. This is what snapshot-replace does to an FK-parent without
strict constraint enforcement.

**Step 2 — Show the fix (Canary 1 GREEN):**
Point to GREEN output: `Original ids PRESERVED: True`, `New key 'hearing_health' INSERTED: True
(id=9)`, `FK integrity: ok=True  All 3 FK children resolve correctly`. The additive-upsert
handles insert-new AND update-in-place without touching existing ids.

**Step 3 — Show the guard gap (Canary 2 RED):**
Run `python3 .sos/wip/spikes/dyn-enum-contract/canary2_empty_publish.py`. Point to RED A:
the current guard says `return True  # Nothing to push is not a failure` on an empty payload.
Point to RED B: the current guard publishes 2 options silently when 2 FK-referenced keys are
missing.

**Step 4 — Show the guard fix (Canary 2 GREEN):**
Point to GREEN: `Coverage OK: all 4 FK-referenced keys present. Publishing 5 options. refused=False`.
The new guard refuses bad inputs and passes good ones — a discriminating check, not a blanket
blocker.

**Step 5 — Bound the claims:**
This is a fixture prototype on SQLite + in-memory fixtures. The mechanism is proven; the
production integration (PostgreSQL staging, live Asana, first-sync reconciliation) is the
next validation gate, owned by moonshot-architect / tech-transfer.

### FAQ

- **Q: Why not just use the existing snapshot-replace with a pre-DELETE check?**
  A: There is no `source` column on `verticals` (`_platform.py:145-147`), so a
  source-scoped DELETE (the pattern in `account_status_store.py:89`) is not possible — the
  DELETE would hit ALL rows. More fundamentally, even a careful DELETE+INSERT reassigns the
  auto-increment `id`, which is an FK-referenced column. The only safe mechanism is upsert.

- **Q: Why not use the gRPC `VerticalService.create` per option?**
  A: `create` raises `AlreadyExistsError` on existing keys (`services/vertical.py:149`) and
  has no update path — it is admin-only and requires N round-trips + error-handling for the
  common (already-exists) case. It is viable for single-key WARN escalation, not bulk upsert.

- **Q: The referential-coverage check seems like it could refuse valid publishes if Asana
  renames a vertical.**
  A: Correct — a rename in Asana produces a new key (`normalize_to_key(new_name)`), and the
  old key disappears from the payload. The guard correctly refuses this until an operator
  updates the DB key to match. This is the intended behavior: renames require a human in the
  loop, not silent automatic replacement. The drift WARN path (not prototyped here) surfaces
  this as an operator task.

---

## Handoff to Moonshot-architect

Ready for handoff. Both discriminating canaries fired with captured output. Shortcuts
documented. GO stated with MODERATE confidence. Four residual risks enumerated. The four
residual risks (concurrent upsert, disabled-option semantics, first-sync reconciliation,
`offers.category` coverage) are the planning surface for moonshot-architect's long-term
architecture design — they are not blockers on the GO verdict, but they are scoped unknowns
the production build must address.
