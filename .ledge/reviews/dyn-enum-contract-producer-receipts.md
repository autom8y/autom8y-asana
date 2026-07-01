---
title: dyn-enum-contract — Sprint-1 PRODUCER Receipts
type: review
status: proven-ready-to-merge (ship-dark, flag OFF)
rite: 10x-dev
role: architect (synthesis)
initiative: dyn-enum-contract
sprint: 1 (producer, autom8y-asana)
worktree: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum
branch: feat/dyn-enum-contract
base_sha: 1eec76223af2be9fd2d25cc3a256e0a3fbaaafad
diff_stat: "+265 / -1 (src/autom8_asana/services/gid_push.py)"
rung_cap: proven -> merged ship-dark (flag OFF)
rung_reached: PROVEN (canary GREEN + gfr spine GREEN + env runnable)
recommendation: GO (producer half — ready-to-merge, ship-dark, flag OFF)
self_grade: "[STRUCTURAL | MODERATE]"
spec: .ledge/decisions/ADR-dyn-enum-contract-shared-contract.md
tdd: .ledge/specs/dyn-enum-contract-sprint1-producer-tdd.md
date: 2026-07-01
---

# dyn-enum-contract — Sprint-1 PRODUCER Receipts

Architect synthesis of the design → build → qa chain. **Every receipt below was
re-run LIVE in this synthesis session** (not transcribed from the upstream
outputs) except where explicitly marked `[QA-ATTESTED]` or `[OPERATOR-GATED]`.
The teeth mutation was re-applied and reverted independently in this session.

**G-PROVE discipline**: each claim carries a `{path}:{line}` anchor, a test-id,
or a pasted command output. **G-THEATER guard**: the canary RED is a
deliberately-miscalibrated guard the tests CORRECTLY catch — never a defect
injected into shipped production code (the mutation was reverted exactly; diff
returns to +265/−1, grep-zero residue).

---

## §0 Provenance & Rung

| Fact | Live receipt |
|---|---|
| Branch | `git rev-parse --abbrev-ref HEAD` → `feat/dyn-enum-contract` |
| Base SHA | `git rev-parse HEAD` → `1eec76223af2be9fd2d25cc3a256e0a3fbaaafad` (= claimed `1eec7622`) |
| Diff | `git diff --stat` → `gid_push.py | 266 +++…-`, `1 file changed, 265 insertions(+), 1 deletion(-)` |
| venv | `./.venv/bin/python --version` → `Python 3.12.13` (runnable; `uv run` NOT used) |
| Files present | `contracts/__init__.py` 13L · `contracts/vocabulary_sync.py` 101L · `services/gid_push.py` 835L · `tests/unit/contracts/test_vocabulary_sync_models.py` 125L · `tests/unit/services/test_gid_push_vocab.py` 406L |

**RUNG REACHED = PROVEN.** The `proven` predicate (canary GREEN + gfr spine
GREEN + env runnable) is satisfied by direct live re-run in this session:
canary 41 passed, gfr spine 207 passed, venv runnable. Rung is **capped at
proven → merged ship-dark, flag OFF**; NOT rounded to live/verified-realized —
the PR merge and the `VOCAB_SYNC_ENABLED=true` flip are operator-sovereign
one-way doors, untouched here.

---

## §1 Two-Sided Discriminating Canary — GREEN/RED Matrix

Command (canary + models): `./.venv/bin/python -m pytest tests/unit/services/test_gid_push_vocab.py tests/unit/contracts/test_vocabulary_sync_models.py -q` → **`41 passed in 0.47s`** (live, this session).

