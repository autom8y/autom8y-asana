---
type: review
status: proposed
task: A4b
clerk_row: 18227
supersedes_terms_of: 7450dbaacf72
governed_by: 1709ec3762a0
scope: BEFORE record over the full life of the served asana image, and card-31 AFTER terms for the next asana deploy
repo: autom8y/autom8y-asana
main_at_read: d912fa0d3e59
read_window_utc: 2026-11-01T13:49Z to 2026-11-01T14:06Z
stamped_utc: "2026-11-01T14:06:47Z"
author_role: observability-engineer (sre, borrowed seat)
mode: READ-ONLY (ECS/ELB describe, CloudWatch metric reads, Logs Insights stats queries; zero writes, invokes or dispatches)
---

# A4b: BEFORE record and card-31 AFTER terms, asana deploy

Stamp: `date -u` = 2026-11-01T14:06:47Z. Region us-east-1. All times are UTC.
Shas and digests are 12-hex prefixes. Resources are named by service, target-group or log-group name only.

Governing ruling: bench card 31 (1709ec3762a0). This record supersedes the **terms** (§7) of A4 (7450dbaacf72). A4 itself is not edited. Resource names are reused from A4: cluster `autom8y-cluster`, service `autom8y-asana-service`, ALB `autom8-prod-alb`, target group `autom8y-asana-service`, log group `/ecs/autom8y-asana-service`.

## 0. Corrections to the prior record (read these first)

| # | A4 said | This read shows | Effect |
|---|---|---|---|
| C-1 | §0 P-3: image 2dcb88fa23e5 "reached the served task only on 10-29". | It has been served since **2026-10-25T16:01:21Z**. Task def :854 (registered 15:45:37Z) started a task at 15:45:55Z, and ECS logged "deployment completed" at 16:01:21Z. That task served from the **alternate** target group `a8-asana-green` (3505 requests, 10-25 to 10-29). Over the same span the `autom8y-asana-service` target group had 0 requests. The 10-29 roll to :856 moved serving back to `autom8y-asana-service`. | A4's BEFORE read only the `autom8y-asana-service` target group. The full life spans **both** target groups, and so does the AFTER. |
| C-2 | §4: "HTTPCode_ELB_5XX_Count = 0", read with a TargetGroup dimension, with RequestCount as the positive control. | `list-metrics` shows that `HTTPCode_ELB_5XX_Count`, `_502`, `_503` and `_504` are published **only** with `[LoadBalancer]` or `[AvailabilityZone,LoadBalancer]`, never with a TargetGroup. A TargetGroup-dimensioned read returns 0 by construction. A positive control on a different metric name cannot detect that. | ELB-generated 5xx cannot be attributed to asana from CloudWatch metrics. This record reports them ALB-wide (shared by every service on `autom8-prod-alb`) and states a separate rule for them (§4, T-3b). |
| C-3 | §1: the memory term was not in A4. | :854 and :855 had memory **8192**. :856 (served since 10-29T22:12:23Z) has **4096**. | The image's life spans two memory configurations. The BEFORE is reported for both segments, and the AFTER requires 4096 (card 31 ruling 4). |

## 1. Served state now (read 2026-11-01T13:50Z, reconfirmed 14:04Z)

| Field | Value |
|---|---|
| Service | ACTIVE, task def `autom8y-asana-service:856`, desired 1 / running 1 / pending 0 |
| Deployments | 1, PRIMARY, rolloutState COMPLETED (created 2026-10-29T22:11:34Z, completed 22:27:27Z) |
| Task-def memory / cpu | **4096** / 2048 |
| asana container digest (task def and running task `imageDigest`) | **`2dcb88fa23e5`** |
| adot-collector digest | `40a7eb9bfa58` |
| Running task | started 2026-10-29T22:12:23Z, HEALTHY, task memory 4096 |
| Target groups | `autom8y-asana-service`: 1 target, healthy. `a8-asana-green`: 0 targets. |
| Production listener rule weights | `autom8y-asana-service` 100, `a8-asana-green` 0 |
| Deployment strategy | CANARY, canaryPercent 10, canaryBakeTimeInMinutes 5, bakeTimeInMinutes 0, circuit breaker **disabled** |

Task-def revisions of this image: :854 (8192, ACTIVE), :855 (8192, INACTIVE), :856 (4096, ACTIVE). All three carry `2dcb88fa23e5`.

## 2. BEFORE: life of image 2dcb88fa23e5

**Life span measured: [2026-10-25T16:02:00Z, 2026-11-01T13:52:00Z), 165.83 h.** The start is the first whole minute after "deployment completed" at 16:01:21Z. The 15:45:55Z to 16:02Z canary and shift window is excluded (N-4).
Segments: **8192** = [10-25T16:02Z, 10-29T22:27Z). **4096** = [10-29T22:27Z, 11-01T13:52Z), starting at the 10-29 "deployment completed" event.

