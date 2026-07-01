---
type: review
status: accepted
artifact_role: critic-verdict
slug: asana-coherence
audits: asana-coherence-case-file.md
head: f4f924d2
date: 2026-06-24
critic_stance: rite-disjoint external (skeptical default)
overall_verdict: CONCUR-WITH-FLAGS
---

# External Critic Verdict — autom8y-asana Ecosystem Coherence

**Audited artifact**: `.ledge/reviews/asana-coherence-case-file.md`
**HEAD**: f4f924d2684386093ef656ecde5e98613cdffce8 (`chore(deps): bump autom8y-core to 4.6.0`) — CONFIRMED at audit time
**Critic role**: RITE-DISJOINT external critic (not a member of the review rite). Default stance: skeptical / refute-first.

---

## GREEN / RED Matrix

| Finding | file:line receipt accurate? | rung honest (not rounded up)? | self-assess capped (G-CRITIC)? | proven-zero from silent telemetry (G-DENOM)? | fork gated on real method? | Verdict |
|---------|---|---|---|---|---|---------|
| H-1 SCAR-REG-001 | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |
| H-2 SCAR-IDEM-001 | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |
| H-3 StatusPush silent-skip | GREEN | GREEN (rung = emitting, NOT alerting) | GREEN | GREEN (prod env-state marked UNVERIFIABLE, not proven-zero) | n/a | **GREEN** |
| H-4 cache_warmer 1437 LOC | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |
| M-1 protocols ~30% overstated | GREEN (file:line correct) | GREEN | GREEN | n/a | n/a | **GREEN-with-flag** (denominator basis) |
| M-5 / FORK-1 deprecated endpoint | GREEN | GREEN | GREEN | GREEN (retire barred on absence-of-evidence) | GREEN (Logs Insights gate w/ recordsScanned>0 condition) | **GREEN** |
| FORK-2 interop orphan | GREEN | GREEN | GREEN | n/a | GREEN (DEFER + watch trigger) | **GREEN** |
| L-1 AIMD fix merged | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |
| L-2 governor-throttle refuted | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |
| Overall grade C (weakest-link) | GREEN | GREEN | GREEN | n/a | n/a | **GREEN** |

**Counts**: GREEN = 10 findings · RED = 0 · flagged = 1 (M-1, non-blocking).

No RED. No pasted RED excerpts required.

---

## Receipt Spot-Checks (independent reads at HEAD f4f924d2)

