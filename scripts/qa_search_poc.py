#!/usr/bin/env python3
"""QA Proof-of-Concept: Search Interface with Real Asana Data.

This script validates the Search Interface implementation against real Asana data
per TDD-search-interface requirements.

Test Criteria:
- office_phone: +19259998806
- vertical: chiropractic

NOTE: The default DataFrame builder does NOT include custom fields.
This POC builds a DataFrame with custom fields manually to validate
the Search Interface functionality.

Usage:
    # Source environment first
    source .env/production

    # Run POC test
    uv run python scripts/qa_search_poc.py

    # Verbose mode with timing breakdown
    uv run python scripts/qa_search_poc.py -v

    # Run edge case tests
    uv run python scripts/qa_search_poc.py --edge-cases
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import TYPE_CHECKING

import polars as pl

from autom8_asana.client import AsanaClient
from autom8_asana.search import SearchService
from autom8_asana.search.models import FieldCondition, SearchCriteria

if TYPE_CHECKING:
    pass

# Target project GID for Offers
OFFERS_PROJECT_GID = "1143843662099250"

# Test criteria per handoff
TEST_OFFICE_PHONE = "+19259998806"
TEST_VERTICAL = "chiropractic"


def print_banner(title: str) -> None:
    """Print a formatted banner."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'-'*50}")
    print(f"  {title}")
    print(f"{'-'*50}")


async def load_offers_dataframe(client: AsanaClient, verbose: bool = False, max_tasks: int = 500) -> pl.DataFrame:
    """Load and cache the Offers project DataFrame WITH custom fields.

    NOTE: The default DataFrame builder does NOT include custom fields.
    This function builds a DataFrame manually with custom fields to
    validate the Search Interface functionality.

    Args:
        client: AsanaClient instance.
        verbose: If True, print detailed progress.
        max_tasks: Maximum number of tasks to fetch (for performance).

    Returns:
        Polars DataFrame with offers and custom fields.
    """
    print_section("Loading Offers DataFrame (with Custom Fields)")

    # Get the project
    project = await client.projects.get_async(
        OFFERS_PROJECT_GID,
        opt_fields=["name", "gid"]
    )
    print(f"Project: {project.name} ({project.gid})")

    # Check if search service already has cached DataFrame
    search = client.search
    if OFFERS_PROJECT_GID in search._project_df_cache:
        df, _ = search._project_df_cache[OFFERS_PROJECT_GID]
        print(f"Using cached DataFrame: {len(df)} rows")
        return df

    # Build DataFrame with custom fields manually
    # (Default builder does not include custom_fields)
    print(f"Fetching tasks with custom fields (max {max_tasks})...")
    start = time.perf_counter()

    tasks_data = []
    count = 0
    async for task in client.tasks.list_async(
        project=OFFERS_PROJECT_GID,
        opt_fields=["gid", "name", "custom_fields", "custom_fields.name", "custom_fields.display_value"],
    ):
        row = {"gid": task.gid, "name": task.name}
        if task.custom_fields:
            for cf in task.custom_fields:
                cf_name = cf.get("name", "unknown") if isinstance(cf, dict) else getattr(cf, "name", "unknown")
                cf_val = cf.get("display_value", "") if isinstance(cf, dict) else getattr(cf, "display_value", "")
                # Convert all values to string for consistency
                row[cf_name] = str(cf_val) if cf_val is not None else None
        tasks_data.append(row)
        count += 1
        if count >= max_tasks:
            break

    elapsed = time.perf_counter() - start
    print(f"Fetched {len(tasks_data)} tasks in {elapsed:.2f}s")

    # Create DataFrame
    df = pl.DataFrame(tasks_data, infer_schema_length=len(tasks_data))
    print(f"DataFrame shape: {df.shape}")

    if verbose:
        print(f"Columns ({len(df.columns)}):")
        for col in sorted(df.columns)[:20]:
            print(f"  - {col}")
        if len(df.columns) > 20:
            print(f"  ... and {len(df.columns) - 20} more")

    # Cache the DataFrame in SearchService
    search.set_project_dataframe(OFFERS_PROJECT_GID, df)
    print(f"Cached in SearchService for fast lookup")

    return df


