---
type: review
status: accepted
---

# dyn-enum-contract — Sprint-3 COHERENCE Receipts (Architect synthesis)

> **Telos**: `dyn-enum-contract` — one typed, additive, FK-safe sync contract carrying an
> Asana enum-option-set change into `autom8y-data.verticals`, driving the rung
> `authored → proven → merged` (ship-dark, flag OFF).
> **Artifact role**: synthesis of design + build + qa into a single coherence attestation for the
> producer half (autom8y-asana). This file is the Architect's coherence receipt; the STRONG
> two-sided attestation belongs to the rite-disjoint review-rite critic at PT-07 / PT-07-live.

- **Worktree**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum`
- **Branch**: `feat/dyn-enum-contract`
- **HEAD**: `1eec76223af2be9fd2d25cc3a256e0a3fbaaafad` (unchanged)
- **Date**: 2026-07-01
- **Runner**: `./.venv/bin/python -m pytest` (NEVER `uv run`)
- **Self-grade**: `[STRUCTURAL | MODERATE]` — G-CRITIC same-rite synthesis ceiling per
  `self-ref-evidence-grade-rule`. STRONG requires the review-rite disjoint critic (PT-07 / PT-07-live).

---

## §0 Method + honest disposition (read first)

**Method.** Every receipt below was **re-run / re-probed by the Architect this session** — not
transcribed from the design/build/qa reports. Where a fact was proven by another agent and NOT
re-executed here (the real-source-mutation teeth), it is labelled `[qa-adversary, cross-referenced]`
and NOT claimed as an Architect direct-inspection receipt (SVR discipline: no receipt without probe).

**Rung — attested honestly, not rounded.**

| Ladder rung | State |
|---|---|
| authored | DONE (sprint-1 producer P + sprint-3 coherence H) |
| **proven (ship-dark, flag OFF)** | **DONE — this artifact** |
| merged | NOT DONE (operator gate; explicitly out of scope for this dispatch) |

Attested rung = **PROVEN, ship-dark (flag OFF), merge-ready**. NOT rounded to live / verified-realized
(that is PT-07-live against the deployed consumer).

**Disposition correction (SVR / telos-integrity — observed state wins over framing).** The dispatch
return-ask phrased the target as "pushed-not-merged." The direct git probe contradicts "pushed":

```
$ git rev-parse HEAD
1eec76223af2be9fd2d25cc3a256e0a3fbaaafad          # unchanged
$ git status --porcelain=v1 -- src/ tests/
 M src/autom8_asana/services/gid_push.py
?? src/autom8_asana/contracts/
?? tests/integration/test_dyn_enum_roundtrip.py
?? tests/unit/contracts/
?? tests/unit/services/test_gid_push_vocab.py
$ git diff --stat
 src/autom8_asana/services/gid_push.py | 478 ++++++...
 1 file changed, 474 insertions(+), 4 deletions(-)
```

The producer content is **uncommitted in the worktree** — NOT committed, NOT pushed, NOT merged, HEAD
at `1eec7622`, no flag flipped. Per the standing constraint ("Do NOT commit/push/merge, do NOT flip
flags") this is correct-and-intended; `push` is the operator's NEXT step, not a state this session
reached. I decline to attest "pushed" because it is not observed true — rounding "proven+uncommitted"
up to "pushed" is precisely the F-HYG-CF-A wave-level-CLOSED-without-per-item-receipts failure the
telos-integrity gate refuses.

---

## §1 gfr-spine non-regression — CON-007 (STRICTLY-ADDITIVE)

The dyn-enum-contract producer work must be strictly-additive to the certified gfr spine: **207 GREEN
at every exit.** Re-run this session:

```
$ ./.venv/bin/python -m pytest tests/unit/resolution/gfr -q
207 passed in 0.46s
```

CON-007 held. The producer surface touches `services/` + `contracts/` only; the gfr resolution spine
is byte-untouched (see §8 SVR-4: `M` is confined to `gid_push.py`; all new files are `contracts/`,
`tests/unit/contracts/`, `tests/unit/services/test_gid_push_vocab.py`, `tests/integration/`).

---

## §2 Two-sided drift-WARN GREEN/RED matrix (with teeth proof)

**Design intent (§S3-4).** One metric `VocabSyncDriftDetected{drift_reason, count, field_key}`
dimension-discriminated **parallel** to the existing `VocabSyncRefused{refuse_reason}` — NOT a name
proliferation. Three producer-observable signals via the pure observer `detect_vocab_drift()`:
`name_collision`, `disabled_option`, `degenerate_name`. Emitted **after** floor-pass, **before**
transport; sync PROCEEDS (drift ≠ refuse). A one-sided always-warn (or never-warn) is G-THEATER.

**Live GREEN receipt (Architect re-run this session):**

```
$ ./.venv/bin/python -m pytest tests/unit/services/test_gid_push_vocab.py \
                                tests/unit/contracts/test_vocabulary_sync_models.py -q
