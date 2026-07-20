---
type: decision
artifact_id: DECISION-asana-mcp-v1-rulings-B1-B5-W5
initiative: asana-mcp-v1
title: "asana-mcp-v1 rulings dossier — B1-B5 + W-5, authored PROPOSED for GATE-BW"
status: accepted
ratification: >
  GATE-BW PASS 2026-07-17 — all six rulings RATIFIED as recommended by explicit operator
  instruction (structured interview; recorded on the operator's behalf, §10). Exposure
  preconditions ride the PASS: C1 idempotency reconciliation + UV-P#4 C2 probe (operator-elected
  fork (i)). GATE-FELT and GATE-PROBE remain open and operator-reserved.
created_at: 2026-07-17
author: moonshot-architect (rnd; sprint-5 rulings-and-topology-dossier LEAD, Wave A)
session: session-20260717-181924-9924bb32
evidence_grade_ceiling: MODERATE   # self-ref: rnd authored, rnd builds. R11 UNCLEARED (needs twice-proven OR rite-disjoint-critic-STRONG). See §9.
critique_status: ATTACHED (two iterations) — iter-1 arch-adversary PASS-WITH-CONDITIONS (rite-disjoint via co-seat inv-20260717-1278d7961503; arch critiques, rnd authored). Report .ledge/reviews/ADVERSARY-REPORT-asana-mcp-v1-rulings-2026-07-17.md; critiqued target_sha256 6824581b906565e24f1acd89f71d84c7da45dfd5ed7ad557f2839902f15bff25 (PRE-amendment dossier). Six conditions discharged at AMENDMENT-1; see §9.5. iter-2 DELTA verdict PASS-WITH-CONDITIONS == gate CLEARS with two non-blocking flags (ND-1/ND-2, applied at AMENDMENT-2) + a 12-item residual list for the operator's GATE-BW reading. DELTA report .ledge/reviews/ADVERSARY-REPORT-asana-mcp-v1-rulings-DELTA-2026-07-17.md; critiqued post-AMENDMENT-1 sha256 ff1a25b7cade3ec80a407fc6dffc68c80aac00f1f16814f03b274a24be289014.
amendment_log:
  - id: AMENDMENT-1
    session: session-20260717-181924-9924bb32
    date: 2026-07-17
    executor: prototype-engineer (rnd; sprint-5 re-entry, amendment EXECUTOR — investigates + surgically amends; never self-ratifies; §10 checkboxes untouched)
    trigger: arch-adversary PASS-WITH-CONDITIONS verdict (6 conditions; condition 1 BLOCKING)
    scope: discharge C1-C6 + A5 qualifier drift + uncarried counter-receipts; frontmatter + B1/B3ii/B4/B5/W-5/§8/Appendix-A/§9.5 touched; ALSO §10 recommendation-summary CELLS for B3 and W-5 updated (non-checkbox text only; all 12 checkboxes untouched — declared here at AMENDMENT-2 per DELTA ND-1); recommendations altered only where condition evidence demanded (B3ii re-scored at C4 — old text preserved)
  - id: AMENDMENT-2
    session: session-20260717-181924-9924bb32
    date: 2026-07-17
    executor: main-thread orchestrator (applying the two pathways the DELTA critic prescribed verbatim; no judgment edits)
    trigger: arch-adversary DELTA PASS-WITH-CONDITIONS (ND-1 manifest under-declaration; ND-2 un-compounded residual interaction)
    scope: AMENDMENT-1 manifest corrected (ND-1); W-5 compounded-residual paragraph + 1800s TTL bound added (ND-2, TTL receipt re-verified by orchestrator at token_service.py:739); §10 checkboxes untouched
gates: "GATE-BW — ratification of these six rulings unlocks write-surface EXPOSURE ONLY (charter §5:96-98). See §8."
grounding:                              # precedence: charter GOVERNS > slate > spikes > .know(stale-flagged)  (frame §4.1)
  charter: .ledge/decisions/DECISION-fleet-mcp-program-alignment-2026-07-17.md          # operator-RATIFIED
  shape: autom8y-asana/.sos/wip/frames/asana-mcp-v1.shape.md                            # sprint-5 block, §3 GATE-BW, §9 R1, §11 GAP-2
  slate: .ledge/spikes/SPIKE-mcp-substrate-concepts-2026-07-17.md                       # B1-B5, E-kills, A/C items (MODERATE ceiling)
  frame: autom8y-asana/.sos/wip/frames/asana-mcp-v1.md                                  # §3 workstreams, §7 SVR ledger
  telos: autom8y-asana/.know/telos/asana-mcp-v1.md                                      # RATIFIED; GATE-BW/FELT/PROBE remain open
source_hash: f3d8eec1   # frame premise anchor; every load-bearing live-code anchor in this dossier re-probed by direct read this session (Appendix A)
---

# DECISION DOSSIER — asana-mcp-v1 rulings B1–B5 + W-5 (PROPOSED)

Six decision POINTS, authored PROPOSED with one pre-filled recommendation each, per the
charter §5.2 grant. **Nothing in this document is decided.** Ratification is reserved to the
operator, always (charter §5:96-98); this session does not self-ratify and marks nothing
closed. Per option-enumeration-discipline, every ruling enumerates structurally distinct
options — including a null/no-new-mechanism option — BEFORE its recommendation.

**Throughline (held):** v1 is REAL only when the operator, in their OWN workflow and from
schemas alone, witnesses an agent (a) answer a real business question via
list→describe→rows→aggregate AND (b) run the add_tag→push(PUT-save)→mark_complete composite
all-or-nothing against a real task. "PRs merged" is NOT the gate; the operator is the sole
closer. This dossier feeds that witness (its W-5 ratification gates limb-(b) EXPOSURE); it
does not close it.

**Standing fences (bind every ruling below):** the MCP process NEVER imports the domain SDK
and makes ZERO direct Asana calls (frame constraint 5); NO fleet code is promoted before the
§4 probe rules COMMIT (constraint 8); the write surface may be BUILT but never
exposed-as-ratified before W-5 passes GATE-BW; no non-idempotent verb ships without the
fail-loud idempotency contract (W-3/B5).

Evidence anchors: `[RV]` = re-verified by direct read this session (verbatim receipts in
Appendix A). `[INH]` = inherited from the frame §7 SVR ledger, the adjudicated slate, or a
named artifact, at the MODERATE ceiling. `[UV-P]` = unverified premise, frozen syntax.

---

## Ruling B1 — Topology: where does the deployed MCP sidecar process live?

**QUESTION.** Which physical placement primitive hosts the asana MCP server for v1's
deployed surface?

