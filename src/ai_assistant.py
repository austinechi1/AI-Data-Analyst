"""
ai_assistant.py
---------------
Connects the app to the OpenAI API.

How a question is answered (the AI never invents the numbers):
  1. plan     - the AI reads the column names and writes SQL or Pandas code
  2. execute  - the APP runs that code against the real data
  3. explain  - the AI sees the actual result and explains it in business language,
                keeping calculated facts, interpretation and recommendation separate

Privacy: only column names, a few example values and the query results
are sent to OpenAI, never the whole dataset.
"""

import builtins
import json
import os
import re

import numpy as np
import pandas as pd
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:  # the app still works without AI features
    OpenAI = None

load_dotenv()  # reads OPENAI_API_KEY from the .env file

DEFAULT_MODEL = "gpt-4o-mini"


def _secret(name):
    """Read a setting from .env first, then from Streamlit secrets (used when deployed)."""
    value = os.getenv(name)
    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None
    return value.strip() if isinstance(value, str) and value.strip() else None


def get_api_key():
    key = _secret("OPENAI_API_KEY")
    return None if key in (None, "your_key_here") else key


def get_model():
    return _secret("OPENAI_MODEL") or DEFAULT_MODEL


def is_configured() -> bool:
    return OpenAI is not None and get_api_key() is not None


# ---------------------------------------------------------------- safe Pandas execution
BLOCKED = ["import", "__", "open(", "exec(", "eval(", "compile(", "globals", "locals", "getattr",
           "setattr", "delattr", "os.", "sys.", "subprocess", "to_csv", "to_excel", "to_pickle",
           "to_sql", "to_parquet", "read_", "input(", "while "]
SAFE_BUILTINS = {n: getattr(builtins, n) for n in [
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min",
    "range", "round", "sorted", "str", "sum", "tuple", "zip", "set", "isinstance", "map", "filter",
    "reversed", "True", "False", "None"] if hasattr(builtins, n)}


def run_pandas(code: str, df: pd.DataFrame):
    """
    Run AI-written Pandas code on a COPY of the data.
    The code must store its answer in a variable called `result`.
    A basic block-list stops file access and imports. This is a
    portfolio-level safeguard, not a full security sandbox.
    """
    lowered = code.lower()
    for word in BLOCKED:
        if word in lowered:
            raise ValueError(f"Blocked unsafe code (contains '{word.strip()}').")
    namespace = {"__builtins__": SAFE_BUILTINS, "df": df.copy(), "pd": pd, "np": np}
    exec(code, namespace)
    if "result" not in namespace:
        raise ValueError("The code did not create a variable called `result`.")
    return namespace["result"]


def to_frame(result) -> pd.DataFrame:
    """Turn any result (table, list, single number) into a DataFrame for display."""
    if isinstance(result, pd.DataFrame):
        return result
    if isinstance(result, pd.Series):
        name = result.name if result.name is not None else "Value"
        return result.rename(name).reset_index()
    if isinstance(result, dict):
        return pd.DataFrame({"Item": list(result.keys()), "Value": list(result.values())})
    if isinstance(result, (list, tuple)):
        return pd.DataFrame({"Value": list(result)})
    if isinstance(result, (np.generic,)):
        result = result.item()
    return pd.DataFrame({"Value": [result]})


def result_preview(frame: pd.DataFrame, max_rows: int = 30) -> str:
    """A compact text version of the result for the AI to read."""
    if frame.empty:
        return "The result is empty (0 rows)."
    shown = frame.head(max_rows).copy()
    for c in shown.select_dtypes("float").columns:
        shown[c] = shown[c].round(4)
    note = f"\n(showing {max_rows} of {len(frame)} rows)" if len(frame) > max_rows else ""
    return f"{len(frame)} rows x {frame.shape[1]} columns\n{shown.to_csv(index=False)}{note}"


