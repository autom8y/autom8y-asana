---
type: handoff
handoff_type: assessment
status: draft
handoff_status: pending
source_rite: security
target_rite: releaser (go-live executor) / build (gate-remediation)
initiative: cr3-clean-break-cutover
created: 2026-06-06
evidence_ceiling: MODERATE-RUNNER-CORROBORATED  # certifying critic = same main thread as the CR-3 authoring session (NOT session-disjoint) → self-ref cap; GitHub-runner execution is environment-disjoint (corroborates the 2 shell gates fire AS WIRED) but does NOT lift the DESIGN grade to STRONG.
discipline: Read-only certification. Production-mutating levers AND secret material stay the user (single-writer). Secrets by name/sha256 prefix only.
---

# HANDOFF — security → releaser/build: CR-3 gate STRONG-certification = REQUEST-CHANGES (MODERATE-RUNNER-CORROBORATED)

> The security rite (rite-disjoint from the CR-3-owning rites, but NOT session-disjoint — same main thread) certified PR #61's gates. Verdict: **Request-Changes**. The two shell seal-proofs are genuine, runner-corroborated controls — **but they are not wired against the production artifacts they defend, and three carry real bypasses.** STRONG is unattainable from this session.

## §0. Verdict
**Overall: MODERATE-RUNNER-CORROBORATED · Request-Changes.** G-THEATER PASSED (both seal-proofs fired RED on disjoint GitHub runners, run `27024257733`, log-verified, non-tautological). But the gates **prove the scanner/guard CAN fire — never that the shipped image/plan is clean** (F-000). CR-3 remains **merged-NOT-live**; nothing is `protecting-prod`.

## §1. Gate matrix (per-gate honest grade)
| Gate | Runner-corrob | Bypassable | Grade |
|---|---|---|---|
| image-layer-secret-scan (CHANGE-001) | ✅ | ⚠️ F-001 | MODERATE-RUNNER-CORROBORATED |
| deploy-scope-guard (CHANGE-005) | ✅ | ⚠️ F-003/F-004 | MODERATE-RUNNER-CORROBORATED |
| AC-6 AST walker (CHANGE-008) | ❌ | ⚠️ F-002 | **WEAK** |
| DW-1 bake control (the vector the scan was minted to close) | ❌ | ⚠️ | **FAIL** (ungated F-000 + unrotated) |
| IAM least-privilege | ❌ | ✗ | **FAIL** (secretsmanager `["*"]`) |
| #60 SM-first SPOF fix | n/a | ✗ | MODERATE (fail-secure, verified vs merged main) |
| DW-2 CI OIDC trust-policy | ❌ | ✗ | WEAK (trust-policy unpinned) |

## §2. New security findings (the prior rites missed — route to remediation)
- **F-000 / TM-GATE-COVERAGE / TM-DEPLOY-UNGATED (HIGH):** neither shell gate is wired against the real artifact (`docker-build.sh`/`deploy-by-channel.sh` @86bf029d have ZERO scanner/guard refs). **Fix:** run `image-layer-secret-scan.sh --image-ref <built-monolith>` + `deploy-scope-guard.sh <resolved-plan>` as BLOCKING steps in the real build/deploy before GO-2 required-checks confer real protection.
- **F-001 (HIGH):** scan regex misses `AWS_SECRET_ACCESS_KEY` (40-char) + base64/split/lowercase/session-token. **Fix:** integrate trufflehog/gitleaks-on-image + base64 pass; best = stop baking `.env`.
- **F-002 (MEDIUM):** AC-6 is substring-scan not AST data-flow; bypassable (concat/hex/getattr); scan path hardcoded to one file, misses `utils/env/main.py` SPOF root. **Fix:** real AST `Constant`/`os.environ`-subscript analysis + widen paths.
- **F-003 (MEDIUM):** deploy-scope-guard map-shape always false-REDs; seal-proof masks it (list-only). **Fix:** branch on `yq eval 'type'`.
- **F-004 (LOW):** subset-only; no scope-creep detection. **Fix:** add `UNEXPECTED SERVICE` RED for exact-set.
- **TM-AC6-SKIP (HIGH):** AC-5/AC-6 (static, no AWS) coupled to the OIDC-gated job → SKIP on PRs → SPOF seatbelt inactive. **Fix:** split into a NO-`if`-gate CI job (runs now, CodeArtifact-free).
- **TM-RESOLVER-FAILOPEN (MEDIUM):** any SM-fetch failure fail-safes to the Secret-2 legacy path (silent posture downgrade; attacker lever). **Fix:** alarm on SM-fail→legacy transition during GO-9 soak.
- **TM-IAM-WILDCARD (CRITICAL, operator):** scope `secretsmanager` to the resolver-envelope ARN.
- Credential topology: Secret-1 path conformant (CT-2), #60 fail-secure (CT-3), DW-2 least-privilege-correct-but-role-broad (CT-4), GO-11 Secret-2 sequencing sound (CT-5).

## §3. Open CRITICALs (operator / single-writer)
1. **DW-1** live AWS key baked + ECR-extractable + scrub-misses-it — operator-deferred 2026-06-06. Rotate + de-bake (rotation ALONE insufficient — must de-bake or the rebake re-exposes).
2. **TM-IAM-WILDCARD** — task role reads every secret; least-privilege scope (IaC, operator apply).
3. **F-000** — gates not wired to prod artifacts; required-checks (GO-2) confer FALSE confidence until wired.

## §4. true_strong_requires (PT-CRITIC unsatisfied)
A critic **NOT driven by this main thread** (fresh-session forge eval-specialist / human security reviewer, disjoint identity) must: (1) re-run + log-verify the seal-proofs; (2) close F-000 (run the scan against the REAL monolith image from 86bf029d, confirm it fires RED on the DW-1 key; wire the guard into the real deploy); (3) fix the DW-2 OIDC gap so the AC+rollback suite runs green-on-runner; (4) re-confirm F-001/F-002/F-003 bypasses closed. Until then: ceiling = MODERATE-RUNNER-CORROBORATED.

## §5. GO-1..GO-11 ratification (security lens)
GO-8 (AC-6 functional canary), GO-9 (soak), GO-10 (Stage-B) **RATIFIED**. GO-1..GO-7 + GO-11 **RATIFIED-WITH-CONDITION** — key conditions: **GO-2** (make checks required) confers real protection ONLY after F-000 wiring; **GO-4** key rotation is INSUFFICIENT without de-bake; **GO-6** prod build must be operator-env (sandbox build ships dev creds). Full conditions in the verdict artifact (`.sos/wip/eunomia/`-adjacent; this HANDOFF + the workflow output `wzbdhlw4r`).

## §6. Recommended next
A **gate-remediation sprint** (build/eunomia rite) closing the reversible findings (F-001/F-002/F-003/F-004 + TM-AC6-SKIP job-split + F-000 wiring once DW-2 lands), then **re-certification by a rite-disjoint critic** (true STRONG). Operator owns DW-1 rotation+de-bake, TM-IAM-WILDCARD scoping, DW-2 OIDC. Do NOT make #61 checks required (GO-2) until F-000 is wired — a required-but-fixture-only gate is false assurance.

*Security exit-gate, 2026-06-06. Rite-disjoint lens (session-NOT-disjoint → MODERATE cap). Read-only; no mutation, no secret material handled. Verdict carried to the seam for the go-live executor + a gate-remediation pass.*