69 passed in 0.49s          # 46 sprint-1 (contract+refuse) + 23 sprint-3 (drift/seed)
```

**Two-sided structure — proven by the 23 sprint-3 node-ids (collected this session).** Each drift
class carries a matched **fire ↔ silent** pair; the payload-ride assertions prove drift never drops a
row; DW-PROCEEDS proves no short-circuit; the refuse-path silences prove orthogonality to the refuse
canary.

| Canary class | RED side (WARN FIRES) | Clean side (SILENT) | Payload / flow invariant |
|---|---|---|---|
| **DW-COLLISION** | `test_collision_warns_and_both_rows_ride_the_payload` | `test_collision_clean_input_emits_no_drift_metric` | both colliding rows RIDE the payload (no drop) |
| **DW-DISABLED** | `test_disabled_warns_and_option_rides_with_enabled_false` | `test_disabled_clean_input_emits_no_drift_metric` | disabled option SHIPS with `enabled=False` (never delete) |
| **DW-DEGENERATE** | `test_degenerate_warns_and_survivor_still_ships` | `test_degenerate_clean_input_emits_no_drift_metric` | surviving row ships; unprojectable never on the wire |
| **DW-PROCEEDS** | `test_drift_proceeds_push_is_still_called` | — | drift NEVER short-circuits `_push_to_data_service` |
| **DW-REFUSE-ORTHOGONALITY** | — | `test_drift_not_emitted_on_refused_empty_path`, `test_drift_not_emitted_on_refused_truncation_path` | drift silent on the refuse paths (louder `VocabSyncRefused` owns them) |
| **DW-SHIPDARK** | — | `test_drift_never_fires_when_shipdark_flag_off` | no metric crosses while flag OFF |
| **Observer-level teeth** | `test_name_collision_fires_on_drift_silent_on_clean`, `test_disabled_option_fires_on_drift_silent_on_clean`, `test_degenerate_name_fires_on_drift_silent_on_clean` | `test_fully_clean_set_returns_no_signals` | each class fires on drift, silent on clean, at the pure-function level |
| **Observer purity** | `test_observer_is_pure_never_mutates_input`, `test_enabled_none_is_not_counted_disabled`, `test_degenerate_needs_raw_count_else_not_computed`, `test_multiple_drift_classes_coexist_in_stable_order` | — | input byte-identical post-observation; `enabled=None` ≠ disabled; degenerate gated on threaded `raw_option_count`; stable signal order |

**TEETH — real-source-mutation proof `[qa-adversary, cross-referenced — NOT re-run by Architect]`.**
The wiring-level teeth (that clean-silence is the observer returning `[]`, not the push swallowing;
that a RED metric is the observer detecting, not a spurious always-on emit) were proven by
qa-adversary via backup→sed→test→restore against the *actual* `detect_vocab_drift` predicates:

- **M1** collision `> 0` → `< 0` (never-warn): `4 failed, 14 passed`; clean-side test stayed GREEN → **fire-side has teeth**.
- **M2** collision `> 0` → `>= 0` (always-warn): `11 failed, 7 passed`; fire-side test stayed GREEN → **clean-side has teeth**.
- **M3** disabled `is False` → `is True`: `7 failed, 11 passed` → disabled class has independent teeth.
- Revert exact: `shasum 465192633f1b8e482ee332eb856ee30f90e7558d7789d3e346938071645bf58b` identical pre/post; predicates pristine; grep-zero residue confirmed.

A one-sided always-warn survives M1; a one-sided never-warn survives M2. Both were caught → **NOT
theater.** The Architect did NOT re-run this mutation (to preserve the byte-identical worktree — §8
SVR-4); it is cross-referenced at MODERATE (same-rite). The STRONG two-sided attestation is the
review-rite disjoint critic's at PT-07.

**Architect-independent teeth corroboration (non-mutating):** the matched fire/silent node-ids above
were collected live this session (`--collect-only`), the full 69 GREEN was re-run this session, and
`test_observer_is_pure_never_mutates_input` is inside that GREEN set — the two-sided *structure* is
present and passing under Architect probe, independent of the mutation receipt.

---

## §3 No-codegen / no-auto-mint / no-delete attestation (ADR-S4-001)

Drift-WARN is observability-ONLY. Proven at three altitudes:

**(a) Contract is structurally additive-only (Architect read of `contracts/vocabulary_sync.py`).** The
response envelope has NO `deleted` field — the accounting enum is `inserted / updated / refused` only:

```python
class VocabularySyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inserted: int
    updated: int
    refused: list[RefusedRow]        # per-row additive-refusal (name-collision → FR-007); NOT a delete
