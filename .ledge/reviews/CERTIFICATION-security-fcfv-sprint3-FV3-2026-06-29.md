---
type: review
status: accepted
verdict: FV-3-PASS (STRONG)
schema_verdict: Approve
slug: fcfv-sprint3-ob-guide-attestation
rite: security
station: N3 security-reviewer (rite-disjoint critic of record)
build_commit: 174518c71a5b7690fd242f32cd3072b71157d684
date: 2026-06-29
---

# FV-3 CERTIFICATION — OB-guide byte-exact tenant-isolation (North Star Family Chiropractic, N=1)

> forwarding-cutover-first-value · sprint-3 OB-GUIDE · security-rite FV-3 · security-reviewer (N3) · 2026-06-29
>
> **Honest rung (VERBATIM):** `byte-exact-verified (qa MODERATE) → security-FV-3-corroborated (STRONG) ← HERE + STAGED — NOT attached, NOT live, NOT first-value-realized; the LIVE attach + every Tier-B lever operator-terminal; PT-02 HALT stands.`

## §1 Verdict

**FV-3-PASS (STRONG)** for the **N=1 byte-exact-verified + staged** rung.

Schema-envelope mapping (`security-verdict.schema.yaml`): **Approve** — `blocking_findings: []` (no blocking finding for the N=1 staged artifact); `signoff_conditions` = the §7 watch-items, all flip-gating / NONE merge-blocking; `risk_acceptances` = T7 (live phone-resolve tenant-selection) carried out-of-N=1-scope, MC-2 #725-gated. The SI-5 recede gate is satisfied: this is a non-blocking verdict, so the if/then clause (`verdict ∈ {Request-Changes, Reject} → blocking_findings REQUIRED`) does not fire.

**Why STRONG, not MODERATE.** 10x-dev self-capped at MODERATE per `self-ref-evidence-grade-rule` (build-rite cannot lift its own grade). The STRONG lift is established here by the **rite-disjoint critic of record** (N3 security-reviewer), corroborated by three further rite-disjoint N2 lenses (threat-modeler / penetration-tester / compliance-architect). Two independent pillars carry the grade:

1. **Independent re-mint convergence** — the grandeur address was reproduced byte-for-byte by a re-mint executed in this critic's own session (not read from the build artifact), and N1 independently reproduced the full-render `sha256 cc1702124d3af095288da75c37596cf7760f6b302c442485cf47665ba74f2644 / 1047203 bytes` rite-disjointly. `harvested == {independent mint}`, exactly one.
2. **Producer-independent teeth (AC-3)** — the non-vacuity of the oracle was re-proven here by tautology mutation: gutting the oracle makes the AC-3 RED arm FAIL ("DID NOT RAISE"), demonstrating the test bites on broken INPUT, not on a green suite alone (`discriminating-canary-doctrine` §2.3; G-THEATER averted).

Per `evidence-grade-vocabulary` STRONG-domain + `external-critique-gate-cross-rite-residency` Axiom 1 (critic-rite-disjointness), the rite-disjoint corroboration discharges the external-concurrence requirement for STRONG at this rung.

## §2 Coverage attestation (review focus areas × depth)

| Focus area | Exercised | Depth | Receipt |
|------------|-----------|-------|---------|
| Authorization / tenant-isolation | YES | re-mint + byte-diff oracle + AC-3 teeth | §3 / §4 |
| Input validation (mint gate) | YES | §6 fail-closed ValueError ×3 + ALT-v4 | §4 |
| Crypto / integrity | YES | sha256 digest receipt (N1) + AC-7 | §4 |
| Data handling / PII (PHI routing addr) | YES | compliance lens (HIPAA/SOC2 scoped) | §5 |
| Error handling / fail-open | YES | producer fail-closed + opt-in OFF | §4 / §6 |
| Live-path residual (out-of-scope) | FLAGGED | T7 grounded by source receipt | §6 |

## §3 Build / source anchors (spot-verified, not rubber-stamped)

