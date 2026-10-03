"""Business Insights: calculated findings, plus optional AI recommendations."""

import streamlit as st

from src.analysis import compute_kpis, product_trends
from src.insights import generate_insights
from src.ai_assistant import friendly_error
from src.ui import ai_setup_message, get_assistant, get_data, page_header

data = get_data()
df, schema = data["df"], data["schema"]

page_header("Business Insights", "Each fact below is calculated directly from the data. The AI section is clearly marked as interpretation.")

insights = generate_insights(df, schema, data["meta"])
st.session_state["insights"] = insights

if not insights:
    st.info("Not enough data to generate insights.")
for ins in insights:
    with st.container(border=True):
        st.markdown(f"**{ins['title']}**")
        st.markdown(f":material/calculate: **Calculated fact:** {ins['fact']}")
        st.markdown(f":material/help: **Why it matters:** {ins['why']}")

if schema.get("revenue") and schema.get("date") and (schema.get("product") or schema.get("product_code")):
    with st.expander("Product trend table (first half vs second half of the period)"):
        st.dataframe(product_trends(df, schema).round(1), hide_index=True)

st.subheader("AI recommendations")
assistant = get_assistant()
if assistant is None:
    ai_setup_message()
else:
    if st.button("Generate AI recommendations", type="primary", icon=":material/auto_awesome:"):
        with st.spinner("Writing recommendations from the calculated facts..."):
            try:
                st.session_state["ai_summary"] = assistant.business_recommendations(
                    insights, compute_kpis(df, schema))
            except Exception as exc:
                st.error(friendly_error(exc))
    summary = st.session_state.get("ai_summary")
    if summary:
        st.info(f":material/psychology: **Interpretation (AI):** {summary.get('summary', '')}")
        for rec in summary.get("recommendations", []):
            st.markdown(f"**{rec.get('title', '')}**: {rec.get('action', '')}  \n"
                        f"*Based on: {rec.get('based_on', '')}*")
        st.caption("AI recommendations are suggestions built on the facts above. Check them before acting.")
