---
type: review
status: accepted
evidence_grade: STRONG-for-corroborated-items   # rite-disjoint independent re-derivation from own worktree + own parquet pulls + own AMP/log/ECS reads
date: 2026-06-11
station: E1 (verification-auditor) — eunomia-rite "Pre-Clear External Corroboration & Governance Custody"
rite_disjointness: eunomia ⊥ sre ⊥ releaser (Axiom-1 critic-rite-disjointness; this station did NOT author the claims under audit)
substrate: origin/main 49099b12 (sole :511, src-IDENTICAL to game-day-proven 3a59c72/:510)
worktree: /tmp/e1-corrob (detached @ 49099b12; REMOVED at close)
verdict_pair: "method-SOUND-with-findings × day-1-CORROBORATED"
governs_corroboration_of:
  - .ledge/decisions/SOAK-DAY-1-ATTESTATION-telos-soak-2026-06-11.md
  - .ledge/decisions/SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md
  - ADR-warmer-path-preserve-enforcement-2026-06-11 / #128 convergence
  - 2026-06-11 keystone game-day (releaser, on :510)
---

# EUNOMIA INTERIM CORROBORATION — keystone game-day + day-1 attestation

> **CEILING: day-1-CORROBORATED. This corroboration does NOT and CANNOT issue
> `soak-CLEARED`; the 06-18 STRONG is clock-gated and reserved even from this
> station.** The clock, anything that resets it, and the
> `2026-06-18T15:24:21Z` STRONG seam stay clock-gated. What this artifact
> establishes is the day-1 substrate, re-derived rite-disjoint and BEFORE the
> clock needs it — not the soak's terminal verdict.

> **GRANDEUR.** Every claim below is re-derived from THIS station's OWN worktree
> (`/tmp/e1-corrob` @ `49099b12`), OWN parquet pulls (`/tmp/e1-band`), OWN AMP
> queries, OWN log reads, and OWN mutation-REDs — NEVER the producer's numbers.
> The producers' figures entered this audit as HYPOTHESES; they leave it as
> independently-confirmed receipts.

---

## VERDICT PAIR

| Axis | Verdict |
|------|---------|
| **Method** | **method-SOUND-with-findings** — the sentinel protocol's four receipt sections all execute as written by a stranger and yield decidable rulings. Three method findings (1 friction, 2 cosmetic/blindspot); ZERO blocking-defects. |
| **Day-1 receipts** | **day-1-CORROBORATED** — all five claim families (One-Gate convergence, mutation-recursion, band, sentinel-dogfood, game-day) independently re-derived. ZERO DISPUTES. ZERO RESET-ADJACENT findings. |

No OPERATOR ATTENTION dispute fired. One etag-vs-md5 reconciliation is recorded
as CORROBORATED-WITH-NOTE (not a dispute — see §5).

---

## ITEM 1 — One-Gate convergence: re-grep + structural re-derivation

`git grep -n "memory_tier\.get\|memory_tier\.put"` over `src/` in the worktree:

| Hit | Site |
|-----|------|
| `dataframe_cache.py:323` | `memory_tier.put` (S3-hit hydrate, normal serve) |
| `dataframe_cache.py:376` | (docstring reference only) |
| `dataframe_cache.py:391` | **`memory_tier.get` — the SOLE serve-side read, INSIDE `_memory_get_serviceable`** |
| `dataframe_cache.py:463` | `memory_tier.put` (circuit-LKG S3 hydrate) |
| `dataframe_cache.py:871` | `memory_tier.put` (put-path promote) |

| Producer claim | My derivation (file:line @ 49099b12) | Verdict |
|----------------|--------------------------------------|---------|
| sole `memory_tier.get` in src/ inside `_memory_get_serviceable` | `memory_tier.get` appears EXACTLY once (`dataframe_cache.py:391`), inside `_memory_get_serviceable` (def at `:365`) | **CORROBORATED** |
| serve fan-in converges on the accessor | TWO callers: `:297` (normal serve via `get_async` → `_check_freshness_and_serve`) and `:433` (circuit-LKG, the 4th serve path). No other serve path reads memory. | **CORROBORATED** |
| `write_decision` threaded into `section_persistence.py` w/ backstop-REFUSE @ ~:905-918 (pop_degraded=True + write_decision=None + non-empty df → REFUSED) | `section_persistence.py:905`: `if population_degraded is True and write_decision is None and not df.is_empty():` → emits `ungated_below_floor_write_refused`, returns True (preserve-on-disk). PRESERVE early-return at `:885`. | **CORROBORATED** (claim path said `builders/section_persistence.py`; actual file is `src/autom8_asana/dataframes/section_persistence.py` — minor path-imprecision, lines exact) |

