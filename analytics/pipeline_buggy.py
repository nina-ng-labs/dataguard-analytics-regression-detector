"""
Buggy analytics pipeline — intentional duplicate-row join.

BUG: orders is joined LEFT to order_items without deduplication.
Because there are exactly 2 line items per order, every order row is
duplicated in the join result. Summing order_total on the joined
DataFrame counts each order twice, producing revenue ~2× the true value.
"""

import pathlib
import pandas as pd
from data.seed import generate

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def run() -> dict:
    """Return analytics summary using the buggy join logic."""
    generate()  # ensure CSVs exist

    orders = pd.read_csv(DATA_DIR / "orders.csv")
    items = pd.read_csv(DATA_DIR / "order_items.csv")

    # BUG: joining without deduplication multiplies order rows
    joined = pd.merge(orders, items, on="order_id", how="left")

    total_revenue = round(float(joined["order_total"].sum()), 2)
    order_count = int(len(joined))

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        # expose joined frame for evidence checks
        "_joined_row_count": len(joined),
    }
