"""cb_harness.py — the silent engine for DiffusionCB.

Definitions only (no drivers, no plots that render). Import with:
    from cb_harness import *
Holds: CBConfig, noise builders (couple_with_env, make_drift, make_noise),
cycle/Pauli builders, circuit builders, run_once/run_cb, the analysis helpers
(get_expectation_value, lambda_from_records, plot_decay), records_to_dataframe,
noise_knobs, and sweep. Drivers live in generate_cb_data.ipynb.
"""

# ── Cell 1 — Imports ──────────────────────────────────────────────────
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import itertools
from dataclasses import dataclass
from typing import Any
import time
import os

# Quantum info: Paulis, Cliffords, channel representations
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import (
    Pauli, PauliList, Clifford, Operator,
    SuperOp, PTM, DensityMatrix, random_pauli,
)
from qiskit.circuit.library import RXGate

# Aer: simulator, noise channels, sampler primitive (hardware-portable path)
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel, QuantumError, ReadoutError,
    depolarizing_error, pauli_error, coherent_unitary_error,
)
from qiskit_aer.primitives import SamplerV2 as AerSampler
from scipy.linalg import expm

rng = np.random.default_rng(42)

import pandas as pd

# ══════════════════════════════ HELPERS ══════════════════════════════

# ---- Config ----
    
# calculate expected lambdas for different noise models
'''noises = {
    "depolarizing": {"kind":"depolarizing", "p":0.05},
    "dephasing":    {"kind":"pauli", "probs":{"I":0.95, "Z":0.05}},
    "bit_flip":     {"kind":"pauli", "probs":{"I":0.95, "X":0.05}},
    "biased":       {"kind":"pauli", "probs":{"I":0.90, "X":0.03, "Y":0.02, "Z":0.05}},
}'''

@dataclass
class CBConfig:
     n_sys_qubits: int
     n_env: int
     shots: int
     m_list: tuple
     L: int
     K: int
     label: str
     rng: np.random.Generator
     factorization: bool = False
     transpile_fn: Any = None
     verbose: bool = False
     reset_env: bool = False
     env_coupling_gate: Any = None   # the U_SE gate; None = no environment coupling

# ---- Oracle: expected λ_P ----

# helpers for expected lambdas here

def to_probs(noise):
    if noise["kind"] == "depolarizing": 
        # see above depol doesnt have probs
        p = noise["p"]
        return {"I": 1-3*p/4, "X": p/4, "Y": p/4, "Z": p/4}
    return noise["probs"]


def expected_lambda(probs, P):
    P = Pauli(P)
    return sum(prob * (1 if P.commutes(Pauli(Q)) else -1) for Q, prob in probs.items())


# predicts what is lambda_P if noise were independent
def expected_lambda_orbit(probs, P, G_map):
    # ---- Step 1: FIND THE ORBIT (this loop is the orbit-finding) ----
    orbit, Q = [], Pauli(P)
    while True:
        label = Q.to_label().lstrip("+-i") # drop the sign
        orbit.append(label) # append to orbit
        Q = Q.evolve(G_map, frame="s") # sandiwch G with Q
        if Q.to_label().lstrip("+-i") == P: # string sign again and check if reached a circle, if yes stop. we found the orbit.
            break
    # ---- Step 2: BARE λ at each spot (per-qubit product) ----
    bare_lambdas = [np.prod([expected_lambda(probs, op) for op in label]) for label in orbit]

    # ---- Step 3: GEOMEAN (root = orbit size) ----
    return np.prod(bare_lambdas) ** (1 / len(orbit))    

# ---- Cycle / noise / Pauli builders ----
# Cell 2 - Helpers
# make_cycle
def make_cycle(gate_name, n_sys_qubits):
    # return the QC with the gate appended
    qc = QuantumCircuit(n_sys_qubits)
    if gate_name == "I":
        order = 1
    elif gate_name == "s":
        order = 4
        for qbit in range(n_sys_qubits):
            qc.s(qbit)
    elif gate_name == "cz":
        order = 2
        for qbit in range(0,  n_sys_qubits-1, 2):
            qc.cz(qbit, qbit + 1)
    elif gate_name == "H":
        for qbit in range(n_sys_qubits):
            qc.h(qbit)
        order = 2
    
    return qc, order


