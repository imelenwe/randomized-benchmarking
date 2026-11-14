"""Conditional diffusion for delta: p(delta | 36 CB features).

Notation: x_0 = delta, x_1..x_T = progressively noisier latents.

    FORWARD (fixed, no learning) -- the closed-form jump:

        x_t = sqrt(alpha_bar_t) * x_0 + sqrt(1 - alpha_bar_t) * eps,   eps ~ N(0,1)

    REVERSE (this is what learns) -- the walk, one step at a time:

        mu_theta(x_t, t) = (1/sqrt(alpha_t)) * ( x_t - ((1 - alpha_t)/sqrt(1 - alpha_bar_t)) * eps_hat )

    alpha_t     = per-step retention        -> used by the reverse walk (step 4)
    alpha_bar_t = alpha_1 * ... * alpha_t   -> used by the forward jump (step 1b)

Conditioning: c = the 36 CB features. Plays the role of the class embedding e_c.
Control to beat: gaussian_net.py -- RMSE 0.006, but |z|>2 = 8.6% (ideal 4.6%).

Build order (see diffusion_plan.md):
    1a. noise_lookup(T)        -- the alpha table. No learning, no data.
    1b. add_noise(x_0, t, ...) -- the forward jump above.
    2.  NoisePredictor         -- MLP: (x_t, t, c) -> eps_hat
    3.  train_diffusion()      -- random t, noise x_0, MSE(eps_hat, eps)
    4.  sample_posterior()     -- reverse walk -> 1000 deltas per run
"""
import numpy as np
import torch
import copy as copy
from IPython.display import display


# Cosine schedule + the s=0.008 offset come from:
#   Nichol & Dhariwal, "Improved Denoising Diffusion Probabilistic Models",
#   ICML 2021, arXiv:2102.09672 -- Section 3.2, Eq. 17:
#       alpha_bar_t = f(t)/f(0),   f(t) = cos( ((t/T + s)/(1 + s)) * pi/2 )^2
#
# Their reason for s: without it, alpha_bar_1 sits so close to 1 that step 1 adds
# almost no noise, and they found the net then can't predict eps accurately there.
# (Recovering eps means dividing by sqrt(1 - alpha_bar_t) -- 0.0157 at t=1 with s=0,
#  so any error gets amplified ~64x.) The offset gives the first steps real noise.
#
# CAVEAT: they picked 0.008 for IMAGES -- chosen so sqrt(beta_0) sits just under the
# pixel bin size 1/127.5. Our x_0 is a standardized delta, not pixels, so 0.008 is
# inherited, not derived for our problem. It only affects the first few steps
# (alpha_bar_T is ~1e-33 for s = 0, 0.008, or 0.05 alike), so it's low-risk to keep.
def noise_lookup(T=100, s=0.008):
     """Cosine lookup -> (alpha, alpha_bar), each length T, index 0 = step t=1.

    Cosine picks the alpha_bar_t CURVE directly (falling 1 -> 0), then backs out
    alpha_t = alpha_bar_t / alpha_bar_{t-1}.  Linear picks alpha_t instead and lets
    the product land wherever -- at T=100 it lands at alpha_bar_T = 0.364, so x_T
    still holds 60% of x_0 and is NOT N(0,1).  Cosine gives alpha_bar_T ~ 0 for any
    T with no tuning, which is what sampling needs as its starting point.
    """
     steps = np.arange(T+1) # 0..T, EVERY step at once -- this is not "a t", it's the whole table's index
     f = np.cos(((steps/T)+s)/(1+s) * np.pi/2) **2
     alpha_bar = f/f[0] # force alpha_bar_0 = 1 exactly f[0] = 0.9998 (the s shift), not 1. This forces alpha_bar_0 = 1 → t=0 means untouched
     alpha = alpha_bar[1:]/alpha_bar[:-1] #[1:] = elems 1..100, [:-1] = elems 0..99 ie all but the last → gives alpha_bar_t / alpha_bar_(t-1) = alpha_t, for all t at once, no loop
     alpha = np.clip(alpha, 1e-3, 0.9999) #raw cosine → alpha_T = exactly 0; step 4 divides by sqrt(alpha_t) → 1/sqrt(0) = inf → NaN. Floor keeps it finite; alpha_bar_T still ~1e-33
     alpha_bar = np.cumprod(alpha) #the clip changed alpha, so the promise alpha_bar_t = alpha_1·…·alpha_t broke. Rebuilding restores it — else add_noise and the sampler run different physics
     return (torch.tensor(alpha, dtype=torch.float32), torch.tensor(alpha_bar, dtype=torch.float32))



