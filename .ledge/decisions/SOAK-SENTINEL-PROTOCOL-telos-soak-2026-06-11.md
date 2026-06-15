---
type: decision
subtype: soak-sentinel-protocol
status: accepted
title: "SOAK SENTINEL PROTOCOL — daily-attestation discipline for the 7-day telos-soak (anchor :511, clear 2026-06-18)"
date: 2026-06-11
clock_state: RUNNING
anchor_utc: 2026-06-11T15:24:21Z
target_clear_utc: 2026-06-18T15:24:21Z
evidence_grade: MODERATE   # sre attesting sre's own watch; the STRONG is eunomia's rite-disjoint at clear
governs:
  - .ledge/decisions/IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md   # the clock + the RESET-vs-LOG law this protocol operationalizes
soak_subject: telos dataframe-resolution-coherence — five-signal verified_realized of the CONVERGED + RECOVERY-HARDENED plane
substrate: ECS :511 / image 49099b1 (BOTH faces) — src-IDENTICAL to game-day-proven 3a59c72
authority: operator Meta-Grant 2026-06-11 (sre pantheon holds user-grade delegation for daily soak attestation + LOG-class rulings; RESET-class is RECOMMEND-ONLY, operator declares)
---

# SOAK SENTINEL PROTOCOL — telos-soak 2026-06-11 → 2026-06-18

> **GRANDEUR ANCHOR.** We hold the 7-day telos-soak (anchor `2026-06-11T15:24:21Z`
> on `:511`/`49099b1`, clear `2026-06-18T15:24:21Z`) as a **SENTINEL, not a
> spectator** — every soak-day attested by **live receipts** (band counts, alarm
> states, AC-6 cadence), every RESET-vs-LOG ruling made by the **codified law**
> with a pasted disambiguation receipt — proven ONLY by live AMP/ECS/S3-content
> receipts, never by a green dashboard or an optimistic absence-of-alarms. The
> clock itself, and anything that resets it, **stays the operator's.**

This protocol is the daily discipline that holds the watch. It governs, and is
governed by, `IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md` (the clock +
the RESET-vs-LOG law). Read that record first; this one operationalizes it.

---

## §0 Strict impossibilities at this station (carried verbatim from the Meta-Grant)

This station is **PRODUCTION-READS-ONLY + ledge-file authoring**. The following
are HARD-OFF, regardless of any receipt:

- Anything that rolls an asana task-def (asana `main` is **MERGE-FROZEN**).
- **RESET-class rulings** — recommend-only; the operator declares.
- **Mid-soak fault injection** — no chaos, no probe-by-breaking. (The iris
  pipe-smoke disambiguation in §4 drives *known-good traffic* at the live
  receiver; it injects no fault and rolls nothing.)

Permitted: `aws describe/get/s3 cp/logs filter`, AMP queries, `gh api` reads,
and Write/Edit of ledge files. **No claim without a pasted receipt.** Adjectives
are rejected.

---

## §1 Per-day record naming

One attestation per soak-day, authored at the station:

```
SOAK-DAY-N-ATTESTATION-telos-soak-2026-06-{DD}.md
```

| Day | File | Soak-date |
|-----|------|-----------|
| 1 | `SOAK-DAY-1-ATTESTATION-telos-soak-2026-06-11.md` | 2026-06-11 (anchor day; authored this dispatch) |
| 2 | `SOAK-DAY-2-ATTESTATION-telos-soak-2026-06-12.md` | 2026-06-12 |
| 3 | `SOAK-DAY-3-ATTESTATION-telos-soak-2026-06-13.md` | 2026-06-13 |
| 4 | `SOAK-DAY-4-ATTESTATION-telos-soak-2026-06-14.md` | 2026-06-14 |
| 5 | `SOAK-DAY-5-ATTESTATION-telos-soak-2026-06-15.md` | 2026-06-15 |
| 6 | `SOAK-DAY-6-ATTESTATION-telos-soak-2026-06-16.md` | 2026-06-16 |
| 7 | `SOAK-DAY-7-ATTESTATION-telos-soak-2026-06-17.md` | 2026-06-17 |
| clear | `SOAK-CLEAR-ATTESTATION-telos-soak-2026-06-18.md` | 2026-06-18 (clear seam; eunomia rite-disjoint STRONG) |

