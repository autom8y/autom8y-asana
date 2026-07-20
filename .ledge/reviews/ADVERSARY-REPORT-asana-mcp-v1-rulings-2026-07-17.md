---
type: review
subtype: adversary-report
status: complete
verdict: PASS-WITH-CONDITIONS
target_artifact: autom8y-asana/.ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md
target_sha256: "6824581b906565e24f1acd89f71d84c7da45dfd5ed7ad557f2839902f15bff25"
critic: arch-adversary (rite-disjoint via co-seat inv-20260717-1278d7961503; rnd is the authoring rite, arch is the critiquing rite)
initiative: asana-mcp-v1
session: session-20260717-181924-9924bb32
date: 2026-07-17
iter: 1
delta_scope_attested: false   # first-round FULL critique per critique-iteration-protocol Phase 1
tl_a_status: CHALLENGE        # falsifiable-evidence axis: one load-bearing claim contradicted at HEAD
tl_b_status: CHALLENGE        # citation-integrity axis: two uncarried adjacent counter-receipts + one qualifier drift
tl_c_status: CHALLENGE        # enumeration/disposition axis: named gaps per ruling; none recommendation-flipping
evidence_grade_ceiling: MODERATE   # self-ref cap on this critic's own judgments; mechanical re-probes are receipts, judgments are not
arch_ref_citations:
  - "AV:SRC-001 (Messick 1989 — construct validity; each challenge names the claim attacked)"
  - "AQ:SRC-010 (Cohen 1960 — rite-disjoint second rater; this critique is the disjoint leg)"
  - "AQ:SRC-013 (Sadler 1989 — criterion-referenced grading resists motivated drift)"
charter_precedence_held: "charter GOVERNS; W-1..W-4 ratified text NOT attacked; only the dossier's carriage of it is audited"
e_kill_relitigation: NONE     # dossier does not re-litigate E1-E5; no challenge herein requires re-litigating them
---

# ADVERSARY-REPORT — asana-mcp-v1 rulings dossier B1-B5 + W-5 (iter 1, FULL scope)

## VERDICT: PASS-WITH-CONDITIONS

The dossier survives most of its own strongest attack surface: 14/14 sampled [RV]
receipts re-verified against live files by this critic; the null options are genuinely
enumerated, not strawmanned; no E-kill is re-litigated; the operator-sovereignty and
grant/reserve boundaries are carried faithfully from the charter. It does NOT pass clean:
one load-bearing evidence claim ("the ratified verbs are naturally idempotent at HEAD")
is contradicted by the fleet's own governed metadata twenty lines above the dossier's
cited anchor range, and the dossier's citation practice at two anchors omits adjacent
counter-context. All defects are concretely repairable at sprint-5 re-entry; none flips
a recommendation on the evidence enumerated. Per the dispatch verdict calculus (BLOCK
only where operator ratification would be unsound), the correct token is
PASS-WITH-CONDITIONS with condition 1 carrying BLOCKING severity if undischarged.

## 1. Enumeration Audit (run FIRST, per option-enumeration-discipline)

Per-ruling outcome: at least one structurally-distinct unenumerated option named, or
exhaustiveness conceded.

- **B1 topology — INCOMPLETE (minor).** Unenumerated: (i) in-process mount (FastMCP app
  mounted into the existing asana FastAPI process — the true null-mechanism placement;
  killed by frame constraint 5, but a kill must be NAMED, not omitted); (ii) Lambda
  placement (the manifest reconciler diffs "live task definition or Lambda config",
  types.go:632 — a structurally distinct deploy unit; weak fit for MCP session
  transport, but unenumerated). Neither overturns O1.
- **B2 TokenManager — SUBSTANTIALLY EXHAUSTIVE.** One weak gap: direct client-credentials
  mint via own httpx call (no SDK at all) — structurally distinct from O4 pass-through;
  trivially killed by joining-not-adding. Recommendation follows from verified evidence
  (AsanaQueryClient co-residence receipt A8 re-verified).
