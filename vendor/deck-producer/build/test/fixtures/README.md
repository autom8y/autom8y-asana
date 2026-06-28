# Acceptance fixtures (PKG-004 / AC-G9)

The deliberately-broken fixture for **AC-G9** is generated **dynamically** by
`build/test/acceptance.mjs` (`checkBrokenFixtureRed`) against the **REAL**
inliner — never a mock re-implementation (a mock that "passes" is theater;
PKG-004 / telos-integrity Gate teeth).

The harness:

1. Copies the real `templates/ghl-calendar-setup` deck into a throwaway
   `templates/_broken-fixture/`.
2. **Mutates the `@ds-bundle` namespace** in the deck source
   (`ContenteDesignSystem_9ed584` → `ContenteDesignSystem_DEADBEEF`) so
   `resolveDeck` fires `NS-DRIFT-CONSUMER`.
3. **Removes a referenced screenshot** so the image map fires `MISSING-ASSET`.
4. Runs the REAL `build/inline.mjs` at the broken fixture and asserts it
   **EXITs non-zero with a named error and writes NO output file**.
5. Tears the fixture down (no residue lands in the committed tree).

Because the fixture is built + destroyed per run, this directory is otherwise
empty — the README is the committed artifact that documents the contract.
