"""Gaussian-output MLP baseline: 36 features -> N(mu, sigma) over delta.

The control experiment for the diffusion model. Outputs a mean and spread
(a single bell curve) for delta; trained by Gaussian negative log-likelihood.
"""
import copy
import torch
import torch.nn as nn
import torch.nn.functional as F


class GaussianNet(nn.Module):
    def __init__(self, in_dim=36, hidden=128):
        # nn.Linear(a, b) is a fully-connected (a.k.a. dense) layer: every one of
        # the a inputs connects to every one of the b outputs.
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 2),                 # output mean and sigma, like the VAE encoder
        )

    def forward(self, x):
        out = self.net(x)                         # shape (N, 2)
        # out[ ... , ... ] — the comma indexes two dims: [rows, columns].
        # ':' (before comma) — all rows (all N examples).
        # '0:1' (after comma) — a slice of columns: index 0 up to but not incl. 1
        #   -> just column 0, kept 2-D as (N, 1).
        mu = out[:, 0:1]
        sigma = F.softplus(out[:, 1:2]) + 1e-3
        # raw output (any number) -> softplus (positive) -> +1e-3 (safely away from 0)
        #   -> a valid sigma, shape (N, 1), ready to define δ ~ N(μ, σ).
        return mu, sigma


# ---------------------------------------------------------------------------
# Gaussian NLL — derivation (why this loss is correct)
#
# Principle: maximum likelihood.
# The net predicts a bell curve over δ:  p(δ|x) = N(δ; μ, σ²).
# Make the TRUE δ as likely as possible under that bell
#   = maximize likelihood
#   = minimize negative log-likelihood (NLL).
#
# Step 1 — Gaussian density (prob. of true y under the predicted bell):
#     N(y; μ, σ²) = 1/(σ·√(2π)) · exp( −(y−μ)² / (2σ²) )
# Step 2 — take the log:
#     log N = −log σ − ½·log(2π) − (y−μ)²/(2σ²)
# Step 3 — negate (we minimize, so flip sign):
#     −log N = log σ + ½·log(2π) + (y−μ)²/(2σ²)
# Step 4 — drop the constant ½·log(2π)
#          (doesn't depend on μ, σ, or any weight → can't move the minimum):
#     NLL = log σ + (y−μ)²/(2σ²)
#
# Match to the code below:
#     torch.log(sigma)  +  0.5 * ((y - mu)/sigma)**2
#     0.5 * ((y−μ)/σ)²  ==  (y−μ)²/(2σ²)     ← exact match
#
# Note: freeze σ constant and this reduces to plain MSE — Gaussian NLL is
# MSE generalized to also learn the uncertainty.
# ---------------------------------------------------------------------------
def gaussian_nll(mu, sigma, y):
    return (torch.log(sigma) + 0.5 * ((y - mu) / sigma) ** 2).mean()


def train_gaussian(Xtr, ytr, hidden=128, epochs=500, lr=3e-4,
                   val_frac=0.15, seed=0, verbose=True):
    """Full-batch Adam, weights selected by VALIDATION NLL.

    Two things matter for calibration + reproducibility:
    - fixed seed  -> same init every run (kills run-to-run flakiness).
    - select best weights by VAL NLL, not train NLL: minimizing train NLL
      rewards over-confidence (tiny sigma fit to train errors), which
      generalizes to too-small sigma on test. Val NLL penalizes that.
    """
    torch.manual_seed(seed)

    # carve a validation slice out of the training data
    g = torch.Generator().manual_seed(seed)
    perm  = torch.randperm(len(Xtr), generator=g)
    n_val = int(val_frac * len(Xtr))
    vi, ti = perm[:n_val], perm[n_val:]
    Xt, yt, Xv, yv = Xtr[ti], ytr[ti], Xtr[vi], ytr[vi]

    model = GaussianNet(in_dim=Xtr.shape[1], hidden=hidden)
    opt   = torch.optim.Adam(model.parameters(), lr=lr)

    best_val, best_state = float("inf"), None
    for epoch in range(epochs):
        model.train()
        mu, sigma = model(Xt)
        loss = gaussian_nll(mu, sigma, yt)
        opt.zero_grad(); loss.backward(); opt.step()

        model.eval()
        with torch.no_grad():
            vmu, vsig = model(Xv)
            vloss = gaussian_nll(vmu, vsig, yv).item()
        if vloss < best_val:                          # select on VAL, not train
            best_val   = vloss
            best_state = copy.deepcopy(model.state_dict())
        if verbose and epoch % 100 == 0:
            print(f"epoch {epoch:3d}  train NLL {loss.item():.4f}  val NLL {vloss:.4f}")

    model.load_state_dict(best_state)
    if verbose:
        print(f"restored best (by val NLL): {best_val:.4f}")
    return model