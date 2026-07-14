"""Continuous-dial data generation for the diffusion model.

Run from the DiffusionCB/ directory (so `from cb_harness import *` resolves).

    python run_gen.py 3        # smoke test: 3 runs
    python run_gen.py          # full run: default 2000

Resumable: each run saves its own parquet and finished files are skipped,
so a re-run continues from where it stopped.

Each file is ~12–16 KB (avg ~14 KB). So:

2,000 files × ~14 KB ≈ ~28 MB. Negligible — basically nothing. Even all three classes later (memory + jitter + drift, ~6,000 files) would be well under 100 MB. And it's gitignored, so none of it touches the repo.


caffeinate -i -s nohup python run_diffusiondatagen.py 2000 > gen.log 2>&1 &
tail -f gen.log

"""
import sys
from cb_harness import *

n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 2000

base = dict(n_sys_qubits=1, shots=1024, m_list=(2, 4, 6, 8, 12, 16),
            L=30, K=30, cycle="I")

sweep_for_diffusion("memory", n_runs=n_runs, delta_range=(0.02, 0.25), base=base)
print(f"DONE: requested {n_runs} memory runs into data_diffusion/")
