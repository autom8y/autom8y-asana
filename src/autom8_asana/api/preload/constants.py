"""Preload subsystem constants.

Extracted from api/main.py per TDD-I5 (API Main Decomposition).
"""

# Concurrency limit for parallel project processing
# Per progressive cache warming architecture: 3 concurrent projects
PROJECT_CONCURRENCY = 3

# Heartbeat interval for preload monitoring
HEARTBEAT_INTERVAL_SECONDS = 30

# Projects to EXCLUDE from preload (exclude-list pattern for DX)
# All registered entity projects are preloaded by default.
# Use this for projects that don't need DataFrame caching.
PRELOAD_EXCLUDE_PROJECT_GIDS: set[str] = set()
