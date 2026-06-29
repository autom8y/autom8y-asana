---
type: decision
subtype: soak-day-attestation
status: accepted
title: "SOAK DAY-1 ATTESTATION — telos-soak RUNNING on :511 (anchor day; four receipts live)"
date: 2026-06-11
soak_day: 1
authored_utc: 2026-06-11T17:03:33Z
clock_state: RUNNING
anchor_utc: 2026-06-11T15:24:21Z
target_clear_utc: 2026-06-18T15:24:21Z
evidence_grade: MODERATE   # sre attesting sre's own watch; STRONG is eunomia's rite-disjoint at clear
verdict: GREEN
governed_by:
  - .ledge/decisions/SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md   # the four-receipt discipline + RESET-vs-LOG tree
  - .ledge/decisions/IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md  # the clock + the law
---

# SOAK DAY-1 ATTESTATION — telos-soak 2026-06-11 (anchor day)

> **Verdict: GREEN.** All four receipt sections derived live this hour (authored
> `2026-06-11T17:03:33Z`, ~99 min after the `15:24:21Z` anchor). Substrate frozen,
> band in-band/growing, alarms armed-not-firing, AC-6 organic burst RESUMED post
> the iris smoke. No RESET-candidate. Watch-item #10 (monolith cadence gap)
> CLOSED by the resume receipt.

Receipts (a) + (c) re-run by me at this station; (b) re-derived first-party from
the live parquets (with gun/coherent honestly seed-cited as cross-repo FPC-tool
values, UV-P-marked); (d) re-derived from a fresh 24h AMP query_range. Seed facts
from the S0 PV-gate run at `16:55:49Z` are cited where they corroborate, never
substituted for a live receipt.

---

## §2(a) Deploy-freeze check — **GREEN**

**(a1) asana `main` HEAD** — re-run by me `2026-06-11T16:58Z`:

```
$ env -u GITHUB_TOKEN gh api repos/autom8y/autom8y-asana/commits/main --jq .sha
49099b120e6292e44fb24ce79d5ae35007e10792
```

= `49099b12…` — **exact match**, no newer commit. The clock is NOT suspect.

**(a2) ECS deployments** — re-run by me `2026-06-11T16:58Z`:

```
$ aws ecs describe-services --cluster autom8y-cluster --services autom8y-asana-service \
    --region us-east-1 \
    --query 'services[0].deployments[*].{td:taskDefinition,roll:rolloutState,desired:desiredCount,running:runningCount}'
[
    {
        "td": "arn:aws:ecs:us-east-1:696318035277:task-definition/autom8y-asana-service:511",
        "roll": "COMPLETED",
        "desired": 1,
        "running": 1
    }
]
```

= **SOLE `:511`, `COMPLETED`, 1/1 running.** No second deployment row, no task-def
≠ `:511`. No deploy mid-window.

**Warmer face corroborator** — re-run `2026-06-11T16:46Z`:

```
$ aws lambda get-function --function-name autom8-asana-cache-warmer --region us-east-1 \
    --query 'Code.ImageUri' --output text
696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:49099b1
```

Both faces (ECS `:511` task-def image + warmer `Code.ImageUri`) carry tag
`49099b1` in lockstep — the substrate-identity invariant holds.

**(a) ruling: GREEN** — substrate frozen at the anchor; nothing moved.

---

## §2(b) Band content (parquet COUNTS) — **GREEN**

Fetched live by me `2026-06-11`:

```
$ aws s3 cp s3://autom8-s3/dataframes/1201081073731555/unit/dataframe.parquet  /tmp/soak-day1/unit.parquet  --region us-east-1
download: … to /tmp/soak-day1/unit.parquet   (200118 B)
$ aws s3 cp s3://autom8-s3/dataframes/1143843662099250/offer/dataframe.parquet /tmp/soak-day1/offer.parquet --region us-east-1
download: … to /tmp/soak-day1/offer.parquet  (237858 B)
```

Etags / mtimes (live, fresh organic warms — well within one staleness window):

```
unit  : etag 38aa29357b0c5a8072ff95e5e81ab6d7  mtime 2026-06-11T16:05:57Z  200118 B
offer : etag f4a4cf8268b9d7adb8c71a217a3f2751  mtime 2026-06-11T16:46:54Z  237858 B
```

First-party polars derivation (re-run by me, not cited):

```
$ .venv/bin/python3  (polars 1.38.1)
UNIT : nonnull-mrr=724 / height=3027   ratio=0.2392   (floor >=0.20 -> PASS)
OFFER: height=4079   nonnull-mrr=1352   nonnull-offer_id=1095
offer_id dtype: String (Utf8)   unit.mrr: Float64   offer.mrr: Float64
```

