---
type: handoff
artifact_subtype: 10x-to-review
initiative: dyn-enum-contract
handoff_type: verified-realized-attestation-request
from_rite: 10x-dev
to_rite: review
from_station: principal-engineer / architect (producer span close)
created: 2026-07-01
status: proposed
rung: merged                 # producer half PROVEN→MERGED (ship-dark, flag OFF); verified-realized is review's to attest
evidence_grade_ceiling: "MODERATE — 10x-dev self-attestation ceiling (G-CRITIC / self-ref-evidence-grade-rule); STRONG is the rite-disjoint review critic's at PT-07"
producer_merge: "autom8y-asana main squash cb4b42017b71f582e7bd09945e96730e6f81ec33 (PR #175, merged 2026-07-01T07:26:03Z)"
consumer_state: "NOT BUILT — autom8y-data sprint-2 is a separate dre session, gated on autom8y-core model-promotion + PT-02 ratification"
---

# HANDOFF: 10x-dev → review — dyn-enum-contract (producer span close, 2026-07-01)

> **Who reads this first**: the review-rite disjoint critic (signal-sifter runs shell-heavy re-runs).
> **Boundary**: the PRODUCER half is proven→MERGED and ready for a rite-disjoint adversarial
> re-attestation NOW. The FULL verified-realized predicate (the LIVE cross-repo round-trip) is
> **run-deferred to PT-07-live** — it needs the consumer built + deployed + the producer flag enabled.

## §1 · What is PROVEN→MERGED (producer half)

`autom8y-asana` PR #175 (squash `cb4b4201`) merged to `main`, **ship-dark** (`VOCAB_SYNC_ENABLED`
default OFF; the vocab push has zero production callers = maximally dark). Bundles:

- **sprint-1 PRODUCER** — reads live Asana `enum_options` (the Vertical cf), projects a NAME-keyed
  option-SET snapshot, pushes to `POST /api/v1/vocabularies/sync` via the endpoint-parameterized
  `_push_to_data_service`, behind a two-sided producer hard-REFUSE (empty + gross-truncation floor)
  replacing the leaf guard *on the vocab path only*. New contract model `src/autom8_asana/contracts/vocabulary_sync.py`
  (`field_key: Literal["vertical"]` + `extra="forbid"`), tagged `[PROPOSE → autom8y-core]`.
- **sprint-3 COHERENCE** — a drift-WARN observability layer (`VocabSyncDriftDetected{drift_reason}`,
  WARN+metric only, name-collision / disabled-carried / degenerate-name signals), the compose-up seed
  (a 2nd `field_key` is a DATA addition), and the authored-but-inert live round-trip harness
  (`tests/integration/test_dyn_enum_roundtrip.py`, 6 legs).

## §2 · 10x-dev self-attestation (MODERATE) — the receipts the review critic re-fires

Every claim below was produced + re-verified in-rite at MODERATE; the review critic re-fires them
rite-disjoint for STRONG.

| Claim | Receipt (re-fire target) |
|---|---|
| Two-sided producer hard-REFUSE has TEETH | `test_gid_push_vocab.py` — empty/truncated → REFUSE (RED input rejected), healthy → publish (GREEN); qa mutation `option_count < floor → >= floor` flipped 6 tests RED, empty stayed GREEN; reverted exact |
| Drift-WARN is observability-only (no mutate/mint/codegen/delete, ADR-S4-001) | AST-pure `detect_vocab_drift` (count-reads + local append + return); contract has NO `deleted` field; qa real-source mutation M1/M2/M3 both-sides caught |
| Three locks | Lock-1 generic path literal (`/verticals/sync` grep-zero as a real path); Lock-2 `field_key: Literal["vertical"]` + `extra="forbid"`; Lock-3 no `gid`/`vertical_id` wire key (grep-zero) |
| Compose-up seed (DEFER-1-READY, registry NOT built) | grep-zero `field_key==` branch; `Literal["vertical"]` single-value; `TestComposeUpSeed` 3/3; fleet registry NOT built (G-DEFER) |
| Strictly-additive / gfr spine non-regression (CON-007) | gfr `tests/unit/resolution/gfr` = **207 GREEN** before+after; combined baseline byte-identical; leaf guards untouched |
| Ship-dark | `VOCAB_SYNC_ENABLED` default OFF + does not ride the default-ON siblings; push unwired |
| Full CI gate GREEN | PR #175: Lint&Type-Check (mypy-strict), 4 test shards, Coverage/Fleet/Semantic/Spectral/OpenAPI, CodeQL, Fuzz, gitleaks, dependency-review, **CodeRabbit review pass** — all GREEN; mergeStateStatus CLEAN |
| F-1 hardened fail-CLOSED | vocab 2xx-body-parse-failure → deterministic FAILURE + `VocabSyncContractParseFailed` alarm (opt-in `strict_response_parse`; siblings byte-identical) — NOT degraded to silent no-op |

