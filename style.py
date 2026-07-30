"""Palette, typography, Matplotlib rc, and the PNG writer shared by all charts."""

from pathlib import Path

ACCENT = "#C2410C"  # quantum items
NEUTRAL = "#94A3B8"  # classical reference points
INK = "#1E293B"  # text, spines, ticks
GRID = "#CBD5E1"  # decade gridlines

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


def save(fig, stem: str, out_dir: Path) -> None:
    """Write *fig* to out_dir/<stem>.png, creating the directory if needed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    fig.savefig(png, facecolor="white")
    print(f"wrote {png}")