def build_data_context(df: pd.DataFrame, schema: dict, sql_schema: str) -> str:
    """Describe the dataset to the AI: columns, types, example values and detected roles."""
    lines = [f"Pandas DataFrame `df` with {len(df):,} rows. Columns:"]
    for col in df.columns:
        examples = df[col].dropna().unique()[:3]
        ex = ", ".join(str(e)[:40] for e in examples)
        lines.append(f"- {col} ({df[col].dtype}); examples: {ex}")
    roles = {k: v for k, v in schema.items() if v}
    lines.append(f"Detected roles: {json.dumps(roles)}")
    if "Revenue" in df.columns:
        lines.append("Revenue was created by the app as Quantity x UnitPrice.")
    if "IsCancelled" in df.columns:
        lines.append("IsCancelled is True for cancelled/returned lines (may already be filtered out).")
    if schema.get("date"):
        d = df[schema["date"]]
        lines.append(f"Date range: {d.min():%Y-%m-%d} to {d.max():%Y-%m-%d}.")
    lines.append("\nThe same data is in SQLite:\n" + sql_schema)
    lines.append("In SQLite, dates are TEXT 'YYYY-MM-DD HH:MM:SS'; use strftime('%Y-%m', col) for months.")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


PLAN_PROMPT = """You are a careful junior data analyst. You answer questions about a dataset by
writing code that the application runs on the real data. Never guess or invent numbers.

Respond with JSON only:
{
 "method": "sql" | "pandas" | "none",
 "code": "the SQL query or Pandas code",
 "chart": {"type": "line" | "bar" | "hbar" | "histogram" | "none", "x": "column in the result", "y": "numeric column in the result", "title": "chart title"},
 "approach": "one plain-English sentence describing the calculation"
}

Rules:
- SQL: one SQLite SELECT on the table described, double-quote column names, round money to 2 decimals, LIMIT 50 for lists.
- Pandas: use only `df`, `pd` and `np`; no imports, no files; store the final answer in `result`
  (a DataFrame, Series or single number). Keep it short.
- Pick charts: time trends -> line, rankings of many items -> hbar, few categories -> bar,
  distributions -> histogram, single numbers -> none.
- Follow-up questions: use the conversation to resolve words like "it", "its", "that country".
- For broad requests like "give me insights", build a small summary table of key figures.
- Use "none" only if the data cannot answer the question; put the reason in "approach".
"""

EXPLAIN_PROMPT = """You are a junior business analyst explaining a calculated result to a
non-technical manager. Use ONLY the numbers in the result. Do not invent figures.

Respond with JSON only:
{
 "answer": "direct answer in 1-2 sentences, with the key numbers",
 "calculation": "how it was calculated, in plain English",
 "interpretation": "what this probably means for the business (clearly an interpretation, not a fact)",
 "recommendation": "one practical next action",
 "next_question": "one useful follow-up question the user could ask"
}
If the result is empty or cannot answer the question, say so honestly in "answer".
Format money with a £ sign unless the data suggests another currency."""


