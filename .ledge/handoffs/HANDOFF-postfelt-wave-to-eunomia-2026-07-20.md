---
artifact_id: HANDOFF-postfelt-wave-to-eunomia-2026-07-20
schema_version: "1.0"
source_rite: postfelt-wave (multi-rite procession — hygiene/sre/10x-dev/docs seats under the PT-01 §B standing grant; dispatcher-coordinated, session b3f74f84)
target_rite: eunomia
handoff_type: validation
priority: critical
blocking: true          # wave closure (telos verified_realized) is blocked on this attest
initiative: asana-mcp-postfelt-hardening
created_at: "2026-07-20T17:58:00Z"
status: pending
response_due: "2026-08-14"   # telos verification_deadline (PROPOSED; operator may amend at A3)
source_artifacts:
  - ".sos/wip/asana-mcp-postfelt-hardening.PT01-activation-ledger.md"   # the wave's receipt authority (local, untracked by design)
  - ".ledge/reviews/ADVERSARY-VERDICTS-asana-mcp-postfelt-wave-2026-07-20.md"
  - ".know/telos/asana-mcp-postfelt-hardening.md"
  - ".know/telos/asana-mcp-v1.md"
  - ".sos/wip/asana-mcp-v1.felt-gate-envelope.md"                       # §5.2 = the operator's verdict, verbatim (local)
  - ".ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md"        # ADDENDUM-1 §A1.4
  - ".know/defer-watch.yaml"
  - ".ledge/handoffs/HANDOFF-wsd-knowledge-governance-to-hygiene-2026-07-19.md"
  - "repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md"   # GATE-PROBE entry (repos repo)
  - ".ledge/handoffs/CHARGE-postfelt-pt09-attest-2026-07-20.md"         # the attestation-plane charge (rendered; disjoint contract)
  - ".ledge/handoffs/CHARGE-postfelt-pt09-attest-2026-07-20.slots.yaml" # machine-readable envelope (reconcile-telos: OK)
provenance:
  - { source: ".know/telos/asana-mcp-postfelt-hardening.md", type: "shape", grade: "strong" }      # operator's verbatim predicate
  - { source: ".ledge/reviews/ADVERSARY-VERDICTS-asana-mcp-postfelt-wave-2026-07-20.md", type: "artifact", grade: "moderate" }
  - { source: ".sos/wip/asana-mcp-postfelt-hardening.PT01-activation-ledger.md", type: "artifact", grade: "moderate" }
