"""
ui.py
-----
Shared interface pieces used by every page:
  - load_css()          applies the light coral theme (assets/style.css)
  - render_header()     title, dataset pill and the "Upload Dataset" button
  - render_sidebar()    logo + dataset status card (the page menu comes from st.navigation)
  - get_data()          gives each page the loaded and cleaned dataset
  - small HTML helpers  KPI cards, panel titles, summary rows, sparklines
Streamlit re-runs the script on every click, so heavy work is cached
with @st.cache_data / @st.cache_resource to keep the app fast.
"""

import hashlib
from html import escape
from pathlib import Path

import streamlit as st

from src import ai_assistant
from src.analysis import profile_dataset
from src.data_cleaning import clean_column_names, detect_column_types, detect_schema, prepare_data, quality_report
from src.data_loader import SAMPLE_NAME, load_bytes, load_sample
from src.icons import icon, svg_img
from src.layout import DATASET_WIDGET_KEYS
from src.sql_engine import SQLEngine
from src.theme import COPPER, COPPER_DARK, GREEN, MUTED

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


# ---------------------------------------------------------------- data loading (cached)
@st.cache_data(show_spinner="Reading your file...")
def _read_upload(data: bytes, name: str):
    return clean_column_names(load_bytes(data, name))


@st.cache_data
def _read_sample():
    return clean_column_names(load_sample())


@st.cache_resource(show_spinner="Profiling and cleaning the data...")
def _process(_raw, key: str, dup: bool, cancel: bool, invalid: bool):
    """Everything that only needs recalculating when the file or cleaning options change."""
    types = detect_column_types(_raw)
    profile = profile_dataset(_raw, types)
    quality = quality_report(_raw, detect_schema(_raw), types)
    df, schema, log, meta = prepare_data(_raw, dup, cancel, invalid)
    return {"types": types, "profile": profile, "quality": quality, "df": df, "schema": schema,
            "log": log, "meta": meta, "clean_types": detect_column_types(df), "engine": SQLEngine(df)}


def _use_sample(value: bool):
    st.session_state["use_sample"] = value


def _load_dataset(uploaded):
    """Read whichever dataset is active (upload wins over the sample) and store it in session state."""
    raw, name, key = None, None, None
    try:
        if uploaded is not None:
            data = uploaded.getvalue()
            raw, name, key = _read_upload(data, uploaded.name), uploaded.name, hashlib.md5(data).hexdigest()
        elif st.session_state.get("use_sample"):
            raw, name, key = _read_sample(), SAMPLE_NAME, "sample"
    except Exception as exc:
        st.session_state["load_error"] = f"Could not read this file: {exc}"

    if raw is None:
        st.session_state.pop("data", None)
        return None

    dup = st.session_state.get("opt_dup", True)
    cancel = st.session_state.get("opt_cancel", True)
    invalid = st.session_state.get("opt_invalid", True)
    processed = _process(raw, key, dup, cancel, invalid)
    data = {"name": name, "raw": raw, "key": f"{key}-{dup}-{cancel}-{invalid}", **processed}

    # A new dataset starts a fresh conversation and summary.
    if st.session_state.get("dataset_key") != key:
        st.session_state["dataset_key"] = key
        for k in ["chat_history", "sql_result", "ai_summary", "ai_highlights", "sql_editor", *DATASET_WIDGET_KEYS]:
            st.session_state.pop(k, None)  # filters too, so the new file's dashboard re-arranges from clean defaults
    st.session_state["data"] = data
    return data


# ---------------------------------------------------------------- layout
def load_css():
    css = (ASSETS / "style.css").read_text(encoding="utf-8")
    st.html(f"<style>{css}</style>")


def render_header():
    """Top bar shown on every page."""
    with st.container(key="app_header"):
        title_col, pill_col, button_col = st.columns([3, 2.2, 1.1], vertical_alignment="center")

        # The upload button is drawn first (in the right-hand column) so the
        # dataset pill next to it can show the file it just loaded.
        with button_col:
            with st.popover("Upload Dataset", icon=":material/upload:", type="primary", width="stretch"):
                uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"], key="uploader")
                if uploaded is None:
                    if st.session_state.get("use_sample"):
                        st.button("Clear sample dataset", on_click=_use_sample, args=(False,))
                    else:
                        st.button("Use sample sales dataset", on_click=_use_sample, args=(True,))
                st.markdown("**Cleaning options**")
                st.checkbox("Remove duplicate rows", value=True, key="opt_dup")
                st.checkbox("Remove cancellations / returns", value=True, key="opt_cancel")
                st.checkbox("Remove zero/negative prices & invalid dates", value=True, key="opt_invalid")
            data = _load_dataset(uploaded)

        with title_col:
            st.html('<div class="app-title">AI Data Analyst</div>'
                    '<div class="app-tagline">Upload. Analyse. Ask. Decide.</div>')
        with pill_col:
            if data is not None:
                st.html(f'<div class="data-pill">{icon("database", 18, MUTED)} {escape(data["name"])} '
                        f'<span class="muted">· {len(data["df"]):,} rows</span></div>')
        if err := st.session_state.pop("load_error", None):
            st.error(err)
    return data


