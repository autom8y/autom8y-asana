---
type: review
subtype: adversary-report
status: complete
iteration: 2-delta
verdict: PASS-WITH-CONDITIONS
adversary_disposition: CONCUR-WITH-FLAGS
ready_for_downstream: true
target_artifact: autom8y-asana/.ledge/decisions/DECISION-asana-mcp-v1-rulings-B1-B5-W5.md
target_sha256_pre_amendment: "6824581b906565e24f1acd89f71d84c7da45dfd5ed7ad557f2839902f15bff25"
target_sha256_amended: "ff1a25b7cade3ec80a407fc6dffc68c80aac00f1f16814f03b274a24be289014"
prior_report: autom8y-asana/.ledge/reviews/ADVERSARY-REPORT-asana-mcp-v1-rulings-2026-07-17.md
critic: arch-adversary (rite-disjoint co-seat inv-20260717-1278d7961503; arch critiques, rnd authored)
initiative: asana-mcp-v1
session: session-20260717-181924-9924bb32
date: 2026-07-17
iter: 2
delta_scope_attested: true    # DELTA-ONLY per critique-iteration-protocol §4; v1-passed surface NOT re-opened
tl_a_status: PASS             # the iter-1 contradicted claim is corrected and the contradiction carried with receipts
tl_b_status: PASS             # A15-A28 spot-checks verified verbatim; two git-layer receipts method-limited (noted, non-load-bearing)
tl_c_status: PASS             # dispositions complete; two new flags recorded below, neither clause-violating
evidence_grade_ceiling: MODERATE   # self-ref cap on this critic's judgments; mechanical re-probes are receipts
challenges_raised:
  - id: ND-1
    taxonomy_id: AC-03
    tl_clause: B
    severity: ADVISORY
    target_element: "frontmatter amendment_log scope + §9.5 deviation note (2) vs §10 W-5 summary cell"
    rationale: "amendment change-manifest under-declares the §10 W-5 summary-cell edit"
    falsification_pathway: "add §10 to amendment_log scope + declare the W-5 cell edit alongside the B3 cell"
    remediation_hint: "one-line manifest correction; checkboxes are pristine, no substantive defect"
  - id: ND-2
    taxonomy_id: AC-01
    tl_clause: C
    severity: FLAG
    target_element: "B3ii-O2 re-weight paragraph x W-5 credential-authority-breadth paragraph"
    rationale: "revision-interaction residual stated piecewise, never compounded for the ratifier"
    falsification_pathway: "one compounding sentence citing the 1800s SA token TTL bound (token_service.py:739), or operator waiver at GATE-BW"
    remediation_hint: "gates nothing; rides to the operator's GATE-BW reading"
arch_ref_citations:
  - "AV:SRC-001 (Messick 1989 — construct validity; each finding names the element attacked)"
  - "AQ:SRC-010 (Cohen 1960 — rite-disjoint second rater; this delta is the disjoint leg re-run)"
  - "AQ:SRC-006 (Kane 2006 — argument-based validity; discharge verified per-condition, not wholesale)"
charter_precedence_held: "charter GOVERNS; W-1..W-4, E-kills, ratified text NOT re-litigated"
---

# ADVERSARY-REPORT — asana-mcp-v1 rulings dossier, iter 2 DELTA (post-AMENDMENT-1)

## VERDICT: PASS-WITH-CONDITIONS (maps to CONCUR-WITH-FLAGS — the gate CLEARS)

All six iteration-1 conditions stand CONFIRMED-DISCHARGED; every load-bearing discharge
receipt this critic could re-execute was re-verified verbatim against live files this
session. AMENDMENT-1 introduced NO blocking defect: the §10 ratification block is pristine
(12/12 checkboxes unchecked, signature blank), the single declared recommendation change
(B3ii) is evidence-demanded and internally consistent with old text preserved
struck-through, and no receipt fabrication was detected across nine independently
re-probed A15–A28 anchors. Two NEW findings fired — one ADVISORY (amendment
change-manifest under-declaration), one FLAG (an un-compounded residual interaction
between the B3ii revision and the C5 residual). Per the two-iteration cap, these flags do
NOT re-open remediation and CANNOT trigger a third critique; they ride to the operator's
GATE-BW reading as part of the residual list in §4. The REMEDIATED dossier is sound for
operator ratification. The operator remains the sole ratifier; nothing here is a felt
verdict.

## 1. Per-condition discharge verification (each independently re-verified)