### 2a. Requests (ALB RequestCount, Sum, 60 s period, 7 windows of 1440 minutes or fewer)

| | `autom8y-asana-service` TG | `a8-asana-green` TG | Total |
|---|---|---|---|
| Life | 4565 | 3505 | **8070** |
| 8192 segment | 0 | 3505 | 3505 |
| 4096 segment | 4565 | 0 | 4565 |

### 2b. 5xx

| Count | Life | 8192 seg | 4096 seg | Attribution |
|---|---|---|---|---|
| HTTPCode_Target_5XX_Count, both asana TGs | **0** | 0 | 0 | asana (TargetGroup dimension) |
| HTTPCode_Target_4XX_Count, both asana TGs | 0 | 0 | 0 | asana |
| HTTPCode_ELB_5XX_Count, **ALB-wide** | 2080 | 655 | 1425 | all services on `autom8-prod-alb`; not attributable (C-2) |
| ELB 502 / 503 / 504, ALB-wide | 23 / 2046 / 11 | | | same |

- **Positive control (Target 5xx):** the same dimension sets return nonzero data before the life (`autom8y-asana-service` TG 9 on 2026-10-21; `a8-asana-green` TG 6 in 2026-09). The life's 0 is a real zero over 8070 requests.
- **ELB 5xx coincidence bound:** only **5** of the 2080 ALB-wide ELB 5xx fall within [T-15 min, T+20 min] of the 10 asana task starts in the life. The large 503 bursts (124, 307, 128, 552, 320, 294 and 224 per hour) do not coincide with any asana task event. 503 on this ALB is dominated by other services. ALB-wide 502+504 = 34 over the life (0.205 per hour).
- `a8-asana-green` UnhealthyRoutingRequestCount = 35 (10-29T00:02Z to 00:03Z, during an unhealthy-task replacement): requests the ALB routed fail-open to an unhealthy target.

### 2c. Task health events (ECS service event buffer; oldest retained event is 10-25T15:45:55Z, so the life is fully covered)

| Segment | "replaced 1 tasks due to an unhealthy status" | Hours | Rate |
|---|---|---|---|
| 8192 | **9** (10-25T23:33Z, 10-26T07:34Z, 10-28T11:33Z, 10-28T13:02Z, 10-29T00:03Z, 03:34Z, 11:34Z, 13:02Z, 15:34Z) | 102.4 | 0.088/h |
| 4096 | **0** | 63.4 | 0 |

This is reported, not explained. No cause is claimed for the difference between segments [TACTICAL | MODERATE].

### 2d. Error-class census (`/ecs/autom8y-asana-service`, Logs Insights, counts and class names only)

**Method.** The error records are the JSON records with `level` in {error, critical, exception, fatal} or `stdlib_level` in {error, critical, ERROR, CRITICAL}. The query is `stats count(*) by level, event, error_type, stdlib_logger, subsystem`, run in 1-day windows. A class signature is computed client-side (script `errclass.py`, §5) as follows:
- a snake_case `event` is used as-is: `ev:<event>[:<error_type>][@<subsystem>]`
- a free-text `event` (stdlib records with data interpolated) is normalized: quoted strings, URLs, emails, UUIDs, hex, numbers, paths and `=value` are stripped, then the result is hashed: `tmpl:<logger>:<sha256[0:12]>`
- the `operation` field is excluded because it carries data-bearing keys.

No log text is printed or stored. Normalization collapses 1166 raw event strings into 12 classes.

| Query set | recordsScanned per window | Total scanned | Error records |
|---|---|---|---|
| 8192 seg, W1 to W5 | 93280, 84108, 95537, 126582, 29480 | 428987 | 1038 |
| 4096 seg, W1 to W3 | 115963, 114639, 77025 | 307627 | 752 |
| Life | | 736614 | **1790** (10.8/h; 4096 seg 11.9/h) |

`recordsScanned` is an Insights scan statistic, not an exact line count. A second windowing of the same span scanned 740104. The error-record count, 1790, was identical on both windowings.

**Census: 12 classes over the life (the BEFORE class set).**

