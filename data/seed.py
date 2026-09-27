"""
Deterministic synthetic e-commerce data generator.

Generates two CSV files:
  data/orders.csv       — 100 rows, one row per order (order_id, order_total)
  data/order_items.csv  — 200 rows, exactly 2 line items per order
                          (order_id, item_id, item_revenue)

Both files are produced with NumPy random seed 42 so every run is identical.
Call generate() to write the files; importing this module has no side effects.
"""

import pathlib
import numpy as np
import pandas as pd

DATA_DIR = pathlib.Path(__file__).parent


def generate() -> None:
    """Write orders.csv and order_items.csv to the data/ directory."""
    rng = np.random.default_rng(42)

    n_orders = 100
    order_ids = [f"ORD-{i:04d}" for i in range(1, n_orders + 1)]
    order_totals = np.round(rng.uniform(10.0, 500.0, size=n_orders), 2)

    orders = pd.DataFrame({"order_id": order_ids, "order_total": order_totals})
    orders.to_csv(DATA_DIR / "orders.csv", index=False)

    # Split each order_total into 2 line items that sum exactly to order_total
    splits = np.round(rng.uniform(0.1, 0.9, size=n_orders), 6)
    item_rows = []
    for i, (oid, total, split) in enumerate(zip(order_ids, order_totals, splits)):
        rev_a = round(total * split, 2)
        rev_b = round(total - rev_a, 2)
        item_rows.append({"order_id": oid, "item_id": f"ITEM-{i*2+1:05d}", "item_revenue": rev_a})
        item_rows.append({"order_id": oid, "item_id": f"ITEM-{i*2+2:05d}", "item_revenue": rev_b})

    order_items = pd.DataFrame(item_rows)
    order_items.to_csv(DATA_DIR / "order_items.csv", index=False)


if __name__ == "__main__":
    generate()
    print("Seed data written to data/orders.csv and data/order_items.csv")
