"""Palette, typography, and Matplotlib rc for both charts."""

# Two hues carry meaning; the rest are tokens for text and lines.
ACCENT = "#C2410C"  # quantum items
NEUTRAL = "#94A3B8"  # classical reference points
INK = "#1E293B"
GRID = "#CBD5E1"  # recessive decade gridlines, shared by both charts

TITLE_SIZE = 12.5
LABEL_SIZE = 10.5  # data-point / bar labels
TICK_SIZE = 9.5

RC = {
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": TITLE_SIZE,
    "axes.labelsize": 11,
    "xtick.labelsize": TICK_SIZE,
    "ytick.labelsize": LABEL_SIZE,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "figure.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.dpi": 200,
}
