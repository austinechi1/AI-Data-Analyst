"""
Dashboard: filters, KPI cards with trends, the main charts and a business summary.
All numbers are calculated from the (filtered) data with Pandas.
"""

import streamlit as st

from src.ai_assistant import friendly_error
from src.analysis import (compute_kpis, correlation_matrix, filter_months, format_kpi, is_sales_data, kpi_trends,
                          numeric_summary, pct_change, period_options, previous_period, revenue_over_time)
from src.insights import dashboard_highlights
from src.ui import get_assistant, get_data, kpi_cards, page_header, panel_title, show_chart, summary_items
from src.visualization import area_line, heatmap, histogram, ranked_bars

data = get_data()
df_all, schema = data["df"], data["schema"]


def dataset_profile():
    profile = data["profile"]
    with st.expander(f"Dataset profile & preview · {data['name']}"):
        c = st.columns(4)
        c[0].metric("Rows", f"{profile['rows']:,}")
        c[1].metric("Columns", profile["columns"])
        c[2].metric("Missing values", f"{profile['missing_values']:,}")
        c[3].metric("Duplicate rows", f"{profile['duplicate_rows']:,}")
        t = st.columns(3)
        for col, label, key in zip(t, ["Date", "Numerical", "Categorical"], ["date", "numerical", "categorical"]):
            col.markdown(f"**{label} columns**\n\n" + ("\n".join(f"- {x}" for x in profile[key]) or "None"))
        st.dataframe(profile["dtypes"], hide_index=True)
        st.markdown("**First 100 rows (cleaned)**")
        st.dataframe(df_all.head(100), hide_index=True)


# ---------------------------------------------------------------- non-sales datasets
if not (is_sales_data(schema) and schema.get("date")):
    page_header("Dataset Overview", "This file isn't sales data, so the dashboard shows a general overview.")
    numerical = data["clean_types"]["numerical"]
    kpi_cards([
        {"label": "Rows", "value": f"{len(df_all):,}", "icon": "database", "note": "after cleaning"},
        {"label": "Columns", "value": str(df_all.shape[1]), "icon": "bars", "note": "in the dataset"},
        {"label": "Numerical columns", "value": str(len(numerical)), "icon": "chart", "note": "can be summed or averaged"},
        {"label": "Missing values", "value": f"{data['profile']['missing_values']:,}", "icon": "alert",
         "note": "in the original file"},
    ])
    left, right = st.columns(2)
    if numerical:
        with left, st.container(key="panel_dist"):
            panel_title("Distribution", "chart")
            col = st.selectbox("Column", numerical, label_visibility="collapsed", key="dist_col")
            show_chart(histogram(df_all, col), "dist_chart")
    corr = correlation_matrix(df_all, numerical)
    if not corr.empty:
        with right, st.container(key="panel_corr"):
            panel_title("Correlation", "trend")
            show_chart(heatmap(corr, ""), "corr_chart")
    with st.expander("Descriptive statistics"):
        st.dataframe(numeric_summary(df_all, numerical))
    dataset_profile()
    st.stop()

# ---------------------------------------------------------------- title + filters
date_col, rev = schema["date"], schema["revenue"]
country_col = schema.get("country")
prod = schema.get("product") or schema.get("product_code")

title_col, period_col, country_sel_col = st.columns([2.4, 1, 1], vertical_alignment="bottom")
with title_col:
    page_header("Sales Performance Overview", "Key metrics and insights from your sales data.")
periods = period_options(df_all, date_col)
period = period_col.selectbox("Period", list(periods), key="f_period", label_visibility="collapsed")
countries = ["All Countries"] + (sorted(df_all[country_col].dropna().astype(str).unique()) if country_col else [])
country = country_sel_col.selectbox("Country", countries, key="f_country", label_visibility="collapsed",
                                    disabled=not country_col)

start, n_months = periods[period]
base = df_all if country == "All Countries" else df_all[df_all[country_col].astype(str) == country]
df = filter_months(base, date_col, start, n_months)
prev = previous_period(base, date_col, start, n_months)

if df.empty:
    st.info("No sales match these filters. Try a different period or country.")
    st.stop()

# ---------------------------------------------------------------- KPI cards
kpis = compute_kpis(df, schema)
prev_kpis = compute_kpis(prev, schema) if prev is not None and not prev.empty else {}
trends = kpi_trends(df, schema)
note = f"vs. previous {n_months} months" if prev_kpis else ("trend over the period" if len(trends) > 1 else "")

