---
type: spec
subtype: sprint-delta-tdd
status: accepted
initiative: dyn-enum-contract
sprint: sprint-3 (coherence — producer, autom8y-asana)
station: architect (design-only; NO production code this phase)
date: 2026-07-01
rite: 10x-dev
rung: authored            # CAP = authored→proven→merged (ship-dark, flag OFF). NEVER live/verified-realized.
evidence_grade_ceiling: "MODERATE — self-referential authorship ceiling (self-ref-evidence-grade-rule + G-CRITIC); STRONG belongs to the review-rite disjoint critic at PT-07/PT-07-live"
governing_spec: ".ledge/decisions/ADR-dyn-enum-contract-shared-contract.md  # the LOCKED sole spec"
delta_base:
  - ".ledge/specs/dyn-enum-contract-sprint1-producer-tdd.md  # sprint-1 producer half — this is a DELTA atop it"
  - ".ledge/reviews/dyn-enum-contract-producer-receipts.md   # sprint-1 PROVEN receipts (canary GREEN + 207 spine)"
build_head_reverified: "producer autom8y-asana feat/dyn-enum-contract @ 1eec7622 (sprint-1 artifacts live in worktree, uncommitted)"
live_baseline: "gfr spine 207 passed · vocab canary+models 46 passed · combined 253 passed (this session, ./.venv/bin/python -m pytest)"
doctrine_precedents:
  - "origin/main:src/autom8_asana/dataframes/models/registry.py  # WARN-first drift gate (model_schema_drift_detected + ModelSchemaDrift), ADR-S4-001 read-only comparator"
  - "origin/main:src/autom8_asana/resolution/gfr/dynvocab_overrides.py  # compose-up: 2nd OVERRIDE_REGISTRY entry is DATA, never a code change"
---

# TDD-Delta — dyn-enum-contract sprint-3 COHERENCE (producer, autom8y-asana)

> **A DELTA atop the sprint-1 producer half — coherence, not a rewrite.** Sprint-1 shipped
> the producer PUSH + two-sided REFUSE canary (empty/truncation), ship-dark (flag OFF), 207 gfr
> spine GREEN. This sprint-3 delta resolves the three remaining *coherence* surfaces the ADR
> named but sprint-1 deferred: (1) **drift-WARN observability** — producer-observable vocab-health
> signals emitted as WARN+metric (never codegen/auto-mint, ADR-S4-001 / FR-006); (2) the
> **compose-up SEED** that makes the contract DEFER-1-READY (the fleet registry is NOT built —
> ESCALATE-only at N≥3, G-DEFER); (3) the **AUTHORED-but-run-deferred** cross-repo LIVE round-trip
> harness that asserts the full realization predicate (the review-rite runs it live post-deploy).
> STRICTLY-ADDITIVE (CON-007): **207 gfr GREEN at every exit.** CAP = **merged ship-dark, flag OFF.**

## §S3-0 · Live baseline (G-PROVE — pasted receipts, no adjectives)

Every number below re-run LIVE this session in the worktree (`./.venv/bin/python -m pytest`, NEVER `uv run`):

| Fact | Command | Result |
|---|---|---|
| gfr certified spine (CON-007 floor) | `pytest tests/unit/resolution/gfr -q` | `207 passed in 0.49s` |
| vocab canary + contract models | `pytest tests/unit/services/test_gid_push_vocab.py tests/unit/contracts/test_vocabulary_sync_models.py -q` | `46 passed in 0.40s` |
| combined (spine + vocab) | both paths together | `253 passed in 0.65s` |
| **compose-up grep-zero** (no field_key value-branch) | `grep -nE 'field_key\s*==\|== *"vertical"' gid_push.py vocabulary_sync.py` | **GREP-ZERO: no field_key value-branch** |
| integration marker registered | `pyproject.toml:121` | `"integration: marks tests as integration tests requiring live API access"` |
| consumer-round-trip skip precedent | `tests/integration/test_schema_contract.py:46-54` | `_requires_data_service = skipif(not _DATA_URL or not _DATA_API_KEY)` + `pytestmark = pytest.mark.integration` |