The convergence-completeness claim holds: ONE gated serve accessor (`_memory_get_serviceable`),
ONE physical write choke (`write_final_artifacts_async`) honoring `WriteDecision`
+ a backstop guard for orphan/no-decision writers.

---

## ITEM 2 — Two mutation-REDs (recursive proof, write-side + serve-side)

Baseline: all 3 files **22 GREEN** in the worktree before mutation
(`6 + 7 + 9`), and **22 GREEN restored** after every revert. Worktree
`git status --porcelain src/` CLEAN at close (no residual mutation).

### Mutation 1 — WRITE-SIDE (PRESERVE early-return neutralized)
`section_persistence.py:885` `if write_decision is WriteDecision.PRESERVE_PRIOR_GOOD:`
→ `if False:`. Re-ran `test_warmer_preserve_enforcement.py`:

```
2 failed, 4 passed
FAILED test_warmer_preserve_enforced_under_revoked_grant
FAILED test_warmer_preserve_offer_isolated
E   AssertionError: assert (3 - 3) == 3      # persisted 0/3 — degraded frame OVERWROTE prior-good
...captured log under mutation:
{"event":"final_artifacts_written","extra":{"row_count":3,"index_written":false,...}}   # the write FIRED where PRESERVE must SKIP
```
This is the game-day 0/N symptom reproduced in isolation: PRESERVE decided
upstream, NOT enforced at the write site → prior-good clobbered. Reverted →
**6 GREEN**.

### Mutation 2b — SERVE-SIDE (degrade-detector blinded)
`dataframe_cache.py:363` `_is_population_degraded_entry` body
`return getattr(entry,"population_degraded",False)` → `return False`. Re-ran
`test_warmer_preserve_serve_altitude.py`:

```
2 failed, 5 passed
FAILED test_preexisting_poisoned_memory_entry_self_corrects_on_serve     # normal serve path
FAILED test_circuit_open_lkg_serves_prior_good_not_poisoned_memory       # circuit-LKG path
E   AssertionError: circuit-LKG served the poisoned 0/3 hot entry under circuit-open
    instead of soft-rejecting population_degraded and rehydrating the prior-good 3/3 from S3
```
Both serve paths surfaced the poisoned 0/3 from the hot tier instead of
rehydrating the prior-good 3/3 — the serve-side soft-reject is load-bearing on
BOTH the normal-serve and circuit-LKG paths. Reverted → **7 GREEN**.

> **KNOW-CANDIDATE (serve-gate load-bearing surface).** A FIRST serve-side
> mutation (returning the raw `memory_tier.get` from `_memory_get_serviceable`,
> bypassing the soft-reject) turned only the circuit-LKG test RED — NOT the
> normal-serve poisoned test. Reason: the normal `get_async` path applies
> `_check_freshness_and_serve` AFTER the accessor, so a bypassed soft-reject is
> masked by the freshness gate on the normal path; the circuit-LKG path serves
> on `_schema_is_valid` ALONE and so is the path where the soft-reject is the
> SOLE guard. Blinding the detector itself (Mutation 2b) breaks both. The
> serve-side gate is genuinely defence-in-depth, not redundant.

---

## ITEM 3 — Band re-derivation (first-party, fresh `aws s3 cp` + polars 1.38.1)

Live S3 HEAD (pulled by me, this session):
```
unit  : etag 38aa29357b0c5a8072ff95e5e81ab6d7  200118 B  lastModified 2026-06-11T16:05:57Z
offer : etag f4a4cf8268b9d7adb8c71a217a3f2751  237858 B  lastModified 2026-06-11T16:46:54Z
```
(Both etags/sizes/mtimes IDENTICAL to day-1's recorded values → the frames are
unchanged since day-1 authoring.)

| Band signal | Producer / day-1 | My first-party derivation | Floor | Verdict |
|-------------|------------------|---------------------------|-------|---------|
| unit nonnull-mrr / height | 724 / 3027 (0.2392) | **724 / 3027  ratio 0.2392** | ≥0.20 | **CORROBORATED** |
| offer nonnull-mrr | 1352 (of 4079) | **1352 / 4079** (nonnull-offer_id 1095) | 1332-class | **CORROBORATED** (1352≥1332) |
| offer_id dtype | String (Utf8) | **String** | Utf8↔Int64 watch | **CORROBORATED** |
| gun (om-notnull & um-null) | 10 | **10** | ≤15 | **CORROBORATED** |
| coherent (both-notnull) | 593 | **593** | ≥561 | **CORROBORATED** |

