"""Joint (theta_J, theta_x, theta_y) data generation.

Reuses cb_harness.py's engine unchanged (circuit building, run_cb, parquet
saving) from the neighboring DiffusionCB/ folder. The only new piece is how
the coupling gate gets built: theta_J/theta_x/theta_y go in directly as
J/hx/hy with delta fixed at 1.0, so there's no separate delta to be
degenerate with (see MultiDimDiffusionCB/analysis/index.html for why).

Importable from anywhere -- the sys.path insert below finds cb_harness.py
regardless of the current working directory.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "DiffusionCB"))
from cb_harness import *
from dataclasses import replace


def draw_theta(rng, theta_range=(-1.0, 1.0), realistic_box=(-0.2, 0.2), realistic_frac=0.5):
    # half the draws come from the real-hardware-sized box (dense coverage of
    # theta~0.02-0.2, where actual crosstalk sits), half from the full box
    # (keeps coverage of the anomaly zone theta~0.4-0.7 and the saturated
    # edge near +/-1 -- see MultiDimDiffusionCB/analysis/index.html)
    box = realistic_box if rng.uniform() < realistic_frac else theta_range
    return rng.uniform(*box, size=3)


def sweep_joint(num_runs, base_config, cycle="I", theta_range=(-1.0, 1.0), data_dir=Path("data"), draw_seed=0, log_every=200):
    data_dir.mkdir(parents=True, exist_ok=True)
    sampler = AerSampler()
    draw_rng = np.random.default_rng(draw_seed)
    created = skipped = 0 
    
    for i in range(num_runs):
        theta_J, theta_x, theta_y = draw_theta(draw_rng, theta_range)
        fname = data_dir / f"memory_run{i:04d}_J{theta_J:.4f}_x{theta_x:.4f}_y{theta_y:.4f}.parquet"
        if fname.exists():
            skipped+=1; continue

        gate = couple_with_env(1.0, J=theta_J, hx=theta_x, hy=theta_y)
        updated_cfg = replace(base_config, rng=np.random.default_rng(i), n_env=1, env_coupling_gate=gate, reset_env=False) # non markovian
        paulis = make_paulis(updated_cfg.n_sys_qubits, updated_cfg.rng, updated_cfg.K)
        Gmap, _ = make_cycle(cycle, updated_cfg.n_sys_qubits)
        Ggate = UnitaryGate(Operator(Gmap).data, label=updated_cfg.label)
        records = run_cb(paulis, updated_cfg, Gmap, Ggate, sampler, quiet=True)

        label ={"noisetype": "memory", "theta_J": theta_J, "theta_x": theta_x, "theta_y":theta_y, "seed": i}
        records_to_dataframe(records, label).to_parquet(fname)
        created+=1
        if created % log_every == 0:
            print(f"[{i+1}/{num_runs}] made {created} new, skipped {skipped}  "
                  f"(last: J={theta_J:.3f} x={theta_x:.3f} y={theta_y:.3f})", flush=True)
    print(f"DONE sweep_joint: made {created} new, skipped {skipped} existing -> {data_dir}", flush=True)