> The anchor moment is `15:24:21Z`. Days 1–7 are the seven 24h windows; the clear
> attestation is authored at/after `2026-06-18T15:24:21Z` and is **eunomia's** —
> sre caps at MODERATE (see §6). Each day's file carries the frontmatter clock
> block from this protocol (anchor/target/clock_state/evidence_grade), verbatim.

---

## §2 The FOUR mandatory receipt sections (with the EXACT command per receipt)

Every daily attestation MUST contain all four. A day cannot be ruled GREEN with a
missing section — a missing receipt is treated as that section's **worst case**
until the receipt is pasted.

### §2(a) Deploy-freeze check

The clock is suspect the instant the substrate moves. Two probes:

**(a1) asana `main` HEAD must still be `49099b12`** (anything newer = a merge to
the satellite's main = the deploy trigger = the clock is suspect → **operator
HALT**, do not rule the day):

```bash
env -u GITHUB_TOKEN gh api repos/autom8y/autom8y-asana/commits/main --jq .sha
# expect: 49099b120e6292e44fb24ce79d5ae35007e10792  (prefix 49099b12)
```

**(a2) ECS must show a SOLE `:511` deployment, `rolloutState=COMPLETED`**
(a second deployment row, or any task-def ≠ `:511`, = a deploy mid-window = RESET-class):

```bash
aws ecs describe-services --cluster autom8y-cluster --services autom8y-asana-service \
  --region us-east-1 \
  --query 'services[0].deployments[*].{td:taskDefinition,roll:rolloutState}'
# expect: exactly ONE element, td .../autom8y-asana-service:511, roll COMPLETED
```

> Optional corroborator (recommended): warmer face still `49099b1` —
> `aws lambda get-function --function-name autom8-asana-cache-warmer --region us-east-1 --query 'Code.ImageUri' --output text`
> (expect `…/autom8y/asana:49099b1`). Both faces moving in lockstep is the
> substrate's identity invariant.

**Ruling**: a1 ≠ `49099b12` OR a2 ≠ sole `:511` COMPLETED → the day is **AMBER**
and the finding is "deploy mid-window — RESET-class, operator ruling required."

### §2(b) Band content — parquet COUNTS, never logs

Counts come from the **parquet content**, derived with polars. Logs are color, not
counts (the denominator-integrity rule).

```bash
aws s3 cp s3://autom8-s3/dataframes/1201081073731555/unit/dataframe.parquet  /tmp/soak-dayN/unit.parquet  --region us-east-1
aws s3 cp s3://autom8-s3/dataframes/1143843662099250/offer/dataframe.parquet /tmp/soak-dayN/offer.parquet --region us-east-1
```

```python
# /Users/tomtenuta/Code/a8/repos/autom8y-asana/.venv/bin/python3
import polars as pl
u = pl.read_parquet("/tmp/soak-dayN/unit.parquet")
o = pl.read_parquet("/tmp/soak-dayN/offer.parquet")
u_h = u.height
u_mrr = u.select(pl.col("mrr").is_not_null().sum()).item()
print("unit nonnull-mrr / height:", u_mrr, "/", u_h, " ratio:", round(u_mrr/u_h, 4))   # FLOOR: ratio >= 0.20
print("offer height:", o.height, " nonnull-mrr (1332-class):", o.select(pl.col("mrr").is_not_null().sum()).item())
print("offer_id dtype (Utf8<->Int64 drift watch):", o.schema["offer_id"])
```

