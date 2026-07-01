---
type: telos
initiative_slug: gfr
authored_at: 2026-06-25T00:00:00Z
authored_by: main-thread (Claude) at OPERATOR DIRECTION — drafted for ratification; user-sovereign per telos-integrity-ref §3 Gate-A
ratified_by: operator (Tom Tenuta) — countersigned 2026-06-25
rite: 10x-dev
schema_version: 1
code_truth_anchor: HEAD f4f924d2 (chore(deps): bump autom8y-core to 4.6.0)
ratification_status: RATIFIED 2026-06-25 (operator countersign; three [OPERATOR-SET] fields approved as-drafted)
---

# Telos Declaration — gfr (GID Field Resolver)

> **RATIFIED 2026-06-25** — operator (Tom Tenuta) countersigned. Drafted by the
> main thread at operator direction; user-sovereign per telos-integrity-ref §3
> Gate-A and now ratified. The three **[OPERATOR-SET]** fields
> (`verification_deadline` = 2026-07-16, `user_visible_surface` wording,
> `rite_disjoint_attester` = review-rite critic) were **approved as-drafted**.
> Amendable at any `/frame`. Gate-A (NOTE-5) is hereby CLOSED.

```yaml
telos:
  initiative_slug: gfr

  inception_anchor:
    framed_at: "2026-06-25"
    frame_artifact: ".sos/wip/frames/gfr.md"  # the envelope frame (myron); shaped at .sos/wip/frames/gfr.shape.md (pythia); brief at .ledge/specs/gfr-alignment-brief.md (status: accepted)
    why_this_initiative_exists: >
      Any fleet caller must resolve a gid to schema-declared fields BY NAME with
      entity-tree topology fully hidden — and the unbuilt send-origination path
      needs gid -> company_id (== chiropractors.guid) to mint the
      {guid}@appointments.contenteapp.com routing address for the CORRECT tenant.
      No GID->guid resolver exists today (the parked "workstream-D"); without it,
      a phone-collision / stale-key / wrong-rep-input mints a format-valid,
      WRONG-CLINIC address -> cross-tenant PHI leak. This initiative is that
      resolver, proven first by the dogfood that closes that leak.

  shipped_definition:
    code_or_artifact_landed: []  # MISSING — nothing landed; populated by sprint-A/BD/C/F PRs (asana engine) and sprint-E (autom8y-core client, separate repo, PROPOSE-only)
    user_visible_surface: >
      [OPERATOR-SET — draft wording, blessed-as-is until you amend]
      A gid-first read facade — resolve(gid, fields) -> values — callable by any
      fleet consumer, returning schema-declared fields by name with provenance,
      never exposing whether the gid is a Business/Unit/Offer/Contact or how the
      tree was traversed. The first user-visible surface is a correctly-tenanted
      {guid}@appointments.contenteapp.com address minted FROM a gid.

  verified_realized_definition:
    user_visible_evidence:
      # The realization predicate, carried verbatim from the frame. This is the telos, not "resolver merged" / "PRs green".
      - "POSITIVE round-trip: an Offer gid -> resolve(gid, [company_id]) returns the chiropractors.guid (cached Company-ID copy by default, data-service-verified on demand via existing asana<->data-service hooks), and the minted {guid}@appointments.contenteapp.com address round-trips through the office-resolution path (_resolve_office_phone, automation/workflows/conversation_audit/workflow.py:547) to the CORRECT tenant — asserted by a LIVE/integration test on tenant identity."
      - "NEGATIVE cross-tenant guard: a DIFFERENT tenant's gid never resolves to THIS tenant's address; the format-valid-but-wrong-clinic failure mode is asserted-closed by a cross-tenant negative test (the PHI-leak guard, distinct from the host-spoof already closed)."
      - "Contract honesty under miss: strict all-or-nothing holds — an unknown/never-warmed-empty field fails with structured UnresolvedError(fields=[...]), never a silent wrong value; stale-but-present counts as resolved with status:'stale' + async refresh."
      - "Topology hidden: the caller passes only (gid, field-names) — no entity-type, no join-path, no S3-frame knowledge — and the same call shape serves an Offer gid (scalar) and a Business gid (row-set), proving the facade hid the fan-out."
    verification_method: in-anger-dogfood
    verification_deadline: "2026-07-16"  # [OPERATOR-SET] proposed placeholder (~3wk from framing); drives Naxos TELOS_OVERDUE — set the real bound
    rite_disjoint_attester: "review-rite external critic (rite-disjoint from the 10x-dev author per §2 R1; PT-05 telos gate in gfr.shape.md). [OPERATOR-SET] — confirm review-rite vs. eunomia/verification-auditor as the binding attester."

  attestation_status:
    inception: INSCRIBED      # declaration exists; operator countersign converts DRAFT -> ratified
    shipped: MISSING          # nothing landed
    verified_realized: UNATTESTED
    last_eunomia_advisory: null

  receipt_grammar:
    per_item_file_line_anchors:
      # Reuse substrate (the ~80% that exists) + the real dogfood caller. Carried from the frame; NOT first-party re-fired line-by-line this pass (see code_verbatim_match).
      - "src/autom8_asana/query/{models,engine,compiler}.py"          # query DSL — FROZEN P1-C-04, build ON TOP
      - "src/autom8_asana/core/entity_registry.py"                    # join_keys, get_join_key, default_projection
      - "src/autom8_asana/dataframes/models/{schema,registry}.py"     # open-by-declaration field vocabulary
      - "src/autom8_asana/models/business/hydration.py"               # gid -> tree type-detect + up-traversal
      - "src/autom8_asana/services/{universal_strategy,dynamic_index,gid_lookup}.py"  # reverse-direction prior art (OUT OF SCOPE here)
      - "automation/workflows/conversation_audit/workflow.py:547"     # _resolve_office_phone — the REAL send-origination caller (NOTE-3)
    cross_stream_concurrence: false   # set true only at verified_realized=ATTESTED (positive + negative test corroborated by the rite-disjoint attester)
    code_verbatim_match: false        # honest: substrate anchors carried from frame/swarm, not re-fired git-show this pass; sprint-0 architect re-verifies at dispatch
```

