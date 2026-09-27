"""
DataGuard check functions.

All checks are pure functions — no file I/O, no side effects.
Each check returns a dict:
    {
        "name":     str,
        "status":   "PASS" | "FAIL",
        "expected": any,
        "actual":   any,
        "evidence": str,
    }

Module-level constants EXPECTED_REVENUE and EXPECTED_ORDER_COUNT are
derived from orders.csv once at import time via the seed generator.
"""

import pathlib
import pandas as pd
from data.seed import generate

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# Derive ground-truth values from the authoritative source CSV
generate()  # ensure the CSV exists before reading
_orders_ref = pd.read_csv(DATA_DIR / "orders.csv")
EXPECTED_REVENUE: float = round(float(_orders_ref["order_total"].sum()), 2)
EXPECTED_ORDER_COUNT: int = int(len(_orders_ref))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_revenue_accuracy(result: dict) -> dict:
    actual = result["total_revenue"]
    passed = abs(actual - EXPECTED_REVENUE) < 0.01
    return {
        "name": "revenue_accuracy",
        "status": "PASS" if passed else "FAIL",
        "expected": EXPECTED_REVENUE,
        "actual": actual,
        "evidence": (
            "Revenue matches expected value."
            if passed
            else f"Revenue is ${actual:,.2f} but expected ${EXPECTED_REVENUE:,.2f} "
                 f"— difference of ${actual - EXPECTED_REVENUE:+,.2f}."
        ),
    }


def _check_duplicate_order_rows(result: dict, expected_order_count: int) -> dict:
    joined_row_count = result["_joined_row_count"]
    passed = joined_row_count == expected_order_count
    return {
        "name": "duplicate_order_rows",
        "status": "PASS" if passed else "FAIL",
        "expected": expected_order_count,
        "actual": joined_row_count,
        "evidence": (
            "Joined row count matches order count — no duplicates detected."
            if passed
            else f"Joined result has {joined_row_count} rows but only "
                 f"{expected_order_count} orders exist. "
                 f"Likely cause: multiple line items per order inflating the join."
        ),
    }


def _check_revenue_deviation_pct(result: dict) -> dict:
    actual = result["total_revenue"]
    deviation_pct = abs(actual - EXPECTED_REVENUE) / EXPECTED_REVENUE * 100
    passed = deviation_pct < 1.0
    return {
        "name": "revenue_deviation_pct",
        "status": "PASS" if passed else "FAIL",
        "expected": "< 1.0%",
        "actual": f"{deviation_pct:.1f}%",
        "evidence": (
            f"Revenue deviation is {deviation_pct:.2f}% — within the 1% threshold."
            if passed
            else f"Revenue deviation is {deviation_pct:.1f}% — exceeds the 1% threshold. "
                 f"This indicates a systematic calculation error, not rounding."
        ),
    }


def _check_order_count_match(result: dict, expected_order_count: int) -> dict:
    actual_count = result["order_count"]
    passed = actual_count == expected_order_count
    return {
        "name": "order_count_match",
        "status": "PASS" if passed else "FAIL",
        "expected": expected_order_count,
        "actual": actual_count,
        "evidence": (
            "Order count matches source data."
            if passed
            else f"Pipeline reports {actual_count} orders but source data has "
                 f"{expected_order_count}. Duplicate rows are being counted as orders."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_all_checks(result: dict) -> list:
    """
    Run all four DataGuard checks against a pipeline result dict.

    Args:
        result: dict returned by pipeline_buggy.run() or pipeline_fixed.run()

    Returns:
        list of check result dicts, one per check.
    """
    return [
        _check_revenue_accuracy(result),
        _check_duplicate_order_rows(result, EXPECTED_ORDER_COUNT),
        _check_revenue_deviation_pct(result),
        _check_order_count_match(result, EXPECTED_ORDER_COUNT),
    ]


def summarize(results: list) -> dict:
    """Return a summary dict with total, passed, and failed counts."""
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    return {"total": len(results), "passed": passed, "failed": failed}
