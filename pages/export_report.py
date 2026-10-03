"""Analysis Report: download everything as one HTML file (open it in a browser, print to PDF if needed)."""

import streamlit as st

from src.analysis import compute_kpis, revenue_over_time, top_n_by
from src.insights import generate_insights
from src.report import build_html_report
from src.ui import get_data, page_header
from src.visualization import area_line, histogram, light_version, ranked_bars

data = get_data()
df, schema = data["df"], data["schema"]

page_header("Analysis Report")
st.write("Download a report with the dataset overview, KPIs, data quality, charts, key findings and "
         "recommendations. Open it in your browser; use Ctrl + P → Save as PDF for a PDF copy.")

kpis = compute_kpis(df, schema)
insights = generate_insights(df, schema, data["meta"])
ai_summary = st.session_state.get("ai_summary")

figures, rev = [], schema.get("revenue")
if rev and schema.get("date"):
    figures.append(area_line(revenue_over_time(df, schema), "Period", "Revenue", "Monthly revenue"))
if rev and schema.get("country"):
    figures.append(ranked_bars(top_n_by(df, schema["country"], rev, 10), schema["country"], rev, "Top 10 countries by revenue"))
prod = schema.get("product") or schema.get("product_code")
if rev and prod:
    figures.append(ranked_bars(top_n_by(df, prod, rev, 10), prod, rev, "Top 10 products by revenue"))
if not rev:
    for col in data["clean_types"]["numerical"][:3]:
        figures.append(histogram(df, col, f"Distribution of {col}"))

c1, c2, c3 = st.columns(3)
c1.metric("Charts", len(figures), border=True)
c2.metric("Key findings", len(insights), border=True)
c3.metric("AI recommendations", "Included" if ai_summary else "Not generated", border=True)
if not ai_summary:
    st.caption("Tip: generate AI recommendations on the Business Insights page first to include them in the report.")

figures = [light_version(f) for f in figures]  # white background for the report
html = build_html_report(data["name"], data["profile"], kpis, data["quality"], insights, figures,
                         data["log"], ai_summary)
file_name = data["name"].rsplit(".", 1)[0] + "_analysis_report.html"
st.download_button("Generate Analysis Report", html.encode("utf-8"), file_name=file_name,
                   mime="text/html", type="primary", icon=":material/download:")