Full receipts: `.ledge/reviews/dyn-enum-contract-producer-receipts.md` + `dyn-enum-contract-coherence-receipts.md`.

## §3 · The realization predicate (the review's attestation target) + what is PENDING

> "Verified-realized" = a NEW or renamed Asana enum_option round-trips into `autom8y-data.verticals`
> via additive-upsert with existing ids + FK children (campaigns / asset_verticals ~43K /
> offers.category) intact within one sync cycle, AND an empty/truncated Asana read is hard-REFUSED
> with an alert (never applied) — asserted by a LIVE/integration test on a real option-set round-trip.
> NOT "endpoint merged", NOT "PRs green". (`.know/telos/dyn-enum-contract.md`)

**The FULL predicate cannot be attested yet** — it needs the CONSUMER half. PENDING:
1. **autom8y-core model-promotion** — home `VocabularySync*` in autom8y-core (a minor bump); the consumer cannot import until this lands (the producer runs on its interim in-repo copy). G-PROPAGATE cross-repo dep.
2. **Consumer sprint-2** (autom8y-data, dre) — the `POST /api/v1/vocabularies/sync` endpoint + `VerticalService.upsert_by_key` (REC-1: route THROUGH `VerticalService.create`, extend with update-name; MySQL `ON DUPLICATE KEY UPDATE`, **no `GET_LOCK`** per ADR §4; 3-edge FK coverage incl. `offers.category` STRING; `extra=forbid`→422; NEVER DELETE). PT-02 rite = dre-native (operator-ratified).
3. **Enable-order (BC-1)** — consumer DEPLOYED before the producer `VOCAB_SYNC_ENABLED` flip; F-1 pre-enable hardening is DONE.
4. **The LIVE round-trip** — the authored harness `tests/integration/test_dyn_enum_roundtrip.py` runs GREEN post-deploy: `AUTOM8Y_DATA_URL=… AUTOM8Y_DATA_API_KEY=… DYN_ENUM_LIVE_ROUNDTRIP=1 ./.venv/bin/python -m pytest tests/integration/test_dyn_enum_roundtrip.py -m integration -v`. Signal-sifter attests. `[UNATTESTED — DEFER-POST-HANDOFF: PT-07-live]`.

## §4 · What the review rite can do NOW vs at PT-07-live

- **NOW (producer-half, STRONG-eligible)**: rite-disjoint adversarial re-attestation of the merged
  producer surface — independently mutation-probe the two-sided canary + the drift-WARN teeth, verify
  the three locks + the AST-purity + the gfr-spine non-regression at `cb4b4201`. This upgrades the
  producer-half self-grade MODERATE → STRONG on the producer surface.
- **AT PT-07-live (post-consumer)**: the FULL verified-realized round-trip attestation (both halves +
  deploy + enable + the live harness). This is the binding telos gate.

## §5 · Rungs + two critics (G-CRITIC — do NOT conflate)

| Rung | State |
|---|---|
| authored | ✓ (ADR, TDDs) |
| proven | ✓ (producer half, in-rite MODERATE, mutation-teeth) |
| merged | ✓ (producer half, `cb4b4201`, ship-dark) |
| verified-realized | ✗ PENDING — the review-rite disjoint critic at PT-07-live, post-consumer |

- **Critic 1 — in-rite qa-adversary** (10x-dev): MODERATE, done (this handoff carries it).
- **Critic 2 — rite-disjoint review critic** (review rite, signal-sifter runs the live round-trip): the STRONG upgrade — producer-surface NOW + full verified-realized at PT-07-live.

## §6 · DEFER register (watch-registered, NOT built)

- **DEFER-1** fleet cf-contract registry — ESCALATE-only at N≥3 (2nd `field_key` binds `/vocabularies/sync` AND 3rd consuming service). One-way door. NOT built (compose-up seed keeps the door open at data-cost).
- Legacy `Vertical(Enum)` / `_missing_` — permanent-OUT, non-canonical.

## §7 · Operator levers at this seam (surface — I do NOT execute)

- **Enter the review rite** (to run the producer-half adversarial re-attestation now):
  `ari sync --rite=review` (SINGULAR) + ONE CC restart. Then the review procession loads this handoff.
- **Downstream (for the full verified-realized)**: stand up the consumer dre session (autom8y-core
  promotion → sprint-2 → deploy) → flip `VOCAB_SYNC_ENABLED` (consumer-deployed-first) → PT-07-live.
- **Producer merge**: DONE (`cb4b4201`).

*This handoff is the 10x-dev producer-span close. The producer half is proven→merged @ MODERATE.
STRONG (producer-surface now + full verified-realized at PT-07-live) is the rite-disjoint review
critic's. Do NOT dispatch review specialists from 10x-dev — the operator switches rites.*
