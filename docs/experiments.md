# Running EWM experiments

**Document version:** 1.0  
**Last reviewed:** 2026-08-27  
**Audience:** Researchers reproducing or extending version `0.1.0`

## Overview

The experiment layer composes scenario economics, shared solvers, metrics, and deterministic local
artifacts. It has no database, service, dashboard, or external model dependency. Every registered
experiment has a fast `smoke` preset and a larger `research` preset.

## Install and discover

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ewm list
ewm describe forecasting.ddge
```

Windows PowerShell uses `.venv\Scripts\Activate.ps1` for activation.

## Registry

| Experiment | Scenario | Main result |
|---|---|---|
| `forecasting.ddge` | Self-fulfilling forecasting | Distinct fixed points, derivative agreement, stability, and simulated autocorrelation |
| `fx.rollout` | Heterogeneous foreign exchange | Prices, volume, volatility, rejections, and accounting residuals |
| `fx.comparative_statics` | Heterogeneous foreign exchange | Replicated paired intervention effects and normal-approximation intervals |
| `credit.regimes` | AI-mediated credit | Economic, predictive, observation, and DDGE metrics for five regimes |

Run any smoke experiment with

```bash
ewm run forecasting.ddge --preset smoke --seed 42 --output runs
ewm run fx.rollout --preset smoke --seed 42 --output runs
ewm run fx.comparative_statics --preset smoke --seed 42 --output runs
ewm run credit.regimes --preset smoke --seed 42 --output runs
```

Replace `smoke` with `research` for the larger named configuration. Research presets are still
synthetic; they increase numerical scale, not empirical validity.

## Presets

| Scenario | Smoke | Research |
|---|---|---|
| Forecasting | 4,096 stationary samples, 64 chains, 256 burn-in periods | 131,072 samples, 256 chains, 2,000 burn-in periods |
| FX rollout | 24 periods, 6 households | 500 periods, 40 households, deeper bank liquidity |
| FX comparative statics | 8 common-random-number replications | 50 common-random-number replications |
| Credit | Named paper-like configuration with 800 applicants | 10,000 applicants and tighter DDGE tolerance |

The complete parameter set is serialized into `config.json`; code, documentation, and a remembered
command are not substitutes for that manifest.

## Python facade

Configure without executing:

```python
import ewm

scenario = ewm.make("fx", preset="smoke", seed=42)
trajectory = ewm.rollout(scenario, periods=24)
print(trajectory.metrics)
```

Solve a declared DDGE problem from explicit starts:

```python
import numpy as np

import ewm
from ewm.equilibrium import FixedPointConfig

scenario = ewm.make("forecasting", preset="smoke", seed=42)
result = ewm.solve_ddge(
    scenario.ddge_problem(),
    (np.array([-1.5]), np.array([0.0]), np.array([1.5])),
    FixedPointConfig(tolerance=1e-9, max_iterations=500),
)
```

Create a complete run bundle:

```python
from pathlib import Path

import ewm

run = ewm.run_experiment(
    "credit.regimes",
    preset="smoke",
    seed=42,
    output_root=Path("runs"),
)
print(run.run_hash, run.run_dir)
```

The corresponding executable programs are in [`examples/`](../examples).

## Artifact contract

Each run is written to `<output>/<run_hash>/` with schema `ewm.run.v1`:

| File | Contract |
|---|---|
| `manifest.json` | Schema, package version, source fingerprint, numerical runtime versions, experiment, scenario, preset, seed, and run hash |
| `config.json` | Full experiment identity and scenario parameters |
| `metrics.json` | Flat, finite scalar metrics for machines |
| `summary.csv` | The same scalar metrics in a two-column research table |
| `trace.npz` | Named numerical arrays such as roots, prices, profits, or residuals |
| `events.jsonl` | Deterministically ordered fixed-point, clearing, or regime records |

The run hash covers artifact schema, experiment, package version, executed EWM source fingerprint,
Python and numerical-library versions, scenario parameters, preset, and seed. Wall-clock time and
output path are deliberately excluded. Repeating identical inputs with the same code and numerical
runtime produces the same hash and byte-identical scientific artifacts. Integration tests enforce
this property.

## Interpreting forecasting output

- `root_count` is the number of distinct fixed points retained after multistart deduplication.
- `stable_root_count` uses the local spectral-radius diagnostic for the undamped update.
- `max_root_gap` compares iterative roots with an independent Brent bracketing calculation.
- `derivative_error` compares the numerical derivative at zero with the analytical value.

Multiplicity is part of the result. A single selected root is not silently substituted for the full
multistart result.

## Interpreting FX output

- `mean_price`, `total_volume`, and `volatility` summarize the rollout.
- `rejected_orders` counts explicit feasibility failures.
- `max_cash_residual` and `max_foreign_residual` audit settlement conservation.

`fx.comparative_statics` reports `firm_demand_shock`, `trend_intensity`, and `fixed_beliefs`
comparisons. Every effect is intervention minus the adaptive baseline. For each output metric it
records the paired mean difference, standard error, interval endpoints, and replication count. The
same seed is used for each baseline-intervention pair; consecutive seeds define the replications.

The FX output describes the synthetic mechanism under its configuration. It is not a forecast of an
observed exchange rate.

## Interpreting credit output

Metrics are prefixed by regime: `no_genai`, `frozen`, `selective_ddge`,
`full_information_ddge`, and `omniscient_oracle`. Each regime reports profit, predicted profit,
approval, adoption, observed-label share, AUC, classification errors, coefficient movement, and
residual diagnostics. The adaptive regimes also report `converged` and `iterations` as flat metrics.
The regime name describes the DDGE target; inspect the convergence flag and residual before calling
one run an achieved fixed point.

The named paper-like preset is a configuration-specific qualitative test. The sensitivity report is
the evidence against treating its sign pattern as universal.

## Reproducibility checklist

1. Record the package commit and retain the manifest's source and runtime fingerprints.
2. Retain the complete run directory, especially `manifest.json` and `config.json`.
3. Compare run hashes before comparing metrics.
4. Use paired seeds or common random numbers for intervention comparisons.
5. Preserve failed starts, rejected actions, residuals, and failed hypotheses.
6. Do not interpret more Monte Carlo precision as more external validity.

## Verification commands

```bash
ruff check .
mypy src
coverage run -m pytest -q
coverage report
python -m build
python examples/forecasting.py
python examples/fx.py
python examples/credit.py
python examples/extensions/cobweb.py
python scripts/scientific_stress.py --quick
```

CI executes this contract on Python 3.11 and 3.12.
