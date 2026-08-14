---
type: review
artifact: TRIAGE-r-cc7-1-baseline-findings-2026-08-14
discharges: R-CC7-1 (baseline suppressed-not-triaged residual; pass named by R-8, operator-fired 2026-08-14)
author_seat: qa-adversary (10x-dev) — PRIMARY AUTHOR (triage probe, not a critique of another author's output)
wave: coc-attest-closure (session-20260814-164654-c8fee4fb)
pin:
  origin_main: c71c5c871dd149e4f407dbf40a4688ecb11c09eb
  head_equals_origin_main: true
  baseline_read_at: origin/main (.gitleaksignore, .gitleaks.toml)
engine: gitleaks 8.24.3 darwin/arm64 (release binary, scratchpad-local, version-verified; CI pins the same 8.24.3 linux_x64)
scan_surface: clean detached worktree at c71c5c87 in session scratchpad (repo working tree was DIRTY and was not scanned)
self_assessment_cap: MODERATE  # self-ref ceiling; single-author derivation
critique_status: UNCRITIQUED-THIS-WAVE  # no rite-disjoint review of this artifact has occurred; claims herein are single-derived, twice-probed where stated
cr5_fence: NO secret values anywhere in this artifact — fingerprints (commit:path:rule:line), paths, rule ids, token DESCRIPTORS (length/charset/shape/entropy/sha256-10 identity hashes), and masked context only
---

# TRIAGE — R-CC7-1: disposition of every baseline-masked live-at-HEAD gitleaks finding

## §1 Charge and denominators (one-quantity-two-questions, resolved)

The CC-7 baseline (`.gitleaksignore` at origin/main) holds **49 fingerprints**. The builder/critic
lineage (CRITIQUE-cc7 `:53`, HANDOFF-coc-landing-close `:58`) says **31** are "baseline-masked
live-at-HEAD findings, 0 `asana-native-pat`". Those are DIFFERENT quantities and this artifact
keeps them apart:

| Quantity | Own-derived value | What it counts |
|---|---|---|
| Baseline fingerprints | **49** | (commit,path,rule,line) tuples in `.gitleaksignore` |
| Full-history findings from c71c5c87 worktree (all local refs) | **49** — byte-identical fingerprint set to the baseline; **0 unbaselined, 0 inert** | historical introduction events |
| HEAD-tree findings (dir-mode, repo config, no baseline) | **31** | secret-shaped strings sitting in the tree at c71c5c87 |
| Baseline fingerprints whose rule-matched content still exists at HEAD | **44 of 49** | fingerprint-level "content survives" |
| Baseline fingerprints history-only (content absent at HEAD) | **5 of 49** — exactly the 5 `asana-native-pat` (cred-t21) | fingerprint-level "content gone" |

**RECONCILIATION vs the builder's numbers — CONFIRMED, with one loud correction of frame.**
My HEAD-tree scan independently reproduces **31** (21 `generic-api-key`, 9 `asana-client-id`,
1 `jwt`, **0 `asana-native-pat`**) at c71c5c87 — the critic's 31 was derived at d7560153;
the count is invariant across the ~20-commit delta. BUT "31 of the 49 are live-at-HEAD" is a
category slip: 31 counts HEAD *locations*; at fingerprint level **44 of 49** anchor content
still present at HEAD (fixture values recur across files; files moved `tests/api/`→`tests/unit/api/`,
`tests/test_auth/`→`tests/unit/auth/`; several fingerprints are branch-side duplicates of the
same content). Any "49−31=18 history-only" arithmetic is WRONG — the history-only remainder is
**5**, and all 5 are the cred-t21 PAT entries. Nothing in the builder's substance is falsified;
the frame is corrected.

**L-5 corroboration (re-derived):** the 3 fingerprints anchored off-main
(`20e92a6c…`, `48f54bcf…`, `51cc12fe…`) are confirmed NOT ancestors of c71c5c87
(`git merge-base --is-ancestor` ×3, all exit 1). Each is a branch-side duplicate of content
that ALSO carries a main-side fingerprint (`bdbf86cb…`, `e49c30d7…`, `16d281d6…` respectively)
— which is why CI (origin-refs clone) stays green while my all-refs scan trips all 49.

## §2 Method + receipts

1. gitleaks 8.24.3 (darwin/arm64) fetched from official GitHub releases into the session
   scratchpad; `gitleaks version` → `8.24.3`. Not installed system-wide.
2. Clean detached worktree at c71c5c87 created in the scratchpad (worktree-guard hook WARNed
   about non-blessed placement; scratchpad placement was deliberate — this wave's write fence is
   `.ledge/reviews/` + scratchpad only; worktree reaped after the run).
3. **Full history**: `gitleaks detect --source . --redact` from inside the worktree (CI-matching
   command mode), baseline neutralized → **49 findings**, fingerprint set == committed baseline
   (set-difference both directions = 0). Report JSON in scratchpad only.
4. **HEAD tree**: `gitleaks detect --source . --no-git --redact` → **31 findings**.
5. **Per-fingerprint content mapping**: because both scans ran `--redact` (mission-mandated), the
   JSON `Secret` fields are the literal string `REDACTED` — a first mapping attempt keyed on them
   matched everything to everything (caught by the uniform len-8 / identical-hash tell) and was
   DISCARDED as invalid. Replacement method, own-hands: for each of the 49 fingerprints,
   `git show {commit}:{path}` → the fingerprint line → rule-shape token extraction in-process →
   presence test against all 2,833 HEAD blobs. Token identities appear below only as sha256-10
   hashes. Three prose/assert lines defeated token extraction and were adjudicated by
   stripped-line equality against HEAD (all equal → live).
6. **Scars logged for the next runner**: (a) `gitleaks git <path>` (new-style CLI) returned 0
   findings on this worktree in two configurations while `detect` returned 49 — root cause not
   fully pinned (CWD-based `.gitleaksignore` auto-discovery is the leading hypothesis: the
   repo-root CWD held the 49-entry baseline); ALWAYS run gitleaks with CWD = scan root and the
   ignore file's location verified, and calibrate any scan against a known-positive before
   trusting a zero. (b) A mapping computed over `--redact`-ed report fields is theater — the
   discriminator is a content-level probe (INCIDENT-2's scar, re-learned at triage altitude).

## §3 Disposition table — all 31 baseline-masked live-at-HEAD findings

Token identity = sha256-10 of the matched token (value never reproduced). Disposition ∈
{rotate, false-positive, accepted-with-owner}. "Baseline fp(s)" = the fingerprint(s) whose
content this HEAD finding realizes (mapping by rule-shape token, not by path — files moved).

| # | Path@HEAD:line | Rule | Token descriptor | Disposition | Owner | Baseline fp(s) (abbrev commit:path:line) | Rationale |
|---|---|---|---|---|---|---|---|
| 1 | `src/autom8_asana/client.py:163` | asana-client-id | numeric-16 `7a51d064a1`, recurs 257× at HEAD | **false-positive** | — | `752062ea:client.py:53`, `83d6d7bb:client.py:103`, `eff1d0d2:client.py:30` | Docstring usage example (`export ASANA_WORKSPACE_GID`). A 16-digit Asana workspace GID is a public object identifier, not a credential; cannot authenticate anything. Rule fires on any asana-context 16-digit number. Shipped file, but shipped content is an identifier. |
| 2 | `tests/unit/test_settings.py:39` | asana-client-id | same token `7a51d064a1` | **false-positive** | — | `eff1d0d2:test_settings.py:39` | Env-fixture assignment of workspace GID. Identifier, not secret. |
| 3 | `tests/unit/test_settings.py:397` | asana-client-id | same token `7a51d064a1` | **false-positive** | — | `eff1d0d2:test_settings.py:452` | Project-GID fixture. Identifier. |
| 4 | `tests/unit/test_settings.py:398` | asana-client-id | numeric-16 `d958ce38a6`, recurs 42× | **false-positive** | — | `eff1d0d2:test_settings.py:453` | Project-GID fixture. Identifier. |
| 5 | `tests/unit/test_config_validation.py:443` | asana-client-id | `7a51d064a1` | **false-positive** | — | `3b1c48ff:test_config_validation.py:468` | GID fixture. Identifier. |
| 6 | `tests/unit/test_config_validation.py:444` | asana-client-id | numeric-16 `37a3d6fa1d`, contains `123` run, recurs 2× | **false-positive** | — | `3b1c48ff:test_config_validation.py:469` | Sequence-composed synthetic GID. Identifier. |
| 7 | `tests/unit/test_config_validation.py:482` | asana-client-id | `7a51d064a1` | **false-positive** | — | `3b1c48ff:test_config_validation.py:507` | GID fixture. |
| 8 | `tests/unit/test_config_validation.py:523` | asana-client-id | `7a51d064a1` | **false-positive** | — | `3b1c48ff:test_config_validation.py:548` | GID fixture. |
| 9 | `tests/unit/test_config_validation.py:535` | asana-client-id | `7a51d064a1` | **false-positive** | — | `3b1c48ff:test_config_validation.py:560` | GID fixture. |
| 10 | `tests/unit/api/routes/test_projects_sections_hardened.py:57` | generic-api-key | `3c3563848c`: legacy `0/`+32-hex, `abc`/`123` runs, ent 4.07, recurs 6× | **accepted-with-owner** | auth test-suite owner (principal-engineer seat); operator informed | `16d281d6:…hardened.py:57`, `51cc12fe:…hardened.py:57` (branch-side dup) | Deliberately PAT-SHAPED synthetic fixture: `0/` + exactly 32 hex meets the repo PAT rule's hex-length floor. Composition (abc/123 keyboard runs) + open 6× reuse + hash ≠ the one known-real PAT (cred-t21, `7bcccacdc3`) refute liveness. HOLD not failure: the `asana-native-pat` rule deliberately excludes the `0/` form (GATE-GAP-1), so this shape-class is structurally invisible to the PAT rule forever. Suggested peg: **DW-COC-06 "legacy-0/hex PAT-shaped fixtures at HEAD"** — trigger: any widening of the PAT rule to `0/` form makes these unbaselined reds. |
| 11 | `tests/unit/auth/test_dual_mode.py:34` | generic-api-key | same `3c3563848c` | **accepted-with-owner** | as #10 | `eff1d0d2:test_auth/test_dual_mode.py:33` | Same fixture, same hold. |
| 12 | `tests/unit/auth/test_dual_mode.py:166` | generic-api-key | same `3c3563848c` | **accepted-with-owner** | as #10 | `f87c8be6:test_auth/test_dual_mode.py:171` | Same fixture, same hold. |
| 13 | `tests/unit/auth/test_dual_mode.py:45` | generic-api-key | `861a49a5e1`: 34-char hex-class, `abc`/`123` runs, no valid PAT prefix, recurs 1× | **false-positive** | — | `eff1d0d2:test_auth/test_dual_mode.py:44` | Deliberately malformed-token negative fixture; matches no Asana PAT form (native or legacy). Non-secret. |
| 14 | `tests/unit/auth/test_dual_mode.py:23` | generic-api-key | `9b78ce63eb`: JWT, 74 chars TOTAL, header alg=RS256, payload `{sub: 10-digit}`, recurs 2× | **false-positive** | — | `eff1d0d2:…dual_mode.py:22`, `9bb06bd8:…dual_mode.py:23` | A 74-char "RS256" JWT is cryptographically impossible as a live token (an RS256 signature alone is ~342 base64 chars). Synthetic verifier fixture; cannot authenticate. |
| 15 | `tests/unit/auth/test_dual_mode.py:158` | generic-api-key | same `9b78ce63eb` | **false-positive** | — | `f87c8be6:…dual_mode.py:162`, `9bb06bd8:…dual_mode.py:162` | Same impossible-JWT fixture. |
| 16 | `tests/unit/auth/test_dual_mode.py:100` | jwt | `4f39ff6beb`: JWT, alg=**none**, NO signature part content, var `jwt_no_sig` | **false-positive** | — | `eff1d0d2:test_auth/test_dual_mode.py:jwt:99` | The canonical unsigned-JWT negative fixture. Grants nothing anywhere that verifies signatures; it exists to prove the verifier rejects it. |
| 17 | `tests/unit/auth/test_integration.py:107` | generic-api-key | `f571ad0fcd`: 45-char JWT-shape, payload NOT base64-decodable | **false-positive** | — | `eff1d0d2:test_auth/test_integration.py:104` | Deliberately malformed JWT for error-path tests. Non-token. |
| 18 | `tests/unit/auth/test_dependencies.py:132` | generic-api-key | `c69ee4dd02`: legacy `0/`+**26**-hex, `abc`/`123` runs, ent 3.99, recurs **15×** | **false-positive** | — | `eff1d0d2:test_auth/test_dependencies.py:133` | 26-hex is BELOW the 32-hex floor the repo's own PAT rule defines — shape-invalid for any Asana PAT form; keyboard-run composition; 15× open reuse as the suite's shared `pat_token` fixture. |
| 19 | `tests/unit/auth/test_dependencies.py:147` | generic-api-key | `bafe4cd209`: 28-char hex-class, `abc`/`123` runs, no prefix, recurs 3× | **false-positive** | — | `eff1d0d2:test_auth/test_dependencies.py:149` | Wrong-token negative fixture; no credential shape. |
| 20 | `tests/unit/auth/test_integration.py:73` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `eff1d0d2:test_auth/test_integration.py:64` | Shared fixture (see #18). |
| 21 | `tests/unit/auth/test_integration.py:89` | generic-api-key | `bafe4cd209` | **false-positive** | — | `eff1d0d2:test_auth/test_integration.py:82` | See #19. |
| 22 | `tests/unit/auth/test_integration.py:289` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `ae2d5983:test_auth/test_integration.py:296` | Shared fixture. |
| 23 | `tests/unit/api/test_routes_resolver.py:346` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `20711b26:tests/api/test_routes_resolver.py:401` | Shared fixture (file relocated). |
| 24 | `tests/unit/api/test_routes_query_rows.py:764` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `81d42fbc:tests/api/test_routes_query_rows.py:761` | Shared fixture (file relocated). |
| 25 | `tests/unit/api/routes/test_resolver_gid_contract.py:423` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `f31dc664:…test_resolver_gid_contract.py:397` | Shared fixture. |
| 26 | `tests/unit/auth/test_dual_mode.py:182` | generic-api-key | `c69ee4dd02` | **false-positive** | — | `f87c8be6:test_auth/test_dual_mode.py:189` | Shared fixture (see #18). |
| 27 | `tests/unit/api/middleware/test_idempotency_contracts.py:127` | generic-api-key | `060ea1f0ea`: 17-char, contains `test`+`key`+`123` | **false-positive** | — | `c62c019b:…test_idempotency_contracts.py:129` | Idempotency-KEY fixture — a request-dedup identifier, not a credential class at all; name and content both fixture-marked. |
| 28 | `tests/unit/api/middleware/test_idempotency_finalize_scar.py:70` | generic-api-key | `3af28f074f`: 17-char, contains `idem`+`key` | **false-positive** | — | `8a3bb21b:…test_idempotency_finalize_scar.py:46` (content-equal line, relocated :46→:70) | Idempotency-key fixture (adjacent :71 46-char checksum string equally non-credential). |
| 29 | `tests/integration/test_gfr_tenant_roundtrip.py:404` | generic-api-key | `9be03cc072`: exact UUID shape (8-4-4-4-12), var `override_key_guid`, recurs 5× | **false-positive** | — | `48f54bcf:…:404` (branch-side), `e49c30d7:…:404` (main-side) | GUID fixture; UUIDs are identifiers. |
| 30 | `.ledge/reviews/DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27.md:80` | generic-api-key | NO token — line is markdown PROSE (masked-verified: sentence about "Metrics CLI Under-count scar's 4 open …"), no quoted secret-shaped string present | **false-positive** | — | `20e92a6c:…:80` (branch-side), `bdbf86cb:…:80` (main-side); stripped-line equal at HEAD | Pure rule misfire on prose. Note: `.gitleaks.toml` allowlists `.know/`, `.claude/`, `.sos/`, `docs/` markdown but NOT `.ledge/` — which is why this file can fire at all. |
| 31 | `tests/unit/query/test_hierarchy.py:145` | generic-api-key | NO token — `assert …default_join_key == …` comparing 13/19-char identifiers | **false-positive** | — | `55e6f7eb:…:146` (stripped-line equal at HEAD :145) | "join_key" keyword misfire on an assert over data-model join keys. Non-secret. |

(Rows 1-31 above are the 31 distinct HEAD findings, one row each; tally verified against the scan report.)

**Fingerprint-level footnote:** baseline fp `66e43a6b:.claude/sessions/…/events.jsonl:asana-client-id:65`
has NO HEAD finding (the whole `.claude/sessions/` tree is absent at HEAD) but its 16-digit GID
(`fcdb4b423f`) appears 4× elsewhere at HEAD — identifier, false-positive class either way. It is
counted in the 44 content-live fingerprints; flagged so nobody reads 44 as "44 files at HEAD".

## §4 Tally + headline

| Disposition | Count (of 31) |
|---|---|
| **rotate (recommended)** | **0** |
| **false-positive** | **28** |
| **accepted-with-owner** | **3** (one shared shape-credible legacy-PAT fixture value, 3 sites) |

**No finding among the 31 is a live or presumed-live credential.** The only rotate-class item in
this repo remains **cred-t21** — the Critical unrotated native ASANA_PAT at commits
`a578ca85`/`525431de`/`15cffee1`, path `.claude/settings.local.json` — which I verified is
**HISTORY-side, not HEAD-side**: the file is absent from the HEAD tree; the single distinct PAT
value (extracted in-process from the two finding-bearing commits; identity `7bcccacdc3`) appears
in ZERO of the 2,833 HEAD blobs under an allowlist-blind sweep; all three commits are ancestors
of main (exposure = history + clones/forks). Rotation is OPERATOR-EXECUTED (F-2 family), owner =
operator, per `.know/defer-watch.yaml:382-403` (status OPERATOR-PENDING-ROTATION). Blast radius
until rotation: any holder of a clone/fork of main history holds a live PAT.

## §5 Paper-only rule/allowlist recommendations (NO edits this wave)

1. `asana-client-id` (9 findings, all 16-digit GIDs): the rule cannot distinguish OAuth client
   IDs from ordinary Asana GIDs, and neither is a secret. Recommend a future security-seated wave
   evaluate disabling this rule or allowlisting it for `tests/**` — baseline accretion is the
   current cost. Do NOT hand-edit now.
2. `generic-api-key` prose/identifier misfires (#27-#31): candidates for a `.ledge/.*\.md$`
   allowlist path (mirroring the existing `.know/.claude/.sos/docs` entries) and for regex-level
   allowlists on `idempotency`/`join_key`/GUID contexts. Recommend-only.
3. The 3 accepted-with-owner legacy-PAT-shaped fixtures: deliberately NOT recommended for
   allowlisting — their visibility is the tripwire (DW-COC-06 proposal, §3 row 10).

## §6 Adjacent observations (cluster duty — probed beyond the charge, all benign)

- `tests/unit/auth/test_bot_pat.py` carries 3 more occurrences of the legacy `0/…` fixture family
  at HEAD that `generic-api-key` does NOT flag — same synthetic class as rows 10-12.
- Allowlist-blind sweeps of all HEAD blobs for foreign credential shapes: AWS `AKIA…` (2 files —
  one shared synthetic SigV4 fixture: contains `TEST`, tail entropy 1.5 vs ~3.5+ for real keys;
  co-located 40-char "secret" contains a `1234` run — benign), Slack `xox…` (2 hits, 15 chars,
  contain `test` — too short to be real), GitHub PATs / private-key PEM / OpenAI / CodeArtifact /
  Slack webhooks: **zero**.
- Legacy `0/`+hex sweep across all HEAD blobs: 6 occurrences in 3 test files, all the fixture
  family above; none matches the cred-t21 PAT identity.

## §7 LANGUAGE RULE for downstream artifacts (binding on citation of this triage)

Permitted, exactly:

> "All 31 baseline-masked live-at-HEAD findings are dispositioned (0 rotate-recommended,
> 28 false-positive, 3 accepted-with-owner under DW-COC-06-proposed); 44 of 49 baseline
> fingerprints anchor HEAD-surviving content, 5 of 49 are history-only and all 5 are the
> cred-t21 `asana-native-pat` entries."

STILL FORBIDDEN — this triage does **not** license "history clean", because:
1. The cred-t21 Critical PAT remains fully exposed in main HISTORY (`a578ca85`/`525431de`/`15cffee1`)
   and remains LIVE until the operator rotates it (F-2; OPERATOR-PENDING-ROTATION).
2. The enforcing gate only ever proves *"no unbaselined finding"* — never *"history clean"*
   (REVIEW-pr368 `:296-302`, carried unchanged).
3. This triage adjudicated the baseline-masked set at HEAD c71c5c87 only; it attests nothing
   about future commits, other refs, or rotation state.

R-CC7-1's *triage* limb is DISCHARGED by this artifact. Its *language fence* survives, now
anchored to the rotation residual: every clean-history-adjacent claim must carry cred-t21/F-2
until rotation lands and is receipted.

## §8 NCSR ledger (pre-registered negatives, refuter returns incl. NULLs)

- **N1 — "no baseline-masked live-at-HEAD finding is a live rotatable credential."**
  Refutation attempted via: (i) shape analysis of all 31 (length/charset/prefix/entropy);
  (ii) recurrence analysis across all HEAD blobs; (iii) identity comparison against the one
  known-real credential in repo history (cred-t21 PAT, `7bcccacdc3`) — no match; (iv) structural
  JWT decode (alg/none, impossible-length RS256 signature, undecodable payload); (v) co-located
  secret-pair probing (AWS key+secret shape). **RESULT: NULL — refutation failed on all 31.**
  Residual honesty: rows 10-12 are shape-credible by construction; their benignity rests on
  composition + reuse + non-identity evidence, not on shape (hence accepted-with-owner, not FP).
  No credential was tested against any live service (CR-1/CR-5 honored; shape-only).
- **N2 — "0 `asana-native-pat` at HEAD."** Re-derived twice: (a) HEAD-tree gitleaks scan with
  the repo config → 0 of that rule among 31; (b) own-hands regex (the rule's exact pattern) over
  all 2,833 HEAD blobs **allowlist-blind** → 0 matches (closes the allowlist blind spot the
  gitleaks run cannot). **CONFIRMED.** Bonus sweep: legacy `0/` form (deliberately outside the
  rule) → 6 fixture occurrences, §6.
- **N3 — "cred-t21 fossils absent at HEAD."** cred-t21 re-derived from
  `.know/defer-watch.yaml:382-403` (Critical, unrotated, `.claude/settings.local.json`,
  commits `a578ca85`/`525431de`/`15cffee1`). Checks: file absent from HEAD tree (TRUE);
  PAT value absent from every HEAD blob, allowlist-blind (TRUE); all 3 commits ancestors of
  main (TRUE — exposure is history-side, verified myself, exactly as the mission stated).
  **CONFIRMED.** Corroborating detail re-derived: only `15cffee1` (3) and `525431de` (2) carry
  the 5 baseline fingerprints; `a578ca85` contributes none (diff-addition scoring), matching
  BUILD `:245-249`.

## §9 UV-Ps (unverified premises, labeled per frozen syntax)

[UV-P: the CI enforcing job at c71c5c87 reproduces this exact 49/0-unbaselined set | METHOD: observe the next `Secrets Scan (enforcing)` main-push run conclusion+log counts | REASON: my load-bearing runs used gitleaks 8.24.3 darwin/arm64 locally; CI runs the same pinned 8.24.3 on linux_x64 — engine-version identity is verified, cross-platform scan-identity is presumed not observed]

[UV-P: the 3 branch-side fingerprints are unreachable in CI clones (fully inert there) | METHOD: gitleaks detect on a fresh origin-refs-only clone | REASON: my worktree scan sees ALL local refs (detect walks --all), so it cannot discriminate CI-visible reachability; non-ancestry of the 3 commits is verified, remote-ref absence for 2 of 3 is inherited from REVIEW-pr368 L-5 not re-derived]

[UV-P: `gitleaks git` zero-finding anomaly root cause (CWD-based .gitleaksignore auto-discovery) | METHOD: controlled re-run varying CWD and ignore-file placement | REASON: not load-bearing for any number in this artifact (all counts derive from `detect`, calibrated 49/49 against the committed baseline and positive-controlled on a synthetic canary); logged as a scar, not chased]

## §10 Self-assessment

MODERATE (capped; single-author, uncritiqued this wave). What is hard: the 49/49 fingerprint
set identity, the 31 HEAD findings, the 0-native-pat-at-HEAD double derivation, the cred-t21
absence-at-HEAD triple check, non-ancestry of the 3 branch-side commits — each is a mechanical
probe re-runnable from this artifact. What is judgment: the FP-vs-accepted-with-owner line
(drawn at shape-credibility) and fixture-benignity readings (composition+reuse+non-identity,
never liveness testing). A rite-disjoint re-derivation would strengthen this to STRONG.