def add_noise(x_0, t, alpha_bar):
    """Forward jump (fixed, no learning): x_0 -> x_t, and the eps we used.

    x_0       : (N, 1) standardized deltas
    t         : (N,)   step index per row, 0-based (index 0 = step t=1)
    alpha_bar : (T,)   from noise_lookup

    Returns (x_t, eps), both (N, 1). eps is the training label -- we drew it,
    so we know it.
    """
    ab = alpha_bar[t].unsqueeze(1) #Shape surgery, and it's load-bearing. x_0 is (N,1). Multiplying (N,) by (N,1) makes broadcasting produce (N,N) — a silent, wrong, memory-exploding result. (N,1) * (N,1) gives (N,1), correct. This is the single easiest bug to write here.
    eps = torch.randn_like(x_0) # draws N(0,1) with x_0's shape, dtype, and device
    x_t = ab.sqrt() * x_0 + (1-ab).sqrt() * eps # rmbr ab is alpha_bar
    return x_t, eps


def time_step_embed(t, dim=16):
    """Sinusoidal step embedding -- same trick as Transformer positional encoding.

    t   : (N,) integer step indices, 0..T-1
    dim : embedding width, EVEN (our design choice -- Transformers use 512+ for
          long sequences; we only have 100 steps, so 16 is plenty)
    Returns (N, dim): each row is `dim` numbers reading t at different frequencies,
    not one number.
    t=  3  ->  [ 0.141   0.296   0.030   0.003  -0.990   0.955   1.000   1.000 ]
    t= 50  ->  [-0.262  -0.959   0.479   0.050   0.965   0.284   0.878   0.999 ]
    t= 97  ->  [ 0.380  -0.272   0.825   0.097  -0.925  -0.962   0.565   0.995 ]

    sin block:  [ 0.141,  0.296,  0.030,  0.003 ]
    cos block:  [-0.990,  0.955,  1.000,  1.000 ]
    full row :  [ 0.141,  0.296,  0.030,  0.003, -0.990, 0.955, 1.000, 1.000 ]   <- 8 numbers, matches d=8 example earlier


    output row  =  [ sin(t·f0), sin(t·f1), sin(t·f2), sin(t·f3),  cos(t·f0), cos(t·f1), cos(t·f2), cos(t·f3) ]
                \_____________ sin BLOCK (uses all 4 freqs) ____________/  \_____________ cos BLOCK (same 4 freqs) ____________/


    freq_i  =  1 / 10000^(2i/d)          <- one frequency per i, i = 0 .. d/2-1

    input:   t    (N,)      one integer step per row
    output:  (N,d)  d different sin/cos readings of that SAME t, at different scales
    returns [sin( t · freq_i ), cos( t · freq_i )]
    """
    i = torch.arange(dim // 2, dtype=torch.float32)
    freq = 1.0/(10000 **(2*i/dim))
    args = t.float().unsqueeze(1) * freq.unsqueeze(0)
    return torch.cat([torch.sin(args), torch.cos(args)], dim=1)


import torch.nn as nn

class NoisePredictor(nn.Module): # preditcs epsilon_hat
    def __init__(self, cond_dim=36, hidden=128, time_step_dim=16):
        super().__init__()
        self.time_step_dim = time_step_dim
        input_dim = 1 + self.time_step_dim + cond_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 1), # one number: eps_har
        )

    def forward(self, x_t, t, c):
        t_embd = time_step_embed(t, dim=self.time_step_dim)
        h = torch.cat([x_t, t_embd, c], dim=1)
        return self.net(h)


