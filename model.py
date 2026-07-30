"""Derivations and their verification against the published figures.

Two independent models: the classical cost of Gidney's RSA-2048 run
(derive_classical_costs / verify_classical_costs) and the break-even times for
polynomial speedups from Babbush et al. 2021 (breakeven / verify_breakeven).
Run as a script, both verification suites execute and nothing is rendered.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

from constants import (
    BABBUSH_2021,
    BANDWIDTH_REFS,
    GIDNEY_2025,
    LATENCY_REFS,
    Breakeven,
    Spec,
)

MIN, HOUR, DAY, YEAR = 60.0, 3600.0, 86400.0, 365.25 * 86400.0


def check(claim: str, computed: float, quoted: float, rel: float = 0.01) -> None:
    """Assert a computed value against its published counterpart, printing both."""
    assert math.isclose(computed, quoted, rel_tol=rel), (
        f"FAIL {claim}: computed {computed:.4g}, quoted {quoted:.4g}"
    )
    print(f"  ok  {claim:<58} {computed:.4g}  (quoted: {quoted:.4g})")


def derive_classical_costs(spec: Spec) -> SimpleNamespace:
    """Derive the classical cost quantities from *spec*.

    Rates are bits per second, byte totals bytes, decode cost microseconds per
    round per patch, logical clock hertz.
    """
    derived = SimpleNamespace()
    derived.runtime_s = spec.runtime_days * 86_400
    derived.rounds_per_s = 1e6 / spec.cycle_us

    # One measured qubit contributes one syndrome bit per round.
    derived.raw_bps = (
        spec.physical_qubits * spec.ancilla_fraction * derived.rounds_per_s
    )
    derived.sparse_bps = derived.raw_bps * spec.detection_fraction
    derived.total_bytes = derived.raw_bps * derived.runtime_s / 8

    # Rotated patch: d^2 data qubits + (d^2 - 1) measure qubits.
    d = spec.code_distance
    derived.patch_qubits = 2 * d * d - 1
    derived.patches = spec.physical_qubits // derived.patch_qubits
    derived.patch_raw_bps = (d * d - 1) * derived.rounds_per_s
    derived.patch_sparse_bps = derived.patch_raw_bps * spec.detection_fraction

    # Sparse blossom publishes no d=25 point, so interpolate its two anchors as
    # a power law on log-log axes (exponent ~3.2). Empirical: it asserts no
    # scaling law of its own. Linear interpolation would read 2.54 us/round.
    (d_lo, t_lo), (d_hi, t_hi) = spec.decode_anchor_lo, spec.decode_anchor_hi
    derived.decode_exponent = math.log(t_hi / t_lo) / math.log(d_hi / d_lo)
    derived.us_per_round_per_patch = t_lo * (d / d_lo) ** derived.decode_exponent

    # Cores that keep decode pace with syndrome production, assuming decode
    # parallelises across patches with no overhead.
    derived.cores = derived.patches * derived.us_per_round_per_patch / spec.cycle_us

    # One logical time step is ~d rounds (Litinski, arXiv:1808.02892), approximate
    # by that paper's own caveat and covering only operations that scale with d.
    derived.logical_clock_hz = 1e6 / (d * spec.cycle_us)
    return derived


def verify_classical_costs(derived: SimpleNamespace, spec: Spec) -> None:
    """Assert the classical cost derivation for *spec* against the published figures."""
    print("Checking the classical cost model:")
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
        "detection events per logical qubit, 12.5 Mb/s",
        derived.patch_sparse_bps,
        12.5e6,
    )
    check("~800 uniform distance-25 patches", derived.patches, 800)
    check(
        "decode cost exponent from the two anchors, ~3.2", derived.decode_exponent, 3.24
    )
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


def breakeven(t_q: float, t_c: float, degree: int, s: float) -> float:
    """Break-even runtime T* in seconds, Babbush et al. 2021 Eq. 3 (S=1) and Eq. 5.

    t_q and t_c are quantum and classical primitive-call times in seconds,
    degree the polynomial degree of the speedup, s the classical parallel
    speedup factor (their S).
    """
    return t_q * (t_q * s / t_c) ** (1.0 / (degree - 1))


# Babbush et al. 2021 Table I as printed, to 2 significant figures. Charts
# recompute from the closed form; these rows pin the recomputation.
# Columns: primitive ("lb" / "sa"), degree, S, printed value in seconds.
TABLE_I = [
    ("lb", 2, 1.0, 2.4 * HOUR),
    ("lb", 2, 1e3, 100 * DAY),
    ("sa", 2, 1.0, 320 * DAY),
    ("sa", 2, 1e3, 880 * YEAR),
    ("lb", 3, 1.0, 12.0),
    ("lb", 3, 1e3, 6.4 * MIN),
    ("sa", 3, 1.0, 58 * MIN),
    ("sa", 3, 1e3, 1.3 * DAY),
    ("lb", 4, 1.0, 1.4),
    ("lb", 4, 1e3, 14.0),
    ("sa", 4, 1.0, 2.9 * MIN),
    ("sa", 4, 1e3, 29 * MIN),
]


def primitive_times(model: Breakeven, primitive: str) -> tuple[float, float]:
    """(t_q, t_c) in seconds for a named primitive: "lb" or "sa"."""
    return {
        "lb": (model.lb_quantum_s, model.lb_classical_s),
        "sa": (model.sa_quantum_s, model.sa_classical_s),
    }[primitive]


def verify_breakeven(model: Breakeven) -> None:
    """Assert the recomputed break-even times against Babbush et al. 2021."""
    print("Checking the break-even ladder against Babbush et al. (2021):")
    # Table I prints 2 significant figures; observed max deviation is 2.7%.
    for primitive, degree, s, printed in TABLE_I:
        t_q, t_c = primitive_times(model, primitive)
        check(
            f"Table I: {primitive}, degree {degree}, S = {s:g}",
            breakeven(t_q, t_c, degree, s),
            printed,
            rel=0.05,
        )

    # Prose example: P = 3,000 CPUs (S ~ P) against the 100-Toffoli primitive.
    # The paper calls the result one year; recomputed it is 304 days.
    check(
        "prose: lower bound vs 3,000 cores, ~ten months ('one year')",
        breakeven(model.lb_quantum_s, model.lb_classical_s, 2, 3e3),
        304 * DAY,
        rel=0.02,
    )
    # Table II (Eq. 12): an R-fold distillation speedup divides the quadratic
    # break-even by R^2. At R = 10, S = 1e3 the table prints 8.8 years.
    check(
        "Table II: sa, degree 2, S = 1e3, distillation speedup R = 10",
        breakeven(model.sa_quantum_s, model.sa_classical_s, 2, 1e3) / 10**2,
        8.8 * YEAR,
        rel=0.05,
    )
    print()


if __name__ == "__main__":
    verify_classical_costs(derive_classical_costs(GIDNEY_2025), GIDNEY_2025)
    verify_breakeven(BABBUSH_2021)