- **B3(i) governance — EXHAUSTIVE** for the decision as scoped (governed / match-neighbors
  / reuse-existing). O2 is a real option honestly killed on the gate-RED receipt (A9
  re-verified), not a strawman.
- **B3(ii) audience — INCOMPLETE (minor).** Unenumerated: reuse the existing
  DATA_PLANE_AUDIENCE itself (join the live second audience rather than mint a third) —
  structurally distinct middle option; easily killed (cross-plane replay), but absent.
  See CH-03 for the UV-P load-bearing finding on the enumerated O1.
- **B3(iii) principal — EXHAUSTIVE** (SA / agent / human-credential null); mirrors the
  charter's own decomposition.
- **B4 PAT budget — EXHAUSTIVE.** Five options including two null-adjacent shapes; the
  strongest-evidenced section, and my re-probe of CHARGE:38/:44 confirms it. Residual
  refinements (shared token-bucket state; priority shedding) are variants of O2's
  taxonomy, not distinct classes. See CH-02 for the missing invariant.
- **B5 floor — INCOMPLETE (notable).** Unenumerated: a MECHANICAL floor — derive
  wrap-eligibility from the governed x-fleet-idempotency metadata via CI gate
  (GOV-009/OperationRegistry machinery already exists) instead of O1's human "binding
  review check". Notable because this option, had it been enumerated, would have
  mechanically surfaced CH-01: the governed metadata at HEAD FAILS the PUT route.
- **W-5 principal bypass — INCOMPLETE (minor).** Unenumerated: (i) time-boxed acceptance
  (sunset/re-ratification at GATE-PROBE or +Nd) as a structurally distinct governance
  shape vs the event-based trigger; (ii) a detective-control mitigation (audit alarm on
  MCP-SA write calls) alongside the four preventive/structural mitigations.

**Null-option strawman check: PASS.** B1-O4 carries real FORs and the POC-de-facto
honesty note; B4-O4 is scar-killed on a verified receipt; W5-O4 is correctly rejected on
charter authority (choosing it would amend ratified W-1 — operator's prerogative). These
are genuine enumerations.

## 2. Evidence Audit — receipts re-verified by this critic

**VERIFIED (all 14 [RV] rows independently re-probed, live files, this session):**

| Receipt | Anchor | Result |
|---|---|---|
| A1 | a8 pkg/manifest/types.go:635-642 | VERIFIED verbatim ("shares the parent's ECR image and deploys atomically"; CommandOverride required). B1-O3's absence-claim (:635-648 no second-container field) also VERIFIED — struct closes at :648. |
| A2/A3 | model.fga:105, :93, :101, :104, :23 | VERIFIED verbatim. `can_write_data: staff or owner`; agent granted write-class elsewhere; exclusion-is-deliberate reading supported. |
| A4 | asana api/main.py:368-373 | VERIFIED verbatim (noop fallback + NoopIdempotencyStore()). |
| A5 | api/main.py:765-766 | Stamps VERIFIED; "hidden routes" QUALIFIER DRIFTED — see CH-07. |
| A6 | tasks.py:530-552 | VERIFIED (add_tag governed idempotent:True at :534; no-op text :548, :552). |
| A7 | tasks.py:272-296, :334 | Range VERIFIED — but two adjacent counter-receipts uncarried: see CH-01, CH-08. |
| A8 | autom8y-core clients/asana_query.py:1 | VERIFIED verbatim. |
| A9 | credential-topology-matrix.yaml:246, :251-261, :274-283 | VERIFIED verbatim (YAML_REGISTRY row; "reconciler NEVER iterates these"; asana-service DB_FALLBACK). |
| A10 | dual token_manager.py glob | VERIFIED — both files exist at HEAD. |
| A11 | design-constraints.md:26-37 | VERIFIED verbatim ("Coordinated SDK version bump across all consumers; high"). |
| A12 | CHARGE-substrate-leg2:38, :44 | VERIFIED verbatim (arbitration CONFIRMED ABSENT; 79,881/25,669/3,095; ~896 429s/12min backfire; cure (a) partition "summing <1500"). |
| A13 | operation_registry.py:13-25, :392 | VERIFIED (crash-fast docstring; `raise OperationAltitudeError(msg)` at :392). Drift-correction from slate's gateway/app.py:314 is legitimate and well-recorded. |
| A14 | data api/main.py:66, :1657-1664; read_only.py:121-125 | VERIFIED verbatim (import at :66; `audience=[FLEET_AUDIENCE, DATA_PLANE_AUDIENCE]` both sites). |

**UV-P #1 independently corroborated on BOTH legs:** grep of
autom8y/sdks/python/autom8y-auth/src/ finds NO DATA_PLANE_AUDIENCE definition (source
absence confirmed), while data main.py:66 does `from autom8y_auth import
DATA_PLANE_AUDIENCE` live (published wheel carries it). The wheel/source skew suspicion
is real. The UV-P labeling is honest. The over-claim rides elsewhere — see CH-03.

**Counter-receipts the dossier did NOT carry (found by this critic):**

1. **tasks.py:254** — the PUT /tasks/{gid} decorator (T2 update_task), the exact route
   both `push(PUT-save)` and `mark_complete` ride, is governed-annotated
   `"x-fleet-idempotency": {"idempotent": False, "key_source": None}`. Eighteen lines
   above the dossier's cited range (:272-296).
2. **tasks.py:272-275** — the OPENING lines of the dossier's own cited range are a
   CAUTION: "Setting completed=true may trigger Asana Rules automations (notifications,
   section moves, workflow transitions)" — a side-effect class bearing directly on W-3
   "whole-chain safe re-run", uncarried.
