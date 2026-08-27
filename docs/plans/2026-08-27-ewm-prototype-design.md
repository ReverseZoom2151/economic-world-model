# Initial Economic World Model Package Design

Date: 2026-08-27  
Status: approved for implementation  
Audience: economic-AI researchers  
Repository: `ReverseZoom2151/economic-world-model`

## 1. Objective and claim boundary

Build a research-oriented Python package that makes two complementary Economic World Model
(EWM) proposals executable:

- Cong's equilibrium framework, especially the behavior-data-learning closure formalized as
  Data-Driven Generative Equilibrium (DDGE).
- Han et al.'s systems blueprint, especially typed agents, executable environments, mechanisms,
  co-evolution, evaluation, and a compact environment-style runtime.

Version 0.1 is a synthetic laboratory package. It may claim that transparent EWM/DDGE mechanisms
are implemented and that prespecified theoretical behavior is reproduced. It must not claim empirical
realism, policy validity, real FX calibration, or sim-to-real digital-twin capability.

## 2. Formal model contract

For intervention or regime `i`, the model is

$$
\mathcal W_i =
(\mathcal S,\mathcal A,\mathcal Y,\Theta,
\mathcal I_i,\mathcal B_i,\mathcal U_i,
\Gamma_i,\mathcal K_i,T_i,O_i,D_i,L_i).
$$

The inner equilibrium correspondence is

$$
E_i(\theta)=\{(\pi,\mu): (\pi,\mu)
\text{ satisfies behavior, belief, feasibility, and market conditions under }\theta\}.
$$

The outer learning map is

$$
F_i(\theta)=L_i(D_i(E_i(\theta),\theta)),
$$

and a DDGE satisfies `theta in F_i(theta)`. The implementation reports

$$
r_i(\theta)=d_\Theta(\theta,F_i(\theta)).
$$

Theory permits a set-valued correspondence. Version 0.1 exposes a single-valued problem protocol,
uses multistart search to discover multiple fixed points, and records the selector and initial condition.
It does not pretend to solve arbitrary equilibrium correspondences.

## 3. Runtime semantics

Four operations remain distinct:

1. `rollout`: simulate policies and learned parameters held fixed unless the world explicitly contains
   within-world adaptation.
2. `solve_equilibrium`: solve the fixed-environment behavioral/economic problem.
3. `retrain`: apply one data-generation and learning update.
4. `solve_ddge`: iterate or solve the complete outer fixed-point problem.

The distinction is an invariant. A converged rollout is not automatically an equilibrium, a fitted
model is not automatically a DDGE, and a small DDGE residual supports a welfare statement only
when a suitable sensitivity or contraction bound is available.

## 4. Shared invariants

- Feasibility is checked before a mechanism accepts an action.
- Accounting and market-clearing residuals are explicit diagnostics.
- Inner-equilibrium and outer-DDGE residuals are reported separately.
- Frozen and endogenous learned components are explicit run modes.
- Every stochastic call receives an owned random-number generator; no hidden global RNG is used.
- Generated data and results record seed, scenario, intervention, parameters, package version, and
  run identifier.
- Multiplicity is surfaced through multistart results rather than overwritten.
- Damping is reported as an algorithmic choice and never treated as proof of stability.
- Scenario modules supply economics but do not own generic runners, solvers, artifacts, RNG, or logs.

## 5. Laboratories

### 5.1 Self-fulfilling forecasting

The deployed slope `theta` induces actions and a nonlinear aggregate:

$$
a_t=\theta X_t,\qquad X_{t+1}=\tanh(ca_t)+\sigma\varepsilon_{t+1}.
$$

Retraining estimates the OLS slope of `X[t+1]` on `X[t]` under the deployment-induced law.
The laboratory tests uniqueness below `c=1`, the pitchfork above `c=1`, local derivative
`F'(0)=c`, basin dependence, finite-sample ejection from the unstable zero equilibrium, and the
inability of within-regime fit to rank self-validating worlds.