| Cond | Iter-1 sev | Delta finding | Evidence re-verified by THIS critic |
|---|---|---|---|
| **C1** | BLOCKING | **CONFIRMED-DISCHARGED (fork b — carry + gate)** | tasks.py:254 `"x-fleet-idempotency": {"idempotent": False, "key_source": None}` re-read VERBATIM at HEAD this session; :272-275 CAUTION verbatim; :315 DELETE True verbatim; :534 add_tag True verbatim. B5 Evidence now states the prior claim was FALSE for 2/3 verbs; tool-hint derivation stated (follows GOVERNED False for push+mark_complete); reconciliation carried as W-5 mitigation (5) + §8 exposure precondition + UV-P register #6. The condition's "state how tool-hint derivation resolves either way" clause: SATISFIED. |
| **C2** | ADVISORY | **CONFIRMED-DISCHARGED (carried-as-UV-P)** | Condition 2's own disjunction permits "receipt or frozen-syntax UV-P". UV-P #4 present in frozen syntax with named METHOD (sandbox-workspace probe at felt-gate staging, sprint-6, operator-witnessed) and honest REASON (zero-direct-calls fence). B5 C2 caveat (state convergence ≠ side-effect silence) present. |
| **C3** | FLAG | **CONFIRMED-DISCHARGED** | B4 authorization carries both invariants + values + derivation + doctrine-binds/values-delegated scope. Re-read s4-seam-contract §2.2 (lines 114-126): `SHARE_WARMERS + SHARE_API + SHARE_MCP ≤ 1.0`, `RATE_RPS × 60 ≤ SHARE_MCP × 1500`, shares 0.60/0.32/0.08, RPS 2.0 / BURST 10 / MAX_WAIT 2.0 — dossier values MATCH the seam contract verbatim; derivation (0.08×1500=120/min=2.0×60) checks arithmetically. |
| **C4** | FLAG | **CONFIRMED-DISCHARGED (both legs) + declared REVISION verified consistent** | Leg 1 re-verified by direct read of the installed package: asana `.venv/.../autom8y_auth/__init__.py` exports `FLEET_AUDIENCE` (import :75, `__all__` :162) and `DATA_PLANE_AUDIENCE` is ABSENT from the entire export surface — A22's probe result corroborated by file-read. Leg 2 re-verified: `create_service_token` signature :477-485 carries NO audience parameter; BOTH issuance branches hardcode `audience="https://api.autom8y.io"` (:705 exempt, :767 business); contrast function at :212 (`effective_audience = audience or ...`) confirms parameterization exists elsewhere but is NOT threaded on the SA path. The REVISED recommendation (bare FLEET_AUDIENCE for v1; dedicated audience = named prerequisite) is exactly the re-score iter-1 CH-03 predicted if mint-side required auth-service change; old text preserved struck-through at BOTH sites (B3ii-O1 + B3 composite); O1b enumerated + killed (answers the iter-1 CH-06 B3ii gap); §10 B3 cell truthful to the revision. |
| **C5** | FLAG | **CONFIRMED-DISCHARGED (residual honestly recorded)** | Breadth paragraph present in W-5 (SA authority = full REST write surface; curation bounds PATH not CREDENTIAL). middleware/core.py re-read: log_data at :151-157 carries request_id/method/path/status_code/duration_ms ONLY — no principal identity; ":146 no sensitive data" comment verbatim. DELETE irreversibility carried (tasks.py:315 True + :332-334 "Permanently deletes this task and ALL subtasks. Dependents are orphaned" — verbatim). Detective control named as DELIBERATE ABSENCE with satellite-side remediation named, not built. |
| **C6** | FLAG | **CONFIRMED-DISCHARGED** | Reverse-coupling named in B1-O1 AGAINST (every MCP-only iteration atomically redeploys production asana) with the reference-posture cadence peak stated; the condition's conditional clause ("cite deploy behavior IF it defrays") honestly deferred as UV-P #5 rather than asserted unverified. Recommendation B1-O1 unchanged with a strengthened AGAINST — legitimate: alternatives' costs unchanged, operator now sees the full cost. |
| A5 | ADVISORY | **CONFIRMED-DISCHARGED** | Qualifier corrected to "spec-VISIBLE introspection routes" — converges exactly to this critic's own iter-1 CH-07 verified reading (main.py:757-766, query.py:83-84); no re-probe required. |

