---
type: review
status: proposed
---

# P12: the asana ECS task-definition drift is a stale a8 manifest, not stale Terraform

**Seat preamble.**
- **Who and when:** platform-engineer (sre, borrowed in autom8y-asana) wrote this at 2026-11-01T13:33:41Z (date -u), on clerk START row 18136.
- **Inputs:** the detector record FINDING-reconcile-drift-detection-autom8y-20261101T132431Z.md (sha ac2f08bbad54) and its ADDENDUM-1 (df76964b1df7).
- **Mode:** read-only. No workflow was triggered, re-run or dispatched. No terraform plan, init, apply or state read. No credential fetch or login. No AWS or GitHub write.
- **Value hygiene:** env and secret values were never printed. Values were hashed (sha256) inside the pipe, and the names were compared by key only.
- **Refs read:**
  - autom8y/autom8y origin/main fe22fee922ad.
  - autom8y/a8 tag v1.6.4 (a2798e3a8d17) and origin/main 50712dada43a.
  - Logs of runs 41310137356 and 41305878178 (reconcile), 40964540253, 41195860626 and 41200509996 (reconcile transitions), 40962598115 and 40963833261 (Service Terraform), and 40207911746 (Satellite Receiver, asana). All logs were masked at the source.
- **AWS:** read-only calls under an SSO session that was already active (describe-services, describe-task-definition, list-task-definitions). None failed on auth, so no call is recorded as NOT TAKEN.

## Headline

- **What drifts:** one field, `resources.memory`. The detector wants **8192** and the served `autom8y-asana-service:856` has **4096**.
- **Which side moved:** Terraform did, on purpose.
  - autom8y #2932 (16510642fe55, merged 2026-10-29T22:00:57Z) right-sized the asana task memory from 8192 to 4096 (`terraform/services/asana/main.tf:185-195`).
  - The gated Service Terraform apply registered :856 at 2026-10-29T22:10:15Z.
- **Why the detector still wants 8192:** "declared", as the detector computes it, is **not Terraform**. It is the **a8 manifest** (`autom8y/a8` `manifest.yaml` at the pinned tag v1.6.4), and that manifest still says `memory: 8192`.
- **Terraform and served agree.** A Terraform catch-up has nothing to catch up.
- **The image is not part of this drift.** a8 v1.6.4 has no image surface, and :856 carries the same image as :854 (2dcb88fa23e5).

## How the detector computes "declared"

- **What runs:** the workflow step "Run reconciler" runs `a8 reconcile plan --all --output json` with `A8_MANIFEST=.a8-manifest/manifest.yaml`.
- **Where the manifest comes from:** a sparse checkout of `autom8y/a8` at `ref: v1.6.4`. The pin comes from `vars.A8_VERSION`, through `scripts/a8-pin-resolve.sh`.
- **The comparator** is `internal/reconcile/differ_taskdef.go` at v1.6.4:
  - It reads the PRIMARY deployment's task definition: GetServiceDeployments, then GetTaskDefinition.
  - It compares, in **one direction only**, the manifest's `environment`, `secrets` and `resources` against the live task definition. Live keys that the manifest does not declare are never compared.
  - Sizing is checked by `diffResources` (`:358`). The memory message is built at `:375`.
  - Image, roles, ports, health check and log config are **not compared**. The workflow's own comment says so: "a8 v1.6.0 has NO image surface".
- **What the manifest declares for `services.asana`** (v1.6.4 and a8 main are identical here):
  - `environment`: none.
  - `secrets`: 3 keys (ASANA_PAT, ASANA_WORKSPACE_GID, SERVICE_CLIENT_SECRET), each as a bare Secrets Manager name.
  - `resources`: cpu 2048, memory 8192, at `manifest.yaml:605-607`.

## Q1: which fields differ, and which side moved

### What the detector compares: manifest v1.6.4 against served :856

The comparator was re-run locally as a pure function over the two documents. No value was displayed.

| Field | Manifest (declared) | Served :856 | Result |
|---|---|---|---|
| resources.cpu | 2048 | 2048 | match |
| **resources.memory** | **8192** | **4096** | **DRIFT** |
| secret ASANA_PAT | bare name | present; matches the bare-name rule | match |
| secret ASANA_WORKSPACE_GID | bare name | present; matches | match |
| secret SERVICE_CLIENT_SECRET | bare name | present; matches | match |
| environment | (none declared) | 26 keys | not compared |

