---
type: telos
initiative_slug: dyn-enum-contract
authored_at: 2026-06-30T00:00:00Z
authored_by: main-thread (Claude) at OPERATOR DIRECTION — drafted for ratification; user-sovereign per telos-integrity-ref §3 Gate-A
ratified_by: "operator (Tom Tenuta) — countersigned 2026-07-01 (as-drafted)"
rite: 10x-dev
schema_version: 1
code_truth_anchor: "origin/main ca28251d (asana producer + gfr/gfr-dynvocab doctrine substrate) + autom8y-data HEAD (consumer); cwd chore/bump-core-4.6.0 f4f924d2 is ~25 commits behind — build proceeds against main + data HEAD, not cwd"
ratification_status: "RATIFIED 2026-07-01 (operator Tom Tenuta countersign, as-drafted; both [OPERATOR-SET] fields approved: verification_deadline 2026-07-23, rite_disjoint_attester = review-rite external critic). Gate-A CLOSED. Drafted 2026-06-30; arch-validated (HANDOFF-arch-to-10x, adversary PASS-WITH-CONDITIONS) before countersign."
---

# Telos Declaration — dyn-enum-contract (Dynamic Enum-Option-Set Sync Contract)

> **RATIFIED 2026-07-01 — operator (Tom Tenuta) countersigned, as-drafted.** Drafted by the
> main thread at operator direction (user-sovereign per `telos-integrity-ref` §3 Gate-A);
> mirrors the gfr / gfr-dynvocab precedent (`authored_by: main-thread at OPERATOR DIRECTION
> — drafted for ratification`; `ratified_by: operator countersign`). Both **[OPERATOR-SET]**
> fields (`verification_deadline` = 2026-07-23, `rite_disjoint_attester` = review-rite
> external critic) were **approved as-drafted**. **Gate-A is CLOSED** — the 10x-dev build may
> start once the operator runs `ari sync --rite=10x-dev` + ONE CC restart. The validated
> design is `.ledge/handoffs/HANDOFF-arch-to-10x-dyn-enum-contract-2026-06-30.md`
> (arch-adversary PASS-WITH-CONDITIONS). Amendable at any `/frame`.

