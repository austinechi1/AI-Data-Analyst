"""AI Assistant: ask questions in plain English. The AI writes the code, the app runs it on the real data."""

import streamlit as st

from src.ai_assistant import build_data_context, friendly_error, get_model
from src.local_assistant import LocalDataAssistant
from src.ui import ai_setup_message, get_assistant, get_data, page_header, show_chart
from src.visualization import auto_chart

data = get_data()
df, schema, engine = data["df"], data["schema"], data["engine"]

EXAMPLES = ["What are my top 10 products?", "Which country generates the most revenue?",
            "What was the best sales month?", "What is the average order value?",
            "Which products have declining sales?", "Which customers purchase most frequently?",
            "What percentage of orders were cancelled?",
            "Give me three important business insights from this dataset."]

title_col, status_col = st.columns([3, 1.2], vertical_alignment="bottom")
with title_col:
    page_header("AI Assistant", "Ask a question about your data. Every number is calculated from the dataset. "
                                "Open “How this was calculated” to check the SQL or Python behind an answer.")

assistant = get_assistant()
local_mode = assistant is None
if local_mode:
    assistant = LocalDataAssistant(schema, data["meta"])
    st.info("**Free built-in assistant active.** The suggested questions are answered with auditable Python "
            "calculations. Add an API key later to unlock unrestricted free-text questions.")

# ---------- connection status ----------
with status_col:
    if local_mode:
        st.caption(":material/check_circle: Free demo mode")
    else:
        with st.popover(f"Connected · {get_model()}", icon=":material/check_circle:", width="stretch"):
            st.write("Send a tiny test request to check your API key, billing and model.")
            if st.button("Test connection", icon=":material/network_check:"):
                with st.spinner("Contacting OpenAI..."):
                    try:
                        assistant.test_connection()
                        st.success("Connection works. You're ready to ask questions.")
                    except Exception as exc:
                        st.error(friendly_error(exc))

history = st.session_state.setdefault("chat_history", [])

top = st.columns([3, 1], vertical_alignment="center")
mode = top[0].radio("Analysis method", ["Auto", "SQL", "Pandas"], horizontal=True,
                    help="Auto lets the AI choose. SQL or Pandas forces that method, useful for showing your skills.")
if history and top[1].button("Clear chat", icon=":material/delete:", width="stretch"):
    history.clear()
    st.rerun()


def ask(question: str):
    st.session_state["pending_question"] = question


def render_turn(i: int, turn: dict):
    with st.chat_message("user"):
        st.write(turn["question"])
    with st.chat_message("assistant"):
        if turn.get("error"):
            st.error(turn["answer"])
            with st.expander("Error details"):
                st.code(turn["error"])
            return
        st.markdown(f"**{turn.get('answer', '')}**")
        if turn.get("result") is not None:
            fig = auto_chart(turn["result"], turn.get("chart"))
            if fig is not None:
                show_chart(fig, f"chat_chart_{i}")
            with st.expander("Calculated result"):
                st.dataframe(turn["result"], hide_index=True)
        if turn.get("code"):
            with st.expander("How this was calculated"):
                st.caption(turn.get("calculation") or turn.get("approach") or "")
                st.code(turn["code"], language="sql" if turn["method"] == "sql" else "python")
        if turn.get("interpretation"):
            st.markdown(f":material/psychology: **Interpretation:** {turn['interpretation']}")
        if turn.get("recommendation"):
            st.markdown(f":material/task_alt: **Recommendation:** {turn['recommendation']}")
        if turn.get("next_question"):
            st.button(f"Next question: {turn['next_question']}", key=f"next_{i}",
                      on_click=ask, args=(turn["next_question"],), type="tertiary", icon=":material/arrow_forward:")


if not history:
    st.markdown("**Try one of these:**")
    cols = st.columns(2)
    for i, q in enumerate(EXAMPLES):
        cols[i % 2].button(q, key=f"example_{i}", on_click=ask, args=(q,), width="stretch")

for i, turn in enumerate(history):
    render_turn(i, turn)

question = st.chat_input("Ask a question about your data")
question = question or st.session_state.pop("pending_question", None)

if question:
    context = build_data_context(df, schema, engine.schema_text())
    with st.chat_message("user"):
        st.write(question)
    with st.spinner("Analysing your data..."):
        try:
            turn = assistant.ask(question, df, engine, context, history, preferred=mode.lower())
        except Exception as exc:
            turn = {"question": question, "error": f"{type(exc).__name__}: {exc}", "answer": friendly_error(exc)}
    history.append(turn)
    st.rerun()
