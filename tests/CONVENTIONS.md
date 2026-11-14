# Test conventions for the autom8y satellites

Applies to new and changed test files. Untouched files are left alone until a change reaches them.

1. **A test never waits on something it does not assert on.** No real network, cloud, event bus or sleep in a unit test. A seam that reaches outside the process (an event publisher, an HTTP client, a cloud SDK) is patched once, in a module-level or conftest fixture, and one test asserts that the seam is called when it should be and not when it should not.
2. **Fakes match the real interface.** Build mocks with `spec_set` or `autospec` against the real class, never against a local stub. A hand-written fake raises on a method the real class lacks and counts every method that writes. One fake per real class, kept in the suite's shared home (`conftest.py` or `tests/_shared/`).
3. **Names say the behavior.** `tests/` mirrors `src/<pkg>/`; a test is named for what it checks and under what condition. No ticket, sprint, wave, seat or agent codes in file, class or test names; that history goes in the commit message.
4. **Cost is marked.** A test that takes more than a second, starts a subprocess or needs a service carries a registered marker (`slow`, `subprocess`, `integration`). A static guard that can fail in seconds is marked so it runs first.
5. **Every change to a test proves it still bites.** A speed-up, refactor or removal ships with a run that plants the defect the test exists to catch and shows it go red. A removal names the test that survives it.