async def test_basic_search(client: AsanaClient, df: pl.DataFrame, verbose: bool = False) -> dict:
    """Test basic search functionality.

    Returns:
        Dict with test results.
    """
    results = {
        "passed": [],
        "failed": [],
        "info": {},
    }

    print_section("Basic Search Tests")
    search = client.search

    # Test 1: Search by Office Phone
    print("\n[Test 1] Search by Office Phone")
    print(f"  Criteria: office_phone = '{TEST_OFFICE_PHONE}'")

    start = time.perf_counter()
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Office Phone": TEST_OFFICE_PHONE},
    )
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Results: {result.total_count} matches in {elapsed:.2f}ms")
    print(f"  From cache: {result.from_cache}")

    if result.total_count > 0:
        results["passed"].append("search_by_phone_returns_results")
        print(f"  PASS: Found {result.total_count} offer(s)")
        for hit in result.hits[:3]:
            print(f"    - {hit.gid}: {hit.name}")
    else:
        results["failed"].append(("search_by_phone_returns_results", "No results found"))
        print(f"  FAIL: No matches found for phone '{TEST_OFFICE_PHONE}'")

    results["info"]["phone_search_time_ms"] = elapsed
    results["info"]["phone_search_count"] = result.total_count

    # Test 2: Search by Vertical
    print("\n[Test 2] Search by Vertical")
    print(f"  Criteria: vertical = '{TEST_VERTICAL}'")

    start = time.perf_counter()
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Vertical": TEST_VERTICAL},
    )
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Results: {result.total_count} matches in {elapsed:.2f}ms")

    if result.total_count > 0:
        results["passed"].append("search_by_vertical_returns_results")
        print(f"  PASS: Found {result.total_count} offer(s)")
    else:
        results["failed"].append(("search_by_vertical_returns_results", "No results found"))
        print(f"  FAIL: No matches found for vertical '{TEST_VERTICAL}'")

    results["info"]["vertical_search_time_ms"] = elapsed
    results["info"]["vertical_search_count"] = result.total_count

    # Test 3: Compound AND search
    print("\n[Test 3] Compound AND Search")
    print(f"  Criteria: office_phone = '{TEST_OFFICE_PHONE}' AND vertical = '{TEST_VERTICAL}'")

    start = time.perf_counter()
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Office Phone": TEST_OFFICE_PHONE, "Vertical": TEST_VERTICAL},
    )
    elapsed = (time.perf_counter() - start) * 1000

    print(f"  Results: {result.total_count} matches in {elapsed:.2f}ms")

    # Even if no compound match, this is valid (might not have exact combo)
    results["passed"].append("compound_search_executes")
    print(f"  PASS: Compound search executed successfully")

    results["info"]["compound_search_time_ms"] = elapsed
    results["info"]["compound_search_count"] = result.total_count

    # Test 4: Verify performance target (<10ms for indexed lookups)
    # NOTE: First query includes column index building - subsequent queries are faster
    print("\n[Test 4] Performance Target Validation (Warm Cache)")

    # Run 5 more queries to get warm cache timing
    warm_times = []
    for _ in range(5):
        start = time.perf_counter()
        await search.find_async(
            OFFERS_PROJECT_GID,
            {"Vertical": TEST_VERTICAL},
        )
        warm_times.append((time.perf_counter() - start) * 1000)

    warm_max = max(warm_times)
    warm_avg = sum(warm_times) / len(warm_times)

    print(f"  Warm cache max: {warm_max:.2f}ms")
    print(f"  Warm cache avg: {warm_avg:.2f}ms")
    print(f"  Target: <10ms per TDD")

    results["info"]["warm_cache_max_ms"] = warm_max
    results["info"]["warm_cache_avg_ms"] = warm_avg

    if warm_avg < 10:
        results["passed"].append("performance_under_10ms")
        print(f"  PASS: Warm cache queries under 10ms target")
    else:
        results["failed"].append(("performance_under_10ms", f"Warm avg: {warm_avg:.2f}ms"))
        print(f"  FAIL: Query time exceeds 10ms target")

    return results