class AIAssistant:
    def __init__(self, client=None, model=None):
        if client is None:
            if not is_configured():
                raise RuntimeError("OpenAI API key not found. Add OPENAI_API_KEY to your .env file.")
            client = OpenAI(api_key=get_api_key())
        self.client = client
        self.model = model or get_model()

    def _chat_json(self, system: str, messages: list) -> dict:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}] + messages,
            response_format={"type": "json_object"},
        )
        return _parse_json(response.choices[0].message.content)

    @staticmethod
    def _history_messages(history: list, limit: int = 6) -> list:
        """Previous questions and answers, so follow-ups like 'what about its AOV?' work."""
        msgs = []
        for turn in history[-limit:]:
            msgs.append({"role": "user", "content": turn["question"]})
            msgs.append({"role": "assistant", "content":
                         f"Method: {turn.get('method')}. Code: {turn.get('code')}. Answer: {turn.get('answer')}"})
        return msgs

    def plan(self, question, context, history, preferred="auto", error_feedback=None):
        prefer = {"sql": "Use SQL.", "pandas": "Use Pandas."}.get(preferred, "Choose SQL or Pandas, whichever is clearer.")
        content = f"DATA CONTEXT:\n{context}\n\nMETHOD: {prefer}\n\nQUESTION: {question}"
        if error_feedback:
            content += f"\n\nYour previous code failed:\n{error_feedback}\nFix it and return corrected JSON."
        return self._chat_json(PLAN_PROMPT, self._history_messages(history) + [{"role": "user", "content": content}])

    def explain(self, question, method, code, frame, history):
        content = (f"QUESTION: {question}\nMETHOD: {method}\nCODE RUN BY THE APP:\n{code}\n\n"
                   f"CALCULATED RESULT:\n{result_preview(frame)}")
        return self._chat_json(EXPLAIN_PROMPT, self._history_messages(history) + [{"role": "user", "content": content}])

    def ask(self, question, df, engine, context, history, preferred="auto") -> dict:
        """Full pipeline: plan -> execute on real data (with one automatic retry) -> explain."""
        turn = {"question": question, "method": None, "code": None, "result": None,
                "chart": None, "error": None}
        error = None
        for _attempt in range(2):
            plan = self.plan(question, context, history, preferred, error_feedback=error)
            method, code = plan.get("method", "none"), (plan.get("code") or "").strip()
            turn.update(method=method, code=code, chart=plan.get("chart"), approach=plan.get("approach"))
            if method == "none" or not code:
                turn.update(answer=plan.get("approach") or "This question can't be answered from the data.")
                return turn
            try:
                raw = engine.run(code) if method == "sql" else run_pandas(code, df)
                turn["result"] = to_frame(raw)
                break
            except Exception as exc:  # give the AI one chance to fix its own code
                error = f"{type(exc).__name__}: {exc}"
        else:
            turn.update(error=error, answer="I couldn't calculate this. Try rephrasing the question.")
            return turn

        turn.update(self.explain(question, method, code, turn["result"], history))
        return turn

    def nl_to_sql(self, question, sql_schema, history=None) -> dict:
        system = ("Convert the question into ONE SQLite SELECT query for the table below. "
                  "Double-quote column names. Dates are TEXT 'YYYY-MM-DD HH:MM:SS'. "
                  'Respond with JSON only: {"sql": "...", "explanation": "one sentence"}\n\n' + sql_schema)
        return self._chat_json(system, self._history_messages(history or []) +
                               [{"role": "user", "content": question}])

    def test_connection(self) -> str:
        """Send a tiny request to check the key and model work. Returns 'ok' or raises."""
        self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": "Reply with the word OK."}])
        return "ok"

    def rewrite_highlights(self, highlights: list, kpis: dict, filters: str) -> list:
        """Turn calculated highlights into a short executive summary, without changing any number."""
        system = ("You are a business analyst writing a dashboard summary for a manager. Rewrite the calculated "
                  "highlights below as exactly 3 items. Keep every number exactly as given; do not add new figures. "
                  "Each text is max 2 sentences and may add one short practical suggestion. "
                  'Respond with JSON only: {"items": [{"title": "max 5 words", "text": "..."}]}')
        payload = {"filters": filters, "kpis": kpis,
                   "highlights": [{"title": h["title"], "text": h["text"]} for h in highlights]}
        out = self._chat_json(system, [{"role": "user", "content": json.dumps(payload, default=str)}])
        items = out.get("items", [])[:3]
        icons = [h.get("icon", "sparkles") for h in highlights] + ["sparkles"] * 3
        return [{"icon": icons[i], "title": it.get("title", ""), "text": it.get("text", "")}
                for i, it in enumerate(items)]

    def business_recommendations(self, insights: list, kpis: dict) -> dict:
        system = ("You are a business analyst. Using ONLY the calculated facts given, write JSON: "
                  '{"summary": "2-3 sentence executive summary", "recommendations": '
                  '[{"title": "...", "action": "...", "based_on": "which fact supports it"}]} '
                  "with 3-5 recommendations. Do not invent numbers.")
        facts = {"kpis": kpis, "insights": [{"title": i["title"], "fact": i["fact"]} for i in insights]}
        return self._chat_json(system, [{"role": "user", "content": json.dumps(facts, default=str)}])


def friendly_error(exc: Exception) -> str:
    """Translate common OpenAI errors into plain English."""
    text = str(exc)
    low = text.lower()
    if "401" in text or "invalid_api_key" in low or "incorrect api key" in low:
        return "OpenAI rejected the API key. Check it was copied fully into .env (it starts with sk-)."
    if "insufficient_quota" in low or "billing" in low:
        return "The key works, but the OpenAI account has no credit. Add a few dollars under Settings → Billing."
    if "429" in text or "rate limit" in low:
        return "Too many requests in a short time. Wait a minute and try again."
    if "model" in low and ("not found" in low or "does not exist" in low or "404" in text):
        return f"The model '{get_model()}' isn't available on this account. Change OPENAI_MODEL in .env."
    if "connection" in low or "timed out" in low:
        return "Couldn't reach OpenAI. Check your internet connection."
    return f"The AI request failed: {text[:300]}"