**H-1 — `reconciliation/section_registry.py:94-107, :128-150`** — VERBATIM CONFIRMED.
Both blocks carry the exact `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotation, reference
`GET /projects/1201081073731555/sections`, and contain visibly sequential placeholders.
Independent count: EXCLUDED_SECTION_GIDS = 4 (`...600`–`...603`), UNIT_SECTION_GIDS = 15
(`...610`–`...624`) → **19 total**. The case file's "19 unverified sequential GIDs" is
ARITHMETICALLY CORRECT (the body line "14" in the :128-150 sub-description undercounts the
UNIT block by one, but the load-bearing headline figure of 19 is right; the
`EXCLUDED_GID_TO_NAME` dict at :153-158 is a separate diagnostic map, correctly excluded
from the routing-frozenset count).

**H-1 rung honesty** — `_validate_gid_set()` (`section_registry.py:47-84`) performs ONLY
format validation + a sequential-placeholder heuristic warning at module import time. It
does NOT call the live Asana API. Therefore the defect is genuinely proven-in-code-only and
the live-Asana confirmation rung is genuinely PENDING. The case file holds H-1 at
"defect proven (in code); live-Asana verification PENDING — NOT proven" and marks it
BLOCKED. **This is NOT rounded up.** Check (2) PASSES.

**H-2 — `api/middleware/idempotency.py:719`** — VERBATIM CONFIRMED. Bare
`except Exception:  # noqa: BLE001 — SCAR-IDEM-001: VERIFY-BEFORE-PROD — finalize failure
means key NOT persisted; a client retry will re-execute the mutation (double-execution
risk)... For S2S callers with strict-once semantics this must be promoted to an error
metric.` The only handler body is `logger.exception(...)` — no `emit_metric`. The case
file's claim ("swallowed, key not persisted, double-execution risk, no CloudWatch metric")
is exact. Rung = "risk proven (defect in code)" — honest.

**H-3 — `services/gid_push.py:498-504`** — CONFIRMED. `if not base_url:` →
`logger.warning("status_push_skipped", ...)` → `return False`. `grep emit_metric` over the
entire file returns NONE. The reciprocal emission claim is corroborated:
`push_orchestrator.py:192-198` emits `StatusPushSuccess`/`StatusPushFailure` via
`emit_metric` — so these ARE structurally unreachable when the early `return False` fires.
The case file correctly grades the observability rung as `emitting` (warning log only) and
does NOT claim `alerting`. Check (2) PASSES.

**H-3 G-DENOM honesty** — The case file states "prod env-config state UNVERIFIABLE from
code alone (G-DENOM)" and frames "Iris observed zero StatusPush* events" as "the MOST
PROBABLE structural explanation," NOT as proof the env var is absent. It does not convert
silent telemetry into a proven-zero. Check (4) PASSES.

**H-4 — `cache_warmer.py`** — CONFIRMED at exactly **1437 LOC** (`wc -l`). Three warm paths
confirmed at :1291-1304 (`entity_types`, `prematerialize_bulk_set`,
`prematerialize_section_set`). Fault-history claim CONFIRMED: dd8e43ab (#141,
"observable AIMD + warm-cycle governor") touched `cache_warmer.py` (+63) and added
`test_warmer_storm_durability.py` (+278); `git show --stat` = "11 files changed, 702
insertions" — exactly as cited.

**M-1 / FORK-2 — `protocols.py:42` + `:44`** — CONFIRMED. Line 42 contains
"Interop covers ~30% of the client surface"; line 44 references
"INTEGRATE-ecosystem-dispatch Section 1.4 for the phased plan." FLAG (non-blocking): the
case file's re-quantification "~14% (2/14 methods)" is partially un-grounded from
protocols.py alone — the file defines only 2 Protocol methods and its migration table lists
4 client methods (2 with interop overlap). The "14" denominator (total DataServiceClient
public methods) is a reviewer assertion not verifiable from this file. Since M-1 is MEDIUM,
is itself a claim that an existing figure is "overstated," and is not load-bearing on any
blocker or on the FORK-2 conclusion (the case file explicitly states the ratio does not
change the fork), the MODERATE grade is acceptable. Flagged for denominator transparency
only.

**M-5 / FORK-1 — `routes/query.py:881, :885`** — CONFIRMED. :881
`response_obj.headers["Sunset"] = "2026-06-01"`; :885 `logger.info("deprecated_query_
endpoint_used", ...)`. `grep emit_metric` over query.py = NONE — confirming the "log-only
signal, no metric" basis. Check (5) PASSES: the FORK-1 retire gate is correctly conditioned
on a real evidence method (Logs Insights aggregation) with an explicit denominator guard —
"Gate PASSES for retire only if (a) recordsScanned > 0 AND (b) zero distinct
caller_service; if recordsScanned = 0, retire remains barred." This is a textbook G-DENOM-
correct gate: retire is NOT licensed by absence-of-evidence.

**L-1** — CONFIRMED merged. dd8e43ab committed 2026-06-19, touches cache_warmer.py.
Rung "fix merged" honest.

**L-2** — CONFIRMED refuted. `_sample_aimd_engaged()` (cache_warmer.py:147-176) is purely
read-only: `getattr` of the read-semaphore stats, returns bool|None, mutates nothing. It
structurally CANNOT zero-output the warmer. The case file's "code-refuted; refutation
proven" is HONEST and the refutation is independently reproducible. Marked closed (not an
open action) — correct.

**Overall grade C** — Weakest-link model is correctly self-labeled
`[PLATFORM-HEURISTIC]` (the B-vs-C boundary) and the median-B / weakest-link-forces-C trace
is internally consistent with the per-category grades. No grade inflation detected.

---

## Check-by-Check Summary

