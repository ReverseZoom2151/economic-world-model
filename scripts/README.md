# Stable entry points

These scripts are repository-level commands used by CI, release checks, documentation, and local
research audits. They remain flat because their paths are documented interfaces.

| Script | Ownership |
|---|---|
| `run_conformance.py` | Paper-level evidence report and source verification gate |
| `verify_sources.py` | Locked PDF identity and page-count verification |
| `run_protocol.py` | Prospectively locked credit protocol execution |
| `scientific_stress.py` | Numerical and scientific stress checks |
| `benchmark_experiments.py` | Explicit local runtime and memory measurements |
| `check_distribution.py` | Wheel and source-distribution contents |
| `check_reproducible_build.py` | Repeated-build identity |
| `check_mutation_results.py` | Mutation-testing gate |

Reusable behavior belongs in `src/ewm/`; scripts should remain thin orchestration boundaries.