| Class signature | Life | 8192 | 4096 |
|---|---|---|---|
| `ev:retry_exhausted:NoSuchKey@s3` | 501 | 341 | 160 |
| `tmpl:autom8_asana:c9d6a8c1bf23` | 535 | 290 | 245 |
| `tmpl:autom8_asana:abeef6279aab` | 238 | 114 | 124 |
| `tmpl:autom8_asana:1e4191a2141e` | 191 | 127 | 64 |
| `tmpl:autom8_asana:c4bfaaf84c98` | 168 | 71 | 97 |
| `ev:cascade_key_null_audit` | 96 | 61 | 35 |
| `tmpl:autom8_asana:de459be4d99c` | 26 | 9 | 17 |
| `ev:freshness_delta_section_failed` | 11 | 6 | 5 |
| `ev:ungated_below_floor_write_refused` | 10 | 10 | 0 |
| `ev:forwarding_receipt_error` | 8 | 4 | 4 |
| `tmpl:opentelemetry.exporter.otlp.proto.grpc.exporter:8cf06959fe4c` | 4 | 4 | 0 |
| `tmpl:autom8_asana:54f1585340b2` | 2 | 1 | 1 |

The 4096 segment's 10 classes are a strict subset of the 8192 segment's 12.

**Non-JSON lines (153002 over the life).** They break down as follows:
- `INFO` lead token: 107216
- timestamped stdlib format `YYYY-MM-DD HH:MM:SS,mmm - logger - LEVEL - `: 45773 (WARNING 43210, INFO 1401, **ERROR 1160**, CRITICAL 0)
- other lowercase lead token: 10
- `RuntimeWarning`: 1 (a warning, not an error class)
- `Traceback`, indented `File` or `ERROR:`-led lines: **0**

The 1160 plain `ERROR` lines are a second rendering of the 1160 `tmpl:autom8_asana:*` records. **Mirror invariant over the life: 1160 = 1160, surplus 0.** The AFTER enforces this invariant (T-4).

**adot-collector sidecar** (`/ecs/asana/adot-collector`, informational; the deploy does not change the sidecar): 1 error class, `internal/queue_sender.go:50`, 32 lines, all in the 8192 segment. 0 in the 4096 segment (recordsScanned 680 and 29).

**Negative and positive controls for the census:**
- The stream filter with a bogus task id returns 0 records, so it filters.
- The current task's stream over the last 24 h returns 289 error records, 9 classes, 0 NEW against the BEFORE set, mirror 206 = 206.

### 2e. Request rate (sizes the AFTER window)

| Measure | Value |
|---|---|
| Life requests per hour, mean | **48.9** (164 full UTC hours) |
| Lowest full hour | **24** (median 24, max 224) |
| 4096 segment mean / lowest | 73.0 / 24 |
| Shape | a flat floor of 24/h (one request per 150 s), plus bursts at about 00, 04, 08, 12, 16 and 20 UTC (hour means 99 to 139) |
| Minutes to accumulate 50 requests, from every start minute in the life (n = 9842) | median **115**, p99 **130**, max **131** |

## 3. NOT TAKEN and open

- **N-1 asana-attributable ELB 5xx: NOT TAKEN.** Not measurable from metrics (C-2). ALB access logs are enabled (`access_logs.s3.enabled=true`), but they were not read because they carry client IPs and request paths, which are outside this seat. Recorded instead: the ALB-wide count and the coincidence bound (§2b).
- **N-2 identity of the 24/h floor caller and the 4-hourly bursts: NOT TAKEN.** Establishing it needs request paths or source addresses. If the floor is synthetic, 50 requests may exercise little of the code (§4 weakness W-3).
- **N-3 Grafana alert state: NOT TAKEN** (seat limit).
- **N-4 the canary and shift window 2026-10-25T15:45:55Z to 16:02:00Z** is excluded from the life totals.
- **U-2 (from A4) stays open:** which path rolled ECS to :856 on 10-29.
- No AWS call failed on auth. Every read above was taken.

## 4. AFTER terms (card 31 form, declared before the deploy)

**Definitions**
- `OLD` = `2dcb88fa23e5`. `NEW_TG` = the asana target group that held **0 targets** in the press-time BEFORE read and holds the new task after the deploy. Today that is `a8-asana-green`. Evidence for the alternation: the 10-25 roll served from `a8-asana-green`, and the 10-29 roll served from `autom8y-asana-service`.
- `T0` = createdAt of the ECS event "registered 1 targets in (target-group ... `NEW_TG`)" for the new task. Hard ceiling: **`TC` = T0 + 180 min**.
- `T50` = the end of the first minute at which cumulative RequestCount on `NEW_TG` from T0 reaches 50.
- **Window W = [T0, T50)**. If 50 is not reached before TC, then W = [T0, TC) and the verdict cannot be better than INCONCLUSIVE.
- Expected duration: at the lowest measured rate (24/h) it is **125 min**. The life's observed worst case from any start minute is 131 min. The ceiling of 180 min is about 1.4x the expected duration [PLATFORM-HEURISTIC: margin over the observed max]. If the canary stalls at 10% weight, 50 requests would take about 20 h, so TC returns INCONCLUSIVE, which is the honest result.
- All reads are taken at least 10 min after the end of W, to allow for metric and log ingestion lag.

