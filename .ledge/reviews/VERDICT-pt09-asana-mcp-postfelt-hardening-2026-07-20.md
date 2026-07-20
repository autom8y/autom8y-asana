---
type: scratch
artifact: eunomia-advisory
target_initiative_slug: asana-mcp-postfelt-hardening
verdict: FLAG-ADVISORY
evidence_grade: MODERATE
status: flag-advisory
date: 2026-07-20
source_hash: origin/main@33c38f35061384cc02744407a78447b696732573
probe_id: pt09-asana-mcp-postfelt-hardening-attest-2026-07-20
attester: eunomia/verification-auditor (rite-disjoint; zero authorship in the wave)
ground_truth_ref: origin/main@33c38f35061384cc02744407a78447b696732573
governing_artifacts_ref: bc4b0aef (PR #253 — NOT yet merged at attest time; read via git show)
binding: >-
  eunomia verification-auditor, rite-disjoint ADVISORY over receipts, R1 binding.
  Felt/witness observations inside the predicate remain the operator's own;
  eunomia attests receipt integrity, never a felt outcome. Product-altitude
  ADVISORY — NON-BLOCKING; surfaces to /go LIVE-eunomia-refusal panel +
  close-comment + this VERDICT artifact. Self-grade caps MODERATE
  (self-ref-evidence-grade-rule); ATTESTED-full is unreachable for a self-ref
  verdict by construction.
---

# VERDICT — PT-09 three-limb receipts-only attest — asana-mcp-postfelt-hardening

> **Product-Altitude ADVISORY** (non-blocking). Three non-substitutable evidence legs
> per limb (three-evidence-leg-attestation): (a) receipts-exist re-read uncached
> post-fetch; (b) discrimination re-derived with the attester's OWN fresh construction;
> (c) user-surface observed DIRECTLY. The attester inherits NONE of the builder's or
> critics' proofs — the five inscribed adversary verdicts are corroborating INPUTS, not
> substitutes. Rite-disjoint by construction: eunomia holds zero authorship in the wave.

## Ground-truth + merge-state honesty

- Fetched `origin` at attest entry. Ground truth = `origin/main@33c38f35`. The operator's
  primary checkout local `main` is frozen PRE-EPIC at `f3d8eec1` (the 3rd-strike
  stale-checkout hazard, charge P-7); every claim below is read against `origin/main` or a
  fresh worktree cut from it, never the frozen local ref.
- Governing artifacts (HANDOFF + CHARGE + slots.yaml) live at `bc4b0aef` (PR #253),
  which is **NOT yet an ancestor of origin/main** at attest time (`git merge-base
  --is-ancestor bc4b0aef origin/main` → false). They were read via `git show bc4b0aef:<path>`;
  content is identical to the eventual merge. Stated honestly per the charge.

## The predicate under attest (operator's verbatim words — telos verified_realized)

> (a) a deploy completes while a client session queries continuously and observes ZERO
> warming errors (TG health-check receipt on /ready + one mid-deploy green session)
> (b) one composite invocation addressed by tag NAME succeeds e2e
> (c) C1 annotation reconciliation + fork-(a) receipt filed on the dossier record

Source: `.know/telos/asana-mcp-postfelt-hardening.md` verified_realized_definition
(origin/main). The operator's felt verdict that shipped the parent (v1) lives verbatim at
`.sos/wip/asana-mcp-v1.felt-gate-envelope.md:503-526` (§5.2) — cited, never paraphrased,
never re-spoken.

---

## Per-limb verdicts (three legs each)

### LIMB (a) — deploy completes + /ready TG health-check + mid-deploy green session — **FLAG-ADVISORY**

**Core predicate: RECEIPT-INTACT and LIVE-CORROBORATED.** One cited cross-check receipt is
CONTRADICTED by live immutable state — flagged, narrowly scoped, substance-true underneath.

| Leg (altitude) | Own-hands receipt | Result |
|---|---|---|
| (a) receipts-exist (uncached, post-fetch) | `.sos/wip/asana-mcp-postfelt-hardening.PT01-activation-ledger.md:225-254` (PT-04 RECEIPT); `.know/scar-tissue.md:142` + `:444-471` SCAR-TG-LIVENESS-001 **CURED**@origin/main; WS-A merge chain ancestry-verified by my own `git merge-base --is-ancestor`: satellite `#248 6edc83d5` ANCESTOR-OK; cross-repo `a8 #104 80402fd3` + `autom8y #1157 d502398d` doc-graded (non-satellite objects, charge P-5) | PRESENT, internally consistent |
| (b) discrimination (OWN construction — live read-only AWS) | `describe-target-groups`: BOTH TGs (autom8y-asana-service, a8-asana-green) HealthCheckPath=`/ready`, Matcher=`200`. `describe-services`: grace=`2400`, PRIMARY `:663` rolloutState COMPLETED. `describe-task-definition :659` (the PT-04 taskdef): healthCheck cmd → `/health`, **startPeriod=120**. Revision walk `:657-663`: `:659=120` (reg 15:12:13Z), `:660=300` (reg 15:13:26Z). `describe-services` events: deployment `ecs-svc/0263950317217302961` completed **15:44:01Z** (to-the-second match), task `98a756a0` started 15:12:28Z. Green TG target `10.0.146.86:8000` **healthy** now. | Regime LIVE; deploy-completion CORROBORATED; **startPeriod=300@:659 CONTRADICTED** |
| (c) user-surface (observed DIRECTLY) | Live `GET https://asana.api.autom8y.io/ready` → HTTP **200** `{"status":"ok","service":"asana",...}` all checks ok (my own hit). PT-04 client-probe log ledger `:241-242` (two mid-warm GETs, 15:24:59Z→200, 15:30:37Z→200) — the "zero warming errors" observation is the operator's/observer's, receipt attested, felt not spoken. | /ready surface LIVE 200; client-probe receipt PRESENT |

**Flag (scoped):** the receipt "taskdef `:659` registered with startPeriod=300" (charge P-1;
COND-2 leg-1 of a8 #104; ledger `:217`,`:236`; adversary chain V1) is **contradicted by live
immutable AWS state** — `:659` carries `startPeriod=120`; the a8-clamp `startPeriod=300`
first appears at `:660`, registered ~73 s AFTER the `:659` deploy was created. Task
definitions are immutable, so `:659` could never have been 300. The clamp's **substance**
(RegisterTaskDefinition ACCEPTS startPeriod=300) is nonetheless **live-true** at `:660-:663`;
the error is a revision-attribution off-by-one, NOT a predicate falsification. startPeriod is
immaterial to the deploy outcome — the container `/health` check serves 200 from process-up
in all four states, and the ≈29.5-min warming survival is governed by service grace=2400
(live-confirmed). The predicate's three parenthetical requirements (deploy completes;
/ready TG receipt; one mid-deploy green session) all hold and are live-corroborated.

### LIMB (b) — one composite invocation addressed by tag NAME succeeds e2e — **PASS-ADVISORY**

| Leg (altitude) | Own-hands receipt | Result |
|---|---|---|
| (a) receipts-exist (uncached, post-fetch) | `#249` merged `b630a901` (my `git merge-base` → ANCESTOR-OK; `gh pr view 249` mergedAt 2026-07-20T16:04:25Z, mergeCommit b630a901); tool chain `mcp/asana_mcp/tools/tag_resolve.py` + `composite_write.py`; `#246` route `2ee3391c` ANCESTOR-OK; route source `src/autom8_asana/api/routes/tags.py`@origin/main (GET /api/v1/tags?name=, idempotent:True, read-only); adversary V3 (PASS-W-C @16cfbb64) → V4 (PASS @b98936e7, all conditions discharged) | PRESENT, ancestry-verified |
| (b) discrimination (OWN construction — live read-only, ZERO writes) | Fresh `GET https://asana.api.autom8y.io/api/v1/tags?name=play_custom_calendar_integration` → HTTP **200**, resolved → **`1209319457948185`**, name exact-match, has_more:false. Resolution-only; NO write verb fired (sandbox deleted per s6; write verbs not the attester's — G-THEATER). | NAME→GID resolution path LIVE on the deployed satellite |
| (c) user-surface (observed DIRECTLY) | The live route above IS the name-addressing user surface. Cured e2e transcript cited from PR #249 body: name-keyed resolution → add_tag → read-back PASS against the deployed satellite; idempotency demonstrated (2×POST 200, read-back count=1); provenance-stamped; `[0]` bare-list-vs-name-scan mechanism attested. The composite WRITE half was operator-witnessed at GATE-FELT (envelope §2.3) + builder e2e — cited, NOT re-fired. | e2e-by-NAME receipt PRESENT + head-bound; write half fenced |

**Basis for PASS-ADVISORY:** the e2e-by-NAME composite receipt is complete and head-bound
(V4 PASS @b98936e7, all conditions discharged; merged b630a901 ANCESTOR-OK). The
discriminating NAME-resolution capability — the novel half limb (b) adds — is LIVE-confirmed
by my own read (zero writes). The one leg I did not personally re-run (the composite WRITE
e2e) is fenced by MANDATE (G-THEATER: ratified write verbs on real tasks are not mine to
fire; sandbox deleted) — an honest fence, cited from the head-bound receipt + operator
witness, not a lazy substitution. Cross-stream concurrence ≥ 2 (my live read + rite-disjoint
V3/V4 + PR #249 CI/tests).

### LIMB (c) — C1 annotation reconciliation + fork-(a) receipt filed — **FLAG-ADVISORY**

| Leg (altitude) | Own-hands receipt | Result |
|---|---|---|
| (a) receipts-exist (uncached, post-fetch) | Dossier ADDENDUM-1 append-only@origin/main (`#247 b0cb45f0` ANCESTOR-OK): `.ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md:856` (ADDENDUM-1), `:872` fork-(a) receipt EXISTS, `:864-891` (§A1.2 C2 no-re-fire receipt — UV-P #4 DISCHARGED-BY-PROBE), `:915-953` (§A1.4 STAGED fork, blank operator-only checkboxes) | FILED, append-only, present |
| (b) discrimination (OWN construction) | Re-verified the staged fork's premise LIVE@origin/main: `src/autom8_asana/api/routes/tasks.py:254` → `"x-fleet-idempotency": {"idempotent": False,...}` and `:534` → `{"idempotent": True,...}` (my own `git show origin/main` read). The SVR the ruling adjudicates is present and matches the filing. | SVR premise LIVE-CONFIRMED |
| (c) user-surface (observed DIRECTLY) | Telos Gate-B rows@origin/main carry real anchors; the K1-a in-tree ancestry receipt is present at telos `:95-101`. Note: the telos cites the receipt "at 53e408ff" — `53e408ff` is a PRE-SQUASH commit (NOT reachable from origin/main; its parent edb72a8e also unreachable); its content landed via squash `b0cb45f0` (ANCESTOR-OK). Faithful squash pattern (adversary chain V5 confirms verbatim). | FILED record present; anchor SHA pre-squash |

**Flag (expected honest rendering):** the fork-(a) receipt is genuinely **FILED** (§A1.2 C2
no-re-fire receipt, append-only, byte-consistent) and the SVR premise is live-verified — BUT
the reconciliation **RULING** is operator-staged (§A1.4 blank checkboxes, "operator's hand
only — sessions never mark this"); the annotation is UNTOUCHED (`tasks.py:254` still reads
idempotent:False). Per G-RUNG I attest the **FILED altitude** and do NOT round up to
"reconciled." The predicate's filing half is receipt-complete; its reconciliation half awaits
the operator's mark (tasks.py:254 fork (a)-flip vs (b′)-keep). FLAG-ADVISORY (not REFUSE —
the receipt is genuinely on the record).

---

## Overall verdict: **FLAG-ADVISORY** (weakest-link)

| Limb | Verdict | Load-bearing basis |
|---|---|---|
| (a) deploy completes + /ready + mid-deploy session | **FLAG-ADVISORY** | Core predicate live-corroborated (deploy completion matched to the second; /ready TGs + grace 2400 + green target healthy live); scoped flag on a contradicted cross-check receipt (startPeriod 300@:659 → actually :659=120, clamp landed :660; substance true) |
| (b) composite invocation by tag NAME e2e | **PASS-ADVISORY** | e2e-by-NAME receipt complete + head-bound (V4 PASS @b98936e7, merged b630a901); NAME-resolution discriminating path live-confirmed by own read; write half fenced (operator-witnessed, cited) |
| (c) C1 reconciliation + fork-(a) receipt filed | **FLAG-ADVISORY** | Fork-(a) receipt FILED (§A1.2) + SVR premise live-verified; reconciliation RULING operator-staged (§A1.4) — FILED altitude attested, never rounded up |

Weakest-link aggregation → **FLAG-ADVISORY**. The wave's substantive predicate is materially
realized and, where live-checkable, corroborated by my own hands. It is NOT clean
PASS-ADVISORY: limb (a) carries a contradicted cross-check receipt and limb (c) is
receipts-FILED with the operator ruling pending. It is NOT REFUSE-ADVISORY: no
shipped/landed/verified/attested claim-token stands with a null receipt — the receipts EXIST
and are largely live-corroborated; the flags are (a) a bounded receipt-accuracy error with
substance-true underneath and (c) an honestly-rendered operator-pending ruling.

## Telos writeback token (never rounded up)

`ari procession writeback-telos` selects verified_realized via grade-licenses-which-token:
**UNATTESTED** (licenses ceiling "merged"), with `last_eunomia_advisory` set to this VERDICT
and `last_eunomia_grade: MODERATE` copied verbatim. This is the honest floor: the
WHOLE-predicate token stays UNATTESTED because limb (c) reconciliation is operator-pending and
limb (a) carries a flagged receipt; the per-limb realization detail (b PASS-ADVISORY, a-core
live-corroborated, c FILED) lives in this advisory. ATTESTED-full is unreachable for a
self-ref verdict by construction; the token is NOT rounded up.

## Corroboration inputs (NOT substitutes for the three legs)

The five inscribed adversary verdicts (`.ledge/reviews/ADVERSARY-VERDICTS-asana-mcp-postfelt-wave-2026-07-20.md`@origin/main)
— V1 a8 #104 PASS-W-C, V2 autom8y #1157 PASS-W-C→PASS, V3/V4 asana #249 PASS-W-C→PASS,
V5 asana #247 CONCUR-W-C — are rite-disjoint INPUTS I read as context. My own three legs
re-derive the evidence independently. One cross-check they carry (V1 COND-2 leg-1: startPeriod
300@:659) is the receipt my discrimination leg contradicted; V1's PASS is not reversed (the
clamp substantively works and is live at :660-:663), but its taskdef anchor is off-by-one.

## Tool receipts

- `ari procession reconcile-telos --charge=<slots.yaml@bc4b0aef> --slug=asana-mcp-postfelt-hardening`
  → **Status OK** (exit 0): SeamRungCeiling=merged, TelosVR=UNATTESTED, LicensedCeiling=merged,
  "seam rung_ceiling is within the licensed ceiling." The charge does not over-claim.
- `ari procession receipts` (ECO-1) on the adversary-verdict chain → REFUSE (exit 4) at line 25:
  `merged 80402fd3` lacks a co-located Gate-C anchor. This is the documented cross-repo-SHA
  limitation (80402fd3 is an a8-repo object, not resolvable against origin/main; charge P-5
  anchors cross-repo SHAs as doc). NOT a fabrication — my receipts-exist legs ancestry-verified
  the satellite SHAs (b630a901/b0cb45f0/33c38f35/2ee3391c/beaf3344/6edc83d5) directly.

## Remaining entropy (not addressed; operator-reserved or deferred)

- **Operator ruling — tasks.py:254 fork** (dossier §A1.4): completes limb (c) reconciliation.
  FLAG-ADVISORY persists until the operator marks fork (a)-flip or (b′)-keep.
- **A3 telos ratification**: status PROPOSED; verification_deadline 2026-08-14 + attester
  amendable at ratification.
- **GATE-PROBE** (repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md), operator-only,
  due 2026-08-03 — NOT touched (hard fence).
- **Receipt-accuracy correction**: the startPeriod=300@:659 claim in the ledger/charge/V1 should
  be corrected to :659=120 / :660=300 in any future amendment (immutable-fact contradiction).
- **Stale-checkout safe-sync** + **dupe PLAY task cleanup**: operator working-tree/Asana hygiene
  (s6 leg-5 recipe).
- **WS-E** (shipped row): still "(planned)" in the telos — shipped stays UNATTESTED-partial.
- Advisory carried from V1: unclamped vendored twin at autom8y
  `terraform/modules/platform/primitives/ecs-fargate-service/main.tf:166` (zero consumers,
  reap candidate).

## Recommendations

1. Surface the startPeriod revision-attribution correction to the wave ledger and V1 discharge
   note (the clamp works — the anchor is off-by-one; do not let the immutable-fact error persist
   as an inherited premise).
2. Operator: rule the tasks.py:254 fork to lift limb (c) FLAG-ADVISORY to receipts-reconciled.
3. Operator: ratify (A3) to firm the deadline/attester and flip status PROPOSED→RATIFIED.
4. On WS-E landing, flip the shipped row and re-run the close-gate.

## Fences approached (none breached)

- **Felt verdict**: NOT spoken. The operator's §5.2 verdict cited verbatim, never paraphrased-as-fact.
- **Asana writes**: ZERO. Limb (b) discrimination was a read-only name-resolution GET (idempotent).
- **Deploy roll**: NONE. PT-04 attested from ledger + live ECS service events; no deploy triggered.
- **GATE-PROBE**: NOT touched (operator-only, due 2026-08-03).
- **Round-up**: refused. merged ≠ applied ≠ protecting-prod held; limb (c) attested at FILED, not reconciled.

## Self-grade

**MODERATE** (ceiling, not floor) per self-ref-evidence-grade-rule: this is a knossos rite
(eunomia) attesting a knossos wave's own records. In-fleet rite-disjointness (eunomia holds
zero authorship in the wave; every leg re-derived with own hands, builders' receipts treated
as CONTEXT never EVIDENCE) lifts this above pure self-attestation but does NOT reach STRONG.
ATTESTED-full is unreachable for this self-ref verdict by construction.

---

## R1 — External-Audit Attestation

```yaml
r1_external_audit_attestation:
  attester_rite: eunomia
  attester_agent: verification-auditor
  target_initiative_slug: asana-mcp-postfelt-hardening
  target_initiative_owner_rite: postfelt-wave (hygiene/sre/10x-dev/docs seats, PT-01 §B grant)
  axiom_1_disjointness_verified: true
  axiom_1_evidence:
    note: "eunomia holds ZERO authorship across the wave's five workstreams; rite synced eunomia 2026-07-20; attester is rite-disjoint by construction (charge G-CRITIC)."
    eunomia_in_roster: false
  axiom_3_credential_scope:
    critic_credential: "eunomia verification-auditor product-altitude ADVISORY at telos-integrity-ref gate-checklist (close-gate/handoff-gate)"
    cumulative_residency_state: "self-ref MODERATE ceiling; in-fleet rite-disjoint; STRONG requires N>=3 non-knossos-monorepo firings (three-evidence-leg-attestation N=5 in-fleet, external N pending)"
  evidence_anchors:
    inception_anchor: ".know/telos/asana-mcp-postfelt-hardening.md inception_anchor (origin/main)"
    shipped_anchors:
      - "src/autom8_asana/api/routes/tags.py:41 (WS-B1 name-resolution route, origin/main)"
      - "src/autom8_asana/api/routes/tasks.py:254 (limb-c SVR: idempotent:False, origin/main)"
      - "src/autom8_asana/api/routes/tasks.py:534 (limb-c SVR: idempotent:True, origin/main)"
    verification_evidence_anchors:
      - "AWS elbv2 describe-target-groups: both asana TGs HealthCheckPath=/ready Matcher=200 (live 2026-07-20)"
      - "AWS ecs describe-services events: deployment ecs-svc/0263950317217302961 completed 2026-07-20T15:44:01Z (live)"
      - "AWS ecs describe-task-definition autom8y-asana-service:659 startPeriod=120 / :660 startPeriod=300 (live)"
      - "GET https://asana.api.autom8y.io/api/v1/tags?name=play_custom_calendar_integration -> 200 gid 1209319457948185 (live read-only)"
  scope_attestation: |
    "This attestation is ADVISORY (non-blocking). Eunomia surfaces the FLAG-ADVISORY to the
    /go dashboard + close-comment + this VERDICT artifact. User-agency preserved: the operator
    adjudicates the tasks.py:254 fork (limb c) and A3 ratification. The dispatching wave has
    NOT self-attested verification-realized; this rite-disjoint check with own-hands live
    AWS + satellite probes satisfies R1 binding. Evidence anchors are EXTERNAL code/live-AWS,
    not eunomia's own DK (dispatcher-critic-degeneracy guard)."
```

## R2 — Receipt-Grammar Attestation

```yaml
r2_receipt_grammar_attestation:
  per_item_receipt_check:
    - item_index: 1
      item_claim_text: "limb (a): a deploy completes + /ready TG health-check + one mid-deploy green session"
      claim_token_class: verified
      receipt_anchor:
        file_line: ".sos/wip/asana-mcp-postfelt-hardening.PT01-activation-ledger.md:225-254"
      code_verbatim_match_verified: true   # + live AWS: deployment ecs-svc/0263950317217302961 completed 15:44:01Z; both TGs /ready matcher 200
      flag: "cross-check receipt startPeriod=300@:659 CONTRADICTED live (:659=120, :660=300); core predicate intact"
    - item_index: 2
      item_claim_text: "limb (b): one composite invocation addressed by tag NAME succeeds e2e"
      claim_token_class: verified
      receipt_anchor:
        eunomia_verdict: ".ledge/reviews/ADVERSARY-VERDICTS-asana-mcp-postfelt-wave-2026-07-20.md V4 (PASS @b98936e7)"
      code_verbatim_match_verified: true   # + live read-only GET name->gid 1209319457948185 on deployed satellite; #249 merged b630a901 ANCESTOR-OK
    - item_index: 3
      item_claim_text: "limb (c): C1 annotation reconciliation + fork-(a) receipt filed on the dossier record"
      claim_token_class: attested
      receipt_anchor:
        file_line: ".ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md:856-964"
      code_verbatim_match_verified: true   # fork-(a) receipt FILED (§A1.2); RULING operator-staged (§A1.4 blank) -> FILED altitude only
      flag: "reconciliation RULING operator-pending; attested at FILED altitude, not reconciled (G-RUNG)"
  cross_stream_concurrence:
    stream_count: 3
    concurring_streams:
      - stream_id: own-hands-live-probes
        verdict_text: "AWS read-only + satellite read-only GET independently corroborate limbs (a)(b) regime + resolution"
        source_artifact: "this VERDICT per-limb tables (live command outputs)"
      - stream_id: rite-disjoint-adversary-chain
        verdict_text: "V1-V5 head-bound PASS/CONCUR, all conditions discharged"
        source_artifact: ".ledge/reviews/ADVERSARY-VERDICTS-asana-mcp-postfelt-wave-2026-07-20.md"
      - stream_id: activation-ledger-receipts
        verdict_text: "PT-04 first /ready-gated deploy receipt; PT-05/06/07 chains"
        source_artifact: ".sos/wip/asana-mcp-postfelt-hardening.PT01-activation-ledger.md"
  aggregate_verdict:
    tier: FLAG-ADVISORY
    rationale: "limb (b) PASS-ADVISORY; limbs (a)+(c) FLAG-ADVISORY (contradicted cross-check receipt on (a); operator-staged reconciliation ruling on (c)). Weakest-link floors to FLAG-ADVISORY. No null receipts -> not REFUSE-ADVISORY."
```