| # | FIRE item | Result | Live receipt (test-id + anchor) |
|---|---|---|---|
| 1 | **CANARY RED-1 — empty read REFUSED** | **GREEN** (guard correctly refuses) | `test_empty_none_refused`, `test_empty_list_refused` PASSED. Guard `gid_push.py:785` `if option_count == 0:` → `VocabSyncRefused{refuse_reason=empty}`, push not called. `test_refuse_short_circuits_before_credential_resolution` PASSED → refuse fires with NO url/token present (refuse is BEFORE creds, not an incidental url-skip). |
| 2 | **CANARY RED-2 — gross-truncation REFUSED** | **GREEN** (guard correctly refuses) | `test_gross_truncation_refused` PASSED → floor guard `gid_push.py:794` `if option_count < floor:` → `VocabSyncRefused{refuse_reason=gross_truncation}`. Boundary `test_exactly_at_floor_is_not_truncated` PASSED → `len == floor` publishes (only `< floor` refuses). |
| 3 | **CANARY GREEN — healthy set PUBLISHES** | **GREEN** | `test_healthy_set_pushes_with_generic_path` PASSED → push awaited once at `endpoint_path="/api/v1/vocabularies/sync"` (`gid_push.py:828`), payload validates as `VocabularySyncRequest`, `field_key=="vertical"`, no `gid` on wire. `test_healthy_set_http_roundtrip_hits_vocab_endpoint` PASSED (through the real `_push_to_data_service` helper). |
| 4 | **TEETH CHECK — two-sided mutation** | **GREEN (bites)** | **Re-run independently this session.** Mutation `gid_push.py:794` `option_count < floor` → `>= floor`, then `pytest test_gid_push_vocab.py -q` → **`6 failed, 23 passed`**. RED set: `test_gross_truncation_refused`, `test_exactly_at_floor_is_not_truncated`, `test_healthy_set_pushes_with_generic_path`, `test_healthy_set_http_roundtrip_hits_vocab_endpoint`, `test_healthy_but_no_url_skips`, `test_healthy_but_no_token_skips`. The **3 C-EMPTY tests stayed GREEN** (empty caught by untouched `==0` at `:785`). Reverted exactly → `git diff --stat` = `+265/−1`; `grep "option_count >= floor"` = **grep-zero residue**; post-revert canary = **41 passed**. |
| 5 | **THREE-LOCKS conformance** | **GREEN** | See §2. |
| 6 | **gfr SPINE non-regression** | **GREEN** | See §3 — **207 passed** (live). |
| 7 | **SHIP-DARK — default OFF** | **GREEN** | See §4 — live env receipt. |

**Teeth interpretation**: the mutation bites ONLY the truncation/healthy
discrimination and NOT the empty branch — a genuinely two-sided canary. The RED
is a broken guard the tests reject, never a shipped defect (G-THEATER clean:
reverted exactly, grep-zero residue).

---

## §2 Three-Locks Conformance Proof

**Lock-1 — generic plural path (`/api/v1/vocabularies/sync`, NEVER `/verticals/sync`)**
```
grep -n "vocabularies/sync" gid_push.py
  748:    Lock-1 generic plural path ``/api/v1/vocabularies/sync`` (NEVER
  828:        endpoint_path="/api/v1/vocabularies/sync",
grep -n "verticals/sync" gid_push.py
  749:    ``/verticals/sync``). Non-blocking with respect to the caller: all
```
`:828` is the sole live path literal; the only `/verticals/sync` occurrence is
the `:749` docstring prohibition (grep-zero as a real path).

**Lock-2 — `field_key: Literal["vertical"]` + `extra="forbid"`**
```
grep -n "field_key" contracts/vocabulary_sync.py     → 68:    field_key: Literal["vertical"]
grep -n 'extra="forbid"' contracts/vocabulary_sync.py → 66 (Request), 97 (Response)
```
Tests: `test_field_key_literal_accepts_vertical`, `test_field_key_rejects_other_value`,
`test_extra_forbid_rejects_unknown_field` PASSED.

