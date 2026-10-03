"""
visualization.py
----------------
Plotly charts with one consistent style (dark copper theme), plus:
  - auto_chart():    picks a sensible chart type for any result table
  - light_version(): restyles a chart for the white downloadable report
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.theme import BORDER, COPPER, COPPER_DARK, MUTED, PEACH, TEXT, blend, rgba

FONT = "Inter, Segoe UI, Arial, sans-serif"


def _style(fig, title="", height=330):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=TEXT)) if title else None,
        height=height, margin=dict(l=10, r=24, t=40 if title else 8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=12),
        hoverlabel=dict(bgcolor="#2B1810", bordercolor=COPPER, font=dict(color=TEXT)),
        showlegend=False,
    )
    grid = dict(gridcolor=rgba(BORDER, 0.9), zeroline=False, linecolor=BORDER, title=None, automargin=True)
    fig.update_xaxes(**grid)
    fig.update_yaxes(**grid)
    return fig


def _money_axis(fig, axis="y", money=True):
    if money:
        (fig.update_yaxes if axis == "y" else fig.update_xaxes)(tickprefix="£", tickformat="~s")


def light_version(fig):
    """Copy a chart and restyle it for a white background (used in the HTML report)."""
    fig = go.Figure(fig)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#334155"),
                      title_font_color="#1F2937")
    fig.update_xaxes(gridcolor="#E5E7EB", linecolor="#CBD5E1")
    fig.update_yaxes(gridcolor="#E5E7EB", linecolor="#CBD5E1")
    for trace in fig.data:
        if getattr(trace, "textfont", None) is not None:
            trace.textfont.color = "#334155"
    return fig


def area_line(df, x, y, title="", money=True, height=330):
    """Line chart with a soft gradient underneath (used for trends over time)."""
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="lines+markers",
        line=dict(color=COPPER, width=3, shape="spline", smoothing=0.3),
        marker=dict(size=8, color=COPPER, line=dict(color="#FFD9C9", width=1.5)),
        fill="tozeroy",
        fillgradient=dict(type="vertical", colorscale=[[0, rgba(COPPER, 0.0)], [1, rgba(COPPER, 0.35)]]),
        hovertemplate=f"%{{x|%b %Y}}<br>{y}: " + ("£%{y:,.0f}" if money else "%{y:,.0f}") + "<extra></extra>",
    ))
    _style(fig, title, height)
    fig.update_xaxes(showgrid=False, tickformat="%b")
    if len(df) and pd.api.types.is_datetime64_any_dtype(df[x]):
        pad = pd.Timedelta(days=12)
        fig.update_xaxes(range=[df[x].min() - pad, df[x].max() + pad], dtick="M1")
    _money_axis(fig, "y", money)
    fig.update_yaxes(griddash="dot", rangemode="tozero")
    return fig


def ranked_bars(df, label, value, title="", money=True, height=330):
    """Horizontal bars, largest at the top, with value labels. Colour fades from copper to peach."""
    df = df.sort_values(value, ascending=True)
    n = len(df)
    colors = [blend(PEACH, COPPER, (i / max(n - 1, 1)) ** 1.5) for i in range(n)]
    text = [f"£{v:,.0f}" if money else f"{v:,.0f}" for v in df[value]]
    fig = go.Figure(go.Bar(
        x=df[value], y=df[label].astype(str), orientation="h", marker=dict(color=colors, cornerradius=3),
        text=text, textposition="outside", textfont=dict(color=TEXT, size=12), cliponaxis=False,
        hovertemplate="%{y}<br>" + ("£%{x:,.0f}" if money else "%{x:,.0f}") + "<extra></extra>",
    ))
    _style(fig, title, height)
    fig.update_yaxes(showgrid=False, tickfont=dict(color="#E8D8CF"))
    fig.update_xaxes(range=[0, df[value].max() * 1.22] if n else None, griddash="dot")
    _money_axis(fig, "x", money)
    return fig


# ---- generic charts (SQL Mode, AI Assistant, non-sales datasets) ----
def line_chart(df, x, y, title=""):
    fig = px.line(df, x=x, y=y, markers=True, color_discrete_sequence=[COPPER])
    fig.update_traces(line_width=3)
    return _style(fig, title)


def bar_chart(df, x, y, title=""):
    fig = px.bar(df, x=x, y=y, color_discrete_sequence=[COPPER])
    return _style(fig, title)


def hbar_chart(df, x, y, title=""):
    """Horizontal bars: x = category (shown on the left), y = value."""
    money = any(w in str(y).lower() for w in ["revenue", "sales", "value", "price", "aov", "amount", "spend"])
    return ranked_bars(df, x, y, title, money=money, height=max(260, 34 * len(df) + 60))


def histogram(df, col, title="", clip_quantile=0.99, nbins=40):
    """Distribution of one numeric column. Very extreme values are clipped so the shape is visible."""
    data = df[[col]].dropna()
    if clip_quantile:
        data = data[data[col] <= data[col].quantile(clip_quantile)]
    fig = px.histogram(data, x=col, nbins=nbins, color_discrete_sequence=[COPPER])
    fig.update_layout(bargap=0.05)
    return _style(fig, title)


def heatmap(corr: pd.DataFrame, title="Correlation between numeric columns"):
    scale = [[0, "#4B6584"], [0.5, "#24140E"], [1, COPPER]]
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale=scale, zmin=-1, zmax=1, aspect="auto")
    return _style(fig, title, height=380)


def _is_time_col(series: pd.Series, name: str) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    return any(w in str(name).lower() for w in ["date", "month", "year", "week", "day", "period", "quarter"])


def auto_chart(result, hint: dict | None = None):
    """
    Choose a chart for a result table:
      time column + number -> line chart
      category + number    -> bar chart (horizontal when there are many / long labels)
      one numeric column   -> histogram
    Returns a Plotly figure, or None if a chart would not help.
    """
    if isinstance(result, pd.Series):
        result = result.reset_index()
    if not isinstance(result, pd.DataFrame) or len(result) < 2 or result.shape[1] == 0:
        return None
    df = result.copy()
    cols = list(df.columns)
    numeric = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
    hint = hint or {}
    kind, x, y, title = hint.get("type"), hint.get("x"), hint.get("y"), hint.get("title", "")

    if kind == "none":
        return None
    if kind in {"line", "bar", "hbar"} and x in cols and y in numeric:
        return {"line": line_chart, "bar": bar_chart, "hbar": hbar_chart}[kind](df, x, y, title)
    if kind == "histogram" and x in numeric:
        return histogram(df, x, title)

    others = [c for c in cols if c not in numeric]
    if not numeric:
        return None
    value = numeric[-1] if len(numeric) > 1 and others == [] else numeric[0]
    time_cols = [c for c in cols if _is_time_col(df[c], c) and c != value]
    if time_cols:
        return line_chart(df.sort_values(time_cols[0]), time_cols[0], value, title)
    if others:
        label = others[0]
        df[label] = df[label].astype(str)
        if len(df) > 30:
            return None
        long_labels = df[label].str.len().max() > 12
        chart = hbar_chart if (len(df) > 6 or long_labels) else bar_chart
        return chart(df, label, value, title)
    if len(numeric) == 1 and len(df) > 10:
        return histogram(df, numeric[0], title)
    return None