def make_noise(noise, n_sys_qubits, label):
    kind = noise["kind"]
    full_error = None
    if kind == "correlated":
        full_error = pauli_error(list(noise["probs"].items()))
    else:
        if kind == "depolarizing":
            error = depolarizing_error(noise["p"], 1)
        elif kind == "pauli":
            error = pauli_error(list(noise["probs"].items()))
        full_error = error
        
        for _ in range(n_sys_qubits -1):
            full_error = full_error.tensor(error)
    
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(full_error, label)
    return nm, full_error.to_quantumchannel()  


# create the pauli comnibations based on qubit size
# for 1 qubit = 4 paulis and 2 qubit =15 paulis use all of them as K
# for 3 qubits onwards trim the list to get a smaller K then len(paulis)

def make_paulis(n_sys_qubits, rng, K=None):

    paulis = [''.join(p) for p in itertools.product("IXYZ", repeat = n_sys_qubits)]
    paulis.remove("I"*n_sys_qubits) # remove the identity
    if n_sys_qubits>2 and K is not None and K<len(paulis):
        return [paulis[i] for i in rng.choice(len(paulis), size=K, replace=False)]
    else:
        return paulis # return as is do not trim for 1 and 2 qubits

# ---- Coupling: non-Markovian S–E environment ----

def couple_with_env(delta, J=1.7, hx=1.47, hy=-1.05):
    # as per PRX paper on non markovian RB
    X = np.array([[0, 1], [1, 0]], dtype=complex) # X gate
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex) # Y gate
    I = np.eye(2, dtype=complex) # identity
    H = J*np.kron(X, X) + hx * (np.kron(X, I) + np.kron(I,X)) + hy * (np.kron(Y, I) + np.kron(I,Y))
    U = expm(-1j*delta*H) # unitary evolution
    return UnitaryGate(U, label="U_SE")

def make_drift(eps):
    # coherent control error: a fixed small over-rotation on the system qubit,
    # applied identically every cycle. no environment — pure unitary on S.
    return RXGate(eps)


# ---- Circuit builders ----
# build the ideal cycle C(P) and the real_noisy_cycle C̃(ρ) for a given Pauli P, sequence length m and random sequence index l
'''
calcuate_ideal_circuit(P, qc):
Build the ideal dressed circuit (same twirls random_paulis + ideal G_map, no noise), then push the probe Pauli P through it classically:

output = Pauli(P).evolve(qc, frame='s')   # P → ±P  (Clifford circuit permutes/signs Paulis)
return 1 if output.phase == 0 else -1     # phase 0 → +1,  phase 2 → −1
Because everything ideal is Clifford, P maps to exactly ±P. That sign is the noiseless answer: measuring P on that circuit would give exactly +1 or −1, deterministically. It's computed on paper (no shots). '''

def calculate_ideal_circuit(P, qc):
    output = Pauli(P).evolve(qc, frame='s')
    assert output.phase in (0,2)
    return 1 if output.phase == 0 else -1

    

def prep_eigenstate(qc, P):
    for qbit, op in enumerate(P[::-1]): # we pass pauli as XZ but qiskit thinks Z is first qubit ie q0 so we reverse this by [::-1]
        if op == "X":
            qc.h(qbit)
        elif op == "Y":
            qc.h(qbit)
            qc.s(qbit)

    
def apply_dressed(qc, random_paulis, G, env_coupling_gate=None, reset_env=False):
    for i , random_pauli in enumerate(random_paulis):
        for qbit, op in enumerate(random_pauli[::-1]):
            if op == "X":
                qc.x(qbit)
            elif op == "Y":
                qc.y(qbit)
            elif op == "Z":
                qc.z(qbit)
        if i < len(random_paulis)-1:
            qc.append(G, range(len(random_pauli)))
            if env_coupling_gate is not None:
                qc.append(env_coupling_gate, range(env_coupling_gate.num_qubits)) # last qubit is env assumes only 2 qubits are there TODO: FIX ME
                if reset_env:
                    qc.reset(range(len(random_pauli), env_coupling_gate.num_qubits)) # reset the env qubit to |0> for next cycle range(start, stop) — start=1, stop=2  →  [1]


def measure_P(qc, P):
    for qbit, op in enumerate(P[::-1]):
        if op == "X":
            qc.h(qbit)
        elif op == "Y":
            qc.sdg(qbit)
            qc.h(qbit)
    qc.measure(range(len(P)), range(len(P))) # measure only system 



