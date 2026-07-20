# Conditional diffusion — build plan

**Goal:** sample the posterior p(δ | 36 features).
**Control to beat:** Gaussian net — RMSE 0.006 (good), |z|>2 = 8.6% (bad, ideal 4.6%).
**Where:** `conditional_diffusion.py`, driven from `sbi_experiments.ipynb`.

## Steps

- [x] **1a. Noise lookup** — `noise_lookup(T)`. Cosine (Nichol & Dhariwal Eq. 17).
      Returns (alpha, alpha_bar), each length T, index 0 = step t=1.
      *Done:* alpha_bar 0.9994 → 2.4e-07, cumprod promise holds.

- [x] **1b. Noiser** — `add_noise(x_0, t, alpha_bar)` → (x_t, eps). Blends x_0 with
      noise using the 1a table (called in, not called by, add_noise).
      *Done:* t=0 gives x_t ≈ x_0; t=99 gives x_t ≈ eps (x_0 fully erased).

- [x] **2a. Time embed** — `time_step_embed(t, dim=16)`. Sinusoidal, sin/cos
      blocks concatenated (not interleaved). Turns 1 number into 16.
      *Done:* verified against hand-worked example (t=3,50,97), exact match.

- [x] **2b. Noise predictor** — `NoisePredictor` MLP: input = [x_t | time_step_embed(t) | c]
      (1 + 16 + 36 = 53 wide) → eps_hat. ~23.5K params.
      *Done:* forward pass verified, output shape (N,1).

- [ ] **3. Train** — `train_diffusion()`. Random t, noise δ_0, MSE(eps_hat, eps).
      *Check:* loss drops.

- [ ] **4. Sample** — `sample_posterior()`. Reverse loop → 1000 δ per run.
      *Check:* mean/std → `report()` → head-to-head vs Gaussian net.

## Gotcha

Standardize δ in, un-standardize samples out. δ spans 0.02–0.25; diffusion
assumes ~N(0,1). Lives inside steps 3 and 4.

## Decisions

| | |
|---|---|
| T | 100 |
| samples per run | 1000 |
| target | δ only (1-D) — scaffold for multi-D later |