def render_sidebar(data):
    st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "icon.svg"))
    with st.sidebar:
        if data is not None:
            status = (f'<div class="status-head"><span class="dot" style="background:{GREEN}"></span>'
                      f'<span style="color:{GREEN}">Dataset Ready</span></div>'
                      f'<div class="status-body">{icon("database", 30, MUTED, 1.6)}<div>'
                      f'{escape(data["name"])}<br><span class="muted">{len(data["df"]):,} clean rows</span>'
                      f'</div></div>')
        else:
            status = (f'<div class="status-head"><span class="dot" style="background:{MUTED}"></span>'
                      f'<span style="color:{MUTED}">No dataset loaded</span></div>')
        if ai_assistant.is_configured():
            ai = f'<span class="dot" style="background:{GREEN}"></span>&nbsp; AI connected · {escape(ai_assistant.get_model())}'
        else:
            ai = f'<span class="dot" style="background:{GREEN}"></span>&nbsp; Free assistant active'
        st.html(f'<div class="status-card">{status}<div class="status-ai">{ai}</div></div>')
        st.write("")
        if st.toggle("Clean screenshot mode", key="clean_mode",
                     help="Hides buttons, expanders and captions so the page is ready to capture."):
            st.html("<style>.stMain [data-testid='stExpander'], .stMain .stButton, .stMain [data-testid='stCaptionContainer'],"
                    ".stMain [data-testid='stPopover'], [data-testid='stToolbar'] { display: none !important; }</style>")


def get_data():
    """Return the current dataset, or show a welcome screen and stop the page."""
    data = st.session_state.get("data")
    if data is None:
        st.html(
            '<div class="hero"><h1>Turn your data into answers.</h1>'
            '<p>Upload a CSV or Excel file with the <b>Upload Dataset</b> button, or start with the sample sales '
            'dataset. The app profiles your data, checks its quality, calculates KPIs and lets you ask questions '
            'in plain English. Every number is calculated from your data.</p>'
            '<div class="steps"><div class="step"><b>1 · Upload</b>CSV or Excel, cleaned automatically.</div>'
            '<div class="step"><b>2 · Analyse</b>KPIs, charts, data quality and insights.</div>'
            '<div class="step"><b>3 · Ask</b>Questions in plain English, answered with SQL or Python.</div></div></div>')
        st.write("")
        st.button("Try the sample sales dataset", type="primary", icon=":material/play_arrow:",
                  on_click=_use_sample, args=(True,))
        st.stop()
    return data


def page_header(title: str, subtitle: str = ""):
    st.html(f'<div class="section-title">{escape(title)}</div>'
            + (f'<div class="section-sub">{escape(subtitle)}</div>' if subtitle else ""))


def panel_title(text: str, icon_name: str, chip: str | None = None, chip_kind: str = "calc"):
    chip_html = f'<span class="chip {chip_kind}">{escape(chip)}</span>' if chip else ""
    st.html(f'<div class="panel-title">{icon(icon_name, 22)}<span>{escape(text)}</span>{chip_html}</div>')


def show_chart(fig, key: str):
    """Show a Plotly chart with our own colours (theme=None) and without the toolbar."""
    st.plotly_chart(fig, key=key, theme=None, config={"displayModeBar": False})


# ---------------------------------------------------------------- KPI cards
def sparkline(values, width=130, height=42, color=COPPER) -> str:
    """A tiny trend line drawn as SVG."""
    vals = [float(v) for v in values if v == v]  # drop NaN
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    step = width / (len(vals) - 1)
    pts = [(i * step, height - 4 - (v - lo) / span * (height - 10)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} {line} {width},{height}"
    gid = "fade"
    return svg_img(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>'
            f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{area}" fill="url(#{gid})"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3.5" fill="{COPPER_DARK}"/></svg>', width, height, "trend")


def kpi_cards(cards: list[dict]):
    """cards: [{label, value, icon, delta (float or None), note, spark (list)}]"""
    html = [f'<div class="kpi-grid n{min(len(cards), 4)}">']  # grid width follows the number of cards
    for c in cards:
        if c.get("delta") is not None:
            d = c["delta"]
            arrow, cls = ("▲", "up") if d >= 0 else ("▼", "down")
            delta = f'<b class="{cls}">{arrow} {d:+.1%}</b><br>{escape(c["note"])}'
        else:
            delta = escape(c.get("note", ""))
        html.append(
            f'<div class="kpi"><div class="kpi-top"><div class="kpi-icon">{icon(c["icon"], 24, COPPER)}</div>'
            f'<div><div class="kpi-label">{escape(c["label"])}</div><div class="kpi-value">{escape(c["value"])}</div>'
            f'</div></div><div class="kpi-bottom"><div class="kpi-delta">{delta}</div>'
            f'{sparkline(c.get("spark", []))}</div></div>')
    html.append("</div>")
    st.html("".join(html))


def summary_items(items: list[dict]):
    """Rows in the Business Summary panel: [{icon, title, text}]"""
    st.html("".join(
        f'<div class="summary-item"><div class="summary-icon">{icon(i.get("icon", "sparkles"), 26)}</div>'
        f'<div><div class="summary-title">{escape(i["title"])}</div>'
        f'<div class="summary-text">{escape(i["text"])}</div></div></div>' for i in items))


# ---------------------------------------------------------------- AI helpers
def get_assistant():
    if not ai_assistant.is_configured():
        return None
    if "assistant" not in st.session_state:
        st.session_state["assistant"] = ai_assistant.AIAssistant()
    return st.session_state["assistant"]


def ai_setup_message():
    with st.container(key="panel_ai_setup"):
        panel_title("Connect the AI Assistant", "sparkles")
        st.markdown(
            "The AI features need your own OpenAI API key. Everything else in the app works without it.\n\n"
            "1. Create a key at **platform.openai.com** → **API keys** (add a little billing credit first).\n"
            "2. In VS Code, copy `.env.example` and rename the copy to `.env`.\n"
            "3. Replace `your_key_here` with your key (no quotes, no spaces) and save.\n"
            "4. Stop the app with **Ctrl + C** and run `streamlit run app.py` again.\n\n"
            "The sidebar will then show **AI connected**.")
