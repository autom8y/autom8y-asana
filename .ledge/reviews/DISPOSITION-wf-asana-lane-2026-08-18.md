---
type: review
status: complete-awaiting-critique
artifact_subtype: sprint-disposition
initiative: dic-comprehensive-landing
sprint: S-09 (W-F asana fleet-class cure lane, incl. the F-9 DURABLE cure)
rite: dre (seat-materialized)
date: 2026-08-18
evidence_grade: MODERATE (self-authored ceiling per self-ref-evidence-grade-rule; rite-disjoint critique pending)
---

# DISPOSITION — W-F asana lane (DIC S-09)

> Authored under seat-materialization: general-purpose agent preloaded verbatim with
> integrity-architect.md + pipeline-steward.md (dre unseated in dispatcher; pythia
> Option-5 2026-08-18).

## §0 Grounding receipts

- **Shape block read**: `autom8y/.sos/wip/frames/dic-comprehensive-landing.shape.md:371-398`
  (S-09) — tree-only read; the shape is the spec of record for this sprint.
- **Rider law**: `autom8y/.ledge/decisions/PACKET-D5-sitting-2026-08-13.md` §5 (W-F) and §3.4
  (F-9 mechanism); `autom8y/.ledge/reviews/CERT-sarm-1601-RECERT-43aa30da-2026-08-13.md:38`
  (the ratified durable-cure semantics: tri-state `has_unit` / `exclude_unset` /
  5xx-on-subtask-fault).
- **Repo pins (re-derived at dispatch)**: autom8y-asana origin/main `844bbde5`
  (branch cut point); autom8y monorepo origin/main `676ec9be` (worktree base, matches charge).
- **S-COR walls re-verified own-hands** (not carried):
  - WALL 1: `autom8y@origin/main terraform/services/asana/main.tf` cache-warmer
    `environment_variables` block carries no `AUTOM8Y_DATA_URL`, `secret_arns` no data-API
    key; **live** `aws lambda get-function-configuration` (read-only, 2026-08-18) on all
    THREE warmer functions confirms both absent from the deployed env.
  - WALL 2: `autom8y-asana src/autom8_asana/core/entity_registry.py:482`
    `key_columns=("office_phone",)`; `src/autom8_asana/services/gid_push.py:132-150`
    `len(parts) == 3` gate; `src/autom8_asana/services/gid_lookup.py:from_dataframe`
    mints `pv1:` + one part per key column — a 1-column key is structurally dropped.
  - F-9 producer defect: `src/autom8_asana/services/intake_resolve_service.py` (pre-cure)
    defaulted `has_unit/has_contact_holder = False`, swallowed subtask faults
    (`business_subtask_check_failed` warning), and passed both fields unconditionally to a
    `bool = False` model — the wire never omitted them
    (consumer residual named at `calendly-intake tripwire/probe.py:68-73`).

## §1 FORTIFY — the F-9 structural design (integrity-architect seat)

**Structural invariant (one, load-bearing):** *a sub-entity key appears on the resolve wire
IFF the producer actually observed that sub-entity's state.* Concretely, per the ratified
semantics:

| Producer world-state | Pre-cure wire | Cured wire |
|---|---|---|
| Subtask listing FAULTS | `200` + `has_unit: false` (fabricated) | **503 SUBTASK_OBSERVATION_FAILED** (5xx-on-subtask-fault) |
| Listing EMPTY (index-lag shape: parent indexed before sub-entities) | `200` + `has_unit: false` (fabricated) | **keys OMITTED** (tri-state unset + scoped exclude-unset serializer) |
| Listing NON-EMPTY, holder absent | `has_unit: false` | `has_unit: false` — a REAL observation; **teeth preserved** |
| Listing NON-EMPTY, holder present | `has_unit: true` | `has_unit: true` |

With this invariant, the catastrophic state — *index lag rendered as a positive assertion,
consumed by W5-3 as written(True) != read(False) → MISMATCH → unattended revert at
`mode: live`* — is **unrepresentable by construction**: the only wire shapes lag can produce
are key-absence (→ consumer `read_field` → ABSENT → UNOBSERVED, which cannot revert) or 503
(→ probe spine-leg raises → ERROR: alarm, never revert). The empty-listing rule is the
producer-side adoption of the probe's own doctrine: **a bare zero is not evidence**.

