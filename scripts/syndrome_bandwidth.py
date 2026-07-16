"""Chart: the syndrome stream next to interconnects engineers plan around.

Verifies the full classical cost model (this is the cost model's chart), then renders.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from constants import BANDWIDTH_REFS, GIDNEY_2025
from model import derive_classical_costs, verify_classical_costs
from style import ACCENT, GRID, INK, LABEL_SIZE, NEUTRAL, RC, save


def si_bps(bps: float) -> str:
    """Format a bit rate with an SI-style Tb/Gb/Mb unit."""
    for cut, prefix in ((1e12, "Tb/s"), (1e9, "Gb/s"), (1e6, "Mb/s")):
        if bps >= cut:
            return f"{bps / cut:.3g} {prefix}"
    return f"{bps:g} b/s"


def main() -> None:
    out_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parent.parent / "results"
    )
    spec = GIDNEY_2025
    derived = derive_classical_costs(spec)
    verify_classical_costs(derived, spec)

    # One neutral hue for classical references, one accent hue for quantum items.
    entries = [(label, bps, NEUTRAL) for label, bps in BANDWIDTH_REFS]
    entries += [
        (
            f"Full machine, raw syndrome ({spec.physical_qubits:,.0f} qubits)",
            derived.raw_bps,
            ACCENT,
        ),
        (
            f"Full machine, detection events (~{spec.detection_fraction:.0%} fire rate)",
            derived.sparse_bps,
            ACCENT,
        ),
        (
            f"One logical qubit (d={spec.code_distance}), raw syndrome",
            derived.patch_raw_bps,
            ACCENT,
        ),
        (
            f"One logical qubit (d={spec.code_distance}), detection events",
            derived.patch_sparse_bps,
            ACCENT,
        ),
    ]
    entries.sort(key=lambda e: e[1])

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        labels, values, colors = zip(*entries)
        ax.set_xscale("log")
        ax.set_xlim(min(values) / 3, max(values) * 4)

        # Recessive decade gridlines: let a bar tip be read against the scale
        # without hunting for its label. Shared visual system with the ladders.
        decades = [1e7, 1e8, 1e9, 1e10, 1e11, 1e12, 1e13]
        for x in decades:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        bars = ax.barh(
            labels,
            values,
            color=colors,
            height=0.62,
            edgecolor="white",
            linewidth=0.8,
            zorder=2,
        )
        # The value rides every bar tip. On a log axis a bar's length is set by
        # the axis floor rather than by the data, so length must never be the
        # only channel: the label is what the reader actually reads the value
        # from, and the decade lines place it.
        for bar, value in zip(bars, values):
            ax.text(
                value * 1.18,
                bar.get_y() + bar.get_height() / 2,
                si_bps(value),
                va="center",
                fontsize=LABEL_SIZE,
                color=INK,
            )
        ax.set_xticks(decades)
        ax.set_xticklabels(
            [
                "10 Mb/s",
                "100 Mb/s",
                "1 Gb/s",
                "10 Gb/s",
                "100 Gb/s",
                "1 Tb/s",
                "10 Tb/s",
            ]
        )
        ax.set_xlabel("sustained data rate (log scale)")
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.set_title(
            "Sustained syndrome bandwidth vs. classical interconnects",
            loc="left",
            pad=12,
        )
        fig.tight_layout()
        save(fig, "syndrome_bandwidth", out_dir)
        plt.close(fig)


if __name__ == "__main__":
    main()
