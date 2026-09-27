# DataGuard — Implementation Plan

## Top-Level Overview

DataGuard is a developer tool that detects silent analytics regressions before analytics code is shipped.
It wraps a small synthetic e-commerce analytics pipeline with deterministic data-integrity and metric-correctness checks,
demonstrates a classic "duplicate-row join bug" that causes revenue double-counting, and surfaces the regression with
clear evidence via a Streamlit UI and a pytest suite.

The demo flow is:
1. App loads with the **buggy** analytics pipeline — checks run and FAIL.
2. Developer clicks **"Fix Bug"** — the fix is applied in-memory.
3. Checks re-run immediately and all pass — FAIL → FIX → PASS is visible on one screen.

**Scope**: five Python files + one data file. No database, no cloud, no auth.

**One-command run**: `streamlit run app.py`
**One-command test**: `pytest`

---

## File Map

```
dataguard/
├── data/
│   └── seed.py            # Generates deterministic synthetic CSV files on first run
├── analytics/
│   ├── pipeline_buggy.py  # Intentionally faulty join (causes duplicate revenue rows)
│   └── pipeline_fixed.py  # Correct join producing accurate metrics
├── checks/
│   └── guards.py          # All DataGuard check functions (pure functions, no I/O)
├── tests/
│   └── test_guards.py     # pytest suite: buggy pipeline FAILS, fixed pipeline PASSES
└── app.py                 # Streamlit UI — single-session FAIL → FIX → PASS demo
```

---

## The Intentional Bug

**File**: `analytics/pipeline_buggy.py`

**Bug type**: Duplicate-row join
The pipeline joins an `orders` table to a `order_items` table on `order_id` using a standard
`merge(..., how='left')` without deduplicating `order_items` first.
Because the seed data has multiple line items per order, each order row is multiplied by the
number of its line items, producing inflated row counts and double-counted revenue.

**Seed data contract** (deterministic, hardcoded random seed):
- `orders.csv`: 100 rows, one row per order, each with a single `order_total` column.
- `order_items.csv`: 200 rows, exactly 2 line items per order, each with an `item_revenue` column.

**Expected revenue** (correct): sum of `order_total` across `orders.csv` — a fixed, known value.
**Buggy revenue** (faulty): sum of `order_total` after the bad join — exactly 2× the expected value.

This makes the regression 100% deterministic and easy to explain.

---

## Sub-Tasks

---

### Sub-Task 1 — Synthetic Data Seed

**Intent**
Create a deterministic data generator so every run uses identical source data.
All checks and expected values are derived from these fixed files.

**Expected Outcomes**
- `data/seed.py` generates `data/orders.csv` and `data/order_items.csv` when run as a script.
- Files are idempotent: re-running `seed.py` produces identical files.
- `orders.csv`: 100 rows, columns `order_id`, `order_total`.
- `order_items.csv`: 200 rows (2 per order), columns `order_id`, `item_id`, `item_revenue`.
- The sum of `order_total` across all orders is a known constant (e.g., computable from seed=42).
- CSVs are committed / generated at startup so the app and tests never need to re-seed.

**Todo List**
- [ ] Create `data/seed.py` using `numpy` random seed 42 to generate both CSVs.
- [ ] `order_total` values: 100 random floats in range [10.00, 500.00], rounded to 2 dp.
- [ ] `item_revenue` values: each order split into 2 line items summing to `order_total`.
- [ ] Write both CSVs to `data/` directory relative to the script.
- [ ] Add a guard so `seed.py` can be imported without side effects (use `if __name__ == "__main__"` and a `generate()` function).

**Relevant Context**
- No external data sources.
- `order_total` is the ground-truth revenue; `item_revenue` is used only by the buggy pipeline.

**Status**: `[x] done`

---

### Sub-Task 2 — Analytics Pipelines (Buggy and Fixed)

**Intent**
Implement two versions of the analytics pipeline so the bug and fix are explicit and isolated.

**Expected Outcomes**
- `analytics/pipeline_buggy.py` exports a `run() -> pd.DataFrame` function.
  - Loads both CSVs.
  - Joins `orders` LEFT JOIN `order_items` on `order_id` WITHOUT deduplication.
  - Returns a summary DataFrame with at least `total_revenue` computed as `sum(order_total)` on the joined result.
  - Revenue is ~2× the correct value due to row multiplication.