evidence_grade: moderate    # self-referential ceiling; this handoff's whole purpose is the external lift
items:
  - id: "PT09-A"
    summary: >-
      Attest limb (a) of the operator's verbatim predicate: "a deploy completes while a
      client session queries continuously and observes ZERO warming errors (TG
      health-check receipt on /ready + one mid-deploy green session)."
    priority: critical
    validation_scope:
      - "Receipts-exist leg (uncached): fetch origin; re-read the PT-04 RECEIPT block in the activation ledger and the SCAR-TG-LIVENESS-001 CURED record on origin/main (.know/scar-tissue.md); confirm the deployment id, timeline, and client-probe lines are present and internally consistent."
      - "Discrimination leg (own construction): live AWS read-only probes — describe-target-groups (both TGs HealthCheckPath=/ready, Matcher 200), describe-services (grace 2400, PRIMARY taskdef :659 COMPLETED), describe-task-definition :659 (healthCheck startPeriod=300, command targets /health); plus the recorded ECS service events for ecs-svc/0263950317217302961 (deployment completed 15:44:01Z after ~29.5 min held-out warming). Do NOT roll a deploy to reproduce — the receipt is historical (G-THEATER)."
      - "User-surface leg: the client probe log inside the PT-04 receipt (two mid-warm authenticated GETs, both 200) + structural corroboration (listener Weight=1 to the serving TG throughout the warm)."
    notes: "COND-2 of the a8 #104 verdict discharged empirically here (startPeriod=300 accepted; WARMING survival ≫390s) — cross-check against verdict V1/V2 in the inscribed chain."
  - id: "PT09-B"
    summary: >-
      Attest limb (b): "one composite invocation addressed by tag NAME succeeds e2e."
    priority: critical
    validation_scope:
      - "Receipts-exist leg: re-read verdict V3/V4 (PASS at b98936e7, all conditions discharged) in the inscribed chain; confirm #249 squash b630a901 is ancestor of origin/main; re-read the PT-05/PLAY-2/PLAY-3 binding receipts at their merged paths (mcp/asana_mcp/tools/tag_resolve.py, composite_write.py TOOL_DESCRIPTION)."
      - "Discrimination leg (own construction, READ-ONLY): a fresh name-resolution GET against the deployed satellite route (/api/v1/tags name query) proving the resolution path live — the SANDBOX IS DELETED (s6) and the ratified write verbs on real tasks are NOT the attester's to fire; resolution-only, zero writes (G-THEATER binding)."
      - "User-surface leg: the cured e2e transcript (scratchpad e2e_transcript.txt referenced in the PR #249 body) — provenance lines (module __file__ + git HEAD b98936e7), the [0b] multi-page bare-list mechanism, and the demonstrated idempotency (2×POST 200, read-back count=1)."
    notes: "The composite invocation receipt is the merged tool chain + the live e2e at the tested head; the LIVE production write half of limb (b) was operator-witnessed at GATE-FELT (envelope §2.3, their record) — cite, never re-fire."
  - id: "PT09-C"
    summary: >-
      Attest limb (c): "C1 annotation reconciliation + fork-(a) receipt filed on the
      dossier record" — at its honest altitude: receipts FILED; the reconciliation
      RULING is operator-staged (§A1.4), completes at their mark.
    priority: critical
    validation_scope:
      - "Receipts-exist leg: dossier ADDENDUM-1 present append-only on origin/main (ratified text byte-identical to its pre-addendum state — re-verify per PT-07's K5 method); the C2 no-re-fire receipt filed (UV-P #4 DISCHARGED-BY-PROBE); §A1.4 carries the STAGED tasks.py:254 fork with the operator-only marker."
      - "Discrimination leg: re-verify the staged fork's premise live — src/autom8_asana/api/routes/tasks.py:254 still carries idempotent:False and :534 idempotent:True on origin/main (the SVR the ruling adjudicates)."
      - "User-surface leg: the telos Gate-B rows + attestation comments (single-writer K1-a ancestry receipt in-tree at 53e408ff) — attest the FILED altitude explicitly; G-RUNG forbids rounding up to reconciled."
    notes: "FLAG-ADVISORY (not REFUSE) is the expected honest rendering for this limb while the operator ruling is pending — the predicate's filing half is receipt-complete."
  - id: "PT09-D"
    summary: >-
      Attest wave integrity + mint the telos writeback: the five-verdict chain, the
      discharge receipts, rung honesty (incl. the owned false-green correction), and
      the HALT-list-never-bitten claim — then reconcile the telos attestation_status
      from your VERDICT via the validated write path.
    priority: high
    validation_scope:
      - "Spot-verify the inscribed verdict chain (V1–V5) against `ari procession receipts` on the artifacts you touch (the ECO-1 gate probe: every realized-state token requires a co-located substrate-verified anchor)."
      - "Run `ari procession reconcile-telos --charge=.ledge/handoffs/CHARGE-postfelt-pt09-attest-2026-07-20.slots.yaml --slug=asana-mcp-postfelt-hardening` — expect Status OK (pre-verified at handoff time: SeamRungCeiling merged ≤ LicensedCeiling merged for TelosVR UNATTESTED)."
      - "Render your per-limb + overall verdict (PASS-ADVISORY / FLAG-ADVISORY / REFUSE-ADVISORY), report to .ledge/reviews/, then `ari procession writeback-telos` from your VERDICT artifact — the token selection follows grade-licenses-which-token and is NEVER rounded up (ATTESTED-full is unreachable for a self-ref verdict by design); land the report + telos writeback via one docs PR."
    notes: "Your own report self-grades MODERATE (self-ref-evidence-grade-rule). Preloads per the dispatch map: three-evidence-leg-attestation, self-ref-evidence-grade-rule, telos-integrity-ref."
---

# HANDOFF — postfelt wave → eunomia (PT-09 three-limb receipts-only attest)

> The work-transfer plane of the /cross-rite-handoff seam. The ATTESTATION plane — the
> six-gate anti-lie charge — is the disjoint sibling artifact
> `CHARGE-postfelt-pt09-attest-2026-07-20.md` (emitter-rendered, G-HALT-clean) with its
> machine-readable envelope `…slots.yaml` (reconcile-telos: **Status OK** at handoff
> time). Paste the rendered charge as the dispatch text for the verification-auditor.

## 1. What crosses this seam

The asana-mcp-postfelt-hardening wave is COMPLETE through PT-08: all five workstreams
merged, the fleet's first fail-closed /ready deploy regime live and receipted on a real
deploy (PT-04), tags addressable by NAME with a live e2e receipt, knowledge/governance
reconciled by a single writer, five head-bound adversary verdicts inscribed with every
condition discharged, the s6 sweep verified two-sidedly clean (PT-08 CONCUR, zero
discrepancies). The repo rite is synced to eunomia (`ari rite current` receipt taken
2026-07-20). What remains is the LAST delegable act — this attest — and the operator's
own reserved rulings.

**The predicate under attest is the operator's, verbatim** (telos
`verified_realized_definition.user_visible_evidence`, carried unamended):

> (a) a deploy completes while a client session queries continuously and observes ZERO
> warming errors (TG health-check receipt on /ready + one mid-deploy green session)
> (b) one composite invocation addressed by tag NAME succeeds e2e
> (c) C1 annotation reconciliation + fork-(a) receipt filed on the dossier record

