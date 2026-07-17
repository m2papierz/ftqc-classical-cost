"""Chart: break-even runtimes for polynomial speedups (Babbush et al. 2021).

Each row is a speedup degree against a level of classical parallelism; its two
dots are the same closed form evaluated at the paper's two primitives.  Nothing
is transcribed from their Table I -- every plotted value is recomputed from
Eq. 5 in model.breakeven and asserted against the table before rendering.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from constants import BABBUSH_2021, GIDNEY_2025, Breakeven
from model import DAY, HOUR, MIN, YEAR, breakeven, primitive_times, verify_breakeven
from style import ACCENT, GRID, INK, LABEL_SIZE, RC, TICK_SIZE, save

SCENARIOS: list[tuple[str, int, float]] = [
    ("quadratic, vs 1,000 cores", 2, 1e3),
    ("quadratic, vs 1 core", 2, 1.0),
    ("cubic, vs 1,000 cores", 3, 1e3),
    ("cubic, vs 1 core", 3, 1.0),
    ("quartic, vs 1,000 cores", 4, 1e3),
    ("quartic, vs 1 core", 4, 1.0),
]

_DURATION_UNITS: list[tuple[float, str]] = [
    (YEAR, "y"),
    (DAY, "d"),
    (HOUR, "h"),
    (MIN, "min"),
]

_TIME_TICKS: list[float] = [1, MIN, HOUR, DAY, YEAR, 1e3 * YEAR]
_TIME_LABELS: list[str] = ["1 s", "1 min", "1 hour", "1 day", "1 year", "1,000 y"]


def fmt_duration(seconds: float) -> str:
    """Format a duration in the largest unit that keeps the number short."""
    for threshold, suffix in _DURATION_UNITS:
        if seconds >= threshold:
            value = seconds / threshold
            return f"{value:,.0f} {suffix}" if value >= 10 else f"{value:.1f} {suffix}"
    return f"{seconds:.0f} s"


def _compute_rows(model: Breakeven) -> list[tuple[str, float, float]]:
    """Return ``(label, lb_time, sa_time)`` for each scenario, sorted by SA time."""
    rows: list[tuple[str, float, float]] = []
    for label, degree, s in SCENARIOS:
        lb = breakeven(*primitive_times(model, "lb"), degree, s)
        sa = breakeven(*primitive_times(model, "sa"), degree, s)
        rows.append((label, lb, sa))
    rows.sort(key=lambda r: r[2])
    return rows


def _plot(rows: list[tuple[str, float, float]], rsa_s: float) -> Figure:
    """Draw the break-even ladder and return the figure.

    Open dot = optimistic "lower bound" floor;
    filled dot = compiled simulated-annealing instance.
    """
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        ax.set_xscale("log")
        floor = min(lb for _, lb, _ in rows) / 3
        ax.set_xlim(floor, max(sa for _, _, sa in rows) * 6)

        for x in _TIME_TICKS:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        _draw_rows(ax, rows)
        _draw_rsa_line(ax, rsa_s)
        _style_axes(ax, rows)

        fig.tight_layout()
    return fig


def _draw_rows(ax: plt.Axes, rows: list[tuple[str, float, float]]) -> None:
    """Plot each scenario as a span between its LB and SA dots."""
    for y, (_, lb, sa) in enumerate(rows):
        ax.hlines(y, lb, sa, color=GRID, lw=1.2, zorder=1)
        ax.plot(lb, y, "o", ms=8, mfc="white", mec=ACCENT, mew=1.6, zorder=3)
        ax.plot(sa, y, "o", ms=8, color=ACCENT, zorder=3)
        for value in (lb, sa):
            ax.annotate(
                fmt_duration(value),
                (value, y),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=LABEL_SIZE,
                color=INK,
            )


def _draw_rsa_line(ax: plt.Axes, rsa_s: float) -> None:
    """Add the dashed vertical reference line for Gidney's RSA-2048 runtime."""
    ax.axvline(rsa_s, color=INK, lw=1.0, ls="--", zorder=2)
    ax.annotate(
        f"the RSA-2048 run ({GIDNEY_2025.runtime_days:g} days)",
        (rsa_s, 1.5),
        xytext=(5, 0),
        textcoords="offset points",
        fontsize=TICK_SIZE + 1.0,
        color=INK,
    )


def _style_axes(ax: plt.Axes, rows: list[tuple[str, float, float]]) -> None:
    """Configure ticks, labels, legend, and spines."""
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([label for label, _, _ in rows], fontsize=TICK_SIZE)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xticks(_TIME_TICKS)
    ax.set_xticklabels(_TIME_LABELS)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("break-even runtime before any quantum advantage (log scale)")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)

    ax.legend(
        handles=[
            plt.Line2D(
                [],
                [],
                marker="o",
                ls="",
                ms=7,
                color=ACCENT,
                label="simulated annealing, N=512 (compiled)",
            ),
            plt.Line2D(
                [],
                [],
                marker="o",
                ls="",
                ms=7,
                mfc="white",
                mec=ACCENT,
                mew=1.6,
                label='"lower bound" primitive (100 Toffolis)',
            ),
        ],
        loc="lower right",
        frameon=False,
        fontsize=TICK_SIZE,
        handletextpad=0.5,
    )
    ax.set_title(
        "How long the machine must run before a polynomial speedup pays",
        loc="left",
        pad=12,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "out_dir",
        nargs="?",
        type=Path,
        default=_PROJECT_ROOT / "results",
        help="directory for the output PNG (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    model = BABBUSH_2021
    verify_breakeven(model)

    rows = _compute_rows(model)
    rsa_s = GIDNEY_2025.runtime_days * DAY
    fig = _plot(rows, rsa_s)
    save(fig, "breakeven_ladder", args.out_dir)
    plt.close(fig)


if __name__ == "__main__":
    main()