- **Result:** exactly one diff, `resources.memory: want 8192, got "4096"`, which is the detector's `asana:ecs_task_definition`.

### Terraform (autom8y main) against served :856

- **Terraform:** `terraform/services/asana/main.tf:194-195` declares `cpu = 2048` and `memory = 4096`. The comment at `:185-193` is dated 2026-10-29 and gives the evidence: memory 30-day max 11.25% of 8192, and 4096 is the Fargate minimum for cpu 2048.
- **Served :856:** cpu "2048", memory "4096". **Terraform and served match.**

### What moved on 10-29: :854 (served from 10-25) against :856 (served from 10-29)

- **Task level:** only `memory` differs (8192 to 4096). No other field differs: cpu, networkMode, requiresCompatibilities, runtimePlatform, taskRoleArn, executionRoleArn and the rest are equal by hash.
- **App container `autom8y-asana-service`:**
  - Image 2dcb88fa23e5 on both.
  - Env: the same 26 key names, and every value sha256 matches.
  - Secrets: the same 6 key names, and every valueFrom sha256 matches.
  - Port mappings, health check and log config are identical.
- **Sidecar `adot-collector`:** identical. The image is 40a7eb9bfa58, and both env keys match by hash.
- **Role names on :856:** task role `autom8y-asana-service-ecs-task`, execution role `autom8y-asana-service-ecs-execution`.
- **Port mappings on :856:** app 8000/tcp, sidecar 4317/tcp.
- **Health check on :856:** CMD-SHELL python urlopen on `localhost:8000/health`, with interval 30, timeout 10, retries 3 and startPeriod 300.
- **Log driver on :856:** awslogs, with the option keys awslogs-group, awslogs-region and awslogs-stream-prefix.

### Which side moved

- **The declared side moved, in Terraform.** The a8 manifest is the second declaration of the same number, and it did not follow.
- **The drift starts exactly at the apply:**

| Event | Time (UTC) |
|---|---|
| Reconcile run 40956266818: **success** | 2026-10-29T21:15:43Z |
| #2932 merged | 22:00:57Z |
| Service Terraform 40962598115 ("asana (production)", workflow_dispatch): Apply job | 22:08:04Z to 22:10:31Z |
| :855 deregistered, then :856 registered | 22:10:14Z, 22:10:15Z |
| ECS deployment on :856 created | 22:11:34Z |
| Reconcile run 40964540253: **failure**, `DRIFTED_PAIRS: asana:ecs_task_definition, data:ecs_task_definition` | 22:16:07Z |
| ECS deployment on :856 completed | 22:27:27Z |

- **Correction to the detector record:** its "likely cause" was autom8y-asana #524 (10-31). That is ruled out. The drift predates #524 by about 36 hours.

## Q2: is it the image ref only, and who registered :856?

- **It is not the image at all.**
  - a8 v1.6.4 does not compare images.
  - :856 and :854 carry the same digest, 2dcb88fa23e5.
  - The FU-7 design (`served_image.tf`) makes Terraform render the **served** image forward. That is why :856 has the digest that was served at the moment of the apply.
- **Who registered :856:** `registeredBy` is the assumed role **`github-actions-terraform`**, at **2026-10-29T22:10:15Z**.
  - The run was Service Terraform 40962598115 ("Service Terraform — asana (production)"), a workflow_dispatch.
  - The GitHub actor and triggering actor are `dtenuta`.
  - The run went Plan, then the production-gated Apply, then success.
- **The image did not become served on 10-29.** It has been served since **2026-10-25T16:01:21Z**:
  - The receiver registered **:854** (role `github-actions-deploy`, 2026-10-25T15:45:37Z), from source :853, with the rollback target set to :852.
  - The ECS service event "deployment completed" is at 2026-10-25T16:01:21Z.
  - The receiver's running-task gate saw `rolloutState=COMPLETED` at 16:01:24Z.
  - On 10-29, Terraform only re-rendered that already-served image into :856, with the new memory.