**Consuming-path refusal contract:** already built and unchanged — the probe's F-3 guard
(`probe.py:read_field`, `model_fields_set` predicate at :159-164) refuses to treat an
uncarried field as a contradiction. This cure emits the preserve-fuel that guard was
starving for: fields_set-faithful key presence. No SDK change is required —
`autom8y_core.models.asana_service.BusinessResolveResponse` keeps `bool = False`; an
omitted key parses to the same attribute value while correctly staying out of
`model_fields_set` (proven cross-seam in the landing suite).

**Recovery floor (independent of the live path):** the operator suspension lever
(`calendly-intake tripwire/killswitch.py` `tripwire.suspension`, OW-3's compensating
control) is config-side and survives any failure/rollback of the asana service producer.
This cure does not touch it, does not retire it, and per T5 does not treat any future
tripwire catch as a success — a catch remains a structural-defect report.

**Phase-aware rollback (keyed on deploy-phase, never lever-name):**
- *Phase MERGED-NOT-DEPLOYED*: `git revert` the PR; no wire shift has occurred; no other act.
- *Phase DEPLOYED-SERVING, no first-create window open*: redeploy the previous asana image;
  the wire regains explicit-false fields; hazard dormant while no create traverses.
- *Phase DEPLOYED-SERVING, first-create window open or imminent (WS-B replay class)*:
  **the same rollback INVERTS to hazardous** — restoring the explicit-false producer while
  W5-3 is armed re-opens the F-9 false-fire. Precondition: suspend the tripwire
  (operator word, killswitch suspension) BEFORE the image rollback, per OW-3's law.

**Residual reactive seams (named for the warden/critic, not papered over):**
1. **Partial-lag**: a non-empty listing whose OTHER holder is still lagging asserts a false
   the probe can trip on. One read cannot discriminate it; it is the ratified
   single-confirmation predicate's own limit (probe.py:68-73), narrowed by this cure from
   "any lag" to "partial lag only".
2. **Total-subtask-loss**: a malformed create that lost BOTH subtasks yields an empty
   listing → UNOBSERVED on the sub-entity legs. The probe's other legs (gid identity,
   key readback, corroborated absence) and recon remain the catch for that class.
3. **Availability trade (deliberate)**: a transient Asana subtask hiccup now 503s the
   resolve instead of silently degrading — consistent with the endpoint's ratified
   fail-closed three-outcome contract (ADR-resolve-cure-design-2026-08-08 D-2a/D-2b).

## §2 LANDING — the two-sided proof (pipeline-steward seat)

