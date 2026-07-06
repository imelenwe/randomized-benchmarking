# Research Spec: Inferring Non-Markovian Noise Structure from Cycle Benchmarking Data via Simulation-Based Inference

**Author:** Lnv, supervised by Prof. Bijita; collaboration with Prof. Sanghka, IIT Hyderabad
**Spec owner:** Claude Code (maintained from 2026-07-06; full ownership delegated by Lnv)
**Date:** July 2026
**Status:** Problem definition / pre-implementation spec — Phase 0 not yet started
**Intended use:** Working spec for implementation with Claude Code

---

## Spec maintenance log

Every change to this spec is logged here as a checkbox. Unchecked = agreed but not yet
written into the body; checked = applied. Newest at top.

- [x] **2026-07-06** — Reframed project as **simulation-based inference (SBI)**; diffusion demoted from "the method" to "one estimator choice, selected *after* the Phase-2 target" (§1, §3.3, §4).
- [x] **2026-07-06** — Renumbered phases to **Phase 0–4** with an explicit **gate** on each; split the old Phase 1 into Phase 0 (clone/scaffold) + Phase 1 (generator + discriminability) so the discriminability check is its own gate (§4).
- [x] **2026-07-06** — Added **§5 Phase-1 detailed design**: quantum S+E collision-model generator, matched-marginal three-class constraint, density-matrix (not stabilizer) backend, CB-only, per-sequence-shot-count data schema, checkpoint discipline.
- [x] **2026-07-06** — Added **§6 How we use the process tensor**: for data generation we propagate the joint S+E state (collision model); the process tensor is never instantiated — it is the *inference target's parameterization*, not the simulator.
- [x] **2026-07-06** — Elevated the **plain-statistics discriminability study** to the make-or-break first experiment, run *before* any neural network, providing the baseline the learned model must beat (§4 Phase 1, §5.3).
- [x] **2026-07-06** — Recorded the two locked design decisions (noise backend = quantum S+E collision model; data granularity = per-sequence shot counts) in §5.

---

## 1. One-paragraph summary

Randomized benchmarking (RB) and cycle benchmarking (CB) theory assumes Markovian noise; under
that assumption the average sequence fidelity (ASF) decays exponentially and the decay rate maps to
gate infidelity. Under non-Markovian (temporally correlated) noise this breaks: decays can be
non-exponential, and even exponential decay rates no longer equal gate infidelity. The process tensor
(Figueroa-Romero et al., PRX Quantum **2**, 040351) is the rigorous mathematical object describing
temporally correlated noise, but it is exponentially large and cannot be tomographed at scale — it is
theory scaffolding, not an experimental protocol. **This project attacks the inverse problem: given raw
(un-averaged) CB data from real hardware, infer the temporal-correlation structure of the noise.** The
inverse map is intractable and multimodal but the *forward* map (noise structure → raw CB data) is
cheaply simulable — so this is a **simulation-based inference (SBI)** problem. We follow the DiffQEC
pattern (arXiv:2604.24640) of learning a posterior over hidden causes from measurable data; a
conditional denoising diffusion model is one candidate estimator, chosen (or not) *after* the inference
target is fixed.

---

## 2. Background and prior work (what is settled)

### 2.1 Established theory (the forward direction: noise model → decay curve)

- **Standard RB (Markovian):** random Clifford sequences, survival probability decays as a single
  exponential `A p^m + B`; `p` maps to average gate fidelity.
- **Cycle benchmarking (CB):** Pauli-resolved variant. Interleaves a dressed cycle with random Pauli
  twirls (randomized compiling). Outputs per-Pauli decay constants `lambda_P`. Under Markovian +
  Pauli-twirl assumptions each `lambda_P` decays exponentially.
- **Process tensor framework (Figueroa-Romero et al., PRX Quantum 2.040351):**
  - Non-Markovianity is structurally defined as: the environment E is never traced out between time
    steps (E carries memory forward via the joint unitaries U_i).
  - The process tensor T_{k:1} is a multilinear map eating an ordered k-tuple of gates and outputting
    the final system state. Its Choi state Upsilon_{k:1} (Eq. A3) is the multi-time generalization of the
    single-channel Choi state C_E.
  - The gate sequence gets its own Choi state (Eq. A6 / A8: the gate Choi state, fraktur-Y or C_m).
    Evaluation of the map = contraction: trace over everything except output S of
    [Upsilon * (1_S tensor GateChoi^T)] (Eq. A5).
  - RB specialization: U_i → Lambda_i (noise maps), giving Upsilon_m (A7) and C_m (A8); ASF
    computation reduces to computing the sequence-average E[C_m^T] (Appendix B, Haar/Weingarten).
  - Consequence: non-Markovian noise generically produces non-exponential ASF decay. (Non-exponential
    does not imply non-Markovian; non-Markovian implies non-exponential up to known exceptions.)
