"""
DataGuard test suite.

Tests verify DataGuard's detection behaviour — not the analytics code itself.

TestBuggyPipelineDetection:
    Asserts that DataGuard correctly identifies each of the four check
    failures produced by the buggy (duplicate-row join) pipeline.
    All assertions are positive claims: "DataGuard detects this regression."

TestFixedPipelineDetection:
    Asserts that DataGuard correctly clears all four checks once the
    pipeline is fixed.

TestSummary:
    Verifies the summarize() helper returns accurate counts for both cases.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find(results: list, name: str) -> dict:
    """Return the check result dict with the given name."""
    for r in results:
        if r["name"] == name:
            return r
    raise KeyError(f"Check '{name}' not found in results")


# ---------------------------------------------------------------------------
# Buggy pipeline — DataGuard must detect all four failures
# ---------------------------------------------------------------------------

class TestBuggyPipelineDetection:
    """DataGuard correctly identifies the duplicate-row join regression."""

    def test_revenue_accuracy_fails(self, buggy_results):
        r = _find(buggy_results, "revenue_accuracy")
        assert r["status"] == "FAIL", (
            f"Expected DataGuard to FAIL revenue_accuracy on the buggy pipeline, "
            f"but got PASS. actual={r['actual']}, expected={r['expected']}"
        )

    def test_duplicate_order_rows_fails(self, buggy_results):
        r = _find(buggy_results, "duplicate_order_rows")
        assert r["status"] == "FAIL", (
            f"Expected DataGuard to FAIL duplicate_order_rows on the buggy pipeline, "
            f"but got PASS. actual={r['actual']}, expected={r['expected']}"
        )

    def test_revenue_deviation_pct_fails(self, buggy_results):
        r = _find(buggy_results, "revenue_deviation_pct")
        assert r["status"] == "FAIL", (
            f"Expected DataGuard to FAIL revenue_deviation_pct on the buggy pipeline, "
            f"but got PASS. actual={r['actual']}, expected={r['expected']}"
        )

    def test_order_count_match_fails(self, buggy_results):
        r = _find(buggy_results, "order_count_match")
        assert r["status"] == "FAIL", (
            f"Expected DataGuard to FAIL order_count_match on the buggy pipeline, "
            f"but got PASS. actual={r['actual']}, expected={r['expected']}"
        )

    def test_buggy_revenue_is_double(self, buggy_results):
        """Verify the bug produces ~2× revenue — confirms the duplicate-row mechanism."""
        from checks.guards import EXPECTED_REVENUE
        r = _find(buggy_results, "revenue_accuracy")
        ratio = r["actual"] / EXPECTED_REVENUE
        assert 1.99 < ratio < 2.01, (
            f"Expected buggy revenue to be ~2× expected, but ratio={ratio:.4f}"
        )


# ---------------------------------------------------------------------------
# Fixed pipeline — DataGuard must clear all four checks
# ---------------------------------------------------------------------------

class TestFixedPipelineDetection:
    """DataGuard correctly clears all checks once the pipeline is fixed."""

    def test_revenue_accuracy_passes(self, fixed_results):
        r = _find(fixed_results, "revenue_accuracy")
        assert r["status"] == "PASS", (
            f"Expected DataGuard to PASS revenue_accuracy on the fixed pipeline, "
            f"but got FAIL. actual={r['actual']}, expected={r['expected']}"
        )

    def test_duplicate_order_rows_passes(self, fixed_results):
        r = _find(fixed_results, "duplicate_order_rows")
        assert r["status"] == "PASS", (
            f"Expected DataGuard to PASS duplicate_order_rows on the fixed pipeline, "
            f"but got FAIL. actual={r['actual']}, expected={r['expected']}"
        )

    def test_revenue_deviation_pct_passes(self, fixed_results):
        r = _find(fixed_results, "revenue_deviation_pct")
        assert r["status"] == "PASS", (
            f"Expected DataGuard to PASS revenue_deviation_pct on the fixed pipeline, "
            f"but got FAIL. actual={r['actual']}, expected={r['expected']}"
        )

    def test_order_count_match_passes(self, fixed_results):
        r = _find(fixed_results, "order_count_match")
        assert r["status"] == "PASS", (
            f"Expected DataGuard to PASS order_count_match on the fixed pipeline, "
            f"but got FAIL. actual={r['actual']}, expected={r['expected']}"
        )


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------

class TestSummary:

    def test_summary_buggy(self, buggy_summary):
        assert buggy_summary == {"total": 4, "passed": 0, "failed": 4}, (
            f"Unexpected buggy summary: {buggy_summary}"
        )

    def test_summary_fixed(self, fixed_summary):
        assert fixed_summary == {"total": 4, "passed": 4, "failed": 0}, (
            f"Unexpected fixed summary: {fixed_summary}"
        )
