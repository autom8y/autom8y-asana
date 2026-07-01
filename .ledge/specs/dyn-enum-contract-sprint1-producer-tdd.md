---
type: spec
subtype: sprint-delta-tdd
status: accepted
initiative: dyn-enum-contract
sprint: sprint-1 (producer — autom8y-asana)
station: architect (design-only; NO production code this phase)
date: 2026-07-01
rite: 10x-dev
rung: authored            # CAP = authored→proven→merged (ship-dark, flag OFF). NEVER live/verified-realized.
evidence_grade_ceiling: "MODERATE — self-referential authorship ceiling (self-ref-evidence-grade-rule + G-CRITIC); STRONG belongs to the review-rite disjoint critic at PT-07"
governing_spec: ".ledge/decisions/ADR-dyn-enum-contract-shared-contract.md  # the LOCKED sole spec; this doc is a DELTA against it, adds nothing it forbids"
build_head_reverified: "producer autom8y-asana feat/dyn-enum-contract @ 1eec76223af2be9fd2d25cc3a256e0a3fbaaafad (C4 anchor re-verification — all producer anchors LIVE at this HEAD)"
---

# TDD-Delta — dyn-enum-contract sprint-1 PRODUCER (autom8y-asana)

> **A DELTA, not a rewrite.** The LOCKED contract is `ADR-dyn-enum-contract-shared-contract.md`
> (three locks §2, EC-1=MySQL §3, PT-04 Option-B §4, REC-1 §5, SDK-home §6, 3-edge FK denom §8).
> This doc resolves the six producer-side build details the ADR left to the build station, each
> grounded in a LIVE `{path}:{line}` re-verified at build HEAD `1eec7622` (C4). It adds the
> producer PUSH half; the consumer endpoint + `vocab_upsert` are sprint-2 (autom8y-data). CAP =
> **merged ship-dark, flag OFF** — the live enable (a NEW flag flip) is the operator's.

## C4 — producer anchor re-verification @ build HEAD 1eec7622 (all LIVE)

| Anchor | ADR cite | LIVE @ 1eec7622 | Verbatim |
|---|---|---|---|
| flag env-var constant | `gid_push.py:62` | `gid_push.py:62` | `GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"` |
| flag gate (DEFAULT-ON idiom) | `gid_push.py:95` | `gid_push.py:95-96` | `val = os.environ.get(...).lower()` → `return val not in {"false", "0", "no"}` |
| 2nd push-path flag (DEFAULT-ON) | — | `gid_push.py:371,:387` | `STATUS_PUSH_ENABLED_ENV_VAR = "STATUS_PUSH_ENABLED"` (per-path flag convention) |
| **DEFAULT-OFF flag idiom (ship-dark precedent)** | — | `cache_warmer.py:242-246` | `os.environ.get("ASANA_VERTICAL_BACKFILL_ENABLED", "").lower() in ("1","true","yes")` |
| endpoint-parameterized push helper | `gid_push.py:163` | `gid_push.py:163-172` | `async def _push_to_data_service(*, endpoint_path: str, payload: dict[str, Any], response_model: type[BaseModel], …) -> bool` |
| leaf empty-guard path A (gid-mappings) | `gid_push.py:328` | `gid_push.py:328` | `return True  # Nothing to push is not a failure` |
| leaf empty-guard path B (account-status) | `gid_push.py:554` | `gid_push.py:554` | `return True  # Nothing to push is not a failure` |
| account-status endpoint_path (reuse exemplar) | `gid_push.py:564` | `gid_push.py:564` | `endpoint_path="/api/v1/account-status/sync"` |
| untyped seam (selected value, NOT the set) | `gid_push.py:490` | `gid_push.py:490` | `"vertical": str(vertical),` (inside `_build_status_entries` — account-status path) |
| live option-SET read field | `custom_field.py:113` | `custom_field.py:113-116` | `enum_options: list[CustomFieldEnumOption] | None` |
| option `enabled` (observability-only) | `custom_field.py:35` | `custom_field.py:35-38` | `enabled: bool | None` |
| model `extra="ignore"` (per ADR-0005) | `custom_field.py:3` | `custom_field.py:3` | `Per ADR-0005: Uses Pydantic v2 with extra="ignore"` |
| live-read client entry | shape ctx | `clients/custom_fields.py:78-84,:127` | `async def get(self, custom_field_gid, *, raw=False, opt_fields=…) -> CustomField …` → `CustomField.model_validate(data)` |
| autom8y-core pin (absorbs SDK bump) | `pyproject.toml:26` | `pyproject.toml:26` | `"autom8y-core>=4.2.0,<5.0.0"` |
| alert emitter | — | `gid_push.py:22,:33` | `from autom8_asana.lambda_handlers.cloudwatch import emit_metric` · `_BRIDGE_FLEET_NAMESPACE = "Autom8y/AsanaBridgeFleet"` |