- **The "unrecorded" registration is :855, and it was never served:**
  - `registeredBy` is `AWSReservedSSO_AdministratorAccess_<suffix>`, the human SSO permission-set role. It was registered at 2026-10-25T16:34:37Z with memory 8192 and image 2dcb88fa23e5.
  - :853 (Terraform's prior render) was deregistered 1 second earlier. That deregister-then-register pair is the shape of a Terraform task-definition replacement, so :855 is most likely a **local Terraform apply under SSO**. This is an inference from timing only; no state was read.
  - The CI apply on 10-29 deregistered :855 at 22:10:14Z when it registered :856.
  - :855 is flagged here for the record. It does not cause this drift.

### Newest 5 ACTIVE revisions of the family

| Revision | cpu | memory | registeredAt (UTC) | registeredBy (role) | app image |
|---|---|---|---|---|---|
| :856 | 2048 | 4096 | 2026-10-29T22:10:15Z | github-actions-terraform | 2dcb88fa23e5 |
| :854 | 2048 | 8192 | 2026-10-25T15:45:37Z | github-actions-deploy | 2dcb88fa23e5 |
| :852 | 2048 | 8192 | 2026-10-02T22:41:38Z | github-actions-deploy | d553636d0dd6 |
| :849 | 2048 | 8192 | 2026-09-24T21:02:24Z | github-actions-deploy | dbe3a8b4ef4a |
| :847 | 2048 | 8192 | 2026-09-24T20:32:50Z | github-actions-deploy | 011bd57ac8a6 |

- **INACTIVE in that span:** :853 (github-actions-terraform, 10-02, deregistered 10-25T16:34:36Z) and :855 (SSO admin, 10-25, deregistered 10-29T22:10:14Z).

## Q3: does the drift explain the HELD receiver run 40207911746?

- **No.** The two are about four days apart and have unrelated causes.
- **HELD came from the canary traffic floor, not from the task definition:**
  - a8 1.6.4 logged: "HELD autom8y-asana-service [InsufficientTraffic]: no verdict — the canary served 0 requests between 2026-10-25T15:54:15Z and 2026-10-25T15:58:45Z (floor 50; the baseline served 0)".
  - That ended "Deploy to ECS (a8 CLI)" with exit 4. The run was red. Its Lambda leg still succeeded.
  - At 15:45, :854 had the same sizing as :852 and :853 (8192), so there was no sizing difference for anything to react to.
- **Why the image ended up served anyway:** this is a8's documented HELD semantics on an ECS-native canary. a8 neither promotes nor rolls back, and its message said ECS "will complete this deployment on its own ... unless you run 'a8 deploy rollback' or 'a8 deploy promote'". ECS completed it at 16:01:21Z. A HELD verdict is therefore an un-vetoed promotion. That is a separate finding for the canary owners (a zero-traffic canary is not evidence), and it is out of this drift's scope.

## A trap the bench must see before ruling: a green may come back by itself, and it will be a revert

- **The deploy lane writes manifest sizing even on gated families.**
  - a8 v1.6.4 `internal/aws/tdenv_gate.go:195-209` (`applyOverlays`) skips the env and secret overlays for a gated family. It still calls `applyResourceOverrides` at `:207`.
  - `ecs_deploy_client.go:443` and `:472` say so in so many words: "Task-level resource overrides still apply".
  - The 10-25 asana deploy logged `has_overrides=true`.
- **What that means for asana:** the **next asana satellite deploy will register a revision at memory 8192**. That silently undoes #2932's right-size, and the detector goes green on asana. That green would be a **revert, not a cure**.
- **This has already happened to data (sister case, same PR):**
  - #2932 also cut data's memory from 10240 to 6144 (`terraform/services/data/main.tf:458-459`).
  - The data manifest still says 10240 (`manifest.yaml:457-459`).
  - On 2026-10-31T11:49:33Z, `github-actions-deploy` registered `autom8y-data-service:708` at **10240**. :709 (11-01) is also at 10240, and it is what is served now.
  - Reconcile run 41195860626 (10-31T11:12Z) still listed `data:ecs_task_definition`. Run 41200509996 (12:18Z) listed only asana.
  - So **data "cleared" because its cost right-size was reverted live.** Data now serves 10240 against a Terraform declaration of 6144, which is real Terraform drift that this detector cannot see.
  - (:706 and :707 at 6144 were registered on 10-31 by the SSO admin role. This is noted, not chased.)

## Q4: cure proposal for the bench

**Pick: (c), a declared-side change in the a8 manifest (the detector's declared source), not in Terraform.** In parallel, the a8 pin moves to a tag that carries it.

### The change

| Repo and file | Line | From | To |
|---|---|---|---|
| `autom8y/a8` `manifest.yaml` (`services.asana.resources.memory`) | 607 | `memory: 8192` | `memory: 4096` |
| `autom8y/a8` `manifest.yaml` (`services.data.resources.memory`), sister, same PR | 459 | `memory: 10240` | `memory: 6144` |

- Line numbers are identical at v1.6.4 and at a8 main 50712dada43a.
- Keep `cpu: 2048` at lines 606 and 458 unchanged; it already matches.

### How it lands

1. **The PR** in `autom8y/a8`, changing only those two lines (the second is the sister edit).
2. **An a8 release tag** that contains it. The reconcile job checks out `manifest.yaml` at the **tag**, not at main, so merging alone does not clear the drift.
3. **A move of `vars.A8_VERSION`** to that tag. The reconcile job and the deploy lane both resolve from it (the 10-25 receiver ran "a8 1.6.4"). This is a repository-variable write: an operator act, routed by the clerk.

### What it does and does not need

- **No Terraform apply for asana.** Served :856 already equals Terraform. The asana cure touches no infrastructure, so this is **not Tom's IaC floor** for asana.
- **Data is different.** Once the manifest says 6144, data still serves 10240 (:709), so reconcile would then go red on `data:ecs_task_definition`. That is the honest state. It is cured by the gated Service Terraform apply for data that #2932 already intended, and that apply **is Tom's floor**.
- **Ordering:** land the data manifest line **before or with** that data apply. Otherwise the next data deploy reverts it again.

### What this does

- The detector's declared value becomes equal to Terraform's. The hourly red on `asana:ecs_task_definition` clears with **no production change**.
- It stops the deploy lane from reverting the right-size on the next asana deploy.

### Why not (a), a Terraform catch-up

- Terraform already declares 4096 at `terraform/services/asana/main.tf:195`, and Terraform rendered :856.
- A Terraform-side "catch-up" against :856 is an empty diff.
- Reverting Terraform to 8192 to satisfy the manifest would undo a measured cost decision in order to please a stale copy.

### Why not (b), a known-gap entry

- **This is not the product of the image-pin design.** The image is not compared, and the image is unchanged from :854 to :856.
- **An exemption would be wrong in kind:**
  - `KNOWN_GAPS` exempts a pair by *status* ("QUERY_FAILED", "DEFERRED"). Exempting a `DRIFT` would add a new meaning to the block.
  - It would blind asana's only paging comparator for secrets and sizing.
  - It would leave the deploy-lane revert armed.

### Structural follow-up (for the a8 owners, not this cure)

- Sizing for gated families has two writers, the a8 manifest and Terraform. That is the same class of defect that D-6 removed for env and secrets. #2932 shows it bites on every Terraform right-size.
- The durable fix is to retire `resources:` from the manifest rows of gated families (asana, auth, scheduling) and to stop `applyResourceOverrides` on the gated arm, so that Terraform is the single writer.
- The cost: the detector's sizing check for those rows goes away. The Terraform drift plan covers sizing instead. The comparator keeps reading secrets, so the asana row stays observed.
- This is carded as a recommendation only. It needs an a8 code change and a ruling.

## Boundaries and grades

- **Live-observed** (AWS describe calls, run logs, git objects): the field diff, the registrations, the drift onset, the ECS self-completion of :854, and the data revert. [STRUCTURAL | MODERATE]
- **Code-read, not live-proven for asana:** that the next asana deploy will write 8192 (`tdenv_gate.go:207`). Data's :708 is the live instance of the same function on the non-gated arm. Asana's own revisions cannot discriminate, because :852 to :854 were all 8192 on both sides.
- **Inference:** :855 as a local Terraform apply under SSO (timing only). [PLATFORM-HEURISTIC]
- **Out of scope, routed nowhere by this read:**
  - the empty `SLACK_DRIFT_WEBHOOK_URL` (already with Tom);
  - HELD-means-ECS-promotes;
  - the 10-29 run of ECS "replaced 1 tasks due to an unhealthy status" events on :854 (5 between 00:03Z and 15:34Z, all before the right-size).
