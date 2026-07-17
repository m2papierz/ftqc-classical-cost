"""Chart: the syndrome stream next to interconnects engineers plan around.

Verifies the full classical cost model (this is the cost model's chart), then renders.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from constants import BANDWIDTH_REFS, GIDNEY_2025, Spec
from model import derive_classical_costs, verify_classical_costs
from style import ACCENT, GRID, INK, LABEL_SIZE, NEUTRAL, RC, save

_BITRATE_UNITS: list[tuple[float, str]] = [
    (1e12, "Tb/s"),
    (1e9, "Gb/s"),
    (1e6, "Mb/s"),
]

_DECADE_TICKS: list[float] = [1e7, 1e8, 1e9, 1e10, 1e11, 1e12, 1e13]
_DECADE_LABELS: list[str] = [
    "10 Mb/s",
    "100 Mb/s",
    "1 Gb/s",
    "10 Gb/s",
    "100 Gb/s",
    "1 Tb/s",
    "10 Tb/s",
]


def format_bitrate(bps: float) -> str:
    """Format a bit rate with an SI-style Tb/Gb/Mb unit."""
    for threshold, unit in _BITRATE_UNITS:
        if bps >= threshold:
            return f"{bps / threshold:.3g} {unit}"
    return f"{bps:g} b/s"


def _build_entries(
    spec: Spec,
    derived: SimpleNamespace,
) -> list[tuple[str, float, str]]:
    """Merge classical bandwidth references with derived syndrome rates, sorted."""
    entries: list[tuple[str, float, str]] = [
        (label, bps, NEUTRAL) for label, bps in BANDWIDTH_REFS
    ]
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
    return entries


def _plot(entries: list[tuple[str, float, str]]) -> Figure:
    """Draw the syndrome bandwidth chart and return the figure."""
    labels, values, colors = zip(*entries)

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(9, 4.0))
        ax.set_xscale("log")
        ax.set_xlim(min(values) / 3, max(values) * 4)

        for x in _DECADE_TICKS:
            ax.axvline(x, color=GRID, lw=0.7, zorder=0)

        _draw_bars(ax, labels, values, colors)
        _style_axes(ax)

        fig.tight_layout()
    return fig


def _draw_bars(
    ax: plt.Axes,
    labels: tuple[str, ...],
    values: tuple[float, ...],
    colors: tuple[str, ...],
) -> None:
    """Draw horizontal bars with bit-rate labels at each tip."""
    bars = ax.barh(
        labels,
        values,
        color=colors,
        height=0.62,
        edgecolor="white",
        linewidth=0.8,
        zorder=2,
    )
    for bar, value in zip(bars, values):
        ax.text(
            value * 1.18,
            bar.get_y() + bar.get_height() / 2,
            format_bitrate(value),
            va="center",
            fontsize=LABEL_SIZE,
            color=INK,
        )


def _style_axes(ax: plt.Axes) -> None:
    """Configure ticks, labels, and spines."""
    ax.set_xticks(_DECADE_TICKS)
    ax.set_xticklabels(_DECADE_LABELS)
    ax.set_xlabel("sustained data rate (log scale)")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(
        "Sustained syndrome bandwidth vs. classical interconnects",
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

    spec = GIDNEY_2025
    derived = derive_classical_costs(spec)
    verify_classical_costs(derived, spec)

    entries = _build_entries(spec, derived)
    fig = _plot(entries)
    save(fig, "syndrome_bandwidth", args.out_dir)
    plt.close(fig)


if __name__ == "__main__":
    main()