| Band signal | Source | Floor / band | Disposition if breached |
|-------------|--------|--------------|-------------------------|
| **unit nonnull-mrr ratio** | unit parquet, first-party polars | **ratio ≥ 0.20** (the ~0.239 sold band) | < 0.20 = unit-frame degrade → investigate; persisting > 1 staleness window = RESET-class |
| **offer nonnull-mrr (1332-class)** | offer parquet, first-party polars | ~1332-class (LIVE-VARIANT; growth OK) | sharp drop toward 0 = offer-frame clobber → RESET-class (FM-1 signature) |
| **gun** (FPC coherence-invariant violation count) | FPC lattice tool (autom8y monorepo; **cross-repo, not first-party at this station**) | **≤ 15** | > 15 = drift-cells multiplying → LOG/investigate per UK-2 unless it co-fires with a collapse |
| **coherent** (FPC coherent-cell count) | FPC lattice tool (cross-repo) | **≥ 561** | < 561 = coherence regression → investigate; growth above the 579–592 envelope is LOG (not degrade) |

> **gun / coherent provenance honesty.** The gun/coherent figures are computed by
> the FPC coherence-invariant tooling that lives in the **autom8y monorepo**, not
> in this receiver repo — they are **not first-party re-derivable at this
> station**. Carry them by the most-recent authoritative cross-repo receipt and
> LABEL them as such (cite the source run + timestamp). Per
> `structural-verification-receipt`, attach a `[UV-P: … | METHOD:
> cross-repo-fpc-tool | REASON: lattice primitive not probable at receiver
> station]` marker on any gun/coherent claim you did not re-run yourself. What IS
> first-party at this station — unit ratio, offer counts, offer_id dtype, and the
> S1 active_mrr substrate stability (§2b-S1 below) — must be re-derived, never
> cited.

**§2b-S1 — the active_mrr denominator (the RESET tripwire 62→7):** the certified
S1 signal is `active_mrr = 62 rows / $79,485` over the **entity-keyed** prefix
`dataframes/1143843662099250/offer/sections/`. The S1 substrate parquets are
dated `2026-06-09` (the warm that established the denominator); verify they are
**unchanged** (mtime stable) each day:

```bash
aws s3 ls s3://autom8-s3/dataframes/1143843662099250/offer/sections/ --region us-east-1 --recursive | sort -k1,2 | tail -3
```

> **TRAP — entity-blind legacy reader.** The deployed `python -m
> autom8_asana.metrics active_mrr` (no `--entity-type` on this branch) reads the
> **legacy project-entity prefix** `…/1143843662099250/sections/` and returns a
> project-entity fossil (~`76685`/`22`), NOT the S1 signal. This is the documented
> offline-reader entity-blind fossil — do **not** treat its value as active_mrr
> for soak purposes. The S1 signal is the `offer/sections/` denominator; collapse
> `62→~7` on THAT prefix is the RESET-candidate.

### §2(c) Alarm states

Armed-not-firing is health. `firing` is the investigation trigger.

```bash
WS=ws-26b271ef-afd6-4158-82cc-74dbcb273976
awscurl --service aps --region us-east-1 \
  "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/${WS}/api/v1/rules" \
| python3 -c "import sys,json; d=json.load(sys.stdin); \
[print(r['name'], r.get('state')) \
 for g in d['data']['groups'] if 'asana' in g['name'].lower() \
 for r in g.get('rules',[]) \
 if r['name'] in {'AsanaReceiverAvailabilityFastBurn','AsanaReceiverAvailabilitySlowBurn','AsanaReceiverHeartbeatAbsent'}]"
```

| Rule | Healthy state | If `firing` |
|------|---------------|-------------|
| `AsanaReceiverAvailabilityFastBurn` | `inactive` (armed, not firing) | burn-rate ALARM under real traffic → **RESET-class** (investigate traffic first) |
| `AsanaReceiverAvailabilitySlowBurn` | `inactive` | burn-rate ALARM under real traffic → **RESET-class** |
| `AsanaReceiverHeartbeatAbsent` | `inactive` | dead-man fired → SLI dark → **RESET-class** (see §5 escalation) |

> A rule **missing** from `/rules` is worse than `firing` — it means the SLO is
> unguarded. Missing = AMBER + operator ruling required.

### §2(d) AC-6 cadence

Judge the **burst cadence**, not instantaneous presence. The metric name is
**PREFIXED** — `autom8y_asana_receiver_query_outcome_total`. The UNPREFIXED name
returns EMPTY (the known trap; an empty result here is a query bug, not a dark
pipe).