- `analytics/pipeline_fixed.py` exports a `run() -> pd.DataFrame` function.
  - Loads `orders.csv` only (or deduplicates correctly before aggregating).
  - Returns the same schema with the correct `total_revenue`.
- Both pipelines return a DataFrame with a consistent schema: `{"total_revenue": float, "order_count": int}`.

**Todo List**
- [ ] Create `analytics/pipeline_buggy.py` with `run()`.
- [ ] Implement the bad join: `pd.merge(orders, items, on='order_id', how='left')` then `sum('order_total')`.
- [ ] Create `analytics/pipeline_fixed.py` with `run()`.
- [ ] Implement correct aggregation: sum `order_total` directly from `orders` DataFrame.
- [ ] Both files must call `data/seed.py`'s `generate()` to ensure CSVs exist before loading.
- [ ] Both return the same output schema for interchangeable use by the checks.

**Relevant Context**
- `data/seed.py` → `generate()` function.
- Output schema must be consistent so `guards.py` works against both pipelines.

**Status**: `[x] done`

---

### Sub-Task 3 — DataGuard Check Functions

**Intent**
Implement all deterministic checks as pure functions in `checks/guards.py`.
Checks take DataFrames as input and return structured results — no file I/O inside checks.

**Expected Outcomes**
- `guards.py` exports a `run_all_checks(result_df, raw_orders_df, raw_items_df) -> list[dict]` function.
- Each check returns a dict: `{"name": str, "status": "PASS"|"FAIL", "expected": any, "actual": any, "evidence": str}`.
- The following checks are implemented:

| Check name | Logic | Fails on buggy pipeline |
|---|---|---|
| `revenue_accuracy` | `abs(actual_revenue - expected_revenue) < 0.01` | Yes — 2× expected |
| `duplicate_order_rows` | Row count of joined result == `len(orders)` | Yes — 200 rows vs 100 |
| `revenue_deviation_pct` | `(actual - expected) / expected * 100 < 1.0` | Yes — ~100% deviation |
| `order_count_match` | `order_count == len(orders)` | Yes — doubled |

- A `EXPECTED_REVENUE` constant is computed once from `orders.csv` at import time.

**Todo List**
- [ ] Create `checks/guards.py`.
- [ ] Load `orders.csv` at module level to derive `EXPECTED_REVENUE` and `EXPECTED_ORDER_COUNT`.
- [ ] Implement each of the four checks as an internal helper.
- [ ] Implement `run_all_checks()` that calls all helpers and returns a list of result dicts.
- [ ] Add a `summarize(results) -> dict` helper returning `{"total": int, "passed": int, "failed": int}`.

**Relevant Context**
- Check inputs come from the pipeline `run()` output plus raw DataFrames for evidence.
- Pure functions make this trivially testable.

**Status**: `[x] done`

---

### Sub-Task 4 — pytest Suite

**Intent**
Provide a `pytest` test file that verifies DataGuard's own detection behaviour — not the analytics code under test.
The suite validates two things: (1) DataGuard correctly identifies all four check failures when the buggy pipeline runs,
and (2) DataGuard correctly reports all four checks as passing when the fixed pipeline runs.
`pytest` exits 0 in both cases because DataGuard is behaving correctly in both scenarios.

**Expected Outcomes**
- `tests/test_guards.py` has two test groups: `TestBuggyPipelineDetection` and `TestFixedPipelineDetection`.
- `TestBuggyPipelineDetection`: runs the buggy pipeline through `run_all_checks()` and **asserts that each of the four checks returns status `"FAIL"`**. This is a positive assertion — DataGuard is working correctly by detecting the regression.
- `TestFixedPipelineDetection`: runs the fixed pipeline through `run_all_checks()` and **asserts that each of the four checks returns status `"PASS"`**.
- No `xfail` markers anywhere — every assertion is a direct positive claim about DataGuard's output.
- `pytest` exits 0 when DataGuard correctly detects the buggy pipeline AND correctly clears the fixed pipeline.