Anchors for the drift observer (LIVE @ 1eec7622, this worktree):

| Anchor | `{path}:{line}` | Verbatim / role |
|---|---|---|
| existing metric family (compose target) | `gid_push.py:698`,`:713`,`:728` | `_emit_vocab_sync_refused` / `_emit_vocab_sync_skipped` / `_emit_vocab_sync_contract_parse_failed` |
| shared bridge namespace | `gid_push.py:41` | `_BRIDGE_FLEET_NAMESPACE = "Autom8y/AsanaBridgeFleet"` |
| projection (raw→projected; degenerate skip) | `gid_push.py:794-807` (skip at `:798`) | `if opt.name is None or not opt.name.strip(): continue` |
| floor guard (refuse boundary) | `gid_push.py:866-877` | `if option_count < floor: … _emit_vocab_sync_refused(gross_truncation)` |
| push transport (drift emit point is BEFORE this) | `gid_push.py:905-906` | `request = VocabularySyncRequest(...)` → `_push_to_data_service(...)` |
| option `enabled` (drift observability field) | `custom_field.py:35-38` | `enabled: bool \| None` |
| WARN-first drift precedent (metric+log) | `registry.py` (origin/main) | `logger.warning("model_schema_drift_detected", … "metrics": {"ModelSchemaDrift": …})` — "HONORS ADR-S4-001: read-only comparator" |
| compose-up-by-DATA precedent | `dynvocab_overrides.py` (origin/main) | `OVERRIDE_REGISTRY: dict[...]` — "a SECOND override is a new entry here (data), never a code change" |

---

## §S3-1 · DRIFT-WARN OBSERVABILITY (producer-side; WARN+metric ONLY; never codegen/auto-mint)

