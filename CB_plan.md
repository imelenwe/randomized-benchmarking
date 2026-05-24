# Cycle Benchmarking (CB) — Implementation Plan

> **Status:** 🟢 **Part A (1 qubit) complete.** Part B **Rung 1 (N=2 identity) complete — factorization holds.**
> Implemented in `CB.ipynb` (separate from `RB.ipynb` = SRB + IRB). Structurally distinct from SRB/IRB:
> no inversion gate, Pauli propagation, per-Pauli decay. Designed to scale 1 → 2 → 3 qubits and to
> swap simulator → IBM hardware.
>
> **▶ Resume here:** Architecture refactored to a `CBConfig` dataclass + `run_experiment(cfg, cycle_gates, noises)`
> (`run_cb`/`run_once` take `cfg`; sim built once per noise). **Rung 1 (N=2, G=I) passes** — measured `F_RC`
> matches the factorized *independent* prediction across all 4 noises (depol 0.92 / dephasing 0.90 / bit-flip 0.89 /
> biased 0.81), weight-2 `λ_P` factorize. Fixed a two-length NaN by `m2 12→8` (low-fidelity multi-qubit Paulis
> decayed below the shot-noise floor → `F_{m2}` could go negative → `(neg)^{1/Δm}=NaN`).
> **Next → Rung 2: N=2, inject correlated `ZZ`, show factorization break.**

## Goal
Estimate the per-Pauli fidelities `λ_P` of a dressed Clifford cycle and the error per cycle
`r = 1 − F_RC` (with `F_RC = avg λ_P`). `λ_P` resolves the **direction-dependent** noise that SRB
averages into one number — and at N≥2 it exposes **correlations between qubits** (crosstalk).
**One build → run → measure path** that also runs on IBM hardware.

