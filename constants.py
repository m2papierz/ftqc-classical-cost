"""Quantum-machine specs, classical cost model, and reference baselines."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    """Uniform d-25 stand-in for Gidney 2025 (arXiv:2505.15917) RSA-2048 machine."""

    # The machine — Gidney 2025, arXiv:2505.15917.
    # Abstract: "less than a million noisy qubits". The paper states no exact
    # total; components sum to 897,864 and S3.2 rounds up: "I report the
    # physical qubit count as one million instead of 900 thousand" for slack.
    physical_qubits: int = 1_000_000
    cycle_us: float = 1.0  # abstract: "a surface code cycle time of 1 microsecond"
    # Abstract: "a control system reaction time of 10 microseconds". Inherited
    # from Gidney & Ekera 2021; this paper never defines the term.
    reaction_us: float = 10.0
    # S3.2: "Dividing 4.63 days by 93.3% gives the actual time estimate per
    # factoring: 4.96 days. Which I round up to a week for slack."
    runtime_days: float = 5.0
    answer_bytes: int = 256  # RSA-2048 factorization: two 1024-bit primes

    # Error correction, superconducting-flavoured. Ancilla fraction: a rotated
    # surface-code patch has d^2 data + (d^2 - 1) measure qubits, so ~1/2.
    # Machine-wide this is an upper bound — routing space is unmeasured.
    ancilla_fraction: float = 0.5
    # S3.2: "a distance of 25 is sufficient for normal surface code patches to
    # reach a per-patch per-round logical error rate of 10^-15". Applies to hot
    # storage and the compute region; cold storage is yoked (no stated distance).
    code_distance: int = 25
    # Stim, rotated_memory_z, uniform depolarizing at p=0.1% (Gidney S3.2's
    # noise model: "1 error per 1000 gates"), bulk detectors, d=25: 1.86%.
    # Rounded to 2%. Not Google's 8.5% — that is measured silicon at SI1000
    # p~0.3-0.4%, a different (noisier) machine than Gidney assumes.
    detection_fraction: float = 0.02

    # The decoder — single-core sparse blossom (Higgott & Gidney 2025,
    # arXiv:2303.15933), benchmarked on one core of an Apple M1 Max.
    # S6: d=17 at p=0.1% has a "mean running time of 0.62 microseconds per
    # round"; S1: "At distance 29 with the same noise model ... 3.5
    # microseconds per round". The paper reports nothing at d=25 and gives no
    # data table, so bill() fits a power law through these two anchors.
    # Scaling is NOT linear in d: S5 finds time "linear in the number of
    # nodes", and N ~ d^3 for a d*d*d circuit, so per-round cost is convex
    # in d. Anchors are (distance, microseconds per round per patch).
    decode_anchor_lo: tuple[int, float] = (17, 0.62)
    decode_anchor_hi: tuple[int, float] = (29, 3.5)

    # Demonstrated state of the art — Google Quantum AI, Nature 638, 920
    # (2025), abstract: "an average decoder latency of 63 us at distance-5 up
    # to a million cycles, with a cycle time of 1.1 us". Reported as 63 +/- 17
    # us, on the 72-qubit processor, from a parallel C++ *software* decoder
    # given exclusive CPU access. It is decode time only: it "does not yet
    # include feedback into the logical circuit", so it is not a reaction time.
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


# The default preset the blog post is written against.
GIDNEY_2025 = Spec()

# Classical reference points: round, widely quoted figures for commodity
# hardware, to calibrate intuition on a log scale. Bit rates are payload rates,
# not raw symbol rates, so they compare like-for-like against a syndrome stream.
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
