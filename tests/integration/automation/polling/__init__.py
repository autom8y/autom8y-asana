"""Integration tests for polling-based automation.

These tests require a real Asana API token and test project/tag/section GIDs.
Set the following environment variables:
  - ASANA_ACCESS_TOKEN or ASANA_PAT: Asana API token
  - ASANA_TEST_PROJECT_GID: GID of a test project
  - ASANA_TEST_TAG_GID: GID of a test tag
  - ASANA_TEST_SECTION_GID: GID of a test section

Tests are marked with @pytest.mark.integration and are skipped if credentials
are not available.

Run integration tests only:
    pytest -m integration tests/integration/automation/polling/

Skip integration tests:
    pytest -m "not integration"
"""
