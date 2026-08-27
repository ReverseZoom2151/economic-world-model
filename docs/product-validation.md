# Local product validation

**Document version:** 1.0<br>
**Last reviewed:** 2026-08-27<br>
**Environment:** Python 3.12.3 on x86-64 WSL2, 64 logical CPUs<br>
**Scope:** Version `0.1.0` software behavior and synthetic scientific evidence

## Outcome

The package passes the locally executable product tests: clean installation, public CLI and Python
workflows, deterministic artifact reproduction, extension through public interfaces, prespecified
scientific stress tests, and isolated performance measurement.

This does not test whether independent economic-AI researchers understand or value the package.
That requires external participants. It also does not provide empirical validation, policy validity,
or evidence that the synthetic economies represent an observed economy.

## Protocol

The local audit used six complementary tests.

1. Clone the public GitHub repository into an empty temporary directory, create an isolated virtual
   environment, install the development package, run `pip check`, discover the registry, execute a
   smoke experiment, and run a documented example.
2. Run all four experiments through the public CLI with smoke and research presets. Validate every
   artifact file, metric, trace, event sequence, run hash, and finite numerical value.
3. Repeat all smoke runs at seed 42 and compare every artifact byte. Repeat at seed 43 and require
   both the run identity and at least one substantive metric to change.
4. Implement a fourth economy outside `src/ewm` using only `ewm`, `ewm.core`, and
   `ewm.equilibrium`.
5. Run the prespecified feedback, market, population, and intervention grids in
   `scripts/scientific_stress.py`.
6. Measure isolated public-API latency and peak resident memory with
   `scripts/benchmark_experiments.py`, then profile the slowest workload with `cProfile`.

No internal application component was mocked. Generated run bundles remained under ignored local
directories and were not used as source code.

## Clean-room and researcher workflow

The public repository at baseline commit `c226c18` installed into an empty virtual environment with
no broken requirements. `ewm list`, `ewm run forecasting.ddge`, and `examples/forecasting.py`
completed from the clone.

The extension test found one real API problem: the documented `World` runtime was not exported by
`ewm.core`. The public export is now explicit. The external
[`cobweb.py`](../examples/extensions/cobweb.py) example composes agents, a constraint, a market
mechanism, and a DDGE problem without importing package implementation modules.

The extension uses linear demand and forecast-conditioned supply:

$$
Q^d=A-Bp,
\qquad
Q^s=a+b\theta.
$$

Market clearing and naive price retraining give

$$
F(\theta)=\frac{A-a-b\theta}{B},
\qquad
\theta^{\star}=\frac{A-a}{B+b}.
$$

With $A=10$, $B=2$, $a=1$, and $b=1$, the numerical solver returns
$\theta^{\star}=p^{\star}=3$, $Q^{\star}=4$, and spectral radius $0.5$. A declared demand
intervention with $A=13$ moves the solved price to $4$ and quantity to $5$. Both agree with the
closed-form oracle.

## End-to-end experiment results

All smoke and research runs at seed 42 completed and produced the six-file `ewm.run.v1` bundle.
Every metric and trace value was finite.

| Experiment | Research result |
|---|---|
| `forecasting.ddge` | Three roots, two locally stable under the named configuration, root gap $3.16\times10^{-11}$ |
| `fx.rollout` | 500 clearing events, cash residual $2.47\times10^{-10}$, foreign residual $1.46\times10^{-11}$ |
| `fx.comparative_statics` | 50 paired replications for twelve comparison-metric combinations |
| `credit.regimes` | Five regimes with economic, predictive, observation, and residual diagnostics |

The second seed-42 execution was byte-identical for all four bundles. At seed 43, run hashes changed
for every experiment. Substantive metrics changed in 42 of 65 credit metrics, 2 of 5 forecasting
metrics, 28 of 60 FX comparison metrics, and 4 of 6 FX rollout metrics.

