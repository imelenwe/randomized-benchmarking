# CB — Working Notes (gotchas, surprises, deferred items)

> Personal notebook for the [Cycle Benchmarking report](../CB_report.md). Not
> for sharing — candid notes about what tripped me up, surprises worth
> remembering, and things I parked. If you come back to CB in 6 months, read
> this before re-reading the code.

## A · Gotchas and fixes

- **`make_cycle("cz")` arg-swap bug.** I wrote `range(0, 2, n_qubits)` — that's
  `(start=0, stop=2, step=n_qubits)`, which emits only one CZ for any `N`.
  Coincidentally correct at `N=2` and `N=3`. Fixed to
  `range(0, n_qubits-1, 2)`. Caught only when prepping for `N=4+`.

- **`make_cycle("H")` only hit q0.** Inconsistent with the `S` branch (which did
  all qubits). Both fixed in the Rung 4 commit.

- **`m₂ = 12 → 8` for `N≥2`.** At `m₂=12`, low-fidelity weight-2 Paulis
  (e.g. `XX` under biased noise) had `λ^m₂ ≈ 0.7¹² ≈ 1.4%`, below the shot
  floor. The ratio `F_{m₂}/F_{m₁}` went negative → NaN. Shortening to 8 keeps
  everything measurable; verified no NaN at `N=3`.

- **`marginal_probs` must be carried by correlated noises explicitly.** The
  orbit predictor needs *single-letter* keys (`{I:0.95, Z:0.05}`) to take
  per-qubit products. The noise dict itself carries *two-letter* joint keys
  (`{II:0.95, ZZ:0.05}`). Same numbers, different shape — both live in the
  noise dict.

- **`expected` column previously special-cased to G=I.** Rung 3 rewired
  `run_experiment` to use `expected_lambda_orbit` for any independent Pauli
  noise on any cycle (orbit length 1 ⇒ identity case recovered for free), so
  `N=1 H` runs and `N=2 I` runs now show expected columns too.

- **`CBConfig.factorization` flag.** Default `False`. The factorization test is
  fundamentally hardware-self-consistency; on sim we have the orbit predictor
  (no false alarms on CZ), so it stays off. Will flip on for #6.

- **Random K-subset can omit "interesting" Paulis at N=3.** First `N=3` run
  drew a subset without `ZZZ`. Looked like a bug; was just the random subset.
  Set `K=63` or `K=None` to force-include everything for sanity.

## B · Surprises worth remembering

- **`F_RC` measured > `F_RC` expected under correlated noise.** First time I
  saw this I assumed bug; it's the actual phenomenon. Crosstalk *helps* the
  average because it pushes 4 Paulis to 1.0. SRB would call this a quality
  improvement. The per-Pauli view is what reverses the verdict.

- **The +0.19 number is exactly `0.19 = 1 − 0.81 = 1 − (1−2q)²`** for q=0.05.
  Closed-form fingerprint — useful as an assertion target.

- **CZ orbits at N=2 — the symmetry pattern.** Three fixed Paulis
  (`ZI, IZ, ZZ`), six 2-cycles: `{XI,XZ}`, `{IX,ZX}`, `{YI,YZ}`, `{IY,ZY}`,
  `{XX,YY}`, `{XY,YX}`. At `N=3` with disjoint `CZ(0,1)`, q2 is a spectator
  and the same six 2-cycles appear per setting of q2.

- **Worst measured Δ in the entire study** was `+0.0684` on `YX` under
  N=2 / G=I / biased noise. The 200 shots × 30 draws shot floor allows roughly
  ±0.05 on a single `λ`; everything stayed inside that band.

- **CB seems to *miss* `IZ, ZI, ZZ` damage entirely** under correlated `ZZ`.
  Worth keeping in mind: not a CB failure, just that the channel is a pure
  `Z⊗Z` Pauli error which commutes with those three observables and so is
  genuinely invisible to them. Other crosstalk shapes (e.g. `XX`-type
  correlated) would light up a different 4-Pauli block.

## C · Open items / deferred

- **Inverse Walsh–Hadamard reconstruction** of `p_Q` from `λ_P` — optional V4
  in the plan; would let us hand back a fitted Pauli error budget alongside
  `F_RC`.

- **`make_paulis` weight-1-marginal guarantee.** Currently the K-subset for
  `N≥3` is uniform random. The `factorization_test` will need all `3N`
  weight-1 marginals to compute factorized products — fix only matters once
  factorization is turned on for hardware (#6).

- **Factorization fix for rotating gates** — open for #6. The naive
  factorization test reads joints as products of bare marginals; on CZ the
  marginals are themselves orbit-geomeans. The hardware-portable version needs
  the same orbit walk that `expected_lambda_orbit` does, but starting from
  *measured* marginals instead of injected probabilities.

- **CZ ≡ ZZ rotation physics.** Parked. CZ is physically implemented as a
  `RZZ(π/2)` (so the residual always-on `ZZ` coupling is the *physical origin*
  of the correlated `ZZ` error). Distinction between the Pauli operator `Z⊗Z`
  and the rotation `exp(−iθ Z⊗Z)` is the bit I haven't fully nailed.

- **Notebook-diff cleanup** (nbstripout vs jupytext). Not important; would
  make notebook commits readable on GitHub.

## D · Reproducibility

| | |
|---|---|
| Env | `qcml-ibmqc` conda environment |
| Qiskit | 1.4.3 |
| Sim backend | Aer (stabilizer for Pauli channels; density-matrix when needed) |
| RNG | `np.random.default_rng(42)` shared across the notebook |
| Code | [`CB.ipynb`](../../CB.ipynb), cells 0–12 (cells 6, 7, 10, 11, 12 produce the report tables) |
| Spec | [`CB_plan.md`](../../CB_plan.md) |
| Figures source | `/tmp/make_cb_figures.py` — data hard-coded from notebook outputs; rerun to regenerate `reports/figures/*.png` |

GitHub: issues #1–#4 (rungs 1–4 / Exp 1–7) all CLOSED; #5 (N=10), #6 (hardware)
OPEN. All Part B commits are on `main` (latest `60d72b1`, pushed).

## E · One-line internal cheat sheet (the things I always forget)

- λ_P is just **(prob errors commute with P) − (prob errors anticommute with P)**.
- For a Pauli channel `{p_Q}`: `λ_P = Σ_Q p_Q · sign`, where `sign = +1` if `[Q,P]=0`, else `−1`.
- Non-Pauli Clifford (H, CZ) rotates `P`; recovered `λ_P` = **geomean over orbit**.
- CZ rule: **X/Y flip → drop a Z on the partner**; I/Z frozen.
- `F_RC` = mean of `λ_P` over K Paulis. SRB-style single number; hides crosstalk.
- The four "both flippable" Paulis (`XX, XY, YX, YY`) are where correlated `Z⊗Z` crosstalk lights up.
- 0.19 ≡ `1 − (1−2q)²` at q=0.05.
- `factorization_test`: needs no noise, false-alarms on rotating gates.
- `expected_lambda_orbit`: needs the noise (or `marginal_probs`), exact on any cycle.