This is the mathematical acceptance laboratory for the generic DDGE solver.

### 5.2 Multi-agent FX

Households trade speculatively under heterogeneous bounded-memory beliefs, firms trade to meet FX
needs, and banks supply liquidity subject to inventory and exposure limits. A uniform-price batch
mechanism accepts typed orders, clears compatible demand and supply, and settles cash against FX.

Hard properties are budget/inventory feasibility, cash and FX conservation apart from declared
external flows, and clearing equality within tolerance. Prespecified paired experiments test the
effects of firm-demand shocks, trend-following intensity, and adaptive versus fixed beliefs.

The FX laboratory is an L2 adaptive-agent world. It is not an empirical FX model or an L6 twin.

### 5.3 AI-mediated credit

Borrowers have latent repayment quality, ten structured features, and fifteen text features. GenAI
polish shifts the text block in an apparently informative direction without changing repayment.
Borrowers adopt when rewriting flips rejection to approval and their adoption cost is below the loan
benefit. The lender uses ridge-logistic screening, normally sees repayment only for approved loans,
and retrains with damping.

The required regimes are no-GenAI baseline, frozen-model counterfactual, selective-observation
DDGE, full-information DDGE, and an omniscient quality oracle. The primary configuration-specific
hypotheses concern sign-reversing frozen counterfactual error, DDGE repair, selective feedback under
misspecification, and the one-step residual as an inconsistency diagnostic.

The implementation must include parameter sensitivity. Paper-like qualitative results are not
promoted to universal claims or exact numerical replication claims.

## 6. Evidence contract

Each experiment has `smoke` and `research` presets. Smoke presets are deterministic, fast, and
suitable for CI. Research presets use paper-scale or otherwise documented samples, prespecified
grids, and at least 50 common-random-number replications for stochastic comparisons.

Evidence is reported as:

- analytical or numerical-oracle tolerances for transparent deterministic results;
- paired differences, effect magnitudes, and Monte Carlo or bootstrap intervals for stochastic
  comparisons;
- complete seed and configuration manifests;
- explicit failed hypotheses and sensitivity results;
- no post-hoc observed power and no p-value-only conclusions.

Mathematical claims receive two independent checks: analytical/special-case reasoning and numerical
or property-based verification.

## 7. Architecture

The package is a modular monolith with one-way dependencies:

```text
API/CLI -> experiments -> scenarios -> core
                   |          |
                   +------> equilibrium -> core
```

More precisely:

- `core` imports no scenario, equilibrium, or experiment module.
- `scenarios` depend on core protocols and numerical libraries, never on solvers or runners.
- `equilibrium` consumes core problem protocols and never imports scenarios.
- `experiments` composes scenarios and solvers.
- `api` is the stable public facade.

The planned source layout is:

```text
src/ewm/
  api.py
  cli.py
  core/{protocols,records,world,agents,constraints,mechanisms,events,randomness}.py
  equilibrium/{fixed_point,inner,ddge,damping,diagnostics}.py
  scenarios/{forecasting,fx,credit}/
  experiments/{registry,runner,metrics,statistics,artifacts}.py
```

The runtime stack is Python 3.11+, NumPy, SciPy, pandas, and scikit-learn. Development uses pytest,
Hypothesis, Ruff, mypy, and coverage. Version 0.1 has no database, service layer, plugin discovery,
distributed runtime, web application, external economic data, or LLM dependency.

### 7.1 Agent-framework decision

Version 0.1 deliberately has no agent-SDK dependency. Its `AgentPolicy` and `EconomicWorld`
protocols are the compatibility boundary.

- Mesa is the closest conceptual match and may receive an optional adapter after version 0.1. Its
  scheduling, `AgentSet`, batch-running, and data-collection facilities are useful, but making Mesa
  the kernel would duplicate or constrain the EWM-specific action validation, market clearing,
  settlement, event provenance, inner-equilibrium, and DDGE layers.