3. **tasks.py:315** — DELETE /tasks/{gid} (irreversible, per its own docstring) is
   governed-annotated idempotent:True — evidence that the governed vocabulary encodes
   protocol-idempotency, not safety; relevant to how tool hints derive (A4 doctrine).

## 3. Challenge Register (severity-ranked; taxonomy per AC-01..AC-05 adapted to
decision-dossier altitude; every challenge carries a falsification pathway)

### CH-01 [BLOCKING severity] — B5/W-3 evidence claim contradicted by governed metadata at HEAD
- **Taxonomy**: AC-02 variant (load-bearing present-tense claim whose falsifying
  evidence exists, adjacent to the cited anchor, and is uncarried). TL-A + TL-B.
- **Target**: B5 Evidence paragraph ("The ratified verbs are naturally idempotent at
  HEAD"); B5-O1 ("No new v1 mechanism: the three ratified verbs already satisfy the
  floor by verb selection"); W-5 exposure story by inheritance.
- **Challenge**: Two of the three ratified verbs (push, mark_complete) ride PUT
  /tasks/{gid}, whose GOVERNED x-fleet-idempotency annotation at HEAD is
  `idempotent: False` (tasks.py:254). The dossier's own doctrine (A4/A5; sprint-1
  reconciliation) is that tool hints derive from the governed vocabulary ONLY — under
  that doctrine, at HEAD, the composite's two PUT-riding legs would inherit
  idempotent:False hints, contradicting the "idempotent end-to-end" story presented for
  GATE-BW. The dossier cites :272-296 and never confronts :254. This is not an attack on
  charter W-4 (operator-ratified REST-PUT-semantics definition — likely the annotation
  is a conservative or erroneous stamp); it is an attack on the dossier's carriage: a
  receipts-first artifact asserted "naturally idempotent at HEAD" while the substrate's
  governance metadata at HEAD says otherwise, and the operator ratifying B5/W-5 would
  not learn it from this dossier.