**Verification-method limits (recorded honestly):** two git-layer receipts could not be
independently re-executed under this critic's tool scope (no git): A16 (`git blame` →
d6e9cef17 single-commit deliberateness of the PUT-False/DELETE-True split) and A20 (s1
branch diff → tasks.py untouched). Both are NON-load-bearing for the C1 discharge: the
discharge is fork (b) — carry the contradiction — and this critic directly confirmed the
load-bearing HEAD state (tasks.py:254 False NOW; both annotations coexist at HEAD in
uniform style). Falsification pathway: re-run `git blame -L 250,258 -L 311,319` on
tasks.py and `git diff --stat main...feat/asana-mcp-v1-s1-hygiene -- '*tasks.py'`; even
if A16's single-commit attribution falsified, the governed value at HEAD is False and the
carried disposition survives.

## 2. New-defect findings (surface introduced BY AMENDMENT-1 — in delta scope)

### ND-1 [ADVISORY] — amendment change-manifest under-declares the §10 W-5 cell edit
- The frontmatter amendment_log scope reads "frontmatter + B1/B3ii/B4/B5/W-5/§8/
  Appendix-A/§9.5 touched" and §9.5 deviation note (2) declares only "the §10 B3
  recommendation summary cell was updated". But the §10 W-5 summary cell was ALSO edited —
  its text references "5th = AMENDMENT-1 C1" and "RECORDED (C5)", which cannot predate the
  amendment (pre-amendment W-5 carried four mitigations).
- **Not a substantive defect**: the edit is truth-INCREASING (the operator must not ratify
  against a stale summary — the executor's own stated rationale), condition-driven (C1/C5
  content), and the checkboxes are pristine (12/12 unchecked, signature blank, re-verified).
  It is a manifest-completeness gap only.
- **Falsification pathway**: add §10 to the amendment_log scope list and declare the W-5
  cell alongside the B3 cell; that observation fully retires this finding.

### ND-2 [FLAG] — revision-interaction residual stated piecewise, never compounded
- The C4 revision (v1 rides bare FLEET_AUDIENCE) interacts with the C5 residual: an
  MCP-SA token is now (a) replayable against ANY internal fleet surface admitting
  FLEET_AUDIENCE (B3ii-O2, stated), (b) authorized for the ENTIRE asana REST write surface
  including irreversible DELETE (C5 breadth, stated), and (c) undetectable off-path (C5
  deliberate absence, stated). Under the ORIGINAL B3ii-O1 recommendation, (a) would have
  been partitioned away; the revision re-couples it. Each factor is honestly stated on its
  own page; the PRODUCT is nowhere compounded for the ratifier, and the W-5 ethos is
  conscious ratification of the whole residual, not its factors.
- **Partial bound this critic found that the dossier does NOT carry**: the SA token TTL is
  1800s — "TTL = settings.SERVICE_TOKEN_TTL_SECONDS (1800)" (auth token_service.py:739,
  re-read this session) — a 30-minute replay window bound on any leaked/replayed MCP-SA
  token. Carrying it would DEFRAY part of this flag.
- **Falsification pathway**: one compounding sentence in W-5 (or the §10 W-5 cell) naming
  the aggregate off-path risk and citing the 1800s TTL bound; OR the operator waives at
  GATE-BW with the piecewise statements deemed sufficient. Either observation retires it.
- **This flag gates nothing.** Per the two-iteration cap there is no third critique; it
  rides to the operator as residual item 8 below.

**Also swept, clean:** no motivated re-weighting beyond evidence (the B3ii-O2 re-weight
is tethered to verified A22/A24 receipts and is the exact consequence iter-1 CH-03
predicted); no silent recommendation change beyond the one declared (B1/B2/B4/B5/W-5
recommendation tokens unchanged — verified against the iter-1 record); no receipt
fabrication (9/16 A15–A28 anchors independently re-probed, all verbatim: A15, A17, A18,
A19, A22-surface, A24×3 sites, A25, A26, A28); no section renumbering (§9.5 and A15–A28
are additive; UV-P register dispositions explicit, numbering continuous).

## 3. Delta-scope attestation + non-regression

- This critique is DELTA-ONLY per critique-iteration-protocol §4. NOT re-opened: iter-1
  passed surface (enumeration audits of B1/B2/B3i/B3iii/B4, the 14 A1–A14 receipts, the
  null-option strawman check, charter-precedence carriage, E-kill non-relitigation);
  charter text; E-kills; foundational topology/principal-class decisions iter-1 did not
  challenge. Un-adopted iter-1 ADVISORIES (CH-06 remainder: B1 in-process-mount/Lambda
  name-kills, B5 mechanical metadata-gate floor, W-5 sunset-clause variant) were
  non-conditions then and are NOT promoted now; they appear in the residual list only.
- Non-regression: no iter-1-accepted item weakened. A5 was corrected toward this critic's
  own reading; A1–A14 claims otherwise untouched; all five unchanged recommendations
  carry STRENGTHENED against-sides or invariants, not weakened ones. PASS.
