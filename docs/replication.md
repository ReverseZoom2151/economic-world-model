# Replication guide

**Document version:** 1.2
**Last reviewed:** 2026-08-28
**Scope:** Reproduce the package's paper claims, protocol checks, and disclosed numerical examples

## Claim vocabulary

This repository uses claim labels with different burdens of evidence:

| Label | Required interpretation |
|---|---|
| `exact-replication` | The locked paper supplies the equations, parameters, and numerical target; an independent check reproduces it within a prespecified tolerance. |
| `conformance` | Code follows a paper definition, protocol, or invariant. It does not assert the same numerical output as the paper. |
| `paper-inspired` | The paper supplies a template and the package identifies every added functional form or parameter. |
| `qualitative-reconstruction` | The paper specifies the mechanism and comparisons but omits inputs required for exact numerical replication. |

The project as a whole is not an exact numerical replica of either paper. Exact claims apply only to
the registered Cong Laboratory II and Laboratory III targets.

## Locked sources

| Source | Locked version | SHA-256 |
|---|---|---|
| Cong, [*Economic World Models and Data-Driven Generative Equilibria*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6559940) | Current draft, April 2026, 72 pages | `c5ed935e09b5b0a607f0523d6be293ba4de1707bc242083ad1cd5a5937820357` |
| Han et al., [*From Economic Agents to Agentic Economies*](https://arxiv.org/abs/2608.06020v1) | arXiv:2608.06020v1, 6 August 2026, 44 pages | `918e51bc34b102a4d51c5a55528cdd90ca78576df2bc1955dee31e65c051c8e6` |

The PDFs are not redistributed. [`references/papers.toml`](../references/papers.toml) contains their
bibliographic identity and expected hashes. Those values are declared locks, not proof that a
command observed local PDF bytes. [`references/conformance.toml`](../references/conformance.toml)
maps paper items to code and evidence.

[`references/replication-targets.toml`](../references/replication-targets.toml) records the numerical
transcription boundary: source locator, classification, typed value, tolerance, implementation
symbol, and evidence test. `source-stated` entries reproduce facts declared by a paper, `derived`
entries follow from declared facts, and `package-authored` entries disclose implementation choices.
A package-authored entry cannot by itself satisfy a source-stated replication target.

### Verify local source files

To inspect PDFs that you supplied in a local directory, run:

```bash
python scripts/verify_sources.py
```

The report compares observed bytes and PDF page structure with the expected registry values. An
ignored PDF that is absent reports `not_present`; absence does not fail this default mode, which is
also suitable for checkouts and CI jobs that do not receive the papers. Hash, page-count, and PDF
structure mismatches fail closed.

For a strict local source audit, require every registered PDF:

```bash
python scripts/verify_sources.py --require-all
```

The verifier neither downloads nor redistributes a source.

## Environment

Use Python 3.11 or 3.12. The CI matrix tests both versions on Ubuntu. Local development also runs
under WSL2. Create an isolated environment from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip check
```

The package records the Python, NumPy, SciPy, pandas, and scikit-learn versions in experiment and
conformance reports. Floating-point last digits can vary across compatible numerical-library builds;
the acceptance ranges below absorb those differences.

## Paper-level conformance

Run:

```bash
python scripts/run_conformance.py
```

Expected conditions:

- the declared conformance and capability-evidence tests pass;
- `schema_version` is `ewm.conformance.v1`;
- `paper_sources` contains the expected registry hashes shown in the table above;
- `source_verification` reports the observation for each local PDF, including `not_present` when an
  ignored file is absent;
- `capability_assessment.achieved_level` is `L2` after a passing suite and `L0` when the suite is
  failed or not run;
- `ddge_assessments.cong-lab-ii.status` is `supported` after the scalar conformance check passes,
  while unexercised scenario claims remain `not_assessed`;
- `empirical_validity` is `not_assessed`;
- the report lists the missing external evidence for L3 through L6, calibration, policy use, and
  exact credit replication.

The conformance fingerprint changes when package code, conformance registries and protocols, or the
reporter changes. Compare it only when reproducing a specific commit.

To combine conformance with a strict local PDF gate, run:

```bash
python scripts/run_conformance.py --require-sources
```

Without `--require-sources`, `not_present` is reported but is not a conformance failure. Any source
that is present but has the wrong hash, page count, or PDF structure still fails.

## Cong Laboratory II: exact scalar DDGE

Run:

```bash
python -m pytest tests/scenarios/test_scalar.py -q
python examples/scalar.py
```

The exact obligations are:

- Equation (A.1) agrees with its closed-form inner solution;
- the linear intervention fixed point agrees with the closed form within $10^{-11}$;
- the saturating model has one DDGE when composite gain $g\leq1$ and three when $g>1$;
- package-import-free direct-equation bracketing and package fixed-point iteration agree within
  $10^{-9}$;
- the independent analytical argument gives one root for $g\leq1$ and three for $g>1$ from oddness,
  the derivative at zero, and strict concavity on the positive axis;
- every fixed-point residual is below $10^{-10}$;
- the Figure 3 near-onset relative error stays below `0.0265` through $g=1.045$ and is
  $0.029\pm0.0002$ at $g=1.05$;
- damping stabilizes the declared contrarian oscillation and does not stabilize the repelling
  self-confirming origin.

The public example's current symmetric roots are approximately
$\{-0.71251478,0,0.71251478\}$, with the origin unstable and the outer roots stable.

## Cong Laboratory III: population targets and package-authored finite-sample damping

Run:

```bash
python -m pytest \
  tests/scenarios/test_forecasting.py \
  tests/scenarios/test_forecasting_replication.py \
  tests/integration/papers/test_independent_numerical_oracles.py -q
python examples/forecasting.py
```

The locked Figure 4 parameters are $c=1.8$, $\sigma=0.5$, and 4,000 observations per finite-sample
retraining round. Seed 42 and damping 0.5 produce the package report. The paper does not state the
damping coefficient, so `references/replication-targets.toml` classifies it as package-authored and
the report exposes it in provenance. It controls the reported numerical path but is not evidence for
a source-stated value.

Expected acceptance conditions:

- population roots lie within `0.003` of $\{-0.795,0,0.795\}$;
- the outer roots are exact negatives within $10^{-12}$ under the analytical odd-symmetry
  implementation;
- maximum population fixed-point residual is below $10^{-10}$;
- the numerical derivative at zero agrees with $c=1.8$ within 1 percent;
- seeds 42 and 101 send initial values $-0.1$ and $0.1$ to the matching sign basins;
- finite-sample noise ejects a zero initialization and ends with absolute slope above `0.7`;
- the momentum ACF is within `0.03` of the positive population root, the zero-model ACF has absolute
  value below `0.03`, and their difference exceeds `0.7`.

The current public report prints `paper_outer_root=0.79532610`, `momentum_acf=0.797495`, and
`zero_acf=0.017492` for seed 42.

The population target match and the finite-sample path are separate claims. A package-import-free
oracle discretizes the stationary Markov kernel, solves its invariant law, computes the
zero-intercept OLS map, and brackets the roots. It agrees with the package population roots within
`0.004`. Its declared scope excludes finite-sample paths. Those paths remain `paper-inspired`
because damping is package-authored.

## Cong Laboratory I: qualitative credit reconstruction

Run:

```bash
python -m pytest \
  tests/scenarios/test_credit.py \
  tests/scenarios/test_credit_paper_targets.py -q
python examples/credit.py
```

The code tests the published mechanism: 10 structured features, 15 text features, a
26-dimensional ridge-logistic learner, endogenous text-polish adoption, the zero-profit approval
cutoff, selective repayment labels, retraining, and five comparison regimes.

The PDF does not identify the feature loadings, feature noise laws, repayment link, enhancement
parameters, adoption-cost law, payoffs, ridge penalty, retraining damping, seeds, sampling-noise
estimator, or stated companion-code URL. Package values must therefore be read as a synthetic
qualitative reconstruction. The report exposes package-minus-paper differences and does not turn
those differences into replication claims.

Exact numerical replication remains blocked until the omitted author primitives or code are public
and their identity can be locked.

Run the shipped prospectively locked local quick protocol with:

```bash
ewm-run-protocol --quick
```

The command is expected to exit 1. All four fixed seeds complete, and all four breach the locked
`solver_residual <= 0.001` tolerance. The report preserves every outcome and seed but sets
`status=fail`, `analysis_valid=false`, `claim_authorized=false`, and
`evidence_status=diagnostic_only`. Do not treat its Student-t, paired-bootstrap, Wilson, or Holm
summaries as authorized inference.

## Cong Appendix D: paper-inspired production instance

Run:

```bash
python -m pytest \
  tests/scenarios/test_production.py \
  tests/integration/examples/test_production_example.py \
  tests/integration/papers/test_independent_numerical_oracles.py -q
python examples/production.py
```

Expected output for the documented package instance:

```text
converged=True rental_rate=0.147500 wage=0.718658 clearing_norm=3.764e-14
primitive_source=package-authored; template_source=Cong Appendix D
```

Accept the result when:

- household budget residuals are below $10^{-10}$;
- household first-order residuals are below $10^{-9}$ for the default instance;
- capital and labor clearing residuals are below $10^{-9}$;
- firm first-order residuals are below $10^{-10}$;
- a package-import-free objective optimizer and market-clearing solve agree on both prices within
  $2\times10^{-5}$ and satisfy their separate residual budgets.

Cong supplies the household budget and borrowing bound, the firm problem, and current-asset and labor
market clearing. The package supplies CRRA preferences, a continuation approximation, a finite
cross-sectional distribution, Cobb-Douglas exponents, productivity, depreciation, and parameter
values. The printed prices are not paper targets.

## Han protocol conformance and capability gates

Run:

```bash
python -m pytest \
  tests/integration/runtime/test_han_runtime_protocol.py \
  tests/integration/experiments/test_layered_evaluation.py \
  tests/conformance/test_han_conformance.py \
  tests/conformance/test_han_l1_l2_validation.py \
  tests/conformance/test_han_l3_l6_readiness.py \
  tests/unit/capabilities/test_capability_levels.py -q
python examples/cognitive_agent.py
python examples/offline_alignment.py
```

The end-to-end test requires this event sequence:

```text
reset -> run_agents -> step -> coevolve -> align -> evaluate
```

`log` is the event ledger that records all six stateful calls. The layered evaluator then reads the
immutable event snapshot. Metrics without evidence remain `not_measured` and `None`.

The compiled FX protocol uses adaptive and fixed-belief arms under seeds 17 and 42. It emits one
validated artifact for each L1/L2 requirement and awards L2 as synthetic systems conformance. The
L3 to L6 readiness protocol emits 16 blocked `readiness:` artifacts and zero higher awards. Offline
cognition, promotion, governance, and alignment fixtures remain below the official evidence gates.

## Artifact verification and replay

Create, verify, and replay a sealed FX artifact:

```bash
ewm run fx.rollout --preset smoke --seed 42 --output runs
ewm verify-run runs/<run_hash>
ewm replay-run runs/<run_hash>
```

Current runs use `ewm.run.v2`, which seals all five payloads and the canonical run identity. Legacy
`ewm.run.v1` bundles receive read-only structural verification and remain unsealed. Deterministic
replay currently supports sealed v2 `fx.rollout` bundles only.

## Full local verification

Run the release gates:

```bash
ruff check .
mypy src
coverage run -m pytest -q
coverage report
python -m build
python scripts/run_conformance.py
python scripts/verify_sources.py --require-all
python scripts/run_conformance.py --require-sources
python scripts/scientific_stress.py
python scripts/benchmark_experiments.py
```

The two strict source commands require the ignored paper PDFs to have been supplied locally. Remote
CI that has only tracked repository contents should use the non-strict conformance command and will
record `not_present` rather than claiming to have observed those files.

The benchmark takes several minutes because it repeats the 50-replication FX research workload in
fresh processes. Performance numbers describe the recorded local environment, not a service-level
objective.

See [limitations](limitations.md) before interpreting any result as evidence about an observed
economy.