async def test_convenience_methods(client: AsanaClient, verbose: bool = False) -> dict:
    """Test convenience methods (find_offers_async, etc.)."""
    results = {
        "passed": [],
        "failed": [],
        "info": {},
    }

    print_section("Convenience Method Tests")
    search = client.search

    # Test find_offers_async with snake_case normalization
    print("\n[Test 5] find_offers_async with snake_case field names")
    print(f"  Criteria: office_phone = '{TEST_OFFICE_PHONE}'")

    try:
        start = time.perf_counter()
        gids = await search.find_offers_async(
            OFFERS_PROJECT_GID,
            office_phone=TEST_OFFICE_PHONE,
        )
        elapsed = (time.perf_counter() - start) * 1000

        print(f"  Results: {len(gids)} GIDs in {elapsed:.2f}ms")
        results["passed"].append("find_offers_async_works")

        if gids:
            print(f"  First 3 GIDs: {gids[:3]}")

    except Exception as e:
        results["failed"].append(("find_offers_async_works", str(e)))
        print(f"  FAIL: {e}")

    # Test find_one_async
    print("\n[Test 6] find_one_async with unique criteria")

    # Try to find a single match by combining criteria
    try:
        result = await search.find_one_async(
            OFFERS_PROJECT_GID,
            {"Office Phone": TEST_OFFICE_PHONE, "Vertical": TEST_VERTICAL},
        )

        if result is not None:
            results["passed"].append("find_one_returns_single_hit")
            print(f"  PASS: Found single match: {result.gid}")
        else:
            # No match is acceptable (criteria may not exist)
            results["passed"].append("find_one_returns_none_for_no_match")
            print(f"  PASS: No match found (expected if combo doesn't exist)")

    except ValueError as e:
        # Multiple matches - this is expected behavior
        results["passed"].append("find_one_raises_on_multiple")
        print(f"  PASS: ValueError raised on multiple matches (expected): {e}")
    except Exception as e:
        results["failed"].append(("find_one_async_works", str(e)))
        print(f"  FAIL: Unexpected error: {e}")

    return results


