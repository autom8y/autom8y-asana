---
type: handoff
handoff: cross-rite
from_rite: sre
to_rite: releaser
class: execution+validation
date: 2026-06-03
status: draft
initiative: cr3-receiver-bulk-fanout-readiness
gates: [two-pronged-parallel-producer-consumer-work]
handoff_back: sre (on certification → clear the two-pronged work; on drift/smoke-fail → reconcile + re-certify)
self_ref_ceiling: MODERATE (lifts to STRONG only on the clean-plan + green-smoke corroboration this handoff commissions)
---

# HANDOFF — sre → releaser: CR-3 Receiver-Substrate Release Certification

## Telos (why this exists — read first)
Two CR-3 handoffs authored 2026-06-03 (the **reverse** producer work-queue and the **return** to the monolith) assert that the receiver-side reliability substrate — most critically the **30-min bulk warmer** and **serve-stale-up-to-the-LKG-ceiling** — is **deployed in prod**. Those claims are load-bearing: the entire "the 502 is now largely mitigated → re-measure post-warmer" reframe rests on them.

**But this substrate landed through out-of-band, operator-approved local `terraform apply` (R1), with the IAM trio destroyed by a satellite-deploy full-apply and then re-applied, plus a SHA-vs-`latest` image-tag drift.** Until a clean reconciling plan proves `prod == main` and a functional smoke proves the substrate behaves, those handoff claims are **MODERATE/assumed, not STRONG**.

**This handoff commissions an INDEPENDENT release-certification + QA-smoke track that GATES the two-pronged parallel work.** Do not let producer (receiver re-gate) or consumer (monolith cutover) proceed on assumed-landed claims. Certify first.

## What must be certified-landed (the substrate the handoffs depend on)
All claimed merged to `main`; releaser confirms the SHAs + that prod reflects them:

| Substrate | Repo / PR | Merge SHA | Live-state receipt |
|---|---|---|---|
| 30-min bulk warmer — checkpoint-prefix code (`prematerialize_*`, env-overridable `CACHE_WARMER_CHECKPOINT_PREFIX`) | autom8y-asana **#96** | `3c1dca5` | image `00ebebb5` on `autom8-asana-cache-warmer-bulk` |
| Bulk warmer module + DMS (`module.cache_warmer_bulk`, `cron(0,30 * * * ? *)`, mem=2048, reserved=1) | autom8y **#331** | `f09ecda` | Lambda Active, `Mem=2048`, `LastMod 2026-06-03T09:06:11Z` |
| Bulk warmer IAM trio (`cache_warmer_bulk_{s3,self_invoke,cloudwatch_metrics}`) | autom8y **#335** | `e2fab87` | `aws iam list-role-policies autom8-asana-cache-warmer-bulk-lambda-role` → 5 inline policies |
| cpu=1024 durable | a8 **v1.3.8** | (version-pin) | ECS taskdef `:459+` cpu=1024 (first CI-registered 1024) |
| Event-loop offload + honest-LKG(10.0) + honest-empty-200 + Retry-After | autom8y-asana **#92/#95** | (merged earlier) | `errors.py:621-638`, `engine.py:264`, `dataframe_cache.py:525-546` |

## The DRIFT RISK to reconcile (the crux)
The bulk module + IAM were applied to the **shared prod TF state** via local `terraform apply -target` (not CI), and the IAM was destroyed once by a satellite-deploy full `just tf-apply asana production` then re-applied from the (then-merged) `main` config. A post-#335 Service-Terraform apply ran **2026-06-03 11:23Z on `f947358` (success)** — evidence of reconciliation — but **zero-drift is NOT proven.**

