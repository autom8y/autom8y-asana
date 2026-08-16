---
type: telos
initiative: chain-of-custody-closure
status: INSCRIBED (inception) — verification_deadline PROPOSED (UV-P-CoC-2)
created: 2026-08-13
inscribed_by: >
  main thread, per RULING-operator-coc-defaults-ratification-2026-08-13 Q-1
  ("defaults stand", 2026-08-13) — the wave's first paper act. The telos block
  below is transplanted VERBATIM from the frame's §2.2 (authored by myron under
  the operator's /frame charge, which supplied the mission and predicate in the
  operator's own words). The single derived field — verification_deadline
  2026-09-12 — stands PROPOSED, not operator-ruled (UV-P-CoC-2 open; derivation
  at frame §2.1).
source: .sos/wip/frames/chain-of-custody-closure.md §2.2 (transplanted verbatim)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
frame: .sos/wip/frames/chain-of-custody-closure.md
shape: .sos/wip/frames/chain-of-custody-closure.shape.md
landing: >
  LANDED on origin/main, 2026-08-14. CORRECTED 2026-08-14 by the eunomia
  verification-auditor seat: the prior text ("in-tree, UN-MERGED — Q-4 HALT
  governs") is SUPERSEDED and was stale at the time this file was last written.
  Q-4/F-4 was lifted by R-5 (full scoped lift) and the landing wave executed:
  CC-7 cfecbb5a, CC-5 43d766f6, CC-1 8301ee09, paper lineage 2ea46474, wave close
  c71c5c87 — all merged, all producer-deploy-dispatched. Re-verified own-hands at
  attest time: the ECS PRIMARY deployment of autom8y-asana-service runs task-def
  :776 with image tag `c71c5c8`, i.e. the merged head c71c5c87 is the LIVE image
  (VERDICT-limb-a-phase4-attest-2026-08-14.md §4). DEPLOY-DISPATCHED remains the
  ceiling for anything the attester did not probe directly.
---

# Telos — chain-of-custody-closure (inscribed 2026-08-13)

**Gate A closed by inscription.** The sovereign declaration is the operator's
dispatch charge, transcribed verbatim by the frame; this file is its durable
home per the ratified Q-1 default.

```yaml
telos:
  initiative_slug: chain-of-custody-closure
  inception_anchor:
    framed_at: "2026-08-13"
    frame_artifact: ".sos/wip/frames/chain-of-custody-closure.md:1"
    why_this_initiative_exists: >-
      (operator's charge, verbatim) The trust machine's own chain of custody
      holds under attack — its swap-detector detects swaps, its write door
      checks permission not merely identity, its warm path feeds what it
      claims to serve, and its secret-leak class cannot recur.
  shipped_definition:
    code_or_artifact_landed:
      # POPULATED AT CLOSE 2026-08-14 (landing wave, R-5..R-8; origin/main c71c5c87). Per-item, per-workstream:
      - "WS-A (swap detector, CC-1 @ merge 8301ee09): src/autom8_asana/observability/payload_hash.py:1 + src/autom8_asana/observability/rung_receipts/join.py:1 + src/autom8_asana/observability/rung_receipts/schema.py:1 + tests/unit/test_swap_detector_closure.py:1 (two-sided teeth; N1/N2 narrowings pinned)"
      - "WS-B (RE-2 receipt at honest rung): .ledge/reviews/DOSSIER-sec002-re2-grant-chain-2026-08-14.md:1 (STRUCTURALLY-VERIFIED chain trace; HIGH stands) + .ledge/decisions/RULINGS-coc-phase2-operator-sitting-2026-08-14.md:40 (R-7: (f)+(a) remediation RATIFIED, named owners — the 'ratified design with a named owner' rung per evidence-item (ii); enforcement build deliberately NOT claimed)"
      - "WS-C (warm-path repair, CC-5 @ merge 43d766f6): src/autom8_asana/lambda_handlers/story_warmer.py:1 (O-A priority-first Tier-1 offers warm + per-entity receipts) + tests/unit/lambda_handlers/test_story_warm_priority_offer.py:1"
      - "WS-D (biting secret-scan gate, CC-7 @ merge cfecbb5a): .github/workflows/gitleaks-enforcing.yml:1 + .gitleaksignore:1 (49 fingerprints) + branch-protection registration executed 2026-08-14T09:12Z (n==10, 'Secrets Scan (enforcing)' app-pinned 15368) + two-sided bite receipt (.ledge/decisions/RECORD-coc-landing-2026-08-14.md:43)"
    user_visible_surface: >-
      The operator (and any exec reader downstream of the parent initiative)
      can trust the readout chain end-to-end: a delivered payload provably IS
      the generated one — a swap is caught by the instrument, not by a human;
      an Asana write requires a grant, not merely a fleet badge — or its
      absence is a ratified, owned design; a section-timelines caller is fed
      observed data or told honestly that it is imputed; a leaked secret
      fails CI red instead of scrolling past.
  verified_realized_definition:
    user_visible_evidence:
      - "(i) two-sided limb-(a) demonstration: a count-preserving payload swap classified NOT_OBSERVABLE AND an honest delivery classified OBSERVABLE, with the join's module contract matching its implementation — no over-claiming docstring survives"
      - "(ii) an RE-2 receipt at whatever rung the evidence honestly reaches: an enforced deny-on-missing-grant in harness, OR a ratified design with a named owner — the two rungs never conflated (ADR-007 axis discipline)"
      - "(iii) a gate proven BITING by canary, red-then-green — precedence: the RUF100 drift-guard canary (RED run 28530472880 → GREEN run 28530879958)"
    verification_method: cross-stream-corroboration
    verification_deadline: "2026-09-12"  # PROPOSED, not operator-ruled — UV-P-CoC-2; derivation at §2.1
    rite_disjoint_attester: >-
      eunomia verification-auditor (rite-disjoint, co-seated per precedent)
      for the mechanism receipts (i)/(iii); the RE-2 rung call, the rotation
      act, and the RE-1 ownership ruling are OPERATOR-ONLY. NOTE: the parent
      initiative's limb-(a) Phase-4 attestation is a SEPARATE act — eunomia's
      to give, BLOCKED until WS-A lands both halves (sre handoff §4a) — and
      it grades the parent ladder, never this telos (§2.4).
  attestation_status:
    inception: INSCRIBED  # this frame §2.2; .know/telos/ inscription pending operator act (Next Commands #1)
    shipped: LANDED  # 2026-08-14 landing wave (R-5..R-8): all four WS classes merged+deploy-dispatched; per-item anchors above; GATE-coc-pt05 PASS-WITH-CARRIES
    verified_realized: ATTESTED (items (i)+(iii) mechanism-attested; item (ii) discharged-by-ruling)  # LINEAGE PRESERVED. 2026-08-14, eunomia verification-auditor (rite-disjoint, co-seated): ATTESTED on items (i) and (iii) ONLY, and ONLY on evidence that attester re-derived own-hands: (i) two-sided swap-detector demonstration — count-preserving swap -> NOT_OBSERVABLE/content_hash_mismatch, honest delivery -> OBSERVABLE, module contract ruled MATCHING its implementation (no over-claiming docstring survives); (iii) gate proven BITING red-then-green by that attester’s OWN synthetic canary (RED failure + mergeStateStatus BLOCKED at 665d459f, PR #374 retired unmerged and branch deleted; GREEN success re-observed at c71c5c87 and f1dd14e7). The prior FLAG on item (ii) is now DISCHARGED-BY-RULING, 2026-08-16: conjunct A (ratified design) was satisfied by R-7; conjunct B (named owner) is satisfied by RULING-cc8-item2-owner-2026-08-14.md:12-14, which names platform-team as owner-of-record with the operator (tomtenuta) as approver-of-record — a REAL, existent seat, exactly the remedy VERDICT-cc8-partial-attest-2026-08-14.md:333-336 specified. Item (ii) is reached at the LOWER of its two permitted rungs (ratified design with a named owner), NEVER at the enforcement rung — the two rungs stay unconflated per ADR-007 axis discipline. The (ii) rung call, the F-2 rotation act and RE-1 ownership remain OPERATOR-ONLY; eunomia recorded a ruled discharge and did not re-judge it. NO-CRITIC DISCLOSURE PERSISTS: CC-8’s ratified critic (compliance-architect/security) was NOT seated for the 2026-08-14 attest and was re-confirmed UNSEATED at the 2026-08-16 recording (own roster receipt) — the completeness of both sweeps is a single-seat assertion at MODERATE. See VERDICT-cc8-partial-attest-2026-08-14.md §6 and VERDICT-limb-a-reattest-live-realized-2026-08-16.md §6/§9.
    last_eunomia_advisory: ".ledge/reviews/VERDICT-limb-a-reattest-live-realized-2026-08-16.md:1"  # 2026-08-16 eunomia verification-auditor touch. SCOPE: ONLY §6 of that artifact bears on THIS telos (the CC-8 item-(ii) un-flag recording). Its claim 1 (RE-ATTEST-LIVE-REALIZED) grades the PARENT exec-insight-delivery ladder and is NOT citable here — the two claims are declared DISJOINT in that artifact’s §0, and the non-substitution fence below (closing paragraph) binds in both directions. Prior advisory: VERDICT-cc8-partial-attest-2026-08-14.md:1 (FLAG-ADVISORY, product-altitude, non-blocking), whose NO-CRITIC DISCLOSURE is carried forward verbatim and still holds.
  receipt_grammar:
    per_item_file_line_anchors:
      - "inception: .sos/wip/frames/chain-of-custody-closure.md §1 (mission verbatim) + §8 SVR-1..SVR-7"
      - "shipped: per-item anchors in code_or_artifact_landed above (2026-08-14, origin/main c71c5c87); corroborated by 3 rite-disjoint pre-merge NCSRs (.ledge/reviews/REVIEW-pr368/369/365-*-premerge-2026-08-14.md, all GO-WITH-CONDITIONS)"
      - "verified_realized item (i): src/autom8_asana/observability/rung_receipts/join.py:98 (clause-4a swap detection) + :126 (clause-4b, distinct reason) + :32 (the docstring that discloses its own clause-3 over-claim) + tests/unit/test_swap_detector_closure.py:184 (TestClause4aResidual — the residual is pinned, not swept). Re-derived own-hands 2026-08-14 in a clean worktree at the pin: 101/101 uncached; auditor-authored two-sided fixture. VERDICT-cc8-partial-attest-2026-08-14.md §3"
      - "verified_realized item (iii): .github/workflows/gitleaks-enforcing.yml:51 (the job name IS the registered context) + :106 (--exit-code 1, no swallow) + :39,:41 (branches: [main] — the coverage boundary) + :61 (fetch-depth: 0) + .gitleaksignore (49 fingerprint lines, own-count). Re-derived own-hands 2026-08-14: branch protection read live (n==10, app 15368, strict+enforce_admins+linear); RED = auditor's OWN synthetic canary PR #374, Secrets Scan (enforcing) FAILURE @15:33:57Z + mergeStateStatus BLOCKED, retired unmerged + branch deleted; GREEN = SUCCESS re-observed at c71c5c87 (13:58:26Z) and f1dd14e7 (15:27:35Z). VERDICT-cc8-partial-attest-2026-08-14.md §4-§5"
      - "verified_realized item (ii): DISCHARGED-BY-RULING 2026-08-16 (recording act; the rung call itself remains OPERATOR-ONLY). Delegating authority: .ledge/decisions/RULING-cc8-item2-owner-2026-08-14.md:18 — 'the un-flag is eunomia’s to record at its next touch, citing this ruling'. Owner/approver of record: RULING-cc8-item2-owner-2026-08-14.md:12-14 — platform-team as owner-of-record, the operator (tomtenuta) as approver-of-record, 'a REAL seat rather than the never-materialized security bench the attest correctly refused to accept'. This satisfies conjunct B ('a named owner'), which VERDICT-cc8-partial-attest-2026-08-14.md:291-310 found unsatisfied and whose remedy it specified at :333-336; conjunct A (ratified design) was already satisfied by R-7 at RULINGS-coc-phase2-operator-sitting-2026-08-14.md:40. SUPERSEDES the prior FLAG entry, which cited RULINGS-coc-phase2-operator-sitting-2026-08-14.md:44-46 (the never-materialized security bench) — that text is unchanged and still true; it is simply no longer the operative owner record. F-2 cred-t21 rotation is NOT discharged by this act (RULING-cc8-item2-owner-2026-08-14.md:20-22 — SCHEDULED on an operator-sovereign clock; the 'history clean' claim remains gated on that rotation alone). Recorded by eunomia verification-auditor, rite-disjoint, co-seated: VERDICT-limb-a-reattest-live-realized-2026-08-16.md §6"
      - "R-CC7-1 CARRY (binding on every citation of the green gate above): the gate proves 'no unbaselined finding', NEVER 'history clean'. 49 = total baseline fingerprint lines (re-derived own-hands); 31 = the live-at-HEAD masked subset (NOT re-derived by the attester; parallel triage dispatch owns it). The two quantities are never interchangeable"
    cross_stream_concurrence: true  # 2026-08-14: set ONLY on the attester's OWN-HANDS corroboration — stream 1 = own uncached suite (101/101) + own two-sided fixture against the real modules in a clean worktree at the pin; stream 2 = own live-platform probes (branch protection, check-runs on RED/GREEN heads, ECS PRIMARY image tag, CloudWatch receipt counts). NOT set on the strength of the three rite-disjoint pre-merge NCSRs, which this seat did not re-run. Anchors: VERDICT-cc8-partial-attest-2026-08-14.md §9 (stream_count: 2).
    code_verbatim_match: true  # shipped anchors verified against origin/main c71c5c87 at close (merge SHAs 8301ee09/43d766f6/cfecbb5a); MODERATE self-cap — not a substitute for eunomia's verified_realized pass
```

**Non-substitution fence (frame §2.4, binding):** an attestation against THIS
telos attests instrument integrity only. It never writes into the parent
telos's `attestation_status`, and no attestation of this telos may be cited as
evidence for Rung E limb (a) or any parent rung. The parent's limb-(a) Phase-4
attestation is eunomia's to give and is BLOCKED until WS-A lands both halves.