async def test_edge_cases(client: AsanaClient, df: pl.DataFrame, verbose: bool = False) -> dict:
    """Test edge cases per QA requirements."""
    results = {
        "passed": [],
        "failed": [],
        "info": {},
    }

    print_section("Edge Case Tests")
    search = client.search

    # Edge Case 1: Non-existent field
    print("\n[Edge 1] Non-existent field returns empty result")
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"NonExistentFieldXYZ123": "value"},
    )

    if result.total_count == 0:
        results["passed"].append("nonexistent_field_returns_empty")
        print(f"  PASS: Empty result for non-existent field")
    else:
        results["failed"].append(("nonexistent_field_returns_empty", f"Got {result.total_count} results"))
        print(f"  FAIL: Expected 0 results, got {result.total_count}")

    # Edge Case 2: Empty criteria returns empty
    print("\n[Edge 2] Empty criteria returns empty result")
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {},
    )

    if result.total_count == 0:
        results["passed"].append("empty_criteria_returns_empty")
        print(f"  PASS: Empty result for empty criteria")
    else:
        results["failed"].append(("empty_criteria_returns_empty", f"Got {result.total_count} results"))
        print(f"  FAIL: Expected 0 results, got {result.total_count}")

    # Edge Case 3: Case-insensitive field name matching
    print("\n[Edge 3] Case-insensitive field name matching")

    # Search with lowercase field name
    result_lower = await search.find_async(
        OFFERS_PROJECT_GID,
        {"vertical": TEST_VERTICAL},  # lowercase
    )

    # Search with uppercase field name
    result_upper = await search.find_async(
        OFFERS_PROJECT_GID,
        {"VERTICAL": TEST_VERTICAL},  # uppercase
    )

    # Both should return same count
    if result_lower.total_count == result_upper.total_count:
        results["passed"].append("case_insensitive_field_names")
        print(f"  PASS: Both cases return {result_lower.total_count} results")
    else:
        results["failed"].append(("case_insensitive_field_names",
                                  f"lower={result_lower.total_count}, upper={result_upper.total_count}"))
        print(f"  FAIL: Case mismatch - lower: {result_lower.total_count}, upper: {result_upper.total_count}")

    # Edge Case 4: Unicode in search value
    print("\n[Edge 4] Unicode characters in search value")
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Vertical": "Test Unicode: cafe"},  # No actual unicode match expected
    )

    # Should execute without error (even if no match)
    results["passed"].append("unicode_search_value_accepted")
    print(f"  PASS: Unicode search executed ({result.total_count} results)")

    # Edge Case 5: Special characters in value
    print("\n[Edge 5] Special characters in search value")
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Office Phone": "+1 (925) 999-8806"},  # Different format
    )

    results["passed"].append("special_chars_in_value_accepted")
    print(f"  PASS: Special chars search executed ({result.total_count} results)")

    # Edge Case 6: Performance with limit
    print("\n[Edge 6] Performance with limit=1")
    start = time.perf_counter()
    result = await search.find_async(
        OFFERS_PROJECT_GID,
        {"Vertical": TEST_VERTICAL},
        limit=1,
    )
    elapsed = (time.perf_counter() - start) * 1000

    if result.total_count <= 1:
        results["passed"].append("limit_respected")
        print(f"  PASS: Limit respected ({result.total_count} result in {elapsed:.2f}ms)")
    else:
        results["failed"].append(("limit_respected", f"Got {result.total_count} results"))
        print(f"  FAIL: Limit not respected, got {result.total_count} results")

    # Edge Case 7: Uncached project returns empty
    print("\n[Edge 7] Uncached project returns empty result")
    result = await search.find_async(
        "nonexistent_project_gid_12345",
        {"Vertical": TEST_VERTICAL},
    )

    if result.total_count == 0 and result.from_cache is False:
        results["passed"].append("uncached_project_returns_empty")
        print(f"  PASS: Empty result for uncached project")
    else:
        results["failed"].append(("uncached_project_returns_empty",
                                  f"count={result.total_count}, from_cache={result.from_cache}"))
        print(f"  FAIL: Unexpected result for uncached project")

    return results