The artifact identity now also includes a SHA-256 fingerprint of the executed `ewm` Python source
and the Python, NumPy, SciPy, pandas, and scikit-learn versions. This prevents two alpha commits with
the same package version and parameters from silently sharing a run directory.

## Prespecified scientific stress test

### Forecasting

The full protocol evaluated 18 cases: feedback values $0.6$, $0.8$, $1.0$, $1.2$, $1.8$, and
$2.2$ under seeds 11, 42, and 303.

- The derivative at zero agreed with its analytical value within $1.31\times10^{-10}$ in every
  case.
- The declared weak-feedback cases had one stable root.
- Feedback values 1.2 and the named 1.8 configuration had three roots and two stable outer roots.
- Iterative and Brent roots agreed within $4.65\times10^{-8}$ across the declared acceptance cases.
- At the critical value 1.0, the two nonzero initializations did not reach tolerance within 500
  iterations. The exact zero initialization remained a fixed point. This is expected near a neutral
  derivative and is retained as a failed-start diagnostic.
- At the exploratory value 2.2, one smoke-sized seed lost one iterative branch and produced an
  unstable finite-difference classification. Research-sized samples recovered all three roots for
  all three seeds, but one branch remained derivative-step sensitive.

For the sensitive branch at feedback 2.2 and seed 42, the estimated derivative ranged from about
$0.008$ at step $10^{-2}$ to $-4.31$ at step $10^{-5}$. The named 1.8 result is therefore supported;
stability classifications in this more extreme finite-sample regime are exploratory and should not
be treated as robust economic conclusions.

### Foreign exchange

The protocol evaluated 81 configurations from three bank depths, three spreads, three trend weights,
and three seeds, each for 120 periods with 12 households.

- Every price remained positive; the minimum was `0.975499`.
- The largest cash residual was $8.73\times10^{-11}$.
- The largest foreign-currency residual was $4.37\times10^{-11}$.
- No order was rejected in this grid. Separate unit and property tests deliberately exercise budget
  and inventory rejection paths.

Fifty paired replications on the stress baseline produced these total-volume effects:

| Intervention minus adaptive baseline | Mean difference | 95% normal interval |
|---|---:|---:|
| Firm-demand shock | 78.25 | [75.18, 81.32] |
| Fixed beliefs | 17.34 | [14.92, 19.76] |
| Stronger trend following | -3.02 | [-5.66, -0.38] |

These are Monte Carlo intervals for this synthetic configuration. They are not empirical confidence
intervals for an observed FX market.

### AI-mediated credit

The protocol evaluated ten independently seeded synthetic populations of 1,200 applicants. The
primary comparison was paired profit per applicant relative to the no-GenAI regime.

| Regime | Mean paired effect | 95% normal interval |
|---|---:|---:|
| Frozen model | -0.00803 | [-0.01119, -0.00486] |
| Selective-observation DDGE | -0.00180 | [-0.00505, 0.00144] |
| Full-information DDGE | 0.00044 | [-0.00264, 0.00352] |

The frozen model predicted a positive intervention effect in every population. Realized profit was
negative in nine populations and exactly unchanged in one, so the strict sign-reversal indicator
held in 9 of 10 cases. Full-information retraining improved realized profit relative to the frozen
model in 10 of 10 cases; selective retraining did so in 8 of 10.

Full-information DDGE reached its declared tolerance in all ten populations. Selective DDGE reached
it in none of the ten: terminal residuals ranged from about `0.0040` to `0.0156`. This is consistent
with the documented discontinuity-cycle limitation, but it means selective results must be described
as residual-qualified approximate states, not exact converged DDGEs.

The five-point polish sensitivity grid retained the zero-adoption boundary and all stronger
interventions, including results that did and did not meet the strict sign-reversal definition.

## Performance baseline

Each measurement ran in a fresh process. Elapsed time starts immediately before the public
`run_experiment` call, so it excludes interpreter startup while peak RSS includes imported numerical
libraries. Smoke results use 10 samples and research results use 5. The p95 and p99 research values
are interpolated from five samples and should be treated as a local baseline, not a production
service-level objective.

