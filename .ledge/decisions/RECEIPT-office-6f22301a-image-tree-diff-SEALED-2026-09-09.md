# RECEIPT — salkin-safe-routing image tree-diff · **SEALED AND UNINTERPRETED**

**Ruling basis:** R-76 (rite-disjoint seat, method mandated) · R-77 (defined so it cannot be
inconclusive) · R-85 (result SEALED).
**Seat:** `clinic·pathologist` — a rite-disjoint, evidence-collection role that by charter collects
and catalogs and **does not form hypotheses**. No lineage to A17.
**Status: SEALED. This artifact RECORDS. It does not conclude, recommend, or dispose.**

## Method — as mandated, not varied
`docker pull` both refs → `docker create` + `docker export` (the **complete layered filesystem as a
running container sees it**) → extract to two trees → `diff -rq` on the **whole trees**.
**No per-layer diffing was performed.** No FAIL-CLOSED condition arose.

**Materialization completeness check** (so a layer cannot be mistaken for an image):
**Tree A = 21,344 files · Tree B = 21,344 files.** Both in the thousands. *(A17's fatal artifact was
87 files — a layer, not an image.)*

| | ref |
|---|---|
| **A** — the frozen subject | `…@sha256:76c21a00…`, sole tag `salkin-safe-routing-20260905-90e0aa5a4937` |
| **B** — what production serves | `:4e0b41f` |

## Result — the whole tree
**1,026 diff lines: 4 only-in-A · 4 only-in-B · 946 modified.**
- The 8 only-in-one-side entries are **four paired `dist-info` directories** — dependency version
  bumps: `anyio` 4.15.0→4.15.1, `autom8y_log` 0.8.0→0.9.0, `boto3` and `botocore` 1.43.89→1.43.90.
- **929 of the 946 modified files are `botocore/data/**/*.json.gz`** service-definition blobs — a
  byproduct of that botocore bump.

## ★ Result — application source (`email_booking_intake`)
**8 entries. ALL MODIFIED. NONE added, NONE removed.** 183 files exist at that prefix on both sides.

| path | A (frozen) | B (production) |
|---|---|---|
| `site-packages/…/intake_classifier/rules.py` | `42740413…` / **39,003 B** | `656b5be2…` / **45,753 B** |
| `site-packages/…/metrics.py` | `70e649d0…` / **71,512 B** | `67a66498…` / **74,290 B** |
| `site-packages/…/pipeline/stages/intake_classify.py` | `229a8888…` / **6,712 B** | `0502be4e…` / **9,209 B** |
| `var/task/src/…/intake_classifier/rules.py` | `cad9271d…` / **39,471 B** | `656b5be2…` / **45,753 B** |
| `var/task/src/…/metrics.py` | `70e649d0…` / **71,512 B** | `67a66498…` / **74,290 B** |
| `var/task/src/…/pipeline/stages/intake_classify.py` | `9ee44058…` / **7,466 B** | `0502be4e…` / **9,209 B** |
| `…dist-info/RECORD` | differs (manifest of the above) | |
| `…dist-info/uv_cache.json` | differs | |

**A recorded observation, byte-level and not an inference:** each module exists at **two install
locations**. In **tree B the two copies are byte-identical** to each other. **In tree A they are
NOT** — `rules.py` is `42740413…`/39,003 B at `site-packages` and `cad9271d…`/39,471 B at
`var/task/src`; `intake_classify.py` is `229a8888…`/6,712 B and `9ee44058…`/7,466 B.
**Stated as measured. What it means is not this receipt's to say.**

## ★★ WHAT THIS SETTLES ABOUT THE RECORD ITSELF
**A17 claimed the image "changed nothing in the application source." A20 retracted that in full.
THE PROPER METHOD CONFIRMS THE RETRACTION AND REFUTES THE ORIGINAL CLAIM.**
Three application-source modules differ — and they are **exactly the files A20 named as overlaid by
the two unread layers**: `rules.py` and `intake_classify.py`, plus `metrics.py`.
**A17 was not merely unproven. It was wrong, and the retraction was correct.**

## WHAT THIS RECEIPT DOES **NOT** DO
- It does **not** say whether the differences **matter**. R-77's residual is explicit: *what changed
  is not whether it mattered*, and that judgement is **booked to the operator**.
- It does **not** recommend restoring, keeping, or deploying anything.
- **It does NOT release R-35.** Two independent reasons:
  1. **R-87: C-13 DOMINATES.** Applies cannot resume until that external conversation happens,
     whatever else completes. **Clock: 2026-09-09T18:00Z, then LOST; reap 09-10T05:28:46Z.**
  2. **Whether a SEALED, uninterpreted receipt satisfies R-74 leg 2 is UNRULED** — the operator
     selected no option at sitting II and answered *"/qa aggressively but unilateral approval is
     granted."* **It must be ruled before C-13 discharges, or it becomes live unruled.**

> **No merge, deploy or apply was performed to produce this receipt. It is read-only measurement.
> The trees and the full diff are preserved in the session scratchpad.**