```

`enabled: bool | None` "rides the envelope for drift-observability ONLY … A disabled-but-referenced
option is a drift WARN, never a DELETE." There is no delete field, no delete path, no mint/codegen field.

**(b) Observer is a pure read (Architect read of gid_push.py:853-914).** `detect_vocab_drift()` body =
count-reads (`len`, `sum(... is False)`, `raw_option_count - len(projected)`) + `signals.append(...)`
to a LOCAL list + `return`. Zero mutation of the input, zero delete/mint/codegen. Runtime proof:
`test_observer_is_pure_never_mutates_input` PASSES in the §2 GREEN set. The `delete`/`DELETE` tokens a
crude grep flags are docstring prose ("never a delete").

**(c) Flow proceeds unchanged over the shipping set (Architect read of gid_push.py:993-1002 — ordering).**

```
959  if not _is_vocab_sync_enabled(): ... return False          # 1. ship-dark gate (DEFAULT OFF)
972  if option_count == 0: ... return False                     # 2. refuse: empty
981  if option_count < floor: ... return False                  #    refuse: gross-truncation vs floor
1001 for drift_reason, drift_count in detect_vocab_drift(...):  # 2b. DRIFT observe — AFTER floor, BEFORE transport
1002     _emit_vocab_sync_drift(drift_reason, drift_count, field_key)   #     read-only; NO return (no short-circuit)
1004 base_url = ...                                             # 3. transport
```

Drift is emitted only over the set that WILL ship (the refuse paths `return` before :1001, so drift is
silent on refuse — matching `test_drift_not_emitted_on_refused_*`). Collided + disabled rows ride the
envelope (present-but-flagged; consumer FR-007 resolves collisions per-row); degenerate is
unprojectable upstream (no Lock-3 key) and is never dropped-as-delete. **ZERO mutation / mint / codegen
/ delete** — honors ADR-S4-001 (detect, don't codegen), FR-006.

---

## §4 Compose-up SEED — DEFER-1-ready, registry NOT built (G-DEFER)

The contract is **DEFER-1-ready** (a 2nd vocabulary = data addition, not a code change) because the
seed already exists from sprint-1 and the machinery is value-blind. The fleet `{field_key:
source_cf_binding}` registry is **NOT built** — escalate-only at N≥3 (A10 one-way door).

**(a) Grep-zero — machinery is field_key-value-blind (Architect re-run this session).** No branch keys
on the field_key VALUE anywhere in producer machinery:

```
$ rg -n 'field_key\s*(==|!=|\bis\b|\bin\b)\s*[\[("'"'"']' \
       src/autom8_asana/services/gid_push.py src/autom8_asana/contracts/vocabulary_sync.py
