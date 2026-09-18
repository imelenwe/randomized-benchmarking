"""CLI driver for the joint (theta_J, theta_x, theta_y) sweep.

    python run_joint_datagen.py 10000

Resumable -- safe to re-run or kill and restart, finished files are skipped.
"""
import sys
from joint_sweep import *

num_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10000

base_config = CBConfig(n_sys_qubits=1, n_env=0, shots=1024, m_list=(2, 4, 6, 8, 12, 16),
                        L=30, K=30, label="CB_cycle", rng=np.random.default_rng(0))

sweep_joint(num_runs=num_runs, base_config=base_config, cycle="I")
print(f"DONE: requested {num_runs} joint runs into data/")
