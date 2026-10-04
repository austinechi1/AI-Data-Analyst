"""
theme.py
--------
One place for the app's colours, so the dashboard, charts and CSS all match.
Light canvas, espresso sidebar, white cards and a coral accent.
"""

BG = "#ECECEC"          # page background
CARD = "#FFFFFF"        # card / panel background
CARD_2 = "#F5F3F2"      # raised elements inside cards
BORDER = "#E2DFDC"
TEXT = "#1E1A18"
MUTED = "#8C8682"
COPPER = "#D9785A"      # main accent (coral)
COPPER_DARK = "#C2603F"
PEACH = "#D6D2CF"       # soft grey used for the smaller bars
GREEN = "#22C55E"
RED = "#DC2626"


def blend(c1: str, c2: str, t: float) -> str:
    """Mix two hex colours. t=0 gives c1, t=1 gives c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rgba(hex_color: str, alpha: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"