| Anchor | Value | Verification (this critic) |
|--------|-------|----------------------------|
| worktree HEAD | `174518c71a5b7690fd242f32cd3072b71157d684` | `git rev-parse HEAD` |
| branch | `feat/fcfv-sprint3-ob-guide-attestation` | `git rev-parse --abbrev-ref HEAD` |
| build commit subject | `feat(onboarding): byte-exact OB-guide forwarding-address attestation for North Star pilot (N=1)` | `git log --oneline -1` |
| worktree state | CLEAN (no staged/unstaged) | `git status --porcelain` empty |
| autom8y-core | `4.9.0` | `importlib.metadata.version('autom8y-core')` → `4.9.0` |
| mint gate import path | `autom8y_core.helpers.routing.format_routing_address` | imported live (re-mint below) |
| test file committed blob | `7e6dcf35023ef20d22bb037a26a72965ad10fe60` | `git rev-parse HEAD:tests/unit/automation/workflows/test_onboarding_walkthrough.py` |

## §4 Disjoint GREEN/RED matrix — N1 ruling + N3 spot-verification receipts

### 4.1 Independent re-mint convergence (N3, this session)

```
MINT: d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com
MATCH_GRANDEUR: True
ALT_V4_MINT: b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com
```

`format_routing_address("d167d635-1468-4ad5-9f88-8d44c8a4d1a9")` == the grandeur address, byte-for-byte. This is the right clinic (CRR-1 guid), minted DIRECTLY from the held guid — never phone- or name-resolved (G-DENOM, positive selection).

### 4.2 Full-render byte-exact (N1 receipt — recorded, not re-derived by N3)

| Field | Value |
|-------|-------|
| FROZEN_SHA256 | `cc1702124d3af095288da75c37596cf7760f6b302c442485cf47665ba74f2644` |
| FROZEN_BYTES | `1047203` |
| PRESENCE(expected) | `True` |
| HARVESTED | `{'d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com'}` (exactly one) |

N1 reproduced this sha256 rite-disjointly. The frozen deck is ephemeral/gitignored; the sha256 is the durable receipt. N3 did not re-render the full deck (out of spot-verify scope); N3's re-mint + the AC-3 teeth re-fire corroborate the load-bearing tenant-correctness claim the digest stands on.

### 4.3 §6 mint-gate fail-closed (N3, this session) — REFUSED ×3

```
REFUSED(ValueError) '7639994340':            format_routing_address requires a canonical lowercase UUID v…
REFUSED(ValueError) '+17156902466':          format_routing_address requires a canonical lowercase UUID v…
REFUSED(ValueError) 'North Star Medical Clinic': format_routing_address requires a canonical lowercase UUID v…
```

The §6 name-collision / phone substrate is **structurally unable to mint** a routing address — phone, E.164, and clinic-name inputs each raise `ValueError`. There is no path from a human-typed name or phone to a minted address.

### 4.4 ObGuide attestation suite (N3, this session) — GREEN

```
uv run --no-sync --extra dev pytest …test_onboarding_walkthrough.py -k ObGuide -p no:xdist -o addopts="" -q
→ 14 passed, 20 deselected in 0.69s
```

N1 full-file receipt: **33 passed, 1 skipped** (the skip is the legitimate `@integration` live-resolve gated on `AUTOM8Y_DATA_URL` — a reserved lever, untouched).

### 4.5 AC-3 tautology-mutation re-fire (N3, this session) — THE TEETH (non-vacuity)

Procedure: weaken `assert_byte_exact_tenant_address` (test:582-588) to a tautology (neuter presence + exclusivity so it can never raise), run the AC-3 pair, then `git restore`.

```
.F                                                          [100%]
___ TestObGuideByteExactAttestation.test_ac3_red_wrong_but_canonical_caught ____
>           with pytest.raises(AssertionError):
E           Failed: DID NOT RAISE <class 'AssertionError'>
tests/unit/automation/workflows/test_onboarding_walkthrough.py:709: Failed
1 failed, 1 passed, 32 deselected in 0.40s
```

Under the gutted oracle: AC-3 RED **FAILS** ("DID NOT RAISE") — the wrong-but-canonical `b167331c-…` render slipped through; AC-3 GREEN trivially passes. Restored:

```
RESTORED_BLOB: 7e6dcf35023ef20d22bb037a26a72965ad10fe60
MATCH_COMMITTED: YES
git status --porcelain: <empty>
```

**Interpretation (G-THEATER):** the verdict rests on broken-INPUT teeth. The AC-3 RED breaks the INPUT (feeds a DIFFERENT valid v4 the producer happily injects — same 1047203-byte shape, only the 36-char address differs) and the SAME oracle that PASSES on `d167d635` RAISES on `b167331c`. The teeth are **producer-independent**: the oracle can disagree with the producer. The surface is never broken. A green suite alone is rejected.

### 4.6 Oracle / harvester strictly-weaker (N3 source inspection)