- **Brillant et al., PRL 135, 070601 (2025) — RB with non-Markovian noise and finite-time gates:**
  - Even when decay remains exponential (short correlation times), the decay rate does NOT equal
    average gate infidelity and depends strongly on gate implementation (ZSX vs U3 vs instant pulse —
    up to ~2x rate difference).
  - Practical diagnostic: run the same benchmark with different gate implementations; disagreement flags
    non-Markovianity.
  - Their generalized cumulant method extends to randomized compiling and CB.

### 2.2 Empirical anchor (our own prior work)

- Built and validated standard RB, interleaved RB, and CB theory + Qiskit implementations.
- Real-hardware CB run on **ibm_fez**: measured `lambda_XX = 0.42` vs. an independence baseline of ~0.90
  (from `lambda_X = 0.90`). This is the dominant-crosstalk anomaly.
- **The anomaly:** CB alone cannot distinguish whether the gap is caused by (a) coherent error,
  (b) stochastic correlated error, or (c) temporally non-Markovian noise. This ambiguity is the concrete
  motivating puzzle.

### 2.3 Method template

- **DiffQEC (arXiv:2604.24640):** discrete denoising diffusion performing posterior inference over error
  configurations given syndrome data. Structurally the same shape as ours: cheap known forward map,
  genuinely degenerate/multimodal posterior, train on simulated (hidden-cause, observable-data) pairs.
  Reuse as a *skeleton* if and only if the Phase-2 target justifies a diffusion estimator.

---

## 3. Problem statement (the inverse direction)

### 3.1 Given / Infer

**Given:** raw cycle-benchmarking data from a quantum processor — kept at per-sequence, per-length,
per-shot granularity, NOT collapsed by averaging or curve fitting.

**Infer:** the temporal-correlation structure of the noise — at minimum a classification/quantification
distinguishing (a) coherent, (b) stochastic-correlated-but-Markovian, and (c) genuinely non-Markovian
noise; at best, a posterior over a compressed parameterization of the (few-step) process tensor.

### 3.2 Where the signal lives (why raw data)

The standard pipeline (average over random sequences `l`, fit decay vs `m`, report one number) destroys
the signal. Temporal correlations live in:
1. The **fluctuations across random sequences `l`** at fixed `m` (a second-moment / variance structure —
   the same quantity unitarity benchmarking mines for coherence).
