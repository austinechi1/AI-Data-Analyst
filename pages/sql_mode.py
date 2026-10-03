"""SQL Mode: write SQL yourself, pick an example, or let the AI translate plain English into SQL."""

import streamlit as st

from src.sql_engine import TABLE_NAME, example_queries
from src.ai_assistant import friendly_error
from src.ui import get_assistant, get_data, page_header, show_chart
from src.visualization import auto_chart

data = get_data()
engine, schema = data["engine"], data["schema"]
assistant = get_assistant()
examples = example_queries(schema)

page_header("SQL Mode", f"Your cleaned data is loaded into a SQLite table called \"{TABLE_NAME}\". Queries are read-only.")

with st.expander("Table columns"):
    st.dataframe([{"Column": n, "SQL type": t} for n, t in engine.columns()], hide_index=True)

if "sql_editor" not in st.session_state:
    st.session_state["sql_editor"] = next(iter(examples.values()))


def use_example():
    st.session_state["sql_editor"] = examples[st.session_state["example_choice"]]
    st.session_state["sql_run"], st.session_state["sql_source"] = True, "example"


def generate_sql():
    question = st.session_state.get("nl_question", "").strip()
    if not question:
        return
    try:
        out = assistant.nl_to_sql(question, engine.schema_text())
        st.session_state["sql_editor"] = out.get("sql", "")
        st.session_state["sql_note"] = out.get("explanation", "")
        st.session_state["sql_run"], st.session_state["sql_source"] = True, "ai"
        st.session_state["sql_question"] = question
    except Exception as exc:
        st.session_state["sql_error"] = friendly_error(exc)


# 1. Plain English -> SQL
st.markdown("#### 1 · Ask in plain English")
if assistant:
    left, right = st.columns([4, 1], vertical_alignment="bottom")
    left.text_input("Question", key="nl_question", placeholder="Show me the top 10 countries by revenue")
    right.button("Generate SQL", on_click=generate_sql, type="primary", icon=":material/auto_awesome:")
else:
    st.caption("Add an OpenAI API key to translate questions into SQL. You can still use the examples below.")

# 2. Examples
st.markdown("#### 2 · Or start from an example")
left, right = st.columns([4, 1], vertical_alignment="bottom")
left.selectbox("Example queries", list(examples), key="example_choice")
right.button("Use example", on_click=use_example)

# 3. Editor
st.markdown("#### 3 · Review and run the SQL")
if note := st.session_state.pop("sql_note", None):
    st.caption(f"AI: {note}")
if err := st.session_state.pop("sql_error", None):
    st.error(err)
st.text_area("SQL query", key="sql_editor", height=180)
if st.button("Run query", icon=":material/play_arrow:"):
    st.session_state["sql_run"], st.session_state["sql_source"] = True, "manual"

if st.session_state.pop("sql_run", False):
    query = st.session_state["sql_editor"]
    try:
        result = engine.run(query)
        st.session_state["sql_result"] = {"query": query, "result": result,
                                          "source": st.session_state.get("sql_source"),
                                          "question": st.session_state.get("sql_question", "SQL query result"),
                                          "explanation": None}
    except Exception as exc:
        st.session_state.pop("sql_result", None)
        st.error(f"Query failed: {exc}")

# 4. Result
res = st.session_state.get("sql_result")
if res:
    st.markdown("#### Result")
    st.code(res["query"], language="sql")
    st.caption(f"{len(res['result']):,} rows returned")
    st.dataframe(res["result"], hide_index=True)
    fig = auto_chart(res["result"])
    if fig is not None:
        show_chart(fig, "sql_chart")

    if assistant:
        if res["explanation"] is None and st.button("Explain this result", icon=":material/psychology:"):
            with st.spinner("Explaining..."):
                try:
                    res["explanation"] = assistant.explain(res["question"], "sql", res["query"], res["result"], [])
                except Exception as exc:
                    st.error(friendly_error(exc))
        if res["explanation"]:
            e = res["explanation"]
            st.markdown(f":material/calculate: **Answer (calculated):** {e.get('answer', '')}")
            st.markdown(f":material/psychology: **Interpretation:** {e.get('interpretation', '')}")
            st.markdown(f":material/task_alt: **Recommendation:** {e.get('recommendation', '')}")
