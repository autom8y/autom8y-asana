---
type: handoff
artifact_type: HANDOFF
subtype: daily-parity-digest
initiative: substrate-v2-epoch
wave: S8-2 (P5 live-parity window — DAY 1)
date: 2026-08-05
session: session-20260803-220334-f2a75514
main_sha: dbd46378 (through #313)
window_clock_start: 2026-08-05T09:19:45Z (first live paced sweep)
window_law: P5 [A-2026-08-03] — evidence-closed; ~3-day floor / 7-day HARD ceiling from clock start
status: accepted
---

# DAILY PARITY HANDOFF — 2026-08-05 (window DAY 1)

**MISSION (verbatim):** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its
correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can
reconstruct the same guarantees as a template application, not a research project."
**PREDICATE (verbatim, NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean
(adversarial fixture replay + bounded live-parity window, every divergence explained) AND a
rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within
freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine
landed at fleet-constitution level.

## ⚑ PROMINENT FLAG (rubric §3 — both thresholds tripped; benign, no interrupt)

**O4 leg-2 corpus drift: −$5,000 / −6.17%** ($80,985 → $75,985 over the 4 dark days) — exceeds
the founding-wound magnitude ($4,800/~6%), which is exactly why the threshold was set there.
Classified **{delta+explanation} EXPLAINED-BENIGN** by the standing adjudicator (decomposition
closes to the penny and the row: ACTIVE −2r/−$3,000 · OPTIMIZE held byte-exact · STAGED −1r/−$2,000;
frame GREW +11 rows; all six wound classes excluded on positive evidence). Exemplar RE-PINNED to
the leg-2 generation (#303). Clock NOT restarted. Full verdict: RECEIPT-s8-0-fixture-recapture
leg-2 section. **NOTE the corrected label:** these 3-section sums are "exemplar aggregates," NOT
active_mrr (referent ruling, below).

## The referent ruling (day's most consequential record)

**RULING-pythia-f305-1 (#307): "active_mrr" DENOTES the production-served number** — 22-section
classifier active set + dedup(office_phone, vertical) + mrr>0 + Float64 sum (offer.py:20-43 /
compute.py:66-116). The 3-section "served_value" label in prior receipts was a MISNOMER. The qa
gate had proven the as-built harness compared a number production never serves ($14,360+ of
production-active MRR invisible — the founding wound's silent-loss shape inside the gate itself).
Nine binding capture-mechanics conditions attached; fail-closed fetch-plan coverage is the
anti-RC-C keystone. LEG A (served definition, via the real `compute_metric` machinery identically
both sides) is the gate anchor; LEG B (exemplar aggregate) is corpus-continuity only.

## Window ledger — DAY 1 (three attempts, zero unexplained, zero wounds, zero observations yet)

| # | Time (UTC) | Outcome | Detail | Budget charged |
|---|---|---|---|---|
| 0 | 09:12 | env-fail (pre-touch) | PYTHONPATH missing → import error; **zero prod touch** | 0 |
| 1 | 09:19:45 | **error (receipted)** | **LEG A v1 = $76,285.00 LIVE** (first served-definition derivation); v2 leg died fail-loud on polars bare-inference ComputeError (receipt `…ec83614f`); never served | **663** (398 page + 265 cascade — complete boundary accounting incl. cascade via script wrapper) |
| 2 | 11:03 | error (receipted) | AWS session creds expired mid-window → v1 S3 read failed pre-Asana (receipt `…bf31ade4`); PROV emit honestly FAILED (no fabricated heartbeat) | 0 |

Ledger: `{"2026-08-05": 663}` of cap 11,200 (5.9%). Every attempt receipted under
`.sos/wip/parity/receipts/2026-08-05/`. **No parity observation yet** — nothing for the
adjudicator to classify (rubric input-contract requires both legs; the error paths never
produced v2). No divergence, no wound, no clock event.

## PROV suite (RC-F live evidence)

- **PROV-2 dead-man: ALARM → OK at 09:23:06Z** after six days of predicted ALARM — cleared by
  sweep-1's real heartbeat. **RC-F-2 quiet-side RECEIPTED**
  (`RECEIPT-prov2-clear-rcf2-2026-08-05.md`); **C10 two-sided evidence COMPLETE** for PT-03 Q6.
- **PROV-1 + PROV-4: ALARM (09:23Z)** on sweep-1's truthful emissions (unprovable=1, mismatch=1 —
  the v2 store is empty because the v2 leg refused to publish). TRUE alarms, ticket-only, known
  cause; expected clear on the first SERVED sweep. Escalates only if they survive the cure.
- PROV-3/5/6: OK throughout.

## Cure train landed today (all P7-gated, all merged)

#313 v2-frame schema fix (bare inference → `safe_dataframe_construct(rows, OFFER_SCHEMA)`, the
literal dataframe_service.py:220 idiom; qa DELTA-gate GO, construction-identity verified to the
function object; + consequential improvement: missing value column now degrades to
`refused-staged_rejected`, incumbent preserved). Also merged: #309 runner (+ SEAM-1 keyword fix —
the scar guard caught a positional entity_type), #308/#314 gate receipts. Three CI reds en route
were root-caused: 2× CodeArtifact token flake (infra), 1× formatting drift (cured 8f68121c).

## External landings mid-window (concurrent activity, on the record)

- **#312 warmer: deadline-yield 429 retry + offer-frame priority — THE V1 WRITER CHANGED.**
  Capture-skew (B1) context for future classifications; P6-adjacency noted, not relitigated here.
- #306 R7 tripwire lambda (touched live.py; its "clear dead noqa" cured the RUF100 red — my
  duplicate cure #310 closed unmerged). #311 CI uv-pin.

## Ledger notes carried per wave-entry ruling G4

(ii) C8 packet's freshness.py/entity_registry.py line-anchors drifted BY DESIGN via C17 — read the
in-place amendment with the packet. (iii) "#292 24 CI checks" count remains locally unverifiable
(historical, non-load-bearing). **SLA re-ratification staging:** asset_edit/process observed 2×
cadence ≈52min < 3600s — the C8 §Ratification `provisional` qualifier is dischargeable on the
operator's word (adjudicator confirmed evidence sufficient; not staged unbidden).

## ⛔ BLOCKED — operator input required to resume sweeps

**The AWS login session has reached its hard expiry** (last export was valid only to 11:10:01Z;
`login_session = arn:aws:iam::696318035277:user/tom.tenuta` needs interactive re-auth). Every
sweep needs S3 (v1 read + v2 store) + Secrets Manager + CloudWatch. **Unblock: run `! aws login`
(interactive) in-session**, then the sweep re-fires from the runbook
(scratchpad `wu4/env_setup.md` + `first_sweep.py`; PYTHONPATH=repo-root; avoid ~:07–:17).

## Next (in order, once unblocked)

1. Re-fire sweep → first SERVED dual-leg observation → standing pythia seat classifies
   {explained-benign | wound} → PROV-1/4 clear on the published artifact.
2. Sweeps continue paced (off-peak preference) toward ≥2 distinct warm cycles in parity;
   park-per-day; resume re-verifies preflight.
3. Window closes on EVIDENCE (four conjuncts) → PT-03 (fresh-instance potnia, Q1-Q6, rite-disjoint
   security critics) → rollback drill → P9 auto-flip → PT-04 → un-hold #279 → DP-1/DP-4b packets
   (DOORS HALT for the operator's word). EUNOMIA DORMANT until S12.