def build_real_circuit(P, m, random_paulis, cfg, G_gate):
    qc = QuantumCircuit(cfg.n_sys_qubits + cfg.n_env, cfg.n_sys_qubits)
    prep_eigenstate(qc, P)
    apply_dressed(qc, random_paulis, G_gate,
                  env_coupling_gate=cfg.env_coupling_gate, reset_env=cfg.reset_env)
    measure_P(qc, P)
    return qc

# ---- Analysis ----

def get_expectation_value(counts, P, shots):
    P = P[::-1] # reverse to match qiskit's ordering
    total = 0
    for bitstring, c in counts.items():
        bitstring = bitstring[::-1] # reverse to match qiskit's ordering
        eigenvalue = 1
        for i in range(len(P)):
            if P[i] !="I" and bitstring[i] =='1':
                eigenvalue *= -1
        total += eigenvalue * c
    return total / shots


def lambda_from_records(record_runs, cfg):
    lambdas = {}
    for P, m_dict in record_runs.items():
        F = {}
        for m, runs in m_dict.items():
            #f_{P,m,l} = Tr[ (ε_l · P) · C̃(ρ) ] = ε_l · Tr[ P · C̃(ρ) ]
            #f_{P,m,l} = ε_l · ⟨P⟩

            f_pmls = [run["pauli_sign"] * get_expectation_value(run["counts"], P, cfg.shots) for run in runs]
            F[m] = np.mean(f_pmls)
        m1 = cfg.m_list[0]
        m2 = cfg.m_list[-1]
        lambdas[P] = (F[m2]/F[m1]) ** (1/(m2-m1))
    return lambdas


def print_lambdas(name, measured, expected=None):
    print(f"\n  {name}")
    if expected is None:
        print(f"  {'P':<5}{'measured':>10}")
        for P in measured:
            print(f"  {P:<5}{measured[P]:>10.4f}")
        print(f"  {'F_RC':<5}{np.mean(list(measured.values())):>10.4f}")
    else:    
        print(f"  {'P':<5}{'expected':>10}{'measured':>10}{'Δ':>9}")
        for P in expected:
            print(f"  {P:<5}{expected[P]:>10.4f}{measured[P]:>10.4f}{measured[P]-expected[P]:>+9.4f}")
        e, m = np.mean(list(expected.values())), np.mean(list(measured.values()))
        print("--------------------------------------------")
        print(f"  {'F_RC':<5}{e:>10.4f}{m:>10.4f}{m-e:>+9.4f}")

def plot_decay(record_runs, cfg, title=""):
    for P, m_dict in record_runs.items():
        ms = sorted(m_dict)
        F  = [np.mean([r["pauli_sign"] * get_expectation_value(r["counts"], P, cfg.shots)
                       for r in m_dict[m]]) for m in ms]
        plt.plot(ms, F, "o-", label=f"P={P}")
    plt.xlabel("m (sequence length)")
    plt.ylabel("F_{P,m}")
    plt.yscale("log")
    plt.title(title)
    plt.legend(); plt.grid(True, alpha=0.3); plt.show()

# ══════════════════════════════ RUN MACHINERY ══════════════════════════════


def run_once(P, m, cfg, G_map, G_gate, sampler):
    # this f_pml = Tr[C(P), C̃(ρ)] is the core of the protocol: one random sequence, one shot at the overlap
    random_paulis = ["".join(cfg.rng.choice(list("IXYZ"), cfg.n_sys_qubits)) for _ in range(m+1)] # for each loop picks one ramdom pauli from I, X, Y, Z

    run_qc = build_real_circuit(P, m, random_paulis, cfg, G_gate)
    
    if cfg.verbose:
        print(f"Drawing for P={P}, m={m}, random_paulis={random_paulis}")
        from IPython.display import display
        display(run_qc.draw(output='mpl'))
        cfg.verbose = False  # Reset verbose to avoid cluttering output in subsequent runs

    if cfg.transpile_fn is not None:
        run_qc = cfg.transpile_fn(run_qc)

    ideal_qc = QuantumCircuit(cfg.n_sys_qubits)
    apply_dressed(ideal_qc, random_paulis, G_map) # check this
    pauli_sign = calculate_ideal_circuit(P, ideal_qc)

    results = sampler.run([run_qc], shots=cfg.shots).result()
    counts = results[0].data.c.get_counts()
    return {"counts":counts, "pauli_sign":pauli_sign, "twirl_seq":random_paulis}