## Realization predicate (the one line that gates close)

> An **Offer gid** resolves **`company_id` (== `chiropractors.guid`)**, AND the minted
> **`{guid}@appointments.contenteapp.com`** address round-trips through the office-resolution
> path to the **CORRECT tenant**, asserted by a **live/integration test on tenant identity**
> — plus a **cross-tenant negative test** proving a different tenant's gid never mints this
> tenant's address. **NOT** "resolver merged", **NOT** "PRs green".

This predicate is carried into **every** sprint's exit criteria per `gfr.shape.md`, and is the
sole content of the **PT-05 telos gate**. Sprint-F (send-origination dogfood) is the telos proof,
not an afterthought.

## Risk map (carried — these are what "verified-realized" defends against)

| Risk | Why it threatens the telos | Where addressed |
|---|---|---|
| **Cross-tenant correctness** | Format-valid ≠ correct-for-this-clinic; a wrong guid mints a wrong-tenant address → PHI leak / misrouted bookings | NEGATIVE test in the predicate; sprint-F; PT-05 |
| **Cold-frame latency (0.5–120s)** | A cold miss must not block or lie; serve-stale-if-any + async rebuild, error only on truly-empty | sprint-C runtime posture; PT-04 |
| **company_id staleness** | Local cached Company-ID copy can drift from data-service truth | tiered truth-source (sprint-BD/D), verify-on-demand via existing hooks; provenance `as_of` |

## Defer registry (OUT OF SCOPE — resist scope-creep)

| Deferred | Already exists as | Status |
|---|---|---|
| Reverse resolution (fields → gid) | `DynamicIndex` / `universal_strategy` | OUT OF SCOPE |
| Writes / write-back | `FieldResolver` | OUT OF SCOPE |
| Bespoke query optimizer | Polars + existing compiler pushdown | OUT OF SCOPE |

## Carried flags (frame + shape SVR/UV-P notes the operator should know)

- **DRIFT-1** — scar-test cluster is **42 markers / 12 files** at HEAD, not the 35 in the brief/`.know`. Constraint unchanged; `.know` refresh advised.
- **NOTE-3 (confirmed)** — the real caller is workflow-private **`_resolve_office_phone`** (`workflow.py:547`), shape ContactHolder→parent-Business→office_phone — a real seam vs. the gid-at-Offer POC scoping; sprint-0 architect reconciles.
- **NOTE-4 (confirmed)** — the `{guid}@appointments` **minting surface is UNBUILT** and not co-located in this checkout (likely the peer send-origination repo); sprint-0 confirms its home before F can prove the round-trip.
- **R-5 (UV-P)** — **`autom8y-core` is not co-located** in `/Users/tomtenuta/Code/a8/repos/` at HEAD; sprint-E (PROPOSE-only, non-blocking for the telos) has a checkout entry-criterion.
- **NOTE-5 (this file)** — resolves the absent-`.know/telos/gfr.md` Gate-A gap; **ratified only on operator countersign**.

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-build declaration; `self_ref_cap: MODERATE` per
`self-ref-evidence-grade-rule`. Code anchors carried from the frame/swarm (not first-party
re-fired this pass — `code_verbatim_match: false`); realization attestation belongs to the
rite-disjoint attester at PT-05 close, not to the author.
