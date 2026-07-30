# ftqc-classical-cost

Itemizes the classical cost of one fault-tolerant quantum run: syndrome bandwidth, telemetry volume, decoder core count, and latency deadlines for the RSA-2048 factoring machine of [Gidney 2025](https://arxiv.org/abs/2505.15917), each placed next to a commodity-hardware reference point (PCIe, 400 GbE, context switches, scheduler ticks). Also recomputes the break-even runtimes for polynomial speedups from [Babbush et al. 2021](https://arxiv.org/abs/2011.04149). Three scripts render one chart each; every derived figure is asserted against its published counterpart before anything is drawn.

Back-of-the-envelope by design: uniform code distance, flat ancilla fraction, decode cost extrapolated past what has been demonstrated. See [Limitations](#limitations) and [Model](#model).

## Results

Defaults are the `GIDNEY_2025` and `BABBUSH_2021` presets in `constants.py`.

| Quantity | Result | Target |
|---|---|---|
| Raw syndrome stream, machine / per patch | 500 Gb/s / 624 Mb/s | `syndrome_bandwidth` |
| Detection-event stream after sparsification | 10 Gb/s | `syndrome_bandwidth` |
| Telemetry over the run vs. size of the answer | 27 PB vs. 256 B (~10¹⁴) | `make check` |
| Decoder cores to keep pace (sparse blossom) | ~1,700 | `make check` |
| Deadlines: cycle / reaction budget / demonstrated | 1 µs / 10 µs / 63 µs | `latency_ladder` |
| Break-even runtime, quadratic / cubic / quartic (compiled SA vs. 1,000 cores) | 880 y / 1.3 d / 29 min | `breakeven_ladder` |

## Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
make install    # uv sync -> .venv/ (runtime + dev deps, locked in uv.lock)
```

## Usage

```bash
make check      # run both verification suites, render nothing
make run        # verify + render all three charts to results/
make fmt        # ruff import sort + format
```

Each chart is a standalone script taking an optional output directory:

```bash
uv run scripts/syndrome_bandwidth.py [out-dir]
uv run scripts/latency_ladder.py     [out-dir]
uv run scripts/breakeven_ladder.py   [out-dir]
```

Plain `python <script> [out-dir]` works with matplotlib >= 3.8 installed. Each script asserts the numbers behind its chart before rendering and fails loudly on a mismatch.

To evaluate a variant, replace fields on the frozen spec:

```python
from dataclasses import replace
from constants import GIDNEY_2025
from model import derive_classical_costs

spec = replace(GIDNEY_2025, physical_qubits=20_000_000, runtime_days=0.33)
costs = derive_classical_costs(spec)
print(f"{costs.raw_bps:.3g} b/s raw syndrome, {costs.cores:.0f} decoder cores")
```

`derive_classical_costs` accepts any spec; `verify_classical_costs` pins the
published figures and will fail on a variant.

## Layout

| Path | Contents |
|---|---|
| [`constants.py`](constants.py) | Pinned inputs: `Spec` (machine and cost model), `Breakeven` (primitive times), reference-point lists. All frozen dataclasses. |
| [`model.py`](model.py) | Every derivation and every assertion. Run directly to execute both verification suites. |
| [`style.py`](style.py) | Shared palette, Matplotlib rc, PNG writer. |
| [`scripts/`](scripts/) | One script per chart, built on the three modules above. |
| [`results/`](results/) | Rendered PNGs. |

## Model

A uniform distance-25 stand-in for Gidney's machine, not a reproduction of it. Where it departs:

- **Telemetry**: one syndrome bit per measure qubit per round; half of the physical qubits are measure qubits (a rotated patch is d² data + d²−1 measure). Machine-wide that is an upper bound — routing space is unmeasured.

- **Detection density**: the 2% sparsification factor is simulated here, not cited. Stim `rotated_memory_z`, uniform depolarizing at p = 0.1% (Gidney's noise model, "1 error per 1000 gates"), bulk detectors at d = 25, gives 1.86%. Google's measured 8.5% is a different regime — real silicon at SI1000 p ≈ 0.3–0.4% — and not what this machine assumes. The resulting per-patch sparsified rate is 12.5 Mb/s, against the "tens of" Mb/s per logical qubit of Battistel et al. ([arXiv:2303.00054](https://arxiv.org/abs/2303.00054)).

- **Patches**: uniform d = 25 patches of 2d²−1 = 1249 qubits give ~800 patches. Gidney's machine is heterogeneous: 1280 cold logical qubits in yoked surface codes at 430 physical qubits each, 131 hot patches at 2(d+1)² = 1352 each, plus a 7×18 compute region — 1537 logical qubits over 897,864 physical. The ~800 figure is this model's, not the paper's.

- **Decoder compute**: extrapolated from the single-core sparse blossom benchmarks of [Higgott & Gidney 2025](https://arxiv.org/abs/2303.15933), which report 0.62 µs/round at d = 17 and 3.5 µs/round at d = 29 but nothing at d = 25. Cost is fitted as a power law through those two per-round anchors, giving an exponent of ~3.2 and 2.2 µs/round at d = 25. The fit interpolates the paper's published points on log-log axes and asserts no scaling law of its own. For reference: linear interpolation between the anchors would read 2.54 µs, and the paper's linear-in-node-count scaling alone (per-round detector count ~ d²) would read 1.34 µs, so the empirical curve grows faster than the node count and the fit sits between the two.

- **What the core count is not**: sparse blossom's benchmarks are batch decoding of pre-sampled shots on one M1 Max core. The paper has no streaming support and states that real-time decoding at scale "motivates the development of a parallelised implementation". The core count also assumes decode parallelises across patches with zero overhead. It bounds the *throughput* problem from below; the binding constraint is the µs-scale *latency* problem, which is why production designs use FPGAs and ASICs.

- **Demonstrated latency**: [Google's below-threshold experiment](https://www.nature.com/articles/s41586-024-08449-y), 63 ± 17 µs at d = 5 on the 72-qubit processor, from a parallel C++ *software* decoder with exclusive CPU access. Decode time only — it "does not yet include feedback into the logical circuit" — so it is not a reaction time and is not directly comparable to Gidney's 10 µs budget.

- **Break-even ladder**: Babbush et al.'s closed form, T\* = t_Q(t_Q·S/t_C)^(1/(d−1)) (their Eq. 3 and, with classical parallelism S, Eq. 5), evaluated at their two primitives: an optimistic 100-Toffoli "lower bound" and a compiled N = 512 simulated-annealing step. No value is transcribed from their Table I; every plotted value is recomputed and asserted against the printed table (2 significant figures, max deviation 2.7%). The model's optimism is the paper's: no prefactor overhead in call counts, one classical clock cycle per Toffoli, serial CCZ distillation, S ≈ P for embarrassingly parallel classical competition. Their *d* is the polynomial degree of the speedup, not code distance, so the code calls it `degree`. The dashed reference line is this repo's other model — the 5-day RSA-2048 runtime — putting the two papers on one axis.

- **Coherence (T1 = 68 µs), not plotted**: same Google paper, *"mean operating T1 of 68 µs"*. It is not a deadline: the code protects the state continuously, so the decoder may lag T1 freely. What T1 bounds is the *cycle*, which must run far faster than it — 1.1 µs there, ~60× — which is why a cycle is microseconds and not tens of them. It is also the most platform-dependent number here: trapped ions and neutral atoms sit orders of magnitude above it.

## Limitations

- Uniform code distance and a flat 50% ancilla fraction across the whole machine; the real layout is heterogeneous and partly yoked.
- Decode cost at d = 25 is interpolated between two published points, from batch benchmarks on one core. Streaming, real-time decoding at this scale is unsolved.
- Core counts assume decode parallelises across patches with zero overhead. They bound throughput, not latency.
- The break-even model inherits every optimistic assumption of Babbush et al.
- Bandwidth reference points are payload rates, not raw symbol rates; the HBM3 row is memory bandwidth, not a transport the syndrome stream would cross.

## Figures

All three charts sort ascending on a log axis. Palette: neutral = classical, accent = quantum. `syndrome_bandwidth` uses bars; `latency_ladder` and `breakeven_ladder` use Cleveland dot ladders. On `latency_ladder`, shape distinguishes machines: circle = Gidney's modelled machine, diamond = Google's 72-qubit device. On `breakeven_ladder` both dots in a row are quantum break-even times, so both wear accent and fill distinguishes the primitive: open = the "lower bound", filled = compiled simulated annealing.

## Sources

Every input and its exact basis: a verbatim quote, a standards or vendor document, an independent measurement, or a simulation run here. Rows marked **derived** are computed in `model.py` from the rows above them.

### The machine: [Gidney 2025, arXiv:2505.15917](https://arxiv.org/abs/2505.15917)

| Input | Value | Basis |
|---|---|---|
| `physical_qubits` | 1,000,000 | Abstract: *"less than a million noisy qubits"*. The paper states no exact total; §3.2: *"I report the physical qubit count as one million instead of 900 thousand"* for slack. Components sum to 897,864. |
| `cycle_us` | 1.0 | Abstract: *"a surface code cycle time of 1 microsecond"* |
| `reaction_us` | 10.0 | Abstract: *"a control system reaction time of 10 microseconds"*. Inherited from Gidney & Ekerå 2021; never defined in this paper. |
| `runtime_days` | 5.0 | §3.2: *"Dividing 4.63 days by 93.3% gives the actual time estimate per factoring: 4.96 days. Which I round up to a week for slack."* |
| `code_distance` | 25 | §3.2: *"a distance of 25 is sufficient for normal surface code patches to reach a per-patch per-round logical error rate of 10^-15"*. Hot storage and compute region only; cold storage is yoked. |
| noise model | p = 0.1% | Abstract: *"a uniform gate error rate of 0.1%"*; §3.2: *"a uniform depolarizing noise model with a noise strength of 1 error per 1000 gates"* |

### The decoder: [Higgott & Gidney 2025, arXiv:2303.15933](https://arxiv.org/abs/2303.15933)

| Input | Value | Basis |
|---|---|---|
| `decode_anchor_lo` | (17, 0.62 µs) | §6: *"for distance-17 surface code circuits with p = 0.1% circuit-level noise, we observe a mean running time of 0.62 microseconds per round"* |
| `decode_anchor_hi` | (29, 3.5 µs) | §1: *"At distance 29 with the same noise model … PyMatching takes 3.5 microseconds per round to decode on a single core"* |
| scaling exponent | 3.24 (**derived**) | Empirical power-law fit through the two per-round anchors above. Steeper than the ~d² that §5's *"running time is linear in the number of nodes"* alone would predict per round. |
| decode cost @ d=25 | 2.16 µs/round (**derived**) | The paper reports no d = 25 point and publishes no data table (Fig. 10 is a log-log plot). |
| benchmark hardware | 1 core, Apple M1 Max | Fig. 10 caption: *"All three decoders use a single core of an M1 Max processor."* No clock speed is stated. |

### Demonstrated state of the art: [Google Quantum AI, Nature 638, 920 (2025)](https://www.nature.com/articles/s41586-024-08449-y) ([arXiv:2408.13687](https://arxiv.org/abs/2408.13687))

| Input | Value | Basis |
|---|---|---|
| `demonstrated_latency_us` | 63.0 | Abstract: *"an average decoder latency of 63 µs at distance-5 up to a million cycles, with a cycle time of 1.1 µs"*. Main text gives 63 ± 17 µs, on the 72-qubit processor. |
| coherence T1 | 68 µs (**not plotted**) | *"mean operating T1 of 68 µs and T2,CPMG of 89 µs"*. Not a deadline, so it is discussed in [Model](#model) rather than drawn. |
| detection probability | 8.5% @ d=5 (**not used**) | *"The surface code detection probabilities are p_det = (7.7%, 8.5%, 8.7%) for d = (3, 5, 7)."* Measured silicon at SI1000 p ≈ 0.3–0.4%: a noisier machine than Gidney assumes, so this repo simulates its own instead. |

### Logical clock: [Litinski, "A Game of Surface Codes", arXiv:1808.02892](https://arxiv.org/abs/1808.02892)

| Input | Value | Basis |
|---|---|---|
| `logical_clock_hz` | 40 kHz (**derived**) | §1: *"Each time step roughly corresponds to d code cycles"*; lattice surgery measurements *"both require d code cycles to account for measurement errors"*. The paper's own caveat: *"the correspondence between 1 time step and d code cycles is not exact"*. |

### Break-even model: [Babbush et al., PRX Quantum 2, 010103 (2021), arXiv:2011.04149](https://arxiv.org/abs/2011.04149)

Prose here is paraphrase; equation numbers and values are the paper's, verified against the arXiv v2 full text.

| Input | Value | Basis |
|---|---|---|
| break-even form | T\* = t_Q(t_Q·S/t_C)^(1/(d−1)) | Eq. 3 (S = 1) and Eq. 5. *d* is the polynomial degree of the speedup; S the classical parallel speedup factor, ≈ P for the embarrassingly parallel problems (search, optimization, Monte Carlo) where quadratic speedups typically arise. |
| `toffoli_s` | 170 µs | Eq. 6: t_G = 30 × 5.5 × 1 µs ≈ 170 µs — 5.5·d surface-code cycles per Toffoli (Gidney-Fowler factories), ~1 µs per round with decoding included, code distance near 30. The product is 165 µs; the paper rounds to 170 and computes with it, as does this repo. |
| `lb_quantum_s` | 17 ms | Eq. 8. A primitive needs G ≥ N Toffolis, and the paper argues no problem worth accelerating fits under ~100 qubits, so N = 100 → 100 × 170 µs. |
| `lb_classical_s` | 33 ns | Eq. 10. A 3 GHz CPU: t_C = 330 ps × L with one clock cycle per Toffoli (L = 100) — an equivalence the paper flags as generous to the quantum side. |
| `sa_quantum_s` | 440 ms | Eq. 9. An N = 512 Sherrington-Kirkpatrick update costs ~2.6 × 10³ Toffolis in the compilation of [Sanders et al., PRX Quantum 1, 020312 (2020)](https://arxiv.org/abs/2007.07391); 2.6e3 × 170 µs = 442 ms, rounded. |
| `sa_classical_s` | 7 ns | Eq. 11. A performant classical simulated-annealing step for the same instance, rejected updates included — techniques of [Isakov et al., Comput. Phys. Commun. 192, 265 (2015)](https://arxiv.org/abs/1401.1084), figure quoted via Sanders et al. |
| Table I | 12 values (**asserted**) | Every degree in {2, 3, 4} × S in {1, 10³} scenario at both primitives, recomputed from Eq. 5 and asserted to the table's 2 printed significant figures (max deviation 2.7%). |
| prose + Table II | 3,000 cores; R = 10 (**asserted**) | The paper's prose example: with P = 3,000 classical CPUs the 100-Toffoli break-even becomes a year — recomputed, 304 days, which the paper rounds up. Table II (Eq. 12: an R-fold distillation speedup divides the quadratic T\* by R²) at R = 10, S = 10³: 8.8 years. |

### Simulated in this repo: [Stim](https://github.com/quantumlib/Stim)

| Input | Value | Basis |
|---|---|---|
| `detection_fraction` | 0.02 | `rotated_memory_z`, uniform depolarizing at p = 0.1% (Gidney's noise model), bulk detectors, d = 25 → 1.86%, rounded to 2%. Definition per [Gidney et al., arXiv:2108.10457](https://arxiv.org/abs/2108.10457): *"the proportion of actual detection events to the total number of potential detection events"*. |

### Classical bandwidth reference points

| Input | Value | Basis |
|---|---|---|
| 10 GbE port | 10 Gb/s | [IEEE 802.3ae-2002](https://standards.ieee.org/ieee/802.3ae/1089/) MAC rate, exactly 10e9. 10GBASE-R's 64b/66b PCS (Clause 49) rides on top: 10 × 66/64 = 10.3125 GBd serial. The detection-event stream lands on it exactly. |
| NVMe Gen5 sequential read | 112 Gb/s | ~14 GB/s over PCIe 5.0 x4. Conservative: [Sandisk SN8100](https://documents.sandisk.com/content/dam/asset-library/en_us/assets/public/sandisk/product/internal-drives/wd-black-ssd/data-sheet-wd-black-sn8100-nvme-ssd.pdf) specs 14,900 MB/s and [Samsung 9100 PRO](https://download.semiconductor.samsung.com/resources/data-sheet/Samsung_NVMe_SSD_9100_PRO_Datasheet_Rev.1.0.pdf) 14,800 MB/s (4 TB; 14,700 at 1–2 TB), i.e. 14.7–14.9 GB/s, under the 15.75 GB/s x4 ceiling. |
| 400 GbE port | 400 Gb/s | [IEEE 802.3bs-2017](https://standards.ieee.org/ieee/802.3bs/6088/) MAC rate, exactly 400e9. 400GBASE-R transcodes 64b/66b to 256B/257B, then KP4 RS(544,514) FEC — both ride on top, not out of payload: 400 × 257/256 × 544/514 = 425 Gb/s serial ([Ethernet Alliance](https://ethernetalliance.org/blog/2018/03/28/a-deep-dive-into-the-802-3bs-200gbase-r-and-400gbase-r-pcspma/)). |
| PCIe 5.0 x16 | 504 Gb/s | 32 GT/s × 16 = 512 Gb/s raw; 128b/130b leaves 504.1 Gb/s = 63.0 GB/s usable per direction ([PCI-SIG](https://pcisig.com/)). Real TLP overhead lands nearer 54–57 GB/s. |
| HBM3 stack | 6.55 Tb/s | [JEDEC JESD238](https://www.jedec.org/standards-documents/docs/jesd238b01): 6.4 Gb/s/pin × 1024-bit bus = 6.5536e12 b/s = 819.2 GB/s, matching JEDEC's *"up to 819 GB/s per device"* ([press release](https://www.jedec.org/news/pressreleases/jedec-publishes-hbm3-update-high-bandwidth-memory-hbm-standard)). Memory bandwidth, not a transport: unlike the rows above, the syndrome stream would never cross an HBM stack. It marks the ceiling of commodity silicon, not a link this data would take. |

### Classical latency reference points

| Input | Value | Basis |
|---|---|---|
| DRAM access | 0.1 µs | Desktop idle 67–83 ns ([Chips and Cheese](https://chipsandcheese.com/p/amds-zen-4-part-2-memory-subsystem-and-conclusion)); matches the canonical [Jeff Dean numbers](https://gist.github.com/jboner/2841832). Server idle ~130 ns, loaded ~300 ns. |
| cheap syscall | 0.2 µs | Minimal syscall (`getpid`) with mitigations on: 76–275 ns across 15 hosts ([gms.tf](https://gms.tf/on-the-costs-of-syscalls.html)). KPTI worst case without PCID ~220 ns at 3 GHz ([arXiv:1811.01412](https://arxiv.org/pdf/1811.01412)). |
| in-rack RDMA, one way | 1.0 µs | InfiniBand in-rack. [ConnectX-5](https://network.nvidia.com/files/doc-2020/pb-connectx-5-en-card.pdf) specced at 750 ns; `ib_send_lat` ~0.85–1.2 µs one way for small messages. |
| Linux context switch | 1.5 µs | Direct cost, pinned, same core ([lmbench `lat_ctx`](https://lmbench.sourceforge.net/man/lat_ctx.8.html), [Bendersky](https://eli.thegreenplace.net/2018/measuring-context-switching-and-memory-overheads-for-linux-threads/)); ~2.2 µs unpinned. |
| datacenter round trip | 100 µs | Same-DC TCP RTT, modern measurements 50–200 µs ([evanjones.ca](https://www.evanjones.ca/network-latencies-2021.html), [TIMELY, SIGCOMM'15](https://dl.acm.org/doi/10.1145/2829988.2787510)). Jeff Dean's canonical 500 µs is a 2007–2009 figure. For comparison, Google's decoder receives syndrome *"via low-latency Ethernet"* with T_input < 10 µs. |
| Linux scheduler tick | 1000 µs | HZ=1000 is the lowlatency/Fedora config; Debian and Ubuntu generic ship HZ=250 (4 ms). [NO_HZ_IDLE](https://docs.kernel.org/timers/no_hz.html) means an idle CPU gets no tick at all, so this is a scale marker, not a periodic wakeup. |

## License

MIT — see [LICENSE](LICENSE).
