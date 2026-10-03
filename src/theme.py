"""
theme.py
--------
One place for the app's colours, so the dashboard, charts and CSS all match.
"""

BG = "#160C08"          # page background
CARD = "#22130D"        # card / panel background
CARD_2 = "#2B1810"      # raised elements inside cards
BORDER = "#3A2219"
TEXT = "#F4E9E3"
MUTED = "#B89D90"
COPPER = "#E07A5F"      # main accent
COPPER_DARK = "#C9603F"
PEACH = "#F6BBA3"       # lighter bars
GREEN = "#4ADE80"
RED = "#F87171"


def blend(c1: str, c2: str, t: float) -> str:
    """Mix two hex colours. t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"
