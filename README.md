# DataGuard

**Detect silent analytics regressions before code ships.**

DataGuard wraps a small e-commerce analytics pipeline with deterministic checks that catch revenue double-counting, duplicate join rows, and metric drift — before they reach production.

## The Bug

`analytics/pipeline_buggy.py` joins `orders` to `order_items` without deduplication.  
With 2 line items per order, every order row is duplicated in the join, causing revenue to be counted twice (~2× the correct value).  
`analytics/pipeline_fixed.py` aggregates directly from `orders.csv` — no join, no duplication.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Streamlit demo  (FAIL → Fix Bug button → PASS)
streamlit run app.py

# 3. Run the pytest suite  (exits 0 when DataGuard detects correctly)
pytest -v
```

## Project Structure

```
data/
  seed.py              # Deterministic CSV generator (NumPy seed 42)
  orders.csv           # 100 orders  — generated on first run
  order_items.csv      # 200 items   — generated on first run
analytics/
  pipeline_buggy.py    # Faulty join  → 2× revenue
  pipeline_fixed.py    # Correct aggregation
checks/
  guards.py            # 4 deterministic check functions
tests/
  conftest.py          # Session-scoped fixtures
  test_guards.py       # pytest suite — 11 tests, exits 0
app.py                 # Streamlit UI entry point
requirements.txt
```

## Test Strategy

Tests verify **DataGuard's detection behaviour**:

| Class | What it proves |
|---|---|
| `TestBuggyPipelineDetection` | DataGuard correctly identifies all 4 FAIL checks on the buggy pipeline |
| `TestFixedPipelineDetection` | DataGuard correctly clears all 4 checks on the fixed pipeline |
| `TestSummary` | `summarize()` returns accurate counts for both cases |

No `xfail` markers — every assertion is a direct positive claim about DataGuard's output.  
`pytest` exits 0 when DataGuard behaves correctly for both pipelines.