**Lock-3 — NAME-keyed only; NEVER `enum_option.gid` / `vertical_id` on the wire**
```
grep -nE "vertical_id|gid" contracts/vocabulary_sync.py
  14:  … NEVER ``enum_option.gid`` / ``vertical_id`` (both   [docstring]
  46:    NEVER the Asana ``enum_option.gid`` nor the consumer's ``vertical_id``. [docstring]
```
Both hits are docstring prohibitions — no `gid`/`vertical_id` field declaration
exists. Tests `test_projection_carries_no_gid`, `test_no_gid_or_vertical_id_surface`
PASSED; the projection `project_enum_options_to_vocabulary_options` drops the gid.

**Ship-dark lock** — see §4 (new default-OFF flag, does not ride default-ON siblings).

---

## §3 gfr Certified-Spine Non-Regression Receipt

Command: `./.venv/bin/python -m pytest tests/unit/resolution/gfr -q` (live, this session)
```
207 passed in 0.54s
```
CON-007 floor GREEN, non-regressed. **Note**: the ADR/TDD "105-test" figure is
the stale frame-era count; the live certified directory is **207**, fully green.

---

## §4 Ship-Dark Flag Default-OFF Proof

Live receipt (this session), `VOCAB_SYNC_ENABLED` unset in env:
```
VOCAB_SYNC_ENABLED present in env : False
_is_vocab_sync_enabled exists     : True
_is_vocab_sync_enabled() (unset)  : False
with GID/STATUS push =true, vocab : False
SHIP-DARK OK: vocab path is DARK unless VOCAB_SYNC_ENABLED explicitly truthy
```
The last line is load-bearing: setting `GID_PUSH_ENABLED=true` **and**
`STATUS_PUSH_ENABLED=true` leaves the vocab path OFF — it does **not** ride the
default-ON sibling flags. This is why a NEW default-OFF flag was required:
reusing `GID_PUSH_ENABLED` (default-ON at `gid_push.py:95-96`) would ship
live-by-default, not dark. Tests: `test_unset_is_disabled`,
`test_shipdark_flag_unset_skips_push`, `test_default_on_push_flags_do_not_enable_vocab`
PASSED. **Flag is OFF at merge; nothing crosses the seam.**

---

## §5 Non-Regression Corroboration

| Surface | Command | Result |
|---|---|---|
| New unit (models + canary) | `pytest tests/unit/contracts/test_vocabulary_sync_models.py tests/unit/services/test_gid_push_vocab.py` | **41 passed** (live) |
| Existing push suite | `pytest tests/unit/services/test_gid_push.py tests/unit/services/test_scheduling_stratum_push.py` | **52 passed** (live) — account-status / gid-mappings paths unchanged |
| gfr spine | `pytest tests/unit/resolution/gfr` | **207 passed** (live) |
| Leaf guards intact | `grep -n "Nothing to push is not a failure"` | `:334` (gid-mappings, was :328) + `:560` (account-status, was :554), both **absent from the diff** — the +6 shift is `typing` gaining `Literal` |
| Combined baseline (gfr + integration) | `[QA-ATTESTED]` | `2 failed, 815 passed, 21 skipped, 1 xfailed, 25 errors` byte-identical before/after; all failures/errors are credential-absent LIVE-API tests (`*_real_api`, `TestLive*`), pre-existing. Not re-run in synthesis (76s + credential-gated); the three disjoint legs above independently establish non-regression on the touched surface. |

---

## §6 Defects / Edges (both fail-safe; neither blocks ship-dark merge)

Carried from qa-adversary; anchors re-verified live this session.

- **F-1 [LOW / observability — pre-enable hardening]** — `VocabularySyncResponse`
  is not argless-constructible (3 required fields, no defaults). The reused
  helper's 2xx-body fallback `parsed = response_model()` at **`gid_push.py:219`**
  (grep-confirmed) assumes argless-constructibility (siblings `GidPushResponse`
  / `AccountStatusPushResponse` are all-optional + `extra="ignore"`). Consequence:
  a 2xx whose body fails `model_validate` → fallback also raises → broad-catch →
  returns **False** + `vocab_sync_error` (never a false-success, never a bad
  write). **Fails SAFE. ZERO impact at ship-dark (flag OFF).** Not on either
  realization-predicate leg (refuse is request-side and proven; positive
  round-trip is sprint-4 integration). **Named pre-enable condition** gating the
  operator's later `VOCAB_SYNC_ENABLED=true` flip → route to principal-engineer:
  give `VocabularySyncResponse` field defaults (`inserted=0, updated=0, refused=[]`)
  or wrap `:219` in its own try/except.

