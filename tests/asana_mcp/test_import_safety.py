"""Contract §4.2 import-safety — two-sided; checklist item 3.

A subprocess installs a sys audit hook, imports asana_mcp.observability AND
asana_mcp.timeouts under audit, and asserts: (1) zero network/subprocess at import;
(2) no settings instance built at import (settings-load-at-call-time); (3) the audit
canary HAS TEETH (catches a real socket op); (4) a deliberately-broken fixture module
that builds Settings at import IS CAUGHT by the same has-instance detector. Child env
strips ASANA_MCP_* to prove import needs no such env (guards INCIDENT 2026-04-28).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parents[2] / "src")

_SCRIPT = r"""
import sys, json, socket, tempfile, os
net = []
_WATCH = ("socket.connect", "socket.getaddrinfo", "subprocess.Popen",
          "os.system", "urllib.Request")
def _hook(event, args):
    if event in _WATCH:
        net.append(event)
sys.addaudithook(_hook)

# --- import BOTH modules under audit ---
import asana_mcp.observability as o
import asana_mcp.timeouts as t
import_net = list(net)

# structural: no module-level settings instance in the real modules
real_has_instance = any(
    isinstance(getattr(o, n, None), o.ObservabilitySettings) for n in dir(o)
)

# teeth 1: the audit hook catches a real network op
try:
    socket.getaddrinfo("nonexistent.invalid.example", 80)
except Exception:
    pass
net_teeth = len(net) > len(import_net)

# teeth 2: a broken fixture that builds Settings at IMPORT is caught by the detector
d = tempfile.mkdtemp()
with open(os.path.join(d, "_broken_import.py"), "w") as f:
    f.write(
        "from asana_mcp.observability import ObservabilitySettings\n"
        "SETTINGS = ObservabilitySettings.from_env()\n"
    )
sys.path.insert(0, d)
import _broken_import as b
broken_has_instance = any(
    isinstance(getattr(b, n, None), o.ObservabilitySettings) for n in dir(b)
)

print(json.dumps({
    "import_net": import_net,
    "real_has_instance": real_has_instance,
    "net_teeth": net_teeth,
    "broken_has_instance": broken_has_instance,
}))
"""


def test_import_safety_and_teeth() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ASANA_MCP_")}
    env["PYTHONPATH"] = _SRC + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"
    data = json.loads(result.stdout.strip().splitlines()[-1])
    assert data["import_net"] == []  # ZERO network at import (C9a)
    assert data["real_has_instance"] is False  # settings-load-at-call-time
    assert data["net_teeth"] is True  # the network canary is non-vacuous
    assert data["broken_has_instance"] is True  # the detector catches import-time Settings()
