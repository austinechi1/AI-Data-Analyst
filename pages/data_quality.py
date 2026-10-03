"""Data Quality: problems found in the raw file and how they were cleaned."""

import pandas as pd
import streamlit as st

from src.ui import get_data, page_header, show_chart
from src.visualization import hbar_chart

data = get_data()
raw, quality = data["raw"], data["quality"]

page_header("Data Quality", "Problems found in the original file, before any cleaning.")

warnings = [q for q in quality if q["status"] == "warning"]
c1, c2, c3 = st.columns(3)
c1.metric("Checks run", len(quality), border=True)
c2.metric("Checks needing review", len(warnings), border=True)
c3.metric("Rows after cleaning", f"{len(data['df']):,}", f"{len(data['df']) - len(raw):,}", border=True)

st.subheader("Data quality report")
for item in quality:
    icon = ":material/warning:" if item["status"] == "warning" else ":material/check_circle:"
    with st.container(border=True):
        left, right = st.columns([1, 3])
        left.markdown(f"{icon} **{item['check']}**")
        left.markdown(f"### {item['count']:,}")
        right.write(item["consequence"])

missing = raw.isna().sum()
missing = missing[missing > 0].sort_values(ascending=False)
if not missing.empty:
    st.subheader("Missing values by column")
    mdf = pd.DataFrame({"Column": missing.index, "Missing": missing.values})
    mdf["% of rows"] = (mdf["Missing"] / len(raw) * 100).round(2)
    left, right = st.columns([2, 1])
    with left:
        show_chart(hbar_chart(mdf, "Column", "Missing", ""), "missing_chart")
    right.dataframe(mdf, hide_index=True)

st.subheader("Cleaning steps applied")
st.caption("You can switch these on or off under Upload Dataset → Cleaning options.")
for step in data["log"]:
    st.markdown(f"- {step}")

st.download_button("Download cleaned data (CSV)", data["df"].to_csv(index=False).encode("utf-8"),
                   file_name="cleaned_data.csv", mime="text/csv", icon=":material/download:")
