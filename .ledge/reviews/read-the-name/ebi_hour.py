"""First-hour EBI intake read after a peer deploy (041-style signals). Read-only.

usage: python3 ebi_hour.py 2026-09-30T13:09:37Z [minutes=60]
"""

import datetime as dt
import json
import re
import subprocess
import sys
import time

sys.path.insert(0, sys.path[0])
from s1lib import emit, insights  # noqa: E402

t0 = dt.datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.UTC)
mins = int(sys.argv[2]) if len(sys.argv) > 2 else 60
T = int(t0.timestamp())
E = T + mins * 60
G = re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27,}")

emit("read", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), f"window {sys.argv[1]} +{mins}m")
r, s = insights(
    T,
    E,
    'filter event in ["handler_invoked","pipeline_completed","terminal_decline","terminal_decline_parked",'
    '"stage_exception","booking_intake_fault","match_call_rejected","match_contract_error",'
    '"lead_lookup_failed_retry","lead_matched_no_mint","guid_resolved_via_data_service"] '
    "| stats count(*) as n by event, decline_class, error_type, status_code",
)
emit(f"scanned {s}")
for x in r:
    emit(
        " ",
        x.get("event"),
        x.get("decline_class") or "",
        x.get("error_type") or "",
        x.get("status_code") or "",
        x["n"],
    )
r, _ = insights(T, E, 'filter event="stage_exception" | stats count(*) as n by stage, error')
for x in r:
    emit("  exc", x.get("stage"), G.sub("<guid>", (x.get("error") or "")[:100]), x["n"])
r, _ = insights(T, E, "filter ispresent(status_code) | stats count(*) as n by event, status_code")
emit("status_code lines:", [(x.get("event"), x.get("status_code"), x["n"]) for x in r] or "none")
r, _ = insights(
    T,
    E,
    "filter @message like /Traceback|Task timed out|Runtime\\.|RuntimeError/ "
    "| stats sum(@message like /Event loop is closed/) as loop_closed, "
    "sum(@message like /^Traceback \\(most recent call last\\):\\s*$/) as tb_headers, count(*) as n",
)
if r:
    x = r[0]
    other = int(x["n"]) - int(x["loop_closed"]) - int(x["tb_headers"])
    emit("runtime-pattern lines:", x, "OTHER (not the known httpx loop-closed wart):", other)
    if other:
        r2, _ = insights(
            T,
            E,
            "filter @message like /Task timed out|Runtime\\.|RuntimeError/ and @message not like /Event loop is closed/ "
            "| fields @timestamp, event, error_type",
        )
        for y in r2[:10]:
            emit("   other:", y.get("@timestamp"), y.get("event"), y.get("error_type"))
else:
    emit("runtime-pattern lines: none")
a = json.loads(
    subprocess.run(
        [
            "aws",
            "cloudwatch",
            "describe-alarms",
            "--region",
            "us-east-1",
            "--alarm-names",
            "ebi-no-lead-stop-match-auth-retry",
            "ebi-no-lead-stop-match-call-rejected-sustained",
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    ).stdout
)
for al in a["MetricAlarms"]:
    emit("alarm", al["AlarmName"], al["StateValue"], al["StateUpdatedTimestamp"][:19])