**Attribution to the new image**
- **Requests and Target 5xx:** per target group. During and after cutover, `NEW_TG` holds only new-image tasks, so its RequestCount and Target_5XX count are new-image counts exactly.
- **Logs:** per log stream `ecs/autom8y-asana-service/<new task id>`, which is exact.
- **Weaknesses:**
  - W-1: if a deploy path reuses the same target group (a rolling update, or the unidentified U-2 path), old and new tasks share it during overlap. Fallback: start the window at the "has stopped" event of the last OLD task (after its drain), and record that the fallback was used.
  - W-2: ELB-generated 5xx are ALB-wide only (T-3b).
  - W-3: the 24/h floor may be synthetic (N-2). Record whether W contained a burst hour (00, 04, 08, 12, 16 or 20 UTC) as a coverage FLAG, not a gate.

**Terms (each term is PASS, FAIL or HELD as stated)**

- **T-1 traffic.** PASS: at least 50 requests on `NEW_TG` in [T0, TC). Fewer than 50: INCONCLUSIVE.
- **T-2 served identity.** All of these, read after T50:
  - every running asana task's container `imageDigest` equals the task-def image digest
  - that digest is **not** `2dcb88fa23e5`
  - adot-collector is `40a7eb9bfa58`, or the change is named.

  Any failure: FAIL.
- **T-3a Target 5xx.** Allowed new-image Target 5xx in W = floor(n_W x k/N), where k/N is the press-time BEFORE Target 5xx count over BEFORE requests. Today k/N = 0/8070, so **the allowance is 0**. Also: Target_5XX on the old TG in W = 0. Any excess: FAIL.
- **T-3b ELB 5xx (ALB-wide).**
  - PASS: ALB-wide ELB 502 + 504 in W is **2 or fewer**. The BEFORE rate is 0.205/h. Empirically, 4.5% of 180-min windows in the life had 3 or more, and the Poisson estimate is P(3 or more) = 2.5%.
  - 3 or more: **HELD**, pending target-group attribution from the access logs by a seat cleared to read them.
  - ELB 503 is reported, not judged (it is dominated by other services, §2b).
- **T-3c health.** PASS needs all of:
  - `NEW_TG` UnhealthyRoutingRequestCount in W = 0
  - `NEW_TG` HealthyHostCount minimum is 1 or more from the first nonzero request minute to the end of W
  - **no** ECS event "replaced 1 tasks due to an unhealthy status" in [T0, end of W]. The 4096 BEFORE rate is 0 in 63.4 h.

  Any failure: FAIL.
- **T-4 error classes.** Run `errclass.py T0 T_end --stream <new task id> --before before_classes.json`.
  - PASS: **NEW classes = 0** against the press-time BEFORE set (today the 12 in §2d), **and** the mirror line reads `surplus=0`.
  - Any NEW class, or a surplus: FAIL. A known false-positive mode: an existing message whose data shape escapes the normalizer hashes as a new `tmpl:` class. That still FAILs the term, and the bench may rule on it.
  - The error-record rate in W is reported against the BEFORE 11.9/h as context, not judged.
- **T-5 memory.** Task-def memory **and** running-task memory = **4096**. 8192, or any other value: FAIL. The bench refused the 8192 revert (card 31 ruling 4).
- **T-6 steady state.** At the read: runningCount == desiredCount, deployments = 1, rolloutState COMPLETED. Otherwise: FAIL.

**Verdict rule**
- **LANDED** = T-1 through T-6 all PASS.
- **FAIL** = any term FAILs. FAIL takes precedence over HELD and INCONCLUSIVE.
- **HELD** = no FAIL, and T-3b is HELD.
- **INCONCLUSIVE** = no FAIL, and T-1 is short of 50 at TC.
- **HELD and INCONCLUSIVE are never LANDED** (card 31 ruling 1). The a8 Receiver's own verdict, for example HELD on InsufficientTraffic, neither satisfies nor overrides any term.

**Press-time BEFORE re-take:** run `before.sh <press time>` and `errclass.py 1792944120 <press epoch> --json before_classes.json`, using the same queries as above. The press-time numbers and class set replace §2's numbers in the AFTER comparison.

## 5. Kit (bash, not zsh; each CloudWatch dimension is a separate `Name=,Value=` argument; `TZ=UTC` pinned)

Life-start epoch 1792944120 = 2026-10-25T16:02:00Z. Requirements: `aws` CLI v2, `jq` and `python3`. Run each script with `bash script.sh` or `python3 -I script.py`.

### 5a. `before.sh` (BEFORE re-take; reproduced §2a, §2b and §2e exactly at 14:05Z)

