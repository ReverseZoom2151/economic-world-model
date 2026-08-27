# Mathematical contract

**Document version:** 1.0  
**Last reviewed:** 2026-08-27  
**Audience:** Economic-AI researchers and contributors

## Purpose and claim boundary

This document states the mathematical objects that version `0.1.0` makes executable. It separates
notation taken from the source papers from scenario equations introduced by this implementation.
The package is a synthetic research laboratory. None of the equations below is an empirical model
of an actual economy unless a future calibration explicitly establishes that claim.

## Source provenance

| Source | Contribution used here |
|---|---|
| Cong, *Economic World Models and Data-Driven Generative Equilibria* | Formal EWM objects, fixed-environment equilibrium, behavior-data-learning closure, DDGE, multiplicity, stability, and residual diagnostics |
| Han et al., *From Economic Agents to Agentic Economies* | Executable agents and environments, typed state transitions, co-evolution, evaluation, and the six-level capability ladder |
| This package | Single-valued numerical protocols, solver choices, and the forecasting, FX, and credit laboratory equations |

The two papers are linked in the repository [README](../README.md#references).

## Economic World Model objects

Cong's Definition 2.6 defines an EWM as a structured tuple. Its exact blocks are:

| Object | Meaning |
|---|---|
| $\mathcal{S}$, $\mathcal{A}$, $\mathcal{Y}$ | State, action, and outcome spaces |
| $\mathcal{I}$ | Set of interventions or regimes |
| $N$ | Number of agents |
| $\mathcal{I}_t^n$ | Information available to agent $n$ at time $t$ |
| $\Pi^n$ | Admissible policies for agent $n$ |
| $\mu_t^n$ | Agent $n$'s belief representation at time $t$ |
| $\mathcal{C}$ | Economic coherence conditions |
| $T_{\theta}$, $O_{\theta}$ | Learned transition and observation kernels |
| $\Psi$ | Intervention semantics |

Version `0.1.0` realizes these ideas through typed records, agent policies, constraints, mechanisms,
transitions, observations, and explicit scenario configurations. It does not claim that every block is
learned or active in every laboratory.

## Inner equilibrium and outer learning

Let $\pi$ denote the profile of agent policies, $\mu$ the profile of beliefs, $\theta\in\Theta$ the
learned system components, and $i$ the regime. Cong defines $E_i(\theta)$ as the set of
behavior-belief pairs satisfying behavioral optimality and belief consistency while $\theta$ is held
fixed. When this equilibrium is unique, its selector is

$$
S_i(\theta)=(\pi_i(\theta),\mu_i(\theta)).
$$

If $D$ generates data and $L$ retrains the learned component, the induced outer map is

$$
F_i(\theta)=L(D(S_i(\theta),\theta;i)).
$$

A full DDGE $(\pi^{\star},\mu^{\star},\theta^{\star})$ satisfies behavioral optimality, belief
consistency, and learning consistency:

$$
\theta^{\star}=L(D(\pi^{\star},\mu^{\star},\theta^{\star};i)).
$$

Under a single-valued selector, the outer condition reduces to

$$
\theta^{\star}=F_i(\theta^{\star}).
$$

The implementation reports the fixed-point residual

$$
r_i(\theta)=\lVert F_i(\theta)-\theta\rVert_2.
$$

A small residual establishes local model-data consistency only. Cong's welfare bound additionally
requires contraction and sensitivity assumptions. The package therefore never reports a residual as
a welfare guarantee by itself.

## Executable operations

```text
fixed theta and regime
        |
        v
solve inner equilibrium -> generate data -> retrain once
        ^                                      |
        |                                      v
        +------------ solve outer DDGE <-------+
```

| Operation | Contract |
|---|---|
| `rollout` | Generate a trajectory under a configured world and declared within-world adaptation |
| `solve_equilibrium` | Solve an inner residual $g(z;\theta,i)=0$ while $\theta$ and $i$ remain fixed |
| `retrain` | Apply one data-generation and learning update $\theta'=F_i(\theta)$ |
| `solve_ddge` | Search for all distinct outer fixed points reached from declared initializations |

The four operations are not interchangeable. In particular, trajectory convergence does not prove
economic equilibrium, and inner equilibrium does not prove learning consistency.

## Version 0.1 numerical scope

The theory permits set-valued correspondences. The code accepts a single-valued `DDGEProblem.update`
map and uses multistart iteration to retain distinct fixed points and their initialization basins. It
records failed starts, residual histories, damping, finite-difference Jacobians, spectral radii, and
local stability. It does not solve arbitrary set-valued equilibrium correspondences.

For a differentiable update $F$, the local diagnostic is

$$
J_F(\theta)=\frac{\partial F(\theta)}{\partial\theta},
\qquad
\rho(J_F(\theta^{\star}))<1
$$

for local stability of undamped fixed-point iteration. Damping changes the numerical update to

$$
\theta_{k+1}=(1-\eta)\theta_k+\eta F(\theta_k),
\qquad 0<\eta\leq 1.
$$

Damping is an algorithmic choice. It is not an existence, uniqueness, or welfare proof.

## Forecasting laboratory

The implementation defines

$$
a_t=\theta X_t,
\qquad
X_{t+1}=\tanh(c\theta X_t)+\sigma\varepsilon_{t+1}.
$$

The population retraining map is the zero-intercept OLS coefficient under the stationary law induced
by $\theta$:

$$
F(\theta)=
\frac{\mathbb{E}_{\theta}[X_t\tanh(c\theta X_t)]}
     {\mathbb{E}_{\theta}[X_t^2]}.
$$

Antithetic common random numbers preserve $F(0)=0$ and the analytical derivative $F'(0)=c$ in the
numerical population map. The named strong-feedback preset has three fixed points, with stable outer
branches and an unstable origin. An independent Brent bracketing oracle verifies the roots found by
iteration. A separate realized finite-sample update retains sampling noise and can leave the unstable
origin.

## Foreign-exchange laboratory

At candidate price $p$, aggregate executable demand and supply are

$$
B(p)=\sum_{o\in\mathcal{B}}q_o\,\mathbf{1}\{p_o\geq p\},
\qquad
S(p)=\sum_{o\in\mathcal{S}}q_o\,\mathbf{1}\{p_o\leq p\}.
$$

The uniform-price batch mechanism selects a candidate limit price that maximizes

$$
V(p)=\min(B(p),S(p)),
$$

then uses declared deterministic tie-breaking and pro-rata allocation on the long side. Feasibility is
checked against aggregate reserved cash or foreign currency before settlement. With no declared
external asset flow, every clearing event must satisfy

$$
\sum_n c_n'=\sum_n c_n,
\qquad
\sum_n f_n'=\sum_n f_n.
$$

The tests cover example books and generated feasible books, including budget and inventory
rejections, clearing equality, deterministic matching, and both conservation identities.
Prespecified firm-demand, trend-intensity, and fixed-belief interventions are paired with the
adaptive baseline by common random numbers. The experiment layer reports intervention-minus-baseline
mean differences and normal-approximation Monte Carlo intervals across independent seeds.

## AI-mediated credit laboratory

Each borrower has latent quality, ten structured features, fifteen text features, an adoption cost,
and a common potential repayment outcome. Polish changes only the text block. A borrower adopts
only when polish changes the lender's decision from rejection to approval and the private cost does
not exceed the loan benefit.

The lender uses ridge-logistic probabilities and approves at the zero-profit threshold

$$
\tau=\frac{\ell}{g+\ell},
$$

where $g$ is repayment gain and $\ell$ is loss given default. Selective retraining observes outcomes
only for approved applicants; full-information retraining observes the whole cohort. With retraining
damping $\eta$, the outer map is

$$
F(\theta)=(1-\eta)\theta+\eta\widehat{\theta}(D_{\theta}).
$$

The five regimes are no GenAI, frozen model, selective-observation DDGE, full-information DDGE,
and an omniscient quality oracle. The named paper-like preset exhibits a frozen predicted-versus-realized
profit sign reversal and DDGE repair. Sensitivity cases retain parameter regions where that sign
pattern does not occur. Finite binary selection can produce a small discontinuity cycle; the runner
reports both the terminal residual and the smallest recent residual as a floor.

## Evidence map

| Claim or invariant | Implementation | Independent evidence |
|---|---|---|
| Fixed-point multiplicity and stability | `ewm.equilibrium` | `tests/unit/test_fixed_point.py`, `tests/unit/test_diagnostics.py` |
| Forecasting roots and derivative | `ewm.scenarios.forecasting` | Analytical derivative plus Brent bracketing in `tests/scenarios/test_forecasting.py` |
| FX feasibility and conservation | `ewm.scenarios.fx` | Example and Hypothesis property tests in `tests/scenarios` and `tests/properties` |
| FX comparative statics | `ewm.experiments.fx` | Replicated common-random-number effects and interval tests in `tests/integration/test_comparisons.py` |
| Credit adoption and observation regimes | `ewm.scenarios.credit` | Economic-invariant and sensitivity tests in `tests/scenarios/test_credit.py` |
| One-way dependencies | Package layer boundaries | AST enforcement in `tests/test_architecture.py` |
| Reproducible public runs | `ewm.api`, `ewm.experiments`, `ewm.cli` | Integration tests for identical artifacts and public flows |
