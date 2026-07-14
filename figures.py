"""Derive, verify, and render the classical cost figures."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from constants import BANDWIDTH_REFS, GIDNEY_2025, LATENCY_REFS, Spec
from style import (
    ACCENT,
    GRID,
    INK,
    LABEL_SIZE,
    NEUTRAL,
    RC,
    TICK_SIZE,
)

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "results"


def bill(spec: Spec) -> SimpleNamespace:
    """Derive every quantity the post quotes from a spec."""
    derived = SimpleNamespace()
    derived.runtime_s = spec.runtime_days * 86_400
    derived.rounds_per_s = 1e6 / spec.cycle_us

    # One measured qubit contributes one syndrome bit per round.
    derived.raw_bps = (
        spec.physical_qubits * spec.ancilla_fraction * derived.rounds_per_s
    )
    derived.sparse_bps = derived.raw_bps * spec.detection_fraction
    derived.total_bytes = derived.raw_bps * derived.runtime_s / 8

    # Surface-code patch: d^2 data qubits + (d^2 - 1) measure qubits.
    d = spec.code_distance
    derived.patch_qubits = 2 * d * d - 1
    derived.patches = spec.physical_qubits // derived.patch_qubits
    derived.patch_raw_bps = (d * d - 1) * derived.rounds_per_s
    derived.patch_sparse_bps = derived.patch_raw_bps * spec.detection_fraction

    # Decode cost at d, fitted through sparse blossom's two published anchors.
    # The paper reports no d=25 point, so extrapolate on its own terms: cost is
    # linear in node count and N ~ d^3, hence a power law in d (exponent ~3.2),
    # not the straight line between anchors. Linear interpolation would read
    # 2.54 us/round here — ~17% high, because the true curve is convex.
    (d_lo, t_lo), (d_hi, t_hi) = spec.decode_anchor_lo, spec.decode_anchor_hi
    derived.decode_exponent = math.log(t_hi / t_lo) / math.log(d_hi / d_lo)
    derived.us_per_round_per_patch = t_lo * (d / d_lo) ** derived.decode_exponent

    # Cores that keep decoding at the pace syndrome data is produced. Assumes
    # decode parallelises across patches with no overhead — an optimistic floor.
    derived.cores = derived.patches * derived.us_per_round_per_patch / spec.cycle_us

    # One logical time step is ~d rounds (Litinski, arXiv:1808.02892; quoted in
    # README "Sources"). Approximate by the paper's own admission, and it covers
    # only operations whose cost scales with d — initialization and
    # single-qubit measurement do not.
    derived.logical_clock_hz = 1e6 / (d * spec.cycle_us)
    return derived


def verify(derived: SimpleNamespace, spec: Spec) -> None:
    """Assert every number quoted in the post against *spec*."""

    def check(claim: str, computed: float, quoted: float, rel: float = 0.01) -> None:
        assert math.isclose(computed, quoted, rel_tol=rel), (
            f"FAIL {claim}: computed {computed:.4g}, post quotes {quoted:.4g}"
        )
        print(f"  ok  {claim:<58} {computed:.4g}  (quoted: {quoted:.4g})")

    print("Checking every number quoted in the post:")
    check("raw syndrome stream ~0.5 Tb/s", derived.raw_bps, 0.5e12)
    check("detection-event stream at 2% density, 10 Gb/s", derived.sparse_bps, 10e9)
    check("~27 PB of telemetry over the run", derived.total_bytes, 27e15)
    check(
        "telemetry-to-answer ratio, 14 orders of magnitude",
        math.log10(derived.total_bytes / spec.answer_bytes),
        14,
        rel=0.05,
    )
    check("raw syndrome per logical qubit, 624 Mb/s", derived.patch_raw_bps, 624e6)
    check(
        "'tens of Mbps per logical qubit' after sparsification",
        derived.patch_sparse_bps,
        12.5e6,
    )
    check("~800 uniform distance-25 patches", derived.patches, 800)
    check("sparse blossom scales ~d^3.2, not linearly", derived.decode_exponent, 3.24)
    check(
        "~2.2 µs/round/patch decode cost at d=25",
        derived.us_per_round_per_patch,
        2.2,
        rel=0.05,
    )
    check("~1,700 cores to keep decode pace", derived.cores, 1_700, rel=0.05)
    check(
        "logical clock near 40 kHz (d*cycle = 25 µs per op)",
        derived.logical_clock_hz,
        40e3,
    )
    check(
        "1 µs cycle ~ ten DRAM accesses",
        spec.cycle_us / dict(LATENCY_REFS)["DRAM access"],
        10,
    )

    # Qualitative comparisons made in the text.
    refs = dict(BANDWIDTH_REFS)
    assert derived.raw_bps > refs["400 GbE network port"], (
        "raw stream should exceed 400 GbE"
    )
    assert math.isclose(derived.raw_bps, refs["PCIe 5.0 x16 link"], rel_tol=0.05), (
        "raw stream should roughly saturate a PCIe 5.0 x16 link"
    )
    assert 1 / spec.detection_fraction > 10, (
        "sparsification should exceed an order of magnitude"
    )
    assert derived.patches * derived.patch_raw_bps <= derived.raw_bps, (
        "patches can't exceed the machine total"
    )
    print("  ok  raw stream > 400 GbE, ~ PCIe 5.0 x16; sparsification > 10x\n")


def save(fig: plt.Figure, stem: str) -> None:
    """Write a chart to OUT_DIR as a PNG."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png = OUT_DIR / f"{stem}.png"
    fig.savefig(png, facecolor="white")
    plt.close(fig)
    print(f"wrote {png}")


def si_bps(bps: float) -> str:
    """Format a bit rate with an SI-style Tb/Gb/Mb unit."""
    for cut, prefix in ((1e12, "Tb/s"), (1e9, "Gb/s"), (1e6, "Mb/s")):
        if bps >= cut:
            return f"{bps / cut:.3g} {prefix}"
    return f"{bps:g} b/s"


def bandwidth_chart(derived: SimpleNamespace, spec: Spec) -> None:
    """The syndrome stream next to interconnects engineers plan around."""
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
        # without hunting for its label. Shared visual system with the ladder.
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
        save(fig, "syndrome_bandwidth")


def latency_chart(spec: Spec) -> None:
    """Classical latency ladder vs. QEC timescales."""
    # Shape says whose number it is, because the ladder mixes two machines:
    # circle = Gidney's modelled machine (and the classical world), diamond =
    # Google's 72-qubit device. Google's 63 µs is not Gidney's machine and not a
    # deadline — it is an achieved measurement — so it gets its own mark.
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
        save(fig, "latency_ladder")


def main() -> None:
    """Run all checks and render both charts."""
    spec = GIDNEY_2025
    derived = bill(spec)
    verify(derived, spec)
    bandwidth_chart(derived, spec)
    latency_chart(spec)


if __name__ == "__main__":
    main()
