# Running EWM experiments

**Document version:** 1.2
**Last reviewed:** 2026-08-29
**Audience:** Researchers reproducing or extending release 0.2.0

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
| `forecasting.ddge` | Self-fulfilling forecasting | Population fixed points, derivative agreement, stability, and simulated autocorrelation |
| `fx.rollout` | Heterogeneous foreign exchange | Compiled execution, prices, volume, rejections, accounting residuals, and canonical events |
| `fx.comparative_statics` | Heterogeneous foreign exchange | Common-random-number paired intervention summaries |
| `credit.regimes` | AI-mediated credit | Economic, predictive, observation, and residual diagnostics for five regimes |

Run any smoke experiment with:

```bash
ewm run forecasting.ddge --preset smoke --seed 42 --output runs
ewm run fx.rollout --preset smoke --seed 42 --output runs
ewm run fx.comparative_statics --preset smoke --seed 42 --output runs
ewm run credit.regimes --preset smoke --seed 42 --output runs
```

Replace `smoke` with `research` for the larger named configuration. Research presets increase
numerical scale and runtime, not empirical validity.

## Presets

| Scenario | Smoke | Research |
|---|---|---|
| Forecasting | 4,096 stationary samples, 64 chains, 256 burn-in periods | 131,072 samples, 256 chains, 2,000 burn-in periods |
| FX rollout | 24 periods, 6 households | 500 periods, 40 households, deeper bank liquidity |
| FX comparative statics | 8 paired replications | 50 paired replications |
| Credit | 800 package-generated applicants | 10,000 package-generated applicants and a tighter DDGE tolerance |

Every run serializes its full parameters and claim metadata into `config.json`. A remembered command
or documentation page is not a substitute for that manifest.

## Python facade

Configure and execute a temporal scenario:

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

## Sealed artifact contract

Each current run is written to `<output>/<run_hash>/` with schema `ewm.run.v2`:

| File | Contract |
|---|---|
| `manifest.json` | Canonical identity, full identity digest, shortened run hash, payload digests and sizes, bundle digest, package and runtime versions, source fingerprint, and integrity level |
| `config.json` | Complete experiment identity, scenario parameters, and claim metadata |
| `metrics.json` | Flat finite scalar metrics |
| `summary.csv` | The same metrics in a two-column table |
| `trace.npz` | Deterministic non-object NumPy arrays |
| `events.jsonl` | Contiguous, deterministically ordered event records |

The writer stages the six files, seals every non-manifest payload with SHA-256, verifies the staged
bundle, and publishes it atomically. Equal source, parameters, seed, and numerical runtime produce
the same identity and bytes. An existing path with a different identity or payload is a collision and
fails closed.

Verify a run before reading it as evidence:

```bash
ewm verify-run runs/<run_hash>
```

The verifier rejects missing, extra, linked, malformed, non-finite, unsafe, or checksum-mismatched
content. Legacy `ewm.run.v1` bundles remain available for structural inspection. They are reported
as `legacy-unsealed`, are never modified by verification, and do not gain v2 integrity retroactively.

Replay a supported sealed run with:

```bash
ewm replay-run runs/<run_hash>
```

Replay requires a checksummed v2 bundle and currently supports only `fx.rollout`. It snapshots the
verified manifest, configuration, and events, rebuilds the compiled FX world, and compares the event
chain, state digest, and step count. Forecasting, credit, and FX comparison artifacts can be verified
but are not accepted by `replay-run`.

## Compiled FX execution

`fx.rollout` executes the compiled world declaration. Characterization tests lock the numerical
outputs recorded before the runtime migration for declared configurations and seeds. The compiled
path adds strict action ownership, declared scheduling, state encoding, atomic transition failure,
canonical event hashes, and deterministic replay without changing those declared market results.

FX output includes:

- `mean_price`, `total_volume`, and `volatility` for the synthetic rollout;
- `rejected_orders` for explicit feasibility failures;
- `max_cash_residual` and `max_foreign_residual` for settlement conservation.

`fx.comparative_statics` keeps the original compatibility summary: intervention-minus-baseline mean
differences, standard errors, and normal-approximation Monte Carlo intervals. It makes no p-value
claim. New prospectively locked protocols use the small-sample methods described below.

## Forecasting interpretation

- `root_count` is the number of distinct population fixed points retained after multistart
  deduplication.
- `stable_root_count` uses the local spectral radius for undamped iteration.
- `max_root_gap` compares package iteration with internal package bracketing.
- `derivative_error` compares the numerical derivative at zero with the analytical value.

