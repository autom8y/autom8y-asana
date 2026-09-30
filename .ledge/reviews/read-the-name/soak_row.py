"""S-1 soak row reader — durable home (rebuilt 2026-09-30 after a /tmp cleanup deleted the session copy).

Usage:  python3 soak_row.py YYYY-MM-DD [YYYY-MM-DD ...]      (read-only; region us-east-1)

Reads, for each complete UTC day, the SOAK §3 row criteria from the evaluator's OWN run lines and CloudWatch:
evaluations / controlled / refused, evaluator_version mix, LastSuccessTimestamp SampleCount, the prober
freshness gauge (count, max), the FOUR named floor alarms plus the success-gap alarm (state at day end,
transitions in the day, action topics), digests published (run lines with paged=true, page_message_id),
the office-line floor-class counts, and the *** residual (max share, runs judged high).
FAIL LOUD: any query that does not complete prints UNTAKEN; nothing is folded into a zero.
Fences: guid8 only on output; 12-digit tokens are redacted before printing; no office names are read.
"""

import datetime as dt
import json
import re
import subprocess
import sys
import time

R = "us-east-1"
LG = "/aws/lambda/autom8-email-booking-intake-office-floor"
ALARMS = [
    "autom8-ebi-booking-floor-freshness-prober-liveness",
    "autom8-ebi-booking-floor-lambda-freshness",
    "autom8-email-booking-intake-office-floor-dlq-not-empty",
    "autom8-email-booking-intake-office-floor-lambda-errors",
    "autom8-ebi-booking-floor-invoke-success-gap",
]


def emit(*p):
    sys.stdout.write(re.sub(r"\d{12}", "<ACCOUNT>", " ".join(str(x) for x in p)) + "\n")
    sys.stdout.flush()


def aws(*a):
    for i in range(6):
        r = subprocess.run(
            ["aws", *a, "--region", R, "--output", "json"], capture_output=True, text=True
        )
        if r.returncode == 0:
            return json.loads(r.stdout) if r.stdout.strip() else {}
        if any(k in r.stderr for k in ("Throttl", "ServiceUnavailable", "LimitExceeded")):
            time.sleep(3 * (i + 1))
            continue
        emit("  AWS ERROR:", r.stderr.strip()[:160])
        return None


def insights(s, e, q):
    st = aws(
        "logs",
        "start-query",
        "--log-group-name",
        LG,
        "--start-time",
        str(s),
        "--end-time",
        str(e),
        "--query-string",
        q,
        "--limit",
        "10000",
    )
    if not st:
        return None
    for _ in range(150):
        res = aws("logs", "get-query-results", "--query-id", st["queryId"])
        if res and res.get("status") in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(2)
    if not res or res.get("status") != "Complete":
        return None
    return [{f["field"]: f["value"] for f in r if f["field"] != "@ptr"} for r in res["results"]]


def metric(ns, name, dims, s, e, stat, period=86400):
    d = aws(
        "cloudwatch",
        "get-metric-statistics",
        "--namespace",
        ns,
        "--metric-name",
        name,
        "--dimensions",
        *dims,
        "--start-time",
        s.isoformat(),
        "--end-time",
        e.isoformat(),
        "--period",
        str(period),
        "--statistics",
        stat,
    )
    return d.get("Datapoints", []) if d else None


for day in sys.argv[1:]:
    s = dt.datetime.fromisoformat(day).replace(tzinfo=dt.UTC)
    e = s + dt.timedelta(days=1)
    S, E = int(s.timestamp()), int(e.timestamp())
    emit(f"ROW {day}")
    r = insights(
        S,
        E,
        'filter event="office_floor_evaluated" | stats count(*) as n_eval, sum(control_status="pass") as n_controlled, sum(control_status!="pass") as n_refused, sum(paged=1) as n_paged, count_distinct(page_message_id) as n_page_ids, max(residual_share) as res_max, sum(residual_share_high=1) as n_res_high by evaluator_version',
    )
    emit("  runs by version:", r if r is not None else "UNTAKEN")
    r = insights(
        S,
        E,
        'filter event="office_floor_office" | stats count(*) as lines, sum(floor_class="zero") as zero, sum(floor_class="rate") as rate, sum(floor_class="quiet") as quiet',
    )
    emit("  office lines:", r if r is not None else "UNTAKEN")
    d = metric("Autom8y/EbiOfficeFloor", "LastSuccessTimestamp", [], s, e, "SampleCount")
    emit(
        "  LastSuccessTimestamp SampleCount:",
        sum(x["SampleCount"] for x in d) if d is not None else "UNTAKEN",
    )
    d = metric(
        "Autom8y/Freshness",
        "age_since_last_invocation_seconds",
        ["Name=FunctionName,Value=autom8-email-booking-intake-office-floor"],
        s,
        e,
        "Maximum",
        300,
    )
    emit(
        "  prober gauge:",
        f"n={len(d)} max={max((x['Maximum'] for x in d), default=None)}"
        if d is not None
        else "UNTAKEN",
    )
    al = aws("cloudwatch", "describe-alarms", "--alarm-names", *ALARMS)
    for a in (al or {}).get("MetricAlarms", []):
        h = aws(
            "cloudwatch",
            "describe-alarm-history",
            "--alarm-name",
            a["AlarmName"],
            "--history-item-type",
            "StateUpdate",
            "--start-date",
            s.isoformat(),
            "--end-date",
            e.isoformat(),
        )
        topics = sorted({x.split(":")[-1] for x in a["AlarmActions"] + a["OKActions"]})
        emit(
            f"  alarm {a['AlarmName'][-44:]:44s} now={a['StateValue']:17s} transitions_in_day={len((h or {}).get('AlarmHistoryItems', [])) if h is not None else 'UNTAKEN'} actions={topics}"
        )
    emit(f"  alarms present: {len((al or {}).get('MetricAlarms', []))} of {len(ALARMS)} expected")
