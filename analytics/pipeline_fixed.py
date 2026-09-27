"""
Fixed analytics pipeline — correct aggregation.

Aggregates revenue directly from orders.csv without joining order_items,
so each order is counted exactly once.
"""

import pathlib
import pandas as pd
from data.seed import generate

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def run() -> dict:
    """Return analytics summary using the correct aggregation logic."""
    generate()  # ensure CSVs exist

    orders = pd.read_csv(DATA_DIR / "orders.csv")

    total_revenue = round(float(orders["order_total"].sum()), 2)
    order_count = int(len(orders))

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "_joined_row_count": order_count,  # same as order_count — no join inflation
    }