**Releaser MUST:**
1. Run a clean `terraform plan` on `autom8y/terraform/services/asana` from `origin/main` (pass the **deployed SHA `image_tag`**, not the `latest` default — Trap-5) and confirm **`0 to add, 0 to change, 0 to destroy`**, or explain/resolve every delta. This proves `prod == main`.
2. Explicitly confirm the **IAM trio is present + matches `main`** (the Trap-4 "full-apply destroys out-of-band resources" class that bit #335) — both the bulk role and (when relevant) any fast role.
3. Confirm the **image-tag pin is consistent + durable** across ECS + both warmers (the cosmetic `:3c1dca5` ↔ `:latest` drift must not mask a real divergence).

## QA SMOKE (functional, content-bound — NOT liveness)
A 2xx that carries an empty/wrong frame is a false pass (SCAR-029 liveness-masquerade). Smoke must assert behavior:
1. **Warm-persist:** a scheduled 30-min bulk sweep writes frames to `s3://autom8-s3/dataframes/{gid}/` + `checkpoints/bulk/`, **`AccessDenied=0`**, BusinessUnits (`1201081073731555`) frame watermark advances.
2. **Serve-stale:** a `/v1/query/{project|section}/rows` for a warm-set GID serves **200 from cache** (FRESH/SWR/LKG) carrying honest `meta.freshness`/`data_age_seconds` — not a build/503.
3. **503/Retry-After:** a cold/over-ceiling GID returns **503 CACHE_BUILD_IN_PROGRESS + `Retry-After`** header.
4. **honest-empty:** a genuinely zero-row GID returns **200 + `meta.honest_empty=true`** (not 503/error).
5. **cpu durable:** the running ECS taskdef is **cpu=1024** (not reverted by a deploy).

## Held PRs — do NOT merge
- **autom8y-asana #97** (fast-lane code, `mergeable_state: clean`) and **autom8y #338** (fast-lane TF, open) are **HELD and likely SUPERSEDED** by the serve-stale-within-bound calibration ratified in the 2026-06-03 stakeholder interview. **They are NOT part of this rollout.** Do not deploy. Disposition (close vs keep-as-fallback) is owned by the serve-stale ADR, not releaser.

## Acceptance criteria (releaser certifies all)
- [ ] The 3 substrate PRs (#96/#331/#335) confirmed merged to `main` at the SHAs above; #97/#338 confirmed NOT merged.
- [ ] Clean `terraform plan` on `services/asana` = **0 drift** (prod == main), IAM trio present, image-tag consistent.
- [ ] Deploy durable: cpu=1024, `autom8-asana-cache-warmer-bulk` Active/mem=2048/30-min schedule/IAM, #96 image on ECS + warmers.
- [ ] QA smoke green on all 5 checks (content-bound).
- [ ] A **certification artifact** (`.ledge/` release note) attesting clean+durable+smoked, lifting the two handoffs' "deployed" claims from MODERATE → STRONG.

## handoff_back
- **On certification (all criteria met):** the two-pronged parallel work is **cleared to proceed** — (producer) the receiver ≥99% re-gate per `HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md`; (consumer) the monolith cutover prep per `HANDOFF-asana-sre-to-autom8-cr3-return-2026-06-03.md`. Stage-B remains human/IC-gated regardless.
- **On drift or smoke-fail:** reconcile (clean apply / fix) + re-certify; **block both prongs** until green. Route TF/deploy fixes → platform-engineer.

## Grounding + disciplines
- Grounding: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/cr3-verified-findings-2026-06-03.md` (verified findings + synthesis); the two CR-3 handoffs in `.ledge/handoffs/`.
- Deploy-trap lessons (apply): **Trap-4** — the satellite deploy runs a full `just tf-apply asana production`; out-of-band/local-applied resources not in `main` get destroyed → `main`-config is the only durable source. **Trap-5** — local applies must pass the deployed SHA `image_tag`, not `latest`. **CI-writer-race / version-pin** — CI checks out the manifest at a pinned `A8_VERSION` (v1.3.8 carries cpu=1024).
- SVR file:line/resource receipts for every platform claim; **never print production secret VALUES** (redact); MODERATE self-ref until the clean-plan + smoke corroborate.