> **Stronger-than-claimed result.** Day-1 seed-CITED gun=10/coherent=593 as
> cross-repo FPC-tool values under a `[UV-P: … METHOD: cross-repo-fpc-tool |
> REASON: lattice primitive not probable at receiver station]` marker. I
> **re-derived both FIRST-PARTY** at this station via the canonical
> `office_phone` group-by-max + inner-join (2263 joined rows) and landed EXACTLY
> on 10 / 593. The UV-P deferral is DISCHARGED for the day-1 figures: what was
> labeled un-probable here was, in fact, probable and confirmed. Counts are
> LIVE-VARIANT vs game-day (unit grew 3021→3027); compared against FLOORS, all
> PASS in the growth direction.

---

## ITEM 4 — Sentinel dogfood: four receipt sections executed AS WRITTEN

Ran each section's commands literally, as a stranger would:

### §2(a) Deploy-freeze — **GREEN**
```
$ env -u GITHUB_TOKEN gh api repos/autom8y/autom8y-asana/commits/main --jq .sha
49099b120e6292e44fb24ce79d5ae35007e10792                       # exact, clock NOT suspect
$ aws ecs describe-services … --query 'services[0].deployments[*]…'
[ { "td": …/autom8y-asana-service:511, "roll":"COMPLETED","desired":1,"running":1 } ]   # SOLE :511
$ aws lambda get-function … --query Code.ImageUri
…/autom8y/asana:49099b1                                         # warmer lockstep
```

### §2(b) Band — **GREEN** (= Item 3; re-used the same first-party pulls)
unit 724/3027 (0.2392), offer 1352/4079, gun 10, coherent 593. S1 substrate
(`offer/sections/` 06-09 dated) re-listing not re-run here (carried by day-1 +
covered by the offer-frame stability); no collapse signal.

### §2(c) Alarm states — **GREEN**
```
AsanaReceiverAvailabilityFastBurn inactive
AsanaReceiverAvailabilitySlowBurn inactive
AsanaReceiverHeartbeatAbsent      inactive          # groups: slo_asana_receiver(+_alerts)
```
All three present + inactive (armed, not firing). None missing.

### §2(d) AC-6 cadence — **GREEN**
Fresh 24h `query_range`, PREFIXED `autom8y_asana_receiver_query_outcome_total`,
`step=1800` (window ~06-10T18:30Z → 06-11T18:43Z):
- **20 organic ~100-class bursts** at hourly `:30` cadence, zero-floors between (known pattern).
- `16:00Z = 1302.9` **LABELED SYNTHETIC** (iris-smoke, ~10× envelope) and EXCLUDED (denominator-integrity).
- **Fresh organic bursts at 16:30Z=98.8, 17:30Z=106.9, 18:30Z=112.9** — cadence has CONTINUED healthy for ~1.7h past day-1 authoring. Day-1's 14:30/15:00/15:30 gap rolled out of my window.

