"""
layout.py
---------
Auto-arrange helpers. Every uploaded file has different columns, so some
dashboard panels may have nothing to show (no country column, no product
column, no correlations...). Instead of drawing an empty card, the page asks
auto_columns() for space only for the panels that have content:

    left, right = auto_columns([has_trend, has_countries], [1.45, 1])

  - hidden panels get None (skip them with `if left:`)
  - the visible panels share the full width, keeping their relative sizes
  - a single visible panel stretches across the whole row
So the dashboard always looks tidy and screenshot-ready, whatever the file.
"""

import streamlit as st

# Widgets whose saved choice belongs to one dataset. They are reset when a new
# file is loaded so the page starts from clean defaults for the new data.
DATASET_WIDGET_KEYS = ["f_period", "f_country", "trend_metric", "country_metric", "product_metric", "dist_col"]


def auto_columns(visible: list[bool], weights: list[float] | None = None, gap: str = "medium"):
    """Return one slot per panel: a Streamlit column if visible, else None."""
    weights = weights or [1] * len(visible)
    shown = [w for w, v in zip(weights, visible) if v]
    if not shown:
        return [None] * len(visible)
    cols = iter(st.columns(shown, gap=gap) if len(shown) > 1 else [st.container()])
    return [next(cols) if v else None for v in visible]


def available(options: dict[str, bool]) -> list[str]:
    """Keep only the dropdown options this dataset can actually answer."""
    return [name for name, ok in options.items() if ok]


def arrange(panels: list[tuple[str, bool, float]], per_row: int = 2, gap: str = "medium") -> dict:
    """
    Pack the visible panels, in their original order, into rows of `per_row`.
    panels: [(name, visible, width_weight), ...]  ->  {name: column or None}
    With every panel present you get the normal layout; when the new file
    can't fill some panels they are dropped and the rest close the gaps.
    """
    shown = [(n, w) for n, v, w in panels if v]
    slots = {n: None for n, _, _ in panels}
    for i in range(0, len(shown), per_row):
        row = shown[i:i + per_row]
        for (name, _), col in zip(row, auto_columns([True] * len(row), [w for _, w in row], gap)):
            slots[name] = col
    return slots
