"""Chart: classical latency ladder vs. QEC timescales.

Draws inputs verbatim (nothing derived), so there is no verify step here;
the quoted comparisons around these numbers are asserted in model.verify_bill.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from constants import GIDNEY_2025, LATENCY_REFS
from style import ACCENT, GRID, INK, NEUTRAL, RC, TICK_SIZE, save


def main() -> None:
    out_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "results"
    )
    spec = GIDNEY_2025

    # Shape says whose number it is, because the ladder mixes two machines:
    # circle = Gidney's modelled machine (and the classical world), diamond =
    # Google's 72-qubit device. Google's 63 µs is not Gidney's machine and not a
    # deadline -- it is an achieved measurement -- so it gets its own mark.
    #
    # Every dot here answers the same question: what must happen by when, and
    # what has anyone actually hit? T1 used to sit at 68 µs and answered
    # neither, while landing 8% from the 63 µs dot and inviting a race that
    # does not exist. It lives in README "Model" as prose instead.
    KINDS = {  # kind -> (colour, marker, legend label)
        "classical": (NEUTRAL, "o", "classical reference point"),
        "deadline": (ACCENT, "o", "QEC deadline (Gidney's machine)"),
        "demonstrated": (ACCENT, "D", "demonstrated (Google, d=5, 72 qubits)"),
    }
    rows = sorted(
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

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        ax.set_xscale("log")
        floor = min(us for _, us, _ in rows) / 3
        ax.set_xlim(floor, max(us for _, us, _ in rows) * 3)

        decades = [0.1, 1, 10, 100, 1000]
        for x in decades:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        for y, (_, us, kind) in enumerate(rows):
            colour, marker, _ = KINDS[kind]
            ax.hlines(y, floor, us, color=GRID, lw=1.0, zorder=1)
            ax.plot(
                us,
                y,
                marker=marker,
                ls="",
                ms=7 if marker == "D" else 8,  # equalise the two markers' area
                zorder=3,
                color=colour,
            )

        # Each value rides its own y-tick label: a number floating beside every
        # dot is noise, and the left column right-aligns them for free.
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(
            [f"{label}   {us:g} µs" for label, us, _ in rows], fontsize=TICK_SIZE
        )
        # Tick labels take their dot's hue. A deliberate departure from "text
        # never wears the data colour": that rule assumes the coloured mark sits
        # beside the text, but here the dot is a rail's width away, so the left
        # column would otherwise lose identity entirely. ACCENT on white clears
        # WCAG AA (~5.9:1), which is the concern the rule exists to protect.
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

        ax.set_xticks(decades)
        ax.set_xticklabels(["0.1", "1", "10", "100", "1000"])
        ax.set_ylim(-0.7, len(rows) - 0.3)
        ax.tick_params(axis="y", length=0)
        ax.set_xlabel("time (µs, log scale)")
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.set_title("Classical latencies vs. QEC timescales", loc="left", pad=12)
        fig.tight_layout()
        save(fig, "latency_ladder", out_dir)
        plt.close(fig)


if __name__ == "__main__":
    main()
