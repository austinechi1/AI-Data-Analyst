"""
AI Data Analyst — Ask Your Data
================================
Entry point of the app. Run with:  streamlit run app.py

This file:
  1. sets up the page and loads the theme (assets/style.css)
  2. defines the page menu (st.navigation)
  3. draws the header (upload button) and sidebar (dataset status)
Each page lives in the pages/ folder.
"""

import streamlit as st

st.set_page_config(page_title="AI Data Analyst", page_icon="📊", layout="wide")

from src.ui import load_css, render_header, render_sidebar  # noqa: E402  (after set_page_config)

navigation = st.navigation([
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/home:", default=True),
    st.Page("pages/data_quality.py", title="Data Quality", icon=":material/database:"),
    st.Page("pages/business_insights.py", title="Business Insights", icon=":material/bar_chart:"),
    st.Page("pages/ai_chat.py", title="AI Assistant", icon=":material/forum:"),
    st.Page("pages/sql_mode.py", title="SQL Mode", icon=":material/code:"),
    st.Page("pages/export_report.py", title="Analysis Report", icon=":material/description:"),
])

load_css()
data = render_header()
render_sidebar(data)
navigation.run()
