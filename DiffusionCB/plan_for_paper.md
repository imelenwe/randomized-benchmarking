# Plan for paper — what's publishable in DiffusionCB

**Big picture (one line):** From ordinary CB data alone, work out whether the noise
has *memory* (non-Markovian) — something standard CB cannot do.

**Why it matters:** Standard CB/RB squash all the data into one number (λ). That number
**cannot** tell memory-noise apart from memoryless-noise — they can give the exact same λ.
We keep the *raw* data (normally thrown away) and recover the difference.

---

## The three publishable angles (small → big)

### 1. The core result — "don't throw away your raw CB data"  ✅ *(shown in sim, 2 of 3 noise types)*
- **Says:** averaging your CB data hides memory in the noise; the raw data reveals it.
- **Evidence so far:** at *matched λ* (same decay rate), **memory's variance across
  sequences grows with sequence length, while jitter's stays flat**. A simple variance
  check separates them — even though λ calls them identical.
- **Status:** proven in simulation for **memory vs jitter**. Drift (the 3rd type) not yet checked.

### 2. The method — an automatic noise classifier from raw CB data  ⬜
- **Says:** a method reads raw CB data and tells you which noise type it is, with a
  confidence level, and it **beats a simple hand-rule**.
- **Needs:** (a) pin down the exact task, (b) build a dumb hand-rule + measure its score,
  (c) build the AI model (maybe diffusion) and beat that score — especially in the hard
  cases where λ is useless.
- **Status:** not started.

### 3. The hardware proof — explain a real anomaly  ⬜
- **Says:** run it on a real IBM chip and explain the **λ_XX = 0.42 anomaly** we already
  saw on ibm_fez; cross-check with an independent test (different gate implementations).
- **Why it lands:** simulation alone is weaker; a real, previously-unexplained effect is
  what referees love. We already *have* the anomaly waiting to be explained.
- **Status:** not started; needs QPU time.

### Bonus: the "limits" result  ⬜
- Even a partly-negative result — *"here's exactly when you can and can't tell the noises
  apart from CB data"* — is publishable and honest.

---

## Plain bottom line

The core paper = **"raw CB data lets you detect non-Markovian noise that standard CB misses."**
The AI model (#2) and the hardware run (#3) make that core **stronger and more convincing** —
they are not separate ideas, they are amplifiers of the same one message.

## Path to get there

1. **Finish the 3-way separation** — add drift; does the variance check separate all three?
2. **Define the model's task + build the simple baseline** — a concrete score to beat.
3. **Build the AI model** — it must beat the baseline.
4. **Run on real hardware** — explain the λ_XX anomaly.

*(Detailed technical spec lives in `nonmarkovian_cb_diffusion_spec.md`; this file is the
plain-language paper picture so we don't lose sight of the goal.)*