grep-zero-exit=1          # no matches
```

**(b) `Literal["vertical"]` is the typed registry (single value), analogue of origin/main
`dynvocab_overrides` OVERRIDE_REGISTRY "2nd entry is DATA"** (Architect read `vocabulary_sync.py:68`):

```python
field_key: Literal["vertical"]   # Lock-2 discriminator, valued from row one; extra="forbid"
```

A 2nd vocab = **1-token Literal extension + 1 source-binding = data-not-logic** (adds a permitted
value; no branch, no new path).

**(c) Proof tests (in the §2 GREEN set):**
- `test_cu1_push_machinery_is_field_key_value_blind` — model_construct bypass → same endpoint, field_key threaded, no new path.
- `test_cu2_no_field_key_value_branch_in_machinery` — grep-zero regression guard.
- `test_cu2_endpoint_is_generic_plural_not_field_key_specific` — endpoint `/api/v1/vocabularies/sync` is generic-plural, not vertical-specific.

The Literal was NOT extended; the fleet registry was NOT built. G-DEFER honored.

---

## §5 Ship-dark — BOTH layers (flag-OFF + unwired)

Ship-dark holds at two independent layers; both re-probed this session.

**Layer 1 — flag DEFAULT OFF, does NOT ride sibling flags (Architect eval this session):**

```
$ GID_PUSH_ENABLED=true STATUS_PUSH_ENABLED=true ./.venv/bin/python -c "..."
env GID_PUSH_ENABLED   = true
env STATUS_PUSH_ENABLED= true
env VOCAB_SYNC_ENABLED = None
_is_vocab_sync_enabled (VOCAB unset, siblings true) = False
_is_vocab_sync_enabled (VOCAB=true)                  = True
```

Even with both sibling flags ON, the vocab flag is False while unset → vocab does NOT ride siblings;
it flips True ONLY on explicit `VOCAB_SYNC_ENABLED` (gid_push.py:690, truthy-in `{1,true,yes}`).

**Layer 2 — dark-by-absence: `push_vocabulary_to_data_service` has ZERO production call-sites
(Architect grep this session):**

```
$ rg -n 'push_vocabulary_to_data_service' src/
src/autom8_asana/services/gid_push.py:187:    ... push_status_to_data_service, and push_vocabulary_to_data_service.   # docstring
src/autom8_asana/services/gid_push.py:251:    ... See push_vocabulary_to_data_service.                                # comment
src/autom8_asana/services/gid_push.py:919:async def push_vocabulary_to_data_service(                                  # the def
```

Only the def + two self-doc references — no orchestrator/warmer caller. **Contrast:** the sibling
account-status push IS wired (`cache_warmer.py:59` import, `cache_warmer.py:1087` call). Vocab is
maximally dark (unwired **and** flag-off) — correct for the rung.

---

## §6 Authored live round-trip harness (PT-07-live, run-deferred)

`tests/integration/test_dyn_enum_roundtrip.py` (295L, NEW) — authored + inert. 6 legs:
POS-NEW / POS-RENAME-SAMEKEY / POS-RENAME-NEWKEY (old key+id RETAINED, no-delete under rename) /
NEG-empty (producer refuse) / NEG-truncated (consumer FR-004 teeth, direct POST) / IDEMPOTENCE.
FK-inert idempotent key `__dyn_enum_canary__` (no cleanup under the no-delete invariant).

**Skip correctness — no false-pass (Architect re-run this session, both modes):**

```
$ ./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py -q
6 skipped in 0.23s                                            # no env → skip

$ AUTOM8Y_DATA_URL=http://127.0.0.1:9 AUTOM8Y_DATA_API_KEY=bogus-s2s DYN_ENUM_LIVE_ROUNDTRIP=1 \
  ./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py -m integration -q --timeout=30
6 skipped in 0.34s                                            # env set + unreachable host → skip, NOT error/false-pass
```

The session fixture catches the connect/404 probe and skips — an env-set run against a dead consumer
degrades to skip, never a green false-pass.

**Operator / review-rite live-run command (in the file docstring):**

```
AUTOM8Y_DATA_URL=https://<deployed-consumer-host> AUTOM8Y_DATA_API_KEY=<s2s-jwt> \
DYN_ENUM_LIVE_ROUNDTRIP=1 ./.venv/bin/python -m pytest \
  tests/integration/test_dyn_enum_roundtrip.py -m integration -v --timeout=60
```

`[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/PT-07-live-roundtrip]` — the review-rite /
signal-sifter attests GREEN post-deploy against the deployed consumer. The consumer-side
verticals-list read-back route is tagged `[UNATTESTED — DEFER-POST-HANDOFF: verticals-list-path]`.

---

## §7 Coherence watches (NON-BLOCKING — consistent with rung = proven ship-dark)

1. **`push_vocabulary_to_data_service` has zero production callers** (§5 Layer 2) — dark-by-absence +
   flag-off = maximally dark, correct for the rung. Warmer→project→push wiring is genuine downstream
   work (sprint-4+/operator, ADR §9 EC-4).
2. **Degenerate (c) signal is production-unreachable today** — no production caller threads
   `raw_option_count` (the public `push_vocabulary_to_data_service` signature accepts it at :856/:923,
   but its only threading is into `detect_vocab_drift`, and the function itself is unwired per watch 1).
   Unit-proven; the sprint-4 wiring MUST thread it for the signal to be live. Watch, not a defect.
3. **Contract model is the interim in-repo definition** (`contracts/vocabulary_sync.py`, tagged
   `[PROPOSE — promote to autom8y-core]`). The G-PROPAGATE core minor bump (ADR §6) is a pending
   cross-repo dependency (escalated to potnia); consumer sprint-2 imports from `autom8y_core`
   post-promotion. Correctly escalated, not done here.
4. **ADR/TDD spine-count wording:** the ADR prose referencing a "105 gfr certified tests" figure is
   stale/differently-scoped; the LIVE floor is **207** and the sprint-3 TDD re-baselines to 207. The
   build correctly holds the live 207 floor (§1). Documentation nit only.
5. **Harness `_VERTICALS_LIST_PATH`** honestly tagged `[UNATTESTED — DEFER-POST-HANDOFF]` — consumer
   read-back unverified until PT-07-live. Correct for a run-deferred harness.

None blocking. All five are downstream/documentation coherence notes.

---

## §8 SVR receipt appendix — load-bearing platform-behavior claims (direct-inspection this session)

| # | Claim | verification_method | Probe → verbatim result |
|---|---|---|---|
| SVR-1 | HEAD unchanged at 1eec7622 | bash-probe | `git rev-parse HEAD` → `1eec76223af2be9fd2d25cc3a256e0a3fbaaafad`, exit 0 |
| SVR-2 | gfr spine 207 GREEN post-change | bash-probe | `pytest tests/unit/resolution/gfr -q` → `207 passed in 0.46s`, exit 0 |
| SVR-3 | compose-up seed intact (no field_key-value branch) | bash-probe | `rg 'field_key\s*(==\|!=\|\bis\b\|\bin\b)\s*[\[("'\'']'` → no matches, `grep-zero-exit=1` |
| SVR-4 | producer surface is additive; `M` confined to gid_push.py | git-ls-files | `git status --porcelain -- src/ tests/` → `M gid_push.py` + `??` contracts/, integration/, unit/contracts/, unit/services/test_gid_push_vocab.py; `git diff --stat` → `1 file changed, 474 insertions(+), 4 deletions(-)` |
| SVR-5 | vocab flag defaults OFF, independent of siblings | bash-probe | eval → `_is_vocab_sync_enabled (VOCAB unset, siblings true) = False`; `(VOCAB=true) = True` |
| SVR-6 | contract response has no `deleted` field | file-read | `contracts/vocabulary_sync.py:99-101` → `inserted: int` / `updated: int` / `refused: list[RefusedRow]` |
| SVR-7 | drift observed after floor, before transport, no short-circuit | file-read | `gid_push.py:1001` → `for drift_reason, drift_count in detect_vocab_drift(opts, raw_option_count=raw_option_count):` (between floor-return :991 and transport :1004; no return in loop) |
| SVR-8 | vocab push unwired; sibling wired | bash-probe | `rg push_vocabulary_to_data_service src/` → only :187/:251/:919; `rg _push_account_status... cache_warmer.py` → :59 import + :1087 call |
| SVR-9 | harness cannot false-pass under env-set-unreachable | bash-probe | env-trio + `127.0.0.1:9` → `6 skipped in 0.34s` |