- Iteration accounting: this is iteration 2 of 2. A BLOCKING here would have exhausted
  the cap (T5b operator escalation). No BLOCKING fired. The gate CLEARS; no third
  iteration exists structurally.

## 4. Residual items — the honest list the operator ratifies WITH at GATE-BW

1. **The carried contradiction (C1)**: PUT /tasks/{gid} is governed idempotent:False at
   HEAD (tasks.py:254); the composite's push + mark_complete legs carry False tool-hints
   until the annotation is reconciled; reconciliation is W-5 mitigation (5) and a §8
   write-surface exposure precondition (UV-P register #6 — a gate, not a premise).
2. **UV-P #2** (dormant): Asana rate-limit per-token vs per-account semantics — bears on
   B4-O5 only, which is rejected for v1.
3. **UV-P #3** (carried): FastMCP 3.x currency — rides to POC pin time; not load-bearing
   for any ruling.
4. **UV-P #4** (C2): Asana Rules re-fire on re-PUT completed=true on an already-complete
   task — sandbox probe at felt-gate staging (sprint-6), operator-witnessed; until then
   W-3 "whole-chain safe re-run" carries the scoped caveat (state converges; downstream
   Rule side-effects may re-fire).
5. **UV-P #5** (C6): a8 service-stateless rolling-deploy/paired-rollback behavior —
   bounds the B1-O1 reverse-coupling cost if confirmed; probe at deployment-PR time.
6. **B3ii v1 audience = bare FLEET_AUDIENCE**: replay widened across internal fleet
   surfaces for the reference window (V-2 bounds it internally); the dedicated-audience
   partition is DEFERRED as a named deployment/promotion prerequisite (auth-service
   audience parameterization + autom8y_auth >=4.2.0 floor bump + new constant).
7. **C5 residual**: MCP-SA effective authority = full REST write surface incl.
   irreversible DELETE (tasks.py:315, :332-334); off-path detective control is a
   DELIBERATE ABSENCE (satellite request log carries no principal identity,
   core.py:151-157); satellite-side remediation named, not built at v1.
8. **ND-2 compounding (this report)**: the product of items 6 × 7 — fleet-wide
   replayability × full-surface authority × no off-path detection — partially bounded by
   the 1800s SA token TTL (token_service.py:739), which the dossier does not yet carry.
9. **B1-O1 reverse-coupling accepted**: every MCP-only iteration atomically redeploys
   production asana, peaking during the pre-felt-gate iteration window; UV-P #5 pending.
10. **Evidence ceiling MODERATE**: rite-disjoint critique now attached (iter-1 + this
    delta), but judgmental recommendations do not auto-lift to STRONG (R11 uncleared);
    the operator ratifies a MODERATE-ceiling dossier knowingly.
11. **Un-adopted iter-1 advisories** (CH-06 remainder, listed in §3) — advisory then,
    advisory now.
12. **Verification-method limits** (§1): A16/A20 git-layer receipts not re-executed by
    this critic; load-bearing HEAD state independently confirmed; re-run commands named.

## 5. Falsification of THIS report

This delta verdict revises if: (a) any of the nine re-probed anchors is shown to have
been read against a non-canonical checkout (this critic read
/Users/tomtenuta/Code/a8/a8/repos/{autom8y-asana,autom8y} working trees at HEAD this
session — a divergent canonical source would falsify the re-verification); (b) the s1
branch (PR #237) IS shown to touch tasks.py:254, making the carried contradiction moot
and ND-list item 1 stale (verdict would IMPROVE toward PASS on re-emission by the
executor, not regress); (c) a pre-amendment copy of the dossier shows the §10 W-5 cell
text predating AMENDMENT-1 (impossible on internal evidence — the cell cites
AMENDMENT-1 — but stated for completeness; would retire ND-1); (d) an existing
platform control is receipted that already compounds-and-bounds the ND-2 aggregate
(e.g., a fleet-level SA anomaly alarm this critic's reads missed) — that receipt retires
ND-2 outright. Self-referential cap: this critic's judgments are MODERATE-ceilinged per
self-ref-evidence-grade-rule; the mechanical re-probes in §1–§2 are receipts and stand
independent of that cap.

# END — iter 2 DELTA. Verdict: PASS-WITH-CONDITIONS (CONCUR-WITH-FLAGS; gate clears;
# flags ride to the operator). The operator is the sole ratifier at GATE-BW and the sole
# closer of the felt gate. No third critique iteration exists.
