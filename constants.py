"""Pinned inputs: machine spec, decoder anchors, break-even primitive times, reference points.

Comments give the citation; README "Sources" gives the verbatim basis for each value.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    """Uniform distance-25 stand-in for the RSA-2048 machine of Gidney 2025 (arXiv:2505.15917)."""

    # Components sum to 897,864; Gidney 2025 §3.2 reports one million for slack.
    physical_qubits: int = 1_000_000
    cycle_us: float = 1.0  # Gidney 2025 abstract
    # Gidney 2025 abstract; the term is inherited and never defined there.
    reaction_us: float = 10.0
    runtime_days: float = 5.0  # Gidney 2025 §3.2: 4.96 days per factoring
    answer_bytes: int = 256  # RSA-2048 factorization: two 1024-bit primes

    # A rotated patch is d^2 data + (d^2 - 1) measure qubits, so ~1/2. Applied
    # machine-wide this is an upper bound: routing space is unmeasured.
    ancilla_fraction: float = 0.5
    code_distance: int = 25  # Gidney 2025 §3.2; hot storage and compute region
    # Stim rotated_memory_z, uniform depolarizing p=0.1%, bulk detectors, d=25:
    # 1.86%, rounded. Google's measured 8.5% is a noisier regime (SI1000).
    detection_fraction: float = 0.02

    # Single-core sparse blossom, (distance, microseconds per round per patch).
    # Higgott & Gidney 2025 (arXiv:2303.15933) §6 and §1. No d=25 point is
    # published, so derive_classical_costs() fits a power law through these two.
    decode_anchor_lo: tuple[int, float] = (17, 0.62)
    decode_anchor_hi: tuple[int, float] = (29, 3.5)

    # Google Quantum AI, Nature 638, 920 (2025): 63 +/- 17 us mean decoder
    # latency on the 72-qubit processor. Decode time only, no feedback into the
    # logical circuit, so it is not a reaction time.
    demonstrated_distance: int = 5
    demonstrated_latency_us: float = 63.0

    def __post_init__(self) -> None:
        assert self.physical_qubits > 0 and self.answer_bytes > 0
        assert self.code_distance >= 3
        assert 0 < self.ancilla_fraction <= 1 and 0 < self.detection_fraction <= 1
        assert self.decode_anchor_lo[0] < self.decode_anchor_hi[0]
        assert (
            min(
                self.cycle_us,
                self.reaction_us,
                self.runtime_days,
                self.demonstrated_latency_us,
                *self.decode_anchor_lo,
                *self.decode_anchor_hi,
            )
            > 0
        )


GIDNEY_2025 = Spec()


@dataclass(frozen=True)
class Breakeven:
    """Primitive-call times of Babbush et al. 2021 (arXiv:2011.04149), in seconds.

    Their model: classical solves in M^degree calls to a classical primitive,
    quantum in M calls to a quantum one. Their "d" is the polynomial degree of
    the speedup; this repo reserves d for code distance and calls it `degree`.
    """

    # Eq. 6: 5.5*d cycles per Toffoli at d near 30 and ~1 us per round gives
    # 165 us; the paper rounds to 170 and computes everything downstream from it.
    toffoli_s: float = 170e-6

    # Eq. 8: 100 Toffolis, the paper's floor on a primitive worth accelerating.
    lb_quantum_s: float = 17e-3
    # Eq. 10: 3 GHz CPU, one clock cycle per Toffoli, L = 100.
    lb_classical_s: float = 33e-9

    # Eq. 9: one N=512 Sherrington-Kirkpatrick update in the compilation of
    # Sanders et al., PRX Quantum 1, 020312 (2020).
    sa_toffolis: float = 2.6e3
    sa_quantum_s: float = 440e-3
    # Eq. 11: classical simulated-annealing step for the same instance,
    # rejected updates included (Isakov et al. 2015, quoted via Sanders et al.).
    sa_classical_s: float = 7e-9

    def __post_init__(self) -> None:
        assert min(vars(self).values()) > 0
        # The quoted times are round-offs of Toffoli count times gate time.
        assert abs(5.5 * 30 * 1e-6 - self.toffoli_s) / self.toffoli_s < 0.04
        assert abs(100 * self.toffoli_s - self.lb_quantum_s) < 1e-12
        rel = abs(self.sa_toffolis * self.toffoli_s - self.sa_quantum_s)
        assert rel / self.sa_quantum_s < 0.01


BABBUSH_2021 = Breakeven()

# Commodity-hardware reference points. Bit rates are payload rates, not raw
# symbol rates, so they compare like-for-like against a syndrome stream.
BANDWIDTH_REFS = [  # (label, bits per second)
    ("10 GbE network port", 10e9),
    ("NVMe Gen5 SSD, sequential read", 112e9),
    ("400 GbE network port", 400e9),
    ("PCIe 5.0 x16 link", 504e9),
    ("HBM3 memory stack", 6.55e12),
]
LATENCY_REFS = [  # (label, microseconds)
    ("DRAM access", 0.1),
    ("cheap syscall", 0.2),
    ("in-rack RDMA, one way", 1.0),
    ("Linux context switch", 1.5),
    ("datacenter round trip (TCP, same DC)", 100.0),
    ("Linux scheduler tick (HZ=1000)", 1000.0),
]