```yaml
telos:
  initiative_slug: dyn-enum-contract

  inception_anchor:
    framed_at: "2026-06-30"
    frame_artifact: ".sos/wip/frames/dyn-enum-contract.md"  # + shape .sos/wip/frames/dyn-enum-contract.shape.md (pythia) + rnd spike .ledge/spikes/{SCOUT,INTEGRATE,PROTO,MOONSHOT,TRANSFER}-dyn-enum-contract.md + handoff .ledge/handoffs/HANDOFF-rnd-to-10x-dyn-enum-contract-2026-06-30.md
    why_this_initiative_exists: >
      An enum-option vocabulary change in Asana — a vertical added, renamed, or disabled —
      does NOT reliably reach autom8y-data's `verticals` dimension through any typed contract
      today. The vocabulary already LEAKS across the asana->data seam UNTYPED
      (AccountStatusEntry.vertical: str, pushed by the cache-warmer) and is materialized SIX
      different ways (one authoritative Asana enum_options + two derived + three legacy),
      reconciled by hand + Slack nudges. The `verticals` table is an FK-PARENT dimension
      (campaigns / asset_verticals ~43K / offers.category all reference it), so the team's
      existing snapshot-replace sync idiom — safe for the account-status LEAF — would ORPHAN
      FK children here. Without ONE typed, additive, FK-safe sync contract, vocabulary drift
      is silent, hand-reconciliation is error-prone, and a careless sync orphans 43K+ rows.
      This initiative IS that contract — proven first by the live round-trip that lands a
      new/renamed option additively with FK children intact and hard-refuses an empty/truncated
      read.

  shipped_definition:
    code_or_artifact_landed: []  # MISSING — nothing landed. Populated by: sprint-1 (producer, autom8y-asana PR) + sprint-2 (consumer, autom8y-data PR — SEPARATE repo) + sprint-3 (coherence, asana PR) + sprint-4 (reconciliation dry-run)
    user_visible_surface: >
      [OPERATOR-SET — draft wording, blessed-as-is until you amend]
      A NEW or renamed Asana Vertical enum-option propagates into autom8y-data's `verticals`
      dimension automatically through ONE typed sync contract
      (POST /api/v1/vocabularies/sync — generic plural path, field_key-discriminated,
      NAME-keyed) — ADDITIVELY (insert-new / update-name / NEVER delete), preserving existing
      ids + all FK children — and an EMPTY or TRUNCATED Asana read is hard-REFUSED with an
      alert rather than applied. No more hand-reconciliation across the six legacy sources.

  verified_realized_definition:
    user_visible_evidence:
      # The realization predicate, carried VERBATIM from the frame, sliced into testable legs.
      # This is the telos, NOT "endpoint merged" / "PRs green".
      - "POSITIVE round-trip: a NEW or renamed Asana enum_option (the live Vertical cf) round-trips into autom8y-data.verticals via additive-upsert keyed on vertical_key — existing ids preserved, FK children (campaigns / asset_verticals ~43K / offers.category STRING edge) intact — within one sync cycle, asserted by a LIVE/integration test on a real option-set round-trip."
      - "NEGATIVE hard-refuse: an EMPTY or TRUNCATED Asana read (missing any FK-referenced key) is hard-REFUSED with an alert and NEVER applied (no DELETE, no partial overwrite) — asserted by a discriminating test (full set passes GREEN; empty/truncated trips the guard RED)."
      - "COMPOSE-UP LOCKS hold: the contract ships on the generic /api/v1/vocabularies/sync path WITH a field_key discriminator AND NAME-keying (vertical_key, NEVER enum_option.gid or vertical_id) — so it composes UP to the DEFER-1 fleet registry at cardinality 1->N without a rewrite."
      - "DRIFT HONESTY: divergence (asana-live vs data-side; name-collision; disabled-but-referenced) is WARNed and NEVER codegen'd / auto-minted (ADR-S4-001 holds); a vertical_name unique=True collision on the UPDATE path is refused-per-row, never silently applied."
      - "SPINE UNREGRESSED: strictly-additive to the gfr 105-test certified spine (CERT-1/CERT-3 inviolable); a NEW endpoint (extending /account-status/sync is BREAKING under extra=forbid)."
    verification_method: in-anger-dogfood
    verification_deadline: "2026-07-23"  # [OPERATOR-SET] CONFIRMED 2026-07-01 (as-drafted, ~3wk from countersign); drives Naxos TELOS_OVERDUE.
    rite_disjoint_attester: "review-rite external critic (rite-disjoint from the 10x-dev author per critic-substitution-rule; PT-07 telos gate in dyn-enum-contract.shape.md; mirrors the gfr / gfr-dynvocab R1 binding). [OPERATOR-SET] CONFIRMED 2026-07-01 — review-rite (not eunomia)."

  attestation_status:
    inception: RATIFIED       # operator (Tom Tenuta) countersigned 2026-07-01 (Gate-A CLOSED)
    shipped: MISSING          # nothing landed
    verified_realized: UNATTESTED
    last_eunomia_advisory: null

  receipt_grammar:
    per_item_file_line_anchors:
      # Reuse substrate carried from the frame's SVR receipts + the spike; 10x-dev re-verifies at build (code_verbatim_match false).
      # Producer (autom8y-asana):
      - "src/autom8_asana/jobs/.../gid_push.py:519"               # leaf-calibrated empty guard the vocab path hardens to referential-coverage hard-refuse
      - "src/autom8_asana/jobs/.../gid_push.py:131"               # _push_to_data_service (endpoint-parameterized) — the producer push helper
      - "src/autom8_asana/models/custom_field.py:113"             # enum_options: list[CustomFieldEnumOption] — the live option-set the producer reads
      - "src/autom8_asana/api/routes/resolver_schema.py:366"      # values_source: 'asana_configured' — the re-point door
      - "src/autom8_asana/dataframes/resolver/default.py:258-263" # selected-value-only read TODAY (the gap this contract fills: option-SET, not selected value)
      # Consumer (autom8y-data — SEPARATE repo /Users/tomtenuta/Code/a8/repos/autom8y-data):
      - "autom8y-data: _platform.py:146"                          # vertical_key unique=True — the portable upsert key
      - "autom8y-data: _platform.py:147"                          # vertical_name unique=True — the UPDATE-path collision hazard (RR / FR-007)
      - "autom8y-data: _platform.py:162"                          # offers.category foreign_key='verticals.key' — the STRING FK edge
      - "autom8y-data: _advertising.py:80,:326"                   # campaigns + asset_verticals (~43K) int FK edges
      - "autom8y-data: services/vertical.py:9"                    # "verticals are permanent" no-delete invariant (DELETE-forbidden)
      # Doctrine precedent (git show origin/main: ca28251d):
      - "src/autom8_asana/resolution/gfr/dynvocab_overrides.py"   # NAME-keyed override registry — 2nd entry is DATA not code (the compose-up precedent)
      - "src/autom8_asana/dataframes/models/registry.py"          # detect_model_schema_drift warn-first gate (drift-WARN-not-codegen)
    cross_stream_concurrence: false   # set true ONLY at verified_realized=ATTESTED (POSITIVE + NEGATIVE corroborated by the rite-disjoint attester at PT-07)
    code_verbatim_match: false        # honest: anchors carried from the frame/spike; sprint-0 architect + each repo's HEAD re-verify at build (producer paths approximate the gid_push module location — re-confirm)
```

## Realization predicate (the one line that gates close — VERBATIM)

> "Verified-realized" = a NEW or renamed Asana enum_option round-trips into
> autom8y-data.verticals via additive-upsert with existing ids + FK children
> (campaigns / asset_verticals ~43K / offers.category) intact within one sync cycle,
> AND an empty/truncated Asana read is hard-REFUSED with an alert (never applied) —
> asserted by a LIVE/integration test on a real option-set round-trip. NOT "endpoint
> merged", NOT "PRs green".