- Harvester `_APPOINTMENT_ADDR_RE` (test:554-556) = `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@appointments\.contenteapp\.com` — unanchored, accepts ANY hex in every slot. Provable **superset** of the producer's `CANONICAL_ADDR_RE` (`inline-dc-runtime.mjs:115-116`, anchored `^…$` + v4 nibble `4` + variant `[89ab]`) ⇒ NOT a reimplementation. Verified by `test_harvester_strictly_weaker_than_canonical_addr_re` (PASS).
- `assert_byte_exact_tenant_address` (test:569-588) = presence + exclusivity; `expected` minted INDEPENDENTLY (test:696, `test_ac3_green_byte_equal_independent_mint`).
- AC-6 static grep-zero (`test_ac6_oracle_source_has_no_live_attach_no_phone_or_name_resolution`, PASS): oracle source carries no `upload_async` / `resolve_routing_address_by_phone` / `resolve_routing_address_by_name` / `nameparser`.

### 4.7 Staged attach / DARK / GATE-1 (N1, corroborated)

Staged attach is guid-structured (`TENANT_BINDING: guid d167d635-…`, PREFERRED, zero re-resolution; phone fallback only; NEVER name). DARK held: opt-in flag `AUTOM8_WALKTHROUGH_ENABLED` unset (`TestOptInKillSwitch::test_unset_flag_disables` PASS → unset MUST disable, opt-in safe-default); no `upload_async`; `/Users/tomtenuta/Code/autom8/.env` never read or staged; N=1.

## §5 N2 dispositions (rite-disjoint corroboration, MODERATE)

| Lens | Disposition | Substance |
|------|-------------|-----------|
| **threat-modeler** | **CORROBORATE (MODERATE) + T7 flag** | STRIDE T1–T6 mitigated-by-construction (strict-v4 mint / producer fail-closed / oracle producer-independent / harvester-weaker / opt-in-OFF / staged-DARK). §6 name-collision structurally unable to mint. G-DENOM positive-selection holds. **T7** = non-blocking watch-item (see §6). |
| **penetration-tester** | **CORROBORATE (MODERATE)** | All 5 probes BLOCKED mitigated-by-construction: (1) name-resolution — no name resolver exists; (2) wrong-but-canonical→attach — attach target is an enumeration task-gid constant, not deck-derivable; (3) oracle-bypass — 12-candidate gate + 20,000-address property test, dangerous quadrant (producer-ACCEPT ∧ harvester-MISS ∧ wrong-tenant) = ∅; (4) `client_name` injection — 6 hostile renders neutralized by `escapeScriptContent`+`assertScriptBalance`, addr stays grandeur; (5) mint-injection — 20/20 adversarial guids raise ValueError. No reachable wrong-tenant / live-attach path. |
| **compliance-architect** | **CORROBORATE (MODERATE)** | Auditable PHI tenant-isolation control — HIPAA §164.312(a)(1) access-control + (c)(1) integrity; SOC 2 CC6.1/CC6.6-6.7/PI1.x — **scoped to the routing-address-correctness boundary**, NOT wholesale HIPAA coverage. Durable (committed AC tests + sha256), positively-selected (AC-3 producer-independent teeth = anti-theater keystone), deterministic + rite-disjoint-reproduced. 5 watch-items, none blocking (see §6 G-A..G-E). |

Convergence is rite-disjoint and unanimous: N1 CONVERGED; all three N2 lenses CORROBORATE; the single T7 flag is correctly out-of-N=1-scope. Per G-HALT this is **FV-3-PASS, not REFUSED**.

## §6 CERTIFICATION BOUNDARY (explicit + honest)

FV-3 **certifies**: the **N=1 staged artifact's tenant-correctness** — the guid-held, directly-minted, byte-verified, DARK deck for North Star Family Chiropractic carries the byte-exact `d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com` ≡ `format_routing_address(CRR-1 guid)`, with producer-independent oracle teeth and no path to a wrong-tenant address or live attach in the attested path.

FV-3 **does NOT certify**: the **live phone-resolve tenant-selection path at fleet scale (T7)** — the sharpest pre-fleet-flip residual. Grounding receipt (N3 source inspection):

