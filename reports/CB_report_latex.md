---
title: "Cycle Benchmarking — Part A + Part B Report"
subtitle: "N=1, 2, 3 — seven experiments"
date: "2026-05-30"
geometry: margin=1.8cm
fontsize: 11pt
documentclass: article
colorlinks: true
linkcolor: NavyBlue
urlcolor: NavyBlue
toccolor: NavyBlue
monofont: "Menlo"
header-includes:
  - \usepackage{amsmath}
  - \usepackage{amssymb}
  - \usepackage{booktabs}
  - \usepackage{longtable}
  - \usepackage{array}
  - \usepackage{newunicodechar}
  # Greek letters
  - \newunicodechar{λ}{\ensuremath{\lambda}}
  - \newunicodechar{ρ}{\ensuremath{\rho}}
  - \newunicodechar{α}{\ensuremath{\alpha}}
  - \newunicodechar{ε}{\ensuremath{\varepsilon}}
  - \newunicodechar{Δ}{\ensuremath{\Delta}}
  - \newunicodechar{Λ}{\ensuremath{\Lambda}}
  - \newunicodechar{Σ}{\ensuremath{\Sigma}}
  # Hat-letters
  - \newunicodechar{Ĉ}{\ensuremath{\hat C}}
  - \newunicodechar{Ĝ}{\ensuremath{\hat G}}
  # Math operators / relations
  - \newunicodechar{∘}{\ensuremath{\circ}}
  - \newunicodechar{⊗}{\ensuremath{\otimes}}
  - \newunicodechar{·}{\ensuremath{\cdot}}
  - \newunicodechar{≈}{\ensuremath{\approx}}
  - \newunicodechar{≠}{\ensuremath{\ne}}
  - \newunicodechar{≤}{\ensuremath{\leq}}
  - \newunicodechar{≥}{\ensuremath{\geq}}
  - \newunicodechar{≡}{\ensuremath{\equiv}}
  - \newunicodechar{⇒}{\ensuremath{\Rightarrow}}
  - \newunicodechar{→}{\ensuremath{\rightarrow}}
  - \newunicodechar{↔}{\ensuremath{\leftrightarrow}}
  - \newunicodechar{⟨}{\ensuremath{\langle}}
  - \newunicodechar{⟩}{\ensuremath{\rangle}}
  - \newunicodechar{−}{\ensuremath{-}}
  # Sub/superscripts
  - \newunicodechar{₀}{\ensuremath{_0}}
  - \newunicodechar{₁}{\ensuremath{_1}}
  - \newunicodechar{₂}{\ensuremath{_2}}
  - \newunicodechar{²}{\ensuremath{^{2}}}
  - \newunicodechar{³}{\ensuremath{^{3}}}
  - \newunicodechar{⁴}{\ensuremath{^{4}}}
  - \newunicodechar{ᴺ}{\ensuremath{^{N}}}
  # Decorative
  - \newunicodechar{⚡}{\,\textbf{!}\,}
  - \newunicodechar{✓}{\ensuremath{\checkmark}}
---