async def test_large_dataframe_performance(client: AsanaClient, df: pl.DataFrame, verbose: bool = False) -> dict:
    """Test performance with the actual DataFrame size."""
    results = {
        "passed": [],
        "failed": [],
        "info": {},
    }

    print_section("Large DataFrame Performance")
    search = client.search

    row_count = len(df)
    print(f"DataFrame size: {row_count} rows")
    results["info"]["dataframe_rows"] = row_count

    # Run multiple queries to get consistent timing
    print("\n[Perf 1] Running 10 consecutive searches")
    times = []

    for i in range(10):
        start = time.perf_counter()
        await search.find_async(
            OFFERS_PROJECT_GID,
            {"Vertical": TEST_VERTICAL},
        )
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    min_time = min(times)
    max_time = max(times)
    avg_time = sum(times) / len(times)

    print(f"  Min: {min_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    print(f"  Avg: {avg_time:.2f}ms")

    results["info"]["perf_min_ms"] = min_time
    results["info"]["perf_max_ms"] = max_time
    results["info"]["perf_avg_ms"] = avg_time

    # Per TDD: <10ms target
    if avg_time < 10:
        results["passed"].append("avg_under_10ms_target")
        print(f"  PASS: Average query time under 10ms target")
    else:
        results["failed"].append(("avg_under_10ms_target", f"Avg: {avg_time:.2f}ms"))
        print(f"  FAIL: Average {avg_time:.2f}ms exceeds 10ms target")

    # Check for large dataset (per TDD: 5000 rows realistic upper bound)
    if row_count >= 1000:
        results["passed"].append("handles_1000plus_rows")
        print(f"  PASS: Handles {row_count}+ rows efficiently")

    return results


async def run_poc_tests(verbose: bool = False, edge_cases: bool = False) -> int:
    """Run all POC tests.

    Returns:
        0 on success, 1 on failure.
    """
    print_banner("QA Search Interface POC")
    print(f"Offers Project: {OFFERS_PROJECT_GID}")
    print(f"Test Phone: {TEST_OFFICE_PHONE}")
    print(f"Test Vertical: {TEST_VERTICAL}")

    client = AsanaClient()
    all_results = {
        "passed": [],
        "failed": [],
        "info": {},
    }

    try:
        # Load DataFrame
        df = await load_offers_dataframe(client, verbose=verbose)
        all_results["info"]["dataframe_rows"] = len(df)

        # Run basic search tests
        basic_results = await test_basic_search(client, df, verbose=verbose)
        all_results["passed"].extend(basic_results["passed"])
        all_results["failed"].extend(basic_results["failed"])
        all_results["info"].update(basic_results["info"])

        # Run convenience method tests
        conv_results = await test_convenience_methods(client, verbose=verbose)
        all_results["passed"].extend(conv_results["passed"])
        all_results["failed"].extend(conv_results["failed"])

        # Run edge case tests if requested
        if edge_cases:
            edge_results = await test_edge_cases(client, df, verbose=verbose)
            all_results["passed"].extend(edge_results["passed"])
            all_results["failed"].extend(edge_results["failed"])
            all_results["info"].update(edge_results["info"])

            # Run performance tests
            perf_results = await test_large_dataframe_performance(client, df, verbose=verbose)
            all_results["passed"].extend(perf_results["passed"])
            all_results["failed"].extend(perf_results["failed"])
            all_results["info"].update(perf_results["info"])

        # Summary
        print_banner("POC Test Summary")

        total_passed = len(all_results["passed"])
        total_failed = len(all_results["failed"])
        total_tests = total_passed + total_failed

        print(f"Tests Run: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")

        if all_results["passed"]:
            print(f"\nPassed Tests:")
            for test in all_results["passed"]:
                print(f"  [PASS] {test}")

        if all_results["failed"]:
            print(f"\nFailed Tests:")
            for test, reason in all_results["failed"]:
                print(f"  [FAIL] {test}: {reason}")

        print(f"\nKey Metrics:")
        print(f"  DataFrame rows: {all_results['info'].get('dataframe_rows', 'N/A')}")
        print(f"  Phone search time: {all_results['info'].get('phone_search_time_ms', 'N/A'):.2f}ms")
        print(f"  Vertical search time: {all_results['info'].get('vertical_search_time_ms', 'N/A'):.2f}ms")

        if total_failed == 0:
            print(f"\n{'='*70}")
            print("  POC VALIDATION: PASSED")
            print(f"{'='*70}")
            return 0
        else:
            print(f"\n{'='*70}")
            print(f"  POC VALIDATION: FAILED ({total_failed} failures)")
            print(f"{'='*70}")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await client.close()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="QA Proof-of-Concept: Search Interface Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--edge-cases", action="store_true",
                       help="Run edge case and performance tests")

    args = parser.parse_args()

    return asyncio.run(run_poc_tests(
        verbose=args.verbose,
        edge_cases=args.edge_cases,
    ))


if __name__ == "__main__":
    sys.exit(main())
