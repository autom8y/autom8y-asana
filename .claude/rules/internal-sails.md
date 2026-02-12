---
paths:
  - "internal/sails/**"
---

When modifying files in internal/sails/:
- Exactly 3 colors: WHITE (ship), GRAY (needs QA), BLACK (do not ship) -- no other states
- Color algorithm: blockers->BLACK, proof failures->BLACK, open questions->GRAY, spike/hotfix->GRAY, all proofs pass->WHITE
- Modifiers are downgrade-only: DOWNGRADE_TO_GRAY, DOWNGRADE_TO_BLACK, HUMAN_OVERRIDE_GRAY
- QA upgrade path: GRAY->WHITE requires constraint_resolution_log + adversarial_tests_added
- Required proofs scale with complexity: PATCH-MODULE need tests/build/lint; INITIATIVE+ add adversarial/integration
- Gate pass criteria: WHITE only (GRAY and BLACK fail the gate)
- Clew contract violations from events.jsonl degrade WHITE to GRAY minimum
- ProofStatus has 4 values: PASS, FAIL, SKIP, UNKNOWN; PASS and SKIP are passing