## Theory recap (only what the code depends on)
- Ideal Clifford cycle `G`, noisy `G̃`. Dressed cycle = random Pauli `Rᵢ`, then `G`, repeated.
- Circuit `C(P) = Rₘ G … R₁ G R₀`, run on a `+1`-eigenstate of `P`, measure `⟨P⟩`.
- **Enforce `G^m = I`** (m a multiple of the cycle's order) ⇒ net Clifford is `I` ⇒ ideal outcome is
  always `±P`. We measure the *input* Pauli; only the **sign** flips with the random draws.
  Fixed measurement basis ⇒ SPAM cancels into a length-independent prefactor `α` (this is why CB is SPAM-robust).
- **Measured quantity:** `f_{P,m,l} = sign × ⟨P⟩`, averaged over `L` draws → `F_{P,m}`.
  Naming: **`ideal_cycle` = C(P)** (classical answer key, ±P) · **`real_cycle` = C̃(ρ)** (noisy run).
- **Two-length estimator (no curve-fit):** `F_{P,m} = α·λ_P^m`, so
  `λ_P = (F_{P,m₂}/F_{P,m₁})^{1/(m₂−m₁)}` — the ratio cancels `α`.
- **Analytic check (commute formula):** for a Pauli channel,
  `λ_P = Σ_Q p_Q·(+1 if Q commutes with P else −1)`. Inverse Walsh–Hadamard reconstructs `p_Q` from `λ_P`.
- **Orbit-geomean:** when `G` is a *non-Pauli* Clifford (H, CZ) it rotates P around an orbit between
  cycles; the recovered `λ_P` is the **geometric mean** of the bare `λ` over that orbit.
- **Verified conventions (qiskit 1.4.3 / qcml-ibmqc):** sign via `Pauli(P).evolve(circ, frame='s')`
  (forward `UPU†`).

## Parameters
- `n_qubits`: 1 (done) → 2, 3.
- `cycle_gate`: `"I"` | `"H"` (order 2) | `"s"` (order 4) | `"cz"` (order 2) → `make_cycle` returns `(G_map, order)`.
- **Two lengths** `m1 = 4`, `m2 = 8` (multiples of the cycle order so `G^m = I`). *(Was 12; shortened so
  low-fidelity multi-qubit Paulis keep a measurable signal at `m2` — at `m2=12`, `λ≈0.72` decays to ~1%, below
  the shot-noise floor, making `(F_{m2}/F_{m1})` go negative → NaN.)*
- `K = 30` Paulis (all non-identity for N≤2; random subset of size `K` for N≥3).
- `L = 30` random sequences per `(P, m)`; `shots = 100` (raise freely in sim).
- `rng = np.random.default_rng(42)` — one shared generator, threaded into `run_cb` / `make_paulis`.

## Fit model
`F_{P,m} = α·λ_P^m`. Two lengths → closed form `λ_P = (F_{m₂}/F_{m₁})^{1/(m₂−m₁)}`, computed inside
`run_cb`. No curve-fit.

## Noise Plan
One spec per noise, rendered two ways so sim and prediction agree:
- **Check:** commute formula `expected_lambda(probs, P)` (geomean over the orbit for rotating cycles).
  `to_probs(noise)` builds the prob dict (depol → `{I:1−3p/4, X/Y/Z:p/4}`).
- **Sim:** attach the *same* Aer `QuantumError` to the labelled `UnitaryGate(label="CB_Cycle")`.

| kind | params | demonstrates | Pauli? | sim |
|---|---|---|---|---|
| `depolarizing` | `p` | isotropic baseline `λ_P = 1−p` | yes | stabilizer |
| `dephasing` | `q` | anisotropy `λ_Z=1`, `λ_X=λ_Y=1−2q` | yes | stabilizer |
| `pauli` | `{pI,pX,pY,pZ}` | general; reconstruct `p_Q` (inverse WHT) | yes | stabilizer |
| `coherent` | `θ` (e.g. `Rz`, `ZZ`) | **twirl in action** — random Paulis visibly needed | no | density-matrix, small N |

- **Noise on `G` only**; random Paulis stay ideal (keeps `λ_P` a pure function of the injected channel).
- **Multi-qubit:** *independent* per-qubit (tensor) → `λ` factorizes; *correlated* 2-qubit (e.g. `ZZ`)
  → factorization breaks (the crosstalk signature). See Part B.

---

## Part A — Single qubit (✅ COMPLETE)

Full pipeline built and validated on 1 qubit, cycles **I** and **H**:

| piece | function(s) | status |
|---|---|---|
| cycle factory | `make_cycle` (I / H / s / cz) | ✅ |
| noise factory | `make_noise` (depol / pauli) | ✅ |
| Pauli set | `make_paulis(n, rng, K)` | ✅ |
| sign | `calculate_ideal_circuit` (`frame='s'`) | ✅ |
| circuit | `build_real_circuit` = `prep_eigenstate` + `apply_dressed` + `measure_P` | ✅ |
| measure | `run_once` + `get_expectation_value` (parity over P-support) | ✅ |
| estimate | `run_cb` (two-length `λ_P`) | ✅ |
| aggregate | `F_RC = mean(λ_P)`, `r = 1 − F_RC` | ✅ |
| check | `to_probs` + `expected_lambda` (commute formula) | ✅ |
| print | `print_lambdas` (expected-vs-measured for I; measured-only for H) | ✅ |

**Validated:**
- **Sign test** — noiseless `f = +1` for every P, every draw.
- **Inject-recover** — measured `λ_P` matches the commute formula across depol / dephasing / bit-flip /
  biased (I cycle), within shot noise.
- **Anisotropy** — dephasing → `λ_Z=1`; bit-flip → `λ_X=1`; biased → all three differ.
- **Orbit-geomean (H cycle)** — H swaps X↔Z, so dephasing ≡ bit-flip through H and the protected
  `λ=1` axes collapse to the X–Z geomean. Confirms the exact machinery CZ needs.

---

## Part B — Multi-qubit (N=2,3; CZ cycle)

**Locked 2026-05-24:** cycle = **CZ entangling layer**; headline = **factorize-then-break crosstalk
demo**; scope = **N=2,3 now, N=10 later**.

**The organizing idea — factorization.** With independent per-qubit noise, `λ_P` factorizes:
`λ_{A⊗B} = λ_A·λ_B`. Crosstalk/correlated error **breaks** it; the deviation is the crosstalk
fingerprint. SRB gives one fidelity number and can't tell the two apart — CB can. Everything below
serves this.

**Orbit-geomean (already proven on H).** CZ is a non-Pauli Clifford → it rotates each Pauli around
an orbit, so recovered `λ_P` = geomean over P's CZ-orbit. CZ **fixes** the Z-type Paulis
(`Z⊗I, I⊗Z, Z⊗Z`) and **pairs** the X-type ones (`X⊗I ↔ X⊗Z`, `I⊗X ↔ Z⊗X`, …).

**The arc (the order):**
1. **Rung 1 — N=2, G=I, independent noise. ✅** Confirmed `λ_{A⊗B} ≈ λ_A·λ_B` and `F_RC` matches the
   factorized prediction across all 4 noises (within shot noise) — N-qubit plumbing validated; the drop in
   `F_RC` vs N=1 is pure independent-error accumulation (weight-2 Paulis decay as the product), no crosstalk.
2. **Rung 2 — N=2, G=I, correlated noise.** Inject a `ZZ` Pauli error → watch factorization **break**.
   *The headline — CB sees what SRB can't.*
3. **Rung 3 — N=2, G=CZ.** Benchmark the real entangling layer; orbit-geomean does its job. Optionally
   reconstruct `p_Q` via inverse Walsh–Hadamard → which 2-qubit error dominates.
4. **Rung 4 — N=3.** Same machinery, K-subset Paulis.

**Cell deltas:**
- `make_cycle`: `"cz"` → a layer of **disjoint** CZs on a fixed pairing `(0,1),(2,3),…`; odd qubit idles.
  (A cycle = one *parallel* layer.)
- `make_noise`: two N-qubit modes — **independent** = tensor of 1q Pauli errors; **correlated** =
  a 2-qubit Pauli error (weight on `ZZ`). *(Start with the `ZZ` Pauli error — stays a Pauli channel,
  stabilizer-friendly, breaks factorization unambiguously. Coherent `exp(-iθ ZZ)` is the later physical version.)*
- `make_paulis`: computed **once** per experiment (inside `run_experiment`) so the set is stable. For N≥3 the
  K-subset must **always include the weight-1 marginals** (3N of them) so `factorization_test` can look them up.
- `m1,m2 = 4,8`: multiples of CZ order 2 ⇒ `G^m=I`.

**Deliverables:**
1. **Factorization breakdown** — `λ_{A⊗B}` vs `λ_A·λ_B`; the deviation matrix = crosstalk signature.
2. **Reconstructed Pauli error budget** of the CZ layer (inverse WHT on `λ_P`).
3. **F_RC / r** for CZ vs idle, and vs N.

**On hardware:** the factorization test needs *no injected truth* — it's a self-consistency check on the
measured `λ_P` alone, so it transfers directly to IBM (where inject-recover is impossible).

---

## Design Decisions
- New notebook; no inversion gate; signed-Pauli observable; two-length closed form (no fit).
- Sign via `frame='s'`; `G^m=I` ⇒ observable always `±P`.
- **Analytic check = commute formula** (the PTM-diagonal route works but is heavier — dropped).
- **Noise on a labelled gate** (IRB trick) so the injected channel is cleanly separable.
- **One execution path** (no exact/SuperOp mode): build → run with shots → parity → estimate `f`.
  Aer method by noise: stabilizer (Pauli, scales) / density-matrix (coherent). Same path → IBM SamplerV2.
- **Measurement = Sampler + parity**, not Estimator — identical code on Aer and IBM.
- Shared `rng` generator threaded via `CBConfig`; `make_paulis` drawn once per experiment (N≥3 subset must include the weight-1 marginals).
- **Architecture:** `CBConfig` (dataclass: n_qubits, shots, m1, m2, L, K, label, rng) → `run_experiment(cfg, cycle_gates, noises)` → `run_cb(paulis, cfg, G_map, G_gate, sim)` → `run_once(P, m, cfg, G_map, G_gate, sim)`.

## Verification
| # | check | status |
|---|-------|--------|
| M1 | noiseless `f = +1` for every P / draw | ✅ |
| M2 | inject-recover: measured `λ_P` vs commute formula (1q) | ✅ |
| V1 | anisotropy (dephasing / bit-flip / biased) | ✅ |
| F1 | factorization `λ_{A⊗B}=λ_A·λ_B` holds (independent) ✅ N=2 / breaks (correlated) ⬜ Rung 2 | 🟡 |
| V4 | reconstruct `p_Q` via inverse Walsh–Hadamard | ⬜ optional, Part B |

> Acceptance tolerances are shot-based (shrink ∝ 1/√(shots·L)) — pin numbers per check as we go.

## Part C — Scaling & Hardware (backlog → issues #5, #6)
- **#5 N=10 scaling demo** — stabilizer sim; first resolve whether the labelled `UnitaryGate` survives
  stabilizer mode (density-matrix dies at 2¹⁰). Plot `F_RC` vs N. Deferred until Part B validates the machinery.
- **#6 IBM hardware** — swap backend → `QiskitRuntimeService` SamplerV2; the build → run → parity path is
  unchanged. Factorization becomes the on-device self-consistency check. Needs the sim validated + queue access.

## Later (planned)
- **Coherent-noise + twirl demo** — inject `coherent(θ)` and show the random-Pauli twirl restores a
  clean `λ_P` (density-matrix sim, small N). The clearest demonstration of *why* the twirl exists.

## Out of scope (this phase)
- Non-Clifford *cycles of interest* (G itself non-Clifford).
- Noisy random Paulis (twirl gates stay ideal for now).
- Full off-diagonal noise reconstruction beyond the diagonal `λ_P`.