'''P has only ±1 eigenvalues. The loop's whole job is: for each measured bitstring, decide whether it's the +1 outcome or the −1 outcome — then average them. ⟨P⟩ is the average of those ±1's, so a number in [−1, +1].

1. For 1 qubit it's trivial (P="Z"): bit "0" → +1, bit "1" → −1. With counts={"0":95,"1":5}:

<Z> = (95·(+1) + 5·(−1)) / 100 = 0.9

That's all. The loop for n=1 literally does (-1)^0 = +1 for "0" and (-1)^1 = −1 for "1".

2. For multiple qubits, a single bitstring's eigenvalue isn't one bit — it's the product of each qubit's ±1. After measure_P rotates P→Z…Z, each qubit gives +1 (bit 0) or −1 (bit 1), and P's eigenvalue is their product:

eigenvalue = (+1 or −1) × (+1 or −1) × ...   over P's support
           = (−1)^(number of 1-bits on the support)
    
'''

def run_cb(paulis_K, cfg, G_map, G_gate, sampler, quiet=False):
    record_runs = {}
    t0 = time.time()
    if not quiet:
        print("==================================================================")
        print(f"Running for {len(paulis_K)} Paulis: {paulis_K}")
    for i, P in enumerate(paulis_K):
        record_runs[P] = {} # dict within dict to store results for each P
        for m in (cfg.m_list):
            record_runs[P][m] = [run_once(P, m, cfg, G_map, G_gate, sampler) for _ in range(cfg.L)]
        if not quiet:
            elapsed = time.time()-t0
            print(f"[{i+1:>2}/{len(paulis_K)}] P={P:<3}  m={list(record_runs[P])} × {cfg.L} seqs [L]  (elapsed {elapsed:.1f}s)", flush=True)

    return record_runs

   
# the run experiment 

def run_markovian_experiment(cfg, cycle_gates, noises):
    paulis = make_paulis(cfg.n_sys_qubits, cfg.rng, cfg.K)
    all_records = {}
    for cycle_gate in cycle_gates:
        G_map, order = make_cycle(cycle_gate, cfg.n_sys_qubits)
        G_gate = UnitaryGate(Operator(G_map).data, label=cfg.label)
        print("==================================================================")
        print(f"Cycle {cycle_gate} (order {order}), {cfg.n_sys_qubits} qubit — expected vs measured λ_P")
        # run the cycle benckhmarking 
        for name, noise in noises.items():
            # expected results
            if (noise["kind"] in ("depolarizing", "pauli")):
                probs = to_probs(noise)
                expected_lambdas = {P: expected_lambda_orbit(probs, P, G_map) for P in paulis}
            elif noise["kind"] == "correlated":
                probs = noise["marginal_probs"]
                expected_lambdas = {P: expected_lambda_orbit(probs, P, G_map) for P in paulis}
                
            else:
                expected_lambdas = None

            # now the real circuit run with noise
            nm, channel = make_noise(noise, cfg.n_sys_qubits, cfg.label)
            sampler = AerSampler(options = {"backend_options":{"noise_model": nm}})
            record_runs = run_cb(paulis, cfg, G_map, G_gate, sampler)
            all_records[(cycle_gate, name)] = record_runs
            measured_lambdas = lambda_from_records(record_runs, cfg)
            print_lambdas(name, measured_lambdas, expected_lambdas)
    return all_records    

def records_to_dataframe(records, label):
    # expect labels as label: {"noistype": "drift", "param": eps, "param_value": 0.1, "seed"}
    rows = []
    for P, m_dict in records.items():
        for m, allrundata in m_dict.items():
            for l, eachrundata in enumerate(allrundata):
                counts = eachrundata["counts"]
                shots = sum(counts.values())
                exp_P = get_expectation_value(counts, P, shots)
                f_pml = eachrundata["pauli_sign"] * exp_P
                rows.append({
                    **label, # spreads noise as cols
                    "P": P, "m": m, "l":l, "f_pml": f_pml,
                    "n_plus": counts.get("0",0),
                    "n_minus": counts.get("1",0),
                    "pauli_sign": eachrundata["pauli_sign"],
                    "twirl_seq": eachrundata["twirl_seq"]
                })
    return pd.DataFrame(rows)

