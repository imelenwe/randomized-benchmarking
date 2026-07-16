"""Data module for SBI: raw CB parquet -> 36 features -> train/test tensors.

One run = one (seed, param_value) = 540 rows of f_pml (3 Paulis x 6 m x 30 l).
Features per run = mean + var of f_pml over the 30 twirls, per (P, m) -> 36 numbers.
Target = param_value (the coupling delta).
"""
import numpy as np
import pandas as pd
from pathlib import Path
import torch


def load_features(data_dir="data_diffusion", test_frac=0.2, seed=0):
    """Return standardized train/test tensors: Xtr, ytr, Xte, yte.

    Features are standardized using TRAIN statistics only (no leakage).
    """
    # 1. load all runs
    files = sorted(Path(data_dir).glob("*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

    # 2. per-run features: mean + var of f_pml over the 30 twirls, per (P, m)
    ex_keys = ["seed", "param_value"]
    agg = df.groupby(ex_keys + ["P", "m"])["f_pml"].agg(["mean", "var"]).reset_index()
    feat = agg.pivot_table(index=ex_keys, columns=["P", "m"], values=["mean", "var"])
    feat.columns = [f"{stat}_{P}{m}" for stat, P, m in feat.columns]
    feat = feat.reset_index()

    # 3. X (N x 36) and y (N x 1 = delta)
    feature_cols = [c for c in feat.columns if c not in ("seed", "param_value")]
    X = feat[feature_cols].to_numpy(dtype="float32")
    y = feat["param_value"].to_numpy(dtype="float32").reshape(-1, 1)

    # 4. split (fixed seed)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    n_test = int(test_frac * len(X))
    test_idx, train_idx = idx[:n_test], idx[n_test:]

    # 5. standardize on TRAIN stats only
    mu, sd = X[train_idx].mean(0), X[train_idx].std(0)
    Xn = (X - mu) / sd

    Xtr = torch.tensor(Xn[train_idx]); ytr = torch.tensor(y[train_idx])
    Xte = torch.tensor(Xn[test_idx]);  yte = torch.tensor(y[test_idx])
    return Xtr, ytr, Xte, yte, feature_cols