- **Falsification pathway**: (a) demonstrate the annotation is erroneous — receipt that
  a fixed-body partial-update PUT is idempotent at the Asana resource level — and
  correct :254 (and audit :193/:480/:635/:688) in the sprint-1 x-fleet reconciliation
  PR, citing the change in the dossier; OR (b) amend B5/W-5 to carry the contradiction
  explicitly and condition exposure on annotation reconciliation. Either observation
  collapses this challenge to a citation-hygiene FLAG.

### CH-02 [FLAG] — B4 partition ruling ratifies a word, not an invariant
- **Taxonomy**: AC-02 (protective content not promoted into the ratified structure). TL-A.
- **Target**: B4 "WHAT RATIFICATION AUTHORIZES".
- **Challenge**: The CHARGE cure (a) — which the dossier itself quotes — carries the
  operative invariant ("env ASANA_RATELIMIT_MAX_REQUESTS per consumer summing <1500;
  config-only"). The ruling text ratifies "partition-first" DOCTRINE without carrying
  the sum-invariant, any value ranges, or a derivation method (the attributed demand
  shares 79,881/25,669/3,095 are sitting right there in P-1). A partition ruling without
  its invariant is ratifiable as a word; a nominal partition (e.g., MCP=1400 of 1500)
  would satisfy it while reproducing the storm.
- **Falsification pathway**: add one sentence to B4's authorization: per-consumer
  budgets MUST sum below the PAT ceiling per CHARGE cure (a), values fixed in the
  sprint-4 PR with derivation method named from the attributed demand shares. If the
  operator's ratification is intended to bind doctrine-only with values delegated,
  say that explicitly — either observation discharges.

### CH-03 [FLAG] — B3(ii) recommendation partially load-bearing on the UV-P's unverified leg
- **Taxonomy**: AC-02 (claim scope exceeds receipt scope). TL-A + TL-B.
- **Target**: B3ii-O1 ("generalizing the live second-audience precedent... the PRECEDENT
  stands on the consumer receipts").
- **Challenge**: The consumer receipts (A14, re-verified) prove ADMISSION-side only —
  fleet middleware accepts a token whose aud is in the set. "Deliberately-minted MCP
  audience" additionally requires the MINT side: that the auth service can mint a token
  with a NEW, chosen audience, and where that is parameterized. That is exactly the leg
  the UV-P defers (definition-site unknown; wheel/source skew confirmed by this critic).
  The dossier's framing ("the PRECEDENT stands on the consumer receipts") over-claims:
  the precedent for admission stands; the precedent for deliberate minting is
  unreceipted. If mint-side audience choice requires an auth-service change, B3ii-O1's
  cost re-scores and the deployment PR serializes behind auth work.
- **Falsification pathway**: probe the installed autom8y_auth wheel for
  DATA_PLANE_AUDIENCE AND receipt the mint-site audience parameterization (file:line of
  where token audience is set at mint) before the deployment PR. A mint-side receipt
  showing parameterized audience discharges this challenge entirely.

### CH-04 [FLAG] — W-5 mitigation (1) bounds the path, not the credential; breadth un-named
- **Taxonomy**: AC-01 adapted (implicated facet — credential authority breadth —
  unaddressed and undeclared). TL-C.
- **Target**: W5-O1 mitigation (1) "route curation as the boundary".
- **Challenge**: Route curation constrains what the agent reaches THROUGH the MCP tool
  surface. It does not constrain the minted SA credential itself: with scopes
  documentation-only (constraint 6, carried honestly) and OpenFGA never evaluating on
  the M2M path (the bypass, said out loud), the SA's effective authority is the ENTIRE
  asana REST surface — including DELETE /tasks/{gid}, which is irreversible by its own
  docstring (tasks.py:332-334). The dossier surfaces the principal-class bypass for
  conscious ratification but not the credential-authority breadth that rides with it. A
  conscious ratification should see both. (This does not re-litigate W-1: writes still
  ship; it names the residual the four mitigations do not cover.)
- **Falsification pathway**: add a breadth paragraph to W-5 (effective SA authority =
  full REST surface; only the MCP path is curated) + name a compensating detective
  control (audit alarm on MCP-SA calls outside the three ratified verbs) or its
  deliberate absence. If a runtime constraint on the SA already exists that this critic
  missed, cite it — that receipt falsifies the challenge.

### CH-05 [FLAG] — B1 mitigating argument is one-directional
- **Taxonomy**: AC-02 (argument asymmetry presented as symmetric cost analysis). TL-C.
- **Target**: B1-O1 "Honest mitigating observation".
- **Challenge**: "Availability is ALREADY functionally coupled" is true in ONE direction
  (MCP needs asana's REST surface) and defrays only the availability component of the
  AGAINST. Atomic co-deploy (types.go:636, verified) couples BOTH directions: every
  MCP-only change redeploys production asana. v1's reference posture is precisely the
  regime of highest MCP iteration churn (tool schema tweaks), so the un-named cost —
  parent exposed to sub-service deploy cadence — peaks exactly during v1. The
  observation does not smuggle the conclusion (the marginal-availability point is
  sound), but it argues the cheap half and stays silent on the half that cuts against O1.
- **Falsification pathway**: name the reverse direction in B1-O1 AGAINST with the
  expected v1 MCP iteration cadence; if fleet deploys are zero-downtime rolling with
  paired rollback, cite that behavior — the receipt would bound the reverse-direction
  cost and discharge the challenge.

### CH-06 [ADVISORY] — Enumeration gaps (aggregated from §1)
- **Taxonomy**: AC-01 adapted (options absent without out-of-scope declaration). TL-C.
- B1 in-process mount (name-kill via constraint 5) + Lambda placement; B3ii
  reuse-DATA_PLANE_AUDIENCE; B5 mechanical metadata-gate floor; W-5 sunset-clause
  variant + detective control. One name-and-kill line each suffices. None flips a
  recommendation.
- **Falsification pathway**: add the kill lines; or show any is not structurally
  distinct from an enumerated option.

### CH-07 [ADVISORY] — A5 qualifier drift ("hidden" vs live "visible")
- **Taxonomy**: AC-02 minor / citation drift. TL-B.
- The stamps at main.py:765-766 apply to spec-VISIBLE /v1/query introspection paths
  (comment at :757-759 says "visible query introspection GET endpoints"; query.py:80-84
  confirms the execution router is hidden and therefore absent from spec["paths"]).
  The dossier's A5 claim says "hidden query routes". The substantive claim (ungoverned
  parallel vocabulary needing sprint-1 reconciliation) stands — and is actually STRONGER
  than cited: hidden routes get ungoverned idempotency PROSE via the
  x-query-method-candidates extension (main.py:735-746) as a second ungoverned
  mechanism. Correct the qualifier; optionally cite the second mechanism.
- **Falsification pathway**: re-read main.py:757-766 + query.py:80-84; if a
  hidden-route stamping block exists elsewhere that this critic missed, cite it.

### CH-08 [ADVISORY, rides condition 2] — Automation-trigger caution inside the cited range, uncarried
- **Taxonomy**: AC-02 (side-effect class unprobed, bearing on a ratified property's
  end-to-end carry). TL-B.
- tasks.py:272-275 (the dossier's OWN cited range) warns completed=true may trigger
  Asana Rules automations. Whether a RE-RUN (re-PUT completed=true on an
  already-complete task) re-fires automations is unprobed in either direction; it bears
  on W-3's "whole-chain safe re-run" as carried into the composite.
- **Falsification pathway**: Asana API docs probe or live test: re-PUT completed=true
  on a completed task; record whether Rules re-fire. Either result is a receipt; a
  no-refire result fully discharges.

## 4. Conditions (numbered; each assignable to sprint-5 re-entry per shape §3 GATE-BW on_fail)

1. **[from CH-01 — BLOCKING if undischarged]** Reconcile the governed idempotency
   contradiction before GATE-BW submission: tasks.py:254 (`PUT /tasks/{gid}`, the
   push/mark_complete carrier) is x-fleet-idempotency idempotent:False at HEAD. Either
   correct the annotation with a receipt (fixed-body partial-update PUT idempotence
   argument) via the sprint-1 x-fleet reconciliation PR and cite it in the dossier, or
   amend B5/W-5 to carry the contradiction and gate exposure on reconciliation. State
   how tool-hint derivation (A4 governed-vocabulary-only doctrine) resolves for the
   composite either way.
2. **[from CH-08]** Probe and record re-run automation semantics (re-PUT completed=true
   on an already-complete task: do Asana Rules re-fire?). Carry the result into the
   composite's safe-re-run claim as receipt or frozen-syntax UV-P.
3. **[from CH-02]** Carry the partition invariant into B4's authorization text:
   per-consumer budgets sum below the PAT ceiling (CHARGE cure (a) "summing <1500"),
   values fixed in the sprint-4 PR, derivation method named from the attributed demand
   shares — or state explicitly that ratification binds doctrine-only with values
   delegated.
4. **[from CH-03]** Before the deployment PR: discharge UV-P #1 on BOTH legs — probe
   the installed autom8y_auth wheel for DATA_PLANE_AUDIENCE AND receipt the mint-side
   audience parameterization. If mint-side requires auth-service change, re-score
   B3ii-O1's cost in the dossier.
5. **[from CH-04]** Add the credential-authority breadth paragraph to W-5 (SA effective
   authority = full REST surface incl. irreversible DELETE; curation bounds the MCP
   path only) + name a detective control or its deliberate absence, so the operator
   ratifies the full residual.
6. **[from CH-05]** Add the reverse-coupling sentence to B1-O1 AGAINST (every MCP-only
   iteration redeploys production asana atomically) with expected v1 iteration cadence;
   cite zero-downtime/paired-rollback deploy behavior if it defrays the cost.

ADVISORY (non-conditions, recommended): CH-06 name-and-kill lines; CH-07 qualifier
correction.

## 5. What this critique does NOT do

It does not ratify (operator-only, charter §5:96-98); it does not speak or gate the felt
verdict (GATE-FELT is the operator's alone); it does not attack ratified charter text
(W-1..W-4, V-rulings, E-kills stand as governed); it does not re-litigate E1-E5, and no
challenge above requires doing so; it does not decide remediation content (rnd's
sprint-5 re-entry owns that). Per critique-iteration-protocol, a second round (if the
dossier is re-authored) is DELTA-scope only; a second BLOCKING-severity finding at
DELTA escalates to the operator — no third round exists.

## 6. Falsification of THIS report

This report's verdict revises if: (a) the tasks.py:254 annotation is shown
pre-corrected in an unmerged sprint-1 PR already cited by the dossier's grounding (this
critic checked only HEAD working trees); (b) a separate governed-idempotent
mark_complete route exists that this critic's grep missed; (c) mint-side audience
parameterization is already receipted in an artifact within the dossier's [INH] chain;
or (d) the operator rules that W-4's REST-semantics definition supersedes governed
metadata for ratification purposes, making CH-01 a substrate-hygiene item rather than a
ratification-evidence item — in which case the verdict recomputes toward PASS with
conditions 3-6 as advisories. Any of these observations should be presented at DELTA.
Self-referential cap: this critic's judgments are MODERATE-ceilinged
(self-ref-evidence-grade-rule); the mechanical re-probes in §2 are receipts and stand
independent of that cap.

# END — iter 1. Verdict: PASS-WITH-CONDITIONS. Six conditions, all assignable to
# sprint-5 re-entry. The operator remains the sole ratifier at GATE-BW.
