"""Shared evaluation harness — identical metrics + plots for every estimator,
so Gaussian net and diffusion are compared honestly.

report(mu, sigma, y) takes predicted mean + spread and the true delta.
It is model-agnostic: for the Gaussian net pass model(X); for diffusion pass
the mean and std of the sampled posterior.
"""
import numpy as np
import torch
import matplotlib.pyplot as plt


def _np(t):
    """Tensor or array -> flat numpy."""
    if torch.is_tensor(t):
        t = t.detach().cpu().numpy()
    return np.asarray(t).ravel()


def report(mu, sigma, y, title="model"):
    mu, sigma, y = _np(mu), _np(sigma), _np(y)

    rmse = np.sqrt(np.mean((mu - y) ** 2))
    nll  = np.mean(np.log(sigma) + 0.5 * ((y - mu) / sigma) ** 2)
    z    = (y - mu) / sigma
    cov1, cov2 = np.mean(np.abs(z) <= 1), np.mean(np.abs(z) <= 2)

    print(f"[{title}]")
    print(f"  test RMSE      : {rmse:.4f}   (delta spans 0.02-0.25)")
    print(f"  test NLL       : {nll:.4f}")
    print(f"  within +/-1 sig: {cov1:.1%}   (ideal 68%)")
    print(f"  within +/-2 sig: {cov2:.1%}   (ideal 95%)")
    print(f"  std of z       : {z.std():.2f}   (ideal 1.0)")
    print(f"  fraction|z|>2  : {np.mean(np.abs(z) > 2):.1%}   (ideal ~4.6%)")

    fig, ax = plt.subplots(1, 2, figsize=(9, 4))

    # predicted vs true
    ax[0].errorbar(y, mu, yerr=sigma, fmt=".", alpha=0.4, ms=4)
    lo, hi = float(y.min()), float(y.max())
    ax[0].plot([lo, hi], [lo, hi], "r--", lw=1)
    ax[0].set_xlabel("true delta"); ax[0].set_ylabel("predicted mu +/- sigma")
    ax[0].set_title(f"{title}: predicted vs true")

    # residual calibration
    ax[1].hist(z, bins=40, density=True, alpha=0.6, label="z=(true-mu)/sigma")
    xs = np.linspace(-5, 5, 200)
    ax[1].plot(xs, np.exp(-xs ** 2 / 2) / np.sqrt(2 * np.pi), "r-", lw=2, label="N(0,1)")
    ax[1].axvline(-2, ls=":", c="gray"); ax[1].axvline(2, ls=":", c="gray")
    ax[1].set_xlabel("z (sigma units)"); ax[1].set_ylabel("density")
    ax[1].set_title("residual calibration"); ax[1].legend()

    plt.tight_layout(); plt.show()
    return dict(rmse=rmse, nll=nll, cov1=cov1, cov2=cov2, z_std=z.std())