```bash
#!/usr/bin/env bash
# A4b BEFORE re-take. Run with bash (not zsh). Read-only.
# usage: bash before.sh END_ISO OUTDIR      (life start is fixed at 2026-10-25T16:02:00Z)
set -uo pipefail
export AWS_REGION=us-east-1 AWS_PAGER="" TZ=UTC
START=2026-10-25T16:02:00Z; END=$1; OUT=$2; mkdir -p "$OUT"; rm -f "$OUT"/*.tsv
LB=app/autom8-prod-alb/b49b62354ff9d00f
TG_BLUE=targetgroup/autom8y-asana-service/75206e89d0fd529e
TG_GREEN=targetgroup/a8-asana-green/a3d18930301108f9
ep() { python3 -I -c "import datetime as d,sys;print(int(d.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()))" "$1"; }
iso() { python3 -I -c "import datetime as d,sys;print(d.datetime.fromtimestamp(int(sys.argv[1]),d.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$1"; }
get() { local f=$1 metric=$2 ws=$3 we=$4; shift 4
  aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name "$metric" \
    --start-time "$ws" --end-time "$we" --period 60 --statistics Sum --dimensions "$@" --output json \
  | jq -r '.Datapoints[] | "\(.Timestamp) \(.Sum)"' >> "$OUT/$f.tsv"; }
s=$(ep "$START"); e=$(ep "$END"); t=$s
while [ "$t" -lt "$e" ]; do            # 1440 one-minute datapoints per call at most
  n=$((t+86400)); [ "$n" -gt "$e" ] && n=$e; ws=$(iso $t); we=$(iso $n); echo "window $ws $we"
  get req_blue   RequestCount              "$ws" "$we" Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$TG_BLUE
  get req_green  RequestCount              "$ws" "$we" Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$TG_GREEN
  get t5xx_blue  HTTPCode_Target_5XX_Count "$ws" "$we" Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$TG_BLUE
  get t5xx_green HTTPCode_Target_5XX_Count "$ws" "$we" Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$TG_GREEN
  get elb502_alb HTTPCode_ELB_502_Count    "$ws" "$we" Name=LoadBalancer,Value=$LB
  get elb503_alb HTTPCode_ELB_503_Count    "$ws" "$we" Name=LoadBalancer,Value=$LB
  get elb504_alb HTTPCode_ELB_504_Count    "$ws" "$we" Name=LoadBalancer,Value=$LB
  get elb5xx_alb HTTPCode_ELB_5XX_Count    "$ws" "$we" Name=LoadBalancer,Value=$LB
  t=$n
done
python3 -I - "$OUT" "$START" "$END" <<'PY'
import sys,collections,datetime as dt,statistics as st,bisect
D,S,E=sys.argv[1],*(dt.datetime.fromisoformat(x.replace('Z','+00:00')).replace(tzinfo=None) for x in sys.argv[2:4])
def load(n):
    d=collections.defaultdict(float)
    for l in open(f"{D}/{n}.tsv"):
        t,v=l.split(); d[dt.datetime.fromisoformat(t).astimezone(dt.timezone.utc).replace(tzinfo=None)]+=float(v)
    return d
M={n:load(n) for n in ("req_blue","req_green","t5xx_blue","t5xx_green","elb502_alb","elb503_alb","elb504_alb","elb5xx_alb")}
tot=lambda n:int(sum(v for t,v in M[n].items() if S<=t<E))
for n in M: print(f"{n:11s} sum={tot(n)}")
mins=[S+dt.timedelta(minutes=i) for i in range(int((E-S).total_seconds()//60))]
r=[M["req_blue"].get(m,0)+M["req_green"].get(m,0) for m in mins]
H=collections.defaultdict(float)
for m,v in zip(mins,r): H[m.replace(minute=0)]+=v
full=[h for h in sorted(H) if h>=S and h+dt.timedelta(hours=1)<=E and h.minute==0 and h>S.replace(minute=0)]
vals=[H[h] for h in full]
print(f"life_hours={(E-S).total_seconds()/3600:.2f} requests={int(sum(r))} full_hours={len(vals)} mean_per_h={st.mean(vals):.1f} lowest_h={min(vals):.0f} median_h={st.median(vals):.0f} max_h={max(vals):.0f}")
c=[0]
for v in r: c.append(c[-1]+v)
w=sorted(j-i for i in range(len(mins)) for j in [bisect.bisect_left(c,c[i]+50)] if j<len(c))
print(f"minutes_to_50: median={w[len(w)//2]} p99={w[int(.99*(len(w)-1))]} max={w[-1]}")
PY
```

Reference output at END=2026-11-01T13:52:00Z: `req_blue 4565, req_green 3505, t5xx_blue 0, t5xx_green 0, elb502_alb 23, elb503_alb 2046, elb504_alb 11, elb5xx_alb 2080; life_hours=165.83 requests=8070 full_hours=164 mean_per_h=48.9 lowest_h=24 median_h=24 max_h=224; minutes_to_50: median=115 p99=130 max=131`.