- **F-2 [INFO / projection edge]** — `project_enum_options_to_vocabulary_options`
  skips only `opt.name is None` at **`gid_push.py:725`** (grep-confirmed), not
  empty/whitespace-only; a whitespace-only option projects to a degenerate
  `VocabularyOption(vertical_key="", name="")` and counts toward the floor.
  Cosmetic/fail-safe (unique `""` key, additive-only, no orphan). Coverage gap:
  `test_skips_nameless_option` covers `None` only. Fix (low priority): skip when
  `not opt.name.strip()`.

---

## §7 [PROPOSE — promote to autom8y-core] Follow-On (cross-repo sequencing)

The typed contract lives in a producer-local, SDK-home-ready, import-pure module:
`src/autom8_asana/contracts/vocabulary_sync.py`. The promotion marker is present:
```
grep -n "PROPOSE" contracts/vocabulary_sync.py
  21:[PROPOSE — promote to autom8y-core] This module is the interim SINGLE …
```
**Rationale**: autom8y-core is NOT co-located in this worktree — it is an
installed package only (`importlib.metadata.version('autom8y-core')` → **4.9.0**;
no co-located source dir under `src/`). The SDK-home per ADR §6 is therefore a
**separate-repo release**, not an in-span edit. The producer defines the single
importable module now and records the promotion as a follow-on (gfr
"core-client PROPOSE-only" precedent) so there is exactly one model definition,
never scattered duplicates.

> **Honest env drift recorded** (premise-integrity): the dispatch env-fact
> stated autom8y-core `4.6.0`; the worktree venv actually resolves **`4.9.0`**.
> Immaterial to the SDK-home decision — the load-bearing fact
> (installed-not-colocated → separate-repo release) holds at either version.

**ESCALATION → potnia (cross-repo sequencing dependency):** the sprint-2
consumer imports this contract **after** it is promoted to autom8y-core and the
core version is bumped. Core-bump-before-consumer is a genuine cross-repo
ordering dependency that exceeds implementation-layer scope. This is the
architect's escalate-to-potnia item, not a producer-side blocker (producer does
not block on autom8y-core; it ships the interim single-source module dark).

---

## §8 EC-2 Live-Read — Operator-Gated Note `[OPERATOR-GATED]`

The live enum-option read path
(`CustomFieldsClient.get(vertical_cf_gid, opt_fields=[…"enum_options"…])` →
`CustomField.enum_options`) requires live Asana credentials from AWS Secrets
Manager (`autom8y/asana/asana-pat`). That path is **operator-shell-only** and
`[UNATTESTED — DEFER-POST-HANDOFF]`. Sprint-1 is fully mocked in CI — no new
auth surface crosses the seam at ship-dark. The live probe is the operator's to
run at/after flip time; it is not a sprint-1 gate. (No new inbound attack
surface, no crypto/PII/session change in the producer path — the FEATURE-gate
security consult is not triggered by this ship-dark request-side contract.)

---

## §9 Env-Gated Items the Operator Must Run (before/at flip)

1. **EC-2 live-read probe** — run the `CustomFieldsClient.get(...)` enum-option
   read against the real vertical custom-field GID with live Asana creds
   (operator shell). Confirms the read shape matches the mocked contract.
2. **F-1 pre-enable hardening** — land the `VocabularySyncResponse` field-defaults
   fix (or `:219` try/except) via principal-engineer **before** flipping
   `VOCAB_SYNC_ENABLED=true`. This is the named pre-enable condition (not a merge
   blocker).