---

## §9 GO/NO-GO + RUNG + producer-PR completeness

### RELEASE RECOMMENDATION — **GO** (coherence half)

All coherence gates GREEN with pasted live receipts re-run this session; zero critical/high defects.

- **§1 gfr-spine**: 207 GREEN (CON-007 strictly-additive) — re-run.
- **§2 two-sided drift-WARN**: 69 GREEN; matched fire/silent node-id pairs + DW-PROCEEDS + refuse-orthogonality + observer-purity; teeth proven by qa real-source mutation (M1/M2/M3, cross-referenced) — NOT theater.
- **§3 no-codegen/no-mint/no-delete**: contract structurally additive-only (`inserted/updated/refused`, no `deleted`); observer pure; ADR-S4-001 / FR-006 honored — read + runtime-proven.
- **§4 compose-up seed**: grep-zero (exit 1) + `Literal["vertical"]` single-value + 3 CU tests; fleet registry NOT built (G-DEFER, escalate-only N≥3).
- **§5 ship-dark**: flag DEFAULT OFF + does not ride siblings + zero production call-sites (both layers) — re-probed.
- **§6 harness**: authored + inert; no false-pass under env-set-unreachable; live-run command handed to operator / review-rite (PT-07-live, deferred).

### RUNG

**PROVEN → ship-dark (flag OFF), merge-ready.** NOT rounded to merged / live / verified-realized.
Merge and flag-flip remain the operator's levers (production-mutating; out of dispatch scope).

