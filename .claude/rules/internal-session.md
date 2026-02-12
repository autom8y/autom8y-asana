---
paths:
  - "internal/session/**"
---

When modifying files in internal/session/:
- FSM: 4 states (NONE, ACTIVE, PARKED, ARCHIVED), 5 transitions
- Lock protocol: JSON LockMetadata v2, 5-minute stale threshold
- Scan-based discovery eliminates TOCTOU races — no in-memory session cache
- SESSION_CONTEXT.md mutations only via Moirai agent or ari CLI commands
- PreToolUse hook (writeguard) blocks direct writes to *_CONTEXT.md files
- Session IDs are timestamp-based with random suffix for uniqueness