```bash
WS=ws-26b271ef-afd6-4158-82cc-74dbcb273976
BASE="https://aps-workspaces.us-east-1.amazonaws.com/workspaces/${WS}/api/v1"
NOW=$(date +%s); START=$((NOW-86400))
QUERY='sum(increase(autom8y_asana_receiver_query_outcome_total[30m]))'
ENC=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$QUERY")
awscurl --service aps --region us-east-1 -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=${ENC}&start=${START}&end=${NOW}&step=1800" \
  "${BASE}/query_range"
```

**How to read it** (the cadence law):
- The healthy pattern is **~100-class bursts at ~hourly `:30` cadence**, with
  **zero-floors BETWEEN bursts**. Zero-floors are the *known pattern*, NOT absence.
- Count the organic bursts in 24h. Roughly hourly cadence (≈ 18–24 bursts/24h with
  occasional skips) = healthy.
- **DENOMINATOR-INTEGRITY RULE**: never silently blend canary/iris traffic into an
  organic-cadence claim. Any bucket inflated by an iris pipe-smoke (a ~1000+ spike
  far above the ~100 envelope) MUST be **LABELED synthetic** and excluded from the
  organic-cadence count. State the organic burst count and the synthetic buckets
  separately.
- A genuine cadence gap = **> 1 missed burst cycle** of zero with no organic
  resume. That is the trigger for the §4 counter-absence instrument — NOT an
  immediate ruling.

---

## §3 RESET-vs-LOG decision tree (operationalized)

Source of law: `IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md` §"What RESETS
vs LOGS". This is its operational form. **LOG-class rulings are delegated to sre.
RESET-class rulings are RECOMMENDED with the receipt and DECLARED only by the
operator.**

```
                         ┌─────────────────────────────────────────────┐
   daily receipts (a–d)  │  Did any of these fire, with a LIVE receipt?  │
            │            └─────────────────────────────────────────────┘
            ▼
  ┌──────────────────────────────────────── RESET-CLASS (recommend-only) ───────────────────────────────────────┐
  │ • active_mrr COLLAPSE (62 → ~7) on the offer/sections denominator         [§2b-S1]                            │
  │ • autom8y_asana_receiver_query_outcome_total ABSENT mid-window            [§2d + §4 disambiguation REQUIRED]  │
  │      …AND the pipe proven DARK under traffic (iris smoke → counter stays 0 under 200s)                        │
  │ • burn-rate SLO ALARM under REAL traffic (FastBurn/SlowBurn = firing)     [§2c]                               │
  │ • SLI dark mid-window (up{job=asana} != 1 / HeartbeatAbsent firing)       [§2c + §5]                          │
  │ • a DEPLOY mid-window (asana main ≠ 49099b12  OR  ECS td ≠ sole :511)     [§2a]  (bit 3× on 2026-06-11)        │
  │ • a DEGRADED frame PERSISTS unhealed past ONE staleness window            [§2b]                               │
  │ ─────────────────────────────────────────────────────────────────────────────────────────────────────────  │
  │  ACTION: write the finding, mark the day AMBER (or RED if user-impacting + confirmed), paste the              │
  │  disambiguation receipt, state "operator ruling required". DO NOT reset the clock. DO NOT rule.               │
  └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
            │  (none of the above)
            ▼
  ┌──────────────────────────────────────── LOG-CLASS (sre-delegated) ───────────────────────────────────────────┐
  │ • the NAMED unit-floor calibration WARN (~0.239 vs 0.8 — UK-2 / FPC-Phase-3 exception)   → LOG, day stays GREEN │
  │ • UK-2 drift-cells (discount / offer.cost / asset_edit.score; offer_id Utf8↔Int64)       → LOG               │
  │ • β-3 canary signals                                                                     → LOG               │
  │ • S2/S3 SEAM-2 deferred-NOT-observed (ad_reporting + payments/mrr monolith consumers)     → LOG               │
  │ • monolith organic-burst CADENCE gap, pipe proven HEALTHY (§4)                            → LOG/WATCH         │
  │ ─────────────────────────────────────────────────────────────────────────────────────────────────────────  │
  │  ACTION: record under "LOG-class observations"; day is GREEN; carry the watch forward.                       │
  └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### §4 The COUNTER-ABSENCE INSTRUMENT — iris pipe-smoke disambiguation

**When**: AC-6 (§2d) looks dark **beyond one missed burst cycle** with no organic
resume. Absence alone is NOT a ruling — disambiguate first. (Method proven
`2026-06-11 15:40–15:56Z`: counter EMPTY → 1284, +468/5m, monotonic ~+100/min
tracking the project arm 1:1, zero `outcome=server_error`.)

**How** (drives KNOWN-GOOD traffic at the live receiver — injects no fault, rolls
nothing):

```bash
# SA self-minting token provider (self-refreshing, survives the SA JWT TTL)
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana
AWS_REGION=us-east-1 PYTHONPATH=src \
  .venv/bin/python3 scripts/canary/receiver_bulk_fanout_deploy_gate.py   # 100rpm known traffic