2. The **joint structure across sequence lengths `m`**.
3. **Per-Pauli structure** (CB's `lambda_P` resolution) and **cross-Pauli correlations**.

Raw data = the full collection indexed by (Pauli P, sequence length m, random sequence l, shot outcomes),
before any averaging over l.

### 3.3 Why simulation-based inference (and where diffusion fits)

The inverse problem is underdetermined and noisy — many noise structures produce similar data — so a
*point estimate* is the wrong object; we want a **posterior** over noise structures. The forward map is
simulable but has no tractable likelihood, which is exactly the SBI / likelihood-free regime. Candidate
posterior estimators: neural posterior estimation, normalizing flows, sequential neural likelihood, and
conditional **diffusion** models. Diffusion is favored when the target is structured/high-dimensional; a
flow or a calibrated Bayesian classifier may match it for a low-dimensional target. **The estimator is
therefore chosen in Phase 3, after the Phase-2 target is fixed — not assumed up front.**

### 3.4 Why CB over RB as the data modality

- Pauli-resolved decays give richer structure than RB's single global number.
- Randomized compiling's repeated identical dressed cycles are a cleaner setting for detecting
  cycle-to-cycle temporal correlation than RB's heterogeneous Clifford sequences.
- We already have working CB code and a real hardware anomaly (`lambda_XX = 0.42`) to explain.

RB is therefore **out of scope as a data source**; we clone CB only.

---

## 4. Plan of attack — phases and gates

Each phase ends at a **gate**: a question that must pass before the next phase is worth starting.
Hardware (Phase 4) is touched only after everything upstream validates, consistent with QPU-safety
discipline.

### Phase 0 — Clone & scaffold
Lift the CB twirl / prepare / measure logic out of `CB/CB.ipynb` into `DiffusionCB/` (CB only, not RB).
Produce a working, callable CB harness on a simulator we control.
→ **Gate:** run one synthetic CB decay end-to-end and recover a clean `lambda_P`.

### Phase 1 — Forward model + discriminability check *(the make-or-break)*
Build the quantum S+E collision-model generator (§5) with three **matched-marginal** classes
(coherent / stochastic-Markovian / non-Markovian), emit per-sequence shot counts, then run the
**plain-statistics** separability study (§5.3) — no neural network yet.
→ **Gate:** do the three classes separate above shot noise at a feasible shot budget?
If **no** → a publishable identifiability / negative result; the project pivots to characterizing *when*
the classes are distinguishable at all. If **yes** → proceed, carrying the hand-designed statistic forward
as the baseline to beat.

### Phase 2 — Define the inference target *(most important design decision)*
Choose the smallest physically-meaningful output space. Candidates:
- Adjacent-cycle correlation coefficient(s) between consecutive dressed-cycle noise realizations.
- A few-parameter restricted process tensor (2–3 step).
- Noise correlation time `tau_c` relative to cycle time (regression target).
- A 3-way classification (coherent / stochastic-Markovian / non-Markovian) with calibrated posteriors.

The estimator family (diffusion vs flow vs classifier) is selected here as a *consequence* of the target's
dimensionality and structure.
→ **Gate:** a written, justified definition of the output space + the Phase-1 baseline number the learned
model must beat.

### Phase 3 — Build the estimator (SBI)
Train the chosen conditional generative model on simulated (noise-structure, raw-CB-data) pairs; it learns
the posterior over the Phase-2 target. Validate on held-out synthetic ground truth: posterior coverage,
calibration, identifiability limits.
→ **Gate:** it beats the Phase-1 hand-designed baseline, with honest (calibrated) posteriors.

### Phase 4 — Real hardware
Re-run CB on IBM (ibm_fez or successor), retaining raw per-sequence data (modify CB code to stop
discarding it), feed real raw data to the trained model, report the inferred temporal structure behind the
`lambda_XX` anomaly. Cross-check with the Brillant gate-implementation diagnostic (ZSX vs U3): does
decay-rate disagreement corroborate the model's inference?
→ **Gate:** the model's inference corroborates an independent diagnostic.

---

## 5. Phase-1 detailed design

Two design decisions are **locked** (2026-07-06):
1. **Noise backend built first = quantum S+E collision model** (formalism-faithful; matches the process
   tensor directly; environment small enough to stay tractable). The classical Ornstein-Uhlenbeck model
   is deferred as a later fast/tunable limit, not built first.
2. **Data granularity = per-sequence shot counts** (maximal signal retention; enables variance-across-`l`
   and cross-Pauli analysis — the whole premise that averaging destroys the signal).

### 5.1 Ground-truth generator (quantum S+E collision model)

- **S** = 1 qubit (CB system; extend to 2 qubits for the CZ cycle later — pilot on 1q).
- **E** = 1 environment qubit, `d_E = 2`, left as a knob to grow.
- **Per cycle:** apply the dressed cycle + a random Pauli twirl on **S**, then a joint unitary
  `U = exp(-i*delta*H)` on **S+E**, with `H` the PRX Eq. 24 two-spin Hamiltonian
  `H = J*X1*X2 + hx*(X1+X2) + hy*(Y1+Y2)`. `delta`, `J` tune correlation strength.
- **E is never traced until the end of the sequence** — this is precisely the non-Markovianity.

### 5.2 The three classes must share the same per-cycle marginal channel (hard requirement)

If the classes differ in their marginal `lambda_P`, any model "wins" trivially by reading the marginal and
the result is vacuous. So all three are calibrated to the **same** `lambda_P`:
- **(c) non-Markovian:** the collision model of §5.1.
- **(b) stochastic-Markovian:** trace-and-reset E every step → i.i.d. Pauli channel per cycle, tuned to the
  same `lambda_P`.
- **(a) coherent:** a fixed unitary over-rotation on S alone, also tuned to the same `lambda_P`.

Calibrating (a)/(b)/(c) to a common `lambda_P` is itself an implementation task (§9 open item).

### 5.3 Discriminability study — the first real experiment (no neural net)

On matched-marginal classes, compute simple summary statistics and test whether the classes separate
above shot noise, as a function of shot budget:
- **variance across random sequences `l`** at fixed `m` (second moment),
- **non-exponentiality**: residual from the best single-exponential fit of the mean decay,
- **cross-Pauli correlation**: does `XX` co-fluctuate with `X`, `Z`?

Output: a separability plot + the shot budget required. This answers "is the signal even there?" and
speaks directly to the `lambda_XX` anomaly. It also yields the baseline the Phase-3 model must beat.

### 5.4 Simulator backend

- Must be **density-matrix or statevector on S+E**, **not stabilizer**: coherent over-rotations and
  `exp(-i*delta*H)` are non-Clifford. (Departs from the usual "stabilizer for Pauli channels" default;
  cost is trivial at 2–4 qubits.)
- Aer `density_matrix` is the default backend.

### 5.5 Raw-data schema and checkpointing

```
record[P][m][l] = {
    counts:      {bitstring: n, ...},   # per-shot measurement counts (persisted)
    twirl_seq:   [ ... ],               # the specific random-compiling twirls used
    class_label: "coherent" | "stochastic_markov" | "non_markov",
    gt_params:   {delta, J, hx, hy, d_E, ...},
}
```
- Persist raw shot counts to disk (JSON / parquet).
- **Checkpoint per `(P, m)` block** so a long generation run is resumable on failure — the same
  checkpoint discipline used for hardware jobs applies to large sim sweeps.

---

## 6. How we use the process tensor (multi-time-step)

Key point: **we never instantiate the process tensor to generate data.** The Choi object `Upsilon_{k:1}`
(Eq. A3) is `d_S^{2k}`-dimensional — exponential and un-buildable. What it *represents* operationally is
cheap:

```
rho_SE  <-  initial joint state                 # dim = d_S * d_E  (e.g. 2*2 = 4)
for each cycle i:
    apply gate G_i  on S only                   # CB dressed cycle + twirl
    apply joint unitary U_i  on S+E             # memory lives here; E is NOT traced
measure S (trace out E only at the very end)
```

This loop **is** the multi-time-step usage (the "collision model" / repeated-interaction picture). The
environment carried forward without tracing is what makes it non-Markovian. Lnv's hand-worked
"Process tensor example" (S in `(|0>+|1>)/sqrt2`, an environment qubit, CNOT_SE at t1 then t2,
propagating the joint density matrix) is exactly a 2-step instance of this loop — scaled up in code it is
the Phase-1 generator.

**So:** the process tensor is the object we later try to infer a *compressed shadow* of (Phase 2), not the
thing we simulate with (Phase 1). For data generation, propagate S+E directly; keeping "few time steps"
is what keeps everything tractable.

---

## 7. Honest caveats / known risks

- **Identifiability:** coherent errors and temporal correlations can mimic each other in some regimes.
  Characterizing *when* they are distinguishable from CB data is itself part of the contribution; a
  limitation result is publishable.
- **Sim-to-real gap:** the model trains on simulated noise; real hardware noise is richer. Mitigations:
  broad noise-model families in training, domain randomization, and the gate-implementation cross-check.
- **"Non-exponential implies non-Markovian" is false in general;** all claims are phrased as posterior
  inference over structured hypotheses, not as a binary detector.
- **Process tensor is never implemented on hardware.** It is the theoretical target/parameterization only.
  Hardware protocol remains plain CB.
- **Estimator risk:** committing to diffusion before Phase 2 would be a hammer-seeking-nail error; the
  spec deliberately defers that choice (§3.3, §4).

---

## 8. Assets already in hand

- Validated Qiskit implementations: standard RB, IRB, CB (GitHub: invinciible-ind/randomized-benchmarking;
  CB report PDF included). `CB/CB.ipynb` is the clone source for Phase 0.
- Real hardware CB result on ibm_fez (`lambda_XX = 0.42`, `lambda_X = 0.90`).
- Line-by-line understanding of the process tensor formalism (PRX Quantum 2.040351, Appendix A fully
  worked: A1–A8, swap mechanics, Choi contractions, entanglement-transfer mechanism).
- Notation handbook (.tex) for the non-Markovian RB paper.
- Anchor papers: Figueroa-Romero et al. PRX Quantum 2.040351 (theory), DiffQEC arXiv:2604.24640 (method
  template), Brillant et al. PRL 135.070601 (finite-time gates + implementation-dependence diagnostic).

---

## 9. Open decisions / immediate next actions

Open (need resolution as we reach them):
1. **Phase-2 inference target** — the single most important design decision; deferred until Phase-1
   discriminability data is in hand.
2. **Matched-marginal calibration** — the procedure to force (a)/(b)/(c) to a common `lambda_P` (§5.2).
3. **Estimator family** — chosen in Phase 3 as a consequence of the Phase-2 target.

Immediate next actions (Phase 0):
1. Clone CB harness from `CB/CB.ipynb` into `DiffusionCB/` (CB only).
2. Stand up the density-matrix simulator path and recover a clean `lambda_P` on a trivial noise model
   (the Phase-0 gate).
3. Then Phase 1: implement the collision-model generator + the three matched-marginal classes + the
   discriminability study.
