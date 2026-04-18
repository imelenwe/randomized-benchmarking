# Standard RB — Implementation Plan

## Parameters
- `m_values = [1, 2, 4, 8, 16, 32, 64, 128]`
- `K = 30` sequences per length
- `shots = 1024`
- `n_qubits`: start with 1, then 2

## Fit model
`F(m) = A·rᵐ + B` — EPC = `(d-1)/d · (1-r)` where `d = 2^n`

---

## Cell Plan

| Cell | Name | Status | Notes |
|------|------|--------|-------|
| 1 | Imports | ✅ done | random_clifford, Aer, noise, numpy, scipy, matplotlib |
| 2 | Config | ⬜ | n_qubits, m_values, K, shots — all in one place |
| 3 | Noise model factory | ⬜ | make_noise_model(type, params) → NoiseModel |
| 4 | Circuit builder | ⬜ | build_rb_circuit(n, m, interleaved_gate=None) |
| 5 | Experiment runner | ⬜ | loop m_values × K, return {m: F(m)} |
| 6 | Curve fit | ⬜ | scipy.curve_fit → r, A, B, EPC |
| 7 | Plot | ⬜ | scatter + decay curve, print r and EPC |

---

## Design Decisions
- Clifford sampling: `random_clifford(n)` black box
- Composition: `Clifford.compose()` to track running product D_m
- Inverse: `D_m.adjoint()` — one inversion per sequence, not per gate
- Circuit build: synth each Clifford individually → append → append inv → measure
- `interleaved_gate=None` stub in cell 4 for future Interleaved RB

## Noise Progression (later)
depolarizing → amplitude damping → thermal relaxation → coherent over-rotation → readout error → fake backend → real QPU