**State transition exercised**: full producer stack — FastAPI route (S2S auth) → service →
subtask observation → tri-state model → scoped serializer → realized wire JSON → parsed by
the REAL consumer SDK model (`autom8y_core.models.asana_service.BusinessResolveResponse`,
the exact class the probe's `read_field` inspects). Suite:
`tests/unit/api/routes/test_intake_resolve_f9_semantics.py`.

**Completeness asserted on the realized output**: raw wire-JSON key presence/absence and
consumer `model_fields_set` membership — never an intermediate boolean or stub handshake.

**Sole discriminator (S5)**: wire key-presence, surfaced as `model_fields_set` membership.
Cheap signals proven blind in
`test_cheap_signal_getattr_is_blind_fields_set_discriminates`: HTTP status, `found`, and
`getattr(parsed, "has_unit")` are byte-identical between "unobserved" and "asserted
absent" — `getattr` is literally the blind instrument that armed F-3/F-9.

**Two-sided receipts (real pre-change code path, per the shape's exit criterion)**:
- **RED-before** @ `844bbde5` src (suite run with `git stash` of the cure):
  `4 failed, 2 passed` — the three lag/unobserved legs failed (wire carried
  `has_unit: false` on an empty listing) and the fault leg failed (200-with-false after the
  pre-cure `business_subtask_check_failed` warning, captured verbatim in the run log). The
  2 passes were the TEETH legs (malformed-bites + healthy) — proving the RED is not
  manufactured and the cure adds no new teeth it then claims to preserve.
- **GREEN-after**: F-9 suite 6/6; adjacent suites
  (`test_intake_resolve.py`, `test_intake_resolve_models.py`,
  `test_intake_resolve_business_index.py`) 66/66; full `tests/unit/api` +
  `tests/unit/services`: 2331 passed, 1 failed —
  `test_query_service.py::...::test_project_gid_none_raises_service_not_configured`,
  **pre-existing**: fails identically with pre-change src at `844bbde5` (verified via
  stash), not introduced by this lane.

**Exit-criterion mapping (shape :387)**: *"a first-create that is genuinely malformed still
trips"* → `test_genuinely_malformed_first_create_keeps_its_teeth` (asserted false on the
wire, fields_set-visible to the probe); *"merely index-lagged does NOT"* →
`test_index_lagged_first_create_is_unobserved_on_the_wire` +
`test_lag_wire_reads_unobserved_at_the_real_consumer` (UNOBSERVED can never MISMATCH).

**Residual gap, named (counter-case yield)**: Asana payloads are mocked at the client seam
(the repo's established harness); no live Asana call was made from this lane. The largest
faithful surface — real route, real auth dependency graph, real serialization, real
consumer SDK parse — was exercised; the live-first-create observation remains S-04's
`F-9 outcome recorded either way` duty (shape :244), not this lane's.

## §3 Rider table (shape exit criterion :388; defer registry D-8, shape :1249)

| Rider (PACKET §5 W-F) | Disposition | Anchor / trigger |
|---|---|---|
| **F-9 durable observation semantics** (tri-state / exclude_unset / 5xx-on-subtask-fault) | **LANDED (PR-UP, unmerged)** | autom8y-asana branch `fix/f9-durable-observation-semantics`: `intake_resolve_models.py` (tri-state + scoped serializer), `intake_resolve_service.py` (observation semantics + `SubtaskObservationError`), `intake_resolve.py` (503 branch), F-9 suite. |
| **Cache-warmer `AUTOM8Y_DATA_URL`** (S-COR-1) | **LANDED (PR-UP, unmerged)** | autom8y/autom8y **PR #1647** — env + `AUTOM8Y_DATA_API_KEY` secret + IAM pattern on all three warmer modules, mirroring `scheduling_stratum_snapshot`. |
| **Entity-registry 2-column key** (S-COR-2) | **DEFERRED (named, D-8)** | See below. |

**S-COR-2 deferral — rationale (premise-validation, all own-hands):**
1. The naive flip (`business.key_columns -> ("office_phone","vertical")`) is
   **refused by the live resolve surface by construction**:
   `intake_resolve_service.py:113-118` (`_business_criterion`) raises
   `BusinessIndexUnavailableError` on any business key other than `["office_phone"]` —
   every `/v1/resolve/business` call would 503. That guard is itself a ratified cure
   (registry-drift fail-closed); the flip is not an edit, it is a redesign of the live
   first-create resolve path.
2. The business DataFrame **has no `vertical` column to key on**
   (`dataframes/schemas/business.py` BUSINESS_COLUMNS + base — absent), and the registry
   audit's sampled Businesses rows carry no Vertical CF value
   (`autom8y/.ledge/reviews/AUDIT-asana-office-registry-keys-2026-08-12.md` §2.3) — a
   2-column mint would produce zero rows even if wired (vacuous cure).
3. A push-only second index (2-column, mint-side) or a consumer-side phone-only fallback
   (recon leg) are both viable designs with different blast radii; choosing between them is
   a design ruling, not a rider-sized edit.

**Named triggers (D-8 watch):**
- **T1**: post-#1647-deploy measurement — with WALL 1 cured, the gid map populates from the
  2-column projects (unit/sales/onboarding/...); read whether the WS-D ASANA leg still
  misses REAL bookings whose business lives only in the Businesses project. If yes, S-COR-2
  is biting in production and reactivates.
- **T2**: a curl-only census of Vertical CF population across the Businesses project
  (2,402 phones) — resolves the vacuity premise before any design is chosen.
- **Owner**: per D-8, S-09 owner surfaces this row; the reactivation design ruling is
  operator/architect, not this lane.

## §4 S-COR-1 fleet-class scope (shape exit criterion :389)

Single-writer topology: the ONLY feeder of `gid_map:lookup` is the autom8y-asana
cache-warmer fleet (`gid_push.py` → `POST /api/v1/gid-mappings/sync` → autom8y-data
`GidMappingStore`, Redis TTL 25h). With the writer blind, **every consumer of
`gid_map:lookup` inherits the blindness**:

1. **autom8y (monorepo) `services/calendly-intake` recon** — the WS-D deadman's ASANA leg
   (`recon/handler.py:250` `get_gid_map_async`; `recon/observers.py:40-45`). The named
   production victim: every booking's `asana_present` reads absent;
   `bookings_aged_out_unresolved` counts an unevaluable band, not correlation failures.
2. **autom8y-data internal serve/lookup surfaces** over the same empty hash:
   `api/services/gid_map_service.py`, `api/services/gid_mapping_store.py`,
   `api/clients/gid_lookup.py`, `analytics/routes/data_service.py`,
   `analytics/core/infra/ttl_policy.py`.
3. **Any SDK composer** of `autom8y_core.clients.data_service.get_gid_map[_async]`
   (`data_service.py:233-308`) or `autom8y_client_sdk` data read (`data/read.py`
   `get_gid_mapping`) — fleet-wide latent inheritance; the census (grep at origin/main,
   both repos) found calendly-intake recon as the only ACTIVE in-production consumer today.
4. **Post-cure residual within scope**: even with #1647 deployed, tasks living ONLY in the
   Businesses project remain outside the map (S-COR-2, deferred above) — the scope
   statement is honest on both sides of the cure.

## §5 UV-P register

- `[UV-P: terraform plan for #1647 renders 3 in-place updates / 0 destroys | METHOD:
  Service Terraform CI plan on the PR | REASON: no terraform init against the live backend
  from this lane; no infra mutation permitted]`
- `[UV-P: Businesses-project Vertical CF population is empty at full census | METHOD: T2
  curl-only enumeration | REASON: audit §2.3 samples only the 21 offenders; no Asana
  credential exercised from this lane]`
- `[UV-P: FastAPI serialize path invokes the scoped model serializer under ALL response
  encodings | METHOD: proven for the served TestClient path (wire-asserted); other
  encoders unexercised | REASON: only the route path serves production traffic]`

## §6 Deltas surfaced LOUDLY (shape wins; deviations named)

1. **`exclude_unset` implemented as a field-scoped model serializer, not the route flag.**
   `response_model_exclude_unset=True` would also strip `meta.timestamp` (a
   `default_factory` field on the fleet `ResponseMeta`,
   autom8y_api_schemas/meta.py:117-121) from the envelope — collateral the ruling did not
   intend. The ruled SEMANTICS (unset never on the wire) are implemented exactly, scoped to
   the two governed fields; proven at the wire.
2. **Disposition filename** uses the real date (`2026-08-18`) for the shape's `2026-08-XX`.
3. **Critique attachment** (exit criterion :390) is carried by the dispatcher per the
   charge: structure-evaluator@arch fires after this seat's exit (critic-substitution —
   the author rite is dre, so change-warden cannot critique here). Slot below.
4. **Seat-materialization disclosure in commits**: the platform's user-only-attribution
   convention (enforced by hook) bars AI markers in commit messages; the disclosure rides
   every authored ARTIFACT (this disposition, PR bodies, the test module docstring)
   instead.
5. **Exit artifact residence**: the shape names `.ledge/reviews/DISPOSITION-...` without a
   repo; per the charge's paper law ("autom8y-asana working tree is authoritative for
   .ledge") it lives here and rides the asana PR.

## §7 Self-assessment and the critique slot

Evidence grade **MODERATE (ceiling)** — both author seats are this agent; every mechanism
claim above is own-hands re-derived and re-runnable, but no claim here is
externally corroborated yet. This lane does NOT self-certify:

- [ ] **structure-evaluator@arch critique** — to be attached by the dispatching main
  thread post-exit (degeneracy guard, shape :377). Attack surface offered: §1's
  empty-listing→UNOBSERVED rule (does it under-power the sub-entity teeth beyond the
  ratified intent?), §3's deferral reasoning, §6.1's serializer-vs-route-flag delta.
