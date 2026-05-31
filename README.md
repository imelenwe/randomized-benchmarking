# Randomized Benchmarking

Research code and write-ups for benchmarking quantum gates: Standard RB,
Interleaved RB, and Cycle Benchmarking.

## Notebooks

GitHub's notebook viewer is currently failing on this repo (see
[issue](#known-issues)). Use these links to view the rendered notebooks:

| Notebook | nbviewer | Colab |
|---|---|---|
| **Cycle Benchmarking** — `CB/CB.ipynb` | [view](https://nbviewer.org/github/imelenwe/randomized-benchmarking/blob/main/CB/CB.ipynb) | [open](https://colab.research.google.com/github/imelenwe/randomized-benchmarking/blob/main/CB/CB.ipynb) |
| **Standard + Interleaved RB** — `RB/RB.ipynb` | [view](https://nbviewer.org/github/imelenwe/randomized-benchmarking/blob/main/RB/RB.ipynb) | [open](https://colab.research.google.com/github/imelenwe/randomized-benchmarking/blob/main/RB/RB.ipynb) |

## Reports

- **Cycle Benchmarking write-up**: [`reports/CB_Report.pdf`](reports/CB_Report.pdf) — 7-experiment study (Exps 1–7), correlated `ZZ` crosstalk fingerprint on CZ, N=2 and N=3 scaling. Self-contained: cited numbers are pinned in Appendix A.

## Layout

```
CB/          Cycle Benchmarking notebook + spec
RB/          Standard + Interleaved RB notebook + spec
reports/     CB report (markdown source, PDF, figures)
```

## Known issues

GitHub's notebook viewer returns "An error occurred" for every `.ipynb` in
this repo, including a minimal 2-cell test notebook. Repo-level GitHub-side
issue, not a notebook-content problem. Use the nbviewer / Colab links above
in the interim.