from qiskit.circuit.library import RXGate

PARAM_NAME = {"memory": "delta", "jitter": "delta", "drift": "eps"}

def noise_knobs(noise_class, param):
    # returns the cfg knobs that DEFINE each class
    if noise_class == "memory":
        return dict(n_env=1, env_coupling_gate=couple_with_env(param), reset_env=False)
    if noise_class == "jitter":
        return dict(n_env=1, env_coupling_gate=couple_with_env(param), reset_env=True)
    if noise_class == "drift":
        return dict(n_env=0, env_coupling_gate=RXGate(param),          reset_env=False)
    raise ValueError(noise_class)

from pathlib import Path

DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)

# called from CB harness gen ipynb which helps in creating data for different noise classes and parameters. It sweeps over the classes, params, and seeds to generate data files for each combination. If a file already exists, it skips that run to allow resuming.
def sweep(classes, params, seeds, base, data_dir=DATA_DIR):
    sampler = AerSampler()
    for noise_class in classes:
        for param in params:
            for seed in seeds:
                pname = PARAM_NAME[noise_class]
                fname = data_dir / f"{noise_class}_{pname}{param:.3f}_seed{seed}.parquet"
                if fname.exists():                      # ← resume: skip finished runs
                    print("skip (done):", fname.name); continue

                cfg = CBConfig(n_sys_qubits=base["n_sys_qubits"], shots=base["shots"],
                               m_list=base["m_list"], L=base["L"], K=base["K"],
                               label="CB_Cycle", rng=np.random.default_rng(seed),
                               **noise_knobs(noise_class, param)) #The ** prefix — Python's dict-unpacking operator. **{"a": 1, "b": 2} inside a function call expands to a=1, b=2 as keyword arguments. So **noise_knobs(noise_class, param) expands that returned dict into n_env=1, env_coupling_gate=..., reset_env=False, feeding them straight into the CBConfig(...) call as its final keyword arguments.
                paulis  = make_paulis(cfg.n_sys_qubits, cfg.rng, cfg.K)
                Gmap, _ = make_cycle(base["cycle"], cfg.n_sys_qubits)
                Ggate   = UnitaryGate(Operator(Gmap).data, label=cfg.label)
                # the actual CB run
                rec     = run_cb(paulis, cfg, Gmap, Ggate, sampler)

                label = {"noisetype": noise_class, "param": pname,
                         "param_value": param, "seed": seed}
                records_to_dataframe(rec, label).to_parquet(fname)
                print("saved:", fname.name)


def sweep_for_diffusion(noise_class, n_runs, delta_range, base,
                        data_dir=Path("data_diffusion"), draw_seed=0, log_every=200):
    data_dir.mkdir(parents=True, exist_ok=True)
    sampler  = AerSampler()
    draw_rng = np.random.default_rng(draw_seed)          # rng that picks the δ values
    made = skipped = 0
    for i in range(n_runs):
        param = float(draw_rng.uniform(*delta_range))    # draw FIRST → i↔δ stays stable on resume
        fname = data_dir / f"{noise_class}_run{i:04d}_delta{param:.4f}.parquet"
        if fname.exists():
            skipped += 1; continue

        cfg = CBConfig(n_sys_qubits=base["n_sys_qubits"], shots=base["shots"],
                       m_list=base["m_list"], L=base["L"], K=base["K"],
                       label="CB_Cycle", rng=np.random.default_rng(i),
                       **noise_knobs(noise_class, param))
        paulis  = make_paulis(cfg.n_sys_qubits, cfg.rng, cfg.K)
        Gmap, _ = make_cycle(base["cycle"], cfg.n_sys_qubits)
        Ggate   = UnitaryGate(Operator(Gmap).data, label=cfg.label)
        rec     = run_cb(paulis, cfg, Gmap, Ggate, sampler, quiet=True)   # no per-run spam

        label = {"noisetype": noise_class, "param": PARAM_NAME[noise_class],
                 "param_value": param, "seed": i}
        records_to_dataframe(rec, label).to_parquet(fname)
        made += 1
        if made % log_every == 0:                        # progress every log_every NEW runs
            print(f"[{i+1}/{n_runs}] made {made} new, skipped {skipped}  (last δ={param:.4f})", flush=True)

    print(f"DONE sweep: made {made} new, skipped {skipped} existing -> {data_dir}", flush=True)