| Experiment | Preset | p50 | p95 | p99 | Maximum peak RSS |
|---|---|---:|---:|---:|---:|
| Credit regimes | Smoke | 0.934s | 1.013s | 1.047s | 171 MiB |
| Credit regimes | Research | 7.757s | 8.110s | 8.151s | 316 MiB |
| Forecasting DDGE | Smoke | 0.462s | 0.465s | 0.466s | 152 MiB |
| Forecasting DDGE | Research | 3.656s | 3.665s | 3.665s | 157 MiB |
| FX comparisons | Smoke | 0.337s | 0.348s | 0.351s | 149 MiB |
| FX comparisons | Research | 39.439s | 39.781s | 39.785s | 154 MiB |
| FX rollout | Smoke | 0.256s | 0.268s | 0.269s | 149 MiB |
| FX rollout | Research | 0.447s | 0.451s | 0.451s | 150 MiB |

One cold CLI observation took approximately 1.6 to 2.3 seconds for the smoke experiments, showing
that interpreter and scientific-library startup dominate the smallest workloads.

The 50-replication FX comparison is the clear runtime bottleneck. A 10-replication `cProfile` sample
recorded 65.7 million calls. `clear_market` accounted for about 74% of cumulative time and
`_clearing_price` for about 38%. The candidate-price aggregate scans are the first optimization
target if the research workload becomes interactive. No optimization was applied during this audit;
the measured baseline and deterministic tie-breaking semantics should be preserved before and after
any change.

## Claims audit

| Public claim | Executable evidence | Verdict |
|---|---|---|
| The package executes synthetic EWM and DDGE mechanisms | Public facade, runtime, solvers, three built-in laboratories, and external cobweb extension | Supported for the declared single-valued version 0.1 scope |
| The named forecasting configuration has three roots and two stable outer branches | Analytical derivative, Brent roots, multistart solver, three seeds | Supported at the named 1.8 configuration |
| The FX mechanism enforces conservation | Example, property, rollout, and 81-case stress tests | Supported within floating-point tolerance for declared mechanisms |
| FX interventions have general economic effects | Synthetic paired intervals from explicit configurations only | Not supported as a general or empirical claim |
| Frozen credit predictions can reverse in realized profit | Default named case and 9 of 10 stress populations | Supported as a configuration-dependent synthetic finding |
| DDGE universally repairs the credit intervention | Full repair relative to frozen in 10 of 10 cases; selective repair in 8 of 10; intervals include zero relative to no GenAI | Not supported as a universal claim |
| Selective credit DDGE converges exactly | Zero strict convergences in the ten-population stress test | Not supported; residual-qualified approximation only |
| Runs are reproducible | Byte-identical seed-42 reruns and deterministic content hashes | Supported on the tested software and platform configurations |
| The package is empirically calibrated or policy-valid | No external data, calibration, or real decision connector | Not supported and explicitly disclaimed |
| The package is a Han L3 to L6 world | No LLM agents, self-rewriting capabilities, endogenous institutions, or live correction loop | Not supported and explicitly disclaimed |

Synthetic tests verify code against declared mathematical and accounting contracts. They do not by
themselves validate the behavioral assumptions, representativeness, or real-world relevance of those
contracts.

## Reproduce locally

```bash
python examples/extensions/cobweb.py
python scripts/scientific_stress.py --quick
python scripts/scientific_stress.py
python scripts/benchmark_experiments.py --smoke-repeats 10 --research-repeats 5
```

The full benchmark takes several minutes because it executes the 50-replication FX research workload
five times in isolated processes.

## Work that still requires external participants or data

- Independent researchers must attempt installation, interpretation, modification, and extension
  without author assistance.
- Economic assumptions need review by domain specialists outside the implementation process.
- Empirical calibration and out-of-sample evaluation require an explicit external dataset and target
  estimand.
- Policy or deployment claims require a separate causal design, governance review, and domain safety
  process.
