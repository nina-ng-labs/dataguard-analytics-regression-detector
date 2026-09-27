"""
DataGuard — Analytics Regression Detector
Streamlit demo UI: single-session FAIL → FIX → PASS story.

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd

from analytics import pipeline_buggy, pipeline_fixed
from checks.guards import run_all_checks, summarize, EXPECTED_REVENUE

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DataGuard",
    page_icon="🛡️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "fixed" not in st.session_state:
    st.session_state.fixed = False

# ---------------------------------------------------------------------------
# Run the active pipeline
# ---------------------------------------------------------------------------
pipeline = pipeline_fixed if st.session_state.fixed else pipeline_buggy
result = pipeline.run()
checks = run_all_checks(result)
summary = summarize(checks)

actual_revenue = result["total_revenue"]
diff = actual_revenue - EXPECTED_REVENUE
deviation_pct = diff / EXPECTED_REVENUE * 100
all_passed = summary["failed"] == 0

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🛡️ DataGuard — Analytics Regression Detector")
st.caption("Detects silent analytics regressions before code ships.")

if st.session_state.fixed:
    st.success("✅ Fix applied — pipeline is now correct.")
else:
    st.error("🐛 Buggy pipeline loaded — duplicate-row join regression active.")

st.divider()

# ---------------------------------------------------------------------------
# Metric row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    label="Expected Revenue",
    value=f"${EXPECTED_REVENUE:,.2f}",
)
col2.metric(
    label="Actual Revenue",
    value=f"${actual_revenue:,.2f}",
    delta=f"{'+' if diff >= 0 else ''}{diff:,.2f}",
    delta_color="inverse",
)
col3.metric(
    label="Difference",
    value=f"${diff:+,.2f}",
    delta_color="inverse",
)
col4.metric(
    label="Deviation",
    value=f"{deviation_pct:+.1f}%",
    delta_color="inverse",
)

st.divider()

# ---------------------------------------------------------------------------
# Check results table
# ---------------------------------------------------------------------------
st.subheader("Check Results")

table_rows = []
for c in checks:
    status_icon = "🟢 PASS" if c["status"] == "PASS" else "🔴 FAIL"
    table_rows.append({
        "Check": c["name"],
        "Status": status_icon,
        "Expected": str(c["expected"]),
        "Actual": str(c["actual"]),
        "Evidence": c["evidence"],
    })

checks_df = pd.DataFrame(table_rows)
st.dataframe(
    checks_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Check":    st.column_config.TextColumn("Check", width="medium"),
        "Status":   st.column_config.TextColumn("Status", width="small"),
        "Expected": st.column_config.TextColumn("Expected", width="medium"),
        "Actual":   st.column_config.TextColumn("Actual", width="medium"),
        "Evidence": st.column_config.TextColumn("Evidence", width="large"),
    },
)

st.caption(f"**{summary['passed']}/{summary['total']} checks passed** — "
           f"{summary['failed']} failure(s) detected.")

st.divider()

# ---------------------------------------------------------------------------
# Root-cause panel / success banner
# ---------------------------------------------------------------------------
if not all_passed:
    st.subheader("🔍 Root-Cause Analysis")
    st.error(
        "**Duplicate-row join detected.**\n\n"
        "The analytics pipeline joins `orders` to `order_items` using "
        "`pd.merge(orders, items, on='order_id', how='left')` "
        "without deduplicating `order_items` first.\n\n"
        "Because the dataset contains **2 line items per order**, every order row "
        "is duplicated in the joined result (100 orders → 200 rows). "
        "Summing `order_total` on this inflated result counts each order **twice**, "
        f"producing revenue of **${actual_revenue:,.2f}** instead of "
        f"the correct **${EXPECTED_REVENUE:,.2f}**.\n\n"
        "**Fix:** aggregate `order_total` directly from `orders.csv`, "
        "bypassing the join entirely."
    )

    st.subheader("🔧 Apply Fix")
    if st.button("🔧 Fix Bug — switch to correct pipeline", type="primary"):
        st.session_state.fixed = True
        st.rerun()
else:
    st.success(
        "✅ **All checks passed — regression resolved.**\n\n"
        f"Revenue is ${actual_revenue:,.2f}, matching the expected "
        f"${EXPECTED_REVENUE:,.2f} exactly. "
        "All four DataGuard checks are green."
    )
    if st.button("↩️ Reset — reload buggy pipeline"):
        st.session_state.fixed = False
        st.rerun()