3. **Consumer-side deep FK coverage** — the 3-edge referential-coverage refuse
   (ADR §8) lives in the sprint-2 consumer (`VerticalService.upsert_by_key`); the
   producer refuses only what it can see (empty / floor). Consumer sprint gates
   that.
4. **Combined LIVE-API baseline** — optionally re-run `pytest tests/unit/resolution/gfr
   tests/integration` with Asana creds present to clear the 25 credential-absent
   errors (pre-existing; unrelated to this change).

---

## §10 Producer-PR Disposition — PUSH, NOT MERGE (surface only; NOT executed)

**Disposition**: the producer work is left **uncommitted in the worktree**, flag
OFF. `git log --oneline -1` → HEAD is the base tip `1eec7622`; producer changes
are uncommitted (`M gid_push.py` + untracked `contracts/`, `tests/unit/contracts/`,
`tests/unit/services/test_gid_push_vocab.py`). Remote is `origin` →
`git@github.com:autom8y/autom8y-asana.git`. Branch tracks `origin/main`; no
`origin/feat/dyn-enum-contract` exists yet.

The following are **surfaced for the operator — deliberately NOT executed**
(PR merge + flag flip are operator-sovereign one-way doors):

```bash
# from the worktree root:
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-dynenum

# 1. stage the 5 producer artifacts (+ the ADR/TDD/receipts docs if desired)
git add src/autom8_asana/contracts/ \
        src/autom8_asana/services/gid_push.py \
        tests/unit/contracts/ \
        tests/unit/services/test_gid_push_vocab.py

# 2. commit (ship-dark; flag OFF)
git commit -m "feat(vocab-sync): dyn-enum-contract producer half (ship-dark, VOCAB_SYNC_ENABLED default OFF)"

# 3. push the feature branch (sets its own upstream, does NOT touch main)
git push -u origin feat/dyn-enum-contract

# 4. open the PR (does NOT merge)
gh pr create --repo autom8y/autom8y-asana --base main --head feat/dyn-enum-contract \
  --title "dyn-enum-contract producer half — ship-dark (flag OFF)" \
  --body "Sprint-1 producer. Two-sided canary GREEN + teeth-proven; three locks held; gfr spine 207 GREEN; ship-dark default-OFF. Do NOT flip VOCAB_SYNC_ENABLED until F-1 pre-enable hardening lands. See .ledge/reviews/dyn-enum-contract-producer-receipts.md."
```

**Do NOT** run `gh pr merge` and **do NOT** set `VOCAB_SYNC_ENABLED=true` — those
are the operator's production-mutating levers.

---

## §11 GO / NO-GO

**RECOMMENDATION: GO** on the producer half — **proven → ready-to-merge,
ship-dark, flag OFF.**

- Two-sided discriminating canary has TEETH (independently mutation-proven this
  session: bites RED on miscalibration, GREEN on the healthy variant; reverted
  exactly, grep-zero residue — not theater).
- Three locks hold (Lock-1 generic path, Lock-2 `field_key` Literal + forbid,
  Lock-3 NAME-keyed no-gid).
- gfr spine unregressed (207 GREEN); existing push suite 52 GREEN.
- Ship-dark is real (new flag, default OFF, does not ride the default-ON siblings).
- F-1 and F-2 both fail SAFE with **zero effect at ship-dark merge**; F-1 is a
  named **pre-enable condition** gating the operator's later flip, not this merge.

**Rung reached**: PROVEN → merged ship-dark, flag OFF (cap honored — NOT rounded
to live/verified-realized). **Self-grade `[STRUCTURAL | MODERATE]`** (G-CRITIC
self-ref ceiling; STRONG is reserved for the rite-disjoint review-rite critic at
PT-07). **No production-mutating lever was pulled**: no commit, no push, no
merge, no flag flip — all surfaced in §10 for the operator.
