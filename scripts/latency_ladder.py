"""Chart: classical latency ladder vs. QEC timescales.

Draws inputs verbatim (nothing derived), so there is no verify step here;
the quoted comparisons around these numbers are asserted in model.verify_classical_costs.
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

from constants import GIDNEY_2025, LATENCY_REFS, Spec
from style import ACCENT, GRID, INK, NEUTRAL, RC, TICK_SIZE, save

# Shape encodes the source machine: circle = Gidney's model or classical,
# diamond = Google's 72-qubit device (an achieved measurement, not a deadline).
KINDS: dict[str, tuple[str, str, str]] = {
    "classical": (NEUTRAL, "o", "classical reference point"),
    "deadline": (ACCENT, "o", "QEC deadline (Gidney's machine)"),
    "demonstrated": (ACCENT, "D", "demonstrated (Google, d=5, 72 qubits)"),
}

_DECADE_TICKS: list[float] = [0.1, 1, 10, 100, 1000]


def _build_rows(spec: Spec) -> list[tuple[str, float, str]]:
    """Merge classical reference latencies with QEC deadlines, sorted by time."""
    return sorted(
        [(label, us, "classical") for label, us in LATENCY_REFS]
        + [
            ("syndrome cycle", spec.cycle_us, "deadline"),
            ("reaction-time budget", spec.reaction_us, "deadline"),
            (
                f"demonstrated decode (d={spec.demonstrated_distance})",
                spec.demonstrated_latency_us,
                "demonstrated",
            ),
        ],
        key=lambda r: r[1],
    )


def _plot(rows: list[tuple[str, float, str]]) -> Figure:
    """Draw the latency ladder and return the figure."""
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        ax.set_xscale("log")
        floor = min(us for _, us, _ in rows) / 3
        ax.set_xlim(floor, max(us for _, us, _ in rows) * 3)

        for x in _DECADE_TICKS:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        _draw_rows(ax, rows, floor)
        _style_axes(ax, rows)

        fig.tight_layout()
    return fig


def _draw_rows(
    ax: plt.Axes,
    rows: list[tuple[str, float, str]],
    floor: float,
) -> None:
    """Plot each latency as a rail from the axis floor to its dot."""
    for y, (_, us, kind) in enumerate(rows):
        colour, marker, _ = KINDS[kind]
        ax.hlines(y, floor, us, color=GRID, lw=1.0, zorder=1)
        ax.plot(
            us,
            y,
            marker=marker,
            ls="",
            ms=7 if marker == "D" else 8,
            zorder=3,
            color=colour,
        )


def _style_axes(ax: plt.Axes, rows: list[tuple[str, float, str]]) -> None:
    """Configure ticks, labels, legend, and spines."""
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(
        [f"{label}   {us:g} µs" for label, us, _ in rows],
        fontsize=TICK_SIZE,
    )
    # Tick labels wear their dot's hue -- ACCENT on white clears WCAG AA (~5.9:1).
    for tick, (_, _, kind) in zip(ax.get_yticklabels(), rows):
        tick.set_color(INK if kind == "classical" else ACCENT)

    ax.legend(
        handles=[
            plt.Line2D(
                [],
                [],
                marker=m,
                ls="",
                ms=6 if m == "D" else 7,
                color=c,
                label=t,
            )
            for c, m, t in KINDS.values()
        ],
        loc="lower right",
        frameon=False,
        fontsize=TICK_SIZE,
        handletextpad=0.5,
    )

    ax.set_xticks(_DECADE_TICKS)
    ax.set_xticklabels(["0.1", "1", "10", "100", "1000"])
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("time (µs, log scale)")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_title("Classical latencies vs. QEC timescales", loc="left", pad=12)


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

    rows = _build_rows(GIDNEY_2025)
    fig = _plot(rows)
    save(fig, "latency_ladder", args.out_dir)
    plt.close(fig)


if __name__ == "__main__":
    main()