- `workflow.py:221` — `gated_address = await self._resolver.resolve_routing_address_by_phone_async(...)` selects the tenant by **PHONE at runtime** with NO oracle / NO known-`expected`.
- `producer.py:141` — `if gated_address.encode("utf-8") not in frozen: raise ProducerFreezeError(...)` is **presence + shape** (`CANONICAL_ADDR_RE`) only. It confirms the *resolved* address is present; it does **not** bind that address to the *correct tenant*. The byte-exact oracle (which binds to an independently-minted `expected`) is an **attestation-time** control with no runtime analogue on the live path.

Consequence: a phone-collision (latent `business.py:192 .first()`, no `ORDER BY` / no `UNIQUE` — EBI F-002) could let a canonical-but-wrong-tenant address sail through the live path AT SCALE. **Correctly contained today** — MC-2 #725 opt-in-OFF; the resolver is MOCKED in all 33 unit tests; only the `@integration` live-resolve test exercises it and it is SKIPPED — and **structurally OUTSIDE** the guid-held N=1 attested path. This is a broad-rollout watch-item for operator/sprint-5, **NOT an N=1 blocker**.

## §7 Consolidated watch-items (routed to operator / sprint-5 — NONE blocking N=1)

**T7 — live runtime tenant-binding (headline residual)** + 4 triggers before any fleet flip:
1. Add a runtime tenant-binding assertion to the live workflow (the runtime analogue of the oracle — assert the frozen local-part == the resolved guid).
2. Discharge the `.first()` non-uniqueness — `UNIQUE(office_phone)` OR deterministic `ORDER BY` + collision-refuse.
3. Un-skip the `@integration` resolve test against a real fixture.
4. Constrain office_phone edit ACL / treat the Asana task field as untrusted input.

**Compliance G-A..G-E** (compliance-architect, none blocking):
- G-A: live-attach audit trail absent (operator-future).
- G-B: fleet-scale isolation not proven (MC-2 #725, out-of-scope for N=1).
- G-C: no machine-checkable `risk_reference` to a threat-model entry.
- G-D: severity-class not formally stamped.
- G-E: the sha256 is toolchain-pinned — the toolchain-ROBUST invariant is the oracle's presence+exclusivity, not the digest.

**Reproducibility conditions (C-1/C-2):** `uv sync --frozen --extra dev` (package env, core 4.9.0 from CodeArtifact); `AUTOM8_WALKTHROUGH_PRODUCER_DIR` set to the vendored producer; node ≥ v22 on PATH.

**Cross-reference:** EBI F-002 `business.py:192 .first()` non-uniqueness — the latent substrate that makes T7's wrong-tenant hazard real at scale (currently LATENT-INERT; blast radius zero on the N=1 attested path).

## §8 GATE-1 disposition

**WITHHELD — no activation GO.** GATE-1 is consumed. `byte-exact-verified + staged + FV-3-corroborated` is **NOT** attached / render-proven against a live client surface. The LIVE attach (Asana task `1210776074464695`), broad rollout, and every Tier-B lever remain **operator-terminal**. PT-02 HALT stands.

## §9 Honest rung (VERBATIM)

> `byte-exact-verified (qa MODERATE) → security-FV-3-corroborated (STRONG) ← HERE + STAGED — NOT attached, NOT live, NOT first-value-realized; the LIVE attach + every Tier-B lever operator-terminal; PT-02 HALT stands.`

## §10 Attestation table (absolute paths)

| Artifact | Absolute path | Verified |
|----------|---------------|----------|
| This certification | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/.ledge/reviews/CERTIFICATION-security-fcfv-sprint3-FV3-2026-06-29.md` | authored + committed |
| Build attestation (N1/principal) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/.ledge/reviews/forwarding-cutover-ob-guide-attestation-2026-06-29.md` | Read |
| Oracle + AC-1..AC-7 tests | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/tests/unit/automation/workflows/test_onboarding_walkthrough.py` | Read + run + mutation re-fire + restored (blob `7e6dcf35…`) |
| Mint gate (called, not reimplemented) | `autom8y_core.helpers.routing.format_routing_address` (autom8y-core 4.9.0) | re-mint + fail-closed ×3 |
| Live workflow (T7 path) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/src/autom8_asana/automation/workflows/onboarding_walkthrough/workflow.py:221` | Read |
| Producer presence/shape check | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/src/autom8_asana/automation/workflows/onboarding_walkthrough/producer.py:141` | Read |

---

**Certified FV-3-PASS (STRONG)** by security-reviewer (N3), rite-disjoint critic of record, 2026-06-29. N=1, positively selected. Operator-terminal: live attach, broad rollout, all Tier-B levers. PT-02 HALT stands.