### Serve-altitude READ-ONLY re-run (Item-5 cross-check)
`initialize_dataframe_cache()` wired a REAL `S3DataFrameStorage` (bucket
autom8-s3, is_available=True). Top-level `cache.get_async("1201081073731555","unit")`
returned **None** (the bare call lacks a live `current_watermark`, so
`_check_freshness_and_serve` rejects as stale). The underlying tier read
`progressive_tier.get_async` returned the live frame **height=3027, watermark
16:05:56Z** through `SectionPersistence → S3DataFrameStorage`.
**Precise statement: the SERVE PATH works** (S3-tier read succeeds, returns
TODAY's 3027-class frame) — this corroborates the serve PATH, NOT the historical
723 number. (Day-1 derived band from `aws s3 cp`+polars, which I corroborated in
Item 3; it did not rely on a live `get_async`.)

---

## ITEM 5 — Game-day artifact re-derivation (/tmp/key-r2 + warmer logs)

### Artifact content (md5 + byte-diff + polars)
| Artifact | md5 | size | polars |
|----------|-----|------|--------|
| unit_priorgood.parquet | `8eb2d94b2af60716e71fe7abab330f4f` | 168087 B | 723 / 3021 |
| unit_underfault.parquet | `8eb2d94b2af60716e71fe7abab330f4f` | 168087 B | 723 / 3021 |
| unit_rehealed.parquet | `2b37ed7fdf5403613f0cf3d82a6a99fa` | 199653 B | 723 / 3021 |

```
$ cmp unit_priorgood.parquet unit_underfault.parquet
BYTE-IDENTICAL
```

| Producer claim | My derivation | Verdict |
|----------------|---------------|---------|
| S3 unit object UNTOUCHED under fault | priorgood ≡ underfault **BYTE-IDENTICAL** (md5 `8eb2d94b…`), both 168087 B | **CORROBORATED** (the central game-day claim) |
| priorgood 723/3021, underfault 723/3021 IDENTICAL | 723/3021 each, byte-identical | **CORROBORATED** |
| size 168087 B | 168087 B exact | **CORROBORATED** |
| rehealed 723/3021 | 723/3021 (md5 `2b37ed7f…`, 199653 B) | **CORROBORATED** |
| priorgood etag `e4317556…` | my **md5** is `8eb2d94b…` (≠ etag) | **CORROBORATED-WITH-NOTE — NOT a dispute** |

> **etag-vs-md5 reconciliation (CORROBORATED-WITH-NOTE).** The producer cited
> `e4317556e0b479abd41163e658ed7f30` as the S3 **etag**; my whole-file **md5** is
> `8eb2d94b…`. For multipart S3 uploads, etag = md5-of-part-md5s + "-N" ≠
> whole-file md5; a single-part etag would equal md5. The divergence means
> either the historical object was multipart, or the local artifact is a
> re-serialization of the same logical content. The **load-bearing claim —
> content identity under fault (priorgood ≡ underfault, byte-identical,
> 723/3021, 168087 B) — is fully corroborated**; the etag STRING itself is NOT
> re-derivable (the historical S3 object is gone — live unit is now
> `38aa2935…`/200118 B/3027 rows). I do not DISPUTE the etag because the claim it
> backs (untouched-under-fault) is independently confirmed by the byte-diff. This
> is a provenance note, not a RESET-adjacent finding.
> `[UV-P: historical priorgood S3 etag e4317556… | METHOD: not-re-derivable (object superseded by live 38aa2935…) | REASON: content-identity claim corroborated by byte-diff; etag-string is S3 metadata of a now-gone object]`

### Warmer logs — `/aws/lambda/autom8-asana-cache-warmer`, window 14:30–15:00Z 2026-06-11
```
fail_closed_write_preserve_prior_good          @ 2026-06-11T14:45:25.241663Z
  reason: below_floor_wholesale_durable_read_outage   trace_id 743d52ade6da49a529fbc240319a98c1
fail_closed_write_preserve_prior_good_enforced @ 2026-06-11T14:45:25.242268Z
  reason: converged_gate_skipped_save_dataframe_at_write_site   (same trace_id, +605µs)
```
| Producer claim | My derivation | Verdict |
|----------------|---------------|---------|
| `…preserve_prior_good` @14:45:25.241Z | `…241663Z`, reason wholesale-outage | **CORROBORATED** |
| `…preserve_prior_good_enforced` @14:45:25.242Z | `…242268Z`, reason gate-skipped-save-at-write-site | **CORROBORATED** |
| `durable_task_cache_read_gid_failed` count 3021 | **3027 total events / 3021 DISTINCT gids** | **CORROBORATED** (3021 = gid-cardinality = the frame population; 6 retried gids) |
| `final_artifacts_written` count 0 in window | **0** | **CORROBORATED** |

---

## METHOD FINDINGS (sentinel protocol critique, 11-lens style)

| # | Finding | Class | Detail |
|---|---------|-------|--------|
| **MF-1** | **§2(a) deploy-freeze is a point-in-time snapshot — blind to a merge that deploys AND self-reverts BETWEEN daily attestations.** | **friction (blindspot)** | The dispatch asked precisely this. §2(a) checks `HEAD==49099b12` + sole `:511 COMPLETED` instantaneously. A mid-window deploy of a new task-def that later reverts to `:511` would leave both probes GREEN at attestation time. The ECS event/deployment-timestamp history (e.g. the `15:24:21Z` steady-state event = the #129 deploy I observed) is the only durable evidence of a transient deploy, and §2(a) does NOT instruct the attester to read `services[0].events` or compare deployment `createdAt` against the prior attestation. **Recommend:** add an §2(a3) — "diff ECS `deployments[].createdAt` and `events[]` against the prior day's attestation; any new deployment event in the window = RESET-class even if HEAD is back to 49099b12." This blindspot already bit once (the #129 deploy raced the 14:59 anchor → re-anchor to 15:24:21Z; §3 records "bit 3× on 2026-06-11"). |
| **MF-2** | **§2(b) declares gun/coherent "not first-party re-derivable at this station" and mandates a UV-P cross-repo label — but they ARE first-party re-derivable from the two parquets via the canonical office_phone join.** | **cosmetic (over-cautious provenance)** | I re-derived gun=10/coherent=593 first-party in one polars block from the same `unit`/`offer` parquets §2(b) already pulls. The FPC lattice TOOL lives cross-repo, but the gun/coherent COUNTS for these two entities are a pure function of the two frames. **Recommend:** §2(b) may upgrade gun/coherent from "carry cross-repo + UV-P" to "first-party re-derive via the canonical join" (the FULL 82-cell lattice remains cross-repo; the 2-frame coherence counts do not). Lowers the station's dependence on a cross-repo seed. |
| **MF-3** | **Protocol pins WHO/WHERE well, but the §4 disambiguation command path assumes a non-stale local checkout.** | **cosmetic (stale-tree trap)** | §4's iris pipe-smoke runs `.venv/bin/python3 scripts/canary/receiver_bulk_fanout_deploy_gate.py` from the local tree. The local tree here is a PRE-SAGA branch (`cr3/gate2-receiver-probe-and-durability`, HEAD `3bbb9bc8`) — a stranger running §4 from the local checkout could execute a stale gate script. §2(a)/§6 pin the SUBSTRATE identity (49099b12) but not the OPERATOR's checkout state. **Recommend:** §0 add a one-line preflight — "run §4 from a worktree at `origin/main`, or `git -C . rev-parse HEAD` and confirm against 49099b12 before driving the canary." (I deliberately ran all CODE from `/tmp/e1-corrob` @ 49099b12, never the stale local tree, per dispatch.) |

**RESET-vs-LOG tree decidability (stranger test): PASS.** Walking §3 against my
live receipts, every branch was boolean-decidable without interpretation: no
active_mrr collapse, no AC-6 dark, no burn-rate firing, no SLI dark, no deploy
mid-window (modulo MF-1's snapshot caveat), no degraded-frame persistence. The
tree routed cleanly to "none of the above → LOG-class → GREEN." The LOG-class
exceptions (unit-floor 0.239 WARN, offer_id Utf8↔Int64, SEAM-2 deferred) are all
named and matched my observations.

---

## DISPUTES

**NONE.** Zero RESET-ADJACENT findings. The single etag-vs-md5 item (§5) is a
CORROBORATED-WITH-NOTE provenance reconciliation — the claim it backs
(untouched-under-fault) is independently confirmed by the byte-diff, so no
side-by-side OPERATOR ATTENTION dispute is raised.

---

## TEST-PRESERVATION + REVERTIBILITY POSTURE (execution-altitude note)

This is a CORROBORATION station, not a consolidation audit — no commits were
authored, staged, or reverted (per the strict-impossibilities grant). Test
preservation IS attested: the 22 #128-contract tests (`6+7+9`) were GREEN at
baseline, RED under each targeted mutation, and GREEN again after every revert,
with the worktree `src/` byte-clean at close. The mutation-REDs ARE the
revertibility proof at the gate level: each gate, when removed, is independently
falsifiable by the test contract.

---

## §6 EVIDENCE GRADE

**STRONG-for-corroborated-items** — every CORROBORATED row rests on rite-disjoint
INDEPENDENT re-derivation: my own worktree git-grep + file-reads, my own
mutation-REDs run in my own ephemeral venv, my own `aws s3 cp` + polars, my own
AMP `query_range`/`/rules`, my own CloudWatch `filter-log-events`, my own ECS
`describe-services`. No producer number was trusted; each was re-computed. This
EXCEEDS the day-1 MODERATE ceiling precisely because it is rite-disjoint (the
day-1 cap was "sre attesting sre's own watch"; this is eunomia re-deriving sre's
and the releaser's claims independently — the §SOAK-SENTINEL §6 design that
"the STRONG is eunomia's, rite-disjoint").

**CEILING RE-AFFIRMED: day-1-CORROBORATED.** This STRONG attaches to the day-1
substrate ONLY. It does NOT touch the clock, does NOT reset it, and does NOT
issue `soak-CLEARED`. The 06-18 STRONG seam remains clock-gated and reserved.

**Rung set:** `keystone-and-day1-rite-disjoint-corroborated` (STRONG, day-1-scoped).