**The attester's binding is the telos's, verbatim**: eunomia verification-auditor,
rite-disjoint ADVISORY over receipts, R1 binding — *"Felt/witness observations inside
the predicate remain the operator's own; eunomia attests receipt integrity, never a
felt outcome."*

## 2. Receipt map (where each limb's evidence lives)

| Limb | Primary receipts | Merge anchors (satellite-resident, ancestry-verified 9/9 on 2026-07-20) |
|---|---|---|
| (a) | Activation ledger §PT-04 RECEIPT (timeline, held-out warming ~29.5 min, client 200-only probes, COND-2 discharge); scar-tissue SCAR-TG-LIVENESS-001 CURED record; live AWS state (TGs /ready, grace 2400, taskdef :659) | satellite #248 `6edc83d5`; fleet chain doc-anchored (autom8y #1157 `d502398d`, #1154 `e8079654`, a8 #104 `80402fd3` — cross-repo, see verdicts V1/V2); apply run 29753896034 |
| (b) | Verdicts V3/V4; #249 merged tool chain (dual-key, PT-05 bindings, PLAY-2 warning, PLAY-3 read-back); cured e2e transcript w/ provenance; #246 satellite route | `b630a901` (#249), `2ee3391c` (#246), `beaf3344` (#242 assembly) |
| (c) | Dossier ADDENDUM-1 (append-only; C2 receipt; §A1.4 STAGED operator fork); telos Gate-B rows + K1-a in-tree receipt | `b0cb45f0` (#247), `53e408ff` (single-writer micro-pass) |
| chain | ADVERSARY-VERDICTS file (V1–V5 + chain-summary table + discharge receipts) | `33c38f35` (#251) |

Ground-truth discipline (G-PREMISE): **fetch first; read origin/main** — the operator's
local main ref is frozen pre-epic at `f3d8eec1` (3rd-strike stale-checkout hazard;
safe-sync recipe in the s6 report, queued to the operator).

## 3. Fences (identical to the charge's hard gates — the short form)

1. **Never a felt verdict.** GATE-FELT was closed by the OPERATOR (envelope §5.2 —
   cite verbatim, never paraphrase-as-fact). GATE-PROBE is operator-only, due
   2026-08-03.
2. **Zero writes to Asana.** The sandbox apparatus is deleted; limb-(b) discrimination
   is read-only name-resolution. Any write → STOP + surface.
3. **Never round up.** Push-triggered fleet terraform runs are PLAN-ONLY; limb (c) is
   FILED-not-reconciled; merged ≠ applied ≠ protecting-prod; your report caps MODERATE.
4. **Do not roll a deploy** to reproduce PT-04 — the receipt is historical; live reads
   + recorded events are the discrimination substrate.

## 4. Open operator items (carried, not yours)

| Item | Where | Effect |
|---|---|---|
| tasks.py:254 fork ruling ((a) flip vs (b′) keep-with-caveat) | dossier ADDENDUM-1 §A1.4 | completes limb (c) reconciliation |
| A3 ratification of the PROPOSED telos | .know/telos/asana-mcp-postfelt-hardening.md | deadline/attester amendable |
| GATE-PROBE COMMIT/PARK/KILL | repos/.ledge/decisions/PROBE-fleet-mcp-second-leg-2026-07-20.md | due 2026-08-03 |
| Stale-checkout safe-sync + dupe PLAY task cleanup | s6 report leg-5 recipe; operator's Asana routing | working-tree + workspace hygiene |

## 5. Dispatch (operator: run after restarting Claude Code in this repo)

The rite is already synced (`Active Rite: eunomia`). After restart, paste:

```
Task(verification-auditor): Execute the PT-09 attest per
.ledge/handoffs/HANDOFF-postfelt-wave-to-eunomia-2026-07-20.md and its charge
.ledge/handoffs/CHARGE-postfelt-pt09-attest-2026-07-20.md — three-limb
receipts-only attestation of asana-mcp-postfelt-hardening, per-limb three
evidence legs, ADVISORY verdicts, telos writeback via
`ari procession writeback-telos`, report to .ledge/reviews/. Preload
three-evidence-leg-attestation + self-ref-evidence-grade-rule +
telos-integrity-ref. Fences: no felt language, no Asana writes, no GATE-PROBE.
```

## 6. Handoff integrity notes

- This artifact + both charge files ride one docs PR; anchors above are valid at its
  merge. The activation ledger and felt-gate envelope are deliberately session-local
  (.sos/wip — the receipt surfaces the attester reads on this machine).
- reconcile-telos pre-flight at handoff time: **Status OK** (SeamRungCeiling merged =
  LicensedCeiling for TelosVR UNATTESTED). The charge does not over-claim; the
  ladder-position receipts live in the non-load-bearing rung_detail per the
  token-authoritative contract.
- Authored by the dispatching session (self-ref, MODERATE ceiling throughout); the
  five inscribed verdicts are rite-disjoint at claim level; the lift beyond MODERATE
  is exactly what this handoff requests.