### 5b. `after.sh` (AFTER read; dry-run against today's state succeeded at 14:04Z)

```bash
#!/usr/bin/env bash
# A4b AFTER kit. Run with bash (not zsh). Read-only: describe/list/get calls only.
# usage: bash after.sh T0 [TEND]   T0/TEND = ISO UTC minute, e.g. 2026-11-03T14:07:00Z
#        TEND defaults to T0+180 min (the ceiling TC). Re-run with TEND=T50 once S4 shows cum>=50.
set -uo pipefail
export AWS_REGION=us-east-1 AWS_PAGER="" TZ=UTC
C=autom8y-cluster; SVC=autom8y-asana-service; OLD=2dcb88fa23e5
LB=app/autom8-prod-alb/b49b62354ff9d00f
TG_BLUE=targetgroup/autom8y-asana-service/75206e89d0fd529e
TG_GREEN=targetgroup/a8-asana-green/a3d18930301108f9
T0=$1
TEND=${2:-$(python3 -I -c "import datetime as d,sys;t=d.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'));print((t+d.timedelta(minutes=180)).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$T0")}
echo "== window [$T0, $TEND)  read at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "== S1 served state (T-2, T-5, T-6)"
aws ecs describe-services --cluster "$C" --services "$SVC" --output json | jq -r '.services[0] | "taskdef=\(.taskDefinition|split("/")[-1]) desired=\(.desiredCount) running=\(.runningCount) pending=\(.pendingCount) deployments=\(.deployments|length) rollout=\([.deployments[].rolloutState]|join(","))"'
TD=$(aws ecs describe-services --cluster "$C" --services "$SVC" --query 'services[0].taskDefinition' --output text)
aws ecs describe-task-definition --task-definition "$TD" --output json | jq -r '.taskDefinition | "td_memory=\(.memory)", (.containerDefinitions[] | "  \(.name) td_digest=\((.image|split("@sha256:")[1] // "NOT-PINNED-BY-DIGEST")[0:12])")'
TASKS=$(aws ecs list-tasks --cluster "$C" --service-name "$SVC" --desired-status RUNNING --query 'taskArns' --output text)
aws ecs describe-tasks --cluster "$C" --tasks $TASKS --output json | jq -r --arg old "$OLD" '.tasks[] | "task_id=\(.taskArn|split("/")[-1]) td=\(.taskDefinitionArn|split("/")[-1]) health=\(.healthStatus) task_memory=\(.memory) started=\(.startedAt)", (.containers[]|select(.name=="autom8y-asana-service")|(.imageDigest|sub("sha256:";"")|.[0:12]) as $d|"  served_digest=\($d) differs_from_old=\($d!=$old)")'

echo "== S2 which target group holds the running task(s) (NEW_TG)"
for n in autom8y-asana-service a8-asana-green; do
  A=$(aws elbv2 describe-target-groups --names "$n" --query 'TargetGroups[0].TargetGroupArn' --output text)
  echo "  $n targets=$(aws elbv2 describe-target-health --target-group-arn "$A" --query 'length(TargetHealthDescriptions)' --output text) states=$(aws elbv2 describe-target-health --target-group-arn "$A" --query 'TargetHealthDescriptions[].TargetHealth.State' --output text)"
done

echo "== S3 ECS events since T0 (T0 registration, drains, unhealthy replacements: T-3c)"
aws ecs describe-services --cluster "$C" --services "$SVC" --output json | jq -r --arg t0 "$T0" '.services[0].events[] | select(.createdAt >= ($t0|sub("Z$";""))) | select(.message|test("steady state")|not) | "  \(.createdAt[0:19])Z \(.message|gsub("arn:[^ )]*:targetgroup/";"targetgroup/")|gsub("\\(task [^)]*\\)";"(task)")|gsub("\\(deployment [^)]*\\)";"(deployment)")|gsub("\\(service [^)]*\\) ?";"")|gsub("taskSet [^)]*";"taskSet"))"'

echo "== S4 per-minute requests and cumulative, both target groups (T-1; T50 = first row with cum>=50 on NEW_TG)"
for tg in "$TG_BLUE" "$TG_GREEN"; do
  aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCount \
    --start-time "$T0" --end-time "$TEND" --period 60 --statistics Sum \
    --dimensions Name=LoadBalancer,Value="$LB" Name=TargetGroup,Value="$tg" --output json \
  | jq -r --arg tg "$(echo "$tg"|cut -d/ -f2)" '[.Datapoints[]|select(.Sum>0)]|sort_by(.Timestamp)|reduce .[] as $p ({c:0,rows:[]}; .c+=$p.Sum | .rows+=["  \($tg) \($p.Timestamp[0:16])Z n=\($p.Sum) cum=\(.c)"]) | (.rows[]), "  \($tg) TOTAL=\(.c)"'
done

echo "== S5 5xx and health over the window (T-3a, T-3b, T-3c)"
m() { aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name "$1" --start-time "$T0" --end-time "$TEND" --period 60 --statistics "$2" "${@:3}" --output json | jq -r --arg s "$2" '[.Datapoints[]|.[$s]] | if length==0 then "none(0 datapoints)" elif $s=="Minimum" then (min|tostring) else (add|tostring) end'; }
for tg in "$TG_BLUE" "$TG_GREEN"; do
  n=$(echo "$tg"|cut -d/ -f2)
  echo "  $n Target_5XX=$(m HTTPCode_Target_5XX_Count Sum --dimensions Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$tg) UnhealthyRouting=$(m UnhealthyRoutingRequestCount Sum --dimensions Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$tg) HealthyHostMin=$(m HealthyHostCount Minimum --dimensions Name=LoadBalancer,Value=$LB Name=TargetGroup,Value=$tg)"
done
echo "  ALB-wide (all services) ELB_502=$(m HTTPCode_ELB_502_Count Sum --dimensions Name=LoadBalancer,Value=$LB) ELB_504=$(m HTTPCode_ELB_504_Count Sum --dimensions Name=LoadBalancer,Value=$LB) ELB_503=$(m HTTPCode_ELB_503_Count Sum --dimensions Name=LoadBalancer,Value=$LB) ELB_5XX=$(m HTTPCode_ELB_5XX_Count Sum --dimensions Name=LoadBalancer,Value=$LB)"
```