The package-import-free oracle under `tests/oracles/forecasting_oracle.py` supplies a stronger
cross-check. It builds a stationary Markov kernel on an independent grid, computes the population
zero-intercept OLS map, and brackets its roots. Its scope is
`population_stationary_kernel_ols_only`; it does not reproduce a finite-sample path.

## Credit interpretation

Metrics are prefixed by `no_genai`, `frozen`, `selective_ddge`, `full_information_ddge`, or
`omniscient_oracle`. Each regime reports profit, approval, adoption, observation coverage,
classification diagnostics, coefficient movement, and residuals. Inspect `converged` and the
residual before calling a run an achieved fixed point.

The named configuration is a qualitative reconstruction. Cong's PDF omits numerical population and
learner primitives needed for exact replication. The package's deterministic recent-iterate residual
minimum is not Cong's finite-cohort sampling-noise floor.

## Prospectively locked local credit protocol

The installed protocol command is:

```bash
ewm-run-protocol --quick
```

The shipped v1 protocol fixes its full TOML content hash and semantic hash, exact seed manifests,
sample sizes, stopping rule, outcomes, units, estimand directions, nulls, tolerances, bootstrap
seeds, and Holm family. Its quick and full replication counts of 4 and 12 are engineering budgets,
not a powered empirical design.

Paired continuous outcomes use Student-t intervals, an owned-seed paired percentile bootstrap, a
paired standardized effect, and two-sided p-values. Binary repair rates use Wilson intervals. Holm's
method controls the prespecified three-outcome family.

The current quick execution completes all four fixed-seed replications and breaches the locked
`solver_residual <= 0.001` tolerance in every replication. It exits nonzero and reports:

```text
status=fail
analysis_valid=false
claim_authorized=false
evidence_status=diagnostic_only
```

The outcomes remain recorded for diagnosis. The observed failure did not trigger a retuned protocol,
and no inference or scientific claim is authorized.

## Five-layer evaluation

`evaluate_layered` builds Han et al.'s agent, environment, co-evolution, alignment, and efficiency
sections from an immutable event snapshot plus supplied evidence. Event-derived metrics include
feasible-action rate, constraint violations, adaptation stability, component drift, discrepancy, and
correction magnitude. Supplied measurements carry units, provenance, and sample size.

Absent measurements remain `not_measured` with value `None`, sample size zero, and no provenance.
The evaluator rejects unknown metrics, wrong units, and attempts to override event-derived values.

## Ontology projection and investigation

Project only after a run passes sealed-bundle verification:

```bash
ewm verify-run runs/<run_hash>
ewm ontology project --run-dir runs/<run_hash> --output projections/<name>
ewm ontology verify --bundle projections/<name>
```

The projection is a derived artifact. It retains source-run, source-bundle, profile, and projection
digests; it never changes or writes inside the run. Its coverage ledger records each supported field
as `projected`, `omitted`, `rejected`, or `unavailable`.

Create a portable investigation from an explicit JSON selection:

```bash
ewm snapshot export runs/<run_hash> \
  --selection selection.json \
  --output investigations/<name>.html
ewm snapshot verify investigations/<name>.html
```

Snapshots work offline and include the same projection and profile identities. Their internal
digests detect corruption but do not authenticate an author. Pass `--expected-sha256` only with a
full-file digest obtained through a separate trusted channel.

The optional local interface uses:

```bash
python -m pip install -e ".[workbench]"
```

The [ontology guide](ontology.md) defines the six layers and DDGE status distinctions. The
[workbench guide](workbench.md) covers the eight investigation workflows and local API. The
[snapshot guide](snapshots.md) covers selections, hard limits, offline behavior, and sharing.

## Reproducibility checklist

1. Record the package commit and retain the manifest's source and runtime fingerprints.
2. Retain all six files, especially `manifest.json` and `config.json`.
3. Run `ewm verify-run` before comparing metrics.
4. Compare full identities and bundle hashes before numerical results.
5. Use paired seeds or common random numbers for intervention comparisons.
6. Preserve failed starts, rejected actions, residuals, protocol failures, and deviations.
7. Do not interpret Monte Carlo precision as external validity.

## Verification commands

```bash
ruff check .
mypy src
coverage run -m pytest -q
coverage report
python -m build
python scripts/run_conformance.py
python scripts/scientific_stress.py --quick
python scripts/check_workbench_network.py
python scripts/benchmark_workbench.py --tier small --repeats 3
```

CI tests Python 3.11 and 3.12. The [replication guide](replication.md) defines paper-specific commands
and tolerances.
