# mcp-island CI canary (discriminating fixture)

This directory holds the **deliberately-broken fixture** that proves the
`mcp-island` CI gate (`.github/workflows/test.yml`) has TEETH — that a
defective `mcp/` state actually turns the gate RED, and that the gate is not
an always-green liveness check.

## Polarity (FORK-F discipline — read before citing exit codes)

| Invocation | Exit code | Meaning |
|---|---|---|
| `cd mcp && python -m pytest tests -q` | `0` | GREEN leg: real 24-file suite passes |
| `cd mcp && python -m pytest canary -q` | `1` | **GREEN receipt**: broken input CORRECTLY REJECTED (1 failed = teeth) |
| `cd mcp && python -m pytest canary -q` | `0` | **ALARM**: no teeth — battery accepted a defective envelope |
| `cd mcp && python -m pytest canary -q` | `5` | **ALARM**: vacuous collection — canary itself broken |

The CI canary step enforces `rc == 1` **exactly** (not merely non-zero): exit
5 (nothing collected) and exit 2/3/4 (harness defect) are treated as gate
failures, not as teeth.

## Doctrine

Per `discriminating-canary-doctrine` (Mode 1 — test-only canary on a working
surface): the RED comes from breaking the **INPUT** the surface judges (a
rows envelope with the SVR-5 honesty attestations stripped), NEVER from
injecting a defect into working production code (G-THEATER, forbidden).
Two-sided: the SAME battery passes the clean envelope (positive control,
lives in this module AND as the original in `tests/test_query_tools.py`) and
rejects the broken one (negative control, fails by design).

This directory sits OUTSIDE `testpaths = ["tests"]` (`mcp/pyproject.toml`),
so normal suite runs never collect it.