This predicate is carried into **every** sprint's exit criteria per
`dyn-enum-contract.shape.md`, and is the sole content of the **PT-07** rite-disjoint
telos gate. Sprint-5 (the review-rite disjoint critic) is the telos proof, not an
afterthought.

## Risk map (carried — what "verified-realized" defends against)

| Risk | Why it threatens the telos | Where addressed |
|---|---|---|
| **EC-1 DB-engine UNRESOLVED** (MySQL vs PostgreSQL) | Determines upsert syntax (`ON CONFLICT` vs `ON DUPLICATE KEY UPDATE`) + lock primitive (`pg_advisory_xact_lock` vs `GET_LOCK`); priors DISAGREE (INTEGRATE MySQL / PROTO PostgreSQL) | **CRITICAL** — sprint-0 architect resolves by inspecting autom8y-data engine/migration config BEFORE sprint-2; PT-01 |
| **RR1 concurrent upsert** | Two syncs racing the upsert could double-insert / deadlock on the FK-parent | single-writer-per-`field_key` advisory lock (engine-specific); sprint-2 / PT-04 |
| **RR2 disabled-option policy** | An Asana-disabled option with live FK children must NOT cascade-delete | present-but-inactive envelope; DELETE-forbidden; drift WARN -> human runbook (operator-judgment) |
| **RR3 first-sync key-mismatch** | data `verticals.key` vs Asana option NAME divergence on initial reconcile -> ORPHAN-RISK | sprint-4 read-only dry-run REFUSES on ORPHAN-RISK (MATCH-don't-re-key); EC-4 |
| **RR4 offers.category STRING-FK coverage** | The string edge silently missed if the coverage query unions only int edges | sprint-2 coverage unions BOTH join types incl. `_platform.py:162`; PT-04 |
| **vertical_name unique=True collision** (`_platform.py:147`) | `UPDATE SET name` collides with an existing distinct row's name | update-name only when non-colliding, else per-row WARN + refuse-the-row |
| **EC-2 live-Asana read** | Whether the live read returns the full populated option-set; cred path operator-shell-only (AWS Secrets Manager `autom8y/asana/asana-pat`) | build-phase-1 live probe; do NOT assume CI parity |
| **Spine regression** | An additive change silently regresses the gfr STRONG-certified identity spine | the gfr certified suite is the mechanical regression gate; option-set rides as a sidecar to enum/multi_enum, never a 7th type |

## Defer registry (OUT OF SCOPE — resist scope-creep)

| Deferred | Disposition |
|---|---|
| Fleet cf-contract REGISTRY (moonshot Option-F generalization) | **DEFER-1** — ESCALATE only on the N>=3 conjunction (2nd `field_key` binds `/vocabularies/sync` AND a 3rd consuming service requests the vocab). ONE-WAY DOOR once 2+ services bind — do NOT build pre-trigger. |
| Legacy `Vertical(Enum)` / `_missing_` phantom-campaign mechanism | **NON-CANONICAL — lessons-only.** Provably unreachable from the seam (0 import edges, INTEGRATE HD-1). Never extended; the producer reads via `CustomFieldsClient`, never `VerticalModel`. |
| Reverse resolution / write-back to Asana / hard-DELETE of options | OUT permanently. A disappeared option is a drift WARN -> runbook, never an auto-mutation. |

## Carried flags (the operator should know)

- **Gate-A** — this file converts the OPEN gate to CLOSED on operator countersign. `/frame` + `/shape` proceeded against this draft; the **build cannot start** until countersign (then `ari sync --rite=10x-dev` + ONE CC restart).
- **Cross-repo** — producer (autom8y-asana) + consumer (autom8y-data) are **SEPARATE PRs**; the consumer endpoint must be **deployed BEFORE** the producer push is enabled (BC-1 / CON-010; build-parallel, enable-ordered).
- **Consumer-repo rite (PT-02 operator fork)** — autom8y-data's `ACTIVE_RITE` is **`dre`** (not 10x-dev). sprint-2 runs in a separate autom8y-data session; the execution rite (10x-dev-synced-into-data vs dre-native with `integrity-architect`) is your choice, NOT pre-picked.
- The two **[OPERATOR-SET]** fields (`verification_deadline` 2026-07-23, `rite_disjoint_attester` review-rite critic) are proposed as-drafted — confirm or amend at countersign.

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-build declaration; `self_ref_cap: MODERATE` per
`self-ref-evidence-grade-rule`. Feasibility is first-party (the rnd spike's two-sided
discriminating canaries, `.sos/wip/spikes/dyn-enum-contract/`); realization attestation
belongs to the rite-disjoint review-rite critic at PT-07 close, not to the author. Code
anchors carried from the frame/spike (`code_verbatim_match: false`) — sprint-0 architect
re-verifies at dispatch.