def train_diffusion(Xtr, ytr, alpha_bar, T=100, hidden=128, epochs=1000,
                     lr=3e-4, val_frac=0.15, seed=0, verbose=True):
    """Xtr = c (36 features), ytr = x_0 (standardized delta).
    Trains NoisePredictor by noise-regression MSE. Same val-selection
    discipline as train_gaussian: fixed seed, best weights by VAL loss.
    """
    torch.manual_seed(seed)

    g = torch.Generator().manual_seed(seed)
    shuffled_idx = torch.randperm(len(Xtr), generator=g) # return random shuffled order of integers
    n_val = int(val_frac * len(Xtr))
    val_idx, train_idx = shuffled_idx[:n_val], shuffled_idx[n_val:] # first 15% is val

    c_train, x0_train = Xtr[train_idx], ytr[train_idx] # note x0_train has the labels
    c_val,   x0_val   = Xtr[val_idx],   ytr[val_idx]
    #display(c_train[:5])
    #display(x0_train[:5])

    # fix ONE noise draw for validation, once, before training starts
    t_val = torch.randint(0, T, (len(x0_val),), generator=g)
    x_t_val, eps_val = add_noise(x0_val, t_val, alpha_bar)

    model = NoisePredictor(cond_dim=Xtr.shape[1], hidden=hidden)
    opt   = torch.optim.Adam(model.parameters(), lr=lr)

    best_val_loss, best_state, best_epoch = float("inf"), None, None
    for epoch in range(epochs):
        model.train()
        t = torch.randint(0, T, (len(x0_train),))
        x_t, eps = add_noise(x0_train, t, alpha_bar) # labels are noised here
        eps_hat  = model(x_t, t, c_train)
        loss = ((eps - eps_hat) ** 2).mean()
        opt.zero_grad(); loss.backward(); opt.step()

        model.eval()
        with torch.no_grad():
            val_loss = ((eps_val - model(x_t_val, t_val, c_val)) ** 2).mean().item()
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
        if verbose and epoch % 100 == 0:
            print(f"epoch {epoch:3d}  train MSE {loss.item():.4f}  val MSE {val_loss:.4f}")

    model.load_state_dict(best_state)
    if verbose:
        print(f"restored best (by val MSE): {best_val_loss:.4f} at the best epcoh: {best_epoch}")
    return model


def sample_posterior_inference(model, conditioned_on, alpha, alpha_bar, num_steps=100, num_samples=1000, seed=0):
    random_generator = torch.Generator().manual_seed(seed)
    num_rows = conditioned_on.shape[0]
    total_samples = num_rows * num_samples

    # model pairs x_t and c by row position, so they need equal row counts. Here x_t has more rows than c but we want to concat x_t and c side by side in the model's forward method. # e.g. condition = [(10,10), (20,20)], num_samples=3:
    #   repeat_interleave -> [(10,10),(10,10),(10,10), (20,20),(20,20),(20,20)]
    # block order (not .repeat's tiling) is what lets the final
    # .reshape(num_rows, num_samples) recover each row's own cloud of samples.

    repeated_condition = conditioned_on.repeat_interleave(num_samples, dim=0)

    #   current_value = Start:   x_T  ~  N(0,1) <- THIS line Repeat for t = T,...,1:  ...
    current_value = torch.randn(total_samples, 1, generator=random_generator) 

    model.eval()
    with torch.no_grad():
        for step in range(num_steps, 0, -1): # loop in reverse 100...0
            step_index = step - 1  # arrays are 0-indexed: index 0 = step t=1
            time_batch = torch.full((total_samples,), step_index, dtype=torch.long) # add a batch number for each row

            predicted_noise = model(current_value, time_batch, repeated_condition)

            alpha_t     = alpha[step_index]
            alpha_bar_t = alpha_bar[step_index]

            # mu_theta: undo one step's worth of the forward corruption
            predicted_mean = (1 / alpha_t.sqrt()) * (
                current_value - ((1 - alpha_t) / (1 - alpha_bar_t).sqrt()) * predicted_noise
            )

            # fresh randomness every step EXCEPT the last -- that's what turns
            # identical starting points into a spread-out posterior cloud
            if step > 1:
                random_noise = torch.randn(total_samples, 1, generator=random_generator)
            else:
                random_noise = torch.zeros(total_samples, 1)

            step_noise_scale = (1 - alpha_t).sqrt()
            current_value = predicted_mean + step_noise_scale * random_noise
            # current_value now holds x_{t-1} -- loop back and do it again

    # x_0: still STANDARDIZED delta -- caller un-standardizes:
    # real_delta = samples * delta_std + delta_mean
    return current_value.reshape(num_rows, num_samples)