**Todo List**
- [ ] Create `tests/test_guards.py`.
- [ ] Add `tests/conftest.py` with two session-scoped fixtures: `buggy_results` and `fixed_results`, each returning the list of check dicts from `run_all_checks()`.
- [ ] `TestBuggyPipelineDetection`: one test per check — assert `result["status"] == "FAIL"` for `revenue_accuracy`, `duplicate_order_rows`, `revenue_deviation_pct`, and `order_count_match`.
- [ ] `TestFixedPipelineDetection`: one test per check — assert `result["status"] == "PASS"` for all four checks.
- [ ] Add a `test_summary_buggy` test asserting `summarize()` returns `{"total": 4, "passed": 0, "failed": 4}`.
- [ ] Add a `test_summary_fixed` test asserting `summarize()` returns `{"total": 4, "passed": 4, "failed": 0}`.
- [ ] `pytest` from project root exits 0 (all assertions are positive claims about DataGuard's detection).

**Relevant Context**
- `analytics/pipeline_buggy.py` → `run()`
- `analytics/pipeline_fixed.py` → `run()`
- `checks/guards.py` → `run_all_checks()`, `summarize()`

**Status**: `[x] done`

---

### Sub-Task 5 — Streamlit Demo UI

**Intent**
Build a single-page Streamlit app that shows the complete FAIL → FIX → PASS story in one session.
No file editing required: a "Fix Bug" button patches the pipeline in-memory and re-runs checks.

**Expected Outcomes**
- `app.py` is the entry point: `streamlit run app.py`.
- On load: runs the **buggy** pipeline, executes all checks, and displays results.
- UI layout (top to bottom):
  1. **Header**: "DataGuard — Analytics Regression Detector"
  2. **Metric row**: Expected Revenue | Actual Revenue | Difference | Deviation %
  3. **Check results table**: name, status (🔴 FAIL / 🟢 PASS), expected, actual, evidence
  4. **Root-cause panel**: highlighted explanation of the join bug (shown only when checks fail)
  5. **"Fix Bug" button**: applies the fix in-memory (switches to `pipeline_fixed.run()`)
  6. After fix: re-renders the same layout with all green — no page reload needed
- Uses `st.session_state` to track whether the fix has been applied.
- No external CSS frameworks; use Streamlit's native components only.

**Todo List**
- [ ] Create `app.py`.
- [ ] Initialize `st.session_state.fixed = False` on first load.
- [ ] Conditionally import and call `pipeline_buggy.run()` or `pipeline_fixed.run()` based on state.
- [ ] Call `run_all_checks()` with pipeline output + raw DataFrames.
- [ ] Render metric columns with `st.metric()` using delta to highlight revenue difference.
- [ ] Render check table with color-coded status using `st.dataframe()` or `st.table()`.
- [ ] Show root-cause `st.error()` block with join explanation when any check fails.
- [ ] Add `st.button("🔧 Fix Bug")` that sets `st.session_state.fixed = True` and triggers rerun.
- [ ] After fix, replace error block with `st.success("All checks passed — regression resolved.")`.

**Relevant Context**
- `checks/guards.py` → `run_all_checks()`, `EXPECTED_REVENUE`
- `analytics/pipeline_buggy.py` and `analytics/pipeline_fixed.py` → `run()`

**Status**: `[x] done`

---

### Sub-Task 6 — Project Wiring and README

**Intent**
Ensure the project is runnable with a single command and includes minimal setup documentation.

**Expected Outcomes**
- `requirements.txt` lists: `pandas`, `numpy`, `streamlit`, `pytest`.
- `README.md` contains: one-line install, one-line run, one-line test, brief description of the bug.
- `data/seed.py` is called automatically on app startup and test setup so no manual pre-seeding is needed.
- All `__init__.py` files exist where needed for imports.

**Todo List**
- [ ] Create `requirements.txt`.
- [ ] Create `README.md` with setup and run instructions.
- [ ] Add `data/__init__.py`, `analytics/__init__.py`, `checks/__init__.py` (empty files).
- [ ] Verify imports work from project root for both `streamlit run app.py` and `pytest`.

**Relevant Context**
- Entry point: `app.py` at project root.
- Test entry point: `tests/test_guards.py`.

**Status**: `[x] done`

---

## Implementation Order

Sub-tasks must be implemented in this order due to dependencies:

1. **Sub-Task 1** — data seed (no dependencies)
2. **Sub-Task 2** — pipelines (depend on seed data)
3. **Sub-Task 3** — check functions (depend on pipeline output schema)
4. **Sub-Task 4** — pytest suite (depends on pipelines + checks)
5. **Sub-Task 5** — Streamlit UI (depends on pipelines + checks)
6. **Sub-Task 6** — wiring + README (depends on all above)