# THEN watch the PREFIXED counter (§2d query) over the smoke window:
```

**The ruling fork** (paste the counter trace as the disambiguation receipt):

| Observation under the smoke | Diagnosis | Ruling |
|-----------------------------|-----------|--------|
| Counter **TRACKS** the driven traffic (climbs ~+100/min, monotonic, zero `server_error`) | pipe HEALTHY; the gap is a **monolith-side cadence gap** | **LOG/WATCH** (sre-delegated). Day stays GREEN. Cross-repo investigation of the monolith satellite arm if no organic resume in 24h. |
| Counter stays **DARK** under sustained 200s (traffic accepted, metric flat) | pipe **BROKEN** — the SLI/EMF path is dark under real traffic | **RESET-grade recommendation** to the operator. Mark AMBER, paste the dark-counter receipt, "operator ruling required." |

> The smoke traffic is itself synthetic — when you next read §2d, the smoke
> bucket(s) MUST be labeled synthetic and excluded from the organic-cadence count
> (denominator-integrity).

---

## §5 Escalation routes (registered, drill-proven)

| Trigger | Route |
|---------|-------|
| `AsanaReceiverHeartbeatAbsent` fires (dead-man) | AMP `absent()` → **SNS → Slack** (drill-proven `2026-06-11 07:51Z`) |
| `FastBurn` / `SlowBurn` fires | same SNS → Slack route |
| Deploy mid-window detected (§2a) | operator HALT; do not rule; recommend re-anchor-or-investigate |
| Confirmed pipe-broken (§4 dark) | operator ruling required; stage rollback (below) |

**Rollback staging pointers** (for the operator's hand — sre stages, operator pulls):

| Asset | Pointer |
|-------|---------|
| Prior task-def (cure) | `:510` / `3a59c72` |
| Prior task-def (pre-cure) | `:509` / `7973c10` |
| Warmer 4-Sid policy capture | `/tmp/key-r2/policy_live_pre.json` |
| Prior-good unit frame | `/tmp/key-r2/unit_priorgood.parquet` |
| β-3 policy rollback sha | `730841e1` |

---

## §6 Evidence-grade header (per attestation)

Each daily attestation **self-caps at MODERATE**: sre is attesting sre's own
watch (self-referential authorship ceiling per `self-ref-evidence-grade-rule`).
The **STRONG** is eunomia's, rite-disjoint, simultaneous five-signal, at the clear
seam (`2026-06-18T15:24:21Z`). No daily attestation may round up to STRONG, and
none may declare `soak-CLEARED` — that ruling belongs to the clear seam.

Each day's frontmatter carries:
`type: decision` · `status: accepted` · `anchor_utc: 2026-06-11T15:24:21Z` ·
`target_clear_utc: 2026-06-18T15:24:21Z` · `clock_state: RUNNING` ·
`evidence_grade: MODERATE`.

**Rung this protocol sets**: `soak-sentinel-discipline-codified` (MODERATE).
