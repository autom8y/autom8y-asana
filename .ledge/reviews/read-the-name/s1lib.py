"""Read-only helpers for the S-1 seat (rebuilt 2026-10-04 after a scratchpad wipe).

aws(*args) -> parsed JSON or None; insights(start, end, query, lg=LG) -> (rows, recordsScanned);
emit(*parts) prints with the account id redacted (hex-safe: digests and sha prefixes survive).
"""

import json
import re
import subprocess
import sys
import time

REGION = "us-east-1"
LG = "/aws/lambda/autom8-email-booking-intake"
_ACCT = re.compile(r"(?<![0-9a-fA-F])\d{12}(?![0-9a-fA-F])")


def aws(*args):
    p = subprocess.run(
        ["aws", *args, "--region", REGION, "--output", "json"], capture_output=True, text=True
    )
    if p.returncode != 0:
        sys.stderr.write("AWS ERROR: " + _ACCT.sub("<ACCOUNT>", p.stderr.strip())[:300] + "\n")
        return None
    try:
        return json.loads(p.stdout) if p.stdout.strip() else {}
    except json.JSONDecodeError:
        return None


def insights(s, e, qs, lg=LG):
    st = aws(
        "logs",
        "start-query",
        "--log-group-name",
        lg,
        "--start-time",
        str(s),
        "--end-time",
        str(e),
        "--query-string",
        qs,
        "--limit",
        "10000",
    )
    if not st:
        sys.exit("START_FAILED")
    res = None
    for _ in range(300):
        res = aws("logs", "get-query-results", "--query-id", st["queryId"])
        if res and res.get("status") in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(2)
    if not res or res.get("status") != "Complete":
        sys.exit("QUERY_NOT_COMPLETE: " + str((res or {}).get("status")))
    rows = [{f["field"]: f.get("value") for f in r} for r in res.get("results", [])]
    return rows, res.get("statistics", {}).get("recordsScanned")


def emit(*parts):
    sys.stdout.write(_ACCT.sub("<ACCOUNT>", " ".join(str(x) for x in parts)) + "\n")
    sys.stdout.flush()
