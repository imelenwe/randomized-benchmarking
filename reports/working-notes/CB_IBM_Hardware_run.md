qiskit_runtime_service._resolve_cloud_instances:WARNING:2026-06-07 09:40:08,385: Default instance not set. Searching all available instances.
ibm_fez: operational=True, pending_jobs=0
  Paulis (K)         : 15
  Lengths            : 2  (m1=4, m2=8)
  Draws per (P,m)    : 5
  Pairs              : 1
  Cycle gates        : 1
  ────────────────────
  Circuits per pair  : 150
  TOTAL CIRCUITS     : 150
  Shots per circuit  : 200
  TOTAL SHOTS        : 30,000
==================================================================
Cycle cz on ibm_fez, qubits [38, 49] noisy
[ 1/15] P=IX   λ=0.9936  (elapsed 83.6s)
[ 2/15] P=IY   λ=0.9903  (elapsed 177.4s)
[ 3/15] P=IZ   λ=1.0000  (elapsed 274.1s)
[ 4/15] P=XI   λ=0.9075  (elapsed 350.7s)
[ 5/15] P=XX   λ=0.4220  (elapsed 412.2s)
[ 6/15] P=XY   λ=0.9906  (elapsed 475.9s)
[ 7/15] P=XZ   λ=0.9957  (elapsed 538.1s)
[ 8/15] P=YI   λ=0.9585  (elapsed 599.2s)

====================================================================================================================================

ibm_fez: operational=True, pending_jobs=0
==================================================================
Continuation on ibm_fez, qubits [38, 49], 7 Paulis
[ 1/7] P=YX   λ=0.9142  (elapsed 66.1s)
[ 2/7] P=YY   λ=0.7753  (elapsed 127.1s)
[ 3/7] P=YZ   λ=0.7966  (elapsed 187.9s)
[ 4/7] P=ZI   λ=0.9935  (elapsed 248.1s)
[ 5/7] P=ZX   λ=0.9928  (elapsed 308.3s)
[ 6/7] P=ZY   λ=0.9946  (elapsed 368.0s)
[ 7/7] P=ZZ   λ=1.0000  (elapsed 428.3s)

Remaining λs:
  YX: 0.9142
  YY: 0.7753
  YZ: 0.7966
  ZI: 0.9935
  ZX: 0.9928
  ZY: 0.9946
  ZZ: 1.0000


ibm_fez/[38, 49]
  P      measured
  IX       0.9936
  IY       0.9903
  IZ       1.0000
  XI       0.9075
  XX       0.4220
  XY       0.9906
  XZ       0.9957
  YI       0.9585
  YX       0.9142
  YY       0.7753
  YZ       0.7966
  ZI       0.9935
  ZX       0.9928
  ZY       0.9946
  ZZ       1.0000
  F_RC     0.9150
  F_RC: 0.9150 vs IBM's CZ error 0.0503
  P       λ_P(measured)  λ_P(expected)        Δ
  XX             0.4220         0.9017  -0.4797
  XY             0.9906         0.8987  +0.0919
  XZ             0.9957         0.9075  +0.0882
  YX             0.9142         0.9524  -0.0381
  YY             0.7753         0.9492  -0.1739
  YZ             0.7966         0.9585  -0.1619
  ZX             0.9928         0.9871  +0.0057
  ZY             0.9946         0.9838  +0.0108
  ZZ             1.0000         0.9935  +0.0065
