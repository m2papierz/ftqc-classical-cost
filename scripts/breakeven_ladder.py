"""Chart: break-even runtimes for polynomial speedups (Babbush et al. 2021).

Each row is a speedup degree against a level of classical parallelism; its two
dots are the same closed form evaluated at the paper's two primitives. Nothing
is transcribed from their Table I -- every plotted value is recomputed from
Eq. 5 in model.breakeven and asserted against the table before rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from constants import BABBUSH_2021, GIDNEY_2025
from model import DAY, HOUR, MIN, YEAR, breakeven, primitive_times, verify_breakeven
from style import ACCENT, GRID, INK, LABEL_SIZE, RC, TICK_SIZE, save

SCENARIOS = [  # (row label, polynomial degree, classical parallel speedup S)
    ("quadratic, vs 1,000 cores", 2, 1e3),
    ("quadratic, vs 1 core", 2, 1.0),
    ("cubic, vs 1,000 cores", 3, 1e3),
    ("cubic, vs 1 core", 3, 1.0),
    ("quartic, vs 1,000 cores", 4, 1e3),
    ("quartic, vs 1 core", 4, 1.0),
]


def fmt(seconds: float) -> str:
    """Format a duration in the largest unit that keeps the number short."""
    for unit, name in ((YEAR, "y"), (DAY, "d"), (HOUR, "h"), (MIN, "min")):
        if seconds >= unit:
            v = seconds / unit
            return f"{v:,.0f} {name}" if v >= 10 else f"{v:.1f} {name}"
    return f"{seconds:.0f} s"


def main() -> None:
    out_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "results"
    )
    model = BABBUSH_2021
    verify_breakeven(model)

    # Two dots per row, one per primitive; both are quantum break-even times,
    # so both wear ACCENT and fill tells them apart: open = the paper's
    # optimistic "lower bound" floor, filled = the compiled simulated-annealing
    # instance. Sorting ascending on the filled dot also groups by degree.
    rows = sorted(
        (
            (
                label,
                *(
                    breakeven(*primitive_times(model, p), degree, s)
                    for p in ("lb", "sa")
                ),
            )
            for label, degree, s in SCENARIOS
        ),
        key=lambda r: r[2],
    )
    # The one number of Gidney's machine that lives on this axis: how long the
    # flagship RSA-2048 factoring run actually takes. Everything above the line
    # would need to outlast that entire run before breaking even once.
    rsa_s = GIDNEY_2025.runtime_days * DAY

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        ax.set_xscale("log")
        floor = min(lb for _, lb, _ in rows) / 3
        ax.set_xlim(floor, max(sa for _, _, sa in rows) * 6)

        ticks = [1, MIN, HOUR, DAY, YEAR, 1e3 * YEAR]
        for x in ticks:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        for y, (_, lb, sa) in enumerate(rows):
            ax.hlines(y, lb, sa, color=GRID, lw=1.2, zorder=1)
            ax.plot(lb, y, "o", ms=8, mfc="white", mec=ACCENT, mew=1.6, zorder=3)
            ax.plot(sa, y, "o", ms=8, color=ACCENT, zorder=3)
            for value in (lb, sa):  # value labels are text, so they wear INK
                ax.annotate(
                    fmt(value),
                    (value, y),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=LABEL_SIZE,
                    color=INK,
                )

        ax.axvline(rsa_s, color=INK, lw=1.0, ls="--", zorder=2)
        ax.annotate(
            f"the RSA-2048 run ({GIDNEY_2025.runtime_days:g} days)",
            (rsa_s, 1.5),
            xytext=(5, 0),
            textcoords="offset points",
            fontsize=TICK_SIZE + 1.0,
            color=INK,
        )

        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([label for label, _, _ in rows], fontsize=TICK_SIZE)
        ax.set_ylim(-0.8, len(rows) - 0.2)
        ax.set_xticks(ticks)
        ax.set_xticklabels(["1 s", "1 min", "1 hour", "1 day", "1 year", "1,000 y"])
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
        fig.tight_layout()
        save(fig, "breakeven_ladder", out_dir)
        plt.close(fig)


if __name__ == "__main__":
    main()