### Producer PR completeness (P sprint-1 + H sprint-3)

The producer half — **P** (sprint-1: contract `vocabulary_sync.py` + refuse/floor push machinery in
`gid_push.py`) **+ H** (sprint-3: drift-WARN observer, compose-up seed, live harness) — is **COMPLETE
and PROVEN, ship-dark (flag OFF)**.

**Disposition (observed, honest):** uncommitted in worktree `feat/dyn-enum-contract`, HEAD unchanged at
`1eec7622` — **NOT committed, NOT pushed, NOT merged; no flag flipped; worktree byte-identical** (source
`M` confined to `gid_push.py`, all else untracked `??`). The dispatch's "pushed-not-merged" is the
operator's NEXT step, not a state reached here; I attest the observed "proven, merge-ready,
not-yet-pushed" rather than round up to "pushed."

**Cross-repo tail (escalated, not done here):** the autom8y-core minor bump homing the contract models
(ADR §6 G-PROPAGATE) gates consumer sprint-2's import — a potnia-owned sequencing dependency.

**Deferred STRONG attestation:** `[UNATTESTED — DEFER-POST-HANDOFF: PT-07-live-roundtrip]` — the
rite-disjoint review-rite critic attests the live two-sided round-trip against the deployed consumer.

Self-grade `[STRUCTURAL | MODERATE]` (G-CRITIC same-rite synthesis ceiling).