cards = []
for name, icon_name, series in [("Total Revenue", "pound", "Revenue"), ("Total Orders", "cart", "Orders"),
                                ("Total Customers", "users", "Customers"), ("Average Order Value", "bars", "AOV")]:
    if name in kpis:
        cards.append({"label": name, "value": format_kpi(name, kpis[name]), "icon": icon_name,
                      "delta": pct_change(kpis[name], prev_kpis.get(name)), "note": note,
                      "spark": trends[series].tolist() if series in trends else []})
kpi_cards(cards)

# ---------------------------------------------------------------- row 1: trend + countries
row1_left, row1_right = st.columns([1.45, 1], gap="medium")
with row1_left, st.container(key="panel_trend"):
    h, s = st.columns([3, 1.2], vertical_alignment="center")
    with h:
        panel_title("Monthly Revenue Trend", "bars")
    metric = s.selectbox("Trend metric", ["Revenue", "Orders", "Average Order Value"], key="trend_metric",
                         label_visibility="collapsed")
    monthly = revenue_over_time(df, schema)
    if metric == "Average Order Value" and "Orders" in monthly:
        monthly["Average Order Value"] = monthly["Revenue"] / monthly["Orders"]
    if metric in monthly:
        show_chart(area_line(monthly, "Period", metric, money=metric != "Orders"), "trend_chart")

with row1_right, st.container(key="panel_country"):
    h, s = st.columns([3, 1.2], vertical_alignment="center")
    with h:
        panel_title("Top Countries by Revenue" if country == "All Countries" else f"Top Customers in {country}", "globe")
    by = s.selectbox("Country metric", ["Revenue", "Orders", "Customers"], key="country_metric",
                     label_visibility="collapsed")
    group = country_col if country == "All Countries" else schema.get("customer")
    if group:
        agg = {"Revenue": (rev, "sum"), "Orders": (schema.get("invoice") or rev, "nunique"),
               "Customers": (schema.get("customer") or rev, "nunique")}[by]
        table = df.groupby(group).agg(**{by: agg}).nlargest(8, by).reset_index()
        show_chart(ranked_bars(table, group, by, money=by == "Revenue"), "country_chart")

# ---------------------------------------------------------------- row 2: products + summary
row2_left, row2_right = st.columns([1.25, 1], gap="medium")
with row2_left, st.container(key="panel_products"):
    h, s = st.columns([3, 1.2], vertical_alignment="center")
    with h:
        panel_title("Top Products by Revenue", "box")
    pm = s.selectbox("Product metric", ["Revenue", "Units Sold"], key="product_metric", label_visibility="collapsed")
    if prod:
        value_col = rev if pm == "Revenue" else schema.get("quantity")
        if value_col:
            table = df.groupby(prod)[value_col].sum().nlargest(8).rename(pm).reset_index()
            show_chart(ranked_bars(table, prod, pm, money=pm == "Revenue", height=360), "product_chart")

with row2_right, st.container(key="panel_summary"):
    assistant = get_assistant()
    highlights = dashboard_highlights(df, schema)
    filter_key = f"{data['key']}|{period}|{country}"
    ai_items = st.session_state.setdefault("ai_highlights", {}).get(filter_key)

    h, b = st.columns([3, 1.3], vertical_alignment="center")
    with h:
        panel_title("AI Business Summary" if ai_items else "Business Summary", "sparkles",
                    chip="AI" if ai_items else "Calculated", chip_kind="ai" if ai_items else "calc")
    if assistant and not ai_items and highlights:
        if b.button("Write with AI", icon=":material/auto_awesome:", key="ai_summary_btn", type="tertiary"):
            with st.spinner("Writing summary..."):
                try:
                    st.session_state["ai_highlights"][filter_key] = assistant.rewrite_highlights(
                        highlights, {k: round(v, 2) for k, v in kpis.items()}, f"{period}, {country}")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))
    summary_items(ai_items or highlights)
    if ai_items:
        st.caption("Written by AI from the calculated figures. Numbers come from the data.")
    if st.button("Ask Your Data", icon=":material/forum:", type="primary", key="ask_data", width="stretch"):
        st.switch_page("pages/ai_chat.py")

st.write("")
dataset_profile()