**Net-new confirmed** (grep @ HEAD): `VocabularySync* / vocabulary_sync / VOCAB_SYNC_ENABLED / VocabularyOption` = **0 hits** in `src/`; `/vocabularies/sync` = **0 hits** (producer only PUSHes; the endpoint is the consumer's). No `contracts/` dir today. No anchor falsified vs the ADR §7 table.

---

## D-1 · TYPED MODEL LOCUS — producer-local, SDK-home-ready

**Decision.** Home the three models in ONE new importable producer-local module:
`src/autom8_asana/contracts/vocabulary_sync.py` (NEW; `contracts/` dir does not exist today — this is the net-new home). Structured so promotion to autom8y-core is a `git mv` + re-export, not a rewrite.

```python
# src/autom8_asana/contracts/vocabulary_sync.py   (SDK-home-ready; promote to autom8y-core per PROPOSE below)
from typing import Literal
from pydantic import BaseModel, ConfigDict

class VocabularyOption(BaseModel):
    vertical_key: str            # Lock-3: normalize(option.name); NEVER enum_option.gid / vertical_id
    name: str                    # display name (consumer UPDATE-name target; unique=True consumer-side)
    enabled: bool | None = None  # ADR §2: drift-observability ONLY; NOT a stored column

class VocabularySyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")   # Lock-2 discriminator integrity; NFR-003 / BC-1 → 422 on unknown
    field_key: Literal["vertical"]               # Lock-2: discriminator, from row one
    options: list[VocabularyOption]              # the full option-SET (not the selected value)

class RefusedRow(BaseModel):
    vertical_key: str
    reason: str

class VocabularySyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")    # per ADR §2 typed-envelope block
    inserted: int
    updated: int
    refused: list[RefusedRow]
```

Grounding: model shapes are verbatim from ADR §2 (`:101-113`); `field_key: Literal["vertical"]` = Lock-2 (`:82-87`); `vertical_key = normalize(option.name)` = Lock-3 (`:89-96`); `enabled` observability-only, NOT stored (ADR §2 `:109`,`:116-118`; the `verticals` schema is id/key/name only, consumer `_platform.py:131-149`).

**`extra="forbid"` on BOTH Request and Response** (per brief + ADR §2 `:104`/`:113`). Note the divergence from the producer's existing response envelopes, which use `extra="ignore"` for forward-compat (`GidPushResponse` `gid_push.py:83`; `AccountStatusPushResponse` `gid_push.py:377`). This is **intentional and safe here, NOT an oversight**, for two reasons: (1) the model is homed ONCE in the SDK (D-1 PROPOSE / ADR §6) so a future Response-field addition is a single atomic SDK bump that moves BOTH sides together — no producer/consumer skew, which is exactly the skew `extra="ignore"` defends against; (2) the entire push seam is broad-catch non-blocking (`push_status_to_data_service` docstring `gid_push.py:510-511` "all exceptions are caught and logged so that a push failure never propagates to the cache warmer") — so a response-parse mismatch degrades to a logged non-fatal + metric, never a crash. The vocab push inherits this non-blocking contract.

**[PROPOSE — promote to autom8y-core] (follow-on, cross-repo, NOT in this span).** autom8y-core is NOT co-located in this worktree (installed pkg 4.6.0 only) — so ADR §6 SDK-home is a SEPARATE-repo release, not an in-span edit. The producer-local module is the interim SINGLE definition (no scattered duplicates). Promotion = an autom8y-core minor bump (e.g. 4.7.0) homing `VocabularyOption / VocabularySyncRequest / VocabularySyncResponse`, absorbed by both repos' existing `>=4.2.0,<5.0.0` pins (producer `pyproject.toml:26`) with **no pin-range edit** (defeats R6 release-coupling). Precedent: `VerticalsListResponse` at autom8y-core `clients/data_intake.py:473` (ADR §6 `:236`) + the gfr "core-client PROPOSE-only" pattern.
**⇒ ESCALATE to potnia (cross-repo dependency):** the consumer sprint-2 imports these models from `autom8y_core` — so the core promotion must land BEFORE sprint-2 binds its typed parse (or, at the latest, before live-enable, since ship-dark holds the seam dark until then). NO second definition is authored in either repo; promotion is a move. This keeps G-PROPAGATE (§6: "0 per-repo duplicates") intact despite the non-co-located core.

---

## D-2 · PRODUCER REFUSE-LAYER — the two-sided guard + the explicit producer↔consumer boundary

**Decision.** Author a NEW producer function (e.g. `push_vocabulary_to_data_service(...)`) in `gid_push.py` whose emptiness/coverage decision point INVERTS the leaf calibration. This is what the ADR §2 / Correction 5 means by "REPLACES the leaf guard FOR THE VOCAB PATH ONLY":

- The vocab function does **not** edit the shared leaf guards. `gid_push.py:328` (gid-mappings) and `gid_push.py:554` (account-status) KEEP `return True  # Nothing to push is not a failure` — those two paths are snapshot-safe leaves. The "replace" is **semantic**: at the structurally-equivalent "is the read empty?" point, the vocab path emits an ALERT and REFUSES (`return False`) instead of returning success. **Do NOT copy the `:328`/`:554` `return True` body into the vocab path.**

**The two-sided producer guard (what the PRODUCER refuses):**

| Read shape | Producer action | Criterion (producer-visible) |
|---|---|---|
| **EMPTY** (`enum_options is None` or `len == 0`) | **REFUSE + ALERT**, `return False`, publish NOTHING | unambiguous; matches telos NEGATIVE leg ("empty … hard-REFUSED") |
| **GROSS-TRUNCATION** (`0 < len < floor`) | **REFUSE + ALERT**, `return False`, publish NOTHING | `len(options) < VOCAB_SYNC_MIN_OPTIONS` (env-configured integer floor) |
| **HEALTHY full set** (`len >= floor`) | project NAME-keyed snapshot → (would-)publish | passes the guard |

**The producer↔consumer refuse BOUNDARY (state it explicitly — this is the load-bearing architectural line):**

- **PRODUCER (sprint-1, autom8y-asana) refuses on what it can SEE:** EMPTY + GROSS-TRUNCATION-vs-floor. The producer has **no access** to the consumer's FK-child tables (campaigns / asset_verticals / offers.category live in autom8y-data), so the producer **cannot** compute the deep "missing-any-FK-referenced-key" check. Its guard is a cheap, defense-in-depth backstop that catches the catastrophic empty/near-empty read from a degraded Asana API before transport.
- **CONSUMER (sprint-2, autom8y-data) owns the DEEP refuse:** the 3-edge FK-referential-coverage hard-refuse (FR-004; ADR §8 G-DENOM=3 — campaigns `_advertising.py:80`, asset_verticals `_advertising.py:326`, offers.category STRING `_platform.py:162`). Those teeth live where the FK data lives. **This TDD does not build them** — it names the boundary so sprint-1 does not over-reach and sprint-2 does not assume the producer covered it.

This is correct layering (defense-in-depth with the authoritative check at the layer that owns the data), NOT a bandaid.

**The floor is a robust, operator-tunable knob — not a magic number.** `VOCAB_SYNC_MIN_OPTIONS` (env int, default `1` → only truly-empty trips by default, so a legitimately-small set never false-positives). STRONG operator guidance: set it near the known population at enable time (consumer hint `vertical.py:65` "~40 verticals" is consumer knowledge — do NOT hardcode it producer-side; expose the lever). The richer **DROP-vs-prior-known-set** signal (a disappeared/renamed option) is deliberately DEFERRED to the sprint-3 drift observer (H workstream: asana-live vs data-side divergence; BC-3 "a disappeared option is a drift WARN → human runbook, never an auto-delete"), NOT collapsed into sprint-1. Sprint-1 producer = EMPTY + floor.

**ALERT mechanism.** REFUSE emits via the existing fleet emitter — `emit_metric("VocabSyncRefused", 1, dimensions={"refuse_reason": "empty"|"gross_truncation"}, namespace=_BRIDGE_FLEET_NAMESPACE)` (`gid_push.py:22`,`:33`; mirrors `_emit_status_push_skipped` `gid_push.py:52-57`) + a structured **ERROR**-level log. NFR-004 (structured logging + deploy-gate) is satisfied by the distinct metric name enabling a deploy-gate alarm.

---

## D-3 · PUSH WIRING — reuse the endpoint-parameterized helper; mock the (not-yet-existent) consumer

**Decision.** Reuse `_push_to_data_service` (`gid_push.py:163`) unchanged, passing `endpoint_path="/api/v1/vocabularies/sync"` (Lock-1 generic plural path — NEVER `/verticals/sync`; ADR §2 `:72-80`). The helper already carries `endpoint_path="/api/v1/account-status/sync"` for the sibling path (`gid_push.py:564`), so this is parameter reuse, not a new transport:

```python
return await _push_to_data_service(
    endpoint_path="/api/v1/vocabularies/sync",          # Lock-1
    payload=request.model_dump(mode="json"),            # VocabularySyncRequest → dict (helper takes dict, :166)
    response_model=VocabularySyncResponse,              # helper takes type[BaseModel], :167
    metric_dimensions={"field_key": "vertical", "option_count": str(len(request.options))},
    log_prefix="vocab_sync",
    base_url=base_url, token=token,
)
```

The consumer endpoint does **not exist yet** (sprint-2). Sprint-1 is unit-tested against a **mocked** `_push_to_data_service` / mocked HTTP: assert the correct `endpoint_path`, that the serialized payload conforms to `VocabularySyncRequest` (field_key + NAME-keyed options), and that REFUSE short-circuits BEFORE any push call. No live consumer contact in sprint-1 (ship-dark). Auth/URL resolution reuses the existing S2S plumbing (`_get_data_service_url` `gid_push.py:138`, `_get_auth_token`/`resolve_secret_from_env` `gid_push.py:147-160`) — NFR-003 S2S parity for free.

---

## D-4 · SHIP-DARK FLAG — a NEW flag defaulting OFF (the ADR ship-dark contract, made real)

**Decision.** Gate the vocab push behind a NEW, SEPARATE flag `VOCAB_SYNC_ENABLED`, **defaulting OFF**. This is REQUIRED, not stylistic: `GID_PUSH_ENABLED` DEFAULTS **ON** (`gid_push.py:95-96` returns `val not in {"false","0","no"}` — true unless explicitly falsy), as does `STATUS_PUSH_ENABLED` (`gid_push.py:387`). Reusing either would ship the vocab path LIVE-by-default — the opposite of ship-dark.

Follow the per-push-path flag convention (each path owns its kill-switch: `:62`, `:371`) but INVERT the default using the in-tree DEFAULT-OFF idiom from `cache_warmer.py:242-246`:

```python
VOCAB_SYNC_ENABLED_ENV_VAR = "VOCAB_SYNC_ENABLED"

def _is_vocab_sync_enabled() -> bool:
    # DEFAULT OFF (ship-dark). Mirror ASANA_VERTICAL_BACKFILL_ENABLED (cache_warmer.py:242), NOT
    # _is_push_enabled (gid_push.py:95, default-ON). Enabled ONLY when explicitly truthy.
    return os.environ.get(VOCAB_SYNC_ENABLED_ENV_VAR, "").lower() in ("1", "true", "yes")
```

`push_vocabulary_to_data_service` first-lines `if not _is_vocab_sync_enabled(): <log disabled + metric>; return False` (mirrors `push_status_to_data_service` `gid_push.py:523-529`). **Merge state: flag UNSET → OFF → nothing crosses the seam.** The live enable (setting `VOCAB_SYNC_ENABLED=true`) is an OPERATOR lever, enable-ordered AFTER the consumer endpoint is deployed (CON-010/BC-1) — do NOT flip in this build.

---

## D-5 · THE READ — live `enum_options` off the Vertical cf; mocked in unit, operator-gated live probe

**Decision.** Read the live option-SET off the Vertical custom field via `CustomFieldsClient.get(vertical_cf_gid, opt_fields=[…, "enum_options", "enum_options.name", "enum_options.enabled"])` → `CustomField.enum_options: list[CustomFieldEnumOption]` (`custom_field.py:113`; client `custom_fields.py:78-127`). This is the option-SET, distinct from the selected-value read that is the untyped gap today (`gid_push.py:490` `str(vertical)` is a per-entry *selected* value; `default.py:258-263` reads `enum_value.name` — the *selected* value). The Vertical cf is identified by name `"vertical"` in existing paths (`intake_create_service.py:332`, `vertical_backfill.py:212`); resolving its gid (config constant vs name-lookup) is a principal-engineer implementation seam.

**Projection.** `enum_options` → `list[VocabularyOption]` via `vertical_key = normalize_vertical_key(option.name)`. No canonical normalizer exists to reuse (only ad-hoc `.lower()` at `batch.py:169`, `vertical_backfill.py:238`) — so author a single deterministic `normalize_vertical_key(name) -> str` co-located with the projection (shape §7 emergent sanctions "NameNormalizer internals … round-trips whitespace/case variants"). It MUST be pure + unit-tested on case/whitespace variants. **First-sync key-MATCH against the consumer's existing `verticals.key` set is NOT sprint-1's job** — that is RR3 / the sprint-4 read-only dry-run (MATCH / INSERT-CANDIDATE / ORPHAN-RISK). Sprint-1 owns a deterministic, testable normalization; sprint-4 proves it matches.

**EC-2 live creds are operator-shell-only.** The CODE is unit-tested with **mocked** `enum_options` (no live Asana call in CI — do NOT assume CI credential parity, ADR §9 EC-2). The LIVE probe (a real read against AWS Secrets Manager `autom8y/asana/asana-pat`) is **operator-gated**, surfaced here as a build-phase step, NOT run by this station. `[UNATTESTED — DEFER-POST-HANDOFF: dyn-enum-contract/EC-2-credential-path]`.

---

## D-6 · TWO-SIDED DISCRIMINATING CANARY — the falsifiable shape for qa-adversary

Hand qa-adversary this spec. The RED cases are deliberately-broken **INPUTS the guard CORRECTLY REJECTS** — never a defect injected into production code (G-THEATER forbidden). A canary with TEETH bites ONLY on the defect; the no-defect variant passes GREEN.

| # | Fixture (mocked `enum_options`) | Env | Expected | Asserts | Grade |
|---|---|---|---|---|---|
| **C-EMPTY** | `None` / `[]` | `VOCAB_SYNC_ENABLED=true` | `push_vocabulary_…` returns `False`; `VocabSyncRefused{refuse_reason=empty}` emitted; **`_push_to_data_service` NOT called** | empty read hard-REFUSED, never transported (telos NEGATIVE) | RED-input→correctly-rejected |
| **C-TRUNCATED** | `len < VOCAB_SYNC_MIN_OPTIONS` (set floor high, e.g. `=5`, feed 2) | `=true`, `VOCAB_SYNC_MIN_OPTIONS=5` | returns `False`; `VocabSyncRefused{refuse_reason=gross_truncation}`; push NOT called | gross-truncation hard-REFUSED (defense-in-depth) | RED-input→correctly-rejected |
| **C-HEALTHY** | full valid set (`len >= floor`) | `=true`, floor `=1` | returns `True`; `_push_to_data_service` called ONCE with `endpoint_path="/api/v1/vocabularies/sync"`, payload validates as `VocabularySyncRequest` (field_key="vertical", NAME-keyed options) | healthy set projects + (would-)publishes | GREEN |
| **C-SHIPDARK** | full valid set | flag UNSET (default OFF) | returns `False`; disabled-log + skip metric; push NOT called | ship-dark holds; unset ⇒ dark | GREEN (dark) |
| **C-NAMEKEY** | options `"General Practice"`, `" general  practice "` | `=true` | both normalize to the SAME `vertical_key`; no `enum_option.gid` / `vertical_id` in payload | Lock-3 NAME-keying; whitespace/case round-trip | GREEN |
| **C-SPINE** | — | — | the gfr **105-test** certified spine GREEN (CON-007 mechanical gate) | strictly-additive; no spine regression | GREEN (non-regression) |

Discrimination property: C-EMPTY and C-TRUNCATED trip the guard RED **because the input is broken**; C-HEALTHY (the no-defect variant) passes the SAME guard GREEN. If C-HEALTHY ever REFUSES, or C-EMPTY/C-TRUNCATED ever PUBLISH, the guard is miscalibrated. The floor being env-configurable makes C-TRUNCATED deterministic without hardcoding consumer knowledge.

---

## Module / file layout (the DELTA surface)

| File | Change | Why |
|---|---|---|
| `src/autom8_asana/contracts/vocabulary_sync.py` | **NEW** | D-1 typed models (SDK-home-ready; promote to core via PROPOSE) |
| `src/autom8_asana/services/gid_push.py` | **ADD** `VOCAB_SYNC_ENABLED_ENV_VAR`, `_is_vocab_sync_enabled()`, `push_vocabulary_to_data_service()`, `normalize_vertical_key()` (or a sibling projection module) | D-2/D-3/D-4/D-5 push + refuse + flag + projection |
| `tests/…/test_gid_push_vocab.py` (+ `test_vocabulary_sync_models.py`) | **NEW** | D-6 two-sided canary + model/normalizer unit tests |
| shared leaf guards `gid_push.py:328`,`:554` | **UNCHANGED** | vocab path INVERTS semantically; gid-mappings/account-status keep the leaf guard |
| `_push_to_data_service` `gid_push.py:163` | **UNCHANGED** | reused via `endpoint_path` param (D-3) |

---

## Lock / REC-1 / ship-dark conformance

| Invariant | Honored by | Anchor |
|---|---|---|
| **Lock-1** generic `POST /api/v1/vocabularies/sync` (never `/verticals/sync`) | D-3 `endpoint_path` literal | ADR §2 `:72`; `gid_push.py:163`,`:564` |
| **Lock-2** `field_key` discriminator = `"vertical"` from row one | D-1 `field_key: Literal["vertical"]` + `extra="forbid"` | ADR §2 `:82`,`:102-104` |
| **Lock-3** NAME-keying `vertical_key`, never gid/`vertical_id` | D-1 `vertical_key` + D-5 `normalize_vertical_key` | ADR §2 `:89-96` |
| **REC-1** route consumer writes through `VerticalService` (no bespoke store) | **N/A to producer** — producer only PUSHes; REC-1 is the sprint-2 consumer store contract | ADR §5 `:211-229` |
| **ship-dark** flag OFF at merge | D-4 NEW `VOCAB_SYNC_ENABLED` default OFF | `cache_warmer.py:242` idiom (NOT `gid_push.py:95`) |
| **CON-007** strictly-additive to gfr 105-spine | D-6 C-SPINE gate; net-new files only | ADR §10 `:370` |
| **CON-008** Asana live enum_options = single source-of-record | D-5 one-way read | ADR §2 `:119-120` |

REC-1 clarification: the sprint-1 producer has no write path to `verticals` — it constructs the typed request and pushes it. The single-writer / additive-upsert / DELETE-forbidden invariants (REC-1, ADR §5) are the CONSUMER's `VerticalService.upsert_by_key` (sprint-2). Naming it here prevents the producer from growing any write-shaped surface.

---

## Risks + reversibility (one-way vs two-way doors)

| Risk | Disposition | Door |
|---|---|---|
| **R6 release-coupling** (models drift if duplicated per-repo) | producer-local module is the interim SINGLE def; PROPOSE core-promotion is a MOVE, not a copy; consumer imports post-promotion. ESCALATE the core-bump sequencing to potnia (cross-repo dep). | two-way (additive SDK bump) |
| **`extra="forbid"` on Response** vs producer forward-compat | safe: SDK-atomic bump moves both sides together (§D-1) + broad-catch non-blocking (`gid_push.py:510`) degrades a parse mismatch to a logged non-fatal | two-way |
| **EC-2 live-read cred scope** | code mocked; live probe operator-gated; producer REFUSE is defense-in-depth on a truncated live read | n/a (deferred) |
| **RR3 first-sync key-mismatch** | out of sprint-1 scope; deterministic normalization here, MATCH-proof in sprint-4 dry-run | n/a |
| **flag flip to live** | operator lever, enable-ordered after consumer deploy (CON-010/BC-1) | **one-way once real data flows** — guarded by ship-dark + operator sovereignty |
| producer builds a `verticals` writer / DELETE | FORBIDDEN — producer has no write path; REC-1/CON-004 are consumer-side | one-way (guarded: not built) |

## Handoff criteria (sprint-1 producer → proven)

- [ ] `contracts/vocabulary_sync.py` net-new; `extra="forbid"` on Request+Response; `field_key: Literal["vertical"]`; `enabled` observability-only.
- [ ] `push_vocabulary_to_data_service` reuses `_push_to_data_service(endpoint_path="/api/v1/vocabularies/sync")`; REFUSE short-circuits before push.
- [ ] `VOCAB_SYNC_ENABLED` NEW + default OFF (backfill idiom); leaf guards `:328`/`:554` untouched.
- [ ] Two-sided canary (D-6) GREEN: C-EMPTY/C-TRUNCATED REFUSE, C-HEALTHY publishes, C-SHIPDARK dark, C-NAMEKEY normalizes, C-SPINE (gfr 105) non-regressed.
- [ ] EC-2 live probe surfaced as operator-gated (not run); models mocked in CI.
- [ ] `[PROPOSE — promote to autom8y-core]` recorded + core-bump sequencing escalated to potnia.
- [ ] Flag OFF at merge (ship-dark). Rung caps at **merged**; live/verified-realized is operator/PT-07-gated.

**Evidence grade:** `[STRUCTURAL | MODERATE]` — self-referential authorship ceiling (self-ref-evidence-grade-rule + G-CRITIC). STRONG belongs to the review-rite disjoint critic at PT-07. Every claim carries a LIVE `{path}:{line}` @ build HEAD 1eec7622 (G-PROVE); no adjectives standing in for receipts.
