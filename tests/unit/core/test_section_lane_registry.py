"""Tests for section-lane key enumeration (ADR §B).

Mirrors TestBulkPrematerializationKeys and TestFastLanePrematerializationKeys
but for the section-arm-only lane.  Every assertion has a direct structural
parallel to its bulk/fast counterpart so the suite is easy to extend.
"""

from __future__ import annotations

# =============================================================================
# Section-Only Key Enumeration
# =============================================================================


class TestSectionOnlyPrematerializationKeys:
    """ADR §B: section_only_prematerialization_keys() yields 34 section keys."""

    def test_enumerates_34_section_keys(self) -> None:
        """34 GIDs x 1 arm = 34 keys -- the section lane's own coverage denominator."""
        from autom8_asana.core.project_registry import (
            consumer_warm_set_gids,
            section_only_prematerialization_keys,
        )

        keys = section_only_prematerialization_keys()
        assert len(keys) == len(consumer_warm_set_gids())
        assert len(keys) == 34

    def test_every_key_is_section_arm(self) -> None:
        """Every (gid, entity_type) pair has entity_type == 'section'."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        keys = section_only_prematerialization_keys()
        assert all(et == "section" for _gid, et in keys)

    def test_every_warm_set_gid_present_in_order(self) -> None:
        """Each of the 34 consumer warm-set GIDs appears exactly once, in order."""
        from autom8_asana.core.project_registry import (
            consumer_warm_set_gids,
            section_only_prematerialization_keys,
        )

        keys = section_only_prematerialization_keys()
        key_gids = [gid for gid, _et in keys]
        warm_gids = list(consumer_warm_set_gids())
        assert key_gids == warm_gids

    def test_exact_section_key_set_membership(self) -> None:
        """Set of keys == {(gid, 'section') for gid in consumer_warm_set_gids()}."""
        from autom8_asana.core.project_registry import (
            consumer_warm_set_gids,
            section_only_prematerialization_keys,
        )

        expected = {(gid, "section") for gid in consumer_warm_set_gids()}
        actual = set(section_only_prematerialization_keys())
        assert actual == expected

    def test_heaviest_first_ordering(self) -> None:
        """CF-2: DNA holder (heaviest GID) leads, matching the bulk-sweep contract."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        keys = section_only_prematerialization_keys()
        # BackendClientSuccessDna ~30k rows -- the OOM driver, must lead.
        assert keys[0] == ("1167650840134033", "section")

    def test_deterministic_order(self) -> None:
        """Enumeration order is stable across calls (checkpoint resume needs it)."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        assert section_only_prematerialization_keys() == section_only_prematerialization_keys()

    def test_no_duplicate_keys(self) -> None:
        """Each (gid, 'section') pair appears exactly once -- no dupes."""
        from autom8_asana.core.project_registry import section_only_prematerialization_keys

        keys = section_only_prematerialization_keys()
        assert len(keys) == len(set(keys))

    def test_section_lane_is_strict_subset_of_bulk_section_arm(self) -> None:
        """Backstop invariant: every section-lane key is in the bulk sweep's section arm.

        This is the runtime mirror of the module-load backstop assertion in
        project_registry.py: the 30-min bulk sweep is the backstop for every
        section-lane GID, so the section key set must be a strict subset of
        the bulk sweep's section arm.
        """
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            section_only_prematerialization_keys,
        )

        section = set(section_only_prematerialization_keys())
        bulk_section = set(bulk_prematerialization_keys(arms=("section",)))
        assert section <= bulk_section
        assert section  # non-empty

    def test_section_lane_is_disjoint_from_bulk_project_arm(self) -> None:
        """Section lane produces ONLY 'section' keys -- no 'project' arm leaks."""
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            section_only_prematerialization_keys,
        )

        section = set(section_only_prematerialization_keys())
        bulk_project = set(bulk_prematerialization_keys(arms=("project",)))
        assert section.isdisjoint(bulk_project)

    def test_section_lane_key_count_is_half_of_bulk(self) -> None:
        """Section lane (34 keys) is exactly half the bulk sweep (68 keys)."""
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            section_only_prematerialization_keys,
        )

        section_count = len(section_only_prematerialization_keys())
        bulk_count = len(bulk_prematerialization_keys())
        assert bulk_count == section_count * 2