| Band signal | Value (live, first-party) | Band/floor | State |
|-------------|---------------------------|------------|-------|
| **unit nonnull-mrr / height** | **724 / 3027** (ratio **0.2392**) | ratio ≥ 0.20 | **PASS** (the named ~0.239 sold band) |
| **offer nonnull-mrr (1332-class)** | **1352** (of 4079 rows) | ~1332-class, LIVE-VARIANT | **PASS** (1352 ≥ 1332; growth) |
| **gun** (FPC coherence-invariant violations) | **10** | ≤ 15 | **PASS** *(seed-cited; see UV-P)* |
| **coherent** (FPC coherent-cell count) | **593** | ≥ 561 | **PASS** *(seed-cited; see UV-P)* |

> `[UV-P: gun=10 and coherent=593 on the :511 frames | METHOD: cross-repo-fpc-tool
> (S0 PV-gate run 2026-06-11T16:55:49Z; corroborated by IC-SOAK-REANCHOR GO-7 @15:26Z
> which read gun=9 / coherent=581) | REASON: the FPC coherence-invariant lattice
> tooling lives in the autom8y monorepo and is not probable at this receiver,
> production-reads-only station]`. What I DID re-derive first-party here — unit
> 724/3027 ratio 0.2392, offer 1352/4079, offer_id dtype String — stands on the
> live parquets above.

**§2b-S1 — active_mrr denominator (RESET tripwire 62→7): GREEN.** The certified S1
denominator (`62 / $79,485`) reads the **entity-keyed** prefix
`dataframes/1143843662099250/offer/sections/`. Those substrate parquets are dated
`2026-06-09` and are **unchanged** (re-listed by me `2026-06-11`):

```
$ aws s3 ls s3://autom8-s3/dataframes/1143843662099250/offer/sections/ --region us-east-1 --recursive | sort -k1,2 | tail -3
2026-06-09 10:53:54  …/offer/sections/1202005604742382.parquet
2026-06-09 10:55:15  …/offer/sections/1143843662099257.parquet
2026-06-09 11:07:26  …/offer/sections/1201105736066893.parquet
```

Stable substrate → the 62-row denominator holds → **no collapse**.

> **Entity-blind legacy-reader TRAP confirmed live (LOG-class, not S1):** the
> deployed `python -m autom8_asana.metrics active_mrr` (no `--entity-type` on this
> branch) read the **legacy project-entity** prefix `…/1143843662099250/sections/`
> and returned the documented project-entity fossil `value=76685.0 / in_scope=22`
> (`entity: project` per its own provenance block). This is the known
> offline-reader entity-blind fossil — **NOT the S1 active_mrr signal** and NOT a
> collapse. Recorded as a LOG-class observation; the S1 signal is the
> `offer/sections/` denominator above.

**(b) ruling: GREEN** — band in-band; offer + coherent in the GROWTH direction;
S1 substrate stable, no collapse.

---

## §2(c) Alarm states — **GREEN**

Re-run by me `2026-06-11T16:46Z` against AMP `/rules`, workspace
`ws-26b271ef-afd6-4158-82cc-74dbcb273976`:

```
group-names-with-asana: ['slo_asana_receiver', 'slo_asana_receiver_alerts']
AsanaReceiverAvailabilityFastBurn: inactive
AsanaReceiverAvailabilitySlowBurn: inactive
AsanaReceiverHeartbeatAbsent:      inactive
```

All three rules **present** and **`inactive`** (= armed, not firing = healthy). No
rule missing; none firing.

**(c) ruling: GREEN** — the must-arm pair + dead-man are armed and silent.

---

## §2(d) AC-6 cadence — **GREEN**

Re-run by me `2026-06-11T17:01Z`: AMP `query_range`,
`sum(increase(autom8y_asana_receiver_query_outcome_total[30m]))` (PREFIXED — the
unprefixed name returns EMPTY), over the last 24h at `step=1800`:

```
series: 1   points: 47   (start 2026-06-10T17:00Z → end 2026-06-11T17:01Z)
ts (UTC)         value
06-10 17:30      104.7  burst
06-10 18:30       86.5  burst
06-10 19:30      110.9  burst
06-10 20:30      105.9  burst
06-10 21:30      104.9  burst
06-10 22:30      108.9  burst
06-10 23:30      104.9  burst
06-11 00:30       95.3  burst
06-11 01:30      104.9  burst
06-11 02:30       96.8  burst
06-11 03:30       96.8  burst
06-11 04:30       97.8  burst
06-11 05:30       98.8  burst
06-11 06:30       11.1
06-11 08:30      107.9  burst
06-11 09:30       31.2  burst
06-11 10:30      107.9  burst
06-11 11:30      111.9  burst
06-11 12:30       60.9  burst
06-11 13:30      104.9  burst
06-11 14:30        0.0  <-- gap
06-11 15:00        0.0  <-- gap
06-11 15:30        0.0  <-- gap
06-11 16:00     1302.9  *** SYNTHETIC (iris smoke tail, 15:40–15:56Z) — EXCLUDED from organic count ***
06-11 16:30       98.8  burst  <-- ORGANIC RESUME
06-11 17:00        0.0  (between-burst floor, expected)
nonzero buckets: 24 / 47
```

