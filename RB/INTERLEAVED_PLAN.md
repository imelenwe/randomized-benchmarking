# Interleaved RB (IRB) — Implementation Plan

> **Status:** 🟡 Draft — discussing before coding. Lives in the same `RB.ipynb` as SRB.

## Goal
Measure the average error of one specific Clifford gate `C` (e.g. `S` on 1q, `CX` on 2q), separated from the bulk-Clifford error measured by SRB.

## Recipe (from slides 26–35)
1. Run **SRB** → fit `F(m) = A·r^m + B` → extract decay `r`
2. Run **IRB** (insert `C` after every random Clifford) → fit `F_IRB(m) = A·p_C^m + B` → extract decay `p_C`
3. **Target-gate error**:
   `r_C = (d−1)/d · (1 − p_C/r)` where `d = 2^n`
4. **Systematic-bias bound** (Magesan et al. Thm 5):
   `E ≤ (d−1)/d · (|r − p_C/r| + 1 − r)` — print alongside `r_C`

---

## Parameters
- `m_values_irb = [1, 2, 4, 8, 16, 32, 64]` — capped one step shorter than SRB (each step is now ~2 gates so decay is faster)
- `K = 30`, `shots = 1024` — same as SRB
- `target_gate`: configurable — `"s"` for 1q, `"cx"` for 2q (parameter, not hardcoded)
- `extra_depol_on_target = 0.005` — small extra depolarizing error on the target gate only, so `p_C < r` and the math is visible

---

## Cell Plan (additions to existing notebook)

### Cell A — Config (IRB) ✅
- `target_gate = SGate() if n_qubits == 1 else CXGate()` — single switch via `n_qubits`
- `noise_to_irb_target = 0.005`
- `m_values_irb = [1, 2, 4, 8, 16, 32, 64]`
- Other params (`shots`, `independent_sequences_per_m`, noise type/params) mirror SRB defaults

### Cell B — Extend `make_noise_model` ✅
- Added `noise_to_irb_target=None` kwarg
- Builds 1q or 2q depolarizing error based on `n_qubits`, attaches to `IRB_TARGET_LABEL`
- Module-level constant `IRB_TARGET_LABEL = "irb_target"` declared near top of notebook

### Cell C — Extend `build_rb_circuit` + `run_experiment` ✅
- Added `UnitaryGate` import
- `build_rb_circuit`: inside the loop, when `interleaved is not None`:
  - Append `UnitaryGate(interleaved.to_matrix(), label=IRB_TARGET_LABEL)`
  - Compose `Clifford(interleaved)` into running product `D` so the final inverse cancels both
- `run_experiment`: added `interleaved=None` kwarg, forwarded to `build_rb_circuit`, added `"unitary"` to `basis_gates`
- Smoke test verified: 1q + SGate circuit shows `Clifford → irb_target → Clifford → irb_target → Clifford (inv) → M`

### Cell D — `run_irb(...)` ✅
- Builds **one shared** `NoiseModel` (carries the `irb_target` channel; fires only on IRB circuits)
- Runs SRB (`interleaved=None`) and IRB (`interleaved=target_gate`) back-to-back
- Fits both with `fit_rbdata`; reinterprets IRB `r` as `p_C`
- Computes `r_C = (d−1)/d · (1 − p_C/r)` and bound `(d−1)/d · (|r − p_C/r| + 1 − r)`
- Returns flat dict: `r, p_C, r_C, bound, srb_results, irb_results, srb_fit, irb_fit`

### Cell E — Plot ✅
- Split into two cells: **run cell** (loops over `n_qubits ∈ [1, 2]`, stores in `irb_results_by_qubits`) and **plot cell** (re-runnable without re-simulating)
- Legend reads in slide notation: `r` (SRB), `p_C` (IRB), `x = p_C/r`, `r_C ± bound`
- Verified results:
  - 1q (S): `r_C = 0.0024 ± 0.0212` vs ground truth `0.0025` ✅ tight match
  - 2q (CX): `r_C = 0.0030 ± 0.1165` vs ground truth `0.00375` — within bound, looser due to 2q SRB curve saturating near `1/d`

### IRB analysis markdown ✅
- Inserted after IRB plot cell. Focuses on `x` (the target's depolarizing param) as the centerpiece — frames the headline as "injected 0.005, recovered 0.005 via x". Drops bound discussion. Keeps 2q saturation explanation and the IRB-below-SRB noise-routing sanity check.

---

## Design Decisions (proposed — discuss)
- **Same notebook (`RB.ipynb`)**: yes — reuses imports, noise factory, fit, runner
- **Target gate as string config** (`"s"`, `"cx"`) → mapped to a Qiskit gate inside the builder. Keeps the API tiny.
- **Inversion**: extend the running-product idea — `D_total = (C·C_m)·(C·C_{m−1})·…·(C·C_1)`, then `D_total.adjoint()` is the single closing gate. One inverse per sequence, same as SRB.
- **Noise injection — labelled `UnitaryGate`**:
  - Wrap target as `UnitaryGate(C.to_matrix(), label="irb_target")`
  - Attach extra depolarizing error to the `"irb_target"` label
  - **Why:** Aer matches noise by instruction name. A raw `SGate` transpiles to `u3` — indistinguishable from random-Clifford `u3`s. Boosting `u3` noise would leak into `Λ` and break the `p_C = x·r` identity.
  - The labelled unitary survives transpile (with `"unitary"` in `basis_gates` + `optimization_level=0`), giving a clean `Λ_c ≠ Λ`. Same mechanism works for both 1q (`S`) and 2q (`CX`).

- **Two-experiment pairing**:
  - SRB and IRB must use the *same* `NoiseModel` instance — otherwise `p_C/r` is meaningless. Bake this into `run_irb`.
  - The shared model carries the `"irb_target"` channel either way; it only fires when an `irb_target` instruction is present (i.e. IRB circuit, not SRB).

---

## Open Questions
1. ~~Transpilation leakage on 1q target~~ ✅ **Resolved**: use labelled `UnitaryGate` (see Design Decisions). Verify in code that Aer matches noise by label on the installed version; if not, fall back to a custom `Gate` subclass with a unique `.name`.
2. **Plot layout** — one chart per `n_qubits` with both SRB and IRB curves overlaid. Legend shows `r`, `p_C`, `r_C`, bound.
3. **Bound formula** — paper gives asymmetric `E_±`; we use the simpler symmetric form `E ≤ (d−1)/d · (|r − p_C/r| + 1 − r)` unless we want tighter bounds.

---

## Out of scope for this phase
- Non-uniform sampling / character RB
- Cycle benchmarking
- Real-hardware runs (still simulator-only)
