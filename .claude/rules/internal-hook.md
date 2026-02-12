---
paths:
  - "internal/hook/**"
---

When modifying files in internal/hook/:
- Two output formats: legacy Result (decision field) and CC-native PreToolUseOutput (hookSpecificOutput envelope)
- CC reads permissionDecision from hookSpecificOutput, NOT from top-level decision field
- Decision maps: allow->allow, block->deny, modify->allow (CC does not support modify)
- Env vars prefixed CLAUDE_; ParseEnv() reads all hook context from environment
- Errors default to allow (graceful degradation) -- never block on hook failure
- clewcontract/: append-only JSONL with 16 event types; thread-safe via mutex
- BufferedEventWriter: 5s flush interval, re-queues on failure, bounded loss window