- PettingZoo is a suitable future adapter when the worlds become multi-agent reinforcement-learning
  environments. Its AEC and Parallel APIs should not dictate the research kernel before an MARL use
  case exists.
- LangGraph may later implement an optional L3 cognitive-policy backend for LLM agents. Durable
  workflow execution and conversational memory are outside the numerical v0 kernel.
- LangChain is unnecessary below that optional backend, and Mastra is excluded because it is a
  TypeScript LLM-application framework while this repository is a Python scientific package.

Adapters must depend on core protocols; core must never import an adapter framework. This preserves
reproducible symbolic agents now and permits Mesa, PettingZoo, LangGraph, or direct model-provider
backends later without rewriting the economy.

## 8. Public API

```python
import ewm

world = ewm.make("fx", preset="smoke", seed=42)
trajectory = ewm.rollout(world, periods=100)

problem = ewm.make("forecasting", preset="research").ddge_problem()
ddge = ewm.solve_ddge(problem)

report = ewm.run_experiment("credit.counterfactual", preset="research", seed=42)
```

Local run artifacts contain a manifest, configuration, metrics, summary table, numerical trace, and
event log. No database or dashboard is involved.

## 9. Conceptual connections and non-equivalences

- DDGE specializes toward performative equilibrium when the deployed learned component is the
  only endogenous feedback object, but the EWM contract also permits beliefs, mechanisms, and
  heterogeneous policies.
- Mean-field equilibrium is recovered only when the learned aggregate and aggregation operator
  match the relevant population consistency map.
- Berk-Nash reasoning motivates best-in-class beliefs under misspecification; it does not make those
  beliefs structurally true.
- Agent-based simulation supplies constructive trajectories, but trajectory convergence alone does
  not establish equilibrium existence or uniqueness.
- A richer learner can reduce approximation error and simultaneously create additional self-validating
  fixed points.
- Damping can repair oscillatory numerical instability, but cannot stabilize a real complementary
  eigenvalue above one.

## 10. Adversarial review and resolutions

The design was reviewed through contribution, methodology, domain, external-validity, and devil's-
advocate lenses.

| Severity | Finding | Resolution |
|---|---|---|
| Critical | Calling three stylized simulations an economic world model could overstate capability. | Publish an explicit capability matrix and claim boundary; FX is L2, forecasting and credit are synthetic DDGE laboratories, and no L6 claim is made. |
| Critical | A generic single-valued fixed-point API could silently erase theoretical multiplicity. | Require multistart searches, store all distinct roots and their basins, and expose selector/initialization metadata. |
| Major | Credit parameters may reproduce a desired sign by construction. | Separate a named paper-like preset from parameter sweeps and report regions where each hypothesis fails. |
| Major | Statistical tests could confuse simulation precision with external evidence. | Use intervals for Monte Carlo uncertainty while stating that synthetic replication provides internal, not empirical, validity. |
| Major | FX trend effects can be non-monotone under constraints. | Prespecify the tested parameter range and retain failed or reversed comparative statics. |
| Major | Small residuals could be sold as small welfare errors. | Report welfare bounds only when contraction and sensitivity inputs are actually computed. |
| Minor | A plugin system would improve future extensibility. | Defer it; an explicit scenario registry is sufficient for version 0.1. |

No unresolved critical finding blocks implementation.

## 11. Implementation order

1. Repository, package metadata, core records, protocols, RNG, and events.
2. World runtime, constraints, mechanisms, and accounting properties.
3. Generic fixed-point/DDGE solver and diagnostics.
4. Forecasting vertical slice.
5. FX vertical slice.
6. Credit vertical slice.
7. Experiment runner, statistical artifacts, documentation, and release verification.

Forecasting retires mathematical risk first; FX then validates market closure; credit comes last
because it composes the largest share of the architecture.