**Decision.** Add a pure, read-only **drift observer** over the *projected, floor-passing* option-SET,
emitting a WARN log + a CloudWatch metric per drift class. The sync **still proceeds** — drift is a
*signal*, not a refuse. This is the exact discipline of the WARN-first `registry.py` gate ("HONORS
ADR-S4-001: read-only comparator. It never writes a schema, generates a column, or mutates a
descriptor"): the vocab observer **never** mutates the option-set, **never** mints a vertical, **never**
auto-deletes. It observes what already flows and alarms.

### The metric grammar (composes with the existing `VocabSync*` family)

ONE new metric, `drift_reason`-discriminated — **parallel to `VocabSyncRefused{refuse_reason}`**
(`gid_push.py:698-710`), NOT a proliferation of metric names. This is the principled composition: the
existing refuse family already uses one metric + a reason dimension; drift is one alarm class (WARN,
non-refuse) with variants. `registry.py` likewise uses a single `ModelSchemaDrift` metric.

```
_emit_vocab_sync_drift(drift_reason: str, count: int, field_key: str) -> None   # mirror of _emit_vocab_sync_refused (:698)
    emit_metric("VocabSyncDriftDetected", 1,
                dimensions={"drift_reason": drift_reason, "count": str(count), "field_key": field_key},
                namespace=_BRIDGE_FLEET_NAMESPACE)                                # gid_push.py:41
    logger.warning("vocab_sync_drift_detected",                                   # WARNING, not ERROR — drift ≠ refuse
                   extra={"drift_reason": drift_reason, "count": count, "field_key": field_key})
```

Closed `drift_reason` enum (constants beside `VOCAB_REFUSE_REASON_*` at `gid_push.py:664-667`):
`VOCAB_DRIFT_REASON_NAME_COLLISION = "name_collision"`, `VOCAB_DRIFT_REASON_DISABLED_OPTION =
"disabled_option"`, `VOCAB_DRIFT_REASON_DEGENERATE_NAME = "degenerate_name"`.

> **Brief-shorthand reconciliation.** The brief's `WARN(vocab_sync_name_collision)` /
> `WARN(vocab_sync_disabled_option)` map to the log-event `vocab_sync_drift_detected` +
> `VocabSyncDriftDetected{drift_reason=name_collision \| disabled_option}`. The shorthand names ARE the
> `drift_reason` dimension values; the single-metric form is the composition with the locked `VocabSync*`
> grammar. A deploy-gate alarm keys on `VocabSyncDriftDetected` (WARN tier, distinct from the ALARMING
> `VocabSyncRefused` and the UNKNOWN-outcome `VocabSyncContractParseFailed`).

### The observer (pure; ADR-S4-001 read-only)

```
def detect_vocab_drift(projected: list[VocabularyOption], *, raw_option_count: int | None = None
                       ) -> list[tuple[str, int]]:
    """Read-only drift signals over the SET that will ship. Pure; never mutates/mints/deletes.
       Returns [(drift_reason, count), …] for each class PRESENT (empty list == clean set)."""
```

| # | Signal | Detection (pure fn of the projected set) | Producer-visible at emission? |
|---|---|---|---|
| **(a)** | **NAME-COLLISION** | `len(projected) - len({o.vertical_key for o in projected})` > 0 — 2+ options normalized to the SAME `vertical_key` | YES — pure fn of the current set |
| **(b)** | **DISABLED-CARRIED** | `sum(1 for o in projected if o.enabled is False)` > 0 — an option carried with `enabled=False` | YES — `enabled` rides the envelope (`custom_field.py:35`) |
| **(c)** | **DEGENERATE-DROP** (optional) | `raw_option_count - len(projected)` > 0 — raw options that lost their NAME-key (None/blank) and were skipped by projection (`gid_push.py:798`) | YES *iff* the caller threads `raw_option_count` (see seam note) |

**Emission point.** In `push_vocabulary_to_data_service`, **after** the floor guard passes (`gid_push.py:877`)
and **before** transport config (`:879`): iterate `detect_vocab_drift(opts, raw_option_count=…)` → one
`_emit_vocab_sync_drift(reason, count, field_key)` per present class → **then proceed to push unchanged.**
On the REFUSED path (empty/truncation) the louder `VocabSyncRefused` already fired; drift-WARN is emitted
only on the set that WILL ship (observe what ships). The observer is non-fatal — `emit_metric` swallows
CloudWatch errors internally (`gid_push.py:701-704`), so observability never fails the push seam.

**Set-churn honesty (the (c) boundary — stated, not hand-waved).** *True* prior-set churn (an option that
DISAPPEARED vs a prior known set — a DROP) is **NOT producer-observable at ship-dark**: the producer is a
stateless single-emission read with no prior-set baseline in-process (CON-008: Asana live enum_options is the
single source-of-record, read fresh each cycle). The cheap producer-side proxy IS **degenerate-drop** (read-
*quality* churn: options that arrived without a usable name). The authoritative DROP/churn signal is the
CONSUMER's `VocabularySyncResponse{inserted, updated, refused}` accounting — a sprint-2/sprint-4 signal
(§S3-3 harness asserts it), **deferred here** (BC-3 "a disappeared option is a drift WARN → human runbook,
never an auto-delete"; the producer never sees the disappearance to warn on it ship-dark).

### How a disabled / collided option FLOWS (present-but-flagged; NEVER dropped-as-delete)

This is the load-bearing invariant. The drift-WARN is **observability layered onto the existing flow** — it
changes NOTHING about what crosses the seam:

| Drift class | Producer projection | Envelope disposition | Consumer disposition (sprint-2) | NEVER |
|---|---|---|---|---|
| **DISABLED** (`enabled=False`) | **projected** (projection at `:798` skips only nameless, NOT disabled) | **rides the envelope** with `enabled=False` (present-but-flagged) | additive-upsert (valid key+name; `enabled` is not a stored column) | **never a delete** (RR2/BC-3) |
| **COLLISION** (2 names→1 key) | **both projected** (collision does not reduce the projected list) | **both rows ride** the envelope, same `vertical_key` | FR-007 per-row guard: one upserts, the other → `RefusedRow` (`vocabulary_sync.py:75`) | **never a producer-side drop** |
| **DEGENERATE** (None/blank name) | **skipped at projection** (`:798`) — no Lock-3 key is *constructible* | never on the wire (no empty-keyed row ever ships) | n/a | **never dropped-as-delete** — it never had a valid identity to delete |

DISABLED + COLLISION are **present-but-flagged** (WARN observes; both still ship). DEGENERATE is
*unprojectable* (dropped at projection because no `vertical_key` can exist per Lock-3 — that is sprint-1
behavior at `:798`, not a new drop); the WARN merely makes the pre-existing skip observable. **No drift
signal removes a valid option; no drift signal is a delete.**

### ZERO auto-mutation confirmation (ADR-S4-001 / FR-006 / NFR-006)

- **No codegen-from-model.** The observer reads `list[VocabularyOption]`; it emits metrics/logs. It writes
  no schema, generates no column, mints no vertical, edits no descriptor. (Mirrors `registry.py` "read-only
  comparator" verbatim discipline.)
- **No phantom-mint.** A collided/disabled/degenerate option is never *created* into a new vertical to
  "resolve" the drift — resolution is the operator's runbook (BC-3), not the producer's.
- **No auto-delete.** Drift is never a `DELETE` — CON-004 (verticals is an FK-parent; no producer write path
  exists at all; §sprint-1 D-2 boundary).
- The observer is a **pure function** + a **non-fatal emitter**; both are strictly-additive to the shipping
  path (the push proceeds identically whether or not drift fired).

---

## §S3-2 · COMPOSE-UP SEED (DEFER-1-READY; the fleet registry is NOT built)

**The single extension point already exists from sprint-1** — a 2nd `field_key` is a DATA addition, not a
new code path. Three facts, each LIVE-verified this session:

1. **The discriminator is the typed registry.** `field_key: Literal["vertical"]` (`vocabulary_sync.py:68`)
   is the closed permitted-value SET. This is the **typed analogue** of the dynvocab `OVERRIDE_REGISTRY`
   dict (origin/main `dynvocab_overrides.py`): where that registry admits a 2nd override by adding a *dict
   entry* (data), the `Literal` admits a 2nd vocabulary by adding a *permitted value* (data). The `Literal`
   is deliberate, NOT a plain `str` — it preserves Lock-2 `extra="forbid"` discriminator integrity (a wrong
   `field_key` is a validation error, not silent drift). Extending the permitted-value set is the DATA
   addition; it adds no branch, no function, no code path.
2. **The push is field_key-parameterized.** `push_vocabulary_to_data_service(options, *, field_key:
   Literal["vertical"] = "vertical", …)` (`gid_push.py:810-813`) threads `field_key` opaquely into
   `VocabularySyncRequest(field_key=…)` and the metric dimensions. **GREP-ZERO proof (this session):**
   `grep -nE 'field_key\s*==|== *"vertical"'` over `gid_push.py` + `vocabulary_sync.py` → **no
   field_key value-branch exists.** The logic never inspects the *value* of `field_key`; it is opaque data.
3. **The endpoint is generic-plural.** `endpoint_path="/api/v1/vocabularies/sync"` (Lock-1, `gid_push.py:907`)
   is NOT field_key-specific (never `/verticals/sync`). A 2nd vocabulary POSTs to the *same* path.
4. **NAME-keying is field_key-agnostic.** `normalize_vertical_key` / `project_enum_options_to_vocabulary_options`
   (`gid_push.py:748`,`:770`) take no `field_key` — they project names→keys identically for any vocabulary.

**⇒ The exact compose-up cost for a 2nd vocabulary (e.g. `"campaign_type"`) is the 1-token Literal
extension** `Literal["vertical"]` → `Literal["vertical", "campaign_type"]` **+ a 2nd source-binding**
(which Asana cf gid feeds which `field_key`). That is data-not-logic: it adds a permitted value to a
discriminator enum and one source mapping; it adds **no branch** to projection/push/transport (grep-zero
proves the machinery is value-blind). This mirrors the dynvocab precedent's "2nd entry is DATA" exactly.

**DEFER-1 boundary (G-DEFER — do NOT build).** The `{field_key: source_cf_binding}` map is where a future
fleet-registry (the dynvocab-style dict, one altitude up) would live. It is **NOT built here** — ESCALATE-only
at the N≥3 conjunction (ADR §7; only `field_key="vertical"` binds today, and `/vocabularies/sync` does not yet
exist consumer-side). The SEED is the *existing* value-blind parameterization that PROVES a 2nd `field_key`
needs no rewrite; building the registry now is the A10 one-way door at N<3 (ADR §11).

### Compose-up PROOF test (design — the "2nd field_key is DATA" canary)

Hand qa two tests that PROVE the machinery is field_key-agnostic **without editing the Literal** (editing it
would be *building*, not proving the seed):

- **CU-1 — machinery is value-blind (model_construct bypass).** Build a request for a hypothetical 2nd
  `field_key` via `VocabularySyncRequest.model_construct(field_key="campaign_type", options=[…])` (bypasses
  the Literal validator — the point is to exercise the *downstream* wiring, not the validator). Drive it
  through the push wiring (patched `_push_to_data_service`) and assert: (i) `endpoint_path` is the SAME
  generic `/api/v1/vocabularies/sync` (NOT `/campaign_type/sync`); (ii) `field_key="campaign_type"` is
  threaded verbatim into the payload + `metric_dimensions`; (iii) the projection that produced `options`
  took no `field_key`. **No new code path was taken.**
- **CU-2 — the extension is DATA, mechanically.** Assert the grep-zero holds as a *regression guard*: a
  source scan of the projection/push machinery contains no `field_key == "…"` / `if field_key is "vertical"`
  branch (the value-blind property CU-1 relies on). If a future edit adds a value-branch, CU-2 goes RED —
  the compose-up seed has been broken and the 2nd vocabulary would need code, not data. (Mirrors the
  dynvocab discipline: `apply_override` reads the mapping; it never `if entity_type == "offer"`-branches.)

CU-1 + CU-2 together are the falsifiable proof that the DEFER-1 door is open by DATA. They add **zero**
production code (design-time test spec); they assert an *existing* structural property.

---

## §S3-3 · LIVE / INTEGRATION HARNESS (AUTHORED; run-deferred to review-rite PT-07-live)

**Decision.** Author the complete cross-repo round-trip harness NOW — full assertion bodies encoding the
realization predicate — but mark it `@pytest.mark.integration` + **skip-when-consumer-absent** so it is
**INERT** in sprint-1/3 CI (the consumer `/api/v1/vocabularies/sync` endpoint does not exist yet). The
review-rite (PT-07-live / signal-sifter, which HAS Bash) runs it live post-deploy; it goes GREEN when the
consumer ships, or finds a real gap. This is spec-as-test: the assertion structure is the acceptance target
made executable, with **no consumer built here.**

**File:** `tests/integration/test_dyn_enum_roundtrip.py` (NEW; `tests/integration/` exists, marker registered
`pyproject.toml:121`).

### Skip guard (mirror `test_schema_contract.py:46-54` + a mutation opt-in + an endpoint probe)

```python
pytestmark = pytest.mark.integration                                   # excluded from the default unit run

_DATA_URL     = os.environ.get("AUTOM8Y_DATA_URL", "").rstrip("/")     # consumer base URL (as test_schema_contract.py:46)
_DATA_API_KEY = os.environ.get("AUTOM8Y_DATA_API_KEY", "")             # S2S JWT             (        …          :47)
_MUTATE_OK    = os.environ.get("DYN_ENUM_LIVE_ROUNDTRIP") == "1"       # explicit destructive-opt-in (this test WRITES verticals)

_requires_live_consumer = pytest.mark.skipif(
    not (_DATA_URL and _DATA_API_KEY and _MUTATE_OK),
    reason="dyn-enum LIVE round-trip: set AUTOM8Y_DATA_URL + AUTOM8Y_DATA_API_KEY + DYN_ENUM_LIVE_ROUNDTRIP=1 "
           "(the consumer /api/v1/vocabularies/sync must be deployed; this test mutates verticals additively).",
)

@pytest.fixture(scope="session")
def live_consumer_or_skip():
    """Endpoint-existence probe: skip (not fail) if /api/v1/vocabularies/sync is absent (pre-deploy 404)."""
    r = httpx.post(f"{_DATA_URL}/api/v1/vocabularies/sync",
                   headers={"Authorization": f"Bearer {_DATA_API_KEY}"},
                   json={"field_key": "vertical", "options": []}, timeout=15)
    if r.status_code == 404:
        pytest.skip("consumer /api/v1/vocabularies/sync not deployed (404) — run post-deploy")
    return _DATA_URL
```

Two-layer inert-ness: (1) `@pytest.mark.integration` keeps it out of the default `tests/unit` run entirely;
(2) even if `tests/integration` is collected, `_requires_live_consumer` SKIPS (never fails/errors) absent the
env trio, and the probe SKIPS on a pre-deploy 404. **CON-007 preserved: sprint-3 exit is still 207 gfr GREEN;
this harness contributes 0 collected failures.**

### The full assertion structure (AUTHORED; the realization predicate `telos:62-66` / ADR §10)

A **stable, namespaced, FK-inert test key** is used throughout — `__dyn_enum_canary__` — because the
no-delete invariant (`vertical.py:9`) means a test insert **cannot be cleaned up**; an idempotent re-runnable
key that no FK child references is the discipline (re-running upserts the same key; no accumulation, no
orphan risk).

| Leg | Setup | Action | Assertions (the teeth) |
|---|---|---|---|
| **PRE** capture | — | GET consumer verticals; sample one existing `(key→id)` + one FK child of each edge (a `campaigns.vertical_id`, an `asset_verticals` row, an `offers.category`) | snapshot for the intact-check |
| **POS-NEW** | full existing SET **+** `__dyn_enum_canary__` | producer push (or POST the `VocabularySyncRequest`) | `inserted>=1`, `refused==[]`; every PRE `(key→id)` **unchanged** (no id churn — additive); all 3 FK samples **still resolve**; new key **present** |
| **POS-RENAME-SAMEKEY** (name refresh) | an existing option, display name re-cased/whitespaced so `normalize()` yields the **same** key | push | `updated>=1`; that row's **id STABLE** (same key→same row); FK children on it **intact** — the UPDATE-name leg |
| **POS-RENAME-NEWKEY** (true rename) | an existing option renamed to a **new** normalized key | push | `inserted>=1` (new key); the **OLD key+id RETAINED** (no delete); FK children on the OLD key **still resolve** — proves no-delete/FK-safe under rename |
| **NEG-empty (producer)** | `None`/`[]` fed to the producer | producer push | producer **REFUSES** (`VocabSyncRefused{empty}`); **nothing reaches the consumer**; verticals **UNCHANGED** vs PRE |
| **NEG-truncated (consumer teeth)** | POST a grossly-truncated request **directly** to the consumer (bypass the producer) | consumer endpoint | consumer's own FR-004 3-edge coverage refuse fires (4xx / all-`refused`); verticals **UNCHANGED** — the authoritative refuse lives where the FK data lives (sprint-1 D-2 boundary) |
| **IDEMPOTENCE (NFR-002)** | re-run POS-NEW's healthy SET | push twice | 2nd run `inserted==0`, `refused==[]`, ids **identical** — no-op-suppressing upsert |

The NEGATIVE leg asserts the predicate at **both** layers: the producer refuse (defense-in-depth, already
unit-proven sprint-1) AND the consumer's authoritative FR-004 coverage refuse (sprint-2 teeth). "Empty/
truncated is never applied" is proven end-to-end.

### The exact live-run command (for the operator / review-rite)

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum
AUTOM8Y_DATA_URL=https://<deployed-consumer-host> \
AUTOM8Y_DATA_API_KEY=<s2s-jwt> \
DYN_ENUM_LIVE_ROUNDTRIP=1 \
./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py -m integration -v --timeout=60
```

`[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/PT-07-live-roundtrip]` — the harness is AUTHORED; its
GREEN is the review-rite's to attest LIVE against the deployed consumer (STRONG belongs to the rite-disjoint
critic, not this station). Until then it is skipped-inert. Run it against a **staging** consumer where
possible; against prod, the `__dyn_enum_canary__` key is the FK-inert, idempotent, no-cleanup-needed marker.

---

## §S3-4 · The TWO-SIDED drift-WARN canary spec (HAND TO qa-adversary)

**G-THEATER discipline.** Each drift-WARN is proven by a **matched pair**: the WARN **FIRES** on a drift
INPUT and is **SILENT** on the clean INPUT. A one-sided always-warn (fires on clean too) OR never-warn
(silent on drift) is theater. The RED input is a deliberately-crafted *drift* option-SET the observer
CORRECTLY flags — never a defect injected into shipped code. Every fixture keeps `len >= floor` (flag on,
`VOCAB_SYNC_MIN_OPTIONS=1`) so the *floor* never fires and the discrimination is drift-vs-clean only.

| # | Drift class | RED input (WARN FIRES) | Clean input (SILENT) | Two-sided assertion |
|---|---|---|---|---|
| **DW-COLLISION** | name-collision | `["Dental", "dental "]` → 2 names, 1 key `"dental"` | `["Dental", "Chiropractic"]` → 2 keys | RED: `VocabSyncDriftDetected{drift_reason=name_collision, count=1}` emitted **AND** BOTH rows still ride the pushed payload (present-but-flagged, no drop). Clean: **no** `name_collision` metric |
| **DW-DISABLED** | disabled-carried | `[Dental(enabled=True), Chiro(enabled=False)]` | `[Dental(enabled=True), Chiro(enabled=True)]` | RED: `{drift_reason=disabled_option, count=1}` emitted **AND** the disabled option is IN the pushed payload with `enabled=False` (never a delete). Clean: **no** `disabled_option` metric |
| **DW-DEGENERATE** (optional c) | degenerate-drop | `[Dental, <name=None>, "  "]` (raw=3, projected=1) | `[Dental, Chiropractic]` (raw=2, projected=2) | RED: `{drift_reason=degenerate_name, count=2}` emitted **AND** surviving Dental still ships. Clean: **no** `degenerate_name` metric |
| **DW-PROCEEDS** | non-refuse invariant | any RED above (flag on, `len>=floor`) | — | drift NEVER short-circuits: `_push_to_data_service` is **still called** (drift is a signal, not a refuse — contrast `VocabSyncRefused` which blocks the push) |
| **DW-TEETH** | mutation bite | flip the observer to always-emit → DW-*-clean go RED; delete the observer → DW-*-RED go silent | — | the matched pairs BITE on both mis-calibrations — proves neither side is theater |

**Discrimination property.** DW-*-RED fire the WARN *because the input carries drift*; DW-*-clean (same code
path) stay silent. If a clean set ever WARNs, or a drift set never WARNs, the observer is miscalibrated
(DW-TEETH catches both). The drift-WARN is orthogonal to the sprint-1 refuse canary: refuse **blocks** the
push (empty/truncation), drift **rides** the push (collision/disabled/degenerate) — DW-PROCEEDS asserts the
distinction. These extend the sprint-1 vocab canary suite (`test_gid_push_vocab.py`); **207 gfr spine
unchanged** (drift observer is producer-local, touches no gfr surface).

---

## §S3-5 · Module / file layout (the DELTA surface)

| File | Change | Why |
|---|---|---|
| `src/autom8_asana/services/gid_push.py` | **ADD** `VOCAB_DRIFT_REASON_*` consts, `detect_vocab_drift()` (pure), `_emit_vocab_sync_drift()` (emitter), one drift-observe call between `:877` and `:879` | §S3-1 drift-WARN observability |
| `src/autom8_asana/services/gid_push.py` | **OPTIONAL** thread `raw_option_count` into `push_vocabulary_to_data_service` for the (c) degenerate signal | §S3-1 (c) seam |
| `tests/unit/services/test_gid_push_vocab.py` | **ADD** DW-COLLISION/DISABLED/DEGENERATE/PROCEEDS/TEETH + CU-1/CU-2 | §S3-4 drift canary + §S3-2 compose-up proof |
| `tests/integration/test_dyn_enum_roundtrip.py` | **NEW** (skipped-inert) | §S3-3 authored live harness |
| projection `:770-807`, floor guard `:866-877`, push transport `:905-914` | **UNCHANGED** | drift is layered observability; refuse/floor/transport untouched |
| `contracts/vocabulary_sync.py` (`field_key: Literal["vertical"]`) | **UNCHANGED** | compose-up seed is the *existing* value-blind parameterization; the Literal is NOT extended (that is DEFER-1 DATA, not built) |

---

## §S3-6 · Conformance & gate ledger

| Invariant | Honored by | Anchor |
|---|---|---|
| **ADR-S4-001 / FR-006** WARN, never codegen/auto-mint | §S3-1 pure read-only observer; zero mutation confirmation | `registry.py` "read-only comparator" precedent |
| **RR2 / BC-3** disabled = WARN, never delete | §S3-1 flow table (present-but-flagged) | `vocabulary_sync.py:55` (`enabled` observability-only) |
| **G-DEFER** DEFER-1 registry ESCALATE-only at N≥3 | §S3-2 seed is existing value-blind parameterization; registry NOT built | ADR §7,§11 A10 |
| **G-THEATER** two-sided drift canary | §S3-4 matched RED/clean pairs + DW-TEETH mutation | — |
| **CON-007** strictly-additive to 207 gfr spine | §S3-0 (207 GREEN live); drift is producer-local; harness skipped-inert | `pytest tests/unit/resolution/gfr` → 207 |
| **ship-dark** flag OFF at merge | drift observer is inside `push_…` (gated by `_is_vocab_sync_enabled`, `gid_push.py:845`) — dark path never emits drift | `gid_push.py:845` |
| **G-PROVE** live `{path}:{line}` receipts | §S3-0 table (all re-run this session) | — |
| **G-RUNG** cap = merged ship-dark, flag OFF | this doc is `authored`; NOT rounded to live/verified | — |

## §S3-7 · Handoff criteria (sprint-3 coherence → proven)

- [ ] `detect_vocab_drift` pure + read-only; `_emit_vocab_sync_drift` mirrors `_emit_vocab_sync_refused`; single `VocabSyncDriftDetected{drift_reason,count,field_key}` metric.
- [ ] Disabled + collided options **ride the envelope** (present-but-flagged); degenerate is unprojectable (never on wire); **no drift is a delete/mint/codegen**.
- [ ] Two-sided drift canary GREEN (DW-COLLISION/DISABLED/DEGENERATE fire on drift, silent on clean; DW-PROCEEDS; DW-TEETH bites).
- [ ] Compose-up proof GREEN (CU-1 value-blind wiring; CU-2 grep-zero regression guard); Literal NOT extended; registry NOT built (G-DEFER).
- [ ] Live harness AUTHORED + skipped-inert (`@pytest.mark.integration` + env-trio skip + 404 probe); exact live-run command recorded; `[UNATTESTED — DEFER-POST-HANDOFF: PT-07-live]`.
- [ ] **207 gfr GREEN** at exit (CON-007); vocab canary suite GREEN with the drift additions.
- [ ] Flag OFF at merge (ship-dark). Rung caps at **merged**; live/verified-realized is operator/PT-07-gated.

**Evidence grade:** `[STRUCTURAL | MODERATE]` — self-referential authorship ceiling (self-ref-evidence-grade-rule
+ G-CRITIC). STRONG belongs to the review-rite disjoint critic at PT-07 (drift canary) / PT-07-live (round-trip
harness). Every claim carries a LIVE `{path}:{line}` or a pasted command receipt (§S3-0); no adjectives stand
in for receipts.