**Restated kill (not re-enumerated for choice):** the fleet MCP gateway is REJECTED-hard as
the #1 default (slate E3 / B1a; charter §7 forbids re-litigating without new evidence). Live
mechanism confirmed at a corrected anchor: the api-gateway OperationRegistry raises
`OperationAltitudeError` at module import on a bad merged-spec entry, propagating to the ECS
entrypoint as a visible restart loop [RV operation_registry.py:13-25, :392 — drift-corrected
from the slate's `gateway/app.py:314` cite]. One fleet service in the tool request path means
one substrate bug downs every MCP surface; per-satellite sidecars keep blast radius
per-satellite. The gateway-vs-sidecar fork is re-scored at #2 scoping, not before.

### Options

**B1-O1 — `parent_service` + `command_override` sub-service (manifest primitive).**
The manifest's sub-service primitive: "A sub-service shares the parent's ECR image and
deploys atomically with it. Per ADR-manifest-sub-service-topology (DS-3)"; CommandOverride
is REQUIRED when ParentService is set [RV a8 pkg/manifest/types.go:635-642]. Precedent:
data-readonly sub-service, manifest.yaml:501-540 [INH slate A2].
- FOR: zero new repo/CI rail/env onboarding (inherits the env-loader substrate [INH slate A2,
  env-architecture.md:149-150]); fastest path to the felt-gate; schema-skew structurally
  minimized — tool schemas are hand-authored from the SAME-COMMIT Pydantic models
  (strongest possible R6 schema-drift guard); one deploy rail, no 6th hand-copied dispatch
  YAML (D5 pressure not worsened).
- AGAINST (weighed HONESTLY, per directive): **atomic co-deploy coupling — no independent
  rollback; a bad asana image downs the MCP with it** [RV types.go:636]; deploy cadence
  coupled to the parent; the shared image CONTAINS domain code, so the constraint-5 import
  fence is enforced ONLY by the import-safety test (C9a, sprint-4), not by image separation.
  **Reverse-coupling, named at AMENDMENT-1 (C6/CH-05):** the coupling cuts BOTH directions —
  because a sub-service "shares the parent's ECR image and deploys atomically with it"
  [RV types.go:635-642], every MCP-only iteration (a tool-schema tweak, a span-attr change,
  a budget-cap retune) redeploys PRODUCTION asana atomically, exposing the parent to the
  sub-service's deploy cadence. v1's reference posture is precisely the highest-MCP-iteration
  regime (curated tool surface still being shaped pre-felt-gate; the reference-posture POC
  expects MULTIPLE sidecar-only iterations before the felt-gate, and each one is a full asana
  production deploy under O1), so this un-named half peaks exactly during v1. The mitigating observation below defrays only the availability half (MCP→asana);
  it is silent on this deploy-cadence half (MCP-change→asana-redeploy). No zero-downtime/
  paired-rollback deploy receipt is carried that would bound the reverse cost [UV-P: a8
  service-stateless rolling-deploy + paired-rollback behavior at pinned ref | METHOD: read
  terraform/modules/stacks/service-stateless deploy config, or SRE confirm, at deployment-PR
  time | REASON: deploy-controller behavior not probed this session; bounds the reverse-
  coupling cost if zero-downtime rolling is confirmed].
- Honest mitigating observation (critiquable): the MCP's entire function is proxying asana's
  REST surface — if the asana service is down, the MCP is useless regardless of placement.
  Availability is ALREADY functionally coupled; O1 adds deploy-path coupling on top of an
  existing functional coupling, which is a smaller marginal cost than it would be for an
  independent-value service. Independent rollback matters most at production cadence — which
  is post-probe, outside v1's reference posture.

**B1-O2 — Sibling repo / separate service with own image.**
The only true cadence-decoupler: independent build, deploy, rollback.
- FOR: independent rollback; import fence enforced STRUCTURALLY (domain code absent from the
  image); the shape #2 would likely inherit if the probe rules COMMIT.
- AGAINST: explicit env-loader onboarding; a NEW CI/dispatch rail (the 6th hand-copied
  satellite-dispatch YAML — the exact D5 duplication signal); REST-contract skew across
  independent deploys (requires D10's behavioral contract test, which is LEDGERED, not
  built); slowest to the felt-gate; heaviest ceremony for a throwaway/reference surface.

**B1-O3 — In-task sidecar container (second container, same ECS task).**
Middle placement: separate image/process, shared task/network (localhost hop).
- FOR: import fence structural (own image); network locality.
- AGAINST: **no live manifest primitive exists for multi-container tasks** — the manifest's
  only sub-service primitive is ParentService/CommandOverride [RV types.go:635-648 shows no
  second-container field]; this option requires NEW manifest + terraform machinery for a
  reference-posture v1 (new-mechanism cost with zero precedent); task-definition revisions
  still co-deploy both containers, so decoupling is partial (build decoupled, deploy not).

**B1-O4 — NULL: no deployed placement in v1; sidecar runs as a local/dev process.**
The felt-gate limbs could in principle be witnessed against a locally-launched MCP (stdio)
hitting the deployed REST surface; "the operator's own workflow" does not strictly require a
deployed sidecar for internal Phase 1.
- FOR: zero deployment mechanism at all (purest null); fastest conceivable witness.
- AGAINST: SA client_secret distribution to dev boxes (credential-scope hazard; rotation scar
  class C9c); per-client config toil is exactly the D8 gap; no shared availability; the
  witnessed surface would NOT be the surface #2 inherits, weakening the probe's evidence
  value. Sub-ruling note: sprint-2's POC already runs in this mode under the grant — the null
  is the POC's de facto state; this ruling governs the DEPLOYED/ratified surface.

**Sub-ruling (rides B1): sidecar mandate is CONDITIONAL, not blanket** [INH slate B1b] —
mandatory where import-time-singleton or scarce-credential hazards exist (asana: LBC-001,
shared PAT). autom8y-data's constraints are evaluated fresh at #2 scoping if the probe rules
COMMIT. Nothing here pre-commits #2's topology.

### Trade-off summary

| Option | Rollback independence | Time-to-felt-gate | New mechanism | Import fence | Schema-drift exposure |
|---|---|---|---|---|---|
| O1 parent_service | NONE (atomic co-deploy) | fastest | none | by test (C9a) | minimal (same-commit) |
| O2 sibling repo | full | slowest | new rail + env onboarding | structural | needs D10 |
| O3 in-task container | partial (build only) | slow | NEW manifest/terraform primitive | structural | needs D10 |
| O4 null (local only) | n/a | fast but low-fidelity | none | by test | minimal |

**RECOMMENDATION (pre-filled): B1-O1** — `parent_service: asana` + `command_override`, with
the atomic-co-deploy coupling ACCEPTED AND NAMED as the recorded cost, correct for v1's
reference posture. Conditions riding the recommendation: (i) import-safety test (C9a) is the
fence — it must be green before exposure; (ii) D10 behavioral contract test stays ledgered;
(iii) placement is RE-SCORED at #2 scoping alongside the gateway costing — O1 is a v1 ruling,
not a fleet pattern (that would need the R11 bar).

**WHAT RATIFICATION AUTHORIZES.** Authoring the manifest sub-service entry
(parent_service/command_override) in the deployment PR — which the operator still merges.
Does NOT authorize fleet promotion, #2 topology, or any gateway work.

---

## Ruling B2 — TokenManager side: which SDK implementation mints the sidecar's S2S JWT?

**QUESTION.** Two live TokenManager implementations exist [RV glob:
`autom8y-core/src/autom8y_core/token_manager.py` AND
`autom8y-auth/src/autom8y_auth/token_manager.py` both present at HEAD; TENSION-001 registry
row at design-constraints.md:26-37, resolution cost "Coordinated SDK version bump across all
consumers; high" — registry stale-flagged, underlying files re-verified live]. Which side
does the MCP sidecar consume — and does resolving the fork gate v1?

### Options

**B2-O1 — autom8y-core side.** The fleet-published SDK the asana satellite ALREADY consumes
(service_token.py:40 imports TokenManager from autom8y_core [INH slate A1]); and the typed
query client the read surface must use lives in the SAME package [RV
autom8y-core/clients/asana_query.py:1 — "AsanaQueryClient - Typed client for autom8y-asana
query engine"]. Thread-safety receipts: token_manager.py:97,130-142,258-268 [INH slate A1].
Joining, not adding: one SDK covers both mint and query.

**B2-O2 — autom8y-auth side.** Exists live [RV glob]. AGAINST: the sidecar would then carry
TWO fleet SDKs for one concern (mint from autom8y-auth, query client from autom8y-core),
widening the dependency surface of a process whose import hygiene is a standing fence; no
capability the core side lacks for this use.

**B2-O3 — Resolve TENSION-001 first, consume the unified manager.** AGAINST: coordinated SDK
bump across all consumers, cost recorded "high" [RV design-constraints.md:37]; zero v1 value;
serializes the felt-gate behind a fleet refactor. The charter/slate posture is explicit:
pick, don't resolve; **the fork resolution must NOT gate v1 or MCP #2**.

**B2-O4 — NULL: no TokenManager at all — inbound-token pass-through.** The sidecar forwards
the calling agent's own bearer token to the REST surface; no SA mint.
- FOR: no mint machinery; per-caller attribution for free.
- AGAINST: every internal agent then needs its own fleet-JWT provisioning (pushes the mint
  problem to N consumers — D8-shaped toil); today's internal agents hold no per-user fleet
  JWTs; this is the E4 agent-delegation-adjacent path, deferred-immature [INH slate E4], and
  the B3(iii) migration trigger — not v1 — governs when it returns.

**Decoupling alternative (rides B2-O1, not a placement option):** publish a TokenManager
conformance/contract test both implementations must pass [INH slate B2, doctrine critic]. It
decouples the expensive fork resolution from all MCP work. Ledger item.

**RECOMMENDATION (pre-filled): B2-O1** — autom8y-core side, picked on the record.
TENSION-001 resolution explicitly does NOT gate v1 or #2; the fork stays ledgered with the
conformance-contract-test noted as the resolution decoupler.

**WHAT RATIFICATION AUTHORIZES.** Records the pick as the standing side for MCP #1 (and the
default question to re-ask, not re-derive, at #2). Authorizes the TENSION-001 ledger
annotation. Lands no code.

---

## Ruling B3 — Mint-time trio: SA governance path, token audience, principal class

**QUESTION.** Three decisions bite when the deployed surface's ServiceAccount is minted:
(i) which governance path the SA lands via; (ii) what token audience is minted;
(iii) which principal class v1 credentials ride. (Timing honesty: the POC rides the EXISTING
live S2S bridge — no new mint [INH shape §5 rejected-edge: "no NEW SA mint needed for v1
reference-posture"]. This trio binds the deployment PR, post-ratification.)

### (i) Governance path — 3 options

**B3i-O1 — YAML_REGISTRY (governed).** The reconciler-iterated class-(a) path
[RV credential-topology-matrix.yaml:246 `governance_source: YAML_REGISTRY`,
`live_mint_status: governed-present`].

**B3i-O2 — DB_FALLBACK (match the neighbors).** `asana-service` itself sits in the
ungoverned class-(a′) bucket [RV matrix:274-283 — `governance_source: DB_FALLBACK`], whose
header documents: "The reconciler NEVER iterates these; NULL-yaml_id DB rows are silently
permitted (sa_reconciler.py:254-267)... These are the SPRINT-3 gate-RED candidates"
[RV matrix:251-261 — the live trace of the OPEN SI-4 gate, named here as required].
AGAINST: knowingly minting a NEW credential into the bucket already flagged gate-RED
manufactures the exact debt the matrix exists to retire.

**B3i-O3 — NULL: no new SA — reuse the existing `asana-service` credentials.** Cheapest.
AGAINST: one client_secret shared across two processes doubles the rotation blast surface
(C9c: rotation is deploy-coupled; a stale secret is a hard 401 outage); MCP calls become
indistinguishable from asana-service internal calls at the auth layer; and the reused
credential is itself DB_FALLBACK-ungoverned — the null inherits O2's defect.

### (ii) Token audience — 3 options

**B3ii-O1 — Deliberately-minted MCP audience,** generalizing the live second-audience
precedent: autom8y-data's middleware admits the SET `{FLEET_AUDIENCE, DATA_PLANE_AUDIENCE}`
[RV autom8y-data api/main.py:66 (import), :1657-1664 (`audience=[FLEET_AUDIENCE,
DATA_PLANE_AUDIENCE]`); read_only.py:121-125 same]. A dedicated audience means an
MCP-minted token cannot be replayed against other fleet surfaces and vice versa, and
preserves V-2's external-horizon audience discipline.

**UV-P #1 DISCHARGED-BY-RECEIPT at AMENDMENT-1 (C4/CH-03) — both legs probed this session, and the discharge RE-SCORES this option:**
- *Leg 1 (wheel symbol):* the installed `autom8y_auth` wheel in the asana venv is version
  **4.1.0** and `DATA_PLANE_AUDIENCE` is **ABSENT** from it; `FLEET_AUDIENCE` is present
  (`https://api.autom8y.io`) [RV bash-probe `.venv/bin/python -c "import autom8y_auth..."` →
  `has DATA_PLANE_AUDIENCE: False`; `FLEET_AUDIENCE value: https://api.autom8y.io`]. The data
  satellite's venv carries `autom8y_auth` **4.2.0**, where the symbol IS present
  (`DATA_PLANE_AUDIENCE = https://data.api.autom8y.io`) [RV bash-probe autom8y-data/.venv].
  The symbol is therefore a **version-floor artifact** — present in the published wheel at
  >=4.2.0, absent at the 4.1.0 asana currently resolves. The wheel/source skew the original
  UV-P suspected is real AND sharper: under B1-O1 (co-deploy in the asana image), the sidecar
  inherits asana's 4.1.0 pin and would have NO second-audience constant available without an
  SDK floor bump to >=4.2.0.
- *Leg 2 (mint-side parameterization):* the SA mint path the sidecar rides —
  `POST /tokens/exchange-business` → `token_service.create_service_token` — does **NOT**
  parameterize audience. Its signature carries no `audience` argument [RV autom8y auth
  `services/token_service.py:477-485`] and BOTH issuance branches HARDCODE the fleet audience
  `create_access_token(..., audience="https://api.autom8y.io")` [RV token_service.py:705, :767].
  An `audience` parameter DOES exist on OTHER token functions (`create_user_access_token`
  :193/:212; the :409 path :419) but is NOT threaded on the SA path, and there is no per-SA
  audience field in the SA registry / models / `service-accounts.yaml` [RV grep: zero matches].
  Consequence: minting a **new, chosen** audience for the SA is not an implementation-time
  detail — it is an **auth-service code change** (add an `audience` parameter to
  `create_service_token`, thread it from SA config or request, update both call sites, define
  a new audience constant in the SDK) plus the >=4.2.0 floor bump from leg 1. The adversary's
  own consumer-side live import (data main.py:66) stands as the rite-disjoint ADMISSION-side
  receipt; admission ≠ minting — exactly CH-03's point.

**~~B3ii-O1 (deliberate MCP audience; carry the UV-P to implementation)~~ RECOMMENDATION REVISED at AMENDMENT-1 → "O1 with a NAMED auth-service prerequisite."** The deliberate-audience
partition is not free at v1: it serializes the deployment PR behind an auth-service change
plus an SDK floor bump — landing auth-service work in service of a reference-posture surface,
which inverts reference-then-promote (V-4). O1 is recorded as the end-state audience
discipline with its prerequisite NAMED, not as a v1-blocking build.

**B3ii-O1b — NEWLY ENUMERATED at AMENDMENT-1 (C4/CH-06): reuse the EXISTING DATA_PLANE_AUDIENCE**
(join the live second audience rather than mint a third — the structurally-distinct middle
option the adversary flagged as absent). KILLED on two independent grounds: (i) semantic
mismatch — `DATA_PLANE_AUDIENCE = https://data.api.autom8y.io` is the DATA plane's audience;
stamping asana-MCP tokens with it makes them replayable against the data plane, WIDENING
cross-plane replay — the opposite of the partition goal; (ii) version-blocked at HEAD — the
symbol is absent from asana's resolved wheel (4.1.0; leg 1), so reuse would ALSO require the
>=4.2.0 floor bump. No cost advantage over O1, with an added semantic penalty.

**B3ii-O2 — Bare FLEET_AUDIENCE.** Cheapest; loses the audience partition; widens replay
surface across fleet services. **RE-WEIGHTED at AMENDMENT-1:** this is exactly what the SA
path mints TODAY with ZERO auth-service change (`audience="https://api.autom8y.io"` hardcoded,
token_service.py:705/:767) and what asana's 4.1.0 wheel already exposes (`FLEET_AUDIENCE`,
leg 1). For an INTERNAL Phase-1 reference surface that makes ZERO direct external calls and
never crosses the external trust boundary (V-2), the widened replay is bounded to internal
fleet surfaces for the reference window — a smaller marginal cost than serializing the
felt-gate behind auth-service work. This becomes the v1 recommendation (see below).

**B3ii-O3 — NULL: whatever the mint path defaults to.** Enumerated to be rejected by name:
a silent default is the exact per-satellite drift V-4's rulings-first tempo exists to
prevent. (AMENDMENT-1 honesty note: the SA path's default is NOT silent — it is the EXPLICIT
hardcoded `https://api.autom8y.io` at token_service.py:705/:767; O2 is therefore the
*conscious* form of what O3 would inherit, which is why v1 lands on O2, not O3.)

### (iii) Principal class — 3 options

**B3iii-O1 — ServiceAccount M2M class**, recorded CONSCIOUS + REVISITABLE with the named
migration trigger (unchanged from charter B3): per-user attribution need, or any write-verb
escalation beyond the ratified set. This choice is what W-5 must rule consciously (below).

**B3iii-O2 — OpenFGA `agent` delegation class** (RFC 8693 `POST /tokens/agent`). The model
side is real [RV model.fga:19-44 — agent type with delegator/permitted_action/business
ceilings], but the path is deferred-immature per E4 [INH slate E4: delegation tuple-writing
unwired on the live path; delegation_service zero test coverage; Gap-005 concurrency cap
unenforced; 30-min TTL no-refresh]. Not re-litigated; the B3 trigger governs when.

**B3iii-O3 — NULL: no machine principal — ride human PAT/user tokens.** AGAINST: reproduces
the shared-PAT scarcity B4 exists to manage and re-instates machine-on-human-credential, the
anti-pattern the SA class exists to end.

**RECOMMENDATION (pre-filled): B3 = O1(i) × [REVISED at AMENDMENT-1] × O1(iii)** —
YAML_REGISTRY (SI-4 open gate named; this SA must NOT join the gate-RED bucket);
**~~deliberately-minted MCP audience (generalize the DATA_PLANE_AUDIENCE precedent; carry the
UV-P to implementation)~~ → for v1: bare FLEET_AUDIENCE (B3ii-O2), which the SA path mints
today with ZERO auth-service change, with the deliberately-minted dedicated audience
(B3ii-O1) RE-SCOPED as a NAMED deployment/promotion prerequisite** (auth-service audience
parameterization on `create_service_token` + `autom8y_auth` floor bump >=4.2.0 + a new
audience constant) — the C4 evidence (mint-side hardcodes FLEET_AUDIENCE; asana pins 4.1.0
lacking any second-audience symbol) demands this re-score; ServiceAccount M2M class conscious
+ revisitable with the trigger named.

**WHAT RATIFICATION AUTHORIZES.** Authoring the SA mint spec (YAML registry row + audience
choice) into the deployment PR. Mints nothing by itself; the trio binds whoever executes the
mint, whenever the deployed surface lands. **AMENDMENT-1:** the audience choice ratified for
v1 is bare FLEET_AUDIENCE (zero auth-service change, mints today); ratification ALSO records
the dedicated-audience partition as the named deployment/promotion prerequisite above — it
does NOT authorize the auth-service change itself, which stays operator-reserved like any
fleet code (constraint 8; V-4 reference-then-promote).

---

## Ruling B4 — Shared-PAT budget partition

**QUESTION.** What protects the shared Asana PAT when MCP becomes its third always-on
consumer class (warmers / API / MCP)?

**Scar record (the strongest evidence base in this dossier):** the 429 storm is ATTRIBUTED —
"single shared bot PAT... cross-consumer arbitration CONFIRMED ABSENT; 6h 429-lines
service=79,881 / warmer-bulk=25,669 / warmer=3,095" [RV CHARGE-substrate-leg2:38 P-1];
the named backfire: "the config.py:184-191 documented backfire: ~896 429s/12min, more
concurrency = worse" [RV CHARGE:44 P-4]; and the cure enumeration ALREADY recommends
"(a) static PAT-budget partition (env ASANA_RATELIMIT_MAX_REQUESTS per consumer summing
<1500; config-only...)" [RV CHARGE:44 P-4(a)]. Partition-first is not invented here — it is
the standing cure recommendation of the attributed incident.

### Options

**B4-O1 — Partition-first:** static env-var budget partition across the three consumer
classes AND an MCP-side rate cap. Config-only; no new service; directly instantiates the
CHARGE cure (a).

**B4-O2 — Dynamic cross-consumer arbitrator (fleet service/ADR).** The CHARGE names the
arbitrator ADR the "durable end-state" [RV CHARGE:44 P-4(c) — "does NOT exist; ADR-ASANA-003
is per-client only"], but E2 descoped it: no second scarce-credential consumer exists; it
survives only as the taxonomy checklist — *external-scarce* (asana: partition/arbitration)
vs *internal-capacity* (data's `get_limit_for_role` config tier) — asked per future MCP
[INH slate B4/E2]. Honest note: O2 remains the end-state candidate AT the E2 trigger.

**B4-O3 — MCP-side cap only, no partition of existing consumers.** Structurally distinct:
leaves warmers/API mutually unpartitioned, so the attributed storm shape (warmer/service
contention) survives intact; caps only the new entrant while the incumbent classes keep
starving each other.

**B4-O4 — NULL: no budget mechanism — rely on AIMD backoff.** Rejected by scar: AIMD
concurrency-first is the NAMED backfire [RV CHARGE:44]; adding an unarbitrated third
consumer, driven by an agent that retries, to a PAT with a CONFIRMED-ABSENT arbiter is the
incident replay with an amplifier.

**B4-O5 — Separate PAT for the MCP consumer class.** Structurally distinct (vendor-level
isolation; possibly a real capacity increase if Asana limits are per-token).
[UV-P: Asana rate-limit semantics per-token vs per-account for bot PATs | METHOD: Asana API
docs probe at implementation time if this option is ever revisited | REASON: not derivable
from repo]. AGAINST: doubles the external-credential rotation/scarcity scar class, forks the
fleet's single-PAT posture, and rests on the unverified premise above. Rejected for v1;
revisit only with the O2 end-state conversation at #2.

**RECOMMENDATION (pre-filled): B4-O1** — partition-first (+cap); arbitration ADR stays
descoped to the E2 trigger (a second external-scarce satellite).

**WHAT RATIFICATION AUTHORIZES.** The partition env-vars themselves are already granted
build (sprint-4; POC criteria). Ratification fixes the DOCTRINE: partition-precedes-exposure
for the asana PAT — the write-exposed surface never rides an unpartitioned PAT — and makes
the external-scarce/internal-capacity taxonomy a mandatory pre-build checklist question for
every future fleet MCP.

**The INVARIANT ratification binds (added at AMENDMENT-1, C3/CH-02 — a partition ruling must
carry its invariant, not just the word "partition-first"):** per-consumer budgets MUST sum
below the shared-PAT ceiling — the CHARGE cure (a) invariant "per consumer summing <1500"
[RV CHARGE:44 P-4(a)]. Two config-time invariants (fail-loud at instrument()/create_server
time, never at import) are the ratified substance: **`ΣSHARE ≤ 1.0`** and
**`RATE_RPS × 60 ≤ SHARE_MCP × 1500`** [RV s4-seam-contract §2.2]. A nominal partition that
satisfied the word while violating the sum (e.g. MCP=1400 of 1500) would reproduce the storm;
the invariants forbid it. **The concrete values land in the sprint-4 PR** (conservative,
env-overridable-without-redeploy starting points, NOT frozen by this ruling): shares
`SHARE_WARMERS=0.60 / SHARE_API=0.32 / SHARE_MCP=0.08`; caps `ASANA_MCP_RATE_RPS=2.0`,
`ASANA_MCP_RATE_BURST=10`, `ASANA_MCP_RATE_MAX_WAIT_S=2.0` [RV s4-seam-contract §2.2].
**Derivation method (named, not asserted):** `SHARE_MCP × 1500 = 0.08 × 1500 = 120/min`, and
`RATE_RPS × 60 = 2.0 × 60 = 120/min` — the two meet at equality, so the RPS cap is exactly the
MCP share of the declared 1500/min bucket; the warmers-majority split (0.60) follows the
attributed demand shares (service=79,881 / warmer-bulk=25,669 / warmer=3,095 over 6h [RV
CHARGE:38 P-1]) and the fact that warmers are the freshness engine with demonstrated storm
exposure [RV config.py:184-191]. **Scope of the ratification, stated explicitly:** it binds
the DOCTRINE (partition-precedes-exposure) AND the two invariants; the numeric VALUES are
bound by the sprint-4 PR and remain build-time-tunable within the invariants.

---

## Ruling B5 — Fail-closed floor + fail-loud standing bar

**QUESTION.** What must already be true of a route before it may be tool-wrapped, and what
standing contract governs any FUTURE non-idempotent write verb?

(Scope note: the slate's original B5 read-only moratorium was AMENDED by charter W-1/W-3 —
idempotent curated verbs ship in v1. What survives as B5, per the charter's own effect table
[INH charter §6], is the fail-closed floor and the fail-loud contract as the standing bar.)

**Evidence.** The structural reason W-3 exists: the idempotency store silently degrades to a
noop backend on failure [RV api/main.py:368-373 — `extra={"backend": "dynamodb", "error":
str(e), "fallback": "noop"}` → `NoopIdempotencyStore()`; SCAR-IDEM-001 OPEN] — silent
degradation plus agentic retries is the double-execution path.

**Governed-idempotency of the ratified verbs — CORRECTED at AMENDMENT-1 (C1/CH-01, the LEAD
evidence defect; prior text asserted "the ratified verbs are naturally idempotent at HEAD",
which is FALSE for two of three):** the three verbs do NOT share one idempotency posture at
HEAD. add_tag is genuinely idempotent — its OWN route POST /tasks/{gid}/tags is
governed-annotated `idempotent: True` and a no-op on repeat [RV tasks.py:534
`"x-fleet-idempotency": {"idempotent": True...}`, :538 `async def add_tag`, :548-552 "Adding a
tag that is already on the task is a no-op"]. BUT push (PUT-save) and mark_complete BOTH ride
PUT /tasks/{gid} (T2 update_task), whose GOVERNED annotation at HEAD is
`x-fleet-idempotency: {idempotent: False, key_source: None}` [RV tasks.py:254]. That False is
DELIBERATE: it was authored in the SAME commit that stamped DELETE /tasks/{gid}
`idempotent: True` [RV tasks.py:315; `git blame` both → commit d6e9cef17 "feat(asana): add
x-fleet-side-effects to mutating operations (R-05 compliance)"] — the author consciously split
PUT-False from DELETE-True. The route docstring names the reason: "Setting completed=true may
trigger Asana Rules automations (notifications, section moves, workflow transitions)"
[RV tasks.py:272-275] — a side-effect class state-convergence does not silence (C2 UV-P below).
The governed vocabulary at HEAD therefore CONTRADICTS natural-idempotency for the PUT route.

**How tool-hint derivation resolves (A4 governed-vocabulary-only doctrine, with anchors):**
sprint-1 fixed that tool hints derive from the GOVERNED x-fleet vocabulary ONLY [INH frame
SVR-1; s1 PR #237]. Under that rule, at HEAD the composite's hints are: add_tag →
idempotent:True (:534); push + mark_complete → idempotent:False (:254). The composite is thus
NOT "idempotent end-to-end" at HEAD on the governed reading; the two PUT-riding legs inherit
False. A fixed-body partial-update PUT carrying `completed=true` IS state-convergent on re-run
(the task ends completed either way) [RV tasks.py:272-296 partial-update PUT carrying
`completed=body.completed`; :334 "PUT with completed=true"], but state-convergence ≠
side-effect silence — so tool-hint derivation FOLLOWS THE GOVERNED VALUE (False); it does NOT
override the annotation with the convergence argument. This holds until the :254 annotation is
reconciled with a receipt; that reconciliation is a binding W-5 mitigation and a §8 unlock
condition (below). [This carries the contradiction per the adversary's fork (b): AMENDMENT-1
did NOT flip the governed annotation — the required receipt is a live-Asana idempotence proof
for a fixed-body partial-update PUT, which is unprobeable under the zero-direct-calls fence
(C2), so the honest disposition is to carry the False and gate exposure on reconciliation, not
to author a speculative correction to a live mutating route beyond the MCP concern.]

Armed-subset exemplars: data's grain-safety matrix + asana's dispatch-time refusals [INH slate
B5]. The ungoverned x-safe/x-idempotent hand-stamps — CORRECTED at AMENDMENT-1 (A5 qualifier,
CH-07): they sit on the spec-VISIBLE /v1/query introspection routes, NOT "hidden" ones
[RV api/main.py:757-759 comment "visible query introspection GET endpoints", stamps :765-766;
the introspection router is `include_in_schema=True` (query.py:83) while the hidden EXECUTION
router is `include_in_schema=False` (query.py:84) and is ABSENT from `spec["paths"]`, so the
loop never reaches it] — and are reconciled by sprint-1 (A4/PR #237) to the governed
`x-fleet-idempotency`/`x-fleet-side-effects` vocabulary. Tool hints derive from the GOVERNED
vocabulary only.

**C2 caveat on W-3's whole-chain safe re-run (added at AMENDMENT-1, CH-08 — state convergence
≠ side-effect silence):** the composite's mark_complete leg re-PUTs `completed=true`; the
route docstring warns this "may trigger Asana Rules automations (notifications, section moves,
workflow transitions)" [RV tasks.py:272-275], and the satellite DOES receive inbound Asana
Rules actions [RV lifecycle/webhook.py:51 "This endpoint receives webhook POST from Asana
Rules"; api/main.py:260 "Receive inbound task notifications from Asana Rules actions"]. Whether
a RE-PUT of completed=true on an ALREADY-complete task RE-FIRES those Rules is Asana-server-side
behavior — unprobeable from the repo and fenced from live calls — so W-3's "whole-chain safe
re-run" carries this scoped caveat: the STATE converges (the task ends completed either way),
but downstream Rule SIDE-EFFECTS may re-fire on re-run. Frozen for the felt-gate staging probe:
[UV-P: Asana Rules re-fire on idempotent re-PUT of completed=true on an already-complete task |
METHOD: controlled sandbox-workspace probe at felt-gate staging (sprint-6), operator-witnessed |
REASON: unprobeable without live Asana; zero-direct-calls fence (constraint 5)]

### Options

**B5-O1 — Fail-closed-before-wrap precondition + fail-loud contract as standing bar.**
(a) A route must ALREADY refuse unsafe/unarmed shapes before it is tool-wrapped — the
refusal lives in the route, and tool schemas describe ONLY the currently-armed subset;
(b) the fail-loud idempotency CONTRACT (interface + degradation telemetry; deliberately NOT
one shared implementation — the four repos' needs diverge) is the standing gate any future
NON-idempotent verb must satisfy before it may even be PROPOSED to the operator. The
sprint-3 groundwork spec is the referenced artifact. No new v1 mechanism: the three ratified
verbs already satisfy the fail-closed floor by verb selection. (AMENDMENT-1 nuance, C1/CH-01:
"satisfy the floor" means the ROUTES refuse unsafe/unarmed shapes and the verbs were SELECTED
for safety — it does NOT assert all three are governed-idempotent; per the Evidence correction
above, push + mark_complete carry governed idempotent:False at tasks.py:254, and their tool
hints follow that value until the annotation is reconciled.)

**B5-O2 — Fix the store NOW (make the noop-degrade fail loud at v1).** Structurally
distinct: store-fixing instead of verb-selection. AGAINST: charter W-3 is explicit that no
idempotency-store work blocks v1; SCAR-IDEM-001 is defanged by verb SELECTION for the
ratified set; the contract spec captures the fix's shape without serializing v1 behind it.

**B5-O3 — Tool-layer guardrails (wrapper-side validation/refusal).** AGAINST as a pattern:
it relocates the safety boundary into the WRAPPER — the exact inversion the floor exists to
prevent. Wrapper guards drift from route truth; route curation (constraint 6) is only sound
if the ROUTES refuse. (Tool-layer UX niceties may exist; they are never the boundary.)

**B5-O4 — NULL: no floor — wrap what exists; rely on W-3 verb selection alone.** AGAINST:
verb selection covers exactly three verbs today. The FLOOR is what keeps the surface safe
under future verb additions and schema evolution; without it, the next verb ships on habit.

**RECOMMENDATION (pre-filled): B5-O1.**

**WHAT RATIFICATION AUTHORIZES.** The precondition becomes a binding review check on every
tool-wrap change (v1 and future); the fail-loud contract spec (sprint-3 groundwork DRAFT)
becomes the NAMED standing gate for any future non-idempotent verb proposal. No store work
is authorized or scheduled. **AMENDMENT-1 (C1):** ratification also records that, at HEAD, the
two PUT-riding legs (push, mark_complete) carry the GOVERNED value idempotent:False
(tasks.py:254); tool-hint derivation follows that value; and the governed-annotation
reconciliation for PUT /tasks/{gid} is a precondition on write-surface EXPOSURE (carried as a
binding W-5 mitigation and a §8 unlock condition), NOT a v1 build task.

---

## Ruling W-5 — Principal-class conscious-bypass ruling (the LEAD risk, said out loud)

**QUESTION.** Do v1 writes consciously ride the ServiceAccount M2M principal class —
thereby BYPASSING the OpenFGA `agent` write-exclusion by principal-class choice — with
route curation as the Phase-1 security boundary?

**The bypass, out loud.** The OpenFGA model grants data-writes to staff/owner ONLY:
`define can_write_data: staff or owner` [RV model.fga:105]; the `agent` principal type
exists [RV model.fga:23] and the exclusion is DELIBERATE, not accidental — the same model
grants `agent` write-class relations elsewhere (`can_write_scheduling: agent or staff or
owner` [RV :93]; `can_send_sms: agent or staff or owner` [RV :101]) and read access to data
(`can_read_data: viewer or agent or staff or owner` [RV :104]), while withholding
`can_write_data` specifically. WS-1 attested this exclusion STRONG [INH slate B5,
ws1-identity-tenancy.md:58-69]. v1's write path does not confront that exclusion — it goes
AROUND it: the sidecar authenticates as a ServiceAccount (M2M), not as an `agent`
principal, so the agent-exclusion never evaluates on the write path. **An LLM agent acts,
but the principal is a service account.** That is a bypass by principal-class choice. It is
being surfaced here for conscious ratification, not inherited silently (charter W-5;
shape §9 R1).

**Also out loud (constraint 6, fleet reality):** scopes are DOCUMENTATION-ONLY in asana
and most of the fleet — only autom8y-data runtime-enforces them [INH slate B3; frame
constraint 6]. The real Phase-1 boundary is therefore ROUTE CURATION: the MCP surface
exposes exactly the curated tools (reads 1-5, +match_business as surface, ONE composite
write), the composite's three verbs are the only write routes reachable through it, and
agents never sequence raw mutations (W-2).

**Credential-authority breadth (added at AMENDMENT-1, C5/CH-04 — route curation bounds the
PATH, not the CREDENTIAL):** route curation constrains what the agent reaches THROUGH the MCP
tool surface; it does NOT constrain the minted SA credential itself. With scopes
DOCUMENTATION-ONLY (above) and OpenFGA never evaluating on the M2M path (the bypass, said out
loud), the SA's effective authority is the ENTIRE S2S REST write surface — every mutating route
the credential can reach — INCLUDING DELETE /tasks/{gid}, governed idempotent:True at
tasks.py:315 but IRREVERSIBLE by its own docstring ("Permanently deletes this task and ALL
subtasks. Dependents are orphaned. No backup is created" [RV tasks.py:332-334]), which the
curated tool surface never exposes. The curated three-verb composite bounds the agent-via-MCP
PATH; it does not bound what the credential could do off-path. **Detective control — stated
honestly as a DELIBERATE ABSENCE (residual risk recorded):** the only audit trail v1 carries is
the s4 span convention `com.autom8y.mcp.*` (seam §3.2), emitted BY the sidecar, so it covers
ON-path calls ONLY. For OFF-path detection (the SA credential used directly against REST,
bypassing the MCP), NO control exists today — the satellite's RequestLoggingMiddleware logs
method/path/status/duration but NOT the authenticated principal [RV api/middleware/core.py:151-157;
:146 "no sensitive data"], so it cannot key on the MCP SA identity. The compensating candidate —
add principal identity (sub/service_name) to the satellite request log, or an audit alarm on
MCP-SA calls outside the three ratified verbs — is a satellite change, NAMED here as the
remediation, NOT built at v1. The operator ratifies W-5 with this residual visible. (This does
not re-litigate W-1: writes still ship; it names the residual the four preventive mitigations do
not cover.)

**Compounded residual (added at AMENDMENT-2, DELTA ND-2):** the two residuals above and B3ii's
v1 audience choice COMPOUND rather than merely coexist: a bare-FLEET_AUDIENCE token is
replayable across internal fleet surfaces (B3ii) × the SA's effective authority is the full
REST write surface including irreversible DELETE (this section) × no off-path detective
control exists (this section) — so a leaked or replayed MCP-SA token is usable fleet-wide,
against everything, invisibly, for its lifetime. The one live bound on that product is the SA
token TTL: 1800s per mint [RV services/auth/.../token_service.py:739 "TTL =
settings.SERVICE_TOKEN_TTL_SECONDS (1800)"]. The operator ratifies W-5 with this compounded
reading visible, not just its piecewise factors.

### Options

**W5-O1 — ACCEPT the conscious bypass for internal Phase 1**, with FIVE mitigations (the
fifth added at AMENDMENT-1):
(1) route curation as the boundary (above) — bounding the agent-via-MCP PATH; see the
credential-authority-breadth paragraph above for what it does NOT bound (the credential
itself) and the recorded off-path detective-control absence; (2) the OpenFGA amendment
DRAFTED — not landed — scoped to EXACTLY add_tag/mark_complete (sprint-3 groundwork), so the
eventual agent-class migration is not designed cold; (3) the migration trigger NAMED and
unchanged from B3: per-user attribution need, or any write-verb escalation beyond the ratified
set; (4) exposure gated HERE — the built composite is not witnessable-as-ratified until this
ruling passes GATE-BW; **(5) [AMENDMENT-1, C1] the governed idempotency contradiction on PUT
/tasks/{gid} (idempotent:False at tasks.py:254, carried in B5) is RECONCILED BEFORE
write-surface exposure — either the annotation is corrected with a live-Asana idempotence
receipt for a fixed-body partial-update PUT, or exposure proceeds only with the composite's two
PUT-riding legs (push, mark_complete) surfaced to the operator as governed-idempotent:False;
this reconciliation is a §8 unlock condition.**

**W5-O2 — Confront the exclusion: ship v1 writes as `agent`-principal.** Wire delegation
tuples, test delegation_service, enforce the Gap-005 cap, fix TTL-no-refresh, land an
OpenFGA amendment — then expose writes under the class built for agents. AGAINST: E4 found
the path deferred-immature [INH slate E4]; this serializes felt-gate limb (b) behind an
auth-service build program, and lands a LIVE authz-model change in service of a
reference-posture surface — inverting reference-then-promote (V-4).

**W5-O3 — Make the bypass explicit in the model NOW: land (not draft) an amendment**
granting the MCP service principal a scoped write relation. FOR: the model would tell the
truth about who writes. AGAINST: a live fleet authz change pre-probe for two verbs on a
throwaway surface; the DRAFT achieves the design-not-cold benefit without landing; landing
remains operator-merge-reserved anyway.

**W5-O4 — NULL: expose no writes in v1 (reads-only).** Enumerated honestly, and rejected on
charter authority rather than session judgment: W-1 is RATIFIED — "writes ship in v1
proper; the MVP is defined by them" [INH charter §2 W-1]. Choosing O4 at GATE-BW is
therefore a charter AMENDMENT, which is the operator's prerogative, not this dossier's.

**RECOMMENDATION (pre-filled): W5-O1** — accept the bypass consciously for internal
Phase 1, all FIVE mitigations binding (the fifth — PUT-route idempotency-annotation
reconciliation before exposure — added at AMENDMENT-1, C1; plus the credential-authority
breadth and its off-path detective-control absence recorded above for conscious ratification).

**WHAT RATIFICATION AUTHORIZES.** Write-surface EXPOSURE: sprint-6 may present the built
composite as a ratified, witnessable surface for felt-gate limb (b). The OpenFGA amendment
remains a DRAFT (landing/merging stays reserved); no verb beyond
add_tag/mark_complete/push-save is authorized (any addition is operator-reserved, charter
§5); nothing crosses the external trust boundary (V-2). **AMENDMENT-1:** exposure is
additionally preconditioned on the C1 PUT-route idempotency-annotation reconciliation
(mitigation 5 / §8 unlock condition); until then the composite's push + mark_complete legs are
governed-idempotent:False and are surfaced to the operator as such.

---

## §8 What GATE-BW unlocks (and what it does not)

**Unlocked by PASS (and ONLY this):** write-surface **EXPOSURE** — sprint-6's limb-(b)
witness may present the composite as a ratified surface.

**Exposure PRECONDITION carried at AMENDMENT-1 (C1) — rides the PASS, adds no new checkbox:**
write-surface exposure does not proceed until the governed idempotency contradiction on PUT
/tasks/{gid} (idempotent:False, tasks.py:254 — the push/mark_complete carrier) is RECONCILED
per W-5 mitigation (5). Reconciliation = EITHER (a) the :254 annotation is corrected with a
live-Asana idempotence receipt for a fixed-body partial-update PUT (a governed-vocabulary
change on a live mutating route beyond the MCP concern — deliberately NOT authored this session,
see the C1 disposition in §9.5), OR (b) exposure proceeds with the composite's two PUT-riding
legs surfaced to the operator as governed-idempotent:False AND the C2 Rules-re-fire UV-P probed
at felt-gate staging (sprint-6). Either way the operator sees the true idempotency posture
before witnessing limb-(b).

**Already granted regardless of this gate (charter §5.1-5.4; no ratification needed):**
the composite POC BUILD (W-1..W-4 are ratified charter text); the OpenFGA amendment DRAFT +
fail-loud contract spec (groundwork); read-tools POC; observability floor; hygiene motions
(D1-D11 ledger, pagination extraction, x-fleet reconciliation).

**NOT unlocked even on PASS:** the felt verdict (GATE-FELT, operator sole closer); the §4
probe ruling (GATE-PROBE); any additional write verb; external exposure (V-2); fleet code
promotion (constraint 8); merges of any PR.

**On AMEND:** Potnia re-authors exactly the flagged rulings (sprint-5 re-entry per shape
§3 GATE-BW on_fail); write exposure stays blocked until PASS.

## §9 Evidence ceiling + planned critique (self-flagged)

- **This dossier caps at MODERATE** (frontmatter `evidence_grade_ceiling`). Author (rnd
  moonshot-architect) is same-rite as the build — self-referential per
  self-ref-evidence-grade-rule; the R11 bar (twice-proven OR rite-disjoint-critic-STRONG)
  is UNCLEARED. No claim herein is graded STRONG; `[RV]` receipts are mechanical
  file-reads, which support the claims but do not lift the judgmental recommendations
  above MODERATE without external corroboration.
- **Planned lift — NOW ATTACHED (AMENDMENT-1):** the co-seated **arch-adversary** critique
  ran (rite-disjoint from rnd via co-seat inv-20260717-1278d7961503) and returned
  PASS-WITH-CONDITIONS [.ledge/reviews/ADVERSARY-REPORT-asana-mcp-v1-rulings-2026-07-17.md].
  Per critic-substitution-rule the critic is rite-disjoint; its enumeration audit ran BEFORE
  its recommendation audit (option-enumeration-discipline §6); it independently re-verified
  14/14 `[RV]` receipts against live files and corroborated UV-P #1 on both legs. The six
  conditions are discharged at AMENDMENT-1 (§9.5). External corroboration of the MECHANICAL
  receipts is now on the record; the critic's own JUDGMENTS remain MODERATE-ceilinged
  (self-ref-evidence-grade-rule), so the judgmental recommendations do NOT auto-lift to STRONG
  — the operator still ratifies against a MODERATE-ceiling dossier, now with a rite-disjoint
  critique attached rather than absent.
- **MODERATE proposals remain ratifiable.** The ceiling describes confidence, not
  legitimacy; the operator is the ratifier either way.

## §9.5 AMENDMENT-1 discharge table (arch-adversary PASS-WITH-CONDITIONS → six conditions)

Executor: prototype-engineer (rnd, sprint-5 re-entry). Each condition investigated with
live Bash/Read this session, then discharged by surgical Edit. **No §10 checkbox was touched;
no ruling self-ratified.** Recommendation changes are marked REVISED and confined to where a
condition's EVIDENCE demanded it (C4 only); the other five carry the flagged content into the
ratifiable structure WITHOUT flipping a recommendation.

| Cond | Sev | Disposition | What changed | Anchors (all [RV] this session) |
|---|---|---|---|---|
| **C1** | BLOCKING | **CARRIED (fork b) — DISCHARGED-BY-EDIT; NO code path** | Fork (a) NOT cleanly provable — the idempotent:False on PUT is DELIBERATE (authored with DELETE:True in one R-05 commit), and the "annotation-wrong" proof requires a live-Asana idempotence receipt that is unprobeable under the zero-direct-calls fence; so B5 Evidence corrected ("naturally idempotent at HEAD" was false for 2/3 verbs), tool-hint derivation stated (follows GOVERNED idempotent:False for push+mark_complete), reconciliation added as W-5 mitigation (5) + §8 exposure precondition | tasks.py:254 (PUT False), :315 (DELETE True), :534 (add_tag True); `git blame`→d6e9cef17; s1 diff → tasks.py untouched (A15,A16,A18,A20) |
| **C2** | ADVISORY | **CARRIED-AS-UV-P** | B5 C2 caveat on W-3 whole-chain safe re-run (state convergence ≠ side-effect silence); frozen UV-P #4 for felt-gate staging probe | tasks.py:272-275 CAUTION; webhook.py:51; api/main.py:260 (A17,A21) |
| **C3** | FLAG | **DISCHARGED-BY-EDIT** | B4 authorization now carries the sum-invariant (`ΣSHARE ≤ 1.0`, `RATE_RPS×60 ≤ SHARE_MCP×1500`), the s4 values (0.60/0.32/0.08; RPS 2.0/BURST 10/MAX_WAIT 2.0), the derivation (0.08×1500=120/min=2.0×60), and the doctrine-binds/values-delegated scope | s4-seam-contract §2.2; CHARGE:44 P-4(a), :38 P-1 (A26) |
| **C4** | FLAG | **DISCHARGED-BY-RECEIPT (UV-P #1, both legs) → recommendation REVISED** | Leg 1: asana wheel 4.1.0 lacks DATA_PLANE_AUDIENCE (data 4.2.0 has it) — version-floor. Leg 2: SA mint path hardcodes FLEET_AUDIENCE, no audience param → dedicated audience = auth-service change. B3ii-O1 re-scored to "named auth-service prerequisite"; reuse-DATA_PLANE_AUDIENCE enumerated + killed; **v1 recommendation REVISED → bare FLEET_AUDIENCE, dedicated audience deferred to deployment/promotion** | asana/data `.venv` probes; token_service.py:477-485,:705,:767 (A22-A25) |
| **C5** | FLAG | **DISCHARGED-BY-EDIT (residual RECORDED)** | W-5 breadth paragraph: SA effective authority = full REST write surface incl. irreversible DELETE; route curation bounds the PATH not the CREDENTIAL. Detective control named as a DELIBERATE ABSENCE (satellite request log omits the principal; only on-path `com.autom8y.mcp.*` spans exist) with satellite-side remediation named | tasks.py:315,:332-334; api/middleware/core.py:151-157,:146 (A19,A28) |
| **C6** | FLAG | **DISCHARGED-BY-EDIT** | B1-O1 AGAINST now names the reverse-coupling (every MCP-only iteration atomically redeploys production asana), with the reference-posture cadence (multiple sidecar-only iterations pre-felt-gate) and a UV-P #5 for the deploy-behavior offset | types.go:635-642 (A1 inherited); B1-O1 |
| **A5** | ADVISORY | **DISCHARGED-BY-EDIT** | qualifier "hidden query routes" → "spec-VISIBLE introspection routes" corrected in B5 Evidence + Appendix A5 row + anchor-drift line; PR #237 interplay noted (governed post-#237) | main.py:757-766; query.py:83-84 (A27) |
| counter-receipts | — | **CARRIED into Appendix A** | tasks.py:254, :272-275 (and :315) added as A15/A17/A19 | as above |
| frontmatter | — | **UPDATED** | critique_status→ATTACHED (report + pre-amendment sha256 6824581b…bff25); amendment_log AMENDMENT-1 added | — |

**Recommendation changes (old → new), the ONLY ones:**
- **B3ii audience (C4):** ~~deliberately-minted MCP audience; carry UV-P to implementation~~ →
  **bare FLEET_AUDIENCE for v1 (zero auth-service change, mints today); dedicated-audience
  partition RE-SCOPED as a NAMED deployment/promotion prerequisite** (auth-service audience
  parameterization on `create_service_token` + `autom8y_auth` >=4.2.0 + new constant). Old text
  preserved struck-through in B3ii-O1 + the B3 composite recommendation.
- B1, B2, B4, B5, W-5 recommendations are UNCHANGED — the conditions carried flagged content
  into the ratifiable structure (invariants, caveats, breadth, reverse-coupling, idempotency
  contradiction) without flipping any recommendation.

**Deviations / honesty notes:** (1) C1 took fork (b) not (a) — no commit was authored on the s1
branch, because the "annotation-wrong" proof is unprobeable under the zero-direct-calls fence
AND flipping a governed annotation on a live mutating route exceeds the same-concern scope; the
contradiction is CARRIED and exposure is gated on reconciliation. (2) The §10 B3 recommendation
summary cell was updated to stay truthful to the C4 re-score (checkboxes UNTOUCHED); an operator
must not ratify against a stale summary. (3) All new platform-behavior claims carry `[RV]`
receipts (A15-A28) or frozen UV-P labels per SVR discipline; no receipt paraphrases its marker.

## §10 Ratification block (operator-only; sessions never mark these)

> Ratify or amend each ruling independently. GATE-BW passes when all six carry RATIFY (or
> AMENDED-then-ratified). Any AMEND routes the named ruling back to sprint-5 re-entry.

| Ruling | Recommendation (one line) | RATIFY | AMEND (note) |
|---|---|---|---|
| B1 topology | parent_service/command_override; co-deploy coupling accepted+named; re-score at #2 | [x] | [ ] ______ |
| B2 TokenManager | autom8y-core side on the record; TENSION-001 never gates v1/#2; conformance-test decoupler ledgered | [x] | [ ] ______ |
| B3 mint trio | YAML_REGISTRY (SI-4 named) × [REVISED A1 (C4): FLEET_AUDIENCE for v1 — dedicated-audience partition = named auth-service prerequisite] × SA-M2M conscious+revisitable (trigger named) | [x] | [ ] ______ |
| B4 PAT budget | partition-first (static env-var split + MCP cap); arbitration stays descoped to E2 trigger | [x] | [ ] ______ |
| B5 floor | fail-closed-before-wrap precondition; fail-loud contract = standing bar for future non-idempotent verbs | [x] | [ ] ______ |
| W-5 principal class | conscious bypass ACCEPTED for internal Phase 1; route curation is the PATH boundary; 5 mitigations binding (5th = AMENDMENT-1 C1 idempotency reconciliation before exposure); credential-authority breadth + off-path detective-control absence RECORDED (C5) | [x] | [ ] ______ |

Operator signature line: **Tom Tenuta (operator) — by explicit interview instruction, recorded
on the operator's behalf by session a8-mcp-substrate**  date: **2026-07-17**
(GATE-BW disposition: **PASS** — all six RATIFY as recommended. Ratification provenance: the
operator answered "Ratify all six as recommended" in the structured interview of 2026-07-17,
with the acknowledgment baked into that choice: the two exposure preconditions (C1 tasks.py:254
idempotency reconciliation; UV-P#4 C2 sandbox probe — operator-elected fork (i), sandbox project
in the real workspace) and the AMENDMENT-2 compounded W-5 residual (1800s-TTL-bounded) ride the
PASS. Write-surface EXPOSURE is now AUTHORIZED subject to those preconditions at felt-gate
staging; nothing else changes hands — GATE-FELT and GATE-PROBE remain open and reserved.)

---

## Appendix A — SVR receipts (re-verified this session vs inherited)

**Re-verified by direct read this session [RV]** (verification_method: file-read unless noted):

| # | Claim | Anchor | Marker (verbatim slice) |
|---|---|---|---|
| A1 | sub-service co-deploys atomically with parent; CommandOverride required | a8 `pkg/manifest/types.go:635-642` | "shares the parent's ECR image and deploys atomically" |
| A2 | OpenFGA excludes `agent` from data-writes | `services/auth/autom8y_auth_server/openfga/model.fga:105` (type :23) | "define can_write_data: staff or owner" |
| A3 | exclusion is deliberate (agent granted writes elsewhere) | `model.fga:93, :101, :104` | "define can_write_scheduling: agent or staff or owner" |
| A4 | idempotency store silently degrades to noop | asana `api/main.py:368-373` | 'extra={"backend": "dynamodb", "error": str(e), "fallback": "noop"}' |
| A5 | ungoverned x-safe/x-idempotent hand-stamps on the **spec-VISIBLE** /v1/query introspection routes (QUALIFIER CORRECTED at AMENDMENT-1, CH-07 — the dossier previously said "hidden"; the loop iterates `spec["paths"]`, and the hidden EXECUTION router is `include_in_schema=False` (query.py:84) so it is ABSENT from the spec and never stamped). Reconciled to the governed vocabulary by s1 PR #237 | asana `api/main.py:757-766` (comment :757-759 "visible query introspection GET endpoints"); `api/routes/query.py:83-84` | 'op["x-idempotent"] = True' + comment "visible query introspection GET endpoints" |
| A6 | add_tag live, governed-annotated idempotent; repeat is no-op | asana `api/routes/tasks.py:530-552` | '"x-fleet-idempotency": {"idempotent": True' |
| A7 | completion rides partial-update PUT with completed field | asana `api/routes/tasks.py:272-296, :334` | "task (PUT with completed=true) instead of deleting" |
| A8 | typed AsanaQueryClient ships in autom8y-core | `sdks/python/autom8y-core/.../clients/asana_query.py:1` | "AsanaQueryClient - Typed client for autom8y-asana query engine" |
| A9 | asana-service SA sits DB_FALLBACK-ungoverned; class header = SI-4 live trace | `services/auth/.know/credential-topology-matrix.yaml:251-283` | "The reconciler NEVER iterates these" |
| A10 | dual TokenManager files both live at HEAD | glob: `autom8y-{core,auth}/.../token_manager.py` (2 files) | — (git-tree existence) |
| A11 | TENSION-001 row + "high" resolution cost | autom8y `.know/design-constraints.md:26-37` (STALE-flagged registry; underlying files re-verified per A10) | "Coordinated SDK version bump across all consumers; high" |
| A12 | 429 storm attributed; arbitration absent; AIMD backfire; partition cure pre-specified | asana `.sos/wip/CHARGE-substrate-leg2-10xdev-cure-2026-07-13.md:38,44` | "cross-consumer arbitration CONFIRMED ABSENT" |
| A13 | gateway crash-fast at import (E3 mechanism), DRIFT-CORRECTED anchor | `services/api-gateway/src/gateway/policy/operation_registry.py:13-25, :392` | "triggers a visible restart loop" |
| A14 | two-audience admission precedent live at consumer | autom8y-data `api/main.py:66, :1657-1664`; `read_only.py:121-125` | "audience=[FLEET_AUDIENCE, DATA_PLANE_AUDIENCE]" |

**AMENDMENT-1 [RV] receipts** (this session, 2026-07-17; discharging the six conditions +
carrying the adversary's uncarried counter-receipts; method file-read unless noted bash-probe/
git):

| # | Claim | Anchor | Marker (verbatim slice) | Cond |
|---|---|---|---|---|
| A15 | PUT /tasks/{gid} (T2 update_task — the push + mark_complete carrier) governed idempotent:False at HEAD | asana `api/routes/tasks.py:254` | `"x-fleet-idempotency": {"idempotent": False, "key_source": None}` | C1 |
| A16 | the PUT-False / DELETE-True split is DELIBERATE — both authored in one R-05 commit | `git blame` tasks.py:254 & :315 → commit `d6e9cef17` | "add x-fleet-side-effects to mutating operations (R-05 compliance)" | C1 |
| A17 | route docstring CAUTION (uncarried counter-receipt #2): completed=true may trigger Asana Rules automations | asana `api/routes/tasks.py:272-275` | "Setting completed=true may trigger Asana Rules automations" | C1/C2 |
| A18 | add_tag rides its OWN route POST /tasks/{gid}/tags, governed idempotent:True (the only naturally-idempotent ratified verb) | asana `api/routes/tasks.py:534` (route decl :524) | `"x-fleet-idempotency": {"idempotent": True` | C1 |
| A19 | DELETE /tasks/{gid} (counter-receipt #3) governed idempotent:True AND irreversible — the SA credential's off-path reach | asana `api/routes/tasks.py:315`, docstring :332-334 | "Permanently deletes this task and ALL subtasks. Dependents are orphaned" | C5 |
| A20 | s1 branch (PR #237) does NOT touch tasks.py — the :254 annotation is untouched by the QUERY-router reconciliation | `git diff --stat main...feat/asana-mcp-v1-s1-hygiene -- src/.../tasks.py` → empty | (s1 touches main.py + tests + D1-D11 ledger only) | C1/A5 |
| A21 | satellite receives inbound Asana Rules actions (Rules are real; re-fire is server-side) | asana `lifecycle/webhook.py:51`; `api/main.py:260` | "This endpoint receives webhook POST from Asana Rules" | C2 |
| A22 | asana venv `autom8y_auth` **4.1.0**: DATA_PLANE_AUDIENCE ABSENT; FLEET_AUDIENCE present | bash-probe asana `.venv/bin/python -c "import autom8y_auth..."` | `has DATA_PLANE_AUDIENCE: False` · `FLEET_AUDIENCE value: https://api.autom8y.io` | C4 |
| A23 | data venv `autom8y_auth` **4.2.0**: DATA_PLANE_AUDIENCE PRESENT (version-floor artifact) | bash-probe autom8y-data `.venv` | `value: https://data.api.autom8y.io` | C4 |
| A24 | SA mint path `create_service_token` has NO audience param; BOTH branches hardcode FLEET_AUDIENCE | autom8y auth `services/token_service.py:477-485`, :705, :767 | `audience="https://api.autom8y.io"` | C4 |
| A25 | audience param EXISTS on other token fns (contrast); no per-SA audience field anywhere | `token_service.py:212`; grep registries/models/`service-accounts.yaml` → 0 matches | `effective_audience = audience or "https://api.autom8y.io"` | C4 |
| A26 | s4 partition invariants + values (C3 invariant carriage) | `.sos/wip/asana-mcp-v1.s4-seam-contract.md §2.2` | "`SHARE_WARMERS + SHARE_API + SHARE_MCP ≤ 1.0` and `RATE_RPS × 60 ≤ SHARE_MCP × 1500`" | C3 |
| A27 | A5 qualifier: stamps ride spec-VISIBLE introspection routes; hidden exec router absent from spec | asana `api/main.py:757-759`; `api/routes/query.py:83-84` | "Annotate visible query introspection GET endpoints as safe reads" / `include_in_schema=False` | A5 |
| A28 | satellite RequestLoggingMiddleware logs method/path/status/duration, NOT the authenticated principal (no off-path SA-identity detective control) | asana `api/middleware/core.py:151-157`, :146 | "no sensitive data" | C5 |

**Inherited [INH]** (not re-probed; cited at owner's ceiling): frame §7 SVR-2 (hidden query
router), SVR-3/SVR-4 (pagination twins), SVR-5 (honesty fields), SVR-11 (provenance-root);
slate A1 token_manager.py thread-safety lines + service_token.py:40; slate A2
env-architecture.md:149-150 + manifest.yaml:501-540 precedent; slate B5/WS-1
ws1-identity-tenancy.md:58-69; slate E4 delegation-immaturity findings; slate B3
scopes-documentation-only (main.py:674-679); charter W-1..W-4 ratified text.

**UV-P register (updated at AMENDMENT-1):**
1. **DISCHARGED-BY-RECEIPT at AMENDMENT-1 (C4)** — was: [UV-P: DATA_PLANE_AUDIENCE definition
   site in published autom8y-auth SDK]. Both legs probed this session: asana venv autom8y_auth
   **4.1.0** → DATA_PLANE_AUDIENCE ABSENT, FLEET_AUDIENCE present (A22); data venv **4.2.0** →
   symbol present `https://data.api.autom8y.io` (A23); SA mint path `create_service_token`
   hardcodes FLEET_AUDIENCE, no audience param (A24). Replaced by a NAMED prerequisite (not a
   premise): a dedicated MCP audience requires an auth-service change + `autom8y_auth` floor
   bump >=4.2.0 — see B3ii (re-scored) + the B3 recommendation.
2. [UV-P: Asana rate-limit semantics per-token vs per-account (B4-O5 only) | METHOD: Asana
   API docs probe if B4-O5 is ever revisited | REASON: not derivable from repo]
3. Carried, unconsumed (frame §7 UV-P-1): FastMCP 3.x currency / protocol 2025-11-25 —
   rides to POC pin time; not load-bearing for any ruling here.
4. **NEW at AMENDMENT-1 (C2):** [UV-P: Asana Rules re-fire on idempotent re-PUT of
   completed=true on an already-complete task | METHOD: controlled sandbox-workspace probe at
   felt-gate staging (sprint-6), operator-witnessed | REASON: unprobeable without live Asana;
   zero-direct-calls fence (constraint 5)]. Bears on W-3 whole-chain safe re-run (B5 C2 caveat).
5. **NEW at AMENDMENT-1 (C6):** [UV-P: a8 service-stateless rolling-deploy + paired-rollback
   behavior at pinned ref | METHOD: read terraform/modules/stacks/service-stateless deploy
   config or SRE confirm, at deployment-PR time | REASON: deploy-controller behavior not probed
   this session; bounds the B1-O1 reverse-coupling cost if zero-downtime rolling is confirmed].
6. **OPEN reconciliation precondition, named at AMENDMENT-1 (C1) — NOT a premise but a gate:**
   the PUT /tasks/{gid} governed idempotent:False annotation (tasks.py:254) awaits reconciliation
   with a live-Asana idempotence receipt for a fixed-body partial-update PUT before write-surface
   exposure (W-5 mitigation 5 / §8 unlock condition). The required receipt is unprobeable under
   the zero-direct-calls fence, so it is CARRIED, not authored this session.

**Anchor drift corrections recorded:** slate `gateway/app.py:314` → live
`operation_registry.py:13-25, :392` (crash-fast mechanism CONFIRMED at corrected anchor).
AMENDMENT-1: A5 qualifier "hidden query routes" → "spec-VISIBLE /v1/query introspection routes"
— the stamp loop iterates `spec["paths"]`, and the hidden execution router is
`include_in_schema=False` (query.py:84), so it is absent from the spec and never stamped (CH-07).

# END — PROPOSED. The operator ratifies at GATE-BW; no session self-ratifies; the felt
# verdict remains the operator's alone.

---

## ADDENDUM-1 (2026-07-20) — C1 reconciliation evidence FILED; fork-(a) receipt on the record

> Appended post-ratification by the WS-D s5 seat (docs/tech-writer,
> asana-mcp-postfelt-hardening; append-only — NO ratified ruling text above is modified,
> no checkbox touched). Evidence ceiling: MODERATE (self-ref authorship;
> self-ref-evidence-grade-rule). Context at filing: GATE-FELT CLOSED 2026-07-20 — v1
> SHIPPED; the felt verdict lives at `.sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526`
> (§5.2, the operator's hand) and is not restated here.

### A1.1 What this addendum files

The B5/C1 chain above carried an OPEN reconciliation gate on the governed
`x-fleet-idempotency: {idempotent: False}` annotation at `tasks.py:254` (the push +
mark_complete carrier): W-5 mitigation (5) (this file `:615-620`), the §8 exposure
precondition (`:661-670`), UV-P register item 4 (`:831-834`), and item 6 (`:839-843` —
"the required receipt is unprobeable under the zero-direct-calls fence, so it is CARRIED,
not authored"). **The required fork-(a) live-Asana idempotence receipt now EXISTS and is
filed here.**

### A1.2 The C2 no-re-fire receipt (operator-witnessed, 2026-07-19)

Per the envelope §3 protocol (operator-elected fork (i): sandbox project in the bound
workspace), recorded at `.sos/wip/asana-mcp-v1.felt-gate-envelope.md:393-416` (§3.3) with
the mechanical bundle at `.sos/wip/asana-mcp-v1.c2-probe-evidence-2026-07-19.json`:

- Target: project ZZ-MCP-C2-PROBE `1216706635260794`, task `1216701886984398`; Rule
  "Complete To Done" (on completion, move ACTIVE → Done) — positive control satisfied by
  its recorded first fire at the task's original completion.
- Probe: two fixed-body re-PUTs of `completed=true` on the already-complete task
  (15:49:31Z and 15:49:37Z, both HTTP 200) → **ZERO new activity** — no second ⚡ rule-run
  entry, no notifications, task stayed in Done (operator observation of the All-activity
  feed). Mechanical corroboration: `modified_at` frozen at 15:06:47Z across both re-PUTs;
  `modified_at_delta_on_reput_2: false`.
- Disposition (envelope §3.4, mechanical): **NO-RE-FIRE → UV-P #4 DISCHARGED-BY-PROBE.**
- Corroboration: the Step 6.5 write-chain smoke (digest §8,
  `.sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md:165-185`) observed the same
  silence live — the completion re-PUT leg committed 200 with no side-effect, exactly as
  the C2 measurement predicted.

### A1.3 The digest-§11 nuance — what this receipt does and does NOT prove (honest scope)

The limb-(b) run (digest §11, `...limb-a-witness-evidence-digest.md:236-271`) recorded the
calendar-integration play firing TWICE across run + directed re-run. Receipt-decided
mechanism: that play is a **CONSUMED-TRIGGER** automation — on fire it strips the trigger
tag and reopens the card — so the re-run legitimately re-ARMED it via the add_tag leg
against externally-reset state. Fire #2 was protocol-authored, not a PUT-idempotency
defect.

Scope split that the reconciliation ruling must honor:

- **PROVEN (C2 + 6.5)**: a fixed-body re-PUT of `completed=true` on an already-complete
  task is Rules-SILENT for a non-consuming Rule, and state-convergent. This is precisely
  the `tasks.py:254` route-level question — the PUT leg itself.
- **NOT proven (and FALSE as a chain-level generalization)**: "whole-chain re-run is
  side-effect silent under all listeners." Against consumed-trigger automations, re-run =
  re-trigger BY DESIGN (W-3 caveat class PLAY-1; `.know/scar-tissue.md`
  SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER). The re-fire mechanism is the add_tag re-ARM after
  the automation resets preconditions — not the re-PUT.

### A1.4 STAGED for the operator — the `tasks.py:254` reconciliation ruling (NOT executed here)

Both receipts are now on the record; the annotation itself is UNTOUCHED (a satellite code
change is outside this sprint's boundary — shape s5 `pr_boundary: "C1 anchor read-only vs
tasks.py:254"`). SVR at filing: `tasks.py:254` still reads
`"x-fleet-idempotency": {"idempotent": False, "key_source": None},` (re-verified by direct
read at `793e670b` this pass; also frame SVR-3 at `2eb830ca`). The fork, staged with its
evidence:

- **Fork (a) — FLIP to `idempotent: True`**, carrying the C2 receipt (A1.2) as the
  live-Asana idempotence proof the original C1 condition demanded (`:664-666`). If taken:
  the route docstring's Rules caution (`tasks.py:272-275`) should be retained but
  re-scoped to the CONSUMED-TRIGGER caveat (A1.3), and the composite's tool hints
  re-derive to idempotent end-to-end under the A4 governed-vocabulary rule.
- **Fork (b′) — KEEP `idempotent: False` with the documented caveat**, on the ground that
  the governed annotation guards the route for ALL callers and listener topologies, and
  chain-level re-run against consumed-trigger listeners is non-convergent in effect
  (A1.3). If kept: the False is no longer an evidence GAP but a documented POSTURE — the
  UV-P #6 "carried, unprobeable" rationale is superseded by this filing either way.

```
RECONCILIATION RULING (operator's hand only — sessions never mark this):
  [x] fork (a) — flip tasks.py:254 to idempotent: True (C2 receipt A1.2; docstring
      re-scoped per A1.3)
  [ ] fork (b′) — keep idempotent: False, caveat documented per A1.3
  Ruling: fork (a) — "Flip to safe-to-retry" (operator's verbatim selection)
  Date: 2026-07-20  Signature: Tom Tenuta — ruled via structured interview
  (adversarial cases presented; Phase-4 Block-III confirmed "Confirm as drafted");
  scribed at the operator's direction, session b3f74f84. Record:
  .ledge/decisions/RULINGS-operator-interview-telos-ratification-2026-07-20.md (R9).
  Executed in the same PR: annotation flip + docstring re-scope per this fork's own
  spec. Deliberately WITHOUT a future-binding automation-design rule (offered, not
  chosen) — the promise rests on the probe evidence.
```

Status effects at filing (mechanical): the §8 exposure precondition was satisfied via fork
(b) — the posture was surfaced to the operator before limb (b) (envelope §2.1(2) banner +
§2.3 posture line) and GATE-BW/GATE-FELT both closed with it in view. The remaining OPEN
item is exactly this staged ruling; it is predicate limb (c) of
asana-mcp-postfelt-hardening (`.know/telos/asana-mcp-postfelt-hardening.md`), which this
filing discharges up to the operator's mark.

### A1.5 Adversary-minor ledger consolidation (cure-wave DELTA, 2026-07-19 — dispositions on the record)

Source: `.ledge/reviews/ADVERSARY-REPORT-asana-mcp-cure-wave-DELTA-2026-07-19.md` (gate
verdict was BLOCKED(D3-F1) → fixed in-wave; D1-F1 MATERIAL ruled ACCEPT by the operator,
digest §6). The five MINORS, consolidated:

| ID | Finding | Disposition (2026-07-20) |
|---|---|---|
| D1-F2 | "seven pipeline entities" is NINE (`process_account_error`, `process_expansion` included; cured vocabulary = 17) | Correction carried into `.know/scar-tissue.md` SCAR-VOCAB-PARITY-001 + `.know/architecture.md` §MCP; the parity test's subset side covers all nine |
| D1-F3 | Pre-existing vacuous adversarial test on main (`tests/unit/services/test_query_service.py:753` vs `entity_service.py:114` guard) | Ledgered `.know/test-coverage.md` Knowledge Gap 8 + `.know/scar-tissue.md` Knowledge Gap 18 — deserves its own fix; NOT a witness-arc regression |
| D2-F1 | No length bound on `_upstream_suffix` interpolation (`mcp/asana_mcp/errors.py:110-142`) | Production-reimplementation rider (~2KB cap); ledgered `.know/test-coverage.md` Knowledge Gap 9 + frame §8 riders |
| D2-F2 | Auth-branch prose fence one-sided (upstream 401 prose could carry warming lexicon) | Same rider class; recommendation = assert the auth suffix never matches the warming lexicon (mirror the disjointness test) |
| D3-F2 | Runbook Step 6.5 "Expect ... Rule firing again" contradicted the C2 no-re-fire record | Superseded by the A1.2/A1.3 filing (authoritative wording: expect NO new fire on the re-PUT; the consumed-trigger caveat governs the add_tag leg); the runbook is a session-plane artifact retired with the shipped witness |

# END ADDENDUM-1 — evidence filed; the reconciliation ruling above awaits the operator's
# hand; nothing in this addendum modifies a ratified ruling.