**Cadence judgment (denominator-integrity applied):**
- **Organic bursts** run at the ~hourly `:30` cadence in the ~100-class, with
  zero-floors between (the known pattern, NOT absence): ~19 organic bursts across
  the 24h.
- **The 16:00Z bucket = 1302.9 is the iris synthetic smoke tail** (the 15:40–15:56Z
  pipe-disambiguation drive, ~10× the organic envelope). **LABELED SYNTHETIC and
  EXCLUDED** from the organic-cadence count per the denominator-integrity rule —
  never silently blended into an organic claim.
- The `14:30Z + 15:00Z + 15:30Z` zero-run = the watch-item #10 monolith cadence
  gap (the bursts that prompted the §4 disambiguation). The pipe was proven
  HEALTHY by the iris smoke (counter tracked traffic 1:1, zero `server_error`).
- **The 16:30Z = 98.8 organic burst is the RESUME receipt** — back in the
  ~100-class envelope, post-smoke, with no synthetic assistance. This **CLOSES
  watch-item #10**: the cadence gap was a monolith-side gap (LOG/WATCH), the
  receiver pipe was never dark, and organic cadence has resumed.

**(d) ruling: GREEN (pipe + organic cadence)** — organic burst resumed at
16:30Z=98.8; the 16:00Z spike is labeled synthetic and excluded.

---

## §3 RESET-vs-LOG disposition for Day-1

**No RESET-candidate fired.** Walking the §3 tree against today's live receipts:

| RESET-class trigger | Today's receipt | Fired? |
|---------------------|-----------------|--------|
| active_mrr collapse 62→~7 | offer/sections substrate unchanged (06-09 dated) | NO |
| AC-6 absent + pipe dark under traffic | organic resume 16:30Z=98.8; pipe proven healthy by iris smoke | NO |
| burn-rate SLO ALARM under real traffic | FastBurn/SlowBurn = inactive | NO |
| SLI dark mid-window | HeartbeatAbsent = inactive | NO |
| deploy mid-window | asana main = 49099b12; sole :511 COMPLETED | NO |
| degraded frame persisting > 1 staleness window | unit 16:05Z + offer 16:46Z fresh, in-band | NO |

**LOG-class observations (sre-delegated; day stays GREEN):**
- The named unit-floor calibration WARN (~0.239 vs 0.8 — UK-2 / FPC-Phase-3
  exception): present-as-expected at ratio 0.2392. LOG.
- offer_id dtype = `String`/Utf8 (the Utf8↔Int64 drift cell): observed; the
  Utf8 face is the live state. LOG/WATCH.
- The entity-blind legacy `metrics active_mrr` fossil (76685/22 over the project
  prefix): the documented offline-reader fossil, NOT the S1 signal. LOG.
- S2/S3 SEAM-2 monolith consumers (ad_reporting + payments/mrr): DEFERRED-NOT-OBSERVED. LOG.

---

## Day-1 NOTE (carried forward to the watch)

- **Watch-item #10 (monolith organic-burst cadence gap) — CLOSED** by the
  16:30Z=98.8 organic resume receipt (§2d). The gap (14:30/15:00/15:30 zeros)
  was a monolith-side cadence gap, not a receiver defect; the pipe was proven
  healthy by the iris smoke; organic cadence has resumed within the same hour.
  No cross-repo monolith investigation needed at this time.
- **coherent = 593 is ONE above the certified 579–592 historical envelope, in the
  GROWTH direction** — LOGGED as growth, NOT a degrade. (Seed/cross-repo-cited per
  §2b UV-P; the IC-SOAK-REANCHOR GO-7 read 581/in-band at 15:26Z, so 593 at the
  S0 gate is a same-direction increment, not a regression.) Carry as a WATCH on
  the upper envelope only — a coherent count *below* 561 would be the signal.
- **The 16:00Z=1302.9 AC-6 bucket is SYNTHETIC** (iris smoke). Any Day-2 reader of
  the trailing 24h must continue to label/exclude it until it rolls out of the
  window (~by 16:00Z Day-2).

---

## Verdict

| Section | Receipt | Verdict |
|---------|---------|---------|
| (a) Deploy-freeze | asana main 49099b12; sole :511 COMPLETED; warmer 49099b1 | **GREEN** |
| (b) Band content | unit 724/3027 (0.2392); offer 1352/4079; gun 10; coherent 593; S1 substrate stable | **GREEN** |
| (c) Alarm states | FastBurn/SlowBurn/HeartbeatAbsent all present + inactive | **GREEN** |
| (d) AC-6 cadence | organic resume 16:30Z=98.8; 16:00Z=1302.9 labeled synthetic | **GREEN** |

**DAY-1 VERDICT: GREEN.** No operator ruling required. Clock RUNNING, unreset,
1/7 days attested.

**Rung: soak-day-1-attested (MODERATE)** — sre attesting sre's own watch; the
STRONG is eunomia's rite-disjoint at the `2026-06-18T15:24:21Z` clear seam.