1. **Receipts say what the case file claims** — PASS. Every spot-checked file:line was read
   independently and matches (one harmless undercount in an H-1 sub-line; headline correct).
2. **No rung rounded up** — PASS. H-1 held at proven-in-code / live-diff PENDING / BLOCKED.
   H-3 held at `emitting`, never `alerting`. No finding claims `live` or `protecting-prod`
   without receipt.
3. **No STRONG asserted without external corroboration** — PASS. The case file caps every
   HIGH finding at "MODERATE per G-CRITIC ceiling — self-assessed; external corroboration
   PENDING." No premature STRONG.
4. **No proven-zero from silent telemetry** — PASS. H-3 ("UNVERIFIABLE"), M-4, and FORK-1
   all explicitly invoke G-DENOM and refuse to treat metric silence as proof of zero.
5. **Forks gated on real evidence method** — PASS. FORK-1 gated on Logs Insights with a
   recordsScanned>0 denominator guard; FORK-2 is DEFER with a dated watch trigger.

---

## Findings Cleared to STRONG by Independent External Corroboration (G-CRITIC discharge)

The case file's G-CRITIC ceiling holds each HIGH at MODERATE pending external corroboration.
As a rite-disjoint external critic I have independently reproduced the in-code receipts for
the following. Per G-CRITIC, my independent read is the external corroboration event that
licenses elevating the **in-code defect leg** (NOT the live-runtime leg) to STRONG:

- **H-1 SCAR-REG-001 — in-code defect leg: external corroboration CONFIRMED → STRONG.**
  The 19 sequential placeholder GIDs and the unverified-against-live-API status are
  independently reproduced. NOTE — the *production-correctness* / routing-correctness leg
  REMAINS at PENDING / BLOCKED: STRONG attaches ONLY to "the constants are unverified
  sequential placeholders," NOT to "routing is wrong." The live-Asana diff is still required
  and must NOT be elevated. (Check (2) preserved.)
- **H-2 SCAR-IDEM-001 — in-code defect leg: external corroboration CONFIRMED → STRONG.**
  The swallowed `finalize()`, non-persistence of the key, the explicit double-execution SCAR
  comment, and the absence of an error metric are independently reproduced. The
  production-impact leg for S2S strict-once callers remains BLOCKED pending caller-contract
  review.
- **H-3 push-seam silent-skip — in-code gate leg: external corroboration CONFIRMED → STRONG.**
  The silent `return False` with warning-only and zero `emit_metric` in gid_push.py, plus
  the reciprocal `StatusPush*` emission in push_orchestrator.py, are independently
  reproduced. The prod-env-state leg remains UNVERIFIABLE (correctly).
- **H-4 cache_warmer coupling — external corroboration CONFIRMED → STRONG.** 1437 LOC, three
  paths, and the dd8e43ab fault-history stat (702 insertions / 11 files) are independently
  reproduced.
- **L-2 governor-throttle refutation — external corroboration CONFIRMED → STRONG.**
  `_sample_aimd_engaged()` read-only nature independently reproduced.

These STRONG elevations apply to the EVIDENCE-IN-CODE legs only. The two production-
readiness blockers (H-1 routing-correctness, H-2 S2S double-execution) remain BLOCKED at the
live/runtime rung — elevating the code leg to STRONG does NOT clear the production gate.

---

## Overall Concurrence Verdict

**CONCUR-WITH-FLAGS.**

The case file is evidentially disciplined: every receipt I spot-checked is accurate, no rung
is rounded up, the G-CRITIC self-assessment ceiling is honestly applied throughout, no
proven-zero is drawn from silent telemetry, and both forks are gated on real evidence
methods (not absence-of-evidence). The two production blockers are correctly held at BLOCKED.

The single flag (non-blocking): M-1's "~14% (2/14 methods)" re-quantification carries a
denominator ("14") that is not verifiable from `protocols.py` alone. Recommend the reviewer
either cite the source enumerating DataServiceClient's 14 public methods or soften to a
qualitative "overstated." This does not affect any HIGH finding, the overall C grade, or
the FORK-2 conclusion.

No BLOCKING objection. The artifact may proceed at CONCUR-WITH-FLAGS.