**Method replay on the 10-29 roll** (`bash after.sh 2026-10-29T22:00:00Z 2026-10-29T23:00:00Z`, the copy extracted from this file):
- S3 gives T0 = 22:12:18Z ("registered 1 targets" in `autom8y-asana-service`), the old task stopping at 22:26:24Z, its deregistration from `a8-asana-green` at 22:26:34Z, and "deployment completed" at 22:27:27Z.
- S4 shows 12 requests on **each** target group in that hour. Per-target-group counting separated old-image and new-image traffic during the overlap.

`$TASKS` is unquoted on purpose: bash word-splits it into one argument per task, and zsh would not. "none(0 datapoints)" on a 5xx metric is a zero, because these metrics publish only nonzero minutes. The positive control in §2b shows the dimension set returns data when errors occur.

### 5c. `errclass.py` (error-class census; prints class signatures and counts only)

T-4 run: `python3 -I errclass.py <T0 epoch> <end-of-W epoch> --stream <new task id from S1> --before before_classes.json`.
Press-time BEFORE: `python3 -I errclass.py 1792944120 <press epoch> --json before_classes.json` (no `--stream`; every stream in the BEFORE is the old image). The kit's T-4 uses the class **keys** of that JSON.

```python
#!/usr/bin/env python3
"""asana error-class census (A4b). Prints class signatures and counts only; never prints log text.
usage: python3 -I errclass.py START_EPOCH END_EPOCH [--stream ECS_TASK_ID] [--json OUT] [--before BEFORE.json]"""
import sys,json,subprocess,time,re,hashlib,collections,os
os.environ.update(AWS_REGION="us-east-1",AWS_PAGER="")
G="/ecs/autom8y-asana-service"
Q=('filter level in ["error","critical","exception","fatal"] or stdlib_level in ["error","critical","ERROR","CRITICAL"] '
   '| stats count(*) as n by level, event, error_type, stdlib_logger, subsystem')
ID=re.compile(r"[a-z_][a-z0-9_.]{0,79}")          # snake_case event names
NAME=re.compile(r"[A-Za-z_][A-Za-z0-9_.]{0,79}")   # logger, exception type, subsystem
SUBS=[(r"https?://\S+","<url>"),(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b","<email>"),
      (r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b","<uuid>"),
      (r"'[^']*'","<q>"),(r'"[^"]*"',"<q>"),(r"\b[0-9a-fA-F]*\d[0-9a-fA-F]*[a-fA-F][0-9a-fA-F]*\b|\b[0-9a-fA-F]*[a-fA-F][0-9a-fA-F]*\d[0-9a-fA-F]*\b","<hex>"),
      (r"=\S+","=<v>"),(r"\S*[/\\]\S*","<path>"),(r"[+]?\d[\d\s().-]{5,}\d","<num>"),(r"\d+(\.\d+)?","<n>"),(r"\{.*\}","<obj>"),(r"\[.*\]","<list>"),(r"\s+"," ")]
def h(s): return hashlib.sha256(s.encode()).hexdigest()[:12]
def norm(s):
    for p,r in SUBS: s=re.sub(p,r,s)
    return s.strip()[:160]
def sig(r):
    ev=r.get("event") or ""; et=r.get("error_type") or ""; lg=r.get("stdlib_logger") or ""; sb=r.get("subsystem") or ""
    et=et if NAME.fullmatch(et) else ("h:"+h(et) if et else "")
    sb=sb if NAME.fullmatch(sb) else ("h:"+h(sb) if sb else "")
    lg=lg if NAME.fullmatch(lg) else ("h:"+h(lg) if lg else "")
    if ID.fullmatch(ev): base="ev:"+ev
    else: base="tmpl:"+(lg or "-")+":"+h(norm(ev))
    return base+(":"+et if et else "")+("@"+sb if sb else "")
def run(s,e,q=None):
    q=q or Q
    qid=json.loads(subprocess.check_output(["aws","logs","start-query","--log-group-name",G,"--start-time",str(s),"--end-time",str(e),"--query-string",q,"--limit","10000","--output","json"]))["queryId"]
    while True:
        r=json.loads(subprocess.check_output(["aws","logs","get-query-results","--query-id",qid,"--output","json"]))
        if r["status"] in("Complete","Failed","Cancelled","Timeout"): return r
        time.sleep(2)
S,E=int(sys.argv[1]),int(sys.argv[2])
arg=lambda f:sys.argv[sys.argv.index(f)+1] if f in sys.argv else None
out,before,stream=arg("--json"),arg("--before"),arg("--stream")
PRE=f'filter @logStream = "ecs/autom8y-asana-service/{stream}" | ' if stream else ''
Q=PRE+Q
QM=PRE+r'filter not ispresent(level) | filter @message like /^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:,]+ - [^ ]+ - (ERROR|CRITICAL) - / | stats count(*) as n'
tot=collections.Counter(); t=S; w=0; scanned=0; matched=0; mirror=0
while t<E:
    n=min(t+86400,E); w+=1; r=run(t,n)
    st=r.get("statistics",{}); rows=[{c["field"]:c["value"] for c in x} for x in r.get("results",[])]
    scanned+=st.get("recordsScanned",0); matched+=st.get("recordsMatched",0)
    print(f"W{w} [{t},{n}) status={r['status']} recordsScanned={st.get('recordsScanned',0):.0f} recordsMatched={st.get('recordsMatched',0):.0f} groups={len(rows)}"+("  TRUNCATED" if len(rows)>=10000 else ""))
    for x in rows: tot[sig(x)]+=int(float(x["n"]))
    rm=run(t,n,QM); mrows=rm.get("results",[]); mc=int(float(mrows[0][0]["value"])) if mrows else 0; mirror+=mc
    print(f"   mirror status={rm['status']} recordsScanned={rm.get('statistics',{}).get('recordsScanned',0):.0f} plainErrorLines={mc}")
    t=n
print(f"TOTAL recordsScanned={scanned:.0f} errorRecords={sum(tot.values())} recordsMatched={matched:.0f} classes={len(tot)}")
for k,c in tot.most_common(): print(f"{c:7d}  {k}")
tm=sum(c for k,c in tot.items() if k.startswith("tmpl:autom8_asana:"))
print(f"MIRROR plainErrorLines={mirror} tmpl_autom8_asana_records={tm} surplus={mirror-tm} -> {'OK' if mirror<=tm else 'SURPLUS (unclassified error source)'}")
if before:
    B=set(json.load(open(before)))
    new=sorted(set(tot)-B); print(f"BEFORE classes={len(B)} NEW classes={len(new)}"); [print("  NEW",k,tot[k]) for k in new]
if out: json.dump(dict(tot),open(out,"w"),indent=0,sort_keys=True)
```

Today's BEFORE class set (`before_classes.json`; any JSON whose keys or elements are these 12 strings works with `--before`):

```json
["ev:cascade_key_null_audit", "ev:forwarding_receipt_error", "ev:freshness_delta_section_failed", "ev:retry_exhausted:NoSuchKey@s3", "ev:ungated_below_floor_write_refused", "tmpl:autom8_asana:1e4191a2141e", "tmpl:autom8_asana:54f1585340b2", "tmpl:autom8_asana:abeef6279aab", "tmpl:autom8_asana:c4bfaaf84c98", "tmpl:autom8_asana:c9d6a8c1bf23", "tmpl:autom8_asana:de459be4d99c", "tmpl:opentelemetry.exporter.otlp.proto.grpc.exporter:8cf06959fe4c"]
```

Grade: every measured value is [TACTICAL | MODERATE]. They are direct reads by this seat at the stamped time. The terms are self-authored, so they cap at MODERATE until a rite-disjoint seat re-runs the kit.