> **Project:** Cycle Benchmarking
> **Notebook:** [`CB.ipynb`](../CB.ipynb) · **Spec:** [`CB_plan.md`](../CB_plan.md)
> **Date:** 2026-05-30 · **Scope:** N=1, 2, 3 — 7 experiments
> **Next:** N=10 stabilizer-sim demo (#5), IBM hardware (#6)
> **Reader:** assumes the [Randomized Benchmarking](../Randomized%20Benchmarking.pdf) slides (meetings 1–3) for theory. This report is what was built and what it showed.

---

## TL;DR

CB was built end-to-end in Qiskit and validated on 1, 2, and 3 qubits across **seven
experiments**. The pipeline reproduces the analytic per-Pauli fidelities $\lambda_P$
within shot noise for every channel — and, the headline result, **catches a real
two-qubit crosstalk error on a real entangling gate (CZ)**: under correlated `ZZ`
noise, the measured $\lambda_P$ for `{XX, XY, YX, YY}` jumps from the independent-noise
baseline `0.81` to `1.00` (Δ = **+0.19**), while the other 11 Paulis stay flat.
That four-Pauli cluster is the signature that SRB averages away.

### Headline figure

![Crosstalk caught on CZ — four-Pauli signature](figures/01_crosstalk_signature_cz.png)

`Δλ_P = λ_P^measured − λ_P^(independent baseline)`. Four Paulis spike to +0.19;
the rest sit at the shot-noise floor. **That cluster is the crosstalk fingerprint.**

### The seven experiments

| Exp | Setup | What it shows | F_RC (expected → measured) |
|---|---|---|---|
| 1 | N=1, G=I, 4 indep noises | per-Pauli $\lambda_P$; commute formula on a flat cycle | 0.87–0.95 → 0.87–0.95 |
| 2 | N=1, G=H, 4 indep noises | H rotates `X↔Z` → preview of orbit-geomean | 0.87–0.95 → 0.86–0.95 |
| 3 | N=2, G=I, 4 indep noises | factorization `λ_{A⊗B} = λ_A·λ_B` holds | 0.80–0.92 → 0.81–0.92 |
| 4 | N=2, G=I, **correlated `ZZ`** | factorization **breaks** on `{XX,XY,YX,YY}` | 0.896 → **0.945** ⚡ |
| 5 | N=2, G=**CZ**, bit_flip | orbit-geomean predictor on a real entangler | 0.895 → 0.895 |
| 6 | N=2, G=CZ, **correlated `ZZ`** | crosstalk caught *on the gate* — the payoff | 0.896 → **0.943** ⚡ |
| 7 | **N=3**, G=CZ, bit_flip | scaling: K-subset, 3q orbits, noise tensoring | 0.849 → 0.854 |

![F_RC across all 7 experiments (each bar pair = one noise channel)](figures/03_frc_summary.png)

The two **red** bars are the correlated-noise runs (Exp 4 and Exp 6).
Measured $F_{RC}$ sits ~5% *above* the predicted baseline — averaging over Paulis
hides the +0.19 spike. **The per-Pauli $\lambda_P$ view is what tells the truth.**

---

## 1 · Methods

Slides cover the CB protocol (Meeting 3, slides 39–48). Recap of the bits this
report uses, in slide notation:

| Object | Form | What it is |
|---|---|---|
| Ideal map / noisy map | $G : \rho \mapsto G\rho G^\dagger$ / $\hat G = \Lambda \circ G$ | ideal vs hardware |
| Ideal circuit | $C(P) = G^m(P) = \varepsilon P$ | classical answer key (since $G^m = I$) |
| Noisy circuit | $\hat C(\rho) = R_m \circ \hat G \circ \ldots \circ R_1 \circ \hat G \circ R_0(\rho)$ | run on Aer |
| Single-run overlap | $f_{P,m,l} = \mathrm{Tr}[C(P) \cdot \hat C(\rho)]$ | $=+1$ if noiseless |
| Sequence average | $F_{P,m} = (1/L) \cdot \sum_l f_{P,m,l}$ | over $L$ random Pauli draws |
| Twirled noise (per direction) | $\Lambda_T(P) = \lambda_P \cdot P$ | the diagonal Pauli channel CB measures |
| Two-length ratio (SPAM-free) | $\lambda_P = \left(F_{P,m_2}/F_{P,m_1}\right)^{1/(m_2-m_1)}$ | $\alpha$ cancels |
| Process fidelity | $F_{RC} = (1/K) \cdot \sum_P \lambda_P$ | one number from K Paulis |
| Error per cycle | $r_{RC} = 1 - F_{RC}$ | headline error |

### Knobs

| Knob | Setting | Why |
|---|---|---|
| `G` | I, H, CZ (disjoint-pair layer) | I = flat baseline; H, CZ = non-Pauli Cliffords, they rotate `P` |
| $m_1, m_2$ | 4, 8 (N≥2); 4, 12 (N=1) | both multiples of cycle order ⇒ $G^m = I$ |
| $K$ | all $4^N - 1$ for N≤2; random 30 of 63 for N=3 | full coverage where it fits |
| $L$ | 30 per `(P, m)` | shot-noise vs runtime |
| `shots` | 100 (N=1), 200 (N≥2) | shot floor matters as `λ_P → 0` |
| sim backend | Aer; noise on a labelled `UnitaryGate("CB_Cycle")` | clean noise injection (IRB trick) |

### How CB resolves one number per Pauli direction

The Pauli twirl over the random $R_i$ forces the noise on $\hat G$ to a *diagonal*
Pauli channel: $\Lambda_T(P) = \lambda_P \cdot P$ — each direction decays independently with
its own scalar $\lambda_P$ (slide 46–47). One dressed cycle pulls one factor of
$\lambda_P$ for the running observable; $m$ cycles stack to $\lambda_P^m$, giving
$F_{P,m} = \alpha \cdot \lambda_P^m$ (slide 48). The two-length ratio cancels $\alpha$ and leaves
$\lambda_P$ per direction.

### How we predict $\lambda_P$ (for sim validation)

For a Pauli channel `{p_Q}`, the **commute formula** gives the bare per-direction decay:

$$\lambda_P^{\text{bare}} = \sum_Q p_Q \cdot \big(+1 \text{ if } [Q,P]=0 \text{ else } -1\big).$$

Each error `Q` that anticommutes with `P` flips the observable's sign, contributing
`−1`. When `G` rotates `P` between cycles (H, CZ), the recovered $\lambda_P$ is the
**geometric mean over `P`'s orbit** of the bare $\lambda$'s — derived inline at **Exp 5**.

### Two detectors, two jobs

| Detector | Needs the noise? | Where it lives |
|---|---|---|
| orbit-geomean predictor | yes (`probs`, or `marginal_probs` for correlated noise) | **simulator** — inject-and-recover validation |
| `factorization_test` on measured $\lambda_P$ | no — pure self-consistency | **hardware** check; off in sim (gated by `CBConfig.factorization=False`) |

In sim the orbit predictor is the honest yardstick. Factorization will become the
hardware self-consistency check once an orbit-aware fix lands for rotating gates
(open for #6).

---

## 2 · Experiments

Each section: **setup → C(P) and Ĉ(ρ) → how noise determines λ_P → results →
walk one critical Pauli → verdict**. Numbers are pulled verbatim from the
notebook outputs.

### Exp 1 — N=1, G=I, independent noise

**Setup.** $N = 1$, $K = 3$ (X, Y, Z), `G=I`, $m_1 = 4$, $m_2 = 12$, `shots=100`, `L=30`.
Four noise channels:
`depolarizing(p=0.05)` · `dephasing{I:0.95, Z:0.05}` · `bit_flip{I:0.95, X:0.05}` ·
`biased{I:0.90, X:0.03, Y:0.02, Z:0.05}`.

**$C(P) = I^4(P) = P$** ($G=I$, $\varepsilon=+1$; same form at $m_1=4$ and $m_2=12$).
**$\hat C(\rho)$ at $m_1 = 4$** — Ĝ = Λ (since G=I); five 1-qubit random Paulis
$R_i \in \{I, X, Y, Z\}$, four Λ insertions:
$$\hat C(\rho) = R_4 \circ \Lambda \circ R_3 \circ \Lambda \circ R_2 \circ \Lambda \circ R_1 \circ \Lambda \circ R_0(\rho).$$
After the twirl each Λ acts as $\Lambda_T$ on the running observable, pulling out
one factor of $\lambda_P$ per cycle → $F_{P,4} = \alpha \cdot \lambda_P^4$.

**The split into individual Paulis happens before the math — at protocol design.**
A single pass of the protocol = one chosen P. Concretely:

1. Pick one P up front (say P=X for this pass).
2. Prepare the +1 eigenstate of that P as the input ρ. For P=X, ρ = $|+\rangle\langle+|$;
   for P=Z, ρ = $|0\rangle\langle 0|$; etc.
3. Run the dressed circuit Ĉ(ρ) (the chain `R_4 ∘ Λ ∘ R_3 ∘ Λ ∘ ...` written
   above).
4. Measure ⟨P⟩ at the end — just the one P you started with. That gives a
   single number $f_{P,m,l}$.
5. Average over L sequences → $F_{P,m}$. Run at m₁=4 and m₂=12 → ratio →
   $\lambda_P$ for that one direction.

So $F_{P,4} = \alpha \cdot \lambda_P^4$ is *per pass* — it's $F_{X,4} = \alpha \cdot \lambda_X^4$ for the X
pass, $F_{Y,4} = \alpha \cdot \lambda_Y^4$ for the Y pass, etc. They're literally three
independent experiments. Three preps, three measurements, three two-length
ratios → three rows in Exp 1's table. (Same K-passes-K-rows logic holds for
Exp 2–7; K just grows.)

**Noise $\rightarrow \lambda_P$.** Commute formula directly. Predicted triples `(λ_X, λ_Y, λ_Z)`:

| Noise | predicted `(λ_X, λ_Y, λ_Z)` |
|---|---|
| depol(p) | `(1−p, 1−p, 1−p)` |
| dephasing(q) | `(1−2q, 1−2q, 1)` |
| bit_flip(q) | `(1, 1−2q, 1−2q)` |
| biased | `(p_I+p_X−p_Y−p_Z, p_I+p_Y−p_X−p_Z, p_I+p_Z−p_X−p_Y)` |

**Results.**

| Noise | λ_X | λ_Y | λ_Z | F_RC (exp → meas) |
|---|---|---|---|---|
| depolarizing | 0.9500 → 0.9534 | 0.9500 → 0.9516 | 0.9500 → 0.9552 | 0.9500 → 0.9534 |
| dephasing | 0.9000 → 0.8985 | 0.9000 → 0.9026 | **1.0000 → 1.0000** | 0.9333 → 0.9337 |
| bit_flip | **1.0000 → 1.0000** | 0.9000 → 0.9052 | 0.9000 → 0.8950 | 0.9333 → 0.9334 |
| biased | 0.8600 → 0.8802 | 0.8400 → 0.8366 | 0.9000 → 0.9054 | 0.8667 → 0.8740 |

**Walking the critical Paulis — dephasing.** Channel = `{I:0.95, Z:0.05}`.
- $\lambda_Z$: `Z` error commutes with the `Z` observable $\rightarrow$ no sign flip ever $\rightarrow$ $\lambda_Z = p_I + p_Z = 1.00$. **Measured 1.0000 exactly** (the protected axis).
- $\lambda_X$: `Z` anticommutes with `X` $\rightarrow$ sign flips when the error fires $\rightarrow$ $\lambda_X = p_I - p_Z = 1 - 2q = 0.90$. Measured 0.8985 (within shot noise).

**Verdict.** Pipeline is correct on 1 qubit. Anisotropy is visible — dephasing
protects `Z`, bit_flip protects `X`, biased protects nothing. All $|\Delta|$ ≤ 0.02.

### Exp 2 — N=1, G=H, independent noise

**Setup.** Same as Exp 1 but `G=H` (Hadamard, order 2). $m_1 = 4$, $m_2 = 12$ both even.

**$C(P) = H^4(P) = P$** ($H^2 = I \Rightarrow H^4 = I$; $\varepsilon = +1$).
**$\hat C(\rho)$ at $m_1 = 4$** — Ĝ = Λ∘H; same five 1q random Paulis as Exp 1:
$$\hat C(\rho) = R_4 \circ \Lambda \circ H \circ R_3 \circ \Lambda \circ H \circ R_2 \circ \Lambda \circ H \circ R_1 \circ \Lambda \circ H \circ R_0(\rho).$$
Between cycles the H factor rotates the running observable: `X ↔ Z`.

**What's different.** `H` is a **non-Pauli Clifford**. Between cycles, `H` rotates
the observable: `H X H = Z` and `H Z H = X` (and `H Y H = −Y`). So a cycle on
`X` looks like noise on `X`, then on `Z`, then on `X`, … alternating. The
recovered $\lambda_X$ mixes the bare $\lambda_X$ and bare $\lambda_Z$.

**Noise $\rightarrow \lambda_P$.** The bare commute formula still gives $\lambda_X^{\text{bare}}, \lambda_Z^{\text{bare}}$;
the cycle's recovered $\lambda_X$ is the geometric mean over the orbit
`{X, Z}` — i.e. $\lambda_X^{\text{recovered}} = \sqrt{\lambda_X^{\text{bare}} \cdot \lambda_Z^{\text{bare}}}$.
(Full derivation in Exp 5.)

**Results.**

| Noise | λ_X | λ_Y | λ_Z | F_RC (exp → meas) |
|---|---|---|---|---|
| depolarizing | 0.9500 → 0.9488 | 0.9500 → 0.9563 | 0.9500 → 0.9561 | 0.9500 → 0.9537 |
| dephasing | 0.9487 → 0.9483 | 0.9000 → 0.8861 | 0.9487 → 0.9473 | 0.9325 → 0.9272 |
| bit_flip | 0.9487 → 0.9463 | 0.9000 → 0.8965 | 0.9487 → 0.9501 | 0.9325 → 0.9310 |
| biased | 0.8798 → 0.8830 | 0.8400 → 0.8415 | 0.8798 → 0.8702 | 0.8665 → 0.8649 |

**Walking the critical Pauli — dephasing on X.** Bare: `λ_X^bare = 0.90`,
`λ_Z^bare = 1.00`. Through H, X rotates to Z and back. Orbit `{X, Z}`.
Predicted `λ_X^recovered = √(0.90 · 1.00) = 0.9487`. **Measured 0.9483.** The
protected `Z` axis is shared with X across the orbit — there is no axis the H
cycle leaves fully protected.

**Verdict.** Non-Pauli Clifford handled correctly. The "protected axis"
behaviour we saw in Exp 1 partly collapses to the orbit geomean — exactly the
machinery CZ will need at N=2.

### Exp 3 — N=2, G=I, independent noise

**Setup.** $N = 2$, $K = 15$ (all non-identity 2q Paulis), `G=I`, $m_1 = 4$, $m_2 = 8$,
`shots=200`, `L=30`. Same four noise channels, each **tensored** to 2 qubits
(error fires independently on each qubit).

**$C(P) = I^4(P) = P$**, $\varepsilon = +1$.
**$\hat C(\rho)$ at $m_1 = 4$** — same chain shape as Exp 1; $R_i$ now 2-qubit Paulis (16
options each) and $\Lambda$ is the tensored 2q channel:
$$\hat C(\rho) = R_4 \circ \Lambda \circ R_3 \circ \Lambda \circ R_2 \circ \Lambda \circ R_1 \circ \Lambda \circ R_0(\rho).$$

**Noise $\rightarrow \lambda_P$.** Independent per-qubit noise ⇒ joint Pauli `λ_{A⊗B}` should
**factorize**:

$$\lambda_{A \otimes B} = \lambda_A \cdot \lambda_B.$$

This is the factorization predicted from the per-qubit commute formula.

**Results (F_RC summary, all 4 noises).**

| Noise | F_RC expected | F_RC measured | Δ |
|---|---|---|---|
| depolarizing | 0.9215 | 0.9226 | +0.0011 |
| dephasing | 0.8960 | 0.8949 | −0.0011 |
| bit_flip | 0.8960 | 0.8986 | +0.0026 |
| biased | 0.7973 | 0.8075 | +0.0102 |

**Walking the critical Pauli — dephasing on XX.** Per-qubit dephasing has
`λ_X = 0.90` and `λ_Z = 1.0` (from Exp 1). Tensored:
- `λ_XX = λ_X · λ_X = 0.81`. Measured `0.8058`. ✓
- `λ_XZ = λ_X · λ_Z = 0.90·1.0 = 0.90`. Measured `0.9006`. ✓
- `λ_ZZ = λ_Z · λ_Z = 1.0`. Measured `1.0000`. ✓

All 15 Paulis under all 4 channels match the factorization prediction within
shot noise. (Worst single Δ across the 60 predictions: `+0.068` on `YX` under
biased noise — still within the shot floor at 200 shots × 30 draws.)

**Verdict.** N-qubit pipeline is sound. The $F_{RC}$ drop vs Exp 1 is pure
independent-error accumulation (weight-2 Paulis decay as a product), nothing
mysterious.

### Exp 4 — N=2, G=I, correlated `ZZ` noise

**Setup.** Same as Exp 3, but a new noise channel: a single 2-qubit Pauli error,
`{II:0.95, ZZ:0.05}`. Both qubits get hit by `Z` *together* or not at all — it is
**not** a tensor of two 1-qubit channels.

**$C(P) = P$**, $\varepsilon = +1$.
**$\hat C(\rho)$ at $m_1 = 4$** — same chain as Exp 3, but $\Lambda$ is now the **single 2-qubit**
Pauli error `{II:0.95, ZZ:0.05}` (not a tensor of two 1q channels):
$$\hat C(\rho) = R_4 \circ \Lambda \circ R_3 \circ \Lambda \circ R_2 \circ \Lambda \circ R_1 \circ \Lambda \circ R_0(\rho).$$

**Noise $\rightarrow \lambda_P$.** Same commute formula, now over 2-qubit errors. The independent
**baseline** comes from the marginal of this noise: each qubit *alone* sees
`{I:0.95, Z:0.05}` — i.e. dephasing-0.05 per qubit. So Exp 3's dephasing
prediction is what we compare against. The data on whether the noise is really
independent or not is in the **per-Pauli $\lambda_P$**.

**Results.**

| Pauli class | predicted (indep. baseline) | measured | Δ |
|---|---|---|---|
| IX, XI, IY, YI (single-X/Y marginals) | 0.9000 | 0.8890 – 0.9055 | ≈ 0 |
| IZ, ZI, ZZ (Z-immune) | 1.0000 | 1.0000 | 0 |
| XZ, ZX, YZ, ZY (one X/Y, one Z) | 0.9000 | 0.8847 – 0.9065 | ≈ 0 |
| **XX, XY, YX, YY** | **0.8100** | **1.0000** | **+0.1900** ⚡ |
| F_RC | 0.8960 | **0.9447** | **+0.0487** |

**Walking the critical Pauli — XX.** Under correlated `{II:0.95, ZZ:0.05}`:

- The `ZZ` error fires (probability 0.05). It hits both qubits with a `Z`.
- The `XX` observable measures `X` on each qubit. `Z` anticommutes with `X`, so each side flips → sign flips on *both* qubits in the same shot → `(−1)(−1) = +1`.
- The `XX` reading is `+1` even when the error fires. Verdict: `λ_XX = 1.0` exactly.

The independent prediction would have been `λ_X · λ_X = 0.90 · 0.90 = 0.81`. The
gap `+0.19` is **the crosstalk fingerprint**: only correlated `Z`s on both qubits
can cancel into `+1` on `XX`. Independent dephasing cannot — two separate flips
are not synchronised. Same logic applies to `XY, YX, YY` — both observables are
"flippable" by `Z`, both flips fire together → cancel → `λ = 1.0`.

![Same +0.19 spike under G=I](figures/01b_crosstalk_signature_identity.png)

**Verdict.** CB has called out correlated noise. `F_RC = 0.9447 > 0.8960` —
crosstalk makes the *average* look ~5% **better** than the matching independent
noise. The per-Pauli view reverses the verdict.

### Exp 5 — N=2, G=CZ, bit_flip — *and the orbit-geomean explainer*

**Setup.** $N = 2$, $K = 15$, `G=CZ` (order 2), $m_1 = 4$, $m_2 = 8$, `shots=200`, `L=30`,
`noise = bit_flip{I:0.95, X:0.05}` tensored.

**$C(P) = CZ^4(P) = P$** ($CZ^2 = I \Rightarrow CZ^4 = I$; $\varepsilon = +1$).
**$\hat C(\rho)$ at $m_1 = 4$** — Ĝ = Λ∘CZ; $R_i$ are 2q random Paulis; $\Lambda$ is bit_flip
tensored to 2 qubits:
$$\hat C(\rho) = R_4 \circ \Lambda \circ CZ \circ R_3 \circ \Lambda \circ CZ \circ R_2 \circ \Lambda \circ CZ \circ R_1 \circ \Lambda \circ CZ \circ R_0(\rho).$$
Between cycles the CZ factor rotates the running observable around its orbit
(see the rule below).

**What's new.** CZ is a non-Pauli Clifford — like H but on two qubits. It
**rotates Paulis** between cycles, on a specific pattern:

> **CZ rule:** `X` or `Y` on a qubit → drops a `Z` on the partner (and toggles `I↔Z`, `X↔Y` on it). `I` or `Z` on a qubit → frozen.

So CZ has **fixed Paulis** `{ZI, IZ, ZZ}` (every qubit holds an I or Z — nothing to rotate), and **2-cycle orbits** for the rest: `{XI ↔ XZ}`, `{IX ↔ ZX}`, `{YI ↔ YZ}`, `{IY ↔ ZY}`, `{XX ↔ YY}`, `{XY ↔ YX}`.

#### The orbit-geomean rule (derivation)

A single dressed cycle is `(R∘CZ∘Λ)`. After the Pauli twirl, the noise per
position is $\Lambda_T(P) = \lambda_P \cdot P$ — but CZ rotates `P → P'` between cycles. So the
observable that started as `P` is, at the next position, `P' = CZ·P·CZ`, which
acquires `Λ_T(P') = λ_{P'} · P'`. After two cycles, `P' → P` again (orbit length
2). Over $m$ cycles (m even):

$$
\langle P, \hat C(\rho)\rangle \;\propto\; \lambda_P \cdot \lambda_{P'} \cdot \lambda_P \cdot \lambda_{P'} \cdots \;\;\text{($m$ factors)}
\;=\; (\lambda_P \cdot \lambda_{P'})^{m/2}
\;=\; \Big(\sqrt{\lambda_P \cdot \lambda_{P'}}\Big)^m.
$$

So the **recovered** decay is the geometric mean: `λ_P^recovered = √(λ_P · λ_{P'})`. The two-length ratio measures *this* — the geomean over the orbit.

**Worked example — `XI` under bit_flip.**
1. Compute bare λ from the commute formula on the tensored channel
   `{II:0.9025, IX:0.0475, XI:0.0475, XX:0.0025}`:
   - $\lambda_{XI}^{\text{bare}}$: which 2q errors commute with `XI`? `II`✓, `IX`✓ (no overlap with q0=X), `XI`✓, `XX`✓. All commute → `λ_XI^bare = 1.00`.
   - $\lambda_{XZ}^{\text{bare}}$: `II`✓, `IX` anticomm (X on q1 anticomm Z on q1) → −, `XI`✓, `XX` anticomm → −. So `λ_XZ^bare = (0.9025 + 0.0475) − (0.0475 + 0.0025) = 0.90`.
2. CZ orbit of `XI` is `{XI, XZ}`. Geomean: `λ_XI^recovered = √(1.00 · 0.90) ≈ 0.9487`.
3. **Measured: 0.9499.** ✓

**Results (all 15 Paulis).**

| Pauli | expected | measured | Δ |
|---|---|---|---|
| IX, XI | 0.9487 | 0.9428, 0.9499 | small |
| IY, YI | 0.8538 | 0.8593, 0.8492 | small |
| IZ, ZI | 0.9000 | 0.8992, 0.8870 | small |
| XX, XY, YX, YY | 0.9000 | 0.9069, 0.9093, 0.9011, 0.8980 | all \|Δ\| ≤ 0.009 |
| XZ, ZX | 0.9487 | 0.9492, 0.9456 | small |
| YZ, ZY | 0.8538 | 0.8533, 0.8611 | small |
| ZZ | 0.8100 | 0.8133 | +0.003 |
| **F_RC** | **0.8947** | **0.8950** | **+0.0003** |

**Verdict.** The orbit-geomean predictor reproduces every measured $\lambda_P$ within
shot noise. CZ works.

> **Why this matters (and why `factorization_test` is wrong here).** The
> factorization test asks: does $\lambda_{A \otimes B} = \lambda_A \cdot \lambda_B$ hold? Under CZ, even with
> *perfectly independent* noise, no: e.g. $\lambda_{XI}$ is now an orbit geomean
> (`√(1·0.90) ≈ 0.9487`), so `λ_XI · λ_IX = 0.9487 · 0.9487 = 0.90` while
> $\lambda_{XX}$ (also an orbit geomean of bare 0.90's) = 0.90. Numerically they happen
> to agree here but the framework is dirty — `factorization_test` will throw
> false alarms once the bare per-qubit λ's are anisotropic. The **orbit
> predictor** is the right yardstick on a rotating gate. (Fix for hardware is
> open under #6.)

### Exp 6 — N=2, G=CZ, correlated `ZZ` — *the payoff*

**Setup.** Same as Exp 5, but `noise = {II:0.95, ZZ:0.05}` (Exp 4's correlated
channel — now attached to a real entangling gate).

**$C(P) = CZ^4(P) = P$**, $\varepsilon = +1$.
**$\hat C(\rho)$ at $m_1 = 4$** — same chain as Exp 5, but $\Lambda$ is now the correlated 2q error
`{II:0.95, ZZ:0.05}`:
$$\hat C(\rho) = R_4 \circ \Lambda \circ CZ \circ R_3 \circ \Lambda \circ CZ \circ R_2 \circ \Lambda \circ CZ \circ R_1 \circ \Lambda \circ CZ \circ R_0(\rho).$$

**Noise $\rightarrow \lambda_P$.** Predictor uses the **per-qubit marginal** `{I:0.95, Z:0.05}` as
the independent baseline (= dephasing-0.05 per qubit), takes bare per-qubit
products, then orbit-geomeans over CZ. **Measured $\lambda_P$ deviating from this
prediction = real crosstalk.**

**Results.**

| Pauli | expected (indep. baseline) | measured | Δ |
|---|---|---|---|
| IX, IY, XI, YI | 0.9000 | 0.8889 – 0.9056 | ≈ 0 |
| IZ, ZI, ZZ | 1.0000 | 1.0000 | 0 |
| XZ, YZ, ZX, ZY | 0.9000 | 0.8883 – 0.8938 | ≈ 0 |
| **XX, XY, YX, YY** | **0.8100** | **1.0000** | **+0.1900** ⚡ |
| F_RC | 0.8960 | **0.9434** | **+0.0474** |

**Walking the critical Pauli — XX under CZ + correlated `ZZ`.**

1. Bare $\lambda$ of `XX` under correlated `{II:0.95, ZZ:0.05}`: the `ZZ` error flips both X's together → cancel → `λ_XX^bare = 1.00`. (Same logic as Exp 4.)
2. CZ orbit of `XX` is `{XX, YY}`. Bare $\lambda_{YY}$ under the same noise: `Z` anticommutes with `Y` on each side, two flips cancel again → `λ_YY^bare = 1.00`.
3. Orbit geomean: `λ_XX^recovered = √(1.00 · 1.00) = 1.00`.
4. **Measured 1.0000.** ✓

Compared to the independent baseline (per-qubit dephasing-0.05 instead of
correlated): bare `λ_X = 0.90`, bare `λ_Z = 1.0`. For the `{XX, YY}` orbit each
bare λ would be `λ_X·λ_X = 0.81`, geomean `0.81`. The **gap** between the
correlated measurement (1.00) and the indep baseline (0.81) **is** the
crosstalk on the gate — exactly the +0.19 of the headline figure.

**Verdict.** Crosstalk detected on a real entangling gate, on exactly the four
Paulis the rule predicts. `F_RC = 0.943` vs baseline `0.896` (+5%) — measured
process fidelity looks *better* than the independent-noise prediction, the same
inversion as Exp 4 but now on CZ. The per-Pauli $\lambda_P$ view exposes the trade
that $F_{RC}$ alone hides.

### Exp 7 — N=3, G=CZ, bit_flip — scaling

**Setup.** $N = 3$, $K = 30$ random Paulis from 63 non-identity 3-qubit Paulis,
`G=CZ` on `(q0, q1)` (q2 idles), $m_1 = 4$, $m_2 = 8$, `shots=200`, `L=30`,
`noise = bit_flip(0.05)` tensored to 3 qubits.

**$C(P) = CZ^4(P) = P$**, $\varepsilon = +1$.
**$\hat C(\rho)$ at $m_1 = 4$** — same chain as Exp 5, but now on 3 qubits: $R_i$ are 3q
random Paulis (64 options each), `CZ` acts on `(q0, q1)` only with q2 idling,
and $\Lambda$ is bit_flip tensored to 3 qubits:
$$\hat C(\rho) = R_4 \circ \Lambda \circ CZ \circ R_3 \circ \Lambda \circ CZ \circ R_2 \circ \Lambda \circ CZ \circ R_1 \circ \Lambda \circ CZ \circ R_0(\rho).$$

**Noise $\rightarrow \lambda_P$.** Same orbit-geomean predictor; orbits are now 3q. The idle
qubit's label stays frozen — only the (q0, q1) pair rotates: e.g.
`IXX → IYY` (q2 frozen as I), `ZXX → ZYY`, etc.

**Results (sample of 30 measured Paulis).**

| Pauli | expected | measured | Δ |
|---|---|---|---|
| `XII` | 1.0000 | 1.0000 | 0 |
| `IZI` | 0.9000 | 0.9019 | +0.002 |
| `IXZ` | 0.9487 | 0.9534 | +0.005 |
| `YYY` | 0.8100 | 0.8409 | +0.031 |
| `ZZZ` | 0.7290 | 0.7171 | −0.012 |
| `YZZ` | 0.7290 | 0.7716 | +0.043 (worst single Δ) |
| F_RC (30 Paulis) | **0.8490** | **0.8544** | **+0.0054** |

**Walking the critical Pauli — `ZZZ`.** Three-qubit observable. Bit_flip on
each qubit means each `Z` independently sees `X` errors with p=0.05.
Per-qubit `λ_Z = 1 − 2(0.05) = 0.90`. Independent product: `0.9³ = 0.729`.
CZ acts only on (q0,q1) — `Z` and `Z` on those two qubits are CZ-fixed (slide
rule: `I/Z → frozen`), so `ZZZ → ZZZ`. Orbit length 1, predicted `0.729`.
**Measured 0.7171.** ✓ (small undershoot at the shot floor).

### Orbit predictor validation across CZ runs

![Expected vs measured λ_P across Exp 5 and Exp 7 (45 Paulis)](figures/02_orbit_validation.png)

All 45 Paulis cluster on `y = x`. The predictor scales from N=2 to N=3 with
no qualitative change — the same orbit machinery just walks a longer chain.

**Verdict.** The K-subset path, 3-qubit orbits (with spectator qubits), and
N-qubit noise tensoring all behave. No NaN at $m_2 = 8$ even for the
lowest-fidelity Paulis (`λ ≈ 0.73`). Machinery scales.

---

## 3 · Analysis

### 3.1 — Why exactly four Paulis light up

A `Z` error anticommutes with `X` and `Y` (sign flip) and commutes with `I` and
`Z` (invisible). For a 2-qubit observable $P = P_0 \otimes P_1$ under a `ZZ` error,
the net sign is the **product** of per-qubit flips:

| P_0 flippable? (X/Y) | P_1 flippable? (X/Y) | flips | λ_P |
|---|---|---|---|
| both immune (Z/I) | — | 0 | 1.0 — `{ZI, IZ, ZZ}` (3 Paulis) |
| one flippable, one immune | — | 1 | `1 − 2q = 0.90` — 8 Paulis |
| **both flippable** | — | **2 → cancel** | **1.0** — `{XX, XY, YX, YY}` (4 Paulis) |

The two flips cancel inside the same shot. Independent dephasing has the same
*per-qubit* flip rate but the flips aren't synchronised — `XX` factorises to
`λ_X · λ_X = 0.81`, not `1.0`. **That cancellation is the signature; the 0.19
gap is its strength.**

### 3.2 — Why $F_{RC}$ *inflates* instead of dropping

Crosstalk *makes 4 of 15 Paulis look perfect*, and `F_RC = avg λ_P` averages
that up:

$$
\begin{aligned}
F_{RC}^{\text{indep}}      &= (3 \cdot 1.0 + 8 \cdot 0.90 + 4 \cdot 0.81)/15 = 0.8960 \\
F_{RC}^{\text{correlated}} &= (3 \cdot 1.0 + 8 \cdot 0.90 + 4 \cdot 1.00)/15 = 0.9460 \\
\text{predicted gap}       &= +0.0500 \quad\leftrightarrow\quad \text{measured (Exp 6)} = +0.0474.
\end{aligned}
$$

Two qubits with correlated errors look ~5% *more reliable on average* than two
qubits with the matching independent errors. SRB would report the higher
number and call it a win. **CB exposes the trade because it never collapses
the 15 Paulis into one mean.**

### 3.3 — Orbit predictor vs `factorization_test` on a rotating gate

`factorization_test` checks $\lambda_{A \otimes B} = \lambda_A \cdot \lambda_B$ — exact under independent
noise *on the identity cycle* (Exp 3 ✓). Under CZ this is no longer true even
under perfectly independent noise: CZ rotates `XI ↔ XZ`, so the recovered
$\lambda_{XI}$ is a geomean over its orbit; $\lambda_{XX}$ is a geomean over a different
orbit; the product `λ_XI · λ_IX` doesn't equal $\lambda_{XX}$ in general. The test
would false-alarm.

The **orbit-geomean predictor** is the right baseline: follow `P` around its
orbit (`Q ← G·P·G†` until it returns), take bare per-qubit-product $\lambda$ at
each step, geomean. Under independent noise this is exact (Exp 5 ✓). Under
correlated noise the bare-product step is wrong on the "both flippable"
Paulis → measurement pulls away → **that gap is the honest crosstalk signal
on a rotating gate** (Exp 6 ✓).

### 3.4 — Scaling

Exp 7 is the first run that touches the three pieces that only appear at N≥3:
the K-subset path (30 of 63 Paulis), 3-qubit orbits with a spectator qubit,
and 3-qubit noise tensoring. All three behaved. No NaN at $m_2 = 8$ — the
lowest expected $\lambda_P$ was `0.729` (on `ZZZ`/`YZZ`), well above the shot
floor. The data point needed before trying N=10 on a stabilizer simulator.

---

## 4 · Next steps

| Issue | Task | Blocker |
|---|---|---|
| **#5** | N=10 stabilizer-sim demo | labelled `UnitaryGate` doesn't run on the stabilizer backend → rebuild cycle from native Cliffords (`qc.cz`) and re-attach noise; add per-pair correlated `ZZ` with non-uniform marginals; plot $F_{RC}$ vs N |
| **#6** | IBM hardware run | swap Aer → `QiskitRuntimeService` SamplerV2; turn `factorization=True`; needs orbit-aware fix to `factorization_test` for rotating gates |

Working notes (gotchas, bugs caught, deferred items, reproducibility) live at
[`personal/CB_notes.md`](personal/CB_notes.md) — for my reference, not part of
this report.
